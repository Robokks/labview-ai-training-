"""Quality-aware and consent-gated SFT JSONL generation. Never uploads data."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from collections import Counter

TASKS = {"text_to_aixml","text_to_graph","graph_to_explanation",
         "aixml_syntax","graph_structure","error_to_fix","project_architecture"}
SILVER_ALLOWED = {"aixml_syntax","graph_structure"}
SYSTEM = ("You are a LabVIEW programming assistant. Preserve precise terminal names, "
          "nets, structure nesting and data types. Do not assert unverified behavior.")

def split_for_project(project: str, seed: str = "v1") -> str:
    value = int(hashlib.sha256(f"{seed}:{project}".encode()).hexdigest()[:12],16) % 100
    return "train" if value < 80 else "validation" if value < 90 else "test"

def reason_to_reject(row: dict) -> str | None:
    if row.get("cloud_approved") is not True:
        return "no_cloud_permission"
    if row.get("contains_confidential") is not False:
        return "confidential_or_unknown"
    for field in ("source_id","source_project","task","instruction","output"):
        if not isinstance(row.get(field),str) or not row[field].strip():
            return "missing_"+field
    if row["task"] not in TASKS:
        return "unknown_task"
    quality, proof = row.get("quality"),row.get("validation",{})
    if not isinstance(proof,dict):
        return "invalid_validation"
    if quality=="gold":
        if proof.get("functional") is not True:
            return "gold_without_functional_proof"
    elif quality=="silver":
        if row["task"] not in SILVER_ALLOWED:
            return "silver_unverified_behavior"
        if not (proof.get("syntax") is True or proof.get("structural") is True):
            return "silver_without_structure_proof"
    else:
        return "bronze_or_unknown_quality"
    return None

def prepare(input_path: Path, output_dir: Path, seed: str="v1") -> dict:
    output_dir.mkdir(parents=True,exist_ok=True)
    results = {s:[] for s in ("train","validation","test")}
    rejected = Counter()
    seen = set()
    for line in input_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            if not isinstance(record,dict):
                raise ValueError
        except (ValueError,json.JSONDecodeError):
            rejected["invalid_json"]+=1
            continue
        reason=reason_to_reject(record)
        if reason:
            rejected[reason]+=1
            continue
        key=hashlib.sha256(
            json.dumps([record["task"],record["instruction"],record["output"]],
                       ensure_ascii=False).encode()
        ).hexdigest()
        if key in seen:
            rejected["duplicate_pair"]+=1
            continue
        seen.add(key)
        group=record.get("project_family") or record["source_project"]
        split=split_for_project(str(group),seed)
        results[split].append({
            "messages":[{"role":"system","content":SYSTEM},
                        {"role":"user","content":record["instruction"]},
                        {"role":"assistant","content":record["output"]}],
            "task":record["task"],"quality":record["quality"],
            "source_hash":hashlib.sha256(record["source_id"].encode()).hexdigest()[:16]
        })
    for split,rows in results.items():
        with (output_dir/f"{split}.jsonl").open("w",encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row,ensure_ascii=False)+"\n")
    report={"accepted":{s:len(rows) for s,rows in results.items()},
            "rejected":dict(rejected),
            "warning":"Each record needs independent IP/confidentiality review before cloud upload."}
    (output_dir/"summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
