# D124 — theta stage versus instantaneous final-R record

2026-09-14. COMPLETE; separate saved audit and raw reconstruction pass.
[Prospective contract](../protocols/L20_THETA_STAGE_V1.md).

## Outcome in plain terms

At the same end-of-writing moment, making a record directly from R works
slightly BETTER than using the accumulated theta record. The instant-R
advantage is **+0.25 [0.14,0.34] preference points** pooled, with seven of
eight blocks favoring instant R. Both records carry strong readable content.
Theta did not provide the predicted additional record-value benefit in this
assay; its deficit is small, not a failure of inheritance.

The frozen PRIMARY is theta-minus-instant, hence **−0.2543131510
[−0.3438313802,−0.1444498698] points**, `INSTANT_R_ADVANTAGE_QUALIFIED`.
This is bounded fresh-reader E5 counterevidence to the proposed extra
theta-stage readout benefit, not a universal theorem that slow writing is
harmful or unnecessary. L20 stays **STRESS_TESTED / MIXED**; D117's bounded
renewal and D123's source-noise buffering findings stand. No active main job,
retry or automatic successor.

## Primary and directions

One primary, terminal qualified P(theta)−P(instant), averaged over the
three source-generation strata and both roles within each of four lives,
then eight paired blocks. P is own-pattern agreement minus alternative-
pattern agreement; points = score difference*100, not relative improvement,
success rate or agreement change alone.10,000 whole-block bootstrap draws;
independent n=8, not192 source pairs,1920 readers or256 cells.

Primary counts: **seven negative/one positive blocks**,26 negative/three
positive/three tied role-averaged lives. No uniform individual disadvantage.

- Pattern A: **−0.32552 [−0.42318,−0.24821] points**; all eight blocks
  negative,28 negative/one positive/three tied averaged lives.
- Pattern B: **−0.18311 [−0.37842,+0.01628] points**; six negative/two
  positive blocks,22 negative/six positive/four tied lives. Its interval
  includes zero: the B direction remains unresolved.

Both directional means are negative, so the prespecified pooled-interval/
both-means rule yields the comparative label. It did NOT require both
directional intervals to exclude zero. Do not report uniform significance.
Neither the small size nor a tied individual value establishes equivalence.

## Content, handling and agreement

Both content routes qualify: intact-minus-own-shuffle and intact-minus-zero
have positive intervals in both directions, all eight blocks and all32
averaged lives positive for each route/direction. Ideal-minus-zero also
passes in both directions. The small theta-versus-instant deficit is
therefore not a comparison of two failed records.

Qualified agreement: correct sign AND strict abs(V)>.2, denominator all256
cells. Means over all blocks/lives/source strata:

| Record | Pattern A agreement | Pattern B agreement | Intact-minus-own-shuffle preference points (95% interval) |
| --- | ---: | ---: | ---: |
| Saved final theta | 93.22% | 86.60% | 42.21802 [40.44189,43.83341] |
| Instant final-R record | 93.56% | 86.87% | 42.58423 [40.79788,44.19968] |
| Supplied ideal | 95.26% | 92.20% | Instrument, not acquired |
| Zero / either reading-off | 44.43% | 42.85% | No record applied |

Intact-minus-zero pooled: theta **42.22819 [40.87519,43.38379]**, instant
**42.48250 [41.09294,43.68500]** points. All864 exact aliases pass: each
route's own sham equals intact, each disabled path equals zero, and the
two zero-role paths match. Those aliases are technical checks, not extra n.

Pattern B individual agreement spans **67.97–93.36%** for theta and
**67.58–93.75%** for instant. Pattern A ranges90.23–97.66% and89.84–97.66%.
The slight mean instant advantage does not imply better minima or universal
high fidelity. No80% threshold was used.

## Secondary checks

The shuffle-adjusted theta specificity gain,
(theta−theta_shuffle)−(instant−instant_shuffle), is also negative pooled:
**−0.36621 [−0.54321,−0.21973] points**, all eight blocks negative,
22 negative/10 positive averaged lives. A **−0.48828 [−0.66325,−0.30924]**
is negative; B **−0.24414 [−0.54118,+0.05290]** remains unresolved.
This is secondary with pointwise/unadjusted intervals, not a second primary.

Qualified theta-minus-instant by source-generation stratum:

- G1 **−0.28687 [−0.46997,−0.04868]** pooled; seven negative/one positive
  blocks. A negative; B unresolved.
- G2 **−0.28076 [−0.37231,−0.19531]**; all eight blocks negative.
  Both directional intervals negative.
- G3 **−0.19531 [−0.27466,−0.12207]**; all eight blocks negative.
  A negative; B unresolved.

No trend was tested, and these reused strata are not three new independent
renewal demonstrations. Specificity is negative pooled in G1/G2 but unresolved
in G3: **−0.10376 [−0.36621,+0.10986]** points.

The ordinary sign-observer contrast is **−0.13021 [−0.24007,−0.01628]**
points pooled, six negative/two positive blocks;19 negative/six positive/
seven tied lives. A **−0.22786 [−0.35807,−0.10579]**; B
**−0.03255 [−0.23600,+0.19531]** unresolved. The sign result's small lower
instant-advantage bound is not robust evidence of a large effect. Correlated
observers/strata do not increase n; all secondary intervals are unadjusted.

## Design and interpretation limits

User approved D123's next lead. All192 D117 primary rewrite sources reused:
blocks60000–60007,four lives,both roles,three strata. Same time1300,
checkpoint7 after1000 writer steps: theta field3 and R field2.192 exact
outgoing theta packets,192 instant `project(tanh(R_final), .3)` packets.
Theta never reprojected. Both mean0/std.3, same2048-byte format and reader
duration/noise. Native source order updates R before theta; these are
contemporaneous final fields, not a stale-R comparison.

Reader keys66000–66007, new tag `l20-theta-stage-v1`; matched fresh
V/EMA/R,300 steps, writer and R-to-V gain off. Only packet bytes cross.
Ten conditions/role with BOTH routes' own shuffles,shams,disabled controls
plus ideal/zero.1920 new readers and864 exact aliases. Both content gates
must pass before either comparative label. No source selection, parameter
sweep, new source writer, renewal cohort or separate DoorKey modification.

The comparison does not show theta unnecessary during source development:
R had already developed under theta feedback while writing. An instant copy
may exploit work already done by the theta-supported source. This result
separates “theta is a useful inherited record” from “theta is a cleaner,
more readable record than contemporaneous R”; only the former is supported
here. Even the latter is tested only through this fixed fresh-reader assay,
not a universal measure of information or every possible timescale.

Across the recent probes, accumulated history can buffer ongoing source
noise (D123), but the extra theta stage is not automatically another
readout-quality upgrade (D124). Those are different interventions. Do not
subtract their aggregate effect sizes or claim the entire cascade identified.
Fixed lambda.001/rho.002, normalization and nonlinear source feedback remain;
no autonomous genome, necessary low-pass mechanism, biological canalization,
learning-only disposition or E6 upgrade.

## Validation, freeze and resources

- **477 tests pass in120.47s**:114 D124,174 D123,104 D120,85 D119;
  no failures/errors/skips. External report
  [d124_tests_attempt1.xml](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/logs/d124_tests_attempt1.xml).
  Fixture root `tmp/d124_tests_attempt1`; disposable full-life5.305s,
  known bridge test1.258s. A pre-file template-edit assertion was corrected
  before test-file creation; no simulation/test failure or data impact.
- Retained bridge COMPLETE **22:51:31.632091 UTC**,29.1105407719s/235455B:
  six already-observed D117 terminal readers match saved states under original
  and independently restated equations, maximum error0. No new source writer.
- Freeze **22:53:03.969869 UTC**,536 inputs,zero main futures.
  SHA256 `de4af0d2a0f9c7c3875ba161dd8df90c8aadfdcfc0aa952f1ee303756f546d86`.
  D123's complete lineage and completed review pinned; six mutable trackers
  and this live review excluded. No science edits after tests/freeze.
- Disposable benchmark **22:55:26.003102 UTC**:20.6240441781s block,
  55.7921483731s hash checking. Forecast456.5766501706s,under600s,foreground
  allowed. Budget92934457B (~88.63MiB),raw block6744064B,
  benchmark5192058B (~4.95MiB). Disposable is not qualification data.
- Main COMPLETE **22:59:50.138338 UTC**, **114.6076352503s /42002613B
  (40.0568MiB)** after execution begins, excluding prior preparation/provenance
  checks.540 prepared inputs/19 output hashes.32 independent full-life
  replays,all1920 recipient paths,max dynamics error0,all864 aliases pass.
- Standalone NumPy/stdlib-only reconstruction from raw terminal states and
  original D117 source endpoints verifies both observers,all168 contrasts'
  means/CIs/block and life values/counts,384 primary packets and864 aliases.
  Maximum statistic discrepancy **5.5511151231e−17**, below1e−12 tolerance;
  packets/observer values/aliases exact. All540 input/19 output hashes match.
  Separate saved-file audit also passes:540 inputs/19 outputs,32 lives,
  1920 paths/864 aliases; metadata, summaries, COMPLETE/STATUS and hashes agree.

All data, outputs, tests, logs and caches under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation`; code/docs only here.
Six CPUs0–5 maximum, numerical threads1, bytecode off. Existing local
bytecode remains124 files/4195796B, newest mtime1788545213.016447.
No deletion,cleanup,commit,exclusion,retry or post-freeze science edit.
Original LAWS/preprint/historical L20 case pins unchanged. Other laws parked.

Final closeout rechecks all536 frozen/540 prepared inputs and19 outputs;
COMPLETE/STATUS,manifest and hash index agree. Four Python ASTs,shell syntax,
whitespace and2028 local Markdown links pass. Six mutable trackers and the
L20 row updated; historical science and bytecode unchanged. Nothing running.

## Artifacts

[Summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_theta_stage_v1_attempt1/summary.json),
[verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_theta_stage_v1_attempt1/verification.json),
[manifest](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l20_theta_stage_v1_attempt1/MANIFEST.json),
[completion](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l20_theta_stage_v1_attempt1/COMPLETE.json),
[output hash index](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_theta_stage_v1_attempt1/output_hashes.sha256).

SHA256 summary `035532cf11f1be1d7ff40a861fe8d3136f31627931bec517e074a2573a0391c1`;
verification `b95c6ac884052b7ef263c0820299a321aab0a9250e765f3a7b5c45fd3ccc7c3a`;
manifest `f1f3180e6fa63eb1bd6360a1362ed214fd49c9d118d2f1fe7b66d319d5eb3928`;
completion `57660d795e647182ded181825a70a005672853e88748c2c058401a5c0362d2a1`;
hash index `9f21851f0af6d6214f3073e51d271aeef08b39c3f50b1fb62f184073a0d06eb9`.

## Recommended next question — proposal only

Shift from more small endpoint-copying comparisons to theta's role DURING
source development: does its feedback help preserve useful content in R?
A bounded next test could start from the same pre-writing state and compare
theta-to-body feedback on/off during a fixed writing interval, while latent
theta writing, R feedback,noise,duration and fresh-reader assay stay fixed.
Primary: readability of instant-R records from feedback-on versus feedback-off
sources, with each route's own content/handling controls. This separates
maintenance of the source from extra cleaning of the outgoing record.

It would require new counterfactual source writer trajectories, not just
new reads of saved records, and would need a separate prospective contract
and runtime forecast. No new protocol,code,identity or run for that proposal
has been created. No need for another norm/rate/threshold sweep. D124 is
closed after audits; do not rerun it to pursue the desired sign.
