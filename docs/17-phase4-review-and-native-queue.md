# Phase 4 review plan — local only

This step follows the completed 1,218-record FourFolders structural audit. It **does not** authorize training or execute any LabVIEW VI.

From PyCharm:

```powershell
git pull
python -m unittest discover -s tests -v
python -m scripts.phase4_review_plan --structural-index "D:\Phase4\structural\structural-index.jsonl" --output-dir "D:\Phase4\review"
```

Outputs in `D:\Phase4\review`:

- `review-report.json`: family assignment counts, held-out coverage warning, and limitations.
- `split-plan.jsonl`: records with deterministic proposed family splits, unchanged source paths, and both permission flags false.
- `permission-review.csv`: blank owner, license, local/cloud approval and confidentiality assessment fields. The source owner must review each family; no auto-approval.
- `native-verification-queue.jsonl`: small SHA-selected sample per family (default 3) for **manual, authorized** scratch-copy checks with LabVIEW 2026. Do not run potentially hardware-interacting VIs without reviewing their behavior and dependencies first.

Only four folder-level families are present, so an 80/10/10 deterministic split may leave one or more partitions empty. Even if all splits are populated, file-level resemblance can cross family boundaries; near-duplicate and dependency checks are still required for a defensible held-out benchmark.

Silver candidates passed AIXML structural equivalence checks, **not** functional validation. The native queue is a request for evidence, not a functional test result. No Gold examples or SFT examples are created here. Do not commit source VIs, AIXML, graphs, or permission-review documents containing private information into this public repository.
