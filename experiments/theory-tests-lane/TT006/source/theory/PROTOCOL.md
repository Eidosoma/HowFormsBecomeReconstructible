# RDT-P01 native development and evaluator handoff

**DRAFT_NOT_REGISTERED; no native jobs launched.** This is a concrete specification for the next development step, not a claim that confirmation is ready. [The manifest](prediction_manifest.json) records unresolved quantities as null. Existing E041 robustness work and the supplied E051 partial results remain a separate programme; do not duplicate them or treat their completion as an untouched RDT holdout.

## 1. Measurement contract

The initial candidate domain is the inspected E041-style full-rewrite, fresh-body system with a fixed damage and cue/noise contract. Identify code by hash, packet source, taught rule, lattice/ports, dynamics, writer, damage distribution, renewal schedule and assay randomness. Each change defines a condition. A mismatch introduced only at terminal testing tests assay transfer, whereas a mismatch in the writer changes renewal; record those separately.

At each sampled packet boundary, develop a separate fresh assay body for the two cue signs. Classify:

- **A:** both output signs and strict margins pass the packet's declared ancestral rule under both cues.
- **B:** the same criteria pass the opposite rule under both cues.
- **Neither:** all remaining valid responses.

Preserve the native strict margin >.25 over the final 32 dynamics steps. These are inherited assay definitions, not invented theory benefit thresholds. The inspected implementation uses 2048 read steps, dt=.2, gain=2, input normalization by incoming absolute weight sum, and a prescribed early dynamics phase; record the complete configuration in the adapter instead of relying on this summary. An input with zero normalizer has zero normalized drive. Invalid/nonfinite simulations get a separate error status and the frozen failure-handling rule; they must not disappear from denominators.

Assays use clones and cannot modify the continuing record. Within-pair cue randomness, between-assay randomness, between-generation randomness and matched condition seeds are four separate design choices. Matched teaching/test randomness currently used in the reported E051 conditions is part of their scope, not evidence of broader noise generalization. Common random numbers across conditions may improve paired comparisons but do not create independent replicates.

The two-mode candidate fits 27 categories of short response histories (three categories at depths 0,1,2). Every estimator receives the same histories and measurement budget. The prototype fits their conventional four-state HMM likelihood with eight fixed starting points; its full settings are in `two_mode.py`. No hidden identity/readiness labels are supplied in this comparison. The native adapter must validate whether repeated stochastic assays have an observation law compatible with this model. Marginal equations and the full path likelihood are separate restrictions.

## 2. Bounded development before confirmation

Use deliberately exposed development packets to establish cost, assay repeatability, response-category occupancy and relevant variance. This package does not choose their count or launch native simulations. Required feasibility outputs are a hashed packet list; all assay/renewal counts; runtime and resource measurements; unobserved categories; convergence and boundary-fit frequencies; and joint-versus-marginal model diagnostics.

Check label symmetry, constant rates and the depth-two restrictions before spending a long-horizon budget. Fixed-record repeated assays without renewal distinguish assay variability from change caused by writing. Include erased/random packets, protected copying and a failed-reader control to ensure the assay distinguishes absence of content from inability to express it. Retain the cost of each probe, failed fit and control.

For full rewrite, a common positive weight rescaling leaves the normalized reader drive unchanged in exact arithmetic. It is a useful adapter consistency check, not a long-horizon prediction. Magnitude-dependent preservation policies and finite arithmetic break the generality of that observation. Do not transfer it to every writer condition.

Fit uncertainty must be assessed during development. The current toy code provides point estimates only. Candidate procedures are founder/block resampling and simulation-based calibration under explicitly fitted alternatives, including boundary rates and coupled/drifting mechanisms. A bootstrap interval alone cannot bound structural misspecification. A parameter confidence region must be propagated through equations (6)–(7), including rare-loss rates near one; unidentifiable forecasts receive wide bounds or an explicit abstention. An unsupported source row is recorded, not filled after viewing outcomes. Abstention rates and intervals as broad as [0,1] count against usefulness.

Set the numerical acceptance margin, required practical improvement, primary horizon, number of blocks, packets per block, paths per packet, tuning budget and uncertainty confidence level **only after** this feasibility evidence. Record rationale and a power/precision analysis using block dependence and the actual paired comparison. Do not infer a native sample size from the conservative toy union bound. Freeze these choices in a new manifest before confirmatory outcomes are accessible.

## 3. Comparison that can defeat the theory

The primary forecast is the three-category terminal distribution, scored at one subsequently frozen horizon. Recommended primary score is the categorical Brier score \(\sum_{c\in\{A,B,N\}}(\widehat p_c-1\{O=c\})^2\), averaged with equal weight per independent founder/block. The exact pooling and number of descendants within each block must be frozen. Secondary outputs are A-probability error, calibration, interval coverage/width, failure-to-fit and abstention. Log score requires a declared numerical zero-probability policy; it must not be introduced after observing failures. Repeated horizons are dependent and not extra independent sample units.

Baselines must include:

| Baseline | Fair comparison and possible interpretation |
|---|---|
| Current expression plus cohort forecast | Establishes whether short trajectories add information beyond what was already visible. |
| Ordinary output Markov model | Uses the same short paths; unsupported rows stay explicit. Any smoothing is fixed and tuned within development for every method that uses it. |
| Same structured conventional HMM | Exactly ties this candidate by construction. It prevents claiming a new mathematical mechanism from new terminology. |
| Strong learned predictor | Uses a fixed representation of initial packet/state plus the same available probes, with comparable tuning access and a frozen development-only selection rule. |
| Native dynamical/basin-sensitivity predictor where available | Adapts the strongest existing model-specific comparator; document its extra observations and cost. An oracle with full future dynamics is reported separately. |

Select one primary rival using a frozen development procedure or correct the family of comparisons. Do not claim improvement merely by beating a deliberately weak present-expression baseline. The candidate's possible merit is an accurate, economical reduction compared with more demanding models, not superiority over its identical HMM implementation. Claim predictive compression only with an explicit cost/accuracy comparison: record bytes alone omit assay simulation, sensing and fitting costs.

Recovery cases and histories matched for present expression are predeclared stress strata, not subsets chosen after failures. Fit own and foreign records under the same A assay if testing historical specificity. The within-record A-minus-B contrast is not a replacement. Terminal distribution is the P01 primary endpoint. All-cycle success requires separate joint success/successor recording and validation; it cannot be inferred by multiplying the marginal forecasts.

## 4. Separation, outcome rules and handoff

Separate development and evaluation by founder/history families and declared task/apparatus conditions, not solely new random seeds. Existing PH/Forms results, E041/E046 summaries and E051 aggregates are exposed. New combinations of already inspected families must be labelled accordingly. A programme-wide exposure check remains necessary: the local register cannot attest what other participants have seen. Theory and theory-tests are procedural lanes within one programme, not external replications.

Before any scored long continuation, save packet hashes, all short observations, fitted parameters, every baseline, predictive distributions/intervals, unsupported statuses, immutable analysis code, exact acceptance rules and the access/exposure record. Evaluators should check equations and implement scoring independently where feasible. The local snapshot supplies provenance; it is not external preregistration.

| Outcome | Interpretation fixed now |
|---|---|
| Accurate, calibrated, economical forecast; strong alternatives cost more | Supports the stated native reduction and its bounded domain. Does not establish autonomous machinery, new HMM theory or universal reconstruction. |
| Accurate but tied by a simpler/cost-equivalent model | Adequate conventional explanation; no demonstrated added predictive value for RDT. |
| Good point fit with failed uncertainty or frequent boundary errors | Reject the claimed reliability; retain the model only as an exploratory summary. |
| Marginal law fails or rates drift/couple | Reject this two-mode version in the declared domain. Any revised state/model gets a new version and new evaluation. |
| Short observations leave rates/forecasts unidentified | No informative test at that budget. Count the abstention and revise feasibility, not the outcome label. |
| Every method fails because assay/adapter is invalid | Apparatus failure; record it and repair the measurement contract before theory inference. |
| Mechanism changes but terminal forecast does not | Do not infer fragility from mechanism change alone; investigate which changes affect the response transition law. |

The evaluator can already reproduce the finite calculations and challenge their proofs. Native confirmation additionally requires the completed adapter, validated uncertainty, justified numerical thresholds, known block design, exposure audit and a fully populated freeze. These are scientific prerequisites, not a request for user approval.

## 5. Reproducing the calculations

Use Python with NumPy, SciPy, Matplotlib and pytest. The working environment used Python 3.13 and the existing PlasticHeredity virtual environment; exact library versions are in the snapshot. Set one numerical thread per process and keep caches local. From this directory:

```bash
python -B verify_snapshot.py
python -B -m pytest -q -p no:cacheprovider --basetemp=.cache/pytest
python -B develop.py calibrate --config development_config.json --output .cache/reproduction/toy_forecasts.json
python -B develop.py evaluate --calibration .cache/reproduction/toy_forecasts.json --output .cache/reproduction/toy_results.json
python -B two_mode_develop.py calibrate --output .cache/reproduction/observable_forecasts.json
python -B two_mode_develop.py evaluate --calibration .cache/reproduction/observable_forecasts.json --output .cache/reproduction/observable_results.json
```

Outputs refuse overwrite. Timestamps and elapsed times will differ. The frozen numerical results refer to the original artifacts in `results/`; preserve them. No native simulator or robustness sweep is invoked by these commands.
