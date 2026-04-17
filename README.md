# nextlabs-sdk

A typed, async-ready Python SDK (and optional CLI) for the
[NextLabs CloudAz Console API](https://developer.nextlabs.com/#/product/cc/api)
and the [NextLabs PDP REST API](https://developer.nextlabs.com/#/product/cc/pdpapi).

> **Status:** Alpha — the public surface may still change. Unofficial project,
> not affiliated with NextLabs.

## Features

- **Two API clients:** `CloudAzClient` for Console management operations and
  `PdpClient` for XACML-style authorization decisions.
- **Sync and async:** every client ships in a sync (`CloudAzClient`,
  `PdpClient`) and an async (`AsyncCloudAzClient`, `AsyncPdpClient`) flavor,
  built on `httpx`.
- **Fully typed** (PEP 561, `py.typed`) with Pydantic v2 request/response
  models — good autocompletion and static checking with mypy/Pyright.
- **CloudAz coverage:** tags, components, component types, policies
  (incl. `retrieveAllPolicies` export and named/scoped search), operators,
  entity audit logs, reporter audit logs (Policy Activity Reports, Monitors,
  Alerts), policy activity reports, activity logs, dashboard, and system
  config.
- **PDP coverage:** `evaluate` (single-action decision) and `permissions`
  (multi-action discovery), with **JSON or XML** payloads.
- **Resilient transport:** OIDC token acquisition + refresh, configurable
  timeout, SSL verification, and retries with exponential backoff.
- **Typed error hierarchy:** HTTP status codes are mapped to
  `AuthenticationError`, `AuthorizationError`, `NotFoundError`,
  `ValidationError`, `ConflictError`, `RateLimitError`, `ServerError`,
  `RequestTimeoutError`, `TransportError`, and `ApiError` — all subclasses
  of `NextLabsError`.
- **Pagination helpers:** `SyncPaginator` / `AsyncPaginator` iterate listed
  endpoints page-by-page or item-by-item.
- **Optional CLI:** a `nextlabs` command-line tool (Typer + Rich) for
  scripting, admin tasks, and quick exploration.

## Installation

```bash
pip install nextlabs-sdk            # library only
pip install "nextlabs-sdk[cli]"     # + nextlabs CLI (Typer, Rich)
```

Requires Python **3.11+**.

## Quick Start — CloudAz (Console API)

```python
from nextlabs_sdk import CloudAzClient
from nextlabs_sdk.cloudaz import TagType

with CloudAzClient(
    base_url="https://cloudaz.example.com",
    username="admin",
    password="secret",
) as client:
    # Paginated list of component tags
    for tag in client.tags.list(TagType.COMPONENT):
        print(tag.id, tag.label)

    # Create a tag, fetch it, then delete it
    tag_id = client.tags.create(TagType.COMPONENT, key="env", label="Env")
    tag = client.tags.get(tag_id)
    client.tags.delete(tag.id)
```

Async equivalent:

```python
import asyncio
from nextlabs_sdk import AsyncCloudAzClient
from nextlabs_sdk.cloudaz import TagType

async def main() -> None:
    async with AsyncCloudAzClient(
        base_url="https://cloudaz.example.com",
        username="admin",
        password="secret",
    ) as client:
        async for tag in client.tags.list(TagType.COMPONENT):
            print(tag.id, tag.label)

asyncio.run(main())
```

## Quick Start — PDP (authorization decisions)

```python
from nextlabs_sdk import PdpClient
from nextlabs_sdk.pdp import (
    Action, Application, EvalRequest, Resource, Subject,
)

with PdpClient(
    base_url="https://pdp.example.com",
    client_id="my-client",
    client_secret="s3cret",
) as pdp:
    decision = pdp.evaluate(
        EvalRequest(
            subject=Subject(id="alice", attributes={"role": "engineer"}),
            resource=Resource(id="doc-42", type="document",
                              attributes={"classification": "internal"}),
            action=Action(id="read"),
            application=Application(id="wiki"),
            return_policy_ids=True,
        )
    )
    result = decision.first_result
    print(result.decision, [p.id for p in result.policy_refs])
```

Use `content_type=ContentType.XML` to exchange XACML XML payloads instead of
JSON. `pdp.permissions(...)` returns the set of actions a subject may perform
on a resource.

## Configuration

```python
from nextlabs_sdk import CloudAzClient, HttpConfig, RetryConfig

client = CloudAzClient(
    base_url="https://cloudaz.example.com",
    username="admin",
    password="secret",
    http_config=HttpConfig(
        timeout=15.0,
        verify_ssl=True,
        retry=RetryConfig(max_retries=5, base_delay=0.5, max_delay=10.0),
    ),
)
```

Retries use exponential backoff with jitter and apply to transient transport
failures and 5xx/429 responses.

## Error handling

```python
from nextlabs_sdk import CloudAzClient
from nextlabs_sdk.exceptions import (
    AuthenticationError, NotFoundError, NextLabsError,
)

try:
    client.tags.get(123)
except AuthenticationError:
    ...  # re-login / rotate credentials
except NotFoundError:
    ...
except NextLabsError as exc:
    print(exc.status_code, exc.request_method, exc.request_url, exc.response_body)
```

## CLI

The optional CLI exposes most CloudAz operations plus PDP evaluation. All
connection options can be supplied via flags or environment variables:

| Variable                    | Purpose                               |
| --------------------------- | ------------------------------------- |
| `NEXTLABS_BASE_URL`         | CloudAz base URL                      |
| `NEXTLABS_USERNAME`         | CloudAz username                      |
| `NEXTLABS_PASSWORD`         | CloudAz password                      |
| `NEXTLABS_CLIENT_ID`        | OIDC client ID (default: `ControlCenterOIDCClient`) |
| `NEXTLABS_CLIENT_SECRET`    | PDP client secret                     |
| `NEXTLABS_PDP_URL`          | PDP base URL (defaults to `--base-url`) |
| `NEXTLABS_TOKEN`            | Pre-issued bearer token; bypasses login/cache |
| `NEXTLABS_CACHE_DIR`        | Override the token cache directory    |

```bash
nextlabs --help
nextlabs tags list --type COMPONENT_TAG
nextlabs policies list
nextlabs pdp eval --subject alice --resource doc-42 --action read \
                  --resource-type document --application wiki
nextlabs --json components list          # machine-readable output
```

Command groups: `auth`, `tags`, `components`, `component-types`, `policies`,
`audit-logs`, `reports`, `dashboard`, `pdp`.

## Authentication & token caching

The CLI persists OIDC tokens between invocations so users do not re-authenticate
on every command.

- **Default cache location** (precedence):
  1. `--cache-dir` / `NEXTLABS_CACHE_DIR`
  2. `$XDG_CACHE_HOME/nextlabs-sdk/tokens.json`
  3. `~/.cache/nextlabs-sdk/tokens.json`

  The file is written with `0600` permissions inside a `0700` directory, and
  all writes are atomic (temp file + `os.replace`). The key is
  `"{token_url}|{username}|{client_id}"` so multiple profiles coexist safely.

- **Login / logout / status**

  ```bash
  nextlabs auth login      # acquire & cache a token
  nextlabs auth status     # show whether a valid cached token exists
  nextlabs auth logout     # remove the cached entry
  ```

- **Refresh tokens** are used transparently when available; on refresh failure
  the CLI falls back to the password grant (if `--password` / `NEXTLABS_PASSWORD`
  is set) and raises `AuthenticationError` with a "Run `nextlabs auth login`"
  hint otherwise.

- **CI bypass** — set `NEXTLABS_TOKEN` (or pass `--token`) to use a pre-issued
  bearer token. No login, no cache writes.

- **SDK default is `NullTokenCache`** (no silent filesystem writes). Library
  consumers can opt in explicitly:

  ```python
  from nextlabs_sdk import CloudAzClient, FileTokenCache

  client = CloudAzClient(
      base_url="https://cloudaz.example.com",
      username="admin",
      password="secret",
      token_cache=FileTokenCache(),  # or a custom TokenCache
  )
  ```

  The public cache API is `TokenCache`, `CachedToken`, `FileTokenCache`,
  `NullTokenCache`, and `StaticTokenAuth`.

## Public API surface

All imports come from three public entry points:

- `nextlabs_sdk` — clients (`CloudAzClient`, `AsyncCloudAzClient`,
  `PdpClient`, `AsyncPdpClient`), transport (`HttpConfig`, `RetryConfig`,
  `create_http_client`, `create_async_http_client`), pagination
  (`SyncPaginator`, `AsyncPaginator`, `PageResult`), auth
  (`CloudAzAuth`, `PdpAuth`, `StaticTokenAuth`), token cache
  (`TokenCache`, `CachedToken`, `FileTokenCache`, `NullTokenCache`),
  and `__version__`.
- `nextlabs_sdk.cloudaz` — CloudAz domain models and enums
  (`Tag`, `TagType`, `Operator`, audit-log / report / dashboard /
  system-config / activity-log models).
- `nextlabs_sdk.pdp` — PDP request/response models and enums
  (`Subject`, `Resource`, `Action`, `Application`, `Environment`,
  `EvalRequest`, `EvalResponse`, `PermissionsRequest`,
  `PermissionsResponse`, `ContentType`, `Decision`,
  `ResourceDimension`, …).
- `nextlabs_sdk.exceptions` — the `NextLabsError` hierarchy.

Anything with a leading underscore (`nextlabs_sdk._cloudaz`,
`nextlabs_sdk._pdp`, etc.) is an internal implementation detail and may
change without notice.

## Project layout

```
src/nextlabs_sdk/
├── cloudaz/        # Public: CloudAz models & enums (re-exports)
├── pdp/            # Public: PDP models & enums (re-exports)
├── exceptions.py   # Public: NextLabsError hierarchy
├── _auth/          # Internal: OIDC auth flows
├── _cloudaz/       # Internal: CloudAz service classes + models
├── _pdp/           # Internal: PDP client + JSON/XML serializers
├── _cli/           # Internal: Typer-based CLI (optional extra)
├── _config.py      # Internal (re-exported): HttpConfig, RetryConfig
├── _http_transport.py
└── _pagination.py  # Internal (re-exported): paginators
```

## Development

See [docs/development.md](docs/development.md) for the full development
guide. Quick reference:

```bash
python ./tools/checks.py              # Black + Flake8 + MyPy + Pyright
python ./tools/tests.py --short       # unit tests
python ./tools/tests.py --short --e2e # + E2E tests (requires Docker)
```

A `.devcontainer` is provided; pre-commit hooks are preconfigured.

## License

MIT — see [LICENSE](LICENSE) for details.
