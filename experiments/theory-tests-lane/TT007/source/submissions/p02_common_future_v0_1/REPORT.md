# P02 common-future analysis: mixed development evidence

The specified signed record statistic adds a modest predictive increment, but
this analysis does not establish P02. Most of the aggregate spacing advantage
shrinks when current outputs are matched. A simple current-margin choice also
outperforms the signed-transfer choice on those matched pairs. Preserve both
findings; there is no basis here for announcing hidden reconstruction capacity
as the explanation of the spacing result.

This package completes the first operational P02 analysis using saved data.
There are no new native simulations and no unexposed outcomes. Earlier negative
P01 short-probe results remain unchanged.

## The question and its boundary

P02 asks whether states with similar current expression have predictably
different continuation under the same future apparatus. We use generation 14,
the first body after the two six-event schedules have ended. Original (O),
single-pulse (P), spaced and clustered histories all use the original writer
from this boundary through generation 32. Repeated tolerance rewriting is
excluded because it would change the future apparatus.

Current expression comprises four task-aligned native mean output signals,
their minimum margin and strict pass status. The endpoint is the separate
generation-32 scattered terminal assay. Candidate signed transfer and comparator
unsigned access are computed from the actual O packet derived from the observed
generation-14 bodies. They are linear record diagnostics, not native success
probabilities. The full boundary and a checkable sufficiency derivation appear
in [THEORY.md](THEORY.md).

There are 512 history-lineage records: eight blocks, four founders, four
recipients, four histories. All related records in a block are excluded together
when making that block's forecasts. Models use the frozen ridge penalty 0.01,
training-only standardization and no parameter or feature search.

## Matched expression weakens the aggregate spacing interpretation

All comparisons below pair spaced and clustered histories within the same
block/founder/recipient. Counts describe the selected pairs, without a causal
mediation interpretation.

| Selection | Pairs | Spaced terminal success | Clustered terminal success | Difference |
|---|---:|---:|---:|---:|
| All contexts | 128 | 109/128, 85.16% | 98/128, 76.56% | +8.59 pp |
| Both pass at generation 14 | 90 | 81/90, 90.00% | 79/90, 87.78% | +2.22 pp |
| Both pass; four output differences ≤0.02 | 84 | 75/84, 89.29% | 74/84, 88.10% | +1.19 pp |
| Exactly equal four outputs | 0 | — | — | — |

The fixed close-output criterion retains 65.625% of the original pairs and
covers every block. The average maximum output difference within these pairs is
0.00087846, with maximum 0.01209894. The 0.02 caliper was not widened, swept or
optimized after observing this result. It is an operating definition in unit
output amplitude, not a validated equivalence margin.

Of the 84 close-output pairs, 70 pass terminally in both branches and five fail
in both. Only nine are discordant: five favor spaced and four favor clustered.
The three fixed choice rules give:

| Choice on all 84 close-output pairs | Terminal successes | Correct on 9 discordant pairs | Regret versus hindsight |
|---|---:|---:|---:|
| Always spaced | 75/84 | 5/9 | 4 |
| Larger current minimum margin | **77/84** | **7/9** | **2** |
| Larger signed record transfer | 76/84 | 6/9 | 3 |

The hindsight oracle succeeds on 79/84; it is not an available decision rule.
There are no exact feature ties on the nine discordant pairs. The small count
precludes a strong ranking claim, but it supplies no evidence that signed
transfer is needed for better choices than current margin in this subset.
These are retrospective choices, not a prospective repair trial.

Matching is also uneven across blocks:

| Block | Close-output pairs | Spaced successes | Clustered successes |
|---|---:|---:|---:|
| 34000 | 8 | 8 | 6 |
| 34001 | 11 | 9 | 10 |
| 34002 | 9 | 9 | 9 |
| 34003 | 11 | 11 | 9 |
| 34004 | 14 | 14 | 13 |
| 34005 | 13 | 8 | 10 |
| 34006 | 7 | 6 | 6 |
| 34007 | 11 | 10 | 11 |

The aggregate counts are pair-weighted descriptions; the eight blocks remain
the inference units. Three matched block differences favor spaced, three favor
clustered and two tie. Approximate matching and one realized continuation per
state cannot establish equality of present probabilities or inequality of
latent continuation capacities.

## Fixed forecasts retain a narrower positive lead

The following scores average equally across the eight excluded blocks. Lower
is better. Every expression model includes the four output signals, minimum
margin, current pass and three history indicators. Quadratic models additionally
include all ten degree-two products of the four output signals.

| Frozen model | Brier error | Log loss |
|---|---:|---:|
| History-only smoothed rate | 0.114485 | 0.386386 |
| Expression + history | **0.085260** | 0.308933 |
| Expression + history + unsigned access | 0.087577 | 0.320590 |
| Above + signed transfer; secondary candidate | 0.080065 | 0.302997 |
| Quadratic expression + history + unsigned access; primary baseline | 0.092186 | 0.336447 |
| Above + signed transfer; primary candidate | **0.087626** | 0.324966 |

The declared primary addition improves Brier error by 0.004560, or 4.95%
relative to its fixed baseline. Six blocks improve and two worsen. Log loss
also improves. The fixed secondary addition improves Brier error by 0.007513
(8.58%), again in six of eight blocks.

That positive increment needs a substantial qualification: the primary
candidate still performs worse than the simpler expression-and-history model
(0.087626 versus 0.085260). Adding unsigned access or quadratic terms did not
make a stronger empirical baseline on these blocks. The primary comparison
therefore does not demonstrate that this more elaborate reconstruction-based
predictor is necessary. The secondary signed model is promising and has the
lowest observed aggregate error, but we do not promote it to the primary result
after seeing the scores.

Continuous current expression alone already improves on the history-only rate
in all eight blocks. Signed transfer may add information in the less flexible
model, yet its apparent value is sensitive to the declared rival. It deserves a
narrow follow-up hypothesis, not an RDT confirmation.

| Excluded block | Primary Brier improvement from signed transfer |
|---|---:|
| 34000 | −0.005111 |
| 34001 | +0.003396 |
| 34002 | +0.008059 |
| 34003 | −0.000753 |
| 34004 | +0.010701 |
| 34005 | +0.003847 |
| 34006 | +0.008326 |
| 34007 | +0.008016 |

All per-history scores, forecasts and fitted coefficients are retained. No
confirmatory significance test, benefit threshold or untouched-cohort claim is
made. Eight excluded folds from already exposed development data are not eight
independent replications of an outcome-blind hypothesis.

![Fixed matching and predictive comparisons](results/p02_comparison.png)

## What this changes in the theory

The strongest defensible claim is conditional and limited: this signed linear
record diagnostic yields a small incremental forecast improvement in the two
fixed model comparisons, while current expression explains much of the raw
history difference and provides a competitive simple predictor. The present
matched-pair decision test favors current margin over signed transfer.

P02 remains **unconfirmed, with mixed development evidence**. Ordinary latent
state, nonlinear expression dynamics and outcome variation under the declared
future remain adequate competing explanations. The exact sufficiency result in
THEORY.md is a derivation under stated assumptions, not a discovery from these
data. There are no exactly expression-equal observed pairs and no repeated
future draws to estimate each state's continuation probability.

The weakest empirical assumption is that signed transfer summarizes something
about future reconstruction that a sufficiently strong current-expression
predictor cannot capture. The most damaging feasible test would freeze the
models, evaluate genuinely unexposed contexts, and repeat future disturbance
draws for matched states. A viable record intervention preserving expression
would further address mechanism. This package neither designs away the negative
comparisons nor launches a confirmatory cohort.

The next theoretical decision is to keep signed transfer as a narrow candidate
and move to P03's damage/resource boundary, unless the user chooses a separately
specified P02 confirmation programme. P01's earlier generation-1/generation-3
negative forecasts and the pulse-recovery counterexample remain in force.

## Provenance, checks and handoff

The definition snapshot predates this extraction and model fitting but postdates
exposure to all source outcomes. It is not preregistration. Source manifests,
case arrays, native boundaries and existing CSV records were checked against
the completed-run hashes. The extraction reconstructed all 512 O captures and
current scores and cross-checked 1,024 CSV rows. It took 0.93 seconds; matching
and all 40 logistic fits plus eight rate calculations took 0.46 seconds.

Eight synthetic tests passed, including whole-block label/preprocessing
isolation, future-field exclusion, missing/duplicate panels, matching boundaries
and decision ties. A separate verifier imported none of the analysis or core
modules. It checked all 512 native output/target records, 3,072 predictions,
48 saved fits/rate calculations, 240 block/history score rows, all 128 pairs,
all subset and decision tables, and 32 independently assembled dense native
reader/capture contexts. All checks passed. This is a separate implementation
within this lane, not external replication or a new full dynamics rerun.

Useful artifacts:

- [P02 card](prediction_manifest.json), [protocol](PROTOCOL.md),
  [configuration](config.json), [exposure record](EXPOSURE_AND_DECISIONS.json).
- [Analysis](results/analysis.json), [records](results/records.csv),
  [pairs](results/pairs.csv), [predictions](results/predictions.csv),
  [scores](results/scores.csv), [fits](results/fits.json).
- [Extraction receipt](results/extraction.json),
  [verification receipt](results/verification.json),
  [definition snapshot](definition_snapshot.json).
- Standalone figure: [PNG](results/p02_comparison.png),
  [SVG](results/p02_comparison.svg), [PDF](results/p02_comparison.pdf).

The completed spacing and pulse source directories are unchanged. All work in
this package stays in the theory lane; no external messages or publication were
performed. No long task is running.
