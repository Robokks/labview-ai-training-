# Implementation roadmap — v1.1

All source development and non-hardware CI happens in GitHub cloud; Windows LabVIEW operations cannot be validated in ordinary GitHub Linux runners. Python IDE: PyCharm (optional for opening project).

| Phase | Deliverable | Exit gate |
|---|---|---|
| P0 Cloud repository | Source, tests, CI, architecture, runbook | Pure-Python tests green |
| P1 MCP feasibility | LabVIEW 2026 backend matrix (NI gRPC and pylabview) | Read VI AIXML, generate only in scratch, compile/readback |
| P2 Inventory | Hashes, duplicates, families, version/dependency report | Every input file accounted for; no source writes |
| P3 Representations | Original AIXML + normalized serialization + typed graph | Semantic-equivalence tests for supported subset |
| P4 Dataset curation | Gold/Silver/Bronze and cloud permissions | Approved SFT examples, project-level held-outs, leakage checks |
| P5 Benchmark | Qwen3-1.7B vs Qwen3.5-2B | Comparable baseline and CPU RAM/latency |
| P6 Cloud fine-tune | Shared checkpoint, pilot QLoRA | Validated improvement plus cost/license log |
| P7 Specialized adapters | Generate, explain, debug, architecture | Each passes independent regression |
| P8 Local-first deployment | CPU model + retrieval + MCP | Runs alongside LabVIEW within 8 GB constraints |
| P9 Weight-space study | Isolated checkpoint edits | Matched held-out improvement over control |
| P10 Production validation | Artifacts, rollback and safety gates | Human approval for production |

## Phase P1 procedure

1. Secure a non-confidential sample of simple and complex VIs.
2. Confirm actual LabVIEW version, Python version, NI add-ons and MCP backend.
3. Start official LabVIEWMCP.exe with the read-only status probe.
4. Export supported VIs and preserve raw AIXML and result metadata.
5. Parse nets/terminals/nesting into a graph. Compare with actual diagram in IDE.
6. Validate with server-native validator before generating a VI in a scratch directory.
7. Verify connector pane, execution/linker state and functional outputs.
8. Record unsupported structures and source-vs-output differences.
9. Only then mark verified records for potential supervised training.

## P4 dataset acceptance

- Family-level group split rather than per-sample split.
- Exact + near-duplicate analysis before cloud upload.
- Gold = verified functional results in defined test environment.
- Silver = verified syntax/structure only; no unverified behavior labels.
- Bronze = incomplete/unverified; retain for review, exclude from trusted SFT.
- All uploaded artifacts need owner permission. No cloud data transfer by default.

## Output artifacts and integration contract

Versioned dataset export, extraction report, training config hash, LoRA adapter, model card and benchmark report. The runtime app resides in Robokks/labview-ai-assist and will receive an integration PR only after acceptance; no automatic overwrite.

## Definition of done

A pilot feature is done only when generation, readback and evaluation agree for a declared supported LabVIEW subset. Comprehensive RT/FPGA/driver coverage remains a target and may require additional work beyond AIXML.
