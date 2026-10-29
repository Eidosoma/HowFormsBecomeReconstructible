# E083 — repeatability under fresh matched readers

18 October 2026. Authorized follow-up to E082. All original E077–E082 outcomes
are known. Reuse every saved E080/E081 source record; no source generation,
writer trajectories, weight edits, case selection or horizon extension. Freeze
two new reader draws per record before observing either draw. This tests transfer
of an observed effect to new reader conditions on known records, not generality
to untouched source records or a revision of E081's original verdict.

## Records and two fresh draws

Use E080 blocks 41000–41031 and E081 blocks 42000–42031, four founders, four
recipients, native/mixture and sham/pulse. For E080, I0/P0/erased-h0/I1/P1/
erased-h1 come from the original audited E077 packets; OF/FF come from E080.
E081 supplies all 26 packets directly. Source bytes and original outcomes must
match their frozen archives. Original E080 endpoints remain labeled E077 context.

Each of two independent fresh draws reads all 26 conditions under matched
injury, birth and noise. Stream tag E083, source block, phase terminal_E080 or
terminal_E081, and generation/draw 0 or 1 determine the new streams. Injury uses
the corresponding phase_injury. The same nuisance draw is shared across all
conditions and endpoints, and opposite-rule founder partners retain their
original pairing. Between draws, injury, birth and noise all change together;
this does not separate their individual contributions.

Unchanged reader: float64, dt .2, noise .02, birth SD .05, 24 scattered nonport
injuries, protected ports, 2,048 steps with first 1,024 unamplified, final 32
observations, both cue margins strictly >.25. Natural absolute-strength
normalization with no positive denominator floor; zero denominator gives zero
drive. Paired cue birth/noise remains part of the apparatus. OF/FF retain ordinary
signs and support, matched selected absolute total before injury and P1 outside
bytes. No clipping or new allocation is performed.

There are 4,096 original source cases across both cohorts (1,024 per cohort/kind),
8,192 case/draw pairs and **106,496 new terminal cue observations**. Draws,
histories, founders and recipients are nested within source blocks, not additional
independent replication units. Retain all fresh cases, including unchanged ones,
both pruning endpoints and individual harms.

## Primary: does the old label carry information within a block and history?

Let d_old = old FF success − old OF success, in {−1,0,+1}. For E080 this label
comes from its own matched-total assay, not E077 or E079. Let d_new be the mean
FF−OF success difference over exactly two E083 draws. For each source block b
and history h, center both differences across its 16 mixture founder/recipient
cases, and compute

`A_bh = mean_i[(d_old_i − mean(d_old)) * (d_new_i − mean(d_new))]`.

The block score A_b is the equal mean of sham/pulse scores. This removes a
block/history-wide shift in average treatment benefit. Constant-label strata
contribute zero; no block is omitted. A positive alignment score means the old
effect labels distinguish relatively larger from smaller new effects within
these strata. It does **not** require every old gain or harm to recur, nor prove
that new effects in the old-harm group remain negative.

Two primary contrasts: mean A_b separately in E080 and E081 mixture records.
Use 10,000 paired whole-block bootstrap draws per cohort, semantic stream
E083/reader_repeatability/bootstrap/cohort, two-sided **97.5% intervals** for
an approximate nominal 95% two-test family. Lower >0: POSITIVE_ALIGNMENT;
upper <0: NEGATIVE_ALIGNMENT; crossing/touching zero: UNRESOLVED. Claim alignment
in both cohorts only when both are positive. No claim of a statistical cohort
difference follows from different labels. Technical/failed controls have null
scientific flags. No pooling cohorts to rescue an unresolved result.

## Required secondary descriptions

Report full-cohort OF/FF success, minimum margin, signed/aligned transfer and
their differences, separately by cohort/kind/history and fresh draw as well as
averaged over the fixed two draws. Retain I0/P0 and I1/P1 fresh-read contrasts,
their change across the saved rewrite, and the full individual pruning table.
These are fresh reads of the existing endpoint records, not new writer events.

Keep four original OF→FF groups: fail/fail, gain, harm, success/success. Report
their exact source-case counts, new signed mean effects, all old-label/new-effect
transition counts, and the number of old gains/harms repeating on zero, one or
both fresh draws. Report new gains and harms among previously unchanged records.
Group-conditional summaries use all original cases and expose empty groups.

Secondary intervals are pointwise 95% whole-block intervals. For conditional
group means, resample block numerators and denominators together. If any bootstrap
draw has zero group denominator, leave that interval null and report the number
of undefined draws; never discard or zero-fill them. A missing group has a null
point estimate. Original outcomes are context/labels, never pooled as a third
fresh draw. No thresholds, groups, draws or analysis settings are selected from
new results; no added streams until a favorable result appears.

## Qualification, evidence and runtime

Pin predecessor complete/audit/closeout receipts, E082 diagnostic provenance and
every source file read. Independently assemble the 26 slots and recount labels;
replay every new reader state with separately implemented equations. Check score
boundaries, nuisance pairing and draw separation, original source bytes, support,
matched mass/outside bytes, unit normalized gain, erased aliases, empty selection,
and all individual tables. Verify alignment by an independently evaluated formula,
including synthetic constant strata, negative/zero effects and positive alignment
without universal sign recurrence. Preserve numerical failures without case removal.

Use excluded source block 900041 from each predecessor for fixture and timing;
the scheduler identifies these tasks as 900080/900081, separate from scientific
source IDs. Fixture uses original small settings; benchmark uses one recipient,
512 steps, both draws and both cohorts. Freeze inputs before these retained runs.
Forecast reader work by steps and recipients, keep static overhead separate,
allow a factor of three and reserve storage. Select workers within the shared
12-CPU ceiling, one numerical thread per worker. Forecasts >600 seconds run
detached, stdin /dev/null, with unique logs/PID/status and bounded startup only.
No automatic polling, restart, extension or successor. Stop at the fixed workload
and closeout. Manuscript integration remains with the other agent.
