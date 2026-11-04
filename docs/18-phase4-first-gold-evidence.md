# Phase 4 — first LabVIEW 2026 manual functional evidence

The operator reported these passing cases for the **True** branch of the copied `F to C (SUB VI).vi`:
32 °F → 0 °C, 212 °F → 100 °C, −40 °F → −40 °C, 98.6 °F → 37 °C.

The block-diagram screenshot showed a Boolean-controlled case structure with the True branch calculating `(F-32) * (5/9)`. The False branch was not inspected. These observations **do not** establish comprehensive Gold qualification or permission to train.

From the PyCharm terminal, after `git pull` and running tests:

```powershell
python -m scripts.phase4_gold_evidence --original "D:\Karthikeyan\Training Data\New folder\New folder (2)\Labview-Training-master\Labview-Training-master\DAY 1\F to C (SUB VI).vi" --copy "D:\Phase4\NativeVerification\F to C (SUB VI).vi" --out "D:\Phase4\NativeVerification\f_to_c_evidence.json" --reviewer "local-operator"
```

This writes metadata locally, verifies both VI files exist, and records their SHA-256 values. It does not run LabVIEW and will not overwrite an existing evidence file. If the scratch file differs from the original, it is **not** a Gold candidate.

Before final Gold promotion: inspect and document the False branch, validate the saved scratch VI state and compile/run arrow, record actual execution evidence and LabVIEW version, verify source rights, and independently reproduce the input/output checks. Do not execute hardware or filesystem/database interactions without review. Keep local paths, screenshots, and underlying VIs out of the public repository.

The 1,218 structurally verified representations remain Silver candidates. The 48 failed conversions remain excluded. No data is authorized for cloud training by this evidence recorder.
