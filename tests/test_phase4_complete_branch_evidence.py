import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase4_gold_evidence import record
from scripts.phase4_complete_branch_evidence import extend_evidence


class Phase4CompleteBranchEvidenceTests(unittest.TestCase):
    def test_both_branches_are_documented_but_not_gold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "original.vi"
            scratch = root / "scratch.vi"
            original.write_bytes(b"same VI")
            scratch.write_bytes(b"same VI")
            evidence = root / "first.json"
            record(original, scratch, evidence, reviewer="operator")
            revised = extend_evidence(evidence, root / "revised.json", original, scratch)
            self.assertEqual(len(revised["test_cases"]), 8)
            self.assertEqual(len(revised["false_case_tests"]), 4)
            self.assertTrue(revised["gold_candidate"])
            self.assertFalse(revised["gold_verified"])
            self.assertFalse(revised["training_eligible"])
            self.assertFalse(revised["cloud_approved"])
            self.assertEqual(json.loads((root / "first.json").read_text())["schema"],
                             "labview-ai-manual-functional-evidence-v1")
            with self.assertRaises(FileExistsError):
                extend_evidence(evidence, root / "revised.json", original, scratch)

    def test_changed_vi_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "original.vi"
            scratch = root / "scratch.vi"
            original.write_bytes(b"same")
            scratch.write_bytes(b"same")
            evidence = root / "first.json"
            record(original, scratch, evidence, reviewer="operator")
            scratch.write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "hash changed"):
                extend_evidence(evidence, root / "revision.json", original, scratch)


if __name__ == "__main__":
    unittest.main()
