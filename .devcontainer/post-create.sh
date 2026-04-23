#!/usr/bin/env bash
set -euo pipefail

# System packages that help agent tooling keep tool output small.
# ripgrep (rg) respects .gitignore by default; the `grep` tool in Copilot
# CLI / Claude Code uses it under the hood — installing it keeps `rg`
# available for direct shell use as well.
if ! command -v rg >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends ripgrep
fi

python -m pip install -r requirements/dev.txt
python -m pip install -e . --no-deps

# Ensure the workspace is a git repo before installing hooks
if [ ! -d .git ]; then
  git init
fi
python -m pre_commit install


.devcontainer/install-skills.sh
