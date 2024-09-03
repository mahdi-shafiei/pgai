import os

import psycopg
import pytest

# skip tests in this module if disabled
enable_vectorizer_tests = os.getenv("ENABLE_VECTORIZER_TESTS")
if not enable_vectorizer_tests or enable_vectorizer_tests == "0":
    pytest.skip(allow_module_level=True)


def db_url(user: str) -> str:
    return f"postgres://{user}@127.0.0.1:5432/test"


def test_chunking_character_text_splitter():
    tests = [
        (
            "select ai.chunking_character_text_splitter('body', 128, 10)",
            {
                "separator": "\n\n",
                "is_separator_regex": False,
                "chunk_size": 128,
                "chunk_column": "body",
                "chunk_overlap": 10,
                "implementation": "character_text_splitter",
                "config_type": "chunking"
            },
        ),
        (
            "select ai.chunking_character_text_splitter('content', 256, 20, separator=>E'\n;')",
            {
                "separator": "\n;",
                "is_separator_regex": False,
                "chunk_size": 256,
                "chunk_column": "content",
                "chunk_overlap": 20,
                "implementation": "character_text_splitter",
                "config_type": "chunking"
            },
        ),
        (
            r"""
                select ai.chunking_character_text_splitter
                ( 'content'
                , 256
                , 20
                , separator=>'(\s+)'
                , is_separator_regex=>true
                )
            """,
            {
                "separator": r"(\s+)",
                "is_separator_regex": True,
                "chunk_size": 256,
                "chunk_column": "content",
                "chunk_overlap": 20,
                "implementation": "character_text_splitter",
                "config_type": "chunking"
            },
        ),
    ]
    with psycopg.connect(db_url("test")) as con:
        with con.cursor() as cur:
            for query, expected in tests:
                cur.execute(query)
                actual = cur.fetchone()[0]
                assert actual.keys() == expected.keys()
                for k, v in actual.items():
                    assert k in expected and v == expected[k]


def test_validate_chunking_character_text_splitter():
    ok = [
        """
        select ai._validate_chunking_character_text_splitter
        ( ai.chunking_character_text_splitter('body', 128, 10)
        , 'public', 'thing'
        )
        """,
    ]
    bad = [
        (
            """
            select ai._validate_chunking_character_text_splitter
            ( ai.chunking_character_text_splitter('content', 128, 10)
            , 'public', 'thing'
            )
            """,
            "chunk column in config does not exist in the table: content",
        ),
        (
            """
            select ai._validate_chunking_character_text_splitter
            ( ai.scheduling_none()
            , 'public', 'thing'
            )
            """,
            "invalid config_type for chunking config",
        )
    ]
    with psycopg.connect(db_url("test"), autocommit=True) as con:
        with con.cursor() as cur:
            cur.execute("drop table if exists public.thing;")
            cur.execute("create table public.thing (id int, color text, weight float, body text)")
            for query in ok:
                cur.execute(query)
                assert True
            for query, err in bad:
                try:
                    cur.execute(query)
                except psycopg.ProgrammingError as ex:
                    msg = str(ex.args[0])
                    assert len(msg) >= len(err) and msg[:len(err)] == err
                else:
                    pytest.fail(f"expected exception: {err}")