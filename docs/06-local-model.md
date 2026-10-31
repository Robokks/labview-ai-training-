# 6. Local model

## Choice

| Item | Choice |
|---|---|
| Base model | **Qwen2.5-Coder-7B-Instruct**, with Qwen2.5-Coder-3B-Instruct as fallback |
| Format | GGUF, quantised **Q4_K_M** |
| Runner | **Ollama** on the internet PC, as a background service. ai-chatbot's home server also works, because DynasBrain talks the OpenAI-compatible API |
| Context | 8K tokens, up to 16K for large VIs |
| Where | Internet PC (laptop, 16 GB). The offline PC uses it over the cable and loads no model |

Later this is replaced by the fine-tuned model from [Training](07-training.md), but only
if it scores better on the test set.

## RAM

Typical figures for Q4_K_M on CPU:

| Part | 3B | 7B |
|---|---|---|
| Model weights | ~2 GB | ~4.7 GB |
| Working memory, 8K context | ~0.3 GB | ~0.5 GB |
| Ollama overhead | ~0.3 GB | ~0.5 GB |
| **Model total** | **~2.5–3 GB** | **~5.5–6 GB** |
| DynasBrain (search, embeddings) | ~0.5–1 GB | ~0.5–1 GB |
| **Total** | **~3.5–4 GB** | **~6.5–7 GB** |

LabVIEW with a project open uses another ~1–2 GB.

- **Laptop, 16 GB:** 7B fits comfortably.
- **PC with 8–9 GB in use:** 7B would make Windows swap to disk. That is not just slower;
  it can freeze the PC for minutes. That is why the model runs on the laptop. If a model is
  wanted on that PC too, use 3B, or free 1–2 GB first (check Task Manager → Memory).

## Speed (CPU, rough)

| | 3B | 7B |
|---|---|---|
| Reading question + search results (~3K tokens) | ~10–30 s | ~30–90 s |
| Writing | ~8–15 words/s | ~3–8 words/s |
| **Typical answer** | **~20–45 s** | **~1–2 min** |
| Multi-step VI creation (several tool rounds) | a few minutes | several minutes |

Slow answers are accepted. The Ask page shows progress and has a Cancel button. To keep it
usable, DynasBrain sends the model only the few most relevant search results.

## Offline installation

Ollama, the model and DynasBrain's embedding model are downloaded **once** on a machine
with internet, then copied.

1. **Ollama:** run `OllamaSetup.exe` from https://ollama.com. It needs Windows 10 22H2 or
   newer; check with `winver`.
2. **Model:** on a PC with internet:

   ```powershell
   ollama pull qwen2.5-coder:7b
   ollama pull qwen2.5-coder:3b      # fallback
   ```

   Models are stored in `%USERPROFILE%\.ollama\models`. To use them on another PC, copy that
   folder to the same place there.
3. **DynasBrain embeddings:** run one `dynasbrain ingest` with internet, so
   all-MiniLM-L6-v2 (~80 MB) is downloaded, then copy its cache along with DynasBrain.
4. **Fine-tuned model (later):** copy `labview-assistant.gguf` and `Modelfile`, then:

   ```powershell
   ollama create labview-assistant -f Modelfile
   ollama run labview-assistant "What does DAQmx Start Task do?"
   ```

## Serving the model over the cable

Ollama listens on `127.0.0.1:11434` by default. In this design the **relay runs on the same
PC as Ollama**, so Ollama does **not** need to be opened to the network. Leave it on
localhost.

## Modelfile (for the fine-tuned model)

```
FROM ./labview-assistant-Q4_K_M.gguf
SYSTEM "You are an expert LabVIEW engineer specialising in NI hardware, DAQmx, NI-XNET CAN bus, Modbus TCP, PROFINET, Siemens S120 drives, MCP tools and industrial test automation."
PARAMETER temperature 0.3
PARAMETER num_ctx 8192
```

A lower temperature (0.3) suits tool calling and AIXML better than 0.7.
