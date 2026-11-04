import json
import tempfile
import unittest
from pathlib import Path
from labview_ai_training.dataset import prepare,split_for_project,reason_to_reject

def row(**kw):
    r={"source_id":"sample-1","source_project":"sample-public",
       "task":"text_to_aixml","instruction":"Add two numbers",
       "output":"<VI _name='Add' description='Add'/>",
       "quality":"gold","validation":{"functional":True},
       "cloud_approved":True,"contains_confidential":False}
    r.update(kw)
    return r

class SFTTests(unittest.TestCase):
    def test_defaults_fail_closed(self):
        self.assertEqual(reason_to_reject({}),"no_cloud_permission")
        self.assertEqual(reason_to_reject(row(cloud_approved=False)),"no_cloud_permission")
        self.assertEqual(reason_to_reject(row(contains_confidential=True)),"confidential_or_unknown")
        self.assertEqual(reason_to_reject(row(quality="bronze")),"bronze_or_unknown_quality")
    def test_silver_restricted(self):
        self.assertEqual(reason_to_reject(row(quality="silver",validation={"syntax":True})),
                         "silver_unverified_behavior")
        self.assertIsNone(reason_to_reject(row(task="aixml_syntax",quality="silver",
                                              validation={"syntax":True})))
    def test_group_split_is_stable(self):
        self.assertEqual(split_for_project("project-1"),split_for_project("project-1"))
    def test_prepare_approval_and_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            records=[row(),row(),row(source_id="bad",cloud_approved=False,
                                     instruction="Unapproved")]
            input_file=base/"in.jsonl"
            input_file.write_text("\n".join(json.dumps(r) for r in records),encoding="utf-8")
            summary=prepare(input_file,base/"out")
            self.assertEqual(sum(summary["accepted"].values()),1)
            self.assertEqual(summary["rejected"]["duplicate_pair"],1)
            self.assertEqual(summary["rejected"]["no_cloud_permission"],1)
if __name__=="__main__":
    unittest.main()
