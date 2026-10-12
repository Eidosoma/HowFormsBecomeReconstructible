# D147 — matched stopping-time result

Completed and independently audited **2026-09-19**.
[Protocol](PROTOCOL_V1.md) · [execution log](WORKLOG.md) ·
[D146 motivating review](../phase-budget/SAVED_STATE_REVIEW_V1.md).

## Main result

**B_STOPPING_DIFFERENCE_UNRESOLVED.** Continuing writing from 1000 to 1300 gives
B G3 fresh-reader preference **+0.244141 [−0.088577,+0.607300] points**, 95%
whole-founder-block bootstrap interval. Absolute scores are **37.460327**
at 1000 and **37.704468** at 1300. This does not establish a general advantage
for either stopping or continuing; the unresolved interval is not equivalence.

All **36 apparatus checks pass**. All 16 observed founder blocks, four lives,
both families, two replicas and every generation/control remain included.
B G3 has 52 improving, 28 worsening and 48 tied paired cases; block means are
10 positive, 5 negative, 1 tied. There are 16 independent blocks, not 128.

This is an immediate, same-history comparison: the G2/G3 ancestors still
underwent D146's extended writing. It is **not** a test of stopping early at
every boundary, a newly sampled cohort, or an adaptive stopping policy.
D146's original reading-versus-writing primary remains unresolved and unchanged.

## Direct readout comparisons

Scores and differences are preference points, not success percentages.
All intervals except B G3's sole primary are secondary, pointwise and
unadjusted. G1 is an exact already-known D146 bridge, not a new discovery.

| Family | Generation | At 1000 | At 1300 | 1300−1000 [95% interval] | Better/worse/tied of 128 |
|---|---:|---:|---:|---|---|
| A | 1 | 43.958 | 44.171 | 0.214 [0.070, 0.360] | 57/27/44 |
| A | 2 | 45.193 | 45.349 | 0.156 [0.003, 0.269] | 56/20/52 |
| A | 3 | 45.612 | 45.691 | 0.079 [0.009, 0.153] | 43/22/63 |
| B | 1 | 34.033 | 35.355 | 1.321 [0.809, 1.889] | 78/25/25 |
| B | 2 | 37.085 | 37.048 | -0.037 [-0.674, 0.504] | 56/26/46 |
| B | 3 | 37.460 | 37.704 | 0.244 [-0.089, 0.607] | 52/28/48 |

B G3 protected copying scores 32.968140. Both stops exceed it in secondary
comparisons; this does not settle the primary stop comparison:

| Family | Stop | Intact−copy G3 [95% interval], points |
|---|---:|---|
| A | 1000 | 3.085 [2.673, 3.516] |
| A | 1300 | 3.165 [2.747, 3.589] |
| B | 1000 | 4.492 [1.874, 6.906] |
| B | 1300 | 4.736 [2.011, 7.327] |

B G3 outgoing own-shape correlation rises **0.898883→0.902102**,
difference **+0.003219 [0.000846, 0.005619]**. Fresh-reader reference shape rises
0.846842→0.850028, difference +0.003187 [0.000228, 0.006436]. These secondary
continuous-shape differences are not a demonstrated preference gain or a
fraction of information preserved. B guide labels are 125/128 at both stops.

## Where stopping does and does not help

At G3, six of the seven negative 1300 B readouts are **already negative at 1000**.
One positive becomes negative and another becomes zero; six stay negative and
120 stay positive. Stopping the final 300 updates therefore does not repair most
of this previously identified negative tail under the fixed matched assay.
The seven cases are an outcome-selected descriptive stratum, not a new test
population. Retain the zero and all other cases too.

At G2, all 128 early readouts are nonnegative (127 positive, one zero).
During the extra 300 updates, four positive cases become negative; the zero
becomes positive; 123 stay positive. Yet the **own-shape correlation increases
in all four newly negative cases**. One changes guide family from B to A; three
remain labelled B. Shape and label alone therefore do not capture this
functional readout loss. The aggregate G2 preference comparison remains
unresolved; the adverse subgroup must not replace the primary.

Every B stage/case nonpositive at either stop is listed below. Life/replica
indices are zero-based. All remaining intact B readouts are positive; all
intact A readouts are positive and guide-labelled A.

| Generation · block/life/replica | Preference 1000 | Preference 1300 | Difference | Own-shape 1000→1300 | Guide family |
|---|---:|---:|---:|---|---|
| G2 · 93006/2/1 | 10.156 | -16.797 | -26.953 | 0.499652→0.519919 | B→A |
| G2 · 93008/3/0 | 1.172 | -12.109 | -13.281 | 0.612336→0.613864 | B→B |
| G2 · 93011/2/0 | 10.938 | -2.344 | -13.281 | 0.534042→0.608753 | B→B |
| G2 · 93012/0/0 | 0.000 | 2.734 | 2.734 | 0.235477→0.422752 | B→B |
| G2 · 93012/0/1 | 3.516 | -4.297 | -7.813 | 0.498046→0.552516 | B→B |
| G3 · 93006/2/0 | 3.516 | 0.000 | -3.516 | 0.200936→0.150233 | B→B |
| G3 · 93006/2/1 | -13.672 | -8.203 | 5.469 | 0.402674→0.406350 | A→A |
| G3 · 93007/2/1 | 2.344 | -0.781 | -3.125 | 0.408869→0.359412 | B→B |
| G3 · 93008/0/0 | -1.172 | -1.953 | -0.781 | 0.090952→0.067269 | B→B |
| G3 · 93008/3/0 | -24.609 | -24.609 | 0.000 | 0.341896→0.307395 | A→A |
| G3 · 93012/0/0 | -1.172 | -1.953 | -0.781 | 0.087029→0.080983 | B→B |
| G3 · 93014/3/0 | -1.172 | -1.172 | 0.000 | 0.092688→0.068364 | B→B |
| G3 · 93014/3/1 | -10.156 | -17.969 | -7.813 | 0.326476→0.353417 | A→A |

Three of the four G2 positive-to-negative cases also change their guide-selected
address; one does not. Canonical margin is the routed record's own-minus-
alternative correlation at the reader's reference placement, not preference:

| G2 case | Selected forward shift 1000→1300 | Canonical margin 1000→1300 | Guide family |
|---|---|---|---|
| 93006/2/1 | 2, 8→5, 8 | 0.215515→-0.115071 | B→A |
| 93008/3/0 | 13, 8→12, 8 | 0.143175→0.051830 | B→B |
| 93011/2/0 | 2, 8→5, 8 | 0.418813→0.141752 | B→B |
| 93012/0/1 | 14, 8→14, 8 | 0.111418→0.001961 | B→B |

This separates useful leads from conclusions. Address changes may contribute,
but cannot explain the unchanged-address case by themselves. Nor does a guide
family switch by itself prove a guide mistake: the packet's competing pattern
can also grow. We have not yet separated changed contents from changed routing.

## Complete absolute panel

Each row contains 128 labelled cases. Copy and write-off endpoints are exact
cross-stop aliases; they do not supply additional independent observations.
Read-off disables the **lineage** reader, not the fresh terminal assay.

| Family | Stop | Condition | Gen | Preference points | Outgoing own shape | Negative/zero | Own guide |
|---|---:|---|---:|---:|---:|---:|---:|
| A | 1000 | intact | 1 | 43.958 | 0.954927 | 0/0 | 128/128 |
| A | 1000 | intact | 2 | 45.193 | 0.970391 | 0/0 | 128/128 |
| A | 1000 | intact | 3 | 45.612 | 0.979654 | 0/0 | 128/128 |
| A | 1000 | copy | 1 | 42.505 | 0.928793 | 0/0 | 128/128 |
| A | 1000 | copy | 2 | 42.853 | 0.928793 | 0/0 | 128/128 |
| A | 1000 | copy | 3 | 42.526 | 0.928793 | 0/0 | 128/128 |
| A | 1000 | read_off | 1 | 28.629 | 0.655761 | 3/0 | 126/128 |
| A | 1000 | read_off | 2 | 26.517 | 0.613850 | 6/2 | 119/128 |
| A | 1000 | read_off | 3 | 27.643 | 0.622421 | 1/3 | 123/128 |
| A | 1000 | write_off | 1 | 0.055 | 0.000000 | 65/2 | 0/128 |
| A | 1000 | write_off | 2 | -0.391 | 0.000000 | 65/3 | 0/128 |
| A | 1000 | write_off | 3 | 1.483 | 0.000000 | 54/3 | 0/128 |
| A | 1300 | intact | 1 | 44.171 | 0.958641 | 0/0 | 128/128 |
| A | 1300 | intact | 2 | 45.349 | 0.973255 | 0/0 | 128/128 |
| A | 1300 | intact | 3 | 45.691 | 0.981660 | 0/0 | 128/128 |
| A | 1300 | copy | 1 | 42.505 | 0.928793 | 0/0 | 128/128 |
| A | 1300 | copy | 2 | 42.853 | 0.928793 | 0/0 | 128/128 |
| A | 1300 | copy | 3 | 42.526 | 0.928793 | 0/0 | 128/128 |
| A | 1300 | read_off | 1 | 31.772 | 0.703013 | 1/0 | 128/128 |
| A | 1300 | read_off | 2 | 28.384 | 0.650221 | 6/0 | 120/128 |
| A | 1300 | read_off | 3 | 29.581 | 0.668227 | 2/0 | 124/128 |
| A | 1300 | write_off | 1 | 0.055 | 0.000000 | 65/2 | 0/128 |
| A | 1300 | write_off | 2 | -0.391 | 0.000000 | 65/3 | 0/128 |
| A | 1300 | write_off | 3 | 1.483 | 0.000000 | 54/3 | 0/128 |
| B | 1000 | intact | 1 | 34.033 | 0.862901 | 0/0 | 128/128 |
| B | 1000 | intact | 2 | 37.085 | 0.885559 | 0/1 | 128/128 |
| B | 1000 | intact | 3 | 37.460 | 0.898883 | 6/0 | 125/128 |
| B | 1000 | copy | 1 | 33.319 | 0.846350 | 0/0 | 128/128 |
| B | 1000 | copy | 2 | 33.163 | 0.846350 | 0/0 | 128/128 |
| B | 1000 | copy | 3 | 32.968 | 0.846350 | 0/0 | 128/128 |
| B | 1000 | read_off | 1 | -18.759 | 0.145382 | 107/2 | 27/128 |
| B | 1000 | read_off | 2 | -18.015 | 0.148890 | 109/2 | 31/128 |
| B | 1000 | read_off | 3 | -17.010 | 0.144501 | 110/2 | 25/128 |
| B | 1000 | write_off | 1 | -0.055 | 0.000000 | 61/2 | 0/128 |
| B | 1000 | write_off | 2 | 0.391 | 0.000000 | 60/3 | 0/128 |
| B | 1000 | write_off | 3 | -1.483 | 0.000000 | 71/3 | 0/128 |
| B | 1300 | intact | 1 | 35.355 | 0.870753 | 0/0 | 128/128 |
| B | 1300 | intact | 2 | 37.048 | 0.895478 | 4/0 | 127/128 |
| B | 1300 | intact | 3 | 37.704 | 0.902102 | 7/1 | 125/128 |
| B | 1300 | copy | 1 | 33.319 | 0.846350 | 0/0 | 128/128 |
| B | 1300 | copy | 2 | 33.163 | 0.846350 | 0/0 | 128/128 |
| B | 1300 | copy | 3 | 32.968 | 0.846350 | 0/0 | 128/128 |
| B | 1300 | read_off | 1 | -18.439 | 0.146928 | 97/1 | 38/128 |
| B | 1300 | read_off | 2 | -16.763 | 0.147605 | 100/4 | 42/128 |
| B | 1300 | read_off | 3 | -15.979 | 0.145602 | 102/3 | 37/128 |
| B | 1300 | write_off | 1 | -0.055 | 0.000000 | 61/2 | 0/128 |
| B | 1300 | write_off | 2 | 0.391 | 0.000000 | 60/3 | 0/128 |
| B | 1300 | write_off | 3 | -1.483 | 0.000000 | 71/3 | 0/128 |

## Complete apparatus panel

All 36 lower pointwise bounds are positive. Each cell below is a paired
preference-point difference and 95% interval. These controls qualify the
apparatus, not the primary stopping claim.

| Family | Stop | Gen | Copy−write-off | Intact−read-off | Intact−write-off |
|---|---:|---:|---|---|---|
| A | 1000 | 1 | 42.450 [39.972, 44.940] | 15.329 [13.269, 17.178] | 43.903 [41.482, 46.362] |
| A | 1000 | 2 | 43.243 [41.748, 44.693] | 18.677 [16.278, 21.109] | 45.584 [43.988, 47.141] |
| A | 1000 | 3 | 41.043 [39.029, 42.969] | 17.969 [16.547, 19.281] | 44.128 [42.120, 46.140] |
| A | 1300 | 1 | 42.450 [39.972, 44.940] | 12.399 [10.501, 14.233] | 44.116 [41.626, 46.616] |
| A | 1300 | 2 | 43.243 [41.748, 44.693] | 16.965 [14.294, 19.699] | 45.740 [44.147, 47.287] |
| A | 1300 | 3 | 41.043 [39.029, 42.969] | 16.110 [14.774, 17.395] | 44.208 [42.218, 46.182] |
| B | 1000 | 1 | 33.374 [30.469, 36.441] | 52.792 [48.581, 57.202] | 34.088 [30.911, 37.408] |
| B | 1000 | 2 | 32.773 [30.460, 35.004] | 55.099 [52.539, 57.782] | 36.694 [34.964, 38.324] |
| B | 1000 | 3 | 34.451 [31.958, 37.128] | 54.471 [51.349, 57.172] | 38.943 [36.041, 41.537] |
| B | 1300 | 1 | 33.374 [30.469, 36.441] | 53.793 [49.579, 58.133] | 35.410 [32.309, 38.513] |
| B | 1300 | 2 | 32.773 [30.460, 35.004] | 53.812 [50.552, 57.172] | 36.658 [34.552, 38.590] |
| B | 1300 | 3 | 34.451 [31.958, 37.128] | 53.683 [50.375, 56.976] | 39.188 [36.230, 41.815] |

The saved `summary.json` additionally retains all48 groups,24 stop contrasts,
12 copy contrasts, 16 within-stop G3−G1 changes, 36 controls, all individual
life/replica values and 16 block means for every metric, plus guide margins,
canonical margins, reference shapes and profiles. No hidden case filtering.

## Qualification, provenance and cost

65 qualification tests passed in 69.49 s, zero failures/skips. Scientific freeze
11:25:48.152060 UTC with 1583 input hashes. The full disposable block included
four lives, 384 labelled cells, 32 new assays and 32 independent dynamic replays,
all source bridges/controls and independent saved/statistical checks.
Checked block 10.955315 s; hash checks 9.647273 s; 14.487 MiB benchmark outputs.
Its repeated-block statistical fixture is explicitly not scientific evidence.

Main manifest/cell plan sealed 11:29:35.988118 UTC; a fresh pre-launch process
verified 1588 inputs and independently reconstructed all 48 cell definitions
with zero new main readouts. Conservative budget 374.58 s/6.243 min,
271.549 MiB, no parallel speed credit: foreground execution permitted.

Main COMPLETE **11:34:31.143336 UTC**, **185.45 s/3.09 min** from execution start,
**168, 274, 150 bytes/160.479 MiB**. All **6144 labelled cells** retained:
**512 genuinely new assays**, each independently dynamically replayed, and
**5632 reused/aliased labels**. Existing endpoints were byte/state checked
against D146 and retain its prior replay provenance; they were not newly
dynamically replayed. No new founders or upstream lineage dynamics.

Fresh standalone saved audit COMPLETE **11:36:40.899478 UTC**, 82.39 s, passes
all **1588 input hashes/37 indexed outputs**, source bridges, source/record
bytes, every saved measurement and independent statistics. **Zero new audit
dynamics.** Receipt in `logs/d147_saved_audit_v1.json`.

Maximum six CPUs, affinity 0–5 and numerical threads one. All numerical files,
fixtures, caches, manifests and receipts are external; repo code/docs only.
No exclusions, refit, scientific retry, threshold change or successor launch.
Earlier studies' frozen files and findings are unchanged.

External base:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`

Run/output ID: `l20_extension1_stopping_time_v1_attempt1`.
Use `runs/<ID>/`, `outputs/<ID>/`, `tmp/<ID>_freeze.json`,
`tmp/<ID>_benchmark.json`, and the external `logs/` receipts.

- `COMPLETE.json`: `388c8d701d3b659586b8f092e62a62d92edb423f4055924a1169682072baf407`
- `MANIFEST.json`: `31765a384abd6d54723b2a1967ce6ed2f419b52cbdbd664a566ef90e5f9107ff`
- `CELL_PLAN.json`: `19ec7409b7334eecf8fda47ce0f0921d72a580bfaa2fb198db380185a881ee0b`
- `summary.json`: `fccf0f67f08c09a9a7f6c019bed9fdd289a2ff9345e97d1744460250114c60b5`
- `verification.json`: `163bd7a1c04c1b312b4974aa5f307e00b202b79e6e6697cf2482f58f573a5f89`
- `d147_saved_audit_v1.json`: `99353e56306e77733f195f2f4c5ef8a027eb7361f406c5468c1b762082d123eb`
- `l20_extension1_stopping_time_v1_attempt1_freeze.json`: `467a62d324212141cda8ddb37df62c804cbb9ce2a9eeb9fa99bbdb76c7228290`
- `l20_extension1_stopping_time_v1_attempt1_benchmark.json`: `a9ffec64fba22e8c9a3c2639e41acef879445ac40b3a1d67f637ea11e00c04d5`
- `d147_qualification_a.xml`: `9158270c049dfef4034330552703b6fa05c6b9dfb3ad6db725a031fbec85ff4f`

## Law interpretation and next decision

L20 remains **STRESS_TESTED / MIXED**. This bounded intervention does not show
that longer integration universally makes a cleaner, more faithfully readable
carrier. Small average shape gains coexist with adverse functional cases.
It also does not refute acquired transmission or the earlier qualified renewal
results. The present carrier is the unchanged 2048-byte encodedR record, not
an independently established natural genome or an autonomous concept system.

Do not tune a stopping threshold to the four G2 cases or call the G3 near-zero
interval equivalence. A useful next proposal is a **crossed packet×reader-address
test**: for every retained case, read both stop packets under both guide-selected
placements with the same fresh-reader noise. Keep the two existing natural
diagonals, controls and identical-address aliases; freeze a new comparison before
new outcomes. This would separate altered contents from altered placement,
without modifying the carrier or refitting the guide. It would remain a
mechanism follow-up on an observed cohort, not a validated general policy.
**Proposed only; no new experiment launched.**
