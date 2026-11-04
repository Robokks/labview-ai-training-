"""Offline benchmark scoring. It does NOT claim VI compilation or functional success."""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict
from .aixml import parse, canonicalize

def evaluate(path: Path) -> dict:
    counts = defaultdict(lambda:{"total":0,"exact":0,"aixml_parseable":0,
                                 "aixml_structural_match":0})
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row=json.loads(line)
        task=str(row["task"])
        actual=str(row["prediction"])
        expected=str(row["reference"])
        x=counts[task]
        x["total"]+=1
        if actual.strip()==expected.strip():
            x["exact"]+=1
        if task in {"text_to_aixml","aixml_syntax"}:
            try:
                a=parse(actual)
                x["aixml_parseable"]+=1
                b=parse(expected)
                # WARNING: rough shape/net-count check is NOT semantic equivalence.
                if len(a["nodes"])==len(b["nodes"]) and len(a["nets"])==len(b["nets"]):
                    x["aixml_structural_match"]+=1
            except (ValueError,KeyError,TypeError,ImportError):
                pass
            except Exception as exc:
                if exc.__class__.__name__!="ParseError":
                    raise
    return {"by_task":dict(counts),
            "limitations":[
                "Exact match and XML parsing do not prove LabVIEW generation or execution",
                "Structural match counts only node and net counts, not semantics",
                "Functional benchmark requires real LabVIEW and independent expected outputs",
            ]}

def save_evaluation(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2),encoding="utf-8")
