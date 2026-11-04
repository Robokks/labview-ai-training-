import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase4_native_f_to_c import CASES, execute, preflight


class FakeVI:
    def __init__(self):
        self.controls = {}
        self.run_count = 0

    def SetControlValue(self, name, value):
        self.controls[name] = value

    def Run(self, wait):
        assert wait is True
        self.run_count += 1
        f = self.controls["Farenheit"]
        self.controls["Celcius"] = (f - 32) * 5 / 9 if self.controls["Boolean"] else f

    def GetControlValue(self, name):
        return self.controls[name]


class FakeApp:
    Version = "26.3.1f1"

    def __init__(self):
        self.vi = FakeVI()

    def GetVIReference(self, name):
        return self.vi


class NativeFTocTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "original.vi"
        self.vi = self.root / "F to C (SUB VI).vi"
        self.evidence = self.root / "evidence.json"
        self.out = self.root / "result.json"
        # Mock the anchored SHA without weakening production's hash check.
        from unittest.mock import patch
        self.patch = patch("scripts.phase4_native_f_to_c.EXPECTED_SHA", hashlib.sha256(b"demo").hexdigest())
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.original.write_bytes(b"demo")
        self.vi.write_bytes(b"demo")
        self.evidence.write_text(json.dumps({
            "schema": "labview-ai-manual-functional-evidence-v2",
            "source_sha256": hashlib.sha256(b"demo").hexdigest(),
            "scratch_sha256": hashlib.sha256(b"demo").hexdigest(),
            "original_path_local": str(self.original),
            "scratch_path_local": str(self.vi),
            "test_cases": [{"result": "reported_pass"} for _ in CASES]}))

    def test_eight_automated_cases_with_mock_app(self):
        app = FakeApp()
        result = execute(self.vi, self.original, self.evidence, self.out, app=app, allow_run=True)
        self.assertEqual(result["passed"], 8)
        self.assertTrue(result["all_passed"])
        self.assertEqual(app.vi.run_count, 8)
        self.assertFalse(result["gold_verified"])
        self.assertFalse(result["training_eligible"])
        self.assertEqual(len(json.loads(self.out.read_text())["tests"]), 8)

    def test_mismatched_binary_is_rejected(self):
        self.vi.write_bytes(b"not demo")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            preflight(self.vi, self.original, self.evidence, self.out)

    def test_run_requires_explicit_flag(self):
        with self.assertRaisesRegex(ValueError, "requires --run"):
            execute(self.vi, self.original, self.evidence, self.out, app=FakeApp())
        self.assertFalse(self.out.exists())

    def test_wrong_labview_version_rejected(self):
        app = FakeApp()
        app.Version = "25.0"
        with self.assertRaisesRegex(RuntimeError, "Expected LabVIEW 2026"):
            execute(self.vi, self.original, self.evidence, self.out, app=app, allow_run=True)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
