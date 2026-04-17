# nextlabs-sdk

Typed Python SDK wrapping the NextLabs CloudAz Console API and PDP REST API.
Python 3.11+. See @docs/development.md for the full development guide.

## Commands

```bash
gh                                    # GitHub CLI
python ./tools/checks.py              # Black + Flake8 + MyPy + Pyright
python ./tools/tests.py --short       # unit tests
python ./tools/tests.py --short --e2e # E2E tests only (requires Docker)
python ./tools/tests.py --short --all # unit + E2E tests (requires Docker)
```

- **Pre-commit hooks** (black, flake8, mypy, pyright) run on `git commit`.
  Use a timeout of at least **120 seconds** when committing via tooling,
  as pyright in particular can be slow.

## Architecture rules

- **Public surface** is only `nextlabs_sdk`, `nextlabs_sdk.cloudaz`,
  `nextlabs_sdk.pdp`, and `nextlabs_sdk.exceptions`. Modules with a
  leading underscore (`_auth/`, `_cloudaz/`, `_pdp/`, `_cli/`,
  `_config.py`, `_http_transport.py`, `_pagination.py`) are internal and
  may change without notice — do not import them from tests, examples,
  or docs.
- **Sync/async parity:** every client and feature ships in both sync and
  async flavors (`CloudAzClient` / `AsyncCloudAzClient`, `PdpClient` /
  `AsyncPdpClient`). When adding or changing behavior, update both.
- **Stack:** `httpx` for transport, Pydantic v2 for request/response
  models, Typer + Rich for the optional CLI.
- **Errors:** raise within the `NextLabsError` hierarchy (see
  `exceptions.py`); do not leak `httpx` or generic exceptions from
  public APIs.

## Code standards

- **setup.cfg**: NEVER modify without consulting the user.
- No `noqa`, `type: ignore`, or `--no-verify` suppressions.
- Single class or main component per file.
- Google-style docstrings.
- TDD: write tests before or alongside implementation.
- Fixing issues: also diagnose why existing tests missed it; improve them.
- Default to NO comments — only add comments when the WHY is not obvious.
- If you commit, ALWAYS use conventional commit messages and write them
  like a human developer would.
- When applicable, use available skills to improve output quality:
  - **tdd** skill — use for all new features and bug fixes.
  - **clean-code** skill — use when writing or refactoring production code.

## Testing

- Mocking: **mockito** (not `unittest.mock`).
- E2E: **testcontainers**; requires Docker + `--e2e` (e2e only) or
  `--all` (unit + e2e) flag.
- Key fixtures: `when`, `unstub` (in `tests/conftest.py`).

## References

When designing the wrapper, refer to the official NextLabs documentation:

- CloudAz Console API: https://developer.nextlabs.com/#/product/cc/api
- PDP REST API: https://developer.nextlabs.com/#/product/cc/pdpapi
- OpenAPI spec: https://developer.nextlabs.com/assets/external/cloudaz/api-docs.json
