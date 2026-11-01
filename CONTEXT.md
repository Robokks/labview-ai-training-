# LabVIEW AI Assistant: Context for a New Session

> Give this file to a new Claude session to continue the work.
> Last updated: 2026-10-31. Replaces the earlier `labview_ai_context.md`.
> The full design is in [docs/](docs/README.md); [PLAN.md](PLAN.md) is the one-page summary.

## Who

- **Karthikeyan S**, Software Department Manager, Team 3 (Deployment), Dynaspede
  Integrated Systems Pvt Ltd, Tamil Nadu, India. GitHub: **Robokks**.
- 8+ years of LabVIEW: DAQmx, NI-XNET CAN, Modbus TCP, PROFINET, Siemens S120, cRIO, PXI,
  FPGA. LabVIEW 2020 and 2026.
- Prefers discussion before coding, and plain explanations.

## Goal

A local AI assistant that understands LabVIEW, answers questions, explains VI logic and
creates small VIs, with confidential code kept on our own machines. QA / code review is
postponed.

## Decisions made

1. **Two repos:** `Robokks/labview-ai-training-` for training (separate);
   `Robokks/labview-ai-assist` (DynasBrain) is the final app, and the local AI lives in it.
2. **Two PCs, direct Ethernet cable, Windows 10 Pro, single user.**
   - **Internet PC = brain:** Claude Code / Codex / local AI (Ollama) run here.
   - **Offline PC = hands:** VIs are created and run **only** here, in a sandbox.
3. **Offline PC runs a DynasBrain Tool Gateway** (MCP over HTTP on the cable): DynasBrain
   knowledge tools + a curated labview-mcp subset + a PowerShell/Python sandbox runner.
4. **Internet PC runs a relay:** starts the chosen AI with its own file/shell tools off and
   the offline gateway as its only toolbox.
5. **Privacy:** per-project setting, **default "Local AI only"**; cloud only with explicit
   per-request permission. Policy to be decided later. Training on Colab uses public data only.
6. **VI logic:** both pylabview and the DynasBrain bridge Exporter VI, merged.
7. **Model:** Qwen2.5-Coder 7B Q4_K_M (3B fallback), CPU, slow answers are fine.
   Laptop 16 GB fits 7B; the other PC has only ~7 GB free, so it uses the model over the cable.
8. **Build order:** L1 cable + read-only gateway → L2 relay → L3 local AI backend →
   L4 labview-mcp + sandbox → L5 logic (pylabview + bridge) → L6 training.
9. **Mobile remote** (docs/11-mobile-remote.md): phone on the office Wi-Fi asks, sends
   commands, views progress; generation stays on the offline PC. Modes in order: A Android →
   online PC → offline PC; B Android → online PC only; C Android → offline PC. PWA first, then ai-chatbot Flutter. Phone approval
   is a per-project setting (Off / View and ask / View, ask and approve), HMAC-signed by the
   phone and verified on the offline PC. Build steps P1–P6, after L2.

## Repositories (all read on 2026-10-31)

| Repo | What it is | State |
|---|---|---|
| `labview-ai-assist` (DynasBrain) | Python app: reads LabVIEW files without LabVIEW (tested on 2020 VIs), call graph, hardware detection, connector panes, hybrid search (SQLite FTS5 + ChromaDB/MiniLM), PDF/Word/OCR, code reader, web UI with VI Hierarchy, MCP server (9 read-only tools), Ask page via headless Claude Code, eval harness, Windows exe in CI | Phase 1 mostly done. Bridge Exporter VI not built. Phase 2 (local model, `AI_BACKEND`) planned in its PLAN.md |
| `labview-mcp` (fork of Zuehlke) | C# MCP server, stdio, **114 tools**. Engine `lvai` (needs LabVIEW 2026 Q3 running) creates/runs VIs from AIXML; engine `pylv` (bundled pylabview) reads/edits VIs with no LabVIEW. 8 agent definitions, 50+ docs | Research-grade; work on copies. Only ~15% of production VIs regenerate via AIXML |
| `ai-chatbot` | Flutter app (Android/Windows): cloud models, offline GGUF via llamadart, LAN home server (OpenAI-compatible API, MCP, UTCP, A2A, PIN pairing), MCP/CLI tools | `docs/HANDOVER.md` §2A (Claude Code sharing) is untested and must be changed to run with offline-PC tools only |
| `LabVIEW-MCP-Server-Toolkit` | LabVIEW SDK: expose your own VIs as MCP tools over HTTP | Later: test rigs |
| `VI-Explorer-VI` | G reader/writer for VI files, LabVIEW ≤ 2016, includes password overwrite | Reference only, not used |
| `labview-ai-training-` (this repo) | Training work + system documentation | `docs/`, PLAN.md and this file. The earlier scripts (`extract_training_data.py`, `convert_chats.py`, `colab_finetune.ipynb`) are not in the repo yet |

## Known facts

- `lvai_apply_aixml_to_vi` fails with Error 42. Use `lvai_generate_vi` /
  `lvai_convert_aixml_to_vi` instead.
- `.vi` files are binary. An AI can only "read" a VI through a converter: DynasBrain's
  reader, pylabview, `lvai_describe_vi`, or the bridge Exporter VI.
- DynasBrain's embedding model (all-MiniLM-L6-v2, ~80 MB) downloads on first use.
  Pre-copy it for offline machines, along with Ollama and the GGUF model.

## Next step

L1 (gateway) and L2 (relay) are built in DynasBrain, branch `ccr-da1e8f34-orde03`. Next:
set up the cable and run them on the two real PCs (docs/05-network-setup.md, steps 1–7),
then **L3**: a local model (Ollama) as a relay backend.

## How to use this file

Paste it into a new session and say:
> "Read CONTEXT.md, PLAN.md and docs/ in Robokks/labview-ai-training- and continue."
