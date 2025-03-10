# Working on the pgai extension

- [pgai extension development prerequisites](#pgai-extension-development-prerequisites)
- [The pgai extension development workflow](#the-pgai-extension-development-workflow)
- [Controlling pgai extension tests](#controlling-pgai-extension-tests)
- [The pgai extension architecture](#the-pgai-extension-architecture)

## pgai extension development prerequisites

To make changes to the pgai extension, do the following in your developer environment:

* Install:
   * [Python3](https://www.python.org/downloads/).
   * [Docker](https://docs.docker.com/get-docker/).
   * A Postgres client like [psql](https://www.timescale.com/blog/how-to-install-psql-on-mac-ubuntu-debian-windows/) or [PopSQL](https://docs.timescale.com/use-timescale/latest/popsql/).
   * [uv](https://docs.astral.sh/uv/getting-started/installation/)
* Retrieve the API Keys for the LLM cloud providers you are working with.
* Clone the pgai source:
   ```bash
   git clone git@github.com:timescale/pgai.git
   cd pgai
   ```
* Ollama and Text to SQL only:
   * [Run Ollama somewhere accessible from your developer environment](https://github.com/ollama/ollama/blob/main/README.md#quickstart).
   * [Pull the `llama3` and  `llava:7b` models](https://github.com/ollama/ollama/blob/main/README.md#pull-a-model):
     ```shell
     ollama pull llama3
     ollama pull llava:7b
     ollama pull smollm:135m
     ```

## The pgai extension development workflow

To make changes to pgai:

1. Build the docker image
   ```bash
   just ext docker-build
   ```
1. Run the container:
   ```bash
   just ext docker-run
   ```
   The root of the repo directory is mounted to `/pgai` in the running container.
   The working directory is at `/pgai/projects/extension`.

1. Work inside the container:
   * **Docker shell**:
      1. Open get a shell session in the container:

         ```bash
         just ext docker-shell
         ```
         You are logged in as root.

      1. Build and Install the extension

         ```bash
         just ext build
         just ext install-all
         ```

      1. Run the unit tests

         First run the test-server in a second shell
         ```bash
         just ext test-server
         ```
         Then, run the tests in the first shell
         ```bash
         just ext test
         ```

      1. Clean build artifacts

         ```bash
         just ext clean
         ```

      1. Uninstall the extension

         ```bash
         just ext uninstall
         ```

   * **psql shell**:
      1. To get a psql shell to the database in the docker container:

         ```bash
         just ext psql-shell
         ```

1. Stop and start the container:

   ```bash
   # Stop the container
   just ext docker-stop
   # Start the container
   just ext docker-start

1. Delete the container:

   ```bash
   # When stopped, delete the container
   just ext docker-rm
   ```


## Controlling pgai extension tests

The [projects/extension/tests](/projects/extension/tests) directory contains the unit tests.

To set up the tests:

1. In a [.env](https://saurabh-kumar.com/python-dotenv/) file, use the following flags to enable/disable test suites
    ```text
    # enable/disable tests
    ENABLE_VECTORIZER_TESTS=1
    ENABLE_DUMP_RESTORE_TESTS=1
    ENABLE_PRIVILEGES_TESTS=1
    ENABLE_CONTENTS_TESTS=1
    ENABLE_SECRETS_TESTS=1
    ```

1. Some tests require extra environment variables to be added to the .env file
   - **OpenAI**:
      - `OPENAI_API_KEY` - an [OpenAI API Key](https://platform.openai.com/api-keys) for OpenAI unit testing.
   - **Ollama**:
      - `OLLAMA_HOST` - the URL to the Ollama instance to use for testing. For example, `http://host.docker.internal:11434`.
   - **Anthropic**:
      - `ANTHROPIC_API_KEY` - an [Anthropic API Key](https://docs.anthropic.com/en/docs/quickstart#set-your-api-key) for Anthropic unit testing.
   - **Cohere**:
      - `COHERE_API_KEY` - a [Cohere API Key](https://docs.cohere.com/docs/rate-limits) for Cohere unit testing.
   - **Voyage**:
      - `VOYAGE_API_KEY` - a [Voyage API Key](https://www.voyageai.com/) for Voyage unit testing.

   Providing these keys automatically enables the corresponding tests.

## Set up your environment
The pgai extension uses `uv` for dependency management. Dependencies are listed
in the [pyproject.toml](/projects/extension/pyproject.toml) file. uv is already installed in the development
docker container. To use it in your local environment, follow uv's
[installation instructions](https://github.com/astral-sh/uv#installation).
Make sure your uv version is at least `0.5.x`.
```bash
uv --version
```

If not, upgrade it with this command.

```bash
uv self update
```

Change directory into the [projects/extension](/projects/extension) directory and create a
virtual environment. Then, activate it.

```bash
cd projects/extension
uv venv
source .venv/bin/activate
```

Install the project's dependencies into the virtual environment.

```bash
uv sync --no-install-project
```

_NOTE:_ Inside the development container, the python dev/test dependencies are installed
into a virtual environment at `/py/.venv/`.

## Dependency management in the pgai extension

Dependencies are listed in the [pyproject.toml](/projects/extension/pyproject.toml) file.

1. The basic commands are:
   1. **Install dependencies**: `uv sync`
   2. **Add a new dependency**: `uv add <package-name>`
   3. **Remove a dependency**: `uv remove <package-name>`

1. Locking dependencies:
   To allow for installation of the pgai extension without having uv available,
   we provide a `requirements-lock.txt` file in addition to the (canonical)
   `uv.lock` file. Setuptools uses the `requirements-lock.txt` file to install
   dependencies without uv. This file is automatically generated from the
   `uv.lock` file with:
   `uv export --format requirements-txt -o requirements-lock.txt`.

## The pgai extension architecture

pgai consists of [SQL](/projects/extension/sql) scripts and a [Python](/projects/extension/ai) package.

* [Develop SQL in pgai](#develop-sql-in-pgai)
* [Develop Python in pgai](#develop-python-in-pgai)
* [Versions prior to 0.4.0](#versions-prior-to-040):


### Develop SQL in the pgai extension

SQL code used by pgai is maintained in [./projects/extension/sql](/projects/extension/sql).

The SQL is organized into:

* **Idempotent scripts**: maintained in [./projects/extension/sql/idempotent](/projects/extension/sql/idempotent).

  Idempotent scripts consist of `CREATE OR REPLACE` style statements, usually as
  functions. They are executed in alphanumeric order every time you install or
  upgrade pgai. In general, it is safe to rename these scripts from one version to
  the next.

* **Incremental scripts**: maintained in [./projects/extension/sql/incremental](/projects/extension/sql/incremental).

  Incremental files create tables and other stateful-structures that should not be
  dropped when you upgrade from one version to another. Each incremental script
  migrates your environment from one version of pgai to the next. You execute each
  incremental script exactly once. It is separate unit-of-work that either succeeds
  or fails.

  Incremental scripts are executed in alphanumeric order on file name. Once an incremental script is published
  in a release, you must not rename it. To facilitate migration, each incremental file is
  [wrapped](/projects/extension/sql/migration.sql). Each migration id is tracked in the `migration` table. For more information,
  see [./projects/extension/sql/head.sql](/projects/extension/sql/head.sql).

* **Built scripts**: `./projects/extension/sql/output/ai--*.sql`

  `just ext build` "compiles" the idempotent and incremental scripts into the final
  form that is installed into a postgres environment as an extension. A script
  named `./projects/extension/sql/output/ai--<current-version>.sql` is built. For every prior version
  (other than 0.1.0, 0.2.0, and 0.3.0), the file is copied to
  `./projects/extension/sql/output/ai--<prior-version>--<current-version>.sql` to give postgres an upgrade
  path from prior versions. The `./projects/extension/sql/output/ai.control` is also ensured to have the
  correct version listed in it.

  When you release a new version, add the `./projects/extension/sql/output/ai--*<current-version>.sql` scripts to this repo with your
  pull request. The scripts from prior versions are checked in and should not be modified after
  having been released.

If you are exclusively working on SQL, you may want to forego the high-level just
recipes in favor of the SQL-specific just recipes:

1. **Clean your environment**: run `just ext clean-sql` to delete `./projects/extension/sql/output/ai--*<current-version>.sql`.

   The `<current-version>` is defined in `versions()` in [./projects/extension/build.py](/projects/extension/build.py).

1. **Build pgai**: run `just ext build` to compile idempotent and incremental scripts
   into `./projects/extension/sql/output/ai--*<current-version>.sql`.
1. **Install pgai**: run `just ext install-sql-all` to install `./projects/extension/sql/output/ai--*.sql` and `./projects/extension/sql/output/ai*.control` into your local
   Postgres environment.

### Develop Python in the pgai extension

Python code used by the pgai extension is maintained in [./projects/extension/ai](/projects/extension/ai).

Database functions
written in [plpython3u](https://www.postgresql.org/docs/current/plpython.html)
can import the modules in this package and any dependencies specified in
[./projects/extension/pyproject.toml](/projects/extension/pyproject.toml).
Including the following line at the beginning of the database function body will
allow you to import. The build process replaces this comment line with Python
code that makes this possible. Note that the leading four spaces are required.

```python
    #ADD-PYTHON-LIB-DIR
```

In order to support multiple versions of pgai in the same Postgres installation, each version of the Python code and
its associated dependencies is installed in `/usr/local/lib/pgai/<version>`

If you are exclusively working on Python, you may want to forego the high-level just
recipes in favor of the Python-specific ones:

1. **Clean your environment**: run `just ext clean-py` to remove build artifacts from your developer environment.
1. **Install pgai**:
   To compile and install the python package with its associated dependencies.
   * Current version: run `just ext install-py`.
   * Versions prior to 0.4.0: run `just ext install-prior-py`.
1. **Uninstall pgai**: run `just ext uninstall-py` and delete all versions of the Python code from
   `/usr/local/lib/pgai`.


### Building prerelease versions of the extension

We would like to avoid long-lived feature branches and the git headaches that entails. 
Yet some features take a while to mature to a level that we are happy to ship and 
support in production environments. Avoiding feature branches means we may be in 
a position where we need to ship but have SQL code that is not fully ready. 
Making changes to SQL objects once they ship is tricky and painful and should be 
minimized.

We want to:
- avoid long-lived feature branches. 
- merge progress to main
- minimize database migrations that alter existing objects
- avoid installing prerelease code in production databases
- allow prerelease code to be installed/tested/trialed in an opt-in manner
- warn when prerelease code is installed
- avoid supporting extension upgrades after prerelease code has been installed

To this end, we allow prerelease functionality to be gated behind feature flags.
We only build and ship prerelease code if the version being built includes a 
prerelease tag. If the version is a production version, we omit the prerelease 
code altogether. Furthermore, if the feature flag is not enabled, the prerelease 
code is NOT executed/installed. 

Incremental or idempotent files numbered greater than 899 and lower than 999 must have a comment at 
the top of the file with a prefix of `--FEATURE-FLAG: ` followed by the name of 
a feature flag. These files are not executed AT ALL unless a session-level GUC 
like `ai.enable_feature_flag_<feature-flag>` is set to `true` when the 
`create extension` or `alter extension ... update` statement is executed.

Incremental/idempotent files numbered less than 900 must NOT have a feature flag 
comment.

Zero or more feature flag GUCs may be enabled at once. Flags that are enabled
when creating/updating the extension are recorded in the `ai.feature_flag` table.

Since feature-flag-gated code is only built and shipped for prerelease versions
in the first place, it can only be installed in an environment not intended for
production in the first place. If one or more feature flag GUCs is enabled, 
all bets are off. The code is pre-production, may not work, is not supported, 
**and upgrades from this state are not supported**. This is a dead-end state.

We do not generate upgrade paths from prerelease versions to production versions.

When working on pre-release features, tests can be written for these features. 
The tests must create a database, enable the correct feature flag, create the 
extension, and then proceed with testing.

**Example:**

```sql
select set_config('ai.enable_feature_flag_my_new_feature', 'true', false);

create extension ai cascade;
NOTICE:  installing required extension "vector"
NOTICE:  installing required extension "plpython3u"
WARNING:  Feature flag "ai.enable_feature_flag_my_new_feature" has been enabled. Pre-release software will be installed. This code is not production-grade, is not guaranteed to work, and is not supported in any way. Extension upgrades are not supported once pre-release software has been installed.
CREATE EXTENSION
```

Once a feature that was gated is finally blessed and "finished", we need a final 
PR that moves the incremental and idempotent SQL files to their final 
(less than 900) places and removes the feature flag comment. Changes to existing 
code/structures that were previously in a gated file could be folded into the 
original file. Tests must be updated to remove the feature flag references.

Frequently, working on new features requires changes to existing SQL code/structures. 
In the case of gated features, we are not able to make changes inline where the 
original code is defined. These changes have to be included in the gated files. 
While this may be somewhat awkward, it works, and it clearly delineates what 
changes to existing stuff are required for a new feature.

## Release the extension

1. Run `just ext clean-sql` in order to remove any prior generated dev sql.
2. Edit the [build.py](/projects/extension/build.py).
   - Set the version to be released as the first element of the array returned by `versions` function. I.e. `"0.7.0",  # released`.
3. Run `just ext build-release`. This will generate, among other tasks, the final .sql files in `projects/extension/sql/output` and update the version in [__init__.py](/projects/extension/ai/__init__.py).
4. As those files are git-ignored, you need to add those to the git index by forcing the addition. 
   - Run `git add -f projects/extension/sql/output/ai--*<YOUR_NEW_VERSION_HERE>.sql`.
5. Craft the release notes for the new version of the extension. Those should be added into [projects/extension/RELEASE_NOTES.md](/projects/extension/RELEASE_NOTES.md).
   - As we are not using release-please, those notes are not automatically generated. Instead, we need to manually add those.  
     You can use the output of the following command to craft the release notes:
     ```shell
     git log $(git describe --tags --abbrev=0 --match "extension-*")..origin/main --pretty=format:"%s ([%h](https://github.com/timescale/pgai/commit/%h))" projects/extension
     ```
6. Create a PR with all the modified files. Use a commit message such as `chore: release extension <YOUR_NEW_VERSION_HERE>`.
7. Once the PR is merged, create a new [github release](https://github.com/timescale/pgai/releases) using a new tag following the format `extension-<version>`. Copy the release notes for this version into the GitHub release description.
8. Prepare the repo for the next development cycle
   - Add a new version (with the patch version incremented) to the top of the versions list in `build.py`, e.g. `0.8.1-dev`
   - Run `just ext build-release` to re-generate the `sql/ai.control` and `ai/__init__.py` files
   - Add and commit the `build.py`, `sql/ai.control`, and `ai/__init__.py` files
   - Open a new PR with this commit
8. Create a new PR on the following repository replacing the value of the `PGAI_VERSION` variable located in the `Makefile` files with the new version:
   - [timescale/timescaledb-docker-ha](https://github.com/timescale/timescaledb-docker-ha/edit/master/Makefile)

[conventional-commits]: https://www.conventionalcommits.org/en/v1.0.0/
