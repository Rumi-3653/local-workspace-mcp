"""End-to-end probe of the Windows -> wsl.exe -> launch.sh MCP bridge.

Spawns exactly the command the clients will use, completes the MCP initialize handshake, lists
tools, calls list_directory on the workspace root, and reports timings. Exit 0 only if all pass.

    .venv\\Scripts\\python.exe wsl-setup\\bridge-test.py --distro Ubuntu-24.04 \
        --launch /home/user/.local/state/local-workspace-mcp/launch.sh [--concurrent 2]
"""

import argparse
import asyncio
import json
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

WSL = r"C:\Windows\System32\wsl.exe"


async def one(tag: str, distro: str, launch: str) -> dict:
    t0 = time.perf_counter()
    params = StdioServerParameters(command=WSL, args=["-d", distro, "--exec", launch])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            init = await session.initialize()
            t_init = time.perf_counter() - t0
            tools = (await session.list_tools()).tools
            names = sorted(t.name for t in tools)
            host = [n for n in names if n.startswith("host_")]
            listing = await session.call_tool("list_directory", {"path": "."})
            text = "".join(getattr(c, "text", "") for c in listing.content)[:400]
            return {
                "tag": tag,
                "server": f"{init.serverInfo.name} {init.serverInfo.version}",
                "init_seconds": round(t_init, 2),
                "total_seconds": round(time.perf_counter() - t0, 2),
                "tools": len(names),
                "host_tools": len(host),
                "sample": names[:6],
                "list_directory_ok": not listing.isError,
                "list_directory_head": text,
            }


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--distro", required=True)
    ap.add_argument("--launch", required=True)
    ap.add_argument("--concurrent", type=int, default=1)
    a = ap.parse_args()
    results = await asyncio.gather(
        *(one(f"client{i+1}", a.distro, a.launch) for i in range(a.concurrent)), return_exceptions=True
    )
    ok = True
    for r in results:
        if isinstance(r, BaseException):
            ok = False
            print(json.dumps({"error": repr(r)}, ensure_ascii=False))
        else:
            ok = ok and r["list_directory_ok"] and r["host_tools"] > 0
            print(json.dumps(r, ensure_ascii=False))
    print("BRIDGE_OK" if ok else "BRIDGE_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
