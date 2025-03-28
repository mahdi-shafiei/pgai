import psycopg
from psycopg.rows import namedtuple_row
from psycopg.sql import SQL, Identifier
from testcontainers.postgres import PostgresContainer  # type: ignore

from pgai import cli
from pgai.vectorizer.features import Features
from pgai.vectorizer.worker_tracking import WorkerTracking


async def test_vectorizer_internal(postgres_container: PostgresContainer):
    db_url = postgres_container.get_connection_url(driver=None)
    with (
        psycopg.connect(db_url, autocommit=True, row_factory=namedtuple_row) as con,
        con.cursor() as cur,
    ):
        cur.execute("create extension if not exists vectorscale cascade")
        pgai_version = cli.get_pgai_version(cur)
        assert pgai_version is None
        cur.execute("create extension if not exists ai cascade")
        pgai_version = cli.get_pgai_version(cur)
        assert pgai_version is not None
        assert len(cli.get_vectorizer_ids(db_url)) == 0
        assert len(cli.get_vectorizer_ids(db_url, [42, 19])) == 0
        cur.execute("create extension if not exists timescaledb")
        cur.execute("drop table if exists note0")
        cur.execute("""
                create table note0
                ( id bigint not null primary key generated always as identity
                , note text not null
                )
            """)
        # insert 5 rows into source
        cur.execute("""
                insert into note0 (note)
                select 'how much wood would a woodchuck chuck if a woodchuck could chuck wood'
                from generate_series(1, 5)
            """)  # noqa
        # insert 5 rows into source
        cur.execute("""
                insert into note0 (note)
                select 'if a woodchuck could chuck wood, a woodchuck would chuck as much wood as he could'
                from generate_series(1, 5)
            """)  # noqa
        # create a vectorizer for the table
        cur.execute("""
                select ai.create_vectorizer
                ( 'note0'::regclass
                , loading=>ai.loading_column('note')
                , embedding=>ai.embedding_openai('text-embedding-3-small', 3)
                , formatting=>ai.formatting_python_template('$id: $chunk')
                , chunking=>ai.chunking_character_text_splitter()
                , scheduling=>
                    ai.scheduling_timescaledb
                    ( interval '5m'
                    , initial_start=>'2050-01-06'::timestamptz
                    , timezone=>'America/Chicago'
                    )
                , indexing=>ai.indexing_diskann(min_rows=>10)
                , grant_to=>null
                , enqueue_existing=>true
                )
            """)
        row = cur.fetchone()
        if row is None:
            raise ValueError("vectorizer_id is None")
        vectorizer_id = row[0]
        if not isinstance(vectorizer_id, int):
            raise ValueError("vectorizer_id is not an integer")

        cur.execute("select * from ai.vectorizer where id = %s", (vectorizer_id,))
        vectorizer_expected = cur.fetchone()

        # test cli.get_vectorizer_ids
        assert len(cli.get_vectorizer_ids(db_url)) == 1
        assert len(cli.get_vectorizer_ids(db_url, [42, 19])) == 0
        assert len(cli.get_vectorizer_ids(db_url, [vectorizer_id, 19])) == 1
        assert len(cli.get_vectorizer_ids(db_url, [vectorizer_id])) == 1

        # test cli.get_vectorizer
        vectorizer_actual = cli.get_vectorizer(db_url, vectorizer_id)
        assert vectorizer_actual is not None
        assert vectorizer_expected.source_table == vectorizer_actual.source_table  # type: ignore

        # run the vectorizer
        features = Features.for_testing_latest_version()
        worker_tracking = WorkerTracking(db_url, 500, features, "0.0.1")

        await vectorizer_actual.run(db_url, features, worker_tracking, 1)

        # make sure the queue was emptied
        cur.execute("select ai.vectorizer_queue_pending(%s)", (vectorizer_id,))
        actual = cur.fetchone()[0]  # type: ignore
        assert actual == 0

        # make sure we got 10 rows out
        cur.execute(
            SQL("select count(*) from {target_schema}.{target_table}").format(
                target_schema=Identifier(vectorizer_expected.target_schema),  # type: ignore
                target_table=Identifier(vectorizer_expected.target_table),  # type: ignore
            )
        )
        actual = cur.fetchone()[0]  # type: ignore
        assert actual == 10

        # make sure the chunks were formatted correctly
        cur.execute(
            SQL("""
                select count(*) = count(*)
                filter (where chunk = format('%s: %s', id, note))
                from {view_schema}.{view_name}
                """).format(
                view_schema=Identifier(vectorizer_expected.view_schema),  # type: ignore
                view_name=Identifier(vectorizer_expected.view_name),  # type: ignore
            )
        )
        actual = cur.fetchone()[0]  # type: ignore
        assert actual is True


async def test_vectorizer_weird_pk(postgres_container: PostgresContainer):
    # make sure we can handle a multi-column primary key with "interesting" data types
    # this has implications on the COPY with binary format logic in the vectorizer
    db_url = postgres_container.get_connection_url(driver=None)
    with (
        psycopg.connect(db_url, autocommit=True, row_factory=namedtuple_row) as con,
        con.cursor() as cur,
    ):
        cur.execute("create extension if not exists vectorscale cascade")
        cur.execute("create extension if not exists timescaledb")
        cur.execute("create extension if not exists ai cascade")
        pgai_version = cli.get_pgai_version(cur)
        assert pgai_version is not None
        cur.execute("drop table if exists weird")
        cur.execute("""
                create table weird
                ( a text[] not null
                , b varchar(3) not null
                , c timestamp with time zone not null
                , d tstzrange not null
                , note text not null
                -- use a different ordering for pk to ensure we handle it
                , primary key (a, c, b, d)
                )
            """)
        # create a vectorizer for the table
        cur.execute("""
                select ai.create_vectorizer
                ( 'weird'::regclass
                , loading=>ai.loading_column('note')
                , embedding=>ai.embedding_openai('text-embedding-3-small', 3)
                , formatting=>ai.formatting_python_template('$chunk')
                , chunking=>ai.chunking_character_text_splitter()
                , scheduling=>
                    ai.scheduling_timescaledb
                    ( interval '5m'
                    , initial_start=>'2050-01-06'::timestamptz
                    , timezone=>'America/Chicago'
                    )
                , indexing=>ai.indexing_diskann(min_rows=>10)
                , grant_to=>null
                , enqueue_existing=>true
                )
            """)
        row = cur.fetchone()
        if row is None:
            raise ValueError("vectorizer_id is None")
        vectorizer_id = row[0]
        if not isinstance(vectorizer_id, int):
            raise ValueError("vectorizer_id is not an integer")

        cur.execute("select * from ai.vectorizer where id = %s", (vectorizer_id,))
        vectorizer_expected = cur.fetchone()

        # test cli.get_vectorizer
        vectorizer_actual = cli.get_vectorizer(db_url, vectorizer_id)
        assert vectorizer_actual is not None
        assert vectorizer_expected.source_table == vectorizer_actual.source_table  # type: ignore

        # insert 7 rows into source
        cur.execute("""
                insert into weird (a, b, c, d, note)
                select
                  array['larry', 'moe', 'curly']
                , 'xyz'
                , t
                , tstzrange(t, t + interval '1d', '[)')
                , 'if two witches watch two watches, which witch watches which watch'
                from generate_series('2025-01-06'::timestamptz, '2025-01-12'::timestamptz, interval '1d') t
            """)  # noqa

        # run the vectorizer
        features = Features.for_testing_latest_version()
        worker_tracking = WorkerTracking(db_url, 500, features, "0.0.1")
        await vectorizer_actual.run(db_url, features, worker_tracking, 1)

        # make sure the queue was emptied
        cur.execute("select ai.vectorizer_queue_pending(%s)", (vectorizer_id,))
        actual = cur.fetchone()[0]  # type: ignore
        assert actual == 0

        # make sure we got 7 rows out
        cur.execute(
            SQL("select count(*) from {target_schema}.{target_table}").format(
                target_schema=Identifier(vectorizer_expected.target_schema),  # type: ignore
                target_table=Identifier(vectorizer_expected.target_table),  # type: ignore
            )
        )
        actual = cur.fetchone()[0]  # type: ignore
        assert actual == 7
