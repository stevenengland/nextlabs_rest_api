#!/usr/bin/env bash
# Deterministic stand-in for the `nextlabs` CLI used only when generating
# the README demo cast (docs/cast/demo.svg). NEVER use this in production
# or tests — see docs/cast/README.md.
#
# It pattern-matches a small whitelist of arguments and prints pre-baked
# Rich-styled output that matches what the real CLI would emit.

set -e

cyan=$'\033[36m'; green=$'\033[32m'; yellow=$'\033[33m'; red=$'\033[31m'
bold=$'\033[1m'; dim=$'\033[2m'; reset=$'\033[0m'
gray=$'\033[90m'

case "$*" in
  "auth login")
    sleep 0.2
    echo "${green}✓${reset} Logged in as ${bold}admin@cloudaz.example.com${reset}"
    echo "  ${dim}Token cached in ~/.cache/nextlabs-sdk/tokens.json (expires in 1h)${reset}"
    ;;

  "policies search"*)
    sleep 0.3
    cat <<EOF
${gray}┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓${reset}
${gray}┃${reset} ${bold}ID${reset}   ${gray}┃${reset} ${bold}Name${reset}                         ${gray}┃${reset} ${bold}Status${reset}   ${gray}┃${reset} ${bold}Effect${reset} ${gray}┃${reset}
${gray}┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩${reset}
${gray}│${reset} 17   ${gray}│${reset} engineers-can-read-internal ${gray}│${reset} ${green}APPROVED${reset} ${gray}│${reset} ${green}ALLOW${reset}  ${gray}│${reset}
${gray}│${reset} 18   ${gray}│${reset} deny-public-pii             ${gray}│${reset} ${green}APPROVED${reset} ${gray}│${reset} ${red}DENY${reset}   ${gray}│${reset}
${gray}│${reset} 23   ${gray}│${reset} contractors-readonly        ${gray}│${reset} ${yellow}DRAFT${reset}    ${gray}│${reset} ${green}ALLOW${reset}  ${gray}│${reset}
${gray}└──────┴────────────────────────────┴──────────┴────────┘${reset}
EOF
    ;;

  "pdp eval"*)
    sleep 0.3
    cat <<EOF
${cyan}Decision${reset}    ${green}${bold}Permit${reset}
${cyan}Status${reset}      ok
${cyan}Matched${reset}     policy-17 (engineers-can-read-internal)
EOF
    ;;

  *)
    echo "${red}fake-nextlabs: unknown stub args:${reset} $*" >&2
    exit 64
    ;;
esac
