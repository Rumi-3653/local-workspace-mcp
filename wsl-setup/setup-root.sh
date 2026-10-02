#!/usr/bin/env bash
# setup-root.sh -- run INSIDE the WSL Ubuntu distro as root.
#   wsl.exe -d <Distro> -u root -- bash /mnt/d/local-workspace-mcp/wsl-setup/setup-root.sh <username>
# Installs system prerequisites for local-workspace-mcp full mode (no Docker worker):
#   git, curl, ripgrep, python3 (>=3.12 on Ubuntu 24.04), Node.js 22 (NodeSource).
# Creates the non-root user if missing and makes it the default login user.
set -euo pipefail

TARGET_USER="${1:-}"
if [ -z "$TARGET_USER" ]; then
  echo "usage: setup-root.sh <username>" >&2
  exit 2
fi
NODE_MAJOR=22
export DEBIAN_FRONTEND=noninteractive

echo "== apt prerequisites =="
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git gnupg ripgrep sudo \
  python3 python3-venv

echo "== Node.js ${NODE_MAJOR}.x (NodeSource) =="
if ! command -v node >/dev/null 2>&1 || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
  chmod 0644 /etc/apt/keyrings/nodesource.gpg
  echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list
  apt-get update -y
  apt-get install -y nodejs
fi

echo "== user ${TARGET_USER} =="
if ! id -u "$TARGET_USER" >/dev/null 2>&1; then
  # No password: the account is only reachable through wsl.exe from this Windows login.
  adduser --uid 1000 --disabled-password --gecos "" "$TARGET_USER"
fi
# Deliberately NO sudo rights: the account has no password, so sudo is unusable from inside the
# distro (tool calls spawned by the MCP engine cannot escalate). Administration goes through
# `wsl.exe -d <Distro> -u root`, which the owning Windows login can always do anyway.
gpasswd -d "$TARGET_USER" sudo >/dev/null 2>&1 || true
rm -f "/etc/sudoers.d/90-${TARGET_USER}"

echo "== /etc/wsl.conf =="
# metadata: POSIX mode bits on /mnt/* files (state/workspace live on ext4 and do not need it; this
# only matters for files under /mnt/d that host_* tools may create or chmod).
# appendWindowsPath=false: keep Windows node.exe/npm.cmd/python.exe out of PATH inside the distro.
cat > /etc/wsl.conf <<'EOF'
[user]
default=__USER__

[boot]
systemd=false

[automount]
enabled=true
options="metadata,umask=022,fmask=011"

[interop]
enabled=true
appendWindowsPath=false
EOF
sed -i "s/__USER__/${TARGET_USER}/" /etc/wsl.conf

echo "== versions =="
python3 --version
node --version
npm --version
rg --version | head -1
git --version
echo "ROOT_SETUP_OK"
