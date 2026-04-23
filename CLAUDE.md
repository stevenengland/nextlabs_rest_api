# nextlabs-sdk

Typed Python SDK wrapping NextLabs CloudAz Console API + PDP REST API.
Python 3.11+. Dev guide: @docs/development.md. Module map:
@docs/architecture.md.

## Environment

Devcontainer. Deps preinstalled in system Python. Use `pip`. No
`venv`/`pipx`/`uv`/`poetry` inside container.

## Commands

```bash
gh                                       # GitHub CLI
python ./tools/checks.py --short         # Black+Flake8+MyPy+Pyright (terse)
python ./tools/checks.py                 # Same, verbose
python ./tools/tests.py --short          # Unit (filtered)
python ./tools/tests.py --short --e2e    # E2E only (needs Docker)
python ./tools/tests.py --short --all    # Unit + E2E (needs Docker)
```

Pre-commit hooks (black, flake8, mypy, pyright) on `git commit`. Timeout
**120 s+** — pyright slow.

## Exploration scope

Keep searches tight. Saves tokens, avoids context poisoning.

- Code: `src/`, `tests/`. Scripts: `tools/`.
- Docs: on-demand only.
- Use `ripgrep` (`rg`) / `grep` tool — honors `.gitignore`.
- Shortened tool output: `head`, `tail`, `git log --oneline -20`,
  `git diff -- <path>`, `pytest --short`. Full dumps on failure only.
- Never view `tests/_openapi/fixtures/nextlabs-openapi.json` (~640 KB,
  ~150K tokens). Grep or line-range read only.
- Skip: caches (gitignored), `tmp/`, `plans/`, `htmlcov/`, `coverage.xml`.

## Architecture rules

- Public surface: `nextlabs_sdk`, `.cloudaz`, `.pdp`, `.exceptions`.
  Underscore modules internal — no imports from tests, examples, docs.
- Sync/async parity: `CloudAzClient`↔`AsyncCloudAzClient`,
  `PdpClient`↔`AsyncPdpClient`. Update both on behavior change.
- Stack: `httpx`, Pydantic v2, Typer + Rich (CLI).
- Errors: raise within `NextLabsError` hierarchy only. Never leak
  `httpx` or generic exceptions from public APIs.

## Code standards

- `setup.cfg`: NEVER modify without consulting user.
- No `noqa`, `type: ignore`, `--no-verify` suppressions.
- One class / main component per file.
- Google-style docstrings.
- TDD: tests before or alongside implementation.
- Bug fixes: diagnose why existing tests missed it; improve them.
- No comments unless WHY non-obvious.
- Conventional commit messages, human-written style.
- Skills when relevant: **tdd** (features + fixes), **clean-code**
  (production code).
- Never touch `changelog.md` — auto-generated.

## Testing

Mocking: **mockito** (not `unittest.mock`). E2E: **testcontainers** via
`--e2e`/`--all`. Key fixtures: `when`, `unstub` in `tests/conftest.py`.

## References

- CloudAz Console API: https://developer.nextlabs.com/#/product/cc/api
- PDP REST API: https://developer.nextlabs.com/#/product/cc/pdpapi
- OpenAPI spec: https://developer.nextlabs.com/assets/external/cloudaz/api-docs.json
