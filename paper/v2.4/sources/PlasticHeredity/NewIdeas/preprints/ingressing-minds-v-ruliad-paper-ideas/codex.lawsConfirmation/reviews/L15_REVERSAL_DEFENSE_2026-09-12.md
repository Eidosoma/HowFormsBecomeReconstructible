# D099 — L15: reversing target roles and challenging both patterns

**Date:** 2026-09-12. [Frozen protocol](../protocols/L15_REVERSAL_DEFENSE_V1.md).
Continuation of [D098](L15_EXPOSURE_DEFENSE_2026-09-12.md), whose source,
protocol, code, tests, outputs and completed review remain unchanged.
Current L15 work state `STRESS_TESTED`, whole-law verdict `MIXED as written`.

## Plain-language result

The duration-dependent reference effect **survives target-role reversal**.
Brief exposure leaves the old pattern dominant; sustained exposure writes a
reference favoring the new pattern. Both states rebound after a pulse that
opposes them, in both orderings. Holding exposure writing or disabling the
reader erases the body-side duration effect exactly.

But the **full registered symmetric-defense criterion fails**. Sustained
exposure reaches **80.18% mean new-pattern fidelity** after an opposing pulse
in the original ordering and **79.15%** in the reversed ordering. The latter
misses the frozen 80% mean gate by **.85 percentage points**. It stays failed;
we do not lower the bar, substitute sham, extend recovery or rerun the cohort.

So this is a robust relative reference-writing effect, not a reliably
high-fidelity switch. All 40 qualification gates and 22/23 main criteria
pass; the single failure is `d1_sustained_new_post`. Technical completion and
positive primary evidence do not mean the combined scientific criterion passed.
No scientific setting or criterion changed after freeze.

## What this adds to D098

D098's final pulse opposed the sustained group's new pattern but favored the
brief group's old pattern. D099 gives **every record both pulse directions
and a sham**, and reverses which pattern is old/new within every paired life.
This tests actual old-pattern defense, not just return to old during release.

Direction 0 forms the native left/right old pattern and exposes the tissue
to a top/bottom new pattern. Direction 1 forms top/bottom as old and exposes
it to left/right as new. Formation uses the native `seed_index=direction`
argument for 120 updates: it is not a relabeling or rotation of an already
settled body. Native theta and phase-wise random draws remain the same across
directions; neither is rotated. We test two roles for these two patterns,
not arbitrary target families or universal orientation independence.

Everything else retains D098's declared settings: fixed unprojected native
theta, rho .002, gain .2/on or 0/off, imposed amplitude 1.2, pulse amplitude
.8, and 16x16 noisy voltage-sheet physics. Histories share total age 1000:
old-only; old 980/new final 20; or new all 1000. Cross each with native or
held exposure R writing. V is overwritten before each step, but R reads the
native post-step body rather than being assigned the template.

Only the terminal **2048-byte float64 R packet** carries exposure history
into readout. Public direction fixes the common new-template starting V/EMA;
every record within a direction receives identical V/EMA and native theta.
All readouts write R at .002, including records held during exposure. Nine
main records: six histories plus known-new, known-old and erased R controls.

After 200 unforced release updates, split into toward-old, toward-new and
sham branches. The two pulses are exact opposites on the 128/256 cells where
the patterns differ; neither changes R or theta. Reset EMA=V equally, then
run 80 unforced updates with common draws. Own-pattern opposition is toward-
new for brief-old and toward-old for sustained-new. Absolute fidelity scores
measure cell signs on that disagreement mask, **not success rates of animals**.
Whole-sheet metrics, voltages, R content/amplitude and mismatch are also saved.

Eight main tissues **45000–45007**, two lives each, both directions within
each life. Eight separate qualification tissues **45080–45087**, same layout.
All are retained. Main has 192 exposure histories / 1728 readout futures;
qualification has 576 control readouts and no exposures. Independent sampling
unit is the tissue: 16 paired lives / 32 direction-specific trajectories per
phase are not 32 independent tissues. Technical aliases are not samples.

## Separate qualification: both patterns in both roles

All **40 prespecified gates** passed before main was reserved. For each
direction and known target, mean own fidelity must be >=.8 before and after
opposing pulse, every tissue >=.75; correct-minus-opposite-content R must be
>.2 in every tissue under the **same pulse**. Loss and rebound must each
be >=.10 on average and >=.05 in every tissue. These are unchanged D098
margins, now applied to both target roles and both orderings.

| Ordering | Known reference | Own fidelity before pulse | After opposing pulse/recovery | Minimum post-pulse tissue mean |
|---|---|---:|---:|---:|
| Original | New (top/bottom) | 91.21% | 90.28% | 86.72% |
| Original | Old (left/right) | 88.82% | 86.47% | 78.91% |
| Reversed | New (left/right) | 89.60% | 87.94% | 80.47% |
| Reversed | Old (top/bottom) | 90.53% | 89.50% | 85.94% |

Mean immediate losses are **43.99–47.90 points**, rebounds **42.97–45.95
points**. The smallest tissue-level post-pulse content contrast is **+.71484**.
These constructed records qualify the apparatus; they do **not** demonstrate
learned writing. No target replacement, gate relaxation, dropped case or
qualification/main pooling occurred.
[Qualification summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l15_reversal_defense_v1_qualification_attempt1/summary.json).

## The primary cannot hide a failed reversal

For each direction and pulse, the reader-on response80 new-fidelity contrast is

`(sustained_live - brief_live) - (sustained_held - brief_held)`.

Average equally over the two pulse directions, then the two lives per tissue,
then eight tissues. The **single primary is the smaller of the two direction
means**, not an average of per-life minima. A good original ordering cannot
compensate for a failed reversal. We also report each direction, each pulse,
the paired reversal-minus-original interaction and the equal-direction mean.

The 10,000 bootstrap draws resample whole tissues, preserving both directions,
lives and all paired conditions. Each draw takes the minimum of its two
direction means; report its percentile 95% interval. Secondary intervals are
pointwise, not multiplicity-adjusted; an uncertain direction interaction is
not evidence of equivalence. Mean fidelity gates are not individual guarantees.

## Main results: relative effect and absolute fidelity are different

The primary, the **weaker direction's pulse-averaged duration-writing effect**,
is **+.6437988**, 95% paired whole-tissue interval **[+.5871582,+.7009277]**.
In percentage points of new-pattern sign fidelity: **+64.38 [58.72,70.09]**.

| Ordering | Duration-writing effect | 95% tissue interval | Positive tissues / lives |
|---|---:|---|---|
| Original: left/right old, top/bottom new | +64.38 points | [+58.86,+70.09] | 8/8; 16/16 |
| Reversed: top/bottom old, left/right new | +64.48 points | [+58.86,+70.34] | 8/8; 16/16 |

Every pulse-specific duration contrast is also positive in every tissue/life:
original **+63.72 / +65.04 points** for toward-old / toward-new; reversed
**+64.36 / +64.60**. Thus pulse averaging is not hiding a sign reversal.
Sham contrasts are **+65.67 / +65.97 points**. These are relative new-fidelity
contrasts between histories, not the percentage of cells perfectly repaired.

Paired reversed-minus-original is **+.0977 points**, interval
**[−.6592,+.8301]**, four positive/four negative tissue blocks and eight
positive/eight negative paired lives. There is **no established directional
difference**, not proof of equivalence or orientation invariance. The
equal-direction mean is +64.43 points, interval [+58.89,+70.20]; it is not
substituted for the prespecified minimum. Both directional block/life tables
and all secondaries remain in the [main summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l15_reversal_defense_v1_attempt1/summary.json).

Absolute own-pattern fidelity after each group's **opposing** pulse:

| Ordering and exposure | Defended pattern | Before pulse | After recovery, 95% interval | Tissue means / lives >=80% |
|---|---|---:|---|---|
| Original, brief | Old left/right | 85.30% | 81.74% [76.76%,86.04%] | 6/8; 11/16 |
| Original, sustained | New top/bottom | 81.49% | 80.18% [75.19%,84.38%] | 5/8; 9/16 |
| Reversed, brief | Old top/bottom | 82.91% | 82.47% [77.88%,86.38%] | 5/8; 10/16 |
| Reversed, sustained | New left/right | 83.06% | **79.15% [74.32%,83.40%] — gate failed** | **4/8; 8/16** |

Each interval spans 80%. A passed sample-mean gate in the other three rows is
not a high-confidence population lower bound of 80%; the failed row does not
establish that the population mean must be below 80%. The operational gate is
nevertheless failed, exactly as registered. Recovered sustained tissue means
range **65.63–87.11% original / 64.84–87.89% reversed**. No low-performing
tissue or life is excluded, and the relative advantage remains positive in
each. D098's +68.95-point primary used a different pulse aggregation and a
different cohort; comparing its number to D099 is not a learning-decay test.

## Both states rebound; neither achieves complete sham-relative recovery

| Ordering and exposure | Immediate loss | Rebound by response80 | Opposing-pulse minus sham, 95% interval |
|---|---:|---:|---|
| Original, brief-old | 44.68 points | 41.11 points | −1.42 [−2.10,−.83] points |
| Original, sustained-new | 47.41 points | 46.09 points | −2.34 [−3.13,−1.51] points |
| Reversed, brief-old | 46.68 points | 46.24 points | −2.20 [−3.03,−1.42] points |
| Reversed, sustained-new | 44.43 points | 40.53 points | −2.15 [−3.03,−1.27] points |

Every immediate loss and rebound is positive in all eight tissues and sixteen
lives, for all four groups. This is the missing symmetric disturbance check:
old-state repair no longer relies on a final pulse that favors old. The
sham-relative costs are negative in every original brief/sustained and reversed
brief tissue; reversed sustained has seven negative/one tied tissue. No life
has a positive challenge-minus-sham cost in any group. Recovery is substantial
but incomplete, and drift without challenge still matters.

Controls and record content, retained without retuning:

- **Writing held:** old-only/brief/sustained R packets and their subsequent
  readouts are exact aliases within each direction. **Reader off:** all nine
  records have bit-identical V/EMA paths within each direction, for every
  pulse. Duration effects are zero by construction, not statistical nulls.
- Pulse-averaged sustained live-minus-held writing is **+63.84 / +63.99
  points** (original/reversed); reading on-minus-off is **+29.83 / +31.49**;
  sustained-minus-erased **+26.98 / +28.47**. All are positive in every tissue
  and life in both directions. These interacting controls are not additive
  shares of a biological process.
- Constructed known-new minus known-old gives **+76.27 / +76.03 points**,
  positive in every tissue/life. Known-new after its opposing pulse has
  **88.82% / 87.55%** new fidelity, versus learned **80.18% / 79.15%**.
- Brief exposure has a small residual effect: brief-minus-old-only is
  **+1.39 / +1.61 new-fidelity points**, all tissues positive, all original
  lives positive and fifteen reversed lives positive/one tied. Brief is not
  literally ignored, even though old remains dominant.
- Incoming brief R has **100% old-sign fidelity**, sustained R **100%
  new-sign fidelity**, in both directions. This does not imply perfect body
  expression. Sustained R RMS is **.77603 / .77474**, compared with **1.2**
  for constructed known-new; brief R RMS is **.96602 / .96730**. Amplitude
  and spatial fine structure remain unseparated explanations for the gap.
  No post-result rescaling, longer hold or new threshold is introduced.

## Connection to L15 and stopping point

| Clause or inference | Updated assessment |
|---|---|
| Reference speed affects repair at fixed gain | D097's bounded E5 result remains unchanged; D099 holds rho/gain fixed. |
| Duration can write a reference that later selects a different body pattern | Strengthened **E5** support across both tested target roles, with fresh paired tissues, fixed rulebook and common-body controls. |
| The earlier positive result is only a favorable pulse direction | Not sufficient as an explanation here: both states rebound under opposing pulses, and the duration contrast remains positive under each pulse in each ordering. |
| Direction-robust high-fidelity brief repair and sustained adoption/defense by the full frozen criterion | **Not confirmed in D099**: 22/23 main requirements pass, but reversed sustained post-pulse mean .791504 is below .8. Retain continuous positive evidence and the gate failure together. |
| The two directions are equivalent, or targets are generally interchangeable | **Not established.** Small uncertain interaction is not equivalence; only two human-specified native templates and one substrate. |
| A universal sharp dial separates injury from legitimate experience, or predicts biological adoption | **Not confirmed.** One rho/gain, two durations, full-field forcing, fixed readout background; no semantic usefulness test or biological organism. |

L15 remains **STRESS_TESTED / MIXED as written**. Strongest added wording:
*In this voltage-sheet assay, brief and sustained imposed histories write
references with different effects on a matched body. The duration contrast
survives reversing the two tested target roles and both pulse directions;
old and new states rebound after opposing disturbances. However, absolute
recovery is variable and incomplete, and the full prespecified symmetric
high-fidelity criterion is not met.*

This is within-life engineered reference memory, not autonomous event
selection, blank-body regeneration, repeated carrier-only descent, an evolved
writer, a 64-byte germ result, or an L17/L20 heredity demonstration. The common
readout body is deliberately set to new; natural continuous-body transfer and
other readout backgrounds are not tested. D098's narrower passing criterion
and original E49/E50 failures remain unchanged; D099 does not rewrite either.

**Recommended next: park further L15 simulations and do a docs-only
clause-level closeout**, then consider L19. D097–D099 now separate repair
speed, exposure-written target choice and symmetric defense well enough for
a bounded verdict. Chasing the last .85 percentage point with nearby rates,
amplitudes or longer recovery would answer a tuning question, not validate
the original universal language. A separately controlled record-strength or
new-target-family study remains an optional future mechanism question, not
a queued run. No next experiment or cleanup is authorized or launched.

## Verification and provenance

- **245 tests passed, zero skipped, 34.39 s**: 87 new D099 tests plus 158
  prior L15/D097/D098 tests. Includes full short/disposable replays of both
  phases, actual reversed formation, symmetric pulses, packet-only interfaces,
  wrong-state/metadata/summary rejection, hand-built minimum-of-means inference,
  and failed qualification blocking main reservation. A known saved D098
  block/two-life anchor replays; no original 36-job E49 cohort rerun.
- **316 inputs frozen 15:41:52 UTC**, before either qualification or main
  cohort. Includes D098's 286 main inputs and completed main/qualification
  artifacts, its final review, new scientific files and external test proof.
  Prior provenance exceptions are not broadened; historical files unchanged.
- Checked disposable block **514199**: qualification **4.63 s**, main
  **18.67 s**, including independent replay, aliases, save/reload and summary.
  Conservative forecasts **226.48 s / 338.79 s**; both below 600 seconds.
  Projected total artifacts **188,476,691 B (~179.75 MiB)**, within the
  unchanged 512-MiB allowance plus 4-GiB external reserve.
- Qualification prepared with **322 inputs**, completed **15:43:32 UTC in
  21.48 s**. Main prepared afterward with **344 inputs**, including all 22
  immutable qualification artifacts; main completed **15:45:44 UTC in
  78.15 s**. Both forecasts were below the detachment threshold; both ran
  foreground on at most four CPUs. No scientific change after the freeze.
- Each phase passes 32 full direction-specific life replays using separately
  restated equations/schedules, **zero state discrepancy**, and 288 exact
  technical alias futures. Final output sets contain 19 hashed files plus
  the hash index. Exact signs, state tolerance 1e-10,
  metrics/summary tolerance 1e-12. Shared native physics means no clean-room,
  independent-substrate or E6/E7 claim.
- Post-completion read-only saved audits **fully replayed both phases again**,
  independently recomputed all metrics/paired pools/40 qualification gates
  and 23 main criteria, and checked **322/344 inputs and 19 outputs per phase**.
  Both pass with zero discrepancy. COMPLETE's embedded pre-completion audit
  reports zero final output hashes because the final index is written afterward;
  the saved audits verify 19 per phase. Main's scientific support flag remains
  false, consistent with its failed absolute-fidelity criterion.

Pinned records:

- [Freeze](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/tmp/l15_reversal_defense_v1_attempt1_freeze.json): `32fe6fa01795bcde314faa483ee77644095d4c973e916e1ab48f33f9534f919e`.
- [Benchmark](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/tmp/l15_reversal_defense_v1_attempt1_benchmark.json): `04786d5bb8a099cb3746babe981d8ab71fdd8ce1c4e9abe62ad430ed73a1e92c`.
- [Test proof](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/logs/d099_tests_20260912_v1.xml): `da9c1cb86a675ced82578af0e90150b8fb65dd31d5aa5c147d01881763b917c6`.
- [Qualification COMPLETE](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l15_reversal_defense_v1_qualification_attempt1/COMPLETE.json).
- [Main COMPLETE](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l15_reversal_defense_v1_attempt1/COMPLETE.json): `ecca353384bcd6d45703266c9bfaf92cafe482b2e22c709a5952b4334b24e0a4`.
- [Main manifest](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l15_reversal_defense_v1_attempt1/MANIFEST.json): `a4cf61fcda8a43b071093a32a783f2d5eb92fbb2635568c811231b0efa480b2c`.
- [Main summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l15_reversal_defense_v1_attempt1/summary.json): `d0e3956845b7e47bdb0edd6dd26adac92f3b31051c675b85870556b8fcaf7b2c`.
- [Main verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l15_reversal_defense_v1_attempt1/verification.json), [qualification verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l15_reversal_defense_v1_qualification_attempt1/verification.json).

All new data/outputs/logs/test fixtures/tmp/cache are external under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation`. Only new code/docs here;
old caches and unrelated dirty changes are preserved. At most four CPUs,
numerical threads one, bytecode disabled. No cleanup, commit, retry or wider
law experiment. HEAD at freeze:
`a2e4a7cbeed47d0ecb8d11a2ffb2312634fb6455`.

Main outputs **83,658,434 B (79.78 MiB)**; qualification **25,149,882 B
(23.98 MiB)**. Run metadata **86,636 / 82,879 B**, benchmarks **13,434,131 B**,
test fixtures **8,014,491 B**, plus small external proof/freeze/timing files.
Free external space after execution **7,238,602,752 B (~6.74 GiB)**; unchanged
reserve/allowance. No active simulation, automatic retry, deletion or commit.
Forecasts >600 seconds remain detached with user-owned polling. L21/L24
remain closed/parked for this review round.

Final documentation QA: **761 local links** across the six trackers/new review
resolve. Four Python ASTs, shell syntax, scoped whitespace/header spacing,
six displayed artifact hashes and the 245-test proof pass. All **316 D099,
258 D098 and 169 D095 frozen inputs** remain unchanged. Post-documentation
saved audits pass in **7.59 s qualification / 19.72 s main**, again verifying
322/344 inputs and 19 outputs each; the scientific failure flag is retained.
No new workspace data/bytecode/log/image files this turn. Existing 124 bytecode
files (4,195,796 B) remain untouched. New D099 files total about **100 KiB**,
code/docs only; workspace allocation approximately **13.5 MiB**. No active job.
