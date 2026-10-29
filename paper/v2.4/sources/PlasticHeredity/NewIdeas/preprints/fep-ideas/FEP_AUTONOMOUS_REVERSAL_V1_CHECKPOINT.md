# Autonomous reversal v1 — execution checkpoint

**Completed 16 October; report and interval correction verified 17 October.**
See the [final report](FEP_AUTONOMOUS_REVERSAL_V1_REPORT.md) and
[pooled-interval correction](FEP_AUTONOMOUS_REVERSAL_V1_CORRECTION.md).
This historical checkpoint records the launch and reviewer guidance.

**Launch record, 16 October 2026:** main run launched detached at 15:41:45 UTC;
launch verified at 15:42:58 UTC. No main outcomes had been inspected at launch.

The [frozen specification](FEP_AUTONOMOUS_REVERSAL_V1.md) tests whether the
structured reversal model can recover economically when it must choose and
pay for its own evidence. The earlier 25.03% gain used supplied answers and
does not answer this question.

Both model implementations are unchanged. Compare CT4-anytime with CT4-structured
on 27 physical base laws, 32 fresh blocks per base, stable conditions and six
change families at four onsets. This gives 864 independent paired blocks,
21,600 paired episodes and 4,320,000 policy decisions, in 216 fixed chunks.
No prior, horizon, exploration bonus or sample-size search is permitted.

The primary contrast is realized post-change reversal cost, including purchased
answers. Equal weights apply to bases and change times; uncertainty clusters
all conditions sharing a block. The two-part criterion requires both a paired
improvement over the old model and cost below always purchasing (.1), using
the upper endpoints of the predeclared Monte Carlo intervals. Stable and
non-reversal harms remain visible; this criterion is scoped to reversal.

## Verification before launch

The design, population, fresh seeds and source identities were frozen at
**15:35:20 UTC**. There are 70 input identities and three new source/specification
snapshots. Main seeds do not overlap the ten earlier seed manifests or this
study's synthetic qualification and benchmark streams.

Qualification passed in **46.53 seconds**: 8,509 runner assertions and 38,501
assertions in the separate reconstruction/report checker. Checks cover full
support batch/scalar agreement, rational planning on short support, terminal
truncation, paid-label masks, the previous baseline evaluator, serial/four-worker
fingerprints, regret accounting, and the complete aggregation path. A repeated
synthetic fixture exercised reporting only; it is not scientific evidence.
The prior model's exact qualification is preserved and reused.

FREEZE SHA-256:
`baf6df858bb4688c04b86285a79de8238901a91100099fe50c0f4551c96aa216`.
QUALIFICATION SHA-256:
`86f4978be6a6e57d5bdc451a7906fdcff7f411d1d884434cb3646da2a9e78cbc`.

## Execution and storage

The benchmark used four workers and four synthetic blocks per worker, taking
**291.19 seconds**. Linear scaling suggests about **4 hours 22 minutes**; the
fixed conservative forecast, `120 + 3 * benchmark_seconds * 864 / 16`, is
**47,292.54 seconds (13 hours 8 minutes)**. This passes the seven-day feasibility
ceiling. These are forecasts, not an observed completion time or a promise;
physical laws and exact decision fallbacks can change throughput.

The detached coordinator PID/session/process group is **3644584**, with workers
**3644586–3644589**. Launch verification confirmed CPUs 0–3, nice priority 10,
and one thread in each numerical worker. The coordinator has three expected
process-pool management threads. An initial launch-helper assertion wrongly
required the coordinator to have only one thread; that check was corrected and
preserved in `LAUNCH_VERIFICATION_ATTEMPT01.json`. It did not stop or restart
the scientific run, alter frozen source, or inspect outcomes. The final check
is `LAUNCH_VERIFIED.json`, and all 70 frozen input identities still match.

The durable stdout/stderr log is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/attempt-01-detached.log`.
It is outside the attempt directory so ongoing logging cannot alter a sealed
artifact hash. The attempt also has `RUN_LOG.txt`, `LAUNCH.json` and `STARTED.json`.

BENCHMARK SHA-256:
`743b478580ad1bb4d782222a4fc861d0204dc7506cfbe74128553b8ac02f20a0`.
Runner SHA-256:
`ca265d3d3392656165eedd410599d167ace16b588a52d5d3a2bc31f779be10e2`.

All generated records are under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/attempt-01/`.
The external ext4 mount was verified with about 66 GiB available. New local
specification/runner/readback source totals 54,002 bytes. No datasets are
written into the workspace. Earlier frozen models and evidence remain intact.

Use CPUs 0–3, one numerical-library thread per worker, no Python bytecode, and
nice priority 10. On completion the runner automatically aggregates and invokes
the separate [readback](readback_fep_autonomous_reversal.py), which reconstructs
saved costs and intervals without rerunning scientific policies. No automatic
progress polling or successor experiment is scheduled.

The FEP question is whether richer structured uncertainty helps evidence
acquisition and useful action. This study does not introduce a new canonical
EFE, claim uniquely FEP behavior, or learn the reversal structure autonomously.

## Reviewer guidance — 16 October 2026

Received through the user after launch, before inspection of main scientific
outcomes. The completion manifest and saved-data readback were not yet present
at 18:29 UTC. This is a reporting clarification, not a replacement for the
frozen specification or a claim of completed autonomous recovery.

> Complete autonomous reversal with purchased feedback included in total cost.
> Compare against both the previous controller and always purchasing. If it
> fails, distinguish failure to acquire evidence, interpret evidence or act
> economically. Keep the supplied-feedback improvement separate from autonomous
> recovery.

The existing runner implements both comparisons and charges every purchased
deployment answer. Report total cost as `wrong answers + .1 * purchases`, with
the two components shown separately, for the complete 100-task episode and
the post-change window. The primary reversal endpoint remains the frozen
post-change cost per task. Always purchasing costs 10 per complete episode,
or .1 per task; its post-change total is `.1 * (101 - onset)`. The shared
64-sample calibration is a supplied starting condition, so this is deployment
cost, not an estimate of end-to-end calibration/data-collection cost.

The final report must organize the saved diagnostics around these questions:

| Possible limit | Evidence already recorded | Interpretation limit |
|---|---|---|
| Acquiring evidence | First post-change purchase, delay, fraction never buying, purchases during confident agreement, and cost before the first purchase. | Late or absent feedback can explain continued ignorance. Free warnings cannot identify a pure global reversal; this does not establish a broken Bayesian update. |
| Interpreting evidence | Purchased-label history, subsequent predictive orientation probabilities, posterior change/reversal mass, and wrong-direction regret after feedback. | Check beliefs against the evaluator's conditional law. An error after one purchased answer does not prove misinterpretation; evidence can remain sparse or ambiguous. Posterior R mass alone does not establish useful prediction. |
| Acting economically | Realized errors plus all purchase costs, both comparator differences, subjective versus conditional action risk, and insufficient-checking/wrong-direction/excess-checking regret. | Future information can justify a purchase that exceeds the immediate known-law floor. High checking cost alone is not proof of waste; assess the full paid outcome. |

The saved `subjective_u` is the prediction **before the current purchase**;
saved change/reversal masses are after that task's retained label. A purchased
answer can affect later predictions, not retrospectively justify its own
selection. Align interpretation analysis with that ordering.

Show the three before/at/after-first-feedback phases, but do not relabel them
as three mutually exclusive causal failures. Acquisition, model adequacy and
the action objective can interact. Different controllers choose different
histories; these diagnostics do not constitute a matched causal intervention.
Any additional descriptive breakdown derived from the existing traces belongs
under this dated reviewer clarification, not the original preregistration.
Do not add outcome-selected thresholds or change the primary success gates.

Keep the earlier **25.03% supplied-feedback diagnostic gain** in a separate
result category. It remains evidence for using supplied information better,
not an autonomous cost reduction. A failure of either autonomous success gate
must be reported; an interval crossing the threshold is inconclusive rather
than proof that the model is worse. Stable and non-reversal harms also remain
part of the report. A functional failure of this specified model/planner is
not a general refutation of FEP.

Complete the existing detached run and automatic saved-data verification.
All numerical source, seeds, costs, sample size and frozen criteria remain
unchanged. This guidance requests no restart, extension or successor study.
