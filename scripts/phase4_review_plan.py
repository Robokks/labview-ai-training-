"""Phase 4 offline review plan: family splits, permissions, and native test queue.

Does not grant permission, build SFT pairs, upload data, or run VIs.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from labview_ai_training.dataset import split_for_project

FIELDS = ("project_family", "owner_or_source", "license_or_authority",
          "local_training_allowed", "cloud_training_allowed",
          "confidentiality_reviewed", "reviewer", "review_date", "notes")


def build(index: Path, output: Path, seed: str = "v1", sample_per_family: int = 3) -> dict:
    if sample_per_family < 0:
        raise ValueError("sample_per_family must not be negative")
    records = [json.loads(line) for line in index.read_text(encoding="utf-8-sig").splitlines()
               if line.strip()]
    families: dict[str, list[dict]] = defaultdict(list)
    seen: set[str] = set()
    errors = []
    excluded = 0
    for i, record in enumerate(records):
        sha = record.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha.lower()):
            errors.append({"index": i, "reason": "invalid_sha256"})
            continue
        if sha in seen:
            errors.append({"index": i, "reason": "duplicate_sha256"})
            continue
        seen.add(sha)
        if not record.get("structurally_verified", False):
            excluded += 1
            continue
        if record.get("quality") != "silver_structural_candidate":
            errors.append({"index": i, "reason": "unexpected_quality"})
            continue
        family = record.get("project_family")
        if not isinstance(family, str) or not family or "|" in family:
            errors.append({"index": i, "reason": "ambiguous_project_family"})
            continue
        families[family].append(record)
    if errors:
        raise ValueError(f"Invalid structural index: {errors[:10]}")
    output.mkdir(parents=True, exist_ok=True)
    assignments = {family: split_for_project(family, seed) for family in sorted(families)}
    index_rows, queue = [], []
    for family in sorted(families):
        group = sorted(families[family], key=lambda r: r["sha256"])
        selected = sorted(group, key=lambda r: hashlib.sha256(
            (seed + ":" + r["sha256"]).encode()).hexdigest())[:sample_per_family]
        selected_hashes = {r["sha256"] for r in selected}
        for r in group:
            index_rows.append({
                "sha256": r["sha256"], "project_family": family, "planned_split": assignments[family],
                "quality": "silver_structural_candidate", "provenance_paths": r["source_paths"],
                "raw_sha256": r.get("raw_sha256"),
                "graph_sha256": r.get("graph_sha256"),
                "native_verification_selected": r["sha256"] in selected_hashes,
                "permission_status": "unreviewed", "training_eligible": False,
                "cloud_approved": False
            })
        for r in selected:
            queue.append({"sha256": r["sha256"], "project_family": family,
                          "source_paths": r["source_paths"], "planned_split": assignments[family],
                          "verification_status": "not_run", "labview_target": "2026",
                          "workspace": "scratch_copy_only",
                          "checks": ["open_and_compile", "inspect_wiring_and_types",
                                     "define_expected_behavior", "execute_safe_test_cases"],
                          "authorization_required": True})
    with (output / "permission-review.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for family in sorted(families):
            writer.writerow({"project_family": family, "notes": "NOT APPROVED - review locally"})
    for name, rows in (("split-plan.jsonl", index_rows), ("native-verification-queue.jsonl", queue)):
        with (output / name).open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    split_counts = dict(Counter(assignments[f] for f in assignments))
    record_counts = dict(Counter(assignments[f] for f, group in families.items() for _ in group))
    report = {"records_read": len(records), "silver_candidates": len(index_rows),
              "previously_excluded": excluded, "family_count": len(families),
              "family_assignments": assignments, "split_family_counts": split_counts,
              "split_record_counts": record_counts, "native_queue_count": len(queue),
              "training_eligible": 0, "cloud_approved": 0,
              "held_out_warning": (not all(split_counts.get(n, 0) for n in ("train", "validation", "test"))),
              "limitations": ["Split is a deterministic preliminary plan, not final independent evaluation.",
                              "Folder-level families may still contain related or near-duplicate VIs.",
                              "No functionality or source rights have been verified.",
                              "No supervised instruction-answer examples created."]}
    (output / "review-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--structural-index", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--seed", default="v1")
    p.add_argument("--sample-per-family", type=int, default=3)
    a = p.parse_args()
    print(json.dumps(build(a.structural_index, a.output_dir, a.seed, a.sample_per_family), indent=2))


if __name__ == "__main__":
    main()
