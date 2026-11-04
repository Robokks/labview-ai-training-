"""Read-only LabVIEW training-source inventory. No uploads or VI execution."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from collections import Counter, defaultdict

EXTS = {".vi",".vit",".lvlib",".lvproj",".lvclass",".ctl",".aixml",".xml",".json",".pdf",".md",".txt",".png",".jpg"}
SKIP = {".git",".venv","venv","__pycache__",".idea","node_modules"}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()

def project_group(path: Path, root: Path) -> str:
    for parent in (path.parent, *path.parents):
        if not (parent == root or root in parent.parents):
            break
        if any(f.suffix.lower() == ".lvproj" for f in parent.iterdir() if f.is_file()):
            return parent.relative_to(root).as_posix() or "."
    parts = path.relative_to(root).parts
    return parts[0] if len(parts) > 1 else "."

def inventory(root: Path) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    records = []
    for path in sorted(root.rglob("*")):
        if any(part in SKIP for part in path.relative_to(root).parts):
            continue
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in EXTS:
            continue
        row = {"relative_path":path.relative_to(root).as_posix(),
               "extension":path.suffix.lower(),
               "project_group":project_group(path, root),
               "quality":"bronze", "cloud_approved":False,
               "extraction_status":"not_attempted"}
        try:
            row.update(size_bytes=path.stat().st_size, sha256=sha256(path), status="ok")
        except OSError as e:
            row.update(status="read_error", error_type=type(e).__name__)
        records.append(row)
    hashes = defaultdict(list)
    for row in records:
        if row.get("sha256"):
            hashes[row["sha256"]].append(row["relative_path"])
    return {"root":str(root),
            "records":records,
            "duplicate_groups":[v for v in hashes.values() if len(v)>1],
            "summary":{"files":len(records),
                       "extensions":dict(Counter(r["extension"] for r in records)),
                       "cloud_approved":0,
                       "read_errors":sum(r["status"]!="ok" for r in records)}}

def save(result: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
