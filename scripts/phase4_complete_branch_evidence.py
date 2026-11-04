"""Append reported Boolean=False checks to a separate, immutable Phase 4 evidence revision.

This script does not execute LabVIEW or approve any training data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


FALSE_CASES = ((32.0, 32.0), (212.0, 212.0), (-40.0, -40.0), (98.6, 98.6))


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extend_evidence(source: Path, destination: Path, original: Path, scratch: Path) -> dict:
    if destination.exists():
        raise FileExistsError(f"Evidence revision already exists: {destination}")
    evidence = json.loads(source.read_text(encoding="utf-8"))
    if evidence.get("schema") != "labview-ai-manual-functional-evidence-v1":
        raise ValueError("Unexpected evidence schema")
    if evidence.get("test_environment", {}).get("labview_version") != "2026":
        raise ValueError("Expected LabVIEW 2026")
    if original.resolve() == scratch.resolve():
        raise ValueError("Original and scratch must be separate files")
    original_sha = file_hash(original)
    scratch_sha = file_hash(scratch)
    if (original_sha != evidence.get("source_sha256")
            or scratch_sha != evidence.get("scratch_sha256")
            or original_sha != scratch_sha):
        raise ValueError("VI binary hash changed since initial evidence; review before continuing")
    tests = evidence.get("test_cases")
    if not isinstance(tests, list) or len(tests) != 4 or any(t.get("result") != "reported_pass" for t in tests):
        raise ValueError("Original True-case evidence is incomplete")
    expected_true = ((32.0, 0.0), (212.0, 100.0), (-40.0, -40.0), (98.6, 37.0))
    if any(float(t.get("fahrenheit")) != f or float(t.get("reported_actual_celsius")) != c
           for t, (f, c) in zip(tests, expected_true)):
        raise ValueError("Original True-case records do not match the reviewed test cases")
    updated = dict(evidence)
    updated["schema"] = "labview-ai-manual-functional-evidence-v2"
    updated["supersedes_sha256"] = file_hash(source)
    updated["updated_utc"] = datetime.now(timezone.utc).isoformat()
    updated["test_environment"] = dict(evidence["test_environment"], test_mode="Boolean=True and False")
    updated["true_case_tests"] = [{**t, "boolean": True} for t in tests]
    updated["false_case_tests"] = [
        {"boolean": False, "fahrenheit": f, "expected_celsius": c,
         "reported_actual_celsius": c, "result": "reported_pass"}
        for f, c in FALSE_CASES
    ]
    updated["test_cases"] = updated["true_case_tests"] + updated["false_case_tests"]
    updated["branch_review"] = {
        "true": "Fahrenheit-to-Celsius conversion (F - 32) * 5 / 9 observed in user screenshot",
        "false": "Direct pass-through F -> Celsius observed in user screenshot",
        "branch_coverage": "four user-reported runs per Boolean branch",
        "independently_verified": False
    }
    updated["limitations"] = [
        "Both Boolean branches visually inspected and user-reported tests passed.",
        "Independent automated execution, repeatability, dependency review and saved-IDE-state evidence remain pending.",
        "Source permissions, confidentiality and training rights remain unreviewed.",
        "Reported test values are not an independent machine-generated result log."
    ]
    updated["gold_candidate"] = True
    updated["gold_verified"] = False
    updated["training_eligible"] = False
    updated["cloud_approved"] = False
    updated["quality_label"] = "manual_functional_candidate"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--copy", type=Path, required=True)
    args = parser.parse_args()
    result = extend_evidence(args.evidence, args.out, args.original, args.copy)
    print(json.dumps({"revision": result["schema"], "test_cases": len(result["test_cases"]),
                      "true_passes": len(result["true_case_tests"]),
                      "false_passes": len(result["false_case_tests"]),
                      "gold_verified": result["gold_verified"],
                      "training_eligible": result["training_eligible"],
                      "output": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
