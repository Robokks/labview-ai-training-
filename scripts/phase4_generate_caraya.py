"""Inspect LabVIEW MCP v2.4.1 and optionally generate Phase 4 Caraya tests.

Requires: pip install mcp
Usage:
  python -m scripts.phase4_generate_caraya
  python -m scripts.phase4_generate_caraya --generate
"""
import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MCP_EXE = Path(r"C:\LabVIEWTools\labview-mcp-v2.4.1\bin\LabVIEWMCP.exe")
SUBJECT = Path(r"D:\Phase4\NativeVerification\F to C (SUB VI).vi")
TEST_FILE = Path(r"D:\Phase4\NativeVerification\Tests\Test F to C.vi")

CASES = [
    {"label": "True freezing", "inputs": {"Farenheit": "32", "Boolean": "true"}, "expect": {"Celcius": "0"}},
    {"label": "True boiling", "inputs": {"Farenheit": "212", "Boolean": "true"}, "expect": {"Celcius": "100"}},
    {"label": "True minus forty", "inputs": {"Farenheit": "-40", "Boolean": "true"}, "expect": {"Celcius": "-40"}},
    {"label": "True fifty", "inputs": {"Farenheit": "50", "Boolean": "true"}, "expect": {"Celcius": "10"}},
    {"label": "False freezing", "inputs": {"Farenheit": "32", "Boolean": "false"}, "expect": {"Celcius": "32"}},
    {"label": "False boiling", "inputs": {"Farenheit": "212", "Boolean": "false"}, "expect": {"Celcius": "212"}},
    {"label": "False minus forty", "inputs": {"Farenheit": "-40", "Boolean": "false"}, "expect": {"Celcius": "-40"}},
    {"label": "False passthrough", "inputs": {"Farenheit": "98.6", "Boolean": "false"}, "expect": {"Celcius": "98.6"}},
]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Create the native Caraya test VI")
    args = parser.parse_args()

    if not MCP_EXE.is_file():
        raise SystemExit(f"MCP executable missing: {MCP_EXE}")
    if not SUBJECT.is_file():
        raise SystemExit(f"Scratch VI missing: {SUBJECT}")
    if args.generate and TEST_FILE.exists():
        raise SystemExit(f"Refusing to overwrite existing test: {TEST_FILE}")

    server = StdioServerParameters(command=str(MCP_EXE), args=["--aixml-backend", "grpc"])
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as client:
            await client.initialize()
            listing = await client.list_tools()
            tools = {tool.name: tool for tool in listing.tools}
            print(f"MCP connected; {len(tools)} tools advertised")
            for name in ("lvai_status", "lvai_generate_test", "lvai_run_vi_as_top_level"):
                print(f"  {name}: {'AVAILABLE' if name in tools else 'MISSING'}")
            if "lvai_generate_test" not in tools:
                raise SystemExit("Required test generator not advertised by this build")
            if not args.generate:
                print("Inspection only. No VI was created or executed.")
                print("To generate: python -m scripts.phase4_generate_caraya --generate")
                return
            TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "viPath": str(SUBJECT),
                "casesJson": json.dumps(CASES),
                "testViPath": str(TEST_FILE),
                "directCall": True,
                "timeoutSeconds": 120,
                "backend": "grpc",
                "measureDiagram": True,
            }
            print("Requesting generation of Caraya test VI (not executing it)...", flush=True)
            result = await client.call_tool("lvai_generate_test", arguments=payload, read_timeout_seconds=600)
            for part in result.content:
                if getattr(part, "text", None):
                    print(part.text)
            print(f"MCP tool error: {bool(result.isError)}")
            print(f"Test VI exists: {TEST_FILE.is_file()}")
            print("Review generator report and inspect generated VI before execution.")
            if result.isError:
                raise SystemExit("MCP reported an error; do not run the test VI.")


if __name__ == "__main__":
    asyncio.run(main())
