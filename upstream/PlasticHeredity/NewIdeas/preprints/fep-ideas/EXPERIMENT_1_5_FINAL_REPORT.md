# Experiment 1.5 final report

## Bottom line

Experiment 1.5 completed as a valid, exactly replayed prospective campaign.
Its preregistered scientific verdict is **`RECURRENCE_NOT_SUPPORTED`**.

The experiment nevertheless resolves the main technical ambiguity left by
Experiment 1 and establishes two narrower positive results:

1. **`MASS_ARTIFACT_CONFIRMED`** — the reversing legacy kNN/PCA cycle was
   caused by count-mass sensitivity introduced by smoothing counts before the
   CLR transform. Removing that scale term restores the expected fission and
   growth directions.
2. **`CALIBRATED_PREDICTION`** — adding either phase-calibrated anomaly
   observer produced small positive strict-8 log-loss gains in every frozen
   candidate-by-half block. Ranking improvement did not replicate across all
   blocks.
3. **`RULEBOOK_INSTRUMENT_QUALIFIED`** — both observers reliably assigned
   lower anomaly to held-out states under their native catalytic matrix than
   under a deterministically matched foreign matrix. The registered
   calibrated rulebook-mismatch score may therefore be carried into
   Experiment 2.

These results do not support variational free energy, active inference,
cognition, autonomous control, prebiotic chemistry, inheritance of a
multi-form probability repertoire, a universal origin-of-life mechanism, or
Platonic causation. They do not alter Experiment 1's sealed
`HYPOTHESIS_NOT_SUPPORTED` and `INVALID` verdicts.

## Completion and integrity

| Item | Result |
| --- | --- |
| Development | 80/80 cells sealed; 80/80 exact replay |
| Confirmation | 480/480 cells sealed before analysis |
| Confirmation replay | 480/480 exact in fresh processes |
| Analysis firewall | Intact |
| Integrity verdict | **`VALID`** |
| Scientific verdict | **`RECURRENCE_NOT_SUPPORTED`** |
| Sealed analysis | 2026-08-19 01:00:32 UTC |
| Wall-clock span to analysis seal | 9 h 21 min 54 s, including an operator pause |
| Capsule size | 2.6 GiB |

All eleven registered integrity gates passed: validation, traced/untraced
equality, endpoint validation, deterministic observers, scale invariance,
relabeling invariance, seed separation, exact development replay, exact
confirmation replay, complete cohort retention, registered source identity,
and the analysis firewall.

Independent close-out checks also passed:

- reopening the existing full analysis verified the complete sealed chain;
- the pinned environment matched `requirements-15-lock.txt`;
- `python -m pytest -q` passed all 17 tests; and
- the 2.6 GiB `runs15/` tree is ignored by Git.

The detached wrapper exited without replacing its initial `running` marker.
At close-out no campaign PID remained, the last scientific artifact had been
sealed for roughly nine hours, and the sealed-chain verifier passed. Only the
unsealed runner metadata was reconciled to `complete`; no scientific artifact
or checksum manifest was changed.

## Design and event yield

The frozen design used 40 development matrices and a disjoint confirmation
cohort of 160 natural-GARD matrices plus 40 homogeneous-generative and 40
fission-only-generative matrices. Both simulator candidates were evaluated.
Each cell used five landmarks and 128 untouched 32-fission futures split into
fixed halves A and B.

The confirmation cohort contained:

- 204,800 natural-GARD futures;
- 102,400 generative-null futures; and
- 3,519 strict-8 events in natural GARD, a rate of **1.718%**.

Candidate 02 produced 1,711 strict-8 events in 102,400 futures (1.671%);
candidate 03 produced 1,808 (1.766%). Neither null mechanism produced a
strict-8 event in 102,400 combined futures.

## Primary recurrence result

The primary claim required both registered contrasts to pass for both
observers, both simulator candidates, and both branch halves.

| Registered component | Replication result |
| --- | --- |
| Phase-adjusted break excess | 8/8 observer/candidate/half blocks passed |
| Strict-8-specific recovery | 5/8 blocks passed |
| Scale-invariant kNN observer gate | Failed |
| Cosine-shelf observer gate | Failed |
| Global recurrence gate | **Failed** |

Candidate 02 passed both contrasts under both observers and both halves.
Candidate 03 retained positive break excess in all four blocks, but its
strict-specific recovery replicated only for invariant kNN in half A. The
other three candidate-03 recovery estimates remained negative in direction
but had 95% intervals crossing zero. Because the frozen rule required every
block, neither observer passed and the only valid adjudication is
`RECURRENCE_NOT_SUPPORTED`.

This is a replication failure, not evidence that every recurrence component
is absent. Break-associated anomaly is robust, and the recovery direction is
descriptively consistent. The strict-specific component is too weak or too
contract-dependent to support the registered observer-robust claim.

The null panels make the boundary sharper. Positive break excess also appeared
in many homogeneous and fission-only blocks. Break anomaly by itself is
therefore not a hereditary signature. The nulls contained no strict-8 or
run-8 events, so they could not estimate the strict-specific recovery
contrast; their failure to show the complete pattern is informative but is
not a positive null estimate of that contrast.

## Why Experiment 1's estimators disagreed

The diagnostic legacy observer reproduced the reversing signs from Experiment
1 in every candidate-by-half block:

- legacy fission shock was about -1.52 to -1.55;
- legacy growth change was about +1.53 to +1.55;
- the isolated fission scale term was about -2.38 to -2.42;
- the isolated growth scale term was about +2.52; and
- the composition-only terms had the expected signs: about +0.86 at fission
  and -0.98 during growth.

All 24 frozen sign tests passed. The additive decomposition closed to a
maximum absolute error of `7.11e-15`. At scientific scale the largest primary
observer rescaling error was `1.26e-12`, inside the registered `1e-10`
tolerance.

The conclusion is technical but decisive: the legacy reversal was produced by
mass-sensitive count smoothing, not by an opposing biological recovery law.
This explains the estimator disagreement in Experiment 1; it does not rescue
that invalid campaign or establish the stronger recurrence hypothesis.

## Prospective strict-8 prediction

The formal prediction verdict was **`CALIBRATED_PREDICTION`**:

- baseline-minus-enhanced log-loss gain passed in 8/8 frozen blocks;
- mean gains were small, ranging from `+0.0128` to `+0.0326`; and
- Holm-adjusted p-values were below 0.05 in every block.

The separate ranking gate failed. Enhanced-minus-baseline concordance passed
in only 4/8 blocks: 1/4 for invariant kNN and 3/4 for the shelf observer. Thus
the anomaly variables improved calibrated probabilities consistently but did
not provide a universally replicated ordering of which individual futures
would become strict-8 positive.

The descriptive permutation control also counsels restraint. Six of the eight
observed log-loss gains lay inside the reported permutation-null quantile
bands; only the two candidate-03 shelf blocks exceeded the displayed upper
quantile. The permutation panel was not the preregistered decision test, so it
does not reverse the formal verdict. It does suggest that much of the gain may
come from calibration or stratified prevalence refinement rather than a strong
event-specific anomaly signal.

The appropriate claim is therefore **small replicated calibrated forecast
gain**, not robust strict-8 discrimination or inheritance of a probability
repertoire.

## Rulebook mismatch and observer reliability

Reference-half reliability passed in all four observer/candidate blocks.
Mean cross-half Spearman correlations were 0.869-0.871 for invariant kNN and
0.931-0.932 for the shelf observer; every 95% lower bound exceeded 0.86,
comfortably above the registered 0.50 floor.

Native specificity passed all eight probe/observer/candidate tests. The mean
foreign-minus-native anomaly was:

- 2.61-3.06 for invariant kNN; and
- 6.72-7.07 for the shelf observer.

Every interval was positive. Experiment 2 may therefore use

`D(beta -> beta' | c) = A_beta'(c) - A_beta(c)`

under the frozen name **calibrated rulebook mismatch**. It is an operational
anomaly contrast, not a log-likelihood ratio, thermodynamic free energy, or an
observer-independent property.

Shelf-destination analysis remains restricted. Only 41/160 candidate-02 and
39/160 candidate-03 natural matrices met the preregistered stable multi-shelf
eligibility rule: 80/320, or 25%. This is not evidence that a multi-form
repertoire is the general inherited object.

## Consequences for the preprint

Experiment 1.5 strengthens the computational and reproducibility story but
does not justify expanding the four-chapter preprint toward FEP, active
inference, inherited probability repertoires, or Platonic forms.

The cleanest new statements are:

- Experiment 1's kNN reversal was a count-mass artifact;
- deterministic, scale-invariant anomaly scores contain small calibrated
  strict-8 forecasting information;
- viable and certification states are strongly specific to their catalytic
  rulebook; and
- the full observer-robust recurrence hypothesis was not supported.

Any manuscript use should label Experiment 1.5 as a separate, valid diagnostic
experiment and preserve Experiment 1's negative scientific and integrity
verdicts unchanged. It should not silently merge the provisional Chapter 5
draft into the current preprint.

## Recommended next transition

Preserve `runs15/full/` unchanged and back it up outside Git. No correction
rerun of Experiment 1.5 is required: its replay and integrity gates passed.

The justified next study is Experiment 2, the fixed-state rulebook-mismatch
and prospective-rehoming test. It should:

1. hold composition fixed while applying frozen, graded beta changes;
2. test whether calibrated rulebook mismatch predicts departure probability
   and latency;
3. test destination capture only in prospectively eligible multi-shelf cells;
4. compare against edit magnitude, ordinary geometry, and matched null edits;
5. retain exact replay, relabeling, scale, and seed-firewall gates; and
6. separate calibration from ranking, promoting the outcome-permutation panel
   to a gate if event-specific prediction is claimed.

## Sealed identifiers and artifacts

- Validation: `9552dcefb3a204053a4dd969f025b5d741696e459bce19f7b83d3e4046c9075a`
- Registration: `2f94efee37aafc82d578941b5da5fbdcfd54723a82f8d205b9a2ae2cbe364420`
- Development: `2ca4d99d17305832c34feecd099dbe7d88b508d9afa4595b4b80c47c168ae7dd`
- Confirmation: `699d92970251229a339c1576378243d39dd7877efe3c092743a6120ba7c395c3`
- Confirmation replay: `5ff6882f3bfde2c93e1dd88ee6791526eec59da024a8b08511f94dc6f520d220`
- Analysis: `471018e0a1ef2b7d2453c1436fdb0240a0bf0e87334750b08cf6c4dd9e79b57b`

Primary local artifacts:

- `runs15/full/registration/protocol.json`
- `runs15/full/development/development.json`
- `runs15/full/confirmation/confirmation.json`
- `runs15/full/confirmation_replay/replay.json`
- `runs15/full/analysis/analysis.json`
- `runs15/full/analysis/metrics.json`
- `runs15/full/analysis/REPORT.md`

The generated capsule is intentionally excluded from version control by
`.gitignore`; this report is the tracked human-readable close-out record.
