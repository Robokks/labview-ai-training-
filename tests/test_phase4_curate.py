import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.phase4_curate import audit, family


class Phase4CurationTests(unittest.TestCase):
    def test_family_boundary(self):
        self.assertEqual(family("TASK/a.vi", ["TASK", "TASK2"]), "TASK")
        with self.assertRaises(ValueError):
            family("TASK3/a.vi", ["TASK"])

    def test_converted_is_bronze_not_approved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sha = hashlib.sha256(b"one").hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"roots": ["TASK"], "records": [
                {"sha256": sha, "source_paths": ["TASK/a.vi"], "status": "converted",
                 "warnings": [], "nodes": 3, "backend": "pylabview", "cloud_approved": False}]}))
            result = audit(manifest, root / "output")
            self.assertEqual(result["indexed_provisional"], 1)
            self.assertEqual(result["training_eligible"], 0)
            row = json.loads((root / "output" / "local-bronze-index.jsonl").read_text())
            self.assertEqual(row["quality"], "bronze")
            self.assertFalse(row["cloud_approved"])

    def test_duplicates_and_failed_are_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sha = hashlib.sha256(b"one").hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"roots": ["TASK"], "records": [
                {"sha256": sha, "source_paths": ["TASK/a.vi"], "status": "converted", "warnings": []},
                {"sha256": sha, "source_paths": ["TASK/a.vi"], "status": "converted", "warnings": []},
                {"sha256": hashlib.sha256(b"two").hexdigest(), "source_paths": ["TASK/b.vi"],
                 "status": "failed", "warnings": []}]}))
            result = audit(manifest, root / "output")
            self.assertEqual(result["indexed_provisional"], 1)
            self.assertEqual(len(result["issues"]), 2)


if __name__ == "__main__":
    unittest.main()
