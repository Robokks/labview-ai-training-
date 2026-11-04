import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase4_retry import retry


class Phase4RetryTests(unittest.TestCase):
    def test_dry_run_and_successful_resumable_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vi = root / "source" / "Example.vi"
            vi.parent.mkdir()
            vi.write_bytes(b"test")
            manifest = root / "batch-results.json"
            manifest.write_text(json.dumps({"records": [{"source_paths": ["Example.vi"],
                "sha256": hashlib.sha256(b"test").hexdigest(), "status": "failed"}]}))
            converter = root / "converter.py"
            converter.write_text('import sys\nfrom pathlib import Path\n'
                'Path(sys.argv[2]).write_text(\'<VI _name="Example.vi"/>\')\n')
            out = root / "out"
            self.assertEqual(retry(manifest, vi.parent, out)["attempted"], 0)
            self.assertEqual(retry(manifest, vi.parent, out, converter, True)["converted"], 1)
            self.assertEqual(json.loads((out / "batch-results.json").read_text())["records"][0]["status"], "converted")
            self.assertEqual(retry(out / "batch-results.json", vi.parent, out, converter, True)["attempted"], 0)
            self.assertEqual(vi.read_bytes(), b"test")

    def test_source_hash_change_blocks_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vi = root / "Example.vi"
            vi.write_bytes(b"changed")
            manifest = root / "batch.json"
            manifest.write_text(json.dumps({"records": [{"source_paths": ["Example.vi"],
                "sha256": "0" * 64, "status": "failed"}]}))
            report = retry(manifest, root, root / "out")
            self.assertEqual(report["errors"][0]["reason"], "source_hash_mismatch")


if __name__ == "__main__":
    unittest.main()
