"""Optional, intentionally read-only MCP connection probe.

Install with: pip install -e ".[mcp]"
LabVIEWMCP.exe must be obtained separately from its official release.
"""
from __future__ import annotations
from pathlib import Path

async def status(exe: Path) -> str:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    exe=exe.expanduser().resolve(strict=True)
    if not exe.is_file():
        raise FileNotFoundError(exe)
    params=StdioServerParameters(command=str(exe), args=[], env=None)
    async with stdio_client(params) as (reader,writer):
        async with ClientSession(reader,writer) as client:
            await client.initialize()
            result=await client.call_tool("lvai_status",arguments={})
            return str(result)
