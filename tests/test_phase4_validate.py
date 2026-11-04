import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from labview_ai_training import aixml
from scripts.phase4_validate import validate

class Phase4StructuralTests(unittest.TestCase):
    def fixture(self, folder, broken=False):
        sha = hashlib.sha256(b"vi").hexdigest()
        raw = '<VI _name="Demo.vi"><Control _name="A" uid="1" outputs="value:1.value"/></VI>'
        manifest = folder / "batch-results.json"
        manifest.write_text(json.dumps({"roots":["TASK"],"records":[
            {"sha256":sha,"source_paths":["TASK/Demo.vi"],"status":"converted","nodes":2,"warnings":[]},
            {"sha256":"f"*64,"source_paths":["TASK/Bad.vi"],"status":"failed"}]}))
        archive = folder / "batch-conversion.zip"
        with zipfile.ZipFile(archive,"w") as z:
            z.writestr(sha+"/raw.aixml",raw)
            z.writestr(sha+"/normalized.aixml",aixml.canonicalize(raw))
            z.writestr(sha+"/graph.json","{}" if broken else json.dumps(aixml.parse(raw)))
        return manifest,archive

    def test_matching_representations_are_not_training_approved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            manifest,archive=self.fixture(root)
            report=validate(manifest,archive,root/"out")
            self.assertEqual(report["structurally_verified"],1)
            self.assertEqual(report["training_eligible"],0)
            self.assertEqual(report["cloud_approved"],0)
            self.assertEqual(report["counts"]["excluded"],1)

    def test_graph_mismatch_remains_bronze(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            manifest,archive=self.fixture(root,broken=True)
            report=validate(manifest,archive,root/"out")
            self.assertEqual(report["counts"]["bronze"],1)
            self.assertEqual(report["structurally_verified"],0)

    def test_missing_archive_records_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            manifest,archive=self.fixture(root)
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("unrelated.txt","test")
            report=validate(manifest,archive,root/"out")
            self.assertEqual(report["structurally_verified"],0)

if __name__=="__main__":
    unittest.main()
