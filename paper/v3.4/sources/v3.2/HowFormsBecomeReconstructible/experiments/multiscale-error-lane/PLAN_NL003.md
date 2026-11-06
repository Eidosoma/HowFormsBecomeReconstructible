# NL003 plan: a level that can tell

**Written 31 October 2026 by fork N3, before any tuning, probe or check ran** (the time is in the run root's progress.md). On the PI's "lets go as you recommendation" (31 October 2026), relayed by the lead with the brief for NL003.

## The question

NL001 and NL002 found that across levels, gain decides, not truth (THEORY §8.24; SYNTHESIS principle 15).
- At the gain where the faithful copy repairs coherent region damage, another history's reference overwrites the intact tissue.
- No gain did one without the other; only an outside signal can arbitrate.

AR002 and AR002C (THEORY §8.28, confirmed) found that a tissue can make such a signal itself. A coherence detector compares an independent reference (sparse cue anchors) with what the tissue holds.

**NL003 asks:** can a signal the tissue makes let the hierarchy's descending pathway repair from a faithful reference and refuse a wrong one, at one gain? This is "a level that can tell" (SYNTHESIS, "What is still missing", 2).

## The tissue: NL002's, unchanged

- **Imported unchanged** from the frozen `nl002/` (and through it `nl001/`, `dl001/`, `lr001/`, `msegrid/`):
  - the 64 × 64 nested stores (L1 the fine record with its bonds; L2 the 4 × 4 region codes; L3 the 16 × 16 block codes);
  - the units `none` (stores) and `dw` (the developing body);
  - histories A and B, acquired; the references copy, foreign and corrupt, and off;
  - the events none, R and K; the cap; the record-only and coded successors; NL002's endpoints.
- **With the arbiter off, every branch equals NL002's bit for bit** (Q3). `nl002.sim.step` is called unchanged, with k2 replaced per site by k2 × G, where G ∈ {0, 1} is the arbiter's gate. With the arbiter off, G = 1 and k2 × 1.0 = k2 exactly.

## The arbiter

**Its evidence: anchors, a new declared component** (AR001's and AR002's positional cue), independent of the descending code.
- **Placement:** a random 1/DENSITY of the cells per case (lr004.sim.anchors' rule: a permutation addressed by (case, 'anchors', density) under NL003's tag).
- **Values:** history A's acquired record signs, sign(R0_A), at the anchored cells, as AR001's anchors hold the acquired record's signs.
- **Density 1/4,** AR001's and AR002's.
  - From the placement rule alone, on the smoke block (no outcome): 99.2% of regions hold at least one anchor and 79% at least three.
  - A side arm at 1/16 (one anchor a region on average; 36% of regions hold none) measures how the protection falls as the evidence thins.
- **The information budget:** the anchors add 1,024 cue signs a sheet at 1/4 (256 at 1/16), against L2's 256 codes. Reported beside every result.

**Its rule, per region and per update** (AR002's coherence rule, moved from "the anchors against the record" to "the anchors against the code"):
- the code's target at a cell is sign(σ Bg), the direction of NL002's descending increment there (σ the gauge frame of the current bonds);
- a **live anchor** is present, sits where the record is confident (|r| ≥ 0.2, `lr005.sim.vote_sign`), and sits where the code has a target (σ ≠ 0);
- n_l counts the region's live anchors, and n_d those whose cue disagrees with the code's target;
- **the region's L2 increment is refused** while n_d ≥ n and n_d ≥ q · n_l, and, for a candidate with a surround, while at most ring_max disagreeing live anchors lie within `ring` sites around the region;
- **otherwise it is admitted.** The gate is a veto: where there is no evidence (no live anchor), the code acts as in NL002.
- **L3 is not gated.** Every reference's block code is A's: B shares A's block signs, and the corrupt reference keeps A's L3. So there is nothing at L3 to refuse, and gating it would only add false refusals.

**The surround, a finding from the templates alone** (`runs/.../nl003/tools/scope_templates.py`, the smoke block 900496, no simulation):
- A and B differ in 80–104 of a sheet's 256 regions (36%), and only 25 of those 742 regions over 8 cases (3%) have no differing neighbour among the 8 around them.
- AR002's surround (no disagreeing live anchor within 2 sites of the window) would therefore admit about 97% of a foreign reference's wrong regions. The rule would refuse almost nothing.
- So the surround is not built in. It is one of the candidates in the tuning rule below, together with the rule without it, and is also reported as a side arm if not chosen. **The lead is asked to rule on this before the freeze** (Decisions, 1).

## The tuning rule (fixed here, before any tuning runs)

- **Candidates:** n ∈ {1, 2, 3} × q ∈ {0.75, 1.0} × surround ∈ {none, AR002's (ring 2 sites, ring_max 0)}, 12 in all.
- **Tuning blocks:** 900430–900433 (engineering, tag mse-p46), both units, at k2 = 0.75 × KC, the gain at which NL002's copy repaired and the foreign reference overwrote.
- **Labels:**
  - copy (events none and R), foreign (none) and corrupt (none), each under every candidate;
  - copy, foreign and corrupt with the arbiter off (none, and R for copy);
  - off (none).
- **Read** at the last update (2,000), on the record, as block means.
- **Constraints (the faithful code keeps its work):** in both units,
  - the faithful copy's refused share of regions in intact tissue is at most 0.02;
  - its alignment with A in intact tissue is within 0.01 of the arbiter-off copy's;
  - its repair of the four flipped regions (R) is within 0.01 of the arbiter-off copy's.
- **Objective:** S = the mean over the two units of min((1 + spec(foreign+arb/none))/2, (1 + spec(corrupt+arb/none))/2). This is the worse of the two refusals: another history and a corrupt code.
- **Choice:** the candidate with the largest S among those meeting the constraints. Ties within 0.005 go to the larger n (more evidence), then q 1, then no surround. If none meets the constraints, the one with the smallest false refusal.
- The tuning's every candidate value is written to `probes/results/p46a_nl003_arbiter_tuning.txt` before P46 runs. P46 and everything after use the chosen rule only.
- **Amended at 20:31:57Z on 31 October 2026, before the tuning ran.**
  - The first version scored S as the minimum of three jobs: the copy's repair, and the two refusals.
  - A 50-update code test on the smoke block (900496, with a provisional rule, to check the code; not a tuning) showed that the faithful copy's code agrees with A's anchors everywhere and is never refused. So the repair term is the same for every candidate, the minimum would have passed the choice to the tie-break, and the weakest arbiter would have won.
  - The repair became a constraint, and the objective the two refusals. The candidates, the blocks and the tie-break are unchanged.

## Events

- **NL002's none, R and K.** K also removes the anchors in the killed square, with everything its cells held (AR001's shared damage). The codes are kept, as in NL002.
- **change, the information-limit pair:** the anchors in the regions where A and B differ are respecified to B's acquired record signs; the record, body and codes are as in none.
  - Scored against A, it is a coherent corruption of the anchors. Scored against B, with the foreign reference, it is a legitimate change of history.
  - It is one run scored twice: from inside the tissue the two are the same observation. Over the differing regions the shares at A's and at B's sign add to 1 in every branch.

## Arms

- **Arbiter off (NL002's arms):** off, plus {copy, foreign, corrupt} × k2 ∈ {0.5, 0.75, 1.0} × KC (10 arms); events none, R and K.
- **Arbiter on (the chosen rule, density 1/4):** {copy, foreign, corrupt} × {0.5, 0.75, 1.0} (9 arms); events none, R, K and change.
- **Side arms (reported):**
  - density 1/16: copy and foreign at 0.75, none and R;
  - misread anchors (GC001's quenched misread at σ 1, each anchor reading A's acquired record at its displaced site): copy and foreign at 0.75, none and R;
  - the surround candidate if it is not chosen: copy, foreign and corrupt at 0.75, none and R.
- **Left out, with reasons:**
  - the reference `own`, the eroded history: secondary for NL003, and NL002 measured it;
  - k2 = 0.25 (nothing happens in the stores) and k2 = 2 (the cap binds);
  - the change event under the arbiter off, which is the none event exactly, since the anchors reach only the arbiter (an alias).

## Successors

- **NL002's two recipients, ungated, for every label:** the L1-only record, and the record with the branch's codes. Plus A's and B's acquired records, and nothing.
- **A third recipient for the arbiter-on labels:** the coded one gated by the arbiter, with the same anchors (inherited by position, killed and changed as in the branch), read against the recipient's own record.

## Endpoints

- NL002's ENDS for the record, the body and the recipients, at the reads 250, 1,000 and 2,000 (tissue) and 500, 1,000 and 2,000 (recipients).
- **The arbiter's own:** the share of regions refused (all regions; the regions where A and B differ; the others), and the share of updates on which any region of the sheet is refused, at each read.

## Statements

Drafted from P46 by the lane's rule: each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold on P46, and passes in both halves of P46. SD_block is the larger of the SD over P46's four block values and the SD over its 32 cases divided by √8.

The candidates, each against NL002's arbiter-off arm at the same gain and on the same draws:
- **the repair is kept:** with the arbiter, the faithful copy repairs coherent region damage (R), and loses at most a little against the arbiter off;
- **the wrong references no longer overwrite:** with the arbiter, the foreign and corrupt references keep A's specificity in intact tissue, where the arbiter-off arm overwrites;
- **at one gain:** both at 0.75 × KC, in the stores and in the body;
- **the faithful code's cost:** the false refusals and the alignment cost where nothing is wrong;
- **the history crosses:** the record-only successor of the protected branch keeps A's specificity;
- **the blind spot:** inside a killed square the anchors are gone, and the arbiter cannot protect there;
- **the information limit:** the change event's identity.

Every part is computed on P46 by the reader before the thresholds are drafted.

## The price (from NL002's development timing, before any NL003 run)

- **NL002's development:** 32 tasks, 1,115 CPU-s a task on average. The tissue took 427 s (dw) and 185 s (none) for 63 labels; the successors 752 s and 980 s for 129 recipients.
- **NL003:** about 80 tissue labels and 213 recipients a task, about 1.3 and 1.65 times NL002's, plus the gate's arithmetic. That is about 1,900 CPU-s a task.
- **The development:** 32 tasks (2 units × 16 blocks), about 17 CPU-hours (the cap is 30), about 1.6 h of wall on 12 workers. Q9 forecasts it from the debug run.
- **Phase A, against its cap of about 10:**

  | Item | CPU-hours |
  |---|---|
  | The smoke | 0.3 |
  | The tuning (8 tasks, no successors) | 0.6 |
  | P46 (8 tasks) | 4.3 |
  | The debug run (4 tasks) | 2.1 |
  | Q1–Q10 | about 1.5 |
  | In all | about 9 |

## Decisions, with reasons (for the lead's review)

1. **The surround (the lead's ruling asked).** The brief names AR002's coherence rule with an agreeing surround. At the region scale the templates show that rule would refuse about 3% of a wrong reference's regions. So it is a candidate in the tuning rule, beside the same rule without it, and the rule chooses. If the lead rules that the surround stays, the arbiter is registered with it, and the no-surround rule is reported as a side arm.
2. **No evidence admits** (a veto, not a licence). This is the brief's "refused where a coherent island of anchors contradicts it". The cost is the blind spot inside a killed square, which is registered.
3. **Live anchors as AR002's,** with the code's target defined there: the record confident, the anchor present, σ ≠ 0.
4. **L2 only is gated,** since every reference's L3 is A's.
5. **The anchors hold A's acquired record signs** at density 1/4 (AR001, AR002). Density 1/16 and GC001's misread are side arms.
6. **K removes the anchors** in the killed square (AR001's shared damage). The codes are kept (NL002).
7. **own, k2 0.25 and k2 2 are dropped** for the price. The arbiter-off change event is not run (it is the none event).
8. **The successors:** NL002's two unchanged, plus a gated coded recipient for the arbiter-on labels.
9. **Identities** as the lead assigned them (below), re-scanned by fork N3.

## Identities (assigned by the lead at about 20:14Z)

| Use | Blocks | Tag | Purpose |
|---|---|---|---|
| Tuning (P46a) | 900430–900433 | mse-p46 | engineering |
| P46 (probe) | 900488–900491 | mse-p46 | engineering |
| Preflight | 900492–900493 | mse-nl003 | engineering |
| Debug | 900494–900495 | mse-nl003 | engineering |
| Smoke and tests | 900496–900497 | mse-nl003 | engineering |
| Spare | 900498–900499 | | |
| Development | 910746–910751, 910753–910758 and 910762–910765 (16 blocks) | mse-nl003 | development |
| Reserve | 910867–910871 | | |

## The tuning's outcome (P46a, 20:33:17–20:39:43Z; `probes/results/p46a_nl003_arbiter_tuning.txt`) and the question for the lead

**The declared rule chose T3q0.75r2** (n 3, q 0.75, AR002's surround), the largest S (0.292) among the 6 feasible candidates. It barely arbitrates. At 0.75 × KC, the foreign reference's specificity is:

| Unit | Arbiter off | The declared choice |
|---|---|---|
| Body | −0.493 | −0.466 |
| Stores | −0.418 | −0.381 |

All six surround candidates are like it, as the templates predicted (3% of the differing regions are isolated).

**Why every rule without the surround was excluded:**
- **The faithful copy is refused in the body.**
  - Its refused share in intact tissue is 0.05–0.12 in the body, against the cap of 0.02; in the stores it is 0.
  - In the developing body the record's bonds relearn from a body that erodes A's minority cells. So the faithful region code, applied in the eroded gauge frame, contradicts A's acquired anchors in some regions.
- **Refusing it there helps.** The copy's alignment with A rises by +0.024 to +0.048 against the arbiter-off copy, but the alignment constraint was two-sided (|align| ≤ 0.01), so it excluded that gain as well.
- **Repair is kept** by every candidate: within +0.000 to +0.016 of the arbiter-off copy.

**What the rules without the surround do** (spec of the foreign and corrupt references at 0.75 × KC):

| Rule | Foreign, stores | Foreign, body | Corrupt, stores | Corrupt, body |
|---|---|---|---|---|
| Arbiter off | −0.418 | −0.493 | +0.236 | +0.247 |
| n 1, q 0.75 | +0.993 | +0.690 | +0.994 | +0.820 |
| n 2, q 0.75 | +0.934 | +0.610 | +0.961 | +0.779 |
| n 3, q 0.75 | +0.758 | +0.477 | +0.872 | +0.703 |

Under q 1 the body's values are lower: +0.405, +0.323 and +0.175 for the foreign reference at n 1, 2 and 3.

**The options (fork N3 stopped here, before P46, as the brief asks):**
- **A. Keep the declared choice** (T3q0.75r2). NL003 would then register that AR002's coherence rule with its surround cannot arbitrate at the region scale: a negative result, largely foreseeable from the templates.
- **B. Amend the constraints before P46,** and let the declared objective choose.
  - The constraints would bound the faithful copy's cost, one-sided: alignment no worse than the arbiter-off copy's by more than 0.01, and repair no worse by more than 0.01.
  - The false-refusal cap would be dropped and the refused share reported, since a refusal of the faithful code in the eroded body can be right.
  - The tuning blocks are engineering, and P46 and the development stay fresh.
  - **Choice: T1q0.75r0** (n 1, q 0.75, no surround; S 0.921; the next is T2q0.75r0 at 0.886, outside the tie of 0.005).
- **C. As B, keeping AR002's evidence threshold n ≥ 2** (det's n 2), so that a single anchor never vetoes a region code.
  - **Choice: T2q0.75r0** (S 0.886).
  - It is more robust to a single misread anchor, at some cost: the foreign reference's specificity is +0.934 in the stores and +0.610 in the body, against B's +0.993 and +0.690.
- **D (with B or C):** the declared choice, the surround rule, kept as a reported side arm (`Asur`, planned), so NL003 also measures the surround's blindness.

**Fork N3's recommendation:** B with D. It is the declared objective with its constraints corrected, and the misread side arm measures n 1's fragility. C is the conservative alternative.

## Amendment 2 to the tuning rule (the lead's ruling, 20:46:04Z on 31 October 2026, after the tuning's values were read and before P46)

**The lead's ruling: B with D.**
- **The reason** (the lead's words, in short): the constraints existed so that the faithful code keeps its work. A two-sided alignment bound, and a cap on refusals that raise alignment, counted a gain as a cost. That was a mis-specification against the constraints' own purpose.
- **The constraints become one-sided,** in both units:
  - the faithful copy's alignment with A in intact tissue no worse than the arbiter-off copy's by more than 0.01;
  - its repair (R) no worse by more than 0.01.
- **The refused share is reported, not capped.**
- **Unchanged:** the objective, the candidates, the blocks and the tie-break.
- **The rule then chooses T1q0.75r0** (n 1, q 0.75, no surround; S 0.9208), against T2q0.75r0's 0.8860, outside the 0.005 tie.
- **The record stays:** the first rule's choice (T3q0.75r2) and every candidate's values remain in p46a's results, which now also print the amended rule's choice.

**Two reported arms,** not registered:
- **Asur** = T3q0.75r2, the first rule's choice: it measures the surround's blindness at the region scale.
- **A2** = T2q0.75r0, AR002's n 2: it measures the cost of never letting a single anchor veto a region.

**n 1's fragility, measured:**
- the chosen rule and A2 in the misread side arm (GC001's σ 1 on the anchors);
- the 1/16-density side arm, for the chosen rule and A2;
- in every arm, the refused share of the faithful copy and of each wrong reference.

**The price:**
- The side arms (copy under none and R; foreign and corrupt under none) run in the tissue only, without recipients.
- So phase A keeps to about 10 CPU-hours, and the development stays under its cap of 30 (about 15).

**The ruling's item 4, done before P46** (20:46–21:01Z; `runs/.../nl003/tools/repro_p46a.py`, results repro_none.json and repro_dw.json):
- `nl003/sim.py` with the "ever refused" flag reran P46a's tuning task 900430 in both units and equalled P46a's arrays bit for bit.
- That is every endpoint array (21 in the stores, 34 in the body) and every raw array (14 and 15), with no difference. The flag `t/a/ever` is the only new key.
