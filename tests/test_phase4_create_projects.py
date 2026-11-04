"""Tests for automatic scratch-only LabVIEW project creation."""
import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.phase4_create_projects import create_from_manifest, create_project


class CreateProjectTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.scratch_root = self.root / "scratch"
        self.scratch_root.mkdir()
        self.scratch = self.scratch_root / "sum.vi"
        self.original = self.root / "source.vi"
        self.original.write_bytes(b"unchanged")
        self.scratch.write_bytes(b"unchanged")
        self.project = self.scratch_root / "SumVerification.lvproj"
        self.template = self.root / "FtoCVerification.lvproj"
        self.template.write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<Project Type="Project" LVVersion="26008000">'
            '<Property Name="ProjectDescription" Type="Str">old</Property>'
            '<Item Name="My Computer" Type="My Computer">'
            '<Property Name="server.app.propertiesEnabled" Type="Bool">true</Property>'
            '<Item Name="F to C (SUB VI).vi" Type="VI" URL="F to C (SUB VI).vi"/>'
            '<Item Name="Tests" Type="Folder">'
            '<Item Name="Test F to C.vi" Type="VI" URL="Tests/Test F to C.vi"/>'
            '</Item></Item>'
            '<Item Name="Dependencies" Type="Dependencies"/>'
            '</Project>', encoding="utf-8")
        self.manifest = self.root / "manifest.json"
        self.expected_hash = hashlib.sha256(self.original.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps({
            "schema": "phase4-caraya-generation-batch-v1",
            "jobs": [{"id": "sum", "source": str(self.original),
                      "scratch": str(self.scratch), "project": str(self.project),
                      "sha256": self.expected_hash}],
        }), encoding="utf-8")

    def test_cloned_project_contains_only_scratch_vi(self):
        r = create_project(self.template, self.scratch, self.project,
                           scratch_root=self.scratch_root,
                           expected_sha256=self.expected_hash)
        self.assertEqual(1, r["vi_entries"])
        xml = ET.parse(self.project).getroot()
        items = [i for i in xml.iter("Item") if i.get("Type") == "VI"]
        self.assertEqual([("sum.vi", "sum.vi")],
                         [(i.get("Name"), i.get("URL")) for i in items])
        self.assertEqual(b"unchanged", self.scratch.read_bytes())
        self.assertTrue(self.template.exists())
        self.assertFalse(r["native_executed"])

    def test_manifest_builds_project(self):
        result = create_from_manifest(self.template, self.manifest, self.scratch_root)
        self.assertEqual(1, result["projects_created"])
        self.assertTrue(self.project.is_file())
        self.assertEqual(0, result["native_executions"])

    def test_refuses_existing_project(self):
        self.project.write_text("existing")
        with self.assertRaises(FileExistsError):
            create_from_manifest(self.template, self.manifest, self.scratch_root)
        self.assertEqual("existing", self.project.read_text())

    def test_refuses_scratch_hash_mismatch(self):
        self.scratch.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            create_from_manifest(self.template, self.manifest, self.scratch_root)
        self.assertFalse(self.project.exists())

    def test_refuses_project_outside_scratch(self):
        with self.assertRaises(ValueError):
            create_project(self.template, self.scratch, self.root / "wrong.lvproj",
                           scratch_root=self.scratch_root)

    def test_refuses_bad_template(self):
        self.template.write_text("<NotProject/>")
        with self.assertRaises(ValueError):
            create_from_manifest(self.template, self.manifest, self.scratch_root)
        self.assertFalse(self.project.exists())

    def test_refuses_original_as_scratch(self):
        data = json.loads(self.manifest.read_text())
        data["jobs"][0]["source"] = str(self.scratch)
        self.manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            create_from_manifest(self.template, self.manifest, self.scratch_root)

if __name__ == "__main__":
    unittest.main()
