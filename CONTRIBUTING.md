# Contributing

Thanks for your interest in `nextlabs-sdk`! Contributions are welcome via
issues and pull requests.

## Development setup

The full development guide lives in [`docs/development.md`](docs/development.md).
A `.devcontainer` is provided that pre-installs every tool referenced below.

Quick reference:

```bash
python ./tools/checks.py              # Black + Flake8 + MyPy + Pyright
python ./tools/tests.py --short       # unit tests
python ./tools/tests.py --short --all # unit + E2E tests (requires Docker)
```

Pre-commit hooks (`black`, `flake8`, `mypy`, `pyright`) run automatically
on `git commit`. Allow at least 120 seconds for the first commit on a
fresh clone — Pyright is the slowest hook.

## Pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/) for
  commit messages and PR titles. The changelog is generated from them.
- Keep public-API changes (`nextlabs_sdk`, `nextlabs_sdk.cloudaz`,
  `nextlabs_sdk.pdp`, `nextlabs_sdk.exceptions`) in sync between the
  sync and async clients.
- Every behavior change needs a test. The project uses
  [`mockito`](https://pypi.org/project/mockito/) for unit tests and
  [`testcontainers`](https://testcontainers.com/) for E2E.

## Reporting issues

- **Bugs and feature requests:** open a GitHub issue.
- **Security vulnerabilities:** please report privately, see
  [`SECURITY.md`](SECURITY.md).
