## Project Intention

**nextlabs-sdk** — A typed Python SDK wrapping the NextLabs CloudAz Console API and PDP REST API

- **Audience:** Python developers integrating with the NextLabs CloudAz platform
- **Scope boundary:** <TODO: what this tool does NOT do>


## Commands

```bash
gh                                    # GitHub CLI
python ./tools/checks.py              # Black + Flake8 + MyPy + Pyright
python ./tools/tests.py --short       # unit tests
python ./tools/tests.py --short --e2e # + E2E (requires Docker)
```

- **Pre-commit hooks** (black, flake8, mypy, pyright) run on `git commit`.
  Use a timeout of at least **120 seconds** when committing via tooling,
  as pyright in particular can be slow.

## Code Standards

- **setup.cfg**: NEVER modify without consulting the user
- No `noqa` or `type: ignore` suppressions
- Single class or main component per file
- Google style docstrings
- TDD: write tests before or alongside implementation
- Fixing issues: also diagnose why existing tests missed it; improve them
- When applicable, use available skills to improve output quality:
  - **tdd** skill — use for all new features and bug fixes
  - **clean-code** skill — use when writing or refactoring production code
- If you commit, write commit messages as a human developer would.
- Default to NO comments - only add comments when the WHY is not obvious.


## Testing

- Mocking: **mockito** (not unittest.mock)
- E2E: **testcontainers**; requires Docker + `--e2e` flag
- Key fixtures: `when`, `unstub` (in `tests/conftest.py`)

## External APIs

- https://developer.nextlabs.com/#/product/cc/api
- https://developer.nextlabs.com/#/product/cc/pdpapi
- https://developer.nextlabs.com/assets/external/cloudaz/api-docs.json
