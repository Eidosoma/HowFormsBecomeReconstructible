# D111 — L16 matched body-context qualification

2026-09-13. **Complete; small positive qualification, not independent main
confirmation.** L16 is now **STRESS_TESTED / MIXED**. L19's completed review
round stays parked. Saved-data audit and separate full saved replay pass.
[Prospective protocol](../protocols/L16_BODY_CONTENT_V1.md),
[approved proposal](L16_NEXT_STEP_2026-09-13.md).

## Result in plain language

Changing the surviving tissue into the alternative pattern's arrangement
nudges regrowth toward that pattern more than shuffling the same voltage
values does. This happens with reference feedback disabled, so that effect
does not require the R-to-V reader. It is a small, variable nudge, not faithful
reconstruction: the late primary is **+1.12 [0.05,2.39] preference points**.

The frozen qualification passes, but the lower interval bound is very close
to zero. Five tissues are positive, one negative and two tied; each direction
has a positive mean but an individually unresolved interval. The signal is
larger earlier in recovery and smaller at the frozen240-step endpoint.
We retain that endpoint, rather than promoting the stronger early result.

Finished **15:19:19.509030 UTC**, **11.9519275976 seconds**, foreground under
the conservative208.44-s forecast, at most six CPUs. Main output files total
**9,748,516 B (~9.30MiB)**, all external. No active job or follow-up cohort.

## Primary and readout qualification

Effects are percentage points on **P = Qalternative − Qown**, not a direct
accuracy improvement. Intervals use eight tissue blocks, with directions
averaged inside each life and two lives averaged per tissue. All secondary
intervals are pointwise. No cell, direction or branch is an independent
replicate. No exclusions or replacement tissues.

| Final240-step comparison | Effect | 95% tissue interval |
| --- | ---: | ---: |
| Primary, gain0: alternative minus shuffled preference, both directions | +1.12305 | [0.04883,2.39258] |
| Direction0 primary component | +0.97656 | [0,2.24609] |
| Direction1 primary component | +1.26953 | [−0.09766,3.12500] |
| Readout gate0: full-alternative minus full-own, gain0 | +3.80859 | [1.75781,5.85938] |
| Readout gate1: same contrast, reciprocal direction | +3.90625 | [1.85547,5.95703] |

All16 lives have nonempty target disagreement, **19–31/64 cells**. Both
readout gates pass, as do the primary lower-bound and both-direction positive
point-mean rules: **QUALIFIED_CONTEXT_STEERING**. This does not mean both
directions independently establish positive effects; neither direction's
primary interval is strictly positive on its own. There is no80% gate.

Primary tissue effects, unscaled:
`[0,0,.00390625,.01171875,.0390625,.00390625,.0390625,−.0078125]`.
Life directions: **nine positive, three negative, four tied**. The formal
pass is thin and heterogeneous; it needs a separate fixed-design confirmation
before a stronger claim about reproducible late steering.

## Prespecified companions and limits

At gain0, alternative-minus-intact preference is **+2.64 [0.83,4.83]** points,
six positive/two tied tissues. Intact-minus-shuffled **own fidelity** is only
**+0.63 [−0.24,1.90]** points, unresolved. Thus this assay does not establish
a large general repair advantage from preserving intact spatial organization.
Neither result decomposes E53's34.67-point reset effect: geometry, cohort and
intervention differ, and the old reset changes bulk as well as content.

With active reference feedback, alternative-minus-shuffled preference is
**+0.68 [0.29,1.22]** points, a positive secondary result. Its alternative-
minus-intact contrast is **+0.39 [−0.10,0.88]**, unresolved, and intact-minus-
shuffled own fidelity **−0.20 [−0.59,0.15]** is unresolved. Do not infer a
feedback-interaction or mediation fraction from separate gain estimates.

The gain0 primary contrast over the frozen checkpoints is:

| Step | Preference effect | 95% interval |
| --- | ---: | ---: |
| 0 | 0 | [0,0] |
| 1 | 0 | [−0.15,0.15] |
| 20 | +4.00 | [2.78,5.22] |
| 80 | +4.69 | [2.54,7.03] |
| 240, primary | +1.12 | [0.05,2.39] |

These endpoint estimates describe stronger early and weaker late signal,
not a new frozen decay-rate test or a reason to replace the late primary.

Descriptive final gain0 own/alternative correctness is **51.90%/50.49%**
with intact context, **51.27%/51.37%** shuffled, and **50.68%/51.90%**
alternative-ranked. The primary mixes a small donor-correctness increase with
loss of own correctness; it is not a1.12-point gain in absolute donor accuracy.
With active R, these pairs are72.07%/49.07%,72.27%/48.97%,71.97%/49.37%.
Neither the relative qualification nor these absolute values establish
faithful arbitrary pattern memory, a50%-chance baseline or heredity.

Sorted birth voltage multisets match exactly; whole-V mean/RMS differences
are at most **1.11e−16 /2.22e−16**. Matching is at birth, not an added
controller that clamps later bulk values. Native clipping allows small
subsequent mean differences. Birth roughness is about **.425 intact/.747
shuffled/.427 alternative-ranked**. Hence interfaces/organization differ;
this is not a pure bit-content intervention or unique-mediator identification.

## Connection to L16 and next decision

This adds bounded **E5 qualification evidence** that the spatial arrangement
of surviving V can influence which pattern appears during repair, including
when reference feedback is off. It goes beyond E53's whole-context removal,
but does not show that the body is an exclusive anatomy carrier, that theta
contains no instance information, or that a biological division of roles
has been established. L16 stays **MIXED**; the old theta/ensemble/alignment/
horizon limitations and pinned historical case remain unchanged.

Recommend **one unchanged fresh-cohort confirmation**: same injury, ranks,
native physics, controls, gains, primary240-step endpoint, direction rules,
gates and eight-tissue sample size; freeze new identities before outcomes.
Keep the early trajectory as a companion, not a new primary chosen because
it is stronger. Do not pool this qualification into the confirmation estimate,
increase gain, tune a cutoff or keep adding cohorts. Proposal only: no new
protocol/code/futures, reserved successor or automatic launch. Reassess this
narrow lead after that one confirmation.

## Original question and design record

Does the spatial pattern in surviving tissue help steer regrowth, beyond
simply leaving the same amount and mixture of tissue behind?

The original E53 context reset removes all old V and changes bulk condition
as well as content. Its upper-left quarter is also shared-positive in the
two launch recipes. A known tissue-0 check after settlement finds only
3–9 differing cells out of64 there, versus26–34 in a centred same-size
quarter. The new geometry is therefore explicit, not an exact repeat of
the old injury assay. No region is chosen using new outcomes.

## Frozen-design intent

Use the centred rows/columns4:12 quarter, native120-step settlement and
240-step regrowth. Two source patterns, reciprocal recipient directions;
intact, shuffled and alternative-ranked context, crossed with native active
versus disabled reference feedback. Match the exact complement voltage
multiset within each direction. Native recipient R persists and updates;
donor R/EMA never transfers. Reset EMA to birth V in every arm, as E53 does.

The primary asks whether **alternative-pattern context shifts donor preference
more than shuffled context**, with reference feedback disabled. It is not
simply intact-minus-shuffled repair. Full-body, bulk-matched controls must
first show detectable reading in both target directions. Exact sham aliases,
absolute fidelity, both directions, all times/gains and every failed gate
are retained. No80% bar or post-result denominator change.

Eight fixed fresh qualification tissues56000–56007, two lives each; disposable
514211 only before freeze. This is one qualification study, not an automatic
main-confirmation cohort.384 branches,16 independently restated life replays,
64 exact sham aliases. Pure observer/algebra fixtures are not scientific data.

Spatial interfaces and roughness change with the intervention. A positive
result would support bounded spatial-content use, not a unique information
carrier, mediation fraction, acquired heredity, genomic necessity or biology.
An instrument failure is not evidence of no memory.

## Technical verification before any fresh cohort

The initial report has99 passing/two failing tests: exact-equality assertions
on independently summed roughness differed by at most2.220446049250313e−16.
They exceeded a mistaken zero-error test assertion, not the predeclared
1e−12 diagnostic tolerance. The tests now distinguish exact discrete scores
and full dynamics from floating diagnostic sums. No scientific parameter,
observer threshold, endpoint, cohort or gate changed. Failed report retained.

The corrected suite has **102 passing tests in12.88 seconds**, including
the prior L16 audit regressions, exact known E53 tissue0 bridge, full-config
disposable replay, all24 birth/multiset cases, no donor-state transfer,
off-reader exact alias, shuffled/rank controls, arm-order/clock/noise identity,
observer and summary reconstruction, corruption tests and external/CPU guards.
Disposable dynamic arrays replay exactly; floating diagnostic tolerance is
checked separately. Source bridge now extends to all six old E53 tissues.

- [First technical report, retained failures](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/logs/d111_tests_v1.xml)
- [Passing technical report](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/logs/d111_tests_v2.xml)

The independently restated checker uses the D097 physics equations but does
not call the production D111 intervention, simulator, observer or summarizer.
This is repository-informed verification, not a clean-room/E6 replication.

## Resource and handoff boundary

Use at most **six CPUs (0–5)**, numeric threads one; old four-CPU launchers
remain unchanged. All data, fixtures, logs and caches stay on `/mnt/bioIce1/`.
Keep4GiB reserve plus512MiB startup allowance. Freeze source/config/test hashes
before any fresh qualification future, then benchmark disposable514211 and
prepare the manifest. Forecasts over600 seconds detach with no polling.
No automatic retry, larger cohort, next study, threshold adjustment or cleanup.

## Source completion, freeze and launch

All six original E53 tissues pass: every retained scalar agrees, all120
branches/eight futures per branch independently replay with **zero dynamic
error**. Source bridge completed in **4.9604582228 seconds**, under its99.372-s
bound. Across all48 known futures, target disagreement spans3–19/64 in the
old quarter and26–41/64 in the centred quarter. The old observer is not
literally blind; the new fixed geometry improves target separation without
selecting fresh outcomes. Known records do not enter the new estimate.

Freeze **15:16:53.312464 UTC**, **118 input hashes**, zero fresh qualification
futures seen. Passing reportv2 and source-control artifacts are included.
Checked full-config disposable block **3.5444656909 seconds**; conservative
forecast **208.4370416980 seconds (3m28s)**. Budget **49,467,031 B (~47.18MiB)**,
including source artifacts and benchmark; below512MiB allowance. Prepared
**122 inputs**, then launched foreground at six CPUs under the600-s gate.
No long detached job or automatically queued confirmation.

- [Source replay summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l16_body_content_v1_source_controls_attempt1/summary.json)
- [Source COMPLETE](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l16_body_content_v1_source_controls_attempt1/COMPLETE.json)
- [Prospective freeze](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/tmp/l16_body_content_qualification_v1_attempt1_freeze.json)
- [Checked timing](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/tmp/l16_body_content_qualification_v1_attempt1_benchmark.json)
- [Prepared manifest](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l16_body_content_qualification_v1_attempt1/MANIFEST.json)

## Completed verification and artifacts

All384 qualification paths completed with16 full independently restated life
replays and64 exact sham aliases. Maximum dynamic-state discrepancy **0**;
independent roughness summation differs by at most2.220446049250313e−16,
inside the predeclared1e−12 diagnostic tolerance. The source bridge has six
additional full replays of known E53 rows, not fresh scientific replication.

`bash scripts/run_l16_body_content.sh --audit --replay` exits0 and passes:
all eight blocks, **122 prepared input hashes**, **19 output hashes**, exact
initial-state contracts, paired RNGs, observers and all100 contrast rows.
This audit actually reruns all repair paths, unlike the saved-check-only
audit during execution. It remains below the600-second replay guard.

A further read-only direct reconstruction from raw V signs/amplitudes and
source targets reproduces all16 life effects, eight tissue means, primary
mean and frozen-bootstrap interval **exactly**, without calling production
measurement or summary. No source/frozen-science edit, exclusion, rescue
rerun, extra qualification cohort, cleanup or source-hash waiver.

- [COMPLETE](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l16_body_content_qualification_v1_attempt1/COMPLETE.json)
- [All results](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l16_body_content_qualification_v1_attempt1/summary.json)
- [Replay verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l16_body_content_qualification_v1_attempt1/verification.json)
- [Output hashes](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l16_body_content_qualification_v1_attempt1/output_hashes.sha256)

SHA-256 summary `ae5df0a9dcf5f069b46c7aa5874dc9d5da18d04fc4e9e3f1f41af32438680e80`;
COMPLETE `374e72c8517c31d1c023f82cb2a2b8a4ce4b8c766030c86bb4c2eafa638df990`;
manifest `7bd374abe1a829e5d4cff1812c123fa0cf952e9977741ee4e0314b49d5957f89`;
output index `f5678371ac202ea4ea5896ac62c639a5c0cfa971da633e275cce898cbb61a5bc`.

Only new code/docs enter the workspace. Main artifacts are9.30MiB external;
source controls, benchmark and both preserved test-fixture sets are also
external. No active job. The next recommendation is a separately approved
fixed-design confirmation, not an automatically running continuation.
