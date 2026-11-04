"""One-command Phase 4 local orchestration: project -> MCP probe -> preflight -> optional generation.

Never executes user VIs, edits source files, or changes approval flags.
Use --generate only with a separately reviewed/approved manifest. 
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from scripts.phase4_create_projects import create_from_manifest
from scripts.phase4_auto_batch import run_batch

DEFAULT_MCP = Path(r"C:\LabVIEWTools\labview-mcp-v2.4.1\bin\LabVIEWMCP.exe")


def orchestrate(manifest: Path, template: Path, scratch_root: Path, output_dir: Path,
                *, generate: bool = False, mcp_exe: Path = DEFAULT_MCP,
                probe: bool = True) -> dict:
    manifest = manifest.resolve()
    template = template.resolve()
    scratch_root = scratch_root.resolve()
    output_dir = output_dir.resolve()
    if not manifest.is_file() or not template.is_file():
        raise FileNotFoundError("Manifest or working project template missing")
    info = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if info.get("schema") != "phase4-caraya-generation-batch-v1":
        raise ValueError("Unsupported manifest schema")
    jobs = info.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("No jobs found")
    if any(not isinstance(job, dict) for job in jobs):
        raise ValueError("Invalid batch job")
    if len({str(job.get("id")) for job in jobs}) != len(jobs):
        raise ValueError("Duplicate batch IDs")
    project_paths = [Path(job["project"]).resolve() for job in jobs]
    existing = [p for p in project_paths if p.is_file()]
    absent = [p for p in project_paths if not p.exists()]
    if existing and absent:
        raise ValueError("Mixed existing/missing projects; resolve explicitly before rerunning")
    if not existing and not absent:
        raise ValueError("Invalid project state")
    if all(p.is_file() for p in project_paths):
        project_result = {"projects_created": 0, "projects_reused": len(project_paths)}
    else:
        project_result = create_from_manifest(template, manifest, scratch_root)
        project_result["projects_reused"] = 0

    probes = []
    if probe:
        if not mcp_exe.is_file():
            probes.append({"status": "mcp_missing", "path": str(mcp_exe)})
        else:
            for job in jobs:
                subject = Path(job["scratch"]).resolve()
                run = subprocess.run(
                    [str(mcp_exe), "--selftest", "--vi", str(subject), "--timeout", "30"],
                    capture_output=True, text=True, timeout=90,
                )
                passed = run.returncode == 0 and "0 failed" in run.stdout
                probes.append({"id": job.get("id"), "passed": passed,
                               "returncode": run.returncode,
                               "summary": next((x.strip() for x in run.stdout.splitlines()
                                                if "passed" in x and "failed" in x),
                                               "No summary")})
    else:
        probes = [{"status": "mcp_not_probed"}]

    # A missed read-only MCP probe blocks generation, never preflight.
    probe_ok = all(r.get("passed") is True for r in probes) if probe else True
    if generate and not probe_ok:
        raise RuntimeError("Cannot generate: one or more MCP self-tests failed")
    report = run_batch(manifest, scratch_root, output_dir / "batch",
                       generate=generate)
    result = {
        "schema": "phase4-local-oneclick-report-v1",
        "projects": project_result, "mcp_probes": probes,
        "batch": report, "native_executions": 0,
        "training_eligible": 0, "cloud_approved": 0,
        "note": ("Generation only; generated test call targets must be reviewed, "
                 "and native Caraya execution requires a separately verified runner."),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "oneclick-report.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--template", type=Path, required=True)
    p.add_argument("--scratch-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--generate", action="store_true")
    p.add_argument("--skip-mcp-selftest", action="store_true")
    args = p.parse_args()
    result = orchestrate(args.manifest, args.template,
                         args.scratch_root, args.output_dir,
                         generate=args.generate, probe=not args.skip_mcp_selftest)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
