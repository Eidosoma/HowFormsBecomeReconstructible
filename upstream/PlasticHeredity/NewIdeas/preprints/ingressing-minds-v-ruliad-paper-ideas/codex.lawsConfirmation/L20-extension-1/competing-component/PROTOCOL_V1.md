# D149 — competing-axis attenuation with equal-distance residual shams

Approved 2026-09-19 after the D148 saved-content review. This is a causal
mechanism follow-up on an observed cohort, not fresh-cohort confirmation.
Freeze this protocol, qualified code, source closure and every edit/alias
decision before new main reader outcomes. Do not change earlier studies.

## Intervention and matched controls

Use D148's late packet in its late, naturally selected placement (LL), at
each generation. Edit AFTER that placement; never reroute the edited packet.
For the centered 16×16 record, decompose into orthogonal row, column and
double-centered residual fields. A's own axis is rows, B's own axis columns;
the other axis is the competing component. These are analyst-supplied features
of these two templates, not learned biological or autonomous concepts.

Write the packet as mean + own + c + r. Let C and R be the RMS norms of c
and r, H=hypot(C,R), and d=0.5 min(C,R). Rotate the (C,R) coefficient vector
toward the residual by theta=2 asin(d/(2H)). The attenuation arm is
mean + own + (C cos(theta)−R sin(theta)) c/C
+ (R cos(theta)+C sin(theta)) r/R.
This reduces the entire competing axis, transfers its energy to the existing
residual direction, and preserves mean, total norm and the entire own axis.
It does not delete information without replacement or globally renormalize.

Two sham arms leave c unchanged and replace r by
cos(beta) r ± R sin(beta) q, with beta=2 asin(d/(2R)). Here q has RMS one,
zero row/column means and is orthogonal to r. Obtain q by projecting a fixed
rank-one Walsh field off r; try outer(h0,h0), then outer(h1,h0), using the
first projected RMS >=0.5. h0 is eight +1 then eight −1; h1 alternates four
+1/four −1. These orthogonal seeds guarantee a well-conditioned choice.
No seed/direction is chosen by outcomes. Both shams have exactly the same
RMS edit distance d as attenuation, and preserve mean, total norm and own
axis. Their average, not the better sham, is the comparator. They are not
inert placebos: residual changes may themselves affect the reader.

If min(C,R) <= 1e-12 max(1, centered RMS), all three edits are identities.
Keep these records and controls; report their count. Never divide by a tiny
norm, invent residual organization in a degenerate case, or exclude it.
Four arms: untouched, attenuate, sham_plus, sham_minus. Float64 invariants
must hold to absolute 1e-12 (not claimed byte-exact numeric conservation).
Carrier stays 2048 bytes; guide/public rulebook unchanged. Values and spatial
organization change; preserving their full histogram is NOT claimed.

## Primary, complete panel and limits

Sole primary: B intact G2 fresh-reader preference, attenuation minus the
average of the two shams. Retain all 128 paired cases in 16 blocks, not just
the four known reversals. Average four lives and two noise replicas per block;
10,000 whole-block bootstrap draws, seed 14920260919, percentile 95% interval.
Positive favors attenuation under this matched edit; negative favors shams;
an interval crossing zero is unresolved, not equivalence.

Keep strict abs(V)>0.2 and sign(V)>0 own-minus-alternative count /256.
100×score is preference points, NOT percent success. Keep absolute arm scores,
attenuation-minus-untouched, sham-mean-minus-untouched, each sham-minus-untouched,
sham-plus-minus-sham-minus, and primary-form contrasts in every group.
Relative superiority without improvement over untouched is not a rescue.
Report all individual/block values, negative/zero outcomes, terminal profiles,
continuous signed V alignment, own/alternative reference correlations, packet
axis energies and correlations, edit dose, degeneracies, and strong-sign versus
activation/deactivation transition accounting. Secondary intervals are pointwise
and unadjusted. No replacement score, selected subgroup primary or dose tuning.

All blocks 93000–93015, four lives, two replicas, A/B, three generations,
intact/copy/lineage-read-off/write-off, all four edits: 12,288 labelled cells.
Only late packets are edited; no early/late mixing, new founders, upstream
writing or diagnostic descendants propagated. Disposable block 514246 is for
qualification/benchmark only. Preserve all conditions, including zero aliases.
Reader 300 steps, checkpoints 0,1,100,300; same D146 terminal birth/read streams
(`l20-extension1-phase-budget-v1`) for every paired arm. No new noise evidence.
D149 bookkeeping namespace `l20-extension1-competing-component-v1`.

Untouched and byte-identical edits reuse the exact source endpoint. Every
nonidentity label gets a new readout and independent full physics replay;
no outcome-based deduplication. Freeze edited-byte hashes and reuse decisions
before outcomes. There are at most 9216 new assays (write-off is degenerate,
so normally fewer); labels are not independent samples. The fixed reader gets
only the edited record plus public parameters/noise, never source body state.

Report copy−write-off, intact−read-off and intact−write-off at each
family/generation/edit (72 checks). Only the 18 UNTOUCHED checks constitute the
apparatus gate (all lower bounds >0). Edited-control changes are mechanism
results, not reasons to tune or suppress the primary. Also retain 24
intact−copy contrasts. Even a failed gate leaves the numerical primary visible.

## Qualification, provenance and resources

Pin D148 main COMPLETE
22f89ccdf1fedf056d3078fef93b57a490d9941abcec911286911e1d67ca8946 and saved-review
COMPLETE 6aba18e05950a379fa3eb3de27f7e403147ec24c8025699cdf83d467fd58b7c2,
the latter's 1703 inputs/19 outputs, saved audit, supplemental qualification
and saved-content report. Preserve that closure and prior claims.

Qualify algebra/invariants, both roles, degenerate and near-degenerate records,
fixed placement, byte aliases, matched births/noise, order independence,
fresh-reader isolation, independent edits/metrics/physics, adversarial corruptions,
source/saved hashes, 16-block statistics, all controls, and launch/resource guards.
Benchmark a complete disposable block (four lives, full panel, every new path
independently replayed), disk roundtrip, saved checks, and a 16-copy statistics
fixture labelled NOT evidence. Freeze the full main cell plan before benchmark.
No qualification/main outcome tuning of the declared edit.

Benchmark forecast: 4×full-life qualification seconds +90. Main conservative
forecast: 16×checked-block seconds×max(1,max main new assays/disposable new
assays) +2×hash seconds +180; no parallel speed credit. Storage budget:
16×uncompressed block bytes +benchmark bytes +128MiB, cap 2GiB plus 4GiB reserve.
All data/logs/caches/fixtures under
/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/.
Only code/docs here; maximum six CPUs, affinity 0–5, numerical threads one.
Any stage forecast >600 seconds is detached with null stdin, new session and
durable logs. Startup acknowledgement only; no automatic progress polling,
retry or successor. Single-use paths; preserve failed attempts.

This tests a particular energy-redistribution intervention against residual
rearrangements, not a unique mediation decomposition. It cannot distinguish
attenuation from its necessary compensating residual-energy increase. It does
not establish autonomous repair, learned ontology, complete shape preservation,
vertical renewal, natural biology, or universal competing-pattern causation.
L20 remains STRESS_TESTED / MIXED pending separate evidence review.
