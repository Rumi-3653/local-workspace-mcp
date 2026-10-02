#!/usr/bin/env bash
# probe.sh -- read-only baseline of the distro; run as root or user.
echo "--- os ---"; head -2 /etc/os-release
echo "--- wsl-distribution.conf ---"; cat /etc/wsl-distribution.conf 2>/dev/null || echo none
echo "--- wsl.conf ---"; cat /etc/wsl.conf 2>/dev/null || echo none
echo "--- id ---"; id
echo "--- users>=1000 ---"; getent passwd | awk -F: '$3>=1000 && $3<65534'
echo "--- python/node/rg/uv ---"; python3 --version 2>&1; node --version 2>&1 || echo no-node; rg --version 2>&1 | head -1 || true; (command -v uv && uv --version) 2>&1 || echo no-uv
echo "--- PATH ---"; echo "$PATH"
echo "--- fs ---"; df -T / /mnt/d 2>/dev/null | tail -2
echo "--- mounts drvfs ---"; grep -E ' /mnt/d ' /proc/mounts || true
echo PROBE_OK
