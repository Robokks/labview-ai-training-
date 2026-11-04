import tempfile
import unittest
from pathlib import Path
from labview_ai_training.inventory import inventory,save

class InventoryTests(unittest.TestCase):
    def test_read_only_inventory_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"project").mkdir()
            (root/"project"/"Main.lvproj").write_text("test",encoding="utf-8")
            (root/"project"/"a.vi").write_bytes(b"same")
            (root/"project"/"b.vi").write_bytes(b"same")
            result=inventory(root)
            self.assertEqual(result["summary"]["files"],3)
            self.assertEqual(len(result["duplicate_groups"]),1)
            self.assertTrue(all(not r["cloud_approved"] for r in result["records"]))
            self.assertEqual(next(r["project_group"] for r in result["records"]
                                  if r["relative_path"].endswith("a.vi")),"project")
            save(result,root/"manifest.json")
            self.assertTrue((root/"manifest.json").exists())
            self.assertEqual((root/"project"/"a.vi").read_bytes(),b"same")
if __name__=="__main__":
    unittest.main()
