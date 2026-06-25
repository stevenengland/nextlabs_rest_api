# ADR 0006: Cross-policy comparison

## Status

Accepted

## Context

The `policies diff` command compares two revisions of a single policy. A new
demand is to compare two *different* policies — answering "how do these two
policies differ in what they actually enforce?" rather than "how did this one
policy change between deployments?".

Two policies always differ in their identity attributes: each has its own
`id`, `name`, `fullName`, folder placement, version counters and owner. A
naive reuse of the revision-diff engine would drown the meaningful payload
delta (subjects, actions, conditions, obligations, tags) under a wall of
identity noise that is true by construction and tells the reader nothing.

We need a comparison mode that suppresses cross-policy identity noise while
preserving every genuine difference in policy content, including differences
nested inside components, obligations and tags — two policies may legitimately
share a component name while differing in its expression, and that difference
must survive.

## Decision Drivers

* Reuse the existing `diff_payloads` engine and renderers rather than forking
  a parallel comparison path.
* Keep the command surface small and predictable; avoid a proliferation of
  flags.
* Suppress only the identity noise that is true by construction, never genuine
  policy-content differences.
* Keep the strip behaviour inspectable: a user must be able to see the full,
  unstripped picture on demand.

## Decision

Extend `policies diff` with an **optional second positional policy id**. Arity
selects the mode: `diff A` keeps the existing single-policy revision diff;
`diff A B` enters cross-policy mode. Mode is never chosen by a flag.

In cross-policy mode:

* Each side resolves its revision independently — latest deployed by default.
  `--from` selects policy A's revision and `--to` selects policy B's; the
  revision flags are not renamed and gain no aliases.
* Before diffing, a **fixed built-in set** of top-level identity fields is
  stripped from each payload:
  `id`, `name`, `fullName`, `folderId`, `parentId`, `parentName`, `version`,
  `revisionCount`, `ownerId`, `ownerDisplayName`. The constant is
  `_CROSS_POLICY_IDENTITY_FIELDS`. There is no user-override flag in this
  iteration.
* The strip is **top-level only**. Nested components, obligations and tags are
  never stripped, so a renamed component or a changed expression still
  surfaces.
* Stripped fields are **silent**: removed before diffing, so they neither
  render as changes nor count toward the hidden-noise total.
* The strip applies only when `--show-all` is off. `--show-all` reveals every
  stripped identity field, exactly as it already reveals noise fields.
* The diff header shows both policy identities (name and id per side) plus a
  short note that identity fields were ignored.
* `--format`, `--exit-code` and the JSON output behave identically in both
  modes; `--exit-code` reflects post-strip differences.

The strip is implemented as a shallow filter in the engine
(`diff_payloads(..., cross_policy=True)`), with the unified renderer applying
the same top-level filter to its JSON body so both human formats stay in
parity.

## Consequences

* Cross-policy comparison reuses one comparison engine and both renderers; the
  only new surface is one optional positional argument and one engine flag.
* The identity strip set is a fixed constant, so behaviour is predictable and
  documented; broadening it (or making it user-configurable) is a deliberate
  future decision rather than an accident.
* Because the strip is top-level only, genuine content differences — including
  those nested inside identically-named components — are never hidden.
* `--show-all` remains the single escape hatch for seeing the complete,
  unfiltered comparison, keeping the suppression inspectable.
