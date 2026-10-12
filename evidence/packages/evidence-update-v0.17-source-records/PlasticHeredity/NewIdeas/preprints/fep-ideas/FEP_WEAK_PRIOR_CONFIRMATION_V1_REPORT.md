# Weak-prior confirmation: economical core recovery repeats on fresh data

**Completed 8 October; verified 9 October 2026.** All three prospective
confirmation criteria pass. Unchanged CT3-flat recovers more cheaply than
always checking, improves recovery against C3, and improves complete core
episodes against C3. It is now a confirmed lead for this fixed core population.
This is fresh Monte Carlo confirmation of a previously selected control,
not generalization to new physical worlds or an independent empirical replication.

Core recovery costs **.098875402 [.098674985, .099075818]**, versus .1 for
always checking and .102961931 for matched C3. That is a **1.12% saving**
against always checking and **3.97% against C3**. Core-full cost, including
calibration, is .085033137: **14.97% below always checking**.

The retained limitations are substantial. Pooled A/B reliability loss costs
.101345703 and transfer recovery .105625940, both above .1. Reversal remains
worse than C3, the first recovery window for a task-26 change worsens, and
111/270 core episode conditions worsen against C3. The positive population
mean does not imply uniform superiority. The earlier calibrated CT3 primary
failure and its reversal harm remain unchanged.

Main execution finished at **20:15:18.285437 UTC on 8 October** in
**8,339.931501712 seconds (2 hours 19 minutes)** on four CPUs. No job or
required readback remains pending. No successor was launched.

## Frozen design and FEP scope

The [prospective design](FEP_WEAK_PRIOR_CONFIRMATION_V1.md),
[wrapper](check_fep_weak_prior_confirmation.py) and
[historical launch checkpoint](FEP_WEAK_PRIOR_CONFIRMATION_V1_CHECKPOINT.md)
remain unchanged. All nine policies were imported from the frozen calibrated-
change implementation. No prior, policy, horizon, price or feedback rule changed.

There are 1,024 fresh paired blocks for each of 27 base sensor laws: 27,648
independent blocks and 525,312 physical episodes. The 513-condition population
is byte-identical to the preceding study: 270 core conditions and 243 separate
partial-corruption conditions. All stable worlds, failure families, change
times and zero-headroom cases remain. The earlier sample is not pooled in.

An episode has 64 known-target calibration observations and 100 deployment
tasks. A wrong report costs 1, a correct report 0 and a purchased answer .1.
Whole-episode means include .064 calibration cost divided by 100 tasks;
post-change/window costs exclude it. Always checking costs .1 without learning.
Core-full weights stable worlds by 1/2 and its nine changed conditions by
1/18 each. Transfer-full applies the analogous separate weighting. Changed
means normalize each condition by its 101−T remaining tasks, then average
conditions equally. More remaining tasks do not give a condition extra weight.

CT3-flat retains calibration for the old-phase joint law. It represents
no change or general/A-failed/B-failed change at supplied times 26, 51, 76.
The single-failure branches use Beta(1,1) new-rate priors for the other sensor;
CT3 instead transfers that sensor's original calibration distribution.
Both retain general change and model uncertainty. New-phase rates are
independent of the old law conditional on calibration, not exactly shared
latent rates; pre-change deployment evidence is not fully transferred.

Exact conditional VFE/Bayesian inference satisfies
`F(q;h,c)=KL(q||p(theta|h,c))-log p(h|c)`. The separately specified action
objective is contingent expected task cost over the present plus two future
decisions, shortened at the episode end. Only paid answers provide label
feedback. Bayesian inference and planning are foundations of this FEP track;
a uniquely FEP advantage is not required. The evidence supports useful action
under this supplied model, not a new canonical EFE, autonomous structure
learning or validation of the broad Free Energy Principle.

Intervals use independent blocks within fixed base-law strata:
`SE^2=sum_base Var(block_base)/(27^2*1024)`, with mean ±1.96 SE. Policy
contrasts are paired within each block. These are nominal Monte Carlo
intervals conditional on this population, not uncertainty over arbitrary
worlds or simultaneous coverage for every descriptive comparison.

## Prospective confirmation criteria

All three require a strictly negative upper 95% contrast bound. The first
is the primary endpoint; their conjunction confirms the comparative core lead.

| Criterion | Contrast | Mean [95% interval] | Verdict |
| --- | --- | --- | --- |
| Economical core recovery | Core-post flat minus .1 | -0.001124598 [-0.001325015, -0.000924182] | PASS |
| Better recovery than C3 | Core-post flat minus C3 | -0.004086530 [-0.004237622, -0.003935438] | PASS |
| Better complete core episodes | Core-full flat minus C3 | -0.000962826 [-0.001025044, -0.000900609] | PASS |


These were frozen before the new sample. The preceding control mean .099142091
motivated selection of CT3-flat, but contributes no observations to the new
estimate or its precision. The previous study's CT3 primary remains failed.
Its five old criteria, re-evaluated descriptively in `reference_CT3`, do not
replace the three confirmation criteria at the root of RESULTS.json.

## All policies, stable worlds and transfer

Every number below uses this new matched cohort. F freezes calibration; S
updates a stationary model; C models general change with current-task planning;
R resets on schedule; C-Y discards purchased labels from future inference;
C2/C3 plan one/two future tasks. CT3 and CT3-flat add supplied failure hypotheses
while retaining C3's horizon. Costs are per task, lower is better.

| Policy | Core full | Core post-change | Stable full | Transfer full | Transfer post-change |
| --- | --- | --- | --- | --- | --- |
| F | 0.121724834 | 0.247366234 | 0.079639204 | 0.091148886 | 0.125053710 |
| S | 0.127427724 | 0.273526374 | 0.079148210 | 0.092940303 | 0.134218704 |
| C | 0.088691621 | 0.113430893 | 0.080177616 | 0.088542275 | 0.114167433 |
| R | 0.093063923 | 0.103728183 | 0.090497892 | 0.094734976 | 0.110443231 |
| C-Y | 0.097900137 | 0.124532930 | 0.088573775 | 0.090756536 | 0.101415271 |
| C2 | 0.086793461 | 0.105819943 | 0.080308150 | 0.088188183 | 0.112336581 |
| C3 | 0.085995963 | 0.102961931 | 0.080441360 | 0.087975787 | 0.111089270 |
| CT3 | 0.088011062 | 0.112066744 | 0.079873218 | 0.086818351 | 0.108007397 |
| CT3-flat | 0.085033137 | 0.098875402 | 0.080368479 | 0.086586753 | 0.105625940 |


CT3-flat's stable mean narrowly improves C3: -0.000072880 [-0.000140082, -0.000005679].
It remains worse than calibrated CT3 on stable episodes:
+0.000495262 [+0.000439571, +0.000550953],
and stationary S is cheaper still. Retain these tradeoffs.

Transfer recovery improves against C3 by -0.005463330 [-0.005619787, -0.005306873],
but still exceeds always checking by +0.005625940 [+0.005407743, +0.005844138].
C-Y is also cheaper on transfer recovery. Partial A alone has a mean below
.1 but its interval includes .1; partial B alone falls below .1 at the nominal
interval. These are descriptive slices, not extra confirmation gates.

## Every family and time

The following post-change summaries combine all 27 base-law condition
records for each family/time, with paired stratified intervals. No row is
selected by headroom or benefit. All nine-arm condition results remain in
the sealed data, including their wrong-report and purchased-answer counts.

| Change | Task | R | C3 | CT3 | CT3-flat | Flat minus C3 [95%] |
| --- | --- | --- | --- | --- | --- | --- |
| A_loss | 26 | 0.109050203 | 0.107349730 | 0.099117139 | 0.099963397 | -0.007386333 [-0.007740956, -0.007031710] |
| A_loss | 51 | 0.109116464 | 0.108136719 | 0.100310619 | 0.100880136 | -0.007256583 [-0.007632463, -0.006880702] |
| A_loss | 76 | 0.108984664 | 0.110183304 | 0.103303819 | 0.103139468 | -0.007043837 [-0.007503481, -0.006584192] |
| B_loss | 26 | 0.108668981 | 0.106848814 | 0.099155382 | 0.100150318 | -0.006698495 [-0.007034347, -0.006362644] |
| B_loss | 51 | 0.108706525 | 0.107877821 | 0.100195313 | 0.100884910 | -0.006992911 [-0.007364925, -0.006620897] |
| B_loss | 76 | 0.108729601 | 0.110114873 | 0.103665943 | 0.103055990 | -0.007058883 [-0.007520742, -0.006597025] |
| reverse | 26 | 0.093604938 | 0.091561921 | 0.140186101 | 0.098918403 | +0.007356481 [+0.006791377, +0.007921586] |
| reverse | 51 | 0.093374711 | 0.090921296 | 0.131630498 | 0.089422164 | -0.001499132 [-0.001814728, -0.001183536] |
| reverse | 76 | 0.093317564 | 0.093662905 | 0.131035880 | 0.093463831 | -0.000199074 [-0.000603429, +0.000205281] |
| A_partial | 26 | 0.106649643 | 0.102031973 | 0.098803819 | 0.098617236 | -0.003414738 [-0.003653563, -0.003175912] |
| A_partial | 51 | 0.106678313 | 0.103119502 | 0.099806858 | 0.099524378 | -0.003595124 [-0.003870517, -0.003319732] |
| A_partial | 76 | 0.106747685 | 0.104982350 | 0.102146123 | 0.101160880 | -0.003821470 [-0.004172264, -0.003470676] |
| B_partial | 26 | 0.106428675 | 0.101860822 | 0.098857735 | 0.098722367 | -0.003138455 [-0.003371351, -0.002905559] |
| B_partial | 51 | 0.106258319 | 0.102741102 | 0.099780237 | 0.099354239 | -0.003386863 [-0.003654585, -0.003119142] |
| B_partial | 76 | 0.106308883 | 0.104397425 | 0.101591146 | 0.100776331 | -0.003621094 [-0.003966151, -0.003276036] |
| both_partial | 26 | 0.118137249 | 0.123916570 | 0.120861111 | 0.115005739 | -0.008910831 [-0.009257148, -0.008564514] |
| both_partial | 51 | 0.118358579 | 0.126378689 | 0.123080223 | 0.116787688 | -0.009591001 [-0.009988950, -0.009193053] |
| both_partial | 76 | 0.118421730 | 0.130375000 | 0.127139323 | 0.120684606 | -0.009690394 [-0.010177647, -0.009203140] |


Pooled reliability-loss flat-minus-C3 is -0.007072840 [-0.007249404, -0.006896277],
while flat-minus-CT3 is +0.000387667 [+0.000232698, +0.000542636].
Thus calibration transfer's local reliability benefit repeats, alongside its
large reversal harm. On reversal flat costs .093934799 and clears .1, but
still loses to C3 by +0.001886092 [+0.001627277, +0.002144907].

First-25-task windows retain a further limitation: after a task-26 change,
flat's mean .113113908 is above both C3 and scheduled reset R. Longer pooled
recovery can improve while the initial response worsens.

| Panel | Start | R | C3 | CT3 | CT3-flat | Flat minus C3 [95%] |
| --- | --- | --- | --- | --- | --- | --- |
| core | 26 | 0.103858989 | 0.108584635 | 0.133574653 | 0.113113908 | +0.004529273 [+0.003991921, +0.005066625] |
| transfer | 26 | 0.110352093 | 0.114657118 | 0.112045910 | 0.110330440 | -0.004326678 [-0.004561114, -0.004092243] |
| stable | 26 | 0.094065394 | 0.079911314 | 0.079062645 | 0.079777054 | -0.000134259 [-0.000234131, -0.000034387] |
| core | 51 | 0.103787857 | 0.105458430 | 0.122119792 | 0.100763792 | -0.004694637 [-0.004957278, -0.004431997] |
| transfer | 51 | 0.110370708 | 0.114013841 | 0.111000145 | 0.108939959 | -0.005073881 [-0.005326000, -0.004821762] |
| stable | 51 | 0.093431858 | 0.080131655 | 0.079495660 | 0.080161603 | +0.000029948 [-0.000106164, +0.000166059] |
| core | 76 | 0.103677276 | 0.104653694 | 0.112668547 | 0.099886429 | -0.004767265 [-0.005037695, -0.004496834] |
| transfer | 76 | 0.110492766 | 0.113251591 | 0.110292197 | 0.107540606 | -0.005710986 [-0.005988828, -0.005433143] |
| stable | 76 | 0.093317564 | 0.080517650 | 0.079729745 | 0.080330440 | -0.000187211 [-0.000351851, -0.000022570] |


Counts below give conditions where flat costs less/equal/more than each
reference. Point signs are determined from integer costs, not rounded means.

| Reference | Core episode lower/equal/higher | Core recovery lower/equal/higher | Transfer episode lower/equal/higher | Transfer recovery lower/equal/higher |
| --- | --- | --- | --- | --- |
| F | 188/0/82 | 179/0/64 | 168/0/75 | 166/0/77 |
| S | 184/0/86 | 175/0/68 | 169/0/74 | 165/0/78 |
| C | 183/0/87 | 176/0/67 | 189/0/54 | 189/0/54 |
| R | 249/0/21 | 186/0/57 | 193/0/50 | 172/0/71 |
| C-Y | 137/0/133 | 112/0/131 | 69/0/174 | 57/1/185 |
| C2 | 165/0/105 | 154/0/89 | 188/0/55 | 188/0/55 |
| C3 | 159/0/111 | 142/0/101 | 185/0/58 | 185/0/58 |
| CT3 | 83/0/187 | 96/1/146 | 82/0/161 | 84/2/157 |


Against C3, 111/270 core episode and 101/243 core recovery conditions worsen;
83 and 81 respectively have nominal lower contrast bounds above zero.
Transfer worsens 58/243 conditions for both endpoints, with 41 episode and
40 recovery lower bounds above zero. These counts are descriptive, without
multiplicity-adjusted discovery claims. The mean benefit coexists with these condition-level harms.

## Diagnostics and remaining cost

Flat usually buys an answer soon after core change: purchase probability
.999887474 and mean wait .061527456 tasks including censoring. Its core net
excess above always checking splits into +.000566728 before the first answer,
zero at the purchase, and −.001691326 afterward. The total is −.001124598.
These phase contributions divide by the full post-change task count; phase
selection is endogenous and does not identify separate causal interventions.

The core conditional physical cost is .098876908 versus a subjective
prediction .093720105. Risk underestimation remains, even though useful
pooled recovery now passes. For comparison, C3's gap is .010383146 and
calibrated CT3's .019906399, versus flat's .005156803. Flat reduces
insufficient checking but increases immediate excess-checking regret; the
full policy cost captures their combined effect and future consequences.

| Panel | Policy | Physical conditional cost | Subjective cost | Risk gap | Insufficient checking | Wrong direction | Excess checking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| core_changed | C3 | 0.102944420 | 0.092561274 | 0.010383146 | 0.010540515 | 0.001467064 | 0.004589153 |
| core_changed | CT3 | 0.112043653 | 0.092137255 | 0.019906399 | 0.005200411 | 0.016123313 | 0.004372241 |
| core_changed | CT3-flat | 0.098876908 | 0.093720105 | 0.005156803 | 0.004865533 | 0.002083087 | 0.005580600 |
| core_reliability | C3 | 0.108404515 | 0.092611160 | 0.015793355 | 0.012433004 | 0.000782409 | 0.003522435 |
| core_reliability | CT3 | 0.100895994 | 0.093340556 | 0.007555438 | 0.005676919 | 0.000556060 | 0.002996349 |
| core_reliability | CT3-flat | 0.101339570 | 0.094273046 | 0.007066524 | 0.005432014 | 0.000367822 | 0.003873067 |
| reverse | C3 | 0.092024231 | 0.092461502 | -0.000437271 | 0.006755536 | 0.002836373 | 0.006722590 |
| reverse | CT3 | 0.134338972 | 0.089730652 | 0.044608320 | 0.004247396 | 0.047257819 | 0.007124026 |
| reverse | CT3-flat | 0.093951583 | 0.092614222 | 0.001337361 | 0.003732570 | 0.005513616 | 0.008995666 |
| transfer | C3 | 0.111138485 | 0.090047032 | 0.021091453 | 0.016601364 | 0.000224995 | 0.001512015 |
| transfer | CT3 | 0.108009852 | 0.091124905 | 0.016884947 | 0.013813188 | 0.000075253 | 0.001321301 |
| transfer | CT3-flat | 0.105681630 | 0.091918645 | 0.013762985 | 0.011023763 | 0.000072665 | 0.001785092 |
| both_partial | C3 | 0.126976432 | 0.092715990 | 0.034260442 | 0.026697045 | 0.000279386 | 0.000000000 |
| both_partial | CT3 | 0.123654346 | 0.093538853 | 0.030115493 | 0.023619566 | 0.000034780 | 0.000000000 |
| both_partial | CT3-flat | 0.117477299 | 0.095177153 | 0.022300146 | 0.017429575 | 0.000047723 | 0.000000000 |


On reversal flat waits .135103202 tasks for a paid answer versus C3's
.024269387 and CT3's .761176215. Its remaining extra wrong-direction and
checking regret are consistent with the retained reversal cost against C3;
phase attribution alone does not prove a remedy. Under both partial
corruptions, flat's .017429575 insufficient-checking regret dominates the
remaining physical excess. This is still a costly task failure.

Mean flat posterior probabilities at task 100 are:

| Panel | No change | General G | A failed | B failed |
| --- | --- | --- | --- | --- |
| core_changed | 0.237787 | 0.211165 | 0.275730 | 0.275317 |
| core_reliability | 0.310035 | 0.074848 | 0.307854 | 0.307263 |
| reverse | 0.093293 | 0.483799 | 0.211484 | 0.211425 |
| transfer | 0.526157 | 0.098766 | 0.187824 | 0.187253 |
| both_partial | 0.382089 | 0.099550 | 0.259478 | 0.258882 |


Posterior labels are not functional success criteria. All other posterior
checkpoints, their intervals and planning diagnostics remain verified in
READBACK.json and the sealed arrays. The model retains uncertainty rather
than receiving a supplied identity for which failure actually occurred.

## Headroom and scientific limits

Exact known-law single-task floors allow either report or a paid answer,
conditioning on the observed sensor pair. They are evaluator bounds, never
policy inputs. All zero-headroom conditions remain in the reported means.

| Post-change group | Exact floor | Decimal floor | Positive/zero-headroom conditions |
| --- | --- | --- | --- |
| core_changed | 373/4320 | 0.086342593 | 102/141 |
| A_loss | 11/120 | 0.091666667 | 27/54 |
| B_loss | 11/120 | 0.091666667 | 27/54 |
| reverse | 109/1440 | 0.075694444 | 48/33 |
| transfer | 6013/64800 | 0.092793210 | 54/189 |
| A_partial | 3853/43200 | 0.089189815 | 27/54 |
| B_partial | 3853/43200 | 0.089189815 | 27/54 |
| both_partial | 1/10 | 0.100000000 | 0/81 |


All 81 both-partial conditions have floor .1. No policy can beat always
checking there in expectation, even with the true law known; reducing the
observed excess remains a meaningful objective. The core analytic floor
.086342593 still leaves room below flat's .098875402 recovery cost.

For exact realized-cost decomposition use the separately sampled floors:
.086347688 for core change and .092800110 for transfer. Every saved block
satisfies `excess = conditional regret - sampled headroom + realization
residual`. The readback verifies these identities and phase/window closure.

The fixture remains deliberately small: known possible change times,
supplied structural hypotheses, fixed costs and a finite sensor-law population.
Confirmation does not remove those assumptions. Bayesian/VFE correctness
and useful behavior agree here for the pooled core objective, while failures
under other changes remain.

## Integrity and reproducibility

Qualification/preparation passed 21,339 cumulative wrapper/shared assertions
in 61.026624034 seconds, including the re-executed rational reference and new
scalar accounting. Separate pre-launch verification passed 57,109 identity
and seed checks. The conservative benchmark forecast was 47,663.426764054
seconds; the main run correctly launched detached without automatic polling.
It used four workers on CPUs 0–3, one BLAS thread each, Python 3.10.12 and
NumPy 1.21.5. Worker CPU time summed to 33,265.003445507 seconds.

The first confirmation attempt completed without failure, correction,
retuning, cohort extension or scientific rerun. Every previous failed attempt,
source, report, checkpoint and readback remains preserved.

Separate saved-count verification with
[readback_fep_weak_prior_confirmation.py](readback_fep_weak_prior_confirmation.py)
passes **296,158 assertions in 17.258654775 seconds**, maximum comparison
error 1.4210854715e−13. It imports no simulation or policy module, and checks
all 4 inputs, 230 outputs, 1,790 preserved identities, two source snapshots,
216 worker fingerprints/indices/CPU records, seed derivations and cohort
separation, integer costs, paired/stratified intervals, every criterion,
condition signs, windows, phase identities, posterior/planning summaries,
fallback totals and exact law floors. It extends the preserved independent
numerical route from the previous readback; the author is the same. This is
numerical verification, not an independent scientific replication.

The unchanged attempt-01 record is **141,428,326 bytes** at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-weak-prior-confirmation-v1/attempt-01/`.
Separate verification files use sibling `readback-2026-10-09/`. Generated data
remain on the verified external drive. Key identities follow.

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| FEP_WEAK_PRIOR_CONFIRMATION_V1.md | 9526 | `26bdbf79f07405e8a7fbc3fe241bbd48880a6d867ce18352f9a9668da1d74422` |
| check_fep_weak_prior_confirmation.py | 25356 | `695179dab393c7428d04434b57d64ed9ce3c1196eeebc54589f0878f0308b57c` |
| FEP_WEAK_PRIOR_CONFIRMATION_V1_CHECKPOINT.md | 7978 | `0af78c380a55a8cf07e08406f69adcc7a962480785bfff4a2213d75d0efa55b0` |
| MANIFEST.json | 497319 | `88ce572779080f3a0ac29ef4d99b11c445d4b0293b4a8dcaeac3f80c45a1d36a` |
| RESULTS.json | 8239670 | `5869567c8d4e9c6774ab31cdf9be71f6528bf85226f304f247dc3f3099102859` |
| READBACK.json | 1464239 | `c8d385a916404362c3282aa89d9d445fd5f2c75cc91d90818ede44e4b8ba23fa` |
| VERIFIER.py | 25266 | `b2bc0e8e3c1d0780ac67e1c4014a916a219505197563821289064503a5fe2e68` |


## Next recommendation

Keep **unchanged CT3-flat as the confirmed core reference**. The next bounded
question should test whether its benefit survives **changes at times the
model was not told to expect**, keeping all controls and all failures visible.
Specify that challenge prospectively before new outcomes. This addresses a
major remaining assumption behind useful adaptation without fitting another
prior to the present result.

No new study is launched or automatically authorized by this readback. The
current experiment and reporting are complete. The FEP track now has confirmed
pooled economical recovery in its supplied core task, with clear boundaries
for the next scientific test. Sister projects and manuscripts remain read-only.
