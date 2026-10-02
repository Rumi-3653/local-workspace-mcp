#!/usr/bin/env bash
# setup-user.sh -- run INSIDE the WSL Ubuntu distro as the target (non-root) user.
#   wsl.exe -d <Distro> -u <user> -- bash /mnt/d/local-workspace-mcp/wsl-setup/setup-user.sh [workspace-path]
# Mirrors scripts/install.py --mode full --skip-worker --no-register, adapted for Linux-under-WSL:
#   uv (user install) -> clone fork into $HOME -> uv sync -> npm ci -> patch_engine -> launch.sh
# Nothing here touches Windows-side client configs; registration is done from Windows afterwards.
set -euo pipefail

REPO_URL="https://github.com/Rumi-3653/local-workspace-mcp.git"
APP_DIR="$HOME/local-workspace-mcp"
STATE_DIR="$HOME/.local/state/local-workspace-mcp"
WORKSPACE="${1:-$HOME/workspace}"
case "$WORKSPACE$APP_DIR$STATE_DIR" in
  *"'"*) echo "paths must not contain a single quote (launch.sh quotes them literally)" >&2; exit 2 ;;
esac

echo "== uv =="
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
uv --version

echo "== checkout =="
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi
cd "$APP_DIR"

echo "== workspace / state =="
if [ ! -d "$WORKSPACE" ]; then
  mkdir -p "$WORKSPACE"
fi
# Literal prefix test (no glob interpretation of the workspace path).
if [ "${STATE_DIR#"$WORKSPACE"/}" != "$STATE_DIR" ] || [ "$STATE_DIR" = "$WORKSPACE" ]; then
  echo "state dir must be outside the workspace" >&2; exit 1
fi
mkdir -p "$STATE_DIR"
chmod 0700 "$STATE_DIR"

echo "== python deps (uv sync --frozen --no-dev) =="
uv sync --frozen --no-dev

echo "== node engine (npm ci --ignore-scripts) =="
npm ci --ignore-scripts --no-fund --no-audit
"$APP_DIR/.venv/bin/python" "$APP_DIR/scripts/patch_engine.py"

echo "== launcher =="
ENGINE_ENTRY="$APP_DIR/node_modules/@wonderwhy-er/desktop-commander/dist/index.js"
test -f "$ENGINE_ENTRY"
LAUNCH="$STATE_DIR/launch.sh"
if [ -f "$LAUNCH" ]; then
  cp -p "$LAUNCH" "$LAUNCH.backup-$(date +%s)"
fi
# Explicit PATH: wsl.exe --exec does not load a login shell, and we do not want /mnt/c entries.
SAFE_PATH="$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
{
  echo '#!/bin/sh'
  echo 'set -eu'
  echo "export PATH='$SAFE_PATH'"
  echo "export HOME='$HOME'"
  echo "export LANG='C.UTF-8'"
  echo "exec '$APP_DIR/.venv/bin/local-workspace-mcp' serve \\"
  echo "  --root '$WORKSPACE' --write \\"
  echo "  --host-engine '$ENGINE_ENTRY' \\"
  echo "  --engine-state '$STATE_DIR/engine' \"\$@\""
} > "$LAUNCH"
chmod 0700 "$LAUNCH"

echo "== smoke: server must start and answer an MCP initialize over stdio =="
"$APP_DIR/.venv/bin/python" - "$LAUNCH" <<'PY'
import asyncio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main(launch):
    params = StdioServerParameters(command=launch, args=[])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            names = sorted(t.name for t in tools)
            host = [n for n in names if n.startswith("host_")]
            print(f"tools={len(names)} host_tools={len(host)}")
            print("sample:", ", ".join(names[:8]))
            assert "list_directory" in names or any(n.endswith("list_directory") for n in names), names
            assert host, "engine tools missing -- patch_engine/npm ci problem"

asyncio.run(main(sys.argv[1]))
PY

echo "LAUNCH=$LAUNCH"
echo "WORKSPACE=$WORKSPACE"
echo "USER_SETUP_OK"
