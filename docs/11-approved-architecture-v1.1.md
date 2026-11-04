# LabVIEW AI architecture v1.1 — approved 2026-11-04

Status: DESIGN FROZEN; implementation is in progress. This document supersedes conflicting assumptions in legacy docs/01–10 (which remain for historical context). IDE is PyCharm; source/CI/cloud training run in hosted environments; LabVIEW MCP and confidential VIs stay on an authorized Windows machine.

## Goal and boundary

Build a bidirectional LabVIEW-specialized AI: natural language -> typed dataflow graph -> AIXML -> native VI, and VI -> AIXML/native structural graph -> verified explanation. Longer-term targets: editing, debugging, testing and project architecture across desktop, DAQmx, LVOOP, RT, FPGA, communications and third-party toolkits. Feature support is gated by actual LabVIEW/MCP compatibility, not assumed.

Cloud training with approved data; local-first quantized inference on Windows 8 GB RAM, no dedicated GPU. Optional cloud inference requires explicit permission for each confidential transfer. Training budget free-first; paid GPU fallback only with approval, initial cap INR 500–2000. Model candidates Qwen3-1.7B and Qwen3.5-2B must be benchmarked before selection.

## Data model

* Source: .vi/.vit/.lvlib/.lvproj/.lvclass/.ctl, manuals, XML/AIXML/JSON, images, problem-to-solution pairs.
* Preserve originals; extract with Zuehlke/labview-mcp and complementary native VI readers.
* Three linked representations: **original AIXML**, cautiously **normalized AIXML**, **typed graph** (nodes, terminal names, networks, nested structures, data types, project/subVI references). AIXML net names such as uid.terminal are **network references**, not simple pointers. Do not invent directed edges from the string alone.
* Hierarchical datasets: node/function, VI, subsystem, project. Multi-scale graph-aware chunks retain boundary connections and source provenance.
* Automatic inventory before training; hashes, duplicate/near-duplicate families, version, dependencies, rights, privacy, errors and coverage.
* Gold: functional tests validated under documented conditions. Silver: structural/syntax validation only; do not claim behavior. Bronze: not trusted for supervised learning.
* Confidence-based labeling: auto-generated descriptions are candidates, not authoritative requirements; review uncertain claims.
* Adaptive balanced mixture: real engineering code, verified public examples, documentation and validated synthetic examples. Split training/test by source project/family and check leakage.

## Model and training

1. Baseline and tiny comparable QLoRA pilots on both Qwen candidates; compare accuracy and real 8 GB Windows CPU inference, not only cloud scores.
2. Train a shared LabVIEW-specialized checkpoint (dataflow, wiring, AIXML, typed-graph reasoning).
3. Train four specialized LoRA adapters from that checkpoint: generation, understanding, debugging/verified repairs, project architecture.
4. Retrieval supplies changing terminal/palette/catalog information and project context; model weights teach reusable concepts. Version-aware API catalog is hybrid public documents + installed palettes + MCP + custom subVIs.
5. Progressive self-correction: supervised verified before/after repairs, optionally benchmark preference methods, with bounded generation/validation/repair at inference. Never self-update model weights on a single failure.
6. Separate Weight-Space Programming experiments on **copies of the shared checkpoint** only. Compare negative controls and ordinary alternatives (data, retrieval, converter fixes); only validated gains may be promoted.

## Execution and security

Read-only project analysis may be automated. Draft VI generation, XML validation, and contained software-only tests may run in an isolated workspace. Editing original projects, hardware writes, RT/FPGA deployment, drive control, destructive changes and safety-critical runs require explicit approval and backups. Never upload confidential source, derived AIXML or runtime logs without authorization.

LabVIEW MCP is research-grade; the gRPC and pylabview backends have different supported coverage. Native VI regeneration may lose layout/icon and may be rejected. Syntax validation != compiling VI != functional correctness.

## Engineering outputs

Source and documentation in Robokks/labview-ai-training-. Runtime app lives in Robokks/labview-ai-assist (DynasBrain); do not overwrite it in this phase. Deliverables: inventory + privacy report, typed graph and conversion tests, gold/silver/bronze catalog, benchmark suite, cloud training manifests, shared checkpoint and four adapters, local inference integration, experimental weight-edit reports, version registry/rollback.

## Version gates

Experimental -> Validated -> Production. Each candidate archives source dataset hash, training config, model license/version, adapter revision, LabVIEW build, MCP/backend version, public/private benchmark, local RAM/latency, safety approval and rollback checkpoint.

## Roadmap

P0 cloud repo scaffold and pure-Python CI; P1 MCP feature matrix and sample read/write scratch round trip; P2 source inventory; P3 canonical representations; P4 quality-controlled datasets; P5 two-model benchmarks; P6 cloud LoRA pilot; P7 specialized adapters; P8 local inference and safe MCP executor; P9 bounded weight-space research; P10 acceptance/release.

**No cloud GPU training or real LabVIEW validation is claimed by this document.**
