# AR005 plan: a second check against scattered false alarms

Fork A3, 2 November 2026, on the PI's "lets start the two next one in parallel" (about 12:00Z, relayed by the lead). Written and committed before any AR005 tuning value exists. No AR005 run has been made.

## Why

AR004 (REPORT_AR004.md) found a trade-off. vpool is AR004's frozen DET_POOL, pool-n3-q1-r1: DET_STAR with one disagreeing live anchor tolerated in the surround. It is used with the vote default. On AR004's 16 development blocks:
- **The gain:** under GC001's misread (σ 1) vpool wins back +0.0957 [+0.0819, +0.1096] of what misreads cost vms, over the sizes 2, 4 and 8. At 4 × 4 and 8 × 8 alone the figures are +0.1163 and +0.1536. vpool also finds the 4 × 4 injury on the patch about twice as often (0.521 against 0.293).
- **The cost under scattered cue damage:** its false alarms cost the sheet +0.0177 [+0.0153, +0.0200], against vms's +0.0058 and the confirmed bound of 0.01.
- **The cost under misreads with no event:** +0.0078.

To a coherence detector, misread anchors and scattered damage are the same evidence: live anchors that disagree with the record.

**AR005 asks:** can a second, independent check on the pooled detector's firing reject scattered-damage clusters while keeping the misread recovery? The target is three things together:
- the cost under scattered cue damage back within the confirmed 0.01, and within 0.002 with no event;
- the misread recovery kept;
- the clean-read hits kept.

## What each guard can separate (derived before any value)

Notation: the record r, the body V, and the cue at the anchors (aval, at the anchor mask am). An anchor is live where the record is confident (|r| ≥ VMIN = 0.2). It disagrees where its cue differs from the record's sign. Anchors sit at random on a quarter of the sites (lr005.sim.anchor_mask). Scattered cue damage flips a random quarter of the anchors (lr005.sim.scattered). The events:

| Situation | Record in the patch | Body in the patch | Cue | Its disagreeing anchors |
|---|---|---|---|---|
| memory | flipped | right | right | every live anchor in the patch |
| correlated | flipped | flipped | right | every live anchor in the patch |
| body | right | flipped | right | none |
| cue (scattered) | right | right | a quarter of anchors flipped, anywhere | the flipped ones |
| misread (σ 1) | (any of the above) | | each anchor reads at a displaced site | wherever the displacement crosses a wall of the pattern |

**(a) The body as the second source.** A window counts only if the confident body disagrees with the record at a share of at least f of the window's disagreeing live anchors.
- **Memory damage:** the body is right where the record is wrong. AR002 found that the body still disagrees with the record over the whole patch at update 1: det-v, its body channel, fired at update 1 over the whole patch. The window's disagreeing anchors are confirmed, and the guard passes.
- **Scattered cue damage and misread anchors:** body and record agree at the disagreeing anchors, so the guard rejects. This is the separation sought: it is structural, not statistical.
- **Its blind spot, correlated damage:** body and record share the error, so the guard rejects there too. AR002's D6 showed this: det-v found correlated damage on the patch in 0.236 of cases, only near the rim, where the body's coupling blurs the shared flip. vguard should fall back to the vote there and lose vpool's worth. Correlated damage is therefore in the runs at both σ, and its cost is measured (K6).
- **Body damage alone:** no anchor disagrees with the record, so the cue channel holds no window and there is nothing to guard. It is run at σ 0, to show that vguard gives up nothing to the vote there.
- **Its noise floor:** body and record also disagree spontaneously at some sites. det-v fired in 0.395 of no-event cases on 6 or more mismatched cells in a 4 × 4 window. A chance cluster of disagreeing anchors is confirmed only if the body happens to disagree at the required share of its anchors, which is rarer at f = 1 than at f = 0.5.
- **The cost of a strict f:** where the body is not confident (|V| < 0.2, near its walls) it confirms nothing. At f = 1 one such anchor stops a true window.
- **Late firings:** the body follows the record over time (the clock's T\* is 1,959 updates). A firing late in a run may find the body already re-specified. Nearly every firing in AR004 came at update 1 (median onset 1 in every event run).

**(b) Cluster shape.** Under q = 1 (DET_STAR and DET_POOL), a held window's disagreeing anchors are all of its live anchors. Their positions are the fixed random anchor layout, the same whether an injury or chance made them disagree. So the connectivity or density of a held window's disagreeing anchors cannot separate the two structurally.
- **The only handle is selection.** A chance window holds with probability 4^−k for its k live anchors, so the chance windows that hold are those with the fewest anchors for their box.
- **At boxes of 4 and more,** chance windows are sparser than the layout's mean, and a density floor rejects them. It also rejects the sparser half of true windows.
- **At boxes of 2 and 3,** a chance window needs only 3 anchors. That is denser than the layout's mean (3/9 against 1/4), so a density floor cannot reject it.
- **The count:** after the surround, these small windows give about 1.5 held windows a case under cue damage (vpool fired in 0.97 of cue@0 cases on P51). So (b) is predicted to leave most of vpool's false alarms and to cost true windows. One cell of (b) is in the grid, to measure that prediction.

**(c) Persistence.** The quenched misread and quenched cue damage are static: aval and am do not change. Before the dial acts, the record changes only by noise and slow relearning. A window that holds at update t holds at t + 1 alike under an injury, a misread or scattered damage. Persistence therefore separates nothing at the dwells that matter. It is not in the grid.

## The arms

| Arm | What it is |
|---|---|
| vote | BEST, AR001's; σ 0 runs only (it never reads the cue) |
| vms | AR003's confirmed controller, frozen: DET_STAR with the vote default |
| vpool | AR004's frozen DET_POOL (pool-n3-q1-r1) with the vote default |
| **vguard** | **DET_POOL plus one guard, chosen by the tuning (below), with the vote default** |

**The machinery is AR004's, imported unchanged** (ar004, ar003, ar002 and ar001). The one new piece is the guarded detector, `ar005.sim.detect`.
- For every configuration without a guard, it calls `ar002.sim.detect` unchanged.
- With a guard, it runs the same update: the same counts (`ar002.sim.integral`, `window_sums`), the dwell per box, the zone, and `ar002.sim.fire`. One added count by box is the guard's.
- With a pass-all guard (f = 0) its windows equal `cue_windows_multi`'s exactly.
- **The run loop:** `ar005.sim.run_vg` is `ar003.sim.run_vd`'s own source, compiled with its one detector call routed through `ar005.sim.detect`. The substitution is asserted to apply exactly once.
- **The task:** `ar005.worker`'s task is `ar003.worker`'s `one` and `task`, from their own source, with `one`'s single vote-default call routed to `run_vg`.
- For the vote, vms and vpool these are AR004's arms bit for bit (the bridge, Q3).

## The guard grid (three cells, each DET_POOL plus one guard)

| Cell | Guard |
|---|---|
| g-body-f1 | (a): the body disagrees with the record at every disagreeing live anchor of the window |
| g-body-f05 | (a): at half or more of them |
| g-dense-25 | (b): the window holds live anchors at a density of at least 1/4 (k ≥ b²/4) |

The body counts as confident by `lr005.sim.vote_sign`, as in AR002's body channel. Grid order: g-body-f1, g-body-f05, g-dense-25.

## The tuning rule (fixed before any tuning value exists)

**Block 900717, tag mse-p53, 8 tasks, real vote-default arms.** This follows AR004's lesson: eligibility rests on the real arms' sheet costs, not on a proxy. The runs, with every candidate as an arm:

| Run | Arms |
|---|---|
| cue@0 (4 × 4) | vote, vpool, the three candidates |
| none@0 | vote (the reference for none@1) |
| none@1 | the three candidates |
| memory@1 at 4 and 8 | vms, vpool, the three candidates |
| memory@0 at 4 | vms, the three candidates |
| correlated@1 at 4 | vpool, the three candidates |

That is 27 arm-runs a task.

**Eligible:** a candidate must meet all four, on the block's 64 lineage-cases a run:
1. the sheet cost r_all(vote) − r_all(c) under cue@0 is at most 0.0075 (the development's margin to the confirmed 0.01, as AR004's tier 1);
2. the sheet cost under none@1, against the vote's none@0, is at most 0.0075 (the margin to AR003's E9 bound, 0.01);
3. σ 0 hits are kept at 4 × 4: u(c, memory@0) − u(vms, memory@0) ≥ −0.01;
4. the misread recovery Rc = (1/2) Σ over L = 4, 8 of [u(c, memory@1, L) − u(vms, memory@1, L)] is positive.

**The choice (VGUARD):** the eligible candidate with the largest Rc, ties within 0.005 going to the grid's order.
- **If none is eligible: STOP and report to the lead.** There is no fallback: the study's target is the cost.
- The correlated cost under misreads, u(vpool, correlated@1) − u(c, correlated@1), is reported for every candidate. It is measured, not an eligibility condition.
- 900718 and 900719 are held for a second tuning stage only on the lead's word. They are not drawn otherwise.
- Every candidate and value goes to `probes/results/p53a_ar005_guard_tuning.txt`. The choice is written into `ar005/design.py` before P53 runs.

## The runs

The sizes are 2, 4 and 8. The statements are over 4 and 8 only, and 2 × 2 is reported. A 2 × 2 patch holds about one anchor, below the cue channel's n = 3, so no cue detector acts there from the patch alone. AR004's development measured R1 at 2 × 2 at +0.017 [−0.001, +0.036].

**P53, the probe** (4 blocks, tag mse-p53; the parts with thresholds only), 22 arm-runs a task:

| Run | Arms |
|---|---|
| memory@0 at 4 and 8 | vote, vms, vguard |
| memory@1 at 4 and 8 | vms, vpool, vguard |
| none@0 | vote, vguard |
| none@1 | vguard |
| cue@0 | vote, vguard |
| correlated@0 at 4 | vote, vpool, vguard |
| correlated@1 at 4 | vpool, vguard |

**The registered set** (the debug run, the preflight and the development), 43 arm-runs a task:

| Run | Arms |
|---|---|
| memory@0 at 2, 4 and 8 | vote, vms, vpool, vguard |
| memory@1 at 2, 4 and 8 | vms, vpool, vguard |
| none@0 | vote, vms, vpool, vguard |
| none@1 | vms, vpool, vguard |
| cue@0 | vote, vms, vpool, vguard |
| correlated@0 at 4 | vote, vms, vpool, vguard |
| correlated@1 at 4 | vms, vpool, vguard |
| body@0 at 4 | vote, vms, vpool, vguard |

**The bridge:** AR004's nine registered runs, with AR005's arms (vguard a placeholder, g-body-f1), on AR004's debug block 900265 under AR004's tag, for li4 × S4_t1 and dw × F0_t0. That is 32 arm-runs a task. Against AR004's own debug outputs there, the vote, vms and vpool must agree bit for bit.

## Statement candidates (thresholds from P53 by the lane's rule)

**The rule.** Each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold on P53, and passes in both halves (900729 and 900739; 900749 and 900759). SD_block is the larger of the SD over P53's four block values and the SD over its 32 case values divided by √8.

**Thresholds** are the strictest round value the rule allows:
- rates in twentieths;
- contrasts and differences in hundredths, or in 0.005 where the strictest value lies within 0.01 of zero;
- sheet costs in thousandths;
- the share k in twentieths.

**Fixed bounds** (0.01, 0.002 and AR003's E9 bound 0.01) are kept only if P53 supports them. A part P53 cannot support is dropped and reported, not loosened. The reader's intervals use the same max rule for the SD.

Notation: u is the record's agreement inside the patch at t = 8,000, pooled per case over the eight unit-body pairs. The vote's value under misreads is its σ 0 run's. The sheet cost is r_all(vote) − r_all(arm); for a σ 1 run, the vote's σ 0 run.

- **K1 (the primary):** under scattered cue damage vguard's false alarms cost intact tissue within the confirmed bound: r_all(vote) − r_all(vguard) in cue@0 ≤ 0.01.
- **K2: no event.**
  - (a) none@0 cost ≤ 0.002, the confirmed bound;
  - (b) none@1 cost, against the vote's none@0, ≤ 0.01, AR003's E9 bound. AR004 dropped this for vpool.
- **K3 (co-primary): the misread recovery kept.**
  - (a) R1g = (1/2) Σ over L = 4, 8 of [u(vguard, memory@1, L) − u(vms, memory@1, L)] at least a floor from P53;
  - (b) R1g − k · R1p ≥ 0, with R1p vpool's same contrast and k the largest twentieth the rule allows. This is the share of vpool's recovery kept (as AR003's E5).
- **K4: clean-read hits kept.** R0g = (1/2) Σ over L = 4, 8 of [u(vguard, memory@0, L) − u(vms, memory@0, L)] at least a non-inferiority threshold.
- **K5: under misreads it still beats the best fixed policy.** W1g = (1/2) Σ over L = 4, 8 of [u(vguard, memory@1, L) − u(vote, memory@0, L)] at least a threshold.
- **K6: the correlated-damage cost, measured (the blind spot).**
  - (a), (b): u(vpool, correlated@σ) − u(vguard, correlated@σ) at most an upper bound, at σ 0 and σ 1;
  - (c): u(vguard, correlated@σ) − u(vote, correlated@0) at least a non-inferiority threshold at both σ. vguard's fallback is the vote.
- **K7: where nothing needs correcting it gives up nothing to the vote.** u(vguard) − u(vote) in the 4 × 4 patch at none@0, and at none@1 against the vote's none@0, each at least a non-inferiority threshold.

**Reported, not registered:**
- vms's and vpool's values everywhere (their cue@0 costs beside K1);
- u(vguard) − u(vote) inside the patch under cue@0;
- body damage at σ 0;
- the 2 × 2 size;
- the detectors' rates, onsets and footprints;
- the recovery fraction.

**No confirmation is declared.** A confirmation could follow on the lead's word, declared then from the development.

## Identities (approved by the lead)

| | Blocks | Tag |
|---|---|---|
| The tuning | 900717 (900718–900719 held, drawn only on the lead's word) | mse-p53 |
| Probe P53 | 900729, 900739 (half 1); 900749, 900759 (half 2) | mse-p53 |
| Preflight | 900779, 900789 | mse-ar005 |
| Debug | 900799 | mse-ar005 |
| Tests | 900817 | mse-ar005 |
| Spare engineering | 900819, 900849 | |
| The bridge | 900265 (AR004's debug block), two tasks | mse-ar004 |
| Development | 910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785, 910786, 910787, 910798, 910799, 910826, 910827, 910958 | mse-ar005 |

- **The scan:** fork A3 scanned these free at 12:09–12:11Z, by the lead's whole-number method over the lane and the run roots (16,294 files). 53 engineering blocks were free, none in a window of 8, and 14 development blocks.
- **910138–910139:** AR004's undrawn reserve, released by the lead at about 12:12Z on 2 November (AR004 closed, no confirmation declared). They are re-checked at the freeze: no file outside AR004's plan and registration may name them.
- **The development's halves,** in ascending block order: the first eight (910138 to 910783) and the last eight (910785 to 910958).
- All blocks lie inside `mse.assay.RANGES` for their purposes.

## Costs

**Caps:** phase A at most 6 CPU-hours; the development at most 30.

The price uses 14 CPU-seconds an arm-run, from AR004's 14.6–14.8 under a load of 40–70.
- **Phase A, about 5.5 CPU-hours:**
  - the bridge, 0.25;
  - the tuning, 0.84;
  - P53, 32 tasks, 2.74;
  - the debug run, 8 tasks of 43 arm-runs, 1.34;
  - Q1–Q10, about 0.25;
  - tests, readers and scans, about 0.1.
- **The guarded arm:** it runs its detector every update until it fires, as any vote-default arm that rarely fires does. Its count adds one integral image to the update.
- **If phase A's spend after P53 projects past 6,** fork A3 stops and reports before the debug run.
- **The development:** 128 tasks of 43 arm-runs, about 21.4 CPU-hours. That is about 2.1 h of wall on 12 workers.

### Amendment, 2 November 2026, 15:34Z: phase A's cap raised to 7 (the lead's ruling, option a)

Written after the bridge and the tuning ran, before any tuning or probe value was read, and committed before the debug run.

1. **The reason, measured.** A vote-default arm that never fires runs its detector every update. That costs about 19.5 CPU-seconds an arm-run, against the plan's 14. The figure comes from the bridge's per-run timings on 900265: AR005's runs cost 20–30 CPU-seconds more than AR004's same runs, all of it the added vguard arm. `run_vg` costs exactly what `run_vd` does. vguard rarely fires under cue damage, with no event, or in correlated damage, by design. This is a price, not a change to the design.
2. **The phase-A ledger, against the new cap of 7 CPU-hours:**

   | Item | CPU-hours |
   |---|---|
   | the bridge (done) | 0.32 |
   | the tuning (done, measured; priced at about 1.12) | 1.22 |
   | P53 | about 3.32 |
   | the debug run | about 1.69 |
   | Q1–Q10 | about 0.25 |
   | the rest | about 0.1 |
   | **in all** | **about 6.9** |

   If the running projection passes 7 at any point, fork A3 stops and reports.
3. **The development's cap stays at 30.** The preflight re-prices the development from measured timings. If that projection passes 30, fork A3 stops and reports before any development block is drawn.
4. **The trim order, named before any value is seen.** The first trim is used only if the preflight's projection passes 30: drop vms from body@0 and from correlated@σ. Those arm-runs are context only, about 3 CPU-hours. Nothing else is trimmed without the lead's word.

## Trims (each reported)

1. **Arms:** the vote, vms, vpool and vguard only. AR004's 6 × 6 side arm is not run.
2. **P53 runs** only the parts with thresholds. Context arms and 2 × 2 come from the development.
3. **The tuning** runs one block, and only the eligibility runs.
4. **Not run:** shared damage, the change pair, and misread strengths other than σ 1.

## What each outcome would mean (in brief)

- **K1 and K3 hold:** an independent second source restores the confirmed bound under scattered damage without giving back the misread recovery, and the trade-off AR004 found is not forced.
- **K1 holds and K3 fails:** the guard buys back the bound by removing the recovery's own windows.
- **K1 fails:** the guard does not separate scattered damage from injuries at these sites.
- **K6** measures what the second source costs where it shares the error.
