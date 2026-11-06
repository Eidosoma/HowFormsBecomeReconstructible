# The information-source audit: the handoff and this lane's plan

**1 November 2026, between 14:03Z and 14:10Z** (by the lead's clock: after a status check at 14:03:08Z and before this note's first commit, pushed at 14:10:38Z; a first version said "about 14:20Z", a time typed without the clock). The PI pasted the handoff below, "Measuring which history each component makes recoverable", and asked the lead: "make a note of this and start a parallel run". This file is that note: what the handoff asks of this lane, how the lane will do it, and the handoff verbatim. No protocol, frozen package or manuscript text is changed by it.

## What the handoff asks of this lane

- **The multiscale lane (its own section):** a post hoc information audit of NL003's retained data, beside the running follow-ups and without changing their protocols. The first deliverable is an export manifest and post hoc block predictions, "not a new positive claim or a rerun".
- **The Forms lane:** E014's founder-identification export, "integrated with the already running protected-foreign and long-horizon specificity work". That work is this lane's HS001 (phase A since about 13:45Z), so the schema request reaches HS001 here.
- **The theory lane** reviews the NL003 decoder freeze, for grouping, input leakage and uncertainty, before any fitting.

## The lane's plan

**IA001, a post hoc information-source audit of NL003** (a forked session; the lead reviews; no simulation).
1. **Retained data only.** NL003's development cohort holds 16 blocks: 910746–910751, 910753–910758 and 910762–910765, 128 cases a unit.
   - Its results were read on 1 November, so every estimate on it is post hoc within that cohort.
   - NL003's engineering roots (P46, the preflight and the debug run) serve only to check the interface, as the handoff's development-only export.
   - Nothing is regenerated. A field that was not saved is recorded as missing. A field computable exactly from saved ones is marked derived, with its rule.
2. **The lead's inventory of what NL003 saved,** per unit and block:
   - the templates TA and TB (int8);
   - the acquired records R0 and RB and the acquired body V0, saved as float32 (native float64);
   - the region codes BgA, BgK, BgB and BgC (int8);
   - every tissue branch's final record r (float32) and bonds H and W (int8), and in the body its final V;
   - the gated branches' final anchor masks and signs (int8);
   - the shards' endpoints at the three reads.
   - **Not saved:**
     - the L3 block codes. **Correction, 1 November, from IA001's inventory:** they are not derivable from R0 by NL001's rule. NL002's `read_codes` reads them from a body with addressed noise. So own's, copy's and corrupt's are derivable from the saved acquisitions, but the foreign reference's is not, because B's acquired body VB was not saved;
     - intermediate states and refusal maps;
     - the successors' states and outgoing packages, of which only their endpoints were kept.
3. **The audit follows the handoff:**
   - the targets A/B identity, minority-region identity and fine detail, kept separate, with their candidate counts and priors;
   - inputs per the handoff's decoder table (setup, record, body, joint, the extra state Z of the anchors and codes, outgoing);
   - inspectable decoders and a stronger regularized comparator;
   - splits grouped by block, with target-shuffled controls and duplicate checks;
   - held-out predictions frozen before scoring;
   - log loss in bits against the prior, confusion matrices, and block-paired differences with whole-block intervals;
   - native reconstruction reported beside decoding.
4. **The order of work:**
   - the export manifest;
   - an interface export on the engineering roots;
   - a dry run of the decoder pipeline there;
   - a draft analysis freeze;
   - the lead's review, then the theory lane's review of the freeze;
   - only then fitting on the development blocks.
5. **Not in scope now:**
   - NL004's retained data, which is the same interface with made anchors, a natural extension after NL003;
   - any rerun;
   - any change to NL003, NL004, AR003 or HS001;
   - any manuscript text.

**HS001 takes the Forms request into its schema** before its freeze, without changing its endpoints or adding simulations.
- **Its own cohort's outputs** carry what an external founder-identification task needs: candidate prototypes as evaluator resources; packets and recipient fields with block IDs and native dtypes; the inclusion decisions; one candidate set for own, foreign and protected records; and phase or coordinate tolerance stated.
- **E014's own cohort:** its raw lineage fields are not on this host. Only the per-block summaries are here; the 128 lineage archives stay on the producing host, with their hashes recorded in E014's handoff. So no identity export of that cohort is made here without those archives, or a deterministic regeneration on the PI's word.
- **No decoder is fitted in HS001.**

**The manuscript hold stays in effect.**

## The handoff, verbatim (as pasted by the PI)

# Measuring which history each component makes recoverable

**1 November 2026. Proposed analyses and lane handoffs; no experiments launched.** This plan accompanies the [information-boundary audit](INFORMATION_BOUNDARY_AUDIT_V3.3.md). It preserves the user's hold on manuscript changes and does not amend any running or frozen protocol. Analyses of already inspected cohorts must be labelled post hoc. A later fresh confirmation needs its own freeze.

The deliverable is a per-assay description of **representation size, recoverable historical identity and native reconstruction**, with those three quantities kept separate. It is not an additive allocation of success to the body, record and apparatus. The [protocol calculations](INFORMATION_AUDIT_CALCULATIONS_V3.3.json) already establish two useful design constraints; all proposed fitted-decoder results below remain unmeasured.

## Start with retained data

1. Retrieve existing matched inputs, outputs and manifests; do not regenerate favorable examples. Record every missing field and any conversion from native precision.
2. Freeze a bounded analysis of TT021 and NL003 first. Their identical-record and extra-anchor controls most directly address whether another component contributes history-specific content.
3. Extend the same reporting format to guided spatial renewal and functional repair. The guide-only null and D145 offset calculation can be checked without launching new trajectories.
4. Keep forecast prevalence/calibration work, long-horizon specificity tests and pruning follow-ups on their existing tracks. This request should not create duplicate simulations or change their primary outcomes.

An initial export may contain all fields from a small, predetermined set of blocks for interface checking. Such an export is for development only. Final analyses require all eligible retained blocks or a documented sample chosen without inspecting the decoding outcome. Do not treat the one D140 figure example as a sample of the full cohort.

## Define the target and the information available

For each assay, declare a historical identity M, its candidate count k and prior, common setup A, incoming record R, body state B at a specified instant, extra controller information Z, and outgoing record O. List codebooks and candidate dictionaries separately as observer resources. Learned references and controller memory count as history-specific state wherever they reside.

Use these input sets when they exist:

| Decoder | Permitted inputs | Question |
|---|---|---|
| Setup-only | A | Does the nominally shared apparatus identify the selected history? |
| Record | A, R | What identity is accessible before repair or rewriting? |
| Body | A, B | What identity is accessible from the surviving body/reference state? |
| Joint | A, R, B | Does adding the body improve access beyond the incoming record? |
| Extra-state | A, R, Z; also A, Z | Do anchors, selected offsets, calibration or controller memory add identity information? |
| Outgoing | A, O | What identity is accessible after writing and at a fresh-body boundary? |

Do not put a true target label inside A and then call decoding successful. When the native forecaster or guard receives the label, document that fact and exclude its full input set from a nontrivial identity test. Evaluate forecast success or policy value separately. A label-blind auxiliary decoder of its packet remains meaningful.

For unprescribed forms, founder IDs have no common semantic meaning across independent blocks. Supply an explicit within-block candidate dictionary for the external recognition task, with identical candidates available to every decoder. The dictionary is not an input to the native writer. State whether the task is matching one of four observed founders, distinguishing family, recovering phase, or recovering fine detail; these are not interchangeable targets.

For the guided assays, report family identity and within-family founder/phase identity separately. For functional records, the taught orientation has two values. For NL003, A/B identity, regional codes and fine signs require separate scores. More cells, bytes or candidate draws do not increase the entropy of a two-value identity.

## Decoders, uncertainty and safeguards

Start with an inspectable decoder matched to each representation: fixed template/candidate comparison, a sign-based structural rule, or regularized linear/logistic prediction. Include a stronger regularized comparator using all permitted cheap features. Select feature scaling, regularization and probability calibration only inside development folds. More flexible decoders may be a sensitivity analysis at a declared additional budget, not an opportunistic replacement for a failed primary decoder.

Split at the independent tissue, founder block or network. Keep all related lives, phases, interventions, records, descendants and candidate prototypes from a source block on the same side of the split. No outcome, target-encoding seed, arm name containing the answer, row order or hidden index may enter the decoder. Use target-shuffled training controls and exact duplicate-input checks. Balanced labels must be checked within relevant backgrounds and strata, not merely across the whole dataset.

Freeze held-out predictions before scoring. With small retained cohorts, use a declared grouped cross-validation scheme and call the result a post hoc estimate within that cohort. An untouched decoder test split does not retroactively make an already developed experimental mechanism prospectively confirmed. Report independent block counts and paired block differences; descendants improve measurement within blocks but do not create more independent samples.

Report, on the same inclusion set and prior:

- Accuracy, balanced accuracy if needed, chance level 1/k for a uniform task, and the full confusion matrix. Specify tie handling; fractional recognition scores are not automatically realized categorical decisions.
- Held-out multiclass log loss in bits, with a frozen probability-floor convention and its sensitivity analysis. Report the prior-only log loss alongside it.
- Block-paired differences between input sets, using whole-block intervals and a stated primary comparison. Keep regime-specific results visible.
- Native fresh-body reconstruction and relevant historical-specificity or continuation endpoints beside decoding. Successful recognition by an external observer is not successful reconstruction by the supplied reader.
- Decoder training cost and per-case inference cost, including candidate templates, probes, optimization and feature construction. Do not charge a complex observer to one representation while calling a weak comparator an information limit for another.

For a known target distribution and a decoder q, the population score

\[
H(M)-\mathbb E[-\log_2 q(M\mid X)]
\]

is a variational lower bound on I(M;X), provided X is the permitted input and the target entropy is correctly specified. Its empirical held-out estimate has sampling uncertainty and can be negative for a poor decoder. Report it as **predictive information relative to the declared prior**, with its assumptions. Do not convert accuracy into bits by an ad hoc formula. A confusion-matrix information estimate concerns the decoder's output and needs a finite-sample bias check.

Differences between two imperfect decoder bounds measure their difference in predictive performance; they are not automatically estimates of unique or conditional mutual information. In particular, R and B can contain redundant information or be informative only jointly. The decoder experiment alone cannot allocate causal credit among them. The [variational-information source](https://proceedings.neurips.cc/paper/2003/hash/a6ea8471c120fe8cc35a2954c9b9c595-Abstract.html) provides the relevant bound; the intended application here is an auxiliary assay, not a claim of exhaustive information measurement.

## Compact handoff format

Each lane should return a small source manifest, block-level prediction table, aggregate report and reproducible analysis script. Large fields can remain in run storage, with path, hash, schema and retrieval instructions. Publish derived per-block outcomes sufficient to reconstruct the reported estimates.

The manifest should include:

| Item | Required content |
|---|---|
| Provenance | Campaign, protocol/code hashes, run root, raw-array hashes, inclusion rule, missingness and exposed/development/held-out status. |
| Boundaries | Time of sampling; incoming, repair-time and outgoing fields; what crosses the recipient boundary; what stays outside. |
| Arrays | Name, shape, native dtype, exported dtype, bytes and any lossy transformation. Include masks, coordinates, gauge and controller state. |
| Target | Candidate count and dictionary, identity prior, nuisance variables, exact definition of the scored distinction. |
| Decoder | Permitted inputs, features, group splits, tuning/calibration rules, seed, code hash and measured resource cost. |
| Predictions | Source-block ID, record/pair ID, regime, condition, boundary/horizon, decoder ID, target, predicted probabilities, native outcome and fold. Labels remain isolated from decoder inputs. |
| Estimates | Absolute scores, native/balanced weighting, paired block differences and intervals; distinguish analytic deductions from fitted estimates. |

A binary prediction table can use `p0,p1`; a k-class table should carry all k probabilities and their label mapping. Keep metadata used for grouping distinct from arrays passed to the decoder. Save numerator and denominator counts rather than only rounded percentages.

## Instructions for the theory-tests lane

> Prepare a post hoc information-source analysis of retained TT021, with D074 and TT032 as distinct supporting comparisons. Do not start new simulations or amend current tests. Retrieve all common-packet, body/reference and outgoing-record arrays plus independent-block and pairing manifests. Verify byte identity within opposite-message pairs before decoding. Compare setup-only, packet-only, body-only, joint and outgoing inputs under the same allowed setup and candidate dictionary. Include early capture, ordinary writing, partner-body substitution and held-snapshot conditions. Report within-pair polarity separately from four-message identity. The common packet has at most 50% four-way accuracy and no within-pair polarity information under the audited assumptions; investigate any violation as an input/interface issue. Test whether partner substitution changes the decoded outgoing identity in the same direction as native fresh-body readout. Preserve D074's failed donor-redirection result and distinguish extra body content from continued live-feedback value. For TT032, decode acquired identity and reset-template identity separately; include the injury/fill mask and reset field in accounting and keep this cohort separate from TT021. Return compact block predictions, masks/state schema, code and hashes; mark missing native fields explicitly.

Theory-tests can also prepare functional repair exports once the TT021 interface is settled:

> Export matched TT014 incoming, repaired, shuffled-addition and erased records, with labels stored separately and the complete inclusion manifest. Inventory the lattice, input pins, optimizer and zero-location information received by repair. Fit a label-blind two-orientation decoder under common setup, compare changes in identity recoverability with fresh-recipient benefit and harm, and preserve regime distinctions. Do not interpret input pins as an output label or zero completion as arbitrary-error correction. TT016/TT018 continuation is a later extension of this audit; retain each experiment's own sampling and noise conditions.

## Instructions for the multiscale lane

> Add a retained-data information audit alongside the running follow-ups, without changing their protocols. For NL003, export local reference/bonds, regional and block codes, live anchor mask/signs, body state and actual outgoing package for every recipient condition. Include positional/gauge/calibration data that the native gate or recipient uses. Distinguish native dtype from saved float32/int8 exports. Compare codes alone, anchors alone and their joint input, with local record and common apparatus held explicit. Evaluate A/B identity, minority-region identity and fine detail separately; do not call 1,024 sign locations 1,024 independent historical bits. Include wrong/foreign anchors and code/anchor disagreements where already retained. Counterbalance or condition on shared background and legitimate updates. Show whether added anchors improve decoding and native successors, and whether coherent wrong agreement remains indistinguishable. The primary first deliverable is an export manifest and post hoc block predictions, not a new positive claim or a rerun. Keep serial inheritance and source-reliability experiments on their existing freezes.

This lane is directly involved in the current reviewer request: the anchors are acquired information outside the regional codes. The previous forecast-specific comment did not require it, but this one does.

## Instructions for the L20/L22 spatial lane

> Audit D135/D140 and D145 as distinct interfaces. Export the full eligible incoming/routed/outgoing packets, guide, selected routing/feedback shifts, body/reference states and founder/block labels from retained runs. Do not use the single illustrative D140 sequence for population estimates. Verify that the guide repositions the existing packet rather than replacing it with template values. Report family identity, within-family founder identity and phase separately. Compare guide/setup-only, packet-only and packet-plus-guide observers with the same candidate dictionary. For D145, list the external family-aware shift selector as an input source and check its saved schedule against the frozen pools. The protocol alone gives 98.3871% optimal family classification and 0.954946 bits from one compatible offset under a balanced two-family prior; this is an analytic design result, not the within-B primary effect or an estimate of the writer's causal use. Keep message-conditioned controls out of the nominally shared setup. For L22 repair, preserve the D074 donor-criterion failure and coordinate exports with theory-tests rather than duplicating TT021 analysis. Return an input/output manifest and compact predictions; no new run is requested.

## Instructions for the Forms lane

> Reuse E014's retained founder/checkpoint fields to define an external founder-identification task among the declared matched candidates. Export candidate prototypes, packets and recipient fields with independent background/block IDs, native dtypes and all inclusion decisions. Prototypes are evaluator resources, not native reader inputs. Preserve the current qualified/sign-only/amplitude outcomes and keep them separate from identity decoding. Use the same candidate set for own, foreign and protected records, and make phase/coordinate tolerance explicit. Integrate this output schema with the already running protected-foreign and long-horizon specificity work, without changing its frozen primary endpoint or duplicating simulations. Compact cell counts alone do not support arbitrary field decoders. If raw fields are elsewhere, supply their hashes and location before any new fitting.

## Instructions for the theory lane

> Coordinate the common decoder reporting format and review the information interpretation. A fixed shared guide, history-specific anchors and a supplied true task orientation are different resources. Do not convert bytes or accuracy directly into historical information, or add separate-source estimates into a causal budget. For TT008/equal-read forecasting, list which labels, ports, histories and probes each predictor receives; keep label-decoding out of predictors already given the answer. Continue the existing absolute-score, natural-prevalence, calibration and stronger-baseline handoff separately. For the current-success guard, document the true-orientation signal, protected incoming packet, candidate record and selection cost. Describe label-removal or backup-removal controls as future policy tests unless already run; do not change the qualified policy retrospectively. Review the TT021 and NL003 post hoc decoder freezes before fitting, especially grouping, input leakage and uncertainty. A common auxiliary identity assay is useful; it is not yet a universal information measure across the simulators.

FEP and cellular/Hopfield lanes need no additional launch for this comment. Their future interfaces should use the same inventory when task-specific controllers or learned calibration are involved. Task transfer and policy-value tests already assigned to them remain the priority.

## When manuscript changes would be justified

The completed inventory can later replace scattered boundary qualifications with a concise main-text table, retaining the detailed audit in supporting material. New measured decoding rows require verified exports, frozen analysis and block-level predictions. Distinguish explicit label access and analytic design bounds from estimates obtained by trained observers.

The strongest new conclusion would combine two results: adding a particular source improves held-out access to historical identity, and a matched intervention on that source changes the identity reconstructed by a native successor. If only decoding improves, say that historical content is externally accessible. If reconstruction improves without added decoding, the source may facilitate reading rather than add distinguishable message content. Neither outcome should be hidden or forced into an additive budget.

No manuscript insertion or qualification change is authorized by the measurements proposed here alone. The current manuscript hold remains in effect while the user runs the follow-ups.
