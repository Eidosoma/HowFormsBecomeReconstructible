# E023 — local compensation in the receiving body

Fixed before new simulation, 20 September 2026. The user authorized this
prospective test after E022's saved-state diagnosis. E022's primary benefit,
failed full qualification and descriptive analysis remain unchanged.

## Cohort and unchanged packet production

Use **32 fresh blocks 21000–21031**, four founders and four lineages per founder:
128 founders and 512 lineages. The excluded benchmark is **900023**, one lineage
per founder. These IDs were checked unused. Retain every case and mask.

Reuse E022 acquisition and its single renewal boundary without modification:
E016 consistent teaching; a 16×16 reciprocal torus, 512 float64 edges / 4096
bytes; E017 staged reading with gain 2, 2048 updates and amplification off for
the first 256; immediate activity-only capture after erasing incoming weights;
128 holding updates with no packet feedback. Keep every original parameter,
including noise .02, dt .2, birth SD .05 and strict .25 port-average margins
over the final 32 updates. Capture still averages the two cue-specific local
products of tanh(3*activity). No label, target, old packet or denominator enters
the writer. Only the captured packet crosses the replacement boundary.

The eight packet conditions are baseline damaged renewal, degree-compensated
damaged renewal, strength-compensated damaged renewal, intact renewal,
protected copying, copying with matched edge erasure, reading blocked and
writing blocked. All damaged renewal bodies lack the same 24 scattered
non-port cells from birth through capture and holding; the intact reference
has no renewal injury. Degree/strength compensation acts only during renewal
as in E022. Copying bypasses bodies. Reading blocked supplies zero effective
incoming weights; writing blocked transmits zero while retaining its computed
capture offline. Body scores remain separate from transmitted function.

## Paired receiving readers

For the original packet (horizon 0) and all eight outgoing packets (horizon 1),
compare two receiving readers with identical packets, masks, births and noise:

1. **fixed_four:** incoming neighbor sum S divided by 4, exactly reproducing
   the unchanged E017/E022 reader.
2. **local_strength:** S divided by the sum of absolute effective incident
   weights at that cell, computed after physical injury and all record or
   communication controls. If that sum is zero, incoming contribution is zero.

There is no floor, pseudocount, threshold, adaptive tuning or output-dependent
selection. Denominators are fixed throughout both staged-reading phases.
Off-stage drift is `-v**3 + 2*(S/d-v)`; the amplified stage adds `v`. Keep
noise, time step, clipping [-2,2], input clamping and absent-cell zeros fixed.
Only input ports are clamped. No score or desired output enters receiving
dynamics. Reading adds no new packet writeback or feedback to the source.

Retain intact, 24-cell scattered loss and non-port 3×3 square lesions in
terminal bodies, independent of renewal injury. Apply both readers to own,
foreign, shuffled, erased, untrained, communication-off and source-cut arms.
The normalized denominator must reflect each control's actual effective
weights, including source-cut edges. Denominators are local to the receiver
and never transmitted. Both readers share randomness within every panel;
different terminal injury panels remain distinct fresh-body assays.

Panel order is horizon 0 fixed/normalized original; horizon 1 all eight
conditions fixed, then all eight normalized. This gives **18 terminal panels,
387072 terminal individual scores and 6144 pre-capture body scores**, nested
within 32 independent blocks. Descendants, opposite rules, cues, readers and
injury panels are not extra independent units.

## Primary and full qualification

The **single primary** is the paired **scattered-terminal both-cue success**
benefit for strength-compensated renewal packets: local-strength receiver
minus fixed-four receiver after one replacement. Require the two-sided 95%
whole-block bootstrap lower bound **>0.10** (10 percentage points).

Full qualification additionally requires all of:

- Normalized candidate absolute both-cue success lower bound **>0.75** in
  both intact and scattered terminal panels. The intact requirement is retained
  from E022; scattered absolute reliability accompanies the new primary.
- All 24 original normalized-candidate gates: six rule×injury individual-cue
  accuracy lower bounds >.75 and 18 own-minus-control lower bounds >.10.
- All 24 original intact-renewal reference gates under **each** receiving
  reader, preserving the old reference and checking the changed apparatus.
- Six normalized-candidate minus normalized-read/write-blocked individual-cue
  advantage lower bounds >.10, across all three terminal injury panels.

Report primary and full conjunction separately, every failed gate, all arms,
rule-specific accuracy, both-cue success, margins and body outputs. Report
normalized-minus-fixed contrasts for every packet condition and the initial
packet, and candidate-minus-each-other-packet contrasts within both receiving
readers. Report the difference between receiver benefits for candidate and
masked-copy packets as a secondary interaction. A normalized receiver may
help copying too; no superiority to copying or mechanism-specific effect is
a qualification requirement. No alternative winner is selected by outcome.

Use 10000 percentile resamples of independent whole blocks with stream
`["E023","bootstrap","receiver"]`. All secondary intervals and qualification
gates are pointwise. Observed 100% is not population certainty. No retuning,
exclusions, extension, severity reduction, scoring change or automatic
successor follows this cohort, regardless of outcome.

## Evidence and execution

Retain predecessor semantic streams intentionally on fresh block IDs:
acquisition `["E016",block,"teach",episode]`; renewal `["E022",block,"develop",1]`
and `["E022",block,"write",1]`; terminal `["E022",block,"assay",h]` and
`["E022",block,"shuffle",h,founder]`; E015 injury masks with phase
`E022_renewal_g1` or `E022_h{h}`. Reader choice never alters a seed or packet.
This permits exact fixture agreement with E022 and no pooling of cohorts.

Save all source, renewal and assay evidence from E022 plus each receiver's
local denominators; preserve complete terminal/body CSVs and frozen inputs.
Independent audit imports no production model/runner. Reuse E022's independent
source/renewal replay and separately replay both receiving readers, checking
every update, packet, denominator, physical zero and source-isolation condition,
then every score, interval and gate. Retain teaching symmetry tolerance 1e-10.

Five fixture tests cover denominator arithmetic/controls/zero strength,
exact unchanged predecessor behavior and paired randomness, unchanged capture
and forbidden information paths, receiving-reader invariants, and independent
end-to-end replay. Preserve failures and snapshots. Freeze all code before
the excluded full-duration benchmark and do not change it based on outcomes.

The benchmark pre-run estimate is `1.5*2*E022_benchmark_workflow_seconds`
(577.45 seconds, below ten minutes). Forecast the full cohort with
`2.5*(benchmark_worker_seconds+benchmark_audit_seconds)*4*ceil(32/workers)+90`.
Scale benchmark bytes by 4×32 plus a 1 GiB reserve. At most 12 logical CPUs,
one numerical thread per process. If the forecast exceeds 600 seconds, detach
with frozen configuration, PID, log and durable status under RUN_POLICY.md;
the user requests progress checks. All writes remain inside experiments.

This tests a supplied change to the receiving apparatus. Normalization changes
effective coupling symmetry despite reciprocal packet edges. A positive
result does not retroactively qualify E022's original-reader packets, identify
a unique microscopic cause, demonstrate acute repair/regrowth, or establish
three-generation or autonomous compensated renewal.
