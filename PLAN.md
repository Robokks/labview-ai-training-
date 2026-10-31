# LabVIEW Local AI: System Plan

Design for an AI assistant that understands Dynaspede's LabVIEW work, answers
questions, explains VI logic and creates small VIs, while confidential code stays on
our own machines.

This file covers the **whole system** across all repositories. Training-specific
work lives in this repository; everything the engineer uses lives in DynasBrain.

Status: **design agreed, nothing built yet** (2026-10-31).

---

## 1. Requirements

| Need | Detail |
|---|---|
| Answer questions | LabVIEW, DAQmx, NI-XNET/CAN, Modbus TCP, PROFINET, Siemens S120, our own projects |
| Understand logic | Explain what a VI does: sequence, data flow, case structures, error handling |
| Create small VIs | From a plain-language description |
| Private | Confidential code and data never leave our machines unless explicitly allowed |
| Local AI | A local model that works with no internet |
| Hardware | CPU only. Slow answers (1–3 min) are acceptable |
| QA / code review | **Postponed** |

## 2. Repositories and their roles

| Repository | Role in this plan |
|---|---|
| **Robokks/labview-ai-training-** (this repo) | Training: datasets, answer-quality test set, fine-tuning notebook, GGUF export. Kept **separate** from the app. |
| **Robokks/labview-ai-assist** (DynasBrain) | **The final app.** Knowledge base (search, VI reader, call graph, hardware), MCP server, Ask page. The local AI lives here. |
| **Robokks/labview-mcp** (fork of Zuehlke/labview-mcp) | The "hands" for LabVIEW: create, read, edit and run VIs. 114 tools, two engines (`lvai` needs LabVIEW 2026 running; `pylv` needs no LabVIEW). |
| **Robokks/ai-chatbot** | Flutter chat app (Android/Windows). General chat, offline GGUF models, LAN home server. Optional chat window to DynasBrain. |
| **Robokks/LabVIEW-MCP-Server-Toolkit** | LabVIEW SDK to expose our own VIs as MCP tools. Later: let the AI operate test rigs. Not in the first version. |
| **Robokks/VI-Explorer-VI** | Low-level VI file reader in G, LabVIEW ≤ 2016 only. Reference only. Its password-overwrite feature is **not** used by the assistant. |

## 3. Machines

Two Windows 10 Pro PCs, joined by a **direct Ethernet cable**. Single user for now.

| | Internet PC | Offline PC |
|---|---|---|
| LabVIEW, Python | yes | yes |
| DynasBrain, ai-chatbot | yes | yes |
| Claude Code / Codex CLI | yes | **no** |
| Local AI (Ollama, 7B) | yes | optional |
| RAM | 16 GB (laptop) | 16 GB, 8–9 GB already in use |
| Role | **Brain**: runs the AI, talks to the internet | **Hands**: files, LabVIEW, PowerShell, Python |
| VIs created and run here | **never** | **only here** |

## 4. Architecture

```
 OFFLINE PC  192.168.50.2                         INTERNET PC  192.168.50.1
 ┌───────────────────────────────────┐            ┌──────────────────────────────────┐
 │ DynasBrain Ask page (UI)          │  1. task   │ Relay (DynasBrain)               │
 │                                   │ ─────────► │   backend: Claude Code | Codex | │
 │ DynasBrain Tool Gateway (MCP/HTTP)│            │            Local AI (Ollama)     │
 │  ├ knowledge: search, get_vi,     │ ◄───────── │ Agent: built-in file and shell   │
 │  │  callers/callees, hardware     │ 2. tool    │ tools OFF; offline PC's gateway  │
 │  ├ labview-mcp (curated subset,   │    calls   │ is its ONLY toolbox              │
 │  │  started locally over stdio)   │ ─────────► │                                  │
 │  └ sandbox runner (PS / Python)   │ 3. results │                                  │
 │ D:\AI-Workspace\  ← VIs land here │ ◄───────── │ 4. final answer                  │
 └───────────────────────────────────┘            └──────────────────────────────────┘
          direct cable, firewall: only 192.168.50.1 → gateway port, access key
```

### Request flow

1. The engineer asks on the offline PC, e.g. "Create a VI that reads AI0 and logs it to CSV".
2. The offline DynasBrain sends the task to the internet PC's relay, together with the
   project's privacy setting (§6).
3. The relay starts the chosen backend:
   - **Claude Code**: `claude -p` headless, with every built-in tool switched off (as
     DynasBrain's `ask.py` already does) and only the offline gateway's MCP tools allowed.
   - **Codex**: same idea, with only the gateway's tools allowed.
   - **Local AI**: a DynasBrain agent loop driving Ollama through the OpenAI-compatible
     API, with the gateway's tools.
4. Every tool call travels back over the cable and **runs on the offline PC**. Only the
   result is returned.
5. The answer comes back to the Ask page. Files exist only on the offline PC.

### Components to build

**Offline PC: DynasBrain Tool Gateway**
- DynasBrain already serves read-only MCP over HTTP (`/mcp`). Extend it into the single
  gateway reachable over the cable.
- Starts **labview-mcp** (`LabVIEWMCP.exe`, stdio) locally and re-exposes a **curated
  subset** of its tools (§5). This also bridges stdio-only labview-mcp to HTTP.
- Adds a **sandbox runner** for PowerShell and Python (§7).
- Write and run tools carry MCP `destructiveHint` and require approval **on the offline PC**.

**Internet PC: Relay and agent launcher**
- Receives tasks from the offline PC, starts the backend, streams progress
  ("searching…", "generating VI…", "waiting for approval…") back, supports cancel.
- Reuses DynasBrain's `ask.py` pattern (headless Claude Code, tools allow-list, question
  over stdin).
- Adds the `AI_BACKEND = claude_code | codex | ollama | openai_compatible` setting
  already planned in DynasBrain's PLAN.md Phase 2.

**ai-chatbot**
- General chat on both PCs, and an optional chat window that connects to the gateway as an
  MCP tool source.
- Its `docs/HANDOVER.md` §2A ("Claude Code / Codex sharing") runs the agent **in a folder on
  the internet PC**. For this plan the agent must instead run with **no local file access and
  the offline gateway's tools only**. Revise §2A before finishing it.

## 5. Curated labview-mcp tool set

114 tools is far too many for a small local model. Start with this set and grow it only when
the test set (§9) shows a need.

| Group | Tools | Needs LabVIEW running |
|---|---|---|
| Status | `lvai_status`, `pylv_status` | lvai: yes |
| Read / understand | `lvai_describe_vi`, `lvai_describe_project`, `lvai_convert_vi_to_aixml`, `pylv_extract`, `pylv_route` | lvai: yes; pylv: no |
| Reference lookups | `lvai_aixml_reference`, `lvai_search_info_cache`, `lvai_palette_index`, `lvai_example_index` | partly no |
| Create (write) | `lvai_check_aixml`, `lvai_validate_aixml`, `lvai_generate_vi` | yes |
| Run (write) | `lvai_run_vi_and_read_values` | yes |

- Do **not** use `lvai_apply_aixml_to_vi` (known Error 42; see labview-mcp `docs/guide/safety.md`).
- Claude Code and Codex can be given a larger set than the local model.
- labview-mcp requires LabVIEW **2026 Q3** for `lvai_*`. On LabVIEW 2020, only `pylv_*`
  and DynasBrain's own reader are available.

## 6. Privacy rules

- Every DynasBrain project has a setting: **Local AI only** or **Cloud allowed**.
- **Default for now: every project is "Local AI only".** The confidentiality policy will be
  decided later. The setting exists from day one, so no redesign is needed.
- Choosing Claude Code or Codex for a "Local AI only" project shows: *"This sends project
  data to the internet. Allow for this request?"* Nothing is sent without that confirmation.
- The **offline PC** enforces this, not the relay: the gateway refuses to return a
  confidential project's data to a cloud-backed session.
- Training (§9) uses **public data only** when it runs on Google Colab. Confidential project
  data stays in DynasBrain's local index and is never put into training files.

## 7. Sandbox on the offline PC

Windows Sandbox is available on Win 10 Pro but is not practical with LabVIEW and its
licence, so the sandbox is layered:

| Layer | Rule |
|---|---|
| Workspace | AI can read and write only inside `D:\AI-Workspace\` (configurable). Real project folders are read-only through DynasBrain. |
| Snapshot | Automatic git commit (or folder copy) before every write, so each change can be undone. |
| Approval | Every create / edit / run shows Allow / Deny on the offline PC. Reads run without asking. |
| Runner | No free-form shell. Only PowerShell and Python scripts, with a working folder and a timeout. |
| Limited user | Scripts run as a limited local Windows user (e.g. `ai-runner`) that can write only to the workspace. |
| No network | The offline PC has no internet route, so scripts cannot send data out. |

## 8. Network link (direct cable)

- Fixed IPs on the cable adapters, e.g. internet PC `192.168.50.1`, offline PC `192.168.50.2`.
- Offline PC cable adapter: **no gateway and no DNS**, so it still has no route to the internet.
- Windows Firewall on the offline PC: allow the gateway port **only** from `192.168.50.1`, on
  that adapter only.
- One shared access key between the two PCs (single user). Room for per-user tokens later
  (DynasBrain PLAN.md M5).
- **Get IT's approval.** The offline PC will accept commands from an internet-connected PC,
  which partly opens its isolation.

## 9. Local model and training (this repository)

### Model

| Item | Choice |
|---|---|
| Base model | Qwen2.5-Coder-7B-Instruct (3B as a fallback) |
| Format | GGUF, Q4_K_M |
| Runner | Ollama on the internet PC (background service). ai-chatbot's home server also works, since DynasBrain uses the OpenAI-compatible API |
| Context | 8K, up to 16K |
| RAM | ~6.5–7 GB for 7B including DynasBrain; ~3.5–4 GB for 3B |
| Speed | ~1–2 min per answer on CPU for 7B. Acceptable |

The offline PC does not need to load a model: it reaches the internet PC's model over the
cable. If a model is wanted on the offline PC too, use 3B there, or free 1–2 GB first.

### Work in this repository

1. **Answer-quality test set first.** Real LabVIEW questions with known good answers. Every
   model (stock, fine-tuned) is scored on it. DynasBrain's `dynasbrain eval` already measures
   *search* quality (hit@5); this set measures *answer* quality.
2. **Public data:** labview-mcp docs (`docs/aixml-reference.md`, error lists, cold-build
   post-mortems), its agent definitions, NI manuals, AIXML examples.
3. **Our own Q&A**, cleaned of confidential details by a person before it is added.
4. **Fine-tune** (QLoRA, Unsloth, Google Colab T4) → GGUF Q4_K_M → `Modelfile`.
5. **Deliver** `labview-assistant.gguf` + `Modelfile` + test-set score. DynasBrain only needs
   the model name to switch.

Fine-tuning mainly teaches **format** (AIXML syntax, tool-call shape, LabVIEW terminology).
Facts come from DynasBrain's search at question time. Train only after the stock model's
weak spots are known from the test set.

### Feedback loop

DynasBrain records questions the engineer marks as badly answered. A person reviews and
removes confidential details, the cleaned examples go into this repository, and the next
model is trained on them and scored on the test set.

## 10. Understanding VI logic

DynasBrain's file reader gets descriptions, links, connector panes, labels and diagram
text, but not structure or wires. Two sources fill the gap, and DynasBrain merges both by
VI path:

| Source | Gives | Works on |
|---|---|---|
| **pylabview** (`pylv_extract`, bundled with labview-mcp) | Diagram objects from the file, no LabVIEW needed | LabVIEW 2020 and 2026, LabVIEW closed |
| **Bridge Exporter VI** (DynasBrain `labview/bridge/README.md`) | LabVIEW's own view: structures, case names, property nodes, constants, wires, `broken` | LabVIEW 2026, built by a person in LabVIEW |

## 11. Milestones

| # | Milestone | Done when |
|---|---|---|
| L1 | **Cable link + read-only gateway** | Fixed IPs and firewall set. Claude Code on the internet PC answers a question using the offline PC's DynasBrain tools over the cable. |
| L2 | **Relay** | A question typed on the offline PC's Ask page is answered by Claude Code, Codex or Ollama on the internet PC, with progress and cancel. Privacy setting enforced. |
| L3 | **Local AI backend** | Stock Qwen2.5-Coder-7B via Ollama answers through the same relay and tools. First test-set score recorded. |
| L4 | **labview-mcp + sandbox on the offline PC** | A small VI is generated and run in `D:\AI-Workspace\` with approval and a snapshot. |
| L5 | **Logic understanding** | pylabview data merged into DynasBrain. Bridge Exporter VI built and its output merged. "Explain this VI" gives sequence and data flow. |
| L6 | **Training** | Test set, public dataset, fine-tuned 7B GGUF. Swapped in only if it beats the stock model on the test set. |
| Later | QA / code review, MCP Server Toolkit for test rigs, multi-user | |

## 12. Open questions

1. Offline PC UI: DynasBrain Ask for LabVIEW work and ai-chatbot for general chat (assumed),
   or ai-chatbot for everything?
2. Confidentiality policy: which projects may go to Claude/Codex? (Default until decided:
   none.)
3. IT approval for the cable link between the internet PC and the offline PC.
4. LabVIEW version on each PC: `lvai_*` tools need LabVIEW 2026 Q3.
5. Claude Code sign-in on the internet PC: subscription login (no API key), as DynasBrain's
   Ask already assumes.
