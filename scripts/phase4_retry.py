"""Read-only, resumable Phase 4 VI-to-AIXML retry for LabVIEW 2026.

Converter interface: python vi2aixml.py INPUT.vi OUTPUT.aixml
No source VI modifications or cloud uploads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from labview_ai_training import aixml


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def retry(manifest: Path, source_root: Path, output_dir: Path,
          converter: Path | None = None, run: bool = False,
          limit: int | None = None, timeout: int = 180) -> dict:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    records = data["records"]
    pending = [r for r in records if r.get("status") == "failed"]
    if limit is not None:
        pending = pending[:limit]
    report = {"scanned": len(records), "pending": len(pending),
              "attempted": 0, "converted": 0, "errors": [], "dry_run": not run}
    if run and converter is None:
        raise ValueError("--converter is required when --run is used")
    root = source_root.resolve()
    for row in pending:
        digest = row["sha256"]
        name = row["source_paths"][0]
        vi = (root / name).resolve()
        if not vi.is_relative_to(root) or not vi.is_file():
            report["errors"].append({"path": name, "reason": "missing_or_unsafe_path"})
            continue
        if sha256(vi) != digest:
            report["errors"].append({"path": name, "reason": "source_hash_mismatch"})
            continue
        if not run:
            continue
        report["attempted"] += 1
        target = output_dir / "aixml" / digest
        target.mkdir(parents=True, exist_ok=True)
        raw = target / "raw.aixml"
        try:
            result = subprocess.run([sys.executable, str(converter), str(vi), str(raw)],
                                    capture_output=True, timeout=timeout, check=False)
            if result.returncode:
                raise RuntimeError(result.stderr.decode("utf-8", "replace")[-600:]
                                   or f"converter exit {result.returncode}")
            source = raw.read_text(encoding="utf-8-sig")
            graph = aixml.parse(source)
            canonical = aixml.canonicalize(source)
            if graph != aixml.parse(canonical) or canonical != aixml.canonicalize(canonical):
                raise ValueError("AIXML normalization mismatch")
            if graph["warnings"]:
                raise ValueError("AIXML graph warnings: " + str(graph["warnings"][:3]))
            (target / "normalized.aixml").write_text(canonical, encoding="utf-8")
            (target / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")
            row["status"] = "converted"
            row["backend"] = "pylabview"
            row["nodes"] = len(graph["nodes"])
            row["warnings"] = []
            row["aixml_sha256"] = sha256(raw)
            row.pop("error", None)
            report["converted"] += 1
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            report["errors"].append({"path": name, "reason": type(exc).__name__,
                                     "detail": str(exc)[-400:]})
        # Atomic checkpoint after every attempted conversion.
        output_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = output_dir / "batch-results.json"
        temporary = checkpoint.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temporary.replace(checkpoint)
    report["remaining_failed"] = sum(r.get("status") == "failed" for r in records)
    report["status_counts"] = dict(Counter(r.get("status", "unknown") for r in records))
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "retry-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--converter", type=Path)
    parser.add_argument("--run", action="store_true", help="execute conversions (default: dry run)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    report = retry(args.manifest, args.source_root, args.output_dir,
                   args.converter, args.run, args.limit, args.timeout)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
