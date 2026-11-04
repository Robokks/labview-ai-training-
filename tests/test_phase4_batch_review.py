"""Tests for offline Phase 4 screening and scratch-only staging."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.phase4_batch_review import inspect, stage

class BatchReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source_root = self.root / "source"
        self.source_root.mkdir()
        self.payload = b"fake labview bytes"
        self.sha = hashlib.sha256(self.payload).hexdigest()
        self.path = "TASK/Math/Temperature Conversion.vi"
        vi = self.source_root.joinpath(*self.path.split("/"))
        vi.parent.mkdir(parents=True)
        vi.write_bytes(self.payload)
        self.index = self.root / "structural-index.jsonl"
        self.archive = self.root / "bundle.zip"
        self.plan = self.root / "plan.json"
        self.approval = self.root / "approval.json"
        self.report = self.root / "staged.json"
        self.scratch = self.root / "scratch"
        self.set_candidates([(self.sha, self.path, "Temperature Conversion.vi", [])])

    def set_candidates(self, rows):
        index = []
        with zipfile.ZipFile(self.archive, "w") as z:
            for sha, path, name, nodes in rows:
                index.append({
                    "sha256": sha, "quality": "silver_structural_candidate",
                    "structurally_verified": True,
                    "project_family": "TASK", "source_paths": [path]
                })
                z.writestr(f"{sha}/graph.json",
                           json.dumps({"vi_name": name, "nodes": nodes}))
        self.index.write_text("".join(json.dumps(x)+"\n" for x in index), encoding="utf-8")

    def screen(self):
        return inspect(self.index, self.archive, self.plan)

    def approve(self, sha=None):
        self.approval.write_text(json.dumps({
            "schema": "phase4-scratch-staging-approval-v1",
            "reviewer": "local_reviewer",
            "approved_sha256": [sha or self.sha],
            "safe_for_scratch_copy": True,
            "authorizes_vi_execution": False,
        }), encoding="utf-8")

    def test_math_name_shortlisted_but_not_authorized(self):
        result = self.screen()
        self.assertEqual(1, len(result["shortlist"]))
        self.assertFalse(result["shortlist"][0]["execution_authorized"])
        self.assertFalse(result["cloud_approved"])

    def test_dangerous_name_never_shortlisted(self):
        self.set_candidates([(self.sha, "TASK/Math/DAQ Temperature Conversion.vi",
                              "DAQ Temperature Conversion.vi", [])])
        result = self.screen()
        self.assertEqual([], result["shortlist"])
        self.assertEqual(1, result["counts"]["excluded_keyword_risk"])

    def test_dangerous_node_never_shortlisted(self):
        self.set_candidates([(self.sha, self.path, "Temperature Conversion.vi",
                              [{"name": "TCP Write"}])])
        self.assertEqual([], self.screen()["shortlist"])

    def test_staging_requires_explicit_approval(self):
        self.screen()
        with self.assertRaises(FileNotFoundError):
            stage(self.plan, self.approval, self.source_root, self.scratch, self.report)

    def test_staging_verifies_sha_and_copies_only(self):
        self.screen()
        self.approve()
        result = stage(self.plan, self.approval, self.source_root, self.scratch, self.report)
        self.assertEqual(1, len(result["copies"]))
        copied = Path(result["copies"][0]["scratch_local"])
        self.assertEqual(self.payload, copied.read_bytes())
        self.assertFalse(result["cloud_approved"])
        self.assertEqual("NOT AUTHORIZED", result["native_execution"])

    def test_staging_rejects_bad_hash(self):
        self.screen()
        self.approve()
        self.source_root.joinpath(*self.path.split("/")).write_bytes(b"changed")
        with self.assertRaises(FileNotFoundError):
            stage(self.plan, self.approval, self.source_root, self.scratch, self.report)

    def test_staging_rejects_execution_approval(self):
        self.screen()
        self.approve()
        data = json.loads(self.approval.read_text())
        data["authorizes_vi_execution"] = True
        self.approval.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            stage(self.plan, self.approval, self.source_root, self.scratch, self.report)

    def test_no_overwrite_of_existing_plan(self):
        self.screen()
        with self.assertRaises(FileExistsError):
            self.screen()

    def test_no_overwrite_of_staged_binary(self):
        self.screen()
        self.approve()
        stage(self.plan, self.approval, self.source_root, self.scratch, self.report)
        self.report.unlink()
        with self.assertRaises(FileExistsError):
            stage(self.plan, self.approval, self.source_root, self.scratch, self.report)

if __name__ == "__main__":
    unittest.main()
