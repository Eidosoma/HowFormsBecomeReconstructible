# D099 — L15 target-role reversal and symmetric defense

Prospective specification, 2026-09-12. User accepted the single reversal /
symmetric-defense recommendation in [D098](../reviews/L15_EXPOSURE_DEFENSE_2026-09-12.md).
Freeze both qualification and main before either cohort; no nearby rate,
amplitude, horizon or target tuning and no automatic retry or further cohort.

## Question and scope

Does the brief/long reference-writing effect survive reversing which pattern
is old/new, and do both resulting patterns recover from an opposing pulse?
D098's final pulse opposed the new pattern but favored the old. Here every
record receives both pulse directions plus sham, under both target orderings.
This is a paired extension, not a clean-room, biological, autonomous learning
or hereditary-renewal experiment. The 64-byte germ is untouched.

## Frozen identities and construction

- Main `l15_reversal_defense_v1_attempt1`, tissues **45000–45007**;
  qualification `l15_reversal_defense_v1_qualification_attempt1`, tissues
  **45080–45087**. Two lives per tissue, both directions within every life.
  Disposable **514199** is engineering-only and never enters cohort estimates.
- Direction 0: native launch recipe 0 (left/right) old, recipe 1 (top/bottom)
  new. Direction 1 reverses these roles. Native settling must actually use
  **seed_index=direction**, not rotate an already settled state or just change
  labels. Both directions have the same native unprojected theta and paired
  phase-wise noise, not rotated theta/noise. Old formation is 120 T updates
  from the source's +/-1 recipe plus native jitter.
- Reuse D098's exact native settings: 16x16 sheet, coupling 1, sigma .3,
  dt .2, rho .002, active comparator gain .2, imposed templates +/-1.2;
  target disagreement mask 128/256 cells. No theta writing or evolution.
- Every main direction/life has six equally aged histories: old-only (`none`),
  old 980/new final 20 (`brief`), new 1000 (`sustained`), each crossed with
  exposure R writing native or held at rho=0. V is overwritten before each
  native step; R reads post-sheet/post-comparator V, never an assigned target.
  Exposure snapshots 0/1/20/500/980/981/1000.
- Carry **only the terminal R**, a 2048-byte float64 packet, into readout.
  Discard exposure V/EMA; recreate public theta; all records in one direction
  start with identical new-template V and EMA=V. The public direction sets
  this shared assay background; history/record identities cannot enter the
  reader. This remains a matched-state within-life diagnostic, not a boundary.
- Add constructed known-new, known-old and erased R controls. Nine main
  records; qualification uses only these three, without exposure histories.
  Constructed R amplitude is not matched to learned R; retain RMS/errors.
- Every record crosses reader on/off (.2/0). All readouts update R at .002,
  even if held during exposure. Release unforced 200 updates, saving
  0/1/20/80/200; then split three branches in fixed order:
  **toward_old, toward_new, sham**. On disagreement cells, pulses add .8 times
  the respective target sign, exact opposites. No initial clipping or R/theta
  change. Every branch resets EMA=V and runs 80 unforced updates, saved
  0/1/20/80. Identical future random draws across branches/records/directions.
- Explicit PCG64/SHA-256 seed tag `l15-reversal-defense-v1`, addressed by
  tissue/life/phase only. No condition or direction in random addresses.
  D098 streams and cohorts are not reused for fresh inference.
- Main: **1728 readout futures**, 192 exposure histories; qualification:
  **576 readout futures**. Each phase has 16 paired lives, or 32 direction-
  specific life replays, within eight independent tissue blocks. Duplicate /
  reversed-call-order checks add **288 technical alias futures per phase**,
  never scientific samples. Native theta must be exact across directions;
  all readout-off V/EMA must be exact record aliases within each direction;
  held-writing histories must be exact readout aliases.

## Qualification gate, both patterns in both orderings

Freeze the main design before qualification. On each direction and each
known target (known-new or known-old), test distinguishing-cell own-target
V sign fidelity. New-target opposition is toward_old; old-target opposition
is toward_new. Compare known content under the **same pulse**, not different
challenges between the correct and opposite-content controls.

For each of these four direction/target combinations, require all ten gates:

1. Mean own fidelity >=.8 before and 80 updates after opposing pulse.
2. Every tissue mean >=.75 at both endpoints.
3. Correct minus opposite-content R >.2 in every tissue at both endpoints.
4. Immediate opposing-pulse loss >=.10 on average, >=.05 in every tissue.
5. Subsequent rebound >=.10 on average, >=.05 in every tissue.

All **40 gates**, full independent dynamics/metrics/summary checks and exact
aliases must pass to permit main reservation. These extend D098's unchanged
margins symmetrically; no criterion is fitted to fresh outcomes. If any fail,
retain every result, mark qualification technically complete but unqualified,
do not launch main, weaken a gate, substitute a target or automatically retry.
This would be an apparatus limitation, not a negative learning conclusion.

## Primary, uncertainty and bounded claim

For each direction/life, at response80 with the reader on, compute the new-
pattern sign fidelity contrast separately under each opposing pulse:

`C = (sustained_live - brief_live) - (sustained_held - brief_held)`.

Average C equally over toward_old and toward_new (not sham), then over the
two lives within each tissue, then equally over eight tissues. The **single
primary estimand is the smaller of the two direction means**, so a strong
original ordering cannot hide a failed reversal. This is not the average of
per-life minima. Retain both directional estimates and all life/block values.

Use 10,000 whole-tissue PCG64 bootstrap draws; keep both directions, lives and
all conditions paired within each resampled tissue. For each draw take the
minimum of its two direction means, then the 2.5/97.5 percentiles. All other
intervals are pointwise, not multiplicity-adjusted. No equivalence claim from
an uncertain direction interaction, no cell/future pseudoreplication or drops.

Bounded direction-robust brief-repair/long-adoption-and-defense requires:

- Qualified controls, primary interval lower bound >0, at least six positive
  tissue contrasts **in each direction** (direction estimates average pulses).
- In **each direction**, brief-live old and sustained-live new fidelity
  >=.8 on the mean before and after their respective **opposing** pulse.
- Incoming brief R old fidelity and sustained R new fidelity >=.8 on means;
  each of those four direction/target groups loses >=.10 fidelity immediately
  and rebounds >=.10 by response80, on means.

Report every criterion, absolute-endpoint intervals and counts of tissue
means/lives >=.8, not just primary positivity. A failure of the .8 mean rule
does not erase a positive continuous effect; neither implies universal success.
Held writing and reader-off duration effects must be exactly zero by design.

Secondaries, by direction: pulse-specific and sham duration interactions;
release200 interaction; pulse-averaged sustained writing and reading effects,
brief-minus-none, sustained-minus-erased, known-new-minus-erased and known-new
minus-known-old. Report opposing-pulse-minus-sham fidelity costs and rebound
for **both** brief-old and sustained-new states. Report paired reversal-minus-
original interaction and the equal-direction mean, without treating uncertain
differences as equivalence. Save all 12 D098 metrics for V/R vs both templates,
V-R mismatch, R RMS, V mean and clipping fraction in conflict/whole regions,
at all registered stages and exposures. Mismatch is never an identity score.

## Provenance, checks and execution

Reuse D097 native physics/I/O and D098 immutable config/packet/measurement
helpers read-only. New independent checker restates reversed initialization,
exposure/readout/pulse schedule, gates and summary, using the already separately
restated D097 physical step and D098 independent metric routine. No new
production simulator or summary is used by the checker. Exact signs; float64
state tolerance 1e-10, metric/summary tolerance 1e-12. No E6/E7 promotion.

Pin D098's completed main/qualification artifacts, its 286 main inputs,
review, new scientific code/protocol/tests/launcher and external passing test
proof. Check a known saved D098 block with full independent replay before
freeze. Short disposable/synthetic tests must reject a label-only reversal,
wrong pulse, corrupted inputs/results/summary, and failed qualification's
attempt to reserve main. Preserve every prior frozen file and failed attempt.

Then freeze -> full checked disposable qualification/main benchmarks ->
qualification -> only if qualified, unchanged main -> saved-output audit.
Each benchmark includes dynamics, independent replay, exact aliases, save /
reload and summary. Forecast phase runtime as 8*checked-block seconds plus
2*input-hash seconds plus 180 seconds. Budget 8*(both uncompressed blocks)
+ benchmark files + 32 MiB metadata margin <=512 MiB; keep external 4 GiB
reserve plus 512 MiB launch allowance. No automatic resizing or cleanup.

All data/outputs/logs/fixtures/tmp/cache under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation`; only new code/docs here.
CPUs 0-3, at most four workers, numerical threads one, bytecode disabled.
Any forecast **>600 seconds must run detached**, fresh session, stdin
/dev/null, external stdout/stderr; record launch, stop and leave polling to
the user. No automatic detached polling, failed-attempt retry or next study.
