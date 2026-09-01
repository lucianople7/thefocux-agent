#!/usr/bin/env bash
# THE FOCUX Agent — one-command installer (macOS / Linux)
# Run:  curl -fsSL https://raw.githubusercontent.com/lucianople7/thefocux-agent/main/install.sh | bash
set -euo pipefail

REPO_URL="https://github.com/lucianople7/thefocux-agent.git"
INSTALL_DIR="$HOME/thefocux-agent"

echo "=== THE FOCUX Agent installer ==="

command -v git >/dev/null || { echo "ERROR: git not found"; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 not found"; exit 1; }
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PYVER" < "3.11" ]]; then
  echo "ERROR: Python 3.11+ required (found $PYVER)"; exit 1
fi

if [ ! -d "$INSTALL_DIR" ]; then
  echo "Cloning THE FOCUX into $INSTALL_DIR ..."
  git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
else
  echo "Updating THE FOCUX ..."
  git -C "$INSTALL_DIR" pull --ff-only
fi

cd "$INSTALL_DIR"
echo "Installing package (pip install -e .) ..."
python3 -m pip install -e ".[dev]"

echo ""
echo "=== Installation complete ==="
echo "  focux skills                  # 57 skills"
echo "  focux agents                  # 11 business roles"
echo "  focux attach ./negocio --workspace mi-negocio   # brain for ANY agent"
echo "  focux absorb --query 'ai agent'                 # real data -> memory"
echo "  focux doctor                  # verify the brain"
echo "  focux install --mcp           # global launchers + user-level MCP"
echo "  focux repl                    # interactive session"
echo "  focux-web --port 47822        # web console: http://127.0.0.1:47822"
echo ""
echo "Configure your provider: copy $INSTALL_DIR/.env.example to .env and add your API key."
