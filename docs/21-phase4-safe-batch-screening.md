# Phase 4 — safe batch shortlist before native verification

The prior F-to-C Caraya run verified **one** VI (8/8 assertions). This workflow
prepares the *next* candidates, but does not generate test cases or execute a VI.

## 1. Screen the structurally verified corpus (offline, read-only)

From PyCharm, after \`git pull\`:

\`\`\`powershell
python -m unittest tests.test_phase4_batch_review -v
python -m scripts.phase4_batch_review screen --structural-index "D:\Phase4\structural\structural-index.jsonl" --archive "C:\Users\DynaAdmin\Documents\Codex\2026-11-04\ip-motor-mode\outputs\FourFolders\batch-conversion.zip" --out "D:\Phase4\review\math-batch-review-v1.json" --limit 3
\`\`\`

**Adjust \`--structural-index\` and \`--archive\` to their actual existing
locations.** Find the structural index if needed by running:
\`\`\`powershell
Get-ChildItem "D:\Phase4" -Recurse -Filter structural-index.jsonl -File | Select-Object -ExpandProperty FullName
\`\`\`

Output is a shortlist of *names that suggest math* and whose metadata does not
contain specified risky keywords. This is not proof of safety, purity, correct
behavior, executability, or eligibility. Files remain in their source location.
No training approval or cloud permission is granted.

## 2. Manual review (mandatory)

Open each candidate in LabVIEW 2026 and inspect **all** subVI dependencies,
diagram structures, VI Server properties and side effects; rule out hardware,
file system, networking, database and control operations. Check licensing and
source ownership. Record the intended truth table and expected numeric values.
Reject anything unknown or stateful. A name-based heuristic can miss hazards.

## 3. Optional scratch staging (copy only; no execution)

After manual review, create a **local** JSON file, e.g.
\`D:\Phase4\review\scratch-approval-v1.json\`:

\`\`\`json
{
  "schema": "phase4-scratch-staging-approval-v1",
  "reviewer": "YOUR_LOCAL_REVIEWER_ID",
  "approved_sha256": ["PASTE_ONE_HASH_FROM_THE_SHORTLIST"],
  "safe_for_scratch_copy": true,
  "authorizes_vi_execution": false
}
\`\`\`

Use a literal SHA-256 from the shortlist, not this placeholder. Approval is only
for staging copies (up to 3 VIs). Source root must be the directory relative to
which the manifest's \`source_paths\` were recorded.

\`\`\`powershell
python -m scripts.phase4_batch_review stage --plan "D:\Phase4\review\math-batch-review-v1.json" --approval "D:\Phase4\review\scratch-approval-v1.json" --source-root "D:\Karthikeyan\Training Data\New folder\New folder (2)" --scratch-root "D:\Phase4\BatchNativeScratch" --out "D:\Phase4\review\math-batch-staged-v1.json"
\`\`\`

The tool checks every source SHA-256 before copying, validates every staged
copy, never overwrites a staged VI or report, and does **not** open, run or
modify the original VI.

## 4. Separate execution authorization and evidence

Before executing a test, independently verify dependencies and the newly
created scratch VI, define deterministic input/expected-output cases, build
or generate a native Caraya test against a scratch-only LabVIEW project, and
inspect the actual call targets. Use JUnit XML to prove all cases were run.
Do not reuse the F-to-C-specific JUnit importer for other VIs: their expected
case identities, source hashes and permissions require separate validators.

This stage deliberately stops **before** VI execution. \`gold_verified\`,
\`training_eligible\`, and \`cloud_approved\` remain false or unassigned for
all new candidates.

## Safety and limitations

- Numeric/mathematical-looking names do not imply side-effect-free behavior.
- Keyword screening is not static analysis and may miss an indirect unsafe call.
- The structural index contains paths, not local source file byte streams; the
  staging operation insists on a matching SHA-256 from the original manifest.
- No private VIs, training data, or evidence are uploaded to GitHub by these tools.
- Do not approve or automatically execute any hardware, networking, database,
  motion, driver, or file-mutating VI.
