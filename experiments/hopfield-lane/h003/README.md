# H003: cue-specific function through complete rewriting

The [protocol](PROTOCOL.md) tests a lead from the completed H002 cohort. In its
four-site complete-writer condition, 49.74% of final readers gave the same
confident response to both opposite cues. The output patches still strongly
opposed each other, while connections associating their response with the cue
were often erased or inverted. See the separately retained
[post-hoc diagnosis](../runs/h003_diagnosis_v1/REPORT.md).

For the existing coactivity writer, identical responses under opposite cues
cancel their contributions to input/output connections. The diagnostic checks
this equation against every saved own-record boundary. It does not change
H002's endpoint or its failed functional qualification.

H003 uses 24 fresh base networks, seeds 13000–13023, through 16 replacements.
It changes the strength of edges incident on the four cue sites while keeping
the body-only writer fixed. The primary gain is 4. A gain-2 dose, a gain-1
baseline, gain at unrelated sites, all nine record interventions, late-only
gain and a longer terminal read provide separate controls. No output clamp or
teacher is available after formation.

The full development run completed in 360.76 seconds. Gain 4 passed all
prespecified candidate gates: terminal own-record function was 89.58%
[85.94, 92.97], versus 31.51% [26.56, 36.72] at baseline. Applying gain 4 only
to the final baseline read achieved 45.31% [40.62, 50.00]. The earlier-versus-
later intervention contrast also passed. All 970 integrity checks passed.
See the [report](../runs/h003_development_v1/REPORT.md),
[numerical summary](../runs/h003_development_v1/summary.json) and
[figure](../runs/h003_development_v1/overview.png).

The full-horizon seed-12900 engineering benchmark passed four scientific
fixtures and 50 retained-data checks in 15.77 seconds. It is excluded from
the development cohort. The conservative full-run forecast was 378 seconds,
so execution was attached on one worker with one numerical thread. See
[runtime forecast](RUNTIME_FORECAST.json),
[completed status](../runs/h003_development_v1/STATUS.json).

The result supports preserving the cue/output relationship through rewriting.
It remains development evidence in a supplied reader/writer architecture.
Protected copying achieved 98.70%, and gain 4 applied at unrelated sites reached
27.08%. The H002 failure under its original reader is retained unchanged.

All source snapshots, records, bodies, masks, ordinary readers and late readers
are retained. Existing outputs are refused. From the lane root, exact replays
use a new output directory:

```bash
bash run_python.sh h003/experiment.py --mode benchmark --output runs/NEW_H003_BENCHMARK
bash run_python.sh h003/experiment.py --mode development --output runs/NEW_H003_REPLAY
```

The development command repeats this cohort; it is not fresh confirmation.
Follow [the execution policy](../../RUN_POLICY.md) when changing runtime scope.
The frozen `source/` preserves the directory hierarchy and can execute with
the pinned interpreter and an output path inside that source tree. Set
numerical threads to one and caches inside the lane.
