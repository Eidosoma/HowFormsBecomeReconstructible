# E018 — function through one and three body-written replacements

Frozen before simulation, 2026-09-18. The user authorizes the next renewal test
after E017 qualified its staged reader. This is the first test of this writer
boundary, not confirmation of previously demonstrated functional inheritance.

## Fixed apparatus and explicit new boundary

Use E016's consistent learned records and E017's staged reader unchanged:
16×16 reciprocal local torus, 512 float64 edge weights (4096 bytes), gain 2,
2048 reading updates with positive linear amplification off for the first 256.
All other E015 defaults, ports, two rules, two input cues and strict ±.25 output
thresholds remain. Source acquisition retains E016's full routine and its unused
ordinary/engineered byproducts for audit; only consistent records enter lineages.

Exactly 32 fresh blocks **16000–16031**, four founders per block (two matched
opposite-rule pairs), and four independent renewal lineages per founder: 128
founders and 512 lineages. None is selected by formation or task success.

At each of three boundaries, each lineage has two fresh, intact cue episodes.
The bodies receive only the incoming packet, the public input and the fixed
reader clock. Birth/noise are paired across cues, opposite rules and boundary
conditions, as in E017. Outputs are never clamped or supplied during renewal.
After 2048 updates, retain the two current body states and **erase the incoming
record before writing**. Reset all communication weights to the supplied unit-
positive scaffold. For 128 further updates use the original local gain-2
dynamics (amplification on), fresh noise and the same input clamp. Accumulate
`tanh(3*v_i)*tanh(3*v_j)` for neighboring cells, averaging equally over all
128 updates and both cue episodes. Encode these means as the new 4096-byte
record. The accumulating new record does not feed back during writing.

The writer API receives only current body states, a public random stream and
fixed parameters; it receives no incoming record, rule, desired output, founder
template or success score. Erased incoming buffers, developed states and all
writing states are retained as offline evidence, never passed to successors.
Only the outgoing packet crosses each boundary. New births and noise are
independent across generations and from teaching and final assays.

This explicitly supplied read→erase→neutral-scaffold write schedule is new.
It tests whether activity can carry useful information across removal of the
incoming weights. It may fail even when the inherited packet reads reliably.
No endpoint freezing, output teaching, success selection, alternative writer
or longer capture window will be added after outcomes.

## Comparisons and assays

Maintain four matched boundary conditions:

1. **renewed**: read and replace by the activity-written record at every boundary.
2. **protected_copy**: preserve exact original record bytes at every boundary.
3. **read_blocked**: replace the incoming weights by zero during every renewal
   reading episode; otherwise use the identical writing procedure.
4. **write_blocked**: read normally, run and retain the same writing calculation,
   but transmit an all-zero packet after each boundary.

Assay the original record once at generation 0 and all four conditions after
one and three replacements. Each assay uses fresh bodies and noise, independently
of the renewal bodies. One paired-cue assay per lineage and damage condition;
four lineages are nested within each founder, not independent blocks. Assay
damage never feeds into the renewal chain. This is challenged expression after
intact renewal, not inheritance through repeated damaged development.

Keep E015/E017's intact, 24 randomly removed non-port cells, and 3×3 square
lesion conditions, without connectivity rejection. Within every assay preserve
own, opposite-rule foreign (same lineage index and boundary condition), shuffled
edge values, erased, untrained, communication-off and input-isolated controls.
All ports are protected. The final 32-step output average determines strict
success. Opposing cues share births/noise; input isolation must produce exactly
identical non-input trajectories. There are **193536** individual condition/cue
scores: 32 blocks × 9 assay panels × 4 founders × 4 lineages × 2 cues × 3 damage
conditions × 7 arms. Every score and all failures count.

## Inference and stopping rule

The single primary endpoint is **intact both-cue strict success after three
renewed replacements**. Require its two-sided 95% whole-block bootstrap lower
bound >.75. Both inputs must be correct for the same matched founder/lineage.
This tests absolute retained function; a small advantage over an ineffective
control alone does not qualify. The .75 threshold applies to this paired-input
primary endpoint, explicitly stricter than the earlier individual-cue threshold.

For the full claim of reliable, information-dependent renewal, additionally
require all original 24 gates after both one and three renewed replacements:
six rule×damage individual-cue accuracy lower bounds >.75 and 18 own-minus-
assay-control accuracy lower bounds >.10. At each of those horizons and each
damage condition, require renewed individual-cue accuracy minus read_blocked
and minus write_blocked lower bounds >.10 (12 further gates). Report primary
and full qualification separately, retaining every failed gate. All technical
checks and the independent audit must pass before any scientific claim.

Report every condition/arm/damage result, rule-specific accuracy, margins,
both-cue accuracy, and paired renewed-minus-copy/read-blocked/write-blocked
effects at both horizons. The protected-copy comparison measures rewriting
cost, without an additional noninferiority claim. Display the original 24 gates
for every assay panel, including initial and copying controls. No pooling with
E015–E017. Use 10000 percentile resamples of the 32 independent whole blocks,
seed ["E018","bootstrap","renewal"]. All intervals and gates beyond the single
primary endpoint are pointwise; the full result is a conjunction, not a search
for whichever endpoint passes. A degenerate 100% bootstrap interval does not
prove population certainty. Stop after this frozen experiment regardless of
outcome; no adaptive rescue or further experiment is automatic.

## Streams, evidence and execution

Source streams stay ["E016",block,"teach",episode_index]. Renewal development
and writing use ["E018",block,"develop",generation] and
["E018",block,"write",generation]. Assays use
["E018",block,"assay",horizon], shuffles
["E018",block,"shuffle",horizon,founder], and unchanged E015 damage generation
with ["E015",block,"E018_h{horizon}","damage"]. No rule or success enters seeds.

Preserve all teaching states/byproducts; all incoming, read-effective, erased,
computed and outgoing record bytes; renewal births/developed endpoints and
final-32-step port traces; all 128 writing states; and assay packets, masks,
births, endpoints, late means and final-32-step port traces. Earlier assay
states are deterministically replayable from frozen inputs/streams. An
independent implementation replays every update and checks bytes, isolation,
scores, intervals and gates without importing the production model or runner.
Reuse existing independent E015/E017 equation helpers only. Retain the 1e-10
teaching sign-symmetry tolerance; saved state replay must be exact.

Short fixtures check current-activity-only writing, local correlations,
record/label exclusion, exact copying, disrupted boundaries and independent
end-to-end replay. Keep failures and fix technical bugs before scientific
execution, without changing criteria after outcomes.

Excluded technical benchmark **900018** uses full durations and three boundaries
but one lineage per founder to keep simulation plus audit below ten minutes
(E017 scaling predicts roughly 4–5 minutes). Only lineage count differs from
the scientific cohort. Forecast conservatively as
`2*(benchmark_worker_seconds+benchmark_audit_seconds)*4*ceil(32/12)+90`.
Check storage from actual benchmark files with ×4×32 scaling plus 1 GiB reserve.
If a benchmark or cohort forecast exceeds 600 seconds, launch detached with
durable status/PID/log and automatic audit/figures; the user polls. At most
12 logical CPUs, one numerical thread per worker. All writes remain in this
experiment tree; manuscripts and sister trees are read-only.

Any positive result concerns an explicitly instructed elementary routing task
and supplied acquisition/reader/writer machinery. It does not demonstrate
autonomous goals, active repair, a new embodiment, or independently active forms.
