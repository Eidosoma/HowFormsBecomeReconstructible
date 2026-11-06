# AR006 plan: guard only the tolerance

Fork A3, 3 November 2026, on the PI's "go with your recommendations" (about 12:25Z, relayed by the lead). AR005's next step 1. Written and committed before any AR006 run; no AR006 value exists.

## Why

**AR005** (REPORT_AR005.md; 16 development blocks) made vguard: DET_POOL plus the body check g-body-f05.
- **Scattered false alarms removed:** under scattered cue damage vguard costs the sheet +0.0025 [+0.0019, +0.0031], against vpool's +0.0193 and the confirmed 0.01.
- **The misread recovery kept:** +0.0988 over vms at 4 × 4 and 8 × 8, 0.86 of vpool's +0.1147.
- **Its blind spot is damage the body shares.** In correlated damage vguard trails vms by −0.331 at σ 0 and −0.109 at σ 1, though it stays above the vote.

vms's DET_STAR fires unguarded at update 1 on correlated damage and repairs it. The body check was applied to every window, including the windows DET_STAR alone would have held, and those needed no second source.

**AR006 asks:** if only the tolerance is guarded, does one controller keep all of these together?
- vguard's protection against scattered damage;
- vpool's misread recovery;
- vms's repair of correlated damage.

Guarding only the tolerance means the windows that pooling adds need the body's confirmation, and DET_STAR's own windows fire as in vms.

AR006's frozen policy is the one later end-to-end tests are meant to carry, so it is built to be confirmable (below).

## The controller, vtol, and what it implies (derived before any value)

DET_STAR (vms's) and DET_POOL (vpool's) are identical except for the surround: ring_max 0 against 1. Both use boxes 2–12, n 3, q 1, a ring of width 2 and dwell 1. So at every box and update, every window DET_STAR holds, DET_POOL holds too: W₀ ⊆ W₁. Let B be the windows the body confirms (g-body-f05: the confident body disagrees with the record at half or more of the window's disagreeing live anchors). Then at every box:
- vms holds W₀;
- vpool holds W₁;
- vguard holds W₁ ∩ B;
- **vtol holds W₀ ∪ (W₁ ∖ W₀ ∩ B) = W₀ ∪ (W₁ ∩ B).** DET_STAR's windows fire unguarded, and the windows pooling adds need the body. The vote is the default.

So **vtol's windows are exactly vms's united with vguard's**, and lie within vpool's. Every vote-default arm is the vote until its own onset, so before any fires they all read the same state. Two consequences follow.
- **The onset.** vtol's onset is the earlier of vms's and vguard's, and never earlier than vpool's.
- **The branch.** Per case, vtol's branch is one of four:
  - the vote's, where neither vms nor vguard fires;
  - vms's, bit for bit, where at vtol's onset only DET_STAR windows hold;
  - vguard's, bit for bit, where only guarded pooled windows hold;
  - a union branch, where both hold, with the zone the union of the two.

Expected by situation:

| Situation | vms | vguard | So vtol |
|---|---|---|---|
| memory, σ 0 | fires at update 1 on the injury | fires on it too (the body is right) | ≈ vpool ≈ vms; R0 near 0, not below vms (vtol ⊇ vms) |
| memory, σ 1 | loses windows to misread anchors | keeps them where the body confirms | at least vguard's recovery in detection, at most vpool's |
| cue@0 (scattered) | chance windows fire unguarded (+0.0056 on AR005's development) | rarely fires (+0.0025) | about vms's cost plus part of vguard's: about +0.006 to +0.008, within 0.01 but with less room than vguard |
| none@0 | | | about 0 |
| none@1 | DET_STAR fires on misread walls (+0.0040) | pooled-only windows need the body, which agrees (+0.0010) | about +0.004 to +0.005, within E9's 0.01 |
| correlated@0 | fires at update 1 on the shared error | mostly rejected there (the body agrees) | fires as vms, mostly on vms's branch exactly: not worse than vms, far above vguard (+0.33 on AR005's values) |
| correlated@1 | DET_STAR loses windows to misreads | the pooled-only windows are rejected (shared error) | about vms (above vguard, below vpool) |
| body@0 | no anchor disagrees with the record | no window | none-like; AR005 measured every arm at the vote's score there |

**No tuning stage.** The derivation leaves no free choice:
- DET_STAR, DET_POOL and g-body-f05 (f 0.5, from AR005's tuning) are frozen;
- the split, guarding the windows pooling adds and only those, is the lead's design.

## The arms and the machinery

| Arm | What it is |
|---|---|
| vote | BEST, AR001's; σ 0 runs only |
| vms | AR003's frozen DET_STAR with the vote default |
| vpool | AR004's frozen DET_POOL with the vote default |
| vguard | AR005's frozen DET_POOL plus g-body-f05 |
| **vtol** | **DET_STAR's windows unguarded, united with DET_POOL's further windows confirmed by g-body-f05; the vote default** |

**The machinery is AR005's, imported unchanged** (ar005, and through it ar004, ar003, ar002 and ar001). The one new piece is the split guard, in `ar006.sim`.
- **Its windows function** handles the split, and delegates every other guard to `ar005.sim.guarded_windows`. It reuses AR002's integral-image counts once for W₀, W₁ and B.
- **`ar006.sim.detect`** is `ar005.sim.detect`'s own source with its one windows call routed through that function.
- **`ar006.sim.run_vt`** is `ar003.sim.run_vd`'s own source with its detector call routed to `ar006.sim.detect`, derived by `ar005.sim.derive` as AR005 did.
- **The task** is `ar003.worker`'s, routed the same way.
- For the vote, vms, vpool and vguard all of this is AR005's arms bit for bit (the bridge).

## The runs

The statements' size means are over 4 × 4 and 8 × 8, as in AR005. The vote never reads the cue, so its σ 1 value is its σ 0 run's.

**The registered set** (the debug run, the preflight and the development), 32 arm-runs a task:

| Run | Arms |
|---|---|
| memory@0 at 4 and 8 | vote, vms, vtol |
| memory@1 at 4 and 8 | vms, vpool, vguard, vtol |
| none@0 | vote, vms, vtol |
| none@1 | vms, vtol |
| cue@0 | vote, vms, vpool, vtol |
| correlated@0 | vote, vms, vpool, vguard, vtol |
| correlated@1 | vms, vpool, vguard, vtol |

**P57, the pilot** (four engineering blocks, two halves; tag mse-p57; the parts with thresholds only), 23 arm-runs a task:

| Run | Arms |
|---|---|
| memory@0 at 4 and 8 | vote, vms, vtol |
| memory@1 at 4 and 8 | vms, vpool, vtol |
| none@0 | vote, vtol |
| none@1 | vtol |
| cue@0 | vote, vtol |
| correlated@0 | vms, vguard, vtol |
| correlated@1 | vms, vguard, vtol |

**The bridge:** AR005's registered runs of those nine situations and sizes, with AR005's arms and vtol, on AR005's debug block 900799 under AR005's tag, for li4 × S4_t1 and dw × F0_t0. That is 41 arm-runs a task. The vote, vms, vpool and vguard must equal AR005's own debug outputs there bit for bit.

**The split guard's arithmetic** is checked on synthetic and random states: its windows equal DET_STAR's windows (`cue_windows_multi`) united with the guarded pooled windows (`ar005.sim.guarded_windows`), at every box.

**Trims (each reported):**
- 2 × 2 is not run. A 2 × 2 patch holds about one anchor, below n 3. AR005 measured it uninformative: +0.0085 [−0.0051, +0.0222] for vguard against vms at σ 1.
- body@0 is not run. No anchor disagrees with the record there, so it is none-like for every cue detector, and AR005 measured every arm at the vote's 0.990.
- vpool and vguard run only where a statement or a direct comparison needs them.

## Statement candidates (derived before any value; thresholds from P57 by the lane's rule)

The primaries are K1, K3 and K5: the cost, the recovery, and the blind spot resolved.
- **K1 (primary):** under scattered cue damage vtol's false alarms cost intact tissue within the confirmed bound: r_all(vote) − r_all(vtol) in cue@0 ≤ 0.01.
- **K2: no event.**
  - (a) none@0 cost ≤ 0.002, the confirmed bound;
  - (b) none@1 cost, against the vote's none@0, ≤ 0.01, AR003's E9 bound.
- **K3 (primary): the misread recovery over vms.**
  - (a) R1 = (1/2) Σ over L = 4, 8 of [u(vtol, memory@1, L) − u(vms, memory@1, L)] at least a floor;
  - (b) its share of vpool's: R1(vtol) − k R1(vpool) ≥ 0, with k the largest twentieth the rule allows.
- **K4: clean-read hits kept against vms.** R0 = (1/2) Σ over L = 4, 8 of [u(vtol, memory@0, L) − u(vms, memory@0, L)] at least a non-inferiority threshold.
- **K5 (primary): the blind spot resolved.**
  - (a) in correlated damage at σ 0, u(vtol) − u(vms) at least a non-inferiority threshold;
  - (b) its gain over vguard there, u(vtol) − u(vguard), at least a threshold;
  - (c), (d) the same two at σ 1.
- **K6: under misreads it still beats the best fixed policy.** W1 = (1/2) Σ over L = 4, 8 of [u(vtol, memory@1, L) − u(vote, memory@0, L)] at least a threshold.
- **K7: nothing given up with no event.** u(vtol) − u(vote) in the 4 × 4 patch at none@0, and at none@1 against the vote's none@0, each at least a non-inferiority threshold.

**The rule** (AR005's):
- Each part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold on P57, and passes in both halves. SD_block is the larger of the block SD and the case SD / √8.
- The thresholds are the strictest round values the rule allows:
  - rates in twentieths;
  - contrasts and differences in hundredths, or in 0.005 where the strictest value lies within 0.01 of zero;
  - sheet costs in thousandths;
  - the share k in twentieths.
- The fixed bounds (0.01, 0.002 and E9's 0.01) are kept only if P57 supports them.
- A part with SD 0 takes the declared allowance −0.005 (AR003's E8).
- A part P57 cannot support is dropped and reported, not loosened.
- The reader's intervals use the max rule.

**Reported, not registered:**
- vms's, vpool's and vguard's values in every run where they ran (their costs beside K1);
- vtol's give inside the patch under cue@0;
- the detectors' rates, onsets and footprints;
- the recovery fraction;
- **the branch accounting:** per case, vtol on the vote's, vms's or vguard's branch exactly, or on a union branch, from the saved onsets and zones. This is a check of the derivation.

**A confirmation, AR006C, is declared now** as a separate step on the lead's word after the development, because AR006's policy is meant to be carried forward.
- 16 fresh blocks from the confirmation range 920000–924999.
- Its criteria: the development's primaries (K1, K3 (a), K5 (a)), each with its 95% interval wholly on its side, under AR003C's rule.
- The details are fixed from the development before any confirmation block is drawn.

## Identities

| | Blocks | Tag |
|---|---|---|
| P57 | 900917, 900918 (half 1); 900919, 900928 (half 2) | mse-p57 |
| Preflight | 900929, 900947 | mse-ar006 |
| Debug | 900948 | mse-ar006 |
| Tests | 900949 | mse-ar006 |
| Spare engineering | 900969, 900989 | |
| The bridge | 900799 (AR005's debug block), two tasks | mse-ar005 |
| Development | 925614, 925615, 925616, 925617, 925618, 925619, 925620, 925621 (half 1); 925622, 925624, 925626, 925627, 925628, 925630, 925633, 925634 (half 2) | mse-ar006 |

- **The scan:** fork A3 scanned these free at 12:29–12:31Z on 3 November by the lead's whole-number method over the lane and the run roots (17,115 files): 40 engineering blocks and 787 of 925000–925999 free.
- **The enrolment purpose, disclosed:** the development blocks come from the slice 925000–925999 of the engine's confirmation range, by the PI's decision recorded in ENGINE.md (3 November, about 12:25Z). They are enrolled through `mse.assay.enrol` under the **confirmation** purpose, because the engine's development range is used up and `mse/assay.py` is not edited. Confirmations keep 920000–924999.
- **The halves** are in ascending block order: the first eight and the last eight.
- The engineering blocks lie inside `mse.assay.RANGES['engineering']`.

## Costs

**Caps:** phase A at most 7 CPU-hours (AR005's measured price); the development at most 30.

The price uses AR005's measured costs: about 19 CPU-seconds a vote-default arm-run (it detects every update until it fires), and about 8 for the vote.

**Phase A, about 5.4 CPU-hours:**

| Item | CPU-hours |
|---|---|
| the bridge, 2 tasks of 41 arm-runs | 0.40 |
| P57, 32 tasks of 23 | 3.49 |
| the debug run, 8 tasks of 32 | 1.23 |
| Q1–Q10 | about 0.21 |
| tests and readers | about 0.1 |

If the running projection passes 7, fork A3 stops and reports.

**The development:** 128 tasks of 32 arm-runs, about 19.7 CPU-hours (about 21.6 under load). The preflight re-prices it. If that projection passes 30, fork A3 stops and reports before any development block. The first trim, only then and on the lead's word: drop vpool from cue@0 and the correlated runs (context only).

## What each outcome would mean (in brief)

- **K1, K3 and K5 hold:** guarding only the tolerance keeps vguard's protection against scattered damage, most of vpool's misread recovery and vms's repair of correlated damage in one controller. That is the policy for the end-to-end tests to carry.
- **K1 fails:** DET_STAR's unguarded chance windows plus vguard's late ones together pass the confirmed bound. The tolerance cannot be split this way at this damage rate.
- **K5 fails:** the union branches (both windows held at the onset) cost the correlated repair. The split then interferes with what vms does alone.
- **K3 fails against vguard's AR005 value:** the unguarded windows' earlier onsets take the place of the better zones the guarded windows would have given.
