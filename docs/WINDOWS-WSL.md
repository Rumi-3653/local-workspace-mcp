# Windows through WSL2 (document mode)

This runs the Linux server inside WSL2; it does **not** add native Windows support.
Keep the repository, Python environment, private state and official Linux
tunnel-client in the Linux filesystem. A dedicated document workspace can live
under `/mnt/c/Users/YOUR_WINDOWS_USER/Documents/LocalWorkspace`.

## Prerequisites

- An installed WSL2 Ubuntu distribution (`wsl.exe --list --verbose`).
- Git, Python 3.12+, uv, and a working Docker CLI/daemon inside that distribution.
  Verify `docker info` as the same Linux user that will run MCP. Docker Desktop
  WSL integration and Docker inside WSL are alternatives; choose one working setup.
- The official Linux tunnel-client matching `uname -m`, downloaded from
  https://github.com/openai/tunnel-client/releases and verified against its SHA256.
- OpenAI tunnel/workspace access and a key restricted to Tunnels Read + Use.

Use a regular Linux user where possible. The existing installation tested below
was root-owned; other installations do not need to copy that choice. Full host
mode was not tested. This guide does not install WSL or Docker.

## Install and connect

In an interactive Ubuntu terminal, clone the repository into a permanent Linux
directory. From that directory, adapt these absolute paths to your Linux user:

```sh
python3 scripts/install.py \
  --workspace /mnt/c/Users/YOUR_WINDOWS_USER/Documents/LocalWorkspace \
  --state /home/YOUR_LINUX_USER/.local/state/local-workspace-mcp \
  --mode documents

.venv/bin/python scripts/connect_chatgpt.py --interactive --run \
  --state /home/YOUR_LINUX_USER/.local/state/local-workspace-mcp \
  --tunnel-client /home/YOUR_LINUX_USER/tools/tunnel-client/tunnel-client
```

Keep private state on the Linux filesystem, outside the document workspace, so
0700/0600 permissions are meaningful. Do not use Linux client registration to
configure a Windows client: that writes the Linux user's client configuration.

Follow [the ChatGPT account guide](CHATGPT.md) to create a tunnel associated with
the intended ChatGPT workspace and its restricted runtime key. Enter the tunnel
ID at the ID prompt. At the hidden key prompt, **paste once and press Enter**.
No visible characters is normal. Do not paste again just because nothing appears.
Run a launcher rather than editing its source: never paste a key into a `.cmd`,
PowerShell script, command argument, chat, screenshot or Git commit.

Keep Docker and the tunnel running. In another Ubuntu terminal:

```sh
/home/YOUR_LINUX_USER/tools/tunnel-client/tunnel-client health \
  --url-file /home/YOUR_LINUX_USER/.local/state/local-workspace-mcp/tunnel-health.url \
  --require-control-plane-poll
```

`doctor` validates configuration; it does not prove the key is accepted. Even
`/readyz` alone is insufficient. Require a successful authenticated control-plane
poll and a real ChatGPT tool call. Inspect error codes locally; do not publish
unredacted logs or credentials.

In ChatGPT, add a custom MCP server using **Tunnel**, the tunnel ID, and **no
additional authentication** (the private tunnel has its own access checks).
Connect the plugin and use it in an ordinary chat:

> Call get_workflow_instructions, then this plugin's run_python with
> print('WINDOWS_WSL_TUNNEL_OK'). Do not substitute built-in Python.
> Report actual stdout and exit_code.

Stop only your tunnel (Ctrl-C), start it again and repeat health and chat checks.
Do not shut down all WSL distributions for this test. Closing the terminal,
shutting down WSL, sleeping or turning off the PC can disconnect ChatGPT.
This recipe does not install a Windows login task or promise reboot persistence.

## Optional Windows STDIO client

Windows clients can launch the Linux MCP independently of the ChatGPT tunnel.
Adapt distro, Linux username and absolute launcher path:

```toml
[mcp_servers.local-workspace]
command = "wsl.exe"
args = ["-d", "Ubuntu", "-u", "YOUR_LINUX_USER", "--", "/home/YOUR_LINUX_USER/.local/state/local-workspace-mcp/launch.sh"]
```

Docker must already be ready in that distro. Preserve other client entries rather
than replacing the whole configuration file. Merely installing Docker Desktop
on Windows does not verify Docker access inside Ubuntu.

## Validation scope

On 2026-10-04 an existing Windows + WSL Ubuntu document-mode installation was
updated to `ba42837`. A Windows MCP client launched `wsl.exe`, discovered 14 tools
and successfully ran Docker Python. Official Linux tunnel-client v0.0.15 passed
health/ready and an authenticated control-plane poll. Ordinary ChatGPT web chat
used the document workflow and returned the Python marker with exit code 0.
After restarting only the tunnel process, a second ordinary ChatGPT Python call
returned a different marker with exit code 0 as well.

This was an existing-installation check, not a clean-machine installer test.
Native Windows, full host mode, ChatGPT desktop/mobile, Windows reboot/login
startup, and Docker Desktop WSL integration were not tested.
