# Phase 4 — batch Caraya automation (local LabVIEW host)

This automates **preflight**, **approved test VI generation**, and **post-run
JUnit result checks** for up to 20 jobs per manifest. It does **not** execute a
LabVIEW VI, create a scratch `.lvproj`, or turn unknown expected values into
independent truth. Those require an independently reviewed test specification.
Original VI bytes are read-only. No cloud upload or dataset gold promotion.

## Run the offline tests

From PyCharm terminal in the repository directory:

```powershell
git pull
python -m unittest tests.test_phase4_auto_batch tests.test_phase4_collect_batch_junit -v
```

## Start with sum.vi

There is an example in `configs/phase4_sum_batch_template.json`. It is **not
an authorization**: the flags `manually_reviewed` and
`risk_accepted_for_generation` are false. Leave them false until a human has
checked the full diagram, dependency tree, output semantics and other side
effects. Also confirm that `Numeric 4` is indeed `A-B`, not `B-A`, because
unverified expected results make bad tests.

The `source` and `scratch` paths and hash are based on the prior checks.
Create an isolated LabVIEW project at
`D:\Phase4\NativeVerification\Sum\SumVerification.lvproj` that explicitly
lists only the scratch `sum.vi`, similar to the working F-to-C direct project
route. Do not add original VIs to that project.

Run non-executing preflight:

```powershell
python -m scripts.phase4_auto_batch --manifest "configs/phase4_sum_batch_template.json" --scratch-root "D:\Phase4\NativeVerification\Sum" --output-dir "D:\Phase4\review\sum-batch-preflight-v1"
```

Expect `blocked_review` until the project exists and the human-review flags
are deliberately set true in a local copy of the manifest. The tool will not
execute any VIs.

After review and approval, use a local copy of the manifest with both flags
true. Do **not** commit the signed-off manifest without considering privacy
and permissions. Generation only:

```powershell
python -m scripts.phase4_auto_batch --manifest "D:\Phase4\review\approved-sum-batch.json" --scratch-root "D:\Phase4\NativeVerification\Sum" --output-dir "D:\Phase4\review\sum-batch-generation-v1" --generate
```

This calls the working LabVIEW MCP `lvai_generate_test` direct route using
the subject scratch VI, custom cases, and scratch project. No execution is
performed. Review the generated test call targets before running any VI. A
report status of `generated_needs_call_target_review` is intentionally **not**
a functional test pass.

## Collect results after running via Caraya

Only after the generated VI and dependencies have been reviewed and native
Caraya tests have been executed in LabVIEW, save the Caraya JUnit XML at the
job's `junit` path. Then use the same approved manifest:

```powershell
python -m scripts.phase4_collect_batch_junit --manifest "D:\Phase4\review\approved-sum-batch.json" --out "D:\Phase4\review\sum-caraya-evidence-v1.json"
```

The collector checks source/scratch hashes, test VI presence, expected case
identities, suite name and all pass/fail/error/skip counters. It never executes
the VI. A matched JUnit file is a functional **candidate**, not cryptographic
proof of the exact VI binary invoked; retain MCP generation logs and the
test project in audit evidence.

Use a **new output directory/file** for subsequent attempts: both steps
refuse overwriting prior evidence.

## Restrictions

- No autonomous execution of 1,218 VIs, hardware, networking or side-effecting code.
- No expected results inferred blindly from the VI itself.
- Unknown candidates remain blocked. Approved independent truth tables are required.
- No dataset-wide gold promotion, training eligibility or cloud approval.
- This code was pushed to GitHub but requires local Python tests and LabVIEW
  integration checks before it is considered production-ready.
