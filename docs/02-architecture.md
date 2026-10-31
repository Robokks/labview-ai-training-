# 2. Architecture

## The two PCs

Two Windows 10 Pro PCs, joined by a **direct Ethernet cable** (no switch, no Wi-Fi).

| | Internet PC | Offline PC |
|---|---|---|
| Cable IP (proposed) | `192.168.50.1` | `192.168.50.2` |
| Internet access | yes | **no** |
| LabVIEW, Python | yes | yes |
| DynasBrain, ai-chatbot | yes | yes |
| Claude Code / Codex CLI | yes | **no** |
| Local AI (Ollama) | yes, 7B | optional, 3B |
| RAM | 16 GB (laptop) | 16 GB, 8–9 GB already in use |
| **Role** | **Brain**: runs the AI, talks to the internet | **Hands**: files, LabVIEW, PowerShell, Python |
| VIs created and run here | **never** | **only here** |

## Components

```mermaid
flowchart TB
    subgraph OFF["Offline PC 192.168.50.2"]
        direction TB
        ASK["DynasBrain Ask page<br/>(engineer types here)"]
        subgraph GW["DynasBrain Tool Gateway (MCP over HTTP, cable only)"]
            KB["Knowledge tools<br/>search · get_vi · get_callers · get_callees<br/>project_overview · hardware_usage · read_document"]
            LVT["labview-mcp curated subset<br/>(LabVIEWMCP.exe started locally, stdio)"]
            SBX["Sandbox runner<br/>PowerShell / Python"]
            POL["Privacy check<br/>per-project setting"]
            APR["Approval prompt<br/>for every write / run"]
        end
        IDX[("DynasBrain index<br/>~/.dynasbrain")]
        WS[("D:\AI-Workspace<br/>git snapshots")]
        LVEXE["LabVIEW 2026"]
        KB --> IDX
        LVT --> LVEXE
        LVT --> WS
        SBX --> WS
    end
    subgraph ON["Internet PC 192.168.50.1"]
        RL["DynasBrain Relay<br/>backend: claude_code | codex | ollama"]
        CC["Claude Code<br/>headless, built-in tools OFF"]
        CX["Codex CLI<br/>gateway tools only"]
        AG["DynasBrain agent loop"]
        OL["Ollama<br/>Qwen2.5-Coder 7B"]
        RL --> CC
        RL --> CX
        RL --> AG --> OL
    end
    CLOUD(("Anthropic /<br/>OpenAI cloud"))
    CC <--> CLOUD
    CX <--> CLOUD
    ASK -- "task + project privacy" --> RL
    CC -- "MCP tool calls" --> GW
    CX -- "MCP tool calls" --> GW
    AG -- "MCP tool calls" --> GW
```

### Offline PC: DynasBrain Tool Gateway (to build)

- DynasBrain already serves MCP over HTTP at `/mcp` (9 read-only tools). The gateway
  extends that server so it can be reached **over the cable only**, with an access key.
- It starts **labview-mcp** (`LabVIEWMCP.exe`) locally over stdio and re-offers a
  **curated subset** of its tools (below). This also solves the fact that labview-mcp
  speaks only stdio and cannot be reached across the network by itself.
- It adds a **sandbox runner** for PowerShell and Python scripts ([Sandbox](04-sandbox.md)).
- It checks every tool result against the project's **privacy setting** ([Privacy](03-privacy.md)).
- Every write or run tool is marked `destructiveHint` and needs **approval on the offline PC**.

### Internet PC: DynasBrain Relay (to build)

- Receives a task from the offline PC's Ask page.
- Starts the chosen backend:
  - **Claude Code:** `claude -p` headless, as DynasBrain's `ask.py` already does. Every built-in tool is off (no shell, no file access), only the gateway's MCP tools are allowed, and the question goes in over stdin.
  - **Codex CLI:** the same principle, with gateway tools only.
  - **Local AI:** a DynasBrain agent loop that calls Ollama through the OpenAI-compatible API and uses the same gateway tools.
- Streams progress back ("searching…", "generating VI…", "waiting for approval…") and supports **cancel**.
- Uses the setting `AI_BACKEND = claude_code | codex | ollama | openai_compatible`, already planned in DynasBrain's PLAN.md Phase 2.

### ai-chatbot

- General chat on both PCs. It can also add the gateway as an MCP tool source (Settings → Tools).
- **Needed change:** its `docs/HANDOVER.md` §2A ("Claude Code / Codex sharing") runs the agent in a
  **folder on the internet PC**. Under this design the agent must run with **no local file
  access** and the **offline gateway's tools only**, so files are never created on the
  internet PC.
- Its home server is also an OpenAI-compatible model server, so it can stand in for Ollama.

## One request, end to end

```mermaid
sequenceDiagram
    autonumber
    actor E as Engineer
    participant A as Ask page (offline)
    participant G as Gateway (offline)
    participant R as Relay (internet)
    participant M as AI backend (internet)
    participant L as LabVIEW (offline)

    E->>A: "Create a VI that reads AI0 and logs it to CSV"
    A->>R: task, project, privacy = Local AI only
    R->>M: start backend (Ollama, because the project is Local AI only)
    M->>G: search("DAQmx read log CSV")
    G-->>M: matching VIs and doc passages
    M->>G: lvai_aixml_reference
    G-->>M: AIXML grammar and terminal names
    Note over M: the model writes AIXML
    M->>G: lvai_check_aixml / lvai_validate_aixml
    G-->>M: ok, or the faults to fix
    M->>G: lvai_generate_vi (write)
    G->>E: Allow / Deny? (on the offline PC)
    E-->>G: Allow
    G->>G: git snapshot of D:\AI-Workspace
    G->>L: generate the VI
    L-->>G: saved D:\AI-Workspace\Read AI0 Log CSV.vi
    G-->>M: saved, connector pane verdict
    M-->>R: final answer
    R-->>A: answer + list of files created
    A-->>E: "Created Read AI0 Log CSV.vi in D:\AI-Workspace"
```

## Curated labview-mcp tool set

labview-mcp offers 114 tools, far too many for a small local model. Start with this
set and grow it only when the [test set](07-training.md#1-answer-quality-test-set) shows a need.

| Group | Tools | Needs LabVIEW running | Kind |
|---|---|---|---|
| Status | `lvai_status`, `pylv_status` | lvai: yes | read |
| Read / understand | `lvai_describe_vi`, `lvai_describe_project`, `lvai_convert_vi_to_aixml`, `pylv_extract`, `pylv_route` | lvai: yes, pylv: no | read |
| Reference lookups | `lvai_aixml_reference`, `lvai_search_info_cache`, `lvai_palette_index`, `lvai_example_index` | partly no | read |
| Create | `lvai_check_aixml`, `lvai_validate_aixml`, `lvai_generate_vi` | yes | **write** |
| Run | `lvai_run_vi_and_read_values` | yes | **write** |

- **Never** expose `lvai_apply_aixml_to_vi`. It fails with Error 42; see labview-mcp
  `docs/guide/safety.md`.
- Claude Code and Codex may get a larger set than the local model.
- `lvai_*` tools need **LabVIEW 2026 Q3** running on the offline PC. With LabVIEW 2020
  only `pylv_*` and DynasBrain's own reader work.
- Generated VIs lose layout, decorations and icon if regenerated. labview-mcp measured that only
  ~15% of production VIs can be regenerated via AIXML. So **new small VIs** are the
  target, not rewriting existing ones.

## Where data lives

| Data | Location | Leaves the offline PC? |
|---|---|---|
| Project VIs and documents | Offline PC project folders | Only as tool results, and only if the privacy setting allows |
| DynasBrain index | Offline PC `~/.dynasbrain` | Same as above |
| AI-created VIs and scripts | Offline PC `D:\AI-Workspace\` | No |
| Prompts and answers, local AI | Internet PC memory, LAN only | No (stays on the cable) |
| Prompts and answers, Claude / Codex | Anthropic / OpenAI | **Yes**, so only for projects that allow it |
| Training data | This repository / Colab | Public data only |
