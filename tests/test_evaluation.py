import json
import tempfile
import unittest
from pathlib import Path
from labview_ai_training.evaluation import evaluate

class EvaluateTests(unittest.TestCase):
    def test_parseable_is_not_functionally_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"pred.jsonl"
            good='<VI _name="Test.vi" description="Example"/>'
            path.write_text(json.dumps({"task":"text_to_aixml",
                                        "prediction":good,"reference":good})+"\n")
            report=evaluate(path)
            item=report["by_task"]["text_to_aixml"]
            self.assertEqual(item["total"],1)
            self.assertEqual(item["exact"],1)
            self.assertEqual(item["aixml_parseable"],1)
            self.assertIn("do not prove", report["limitations"][0])
if __name__=="__main__":
    unittest.main()
