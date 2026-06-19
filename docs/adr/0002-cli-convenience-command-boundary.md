# ADR 0002: CLI convenience-command boundary

## Status

Accepted

## Context

`nextlabs-sdk` ships in two installable shapes: the core SDK
(`pip install nextlabs-sdk`) and the CLI extra (`pip install
nextlabs-sdk[cli]`). The original mental model was strict: the SDK is a
faithful, opinion-free wrapper of the CloudAz Console API and the PDP REST
API, and the CLI is a thin shell that mirrors SDK calls one-to-one (get,
create, delete, etc.).

A new class of demand has emerged that does not fit that model cleanly:
**convenience features that compose existing SDK calls and present a
result**, without introducing new business logic or persistent state. The
first concrete example is a command that diffs the content of a policy in
its last deployed state against the deployed state before it — it fetches
two revisions the SDK already knows how to retrieve (`list_history`,
`get_revision`) and renders the delta.

These features are neither "pure API wrapper" (they compose and present)
nor "third-domain product logic" (they encode no platform rules). We need a
durable rule for where such features live, so each new convenience request
does not re-open the same placement debate.

## Decision Drivers

* Keep the SDK core opinion-free: no rendering, no terminal concerns, no
  composite "do three calls and format" helpers leaking into the public
  surface that application developers import.
* Give convenience/composition features an unambiguous home so they are not
  blocked or bikeshedded on every request.
* Avoid premature packaging overhead (a second distributable, its own
  release cadence, its own config/plugin model) before there is evidence it
  is needed.
* Preserve the existing public-surface discipline from ADR 0001 (underscore
  internals, curated facades).

## Considered Options

### Option 1 — Put convenience logic in the SDK core (public)

Add composite helpers (fetch-two-revisions-and-diff) to the public SDK so
both scripts and the CLI can call them.

**Pros:** reusable from application code.
**Cons:** the SDK stops being an opinion-free wrapper; presentation and
composition concerns bleed into the public surface; every convenience
request grows the public API and its compatibility burden. Diff/rendering
has no natural place in a transport-level client.

### Option 2 — Put convenience logic in the CLI layer (`[cli]`)

Keep composition and presentation entirely inside the CLI extra. The SDK
exposes only the primitive calls; the CLI fetches, composes, filters, and
renders.

**Pros:** SDK core stays pure; convenience features get a clear home; no new
packaging; the boundary is visible in the filesystem (CLI-internal
modules). Mirrors the tension analysis: composing and formatting are CLI
territory, not impurity.
**Cons:** the composite logic is not importable from plain application code
(acceptable — these features are human-facing by nature).

### Option 3 — Create a separate `nextlabs-cli` package

Split the CLI into its own distributable that depends on the SDK.

**Pros:** independent release cadence; CLI contributors need no SDK
internals; enables alternative SDK backends behind one CLI.
**Cons:** premature for current scope; doubles release/versioning overhead;
no present requirement (own config files, plugin model, third-party
backends) justifies it.

## Decision

**Option 2 — convenience/composition commands live in the CLI layer
(`nextlabs-sdk[cli]`), as CLI-internal modules.**

The boundary rule, to be used for every future convenience request:

* **SDK core (`nextlabs_sdk`, `.cloudaz`, `.pdp`)** contains direct mappings
  of API endpoints, data models, auth/transport, and anything an
  application developer calls from code. It returns data and holds no
  opinion on output.
* **CLI extra (`nextlabs-sdk[cli]`)** may compose multiple SDK calls, filter
  and normalise their results, and render them (tables, trees, diffs,
  colour, paging, JSON) — **provided it introduces no new business logic and
  requires no persistent state of its own.**
* **Neither layer** hosts NextLabs platform/business rules, nor stateful
  workflows that span sessions.

A convenience feature graduates out of the CLI extra (toward Option 1 or 3)
only when it needs persistent state, an external system not already in the
SDK, or an independent release cadence. Until then, it stays CLI-internal.

The first application of this rule is the `policies diff` command, whose
diff engine and renderers live under CLI-internal modules and consume only
the existing `PolicyService` primitives.

## Consequences

* **Positive:** every future convenience request has a default home and a
  crisp test ("new business logic or persistent state? → not the CLI").
* **Positive:** the SDK public surface stays minimal and opinion-free,
  preserving ADR 0001's discipline.
* **Positive:** the boundary is visible in the filesystem — composite logic
  sits in CLI-internal packages, not in the SDK facades.
* **Negative:** composite convenience logic is not reusable from plain
  application code. Accepted: these features are inherently human-facing; if
  a genuine library consumer appears, that is the trigger to revisit
  Option 1/3.
* **Neutral:** this ADR governs placement only; it does not change the
  public API surface defined by ADR 0001.
