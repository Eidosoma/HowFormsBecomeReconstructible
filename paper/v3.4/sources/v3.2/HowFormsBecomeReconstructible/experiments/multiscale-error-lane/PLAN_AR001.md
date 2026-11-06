# PLAN AR001: which source to correct, frozen (DRAFT, phase A)

**30 October 2026, fork A. Approved by the lead after phase A; frozen at 23:20:01Z (REGISTRATION_AR001.md).** The design is the AR001 section of REVIEW_V25_NEXT_EXPERIMENTS.md (the v2.5 review's experiment 6; the lane's ME002–ME004 question), built on the PI's "sounds good as you see fit on the order and most important" and "sounds good, keep going great job :)", relayed by the lead.

## The question

The body, the record and the cue can disagree. Can a frozen controller choose what to correct better than the best fixed policy, at the same resource ceiling, when it is not told which source is wrong? It has a regime signal of declared reliability, and the evidence may arrive late.

## What is built

**The tissue** is BE006's at its calibrated clock SL, imported unchanged:
- LR004's record of relations read by DL001's bodies at gain 0.2, after DL002's acquisition;
- the positional cue: anchors at a quarter of the cells, holding the acquired record's signs;
- BE001's 32 × 32 sheet;
- every bond's Hebbian rate at 3 × 10⁻⁴, with the bond noise scaled with it (3 × 10⁻⁵): CALIBRATION.md's clocks at τ_m = 300 updates an hour, T\* = 1,959 updates (6.5 h).

One event at t = 0 on a 4 × 4 patch, then 8,000 updates (26.7 h), scored at t = 8,000.

**Seven situations** (LR005's, plus correlated errors):

| Situation | What happens | Which source is right |
|---|---|---|
| none | nothing | all |
| body | the body flipped in the patch | record and cue |
| memory | the record flipped, consistent bonds | body and cue |
| correlated | the body and the record both flipped | the cue only |
| shared | the patch's cells killed with everything they held | none inside; the surroundings |
| cue | a quarter of the anchors flipped, scattered | body and record |
| change | the patch's anchors flipped | the cue, if the change is legitimate; body and record, if it is coherent corruption |

The change run is scored twice: against the new target (a legitimate change) and against the old one (coherent cue corruption). That is the information-limit pair: identical observations, different correct answers. So there are eight scorings.

**Eight policies,** all at the same clock, rate, bond noise, pull and window (the resource ceiling):

| Policy | Corrects | From |
|---|---|---|
| inactive | nothing | — |
| record | the body | the record, which keeps itself (record+parity, LR001) |
| body | the record | the body (LR002) |
| vote | the record | the majority of the body and two records (LR004) |
| arbiter | the record | the body where body and record agree; the cue at an anchor where they disagree; else the record (LR004) |
| latch | the record | the cue where at least half the live anchors within 3 sites disagree, held 15,000 updates (LR005's community-s at the calibrated commitment) |
| rest | the record | BE001's detector at λ = 3 with the calibrated commitment: the controller without its signal |
| dial | the record | the controller: BE006's dial-SL, closing the footprint's junctions to λ = 1 while the regime signal is on (updates 1–1,000) |

**The bridges, bit for bit** (checks Q3; tested):
- rest and dial equal `be006.sim.run`'s never-SL and dial-SL;
- at the lane's clock on an 8 × 8 patch with the latch's hold at 300, record, body, vote, arbiter and latch equal `lr005.sim.run`'s record+parity, body, vote2r, cue and community-s.

**The signal's reliability** is declared as a hit rate h and a false-alarm rate f.
- **p = h** when re-specifying the patch to the cue is right: memory, correlated, and the change scored as legitimate.
- **p = f** in every other scoring.
- Every case is simulated with the signal on (dial) and off (rest) on paired draws, so the controller's expected score is exact: p u(dial) + (1 − p) u(rest). No signal draw is simulated. The fixed policies never read the signal.

**The utility** U is the mean of the record's agreement inside the patch over the eight scorings, with equal weights (declared now, for the confirmation too). **The harm bound** is a sham's cost to the whole sheet: r_all(rest) − r_all(dial) with no event and under scattered cue damage.

**The information-limit identity (derived).** In the patch the new and old targets are exact inverses, so for every branch u(new) + u(old) = 1 exactly. Every policy, the controller with an uninformative signal (h = f) included, ties on the pair. Only h > f can win there, by (h − f)(u_on − u_off).

**Side arms, on the controller only.** The fixed policies never read the signal, so their outcomes are the main grid's.
- **Timing:** the signal at 0.5, 1 and 2 T\* in every situation.
- **Precision:** the footprint shifted by 4 or 6 sites (half the patch, none of it), or the patch dilated by 0 or 8 instead of 2, in memory, change and cue.
- **Misread cues:** GC001's quenched misread (σ = 1) in none, memory and change, for the four policies that read the cue (arbiter, latch, rest, dial).

## Trims (each to the caps, reported)

1. **Eight unit-body pairs, not twelve:** S4 and F0 at θ × 0 and × 1, with dw and li4. LB was dropped.
2. **vote3 and community-c were dropped.** LR005 found the three-way vote behaves like the cue arbiter, and community-c is the latch's cautious setting.
3. **"After execution" and "after a reset" were not run.** BE007 and BE010 established them in this tissue at this clock: a signal after execution does nothing, and decommitment reopens the window. The fixed policies have no commitment to execute or clear, so these timings offer no shared comparison. Named next steps.
4. **One read gain (0.2) and one patch size (4 × 4),** BE002's dial regime.
5. **The latch's hold is the calibrated commitment (15,000), not LR005's 300.** At this clock a 300-update commitment lapses before the decision is written (BE006 K6–K8), so 300 would handicap the latch.
6. **The controller is not tuned in AR001.** It is BE006's dial-SL as built; the development measures it.

## Identities (scanned free over the lane and its run roots, ranges expanded)

| | Blocks | Tag |
|---|---|---|
| Probe P41 | 900025–900028 | mse-p41 |
| Preflight | 900029–900030 | mse-ar001 |
| Debug and tests | 900031–900032 | mse-ar001 |
| Development | 910528–910543 | mse-ar001 |
| A later confirmation (reserved, not drawn) | 920000 onward, its count set from the development's block variance | |

## Costs

**The smoke** (`probes/p41s_ar001_smoke.py`, debug block 900031, the full 8,000 updates and every run, digest 051af4cc7450):
- li4 × S4_t1 took 914.7 CPU-seconds, and dw × F0_t0 811.5, for 92 arm-runs of 8 cases.
- That is 8.5–10.5 s an arm-run; the dial arms cost a little more (the sparse LU while the signal is on).

**Trimmed after the smoke:** timing arms in every situation (101 arm-runs) would have put P41 at about 8.4 CPU-hours, over its cap. The timing arms are kept in memory, correlated, change and cue (92 arm-runs). In none, body and shared the prompt sham cost nothing measurable in the smoke.

**Actual:** P41 took 24,995 CPU-seconds (6.94 CPU-hours) for 32 tasks under a 1-minute load of 26–42. The debug run took 9,655 CPU-seconds (2.68 CPU-hours) for 16 tasks.

**Forecasts** (about 860 s a task):
- P41, 32 tasks: 7.7 CPU-hours.
- Preflight and debug, 16 tasks each: 3.8 CPU-hours each.
- Development, 128 tasks: about 31 CPU-hours, 2.6 h on 12 workers.
