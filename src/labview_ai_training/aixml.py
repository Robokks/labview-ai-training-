"""Loss-conscious AIXML reader: net references are not inferred execution edges."""
from __future__ import annotations
import xml.etree.ElementTree as ET
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
    root = ET.fromstring(text)
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
        if parent and parent not in ("root", container):
            warnings.append(f"UID parent/nesting mismatch: {uid} -> {parent}")
        idx = len(nodes)
        node = {"kind":e.tag,"uid":uid,"name":e.get("_name"),
                "container_uid":container,"declared_parent_uid":parent,
                "attributes":dict(e.attrib),
                "inputs":_ports(e.get("inputs","")),
                "outputs":_ports(e.get("outputs",""))}
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
            "limitations":["No execution direction inferred from net identifiers",
                           "AIXML may omit native VI attributes and diagram layout"]}

def canonicalize(text: str) -> str:
    """Stable XML serialization. UIDs and nets deliberately remain UNCHANGED."""
    parse(text)
    return ET.canonicalize(text,strip_text=False)

def load(path: Path) -> dict:
    return parse(path.read_text(encoding="utf-8-sig"))
