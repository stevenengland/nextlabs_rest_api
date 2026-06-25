# ADR 0004: Policy search expression grammar (SCIM `--where` + `--field`)

## Status

Draft

<!--
Lifecycle: Draft (recorded, not yet realised) → Implemented (the
delivering slices of PRD #226 have landed). The final docs slice flips
this to Implemented; intermediate slices realise the decision below.
-->

## Context

`nextlabs policies search` exposes only six hard-coded flags
(`--status`, `--effect`, `--text`, `--tag`, `--sort`, `--page-size`).
The backend `POST /console/api/v1/policy/search` accepts a far richer
`SearchCriteria`: an array of `SearchField` entries spanning eight match
types (`SINGLE`, `SINGLE_EXACT_MATCH`, `TEXT`, `DATE`, `MULTI`,
`MULTI_EXACT_MATCH`, `NESTED`, `NESTED_MULTI`) over arbitrary policy
fields. The full server-side search surface is unreachable from the CLI,
and there is no supported path to pass a raw payload.

Two properties of the backend constrain any solution:

1. **`fields[]` are combined with AND only** — there is no server-side
   `OR`, negation, or grouping across fields.
2. **Field names are server-defined** and vary by endpoint; there is no
   discovery API.

Because the CLI translates user input *client-side* into the criteria
payload, the backend's AND-only limit constrains the **semantics** we can
honour, not the **syntax** we may accept.

ADR 0002 draws the SDK-core vs. CLI-extra boundary: composition and
rendering belong to the CLI; the SDK core stays an opinion-free API
wrapper. This ADR must place the new parsing code on the correct side of
that line.

## Decision Drivers

* Reach **all eight match types**, including nested and date.
* Serve both a **human-typable** register and a **scriptable** register.
* **Stay close to a hardened, existing grammar** rather than inventing a
  bespoke query language we would have to specify and maintain.
* Be **reusable** beyond the CLI (programmatic SDK callers) and raise
  within the `NextLabsError` hierarchy.
* **Non-breaking** for current flag users.
* Respect the ADR 0002 boundary.

## Considered Options

### Option 1 — Bespoke query language

Invent a CLI query DSL with our own operators/precedence.

**Cons:** a parser to specify, test, and maintain; reinvents solved
problems; most query-language power (OR/NOT) cannot be pushed to an
AND-only backend, so it would be cosmetic or rejected anyway.

### Option 2 — Structured repeatable flag only (AWS/kubectl style)

A single `--field Name=Value`-style flag, no human grammar.

**Pros:** structurally identical to the backend (AWS `--filters`:
OR-within-values, AND-across-filters); minimal surface.
**Cons:** verbose, less readable for multi-criteria human use.

### Option 3 — Established REST filter grammar (human) + machine flag (chosen)

Adopt a hardened, standardised REST filter grammar for the human
register and a small explicit flag for the scriptable register; both
compile to the same `SearchField` list. Grammar sub-options weighed:
**SCIM (RFC 7644)**, **OData v4**, **RSQL/FIQL**.

* SCIM's complex-attribute grouping `tags[key eq "v"]` maps 1:1 to the
  backend's `nestedField`; `sw`/`co` cleanly split prefix vs. contains;
  it is the native filter vocabulary for an IAM/policy audience; a mature
  Python parser exists (`scim2-filter-parser`).
* OData is widely recognised but expresses nesting via verbose `any()`
  lambdas.
* RSQL is compact and Spring-idiomatic but has no nested grouping and
  thin Python tooling.

### Option 4 — Raw JSON only

Only accept a hand-written `SearchCriteria` JSON file.

**Cons:** maximal power, no ergonomics or discoverability.

## Decision

Adopt **Option 3 with SCIM (RFC 7644)** as the human grammar, alongside a
machine flag and a raw escape. Concretely, `nextlabs policies search`
gains three front-ends that all compile to one `SearchField` list (which
the backend ANDs):

* **`--where '<SCIM filter>'`** — human register. Parsed with the
  RFC-7644-conformant `scim2-filter-parser` (lexer + AST); we own only
  the AST → `SearchField` transpiler.
* **`--field 'NAME[:TYPE]=VALUE'`** (repeatable) — machine register. A
  small hand-written parser with an inference ladder (dotted → nested,
  comma → multi, else `SINGLE_EXACT_MATCH`); `:TYPE` overrides.
* **`--criteria-file <path>`** — raw escape; mutually exclusive with the
  expression flags.

The existing flags remain as **desugaring shorthands** (non-breaking).
Because the backend cannot `OR`/negate across fields, the transpiler
**rejects cross-field `OR`/`NOT`** with a clear `SearchExpressionError`,
while collapsing a **same-field `or`-group** into a `MULTI` list. The
reserved attribute `text` emits the backend's bundled `TEXT` entry.

**Placement (relative to ADR 0002):** the parsers live in the **SDK core**
(`_cloudaz`), not the CLI extra. They are pure, side-effect-free
transforms that produce an API-model object (`SearchField`) for a single
call — the same role as the existing `SearchCriteria` builder. They are
**not** the "compose multiple calls and render" convenience that ADR 0002
confines to the CLI. The new `scim2-filter-parser` dependency is added to
the **`cli` optional-dependency group**, since `--where` is a CLI-only
feature; core SDK dependencies are untouched.

## Consequences

* **Positive:** the full eight-type backend search surface becomes
  reachable; users get a readable human register and a scriptable one.
* **Positive:** anchoring on RFC 7644 + an existing parser keeps the
  bespoke surface to the type mapping only.
* **Positive:** parsers are reusable by programmatic SDK callers and obey
  the error-hierarchy rule.
* **Positive:** existing flag invocations keep working unchanged.
* **Negative:** a new CLI-only dependency (`scim2-filter-parser`).
* **Negative / accepted:** `OR`/`NOT` across fields are rejected, not
  emulated; users run separate searches. Honest to the backend.
* **Open / to verify:** the precise `SINGLE` vs. `SINGLE_EXACT_MATCH`
  boundary and whether a date keyword needs a client-computed window are
  pinned against the live backend in E2E.
* **Neutral:** governs the policy-search command only; the parser core is
  written generically for cheap later reuse by other search endpoints.
