"""Unit tests for strict Phase 4 Caraya evidence import (no LabVIEW required)."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase4_import_caraya_evidence import (
    EXPECTED_SHA256, EXPECTED_CASES, import_caraya,
)
from unittest.mock import patch

class CarayaImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "original.vi"
        self.scratch = self.root / "scratch.vi"
        self.test_vi = self.root / "Test F to C.vi"
        for path in (self.original, self.scratch, self.test_vi):
            path.write_bytes(b"test binary")
        self.evidence = self.root / "manual.json"
        self.evidence.write_text(json.dumps({
            "schema": "labview-ai-manual-functional-evidence-v2",
            "source_sha256": EXPECTED_SHA256,
            "scratch_sha256": EXPECTED_SHA256,
            "test_environment": {"labview_version": "2026"},
            "test_cases": [{"result": "reported_pass"}] * 8,
        }), encoding="utf-8")
        self.junit = self.root / "caraya.xml"
        self.output = self.root / "native.json"
        self.write_xml()
        self.hash_patch = patch("scripts.phase4_import_caraya_evidence.sha256",
            side_effect=lambda path: EXPECTED_SHA256 if path in (self.original, self.scratch)
            else "f" * 64)
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)

    def write_xml(self, *, names=None, failures=0):
        names = sorted(EXPECTED_CASES) if names is None else names
        cases = "".join(f'<testcase classname="Test F to C" name="{name}"/>' for name in names)
        self.junit.write_text(
            '<testsuites framework-name="Caraya" framework-version="1.4.4.148">'
            f'<testsuite name="Test F to C" tests="8" failures="{failures}" '
            'errors="0" skipped="0" timestamp="2026-11-04T23:45:14.261">'
            f'{cases}</testsuite></testsuites>', encoding="utf-8")

    def import_it(self):
        return import_caraya(self.junit, self.evidence, self.original,
                             self.scratch, self.test_vi, self.output)

    def test_clean_junit_passes_without_training_approval(self):
        r = self.import_it()
        self.assertTrue(r["native_functional_verified"])
        self.assertFalse(r["gold_verified"])
        self.assertFalse(r["training_eligible"])
        self.assertFalse(r["cloud_approved"])
        self.assertEqual(8, r["junit_counts"]["tests"])
        self.assertTrue(self.output.is_file())

    def test_failure_counter_refused(self):
        self.write_xml(failures=1)
        with self.assertRaises(ValueError):
            self.import_it()
        self.assertFalse(self.output.exists())

    def test_missing_case_refused(self):
        self.write_xml(names=sorted(EXPECTED_CASES)[:-1])
        with self.assertRaises(ValueError):
            self.import_it()

    def test_duplicate_case_refused(self):
        names = sorted(EXPECTED_CASES)
        self.write_xml(names=names[:-1] + [names[0]])
        with self.assertRaises(ValueError):
            self.import_it()

    def test_existing_output_refused(self):
        self.output.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.import_it()
        self.assertEqual("existing", self.output.read_text())

    def test_changed_scratch_hash_refused(self):
        self.hash_patch.stop()
        with patch("scripts.phase4_import_caraya_evidence.sha256", return_value="0"*64):
            with self.assertRaises(ValueError):
                self.import_it()

if __name__ == "__main__":
    unittest.main()
