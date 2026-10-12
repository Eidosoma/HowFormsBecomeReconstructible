# E002 — exact history-dependent accessibility

[Protocol](PROTOCOL.md) · [Pilot report](runs/pilot_v1/REPORT.md) ·
[Numerical summary](runs/pilot_v1/summary.json) ·
[Audit](runs/pilot_v1/INDEPENDENT_AUDIT.json)

784 complete transition maps, each with 1,024 starting states. A supplied
partial additive reader can redistribute access to the same recurrent
destinations or change which recurrent destinations exist. Cycles and repeated
founder outcomes are retained. An advantage over foreign history does not
necessarily imply an advantage over no record.

From the experiments root:

```bash
bash run_python.sh E002_history_accessibility/tests.py
bash run_python.sh E002_history_accessibility/run.py --output E002_history_accessibility/runs/NEW_RUN
bash run_python.sh E002_history_accessibility/audit.py E002_history_accessibility/runs/NEW_RUN
```

`NEW_RUN` must not exist. This repeats the declared pilot rulebooks; it is not
a new confirmation cohort. The audit independently recomputes every saved
transition with scalar updates. Complete successor tables, cycle members,
basin assignments, founder histories, and packet values remain available.

![Finite accessibility maps](runs/pilot_v1/accessibility.png)
