# Architecture

> If this file diverges from `src/`, `src/` wins — update this file.

Compact module map for orientation. Deep details live in code and docstrings.

## Public surface

| Module | Responsibility | Key exports |
|---|---|---|
| `nextlabs_sdk` | Package root; re-exports public clients and errors | `CloudAzClient`, `AsyncCloudAzClient`, `PdpClient`, `AsyncPdpClient` |
| `nextlabs_sdk.cloudaz` | CloudAz Console API client (sync + async) | `CloudAzClient`, `AsyncCloudAzClient`, response/request models |
| `nextlabs_sdk.pdp` | PDP REST client (sync + async) | `PdpClient`, `AsyncPdpClient`, evaluation payload models |
| `nextlabs_sdk.exceptions` | Public error hierarchy | `NextLabsError` and subclasses |

Everything else (leading underscore) is **internal** and may change without
notice — do not import from tests outside their own module, examples, or docs.

## Internal layout (`src/nextlabs_sdk/`)

| Path | Role |
|---|---|
| `_auth/` | OIDC auth: token acquisition, refresh, bearer injection (`CloudAzAuth`). |
| `_auth/_active_account/` | Active-account selection and persistence. |
| `_auth/_token_cache/` | File-backed token store (`CachedToken`, `FileTokenCache`). |
| `_cloudaz/` | CloudAz client internals: request builders, pagination, response helpers. |
| `_pdp/` | PDP client internals: token-url resolution, evaluation request/response models. |
| `_pdp/_payload/` | PDP evaluation payload Pydantic models. |
| `_cli/` | Typer + Rich CLI: entrypoints, context resolvers, error handler, subcommands. |
| `_config.py` | Environment-driven config resolution. |
| `_http_transport.py` | Shared `httpx` transport factory (proxies, retries, TLS). |
| `_pagination.py` | Cursor / page helpers (`parse_paginated`, `build_page`, `PageResult`). |

## Key conventions

- **Sync/async parity:** every client and feature ships in both flavors
  (`CloudAzClient` ↔ `AsyncCloudAzClient`, `PdpClient` ↔ `AsyncPdpClient`).
  Changing one without the other is a regression.
- **Response models:** Pydantic v2, `ConfigDict(frozen=True)`.
- **Errors:** raise only within the `NextLabsError` hierarchy from public
  APIs; never leak `httpx.*` or stdlib exceptions.
- **Transport stack:** `httpx` (sync + async), Pydantic v2, Typer + Rich (CLI).
- **Mocking:** `mockito` for unit tests; `testcontainers` + WireMock for E2E.

## Tests layout (`tests/`)

- Unit tests live beside the modules they cover, in `tests/<area>/`.
- E2E tests under `tests/e2e/`; require Docker and the `--e2e`/`--all` flag of
  `tools/tests.py`.
- Shared fixtures in `tests/conftest.py` (`when`, `unstub`).
- Large vendor fixture: `tests/_openapi/fixtures/nextlabs-openapi.json`
  (~640 KB). **Grep it, don't view it.**

## Scripts (`tools/`)

| Script | Purpose |
|---|---|
| `checks.py` | Black + Flake8 + MyPy + Pyright. `--short` for terse output. Accepts a tool name (`black` / `flake8` / `mypy` / `pyright`) and/or file paths to narrow the run; narrowed `mypy` auto-adds `--follow-imports=silent`. |
| `tests.py` | Pytest wrapper. `--short` filters output; `--e2e` / `--all` pick markers. Accepts path/nodeid targets (e.g. `tests/foo.py::test_bar`); explicit targets drop the default `-m "not e2e"` marker and auto-disable coverage so single-file runs don't trip the 90% gate. |
| `fetch_openapi_spec.py` | Refresh committed OpenAPI fixture (local only). |
| `build.py` | Build tasks. |
| `init_project.sh` | Setup helper (template bootstrap). |
