# E006 — compact records through three replacements

[Report](runs/development_v1/REPORT.md) · [Protocol](PROTOCOL.md) ·
[Audit](runs/development_v1/INDEPENDENT_AUDIT.json)

Both 512- and 128-byte records passed the declared serial-renewal criteria.
At 128 bytes, terminal own-minus-foreign agreement was +2.04 [0.61, 3.81]
percentage points (97.5% interval, accounting for the two compressed sizes).
The field was re-encoded at every boundary, including three body-written
replacements followed by an independent fresh reader.

Absolute founder agreement fell from 72.14% with 2048 bytes to 67.30% with
128 bytes. Protected copies remained better at every capacity. This is
development evidence on 64 reused founders with fresh recipient futures;
compression changes spatial resolution and field amplitude together.

Main runtime: 54.13 seconds. The independent audit checks all 48 raw files,
15,360 score observations, intervals, byte budgets, copying, erasure, and
encoded-value scrambling. A reporting-only failure in the first disposable
benchmark is preserved in `runs/benchmark_v1`; its correction changed no
scientific parameters. The full successful benchmark is `benchmark_v2`.

![Serial reconstruction across packet sizes](figures/compact_renewal.png)

The terminal compressed intervals use 97.5% coverage; other displayed
intervals are pointwise 95%. Shared geometry and decoding machinery are
excluded from the inherited byte count.

To repeat the same known founders with the same declared futures into a new
directory, from the experiments root:

```bash
bash run_python.sh E006_compact_renewal/tests.py
bash run_python.sh E006_compact_renewal/run.py --workers 12 --output E006_compact_renewal/runs/NEW_RUN
bash run_python.sh E006_compact_renewal/audit.py E006_compact_renewal/runs/NEW_RUN
```

Another output directory alone does not create an independent cohort.
