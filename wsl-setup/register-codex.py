"""Register the WSL-hosted launcher in ~/.codex/config.toml (shared by Codex CLI and ChatGPT Desktop).

Windows-side replacement for src/local_workspace_mcp/client_setup.py (which imports fcntl and
insists the command be an executable file on this OS). Same guarantees: backup first, refuse to
touch a same-name entry that points elsewhere, verify every other setting survives round-trip.

    .venv\\Scripts\\python.exe wsl-setup\\register-codex.py --distro Ubuntu-24.04 \
        --launch /home/user/.local/state/local-workspace-mcp/launch.sh [--timeout 60] [--dry-run]
"""

import argparse
import json
import os
import secrets
import subprocess
import time
from pathlib import Path

import tomlkit

WSL = r"C:\Windows\System32\wsl.exe"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--distro", required=True)
    ap.add_argument("--launch", required=True, help="absolute Linux path of launch.sh inside the distro")
    ap.add_argument("--server-name", default="local-workspace")
    ap.add_argument("--timeout", type=int, default=60, help="startup_timeout_sec (cold WSL VM)")
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.launch.startswith("/"):
        raise SystemExit("--launch must be an absolute Linux path inside the distro.")
    # Same check client_setup.py does with os.access(X_OK), performed inside the distro.
    probe = subprocess.run([WSL, "-d", a.distro, "--exec", "/usr/bin/test", "-x", a.launch])
    if probe.returncode != 0:
        raise SystemExit(f"{a.launch} is not an executable file in distro {a.distro}; nothing written.")

    config = a.config or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    config = config.expanduser().resolve()
    original = config.read_bytes() if config.exists() else b""
    doc = tomlkit.parse(original.decode("utf-8"))
    servers = doc.get("mcp_servers")
    if servers is None:
        doc["mcp_servers"] = tomlkit.table()
        servers = doc["mcp_servers"]
    if not isinstance(servers, dict):
        raise SystemExit("mcp_servers must be a TOML table")
    if isinstance(servers, tomlkit.items.InlineTable):
        raise SystemExit("mcp_servers is an inline table; convert it to [mcp_servers.*] tables first.")

    args = ["-d", a.distro, "--exec", a.launch]
    before = doc.unwrap()
    target = None
    for name, entry in servers.items():
        if isinstance(entry, dict) and entry.get("command") == WSL and list(entry.get("args", [])) == args:
            target = name
            break
    if target is None:
        if a.server_name in servers:
            raise SystemExit(f"Server '{a.server_name}' already exists and points elsewhere; choose --server-name.")
        target = a.server_name
        entry = tomlkit.table()
        entry["command"] = tomlkit.string(WSL, literal=True)  # single-quoted: backslashes stay readable
        entry["args"] = args
        entry["startup_timeout_sec"] = a.timeout
        entry["enabled"] = True
        servers[target] = entry
    else:
        # Same launcher already registered (maybe under another name): only refresh the timeout.
        if servers[target].get("startup_timeout_sec") == a.timeout:
            print(json.dumps({"changed": False, "server_name": target, "config": str(config)}, ensure_ascii=False))
            return
        servers[target]["startup_timeout_sec"] = a.timeout
    encoded = tomlkit.dumps(doc).encode("utf-8")

    checked = tomlkit.parse(encoded.decode("utf-8")).unwrap()
    del checked["mcp_servers"][target]
    if "mcp_servers" not in before:
        del checked["mcp_servers"]
    elif target in before["mcp_servers"]:
        before["mcp_servers"].pop(target)
    if checked != before:
        raise SystemExit("Unrelated settings would change; refusing to write.")

    if a.dry_run:
        print(tomlkit.dumps(servers[target]))
        print(json.dumps({"dry_run": True, "config": str(config)}, ensure_ascii=False))
        return

    backup = None
    if original:
        backup = config.with_name(f"{config.name}.lwmcp-backup-{time.time_ns()}-{secrets.token_hex(3)}")
        backup.write_bytes(original)
    tmp = config.with_name(f".lwmcp-config-{secrets.token_hex(4)}.tmp")
    tmp.write_bytes(encoded)
    if (config.read_bytes() if config.exists() else b"") != original:
        tmp.unlink()
        raise SystemExit("config.toml changed while preparing the edit; rerun.")
    os.replace(tmp, config)
    print(json.dumps({"changed": True, "server_name": target, "config": str(config),
                      "backup": str(backup) if backup else None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
