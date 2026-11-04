# Security, evaluation and release gates — LabVIEW AI v1.1

## Data ownership

AIXML, graphs, logs and synthesized explanations can expose proprietary logic even when raw .vi files are absent. Treat these as confidential by default. Never upload to a public GitHub repo or third-party cloud training job without authorization from the data owner.

The current repository is public. Source inventory output (even only filenames and hashes) may be sensitive. The local CLI does not upload; the cloud QLoRA script only reads a user-specified approved JSONL file and keeps outputs in the configured workspace.

## Controlled autonomy

Allowed without special hardware permission: source inspection, isolated AIXML parsing, typed-graph preparation, validator checks on public samples, generating scratch VIs when explicitly enabled, contained software-only tests with known side effects.

Approval required: overwrite/edit original source, modify real hardware output, DAQ/drive/PLC actuation, RT/FPGA deployment, tests that may start external processes or writes, network services exposed beyond local trusted boundaries, and training-data upload.

No tool with a destructive capability should be granted blanket authorization. Back up/commit first, log each attempted change and preserve original files.

## Acceptance metrics

| Dimension | Measured evidence | Not equivalent to |
|---|---|---|
| Well-formed AIXML | XML parsing passes | LabVIEW validation |
| Semantic AIXML validity | Target-version MCP validator passes | Executable VI |
| VI executable | Compilation/linker success | Correct behavior |
| Verified functionality | Independent input/output tests pass | All hardware conditions |
| Explanation correctness | Reviewer-verified functional/dataflow claims | Plausible prose |
| Debugging | Correct repair and regression suite | Silent XML rewrite |
| Local deployment | Peak 8GB memory, latency, stability with LabVIEW open | Cloud GPU score |

Independent public/private benchmarks must be separated at project-family level; deduplicate exact and near duplicates. Version every model, adapter, converter, catalog, benchmark and LabVIEW/MCP backend.

## Release registry

Prototype -> Validated -> Approved. Record base model SHA/revision, training-data hash/consent, adapters, random seed, hyperparameters, evaluation results, and rollback pointers. Weight-space experiments are separate forks with hash-level manifests and negative controls; never change stable checkpoints.

## Current verification boundary

Pure-Python unit tests can run in GitHub CI. Native VI generation, compilation and behavior testing require a Windows machine with LabVIEW and the appropriate MCP backend. Cloud QLoRA requires separately approved data and CUDA GPU. Neither environment is provided by this repository.
