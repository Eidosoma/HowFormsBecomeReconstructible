# E001 — unprescribed capture and renewal

[Protocol](PROTOCOL.md) · [Pilot report](runs/pilot_v1/REPORT.md) ·
[Numerical summary](runs/pilot_v1/summary.json) ·
[Audit](runs/pilot_v1/INDEPENDENT_AUDIT.json)

64 uninstructed founders, all retained. Shared heterogeneous backgrounds passed
the pilot's complete formation/capture/renewal criteria. Homogeneous founders
had a larger history-specific reconstruction effect but failed the formation
qualification. Both conditions lost fidelity relative to unchanged copying.
These are development results, not fresh-cohort confirmations.

From the experiments root:

```bash
bash run_python.sh E001_unprescribed_capture/tests.py
bash run_python.sh E001_unprescribed_capture/run.py --workers 12 --output E001_unprescribed_capture/runs/NEW_RUN
bash run_python.sh E001_unprescribed_capture/audit.py E001_unprescribed_capture/runs/NEW_RUN
```

`NEW_RUN` must not exist. The pilot takes roughly half a minute on this host;
respect the [ten-minute detachment rule](../RUN_POLICY.md) for larger follow-ups.
The current runner repeats the **same pilot cohort**; a new output directory
alone is not a fresh confirmation. New scientific cohorts require new declared
IDs and a new frozen protocol/code version.

![All-cohort reconstruction](runs/pilot_v1/renewal.png)

The fixed [example panel](runs/pilot_v1/fixed_examples.png) shows every founder
in block 0, recipient 0, chosen by identity rather than outcome. The raw fields,
all packet bytes, formation observations, and score rows are retained in the
run directory. The smaller-packet panel tests one transfer only.
