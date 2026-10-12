# E007 — fresh confirmation of compact renewal

[Protocol](PROTOCOL.md) · [Report](runs/confirmation_v1/REPORT.md) ·
[Independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json)

**Confirmed on 128 fresh founders in 32 blocks.** All formation, acquisition,
specificity, reading and writing gates passed at 128 and 2048 bytes. The compact
terminal own-minus-foreign advantage is +1.66 [1.14, 2.17] percentage points
(95% whole-block interval). Every declared founder remains included.

Absolute own agreement is 67.35% at 128 bytes and 71.29% at 2048 bytes.
Compact renewal remains 1.29 [0.79, 1.82] points below same-budget protected
copying. This confirms a modest historical distinction through three rewrites
and a fresh terminal reader. The comparison changes spatial resolution and
field amplitude together, and excludes shared reader/writer machinery from
packet size. It is a fresh-cohort confirmation in the existing codebase.

The audit checks formation, 64 raw lifecycle files, 20,480 individual score
observations, intervals, packet budgets, copying, erasure and control identities.
No tuning, pooling or scientific cohort extension occurred.

![Compact confirmation](figures/compact_renewal.png)

From the experiments root:

```bash
bash run_python.sh E007_compact_confirmation/tests.py
bash run_python.sh E007_compact_confirmation/run.py --workers 12 --output E007_compact_confirmation/runs/NEW_RUN
bash run_python.sh E007_compact_confirmation/audit.py E007_compact_confirmation/runs/NEW_RUN
```

NEW_RUN must not exist. This repeats the same declared cohort, not another
independent sample. The disposable benchmark and runtime forecast are retained.
