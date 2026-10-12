# D129 — address ambiguity audit

2026-09-15. COMPLETE; saved-data audit and standalone reconstruction pass.
[Audit protocol](../protocols/L20_ADDRESS_AMBIGUITY_AUDIT_V1.md).

## Result and scope

**Template-assisted alignment is a promising next experiment. This audit is
post-hoc and descriptive, not a tested decoder or new confirmation of L20.**
L20 remains STRESS_TESTED / MIXED.

On the 192 translated-source records, the supplied-template comparison
identified the correct family in **190/192 (98.96%)**. Its joint best-fit set
contained the expected historical-shift phase in **181/192 (94.27%)**.
These are retained, previously observed records, with repeated lives/strata
inside eight blocks—not 192 independent or unseen test examples.

The analysis used both canonical templates and packet bytes, but did not
receive the true role or source shift until evaluation. It retained all
maximizing offsets rather than selecting a corrected packet. No reader
outcome was loaded; no new simulation, decoder fitting or renewal occurred.

| Retained route / family | Unique correct family | Expected phase in joint best-fit set | Best own-family correlation, mean |
| --- | --- | --- | --- |
| Translated A | 96/96 | 87/96 | 0.94217 |
| Translated B | 94/96 | 94/96 | 0.84542 |
| Aligned A | 96/96 | 96/96 | 0.97749 |
| Aligned B | 96/96 | 96/96 | 0.91823 |

For B, conditioning on the true family gives the expected phase in all96
own-family best-fit sets; two records instead favor family A globally.
Both are block70005, life0, strata2/3: not two independent founder failures.
Their family margins are -0.08417 and -0.15364. No failures were excluded.

The nine A phase mismatches are all one grid cell from the expected phase,
after accounting for target symmetries. Mean own-template improvement over
the expected shift is only0.001176 across all96 A records, maximum0.040557.
This does not make the historical shift incorrect, or establish that the
alternative phase would improve a descendant. It is a static fit diagnostic.

Inverse-shifted translated records repeat the same family and expected-phase
counts; shifted aligned records repeat their aligned counterparts. This is
the expected translation invariance of the exhaustive template comparison,
not additional evidence from independent examples.

## What the ambiguities mean

A's ideal pattern has16 distinct translated phases and16 shifts that leave
it unchanged. B has8 phases and32 such shifts. Their translation orbits do
not intersect, so identifying family can be easy while identifying an exact
shift label is underdetermined.

For every nonconstant audited record, the own-family template fit retains
exactly16 A or32 B maximizing offsets. These are equivalent relative to the
ideal template, not necessarily byte-identical corrected noisy records.

In fact, all1,536 nonideal route/shuffle observations have only the identity
as an exact value self-symmetry. Their noise/texture breaks the ideal
symmetries. **That neither proves nor rules out historical-origin clues in
the noisy records.** Template-fit ties arise from the template's symmetries;
a unique-looking noisy sheet does not by itself specify its original origin.

In the restricted ideal model, even with family known, uniform shifts on
all256 offsets permit exact-shift success at most6.25% for A and3.125% for B.
With D127's nonzero-only uniform support, those counting limits become
16/255 =6.2745% and8/255 =3.1373%; canonical observations have15/31 aliases,
other observations16/32. These bounds DO NOT apply automatically to noisy
D127 developmental records under their particular source distribution.

The unanchored translation observation model also admits256 latent/shift
descriptions (255 with nonzero shifts) producing the same observed bytes.
Those alternative latent fields are not shown to be valid D127 source
histories. This is an algebraic access warning, not proof that no learned
decoder could infer exact shifts from the actual source distribution.

## Structure, residual distortion and controls

Packet-only features show strong directional structure without target input:
translated A's row-mean variance fraction averages0.96987; translated B's
column-mean fraction0.91244. Their opposite-axis fractions are0.00765 and
0.02261. Corresponding shuffled records are around0.06 on either axis.
These are spatial projections, not causal fractions, learned class labels,
absolute-origin estimates or inherited information quantities.

Even allowing every template translation, the translated-source records
fit their own ideal family less closely on average than aligned records:
A0.94217 versus0.97749; B0.84542 versus0.91823. Thus the two ensembles are
not related solely by a rigid shift. This is consistent with D128's
incomplete rescue, but does not causally apportion its remaining reader gap.

All three ideal routes identify family and expected phase in192/192 cases
each. Zero records are ambiguous between both families and all512 template/
offset candidates, with no expected phase or forced answer.

Translated shuffles identify family in96/192 cases, split A64/96 versus
B32/96; do not treat A's above-half count alone as evidence of retained
content. The template comparison is visibly biased toward A on these
controls. The other three shuffle panels return89/192,90/192 and89/192
correct families. No probability calibration or chance hypothesis test was
performed; all summaries are descriptive, with no new qualification gate.

## Law connection and next proposal only

D129 separates family identity, template-relative alignment, exact historical
address, and actual descendant performance. D128 remains the causal rescue
result. The current audit makes a supplied-template, shift-blind reader a
reasonable candidate, not a confirmed capability.

For L20, the still-open question is whether a reader can use the packet's
content with an explicitly declared address rule instead of an analyst's
saved shift. For L17, poor fixed-coordinate readout need not imply no
transmissible pattern identity. This does not retest the original long-horizon
fine-anatomy claims, demonstrate learned ontology, or upgrade either law to
a universal statement.

Next proposal: a prospectively frozen **template-assisted, shift-blind
alignment reader**, tested on fresh source records and fresh recipients.
Its only intervention should be a rigid permutation of the supplied record,
not substitution or injection of an ideal template. Fix a tie-handling rule
before outcomes; compare with no correction, the known-shift correction and
matched shuffled/ideal controls. The true shift/role must stay evaluation-only.
No inference from static fit alone that a different chosen phase helps.

This would test useful address recovery given a supplied template library,
not autonomous learning of the library or a historical-origin impossibility
theorem. New protocol, identities and user approval are needed. No successor
code, decoder, simulation or run was created or launched here.

## Execution and verification

Four new science files (script, tests, wrapper, protocol) and this live
review; all earlier frozen inputs, including the completed D128 review,
were preserved.299 tests passed in17.19s, no failures/skips, including all256
ideal shifts. External report logs/d129_tests_attempt1.xml; fixtures under
tmp/d129_tests_attempt1. XML full-panel duration1.783s implied the fixed
177.056s forecast, below the600s foreground guard.

Input snapshot2026-09-15 17:46:48.936062 UTC pinned729 inputs, including326
repository-side files. Audit COMPLETE17:47:21.049655 UTC in32.1136232s,
2,855,267 bytes before the COMPLETE marker and2,856,711 bytes total
(~2.72MiB), within32MiB. One process/numeric thread, CPU affinity0–5.
All data/logs/caches external. No long job, detachment or polling loop.

All2,304 records,1,561 distinct packet byte strings and1,179,648 correlations
are retained. Direct sums and independently restated FFT correlations agree
within1.33226763e-15. Execution-time saved roundtrip passes. A separate saved
audit again passes729 input/five output hashes, all rows/maps/statistics.

The separately prepared NumPy/stdlib-only reconstruction imports neither
the production audit nor its checker. It uses separable one-dimensional
template projections and explicit modular indexing to reconstruct packet
features, every score, family/phase/tie diagnostics, geometry and all group
summaries from D128 packet data. It passes on first execution: maximum score/
summary difference1.33226763e-15, feature difference4.44089210e-16.
No source/reader trajectories, outcome-based offset selection, fitted decoder,
confidence intervals, new thresholds, exclusions, retries or automatic follow-on.

Artifacts under /mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation:

- [Summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_address_ambiguity_audit_v1_attempt1/summary.json), SHA256 fd6c2fbfb46e913ec9098383d361046db52cecba8713e476a3ecfc25ee30aa40.
- [Records](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_address_ambiguity_audit_v1_attempt1/records.json), SHA256 aba2f4ed3778529fa200ae0f40a57f383f01581bd2454ae1e26b0735095b0de7.
- [Scores](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_address_ambiguity_audit_v1_attempt1/scores.npz), SHA256 b278ef1b233f9483864976cb993a32046da414fa1ea61edb40ffef6b1dd4327e.
- [Verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_address_ambiguity_audit_v1_attempt1/verification.json), SHA256 863db31da9dbf902e4ee12b6da79d2fb45eb72b44e3847ea457e4630dc23f94f.
- [Input snapshot](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_address_ambiguity_audit_v1_attempt1/INPUTS.json), SHA256 eb82b7ef3916001bb062f1d276737468b4e7305401b3de40d643a78ed5014e81.
- [COMPLETE](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_address_ambiguity_audit_v1_attempt1/COMPLETE.json), SHA256 9ef84685cb2baf1d7832c74b08f00b80d68bd69a606043877bd0673a3c2de429.
