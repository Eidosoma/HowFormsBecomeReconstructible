# H002: complete rewriting under reduced cue support

The [protocol](PROTOCOL.md) specifies a 24-block prospective development
experiment. Complete rewriting and a half-retained record each face eight or
four clamped input sites, with matched births, damage and controls through
16 activity replacements. This is a forms model extension on new inputs,
using the lane's H001 implementation. It is not publication confirmation.

The development run completed in 688.37 seconds on one worker. All 24 blocks
and 3,224 integrity checks passed. Both writers qualified as capture candidates;
both failed the taught-function gates under reduced cue support. This is a
development result. See the [report](../runs/h002_development_v1/REPORT.md),
[numerical summary](../runs/h002_development_v1/summary.json) and
[figure](../runs/h002_development_v1/overview.png).

The run was launched detached on 11 October 2026:

- [Frozen launch specification](../runs/h002_development_v1_launch.json)
- [Durable status](../runs/h002_development_v1/STATUS.json)
- [Execution log](../runs/h002_development_v1.log)

The run retains `audit.json`, `summary.json`, `REPORT.md`, and PNG/PDF figures
alongside the full raw evidence. The original conservative launch forecast was
about 22 minutes. Follow the shared [execution policy](../../RUN_POLICY.md)
for future runs.

The two excluded engineering runs, `h002_benchmark_v1` and
`h002_benchmark_v2`, share seed 11900 and two replacements. Every scientific
array agrees between them. Each passed 58 boundary, source and replay checks.
The later run adds a portable source directory layout, explicit figure labels
and record-strength diagnostics; it changes no simulated outcome or gate.

From the lane root, another excluded engineering replay can be run with:

```bash
bash run_python.sh h002/experiment.py --mode benchmark --output runs/NEW_BENCHMARK
```

For an exact full-cohort reexecution, use `--mode development` with a new output
directory and detached execution. That repeats the registered development
seeds; it is not fresh confirmation. `launch.py` is the one-time launcher for
the named campaign and refuses to overwrite it.

Frozen source trees in v2 and later preserve `model.py`, `run.py` and the
`h002/` directory. Execute the frozen `h002/experiment.py` with the pinned
Python interpreter, numerical threads set to one, and an output path inside
that frozen source tree. Set matplotlib/cache directories inside the lane.
This permits replay even after the working source changes.
