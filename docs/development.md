# Development Guide

## Dev Container (Recommended)

1. Open this project in VS Code
2. When prompted, click **"Reopen in Container"**
3. Wait for the container to build and `post-create.sh` to complete
4. You're ready — pre-commit hooks, linters, and tests are pre-configured

### Docker from inside the dev container

The dev container uses Docker-outside-of-Docker. To run Docker commands that
need host file paths (e.g., volume mounts), use the `LOCAL_WORKSPACE_FOLDER`
environment variable:

```bash
docker run -v "$LOCAL_WORKSPACE_FOLDER/data:/app/data" nextlabs-sdk
```

## Quality Checks

```bash
python ./tools/checks.py              # Run all: Black + Flake8 + MyPy + Pyright
python ./tools/checks.py black        # Run a single check
python ./tools/checks.py flake8
python ./tools/checks.py mypy
python ./tools/checks.py pyright
```

## Tests

```bash
python ./tools/tests.py --short       # Unit tests (filtered output)
python ./tools/tests.py --short --e2e # E2E tests (requires Docker)
python ./tools/tests.py               # Full pytest output
```

## Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. They execute:
- **black** — code formatting
- **flake8** — linting (wemake-python-styleguide)
- **mypy** — type checking
- **pyright** — type checking (Pylance engine)

> **Note:** Use a timeout of at least **120 seconds** when committing via
> tooling, as pyright in particular can be slow.

To run hooks manually:

```bash
pre-commit run --all-files
```

## Docker Build

```bash
# Via script (builds + exports tar):
./tools/build_docker_container.sh

# Skip tar export:
./tools/build_docker_container.sh --no-tar

# Via Compose:
docker compose -f docker/compose.yaml up --build
```

## Bare Metal Setup

For non-Docker deployments:

```bash
./tools/setup_bare_metal.sh
```

## E2E Tests

```bash
python ./tools/tests.py --short --e2e
```

Requires Docker. Spins up a WireMock container that serves stubs derived from
the committed OpenAPI spec at `tests/_openapi/fixtures/nextlabs-openapi.json`.

### Regenerating the OpenAPI fixture

The vendor spec is committed so the test suite stays hermetic. To refresh:

```bash
python tools/fetch_openapi_spec.py
```

This writes the latest spec to
`tests/_openapi/fixtures/nextlabs-openapi.json`. Review the diff, run the test
suite (including `--e2e`), fix any new round-trip or model-registry failures,
then commit. The helper refuses to run in CI.
