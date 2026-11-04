# Phase 4 — resume LabVIEW 2026 dataset conversion (PyCharm)

This is a **local-only** operation. The program reads the existing manifest, checks every VI against its saved SHA-256, retries failed records with the *pylabview* `vi2aixml.py` converter, verifies the graph and normalization, and checkpoints results after each attempted VI. It never modifies the source VIs. No files are uploaded.

## Inputs from the earlier Codex machine

- `outputs/FourFolders/batch-results.json` from the supplied `outputs.7z` archive.
- The original folders under `D:\Karthikeyan\Training Data\New folder\New folder (2)` (or a new equivalent root with the same relative paths).
- The `vi2aixml.py` converter from your working LabVIEW MCP/pylabview installation. This is an external dependency, **not** bundled in this repository.

Run these commands from the **PyCharm terminal** in the cloned repo, updating paths for your PC. First check the manifest and source-file hashes **without conversion**:

```powershell
python -m scripts.phase4_retry --manifest "D:\Phase4\batch-results.json" --source-root "D:\Karthikeyan\Training Data\New folder\New folder (2)" --output-dir "D:\Phase4\retry"
```

After reviewing `retry-report.json`, test one failed conversion:

```powershell
python -m scripts.phase4_retry --manifest "D:\Phase4\batch-results.json" --source-root "D:\Karthikeyan\Training Data\New folder\New folder (2)" --output-dir "D:\Phase4\retry" --converter "C:\path\to\aixml-pylabview\vi2aixml.py" --run --limit 1
```

For the remaining failures, rerun using the checkpoint `D:\Phase4\retry\batch-results.json` as `--manifest`, remove `--limit 1`, and keep the same output directory. The output includes `retry-report.json`, `batch-results.json`, and `aixml/<sha256>/` for successful conversions.

Run `python -m unittest discover -s tests -v` before and after. Test results on synthetic fixtures do **not** establish that all real-world VIs converted correctly. Any remaining failures are retained for review. **Do not publish the resulting files or train on them until source rights, confidentiality, and functional quality have been reviewed.**

The old native MCP fallback script assumed every response carried a top-level `results` key and stopped with `KeyError: 'results'`. The new retry uses the existing offline converter interface instead. It does not claim to reproduce or automatically repair unsupported VIs.
