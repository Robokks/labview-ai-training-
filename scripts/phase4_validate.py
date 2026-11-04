"""Read-only AIXML structural validation for LabVIEW 2026 Phase 4."""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from labview_ai_training import aixml

def validate(manifest: Path, archive: Path, output_dir: Path) -> dict:
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    roots, records = data["roots"], data["records"]
    results = []
    families = Counter()
    with zipfile.ZipFile(archive) as z:
        available = set(z.namelist())
        for r in records:
            sha = r.get("sha256", "")
            paths = r.get("source_paths", [])
            item = dict(sha256=sha, source_paths=paths, quality="excluded",
                        structurally_verified=False, training_eligible=False,
                        cloud_approved=False)
            if r.get("status") != "converted":
                item["reason"] = "conversion_failed"
            else:
                try:
                    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha.lower()):
                        raise ValueError("invalid_sha256")
                    if not paths:
                        raise ValueError("missing_source_paths")
                    groups = set()
                    for p in paths:
                        matches = [root for root in roots if p.startswith(root + "/")]
                        if not matches:
                            raise ValueError("unknown_project_family")
                        groups.add(max(matches, key=len))
                    names = [f"{sha}/{n}" for n in ("raw.aixml", "normalized.aixml", "graph.json")]
                    missing = [name for name in names if name not in available]
                    if missing:
                        raise ValueError("missing_archive_members")
                    raw, norm, saved = [z.read(name) for name in names]
                    text = raw.decode("utf-8-sig")
                    normalized = norm.decode("utf-8-sig")
                    graph = aixml.parse(text)
                    if graph != aixml.parse(normalized) or graph != json.loads(saved.decode("utf-8-sig")):
                        raise ValueError("representation_graph_mismatch")
                    if aixml.canonicalize(text) != normalized:
                        raise ValueError("normalization_mismatch")
                    if graph["warnings"] or r.get("warnings"):
                        raise ValueError("graph_warnings")
                    if r.get("nodes") != len(graph["nodes"]):
                        raise ValueError("node_count_mismatch")
                    if not graph["vi_name"]:
                        raise ValueError("missing_vi_name")
                    item.update(quality="silver_structural_candidate", structurally_verified=True,
                                project_family="|".join(sorted(groups)), nodes=len(graph["nodes"]),
                                nets=len(graph["nets"]),
                                raw_sha256=hashlib.sha256(raw).hexdigest(),
                                normalized_sha256=hashlib.sha256(norm).hexdigest(),
                                graph_sha256=hashlib.sha256(saved).hexdigest(),
                                reason="representation_equivalence_passed")
                    families.update(groups)
                except (ValueError, KeyError, UnicodeError, RuntimeError, zipfile.BadZipFile) as exc:
                    item.update(quality="bronze", reason=str(exc)[:350])
            results.append(item)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "structural-index.jsonl").write_text(
        "".join(json.dumps(x, sort_keys=True) + "\n" for x in results), encoding="utf-8")
    report = {"manifest_records": len(records),
              "counts": dict(Counter(x["quality"] for x in results)),
              "structurally_verified": sum(x["structurally_verified"] for x in results),
              "training_eligible": 0, "cloud_approved": 0,
              "family_counts": dict(families),
              "reason_counts": dict(Counter(x["reason"] for x in results)),
              "scope": "Structure only, no native execution or training permission established."}
    (output_dir / "structural-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.manifest, args.archive, args.output_dir), indent=2))

if __name__ == "__main__":
    main()
