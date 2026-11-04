# LabVIEW AI Training — Cloud Development (v1.1)

**Status:** Approved architecture + initial Python scaffold committed. This repository is for data inventory, graph/AIXML preparation, cloud fine-tuning experiments and evaluation, not the running DynasBrain app.

## Key links

- [Frozen architecture and 35 decisions](docs/11-approved-architecture-v1.1.md)
- [Phase-by-phase implementation plan](docs/12-implementation-roadmap-v1.1.md)
- [Training data mapping and CLI](docs/13-data-contract-v1.1.md)
- [Cloud training and model comparison runbook](docs/14-cloud-training-runbook-v1.1.md)
- [Previous design (historical)](docs/README.md)
- [Runtime application (DynasBrain)](https://github.com/Robokks/labview-ai-assist)
- [LabVIEW MCP dependency](https://github.com/Zuehlke/labview-mcp)

## Included source

- `src/labview_ai_training/inventory.py` — read-only source hashing, duplicates and provisional project grouping.
- `src/labview_ai_training/aixml.py` — cautious AIXML parsing, node/net memberships and canonical serialization.
- `src/labview_ai_training/dataset.py` — Gold/Silver/Bronze- and privacy-aware SFT preparation with project-based splits.
- `src/labview_ai_training/mcp_bridge.py` — read-only LabVIEW MCP connection probe (optional MCP dependency).
- `scripts/train_qlora.py` — opt-in CUDA pilot (not run or validated on real data).
- `tests/` and `.github/workflows/training-ci.yml` — pure-Python tests and GitHub CI.

## Quick use

Use Python 3.11+ in GitHub Codespaces or PyCharm. Install package:

    pip install -e .
    python -m unittest discover -s tests -v
    python -m labview_ai_training --help

Read-only file inventory:

    python -m labview_ai_training inventory --root PATH_TO_SAMPLES --out inventory.json

Parse an exported AIXML:

    python -m labview_ai_training graph --input sample.aixml --out sample.graph.json

Prepare **authorized** example JSONL for training:

    python -m labview_ai_training prepare-sft --input approved.jsonl --output-dir prepared

No command automatically uploads data or edits LabVIEW files. The official LabVIEW MCP EXE and a Windows LabVIEW installation are separately needed for real VI integration.

## Privacy and current limits

This repository is **public**. Do not commit confidential VIs, AIXML, company data, credentials or derived graphs. Model training is not running: it needs an explicitly approved dataset and an authorized cloud GPU session. Full native VI generation, model benchmarks and deployment are future milestones, not completed features. The old docs/01–10 describe an earlier two-PC plan; the new docs/11–14 supersede conflicting choices on this branch.
