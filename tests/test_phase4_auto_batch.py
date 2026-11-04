"""Safe offline tests for Phase 4 automated Caraya batch preflight."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase4_auto_batch import run_batch


class AutoBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scratch_root = self.root / "Scratch"
        self.scratch_root.mkdir()
        self.original = self.root / "original.vi"
        self.scratch = self.scratch_root / "sum.vi"
        self.original.write_bytes(b"LABVIEW-STUB")
        self.scratch.write_bytes(b"LABVIEW-STUB")
        self.project = self.scratch_root / "SumVerification.lvproj"
        self.project.write_text("<Project/>")
        self.cases = self.scratch_root / "cases.json"
        self.cases.write_text(json.dumps([{
            "label": "addition", "inputs": {"Numeric": "10", "Numeric 2": "5"},
            "expect": {"Numeric 3": "15", "Numeric 4": "5"}
        }]))
        self.out = self.scratch_root / "Tests" / "Test sum.vi"
        self.manifest = self.root / "manifest.json"
        self.result_dir = self.root / "reports"
        self.job = {
            "id": "sum",
            "source": str(self.original),
            "scratch": str(self.scratch),
            "sha256": hashlib.sha256(self.original.read_bytes()).hexdigest(),
            "project": str(self.project),
            "cases": str(self.cases),
            "test_vi": str(self.out),
            "manually_reviewed": True,
            "risk_accepted_for_generation": True,
            "allow_vi_execution": False,
        }
        self.save_manifest()

    def save_manifest(self):
        self.manifest.write_text(json.dumps({
            "schema": "phase4-caraya-generation-batch-v1",
            "jobs": [self.job],
        }))

    def test_safe_preflight_does_not_generate(self):
        report = run_batch(self.manifest, self.scratch_root, self.result_dir)
        self.assertEqual("ready_for_native_generation", report["jobs"][0]["status"])
        self.assertEqual(0, report["native_executions"])
        self.assertFalse(self.out.exists())
        self.assertEqual(0, report["cloud_approved"])

    def test_blocked_when_review_missing(self):
        self.job["manually_reviewed"] = False
        self.save_manifest()
        report = run_batch(self.manifest, self.scratch_root, self.result_dir)
        self.assertEqual("blocked_review", report["jobs"][0]["status"])

    def test_blocked_when_execution_flag_true(self):
        self.job["allow_vi_execution"] = True
        self.save_manifest()
        report = run_batch(self.manifest, self.scratch_root, self.result_dir)
        self.assertEqual("blocked_review", report["jobs"][0]["status"])

    def test_hash_mismatch_blocks(self):
        self.scratch.write_bytes(b"MODIFIED")
        report = run_batch(self.manifest, self.scratch_root, self.result_dir)
        self.assertEqual("blocked_review", report["jobs"][0]["status"])

    def test_output_exists_blocks(self):
        self.out.parent.mkdir()
        self.out.write_bytes(b"old")
        report = run_batch(self.manifest, self.scratch_root, self.result_dir)
        self.assertEqual("blocked_review", report["jobs"][0]["status"])

    def test_project_outside_scratch_blocks(self):
        self.job["project"] = str(self.original)
        self.save_manifest()
        report = run_batch(self.manifest, self.scratch_root, self.result_dir)
        self.assertEqual("blocked_review", report["jobs"][0]["status"])

    def test_duplicate_labels_block(self):
        case = json.loads(self.cases.read_text())[0]
        self.cases.write_text(json.dumps([case, case]))
        report = run_batch(self.manifest, self.scratch_root, self.result_dir)
        self.assertEqual("blocked_review", report["jobs"][0]["status"])

if __name__ == "__main__":
    unittest.main()
