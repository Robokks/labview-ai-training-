"""Command-line entry point for safe dataset preparation and read-only MCP probing."""
import argparse
import asyncio
import json
from pathlib import Path

from . import aixml, dataset, inventory

def main(argv=None):
    p=argparse.ArgumentParser(prog="labview-ai-training")
    sub=p.add_subparsers(dest="command",required=True)

    inv=sub.add_parser("inventory",help="Read-only source manifest")
    inv.add_argument("--root",required=True,type=Path)
    inv.add_argument("--out",required=True,type=Path)

    graph=sub.add_parser("graph",help="Extract AIXML nodes, terminals and nets")
    graph.add_argument("--input",required=True,type=Path)
    graph.add_argument("--out",required=True,type=Path)

    ds=sub.add_parser("prepare-sft",help="Filter approved records and group-split SFT data")
    ds.add_argument("--input",required=True,type=Path)
    ds.add_argument("--output-dir",required=True,type=Path)
    ds.add_argument("--seed",default="v1")

    mcp=sub.add_parser("mcp-status",help="Read-only LabVIEW MCP health probe")
    mcp.add_argument("--exe",required=True,type=Path)
    args=p.parse_args(argv)

    if args.command=="inventory":
        result=inventory.inventory(args.root)
        inventory.save(result,args.out)
        print(json.dumps(result["summary"],indent=2))
    elif args.command=="graph":
        result=aixml.load(args.input)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
        print(f"Extracted {len(result['nodes'])} elements, {len(result['nets'])} nets")
    elif args.command=="prepare-sft":
        print(json.dumps(dataset.prepare(args.input,args.output_dir,args.seed),indent=2))
    elif args.command=="mcp-status":
        from .mcp_bridge import status
        print(asyncio.run(status(args.exe)))

if __name__=="__main__":
    main()
