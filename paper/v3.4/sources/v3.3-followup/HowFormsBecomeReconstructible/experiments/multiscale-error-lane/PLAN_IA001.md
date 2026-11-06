# IA001 plan: which history each component of NL003 makes recoverable

**Written 1 November 2026 by fork I1, before any export or decoder** (times in the run root's progress.md). It answers the PI's handoff "Measuring which history each component makes recoverable", pasted between 14:03Z and 14:10Z on 1 November with the words "make a note of this and start a parallel run". The lead relayed it in INFORMATION_AUDIT_HANDOFF.md (the lane's plan and the handoff verbatim). The task is that note's "Instructions for the multiscale lane".

## What IA001 is, and is not

- **A post hoc, retained-data information-source audit of NL003.** No simulation, no rerun, no block drawn. Nothing in NL003's, NL002's or NL001's frozen packages or run roots is changed.
- **The first deliverable** is an export manifest. Post hoc block predictions follow only after the analysis freeze has been reviewed by the lead and then by the theory lane.
- **Every estimate on NL003's development cohort is post hoc within that cohort.** The cohort is 16 blocks: 910746–910751, 910753–910758 and 910762–910765, with 8 cases a block in each of 2 units. NL003's results on it were read on 1 November. Nothing here confirms NL003, and no positive claim is made beyond what the predictions show.
- **No decoder touches development data before the freeze is reviewed.** NL003's engineering roots serve only to check the interface, as the handoff's development-only export: P46 (900488–900491, tag mse-p46), the preflight (900492–900493) and the debug run (900494–900495, tag mse-nl003).

## The inventory: retained, derived, missing

Read from `nl003/worker.py` (what was saved and how) and from the files, all under the frozen digest `ece312e2b4f8…`. Per unit (none, dw) and block, `raw/<unit>/<block>.npz` holds:

| Array | Shape | Saved dtype | Native | Transformation |
|---|---|---|---|---|
| TA, TB | 8 × 64 × 64 | int8 | float64 ±1 | exact |
| R0, RB (A's and B's acquired records) | 8 × 64 × 64 | float32 | float64 | rounded to float32 |
| V0 (A's acquired body) | 8 × 64 × 64 | float32 | float64 | rounded to float32 |
| BgA, BgK, BgB, BgC (L2: own, copy, foreign, corrupt) | 8 × 16 × 16 | int8 | float64, 1.2 × sign, constant on each region | the sign at each region's corner; lossless (native = 1.2 × the sign over the region) |
| r (each tissue branch's final record) | 90 × 8 × 64 × 64 | float32 | float64 | rounded to float32 |
| H, W (final bonds) | 90 × 8 × 64 × 64 | int8 | float64 in {−1, 0, 1} | exact |
| V (final body; dw only) | 90 × 8 × 64 × 64 | float32 | float64 | rounded to float32 |
| am, aval (gated branches' final anchors) | 60 × 8 × 64 × 64 | int8 | bool and float64 in {−1, 0, 1} | exact |

`shards/<unit>/<block>.npz` holds the endpoints at the reads (tissue 250, 1,000, 2,000; recipients 500, 1,000, 2,000), the dose, the case counts (ncorrupt, n_dreg, n_min_reg, n_anchor_live0), and in its meta the branch names (labels, rlabels, gated, gated_r, succ) and the case keys. `manifest.json` gives every file's sha256.

**Derived exactly from retained fields,** by the frozen rule named (each to be checked in the interface export):
- the gauge frame σ of any saved bonds (`nl001.sim.gauge_frame`);
- the anchor sites per density, by `nl003.sim.anchors` (case, 'anchors', density), and the misread values by `nl003.sim.read_displaced`;
- the event units (R's four regions, K's square) by `nl001.sim.event_units` and `kill_mask`, and NL002's masks (the differing regions and cells, A's minority regions and cells; observer resources, never decoder inputs);
- the acquired records' bonds, `edges_from(bonds(R0, True))` and the same for RB;
- **the L3 block codes** of own and copy, and so of corrupt, which takes own's L3. `nl002.sim.read_codes` reads them from a body or record with addressed noise: B3 = 1.2 × block mean of sign(V) + 0.1 × N(0, 1) per block. Own's reads sign(V0), copy's sign(R0).
- the live anchor mask at the final instant t = 2,000: am & (|r| ≥ 0.2) & (sign(σ Bg) ≠ 0), from the final r, σ and the branch's code;
- the recipients' birth fields (address(tag, case, 'successor', 'dw')).

**Missing** (not saved, and not derivable without rerunning dynamics):
- B's acquired body VB, and so **the foreign reference's L3 code B3B**, which `read_codes` reads from VB;
- the bodies' moving averages E0 and EB;
- every intermediate state (t = 1–1,999), the refusal maps, and the live masks before t = 2,000;
- the recipients' own states: only their endpoints at 500, 1,000 and 2,000 were kept.

**A correction to the brief's inventory:** the L3 codes are read from bodies by NL002's `read_codes`, not derived from R0 by NL001's rule. Own's and copy's derive exactly from saved fields; B's does not.

**The outgoing package, field by field,** for every recipient condition: NL002's record-only and coded recipients, NL003's gated coded recipient, and the three extra record-only branches acqA, acqB and none.
- **The parent's final record r:** retained as float32. The recipient read the float64 value, so the export is lossy in the last bits.
- **Its bonds H and W:** retained, exact.
- **The codes,** for the coded and gated recipients:
  - L2 exact;
  - L3 derived for own, copy and corrupt, and missing for foreign;
  - the arm's k2 and k3 are design constants.
- **The anchors,** for the gated recipient: retained, exact (the parent's final am and aval, which the recipient reads unchanged).
- **The extra branches:** acqA and acqB use R0 and RB (float32) with their derived bonds; none uses zeros and gain 0.
- **What stays outside:** the birth fields and the recipient's noise streams, which belong to the common apparatus.

## What NL003's design lets vary (identifiability)

- **The tissue's acquired history is always A,** and the anchors hold A's signs. The exceptions are change, where the differing regions hold B's, the misread arms, where A's signs are read displaced, and K, where the square's anchors are removed. A target such as "which history did the tissue acquire" or "which history do the anchors hold" is therefore fixed by the design, and not identifiable as stated: a constant predictor scores perfectly.
- **What varies within a case:**
  - the reference fed to the descending pathway: copy (A's L2, read from A's record), foreign (B's) and corrupt (A's with as many regions flipped as differ between A and B);
  - the arbiter (off, the rule, the side arms);
  - the event (none, R, K, change) and the gain (0.5, 0.75, 1);
  - and, through the dynamics, the final record and the outgoing package.
- **The label must never enter an input:** the arm name, the reference index, which code array was used, and the masks built from TA and TB.
- **The shared background:** A and B share their block signs, so A/B identity is carried only by the minority structure. A decoder must not score from the block signs, which are counterbalanced by construction.
- **The legitimate update:** change is one run scored twice, and its inputs are identical under both readings, so any decoder is at chance for that distinction. This is analytic, and is checked as an exact duplicate-input identity.

**The entropy accounting** (analytic, from NL001's generator; computed, not fitted):
- **A/B identity:** 1 bit (k = 2, uniform).
- **The shared background:** the block signs, 13.65 bits a sheet.
- **A's minority regions:** 10.83 bits a block given its sign, 173.28 a sheet. A and B differ in 6 regions a block on average, 96 a sheet.
- **A's minority cells:** 6.91 bits a region given its sign, 1,768.16 a sheet.
- **What the 1,024 anchor sites carry:** A's sign at a random quarter of the cells, which reveals at most about 2.14 bits a region of minority-cell placement beyond the region sign, about 547 bits a sheet. They are not 1,024 independent bits, and relative to A/B identity the relevant quantity is 1 bit.

## The targets: the definitional choice, for the lead's ruling before the dry run

The handoff asks for A/B identity, minority-region identity and fine detail to be scored separately. It also asks to compare codes alone, anchors alone and their joint input. The brief says the code array's own identity is the label. These admit three readings, with different meanings, so the definition is not settled.

**Option I: judging the incoming code (dictionary-free; the native arbiter's problem).**
- **Target:** M = whether the L2 code delivered to the tissue is its own history's or another's: copy against foreign, k = 2, a uniform prior by design (one of each a case and gain). Corrupt against copy is a second binary task.
- **Inputs:**
  - the code's 256 region signs, as values, with no index;
  - plus one tissue source: none (setup only), the local record at the branch, the body V0, the anchors, or a joint.
- **No candidate dictionary:** the decoder, like the native gate, has only the tissue's own state to compare against.
- **Expected analytically:**
  - code alone, chance (copy and foreign codes are exchangeable draws);
  - anchors alone, no target information (there is no code to judge);
  - the code with the record, the anchors or the body, high.
  - That is "informative only jointly", the handoff's case.
- **Per region,** the same task is the native gate's granularity: is the code's sign in this region the tissue's own? There the misread and density-1/16 arms and K matter.

**Option II: which history each source carries (with the within-case dictionary {TA, TB} as an observer resource).**
- **Target:** for each source in each condition, its A/B identity, minority-region identity (per differing region, A's or B's sign) and fine detail (A's minority cells), scored against the dictionary.
- **Sources:** the record at the branch, the body, the delivered code, the anchors, the final record and the outgoing package.
- **This is a content inventory.** For the static sources it is analytic (sign R0 = TA, the copy's code ≈ A's region signs, the anchors = A's signs at the sites); for the final record and body, under each condition, it is fitted.
- **It measures what the reviewer named:** the anchors carry A's fine detail, which the region codes cannot. But a target fixed by the design (the anchors' A) is reported as analytic, not scored by a fitted decoder.

**Option III: whether the exposure crosses (the outgoing row).**
- **Target:** M = copy against foreign reference, decoded from the outgoing record r and bonds H, W only, without the codes, which are the label at that boundary. The anchors are added for the gated recipient's package.
- **Beside it,** the native successors' specificity: record-only, ungated coded and gated coded.
- **Expected:** with the arbiter off the foreign exposure is visible in the record (overwritten); with the rule it is largely hidden (the record stays A). So added anchors would lower the decodability of the exposure while raising the native successor's A.

**The recommendation:**
- Option I as the registered primary, at the branch instant under none: the block-paired held-out log loss (bits) of the code with the anchors, minus the code with setup only, at k* = 0.75.
- Option I's per-region version and Option II's content inventory as prespecified secondary measurements, each score kept separate.
- Option III reported beside the native successors.
- The change identity checked as an exact duplicate-input identity.

## Decoders, splits and metrics (the handoff's rules; the details go into the freeze)

- **Decoders:**
  - inspectable first: the sign-agreement rule in the code's gauge frame, which is the native gate's arithmetic, and template comparison against the dictionary (Option II);
  - regularized logistic regression on region-level agreement counts, with the L2 penalty chosen inside the training folds;
  - one stronger regularized comparator on all permitted cheap features.
- **Splits:** by block (16 development blocks; leave-two-blocks-out folds, fixed by block order). Every branch, recipient and candidate of a block stays on the same side.
- **Controls:**
  - target-shuffled training (labels permuted within the training folds, the held-out labels untouched);
  - exact duplicate-input checks;
  - label balance checked within the strata unit × event × gain × arbiter variant.
- **Predictions are frozen** (written and hashed) before any score is computed.
- **Metrics:**
  - accuracy, chance 1/k and the confusion matrix, with ties scored p = 1/k;
  - held-out log loss in bits with a probability floor of 10⁻³ (sensitivity at 10⁻² and 10⁻⁴), against the prior-only log loss;
  - predictive information relative to the prior, H(M) − E[−log₂ q], with its assumptions, never accuracy turned into bits;
  - block-paired differences between input sets with whole-block 95% t intervals (t(0.975, 15)), on one declared primary comparison;
  - the native endpoints beside the decoding, and each decoder's fitting and inference cost.

## The price

- **CPU:** the manifest, the derivation checks and the interface export about 0.3 CPU-hours (reading about 1.3 GB). The fits after the freeze are under 1 CPU-hour; logistic models on a few thousand samples.
- **Disk:** the interface export on the engineering roots stays under 0.2 GB in IA001's run root. The full fields stay in NL003's run root, cited by path, sha256 and schema.
- **Compute:** at most 4 single-threaded processes at nice 10.

## The order of work (the lead's brief)

1. This plan.
2. The package `ia001/` (inventory, export and manifest, checks, decoders, analyze) and `tests/test_ia001.py`; the decoders are tested on synthetic data only.
3. The full export manifest for the development root: the manifest only, with no decoder.
4. The interface export on the engineering roots, with the derivation checks. The decoder dry run waits for the lead's ruling on the targets above.
5. The draft IA001_ANALYSIS_FREEZE.md, after the ruling.
6. The lead's review, then the theory lane's review of the freeze; only then fitting on the development blocks.
