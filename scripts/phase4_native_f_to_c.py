"""Automated LabVIEW 2026 F-to-C verification via Windows COM.

STRICTLY limited to the previously reviewed scratch VI. Never saves the VI,
writes to original source, runs other VIs, or promotes training permission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_SHA = "46db1c751e6834f8d9857e75cc06a08658ccf2aac96b2ebdda7ee4418570cfe9"
VI_FILENAME = "F to C (SUB VI).vi"
CASES = [(True, 32.0, 0.0), (True, 212.0, 100.0),
         (True, -40.0, -40.0), (True, 98.6, 37.0),
         (False, 32.0, 32.0), (False, 212.0, 212.0),
         (False, -40.0, -40.0), (False, 98.6, 98.6)]


def sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def preflight(vi: Path, original: Path, evidence: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Report already exists: {output}")
    if not vi.is_file() or not original.is_file():
        raise FileNotFoundError("Both scratch VI and original VI must exist")
    if not evidence.is_file():
        raise FileNotFoundError(evidence)
    if vi.resolve() == original.resolve() or vi.name != VI_FILENAME:
        raise ValueError("Only the separate reviewed F-to-C scratch VI is allowed")
    report = json.loads(evidence.read_text(encoding="utf-8"))
    if report.get("schema") != "labview-ai-manual-functional-evidence-v2":
        raise ValueError("Expected the reviewed v2 evidence record")
    for path, key in ((vi, "scratch_sha256"), (original, "source_sha256")):
        current = sha256(path)
        if current != report.get(key) or current != EXPECTED_SHA:
            raise ValueError(f"VI hash mismatch: {path}")
    if Path(report.get("scratch_path_local", "")).resolve() != vi.resolve():
        raise ValueError("Scratch path does not match evidence")
    if Path(report.get("original_path_local", "")).resolve() != original.resolve():
        raise ValueError("Original path does not match evidence")
    if len(report.get("test_cases", [])) != len(CASES):
        raise ValueError("Missing eight manually verified cases")
    return report


def execute(vi: Path, original: Path, evidence: Path, output: Path,
            app=None, allow_run: bool = False) -> dict:
    saved = preflight(vi, original, evidence, output)
    if not allow_run:
        raise ValueError("Execution requires --run after reviewing the exact VI and environment")
    if sys.platform != "win32" and app is None:
        raise OSError("Windows and LabVIEW COM automation are required")
    if app is None:
        try:
            import win32com.client
        except ImportError as exc:
            raise RuntimeError("Install pywin32: python -m pip install pywin32") from exc
        # Attach to an already running LabVIEW instance; do not start another process.
        app = win32com.client.GetActiveObject("LabVIEW.Application")
    version = str(app.Version)
    if not version.startswith("26"):
        raise RuntimeError(f"Expected LabVIEW 2026 (26.x); got {version!r}")
    handle = app.GetVIReference(str(vi.resolve()))
    if hasattr(handle, "_FlagAsMethod"):
        handle._FlagAsMethod("Run")
    rows = []
    for boolean, fahrenheit, expected in CASES:
        item = {"boolean": boolean, "fahrenheit": fahrenheit,
                "expected_celsius": expected}
        try:
            handle.SetControlValue("Boolean", boolean)
            handle.SetControlValue("Farenheit", fahrenheit)
            handle.Run(True)
            actual = float(handle.GetControlValue("Celcius"))
            item["actual_celsius"] = actual
            item["passed"] = math.isfinite(actual) and math.isclose(
                actual, expected, rel_tol=1e-9, abs_tol=1e-6)
        except Exception as exc:
            item["passed"] = False
            item["error"] = f"{type(exc).__name__}: {exc}"[:600]
        rows.append(item)
    # Check that no on-disk source VI bytes were modified.
    unchanged = (sha256(vi) == saved["scratch_sha256"] and
                 sha256(original) == saved["source_sha256"])
    passed = sum(item["passed"] for item in rows)
    result = {"schema": "labview-ai-native-functional-test-v1",
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "labview_version": version, "vi": str(vi),
              "scratch_sha256": saved["scratch_sha256"],
              "manual_evidence_sha256": sha256(evidence),
              "control_names": ["Boolean", "Farenheit"],
              "indicator_name": "Celcius",
              "execution_method": "LabVIEW COM GetVIReference, SetControlValue, Run(True), GetControlValue",
              "tests": rows, "passed": passed, "total": len(rows),
              "binary_unchanged": unchanged,
              "all_passed": passed == len(rows) and unchanged,
              "gold_candidate": passed == len(rows) and unchanged,
              "gold_verified": False,
              "training_eligible": False,
              "cloud_approved": False,
              "limitations": ["No independent compile diagnostics or dependency audit collected",
                              "Only this VI's two Boolean branches were tested",
                              "Training rights and confidentiality have not been reviewed"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents silently replacing prior verification evidence.
    with output.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vi", type=Path, required=True)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--run", action="store_true")
    args = p.parse_args()
    result = execute(args.vi, args.original, args.evidence, args.out, allow_run=args.run)
    print(json.dumps({"passed": result["passed"], "total": result["total"],
                      "all_passed": result["all_passed"],
                      "binary_unchanged": result["binary_unchanged"],
                      "gold_verified": result["gold_verified"], "output": str(args.out)}, indent=2))
    if not result["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
