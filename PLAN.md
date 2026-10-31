# LabVIEW Local AI: One-Page Plan

The full design is in **[docs/](docs/README.md)**. This page is the summary.

Status: **design agreed, nothing built yet** (2026-10-31).

## Goal

A LabVIEW AI assistant that answers questions, explains VI logic and creates small VIs,
with confidential code kept on our own machines. QA / code review is postponed.
→ [Overview](docs/01-overview.md)

## Design

| Decision | Detail | Doc |
|---|---|---|
| Two repos | This repo = training (separate). DynasBrain (`labview-ai-assist`) = the app; the local AI lives there | [Overview](docs/01-overview.md) |
| Two PCs, direct cable, Win 10 Pro, single user | **Internet PC = brain** (Claude Code / Codex / Ollama). **Offline PC = hands** (VIs and scripts created and run only there) | [Architecture](docs/02-architecture.md) |
| Offline PC: Tool Gateway | DynasBrain knowledge tools + curated labview-mcp tools + PowerShell/Python sandbox runner, over the cable | [Architecture](docs/02-architecture.md#components) |
| Internet PC: Relay | Runs the chosen AI with its own file/shell tools off; the offline gateway is its only toolbox | [Architecture](docs/02-architecture.md#internet-pc-dynasbrain-relay-to-build) |
| Privacy | Per-project setting, **default "Local AI only"**, enforced on the offline PC. Cloud only with per-request permission. Training uses public data only | [Privacy](docs/03-privacy.md) |
| Sandbox | Workspace folder, git snapshot before every change, approvals, restricted runner, limited Windows user | [Sandbox](docs/04-sandbox.md) |
| Network | Fixed IPs `192.168.50.1` / `.2`, no gateway/DNS on the cable, firewall locked to the internet PC, access key, IT approval | [Network setup](docs/05-network-setup.md) |
| Model | Qwen2.5-Coder 7B Q4_K_M on the laptop via Ollama (3B fallback). CPU, slow is fine | [Local model](docs/06-local-model.md) |
| Training | Test set first → public data + reviewed own Q&A → QLoRA on Colab → GGUF. Used only if it beats the stock model | [Training](docs/07-training.md) |
| VI logic | DynasBrain reader + pylabview + bridge Exporter VI, merged | [VI logic](docs/08-vi-understanding.md) |

## Build order

L1 cable + read-only gateway → L2 relay → L3 local AI backend → L4 labview-mcp + sandbox →
L5 VI logic → L6 training. → [Milestones](docs/09-milestones.md)

## Next step

**L1:** set up the cable ([Network setup](docs/05-network-setup.md)), run
`dynasbrain serve --host 192.168.50.2` on the offline PC, and ask Claude Code on the
internet PC a question about a non-confidential test project.
