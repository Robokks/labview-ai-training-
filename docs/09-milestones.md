# 9. Milestones

Each milestone ends with something that can be tried on the two PCs.

```mermaid
flowchart LR
    L1["L1<br/>Cable +<br/>read-only gateway"] --> L2["L2<br/>Relay"]
    L2 --> L3["L3<br/>Local AI backend"]
    L3 --> L4["L4<br/>labview-mcp +<br/>sandbox"]
    L4 --> L5["L5<br/>VI logic<br/>pylabview + bridge"]
    L3 --> L6["L6<br/>Training"]
    L5 --> L6
    L2 --> P1["P1–P6<br/>Mobile remote"]
    L4 -. "generate from phone" .-> P1
```

| # | Milestone | Repo | Done when |
|---|---|---|---|
| **L1** | Cable link + read-only gateway | DynasBrain | Fixed IPs and firewall set ([Network setup](05-network-setup.md)). Claude Code on the internet PC answers a question using the offline PC's DynasBrain tools over the cable. Then the gateway adds an access key and serves only the MCP endpoint on the cable. |
| **L2** | Relay | DynasBrain | A question typed on the offline PC's Ask page is answered by Claude Code or Codex on the internet PC, with progress and cancel. Privacy setting enforced on the offline PC, with an audit log. |
| **L3** | Local AI backend | DynasBrain | Stock Qwen2.5-Coder 7B via Ollama answers through the same relay and tools. The first test-set score is recorded. |
| **L4** | labview-mcp + sandbox | DynasBrain | The gateway starts labview-mcp and offers the curated tools. A small VI is generated and run in `D:\AI-Workspace\` with approval and a git snapshot. PowerShell/Python runner as the limited user. |
| **L5** | VI logic | DynasBrain + LabVIEW | pylabview data merged into DynasBrain. The bridge Exporter VI built and its output merged. "Explain this VI" gives sequence and data flow. |
| **L6** | Training | this repo | Test set, public dataset, fine-tuned 7B GGUF. Swapped in only if it beats the stock model. |
| **P1–P6** | Mobile remote | DynasBrain, ai-chatbot | Phone on the office Wi-Fi asks, sends commands, sees progress and approves (per project); VIs still generated on the offline PC. Steps in [Mobile remote](11-mobile-remote.md#build-plan) |
| Later | | | QA / code review; MCP Server Toolkit for test rigs; multi-user tokens; LabVIEW WebView2 panel |

**Status (2026-11-01):** L1 and L2 are built in DynasBrain (branch `ccr-da1e8f34-orde03`):
`dynasbrain gateway`, `gateway-token`, `privacy`, `relay`, `relay-key`, `relay-connect`, plus
Cancel on the Ask page. They are tested, including one run with real Claude Code. Still
needed from a person: the cable, IPs and firewall ([Network setup](05-network-setup.md)),
then a first run on the two real PCs. Codex on the relay is not wired up yet.

## Also to do

- **ai-chatbot:** revise HANDOVER §2A so shared Claude Code / Codex use only the offline
  gateway's tools, not a folder on the internet PC.
- **Training repo:** add the earlier scripts (`extract_training_data.py`, `convert_chats.py`,
  `colab_finetune.ipynb`).

## Open questions

| # | Question | Default until decided |
|---|---|---|
| 1 | Offline PC UI: DynasBrain Ask for LabVIEW work and ai-chatbot for general chat, or ai-chatbot for everything? | DynasBrain Ask for LabVIEW |
| 2 | Confidentiality policy: which projects may go to Claude/Codex? | None ("Local AI only") |
| 3 | IT approval for the cable link | Required before L1 on real projects |
| 4 | LabVIEW version on each PC (`lvai_*` needs 2026 Q3) | Assume 2026 Q3 on the offline PC |
| 5 | Claude Code sign-in on the internet PC | Subscription login, no API key |
| 6 | CPU model of each PC, for better speed estimates | — |
| 7 | Office Wi-Fi subnet and client isolation, for the phone ([Mobile remote](11-mobile-remote.md#open-questions)) | Ask IT before P1 |
