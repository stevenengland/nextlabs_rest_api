# ADR 0001: Public API surface via sub-package facades

## Status

Accepted

## Context

`nextlabs-sdk` wraps two distinct NextLabs services — the CloudAz Console API
and the PDP REST API. Each service has its own client, models, enums, and
service helpers. Consumers need a stable, documented import path for every
public symbol, but all implementation currently lives under underscore-prefixed
internal packages (`_cloudaz`, `_pdp`). Repos that enforce import-hygiene
rules (e.g. `check-no-private-import` linters) cannot use the SDK at all
without suppressions.

We need to decide where the canonical public symbols are exported from.

## Decision Drivers

* Two independent service domains with non-overlapping models.
* Avoid name collisions as each domain grows (e.g. both could define `Client`).
* Minimise cognitive load for consumers — imports should make the service
  domain obvious at the call-site.
* Follow precedent set by multi-service SDKs (AWS SDK, Azure SDK, Google Cloud
  client libraries) that scope public surfaces by service.

## Considered Options

### Option 1 — Top-level flat namespace

Export every public symbol from `nextlabs_sdk.__init__`:

```python
from nextlabs_sdk import CloudAzClient, Policy, PdpClient, EvalRequest
```

**Pros:** single import target.
**Cons:** high collision risk as domains grow; no visual cue which service a
symbol belongs to; `__init__` becomes a maintenance bottleneck.

### Option 2 — Sub-package facades scoped by service domain

Create `nextlabs_sdk.cloudaz` and `nextlabs_sdk.pdp` as thin facade packages
that re-export curated symbols from the internal implementation:

```python
from nextlabs_sdk.cloudaz import CloudAzClient, Policy
from nextlabs_sdk.pdp import PdpClient, EvalRequest
```

**Pros:** natural namespace boundary per service; collision-proof; mirrors
multi-service SDK conventions; each facade is independently testable.
**Cons:** two import targets instead of one.

### Option 3 — Both (flat + sub-package)

Re-export everything at both levels.

**Pros:** maximum convenience.
**Cons:** duplicated export lists to keep in sync; unclear which path is
canonical; IDE auto-import picks inconsistent paths.

## Decision

**Option 2 — Sub-package facades scoped by service domain.**

Each facade package (`nextlabs_sdk.cloudaz`, `nextlabs_sdk.pdp`) owns an
`__init__.py` that:

1. Declares `__all__` with alphabetical ordering within logical groups
   (Clients, Models, Services, Enums/Types).
2. Uses group comments (e.g. `# Clients`, `# Models`) for readability.
3. Re-exports symbols via explicit `X as X` imports from the corresponding
   internal package namespace (`_cloudaz`, `_pdp`), whose own `__all__` serves
   as the canonical export registry. Facade imports are decoupled from internal
   submodule structure — they reference only the internal package, not its
   individual modules.

The top-level `nextlabs_sdk.__init__` remains intentionally thin — it exports
cross-cutting symbols (auth strategies, exceptions, HTTP configuration) and
convenience re-exports of the main service clients (`CloudAzClient`,
`PdpClient`, and their async variants).

## Consequences

* **Positive:** import paths encode the service domain, reducing ambiguity.
  Adding symbols to one facade cannot break the other.
* **Positive:** each facade gets its own export-verification test
  (`test_cloudaz_exports.py`, `test_pdp_exports.py`, `test_top_level_exports.py`),
  catching accidental regressions independently.
* **Negative:** consumers must know which sub-package to import from. This is
  mitigated by documentation and by the package names matching the service
  names.
* **Neutral:** internal underscore packages (`_cloudaz`, `_pdp`) remain the
  implementation home; facades are a re-export layer only.
