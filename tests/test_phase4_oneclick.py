"""Offline tests of the one-command Phase 4 orchestrator."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase4_oneclick import orchestrate


class OneClickTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scratch_root = self.root / "Scratch"
        self.scratch_root.mkdir()
        self.source = self.root / "original.vi"
        self.scratch = self.scratch_root / "sum.vi"
        for path in (self.source, self.scratch):
            path.write_bytes(b"sample VI")
        self.project = self.scratch_root / "SumVerification.lvproj"
        self.template = self.root / "FtoCVerification.lvproj"
        self.template.write_text(
            '<Project Type="Project">'
            '<Item Name="My Computer" Type="My Computer">'
            '<Item Name="old.vi" Type="VI" URL="old.vi"/></Item>'
            '</Project>', encoding="utf-8")
        self.cases = self.scratch_root / "cases.json"
        self.cases.write_text(json.dumps([{
            "label": "sum", "inputs": {"A": "1", "B": "2"},
            "expect": {"Out": "3"},
        }]), encoding="utf-8")
        self.manifest = self.root / "manifest.json"
        self.job = {
            "id": "sum", "source": str(self.source),
            "scratch": str(self.scratch),
            "project": str(self.project),
            "sha256": hashlib.sha256(b"sample VI").hexdigest(),
            "cases": str(self.cases),
            "test_vi": str(self.scratch_root / "Tests" / "Test sum.vi"),
            "manually_reviewed": False,
            "risk_accepted_for_generation": False,
            "allow_vi_execution": False,
        }
        self.save_manifest()

    def save_manifest(self):
        self.manifest.write_text(json.dumps({
            "schema": "phase4-caraya-generation-batch-v1", "jobs": [self.job]
        }), encoding="utf-8")

    def test_creates_project_and_reports_blocked_review_without_execution(self):
        out = self.root / "out-v1"
        result = orchestrate(self.manifest, self.template,
                             self.scratch_root, out, probe=False)
        self.assertEqual(1, result["projects"]["projects_created"])
        self.assertEqual("blocked_review", result["batch"]["jobs"][0]["status"])
        self.assertTrue(self.project.exists())
        self.assertEqual(0, result["native_executions"])
        self.assertFalse(result["cloud_approved"])

    def test_reuses_valid_existing_project_for_preflight(self):
        orchestrate(self.manifest, self.template, self.scratch_root,
                    self.root / "first", probe=False)
        result = orchestrate(self.manifest, self.template, self.scratch_root,
                             self.root / "second", probe=False)
        self.assertEqual(1, result["projects"]["projects_reused"])

    def test_refuses_modified_vi_hash(self):
        self.scratch.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            orchestrate(self.manifest, self.template, self.scratch_root,
                        self.root / "out", probe=False)
        self.assertFalse(self.project.exists())

    def test_does_not_automatically_approve_flags(self):
        orchestrate(self.manifest, self.template, self.scratch_root,
                    self.root / "out", probe=False)
        data = json.loads(self.manifest.read_text())
        self.assertFalse(data["jobs"][0]["manually_reviewed"])
        self.assertFalse(data["jobs"][0]["risk_accepted_for_generation"])

if __name__ == "__main__":
    unittest.main()
