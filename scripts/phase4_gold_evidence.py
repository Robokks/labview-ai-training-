"""Create local, auditable evidence for the manually tested F-to-C VI.

Never executes a VI, modifies a source VI, or grants cloud/training permission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


CASES = [
    {"fahrenheit": 32.0, "expected_celsius": 0.0},
    {"fahrenheit": 212.0, "expected_celsius": 100.0},
    {"fahrenheit": -40.0, "expected_celsius": -40.0},
    {"fahrenheit": 98.6, "expected_celsius": 37.0},
]


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def record(original: Path, copy: Path, destination: Path, *,
           reviewer: str, labview_version: str = "2026") -> dict:
    if not original.is_file() or not copy.is_file():
        raise FileNotFoundError("Both the original and scratch VI must exist.")
    if original.resolve() == copy.resolve():
        raise ValueError("Original and scratch VI must be separate files.")
    source_sha = digest(original)
    scratch_sha = digest(copy)
    same = source_sha == scratch_sha
    result = {
        "schema": "labview-ai-manual-functional-evidence-v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "vi": copy.name,
        "original_path_local": str(original),
        "scratch_path_local": str(copy),
        "source_sha256": source_sha,
        "scratch_sha256": scratch_sha,
        "binary_matches_original": same,
        "test_environment": {"labview_version": labview_version,
                             "execution": "user-reported native LabVIEW front-panel run",
                             "test_mode": "Boolean=True"},
        "test_cases": [{**case, "reported_actual_celsius": case["expected_celsius"],
                        "result": "reported_pass"} for case in CASES],
        "evidence_provenance": {"reviewer": reviewer,
                                "source": "User statement in ChatGPT conversation",
                                "independent_reexecution": False,
                                "automated_execution": False},
        "limitations": [
            "Boolean=False branch behavior is not inspected or tested.",
            "Native compile status, dependencies and unsaved IDE edits were not independently captured.",
            "User-reported results require independent reproducibility before final Gold promotion.",
            "Hash matching confirms file bytes only; it does not establish runtime behavior."
        ],
        "gold_candidate": bool(same),
        "gold_verified": False,
        "training_eligible": False,
        "cloud_approved": False,
        "quality_label": "manual_functional_candidate" if same else "binary_mismatch_review"
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing evidence: {destination}")
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--copy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reviewer", required=True,
                        help="Local reviewer identifier for the evidence")
    parser.add_argument("--labview-version", default="2026")
    args = parser.parse_args()
    print(json.dumps(record(args.original, args.copy, args.out,
                            reviewer=args.reviewer,
                            labview_version=args.labview_version), indent=2))


if __name__ == "__main__":
    main()
