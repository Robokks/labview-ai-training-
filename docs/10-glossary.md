# 10. Glossary

| Term | Meaning |
|---|---|
| **AIXML** | A text format for LabVIEW block diagrams used by LabVIEW 2026's AI feature. labview-mcp turns AIXML into a real `.vi`. |
| **Bridge Exporter VI** | A LabVIEW VI (to be built) that uses VI Scripting to export each VI's structure and wires to `*.dynasbrain.json` for DynasBrain. |
| **Codex CLI** | OpenAI's command-line coding agent. |
| **Claude Code** | Anthropic's command-line coding agent. DynasBrain runs it headless (`claude -p`). |
| **Context (window)** | How much text a model can look at in one go, measured in tokens (8K ≈ 6,000 words). |
| **DynasBrain** | Our knowledge base app (repo `labview-ai-assist`): search, VI reader, call graph, MCP server, Ask page. |
| **Fine-tuning / QLoRA** | Further training an existing model on our examples. QLoRA is a memory-saving method that fits a 7B model on a free Colab GPU. |
| **Gateway** | The DynasBrain service on the offline PC that offers all tools over the cable and enforces privacy and approvals. |
| **GGUF** | The file format for local models used by Ollama and llama.cpp. |
| **Hybrid search** | Keyword search (exact VI names) combined with meaning search (same idea, different words). |
| **labview-mcp** | MCP server that lets an AI read, write and run LabVIEW code (fork of Zuehlke/labview-mcp). |
| **lvai / pylv** | labview-mcp's two engines. `lvai_*` tools talk to a running LabVIEW 2026; `pylv_*` tools use pylabview and need no LabVIEW. |
| **MCP** | Model Context Protocol: the standard way an AI calls external tools. |
| **Ollama** | A program that runs local models on Windows and offers an OpenAI-compatible API. |
| **OpenAI-compatible API** | The common `/v1/chat/completions` interface. Ollama, ai-chatbot's home server and many others offer it. |
| **Phone setting** | Per-project setting for the mobile remote: Off, View and ask, or View, ask and approve. |
| **PWA** | Progressive web app: a web page that can be added to the phone's home screen and looks like an app. |
| **pylabview** | Open-source Python library that reads and writes the `.vi` file container. Bundled with labview-mcp. |
| **Q4_K_M** | A 4-bit quantisation: the model is about a quarter of its original size, with little quality loss. |
| **RAG** | Retrieval-augmented generation: search first, then give the results to the model to answer from. This is how DynasBrain gives the model our facts. |
| **Relay** | The DynasBrain service on the internet PC that receives a task and runs Claude Code, Codex or the local AI against the offline gateway. |
| **stdio** | A program talking through its standard input/output. labview-mcp speaks MCP this way, so it is started locally by the gateway. |
| **Test set** | Real questions with known good answers, used to score each model. |
| **Token** | A piece of a word. Roughly 1 token ≈ ¾ of an English word. |
