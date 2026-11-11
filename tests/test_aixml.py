import tempfile
import unittest
from pathlib import Path
from labview_ai_training import aixml

SAMPLE='''<VI _name="Add.vi" description="Add two numbers">
  <Control _name="a" uid="1" outputs="value:1.value" type="double" value="1"/>
  <Control _name="b" uid="2" outputs="value:2.value" type="double" value="2"/>
  <Node _name="Add" uid="3" inputs="x:1.value,y:2.value" outputs="x+y:3.x+y"/>
  <Indicator _name="sum" uid="4" inputs="value:3.x+y" value="0" type="double"/>
</VI>'''

class AIXMLTests(unittest.TestCase):
    def test_parse_and_preserve_nets(self):
        graph=aixml.parse(SAMPLE)
        self.assertEqual(graph["vi_name"],"Add.vi")
        self.assertEqual(len(graph["nets"]),3)
        self.assertEqual(len(graph["nodes"]),5)
        self.assertEqual(graph["nets"]["1.value"][1]["direction"],"input")
        self.assertIn("No execution direction", graph["limitations"][0])
    def test_for_loop_count_joins_source_net(self):
        graph = aixml.parse('<VI><Control uid="1" outputs="value:1.value"/>'
                            '<Structure _name="For Loop" uid="2" maxin="1.value"/></VI>')
        endpoints = [(p["uid"], p["terminal"], p["direction"]) for p in graph["nets"]["1.value"]]
        self.assertEqual(endpoints, [("1", "value", "output"), ("2", "maxin", "input")])

    def test_case_selector_joins_source_net(self):
        graph = aixml.parse('<VI><Control uid="1" outputs="value:1.value"/>'
                            '<Structure _name="Case Structure" uid="2" selectin="1.value">'
                            '<CaseFrame uid="3" selector="True"/></Structure></VI>')
        endpoints = [(p["uid"], p["terminal"], p["direction"]) for p in graph["nets"]["1.value"]]
        self.assertEqual(endpoints, [("1", "value", "output"), ("2", "selectin", "input")])

    def test_canonicalized(self):
        c=aixml.canonicalize(SAMPLE)
        self.assertEqual(aixml.parse(c)["nets"], aixml.parse(SAMPLE)["nets"])
    def test_backend_pane_metadata_survives_normalization(self):
        text = SAMPLE + '<?lvmcp pane="4833"?>'
        for source in (text, aixml.canonicalize(text)):
            self.assertEqual(aixml.parse(source)["processing_instructions"], ['lvmcp pane="4833"'])

    def test_nested_node_declaring_root_is_flagged(self):
        text = '<VI><Structure uid="1"><Node uid="2" uid_parent="root"/></Structure></VI>'
        self.assertTrue(aixml.parse(text)["warnings"])

    def test_call_link_pi_preserves_literal_entities(self):
        xml = SAMPLE + '<?lvmcp calllink path="&lt;vilib&gt;|numeric"?>'
        normalized = aixml.canonicalize(xml)
        self.assertEqual(aixml.parse(xml), aixml.parse(normalized))
        self.assertEqual(normalized, aixml.canonicalize(normalized))

    def test_reject_entity(self):
        with self.assertRaises(ValueError):
            aixml.parse('<!DOCTYPE VI [<!ENTITY ex "x">]><VI/>')
    def test_root_must_be_vi(self):
        with self.assertRaises(ValueError):
            aixml.parse("<Project/>")
    def test_duplicate_uid_warning(self):
        data='<VI><Node uid="1"/><Node uid="1"/></VI>'
        self.assertTrue(aixml.parse(data)["warnings"])
if __name__=="__main__":
    unittest.main()
