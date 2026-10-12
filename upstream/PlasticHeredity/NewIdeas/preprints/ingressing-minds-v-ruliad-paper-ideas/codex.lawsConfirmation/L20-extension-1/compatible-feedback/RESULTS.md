# D144 — completed: compatible feedback improves fresh-descendant reconstruction

Main COMPLETE **2026-09-18 11:47:55.448717 UTC**. Fresh-process saved-output
audit passed on the user's status request, 2026-09-18; no new dynamics.
[Protocol](PROTOCOL_V1.md), [tracker](README.md), [work log](WORKLOG.md).

## Main result, in plain terms

For the striped B pattern, shifting writing feedback in ways that preserve
its ideal pattern helped the next, newly initialized body reconstruct it.
The benefit was not just a nicer-looking writing body: the registered
fresh-descendant outcome improved. This is a positive result for a specific,
externally supplied feedback rule after **one rewrite**, not confirmation of
L20 as a whole or proof of repeated, autonomous renewal.

The sole registered primary, B q=+1 nonzero shift minus B zero shift, is
**+3.91846 preference points**, whole-founder-block 95% interval
**[+2.82280, +5.12695]**. Absolute terminal preferences are **35.87646**
and **31.95801** points respectively. All 16 paired founder-block means are
positive (descriptive, not a new success gate). All six apparatus checks pass.
Frozen classification: `B_COMPATIBLE_DESCENDANT_BENEFIT`.

Preference points mean 100 times the existing own-minus-alternative score;
they are **not a success percentage**. Each condition has 128 observations
(16 blocks × four lives × two noise replicates), but inference resamples
the **16 whole founder blocks**, not 128 independent founders.
10,000 bootstrap draws; fixed seed 14420260918. No exclusions or refits.

## Shape, controls and limits

B outgoing-record best translated own-shape correlation rises from
0.812913 with zero shift to 0.886149 with compatible shifts:
paired +0.073236 [0.055629, 0.092107]. Writer-end R shape rises
0.812138→0.882269, paired +0.070131 [0.052993, 0.088443].
Fresh-descendant R shape rises 0.762010→0.833398, paired
+0.071388 [0.052155, 0.092824]. These are registered **secondary** endpoints,
with pointwise, multiplicity-unadjusted intervals.

A also shows a smaller secondary preference benefit:
+0.68359 [0.43030, 0.94910] points for compatible shifts.
B's class means improve as ideal compatibility increases; the opposing
q=-1 class is worse than zero shift by -10.67810 [-12.42989, -8.89885]
points. A is less strongly and less monotonically ordered.
All classes and controls, including unfavorable outcomes, appear below.

Protected-copy B terminal preference is 33.41064 points, between zero
shift and compatible shifts. Incoming B record shape is 0.855313;
protected copying preserves it, while the compatible writer's mean outgoing
shape is 0.886149. These mean comparisons suggest improvement relative to
the imperfect starting pattern; they are not a newly registered
compatible-minus-copy test or evidence of exact record preservation.
Shape is ideal-template correlation, **not a fraction of information saved**.

Crucially, both zero-shift and compatible B records receive their own guide
label in all 128 cases, yet their continuous reconstruction scores differ.
Compatible B retains one negative terminal preference; zero shift retains
none. Improvement in the mean does not imply uniformly better outcomes or
perfect reconstruction. No new 80% threshold is used.

The full main address schedule was sealed before founder generation.
All first-reader paths match across normal conditions within a paired case,
and enabled writers match through writing step 1. The intervention changes
writer feedback geometry; the fresh descendant receives only the declared
2048-byte carrier plus the unchanged public 4096-byte guide/rules.
The favorable geometry is supplied using family knowledge, not learned by
the tissue. Only two familiar target families and one frozen guide are tested.

## Absolute outcomes: every retained condition

Each row contains 128 paired-case observations. Negative/zero counts concern
final preference; the last column concerns the terminal guide's family choice.
Means below are not pass rates. The frozen JSON retains absolute intervals
for every metric as well as all individual values and block means.

| Family | Condition | Final preference (points) | Outgoing shape | Writer-end R shape | Final R shape | Negative / zero | Own guide label |
|---|---|---:|---:|---:|---:|---:|---:|
| A | zero shift | 43.414 | 0.94144 | 0.94019 | 0.90783 | 0 / 0 | 128/128 |
| A | q=-1.00 | 41.309 | 0.89109 | 0.88865 | 0.87503 | 0 / 0 | 128/128 |
| A | q=-0.75 | 43.140 | 0.92889 | 0.92591 | 0.90297 | 0 / 0 | 128/128 |
| A | q=-0.50 | 44.019 | 0.94611 | 0.94142 | 0.91731 | 0 / 0 | 128/128 |
| A | q=-0.25 | 43.927 | 0.94719 | 0.94158 | 0.91942 | 0 / 0 | 128/128 |
| A | q=0.00 | 43.857 | 0.94488 | 0.93801 | 0.91839 | 0 / 0 | 128/128 |
| A | q=0.25 | 43.823 | 0.94489 | 0.93586 | 0.91935 | 0 / 0 | 128/128 |
| A | q=0.50 | 44.046 | 0.95031 | 0.94124 | 0.92239 | 0 / 0 | 128/128 |
| A | q=0.75 | 43.695 | 0.95258 | 0.94693 | 0.91854 | 0 / 0 | 128/128 |
| A | q=1.00 | 44.098 | 0.95616 | 0.95274 | 0.91987 | 0 / 0 | 128/128 |
| A | protected copy | 42.911 | 0.93651 | 0.92506 | 0.90536 | 0 / 0 | 128/128 |
| A | reading off | 19.955 | 0.47389 | 0.47950 | 0.46520 | 10 / 0 | 117/128 |
| A | writing off | -2.054 | 0.00000 | 0.92506 | 0.38868 | 68 / 2 | 0/128 |
| B | zero shift | 31.958 | 0.81291 | 0.81214 | 0.76201 | 0 / 0 | 128/128 |
| B | q=-1.00 | 21.280 | 0.65262 | 0.64535 | 0.60379 | 11 / 0 | 120/128 |
| B | q=-0.50 | 24.341 | 0.70687 | 0.70278 | 0.65619 | 5 / 0 | 126/128 |
| B | q=0.00 | 30.359 | 0.80073 | 0.79680 | 0.75418 | 3 / 0 | 126/128 |
| B | q=0.50 | 34.048 | 0.84025 | 0.83577 | 0.79218 | 1 / 0 | 128/128 |
| B | q=1.00 | 35.876 | 0.88615 | 0.88227 | 0.83340 | 1 / 0 | 128/128 |
| B | protected copy | 33.411 | 0.85531 | 0.58002 | 0.79851 | 0 / 0 | 128/128 |
| B | reading off | -19.955 | 0.11515 | 0.11405 | 0.10375 | 118 / 0 | 11/128 |
| B | writing off | 2.054 | 0.00000 | 0.58002 | 0.12384 | 58 / 2 | 0/128 |

Incoming-record shape is 0.936511 for A and 0.855313 for B.
Protected copy transmits that record unchanged; its writer-end body is not
the transmitted record. Writing-off transmits the zero field. Reading-off
disables the first reader only, not the final assay.

## All paired contrasts against zero shift

Entries are mean [pointwise 95% whole-founder-block interval].
Only **B q=+1 final preference** is primary. Other intervals are unadjusted
secondary descriptions; crossing zero means unresolved, not equivalence.
q denotes the exact ideal-pattern compatibility, not displacement size.

| Family | Condition minus zero shift | Final preference (points) | Outgoing shape | Writer-end R shape | Final R shape |
|---|---|---|---|---|---|
| A | q=-1.00 | -2.106 [-2.408, -1.797] | -0.05035 [-0.05735, -0.04423] | -0.05154 [-0.05886, -0.04518] | -0.03281 [-0.03858, -0.02765] |
| A | q=-0.75 | -0.275 [-0.638, 0.067] | -0.01255 [-0.02025, -0.00498] | -0.01428 [-0.02151, -0.00719] | -0.00486 [-0.01135, 0.00158] |
| A | q=-0.50 | 0.604 [0.183, 1.031] | 0.00467 [-0.00385, 0.01316] | 0.00123 [-0.00657, 0.00898] | 0.00948 [0.00201, 0.01713] |
| A | q=-0.25 | 0.513 [0.070, 0.967] | 0.00575 [-0.00324, 0.01445] | 0.00139 [-0.00656, 0.00914] | 0.01159 [0.00332, 0.01962] |
| A | q=0.00 | 0.443 [-0.015, 0.897] | 0.00344 [-0.00521, 0.01174] | -0.00218 [-0.00981, 0.00510] | 0.01056 [0.00224, 0.01843] |
| A | q=0.25 | 0.409 [-0.031, 0.858] | 0.00345 [-0.00451, 0.01114] | -0.00433 [-0.01127, 0.00240] | 0.01152 [0.00363, 0.01912] |
| A | q=0.50 | 0.632 [0.146, 1.077] | 0.00887 [0.00105, 0.01622] | 0.00105 [-0.00584, 0.00753] | 0.01456 [0.00735, 0.02135] |
| A | q=0.75 | 0.281 [-0.177, 0.702] | 0.01114 [0.00391, 0.01766] | 0.00674 [0.00034, 0.01251] | 0.01071 [0.00430, 0.01657] |
| A | q=1.00 | 0.684 [0.430, 0.949] | 0.01472 [0.01236, 0.01759] | 0.01255 [0.01059, 0.01500] | 0.01204 [0.00986, 0.01441] |
| A | protected copy | -0.504 [-0.650, -0.366] | -0.00493 [-0.00724, -0.00265] | -0.01513 [-0.01955, -0.01073] | -0.00247 [-0.00425, -0.00081] |
| A | reading off | -23.459 [-25.247, -21.634] | -0.46755 [-0.49829, -0.43561] | -0.46069 [-0.49084, -0.42920] | -0.44263 [-0.47506, -0.40930] |
| A | writing off | -45.468 [-47.134, -43.799] | -0.94144 [-0.94912, -0.93371] | -0.01513 [-0.01955, -0.01073] | -0.51915 [-0.55046, -0.48643] |
| B | q=-1.00 | -10.678 [-12.430, -8.899] | -0.16030 [-0.17994, -0.14162] | -0.16679 [-0.18736, -0.14756] | -0.15822 [-0.18234, -0.13407] |
| B | q=-0.50 | -7.617 [-9.290, -6.052] | -0.10604 [-0.12498, -0.08706] | -0.10936 [-0.12832, -0.09052] | -0.10582 [-0.12751, -0.08367] |
| B | q=0.00 | -1.599 [-2.957, -0.589] | -0.01219 [-0.02897, 0.00474] | -0.01534 [-0.03152, 0.00092] | -0.00783 [-0.02529, 0.00916] |
| B | q=0.50 | 2.090 [1.056, 3.143] | 0.02734 [0.01211, 0.04320] | 0.02363 [0.00859, 0.03948] | 0.03017 [0.01398, 0.04741] |
| B | q=1.00 | 3.918 [2.823, 5.127] | 0.07324 [0.05563, 0.09211] | 0.07013 [0.05299, 0.08844] | 0.07139 [0.05216, 0.09282] |
| B | protected copy | 1.453 [0.668, 2.234] | 0.04240 [0.02694, 0.05785] | -0.23212 [-0.25026, -0.21323] | 0.03650 [0.02391, 0.04835] |
| B | reading off | -51.913 [-54.404, -49.148] | -0.69776 [-0.73687, -0.65140] | -0.69808 [-0.73572, -0.65316] | -0.65826 [-0.69960, -0.61094] |
| B | writing off | -29.904 [-32.794, -26.688] | -0.81291 [-0.85086, -0.77049] | -0.23212 [-0.25026, -0.21323] | -0.63817 [-0.68176, -0.59081] |

## Complete apparatus panel

All six predeclared lower confidence bounds exceed zero. These comparisons
qualify the apparatus; they are not pooled into the primary effect.

| Family | Required contrast | Preference-point effect [95% interval] | Pass |
|---|---|---|---|
| A | protected copy minus writing off | 44.965 [43.271, 46.677] | yes |
| A | zero shift minus reading off | 23.459 [21.634, 25.247] | yes |
| A | zero shift minus writing off | 45.468 [43.799, 47.134] | yes |
| B | protected copy minus writing off | 31.357 [28.259, 34.155] | yes |
| B | zero shift minus reading off | 51.913 [49.148, 54.404] | yes |
| B | zero shift minus writing off | 29.904 [26.688, 32.794] | yes |

## Saved chronology and sampling

Selected chronology below shows the two extremes and zero shift in **both**
families. Each cell is native preference points / best translated R-shape
correlation. The complete mean profiles for **all 22 conditions** remain
in frozen `summary.json`: first read 0,1,100,101,300; write 0,1,300,1000;
fresh read 0,1,100,300. No stopping-time selection.

| Family / condition | Write 0 | Write 1 | Write 300 | Write 1000 | Fresh-reader 300 |
|---|---|---|---|---|---|
| A / zero shift | 43.12 / 0.9036 | 42.46 / 0.9039 | 43.61 / 0.9315 | 44.09 / 0.9402 | 43.41 / 0.9078 |
| A / q=-1.00 | 43.12 / 0.9036 | 42.46 / 0.9039 | -41.56 / 0.6060 | -37.57 / 0.8886 | 41.31 / 0.8750 |
| A / q=1.00 | 43.12 / 0.9036 | 42.46 / 0.9039 | 43.89 / 0.9423 | 44.72 / 0.9527 | 44.10 / 0.9199 |
| B / zero shift | 33.40 / 0.7971 | 32.99 / 0.7974 | 33.17 / 0.8140 | 33.50 / 0.8121 | 31.96 / 0.7620 |
| B / q=-1.00 | 33.40 / 0.7971 | 32.99 / 0.7974 | -32.43 / 0.3256 | -20.67 / 0.6454 | 21.28 / 0.6038 |
| B / q=1.00 | 33.40 / 0.7971 | 32.99 / 0.7974 | 37.15 / 0.8747 | 40.02 / 0.8823 | 35.88 / 0.8334 |

The opposing A writer can have a reversed native-coordinate preference
while retaining recognizable translated shape; the guide then routes its
record for the fresh reader. Native phase, ideal shape and descendant
function are therefore kept separate. This is not evidence that all
opposing feedback merely translates intact records.

Each compatibility class has 128 precommitted address draws, with
replacement. All 15 allowable A q=+1 offsets occurred; 30 of the 31 B q=+1
offsets occurred. The missing offset was not filled in and repeated draws
were not removed. Every class's raw 16×16 address-frequency grid is retained
in `summary.json`; the sealed `ADDRESS_SCHEDULE.json` and block artifacts
retain all assignments. Equal class sampling is not uniform sampling of all
255 nonzero shifts. No individual favorable displacement was selected.

## Qualification, integrity and computation costs

55 qualification tests passed in 113.88s. Freeze 11:22:04.844668 UTC,
1395 inputs. The full disposable benchmark completed 11:25:31.795025 UTC:
138.106768s checked block plus 6.053949s hashes; 13.50MiB external.
The benchmark's repeated-block statistics fixture is not scientific evidence.

The first cold standalone benchmark-audit CLI stopped with
`ModuleNotFoundError: voltage_web` because its entry point omitted package
initialization. Preserved in the work log; no frozen code was edited.
A fresh process calling the existing `preflight(False)` before
`benchmark_audit()` passed all saved artifacts with zero new dynamics.
Normal main prepare and saved audit already include that preflight.

Main prepared 11:30:09.580000 UTC with 1400 pinned inputs. Full schedule and
input hashes verified before any main founders or outcomes. Startup ACK
11:33:37.038117 UTC, PID3804640; detached with null stdin, new session,
durable external log, at most six workers/CPUs, numerical threads one.
No automatic progress polling, retry, successor or refit occurred.
The run was first inspected on the user's subsequent status request.

Recorded main wall time **858.411772s / 14.31min**; main output bytes
**203,279,684 / 193.86MiB**, all external. Conservative launch budget was
40.03min / 378.90MiB (no parallel speed credit). These are wall time and
artifact bytes, not measured total CPU-seconds. Code/docs only in the repo.

Production independently replayed every source and condition path:
16 fresh blocks, 128 founder acquisitions / record–host pairs,
2816 condition/noise paths, 2304 enabled rewrites, 5632 reader paths.
The fresh `--audit` process then passed **1400 input hashes / 37 indexed
outputs**, all blocks, independent statistics, source/reset/routing checks,
full schedule and saved replay receipts; **zero new dynamics**.
The hash-index file itself is checked separately from the 37 outputs.
No frozen scientific source, guide, protocol or previous result changed.

## Provenance and next decision

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`.
Run ID: `l20_extension1_compatible_feedback_v1_attempt1`.
Receipts: `runs/<run_id>/`; artifacts: `outputs/<run_id>/`;
durable log: `logs/<run_id>_execute.log`.
Full numerical results are in the frozen `summary.json`, with independent
checks in `verification.json`.

- Freeze: `1c91123910ae868c3681d6b61dd734292f9f0b8f5cb5aac61e3321717e277a71`.
- Benchmark receipt: `19676634c17764439d392db74f3e583582120ec2c4a9f73929b7976b1b4d3424`.
- Main manifest: `82052aa67d1aac04f0c69c6c2721204e1adcd09df8053b7ce90dba0ebd4b35db`.
- Main address schedule: `47bbd868ad53f1604eb76222e6cd912149f3b448c1456fcbb0c1da077cb9c3bf`.
- COMPLETE: `7635ba636424624db675a97117d52f4a2ffc19df9c5a00b727b722e69776a645`.
- Summary: `8d8b989238ab50ef22dc2e085e4fd800c4562241c63299b1a07596477870b1d3`.
- Verification: `7de7462a6e558d9c4f17d0e445f0be50f54e47299d294a0e604bfebffa978eb5`.
- Output hash index: `1b6dba2c63bc86353149f54543a1135c1d90a46d32b641630caac7f83771d7eb`.

L20 remains **STRESS_TESTED / MIXED**. D141's prospective diagnostic
comparison remains unresolved; D142/D143 conclusions remain unchanged.
D144 supports a bounded externally supplied, geometry-compatible writer
benefit. It establishes neither autonomous address discovery/repair,
unseen-family generalization, unlimited renewal, complete preservation,
protected-copy equivalence, nor a universally cleaner slow-layer cascade.

**Proposed next step, not launched:** test whether this compatible-feedback
advantage survives three complete read–rewrite–fresh-body replacements,
retaining zero-shift, protected-copy and disabled-reading/writing controls.
Freeze a new serial protocol and primary before producing those outcomes;
carry this one-rewrite result forward without reinterpreting it as serial
evidence. No successor or additional experiment was started on this status turn.
