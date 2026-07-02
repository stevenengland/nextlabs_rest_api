# ADR 0003: Encrypt the CLI token cache at rest

## Status

Accepted — implemented.

The implementation has landed. The historical slice plan remains below for
traceability; the implementation confirmations capture the resolved values.

Tracking: PRD [#130](https://github.com/stevenengland/nextlabs_rest_api/issues/130).
Builds on ADR 0001 (public API surface) and ADR 0002 (CLI convenience-command
boundary).

## Context

The `nextlabs` CLI persists OAuth credentials (access tokens, refresh tokens,
OIDC id_tokens, client secrets) in cleartext at
`~/.cache/nextlabs-sdk/tokens.json` (mode `0600`). File permissions protect
against other local UIDs but give **zero** protection once the bytes leave the
live host: disk backups, container/VM snapshots, a stolen laptop disk, or sync
tools all exfiltrate valid credentials.

We want transparent encryption-at-rest for the token cache that works on
Windows, macOS, Linux, headless servers, devcontainers, and CI — without
forcing users to maintain shell wrappers or per-shell ceremony.

### Threat model (scope boundary)

Encryption-at-rest here defends against **off-host exfiltration** — backups,
snapshots, lost or stolen disks. It does **not** defend against a compromised
*live* host: any process running as the same UID can already read the
plaintext file today and can read the in-process key after unlock. This is the
same boundary that `gh`, `aws`, and `az` accept; none of them prompt for a
secret on every command, because the OS login session is the trust boundary.

This boundary is load-bearing: it is the reason we **drop** `auth lock` and
`auth change-password` (they only address the live-host threat we have scoped
out), and the reason we never force per-command prompting.

## Decision Drivers

* Protect the at-rest case (backups/snapshots/stolen disk), which plaintext
  `0600` does not.
* Match user expectations set by industry CLIs (`gh`, `aws`, `az`): transparent
  unlock when an OS keyring is present, never break automation, never abort.
* Keep the SDK core lean and the crypto core deep and IO-free (testable without
  a filesystem, keyring, or TTY).
* Preserve the `TokenCache` interface (ADR 0001 public surface) and the CLI
  boundary (ADR 0002) — no new business logic or persistent state leaks into
  the wrong layer.
* Cross-platform parity: identical behavior on Windows/macOS/Linux, including
  headless and CI.
* Each implementation slice must be independently shippable with **no
  regression** for existing users.

## Considered Options

### A. Key derivation model

1. **Direct key** — each source's secret is fed through Argon2id to produce the
   AES key directly. Simplest, but: the file format forks (salt present for
   passphrases, absent for a random keyring key); switching sources requires a
   full re-encrypt; Argon2id runs even on a high-entropy random keyring key
   (pure latency, no security gain); and `change-password`/rotation would
   require re-encrypting the whole file.
2. **Single-slot envelope (chosen)** — a random 256-bit Data Encryption Key
   (DEK) encrypts the file; the DEK is wrapped by a Key-Encryption-Key (KEK)
   derived from whichever source unlocked. One fixed file layout for every
   source; the crypto core stays passphrase-agnostic; the DEK is always full
   entropy regardless of source; future rotation is a cheap rewrap of one
   field, not a data re-encrypt.
3. **Multi-slot envelope (LUKS/age style)** — N variable-length wrap slots in
   the header. Maximally flexible (multiple unlock methods per file,
   cross-machine), but introduces variable-length binary parsing we would not
   exercise in v1 (one active source per machine). Rejected as premature; the
   chosen format can grow to this via a version bump.

### B. Rollout / fallback behavior

1. **Hard cutover** — encryption on by default; a non-TTY context with no
   passphrase source aborts. Cleanest posture, but breaks existing cron / CI /
   devcontainer automation on upgrade and is more hostile than `gh`.
2. **Encrypt-when-possible, never abort (chosen)** — encrypt whenever a source
   exists; otherwise fall back to plaintext with a one-time warning. Existing
   plaintext caches are never broken. Mirrors `gh` ("secure storage when a
   keyring is available, plaintext fallback otherwise").

### C. Dependency placement

1. **All crypto + keyring as an optional `[secure]`/`[cli]` extra** — keeps core
   lean, but a library consumer who wants the encrypted cache (the public peer
   of `FileTokenCache`) is forced to install CLI/UI deps or hit `ImportError`.
2. **Crypto in core, keyring in `[cli]` (chosen)** — `cryptography` and
   `argon2-cffi` become core dependencies so `EncryptedFileTokenCache` is a
   first-class, always-importable public class (symmetric with the existing
   public `FileTokenCache`). `keyring` — the app/UX persistence-backend concern,
   flaky on headless — stays in `[cli]`, used only by the CLI-wired resolver.
   This mirrors `azure-identity` (cryptography is core) while keeping the
   keyring/DPAPI persistence piece nearer the app, like `msal-extensions`.
3. **Everything in core** — simplest, but pushes a flaky, app-flavored `keyring`
   dependency onto every plain SDK consumer.

### D. Argon2 parameter handling

1. **Free-form params in the header** — flexible tuning, but an attacker can
   raise memory/iterations in a tampered header and force huge allocations
   *before* AES-GCM authentication can detect the tampering (pre-auth DoS).
2. **Code-owned suite-id (chosen)** — the header carries a 1-byte suite-id that
   indexes a parameter table baked into the code (plus the salt). No
   attacker-controlled cost; simpler format; new tuning = new suite-id + version
   bump.

## Decision

Implement transparent, **encrypt-when-possible** at-rest encryption for the CLI
token cache using a **fixed-layout, single-slot envelope** design.

### Cryptography and file format

* **Cipher:** AES-256-GCM for both the file payload (under the DEK) and the DEK
  wrap (under the KEK).
* **KDF:** Argon2id (`argon2-cffi`), used **only** on human-passphrase paths
  (`NEXTLABS_MASTER_PASSWORD`, TTY). Parameters are selected by a code-owned
  **suite-id**, not read free-form from the file.
* **DEK:** a fresh random 256-bit key per cache file; it encrypts the JSON
  payload directly and never changes for the life of the file.
* **On-disk binary format (one fixed layout for all sources):** magic `NLBX` ·
  version byte · wrap-type byte (`0` = argon2 passphrase, `1` = raw/keyring) ·
  suite-id + salt (zeroed when wrap-type is raw) · wrapped DEK (32 bytes + GCM
  tag) · data nonce (12 bytes) · AES-256-GCM ciphertext · GCM tag. The full
  header is fed as AAD to the payload cipher, so any tampering (including
  lowering KDF strength) fails authentication.
* **Decryption failures** (wrong passphrase, tampered ciphertext, tampered
  header, unknown version, garbage) all normalize to a **single** generic
  `TokenCacheError` in the `NextLabsError` hierarchy — no oracle leakage, no
  per-failure exception types. Its message directs the user to delete the cache
  and re-login; recovery without the secret is by design impossible.

### Passphrase sources and resolution

Resolution order is fixed and used by every consumer:

1. `NEXTLABS_TOKEN` set → bypass the cache entirely (unchanged behavior).
2. `NEXTLABS_MASTER_PASSWORD` → Argon2id → KEK (canonical CI/CD path).
3. OS keyring (`keyring` library; auto-selects Credential Manager/DPAPI,
   Keychain, or Secret Service) → stores a **raw random 32-byte KEK**, no
   Argon2. `available()` self-tests via a write→read→delete sentinel to detect
   the null backend; backend errors fall through.
4. Interactive TTY passphrase via the console abstraction → Argon2id → KEK.
5. No source → **plaintext fallback with a one-time warning** (see rollout).

The resolver returns `(secret_material, source_label)` where the label is one
of `env` / `keyring` / `tty` / `none`. The unwrapped DEK is **cached
in-process** for the lifetime of a single CLI invocation, so Argon2id runs at
most once per command (not once per `load`/`save`).

### Rollout (encrypt-when-possible, never abort)

* A source is available → encrypt. ✔ the goal.
* Interactive TTY, no source → confirmation gate / passphrase prompt.
* **Non-TTY, no source → write plaintext + one-time stderr warning. Never
  abort.** `NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1` silences the warning.
* An existing plaintext cache is **never broken** by an upgrade.

### Migration

`EncryptedFileTokenCache.load` reads **both** formats (legacy plaintext JSON or
`NLBX`) and never writes. Because `save` always rewrites the whole file
encrypted, migration completes **organically on the next write** — atomic, no
read-path mutation, no race, no prompt inside `load`.

### Module and API design

* New, under `src/nextlabs_sdk/_auth/_token_cache/`: `_secret_box.py`
  (envelope crypto, IO-free), `_encrypted_file_token_cache.py`
  (`TokenCache` impl), per-source files (`_env_passphrase_source.py`,
  `_keyring_passphrase_source.py`, `_interactive_passphrase_source.py`,
  `_passphrase_resolver.py` — one class per file), and `_cache_factory.py`.
* **Factory contract is split:**
  * `build_token_cache(...) -> TokenCache` — a drop-in for every existing
    consumer. The `TokenCache` interface (`load`/`save`/`delete`/`keys`) is
    **unchanged**; the ~10 current `build_file_cache(...)` call sites migrate to
    it and the two concrete `FileTokenCache` parameter types
    (`known_accounts`, `_client_factory`) widen to `TokenCache`.
  * `inspect_token_cache(...) -> CacheStatus` — a **read-only** inspector for
    the status command. Reports path, encryption state, source label, and KDF
    suite **without unlocking, without Argon2, without prompting**.
* **Console I/O** is an injectable abstraction (`isatty` / `prompt_secret` /
  `confirm`): POSIX opens `/dev/tty`; Windows uses the console. The factory and
  resolver depend on this abstraction, not raw `stdin`/`stdout`, so behavior is
  cross-platform and mockable.
* **Atomic writes** reuse the existing `mkstemp` (same directory, `0600`) →
  write → `os.replace` pattern via a shared helper; directory mode `0700` and
  file mode `0600` are preserved.
* `EncryptedFileTokenCache` is a **single** class for both sync and async
  clients (file IO is not async-bound) and is promoted to the public surface
  (`nextlabs_sdk`), symmetric with `FileTokenCache`.

### CLI surface

* `nextlabs auth status` is **extended** (not duplicated) with a concise cache
  line (`gh`-style), sourced from `inspect_token_cache`, shown even when no
  token is present.
* `auth lock` and `auth change-password` are **not** implemented (out of scope
  per the threat model; recovery is `auth logout` + re-login). The envelope
  design leaves rewrap-based rotation a cheap future addition if a concrete
  need appears.

### Dependencies

* `cryptography` and `argon2-cffi` → **core** dependencies.
* `keyring` → **`[cli]`** extra. The encrypted modules are arranged so that
  `import nextlabs_sdk` without `[cli]` never triggers a keyring import.

## Consequences

* **Positive:** at-rest credentials are protected against backups/snapshots/
  stolen disks; transparent on desktops with a keyring; the canonical CI path is
  a single env var; nothing breaks on upgrade.
* **Positive:** the crypto core is deep, IO-free, passphrase-agnostic, and
  exhaustively unit-testable; one file format; one generic failure mode.
* **Positive:** `EncryptedFileTokenCache` is reusable by library consumers, not
  just the CLI, consistent with ADR 0001's public-surface discipline.
* **Positive:** slices are additive and individually shippable; the tracer
  encrypts env users while leaving everyone else exactly as before.
* **Negative:** `cryptography` and `argon2-cffi` (a C-extension) become core
  dependencies for all SDK consumers, including those who never persist tokens.
  Accepted: `cryptography` is near-ubiquitous and this keeps the public
  encrypted cache import-clean.
* **Negative:** a CI user who *expected* encryption but configured no source
  gets plaintext (with a warning) rather than a hard failure. Accepted as the
  `gh`-aligned trade-off; the warning explains how to enable encryption.
* **Neutral:** the suite-id approach trades free-form KDF tuning for a versioned
  table; tuning requires a code change plus a new suite-id.

## Implementation confirmations

* Argon2id suite 1 uses memory cost `65536`, time cost `3`, parallelism `4`,
  a 16-byte salt, and a 32-byte derived key.
* The `NLBX` header is fixed-layout: magic `NLBX`, version, wrap type,
  suite-id, salt, and wrapped DEK. The header is bound as AEAD additional data.
* The plaintext fallback warning is:
  `warning: token cache is stored UNENCRYPTED; set NEXTLABS_MASTER_PASSWORD to encrypt it, or NEXTLABS_DISABLE_TOKEN_ENCRYPTION=1 to silence this warning`.
* `TokenCacheError` uses one generic message for unreadable, undecryptable, or
  tampered cache data.
* Legacy plaintext migration is organic: reads leave plaintext untouched; the
  next encrypted write rewrites the file as an `NLBX` envelope.
* The in-process DEK cache lives only on each `EncryptedFileTokenCache`
  instance, so it never persists across CLI invocations.

## Revised slice plan (supersedes the original #131–#138 cut)

* **Closed:** #137 (`auth lock`), #138 (`auth change-password`).
* **#131 (re-cut) — encryption core + env path, safe-by-default:** envelope
  `SecretBox`, `EncryptedFileTokenCache` (reads both formats, writes encrypted,
  shared atomic helper, in-process DEK cache), `EnvVarPassphraseSource` +
  resolver, split `build_token_cache` / `inspect_token_cache`, `TokenCache`
  call-site migration, `TokenCacheError`, console abstraction skeleton, env-var
  wiring, dependency moves, public export. No-source ⇒ plaintext + warning
  (never abort). Independently shippable.
* **#132 — keyring source:** raw random KEK, sentinel probe, slotted into the
  resolver. Additive.
* **#133 — TTY source + plaintext confirmation gate:** interactive prompt and
  confirmation via the console abstraction (absorbs the interactive part of the
  original #135). Additive.
* **#136 — status cache line:** extend `auth status` via `inspect_token_cache`.
  Additive.
