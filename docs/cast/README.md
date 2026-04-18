# CLI demo cast

The animated GIF embedded near the top of the project [`README.md`](../../README.md)
is generated from [`demo.tape`](demo.tape) using
[charmbracelet/vhs](https://github.com/charmbracelet/vhs).

## Regenerate the GIF

The devcontainer ships `vhs`, `ttyd`, and `ffmpeg` preinstalled (see
`.devcontainer/Dockerfile`). From the repository root:

```bash
vhs docs/cast/demo.tape
```

This (re)writes `docs/cast/demo.gif`. Commit both `demo.tape` and the
regenerated `demo.gif` together so the source-of-truth and the rendered
output never drift.

## What the demo shows

A short narrative covering the three most common day-one operations:

1. `nextlabs auth login` — acquire and cache an OIDC token.
2. `nextlabs policies search` — list policies in a Rich table.
3. `nextlabs pdp eval ...` — make a single authorization decision and
   see the `Permit` / `Deny` result.

The cast runs against a **scripted fixture** baked into the tape (no
live tenant), so the output is fully deterministic. If the real CLI's
output evolves and the cast looks stale, edit `demo.tape` and
regenerate.
