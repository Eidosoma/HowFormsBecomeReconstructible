# L23 — Matched edge-phase control, D085

Status: **COMPLETE and independently checked on the user's status request**.
Finished **16:57:36 UTC, 2026-09-10**; first inspection **19:08:50 UTC**.
No polling between detached launch and the user's request.
User approved D084's additional-placement recommendation with “let's go” on
2026-09-10. L23 remains `MIXED`, `STRESS_TESTED`; L22 stays parked at D080.

**Main finding:** the join advantage survives all three matched internal
placements, not just D084's midpoint control. Both absolute composite error
and composition-cost contrasts favor true joins in every block after averaging
the twelve pairs, at both norms and both removals. Raw and pixel errors agree.
Primary CD remains a composition-cost exception across all three phases;
individual paired starts and some interior-only views are also contrary.
This strengthens bounded local join interference, not a universal law,
learned address, independent replication or hereditary-renewal claim.

## Plain-language question

The previous test found that weakening links between the pieces helped more
than weakening the same link pattern at their midpoints. Was that genuinely
about the joins, or partly about choosing that particular comparison position?
Add two positions, one cell to either side of the midpoint, and compare each
separately with the true joins. Link count, connectivity, pieces, instructions,
starting budget and noise stay matched. Retain all pairings, including CD.

This is a targeted challenge to the interpretation, not a new general law or
independent replication. The [protocol](../protocols/L23_EDGE_PHASE_CONTROL_V1.md)
limits the experiment to four diagonal phases, not every possible edge
placement. Global mean coupling remains; local cuts do not fully isolate bodies.

## Implementation and validation

- New [runner](../src/laws_confirmation/l23_edge_phase_control.py),
  [independent checker](../scripts/audit_l23_edge_phase_control_outputs.py),
  [tests](../tests/test_l23_edge_phase_control.py) and
  [four-CPU launcher](../scripts/run_l23_edge_phase_control.sh).
- Uses the frozen [D084 step](../src/laws_confirmation/l23_contact_intervention.py)
  unchanged. Reuses all five saved checker arms; only phases 1/3 at removals
  .5/1 are new. Sixteen old blocks, both norms, all twelve pairs/budgets/readers
  and eight paired starts remain. No fresh independent block or learning.
- Initial **71 tests passed in 17.33 seconds**, synthetic/disposable short
  trajectories only. Artifacts preserved externally at
  `tmp/l23-phase-tests-SBmNZH/`. No failed tests or predecessor changes.
- Added source-record corruption and benchmark preparation guards before
  freeze. **223 scoped tests passed in 45.90 seconds**: 87 new, 90 D084,
  38 D083, six trace-observer and two output-isolation tests. Artifacts at
  external `tmp/l23-phase-regression-OFzSGk/`. No failures or new scientific
  panel effects.
- Initial free space: external **6,600,069,120 bytes (6.15 GiB)**, root
  **8,520,429,568 bytes (7.94 GiB)**. Fixed output allowance one GiB, reserve
  four GiB. Save new fields/statistics only, reusing source files in place.
  No cleanup or deletion.

## Frozen comparison and interpretation

Twenty-four focal rows compare true joins with each of three internal phases,
at both norms/removals: absolute composite advantage and composition-cost
advantage. Eight midpoint rows reuse D084 only and are explicitly marked
source-only. Report all phases separately, all sixteen block means, twelve
pair means and paired direction counts; do not hide a failing phase by averaging.

All absolute normalized/isolated errors and original-arm changes must accompany
cost contrasts. Keep secondary controls, pixel/raw errors, budget and time
strata, and the CD exception. Matched graph topology does not match local
target morphology. No learned address, precise mediation or renewal follows.

The run independently replayed 128 new panels and 64 source anchors,
checking all five snapshots and source-anchor hashes. Only new final V,
checkpoint statistics, diagnostics and state digests are stored. Actual
hashed outputs **627,608,388 bytes (599 MiB)**, all external. The source's
five arms are not a fresh confirmation.

## Timing and handoff

Frozen before timing: five new scientific files and the completed
[D084 review](L23_CONTACT_INTERVENTION_2026-09-10.md).
Full-duration disposable benchmark covers four new arms and two exact
source anchors; no effect reporting. Conservative forecast credits no
four-worker speedup. Any forecast over ten minutes must be detached, with
no child polling until the user requests status. No automatic follow-on.

Benchmark passed **2026-09-10 16:09:29.787223 UTC**, approximately four
minutes attached. All six 300-sweep panels passed independent replay/observers;
the two source anchors also exactly matched frozen D084 snapshot hashes/RNG.
All **541 frozen input hashes** verified before and after; no disposable
effects reported or used for selection.

New-arm compute seconds, phase1-half/phase3-half/phase1-cut/phase3-cut:
**27.694488 / 26.115787 / 26.609759 / 25.940851**. Anchor compute seconds,
join-half/midpoint-cut (including extra D084 forward runs):
**40.573288 / 43.315628**. Save/readback **2.9927753377705812 seconds**,
hash/source checks **30.044688754249364 seconds**. Fixed per-panel estimate
**43.81442426595216 seconds**; conservative forecast
**8,652.458836571313 seconds (144.2 minutes / 2.40 hours)**. No credited
four-worker speedup; this is a planning allowance, not observed main progress.

Immutable preparation pinned and verified **544 inputs**, including benchmark
metadata and both benchmark artifacts. Benchmark data and logs remain external
under the run's benchmark names. The five-GiB starting storage gate passed.

## Detached launch record — user owns polling

Launch **2026-09-10T16:10:46.253318+00:00**, **PID 840497**, CPU affinity 0–3,
at most four workers, one numerical thread each. Conservative planning finish
approximately **18:35 UTC** (144.2 minutes from launch); actual execution may
finish earlier. This is an estimate, not observed main-run progress.

External root: `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation`.

- Run records: `runs/l23_edge_phase_control_v1_attempt1/`.
- User-owned status: `runs/l23_edge_phase_control_v1_attempt1/STATUS.json`.
- Outputs: `outputs/l23_edge_phase_control_v1_attempt1/`.
- Logs: `logs/l23_edge_phase_control_v1_attempt1.{stdout,stderr}.log`.
- Parent handoff log: `logs/l23_edge_phase_control_v1_attempt1.launch.log`.

Only parent preparation/launch metadata was received on the launch turn.
No child process, status, log, marker or scientific output was inspected
until the user's status request at 19:08:50 UTC. No automatic retry, cleanup,
sample extension or later experiment. Completed review follows below.

## Pre-benchmark freeze and QA

All **541 unique absolute input paths** exist, totaling **8,937,602,861 bytes**.
After loading the source engine API, all **45 imported repository modules**
are covered. All **572 local links across nine documents**, shell syntax and
scoped whitespace pass. D084 scientific hashes and completed D083 review
remain unchanged. Workspace **12 MiB**, external free **6,538,133,504 bytes**,
root **8,516,124,672 bytes** after tests. Test artifacts are 8.8/51 MiB external.
The five-GiB starting gate passes; no cleanup or deletion.

Frozen SHA-256 values:

| File | SHA-256 |
| --- | --- |
| Runner | `ff30cb229801e08bf47c9a0286f668c54b86d28de515172e96f996846ac5ce21` |
| Independent checker | `69a747194755c190a54e2104753cbd348aa4395ade79a49eeff8d6a014dec8c7` |
| Tests | `70187724f2db5f08a005426565ee5eea09fdfe701eafb49aa46f37f2ff0efe3b` |
| Launcher | `30f5d70b04bfe260b367161fa1afb4d2d22b0f770da4c83f56f5ce3a0183d155` |
| Protocol | `05e9f6ea2c9c17feaed3dacfc389ff2f70a8b53b1c4d36342dae7b23a32cee30` |
| Completed D084 review | `bebbd7891ebf9bb72ecf011703967ee4219f02c0a02877c00bd847a5d1e5a4fc` |

Do not edit these inputs after timing starts. The disposable benchmark
verifies the complete predecessor hash closure before and after execution.

All sixteen existing D084 block metadata records additionally satisfy the
new checker's frozen source-anchor contract. This read-only check inspected
metadata, not new effects, and did not replay source fields.

## Checklist used for the user-requested status review

First check status/markers; do not restart an unfinished or failed job.
After completion, verify the frozen input/output hashes and saved contract,
read back all sixteen new blocks, independently assemble old/new arms and
check aliases, final-state hashes, endpoint errors/metrics, anchor metadata
and pooled/focal results. The run itself performs full dynamics replay;
do not silently repeat that expensive simulation during a status check.

Report each internal phase separately at each norm/removal, distinguishing
sixteen new focal comparisons from eight source-only ones. Interpret absolute
composite improvement together with isolated-control changes. Keep block and
pair exceptions, including CD, and distinguish standardized results from
raw/pixel-error companions. No single pooled number establishes a general law.

## Completion and independent saved-result verification

Completed **2026-09-10T16:57:36.258640+00:00**, reported execution
**2,803.660417 seconds (46.7 minutes)**, **46.8 minutes after launch**.
All sixteen blocks complete; COMPLETE present, FAILED absent, stderr empty.
The conservative 144.2-minute estimate was not a live progress prediction.

A read-only **72.850663-second** status audit verified all **544 input/36
output hashes**, exact contracts/manifests/status, the complete predecessor
closure, all sixteen saved new blocks and their nine-arm provenance/aliases,
**128 new final-V hashes and independently reconstructed errors/metrics**,
**64 source-anchor metadata/snapshot-hash bridges**, saved pooled summaries
and every focal distribution. No new dynamics were run. Full independent
replay of **192 panels / 960 V/EMA/R checkpoint batches** happened during
the original execution; the status audit does not claim to repeat it.

Maximum recorded replay discrepancy **4.5285997174460135e-13**, below 1e-10.
Zero inactive V/template variance flags. Prior **223 scoped tests** stand;
no frozen scientific input or completed D084 review changed. Outputs occupy
599 MiB external; workspace 12 MiB. At inspection, external free
**5,880,877,056 bytes (5.5 GiB)**, root **8,214,179,840 bytes (7.6 GiB)**.
Maximum four CPUs; no new data files, cleanup, retry or further launch.

## All twenty-four focal outcomes

Checker4, matched mean, sweep 300, all twelve pairs, whole-region standardized
error. Positive favors joins. Each row below contains both focal outcomes;
brackets give the observed sixteen-block range, not confidence intervals.
**Every outcome has 16 positive / 0 tied / 0 negative block means.**
The final column counts negative observations among 1,536 paired
block/pair/start cases, absolute/composition; ties are zero, positives are
1,536 minus the displayed count. Starts/pairs are not independent blocks.
Phase **2 is source-only**: its eight outcomes reuse D084, not new confirmation.

| Norm | Removal | Phase | Absolute advantage [block range] | Composition advantage [block range] | Negative paired cases A/C |
| --- | --- | --- | --- | --- | --- |
| .15 | .5 | 1 | .061642 [.056061, .068559] | .032531 [.029152, .036023] | 16 / 158 |
| .15 | .5 | 2 | .061857 [.056549, .070139] | .035008 [.032696, .037636] | 22 / 198 |
| .15 | .5 | 3 | .061380 [.056817, .068604] | .031351 [.027624, .035022] | 28 / 207 |
| .15 | 1 | 1 | .144861 [.136079, .157268] | .074672 [.070699, .078458] | 5 / 108 |
| .15 | 1 | 2 | .146026 [.134730, .161616] | .080293 [.073640, .086438] | 11 / 130 |
| .15 | 1 | 3 | .141135 [.133552, .153518] | .069014 [.064848, .074489] | 16 / 168 |
| .30 | .5 | 1 | .044543 [.039967, .048689] | .024728 [.021615, .026850] | 2 / 126 |
| .30 | .5 | 2 | .037370 [.033077, .042766] | .022990 [.019295, .024561] | 27 / 140 |
| .30 | .5 | 3 | .042294 [.039064, .045711] | .024128 [.023192, .025690] | 32 / 127 |
| .30 | 1 | 1 | .093139 [.084701, .099844] | .047633 [.043644, .053399] | 3 / 105 |
| .30 | 1 | 2 | .072904 [.064624, .080185] | .043380 [.037046, .047064] | 31 / 145 |
| .30 | 1 | 3 | .088556 [.080225, .096445] | .049162 [.043842, .053162] | 27 / 88 |

All twelve absolute-advantage pair means are positive in every condition.
Composition advantage has eleven positive pair means and one negative, CD,
at the primary norm; all twelve pair means are positive at the secondary norm.
The full sixteen-block and twelve-pair means, exact ranges and paired counts
for every outcome are retained in the checked
[analysis](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l23_edge_phase_control_v1_attempt1/analysis.json).

## Absolute errors: not merely a damaged comparator

Matched endpoint averages, N = normalized composite, I = same-arm virtual
isolated halves. Original/join/midpoint rows reuse D084. NSE and pixel error
are lower-better; recognition is higher-better. These are absolute errors,
not percentages of relative improvement.

| Norm | Arm | NSE N | NSE I | Pixel error N | Recognition N |
| --- | --- | --- | --- | --- | --- |
| .15 | original | .370087 | .332576 | .171242 | .911241 |
| .15 | join_half | .321678 | .313756 | .141055 | .972982 |
| .15 | phase1_half | .383320 | .342867 | .180763 | .937337 |
| .15 | internal_half | .383535 | .340605 | .182266 | .938368 |
| .15 | phase3_half | .383058 | .343785 | .180216 | .946940 |
| .15 | join_cut | .279533 | .306672 | .112574 | .996419 |
| .15 | phase1_cut | .424394 | .376861 | .202840 | .970215 |
| .15 | internal_cut | .425559 | .372406 | .208682 | .969727 |
| .15 | phase3_cut | .420669 | .378794 | .200155 | .984375 |
| .30 | original | .243251 | .226054 | .105268 | .994141 |
| .30 | join_half | .203574 | .207646 | .080442 | .999674 |
| .30 | phase1_half | .248116 | .227461 | .111430 | .996257 |
| .30 | internal_half | .240944 | .222026 | .107048 | .997233 |
| .30 | phase3_half | .245868 | .225812 | .110301 | .998372 |
| .30 | join_cut | .177670 | .198423 | .065033 | 1.000000 |
| .30 | phase1_cut | .270809 | .243929 | .127940 | .999674 |
| .30 | internal_cut | .250574 | .227946 | .117599 | 1.000000 |
| .30 | phase3_cut | .266226 | .237817 | .125178 | .999674 |

D084's real improvement of both composite and isolated errors from original
survives unchanged. New internal cuts do not reveal a better-composing phase
on the pooled criterion.
At the primary norm, both new internal placements worsen standardized/raw/
pixel composite error from original while improving label recognition.
At the stronger norm, almost-perfect labels coexist with 12.79%/12.52% pixel
error in new full-cut phases, versus 6.50% for true joins. Labels are not
anatomical fidelity. The comparison is not merely an isolated-control injury;
nevertheless, damaging useful within-piece links contributes to internal
arms' poorer outcomes and is not a unique mediation proof.

## Secondary checks and retained exceptions

All four observers give positive pooled absolute/composition advantages in
all sixteen blocks at every phase/norm/removal. Whole-region standardized
error and alignment shortfall coincide with active variances; they are not
independent confirmations. Raw and pixel-error agreement adds distinct views.
All **216** standardized contrasts across three budgets, all/eligible-AB/BA/
excluded-ten strata, phases, norms, removals and two outcomes have positive
block means throughout. These overlapping strata and budget aliases are not
216 independent replications.

CD at the primary norm retains negative standardized composition advantage:

| Removal | Phase | CD composition mean | Positive/tied/negative blocks |
| --- | --- | --- | --- |
| .5 | 1 | −.002034 | 3 / 0 / 13 |
| .5 | 2 | −.010491 | 1 / 0 / 15 |
| .5 | 3 | −.014661 | 1 / 0 / 15 |
| 1 | 1 | −.004328 | 5 / 0 / 11 |
| 1 | 2 | −.015046 | 1 / 0 / 15 |
| 1 | 3 | −.018813 | 0 / 0 / 16 |

Its absolute composite advantage remains positive on average; the isolated
comparison gains still more. CD's observer dependence remains: phase1 raw/
pixel composition contrasts are positive at both removals despite negative
standardized contrasts; phase3 raw/pixel are negative at half removal but
positive at full removal. At the secondary norm all CD observer means are
positive, yet standardized composition still has one to four negative blocks.
For primary CD phase3-half, absolute advantage itself has one negative block.

Birth contrasts are exactly zero. At sweep 1, pooled standardized advantages
are tiny negative with mixed block signs. At 50/150/300, both contrasts are
positive in every pooled block for all phases/norms/removals. No precise
onset is identified. Endpoint seam advantages are positive throughout, but
some secondary-norm interior-only absolute contrasts are mixed: phase2-half
9/7, phase3-half 10/6, phase3-full 15/1 positive/negative blocks. Their means
remain positive; composition advantages stay positive in all blocks.
Original region standardization and global mean coupling limit localization.

## Law assessment and recommendation

Keep L23 **MIXED / STRESS_TESTED**. D081 showed that balance helps rather
than being a necessary pre-screen; D082/D083 showed geometry-dependent cost
and its spatial distribution; D084 intervened on local contact; D085 now
shows that the join advantage was not peculiar to the midpoint comparator.
Balancing the starting budget is not the whole story: how pieces interact
also matters, within this fixed assay.

Still only four diagonal phases, fixed forms/physics, the same sixteen
blocks, engineered addresses, global coupling and clipping. No general
composition law, learned ontology or renewable carrier established.
**Recommendation only:** park this narrow edge-placement question for now;
a future revisit should change forms/topology or isolate a genuinely new
mechanism, not add another nearby placement. No such study or law switch
has been approved or launched on this status request.
