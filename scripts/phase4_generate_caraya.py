"""Inspect LabVIEW MCP v2.4.1 and optionally generate Phase 4 Caraya tests.

Requires: pip install mcp
Usage:
  python -m scripts.phase4_generate_caraya
  python -m scripts.phase4_generate_caraya --generate
"""
import argparse
import asyncio
import json
import subprocess
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
    parser.add_argument("--diagnose", action="store_true", help="Check bundled pylabview provisioning without generating")
    parser.add_argument("--project", type=Path, help="Existing .lvproj that lists the subject (direct generator route)")
    parser.add_argument("--subject", type=Path, default=SUBJECT)
    parser.add_argument("--test-file", type=Path, default=TEST_FILE)
    parser.add_argument("--cases-json", type=Path)
    args = parser.parse_args()

    if not MCP_EXE.is_file():
        raise SystemExit(f"MCP executable missing: {MCP_EXE}")
    if args.diagnose:
        check = subprocess.run([str(MCP_EXE), "--pylv-status"], check=False)
        return check.returncode
    if args.project and not args.project.is_file():
        raise SystemExit(f"Project missing: {args.project}")
    subject = args.subject.resolve()
    test_file = args.test_file.resolve()
    cases = CASES
    if args.cases_json:
        cases = json.loads(args.cases_json.read_text(encoding="utf-8-sig"))
        if (not isinstance(cases, list) or not 1 <= len(cases) <= 20
                or any(not isinstance(x, dict) or not isinstance(x.get("label"), str)
                       or not isinstance(x.get("inputs"), dict)
                       or not isinstance(x.get("expect"), dict)
                       or not x["inputs"] or not x["expect"] for x in cases)):
            raise SystemExit("Invalid cases JSON")
        if len({x["label"] for x in cases}) != len(cases):
            raise SystemExit("Duplicate case labels")
        if not args.project:
            raise SystemExit("Custom cases require an existing LabVIEW project")
    elif subject != SUBJECT.resolve():
        raise SystemExit("Custom subject requires --cases-json")
    if args.generate and (test_file == subject or not test_file.is_relative_to(subject.parent)):
        raise SystemExit("Test output must be inside the subject scratch directory")
    if not subject.is_file():
        raise SystemExit(f"Scratch VI missing: {subject}")
    if args.generate and test_file.exists():
        raise SystemExit(f"Refusing to overwrite existing test: {test_file}")

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
            test_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "viPath": str(subject),
                "casesJson": json.dumps(cases),
                "testViPath": str(test_file),
                "directCall": True,
                "timeoutSeconds": 120,
                "backend": "grpc",
                "measureDiagram": True,
            }
            if args.project:
                payload["projectPath"] = str(args.project.resolve())
            print("Requesting generation of Caraya test VI (not executing it)...", flush=True)
            result = await client.call_tool("lvai_generate_test", arguments=payload, read_timeout_seconds=600)
            tool_error = bool(getattr(result, "is_error", False))
            report = None
            for part in result.content:
                body = getattr(part, "text", None)
                if not body:
                    continue
                print(body)
                if report is None:
                    try:
                        report = json.loads(body)
                    except (ValueError, TypeError):
                        pass
            generator_ok = isinstance(report, dict) and report.get("ok") is True
            print(f"MCP tool error: {tool_error}")
            print(f"Generator succeeded: {generator_ok}")
            print(f"Test VI exists: {test_file.is_file()}")
            if not generator_ok or tool_error:
                if isinstance(report, dict):
                    print(f"Failed at: {report.get('failedAtStep', 'unknown')}")
                    if report.get("failedAtStep") == "retarget":
                        print("UNSAFE TO RUN: test VI still calls the placeholder, NOT F-to-C.")
                        print("Check bundled pylabview: python -m scripts.phase4_generate_caraya --diagnose")
                        print("Or provide an existing .lvproj listing the scratch VI with --project.")
                print("NO FUNCTIONAL TESTS WERE EXECUTED. Do not run the generated VI.")
                return 1
            print("Test generation reported success; inspect call targets before execution.")
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
