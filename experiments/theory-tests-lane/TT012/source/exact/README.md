# P05 exact sign alignment audit

Completed development audit. Start with [REPORT.md](REPORT.md); the derivation is
in [THEORY.md](THEORY.md). All 128 fixed donor pairs fail exact alignment on a cycle.
No long-running assay was launched. The fallback supplement was specified after
that result and is kept separate from the primary audit.

`PROTOCOL.md` defines the original question. `results_v1/START.json` binds the
primary scripts before saved-record analysis. `SOURCE_BINDINGS.json` binds copied
support modules and the preceding P05 source receipts. `COMPLETE.json` binds the
finished package, including later verification, the supplement and reports.
These commitments establish provenance, not preregistration.

Scripts refuse to overwrite result files. To reproduce, copy the root source and
configuration files into a new sibling directory within the theory lane, without
copying `results_v1`, then run these commands from that new directory using the
project Python environment. Set PYTHONDONTWRITEBYTECODE=1 and set OMP_NUM_THREADS,
OPENBLAS_NUM_THREADS and MKL_NUM_THREADS to 1. Keep pytest temporary data in the lane.

```text
python -m pytest -q -p no:cacheprovider --basetemp=<new-lane-cache-path> test_alignment.py
python audit.py
python symmetry.py
python verify.py
python fallback_diagnostic.py
```

The independent verifier uses a different parity implementation. Its first failed
attempt and the corrected full rerun are retained in `results_v1`. That was a pin
index ordering error in the verifier, not a changed analysis or dropped case.
The fixed package's test record is `results_v1/VALIDATION.json`.
