"""Loss-conscious AIXML reader: net references are not inferred execution edges."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from io import StringIO
import re
from pathlib import Path
from collections import defaultdict

def _safe(text: str) -> None:
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("DTD and entity declarations are not allowed")

def _ports(raw: str) -> list[dict]:
    out = []
    for token in filter(None, raw.split(",")):
        if ":" not in token:
            out.append({"raw":token,"invalid":True})
        else:
            terminal,net = token.split(":",1)
            out.append({"terminal":terminal,"net":net,"raw":token})
    return out

def parse(text: str) -> dict:
    _safe(text)
    events = ET.iterparse(StringIO(text), events=("pi",))
    processing_instructions = [element.text for _, element in events]
    root = events.root
    if root.tag != "VI":
        raise ValueError("Expected top-level VI element")
    nodes, warnings = [], []
    nets = defaultdict(list)
    seen = set()
    def visit(e: ET.Element, container: str | None = None):
        uid = e.get("uid")
        if uid is not None:
            if uid in seen:
                warnings.append(f"Duplicate UID: {uid}")
            seen.add(uid)
        parent = e.get("uid_parent")
        if parent and parent != (container or "root"):
            warnings.append(f"UID parent/nesting mismatch: {uid} -> {parent}")
        idx = len(nodes)
        node = {"kind":e.tag,"uid":uid,"name":e.get("_name"),
                "container_uid":container,"declared_parent_uid":parent,
                "attributes":dict(e.attrib),
                "inputs":_ports(e.get("inputs","")),
                "outputs":_ports(e.get("outputs",""))}
        if e.tag == "Structure" and node["name"] == "For Loop" and e.get("maxin"):
            net = e.attrib["maxin"]
            node["inputs"].append({"terminal": "maxin", "net": net, "raw": net})
        nodes.append(node)
        for direction in ("inputs","outputs"):
            for port in node[direction]:
                if port.get("net"):
                    nets[port["net"]].append({
                        "node_index":idx,"uid":uid,
                        "terminal":port["terminal"],
                        "direction":direction[:-1]})
                if port.get("invalid"):
                    warnings.append(f"Malformed terminal binding: {port['raw']}")
        for child in e:
            visit(child,uid if uid is not None else container)
    visit(root)
    return {"format":"labview-aixml-graph-v1","vi_name":root.get("_name"),
            "nodes":nodes,"nets":dict(nets),"warnings":warnings,
            "processing_instructions":processing_instructions,
            "limitations":["No execution direction inferred from net identifiers",
                           "AIXML may omit native VI attributes and diagram layout"]}

def canonicalize(text: str) -> str:
    """Stable XML serialization. UIDs and nets deliberately remain UNCHANGED."""
    parse(text)
    instructions = iter(parse(text)["processing_instructions"])
    normalized = ET.canonicalize(text,strip_text=False)
    # ElementTree escapes ampersands in PI data even though PIs contain literal text.
    return re.sub(r"<\?.*?\?>", lambda _: "<?" + next(instructions) + "?>",
                  normalized, flags=re.DOTALL)

def load(path: Path) -> dict:
    return parse(path.read_text(encoding="utf-8-sig"))
