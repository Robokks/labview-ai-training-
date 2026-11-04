# Training data contract and CLI (v1)

Our pipeline is designed to process proprietary LabVIEW code **locally by default**. The GitHub repository is public: never commit real project files or derived AIXML without authorization.

## Three linked representations

- Original VI/source (unchanged, held locally).
- Original AIXML and conservative XML canonicalization (UIDs and nets untouched).
- Typed structural graph: node kind, UID, parent, raw attributes, inputs, outputs and net memberships. Net membership does NOT prove an execution edge.

The standard-library prototype parses native AIXML already exported by MCP; it does not directly decode binary VIs or claim round-trip equivalence.

## Example SFT input (illustrative only, NOT a verified Gold example)

    {"source_id":"sample-01","source_project":"public-demo","task":"aixml_syntax","instruction":"Explain the AIXML fields","output":"Example explanation","quality":"silver","validation":{"syntax":true},"cloud_approved":true,"contains_confidential":false}

A real record must be reviewed. Only explicitly approved, non-confidential Gold records (functional evidence) and Silver records for syntax/structure tasks are eligible. Bronze is excluded.

Supported task names: text_to_aixml, text_to_graph, graph_to_explanation, aixml_syntax, graph_structure, error_to_fix, project_architecture.

## Local commands after pip install -e .

1. Inventory copies of public samples:
   `python -m labview_ai_training inventory --root C:\PublicLVExamples --out C:\Temp\lv_inventory.json`
2. Parse an exported AIXML file:
   `python -m labview_ai_training graph --input C:\Temp\Add.aixml --out C:\Temp\Add.graph.json`
3. Turn reviewed JSONL records into supervised fine-tuning splits:
   `python -m labview_ai_training prepare-sft --input C:\Approved\examples.jsonl --output-dir C:\Approved\splits`
4. Probe the separate official MCP server read-only after pip install -e ".[mcp]":
   `python -m labview_ai_training mcp-status --exe C:\Tools\LabVIEWMCP.exe`

No command above uploads training data.

## Data-quality requirements

Source metadata: checksum, source project/family, VI version, dependencies, rights/permission, extraction backend, known gaps. Retain full provenance of synthetic labels and corrections. Keep project families together across train/validation/test. Check near duplicates prior to any public/private benchmarking.

## Tokenization and chunking

Whole-VI where practical; graph-aware chunks maintain boundary nets and enclosing structure IDs. Avoid naive character splitting of XML, random UID renaming or treating structural matches as functional verification.

## Known scaffold limitations

Project grouping uses folder/.lvproj heuristics, not a resolved call graph. XML parser does not establish LabVIEW semantic validity. SFT data consent markers are file-level assertions by the dataset owner, not an automated legal classification.
