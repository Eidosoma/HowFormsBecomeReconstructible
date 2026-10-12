# E022 — local reader compensation through one damaged renewal

Fixed before new simulation, 20 September 2026. The user authorized this
test after E021's saved-boundary diagnosis. E021's prospective failure and
post-hoc diagnostic remain unchanged; no observations are pooled here.

## Fixed apparatus and intervention

Use **32 fresh blocks 20000–20031**, four founders and four lineages per
founder: 128 founders, 512 lineages. The excluded benchmark is **900022**.
These IDs were checked unused before implementation. Retain every case.

Keep E016 consistent acquisition, E017 staged reading and the E019–E021
immediate activity writer. Use the existing 16×16 reciprocal torus, 512
float64 edges / 4096 bytes, two opposing rules and cues, gain 2, 2048 reading
updates, amplification off for the first 256, strict ±0.25 output margins
on the final 32 updates, 512 teaching updates per cue and final-128 teaching
capture. Other E015 parameters remain fixed.

Perform **one** renewal replacement. Remove 24 scattered non-port cells at
birth, keeping their activity and incident communication edges zero through
reading, capture and the 128-update holding window. Masks are paired across
opposite founders, cues and all damaged conditions. Accept every mask without
connectivity rejection. The intact reference has no renewal injury. This
tests damaged development, not acute repair or regrowth.

For effective incoming weights w and body activity v, let
`S_i = sum_j(w_ij * v_j)` over the four physical neighbor positions. The local
reading term is `2*(S_i/d_i - v_i)`. Compare three fixed denominators:

1. **baseline:** d_i = 4, reproducing the unchanged reader.
2. **degree_compensated:** d_i is the number of physically present incident
   neighbors, independent of the magnitudes or zeros in the record.
3. **strength_compensated:** d_i = sum_j(abs(w_ij)), the total effective
   absolute incident weight after physical injury and boundary controls.

If d_i is zero, define the incoming contribution as zero. There is no floor,
pseudocount, tuned gain or weight threshold. Denominators are fixed during
the reading episode and used in both stages. Off-stage drift is
`-v_i**3 + 2*(S_i/d_i-v_i)`; amplified drift adds `v_i`. Keep the original
time step, additive noise, clipping, input clamp and absent-cell constraints.
Only input is clamped during reading. Denominators use current local edges,
never rule labels, target outputs, future assays or selected successful cases.

At read end erase effective incoming packet bytes before calling the writer.
Capture uses exactly `encode(mean_cues(correlations(body, beta=3)))`, with
the same operation order as E021. Its API receives only activity and fixed
parameters. No denominator, injury mask, old record, target, score or label
enters capture. Retain the new packet unchanged through the original
unit-positive-scaffold holding window on surviving edges, without feedback.
Only the outgoing 4096-byte packet enters independent terminal bodies.

## Eight paired conditions and unchanged terminal assays

Condition order is baseline, degree_compensated, strength_compensated,
intact_renewed, protected_copy, masked_copy, read_blocked, write_blocked.
The six body branches are indices 0, 1, 2, 3, 6, 7. Intact renewal uses
denominator four; blocked branches use the strength-compensated reader.

- Protected copying preserves the original packet exactly and bypasses bodies.
- Masked copying erases the same incident edges from the original packet,
  keeping surviving values unchanged; it does not develop or learn.
- Reading blocked sets effective incoming weights and strength denominators
  to zero but retains physical injury and the normal activity writer.
- Writing blocked develops with the candidate reader, retains computed
  capture for audit, but transmits an all-zero packet.

All branches share renewal birth/noise realizations. Assay the original
packet at horizon 0 and every outgoing condition at horizon 1 in fresh bodies.
Every terminal assay uses the **unchanged denominator-four E017 reader**,
with intact, 24 scattered-loss and non-port 3×3 lesion panels. Keep own,
opposite-rule foreign, shuffled, erased, untrained, communication-off and
input-isolated arms. Terminal masks are independent of renewal injury;
births/noise/shuffles/masks are shared between compared conditions.

There are **193536 terminal individual scores** across nine panels, plus
**6144 renewal-body individual scores** from the six body branches. Body
scores describe pre-capture responses and cannot substitute for a functional
terminal endpoint. They do not form additional independent experimental units.

## Primary, qualification and reporting

The **single primary** is strength_compensated minus baseline in intact-
terminal-assay **both-cue success after one replacement**, using the paired
whole-block difference. Require the two-sided 95% bootstrap lower bound
**>0.10**, i.e. more than 10 percentage points.

Full qualification additionally requires:

- Candidate absolute intact-terminal both-cue lower bound >0.75.
- All 24 original candidate gates: six rule×terminal-injury individual-cue
  accuracy lower bounds >0.75 and 18 own-minus-control lower bounds >0.10.
- All 24 original gates for the paired intact-renewal reference.
- Six candidate-minus-read/write-blocked individual-cue lower bounds >0.10,
  across the three terminal injury panels.

Report primary and full conjunction separately, every failed gate, all arms,
rule-specific accuracy and margins, body accuracy/both-cue success/margins,
candidate-minus-each-other-condition contrasts, and degree-minus-baseline.
The strength candidate is fixed; the degree condition is a mechanism control,
not an alternative selected after seeing outcomes. No superiority over
copying, equivalence, noninferiority or unique mechanistic explanation is
prespecified. Stop after this cohort regardless of outcome.

Use 10000 percentile resamples of independent whole blocks with stream
`["E022","bootstrap","compensation"]`. All secondary intervals and gates
are pointwise; descendants, opposite founders, cues and injury panels are
nested. Observed 100% does not establish population certainty. No retuning,
exclusions, cohort extension, severity reduction, terminal-reader change or
automatic follow-up. Three-boundary qualification would require another test.

## Evidence and execution

Acquisition retains `["E016",block,"teach",episode_index]` on fresh IDs.
Renewal uses `["E022",block,"develop",1]` and `["E022",block,"write",1]`.
Renewal masks use unchanged E015 mask generation with phase `E022_renewal_g1`,
selecting the scattered mask. Terminal streams use `["E022",block,"assay",h]`,
shuffles `["E022",block,"shuffle",h,founder]`, and E015 masks with phase
`E022_h{h}`. Outcomes never enter a stream seed.

Save source evidence; original/incoming/effective/erased/computed/outgoing
packets; masks; local denominators; reading births/endpoints/final port
windows; every holding state; all terminal evidence; and terminal/body CSVs.
Saved denominators and earlier packets are offline audit evidence only.
An independent auditor imports no production model/runner and reproduces
every update, denominator, erasure, physical zero, packet, score, interval
and gate. It checks blocked/source-isolated equality at every relevant
update and retains the 1e-10 teaching-symmetry tolerance.

Five fixtures cover local arithmetic/zero-strength cases; exact predecessor
baseline and terminal agreement; unchanged activity-only capture; physical
damage, blocked boundaries and forbidden information paths; and independent
end-to-end replay. Preserve failed attempts and all input snapshots.

Run the excluded full-duration one-lineage benchmark after fixtures. Its
pre-run estimate is `1.5*(9/13)*E021_benchmark_workflow_seconds`, below ten
minutes. Benchmark outcomes do not select parameters. Forecast the cohort
with `2.5*(benchmark_worker_seconds+benchmark_audit_seconds)*4*ceil(32/workers)+90`,
where workers=min(12, available CPUs). Scale benchmark bytes by 4×32 plus a
1 GiB reserve. Runs forecast over 600 seconds detach under RUN_POLICY.md;
the user polls. All writes remain in experiments, with one numerical thread
per worker and at most 12 logical CPUs total.

Compensation is supplied machinery. Row normalization changes effective
coupling symmetry despite reciprocal stored edges. A positive result would
establish one-boundary functional transmission with this intervention, not
native compensation, acute repair, regrowth, autonomous timing or indefinite
renewal. Prior experiments, manuscripts and sister sources remain unchanged.
