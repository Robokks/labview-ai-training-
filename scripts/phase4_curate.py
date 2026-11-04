"""Audit converted VI metadata without treating conversion as functional verification."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path


def family(path: str, roots: list[str]) -> str:
    matches = [r for r in roots if path == r or path.startswith(r + "/")]
    if not matches:
        raise ValueError("Unknown project family: " + path)
    return max(matches, key=len)


def audit(manifest: Path, output_dir: Path, failed_manifest: Path | None = None) -> dict:
    source = json.loads(manifest.read_text(encoding="utf-8-sig"))
    roots, records = source["roots"], source["records"]
    index, problems, seen = [], [], set()
    counts = Counter()
    for i, record in enumerate(records):
        sha, paths = record.get("sha256"), record.get("source_paths")
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha.lower()):
            problems.append({"index": i, "reason": "bad_sha256"})
            continue
        if sha in seen:
            problems.append({"index": i, "reason": "duplicate_binary_hash"})
            continue
        seen.add(sha)
        if record.get("status") != "converted" or record.get("warnings"):
            problems.append({"index": i, "reason": "not_clean_conversion"})
            continue
        if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p for p in paths):
            problems.append({"index": i, "reason": "missing_source_paths"})
            continue
        try:
            groups = sorted({family(p, roots) for p in paths})
        except ValueError:
            problems.append({"index": i, "reason": "unmapped_family"})
            continue
        counts.update(groups)
        index.append({"sha256": sha, "source_paths": paths,
                      "project_family": "|".join(groups), "backend": record.get("backend"),
                      "nodes": record.get("nodes"), "quality": "bronze",
                      "training_eligible": False, "cloud_approved": False,
                      "needs": ["AIXML and graph review", "owner and license permission",
                                "structural or functional validation"]})
    deferred = None
    if failed_manifest:
        failures = json.loads(failed_manifest.read_text(encoding="utf-8-sig"))
        pending = failures.get("retry_candidates", []) + failures.get("deferred", [])
        deferred = len(pending)
        overlap = seen.intersection(r.get("sha256") for r in pending)
        if overlap:
            problems.append({"reason": "converted_failed_overlap", "count": len(overlap)})
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "local-bronze-index.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in index),
        encoding="utf-8")
    report = {"converted_records_in_manifest": len(records), "indexed_provisional": len(index),
              "training_eligible": 0, "cloud_approved": 0,
              "deferred_failed_records": deferred, "source_families": dict(counts),
              "issues": problems, "status": "metadata_audit_only"}
    (output_dir / "audit-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--failed-manifest", type=Path)
    a = p.parse_args()
    print(json.dumps(audit(a.manifest, a.output_dir, a.failed_manifest), indent=2))


if __name__ == "__main__":
    main()
