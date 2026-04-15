#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements/dev.txt
python -m pip install -e . --no-deps

# Ensure the workspace is a git repo before installing hooks
if [ ! -d .git ]; then
  git init
fi
python -m pre_commit install


.devcontainer/install-skills.sh
