# TT050 causal diagnosis for the E119 duration study — 1 November 2026

TT050 completed at 16:37 UTC and passed saved-data closeout. No E119 continuation
outcomes were opened during this review, and this note does not amend its freeze.
The full [TT050 findings](../theory-tests-lane/TT050/FINDINGS.md) and
[stream/instrumentation contract](../theory-tests-lane/TT050/FORMS_INTEGRATION.md)
are in theory-tests-lane. Relative links resolve from the delivered E119 copy.

Use the existing exact source/stream join, not a new simulation campaign:
blocks 41000–41007, all 512 source records; native/mixture × sham/pulse,
four founders, four recipients; two paired terminal draws across all arms and
both horizons. TT050 independently reproduces every saved E077 I/P first-writer
packet. Verify E119's actual stream, source and code manifests against the
integration contract before treating measurements as shared. TT050 was frozen
against the then-supplied E119 model and developing seed plan, not any uninspected
later amendment. These are exposed sources, not a new independent cohort.

The principal mixture panel gives the following immediate → one-rewrite
success counts, each out of 512 paired receiving contexts:

- Unchanged I: 255 → 318 (49.80% → 62.11%).
- Fully pruned P: 309 → 313 (60.35% → 61.13%).
- Connectivity-preserving C: 283 → 329 (55.27% → 64.26%).
- Count-matched L_native retaining other original edges: 295 → 315.
- L, same complete retained signed-weight multiset as C at isolation-preserving
  locations: 291 → 297 (56.84% → 58.01%).

At h1, C−P is +3.13 points [0.78, 5.86]; C−L is +6.25 [2.73, 9.97]. These are
pointwise approximate 95% whole-block percentile intervals; the bounded
Hoeffding intervals remain wide and include zero. P−I is −0.98 [−3.91, 2.73],
so this mixture panel does not establish the original later pruning penalty.
C−I at h1 is +2.15 [−0.59, 4.88], not a noninferiority result. C retains only
part of the immediate benefit and harms some paired receiving contexts.

C prevents initial new isolation (mean 0 versus P's 21.91 cells), but after
fresh writer injury it still creates 2.06 newly isolated surviving cells versus
20.00 for P and 13.90 for L. Their selected-edge fallback counts average 7.48,
59.94 and 41.96 respectively. All newly isolated live cells have zero cue
contrast under the matched apparatus. C/L match raw weights and counts but
not normalized coupling, graph placement or injury vulnerability. This is a
causal connectivity/placement lead, not unique mediation by isolation counts.

C−L remains positive in point estimates under reversed signs and quarter
magnitudes. Same-body P capture substitutions are byte identical to P in all
512 records and cannot distinguish capture routes. For C, ordinary selected
capture and its magnitude substitution each lose 2.34 mixture points; the sign
substitution changes 439/512 packets but has no observed binary effect. Keep
the continuous outcomes and do not infer sign equivalence or assume harmful
task-irrelevant signs. Native sources have a much larger h1 pruning penalty
without a material immediate benefit; preserve the source/history strata.

TT050 has only h0 and h1. E119's subsequent rewrites must decide convergence,
persistence or alternation; TT050 cannot answer duration or independent-noise/
tolerant-writer transport. No new serial confirmation or manuscript change
has been launched.

Compact retained outputs are `runs/development_v1/analysis/RESULTS.json` and
`CASES.csv`, plus `closeout_review_v1/{STRATA.json,PLACEMENT_INTERACTIONS.json,
CAPTURE_ALIASES.json,WRITING_BODY_BLOCKS.csv,REVIEW.json}` under TT050.
Full packets, masks, cue contrasts, fallback masks, connected components,
port reachability and normalized coupling remain in each `block_*/` directory.
The complete raw-array files are not duplicated by this handoff.

Closeout checked 144 frozen inputs, 290 distinct files, 28,672 case rows and
504 paired metric/interval calculations. The original run had independent
native replay and E077 bridges in every block. Frozen inputs and automated
outputs remain unchanged. The manuscript hold and the queued TT021 identity
audit are separate and remain in force.
