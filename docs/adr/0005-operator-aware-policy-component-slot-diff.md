# ADR 0005: Operator-aware policy component-slot diff

## Status

Draft — drives PRD #235 (originates from bug report #216).

## Context

`policies diff` compares the five policy component slots (`subjectComponents`,
`toSubjectComponents`, `fromResourceComponents`, `toResourceComponents`,
`actionComponents`). Each slot is a `list[ComponentGroup]`, and each
`ComponentGroup` carries an `operator: str` plus a list of component refs. The
`operator` combines components **within** a group; groups are joined across the
list by an **implicit AND** (the model has no inter-group operator field).

The current comparison flattens every group in a slot into a single
identity-keyed map (`flatten_slot()` → `dict[id|name -> ComponentSummary]`),
which **discards `operator` and group boundaries**. Consequences:

- A pure operator flip (a group changing `OR` → `AND` with identical members)
  is reported as **no change**.
- A regrouping that moves components across operator boundaries — e.g.
  `(A OR B) AND C` vs `(A OR C) AND B` — is reported as **no change**, because
  the flat component set is identical.

Both cases change authorization semantics while the diff shows equality. This is
a correctness gap for anyone using `policies diff` to gate revision or
cross-environment drift.

Verified facts that constrain the design:

- Components and `tags` are compared **order-free** today (identity-matched), by
  design. Obligations are compared **positionally** within `(name,
  policyModelId)` buckets.
- `operator` is a free string with no case normalization anywhere.
- `ComponentGroup` does not nest. `ComponentSummary` keeps `id`, `name`,
  `version`. The noise blacklist strips `deploymentTime`, `deploymentRequest`,
  `createdDate`, `lastUpdatedDate`, `modifiedBy`, `modifiedById`,
  `deploymentPending`.

## Decision Drivers

- Fix the operator/grouping blindness (the actual defect).
- Preserve today's order-free membership behavior: a component that moves
  position — or moves between groups — must stay **recognized as present**,
  never reported as removed + added.
- Avoid assuming a server ordering guarantee the current code deliberately
  sidesteps (identity matching exists precisely so order does not matter).
- Keep output legible and the change minimal: reuse the existing change-record
  type, renderers, and `--exit-code`.
- Keep the comparison strategy swappable, so a later move to an ordered model is
  a localized change.

## Considered Options

### Option 1 — Order-free, group-aware (CHOSEN)

Keep identity-based matching. Compare each slot in two parts over one pass:

- **Membership** (unchanged from today): union of identities; per-component
  `+ / - / ~version`. Order-free.
- **Grouping** (new): over the components present in **both** revisions, compare
  the partition as a set of `(normalized-operator, frozenset(identity))` groups.
  Any difference emits a single grouping change.

Pros: fixes operator + cross-group drift; preserves moved=present; no ordering
assumption; small surface; reuses identity logic; deterministic (set algebra, no
matching heuristic). Catches structural drift even when operators are unchanged
(e.g. `(A OR B)` splitting into `(A) AND (B)`), because it compares the
frozenset partition, not per-component operator labels.

Cons: structural drift renders at group granularity (a `~ grouping` block)
rather than as a per-component move.

### Option 2 — Ordered + difflib (DEFERRED)

Switch component slots to ordered comparison: align groups positionally, align
components within a group by identity using `difflib.SequenceMatcher`
(`autojunk=False`), then attribute-compare matched pairs (applying the existing
blacklist). Operator drift falls out as `group[i].operator` change. A mid-list
insert (`1 2 3` → `1 2 X 3`) renders as `+ X` only.

Pros: single ordered pass; clean per-component output; handles mid-insert
gracefully; operator drift is incidental.

Cons: switches components from order-free to order-sensitive — a behavior change
beyond the defect, and it **reverses** the moved=present property. Relies on the
server returning groups/components in stable order across revisions; if order is
not guaranteed, it produces spurious false diffs. Larger blast radius.

### Option 3 — Coarse atomic groups (REJECTED)

Treat each group as an atomic `(operator, frozenset(identity))`; any differing
group renders as whole-group remove + add. Simplest and deterministic, but a
one-component edit reprints the entire group — too noisy for the common
multi-group slot.

### Option 4 — Group-matched fine-grained (REJECTED)

Match groups across revisions by best identity-overlap, then diff within matched
groups. Finest output, but the matching heuristic is ambiguous exactly on the
cross-group reshuffle the defect is about, and is nondeterministic.

## Decision

Adopt **Option 1 (order-free, group-aware)**.

Isolate the whole comparison behind one deep-module seam:

```
compare_slot(old_slot, new_slot) -> list[FieldChange]
```

The diff engine delegates per-slot comparison to it. The grouping signal reuses
`FieldChange(kind="change")` with path `"<slot>.grouping"` and canonical
structure strings in `old`/`new`; both renderers and `--exit-code` inherit it.
Operator comparison normalizes via `casefold().strip()` (display preserves
original casing). Obligations, `tags`, `sub_policy_refs`, `attributes`, and
nested `subComponents` are unchanged.

We do **not** ship Option 2 alongside (no strategy registry, config flag, or
dead alternative-model code). The optionality lives in this ADR plus the
`compare_slot` seam.

### Revisit triggers (when to switch to Option 2)

Switch deliberately only when **all** hold:

1. The server is confirmed to guarantee stable group/component ordering across
   revisions (removing the spurious-diff risk).
2. Users need positional / sequence-level granularity that Option 1's
   group-grained `~ grouping` block cannot express.
3. Mid-insert legibility (`+ X` only) becomes a concrete requirement.

### Migration cost

Localized: rewrite the body of `compare_slot` and its golden tests' design-bound
assertions. `_engine.py` orchestration, `_render_semantic.py`,
`_render_unified.py`, and the CLI are untouched.

## Consequences

Easier:

- `policies diff` detects operator flips and cross-group regrouping; revision /
  environment gates catch authorization-semantics drift.
- The membership path is unchanged, so existing add/remove/version output and
  its order-independence are preserved.
- A future model swap is a one-module change with a documented trigger set.

Harder / accepted:

- Structural drift surfaces at group granularity, not as a per-component move.
- Tests are split into design-agnostic invariants (operator drift detected;
  add/remove stays per-component; moved component never lost) and
  design-specific render assertions; the latter are rewritten if Option 2 is
  ever adopted.
