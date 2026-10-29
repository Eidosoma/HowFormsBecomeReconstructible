# H035 — Two acquired cue rules through complete rewriting

**Completed at 15:35:10 UTC on 17 October 2026.** All eight pilot networks
finished. Controller **829999** and its workers have exited. Elapsed time was
**19m32s**, including **17m11s** waiting for shared CPU capacity; work and
bookkeeping took **2m21s**. No later campaign was launched.

Verdict: **STARTING_TASK_PASSES_REWRITING_LIMITED**. The starting-task screen
passes; the rewriting and selective-content screens fail. All **14 controls
and 6,112 numerical/boundary audit checks** pass across the eight engineering
benchmark executions and eight pilot blocks (3,056 checks for the pilot).

The [protocol](PROTOCOL.md) compares A alone, B alone and both at matched
four-trial update and writer budgets. Four acquisition histories assign two
independent rule signs. Eleven arms include selective foreign records,
erasure, read/write blocks and copying. Each of the eight base networks has
four histories and two descendants per history: 64 related readouts per
condition, with **eight independent networks**, not 64 independent samples.

| Condition | Rule A | Rule B | Both rules |
| --- | ---: | ---: | ---: |
| Both-rule load, initial | 90.62% | 90.62% | 81.25% |
| Both-rule load, 16 rewrites | 23.44% | 31.25% | 10.94% |
| Both-rule load, protected copy at G16 | 79.69% | 76.56% | 59.38% |
| A alone, 16 rewrites | 93.75% | untrained | — |
| B alone, 16 rewrites | untrained | 90.62% | — |

Both-rule renewal joint success is 48.44% at G1, 29.69% at G4, 28.12% at
G8 and 10.94% at G16. Every network has lower joint performance at G16 than
initially, and protected copying outperforms renewal on every network at G16.
The mean G16 protected-copy advantage is **48.44 percentage points**. The
unchanged protected records are tested with fresh activity at each checkpoint;
variation in their readout rates does not mean the copied weights deteriorated.

Selective foreign records express the changed donor rule and preserve the
other rule sufficiently to pass all initial selective-content gates. At G16,
donor-rule reconstruction is only 23.44% for foreign A and 31.25% for foreign B;
the required selective-content lead fails. Erasure, read-off, write-off,
scrambled records, scrambled writers and cumulatively damaged copying all
have zero both-rule joint success at G16. Renewal exceeds damaged copying by
10.94 points but fails the other required rewriting gates; that one contrast
does not rescue the screen.

This pilot exposes a load-sensitive failure in the declared damage, reading
and rewriting chain. The individual-rule declines show that the result is
not solely a stricter joint observer. It does not yet isolate damaged reading
from the coactivity writer as the cause. A bounded next diagnosis can trace
where errors first appear in the saved bodies and records, then use a declared
intervention if needed. No fresh confirmation, predictor search or manuscript
change follows automatically. Earlier H031/H033 findings remain separate.

The subsequently authorized [H036 diagnosis](../h036/README.md) completed on
17 October. Its matched fresh probes show a first-boundary joint decline
from 69.14% to 50.39% under intact read/rewrite, on every network. Correct
bodies preserve their success under warm replay, yet their rewritten records
often fail in fresh recipients. This identifies a fresh-reconstruction
limitation even without first-boundary damage; cue access, settling time and
encoding remain to be separated. It uses different probe tapes, leaves all
H035 results intact, and does not test a fully undamaged serial lineage.

The four-block serial/parallel benchmarks took **78.552/21.369 seconds**
(**3.68x** speedup), with **80 exactly equal arrays** and matching audits.
Four workers were selected before pilot inputs. The main eight-network stage
took **30.654 seconds** excluding admission waits. All numerical libraries
used one thread per worker.

Independent retained-evidence closeout at **16:31:35 UTC** passed **1,500
checks** in 2.053 seconds. It verified all **71 final checksum entries**, stage
seals, live/frozen source agreement, benchmark equality, all 6,112 saved audit
checks, every one of the 1,320 network-outcome CSV rows and every frozen gate.
A separate observer using binary matching counts reconstructed all per-rule,
joint and donor scores directly from retained activity. No trajectory or
predictor was rerun. The figure was inspected.

The engineering smoke remains separate and excluded: one block, 14 controls,
382 audit checks, 14.274 seconds for generation/I/O/replay. No scientific
setting or threshold was changed after those engineering outcomes.

An administrative amendment removes measured CPU waits from the compute
forecast before scaling by block count. Both old/new workflow and protocol
hashes are recorded; scientific model, design, analysis, audit and fixture
sources remain byte-identical to the immutable smoke package.

[Pilot report](../runs/h035_pilot_v1/REPORT.md) ·
[Summary and all gates](../runs/h035_pilot_v1/summary.json) ·
[Network outcomes](../runs/h035_pilot_v1/network_outcomes.csv) ·
[Figure](../runs/h035_pilot_v1/overview.png) ·
[Exportable PDF](../runs/h035_pilot_v1/overview.pdf) ·
[Independent closeout](../.cache/h035_closeout_v1.json) ·
[Completed status](../runs/h035_pilot_v1/STATUS.json) ·
[Smoke report](../runs/h035_smoke_v1/REPORT.md) ·
[Frozen pilot configuration](../runs/h035_pilot_v1/config.json) ·
[Launch ledger](../runs/h035_pilot_v1_launch.json).

```bash
bash run_python.sh h035/workflow.py --mode smoke --version v1
bash run_python.sh h035/workflow.py --mode pilot --version v1
```

Each command refuses occupied destinations. The pilot requires a completed
smoke run and unchanged scientific sources. Its workflow includes both
engineering benchmarks, chooses four workers only after measured speedup
and exact equality, and then runs exactly eight pilot networks. A forecast
above ten minutes runs detached under the shared execution policy. No
confirmation, further campaign or manuscript edit is automatic.
