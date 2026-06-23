---
name: nextlabs-cli
description: Compose `nextlabs` CLI commands (NextLabs CloudAz Console + PDP; `pip install nextlabs-sdk[cli]`) to answer a question. Use when the user wants to look up, search, compare, or report on NextLabs policies, components, tags, PDP decisions, reports, dashboards, or audit/activity logs — especially when the answer needs a name resolved to an ID or several commands chained together.
---

The `nextlabs` CLI wraps the CloudAz Console API and the PDP REST API. Most
real questions are not one command but a small composition: you **resolve** a
human reference to an ID, **act** with the command that needs that ID, then
**interpret** the result for the user. Infer the chain the question implies;
the example below is one shape, not the only one.

## Method

Run this loop. Each step names what "done" means before the next begins.

1. **Gate on auth.** Run `nextlabs auth status`. If no valid token exists,
   stop and tell the user to run `nextlabs auth login` (or set
   `NEXTLABS_TOKEN`/env vars) — do not retry blindly. *Done when:* a valid
   token is confirmed, or the user has been handed the exact auth command.
2. **Map the question to commands.** Pick the group(s) and command(s) that
   reach the answer. The CLI is self-documenting: read exact flags with
   `nextlabs <group> <command> --help` — never guess a flag name. If a
   command takes an ID but you only hold a name, plan a resolve step first.
   *Done when:* every command in the chain is chosen with `--help`-verified
   flags.
3. **Resolve names to IDs.** For each ID-keyed command, run the matching
   `search`/`list` with `-o json` and extract `.id`. On zero matches, tell the
   user; on several, list the candidates and ask which. *Done when:* every
   ID-keyed command has a concrete numeric ID — none invented.
4. **Run and chain.** Use `-o json` for any output you must parse or feed into
   the next command; use a human format for the final result you show the
   user. *Done when:* the commands have run and returned data (not an error).
5. **Interpret.** Read the real output and answer in plain terms. Never invent
   IDs, fields, or results; if a command failed, report the failure. *Done
   when:* the user's actual question is answered from observed output.

## JSON to chain, human to show

`-o`/`--output` takes `table` (default) · `wide` · `detail` · `json`. Choose
by audience: **json** when a later step or you must parse it; **table/detail/
wide** for the answer a human reads.

`-o` is a **global** option — it sits *before* the group, never after the
subcommand:

- ✅ `nextlabs -o json policies search --text billing`
- ❌ `nextlabs policies search --text billing -o json`  *(No such option)*

The same placement rule holds for every global option (`--token`,
`--base-url`, `--username`, `--pdp-url`, `-v`): before the group. Command-
specific flags (`--text`, `--from`, `--status`, …) go after the subcommand.

## Conventions

- **Auth.** Credentials come from `NEXTLABS_BASE_URL` + `NEXTLABS_USERNAME`
  (+ `NEXTLABS_PASSWORD`) or a pre-issued `NEXTLABS_TOKEN` / `--token` (which
  bypasses login and the cache). Failures hint "Run `nextlabs auth login`".
- **Name → ID.** No command searches by name and acts in one call — a name
  always costs a resolve hop before the command that consumes the id.
- **Policy diff** auto-selects the two most recent *deployed* revisions;
  override with `--from`/`--to`. `-o json` yields
  `{ "changes": [{path, kind, old, new}], "hidden_noise_count": N }`;
  `--format semantic|unified` controls the human view; `--show-all` reveals
  ordering/noise; `--exit-code` returns non-zero when differences remain.
- **Log time windows** (`audit-logs`, `activity-logs`) use `--start-date`/
  `--end-date` in **epoch milliseconds**.

## Command map

| Group                  | Reach for it to…                                              |
| ---------------------- | ------------------------------------------------------------ |
| `auth`                 | login · logout · status · test · accounts · use (the gate)   |
| `policies`             | search · get · history · view-revision · **diff** · deploy · export · find-dependencies · generate-xacml/pdf |
| `components`           | search · get · create/modify/delete · deploy · find-dependencies |
| `component-types`      | search · get · clone · create/modify/delete                  |
| `tags`                 | list `<tag_type>` · get · create · delete                    |
| `operators`            | list · list-by-type · list-types (data-type metadata)        |
| `pdp`                  | **eval** · permissions · explain (authorization decisions)   |
| `reports`              | list · get · widgets · enforcements · export · generate-\*   |
| `dashboard`            | alerts · top-users · top-resources · top-policies            |
| `audit-logs`          | search · export · list-users (entity-change audit trail)     |
| `activity-logs`        | search · get-by-row-id · export (enforcement activity)       |
| `reporter-audit-logs`  | search                                                        |
| `system-config`        | get (Reporter UI settings)                                    |

## Example — "Compare the last two revisions of policy 'test policy'"

```bash
# 1. Gate on auth.
nextlabs auth status                      # else: nextlabs auth login

# 2-3. Resolve the name to an ID (json to chain).
nextlabs -o json policies search --text "test policy" \
  | jq '.[] | {id, name}'                 # confirm the match, take its .id
#   0 hits → tell the user; >1 → list candidates and ask which.

# 4. Act: diff auto-picks the two most recent deployed revisions.
nextlabs -o json policies diff <id>       # structured changes to interpret
#   or, for a human to read:  nextlabs policies diff <id>

# 5. Interpret: summarise each change as path + kind + old→new, calling out
#    effect, condition, and obligation changes; mention hidden_noise_count.
```
