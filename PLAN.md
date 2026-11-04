# LabVIEW AI — Final approved plan v1.1 (2026-11-04)

**Delivery model:** Develop and store all source and documentation in GitHub; execute cloud GPU training only with approved input and explicit budget authorization. PyCharm is the preferred IDE for optional local review, not a dependency of cloud CI. Local-first inference on Windows, 8 GB RAM/no dedicated GPU, using the existing DynasBrain application (`Robokks/labview-ai-assist`).

## Frozen architecture

- Bidirectional **Text -> typed graph -> AIXML -> native VI**, and **VI -> graph/AIXML -> explanation**.
- Target complete LabVIEW ecosystem (desktop, instrument drivers, DAQmx, LVOOP, RT/FPGA) via staged tested feature coverage.
- Reuse Zuehlke/labview-mcp for VI operations; use `grpc` or `pylabview` per supported release/backend. Do not duplicate the VI editor.
- Automatically inventory unknown dataset; original VI, original/normalized AIXML, and typed net graph retained with provenance.
- Gold (behavioral verified), Silver (structural verified), Bronze (unverified/review only).
- Automatic candidate labeling with confidence/validation; multi-scale graph learning; family-level train/validation/test.
- Adaptively combine verified real VIs, public samples, manuals and validated synthetic examples.
- Benchmark Qwen3-1.7B and Qwen3.5-2B before selecting a foundation; then shared LabVIEW checkpoint and four specialized LoRA adapters: generator, understanding, debugging, architecture.
- Cloud QLoRA/LoRA with free-first resources; optional INR 500–2000 cap subject to approval. Keep confidential source and local project catalog off cloud without permission.
- Local quantized inference with live versioned function/terminal catalog, retrieval and controlled MCP workspace.
- Verified error repair training and optional evaluated preference methods; no unreviewed self-learning.
- Weight-space experiments only on isolated copies of shared checkpoint, benchmarked against alternatives.
- Experiment registry, quality gates, staged promotion and rollback. No source VI overwrite or physical hardware action without explicit approval.

## Ordered milestones

P0: GitHub scaffold, docs, unit tests, CI.
P1: Real LabVIEW MCP compatibility and scratch VI round trip.
P2: Corpus inventory and permissions.
P3: Typed graph/normalized AIXML with loss detection.
P4: Verified and consent-filtered SFT pairs, leakage prevention.
P5: Baseline benchmarks including local CPU constraints.
P6: Cloud pilot QLoRA and model selection.
P7: Shared checkpoint and four adapters.
P8: DynasBrain integration and safe native VI testing.
P9: Experimental weight-space edits.
P10: Release with acceptance report and rollback.

## Current repository deliverables

Pure-Python inventory, AIXML graph reader, approved-data SFT builder, read-only MCP status probe, opt-in QLoRA prototype, and unit-test CI. No native LabVIEW functionality or cloud GPU training was executed in GitHub CI; those need an authorized host/environment and input data.

## Source-of-truth documents

[Architecture](docs/11-approved-architecture-v1.1.md) · [Roadmap](docs/12-implementation-roadmap-v1.1.md) · [Data contract](docs/13-data-contract-v1.1.md) · [Cloud runbook](docs/14-cloud-training-runbook-v1.1.md)

Old docs/01–10 are kept unchanged as historical context for an earlier two-PC design, not the current architecture.
