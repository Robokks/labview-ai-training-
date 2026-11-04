"""Phase 4 candidate screening and explicitly approved scratch staging.

No VI execution, no generation, no mutation of source files, no cloud transfer.
The filename/graph heuristic is a REVIEW AID, never an execution authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

HASH = re.compile(r"^[0-9a-f]{64}$")
MATH = re.compile(r"(math|arithmetic|calculat|conversion|convert|temperature|fahrenheit|celsius|celcius|farenheit|average|mean|median|absolute|square|round|factorial|sum|add|subtract|multiply|divide|sinus|sine|cosine|sqrt|quadratic|f to c|c to f)", re.I)
DANGER = re.compile(r"(daq|device|driver|hardware|visa|serial|rs.?232|rs.?422|modbus|tcp|udp|ethernet|network|http|webcam|camera|motor|servo|motion|drive|actuator|relay|contactor|plc|fpga|realtime|real.time|cdaq|crio|instrument|oscilloscope|database|sql|oracle|file.?io|read.?file|write.?file|delete|remove|rename|process|command|system.?exec|shell|python|dll|call.?library|activex|shared.?variable|queue|notifier|event|socket|usb|canopen|power.?supply|sfc|load.?bank|deploy|reboot|shutdown|format.?disk|registry)", re.I)

# Whole-token math matches on the *subject VI basename*, never ancestor folders.
# Prevent e.g. "sum" inside "Consume Message" from being called mathematics.
MATH_SUBJECT = re.compile(
    r"(?<![A-Za-z])(?:math|arithmetic|calculate|calculation|conversion|convert|"
    r"fahrenheit|farenheit|celsius|celcius|average|mean|median|absolute|"
    r"square|round|factorial|sum|add|subtract|multiply|divide|sine|cosine|"
    r"sqrt|quadratic|f[ _-]*to[ _-]*c|c[ _-]*to[ _-]*f)(?![A-Za-z])", re.I
)
# Conservative metadata-only refusal for operations with plausible side effects.
# Use explicit words to avoid excluding every graph through generic field names.
SIDE_EFFECT = re.compile(
    r"(?:rabbitmq|mqtt|amqp|logging|logger|log[ _-]*data|record[ _-]*data|"
    r"save[ _-]*data|write[ _-]*data|append[ _-]*file|"
    r"\biot\b|\bnetwork\b|\btcp\b|\budp\b|\bdaq\b|\bvisa\b|"
    r"\bserial\b|\bmodbus\b|\bdevice\b|\bhardware\b|\bdatabase\b|"
    r"\bcamera\b|\bwebcam\b|\bdriver\b|\bmotor\b|\bplc\b|"
    r"\bfile[ _-]*io\b|\bactuator\b|\bdll\b)", re.I
)

def read_records(index: Path):
    seen = set()
    for line_no, line in enumerate(index.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        sha = record.get("sha256")
        if not isinstance(sha, str) or not HASH.fullmatch(sha):
            raise ValueError(f"Invalid SHA-256 on line {line_no}")
        if sha in seen:
            raise ValueError(f"Duplicate SHA-256 on line {line_no}")
        seen.add(sha)
        yield record

def inspect(index: Path, archive: Path, output: Path, limit: int = 3) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    reviewed = []
    with zipfile.ZipFile(archive) as z:
        members = set(z.namelist())
        for record in read_records(index):
            if record.get("quality") != "silver_structural_candidate" or not record.get("structurally_verified"):
                continue
            paths = record.get("source_paths")
            if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
                continue
            sha = record["sha256"]
            name = f"{sha}/graph.json"
            if name not in members:
                continue
            try:
                graph = json.loads(z.read(name))
            except (ValueError, UnicodeError):
                continue
            if not isinstance(graph, dict):
                continue
            # Block suspicious content in both names and graph text, but do NOT infer
            # that absence of suspicious words makes an unknown VI safe.
            labels = " ".join([*paths, str(graph.get("vi_name", ""))])
            # Generic serialized graph metadata contains risk keywords such as
            # "network" and "process". Those are NOT VI operations, and caused
            # all 1,218 records to be excluded. Review semantic node fields only.
            suspicious = bool(DANGER.search(labels)) or bool(SIDE_EFFECT.search(labels))
            risk_hits = []
            if SIDE_EFFECT.search(labels):
                risk_hits.append("path or subject suggests side effects")
            for node in graph.get("nodes", []):
                if not isinstance(node, dict):
                    continue
                for field in ("name", "label", "target", "function", "opcode", "kind"):
                    value = node.get(field)
                    if isinstance(value, str) and (DANGER.search(value) or SIDE_EFFECT.search(value)):
                        risk_hits.append(f"{field}: {value[:100]}")
                        suspicious = True
            subjects = [PurePosixPath(p).name.rsplit(":", 1)[-1] for p in paths]
            subjects.append(str(graph.get("vi_name", "")).rsplit(":", 1)[-1])
            math_hint = any(MATH_SUBJECT.search(subject) for subject in subjects)
            assessment = "excluded_keyword_risk" if suspicious else (
                "manual_review_candidate" if math_hint else "unknown_behavior_not_selected"
            )
            reviewed.append({
                "sha256": sha, "project_family": record.get("project_family"),
                "source_paths": paths, "vi_name": graph.get("vi_name"),
                "assessment": assessment, "math_name_hint": math_hint,
                "keyword_risk_found": suspicious, "risk_examples": risk_hits[:5],
                "needs_human_block_diagram_review": True,
                "requires_expected_outputs_and_dependency_review": True,
                "execution_authorized": False, "training_eligible": False, "cloud_approved": False,
            })
    shortlist = sorted((x for x in reviewed if x["assessment"] == "manual_review_candidate"),
                       key=lambda x: (len(x["source_paths"]), x["sha256"]))[:limit]
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": "phase4-batch-review-v1", "mode": "metadata_screening_only",
        "counts": dict(Counter(r["assessment"] for r in reviewed)),
        "shortlist": shortlist, "limit": limit, "execution_authorized": False,
        "training_eligible": False, "cloud_approved": False,
        "limitations": [
            "Keyword screening is neither static program analysis nor a security guarantee.",
            "No suspicious keywords found does NOT imply that a VI is safe.",
            "Every candidate requires manual LabVIEW block diagram, dependencies and side-effects review.",
            "No native VI has been run, generated or verified by this script.",
        ],
    }
    with output.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result

def stage(plan: Path, approval: Path, source_root: Path, scratch_root: Path, report_path: Path) -> dict:
    if report_path.exists():
        raise FileExistsError(f"Refusing to overwrite {report_path}")
    data = json.loads(plan.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "phase4-batch-review-v1" or data.get("execution_authorized") is not False:
        raise ValueError("Invalid review plan")
    decision = json.loads(approval.read_text(encoding="utf-8-sig"))
    if decision.get("schema") != "phase4-scratch-staging-approval-v1":
        raise ValueError("Invalid approval schema")
    approved = decision.get("approved_sha256", [])
    if not isinstance(approved, list) or len(approved) == 0 or len(approved) > 3 or len(set(approved)) != len(approved):
        raise ValueError("Approval must contain 1-3 distinct SHA-256 strings")
    if decision.get("reviewer") in (None, "") or decision.get("safe_for_scratch_copy") is not True:
        raise ValueError("Named reviewer must approve SCRATCH COPIES")
    if decision.get("authorizes_vi_execution") is not False:
        raise ValueError("Staging approval must NOT authorize execution")
    short = {r["sha256"]: r for r in data.get("shortlist", [])}
    if any(h not in short or not HASH.fullmatch(h) for h in approved):
        raise ValueError("Approval includes a VI not on the screened shortlist")
    if not source_root.is_dir():
        raise FileNotFoundError(f"Source root not found: {source_root}")
    scratch_root.mkdir(parents=True, exist_ok=True)
    if source_root.resolve() == scratch_root.resolve() or source_root.resolve() in scratch_root.resolve().parents:
        raise ValueError("Scratch root must not be within the source tree")
    if scratch_root.resolve() in source_root.resolve().parents:
        raise ValueError("Source root must not be inside scratch tree")
    staged = []
    # Preflight EVERY input before copying ANYTHING.
    for sha in approved:
        record = short[sha]
        viable = []
        for relative in record["source_paths"]:
            p = PurePosixPath(relative)
            if p.is_absolute() or any(part in (".", "..") for part in p.parts) or not p.parts:
                raise ValueError(f"Unsafe source path: {relative}")
            candidate = source_root.joinpath(*p.parts).resolve()
            if not candidate.is_relative_to(source_root.resolve()):
                raise ValueError("Source path leaves root")
            if candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest() == sha:
                viable.append(candidate)
        if not viable:
            raise FileNotFoundError(f"No hash-matching source file for {sha}; check --source-root")
        source = viable[0]
        dest = scratch_root / sha[:12] / source.name
        if dest.exists():
            raise FileExistsError(f"Refusing to overwrite staged VI: {dest}")
        staged.append((sha, source, dest))
    for _, source, dest in staged:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as r, dest.open("xb") as w:
            shutil.copyfileobj(r, w)
    for sha, source, dest in staged:
        if hashlib.sha256(dest.read_bytes()).hexdigest() != sha:
            raise RuntimeError(f"Scratch hash mismatch after copy: {dest}")
    result = {
        "schema": "phase4-staged-scratch-v1", "reviewer": decision["reviewer"],
        "copies": [{"sha256": sha, "original_local": str(source), "scratch_local": str(dest)}
                   for sha, source, dest in staged],
        "native_execution": "NOT AUTHORIZED", "training_eligible": False, "cloud_approved": False,
        "next_required": "Inspect each diagram/dependency and define explicit cases before generating or running tests.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("screen", help="Read-only shortlist from existing structure evidence")
    for name in ("structural-index", "archive", "out"):
        s.add_argument("--"+name, type=Path, required=True)
    s.add_argument("--limit", type=int, default=3)
    t = sub.add_parser("stage", help="Copy explicitly reviewed binaries to scratch; never execute")
    for name in ("plan", "approval", "source-root", "scratch-root", "out"):
        t.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    result = (inspect(a.structural_index, a.archive, a.out, a.limit) if a.command == "screen"
              else stage(a.plan, a.approval, a.source_root, a.scratch_root, a.out))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
