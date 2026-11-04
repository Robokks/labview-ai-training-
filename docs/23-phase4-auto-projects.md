# Phase 4 — automatic scratch LabVIEW project creation

No more manual File → Create Project steps.

The `phase4_create_projects` command clones the XML structure of the
**working** F-to-C verification project and creates one project per batch
manifest job, each containing only the job's scratch VI. It preserves the
existing project's root/target properties and removes the template's other
project items. The original template and source VI remain read-only.

## 1. Run the automatic project creation

Open PyCharm terminal at the repository root.

```powershell
git pull
python -m unittest tests.test_phase4_create_projects -v
```

Then (single line):

```powershell
python -m scripts.phase4_create_projects --template "D:\Phase4\NativeVerification\FtoCVerification.lvproj" --manifest "configs/phase4_sum_batch_template.json" --scratch-root "D:\Phase4\NativeVerification\Sum"
```

Expected: `projects_created: 1`, and a new project at:
`D:\Phase4\NativeVerification\Sum\SumVerification.lvproj`.

The script validates source and scratch SHA-256, verifies paths stay in the
scratch root, prevents overwrites, and never opens or executes the VI.

## 2. Confirm the project structure

```powershell
Test-Path "D:\Phase4\NativeVerification\Sum\SumVerification.lvproj"
```

`True` confirms project **file creation only**. Actual compatibility,
relative dependency resolution and native opening require LabVIEW verification.
A successfully created XML file is not equivalent to a LabVIEW-verified project.

## 3. Preflight

Use a new output directory if repeating preflight:

```powershell
python -m scripts.phase4_auto_batch --manifest "configs/phase4_sum_batch_template.json" --scratch-root "D:\Phase4\NativeVerification\Sum" --output-dir "D:\Phase4\review\sum-batch-preflight-v2"
```

`blocked_review` is expected because the template intentionally retains
`manually_reviewed=false`. We have not yet independently verified all
expected outputs and dependencies.

Do not flip approval flags merely to bypass the review gate. After review,
create a separate local approved manifest for automatic test generation.
