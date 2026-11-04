import json
import tempfile
import unittest
from pathlib import Path
from scripts.phase4_gold_evidence import record


class GoldEvidenceTests(unittest.TestCase):
    def test_matching_scratch_copy_records_manual_candidate_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "source.vi"
            copy = root / "copy.vi"
            original.write_bytes(b"labview")
            copy.write_bytes(b"labview")
            target = root / "evidence.json"
            result = record(original, copy, target, reviewer="operator")
            self.assertTrue(result["binary_matches_original"])
            self.assertTrue(result["gold_candidate"])
            self.assertFalse(result["gold_verified"])
            self.assertFalse(result["cloud_approved"])
            self.assertFalse(result["training_eligible"])
            self.assertEqual(len(result["test_cases"]), 4)
            self.assertEqual(json.loads(target.read_text())["quality_label"], "manual_functional_candidate")
            with self.assertRaises(FileExistsError):
                record(original, copy, target, reviewer="operator")

    def test_modified_copy_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "source.vi"
            copy = root / "copy.vi"
            original.write_bytes(b"old")
            copy.write_bytes(b"changed")
            result = record(original, copy, root / "evidence.json", reviewer="operator")
            self.assertFalse(result["binary_matches_original"])
            self.assertFalse(result["gold_candidate"])
            self.assertFalse(result["gold_verified"])

    def test_source_and_copy_must_be_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "VI.vi"
            path.write_bytes(b"test")
            with self.assertRaises(ValueError):
                record(path, path, Path(temp)/"evidence.json", reviewer="operator")


if __name__ == "__main__":
    unittest.main()
