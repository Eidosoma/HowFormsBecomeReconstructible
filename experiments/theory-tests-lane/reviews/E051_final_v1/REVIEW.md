# Completed E051 review — 9 October 2026

E051 passes its frozen rebuilding-pairing robustness criterion, and its separate full dynamics audit reports PASS for all 32 blocks. The completed cohort supports high original-writer performance when rebuilding cue noise is mismatched. It also shows that the original writer's comparative advantage depends strongly on that noise regime. This is development evidence for new theory claims, not an RDT confirmation.

The scientific run finished on 8 October at 22:38:23 UTC; the independent audit finished on 9 October at 06:18:31 UTC. The audit identifies completion hash `aff3387d46e6f907d033d2c0046cf93d7b349c1f06243ee02600ca54567c9c62` and reports replay of all teaching, rebuilding, holding, assays and mechanism summaries. Its legacy-compatibility flag is false because the scientific mode does not repeat the excluded fixture/benchmark's E041 comparison; the code explicitly assigns that flag by run mode. It is not a reported legacy mismatch.

## Completed outcomes

All counts are h32 normalized scattered-terminal both-cue successes out of 512 lineages in 32 independent blocks. A terminal success does not mean all 32 rebuilding bodies succeeded.

| Rebuilding cue condition | Original exact writer | Ordinary writer | Pure contrast | Bridge preservation | Tolerance 1e-4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Matched | 458 (89.45%) | 110 (21.48%) | 0 | 368 (71.88%) | 13 (2.54%) |
| Noise correlation .999 | 497 (97.07%) | 466 (91.02%) | 497 (97.07%) | 486 (94.92%) | 320 (62.50%) |
| Noise correlation .99 | 494 (96.48%) | 484 (94.53%) | 494 (96.48%) | 492 (96.09%) | 403 (78.71%) |
| Noise correlation .9 | 492 (96.09%) | 497 (97.07%) | 492 (96.09%) | 494 (96.48%) | 440 (85.94%) |
| Independent noise | 495 (96.68%) | 500 (97.66%) | 495 (96.68%) | 511 (99.80%) | 485 (94.73%) |
| Reset correlation .99 | 457 (89.26%) | 115 (22.46%) | 0 | 368 (71.88%) | 14 (2.73%) |
| Independent reset | 456 (89.06%) | 98 (19.14%) | 0 | 368 (71.88%) | 14 (2.73%) |

The original writer meets all five primary requirements. Absolute lower bootstrap bounds are 86.13% matched, 95.12% at noise correlation .999, and 86.13% at reset correlation .99, each above 75%. The two mild-perturbation differences from matched performance are +7.62 percentage points [5.08, 10.35] and −0.20 [−0.98, 0.59]; both lower bounds exceed −5 points. This verifies E051's prespecified conjunction. The intervals are whole-block bootstrap intervals under its declared procedure.

The original-minus-ordinary advantage is +67.97 points [63.48, 72.27] with matched rebuilding noise, +6.05 [3.52, 8.40] at correlation .999, and −0.98 [−2.93, 0.98] with independent noise. Pure contrast has the same aggregate terminal scores as the original writer in all four noise-mismatch arms. Under independent noise, bridge preservation exceeds the original writer by 3.13 points [1.56, 4.69]. These are the declared secondary, pointwise comparisons; they do not establish population equivalence or a familywise claim across alternatives. Bridge preservation still writes some edges and must not be called protected copying.

Returning-edge fallback selection is 100% under matched cues and both reset-only perturbations, and zero under all four rebuilding-noise perturbations. Mean absolute returning-edge contrast changes from zero to .0016407 at noise correlation .999 and .0526028 with independent noise. Thus the measured mechanism changes while terminal performance stays high. Connectivity and mean magnitudes alone do not identify which connections carry function.

The fixed tolerance writer remains harmful in the matched regime: 13/512 successes versus 458/512. It reaches 320/512 at correlation .999 and 485/512 with independent noise. This result concerns the specified threshold and its changes to all eligible small nonzero contrasts; it does not show that every finite-tolerance rule fails.

## Verification and interpretation limits

This lane verified the audit-to-completion identity, all 20 frozen input hashes, and the report/summary/manifest hashes. It checked 64 raw input files, reconstructed 110,592 h32 cue observations from saved mean ports with an independent scalar score calculation, and reproduced 236 endpoint, comparator and mechanism summaries, including their fixed bootstrap intervals and all primary gates. The retained [receipt](SOURCE_RECEIPT.json), [script](verify.py) and [checked arrays](h32_checked_arrays.npz) specify this bounded verification. This lane did not rerun the eight-hour dynamics workflow; the source audit is a separate implementation, not an independent experimental cohort.

The original bootstrap procedure can return [0,0] or [1,1] when all sampled block outcomes coincide. Such degenerate intervals do not establish zero population uncertainty. No stronger rare-event guarantee is inferred here.

Teaching, holding and terminal-assay cue pairing remain unchanged. E051 does not test joint rebuilding reset-plus-noise perturbation, independent terminal cue randomness, the full E041 qualification battery, or indefinite heredity. The eight-block early snapshot remains preserved; this review supersedes its pending completion/audit status. All 32 blocks are now explicitly exposed development evidence for new RDT predictions in this lane.

## Next experiment

The recommended next theory-tests task is [TT005's draft repeated-readout study](../../TT005/DRAFT_PROTOCOL.md). It reuses fixed E051 final packets, crosses terminal cue-noise and cue-reset pairing, and repeats assays without rewriting the packet. That addresses the observation model left unresolved by TT003 and TT004 and the assay-pairing limit of E051. Both-cue success, individual-cue margins and repeat disagreement must be retained: changing cue dependence can change the joint success probability without changing either cue's marginal probability.

The theory lane already has protocols for native sign/magnitude interventions and a single tolerance pulse; those would duplicate a new tolerance-mechanism study here. E052's planning draft addresses finite precision and normalization. Their existence supports prioritizing this complementary readout task. Their latest result reports were not opened in this review; prior native continuation counts printed in those protocols were logged as incidental development exposure.

After a readout contract is specified and assessed, the forecasting task remains full-model uncertainty and selection-aware abstention, followed by a genuinely sealed prospective comparison on eligible conditions. TT004's two submodel guarantees do not validate that complete predictor. No TT005 implementation, benchmark or scientific job has been launched.
