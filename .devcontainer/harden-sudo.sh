#!/usr/bin/env bash
#
# Gate `sudo` behind a password that only you know.
#
# By default the `vscode` user has passwordless sudo (NOPASSWD:ALL) and a
# locked login password, so any process running as `vscode` -- including an
# autonomous agent -- can become root with zero friction. This script, run
# once by a human in a real terminal, sets a login password you type (never
# stored in any image layer) and removes NOPASSWD so future `sudo` calls
# require that password.
#
# Caveat worth understanding: during container setup `vscode` keeps
# passwordless sudo because post-create.sh needs it. Anything running as
# `vscode` in that window can set the password and rewrite sudoers, so this
# cannot be cryptographically "human-only" -- it is "first to lock it wins."
# The mitigation is simply to run this yourself, early, right after setup.

set -euo pipefail

readonly USER_NAME="vscode"
readonly SUDOERS_FILE="/etc/sudoers.d/${USER_NAME}"
readonly STAGED_SUDOERS_FILE="${SUDOERS_FILE}.harden-sudo"
readonly LOCK_FILE="/tmp/${USER_NAME}-harden-sudo.lock"
readonly MIN_LEN=8

die() {
  echo "error: $*" >&2
  exit 1
}

# 1. Human-only: refuse to run without a terminal on both ends. This stops a
#    headless agent from driving the prompts.
if [ ! -t 0 ] || [ ! -t 1 ]; then
  die "this script must be run interactively in a terminal (a human types the password)"
fi

command -v flock >/dev/null || die "'flock' is required to serialize hardening attempts"
exec 9>"${LOCK_FILE}"
flock -n 9 || die "another sudo hardening attempt is already running"

# 2. Idempotency: if sudo already needs a password, there is nothing to do.
sudo -k
if ! sudo -n true 2>/dev/null; then
  echo "sudo is already password-gated for ${USER_NAME}; nothing to do."
  exit 0
fi

# Prepare and validate the sudoers change before touching the account password.
tmp="$(mktemp)"
original="$(mktemp)"
pw=""
password_changed=false
hardening_complete=false

restore_initial_state() {
  local restore_command
  restore_command='install -m 0440 -o root -g root "$1" "$4" && mv -f "$4" "$2" && passwd -l "$3"'

  if sudo -n sh -c "${restore_command}" sh \
    "${original}" "${SUDOERS_FILE}" "${USER_NAME}" \
    "${STAGED_SUDOERS_FILE}" >/dev/null 2>&1; then
    return
  fi
  if printf '%s\n' "${pw}" | sudo -S -p '' sh -c "${restore_command}" sh \
    "${original}" "${SUDOERS_FILE}" "${USER_NAME}" \
    "${STAGED_SUDOERS_FILE}" >/dev/null 2>&1; then
    return
  fi
  echo "warning: automatic rollback failed; rebuild the container before continuing" >&2
}

cleanup() {
  local status=$?
  trap - EXIT
  if [ "${password_changed}" = true ] && [ "${hardening_complete}" = false ]; then
    restore_initial_state
  fi
  rm -f "${tmp}" "${original}"
  exit "${status}"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

sudo cat "${SUDOERS_FILE}" > "${original}"
chmod 0600 "${original}"
printf '%s ALL=(root) ALL\n' "${USER_NAME}" > "${tmp}"
sudo visudo -cf "${tmp}" >/dev/null || die "generated sudoers rule failed validation"

echo "This will set a login password for '${USER_NAME}' and require it for sudo."
echo "The password is read from the terminal and never stored in any image."
echo

# 3. Prompt twice, confirm match, enforce a minimum length. Loop until valid.
while true; do
  read -rs -p "New sudo password: " pw1; echo
  read -rs -p "Retype password:   " pw2; echo
  if [ "${pw1}" != "${pw2}" ]; then
    echo "passwords do not match; try again." >&2
    continue
  fi
  if [ "${#pw1}" -lt "${MIN_LEN}" ]; then
    echo "password must be at least ${MIN_LEN} characters; try again." >&2
    continue
  fi
  pw="${pw1}"
  unset pw1 pw2
  break
done

# 4. Set the password via the still-present passwordless sudo. Feed it on
#    stdin so the secret never appears in argv / ps / shell history.
password_changed=true
printf '%s:%s\n' "${USER_NAME}" "${pw}" | sudo chpasswd

# 5. Drop NOPASSWD. The candidate was already validated before the password
#    changed; stage it beside the live rule for an atomic rename, then validate
#    the whole sudoers set.
sudo install -m 0440 -o root -g root "${tmp}" "${STAGED_SUDOERS_FILE}"
sudo mv -f "${STAGED_SUDOERS_FILE}" "${SUDOERS_FILE}"
sudo visudo -c >/dev/null || die "sudoers set is invalid after install (check ${SUDOERS_FILE})"

# 6. Verify the gate is actually closed, then report.
sudo -k
if sudo -n true 2>/dev/null; then
  die "sudo still works without a password -- lockdown did not take effect"
fi
if ! passwd -S "${USER_NAME}" | grep -q '^'"${USER_NAME}"' P '; then
  die "password is not in the expected (usable) state; check 'passwd -S ${USER_NAME}'"
fi

hardening_complete=true
unset pw

echo
echo "Done. 'sudo' now requires the password you just set."
echo "Note: until you ran this, sudo was passwordless. If an agent could have"
echo "run earlier in this container's life, treat that window as untrusted."
echo "To undo: run 'sudo visudo -f ${SUDOERS_FILE}', authenticate with the"
echo "current password, change the rule to '${USER_NAME} ALL=(root) NOPASSWD:ALL',"
echo "and save. After NOPASSWD is restored, optionally run 'sudo passwd -l ${USER_NAME}'."
