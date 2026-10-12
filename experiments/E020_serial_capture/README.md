# E020 — serial immediate capture

Status: **complete; reliable functional renewal qualified. Independent audit
and closeout passed.** All 32 fresh blocks (18000–18031), 128 founders, 512
lineages and 193536 individual scores were retained. No job remains running.

This tests E019's unchanged immediate writer through three successive record
replacements on 32 fresh blocks (18000–18031), with four founders and four
lineages per founder. Protected-copy, read-blocked and write-blocked chains
are retained. Only each predecessor's outgoing packet reaches the next body.

After three replacements, **512/512 intact lineages** succeeded under both
opposing cues. The primary whole-block bootstrap interval was [100%, 100%],
passing its lower-bound >75% criterion. This degenerate interval describes
the observed cohort; it does not establish population certainty.

Both-cue success, % [95% whole-block bootstrap]:

| Replacements | Record | Intact | Scattered cell loss | Square lesion |
| --- | --- | --- | --- | --- |
| 0 | Original | 99.8 [99.4, 100] | 82.8 [78.3, 87.1] | 99.6 [99.0, 100] |
| 1 | Immediate capture | 100 [100, 100] | 87.9 [84.0, 91.6] | 100 [100, 100] |
| 1 | Protected copy | 100 [100, 100] | 82.2 [77.1, 86.9] | 99.8 [99.4, 100] |
| 3 | Immediate capture | 100 [100, 100] | 85.9 [82.2, 89.5] | 100 [100, 100] |
| 3 | Protected copy | 100 [100, 100] | 80.1 [75.0, 85.2] | 99.8 [99.4, 100] |

Reading-blocked and writing-blocked chains had **zero** both-cue successes
under every damage condition at both assayed renewal horizons. Full
qualification passed: the primary, intact both-cue reliability after one
replacement, all **24 original gates at each horizon**, and all **12**
reading/writing-dependence gates. Original gates concern individual-cue
rule-specific reliability and own-minus-control advantages. Renewed
individual-cue success after three replacements was 100% intact, 92.97%
under scattered loss and 100% under square lesions.

Under scattered loss, immediate capture exceeded protected copying after
three replacements by **5.86 percentage points [2.15, 9.96]**. The change in
renewed both-cue success from replacement one to three was **-1.95 points
[-7.03, 3.12]**, with no resolved decline. These are secondary pointwise
comparisons; neither equivalence to copying nor zero population decay was a
prespecified claim. All results and controls remain in the report.

The existing staged reader and 128-update holding window remain fixed. No
outcomes are pooled with E019. The result establishes body-derived functional
transmission through three intact renewal boundaries with no output reteaching.
Damage was applied only to independent terminal assays. Autonomous timing,
indefinite renewal, damaged renewal and active repair remain untested here.
The subsequent [E021](../E021_damaged_renewal/README.md) test is now complete:
with 24 scattered non-port cells absent in each renewal generation,
intact-assay both-cue success fell to 1.6% after three replacements, while
the same-cohort intact-renewal reference retained 100% observed success.
E021's independent audit passed, but reliable damaged renewal failed.

The workflow finished **19 September 2026 at 18:09:27 UTC**. Simulation and
reporting took 2959.25 seconds; independent replay took 3783.83 seconds; total
runtime was **112.42 minutes**. This exceeded the retained 103.88-minute forecast
by **8.54 minutes (8.2%)**. All eight workers used one numerical thread each.
No retuning, exclusions, restarts or cohort extension occurred.

Independent replay reproduced every teaching, renewal and assay update,
every packet boundary, every score, interval and gate, with exact isolation
checks. Closeout verified all original outputs and frozen inputs for fixtures,
benchmark and cohort, workflow/figure references, and unchanged E014–E019
inputs. The scientific figure was visually inspected.

[Scientific report](runs/renewal_v1/REPORT.md),
[results](runs/renewal_v1/summary.json),
[figure](figures/renewal_v1/serial_capture.png),
[independent audit](runs/renewal_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json), [frozen protocol](PROTOCOL.md).

Technical evidence: [fixture receipt](analysis/fixtures_v1.json),
[fixture log](analysis/fixtures_v1.log),
[fixture independent audit](analysis/fixture_attempt1/INDEPENDENT_AUDIT.json),
[prebenchmark verification](analysis/prebenchmark_verification_v1.json),
[benchmark status](jobs/benchmark_v1/status.json),
[benchmark independent audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json),
[prelaunch verification](analysis/prelaunch_verification_v1.json),
[runtime/storage forecast](analysis/forecast_v1.json),
[startup verification](analysis/launch_verification_v1.json),
[final status](jobs/renewal_v1/status.json),
[workflow log](jobs/renewal_v1/workflow.log).

All three fixtures passed on the first attempt in 8.70 seconds (8.93 seconds
including launcher overhead). The full-duration excluded benchmark used
94.57 seconds for its worker, 95.25 seconds for simulation/reporting,
97.39 seconds for independent replay, and 194.10 seconds overall. All 1512
benchmark scores and all three record boundaries replayed exactly. The
benchmark figure was inspected and all original hashes verified.

The original forecast used eight available CPUs. Forecast storage including
the 1 GiB reserve was 2.97 GiB; 26.30 GiB was available. The original estimate
and startup evidence remain unchanged.
