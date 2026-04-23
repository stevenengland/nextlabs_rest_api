#!/usr/bin/env bash
# ── Project Template Init Script ──
# Run once after cloning the template repo. Replaces placeholder names,
# configures platform-specific tooling, and prints a review checklist.
#
# Usage (interactive):
#   ./tools/init_project.sh
#
# Usage (non-interactive / scriptable):
#   Set INIT_NONINTERACTIVE=1 and pre-set variables via environment:
#
#   INIT_NONINTERACTIVE=1 \
#   PROJECT_SLUG=smartbroker_b2b \
#   DESCRIPTION="Python client library" \
#   PYTHON_VERSION=3.12 \
#   GIT_PLATFORM=github \
#   PROJECT_TYPE=library \
#   COV_THRESHOLD=90 \
#   MAX_COMPLEXITY=10 \
#   MAX_COGNITIVE=12 \
#   AUTHOR_NAME="Jane Doe" \
#   AUTHOR_EMAIL="jane@example.com" \
#   LICENSE_TYPE=MIT \
#   EXT_MERMAID=true \
#   REPO_URL=https://github.com/user/repo \
#   REMOVE_SELF=Y \
#   ./tools/init_project.sh
#
# Any variable already set in the environment is used as-is (no prompt).
# In non-interactive mode, unset variables use their defaults.
#
# This script will self-delete after successful execution (unless declined).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

NONINTERACTIVE="${INIT_NONINTERACTIVE:-}"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_step() { echo -e "${CYAN}  ✓${NC} $1"; }
print_warn() { echo -e "${YELLOW}  !${NC} $1"; }

# ── Helpers ──
# ask PROMPT DEFAULT VARNAME
# If VARNAME is already set in the environment, skip the prompt.
# In non-interactive mode, use the default for unset variables.
ask() {
    local prompt="$1" default="$2" varname="$3"
    # If variable is already set in environment, keep it
    if [ -n "${!varname+x}" ] && [ -n "${!varname}" ]; then
        return
    fi
    if [ -n "$NONINTERACTIVE" ]; then
        eval "$varname=\"$default\""
        return
    fi
    if [ -n "$default" ]; then
        read -rp "$prompt [$default]: " input
        eval "$varname=\"\${input:-$default}\""
    else
        read -rp "$prompt: " input
        eval "$varname=\"$input\""
    fi
}

# ask_yn PROMPT DEFAULT VARNAME
# Same env-override / non-interactive logic. Values: true/false.
ask_yn() {
    local prompt="$1" default="$2" varname="$3"
    if [ -n "${!varname+x}" ] && [ -n "${!varname}" ]; then
        return
    fi
    if [ -n "$NONINTERACTIVE" ]; then
        if [[ "$default" =~ ^[Yy] ]]; then
            eval "$varname=true"
        else
            eval "$varname=false"
        fi
        return
    fi
    read -rp "$prompt [$default]: " input
    input="${input:-$default}"
    if [[ "$input" =~ ^[Yy] ]]; then
        eval "$varname=true"
    else
        eval "$varname=false"
    fi
}

# ── Gather Inputs ──
echo ""
echo -e "${GREEN}=== Python Project Template Setup ===${NC}"
if [ -n "$NONINTERACTIVE" ]; then
    echo -e "  (non-interactive mode)"
fi
echo ""

ask "Project name (snake_case, e.g. my_cool_tool)" "my_project" PROJECT_SLUG
ask "Description" "" DESCRIPTION
ask "Python version" "3.12" PYTHON_VERSION
ask "Git platform (gitlab/github)" "gitlab" GIT_PLATFORM
ask "Project type (library/library+cli)" "library" PROJECT_TYPE
ask "Coverage threshold (%)" "90" COV_THRESHOLD
ask "Max McCabe complexity (wemake default: 10)" "10" MAX_COMPLEXITY
ask "Max cognitive complexity (wemake default: 12)" "12" MAX_COGNITIVE

echo ""
echo "PyPI publishing:"
ask "Author name" "" AUTHOR_NAME
ask "Author email" "" AUTHOR_EMAIL
ask "License (MIT/Apache-2.0)" "MIT" LICENSE_TYPE

echo ""
echo "Optional VS Code extensions:"
ask_yn "  Mermaid chart (mermaidchart.vscode-mermaid-chart)?" "y" EXT_MERMAID

if [ "$PROJECT_TYPE" = "library+cli" ]; then
    echo ""
    echo "Data directories to create:"
    ask_yn "  data/config/?" "y" DIR_CONFIG
    ask_yn "  data/secrets/?" "y" DIR_SECRETS
    ask_yn "  data/logs/?" "n" DIR_LOGS
else
    DIR_CONFIG=false
    DIR_SECRETS=false
    DIR_LOGS=false
fi

# ── Derive values ──
# Hyphenated form for pyproject.toml name, Docker image, CLI entry point
PROJECT_HYPHEN="${PROJECT_SLUG//_/-}"
# Python min version floor (e.g., 3.12 → >=3.12)
PYTHON_FLOOR=">=${PYTHON_VERSION}"

# ── Detect repository URL ──
if [ -z "${REPO_URL:-}" ]; then
    REPO_URL=""
    if git -C "$PROJECT_DIR" remote get-url origin &>/dev/null; then
        REPO_URL="$(git -C "$PROJECT_DIR" remote get-url origin)"
        # Normalize SSH URLs to HTTPS
        REPO_URL="${REPO_URL/git@github.com:/https://github.com/}"
        REPO_URL="${REPO_URL/git@gitlab.com:/https://gitlab.com/}"
        REPO_URL="${REPO_URL%.git}"
    fi
fi
if [ -z "$REPO_URL" ]; then
    ask "Repository URL (e.g. https://github.com/user/repo)" "" REPO_URL
fi

echo ""
echo -e "${GREEN}=== Patching files ===${NC}"
echo ""

# ── File patching helper ──
# Replaces all occurrences of a pattern in a file.
patch_file() {
    local file="$1" old="$2" new="$3"
    if [ -f "$file" ]; then
        sed -i "s|${old}|${new}|g" "$file"
    fi
}

# ── Rename source directory ──
if [ "$PROJECT_SLUG" != "my_project" ] && [ -d "$PROJECT_DIR/src/my_project" ]; then
    mv "$PROJECT_DIR/src/my_project" "$PROJECT_DIR/src/$PROJECT_SLUG"
    print_step "src/my_project/ → src/$PROJECT_SLUG/"
fi

# ── Patch all template files ──
FILES_TO_PATCH=(
    "pyproject.toml"
    "setup.cfg"
    "README.md"
    "CLAUDE.md"
    ".env.example"
    "docker/Dockerfile"
    "docker/compose.yaml"
    "tools/build_docker_container.sh"
    ".vscode/settings.json"
    ".vscode/launch.json"
    ".devcontainer/devcontainer.json"
    ".devcontainer/Dockerfile"
    ".devcontainer/post-create.sh"
    ".dockerignore"
    ".gitignore"
    "docs/development.md"
    "tests/conftest.py"
    "tests/e2e/conftest.py"
)

for relpath in "${FILES_TO_PATCH[@]}"; do
    filepath="$PROJECT_DIR/$relpath"
    if [ -f "$filepath" ]; then
        # Replace slug (underscore form) — used in Python imports, dir names
        patch_file "$filepath" "my_project" "$PROJECT_SLUG"
        # Replace hyphenated form — used in pyproject name, Docker tags, CLI
        patch_file "$filepath" "my-project" "$PROJECT_HYPHEN"
        print_step "$relpath"
    fi
done

# ── Update __main__.py after rename ──
MAIN_PY="$PROJECT_DIR/src/$PROJECT_SLUG/__main__.py"
if [ -f "$MAIN_PY" ]; then
    patch_file "$MAIN_PY" "my_project" "$PROJECT_SLUG"
    patch_file "$MAIN_PY" "my-project" "$PROJECT_HYPHEN"
    print_step "src/$PROJECT_SLUG/__main__.py"
fi

# ── Update __init__.py after rename ──
INIT_PY="$PROJECT_DIR/src/$PROJECT_SLUG/__init__.py"
if [ -f "$INIT_PY" ]; then
    patch_file "$INIT_PY" "my_project" "$PROJECT_SLUG"
    patch_file "$INIT_PY" "my-project" "$PROJECT_HYPHEN"
    print_step "src/$PROJECT_SLUG/__init__.py"
fi

# ── Python version patches ──
if [ "$PYTHON_VERSION" != "3.12" ]; then
    # Devcontainer Dockerfile
    patch_file "$PROJECT_DIR/.devcontainer/Dockerfile" \
        "python:3.12-bookworm" "python:${PYTHON_VERSION}-bookworm"
    # Production Dockerfile
    patch_file "$PROJECT_DIR/docker/Dockerfile" \
        "python:3.12-slim" "python:${PYTHON_VERSION}-slim"
    # pyproject.toml
    patch_file "$PROJECT_DIR/pyproject.toml" \
        '>=3.11' "$PYTHON_FLOOR"
    print_step "Python version → $PYTHON_VERSION"
fi

# ── Description ──
if [ -n "$DESCRIPTION" ]; then
    sed -i "s|^description = \"\"$|description = \"${DESCRIPTION}\"|" "$PROJECT_DIR/pyproject.toml"
    # Docker label (only if file exists)
    if [ -f "$PROJECT_DIR/docker/Dockerfile" ]; then
        sed -i "s|org.opencontainers.image.description=\"\"|org.opencontainers.image.description=\"${DESCRIPTION}\"|" \
            "$PROJECT_DIR/docker/Dockerfile"
    fi
    print_step "Description set"
fi

# ── Project type ──
if [ "$PROJECT_TYPE" = "library" ]; then
    # Delete __main__.py — pure library, no CLI
    rm -f "$PROJECT_DIR/src/$PROJECT_SLUG/__main__.py"
    print_step "__main__.py removed (library mode)"

    # Remove the CLI scripts block from pyproject.toml
    sed -i '/# ── Uncomment if building a CLI ──/d' "$PROJECT_DIR/pyproject.toml"
    sed -i '/# \[project\.scripts\]/d' "$PROJECT_DIR/pyproject.toml"
    sed -i "/# ${PROJECT_HYPHEN} = /d" "$PROJECT_DIR/pyproject.toml"
    print_step "[project.scripts] removed (library mode)"

    # Create py.typed marker
    touch "$PROJECT_DIR/src/$PROJECT_SLUG/py.typed"
    # Enable package-data in pyproject.toml
    sed -i "s|# \[tool.setuptools.package-data\]|[tool.setuptools.package-data]|" "$PROJECT_DIR/pyproject.toml"
    sed -i "s|# ${PROJECT_SLUG} = \[\"py.typed\"\]|${PROJECT_SLUG} = [\"py.typed\"]|" "$PROJECT_DIR/pyproject.toml"
    print_step "py.typed marker + package-data enabled"

    # Delete Docker files — libraries don't need containers
    rm -rf "$PROJECT_DIR/docker"
    rm -f "$PROJECT_DIR/tools/build_docker_container.sh"
    rm -f "$PROJECT_DIR/.dockerignore"
    print_step "Docker files removed (library mode)"

    # Delete .env.example — libraries don't own runtime config
    rm -f "$PROJECT_DIR/.env.example"
    sed -i '/^\.env$/d' "$PROJECT_DIR/.gitignore"
    sed -i '/envFile/d' "$PROJECT_DIR/.vscode/launch.json"
    print_step ".env references removed (library mode)"

    # Delete data/ directory — libraries don't own runtime data
    rm -rf "$PROJECT_DIR/data"
    print_step "data/ directory removed (library mode)"

    # Replace README.md with library-focused scaffold
    YEAR="$(date +%Y)"
    cat > "$PROJECT_DIR/README.md" << LIBREADME
# ${PROJECT_HYPHEN}

${DESCRIPTION}

## Installation

\`\`\`bash
pip install ${PROJECT_HYPHEN}
\`\`\`

## Quick Start

\`\`\`python
import ${PROJECT_SLUG}

# TODO: Add usage example
\`\`\`

## Development

See [docs/development.md](docs/development.md) for the full development guide.

## License

${LICENSE_TYPE} — see [LICENSE](LICENSE) for details.
LIBREADME
    print_step "README.md replaced with library scaffold"
else
    # Enable the CLI scripts block in pyproject.toml
    sed -i '/# ── Uncomment if building a CLI ──/d' "$PROJECT_DIR/pyproject.toml"
    sed -i "s|# \[project\.scripts\]|[project.scripts]|" "$PROJECT_DIR/pyproject.toml"
    sed -i "s|# ${PROJECT_HYPHEN} = \"${PROJECT_SLUG}.cli:app\"|${PROJECT_HYPHEN} = \"${PROJECT_SLUG}.cli:app\"|" "$PROJECT_DIR/pyproject.toml"
    print_step "[project.scripts] enabled (CLI mode)"
    print_step "Project type → library+cli (CLI files kept)"
fi

# ── PyPI metadata ──
# License
if [ "$LICENSE_TYPE" = "Apache-2.0" ]; then
    sed -i "s|# license = {text = \"MIT\"}|license = {text = \"Apache-2.0\"}|" "$PROJECT_DIR/pyproject.toml"
else
    sed -i "s|# license = {text = \"MIT\"}|license = {text = \"MIT\"}|" "$PROJECT_DIR/pyproject.toml"
fi
print_step "License → $LICENSE_TYPE"

# Create LICENSE file
YEAR="$(date +%Y)"
if [ "$LICENSE_TYPE" = "Apache-2.0" ]; then
    cat > "$PROJECT_DIR/LICENSE" << 'APACHELICENSE'
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
APACHELICENSE
else
    cat > "$PROJECT_DIR/LICENSE" << MITLICENSE
MIT License

Copyright (c) ${YEAR} ${AUTHOR_NAME}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
MITLICENSE
fi
print_step "LICENSE file created"

# Author + readme + urls
sed -i "s|# readme = \"README.md\"|readme = \"README.md\"|" "$PROJECT_DIR/pyproject.toml"
if [ -n "$AUTHOR_NAME" ] && [ -n "$AUTHOR_EMAIL" ]; then
    sed -i "/^readme = \"README.md\"/a authors = [{name = \"${AUTHOR_NAME}\", email = \"${AUTHOR_EMAIL}\"}]" \
        "$PROJECT_DIR/pyproject.toml"
    print_step "Author metadata set"
fi

# URLs
if [ -n "$REPO_URL" ]; then
    sed -i "s|# \[project.urls\]|[project.urls]|" "$PROJECT_DIR/pyproject.toml"
    sed -i "s|# Homepage = \"https://github.com/OWNER/${PROJECT_HYPHEN}\"|Homepage = \"${REPO_URL}\"|" \
        "$PROJECT_DIR/pyproject.toml"
    sed -i "s|# Repository = \"https://github.com/OWNER/${PROJECT_HYPHEN}\"|Repository = \"${REPO_URL}\"|" \
        "$PROJECT_DIR/pyproject.toml"
    sed -i "s|# \"Bug Tracker\" = \"https://github.com/OWNER/${PROJECT_HYPHEN}/issues\"|\"Bug Tracker\" = \"${REPO_URL}/issues\"|" \
        "$PROJECT_DIR/pyproject.toml"
    print_step "Project URLs set"
fi

# Enable bump-my-version config
sed -i "s|# \[tool.bumpversion\]|[tool.bumpversion]|" "$PROJECT_DIR/pyproject.toml"
sed -i "s|# current_version = \"0.1.0\"|current_version = \"0.1.0\"|" "$PROJECT_DIR/pyproject.toml"
sed -i "s|# commit = true|commit = true|" "$PROJECT_DIR/pyproject.toml"
sed -i "s|# tag = true|tag = true|" "$PROJECT_DIR/pyproject.toml"
sed -i 's|# tag_name = "v{new_version}"|tag_name = "v{new_version}"|' "$PROJECT_DIR/pyproject.toml"
sed -i "s|# \[\[tool.bumpversion.files\]\]|[[tool.bumpversion.files]]|" "$PROJECT_DIR/pyproject.toml"
sed -i "s|# filename = \"version.txt\"|filename = \"version.txt\"|" "$PROJECT_DIR/pyproject.toml"
print_step "bump-my-version config enabled"

# ── Coverage threshold ──
if [ "$COV_THRESHOLD" != "90" ]; then
    patch_file "$PROJECT_DIR/setup.cfg" \
        "--cov-fail-under=90" "--cov-fail-under=$COV_THRESHOLD"
    print_step "Coverage threshold → ${COV_THRESHOLD}%"
fi

# ── Complexity limits ──
if [ "$MAX_COMPLEXITY" != "10" ]; then
    sed -i "s|^max-complexity = 10$|max-complexity = $MAX_COMPLEXITY|" "$PROJECT_DIR/setup.cfg"
    print_step "Max McCabe complexity → $MAX_COMPLEXITY"
fi
if [ "$MAX_COGNITIVE" != "12" ]; then
    sed -i "s|^max-cognitive-complexity = 12$|max-cognitive-complexity = $MAX_COGNITIVE|" "$PROJECT_DIR/setup.cfg"
    print_step "Max cognitive complexity → $MAX_COGNITIVE"
fi

# ── Git platform ──
if [ "$GIT_PLATFORM" = "github" ]; then
    # Swap extension in devcontainer.json
    sed -i '/"gitlab.gitlab-workflow"/d' "$PROJECT_DIR/.devcontainer/devcontainer.json"
    sed -i '/\/\/ GitLab:/d' "$PROJECT_DIR/.devcontainer/devcontainer.json"
    sed -i 's|// "github.vscode-pull-request-github"|"github.vscode-pull-request-github"|' \
        "$PROJECT_DIR/.devcontainer/devcontainer.json"
    sed -i '/\/\/ GitHub:/d' "$PROJECT_DIR/.devcontainer/devcontainer.json"
    sed -i '/\/\/ ── Platform-specific/d' "$PROJECT_DIR/.devcontainer/devcontainer.json"

    # Remove glab install from post-create
    sed -i '/# ── Platform-specific/d' "$PROJECT_DIR/.devcontainer/post-create.sh"
    sed -i '/# GitLab:/d' "$PROJECT_DIR/.devcontainer/post-create.sh"
    sed -i '/install-glab.sh/d' "$PROJECT_DIR/.devcontainer/post-create.sh"
    sed -i '/# GitHub: gh is installed/d' "$PROJECT_DIR/.devcontainer/post-create.sh"
    rm -f "$PROJECT_DIR/.devcontainer/install-glab.sh"

    # Swap CLI reference in CLAUDE.md
    sed -i 's|glab.*# GitLab CLI (or: gh for GitHub)|gh                                    # GitHub CLI|' \
        "$PROJECT_DIR/CLAUDE.md"
    sed -i 's|glab.*# GitLab CLI (or: gh for GitHub)|gh                                    # GitHub CLI|' \
        "$PROJECT_DIR/README.md"

    # Swap auto-approve in settings.json
    sed -i 's|"glab": true|"gh": true|' "$PROJECT_DIR/.vscode/settings.json"

    print_step "Git platform → GitHub"
else
    # Remove the commented GitHub extension line
    sed -i '/github.vscode-pull-request-github/d' "$PROJECT_DIR/.devcontainer/devcontainer.json"
    sed -i '/\/\/ GitHub:/d' "$PROJECT_DIR/.devcontainer/devcontainer.json"
    sed -i '/\/\/ GitLab:/d' "$PROJECT_DIR/.devcontainer/devcontainer.json"
    sed -i '/\/\/ ── Platform-specific/d' "$PROJECT_DIR/.devcontainer/devcontainer.json"

    # Clean up post-create comments
    sed -i '/# ── Platform-specific/d' "$PROJECT_DIR/.devcontainer/post-create.sh"
    sed -i '/# GitHub: gh is installed/d' "$PROJECT_DIR/.devcontainer/post-create.sh"
    sed -i '/# GitLab:/d' "$PROJECT_DIR/.devcontainer/post-create.sh"

    # Simplify CLI reference in CLAUDE.md / README.md
    sed -i 's|glab.*# GitLab CLI (or: gh for GitHub)|glab                                  # GitLab CLI|' \
        "$PROJECT_DIR/CLAUDE.md"
    sed -i 's|glab.*# GitLab CLI (or: gh for GitHub)|glab                                  # GitLab CLI|' \
        "$PROJECT_DIR/README.md"

    print_step "Git platform → GitLab"
fi

# ── Optional extensions ──
if [ "$EXT_MERMAID" = "true" ]; then
    sed -i 's|// "mermaidchart.vscode-mermaid-chart"|"mermaidchart.vscode-mermaid-chart"|' \
        "$PROJECT_DIR/.devcontainer/devcontainer.json"
    print_step "Extension: Mermaid chart → enabled"
fi

# ── Data directories ──
if [ "$DIR_CONFIG" = "true" ]; then
    mkdir -p "$PROJECT_DIR/data/config"
    touch "$PROJECT_DIR/data/config/.gitkeep"
    print_step "data/config/ created"
else
    rm -rf "$PROJECT_DIR/data/config"
fi

if [ "$DIR_SECRETS" = "true" ]; then
    mkdir -p "$PROJECT_DIR/data/secrets"
    touch "$PROJECT_DIR/data/secrets/.gitkeep"
    print_step "data/secrets/ created"
else
    rm -rf "$PROJECT_DIR/data/secrets"
fi

if [ "$DIR_LOGS" = "true" ]; then
    mkdir -p "$PROJECT_DIR/data/logs"
    touch "$PROJECT_DIR/data/logs/.gitkeep"
    print_step "data/logs/ created"
fi

# Remove data/ entirely if nothing was selected
if [ "$DIR_CONFIG" = "false" ] && [ "$DIR_SECRETS" = "false" ] && [ "$DIR_LOGS" = "false" ]; then
    rm -rf "$PROJECT_DIR/data"
    print_warn "data/ directory removed (nothing selected)"
fi

# ── Recreate AGENTS.md symlink (in case CLAUDE.md was patched) ──
rm -f "$PROJECT_DIR/AGENTS.md"
ln -sf CLAUDE.md "$PROJECT_DIR/AGENTS.md"
print_step "AGENTS.md → CLAUDE.md (symlink)"

# ── Checklist ──
echo ""
echo -e "${GREEN}=== Review these files ===${NC}"
echo ""
echo "  [ ] CLAUDE.md           — Fill in Project Intention, Audience, Scope"
echo "  [ ] pyproject.toml      — Add dependencies; review classifiers and keywords"
echo "  [ ] setup.cfg           — Add per-file-ignores for your module names as needed"
echo "  [ ]                     — Uncomment Pydantic mypy plugin if using Pydantic"
if [ "$PROJECT_TYPE" = "library+cli" ]; then
    echo "  [ ] docker/Dockerfile   — Uncomment your entrypoint pattern (CLI / service / script)"
    echo "  [ ] docker/compose.yaml — Uncomment volume mounts and command"
fi
echo "  [ ] .vscode/launch.json — Uncomment/add debug configurations"
echo "  [ ] requirements/constraints.txt — Pin versions for your runtime dependencies"
echo ""

# ── Self-delete ──
if [ -n "$NONINTERACTIVE" ]; then
    REMOVE_SELF="${REMOVE_SELF:-Y}"
else
    read -rp "Remove this init script? [Y/n]: " REMOVE_SELF
    REMOVE_SELF="${REMOVE_SELF:-Y}"
fi
if [[ "$REMOVE_SELF" =~ ^[Yy] ]]; then
    rm -f "$0"
    print_step "Init script removed"
fi

echo ""
echo -e "${GREEN}=== Next steps ===${NC}"
echo ""
echo "  Authenticate your CLI tools:"
echo ""
echo "    # GitLab"
echo "    glab auth login"
echo ""
echo "    # GitHub"
echo "    gh auth login"
echo ""
echo -e "${GREEN}=== Done. Happy coding! ===${NC}"
echo ""
