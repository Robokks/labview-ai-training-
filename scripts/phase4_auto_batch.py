"""Guarded batch orchestration for native LabVIEW Caraya test generation.

This module NEVER runs a VI or approves data for training. A user-supplied
review manifest supplies source hashes, scratch copies, cases and LabVIEW
projects. Successful direct-route generation is checked before recording.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def validate_job(job: dict, scratch_root: Path) -> dict:
    needed = ("id", "source", "scratch", "sha256", "project", "cases", "test_vi")
    if any(not isinstance(job.get(k), str) or not job[k] for k in needed):
        raise ValueError("Job has missing fields: " + ", ".join(needed))
    if not job["id"].replace("-", "").replace("_", "").isalnum():
        raise ValueError("Job ID must contain only letters, numbers, dash and underscore")
    if job.get("manually_reviewed") is not True:
        raise ValueError("Job must be manually reviewed before generation")
    if job.get("risk_accepted_for_generation") is not True:
        raise ValueError("Job requires explicit generation approval")
    if job.get("allow_vi_execution") is not False:
        raise ValueError("Batch tool prohibits native execution")
    source, scratch, project, cases, test_vi = (
        Path(job[k]).resolve() for k in ("source", "scratch", "project", "cases", "test_vi"))
    if not source.is_file() or not scratch.is_file() or not project.is_file() or not cases.is_file():
        raise FileNotFoundError("Source, scratch, project or cases file missing")
    if source == scratch or not is_inside(scratch, scratch_root):
        raise ValueError("Scratch VI must be distinct and inside scratch root")
    if not is_inside(project, scratch_root) or not is_inside(test_vi, scratch_root):
        raise ValueError("Project and output test VI must live inside scratch root")
    if test_vi == scratch or test_vi == source or test_vi.exists():
        raise ValueError("Output test file collides with a VI or already exists")
    expected = job["sha256"].lower()
    if len(expected) != 64 or any(x not in "0123456789abcdef" for x in expected):
        raise ValueError("Invalid expected SHA-256")
    if file_sha256(source) != expected or file_sha256(scratch) != expected:
        raise ValueError("Source/scratch hash mismatch")
    data = json.loads(cases.read_text(encoding="utf-8-sig"))
    if (not isinstance(data, list) or not 1 <= len(data) <= 20
            or any(not isinstance(x, dict) or not isinstance(x.get("label"), str)
                   or not isinstance(x.get("inputs"), dict)
                   or not isinstance(x.get("expect"), dict)
                   or not x["inputs"] or not x["expect"] for x in data)):
        raise ValueError("Cases must contain 1-20 labeled input/expected-output mappings")
    if len(set(x["label"] for x in data)) != len(data):
        raise ValueError("Duplicate labels in expected test cases")
    return {
        "id": job["id"], "source": source, "scratch": scratch,
        "project": project, "cases": cases, "test_vi": test_vi,
        "sha256": expected, "case_count": len(data),
    }


def run_batch(manifest: Path, scratch_root: Path, output_dir: Path, *,
              generate: bool = False, timeout: int = 900) -> dict:
    if not 30 <= timeout <= 3600:
        raise ValueError("Timeout must be 30-3600 seconds")
    info = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if info.get("schema") != "phase4-caraya-generation-batch-v1":
        raise ValueError("Unexpected manifest schema")
    jobs = info.get("jobs")
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 20:
        raise ValueError("Expected 1-20 batch jobs")
    if any(not isinstance(x, dict) for x in jobs):
        raise ValueError("Each job must be an object")
    if len({x.get("id") for x in jobs}) != len(jobs):
        raise ValueError("Duplicate job IDs")

    if output_dir.exists() and (output_dir / ("batch-generation-report.json" if generate else "batch-preflight-report.json")).exists():
        raise FileExistsError("Report already exists. Use a new output directory for a new run")
    results = []
    # Independent per-job validation lets other candidates be reported without
    # accidentally authorizing any invalid item.
    for job in jobs:
        name = str(job.get("id", "invalid"))
        try:
            valid = validate_job(job, scratch_root)
            status = "ready_for_native_generation"
            error = None
        except (ValueError, FileNotFoundError, KeyError, OSError, TypeError) as exc:
            valid = None
            status = "blocked_review"
            error = str(exc)
        item = {"id": name, "status": status, "reason": error,
                "generated": False, "native_executed": False,
                "training_eligible": False, "cloud_approved": False}
        if generate and valid:
            log_path = output_dir / (name + ".generation.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            command = [
                sys.executable, "-m", "scripts.phase4_generate_caraya",
                "--generate", "--subject", str(valid["scratch"]),
                "--test-file", str(valid["test_vi"]),
                "--cases-json", str(valid["cases"]),
                "--project", str(valid["project"]),
            ]
            try:
                proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
                log_path.write_text(proc.stdout + "\nSTDERR:\n" + proc.stderr, encoding="utf-8")
                # Non-zero exit, missing test, or placeholder route means failure.
                output = proc.stdout
                direct = '"route": "direct"' in output
                correct_target = valid["scratch"].name in output
                success = (proc.returncode == 0 and valid["test_vi"].is_file()
                           and "Generator succeeded: True" in output
                           and direct and correct_target
                           and "MCP tool error: False" in output)
                item.update(status="generated_needs_call_target_review" if success
                            else "generation_failed_needs_review",
                            generated=success, reason=None if success
                            else "Check local generation log before any execution",
                            generator_log_local=str(log_path))
            except subprocess.TimeoutExpired as exc:
                log_path.write_text(
                    (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes)
                    else (exc.stdout or ""), encoding="utf-8")
                item.update(status="generation_timeout_needs_review",
                            reason="Generation timed out; inspect LabVIEW and output file",
                            generator_log_local=str(log_path))
        results.append(item)
    report = {
        "schema": "phase4-generation-batch-report-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "generate_only" if generate else "preflight_only",
        "jobs": results,
        "generated_count": sum(x["generated"] for x in results),
        "native_executions": 0,
        "training_eligible": 0,
        "cloud_approved": 0,
        "next_step": "Review generated call targets, then run approved Caraya tests and collect JUnit XML separately.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / ("batch-generation-report.json" if generate else "batch-preflight-report.json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--scratch-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--generate", action="store_true",
                        help="Generate Caraya test VIs only, never execute them")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run_batch(args.manifest, args.scratch_root,
                               args.output_dir, generate=args.generate,
                               timeout=args.timeout), indent=2))


if __name__ == "__main__":
    main()
