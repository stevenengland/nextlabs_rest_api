# Troubleshooting

Common symptoms and fixes when using the `nextlabs` CLI or the
`nextlabs-sdk` Python library. Each entry follows a
**symptom → cause → fix** pattern. If your problem isn't listed, please
[open an issue](https://github.com/stevenengland/nextlabs_rest_api/issues).

## `AuthenticationError` on every command after a working session

**Symptom:** every `nextlabs` invocation fails with
`AuthenticationError`, including ones that worked yesterday.

**Cause:** the cached OIDC token has expired *and* the refresh-token
flow has failed (refresh expired, credentials rotated, or the cached
entry is bound to a different `client_id`).

**Fix:**

```bash
nextlabs auth logout
nextlabs auth login
```

If you maintain multiple environments, list and switch between cached
accounts with `nextlabs auth accounts` and `nextlabs auth use <name>`.

## `Re-login required` on a long-running session

**Symptom:** a command fails with
`Re-login required: Refresh token rejected by server — re-login required`
(followed by provider detail such as `invalid_grant`).

**Cause:** the cached refresh token is no longer usable (expired, the
CloudAz session was revoked, or credentials were rotated). The CLI
surfaces this as `RefreshTokenExpiredError`, a dedicated subclass of
`AuthenticationError`.

**Fix:** on an interactive TTY the CLI prompts for your password once
and retries the command transparently. In non-interactive contexts
(scripts, CI), re-supply credentials explicitly — for example via
`--password` / `NEXTLABS_PASSWORD`, or by calling
`nextlabs auth login` again. Run `nextlabs auth status` to confirm
the new cached entry is `Refreshable: yes`.

## PDP commands keep prompting for `--client-secret` / `--pdp-url`

**Symptom:** every `nextlabs pdp …` call needs `--client-secret`,
`--pdp-url`, and `--pdp-auth` again, even after a successful run.

**Cause:** PDP commands use OAuth *client-credentials*, not
username/password. Until the PDP credentials are registered in the
local cache, the CLI has nowhere to recover them from.

**Fix:** register the account once with `auth login --type pdp`.

```bash
nextlabs auth login --type pdp \
  --pdp-url https://pdp.example --client-id my-client \
  --client-secret "$SECRET" --pdp-auth pdp
```

The CLI mints a token, caches the `client_secret` alongside it, and
persists `pdp_url` + `pdp_auth` as account preferences. Subsequent
`nextlabs pdp …` invocations reuse all three transparently. Rotate
the secret by re-running `auth login --type pdp` with the new value;
clear the entry with `nextlabs auth logout` (after
`nextlabs auth use "[pdp]@<pdp-url>"` if it is not already active).

## SSL verification failures against an internal CloudAz instance

**Symptom:**
`SSLError: certificate verify failed: self-signed certificate in certificate chain`.

**Cause:** an on-premise CloudAz deployment is fronted by a private CA
or a self-signed certificate that your OS trust store doesn't know
about.

**Fix (production-correct):** install the CA bundle into your system
trust store (or set `SSL_CERT_FILE` to a bundle that contains it).

**Fix (development only — never in production):** disable verification
for one invocation:

```bash
nextlabs --no-verify policies search
```

For the SDK, use `HttpConfig(verify_ssl=False)`.

## `NEXTLABS_TOKEN` is set but the CLI still asks for a password

**Symptom:** you set `NEXTLABS_TOKEN` (or pass `--token`) for CI use,
but the CLI prompts for or rejects a missing `--password`.

**Cause:** the variable name has a typo, or the value is empty / unset
in the shell that actually runs `nextlabs` (common in `make` recipes
and CI runners that strip env vars by default).

**Fix:** verify the variable is non-empty in the same shell:

```bash
[ -n "$NEXTLABS_TOKEN" ] && echo "ok" || echo "MISSING"
nextlabs auth status
```

When `--token` / `NEXTLABS_TOKEN` is set, the CLI bypasses the login
flow *and* the token cache entirely — no password is consulted, no
cache file is written.

## "Where is my cached token stored?"

**Symptom:** you want to delete or inspect the cache file but don't
know where it lives.

**Cause:** the location depends on `--cache-dir`, `NEXTLABS_CACHE_DIR`,
and `XDG_CACHE_HOME`.

**Fix:** the lookup precedence is:

1. `--cache-dir <path>` or `NEXTLABS_CACHE_DIR` → `<path>/tokens.json`
2. `$XDG_CACHE_HOME/nextlabs-sdk/tokens.json`
3. `~/.cache/nextlabs-sdk/tokens.json`

The file is written `0600` inside a `0700` directory. To wipe it:

```bash
nextlabs auth logout              # preferred
rm "$(echo "${NEXTLABS_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}}")/nextlabs-sdk/tokens.json"
```

## PDP returns no `Permit`/`Deny` decision (status code is non-OK)

**Symptom:** `nextlabs pdp eval ...` returns a result whose
`status.code` is something other than `ok` and whose `decision` is not
the `Permit`/`Deny` you expected.

**Cause:** the request is missing a subject, resource, action, or
environment attribute that one of your policies requires. The PDP
cannot reach a definitive answer.

**Fix:** re-run with HTTP-level tracing to see the exact request/response
the CLI is sending:

```bash
nextlabs -vv pdp eval \
  --subject alice --resource doc-42 --resource-type document \
  --action read --application wiki \
  --subject-attr role=engineer \
  --resource-attr classification=internal
```

Use `-v` (single) to add only request context to errors; `-vv` (double)
prints every HTTP request and response body. Add the missing attribute
with `--subject-attr key=value`, `--resource-attr key=value`, etc.
