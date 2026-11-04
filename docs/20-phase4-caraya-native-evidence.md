# Phase 4 — import native Caraya evidence (F-to-C)

Scope: **one verified scratch VI only**. The Caraya JUnit XML submitted on
2026-11-04 reported `tests=8`, `failures=0`, `errors=0`, `skipped=0`,
using Caraya 1.4.4.148. A separate generator report confirmed direct calls
to `F to C (SUB VI).vi`, with an executable native test VI.

## Before running

- Preserve the original source VI, scratch VI and generated Caraya test VI.
- Keep the Caraya XML locally (it is **not** pushed into GitHub by this importer).
- Confirm the manual evidence v2 exists at
  `D:\Phase4\NativeVerification\f_to_c_evidence_v2.json`.
- Copy the generated JUnit report to
  `D:\Phase4\NativeVerification\Test F to C.xml`
  (or supply its actual local path).

From the repo root in PyCharm PowerShell, after `git pull`:

```powershell
python -m unittest tests.test_phase4_import_caraya_evidence -v

python -m scripts.phase4_import_caraya_evidence `
  --junit "D:\Phase4\NativeVerification\Test F to C.xml" `
  --evidence "D:\Phase4\NativeVerification\f_to_c_evidence_v2.json" `
  --original "D:\Karthikeyan\Training Data\New folder\New folder (2)\Labview-Training-master\Labview-Training-master\DAY 1\F to C (SUB VI).vi" `
  --scratch "D:\Phase4\NativeVerification\F to C (SUB VI).vi" `
  --test-vi "D:\Phase4\NativeVerification\Tests\Test F to C.vi" `
  --out "D:\Phase4\NativeVerification\f_to_c_native_caraya_v1.json"
```

The importer refuses mismatched original/scratch SHA-256, wrong manual evidence
revision, missing/duplicate case identities, malformed or failing JUnit, and
existing output files. It reads all VIs without modifying them.

Expected interpretation of a successful importer run:

- `native_functional_verified=true`
- `gold_candidate=true`
- `gold_verified=false` (final provenance and curation review outstanding)
- `training_eligible=false`, `cloud_approved=false`

Retain the original JUnit, the generated native test VI, the direct-route
generator report and the evidence JSON for audit. Do not count this one
native case as proof that the other 1,217 structural candidates are functional.
