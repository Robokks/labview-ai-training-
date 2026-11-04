"""Unit tests for Caraya batch JUnit evidence collector."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase4_collect_batch_junit import collect


class BatchJUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.vi"
        self.scratch = self.root / "scratch.vi"
        self.test_vi = self.root / "Test sum.vi"
        self.junit = self.root / "Test sum.xml"
        self.cases = self.root / "cases.json"
        self.manifest = self.root / "manifest.json"
        self.out = self.root / "evidence.json"
        for p in (self.source, self.scratch, self.test_vi):
            p.write_bytes(b"binary")
        self.cases.write_text(json.dumps([{
            "label": "positive", "inputs": {"Numeric": "1"},
            "expect": {"Numeric 3": "1"}
        }]))
        self.write_xml()
        self.job = {
            "id": "sum", "source": str(self.source), "scratch": str(self.scratch),
            "test_vi": str(self.test_vi), "cases": str(self.cases),
            "junit": str(self.junit), "suite_name": "Test sum",
            "sha256": hashlib.sha256(b"binary").hexdigest(),
        }
        self.save_manifest()

    def write_xml(self, name="positive", failures=0):
        self.junit.write_text(
            '<testsuites framework-name="Caraya" framework-version="1.4.4.148">'
            f'<testsuite name="Test sum" tests="1" failures="{failures}" errors="0" skipped="0">'
            f'<testcase classname="Test sum" name="{name}"/>'
            '</testsuite></testsuites>'
        )

    def save_manifest(self):
        self.manifest.write_text(json.dumps({
            "schema": "phase4-caraya-generation-batch-v1", "jobs": [self.job]}))

    def test_valid_xml_yields_functional_candidate_only(self):
        result = collect(self.manifest, self.out)
        self.assertEqual(1, result["vis_verified_by_junit"])
        self.assertEqual(1, result["cases_verified"])
        self.assertEqual(0, result["training_eligible"])
        self.assertFalse(result["jobs"][0]["gold_verified"])

    def test_failed_assertion_is_blocked(self):
        self.write_xml(failures=1)
        result = collect(self.manifest, self.out)
        self.assertEqual(0, result["vis_verified_by_junit"])

    def test_wrong_case_name_is_blocked(self):
        self.write_xml(name="incorrect")
        self.assertEqual("blocked_or_failed", collect(self.manifest, self.out)["jobs"][0]["status"])

    def test_missing_junit_is_blocked(self):
        self.junit.unlink()
        self.assertEqual(0, collect(self.manifest, self.out)["vis_verified_by_junit"])

    def test_changed_scratch_is_blocked(self):
        self.scratch.write_bytes(b"changed")
        self.assertEqual(0, collect(self.manifest, self.out)["vis_verified_by_junit"])

    def test_refuse_overwriting_evidence(self):
        self.out.write_text("existing")
        with self.assertRaises(FileExistsError):
            collect(self.manifest, self.out)
        self.assertEqual("existing", self.out.read_text())

if __name__ == "__main__":
    unittest.main()
