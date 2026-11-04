import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.phase4_review_plan import build


class Phase4ReviewPlanTests(unittest.TestCase):
    def test_permissions_fail_closed_and_families_stay_together(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            rows = []
            for family in ("TASK", "OTHER"):
                for n in range(3):
                    rows.append({"sha256": hashlib.sha256(f"{family}-{n}".encode()).hexdigest(),
                                 "source_paths": [f"{family}/{n}.vi"],
                                 "project_family": family, "quality": "silver_structural_candidate",
                                 "structurally_verified": True})
            rows.append({"sha256": hashlib.sha256(b"failed").hexdigest(),
                         "quality": "excluded", "structurally_verified": False})
            source = p / "structural-index.jsonl"
            source.write_text("".join(json.dumps(r)+"\n" for r in rows), encoding="utf-8")
            report = build(source, p / "result", sample_per_family=2)
            self.assertEqual(report["silver_candidates"], 6)
            self.assertEqual(report["previously_excluded"], 1)
            self.assertEqual(report["native_queue_count"], 4)
            self.assertEqual(report["cloud_approved"], 0)
            self.assertEqual(report["training_eligible"], 0)
            planned = [json.loads(s) for s in (p/"result"/"split-plan.jsonl").read_text().splitlines()]
            self.assertTrue(all(not r["training_eligible"] and not r["cloud_approved"] for r in planned))
            self.assertEqual(len({r["planned_split"] for r in planned if r["project_family"] == "TASK"}), 1)
            with (p/"result"/"permission-review.csv").open(newline="", encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 2)

    def test_duplicate_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            item = {"sha256": "a"*64, "source_paths": ["TASK/a.vi"],
                    "project_family": "TASK", "structurally_verified": True,
                    "quality": "silver_structural_candidate"}
            source = p / "index.jsonl"
            source.write_text(json.dumps(item)+"\n"+json.dumps(item)+"\n")
            with self.assertRaisesRegex(ValueError, "duplicate_sha256"):
                build(source, p/"result")

    def test_no_automatic_heldout_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            item = {"sha256": "a"*64, "source_paths": ["TASK/a.vi"],
                    "project_family": "TASK", "structurally_verified": True,
                    "quality": "silver_structural_candidate"}
            source = p / "index.jsonl"
            source.write_text(json.dumps(item)+"\n")
            result = build(source, p/"result")
            self.assertTrue(result["held_out_warning"])
            self.assertEqual(result["native_queue_count"], 1)


if __name__ == "__main__":
    unittest.main()
