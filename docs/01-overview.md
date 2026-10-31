# 1. Overview

## Goal

A LabVIEW-specialised AI assistant for Dynaspede that:

- **answers questions** about LabVIEW, NI hardware and our own projects;
- **explains VI logic**: sequence, data flow, case structures, error handling;
- **creates small VIs** from a plain-language description;
- keeps **confidential code and data on our own machines**;
- can use a **local AI model** that works without the internet.

QA / code review is **postponed** and not part of the first version.

## Requirements

| Area | Requirement |
|---|---|
| Domain | LabVIEW 2020 and 2026, DAQmx, NI-XNET CAN, Modbus TCP, PROFINET, Siemens S120, cRIO, PXI, FPGA |
| Privacy | Confidential projects are never sent to a cloud AI without explicit permission ([Privacy](03-privacy.md)) |
| Execution | VIs and scripts are created and run **only on the offline PC**, in a sandbox ([Sandbox](04-sandbox.md)) |
| Hardware | CPU only, no GPU. Answers taking 1–3 minutes are acceptable |
| Operating system | Windows 10 Pro on both PCs |
| Users | Single user for now. Multi-user later |

## Who uses it

Karthikeyan S (Software Department Manager, Team 3 Deployment) first, then the team.
A single user means one shared access key, with no user accounts yet.

## Repositories

| Repository | Role |
|---|---|
| [Robokks/labview-ai-assist](https://github.com/Robokks/labview-ai-assist) (**DynasBrain**) | **The app.** Knowledge base over our LabVIEW projects and documents, MCP server, Ask page. The local AI, the gateway and the relay are added here. |
| [Robokks/labview-ai-training-](https://github.com/Robokks/labview-ai-training-) (this repo) | **Training**, kept separate: test set, datasets, fine-tuning, GGUF export. Plus this documentation. |
| [Robokks/labview-mcp](https://github.com/Robokks/labview-mcp) | Fork of Zuehlke/labview-mcp. Creates, reads, edits and runs VIs. 114 tools, two engines. |
| [Robokks/ai-chatbot](https://github.com/Robokks/ai-chatbot) | Flutter chat app for Android and Windows. General chat, offline GGUF models, LAN home server. Optional chat window to DynasBrain. |
| [Robokks/LabVIEW-MCP-Server-Toolkit](https://github.com/Robokks/LabVIEW-MCP-Server-Toolkit) | LabVIEW SDK that exposes our own VIs as MCP tools. Later, so the AI can operate test rigs. |
| [Robokks/VI-Explorer-VI](https://github.com/Robokks/VI-Explorer-VI) | VI file reader in G, LabVIEW ≤ 2016 only. Reference only. |

### What already exists

**DynasBrain**:
- Reads `.lvproj`, `.lvlib`, `.lvclass`, `.vi` and `.ctl` files **without LabVIEW**. Tested on LabVIEW 2020 VIs.
- Builds the call graph and finds hardware use (DAQmx, XNET, VISA, Modbus, device names, ports).
- Decodes connector panes.
- Hybrid search: SQLite FTS5 keywords + ChromaDB meaning search with a local MiniLM model.
- Reads PDF, Word and Markdown, with offline OCR, plus C/C++/Python source.
- Web UI with a VI Hierarchy view, an MCP server with 9 read-only tools, an Ask page using headless Claude Code, a search-quality eval and a Windows `.exe` built in CI.

**labview-mcp**:
- Engine `lvai` (needs LabVIEW 2026 Q3 running) generates VIs from AIXML, validates and runs them.
- Engine `pylv` (bundled pylabview, no LabVIEW needed) reads and edits existing VIs.
- 8 agent definitions and 50+ pages of measured notes.

**ai-chatbot**:
- Cloud and offline models, a home server with an OpenAI-compatible API, MCP/UTCP/A2A.
- MCP client with tool approvals.

### What this design adds

1. A **Tool Gateway** in DynasBrain on the offline PC ([Architecture](02-architecture.md)).
2. A **Relay** in DynasBrain on the internet PC that runs Claude Code, Codex or the local AI.
3. A **local AI backend** (Ollama) in DynasBrain ([Local model](06-local-model.md)).
4. **Privacy enforcement** and a **sandbox** on the offline PC.
5. **VI logic** from pylabview and the bridge Exporter VI ([Understanding VI logic](08-vi-understanding.md)).
6. A **fine-tuned model** from this repository ([Training](07-training.md)), used only if it
   beats the stock model.
