r"""End-to-end acceptance of the run_python Docker worker through the real MCP bridge.

Spawns the same wsl.exe command the clients use, checks run_python is registered, then runs a
document job inside the disposable container: create XLSX + DOCX + a CJK-labelled PNG chart in
/output, re-open each file inside the container, and print verified numbers. Exit 0 only if all pass.

    .venv\Scripts\python.exe wsl-setup\verify-python.py --distro Ubuntu-24.04 \
        --launch /home/user/.local/state/local-workspace-mcp/launch.sh
"""

import argparse
import asyncio
import json
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

WSL = r"C:\Windows\System32\wsl.exe"

JOB = """
import pandas as pd
df = pd.DataFrame({"item": ["PC板", "直橫料", "燈具"], "qty": [12, 8, 20],
                   "amount": [36000, 52000, 15000]})
df.to_excel("/output/acceptance-report.xlsx", index=False)
back = pd.read_excel("/output/acceptance-report.xlsx")
print("XLSX_TOTAL", int(back["amount"].sum()))

from docx import Document
doc = Document()
doc.add_heading("local-workspace-mcp 驗收文件", 0)
doc.add_paragraph("中文內容測試：五金採買報表產線。總額 103,000 元。")
doc.save("/output/acceptance-doc.docx")
print("DOCX_PARAS", len(Document("/output/acceptance-doc.docx").paragraphs))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK TC", "Noto Sans CJK SC", "Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
fig, ax = plt.subplots(figsize=(5, 3))
ax.bar(df["item"], df["amount"])
ax.set_title("九月採買金額")
fig.savefig("/output/acceptance-chart.png", dpi=100, bbox_inches="tight")
import os
print("PNG_BYTES", os.path.getsize("/output/acceptance-chart.png"))
"""


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--distro", required=True)
    ap.add_argument("--launch", required=True)
    a = ap.parse_args()
    t0 = time.perf_counter()
    params = StdioServerParameters(command=WSL, args=["-d", a.distro, "--exec", a.launch])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            names = sorted(t.name for t in (await session.list_tools()).tools)
            if "run_python" not in names:
                print(json.dumps({"ok": False, "error": "run_python missing", "tools": len(names)}))
                return 1
            job = await session.call_tool("run_python", {"code": JOB})
            body = "".join(getattr(c, "text", "") for c in job.content)
            arts = await session.call_tool("list_artifacts", {})
            files = "".join(getattr(c, "text", "") for c in arts.content)
    result = {
        "ok": (not job.isError) and "XLSX_TOTAL 103000" in body and "DOCX_PARAS" in body
        and "PNG_BYTES" in body,
        "tools": len(names),
        "run_python_isError": job.isError,
        "run_python_output": body[:600],
        "artifacts": files[:400],
        "total_seconds": round(time.perf_counter() - t0, 1),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
