# E054 — record interventions

**Complete and independently verified.** Finished **11 October 2026 at
14:48 UTC**, after **1h53m**, including the independent audit. The padded
6h38m launch forecast was conservative. Artifact closeout passed at **16:16 UTC**:
all 219 original scientific outputs, 24 frozen inputs, 102 original source
files, 1,632 inference summaries and figure provenance were verified. Independent
replay covered all **168,960 terminal cue observations**. Numerical controls passed.

Sensitivity to relative strengths depends strongly on rebuilding cue-noise history.
For h32 full-rewrite records, scattered-injury success under common fresh readers is:

| Record intervention | Shared rebuilding cue noise | Independent rebuilding cue noise |
| --- | ---: | ---: |
| Untouched | 86.52% | 95.90% |
| Permute magnitudes within sign classes | 12.11% | 94.34% |
| Equalize nonzero magnitudes | 39.06% | 96.68% |
| Coordinated cell switching, with transformed reset/noise | 86.52% | 95.90% |
| Isolated edge-sign flips | 13.28% | 16.02% |
| Delete the same edges selected for isolated flips | 81.25% | 94.92% |

The three primary contrasts concern the shared-noise history. Magnitude permutation
costs **74.41 points [69.92, 78.71]**; isolated signs versus coordinated switching
cost **73.24 points [68.42, 77.54]**. Both pass the declared loss-exceeds-five
criterion using family-adjusted 98.333% intervals. Deleting the selected edges
costs **5.27 points [3.32, 7.62]**: the loss is detectable, but its position relative
to the five-point threshold is **unresolved**. These are sensitivity classifications,
not an overall success/failure verdict for E054.

Independent-noise magnitude permutation has a secondary effect of **−1.56 points
[−2.93, 0.00]** (pointwise 95% interval). Its small effect, versus the shared-noise
result, supports studying which aspects of signed strength organization different
rebuilding histories retain. It does not make magnitudes universally irrelevant.
The intervention doses differ, so loss sizes cannot rank the importance of signs,
strengths and connectivity on a common scale.

Uniform halving preserves normalized coupling and outputs exactly in this reader.
Coordinated switching preserves aligned coupling exactly; its largest output
discrepancy is **2.22e-16**, with identical success outcomes. This control transforms
the reset and noise along with the record. Exact restoration reproduces trajectories;
erased records give zero success. These controls qualify the comparisons under
the declared normalized reader; they do not establish arbitrary sign-flip invariance.

Deleting the selected subset of newest returning repairs leaves aggregate success
unchanged in both full-rewrite histories. This terminal assay does not test whether
those repairs were needed earlier or would matter during another rewrite. Relative
to matched-other deletion, the shared-noise effect is **+2.54 points [1.17, 3.91]**,
a secondary pointwise comparison. Records and sources are reused from E051;
the fresh-reader interventions are not an independent source-cohort confirmation.

[Audited report](runs/interventions_v1/REPORT.md),
[full intervals and diagnostics](runs/interventions_v1/summary.json),
[independent audit](runs/interventions_v1/INDEPENDENT_AUDIT.json),
[figure](figures/interventions_v1/record_interventions.png),
[closeout receipt](analysis/closeout_v1.json).

Design fixed before intervention outcomes; no settings changed at launch.
Nineteen executable checks and both retained technical runs passed. Each independent
audit replayed source extraction, all interventions, graph/coupling diagnostics,
reader trajectories, scores and 1,632 summaries. All 24 frozen input hashes match.
E053 completion, independent audit and closeout are required by the launcher.
No automatic successor or polling. After a separate user instruction, E055
completed technical validation and launched its frozen pulse/capture test on
11 October at 16:48 UTC.

[Launch verification](analysis/scientific_launch_verification_v1.json),
[job status](jobs/interventions_v1/status.json),
[frozen scientific manifest](jobs/interventions_v1/manifest.json).

The question is which features of a record let a fresh body recover its task:
relative weight magnitudes, coordinated signs, or access through connections.
Use all 32 audited E051 blocks, with acquired records and four h32 histories:
full rewrite/preservation × matched/independent cue noise. E051 supplies the
policy comparison missing from E053. Reusing these records is explicit; this is
a mechanistic follow-up, not a fresh confirmation of the earlier result.

Eleven arms include magnitude permutation/equalization, anchored coordinated
switching versus matched isolated sign flips, deletion of the same flipped edges,
and newly repaired versus matched-other-edge deletion. Untouched, uniform scaling,
exact restoration and erased records provide controls. Every arm uses the same
fresh reader; switching also transforms reset/noise to test the predicted symmetry.
No rewriting intervenes between perturbation and the functional assay.

The primary sensitivity family uses h32 matched-noise full rewrite, scattered
injury. Three contrasts get simultaneous Bonferroni bootstrap intervals. Both-cue
function, signed transfer, normalized couplings, graph parity, reachability, actual
edit exposure and policy interactions remain available for all histories/injuries.
Different perturbation doses do not rank feature importance by loss size alone.

- [Fixed protocol](PROTOCOL.md)
- [Pinned source receipts](SOURCE_DATA.json)
- [Design snapshot](analysis/design_v1/manifest.json)
- [Implementation](model.py) and [independent replay](audit_model.py)
- [Executable checks](tests.py) and [19-check result](analysis/tests_v1.log)
- [Readiness receipt](analysis/technical_v1.json)
- [Fixture audit](runs/fixture_v1/INDEPENDENT_AUDIT.json) and [benchmark audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json)
- [Runtime and storage forecast](analysis/forecast_v1.json)

Preparation used one single-thread worker. The conservative scientific forecast was
**6h38m with eight workers**, including independent replay; storage reserve is
1.27 GB (1.18 GiB). This is a padded forecast, not a measured scientific runtime.

The fixture completed normally in 37.58 seconds. The benchmark simulation completed
in 12.94 worker seconds; its supervisor then exited with signal status 143 before
starting the audit. Cause unknown. The complete simulation and original logs were
preserved and verified; the remaining audit (17.96 worker seconds) and figure were
completed manually using unchanged frozen code. No simulation was repeated.
[Interruption record](jobs/benchmark_v1/INTERRUPTION.json).

The explicit scientific launch command used was:

```bash
bash run_python.sh E054_record_interventions/workflow.py --mode scientific --workers 8 --detach
```

The command refuses incomplete predecessor evidence, changed frozen inputs,
missing technical receipts, inadequate disk reserve or excess active numerical
workers. Scientific completion includes independent replay and an audited figure;
the user requests subsequent status checks.
