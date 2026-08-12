# Development Guide

## Dev Container (Recommended)

1. Open this project in VS Code
2. When prompted, click **"Reopen in Container"**
3. Wait for the container to build and `post-create.sh` to complete
4. You're ready — pre-commit hooks, linters, and tests are pre-configured

Dependencies are preinstalled in the container's system Python — use `pip`
directly; no `venv`, `pipx`, `uv`, or `poetry` is needed inside the container.

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
python ./tools/tests.py --short --e2e # E2E tests only (requires Docker)
python ./tools/tests.py --short --all # Unit + E2E tests (requires Docker)
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

## Package Build

```bash
python ./tools/build.py
```

There is no project-level Docker image or Compose build checked in. The
`.devcontainer/` Compose files are only for the VS Code development container.

## Local setup without the dev container

If you cannot (or do not want to) use the dev container, set up a local
virtual environment manually:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt -c requirements/constraints.txt
pip install -e . --no-deps
pre-commit install
```

Docker is still required to run the E2E suite (`tests.py --e2e`).

## Dependencies

Token-cache encryption at rest is part of the core library, so `cryptography`
and `argon2-cffi` are now core runtime dependencies (declared under
`[project.dependencies]` in `pyproject.toml`). `keyring` stays in the optional
`[cli]` extra — it is only used by the CLI.

### Who owns what

Renovate's native `pip-compile` manager is the sole owner of the **compiled
lock** `requirements/constraints.txt`. It never edits the lock in isolation: it
reads the **source inputs** from the lock's generated header, updates a source
input, and regenerates the lock in the same pull request. The standalone
`pep621` and `pip_requirements` managers are deliberately disabled so a source
update can never land without its lock.

| Source input | Holds | Update metadata |
| --- | --- | --- |
| `pyproject.toml` | Runtime dependencies as ranges | `fix(deps)`, `rangeStrategy: bump`, patch/minor automerged |
| `requirements/dev-compile.in` | Bare development tool names plus the **compiler pin** | `chore(deps-dev)`, automerged except `pip-tools` |
| `requirements/overrides.in` | Deliberate transitive pins, each with a reason and issue reference | manual review, never automerged |

Because policies are keyed by source file, every update is attributable: a
runtime bump is a `pyproject.toml` change with `fix(deps)` metadata, and
development tooling and pinned transitives are maintained together through the
regenerated lock rather than as separate loose requirement files.

### Updating dependencies

Never hand-edit the compiled lock. Change the relevant source input, then
regenerate:

```bash
python tools/lock.py            # regenerate requirements/constraints.txt
python tools/lock.py --check    # verify it matches the source inputs
```

`--check` is what CI runs. If the compiler cannot resolve the inputs it exits
non-zero with the compiler's own diagnostic plus a one-line repair
instruction — no traceback. Read that diagnostic to tell the two causes
apart: a package or version that does not exist (`No matching distribution
found`) means the requirement itself is wrong, while a reported conflict
(`ResolutionImpossible`) means two source requirements contradict each other.
Either way, relax or correct the offending pin and regenerate. A non-zero
exit whose diagnostic says neither is a crash inside the compiler; its
traceback is passed through untouched. `tools/lock.py`
refuses to run under a Python minor version other than the devcontainer
image's, since the resolved closure is version-specific.

### Upgrading the lock compiler

The compiler pin is exact on both sides, so `pip-tools` updates are never
automerged. Completing one means all three of:

1. bump `constraints.pipTools` in `.github/renovate.json5`,
2. bump `pip-tools==<version>` in `requirements/dev-compile.in`,
3. regenerate the lock with `python tools/lock.py`.

`constraints.pipTools` is deprecated upstream but load-bearing until a
Renovate migration supplies a replacement — re-check it whenever
`RENOVATE_CORE_VERSION` in `.github/workflows/renovate.yml` moves.

### Dependency dashboard

Renovate's **dependency dashboard** issue is the queue of pending and blocked
updates. Use it to see what is waiting on manual review (majors, `pip-tools`,
override-input changes), to retry a failed branch, and to confirm that an
update Renovate should have proposed actually appears.

### Validating the extraction

Changing a dependency-integration file (`.github/renovate.json5`, the source
inputs, the compiled lock, `tools/lock.py`, `tools/renovate_guard.py`, or the
Renovate workflow) triggers the `Renovate extraction smoke test` job. It runs a
local Renovate extraction and hands the **extraction report** to
`tools/renovate_guard.py`, which asserts that `pip-compile` still associates
every source input with the compiled lock. It is intentionally scoped to those
paths and is not a repository-wide required check.

The guard tolerates the warnings a tokenless local extraction always emits
(missing GitHub token, a comments-only override input, `requires-python`, and
build-system requirements) and fails on anything else.

### CI enforcement and its boundary

`Check and Coverage Test` is the single required status. It installs the pinned
compiler first and runs `python tools/lock.py --check` **before** the full
development install, so a source/lock contradiction is reported plainly instead
of being obscured by pip's resolver. A valid lock then continues into the
constrained install, quality checks, the unit/E2E suite, and the package build.

The repository ruleset that requires this status permits administrator bypass.
That bypass is an operational escape hatch for emergencies, not part of the
guarantee: a merge that uses it has not been proven against the compiled lock,
so regenerate and verify the lock in a follow-up pull request.

## E2E Tests

```bash
python ./tools/tests.py --short --e2e
```

Requires Docker. Spins up a WireMock container that serves stubs derived from
the committed OpenAPI spec at `tests/openapi/_openapi/fixtures/nextlabs-openapi.json`.
The full E2E suite runs in about 25 seconds on top of the ~18 second unit run.

### Troubleshooting

- **`docker: command not found` or Docker socket unavailable:** E2E tests are
  automatically skipped when Docker is not reachable. Inside the dev container
  make sure the Docker-in-Docker feature is enabled (see *Docker from inside
  the dev container* above).
- **Tests hang at WireMock startup / connection refused:** when running from
  inside a container the host-mapped port is not routable. The fixtures
  resolve the WireMock container's internal IP via `docker inspect` and talk
  to it on port 8080 directly — verify Docker network reachability with
  `docker network ls` and `docker inspect <container>`.
- **Corporate proxy breaks requests to WireMock:** the conftest clears
  `HTTP(S)_PROXY` before each test because httpx's `NO_PROXY` does not
  understand CIDR ranges. If you see unexpected proxy traffic, confirm the
  clearing logic in `tests/e2e/conftest.py` still fires.
- **`nextlabs: command not found` in CLI tests:** the subprocess fixtures
  inherit the full `os.environ` so the installed entry point is found via
  user site-packages. If you override `PATH`/`HOME` in a custom fixture you
  must keep them pointed at the same Python environment.

### Regenerating the OpenAPI fixture

The vendor spec is committed so the test suite stays hermetic. To refresh:

```bash
python tools/fetch_openapi_spec.py
```

This writes the latest spec to
`tests/openapi/_openapi/fixtures/nextlabs-openapi.json`. Review the diff, run the test
suite (including `--e2e`), fix any new round-trip or model-registry failures,
then commit. The helper refuses to run in CI.

## Policy search expressions

The `nextlabs policies search` front-ends (`--where`, `--field`,
`--criteria-file`) are thin CLI wrappers over pure, side-effect-free
transforms in `_cloudaz/_search/`. All three compile to one
`SearchField` list that the backend combines with **AND**. The CLI-facing
walkthrough lives in the [README](../README.md#searching-policies); the
design rationale is [ADR 0004](adr/0004-policy-search-expression-grammar.md).

The parser entry points are part of the supported public surface and are
reusable by programmatic SDK callers — import them from
`nextlabs_sdk.cloudaz`, never from the internal `_cloudaz` modules:

| Entry point | Input → output |
| --- | --- |
| `transpile_where` | A SCIM `--where` string → `list[SearchField]`. |
| `parse_field_expr` | One `NAME[:TYPE]=VALUE` `--field` token → `SearchField`. |
| `date_value` / `epoch_millis` | A DATE keyword or `from..to` ISO range → date payload. |

```python
from nextlabs_sdk.cloudaz import parse_field_expr, transpile_where

fields = transpile_where('name sw "billing" and status eq "APPROVED"')
fields.append(parse_field_expr("tags.team=finance"))
```

### SCIM operator → match-type mapping

`--where` maps SCIM operators onto the eight backend `SearchFieldType`
values:

| SCIM input | Match type |
| --- | --- |
| `field sw "v"` (prefix) | `SINGLE` |
| `field eq "v"` / `field co "v"` (scalar) | `SINGLE_EXACT_MATCH` |
| `field co "a" or field co "b"` (same field) | `MULTI` |
| `field eq "a" or field eq "b"` (same field) | `MULTI_EXACT_MATCH` |
| `field ge/gt/le/lt "<iso-date>"` | `DATE` (`fromDate`/`toDate`) |
| `attr[sub op "v"]` (nested) | `NESTED` |
| `attr[sub op "a" or sub op "b"]` (same sub) | `NESTED_MULTI` |
| `text co "v"` (reserved attribute) | `TEXT` (subfields `name`, `description`) |

`--field` uses the same `SearchFieldType` tokens explicitly
(case-insensitive after `:`) and otherwise infers: a dotted `NAME` →
`NESTED`/`NESTED_MULTI`, a comma in `VALUE` → `MULTI`, else
`SINGLE_EXACT_MATCH`.

All parsers raise `SearchExpressionError` (a `NextLabsError` subclass) on
malformed input, an unsupported operator, a cross-field `OR`/`NOT`, or a
`--criteria-file` combined with an expression flag — never a raw parser,
`ValueError`, or `httpx` exception.
