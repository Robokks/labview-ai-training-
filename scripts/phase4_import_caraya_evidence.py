"""Import independently generated Caraya JUnit evidence for the Phase 4 F-to-C gold candidate.

Read-only with respect to LabVIEW VIs and existing evidence; writes a NEW JSON
record only after all file hashes, case identities, and JUnit counters pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

EXPECTED_SHA256 = "46db1c751e6834f8d9857e75cc06a08658ccf2aac96b2ebdda7ee4418570cfe9"
EXPECTED_CASES = frozenset({
    "True freezing", "True boiling", "True minus forty", "True fifty",
    "False freezing", "False boiling", "False minus forty", "False passthrough",
})

def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def import_caraya(junit: Path, evidence: Path, original: Path, scratch: Path,
                  test_vi: Path, output: Path) -> dict:
    for path in (junit, evidence, original, scratch, test_vi):
        if not path.is_file():
            raise FileNotFoundError(f"Required input missing: {path}")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {output}")
    if original.resolve() == scratch.resolve():
        raise ValueError("Original and scratch must be different files")

    record = json.loads(evidence.read_text(encoding="utf-8-sig"))
    if record.get("schema") != "labview-ai-manual-functional-evidence-v2":
        raise ValueError("Expected the Phase 4 manual evidence v2")
    source_hash, scratch_hash = sha256(original), sha256(scratch)
    if source_hash != EXPECTED_SHA256 or scratch_hash != EXPECTED_SHA256:
        raise ValueError("Original or scratch VI hash changed; stop and investigate")
    if record.get("source_sha256") != source_hash or record.get("scratch_sha256") != scratch_hash:
        raise ValueError("Manual evidence does not match current VI hashes")
    if record.get("test_environment", {}).get("labview_version") != "2026":
        raise ValueError("Expected LabVIEW 2026 manual evidence")

    root = ET.parse(junit).getroot()
    if root.tag != "testsuites" or root.attrib.get("framework-name") != "Caraya":
        raise ValueError("Expected a Caraya testsuites XML root")
    suites = root.findall("testsuite")
    if len(suites) != 1:
        raise ValueError("Exactly one F-to-C testsuite is required")
    suite = suites[0]
    if suite.get("name") != "Test F to C":
        raise ValueError("Unexpected testsuite name")
    try:
        counts = {field: int(suite.attrib[field]) for field in ("tests", "failures", "errors", "skipped")}
    except (KeyError, ValueError) as exc:
        raise ValueError("Missing or invalid JUnit counters") from exc
    tests = suite.findall("testcase")
    names = [case.get("name") for case in tests]
    if counts != {"tests": 8, "failures": 0, "errors": 0, "skipped": 0}:
        raise ValueError(f"JUnit summary is not 8 clean passes: {counts}")
    if len(tests) != 8 or len(set(names)) != 8 or set(names) != EXPECTED_CASES:
        raise ValueError("JUnit case names missing, duplicated, or unexpected")
    for case in tests:
        if case.get("classname") != "Test F to C":
            raise ValueError("Unexpected JUnit testcase class")
        if list(case):
            raise ValueError("Test case has nested outcome elements; not a clean pass")
    if not suite.get("timestamp"):
        raise ValueError("Missing JUnit execution timestamp")
    if not root.attrib.get("framework-version"):
        raise ValueError("Missing Caraya version")
    manual_cases = record.get("test_cases", [])
    if len(manual_cases) != 8 or any(c.get("result") != "reported_pass" for c in manual_cases):
        raise ValueError("Manual evidence has not recorded eight reported passes")

    result = {
        "schema": "labview-ai-native-caraya-evidence-v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "subject": scratch.name,
        "original_path_local": str(original.resolve()),
        "scratch_path_local": str(scratch.resolve()),
        "test_vi_path_local": str(test_vi.resolve()),
        "junit_path_local": str(junit.resolve()),
        "source_sha256": source_hash,
        "scratch_sha256": scratch_hash,
        "test_vi_sha256": sha256(test_vi),
        "junit_sha256": sha256(junit),
        "manual_evidence_v2_sha256": sha256(evidence),
        "framework": "Caraya",
        "framework_version": root.attrib["framework-version"],
        "execution_timestamp": suite.attrib["timestamp"],
        "junit_counts": counts,
        "case_names": sorted(names),
        "case_name_coverage": "four True and four False branch names",
        "native_functional_verified": True,
        "gold_candidate": True,
        "gold_verified": False,
        "training_eligible": False,
        "cloud_approved": False,
        "quality_label": "native_functional_verified_candidate",
        "verification_basis": [
            "Original and scratch VI binary hashes match prior manual evidence.",
            "Submitted Caraya JUnit report contains eight distinct passing case names.",
            "Generated test VI was independently reported by MCP to call F to C (SUB VI).vi via direct project route.",
        ],
        "limitations": [
            "JUnit XML alone does not cryptographically prove which VI binary ran; retain the MCP generator report and project/test VI as provenance.",
            "Caraya reports pass/fail outcomes, not captured per-case numeric measurements.",
            "Training rights, dataset provenance, leakage controls and cloud permission remain separate gates.",
            "This evidence verifies one VI, not the full Phase 4 dataset.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument("--test-vi", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = import_caraya(args.junit, args.evidence, args.original,
                           args.scratch, args.test_vi, args.out)
    print(json.dumps({
        "native_functional_verified": result["native_functional_verified"],
        "junit_counts": result["junit_counts"],
        "gold_candidate": result["gold_candidate"],
        "gold_verified": result["gold_verified"],
        "training_eligible": result["training_eligible"],
        "cloud_approved": result["cloud_approved"],
        "evidence_written": str(args.out),
    }, indent=2))

if __name__ == "__main__":
    main()
