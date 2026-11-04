"""Create scratch-only LabVIEW projects from a known-working project template.

No LabVIEW execution, no modification of original VI or template project.
Preserves the template's project settings, while replacing project items with
exactly one scratch VI and an empty Build Specifications folder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _element_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def create_project(template: Path, subject: Path, output: Path, *,
                   scratch_root: Path, expected_sha256: str | None = None) -> dict:
    template, subject, output, scratch_root = (
        p.resolve() for p in (template, subject, output, scratch_root)
    )
    if not template.is_file() or not subject.is_file():
        raise FileNotFoundError("Working project template or scratch VI is missing")
    if output.exists():
        raise FileExistsError(f"Project already exists, refusing overwrite: {output}")
    if template == output or subject == output:
        raise ValueError("Output must differ from template and VI")
    if not subject.is_relative_to(scratch_root) or not output.is_relative_to(scratch_root):
        raise ValueError("Subject and output must remain in scratch root")
    if subject.parent != output.parent:
        raise ValueError("Project must be saved alongside its scratch VI")
    if output.suffix.lower() != ".lvproj" or subject.suffix.lower() != ".vi":
        raise ValueError("Expected .lvproj output and .vi subject")
    sha = digest(subject)
    if expected_sha256 and sha.lower() != expected_sha256.lower():
        raise ValueError("Scratch VI hash differs from approved source")

    tree = ET.parse(template)
    root = tree.getroot()
    if _element_tag(root.tag) != "Project" or root.get("Type") != "Project":
        raise ValueError("Template is not an NI LabVIEW project")
    machines = [
        x for x in root if _element_tag(x.tag) == "Item"
        and x.get("Type") == "My Computer"
    ]
    if len(machines) != 1:
        raise ValueError("Template must include exactly one My Computer target")
    machine = machines[0]
    # Preserve root/project and target Property entries, but remove ALL listed VIs,
    # dependencies and project virtual folders from the cloned target.
    for item in list(machine):
        if _element_tag(item.tag) == "Item":
            machine.remove(item)
    for item in list(root):
        if _element_tag(item.tag) == "Item" and item is not machine:
            root.remove(item)
    # LabVIEW project's relative URL is resolved from project directory.
    vi_item = ET.Element("Item", {
        "Name": subject.name,
        "Type": "VI",
        "URL": subject.name,
    })
    machine.append(vi_item)
    # File content never points to the previously working F-to-C subject.
    vi_entries = [x for x in root.iter()
                  if _element_tag(x.tag) == "Item" and x.get("Type") == "VI"]
    if len(vi_entries) != 1 or vi_entries[0].get("URL") != subject.name:
        raise ValueError("Generated project has incorrect VI inventory")

    # Ensure the scratch VI still matches the expected binary before creating.
    if digest(subject) != sha:
        raise ValueError("Scratch VI changed while making project")
    output.parent.mkdir(parents=True, exist_ok=True)
    # 'xb' fails rather than overwriting an existing artifact.
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with output.open("xb") as stream:
        stream.write(data)
    return {"project": str(output), "scratch_vi": str(subject),
            "sha256": sha, "template": str(template),
            "vi_entries": 1, "labview_open_verified": False,
            "native_executed": False, "cloud_approved": False}


def create_from_manifest(template: Path, manifest: Path, scratch_root: Path) -> dict:
    config = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if config.get("schema") != "phase4-caraya-generation-batch-v1":
        raise ValueError("Unsupported batch manifest schema")
    jobs = config.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("No jobs found")
    # Every job must be safe for project creation before ANY files are written.
    params = []
    outputs = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("Invalid job")
        original = Path(job["source"]).resolve()
        scratch = Path(job["scratch"]).resolve()
        output = Path(job["project"]).resolve()
        if not original.is_file() or not scratch.is_file():
            raise FileNotFoundError("Source or scratch VI missing")
        if original == scratch:
            raise ValueError("Original and scratch must be separate")
        if not scratch.is_relative_to(scratch_root.resolve()) or not output.is_relative_to(scratch_root.resolve()):
            raise ValueError("Job project or scratch VI is outside scratch root")
        if scratch.parent != output.parent:
            raise ValueError("Each project must sit beside its scratch VI")
        if output.exists() or output in outputs:
            raise FileExistsError(f"Duplicate or existing project: {output}")
        expected = job["sha256"]
        if digest(original).lower() != expected.lower() or digest(scratch).lower() != expected.lower():
            raise ValueError("Source/scratch hash does not match job manifest")
        params.append((scratch, output, expected))
        outputs.add(output)

    results = [
        create_project(template, scratch, output, scratch_root=scratch_root,
                       expected_sha256=expected)
        for scratch, output, expected in params
    ]
    return {"projects_created": len(results), "projects": results,
            "native_executions": 0, "cloud_approved": False,
            "next_step": "Open projects in LabVIEW, confirm VI loads and target resolution before generating test VIs."}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--template", type=Path, required=True,
                   help="Known-working local .lvproj to clone safely")
    p.add_argument("--manifest", type=Path, required=True,
                   help="Batch manifest containing scratch VI and project paths")
    p.add_argument("--scratch-root", type=Path, required=True)
    a = p.parse_args()
    result = create_from_manifest(a.template, a.manifest, a.scratch_root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
