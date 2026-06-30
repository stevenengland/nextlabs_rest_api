# ADR 0007: Forensic obligation removal content and list element-count markers in the semantic diff

## Status

Draft — drives PRD #264. To be finalised as the implementation slice lands
(decision text below is settled; `Consequences` / migration notes will be
confirmed against the merged implementation).

## Context

`policies diff` renders a human-readable **semantic** view (default) and a
`--format unified` view. In the semantic view, added/removed **obligations** are
shown as a one-line summary carrying only the obligation `name`
(`ObligationSummary`). The engine discards the obligation's `params` and
`policyModelId` for the add/remove case, so the payload never reaches the
renderer. The full content is only recoverable from `--format unified`, which is
harder to read and re-orders/strips fields.

This is a forensic blind spot. For revision audit ("what was in the block that
got deleted?") an analyst sees that an `enforce_table_list` or `data_masking`
obligation disappeared, but not *which* tables or masking rules it carried.

Verified facts that constrain the design:

- Three semantic-render sites replace removed/added container content with a
  summary, by design: obligations (`ObligationSummary`), tags (`TagSummary`),
  and component slots (`ComponentSummary`). Generic dict keys and nested objects
  already render full content on add/remove.
- Obligations are matched **positionally** within `(name, policyModelId)`
  buckets (per ADR 0005); tags and component slots are identity-matched.
- `--show-all` currently means "reveal ordering + noise differences"; a dim
  footer reports `N noise-only change(s) hidden`.
- The diff model (`FieldChange`) retains no element counts for list-typed
  fields; lists are either expanded into per-element add/remove/change nodes
  (obligations/tags/slots) or compared as a single `change` carrying full
  old/new lists (generic arrays).

A second, related observation: when a list-typed field's **element count**
changes, the semantic view shows the individual `+ / -` lines but gives no
at-a-glance count signal, and a positionally-paired obligation removal can be
visually conflated with an in-place edit.

## Decision Drivers

- Make "what was removed/added" visible in the readable view without forcing the
  unified view.
- Prefer removing an inconsistency over adding a configuration knob (generic
  keys/objects already expand; the summary sites are the outliers).
- Keep the default view scannable; avoid dumping low-signal structural fields.
- Do not destabilise `--format unified` (parsed by tooling).
- Do not change authorization-relevant matching semantics as a side effect.

## Considered Options

### Option A — Expand obligation content on add/remove, obligations only (CHOSEN)

Stop discarding obligation payload in the engine; carry the full obligation on
the add/remove change record. The renderer keeps the one-line summary header and
nests the content beneath it as `+ / -` field-lines, reusing existing
nested-field formatting and the existing `--show-all`-gated noise filter.
Expansion is **always on**; only the in-expansion noise filtering respects
`--show-all`. Tags and component slots are left as summaries.

Pros: closes the forensic gap by default; consistent with how generic
keys/objects already render; small surface; no new flag; no matching change.
Cons: a removed obligation with a large `params` adds vertical space (bounded;
the summary header keeps it scannable).

### Option B — Gate expansion behind `--show-all` (REJECTED)

Keep terse summaries by default; expand only under `--show-all`.

Pros: reuses the filter-by-default idiom; keeps default minimal.
Cons: hides the primary forensic signal by default; overloads `--show-all`
(today purely noise/ordering); leaves the generic-vs-special inconsistency in
place.

### Option C — Expand all three summary sites (obligations, tags, components) (REJECTED)

Pros: uniform "removal always shows content".
Cons: tag summaries (`key (LABEL)`) and component summaries (`name (id=N)` +
version) already carry the salient identity; the remaining fields are constant
(`type`, `status`) or low-signal structural/empty (`member_conditions: []`,
deployment metadata). Expansion would add noise without forensic value.

### Option D — Change obligation matching to unordered/similarity (DEFERRED)

The motivating data made positional pairing look like an in-place edit. Best-
match/unordered matching would render removals as clean add/remove.

Cons: changes authorization-relevant comparison semantics; larger blast radius;
governed by ADR 0005. Out of scope here — this ADR changes only the *rendering*
of unmatched obligations, not the matching.

### Element-count marker (orthogonal, CHOSEN)

Annotate any list-typed field whose element count differs with `[old → new]` on
its header line, semantic view only, emitted only when the count changed, net
counts only. Applies to obligations, tags, component slots, and generic arrays.
Requires the diff model to retain old/new element counts (or both lengths).

Rejected variants: always show `[n]` (noisier); show a `+a −b` breakdown
(redundant with the per-element `+ / -` lines).

## Decision

Adopt **Option A** for content expansion (obligations only, always-on,
noise-filter respects `--show-all`) and the **element-count marker** for all
list-typed fields (semantic view only, shown only when the count changes).

Both changes are confined to the engine (carry obligation payload; retain list
element counts) and the semantic renderer (expand content; emit the marker). The
`--format unified` renderer is untouched. Obligation matching is unchanged
(positional within `(name, policyModelId)`, per ADR 0005); `--show-all` keeps
its current meaning.

Scope covers both `allowObligations` and `denyObligations`.

## Consequences

> To be confirmed against the merged slice.

Easier:

- The readable diff shows the full content of removed/added obligations by
  default, closing the forensic gap without the unified view.
- A `[old → new]` marker makes list-size changes obvious regardless of whether
  the diff is ordered or unordered.
- The special-cased obligation removal now matches how generic keys/objects
  already render (one fewer inconsistency).

Harder / accepted:

- Removed obligations with large `params` consume more vertical space (bounded by
  the noise filter and the retained summary header).
- Golden semantic-render tests for obligation add/remove and for list headers are
  updated; `--format unified` golden tests must stay unchanged.

### Not addressed here

- Obligation matching strategy (positional vs unordered vs similarity) — ADR 0005
  governs; revisit separately if needed.
- Component slots with identical `(id, name, version)` but changed internals
  (e.g. `member_conditions`) reported as "no change" — a pre-existing change-
  *detection* gap in ADR 0005's area, distinct from this removal-*content* work.
