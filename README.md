# nextlabs-sdk

[![PyPI version](https://img.shields.io/pypi/v/nextlabs-sdk.svg)](https://pypi.org/project/nextlabs-sdk/)
[![Python versions](https://img.shields.io/pypi/pyversions/nextlabs-sdk.svg)](https://pypi.org/project/nextlabs-sdk/)
[![CI](https://github.com/stevenengland/nextlabs_rest_api/actions/workflows/code_testing.yml/badge.svg)](https://github.com/stevenengland/nextlabs_rest_api/actions/workflows/code_testing.yml)
[![License: MIT](https://img.shields.io/github/license/stevenengland/nextlabs_rest_api.svg)](LICENSE)

> *Typed Python SDK and CLI for the NextLabs CloudAz Console & PDP REST APIs.*

> [!WARNING]
> **Alpha** — the public surface may still change. Unofficial project, not
> affiliated with NextLabs.

![CLI demo: auth login → policies search → pdp eval](docs/cast/demo.gif)

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Using the SDK](#using-the-sdk)
- [Using the CLI](#using-the-cli)
- [Configuration & authentication](#configuration--authentication)
- [Project layout](#project-layout)
- [Development](#development)
- [License](#license)

## Features

- **Two API clients** — `CloudAzClient` for Console management and
  `PdpClient` for XACML-style authorization decisions.
- **Sync and async parity** — every client ships in a sync
  (`CloudAzClient`, `PdpClient`) and an async (`AsyncCloudAzClient`,
  `AsyncPdpClient`) flavor, built on `httpx`.
- **Fully typed** (PEP 561, `py.typed`) with Pydantic v2 request/response
  models — strong autocompletion under mypy and Pyright.
- **CloudAz coverage** — tags, components, component types, policies
  (incl. `retrieveAllPolicies` export and named/scoped search), operators,
  entity audit logs, reporter audit logs (Policy Activity Reports,
  Monitors, Alerts), policy activity reports, activity logs, dashboard,
  and system config.
- **PDP coverage** — `evaluate` (single decision) and `permissions`
  (multi-action discovery), with **JSON or XML** payloads.
- **Resilient transport** — OIDC token acquisition + refresh,
  configurable timeout, SSL verification, and retries with exponential
  backoff (clamped `Retry-After` honoured on 429/503).
- **Typed error hierarchy** — HTTP status codes map to
  `AuthenticationError`, `AuthorizationError`, `NotFoundError`,
  `ValidationError`, `ConflictError`, `RateLimitError`, `ServerError`,
  `RequestTimeoutError`, `TransportError`, and `ApiError` — all
  subclasses of `NextLabsError`.
- **Pagination helpers** — `SyncPaginator` / `AsyncPaginator` iterate
  listed endpoints page-by-page or item-by-item.
- **Optional CLI** — a `nextlabs` command (Typer + Rich) for scripting,
  admin tasks, and quick exploration. Persistent OIDC token cache, four
  output formats (`table` / `wide` / `detail` / `json`), per-call
  verbosity for HTTP tracing.

## Installation

```bash
pip install nextlabs-sdk            # library only
pip install "nextlabs-sdk[cli]"     # + nextlabs CLI (Typer, Rich)
```

If you install the library without the `[cli]` extra, the `nextlabs`
command is still registered but will print a friendly error pointing at
`pip install 'nextlabs-sdk[cli]'` and exit with status `1`.

Requires Python **3.11+**.

---

## Using the SDK

### Quick start — CloudAz (sync)

```python
from nextlabs_sdk import CloudAzClient
from nextlabs_sdk.cloudaz import TagType

with CloudAzClient(
    base_url="https://cloudaz.example.com",
    username="admin",
    password="secret",
) as client:
    for tag in client.tags.list(TagType.COMPONENT):
        print(tag.id, tag.label)

    tag_id = client.tags.create(TagType.COMPONENT, key="env", label="Env")
    tag = client.tags.get(tag_id)
    client.tags.delete(tag.id)
```

### Quick start — CloudAz (async)

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

### Quick start — PDP

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
            resource=Resource(
                id="doc-42",
                type="document",
                attributes={"classification": "internal"},
            ),
            action=Action(id="read"),
            application=Application(id="wiki"),
            return_policy_ids=True,
        )
    )
    result = decision.first_result
    print(result.decision, [p.id for p in result.policy_refs])
```

Use `content_type=ContentType.XML` to exchange XACML XML payloads
instead of JSON. `pdp.permissions(...)` returns the set of actions a
subject may perform on a resource.

### Pagination

`SyncPaginator` / `AsyncPaginator` are returned by every list method.
Iterate page-by-page (`.pages()`) or item-by-item (default `__iter__`):

```python
for tag in client.tags.list(TagType.COMPONENT):       # one item at a time
    ...

for page in client.tags.list(TagType.COMPONENT).pages():
    print(page.total, len(page.items))                # PageResult metadata
```

### Error handling

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

### Public API surface

All imports come from four public entry points:

- `nextlabs_sdk` — clients (`CloudAzClient`, `AsyncCloudAzClient`,
  `PdpClient`, `AsyncPdpClient`), transport (`HttpConfig`,
  `RetryConfig`, `create_http_client`, `create_async_http_client`),
  pagination (`SyncPaginator`, `AsyncPaginator`, `PageResult`), auth
  (`CloudAzAuth`, `PdpAuth`, `StaticTokenAuth`), token cache
  (`TokenCache`, `CachedToken`, `FileTokenCache`, `NullTokenCache`),
  and `__version__`.
- `nextlabs_sdk.cloudaz` — CloudAz domain models and enums (`Tag`,
  `TagType`, `Operator`, audit-log / report / dashboard /
  system-config / activity-log models).
- `nextlabs_sdk.pdp` — PDP request/response models and enums
  (`Subject`, `Resource`, `Action`, `Application`, `Environment`,
  `EvalRequest`, `EvalResponse`, `PermissionsRequest`,
  `PermissionsResponse`, `ContentType`, `Decision`,
  `ResourceDimension`, …).
- `nextlabs_sdk.exceptions` — the `NextLabsError` hierarchy.

Anything with a leading underscore (`nextlabs_sdk._cloudaz`,
`nextlabs_sdk._pdp`, `nextlabs_sdk._cli`, `nextlabs_sdk._auth`, …)
is an internal implementation detail and may change without notice.

---

## Using the CLI

The optional CLI exposes most CloudAz operations plus PDP evaluation.

### Quick start

```bash
pip install "nextlabs-sdk[cli]"

export NEXTLABS_BASE_URL="https://cloudaz.example.com"
export NEXTLABS_USERNAME="admin"

nextlabs auth login                # acquire & cache a token
nextlabs auth status               # is the cached token still valid?
nextlabs policies search --status APPROVED
nextlabs pdp eval --subject alice --resource doc-42 \
                  --resource-type document --action read --application wiki
```

### Command groups

```text
auth             login | logout | status | test | accounts | use
tags             list (positional <tag_type>) | get | create | delete
components       search | get | create | update | delete
component-types  list | get | create | update | delete
policies         search | get | export-all | tags
audit-logs       search (--start-date / --end-date in epoch-ms)
reports          ...
dashboard        ...
pdp              eval | permissions
```

Use `nextlabs <group> --help` for the exact flags of each subcommand.

### Output formats

Every list/get command accepts `-o` / `--output`. Values are
case-insensitive.

| Format   | When to use                                                   |
| -------- | ------------------------------------------------------------- |
| `table`  | Default. Compact columns; long values wrap (never truncated). |
| `wide`   | Table plus extra columns (owner, timestamps, version, …).     |
| `detail` | Sectioned per-item output, `kubectl describe` style.          |
| `json`   | Raw JSON dump of the response model(s). Machine-readable.     |

```bash
nextlabs -o wide policies search
nextlabs -o detail policies get 17
nextlabs --output json components search    # machine-readable
```

### Recipes

Real workflows assembled from the commands shipped today.

**1. Daily admin — find an approved policy and read it.**

```bash
nextlabs auth login
nextlabs policies search --status APPROVED --text "billing"
nextlabs policies get 17 -o detail
```

**2. CI authorization smoke test — fail the build if `alice` cannot read the wiki.**

```bash
nextlabs --token "$NEXTLABS_TOKEN" \
  pdp eval --subject alice --resource doc-42 --resource-type document \
           --action read --application wiki -o json \
  | jq -e '.eval_results[0].decision == "Permit"'
```

**3. Export the policy catalogue to version control.**

```bash
nextlabs -o json policies search --page-size 1000 > policies.json
git add policies.json && git commit -m "chore: snapshot policies"
```

**4. Audit recent activity (last hour).**

```bash
END=$(date +%s%3N)
START=$((END - 3600000))
nextlabs audit-logs search --start-date "$START" --end-date "$END"
```

**5. Run in CI without an interactive login.**

```bash
NEXTLABS_BASE_URL="https://cloudaz.example.com" \
NEXTLABS_TOKEN="$(vault kv get -field=token secret/nextlabs/ci)" \
  nextlabs policies search --page-size 50
```

`NEXTLABS_TOKEN` (or `--token`) bypasses the OIDC login flow **and** the
token cache — nothing is read from or written to disk.

**6. Templated extraction with `jq`.**

```bash
nextlabs -o json components search | jq '.[].id'
```

For more day-to-day fixes (auth cache, SSL trust, missing PDP attributes,
…) see [`docs/troubleshooting.md`](docs/troubleshooting.md).

---

## Configuration & authentication

Both the SDK and the CLI share the same transport, retry, and OIDC
machinery.

### `HttpConfig` and `RetryConfig`

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

Retries use exponential backoff with jitter and apply to transient
transport failures and 5xx / 429 responses. `Retry-After` is honoured
and clamped to `max_delay`.

### OIDC tokens, caching, and environment variables

The CLI persists OIDC tokens between invocations so users do not
re-authenticate on every command. The SDK defaults to `NullTokenCache`
(no silent filesystem writes); library consumers opt in explicitly:

```python
from nextlabs_sdk import CloudAzClient, FileTokenCache

client = CloudAzClient(
    base_url="https://cloudaz.example.com",
    username="admin",
    password="secret",
    token_cache=FileTokenCache(),  # or any custom TokenCache
)
```

**Token cache lookup precedence** (CLI):

1. `--cache-dir <path>` or `NEXTLABS_CACHE_DIR` → `<path>/tokens.json`
2. `$XDG_CACHE_HOME/nextlabs-sdk/tokens.json`
3. `~/.cache/nextlabs-sdk/tokens.json`

The file is written `0600` inside a `0700` directory; writes are atomic
(temp file + `os.replace`). The cache key is
`"{token_url}|{username}|{client_id}"` so multiple profiles coexist.

Refresh tokens are used transparently when available; on refresh failure
the CLI falls back to the password grant (if `--password` /
`NEXTLABS_PASSWORD` is set) and otherwise raises `AuthenticationError`
with a "Run `nextlabs auth login`" hint.

### PDP authentication — CloudAz vs PDP token endpoint

The NextLabs docs describe two legitimate OAuth token endpoints for PDP
calls:

- **CloudAz endpoint** — `/cas/token` on the CloudAz host.
- **PDP endpoint** — `/dpc/oauth` on the PDP host.

The CLI exposes both via `--pdp-auth {cloudaz,pdp}` (env
`NEXTLABS_PDP_AUTH`). The default depends on which hosts you pass:

| Flags set                          | Default flavor | Token URL hit                 |
| ---------------------------------- | -------------- | ----------------------------- |
| `--base-url` + `--pdp-url`         | `cloudaz`      | `<base-url>/cas/token`        |
| `--pdp-url` only                   | `pdp`          | `<pdp-url>/dpc/oauth`         |

Explicit `--pdp-auth` always wins over the derivation. `--pdp-url` is
required for every PDP command; `--base-url` is required only for the
`cloudaz` flavor. When `--pdp-auth=pdp`, the token POST needs a
PDP-specific client ID — pass `--pdp-client-id` (or set
`NEXTLABS_PDP_CLIENT_ID`); the CloudAz default `--client-id` is not
reused.

```bash
# CloudAz-hosted auth (default when --base-url is set)
nextlabs --base-url https://cloudaz.example --pdp-url https://pdp.example \
  --client-secret "$SECRET" \
  pdp eval --subject alice --resource doc-42 --resource-type document \
           --action read

# PDP-hosted auth (requires an explicit PDP client ID)
nextlabs --pdp-url https://pdp.example --pdp-client-id my-pdp-client \
  --client-secret "$SECRET" \
  pdp eval --subject alice --resource doc-42 --resource-type document \
           --action read

# Force PDP-hosted auth even when a CloudAz host is configured
nextlabs --base-url https://cloudaz.example --pdp-url https://pdp.example \
  --pdp-auth pdp --pdp-client-id my-pdp-client --client-secret "$SECRET" \
  pdp eval ...
```

#### Register a PDP account once with `auth login --type pdp`

You can also persist the PDP client credentials in the token cache so
subsequent `nextlabs pdp …` calls do not need `--client-secret`,
`--pdp-url`, `--pdp-client-id`, or `--pdp-auth` on every invocation:

```bash
# One-time login — mints a token, caches it alongside the client_secret,
# and stores pdp_url / pdp_auth as preferences for this account.
nextlabs auth login --type pdp \
  --pdp-url https://pdp.example --pdp-client-id my-pdp-client \
  --client-secret "$SECRET" --pdp-auth pdp

# Later commands reuse the cached credentials automatically.
nextlabs pdp eval --subject alice --resource doc-42 \
  --resource-type document --action read
```

PDP entries appear in `nextlabs auth accounts` with kind `pdp` and an
empty username; target them explicitly with
`nextlabs auth use "[pdp]@https://pdp.example"`. Running
`nextlabs auth logout` clears the cached token, preferences, and active
pointer for the selected account.

**Environment variables**

| Variable                   | Purpose                                                       |
| -------------------------- | ------------------------------------------------------------- |
| `NEXTLABS_BASE_URL`        | CloudAz base URL                                              |
| `NEXTLABS_USERNAME`        | CloudAz username                                              |
| `NEXTLABS_PASSWORD`        | CloudAz password                                              |
| `NEXTLABS_CLIENT_ID`       | CloudAz OIDC client ID (default: `ControlCenterOIDCClient`)   |
| `NEXTLABS_CLIENT_SECRET`   | PDP client secret                                             |
| `NEXTLABS_PDP_URL`         | PDP base URL (host serving `/dpc/authorization/*`)            |
| `NEXTLABS_PDP_AUTH`        | PDP token endpoint flavor: `cloudaz` or `pdp` (see above)     |
| `NEXTLABS_PDP_CLIENT_ID`   | PDP-specific client ID (required when `--pdp-auth=pdp`)       |
| `NEXTLABS_TOKEN`           | Pre-issued bearer token; bypasses the login flow and cache    |
| `NEXTLABS_CACHE_DIR`       | Directory holding `tokens.json` (overrides XDG default)       |

Top-level CLI flags worth knowing: `--no-verify` (skip TLS verification —
dev only), `-v` / `-vv` (verbose; `-vv` logs every HTTP request and
response body), `--token` (one-shot bearer override).

---

## Project layout

```
src/nextlabs_sdk/
├── cloudaz/        # Public: CloudAz models & enums (re-exports)
├── pdp/            # Public: PDP models & enums (re-exports)
├── exceptions.py   # Public: NextLabsError hierarchy
├── _auth/          # Internal: OIDC auth flows + token cache
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
python ./tools/tests.py --short --e2e # E2E tests only (requires Docker)
python ./tools/tests.py --short --all # unit + E2E tests (requires Docker)
```

A `.devcontainer` is provided; pre-commit hooks (`black`, `flake8`,
`mypy`, `pyright`) are preconfigured. The CLI demo above is regenerated
with `vhs docs/cast/demo.tape` — see
[`docs/cast/README.md`](docs/cast/README.md).

## License

MIT — see [LICENSE](LICENSE).

---

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) ·
[Changelog](CHANGELOG.md) · [Troubleshooting](docs/troubleshooting.md)
