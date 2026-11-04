# Phase 4 — native LabVIEW 2026 F-to-C COM verification

The operator has already manually executed **both Boolean branches** of the copied
`F to C (SUB VI).vi`, with four reported passing values per branch.
`f_to_c_evidence_v2.json` records those statements. This workflow attempts
independent repeatable execution using the **already-running LabVIEW 2026**
COM interface and writes a new local JSON report.

Before running: close the VI's open edit windows or ensure no unsaved changes, start
LabVIEW 2026, and confirm the copied VI has no unexpected external operations.
Do not run the full 12-VI queue with this script. It is deliberately restricted
to the reviewed F-to-C binary hash and exact control names.

In PyCharm (Windows, Python 3.12):

```powershell
git pull
python -m pip install pywin32
python -m unittest discover -s tests -v
python -m scripts.phase4_native_f_to_c --vi "D:\Phase4\NativeVerification\F to C (SUB VI).vi" --original "D:\Karthikeyan\Training Data\New folder\New folder (2)\Labview-Training-master\Labview-Training-master\DAY 1\F to C (SUB VI).vi" --evidence "D:\Phase4\NativeVerification\f_to_c_evidence_v2.json" --out "D:\Phase4\NativeVerification\f_to_c_automated_v1.json" --run
```

The run requires a running LabVIEW 2026 COM automation server, and the external
`pywin32` package. It binds to the existing LabVIEW instance with
`GetActiveObject("LabVIEW.Application")`. If that binding is unavailable,
report the COM error; do not force-terminate LabVIEW or launch multiple instances
until the actual session and registration state are understood.

Eight inputs are tested: Boolean=True returns (0,100,-40,37) for F=(32,212,-40,98.6).
Boolean=False returns (32,212,-40,98.6) unchanged. Float comparison uses
an absolute tolerance of 1e-6. Source and scratch SHA-256 values are checked against
manual evidence before execution and again after the eight runs. No VI save operation
is called. Output paths must not already exist; the tool will not overwrite
previous evidence. If COM fails partway through, the case is marked failed in the
report. The process exits nonzero when any of the eight checks fail.

Automated success is an important step, **not automatic Gold promotion**:
the script deliberately leaves `gold_verified`, `training_eligible`,
and `cloud_approved` false until remaining compile/dependency,
independent review, IP/confidentiality, and authorization checks are completed.
Keep this report and the source VIs local; do not publish private path metadata.
