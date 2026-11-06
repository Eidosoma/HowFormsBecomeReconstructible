# IA001 analysis freeze (DRAFT): which history each component of NL003 makes recoverable

**DRAFT, 1 November 2026, fork I1, for the lead's review and then the theory lane's.** No decoder has been fitted on NL003's development root; `ia001.analyze` refuses it until `ia001/frozen/analysis_freeze.json` exists. On the reviews' word, that file is written from this document with the code hashes below, and only then is the development root analysed.

- **The task:** the handoff "Measuring which history each component makes recoverable" (pasted by the PI between 14:03Z and 14:10Z on 1 November; INFORMATION_AUDIT_HANDOFF.md, "Instructions for the multiscale lane").
- **Scoping:** PLAN_IA001.md.
- **The lead's ruling on the targets:** 14:28Z, adopted here in full.
- **Status:** a post hoc information-source audit of NL003's retained data.
  - NL003's development cohort was read on 1 November, so every estimate below is post hoc within that cohort.
  - No simulation, no rerun, no block drawn; nothing here confirms NL003.
  - The scores of an external observer, with or without the dictionary, are not the native reader's reconstruction, which is reported beside them.

## The data and the inclusion rule

- **The cohort:** all 16 development blocks of NL003, 910746–910751, 910753–910758 and 910762–910765, with all 8 cases a block. Nothing is excluded.
- **The files:** `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/nl003/development/` (raw and shards, both units).
  - Every file's sha256 equals NL003's manifest.
  - The export manifest `ia001/manifest_development.json` (81,086 B) lists every array's sha256, the derived fields with their rules, and the missing fields.
- **One case counts once at the branch.** At t = 0 the code, the anchors, R0 and V0 are the same acquisitions in both units. The branch analyses therefore read the `none` unit's files.
  - That the `dw` unit's branch inputs are byte-identical is checked per block (TA, TB, R0, RB, V0, the four L2 codes, and the anchors of copy-k0.75+A/none and foreign-k0.75+A/none), as part of the duplicate check.
  - At t = 2,000 the units differ, so they are analysed separately and never pooled.
- **Exactly derived, verified on the development root with 0 differences:**
  - sign R0 = TA and sign RB = TB at every cell (min |R0| 0.280);
  - the L2 codes of own and copy recomputed from the saved float32 fields (smallest sign margin 8.7 × 10⁻⁵), and corrupt's recomputed;
  - all 1,920 gated branch-blocks' anchors rebuilt by NL003's rule;
  - one float32 record cell within 10⁻⁶ of the 0.2 bound.
- **Missing and not used:** B's acquired body, so the foreign reference's L3 code; the moving averages; intermediate states and refusal maps; the recipients' states.

## The input blocks

A sample's inputs are built from these alone. Never inputs: the arm name, the reference index, which code array was used, the event label, and the masks built from the dictionary.

| Block | Content |
|---|---|
| S, setup | the 64 × 64 sheet, its 4 × 4 regions, 16 × 16 blocks and region corners, the gauge rule, the anchor densities (design constants; no case data) |
| C, code | the delivered L2 code: its 256 region signs |
| Z, anchors | the gated branch's anchor mask and signs (static over the window) |
| L, bonds | the local record's bonds H, W, and so its gauge frame σ: history-specific (the acquired relations), part of the record |
| R, record | the local record's values (R0 at the branch; the final r at t = 2,000) |
| B, body | the body (V0 at the branch; the final V at t = 2,000) |
| dictionary | TA, TB: an observer resource, used only by Options II and III, and declared there |

**Why the frame belongs to the record.** In NL002's gauge code, a region's L2 sign is, for a record read exactly, the sign of the region's corner cell. A comparison of C with a field without L (frame-free) therefore compares at the region corners. A framed comparison compares sign(σ C) with the field at every cell, which is the native gate's arithmetic and needs L.

## The analytic results, stated before any fit

1. **info(code + record + anchors) − info(code + record) = 0 at the branch, by construction.** The anchors are sign(R0_A) at the case's sites, a deterministic function of the record and the setup. The fitted difference is a check of the decoders, not a measurement. The anchors' only unique contribution is that they persist (t = 2,000).
2. **Anchors alone carry no information about the delivered code.** Each case's two samples (copy, foreign) have identical inputs, so every decoder is at chance: 1 bit at the best constant. Fitted values are reported as checks.
3. **The change pair is at chance.** It is one run scored twice, against A as a coherent corruption and against B as a legitimate change, so its inputs are identical under both readings and any decoder is at chance. It is reported, not fitted.
4. **The information accounting** (from NL001's generator):
   - the delivered code's identity is 1 bit (k = 2, uniform);
   - the shared block background is 13.65 bits a sheet;
   - A's minority regions are 173.28 bits a sheet, and A and B differ in about 96 regions;
   - A's minority cells are 1,768.16 bits a sheet;
   - the 1,024 anchor sites reveal at most about 547 bits of minority-cell placement beyond the region signs. They are not 1,024 independent bits.
   - Differences between decoder bounds are differences in predictive performance, not unique or conditional mutual information, and no causal budget is formed.

## The targets

**The primary (Option I).**
- **Target:** M = the delivered L2 code's identity: copy (A's, read from A's record; y = 1) against foreign (B's, read from B's body; y = 0).
- **k = 2, with a uniform prior by design:** each case contributes one sample of each.
- **No dictionary.**
- **The instant:** the branch (t = 0), event none. The inputs at t = 0 do not depend on the gain; k 0.75 names the gated branch whose anchors are read (density 1/4, values sign R0).
- **The primary comparison, the only one, as an information gain.** The lane's convention, used for every paired difference in this document: a difference is an information gain in bits, and positive means better.
  - **primary = info(stronger, code + anchors) − info(stronger, code + setup) = loss(code + setup) − loss(code + anchors):** the block-paired mean over the 16 blocks of the per-sample held-out log-loss difference, at the probability floor 10⁻³.
  - Its 95% interval uses t(0.975, 15) on the 16 block means.

**Also at the branch, the same target:**
- code + setup;
- anchors alone;
- code + anchors (frame-free);
- code + anchors + frame (the native gate's inputs at the branch);
- code + record (R and L);
- code + body (frame-free) and code + body + bonds;
- code + record + anchors (analytic result 1).

A pathway control: own (A's code read from A's body) against foreign (B's, from B's body), code alone. It separates a reading-pathway signature from identity, since copy is read from a record and foreign from a body.

**Secondary: the instant t = 2,000** (both units separately; event none, k 0.75).
- **The same target in the arbiter-off arm and in the gated arm.** The inputs are:
  - code + the final record (r and its final bonds);
  - code + the anchors (frame-free; static, so equal to the branch's);
  - the gate's inputs (code, anchors, the final bonds' frame and the confidence |r| ≥ 0.2).
- **What it tests:** the anchors' persistence. Where a foreign code overwrites the record, the record comes to agree with it (coherent wrong agreement), and code + record loses the identity to the extent that the overwrite is complete. Code + anchors does not.
- **The paired difference,** by unit and arm: the gain info(code + anchors) − info(code + final record).
- **Reported beside it:** the live anchors' disagreement with the code's target at t = 2,000, by unit and arm.

**Secondary: Option I per region** (the branch, the `none` unit).
- **Samples:** every region where the copy and foreign codes differ in sign, once with each code (y = 1 for copy's region, y = 0 for foreign's).
- **Inputs, with each anchor arm's anchors:** A, A2, Asur, As1, A2s1, A16, A2d16.
- **The inspectable decoder** is the native rule's decision (nl003.sim.gate on the branch state, with the arm's n, q and surround). The stronger comparator uses the region's agreeing, disagreeing and live anchor counts.
- **Regions of a case are not independent samples.** Groups are blocks, and the block is the unit of every interval.

**Secondary: Option II, which history each source carries.**
- **The dictionary {TA, TB},** in a case-keyed random order: the first candidate is A with probability 1/2, seeded by the case key and 20261101, independent of every label.
- **The target:** whether the first candidate is A (k = 2).
- **The levels, scored separately:**
  - region level: the region signs in the regions where A and B differ;
  - fine detail: the differing cells inside the regions where A and B agree, and each candidate's own minority cells;
  - combined.
- **Masks** are symmetric in the two candidates.
- **The sources:**
  - the static ones (R0, the anchors, the copy and foreign codes) are analytic: sign R0 = TA; the anchors are sign R0 at the sites; the copy code is A's region-corner signs, the foreign code B's as read from B's body;
  - the final record (both units) and the final body (dw) are fitted, in the conditions copy, foreign and corrupt × off and gated (k 0.75, none).
- **One decoder pooled over the conditions,** scored per condition. The condition is never an input: a decoder trained within one condition could learn to invert it.

**Reported: Option III, the exposure at the outgoing boundary.**
- **Target:** copy against foreign.
- **Inputs:** the outgoing package (the final r, H, W, plus the anchors for the gated package; never the codes, which are the label at that boundary). The dictionary is used in fixed roles (A, the tissue's own), as a declared observer resource.
- **Coverage:** per unit and package.
- **Beside it,** the native successors' specificity at 2,000: record-only (s/), coded (c/) and gated coded (g/).

## The decoders and their features

- **Inspectable,** each through a logistic link fitted inside the training folds:
  - the prior (p = 0.5) where an input set has no reference (code + setup; anchors alone);
  - the frame-free corner rule (the share of anchored or valued region corners where the field's sign contradicts the code);
  - the framed agreement (the share of compared cells where sign(F) ≠ sign(σ C));
  - the native rule per region;
  - the 2AFC agreement difference.
- **The regularized logistic** on per-region features: the code's 256 region signs (code alone), the corner comparison (−1, 0, +1 a region), or the framed per-region disagreement fraction; 512 features for record + anchors.
- **The stronger comparator, the primary decoder on both sides of the primary comparison:** a regularized logistic on all permitted cheap features.
  - **The code's own features** (18: the share of + regions, each block's count of regions against the block's own code majority, and their total) enter every input set that holds the code.
  - **Added to them per input set:**
    - the corner comparison's (disagreeing share, disagreeing and compared counts);
    - the framed comparison's (disagreeing share, the share of regions with any disagreement, the share refused by the native rule n 1, q 0.75, the compared count);
    - for anchors alone, the anchors' sign counts per block;
    - for Option II, the level's agreement differences.
  - **Why it is primary:** the same decoder family on both sides, so that no weak comparator is called an information limit (the handoff). The inspectable decoders are reported beside.
- **Fitting:**
  - L2 logistic regression (scikit-learn 1.7.1, lbfgs);
  - the penalty C ∈ {0.01, 0.1, 1, 10, 100} chosen by inner leave-one-block-out on the training blocks (log loss);
  - standardization fitted on the training folds.
- **Folds:** two consecutive blocks in the declared block order, 8 folds. Every sample of a block (its codes, branches, regions, conditions and units) is on one side.

## Controls and safeguards

- **Target-shuffled training,** for every stronger decoder: the labels are permuted within (block × stratum) in the training folds (seed 1), and the held-out labels are untouched. It must give no positive information.
- **Exact duplicate-input checks** on every decoder's inputs: pairs of identical rows, and those with different labels. The anchors-alone and change identities are expected, and the cross-unit identity at the branch is checked.
- **Label balance per block:** 0.5 by design for Options I and III; random and reported for Option II.
- **Held-out predictions are written,** with each one's sha256 and the file's, before any score is computed.
- **Probability floor:** 10⁻³ (clipping to [floor, 1 − floor]), with the sensitivity at 10⁻² and 10⁻⁴.
- **Metrics:**
  - accuracy, with ties (p = 0.5) credited 1/2; chance 0.5; the confusion matrix;
  - held-out log loss in bits; the prior-only log loss (1 bit);
  - the predictive information relative to the prior, H(M) − E[−log₂ q(M | X)], a variational lower bound on I(M; X) under the declared prior, which can be negative for a poor decoder; never accuracy converted into bits;
  - block-paired differences with whole-block 95% t intervals;
  - each decoder's fitting and inference cost.
- **The native endpoints are reported beside the decoding:** the tissue's specificity and the successors' (s/, c/, g/) at the last read.

## The dry run on NL003's engineering roots (development-only; not a result)

- **The setup:** P46, the preflight and the debug run, 8 blocks (900488–900495) and 64 cases, in 4 folds of 2 blocks.
- **Run:** 23.1 s of wall on one core.
- **The predictions:** `runs/.../ia001/dry_run/predictions.npz`, sha256 `ba800696724413c7…`, written before the scores.
- **The report:** `report.json`.

**The branch** (the stronger comparator unless named; information in bits):
- code + setup −0.073 (the prior 0; the regularized logistic −0.079);
- anchors alone 0.000 exactly (64 duplicate pairs with different labels: analytic result 2);
- code + anchors +0.997 (inspectable +0.999); code + anchors + frame +0.998;
- code + record +0.998; code + body +0.992; code + record + anchors +0.998;
- the shuffled controls −0.033 to −0.010;
- the pathway control (own against foreign, code alone) −0.097: no signature;
- **the primary (dry run):** +1.071 bits [+0.939, +1.202] over 8 blocks;
- **analytic result 1 (dry run):** +0.00005 [−0.00002, +0.00013], zero up to fitting noise;
- the cross-unit branch inputs byte-identical in all 8 blocks.

**t = 2,000:**
- **Code + anchors** keeps the bit in every unit and arm (+0.997).
- **Code + the final record:**
  - keeps it with the gate (stores +0.998, body +0.998);
  - keeps it in the stores' arbiter-off arm too (+0.998). There the foreign code overwrote only part of the differing regions (specificity −0.384), so the record still contradicts it elsewhere;
  - in the body's arbiter-off arm it keeps +0.532 of the bit.
- **The gain of code + anchors over code + the final record:**
  - +0.466 [+0.270, +0.662] in the body's arbiter-off arm;
  - −0.0009, −0.0010 and −0.0004 in the stores' arbiter-off arm, the stores' gated arm and the body's gated arm, where both decoders are near perfect.
- **The live anchors' disagreement with the code's target:**

  | Unit, arm | copy | foreign |
  |---|---|---|
  | stores, off | 0.000 | 0.420 |
  | stores, gated | 0.000 | 0.421 |
  | body, off | 0.193 | 0.373 |
  | body, gated | 0.227 | 0.412 |

**Per region** (13,794 region samples; the native rule | the stronger comparator):

| Arm | Native rule | Stronger comparator |
|---|---|---|
| A | +0.956 | +0.987 |
| A2 | +0.829 | +0.987 (same anchors) |
| Asur | +0.016 | +0.987 |
| As1 (misread) | +0.210 | +0.396 |
| A2s1 | +0.207 | +0.396 |
| A16 (density 1/16) | +0.443 | +0.650 |
| A2d16 | +0.146 | +0.650 |

**Option II** (information for the first candidate being A):
- **Region level:** the arbiter-off foreign record carries B's coarse identity (stores −0.969, body record −1.193, body −0.992). Gated it carries A's (+0.92, +0.80, +0.90). Under corrupt/off, +0.420, +0.402 and +0.556.
- **Fine detail:** the foreign record keeps A's (stores +0.999, body record +0.861, body +0.827).
- **Combined:** dominated by the fine detail.
- **So identity is level-specific:** a foreign region code imposes B's coarse pattern and leaves A's fine detail.

**Option III** (the exposure, copy against foreign, from the outgoing package):
- with the arbiter off it is visible: +0.998 in the stores, +0.998 in the body;
- in the gated package it is half hidden in the stores (+0.418; region level +0.293) and visible in the body (+0.988).
- **The native successors after foreign, in the stores:** off: the coded successor −0.286, record-only +0.306. Gated: the gated coded successor +0.980.
- **In the body:** off: coded −0.359, record-only −0.286. Gated: gated coded +0.690.

## What each outcome would mean (the handoff's last section)

- **The primary's direction is expected from the design.** The anchors hold A's acquired signs, and a foreign code contradicts them in the regions where A and B differ, so code + anchors must beat code + setup. The primary's value is the accounting (where the identity sits, and how much), not a discovery. The informative results are:
  - analytic result 1: the anchors' redundancy with the record at the branch;
  - their persistence at t = 2,000. In the body's arbiter-off arm code + record keeps +0.532 of the bit and code + anchors all of it: a gain of +0.466 on the dry run;
  - the per-region losses under misread and sparse anchors, with the native rule discarding part of what the anchors carry;
  - Option II's level-specific identity.
- **If code + anchors recovers the identity and code alone and anchors alone do not:**
  - the anchors are externally accessible historical content that tells the faithful reference from the foreign one only jointly with the code;
  - neither carries it alone;
  - with the native gate's refusals and the successors (NL003's gated against ungated coded successor), this is the handoff's combined result: an added source improves held-out access to the identity, and a matched intervention on that source changes the identity the native successor reconstructs.
- **At the branch the anchors add nothing beyond the local record** (analytic result 1). A positive t = 2,000 gain of code + anchors over code + record in the arbiter-off arm would locate their contribution in persistence, not in content.
  - If code + record keeps the identity anyway, the overwrite was incomplete. Coherent wrong agreement is partial, and the record still holds evidence.
- **If code alone carries information above the shuffled control:** the codes betray their reading pathway or another regularity. The own/foreign control tells which; it is not identity.
- **Option II's levels:** identity is reported per level. Region-level and fine-detail identity can point to different histories in the same record, and neither is "the" identity.
- **Per region:** misread and sparse anchors carry less per-region identity, and the surround rule discards what they carry. These map to NL003's side arms, as external access, not native protection.
- **The change pair** is unresolvable by any decoder (identical inputs): the information limit, stated.
- **What this does not license:**
  - an exhaustive measure of information;
  - a causal allocation among record, body and anchors;
  - a confirmation of NL003;
  - reading the dictionary-based scores (Options II and III) as the native reader's reconstruction;
  - any manuscript change: the PI's hold stands.

## Resources and code

- **The development forecast:** about twice the dry run's samples; about 1 minute of wall and under 0.1 CPU-hours, one core at nice 10.
- **The code to be frozen** (sha256 prefixes at this draft):

  | File | sha256 |
  |---|---|
  | ia001/analyze.py | 5574ddd0913c |
  | ia001/checks.py | 78b5af83c3cb |
  | ia001/decoders.py | 571f4f7ea0c7 |
  | ia001/design.py | 299107115ee8 |
  | ia001/export.py | b17e187544d6 |
  | ia001/inventory.py | 1b92fcbf537d |
  | tests/test_ia001.py | 79b4510532ce |

- **Changes after the reviews** are recorded here as dated amendments before any development fit.
