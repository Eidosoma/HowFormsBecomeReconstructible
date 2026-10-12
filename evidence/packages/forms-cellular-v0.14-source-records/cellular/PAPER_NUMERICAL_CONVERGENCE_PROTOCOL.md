# P28: fixed-source numerical convergence after the P27 stop

Registered October 3, 2026 after the user authorized fixing the numerical
disagreement. Registration precedes P28 scientific integration. P27 remains
a stopped experiment with unchanged protocol, code, data and acceptance
criteria. This study diagnoses a numerical issue; it does not retrospectively
qualify P27 or fill its missing transmission assays.

## Question and fixed factors

P27 had four failed coarse/fine pairs: the immediate five-unit pause at time
120 (XEE versus EEE) and the 100-unit pause starting at ten at time 225
(MXE versus XXE), under sequence 17021 and both histories. Its final retention
outcomes agreed. The original coarse/fine comparison changes both archived
starting states and numerical settings. Cross those factors explicitly.

Use the following complete factorial, with no outcome-dependent extensions:

- Four schedules: baseline, pause_0_5, pause_0_25, pause_10_100.
- Both written and ordinary histories.
- Both P27 archived source precisions, coarse and fine.
- Five numerical resolution divisors: 1, 2, 4, 8, 16.
- The same incoming sequence heldout_17021, unchanged eleven-entry draw book;
  use the first five draws.

This gives **80 renewed-parent cases**, each with all 26 P27 phases:
twenty first-challenge segments, four later replacements and two isolated
holds. Total **2,080 integrations**. No onward assays are included. The
affected schedules are deliberately selected from the stopped result;
this is a diagnostic study, not an independent confirmation of their
biological or model effect. Baseline and the immediate 25-unit schedule
provide previously passing negative/positive controls.

Source precision selects the complete archived all-before fork and incoming
stock. Hold those exact arrays fixed across all five numerical settings.
The legacy field named fine denotes source precision only in these new
case records; source_fine and resolution record the separate factors
explicitly. No averaging, polishing or adjustment of starting concentrations.

At divisor q, use native time_step = 0.0001/q, concentration adaptive limit
0.001/q, voltage adaptive limit 0.0001/q and phase step cap
min(100, horizon/100)/q. Preserve native explicit Euler equations, adaptive
proposal, multiplication order and integer tick clipping. Sampling remains
min(100, horizon/20), independent of q. Divisors one and two exactly recover
P27's original numerical settings; the factor crosses both starting states
with all numerical levels. The finest pair is fixed at **8 versus 16**.

## State and schedule preservation

Reuse the P27 all-before assembly, applying its single native noniterative
binding refresh with no primary state edits. Start at logical time 1180300.
Retain the original counterfactual P27 cell identities for each reconstruction;
cases at different numerical settings are comparisons of the same lineage,
not independent cell populations or biological replicates.

Use P27's common first-challenge boundaries:
0,5,10,15,20,25,50,75,100,105,110,115,120,125,150,175,200,225,250,275,300.
Block RNA only during the schedule's registered pause, then restore it.
Carry exact live state and identities between every segment. Preserve all
raw samples and calculate the inherited diagnostic at 0,15,...,300.

Insert the same five incoming cells at positions 1,2,0,1,2, varying only
incoming ZEB protein by the unchanged fixed sequence. Preserve survivors.
Later replacement intervals last 300 and remain continuously open.
Isolate the actual final trio for two 10000-unit holds, ending at 1201800.
Keep the native E/M/X classifier and the inherited final-quarter stability
criterion. Report final retention separately from intermediate stability.

## Fixed stages and validation

1. Replay: the sixteen diagonal cases (coarse source with divisor one,
   fine source with divisor two), across all schedules and histories.
   Require exact agreement with every P27 numerical array and reconstructed
   outcome. The P27 disagreement itself is expected to remain reproducible;
   it is not an error to suppress in this study. Cumulative 16 cases /
   416 integrations.
2. Convergence: the remaining sixty-four factor combinations. Execute every
   case after replay passes. Cumulative 80 cases / 2080 integrations.
   No low-resolution or unfavorable scientific result selects another case.

Independently audit every new schedule, state transfer, incoming draw,
assembly, geometry, transport route, numerical parameter, clock trace,
observation and result. Verify the 40 baseline/25-unit control outcomes
against their matching P27 source precision for retained E, sampled
resistance/recovery, first-cell stability and complete carrier replacement.
Require all 40 pairs of cases sharing an initial communication schedule at
the same source, history and numerical setting to match exactly until their
schedules differ (eight pairs in the replay stage).

A valid diagnostic report and successful numerical convergence are separate
outcomes. A valid nonconvergent result must be saved and reported, without
being relabeled a software failure or prompting an automatic retry.
Technical defects, failed exact replay or changed control outcomes stop
interpretation. A valid negative diagnosis does not resolve P27.

## Predeclared convergence criteria

For all sixteen fixed-source/history/schedule groups, report all four
adjacent comparisons: 1–2, 2–4, 4–8 and 8–16, giving 64 comparisons.

For each adjacent comparison, independently report:

- Exact equality of reconstructed outcomes.
- Agreement of every cell's E/M/X label at every phase endpoint.
- Equality of the complete common-grid first-challenge diagnostic, including
  observed labels and first-loss/first-return brackets.
- Maximum normalized concentration difference over all saved samples in all
  phases, using primary rows 0–7 and 16. At each corresponding value x,y,
  normalize abs(x-y) by max(1,abs(x),abs(y)), then take the maximum.
- Raw maximum phase-end differences and the individual phase comparisons.

A fixed-source group is converged on this tested ladder only if the 8–16
comparison has the same phase inventory, exactly matching outcomes, all
phase-end labels and the common-grid diagnostic; its maximum normalized
primary-state difference must be at most 0.01 and no larger than the 4–8
difference plus 1e-12. These finite-ladder criteria are diagnostic tolerances,
not a proof of exact-solution convergence. Do not choose an earlier passing
pair if 8–16 fails, change tolerances, alter sampling, or extend the ladder
after seeing results.

Also compare coarse-source versus fine-source trajectories at divisor 16,
separately for each history/schedule (eight comparisons). Source robustness
requires matching outcomes, phase-end labels and complete common-grid
diagnostics, plus normalized error at most 0.01. Report this independently
from solver convergence. A source-sensitive result identifies unresolved
upstream checkpoint uncertainty even if each fixed-source ladder converges.

Support for a refined full-panel run requires valid technical audits, all
sixteen finest-resolution groups converged and all eight source comparisons
robust. It does not establish onward transmission or generalize to P27's
other schedules, sequence legacy, or biological systems. No full-panel or
onward run is launched automatically by this protocol.

## Preservation, software and resources

Pin P27's terminal failed status, summary, both stage audits, historical
preflight, software log and input manifest, plus the stopped-run review.
Verify its known four failures and distinguish a valid diagnostic archive
from a passed predecessor experiment. Verify every inherited source/input
hash without rerunning old mathematical audits.

New execution source is in p28_numerical_convergence/ plus this protocol.
The manifest has **265 execution sources** and **31,265 input paths**.
The legacy scripts/configs inventory and all prior executed artifacts stay
unchanged. Directory references are references, not independent backups.
All large files, test fixtures, logs, caches and temporary files stay under
/mnt/workspaces/levin-cancer-gj-exploration/p28-numerical-convergence.

Require all **36 synthetic-panel, exact-diagonal-replay and fault tests**
before scientific execution. Freeze the complete source manifest before
the detached supervisor repeats verification. A partial successful test log
cannot satisfy the gate. Synthetic trajectories test software and are not
scientific predictions. Tests explicitly reject transient-only label
disagreement, recovery-timing disagreement, large same-label errors,
noncontracting errors, hidden source sensitivity, state/clock corruption
and changed history, while retaining valid negative diagnostic outcomes.

Two workers, one numerical-library thread each, an exclusive P28 lock and
five GiB free on the actual output filesystem at launch, case and phase
boundaries. Watchdogs: verification two hours, individual case six hours,
runner including preflight forty hours, final audit six hours, overall
forty-eight hours. Long runs are detached with durable logs, heartbeat and
completion status, as requested. No automatic retry or downstream run.
