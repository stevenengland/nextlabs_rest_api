# Token cache encryption

How the `nextlabs` CLI protects the OIDC token cache (`tokens.json`) at
rest, what the interactive hints mean, and how to reset a remembered
choice. See the [README](../README.md#oidc-tokens-caching-and-environment-variables)
for the cache location and lookup precedence.

## Resolution flow

`build_token_cache` consults passphrase sources in a fixed order every
time it runs:

1. **`NEXTLABS_MASTER_PASSWORD`** (environment variable) — used verbatim
   if set.
2. **OS keyring** — on first use, a random 32-byte key-encryption key
   (KEK) is generated and stored in the keyring; later runs reuse it. A
   keyring that is missing, locked, or a null backend is treated as
   unavailable and resolution falls through to the next source.
3. **Interactive TTY prompt** — on a controlling terminal, the CLI asks
   for a passphrase and derives Argon2id key material from it. An empty
   entry, a non-interactive stream, or an unusable `/dev/tty` is treated
   as unavailable. A [remembered plaintext choice](#remembered-choice)
   is consulted before this prompt, so once remembered the CLI never
   asks for a passphrase again.

If a source resolves, the cache becomes an `EncryptedFileTokenCache`: an
`NLBX` envelope where a random data key (DEK) encrypts the payload under
AES-256-GCM, itself wrapped by the resolved KEK (Argon2id for a
passphrase, HKDF-SHA256 for a keyring-sourced key).

If no source resolves and a controlling terminal is present, the CLI
warns and asks for confirmation before storing the cache unencrypted
(see [Interactive hints](#interactive-hints) below); declining aborts
without writing anything. With no terminal at all, the cache falls back
to plaintext with a single stderr warning and never aborts — set
`NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1` to silence that warning.

## Interactive hints

When no passphrase source resolves and a controlling terminal is
present, the CLI prints one state-aware hint to that terminal
(`/dev/tty`) — so it survives stdout/stderr redirection — before
deciding what happens next. Fresh and legacy plaintext fall through to
a confirmation prompt (below); lockout instead aborts immediately, with
no prompt shown:

- **Fresh** — no cache file exists yet:

  > No token cache yet; it will be created at {path}. It can be
  > encrypted at rest, but no passphrase source is set
  > (NEXTLABS_MASTER_PASSWORD or an OS keyring). See the project's
  > online documentation for details.

- **Legacy plaintext** — a cache file exists and is already unencrypted:

  > Your existing token cache at {path} is UNENCRYPTED and may contain
  > access/refresh tokens in plain text. Set NEXTLABS_MASTER_PASSWORD or
  > an OS keyring to re-encrypt it on the next write. See the project's
  > online documentation for details.

- **Lockout** — a cache file exists and is encrypted, but no source can
  unlock it. No confirmation prompt follows (see
  [Lockout abort](#lockout-abort) below).

## Remembered choice

After confirming plaintext storage, the CLI offers a one-time follow-up
prompt:

> Remember this choice so I stop asking? \[Y/n\]:

Accepting (the default) persists the acknowledgement and prints:

> Saved. The CLI won't ask again. To re-enable encryption, set
> NEXTLABS_MASTER_PASSWORD or an OS keyring; nextlabs auth status shows
> the cache location and current choice.

Once remembered, later runs with no environment or keyring passphrase
source skip the interactive passphrase prompt, the hint, and the
confirmation prompt, and build a plaintext cache silently. The
remembered choice is consulted after the keyring but before the
interactive passphrase prompt, so configuring `NEXTLABS_MASTER_PASSWORD`
or a keyring later upgrades the cache to encryption without needing to
reset anything.

The choice is global — shared by every account — and stored under a
reserved key in the same JSON file as other CLI account preferences
(`account_prefs.json`), not per account. `nextlabs auth status` reports
it as `Remembered plaintext choice: yes` / `no`.

## Lockout abort

If a cache file exists and is encrypted, but no configured source can
unlock it (wrong or missing passphrase, keyring entry cleared, etc.),
the CLI never falls back to plaintext for that file. It prints:

> Your token cache at {path} is ENCRYPTED but no passphrase source is
> available to unlock it. Set the original NEXTLABS_MASTER_PASSWORD /
> keyring, or delete {path} to start fresh. See the project's online
> documentation for details.

...and aborts the command without touching the file. This check runs
before the remembered choice is consulted, so a remembered
acknowledgement can never cause an encrypted cache to be silently
overwritten with plaintext.

## Resetting the remembered choice

The remembered choice has no dedicated CLI command; reset it by editing
the preferences file directly:

1. Locate `account_prefs.json` — the same directory as the token cache
   (`NEXTLABS_CACHE_DIR`, then `$XDG_CACHE_HOME/nextlabs-sdk`, then
   `~/.cache/nextlabs-sdk`).
2. Remove the reserved `"__token_cache__"` top-level key (real account
   entries are keyed by `base_url|username|client_id[|kind]`, which
   always contains `|`, so it never collides with the reserved key).
3. Save the file. The next run with no passphrase source available
   shows the hints and confirmation prompt again.
