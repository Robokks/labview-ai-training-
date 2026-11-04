# Cloud training and evaluation runbook

**No model has been fine-tuned by this repository yet.** Free or paid cloud GPU must be explicitly provisioned and approved. There is no GPU key, private training corpus, or scheduled training job in this repository.

## Preparation

- Complete P0/P1 on public sample files and P2/P3 extraction.
- Make reviewed, provider-approved `train.jsonl`, `validation.jsonl`, `test.jsonl` using the fail-closed CLI.
- Run baseline evaluations for Qwen3-1.7B and Qwen3.5-2B before training.
- Check model licenses and current Transformers/PEFT/bitsandbytes compatibility (especially for Qwen3.5 multimodal support).
- Keep private held-out examples local: never transmit them to a free GPU session without authorization.

## Cloud pilot

1. Start an authorized CUDA environment (free GPU first, paid only within approved INR 500–2000 limit).
2. Clone this repo branch into the cloud session.
3. `pip install -e ".[cloud]"` (record exact dependency versions).
4. Stage ONLY approved non-confidential examples; never store credentials in source.
5. `python scripts/train_qlora.py --train-jsonl approved/train.jsonl --model Qwen/Qwen3-1.7B --output-dir results/pilot`
6. Evaluate against the unmodified base and against unseen public holdouts using separate evaluators.
7. Save adapter weights and training manifest in access-controlled artifact storage (no auto push to a public Hugging Face model).
8. Repeat a comparable pilot for the second model only if its target architecture is supported and budget allows.
9. Select foundation model on task pass rates, stability, local 8 GB RAM and CPU response time.
10. Train shared LabVIEW checkpoint, then four LoRA adapters; verify each independently.

## Status and limitations

The cloud script is an illustrative, opt-in CUDA PEFT SFT trainer; it has not been tested on a GPU in this session. It does **not** implement token-level preference optimization, weight-space editing, GGUF export or LabVIEW native validation yet. Avoid claiming performance improvements until measured.

## Evaluation gates

AIXML syntax, target version validator, native VI executable state, verified functional outputs, explanation fidelity, repair regression, project graph preservation, privacy compliance, and deployment memory are distinct axes. Gate releases on critical failures, not an averaged metric.

## Weight-space experiments

Only on isolated shared checkpoint copies, never the unmodified base or production model. Compare matched tasks, negative controls, prompt/retrieval alternatives and held-out performance. Preserve complete edit hashes and rollback paths.
