# Forecast validation: useful learning, conditional forecast reliability

**Completed 22 September 2026.** The [analysis contract](FEP_FORECAST_VALIDATION_V1.md)
and [checker](check_fep_forecast_validation.py) were frozen before qualification
and the nine-environment calculation. The
[preceding attribution](FEP_STOPPING_ATTRIBUTION_V1_REPORT.md) remains a known
motivating result, outside the new panel.

**Learning pays on the new panel, and stopping improves average cost.** The
primary controller's net loss is .076026980 per task against .1 for always
asking, about 23.97% lower. It buys 46.33 calibration pairs instead of 64,
saving 27.61%, while improving on fixed calibration's .076392169 net loss.

**Uniform stopping improvement fails:** stopping is worse than fixed 64 in
three of the nine environments. The own-prior control matches the saved
root predictions exactly, but fixed-environment risk and learning-value
forecasts can disagree with actual performance. One losing case even has
an overestimate of current risk, so excessive confidence alone is not a
general explanation of the stopping problem.

Both original studies retain their original verdicts. In particular, this
new panel's average efficiency gain does not overturn the preceding failure
on its different, fixed independent/shared aggregate. No policy was changed
or promoted, and no unique FEP advantage was tested.

## Fixed question and model

The agent learns usefully in the preceding shared-fault task, but sometimes
stops on histories that make its sensors appear safer than they are. This
study asks whether that mismatch extends to a declared panel of new fixed
environments, while checking the different guarantee that applies under the
learner's own prior. It changes no controller and selects no repair.

The primary agent deploys the saved MAP-selected model; the strong comparison
deploys the saved posterior model average. Both saved stopping policies use
the full structural posterior for acquisition. The error models, .9/.1
structural prior, conjugate parameter priors and all response tables remain
fixed. Exact model evidence/VFE supplies inference. Acquisition uses Bayesian
future task loss and actual costs, with no information bonus or new EFE.

The task still supplies known-positive paired calibration, a stationary IID
error law, symmetric transfer to later fair binary targets, and access to a
perfect reference. Wrong reports cost 1, references .1, calibration pairs
.001, the later task horizon is 100, and the calibration cap is 64. There
is no deployment feedback learning. These resources and transfer assumptions
remain part of the model; dependence does not identify a physical cause.

## Why the own-prior control should agree

Let c count observed calibration error pairs and K_s(c) count the ordered
histories that reach c without an earlier stop under saved schedule s.
For a fixed stationary Q, their stopping probability is

```
P_Q(c_stop_s) = K_s(c) * product_e Q_e**c_e.
```

Under the original prior pi over structures and parameters, replace the
product by its integrated evidence m(c). The factor K_s(c) does not depend
on Q. Conditional on c and stopping, it therefore cancels from the posterior:

```
p(Q | c, stop_s) = p(Q | c).
r(c) = E_prior[R_Q(c) | c, stop_s].
```

Here r is the predicted risk of the actual deployed response table, even
when that table selects a single model. Its forecast still uses the full
acquisition posterior. The same conditional-expectation identity holds for
the value of finishing calibration. Averaging within any of the declared
forecast bins preserves the identity under this own-prior population.

This is an internal mathematical control, not evidence that the prior
matches a particular environment. A posterior mean need not equal the risk
at each individual parameter value. Counting only selected stopped histories
with unconditional multinomial weights would evaluate the wrong population.

## New environment panel

The primary population gives equal weight to nine predeclared laws. Sensor
A error is .05, .15 or .25; B error is twice that. For each reliability level,
dependence interpolates from independent errors through a midpoint to fully
nested A errors. The interpolation parameter is not Pearson correlation or
a physically identified common-cause strength.

| A error | B error | Independent Q | Midpoint Q | Nested Q |
|---|---|---|---|---|
| .05 | .10 | (.855,.095,.045,.005) | (.8775,.0725,.0225,.0275) | (.90,.05,0,.05) |
| .15 | .30 | (.595,.255,.105,.045) | (.6475,.2025,.0525,.0975) | (.70,.15,0,.15) |
| .25 | .50 | (.375,.375,.125,.125) | (.4375,.3125,.0625,.1875) | (.50,.25,0,.25) |

Cells follow error-pair order 00/01/10/11. None equals a previous truth
fixture. The old shared case is replayed only as an integrity check and
receives no weight in the new aggregate. This is a prospectively specified
finite panel after a known motivating result, not an independent sampled
replication or an assessment of all possible environments.

The high-error independent and midpoint cases already make always asking
optimal with known Q. Their presence prevents a selective usefulness claim;
failure to beat that reference there is not a surprising new discovery.

## Three registered questions, three separate answers

| Registered question, equal nine-environment panel | Primary MAP edit | Averaged controller |
|---|---|---|
| Learning pays versus always asking | **Pass:** .076026980 < .1 | **Pass:** .076016683 < .1 |
| Stopping is no worse than fixed 64 on average | **Pass:** −.000365189 | **Pass:** −.000140304 |
| Stopping is no worse in every environment | **Fail:** 6/9 improve | **Fail:** 8/9 improve |

Both full controllers learn usefully in six of nine environments. These
are exactly the six panel environments whose known-Q best response costs
less than .1. In the other three, always asking is already the best response
with known Q; the agent incurs extra costs while learning and sometimes
making less suitable decisions. This is a bounded functional success with
explicit limits, not a guarantee over all environments.

The primary saves 17.667535383 pairs on average and reduces net loss by
.000365189200137 relative to fixed 64, about .4780%. Averaging has a slightly
lower new-panel net loss than MAP, but it also uses a different stopping
schedule. This whole-controller comparison does not isolate model averaging
on matched histories and does not select a replacement controller.

| A error / dependence | Mean pairs, edit | Edit net loss | Fixed-64 edit | Edit minus fixed | Averaged net loss | Known-Q best raw loss |
|---|---:|---:|---:|---:|---:|---:|
| .05 / independent | 31.31743 | .019691865 | .020068166 | −.000376301 | .019837246 | .019 |
| .05 / midpoint | 41.07658 | .038433065 | .039119765 | −.000686699 | .038369348 | .037 |
| .05 / nested | 51.54171 | .059342685 | .059263897 | +.000078789 | .059361912 | .050 |
| .15 / independent | 51.96514 | .086276571 | .086228890 | +.000047681 | .086207526 | .081 |
| .15 / midpoint | 50.91287 | .112582092 | .113906125 | −.001324033 | .112205406 | .100 |
| .15 / nested | 63.17198 | .089110937 | .088904390 | +.000206547 | .089423050 | .085 |
| .25 / independent | 30.82230 | .100754641 | .101130949 | −.000376308 | .100761886 | .100 |
| .25 / midpoint | 35.39732 | .102403240 | .103247664 | −.000844424 | .102335630 | .100 |
| .25 / nested | 60.78686 | .075647724 | .075659678 | −.000011954 | .075648145 | .075 |
| **Equal panel** | **46.33246** | **.076026980** | **.076392169** | **−.000365189** | **.076016683** | — |

Net losses include calibration cost; the known-Q column is a no-learning
raw-loss lower bound, not an implemented controller receiving hidden truth.
The midpoint .15 case loses about 12.58% against always asking, including
calibration. Its raw loss is already .112072963, so this failure is not just
the price of buying observations. The known-Q raw optimum is .1.

For the averaged controller, fixed-64 mean loss is .076156987, mean calibration
count is 46.77258, and the only positive stopping gap is +.000164199500109
at .15/nested. All individual fixed/actual comparisons remain in the record.

## Forecast risk and forecast learning value differ

For each stopped history, completing to 64 integrates all possible future
observations under Q. Its net benefit subtracts the remaining calibration
charge. Positive benefit means improvement in expectation, not that every
realized continuation helps. The stopping-weighted mean must exactly equal
adaptive loss minus fixed-64 loss. The agent receives no evaluator Q.

The full record retains each environment, all six fixed predicted-risk
bins and all 65 stopping-count strata, including empty bins and helpful
stops. Forecast means under the new population use exact probability weights
and rigorous floor bounds of width at most 2^-40, about 9.095e-13. The bins,
policy decisions, benefit signs, physical losses and gates are exact. No
rounded forecast selects an action or decides a gate.

The table gives primary-controller averages over its actual stopping law.
Predicted columns are rounded from the rigorous intervals; their widths
are below 9.095e-13. Positive completion benefit means finishing helps;
negative means stopping helps. Every individual reachable stop has
nonpositive predicted completion benefit under the full original posterior.

| A error / dependence | Predicted raw risk | Actual raw risk | Predicted completion benefit | Actual expected completion benefit | Positive benefit given early stop |
|---|---:|---:|---:|---:|---:|
| .05 / independent | .029450549 | .019378691 | −.000285218 | −.000376301 | .0129% |
| .05 / midpoint | .035226658 | .038022300 | −.000224561 | −.000686699 | .0072% |
| .05 / nested | .052902418 | .058827268 | −.000149369 | +.000078789 | 28.6204% |
| .15 / independent | .080468032 | .085756919 | −.000118467 | +.000047681 | 14.7389% |
| .15 / midpoint | .087073354 | .112072963 | −.000496085 | −.001324033 | 31.8483% |
| .15 / nested | .090932246 | .088479217 | −.000006887 | +.000206547 | 20.3054% |
| .25 / independent | .099938938 | .100446418 | −.000312096 | −.000376308 | .1503% |
| .25 / midpoint | .099292825 | .102049267 | −.000353775 | −.000844424 | 1.4221% |
| .25 / nested | .082323526 | .075039856 | −.000019540 | −.000011954 | .1064% |
| **Equal panel** | **.073067616** | **.075563655** | **−.000218444** | **−.000365189** | **9.1562%** |

The aggregate last column conditions the whole equal-panel episode mixture
on stopping early; it is not the unweighted mean of the nine conditional
percentages. Early stopping occurs on probability .817203886, and beneficial
completion on .074824711 of all episodes. Their ratio is .091561864.
Positive weighted completion benefit is .000131200689042; negative benefit
is −.000496389889179. Their sum is the mean stopping gap. Thus the earlier
91.31% figure for the old shared truth does not generalize to this population.

On average the edit controller underpredicts raw risk by
[.002496039116980, .002496039117890]. Averaging underpredicts by
[.002421877758193, .002421877759103]. This diagnoses a population-dependent
forecast error, not numerical uncertainty or a contradiction of Bayesian
calibration under the learner's own prior.

The .15/nested case is an informative qualification of the earlier narrative:
current predicted risk .090932246 exceeds actual .088479217, yet the agent
declines completion whose true expected benefit is +.000206547. Mean
forecast benefit is −.000006887. A current-risk estimate can be conservative
while the forecast of improvement from further learning is too pessimistic.
The value of learning depends on the difference between present and future
risk, as well as cost. Correcting only present-risk confidence would not by
itself establish correct stopping decisions.

The fixed bins also show why a population average is incomplete. In the
.15/midpoint environment, the [.075,.1) forecast bin has probability
.251827540, mean predicted raw risk .086965209 and actual risk .123848583.
In .15/nested, the same bin contains probability .952102762, with predicted
risk .091027815 and actual .087273781. All bins, including low-probability
failures and the empty [.125,1] bin, remain in each environment file. These
are descriptive entries from the predeclared partition, not selected gates
or a basis for tuning.

## Own-prior consistency passes, with its intended scope

| Original prior population | Edit | Average |
|---|---:|---:|
| Mean calibration count | 42.461215214 | 42.644689792 |
| Predicted and integrated raw risk | .073661357634 | .073639758321 |
| Net task loss | .074085969786 | .074066205219 |
| Fixed-64 net loss | .074293019649 | .074252870774 |
| Completion benefit | −.000207049863 | −.000186665555 |

Both integrated net losses reproduce the sealed Bellman root values divided
by 100 exactly, as do the fixed-64 references. Stopping-path mass normalizes
exactly and expected purchases equal the stopping-count charge. Conditional
calibration in the declared bins follows the posterior identity above; it
is not an additional empirical success. The old shared-case integrity replay
also exactly reproduces its prior loss, count and completion-attribution
totals without entering the new panel.

## FEP interpretation and next step

The useful result is broader than one favorable shared-fault fixture: this
frozen agent learns useful decisions in all six new panel environments with
task headroom, and saves observations without losing average value on the
declared panel. The negative result is also clear: exact free-energy/Bayesian
inference does not promise accurate risk or learning-value forecasts at every
fixed parameter value. The joint model already contains these error laws;
this is not evidence that the truth lies outside the supplied model family.
Finite evidence and the difference between the prior population and these
fixed environments matter.

There is no unique FEP advantage here. VFE specifies inference/model evidence;
useful acquisition is supplied by task-sensitive Bayesian planning. Averaging
does not remove all fixed-environment stopping losses. The earlier information
bonus failures, original efficiency failure and partial-dependence regression
remain unchanged. A blanket increase in confidence caution is not validated
by this result, and none was applied.

**Next recommended:** one bounded design testing whether a reference answer
already bought for a task can also improve the world model used on later
tasks. Compare reuse of that observed feedback with the current no-update
controller, using matched initial actions and fully charged reference costs.
This would explicitly relax the current no-deployment-learning restriction;
it is not an existing capability or a proven remedy. Keep current-risk and
future-learning forecasts separate, preserve the known negative cases, and
declare the new comparison before calculation. This moves toward practical
online world-model learning without changing priors or adding a confidence
weight. No such successor was implemented or run here.

## Execution record

Preparation passed 4,849 checks in .172 seconds on the first execution. The
qualification compares the count recursions with directly enumerated ordered
histories and completions through cap 3, under the prior and every declared
truth. It includes outcome-dependent stopping, exact bin boundaries, signed
quantization and containment of the independently calculated forecasts.

A cap-12 benchmark of the same kernels forecast 470.8 seconds including a
sixfold extrapolation factor and I/O allowance. The main calculation started
with one process, below the user's four-CPU ceiling and ten-minute detachment
threshold. Main execution completed in **68.035693301 seconds wall and
68.002454378 seconds CPU**, one Python 3.10.12 process, on the first attempt.
There was no failure, correction, rerun or tuning after the freeze.

The prior calculation covers 814,385 count states. The nine new truths plus
the labeled integrity replay cover 8,143,850 truth-completion states. The
compact ledger records 259,142 reachable stopped-controller forecasts.
All **2,040,142 checks** pass, mostly repeated state/record invariants rather
than independent experiments. Maximum saved-display residual is
1.3877787807814457e-17; physical outcomes, attribution identities and gate
comparisons are exact. No optimizer or sampled trajectory was run.

Start: 2026-09-22 14:02:46.435624 UTC. Finish: 14:03:54.477580 UTC.
Readback verified 12 input, 28 output and 62 preserved entries. All earlier
frozen sources, reports and manuscripts remain unchanged. The complete
record is **5,526,010 bytes**. All generated artifacts use
`/mnt/bioIce1/fep-ideas/formal-checks/fep-forecast-validation-v1/attempt-01/`.
The record preserves snapshots, qualification and logs before the main run.
No manuscript integration or sister-project writing is part of this task.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Contract | 9,618 | `ae0423da32c804ec0f4b48cd3c0dffd7339324da27cf55f75713bfea7b0fda19` |
| Checker | 30,272 | `f6019a6feb21bf0498e5672bee4d4020ad6701b460c1ae814941d02d3e0d1c1b` |
| [Manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-forecast-validation-v1/attempt-01/MANIFEST.json) | 25,673 | `88410f24829e4230253d1f245f56d3bbf7638592d9c47fe36d57860186b159ee` |
| [Results](/mnt/bioIce1/fep-ideas/formal-checks/fep-forecast-validation-v1/attempt-01/RESULTS.json) | 179,709 | `946999c4cf65c0185686b90a56f33d21fbb981bceabc80bd22342910323e033e` |
| [Prior control](/mnt/bioIce1/fep-ideas/formal-checks/fep-forecast-validation-v1/attempt-01/PRIOR_CONTROL.json) | 33,644 | `a0b8be909335e489ad061a580c36bb04d2909426ce790a089ed3ed5be7ef7874` |
| [Stopped forecasts](/mnt/bioIce1/fep-ideas/formal-checks/fep-forecast-validation-v1/attempt-01/STOPPED_FORECASTS.jsonl.gz) | 3,504,883 | `35154325d6adc3101598f1fdc33f14d7fc87b48bf2b9abf6603c181491dd7100` |
| [Run log](/mnt/bioIce1/fep-ideas/formal-checks/fep-forecast-validation-v1/attempt-01/RUN_LOG.txt) | 1,479 | `1fabf8abdd44ebd3dabbda746c52fd971c6bc5d81ff200e353beba95639a7b8f` |

Each environment JSON contains the complete signed summaries, all fixed risk
bins and all stopping-count strata for both controllers. The manifest also
identifies preparation, qualification, the old-case replay and source copies.
