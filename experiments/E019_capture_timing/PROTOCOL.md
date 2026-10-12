# E019 — functional record capture before and after body drift

Frozen before new simulation, 19 September 2026. The user authorized the
capture-timing proposal following E018's saved-data review. That review exposed
E018 outcomes; the present candidates are outcome-informed hypotheses tested
prospectively on new blocks, not a rediscovery or regrading of E018.

## Apparatus, cohort and single replacement

Keep E016 consistent acquisition and E017 staged reading unchanged: 16×16
reciprocal local sheet, 512 float64 edge weights (4096 bytes), gain 2, 2048
reading updates with positive linear amplification absent for the first 256.
Retain the E015 defaults, two rules, opposing cues, ports, ±0.25 strict margins
and final-32-step assay average. Teaching runs 512 updates per cue and captures
the final 128; only the consistent record enters the experiment.

Use 32 fresh blocks **17000–17031**, four founders per block, four recipient
lineages per founder: 128 founders and 512 lineages. All cases count; no founder
qualification, success selection, tuning or cohort extension. Source streams
retain the E016 teaching tag but these block IDs have not been used there.

Each intact renewal body reads the source record in two cue episodes, with
outputs free. Cue episodes and opposite-rule founders share birth/noise as in
E018. After reading, erase incoming weights; only current body activity enters
the writer API. Inputs stay clamped. The three candidate records are:

1. **immediate:** local `tanh(3*v_i)*tanh(3*v_j)` correlations at read-end,
   calculated after erasure and before any scaffold update, equally averaged
   over the two cues.
2. **delayed:** the identical snapshot estimator after 128 unit-positive-
   scaffold updates with gain 2 and amplification on.
3. **averaged:** the E018 estimator, equally averaging correlations over those
   same 128 post-update states and both cues.

All candidates share the exact reading and writing body trajectories; none
affects the others or feeds back while writing. Hold the newly computed
immediate packet without feedback until the common end of the 128-update
window. Its extra storage is the outgoing record, not preserved incoming
weights. The snapshot comparison has identical estimators and packet sizes;
averaging versus a snapshot additionally changes the estimator. This supplied
clock and early record protection are explicit interventions, not autonomous
timing or a claim of matched computational cost.

## Controls and retained evidence

There are eight terminal packet conditions, in fixed order:
`immediate`, `delayed`, `averaged`, `protected_copy`,
`immediate_read_blocked`, `delayed_read_blocked`, `averaged_read_blocked`,
`write_blocked`. The three read-blocked writers use a second, shared body
trajectory whose incoming weights are zero before reading. The write-blocked
condition transmits zeros; its normal body/writer calculation is shared with
the enabled conditions and retained. Protected copying preserves original
bytes explicitly. No label, desired output, scorer or source packet is an
argument to the activity writer.

Assay the initial record at horizon 0 and all eight terminal records after
exactly one replacement. Every assay uses fresh bodies and noise; all eight
terminal conditions share those random inputs, masks and shuffled addresses.
Assays do not train the next body or select records. Retain intact, 24 scattered
non-port losses and a 3×3 lesion, with ports protected and no connectivity
rejection. Preserve own, opposite-rule foreign, shuffled, erased, untrained,
communication-off and input-isolated arms. Damage affects final assays only.

There are **193536 individual scores**: 32 blocks × 9 panels × 4 founders ×
4 lineages × 2 cues × 3 damage conditions × 7 arms. Save all teaching evidence,
incoming/read-effective/erased packets, developed endpoints and final reading
port windows, all 128 writing states, all three computed records from both
reading branches, outgoing packets, and assay packets/masks/births/endpoints/
late means/final-32-step port windows. Earlier reading updates replay exactly
from the frozen inputs and named streams.

## Endpoints and fixed decisions

The **single primary endpoint** is the paired immediate-minus-delayed
difference in intact both-cue strict success after one replacement. Its
two-sided 95% whole-block bootstrap lower bound must exceed zero. This is the
timing comparison with identical snapshot estimators; it is not selected among
the three candidates after seeing results.

Full qualification of reliable early capture additionally requires:

- Immediate intact both-cue success lower bound >0.75.
- Immediate-minus-averaged intact both-cue success lower bound >0.
- All original 24 gates for immediate records: six rule×damage individual-
  cue accuracy lower bounds >0.75 and 18 own-minus-assay-control accuracy
  lower bounds >0.10.
- All six immediate-minus-matched-read-blocked and immediate-minus-write-
  blocked individual-cue advantages across damage conditions with lower
  bounds >0.10.

Report the primary timing result, absolute one-boundary reliability and full
conjunction separately. Other estimates, controls, qualification gates and
contrasts are secondary, pointwise 95% intervals. Report all three writers'
matched reading/writing-dependence gates and original gates without using a
secondary writer to rescue the predeclared immediate-capture claim. Report
immediate-minus-copy, delayed-minus-averaged, every arm, rule-specific success,
margins and both-cue success. There is no copying-equivalence claim.

Use 10000 whole-block percentile resamples with seed
`["E019","bootstrap","capture_timing"]`. Founders, cues, lineages and the
damage panels are nested observations, not independent sampling units. A
100% sample and degenerate bootstrap interval do not prove population
certainty. Stop after the fixed cohort regardless of result; three-generation
renewal is a later experiment, not part of this run.

## Streams, checks and execution

Source streams: `["E016",block,"teach",episode_index]`.
Boundary streams: `["E019",block,"develop",1]` and
`["E019",block,"write",1]`. Assays use
`["E019",block,"assay",horizon]`, shuffles
`["E019",block,"shuffle",horizon,founder]`, and masks
`["E015",block,"E019_h{horizon}","damage"]`. No outcome enters a seed.

Three short fixtures check snapshot/average arithmetic, erasure and forbidden
information paths, and independent end-to-end replay. Preserve failed attempts.
Independent audit code imports no production model or runner, checks every
teaching/development/writing/assay update, exactly reproduces all packet bytes,
checks input isolation at every assay update, and recomputes every score,
interval and gate. Retain the 1e-10 teaching sign-symmetry tolerance.

Excluded technical benchmark **900019** uses full durations and all conditions,
with one lineage per founder. Its expected duration is below ten minutes from
the analogous E018 benchmark; it determines timing/storage, not design choices.
Forecast the 32-block, four-lineage cohort conservatively as
`2*(benchmark_worker_seconds+benchmark_audit_seconds)*4*ceil(32/12)+90`.
Storage forecast scales measured benchmark files by 4×32 plus 1 GiB reserve.
At most 12 CPUs and one numerical thread per process; no GPU. Forecasts above
600 seconds require a detached durable workflow and user polling. All writes
stay in this experiment tree. Prior inputs and manuscript/sister sources remain
unchanged. No automatic parameter search or successor follows the outcome.

A positive result establishes an engineered, activity-derived record useful
after one boundary for instructed routing. It does not establish serial
functional renewal, active repair, flexible compensation, autonomous goals,
writer origin or independently active patterns.
