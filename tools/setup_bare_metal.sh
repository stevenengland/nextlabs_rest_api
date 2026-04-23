#!/usr/bin/env bash
# Bare-metal setup script for library development.
# Creates a virtual environment, installs the package in dev mode.
#
# Usage:
#   ./tools/setup_bare_metal.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_DIR="$PROJECT_DIR/.venv"

echo "=== Library dev setup ==="
echo "  Project  : $PROJECT_DIR"
echo "  Venv     : $VENV_DIR"
echo ""

# --- Virtual environment ------------------------------------------------------
if [ -d "$VENV_DIR" ]; then
    echo "[ok] Virtual environment already exists at $VENV_DIR"
else
    echo "[..] Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
    echo "[ok] Virtual environment created."
fi

# --- Install package ----------------------------------------------------------
echo "[..] Installing package in dev mode ..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements/dev.txt" \
    -c "$PROJECT_DIR/requirements/constraints.txt" --quiet
echo "[ok] Package installed."

# --- Pre-commit ---------------------------------------------------------------
"$VENV_DIR/bin/pre-commit" install
echo "[ok] Pre-commit hooks installed."

# --- Optional system tooling --------------------------------------------------
# ripgrep (`rg`) is recommended: it respects .gitignore and keeps agent
# code-search tool output small. Install via your platform's package manager:
#   Debian/Ubuntu : sudo apt-get install ripgrep
#   Fedora/RHEL   : sudo dnf install ripgrep
#   macOS         : brew install ripgrep
if ! command -v rg >/dev/null 2>&1; then
    echo "[warn] ripgrep (rg) not found. Install it to speed up agent/code search."
fi

# --- Summary ------------------------------------------------------------------
echo ""
echo "=== Setup complete ==="
echo ""
echo "Activate with:"
echo "  source $VENV_DIR/bin/activate"
echo ""
