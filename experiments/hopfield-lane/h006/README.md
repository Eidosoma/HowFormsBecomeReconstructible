# H006: direct record interventions at matched current function

The [frozen protocol](PROTOCOL.md) follows H005's small, unqualified future
difference with direct interventions on the same acquired record. H006 flips
balanced positive and negative connections at two locations: cue-to-output
and cue-to-hidden. The controls preserve the entire weight histogram, record
norm, nonzero count, perturbation size, number of flips per cue and supplied
reader gain. Hidden connections are an active comparator.

The study completed on **12 October 2026** and **does not qualify**. Dose 4
was the only selection candidate passing all frozen gates. Independent assay
validation retained **195 of 256 packets across all 16 networks**, with no
failed current gate. All ten scientific fixtures and **7,159 audit checks**
passed. Runtime was **17 minutes 21 seconds**. All five checksum manifests
verified and the finished figure was inspected. See the
[report](../runs/h006_development_v1/REPORT.md),
[summary](../runs/h006_development_v1/summary.json) and
[figure](../runs/h006_development_v1/overview.png).

| Variant | Independent current success | Terminal renewed success [marginal 95% interval] |
|---|---:|---:|
| Unchanged | 97.26% | 89.59% [87.42, 91.69] |
| Cue-to-output flips | 96.89% | 89.65% [87.48, 91.74] |
| Cue-to-hidden flips | 96.93% | 89.46% [87.28, 91.54] |

Unchanged minus output-flip renewal is **-0.07 percentage points** [95% interval
-0.20, 0.00]; hidden-flip minus output-flip renewal is **-0.20 points**
[-0.39, 0.00]. Both fail their ten-point minima and adjusted directional
bounds. All four route controls pass. Current equivalence remains a declared
finite-observer tolerance; it does not mean exact latent equality. Larger
doses failed selection and were not retried after opening futures.

A [post-result diagnostic](CLOSEOUT_DIAGNOSTICS.json), computed by
[closeout_diagnostics.py](closeout_diagnostics.py) from retained arrays without
new simulations, finds exact full-packet agreement with unchanged renewal
after the first replacement/write in **99.56%** of output-flip trajectories
and **99.42%** of hidden-flip trajectories, averaging base networks equally.
Initial agreement was zero by construction. Terminal agreement is 99.93% and
99.61%. These trajectories usually lost the intervention difference at the
first rewrite. Agreement with the unchanged branch does not imply correct
function or restoration of the initial ancestral packet. This is descriptive
evidence, not a new qualification test or a useful-repair claim.

A subsequent [mechanism diagnostic](LEAD_DIAGNOSTICS.json) identifies a
different intervention worth testing. All 195 unchanged matched packets can
be expressed as one binary activity outer product with its diagonal removed;
none of the 390 edge-flipped packets can be produced exactly by the fixed
two-observation writer. With no zero off-diagonal entries, that writer's two
binary observations must agree up to a global sign, which forces this outer
product form. This algebra helps explain why the small edge edits were
overwritten; it does not assert that every possible edit must converge.

H005 already contains **61 matched pairs in 22 networks** with the same source
activity at sites 0–23 and differences confined to hidden neurons 24–63.
Both records in each pair have that coherent outer-product form. Their packets
remain distinct in all eight branches through all 16 further replacements.
The [post-result subgroup outcomes](HIDDEN_PAIR_OUTCOMES.json) are current
success 97.23% versus 98.04% and future success 84.63% versus 89.50%.
The 4.87-point future gap is exploratory and below H005's ten-point minimum;
the 0.81-point present gap is a point estimate, not a newly passed equivalence
test. This selected subgroup does not rescue either experiment or isolate a
causal history effect.

The next candidate is to change a coherent hidden activity pattern and encode
it with the existing writer. Swapping an opposite-phase hidden-neuron pair
in both source observations produces a different valid record while preserving
the visible record block, full weight histogram and permutation invariants.
This algebraic construction was checked for all 195 H006 matched sources;
its actual reader performance and persistence were not simulated in those
diagnostics. The subsequent [H007 screen](../h007/README.md) passed tight
current matching and one-replacement functional retention at all four tested
swap sizes. Its nominated eight-pair swap reached 94.15% joint exact retention
of both distinct, functional records across 24 development networks. A separate
study is still needed to test different long-term durability. H006's negative
outcome remains unchanged. The diagnostic scripts are
[lead_diagnostics.py](lead_diagnostics.py) and
[hidden_pair_outcomes.py](hidden_pair_outcomes.py).

Five doses (4, 8, 16, 24 and 32 unique edges) are screened using **current
function only** on eight H003 development networks. Eight exact matching
probes and 64 independent validation probes test each dose. Choose the largest
dose that passes every one-point equivalence and coverage gate. Sixteen
separate H003 networks then test that one dose with their own probes. All
source networks are previously exposed development checkpoints; these are new
interventions and tapes, not a fresh-base confirmation.

Selection is sealed before the assay; the assay cohort, current validation and
directional forecast are sealed before futures. Failure at either current
stage stops the study without a fallback dose. If current validation passes,
every assay candidate gets eight common-future branches through 16 further
replacements. Seven record arms include exact restoration, donor swaps,
protected/cumulative-loss copies and read/write blocks. Both planned location
contrasts require a ten-point future effect and an adjusted positive bound.

From the lane root:

```bash
bash run_python.sh h006/launch.py --mode benchmark
bash run_python.sh h006/launch.py --mode development
```

Destinations are unique; the launcher refuses existing files. `--version`
retains a distinct technical attempt, and `--benchmark` can name its matching
completed engineering run. Each worker executes its own frozen source and
extracted inputs. The benchmark uses seed 12900 and forces the largest dose
solely to exercise the complete pipeline; it cannot select the study dose.

The runtime forecast includes the entire benchmark, scaled by 24 plus 25%
and 60 seconds. Runs over ten minutes detach with one worker, one numerical
thread, closed stdin and durable log/PID/status under the
[execution policy](../../RUN_POLICY.md). Status checks are user-requested.
All source, probes, masks, packets, bodies, controls and decisions remain
retained. Frozen H004/H005 results and the main forms manuscript are unchanged.

## Engineering benchmark — 11 October 2026

The complete excluded seed-12900 run finished in **79.27 seconds**, including
15.17 seconds through both present stages, 40.56 seconds of future simulation
and 21.28 seconds of retained-data audit. All six H006 fixtures, four original
dynamics fixtures and **524 audit checks** passed. All five checksum manifests
verified and the finished figure was inspected. See the
[engineering report](../runs/h006_benchmark_v1/REPORT.md).

The benchmark forced dose 32 regardless of current gates, as declared, to
exercise all eight futures and controls. This one-block engineering exercise
has no population verdict; its dose and outcomes do not select or retune the
main study. Its report's eight/sixteen-network description refers to the main
design; the engineering block itself is only seed 12900 in each stage.

The conservative forecast is **40.63 minutes**: the complete benchmark times
24, plus 25% and 60 seconds. A current-gate failure can finish earlier. The
protocol, model, observer, dose selector and future decision remain unchanged
after the benchmark.

The main study was launched detached on 11 October, **PID 3558288**, with one
worker and one numerical thread. All 24 extracted source blocks, the fixed
split, protocol, code and configuration were sealed before launch. Selection
and independent assay enrollment receive their own subsequent seals before
any futures. At that launch entry, no main-study observation had been inspected.
See the [launch ledger](../runs/h006_development_v1_launch.json),
[config](../runs/h006_development_v1/config.json) and
[status](../runs/h006_development_v1/STATUS.json). The later user-requested status
check found the completed result above. No H006 job remains running.
