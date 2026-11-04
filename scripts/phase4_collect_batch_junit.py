"""Verify Caraya JUnit reports for multiple Phase 4 approved candidates.

Does not execute VIs, does not authorize training/cloud use. Each result must
match declared case labels and an unchanged source/scratch VI hash.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def collect(manifest: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Will not overwrite {output}")
    spec = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if spec.get("schema") != "phase4-caraya-generation-batch-v1":
        raise ValueError("Wrong batch manifest schema")
    rows = []
    for job in spec.get("jobs", []):
        item = {"id": job.get("id"), "native_functional_verified": False,
                "gold_verified": False, "training_eligible": False, "cloud_approved": False}
        try:
            original = Path(job["source"])
            scratch = Path(job["scratch"])
            test = Path(job["test_vi"])
            cases = json.loads(Path(job["cases"]).read_text(encoding="utf-8-sig"))
            junit = Path(job["junit"])
            expected_sha = job["sha256"].lower()
            if (not original.is_file() or not scratch.is_file() or not test.is_file()
                    or not junit.is_file()):
                raise FileNotFoundError("Source/scratch/test VI or JUnit is missing")
            if digest(original) != expected_sha or digest(scratch) != expected_sha:
                raise ValueError("Source or scratch hash mismatch")
            labels = [c["label"] for c in cases]
            if not labels or len(labels) != len(set(labels)):
                raise ValueError("Missing or duplicate expected case names")
            tree = ET.parse(junit)
            root = tree.getroot()
            if root.tag != "testsuites" or root.get("framework-name") != "Caraya":
                raise ValueError("Not a Caraya JUnit report")
            suites = root.findall("testsuite")
            if len(suites) != 1:
                raise ValueError("Expected one test suite per job")
            suite = suites[0]
            if suite.get("name") != job.get("suite_name"):
                raise ValueError("JUnit suite name does not match approved job")
            counts = {k: int(suite.attrib[k]) for k in ("tests", "failures", "errors", "skipped")}
            if (counts["tests"] != len(labels) or counts["failures"] != 0
                    or counts["errors"] != 0 or counts["skipped"] != 0):
                raise ValueError("JUnit did not report a complete clean pass")
            observed = suite.findall("testcase")
            if (len(observed) != len(labels) or
                    {x.get("name") for x in observed} != set(labels) or
                    any(x.get("classname") != job["suite_name"] or list(x) for x in observed)):
                raise ValueError("JUnit testcase details differ from expected cases")
            item.update(native_functional_verified=True,
                        status="junit_8_or_more_passes_verified",
                        passed_cases=len(labels), source_sha256=expected_sha,
                        junit_sha256=digest(junit),
                        test_vi_sha256=digest(test),
                        framework_version=root.get("framework-version"),
                        execution_timestamp=suite.get("timestamp"),
                        limitations=[
                            "JUnit identity and file hash agreement do not prove the exact executed LabVIEW binary.",
                            "Direct call target and fixture dependencies require a separate auditable generator log.",
                            "No training rights or cloud upload permission inferred."
                        ])
        except (OSError, ValueError, TypeError, KeyError, ET.ParseError) as exc:
            item.update(status="blocked_or_failed", reason=str(exc))
        rows.append(item)
    result = {"schema": "phase4-caraya-batch-junit-evidence-v1",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "cases_verified": sum(x.get("passed_cases", 0) for x in rows),
              "vis_verified_by_junit": sum(x["native_functional_verified"] for x in rows),
              "gold_verified": 0, "training_eligible": 0, "cloud_approved": 0,
              "jobs": rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(collect(args.manifest, args.out), indent=2))


if __name__ == "__main__":
    main()
