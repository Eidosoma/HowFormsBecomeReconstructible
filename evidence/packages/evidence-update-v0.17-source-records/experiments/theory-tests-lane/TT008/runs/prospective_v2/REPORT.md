# TT008 prospective P02 validation

**PROSPECTIVE_IN_DOMAIN_PREDICTIVE_SUPERIORITY**. Independent native replay and scoring checks: PASS.

The fixed study completed 64 new blocks, 4,096 related history records and 24,576 sealed predictions. All predictions were sealed at 2026-10-10T05:13:36.139249+00:00 before any new post-boundary continuation. The model artifact and protocol were frozen before generating these blocks. No test-outcome refitting or model selection occurred.

The population, endpoint and supplied apparatus match the development experiment. This is in-domain validation of an openly selected development candidate. It does not change TT007’s original primary result, validate P01, establish a causal state-capacity inequality or demonstrate cross-apparatus RDT generality.

## Fixed primary comparisons

The gain is baseline Brier loss minus candidate Brier loss, averaged first within each block and then across 64 blocks. Both one-sided 95% lower limits must exceed 0.002. Student-t inference is approximate and conditional on the fixed training sample; each block keeps its related histories, paired founders and recipients together.

| Primary rival | Mean Brier gain | Lower one-sided 95% limit | Upper one-sided 95% limit | Positive blocks | Lower limit >0.002 |
|---|---:|---:|---:|---:|---|
| Expression + history | +0.008647 | +0.006698 | +0.010596 | 53/64 | True |
| Expression + unsigned | +0.009081 | +0.007231 | +0.010931 | 55/64 | True |

Conjunctive practical-superiority gate: **PASS**. A failed lower-limit gate does not establish equality. The 0.002 margin is an operational predictive threshold, not a physical-energy or fitness claim.

## All frozen rivals

| Model | Equal-block Brier error | Log loss |
|---|---:|---:|
| Signed-transfer candidate | 0.129131 | 0.444421 |
| Expression + history | 0.137778 | 0.461145 |
| Expression + unsigned | 0.138212 | 0.462362 |
| Quadratic + unsigned | 0.140094 | 0.471731 |
| Nonlinear expression rival | 0.137932 | 0.468423 |
| Nonlinear full-packet rival | 0.138251 | 0.546359 |

The nonlinear full-packet rival receives all 512 outgoing weights. The other nonlinear rival receives the expression/history/unsigned channels. Secondary rival rankings do not replace the two primary comparisons. All models use the same 512 exposed development labels; candidate and comparator training/tuning and representation costs remain distinct. Kernel predictions are clipped to [0,1]; reported log loss clips the scored outcome probability below at 1e-15.

## Histories and exploratory strata

| History | Terminal successes / 1,024 |
|---|---:|
| clustered_tolerance_rewrite | 728 |
| exact_rewrite | 852 |
| single_tolerance_rewrite | 854 |
| spaced_tolerance_rewrite | 802 |

| Generation-14 status | Records | Terminal successes | Gain contribution vs expression/history | Gain contribution vs expression/unsigned |
|---|---:|---:|---:|---:|
| Passing | 3424 | 2944 | -0.000152 | -0.000293 |
| Failing | 672 | 292 | +0.008799 | +0.009374 |

Stratum contributions sum to the overall gain. These are descriptive diagnostics. Later success is a fresh scattered assay after continued rebuilding, not recovery under the same current injury.

There are 602 strict spaced/clustered matches under the fixed both-pass/0.02 rule and 0 pairs with exactly equal output vectors. Approximate matches alone do not establish equal state-specific success probability. No repeated-future capacity estimate or causal mediation claim is made.

| Fixed decision rule | Selected successes | Discordant pairs | Correct discordant choices | Ties on discordant pairs |
|---|---:|---:|---:|---:|
| Signed-transfer candidate | 528 | 81 | 50 | 0 |
| constant | 528 | 81 | 50 | 0 |
| Expression + history | 528 | 81 | 50 | 0 |
| Expression + unsigned | 528 | 81 | 50 | 0 |
| Nonlinear expression rival | 526 | 81 | 48 | 0 |
| margin | 520 | 81 | 42 | 0 |
| Nonlinear full-packet rival | 525 | 81 | 47 | 0 |
| Quadratic + unsigned | 528 | 81 | 50 | 0 |
| signed | 525 | 81 | 47 | 0 |

## Technical evidence and limits

Erased scattered controls succeeded 0/1024. Independent scoring checked 15,360 terminal rows against raw cue/port means and all block loss contrasts by scalar arithmetic. The largest sealed-prediction reconstruction discrepancy was 0.

The complete known block passed every retained generation 3–32 boundary and terminal comparison before new test generation. Production acquisition and every new nonlinear read/capture were separately replayed byte for byte. Damage, reset, cue-end bodies, outgoing packets and temporal means are retained with array hashes. Source holding states are causally discarded and were not simulated; no holding-state endpoint is claimed.

The model search and sample plan used eight exposed development blocks. The plug-in 64-block power estimate was approximately 81.9% against the simple rival, versus 41.2% under the stated higher-variance sensitivity. No adaptation was made to improve those estimates after test access. Prediction separation is procedural within a shared filesystem, not independent custody or external replication.

Execution used one process and one numerical thread, CPU affinity [7]. The frozen runtime forecast was 18.75 hours. Inputs, fitted coefficients/kernel supports, registration, qualification, native arrays, predictions, scores, replay receipts and software identities are retained. The run has no automatic successor.

![Prospective results](tt008_results.png)
