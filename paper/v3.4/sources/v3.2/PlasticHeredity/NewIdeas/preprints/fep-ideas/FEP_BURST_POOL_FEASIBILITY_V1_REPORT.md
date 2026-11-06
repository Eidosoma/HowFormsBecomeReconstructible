# Existing-policy feasibility: a certified limit, with both FEP checks completed

Completed and independently verified 31 October 2026 under the
[prospective protocol](FEP_BURST_POOL_FEASIBILITY_V1.md). All ten physical
profiles were already exposed in the [full-onset study](FEP_BURST_ALLTIMING_V1_REPORT.md).
This is development and diagnosis, with no fresh validation claim.

**Neither frozen seven-policy pool contains a mixture that meets the stable
budget and both recovery requirements across these ten profiles.** Exact
primal/dual certificates establish this limit for every mixture in each pool.
It is not just a failure of the selected mixtures or a numerical search.
It does not establish impossibility for other controllers or FEP models.

Reliability learning has useful effects: its optimized pool has the less
negative margin, and its selected mixture recovers more cheaply than the
separately optimized ablated mixture in all ten profiles. Nevertheless, both
fail. The same-weight causal ablation gives a different result: reliability
updating lowers stable cost and wrong confidence, but worsens recovery and
B+R throughout. Neither comparison is omitted or substituted for the other.

## Exact selection and the bottleneck

T=10, the reversal prior, costs, purchased-feedback interface and 5% marginal
sensor error remain unchanged. Each pool contains its six previously frozen
mu policies and no-purchase floor. We choose one component per episode using
one global weight vector; the controller never receives the true profile,
orientation or error regime. No planner or policy graph was regenerated.

For each pool, maximize a common margin delta while retaining S<=K as a hard
constraint in every profile. The three margin constraints are S+delta<=K,
R+delta<=.1 and R+delta<=R_hybrid. Here K=.0955500613134765625, S is stable
cost per task, R averages recovery cost per remaining task over all ten
reversal onsets, and B is full-prior episode cost per task. Every purchased
target costs .1; every unaided error costs 1. B and B+R do not select weights.

The floor has S=.05<K throughout. Thus a mixture satisfying both strict
recovery inequalities and the stable budget would admit a small floor
perturbation with positive common margin. The negative optima below certify
infeasibility of the original criteria, including their boundary cases.
Exact weights, matrices, slack values and dual witnesses are in SOLUTIONS.json.
The deterministic simplex vertex is not claimed to be unique.

| Pool | mu=2 weight | mu=4 weight | Optimal common margin |
| --- | --- | --- | --- |
| full | 0.702987570 | 0.297012430 | -0.016751433 |
| ablated | 0.039798959 | 0.960201041 | -0.020512560 |

All other component weights, including the floor, are zero at these selected
vertices. The full pool improves the optimal margin by .003761127 relative
to the ablated pool. Both selected mixtures remain budget-feasible everywhere,
but each fails both recovery comparisons everywhere.

| Exposed profile | Full S | Full R | Optimized ablated S | Optimized ablated R | Hybrid R |
| --- | --- | --- | --- | --- | --- |
| Independent | 0.089262811 | 0.113426103 | 0.086293458 | 0.115531958 | 0.096674669 |
| Constant .75 | 0.083046738 | 0.107583892 | 0.089733330 | 0.113289973 | 0.093783807 |
| Constant .2 | 0.090764478 | 0.111178074 | 0.087747814 | 0.113846248 | 0.095362825 |
| Constant .4 | 0.089918931 | 0.109391206 | 0.090493803 | 0.112387016 | 0.094418826 |
| Constant .6 | 0.086840062 | 0.108139010 | 0.091861207 | 0.111918203 | 0.093842335 |
| Constant .8 | 0.081511974 | 0.107428999 | 0.088028455 | 0.114354709 | 0.093842148 |
| Alternating, starts low | 0.093481431 | 0.108872818 | 0.083978159 | 0.110047482 | 0.093152191 |
| Alternating, starts high | 0.095550061 | 0.107081039 | 0.088437224 | 0.113749581 | 0.093550633 |
| Persistence begins after task 5 | 0.087369380 | 0.107811493 | 0.086385025 | 0.112897505 | 0.095001817 |
| Persistence ends after task 5 | 0.083704319 | 0.112701287 | 0.095550061 | 0.113348153 | 0.096260203 |

The dual witnesses yield especially simple bounds. For every policy in a
pool, the saved certificate verifies an inequality of the form
`R_recovery_profile + lambda*S_budget_profile >= constant`. It therefore
holds for every mixture. Substituting S<=K gives:

| Pool | Binding stable profile | Binding recovery profile | Certified R lower bound |
| --- | --- | --- | --- |
| full | Alternating, starts high | Independent | 0.113426103 |
| ablated | Persistence ends after task 5 | Constant .8 | 0.114354709 |

For the full pool, lambda is approximately 1.845795800; for the ablated pool,
1.386114362. Each bound already exceeds .1, even before requiring improvement
over the hybrid. The exact inequalities and every component residual are
saved separately in reporting DERIVED.json. This identifies incompatible
budget/recovery behavior within the existing pools, without requiring a
continuous-correlation claim or reusing the independence interpolation proof.

## Check 1: correlated errors and false confidence

The selected full mixture is evaluated with identical weights in unchanged
worlds and all ten genuine reversal worlds. Relative to its independent-error
reference, all nine correlated profiles increase stable wrong-confidence
frequency, stable orientation Brier loss, and actual wrongly confident errors
under the full prior. Mean stable confidence increases in six profiles;
stable total cost increases in four. Constant .4 and alternating-low exhibit
all five adverse signs together. More correlation does not uniformly worsen
all outcomes: recovery improves relative to independence in all nine profiles,
although it remains above both recovery limits.

The alternating-low example separates average confidence from its harmful tail.
Wrong confidence means at least 95% pre-action belief in the wrong orientation;
frequency and Brier loss are per task. Purchases and errors are per episode.

| Stable-world quantity | Independent | Alternating, starts low |
| --- | --- | --- |
| stable_confidence | 0.904474581 | 0.904794036 |
| stable_wrong95 | 0.000404190 | 0.003198787 |
| stable_wrong95_errors | 0.000335023 | 0.002594874 |
| stable_brier | 0.028611742 | 0.040448350 |
| stable_purchases | 7.565869869 | 7.468295984 |
| stable_errors | 0.136041126 | 0.187984709 |
| stable | 0.089262811 | 0.093481431 |

Wrong-confidence frequency rises from **.0404% to .3199%** of stable decisions.
Mean confidence rises only slightly, from about 90.4475% to 90.4794%. Errors
made while wrongly confident rise from .0335% to .2595% of tasks. Stable
cost rises by .004218619: .051943583 extra errors outweigh the fees saved
by .097573885 fewer purchases per episode. The exact decomposition is
`delta S=(delta errors+.1*delta purchases)/10`.

Repeated identical wrong purchased labels still push orientation belief in
the wrong direction. In this example, expected repeat events increase from
.016173525 to .123838096 per stable episode, and every counted event increases
wrong-orientation probability. This does not mean confidence rises on every
trajectory, or that every wrong orientation produces an action error: a
persistent sensor error can compensate a genuine orientation reversal.

All signed contrasts, repeated-label scores, stable/full-prior confidence,
Brier losses, actual errors and purchase fees are retained. The richer
reliability model reduces false confidence relative to the ablated models,
but does not remove sensitivity to the physical correlation law.

## Check 2: reliability freezing and the optimized ablated control

The causal intervention pairs full_mu02/full_mu04 with the existing
ablated_mu02/ablated_mu04 at exactly the full mixture's weights. Orientation
learning and observation access remain available; conditional reliability
state is reset in real and imagined updates. Policies may purchase different
subsets of the same physical distribution. This is a controller-level
intervention, not an interpretation-only comparison on identical observations.

Reliability updating lowers stable cost and stable wrong confidence in all
ten profiles. It lowers stable Brier loss in six. However, it increases R
and B+R in **all ten**, and confident orientation adoption is slower throughout.
The paired ablation violates the stable budget in eight profiles. Both are
budget-feasible at independence and persistence beginning after task 5; the
full controller still has worse R and B+R there. The positive causal recovery
criterion is therefore unmet, even in those matched-budget cases.

Separately optimizing the ablated pool gives a fairer comparison of what
each existing pool can achieve under the hard budget. Both optimized mixtures
meet K throughout; full reliability has lower R in ten profiles and lower
B+R in nine, with alternating-low the exception. Full stable cost is lower
in five. These are conditional benefits under a common selection procedure,
not evidence that the failed full mixture is generally successful.

Counts below are strict improvements over ten exposed profiles, not
probabilities. The two ablation comparisons are deliberately separate.

| Comparator | Full S lower | Full B lower | Full R lower | Full B+R lower |
| --- | --- | --- | --- | --- |
| previous_full | 10 | 8 | 0 | 0 |
| frozen_reliability | 10 | 6 | 0 | 0 |
| selected_ablated | 5 | 6 | 10 | 9 |
| joint_mixture | 9 | 6 | 0 | 0 |
| fixed_pool | 10 | 6 | 0 | 0 |
| hybrid | 10 | 9 | 0 | 0 |
| always | 10 | 10 | 0 | 4 |
| conservative | 0 | 10 | 10 | 10 |
| fixed_schedule | 9 | 10 | 5 | 9 |
| matched_bayesian | 0 | 0 | 0 | 0 |

The best previously selected fixed schedule costs S=.095 and R=.1085 in
every profile. The full mixture beats its recovery in only five profiles,
although it lowers B in all ten and B+R in nine. The conservative rule also
meets the stable budget but has much worse recovery. The prior full mixture
recovers more cheaply throughout but retains its previously documented
budget failures. All controls remain frozen.

Matched ordinary Bayesian planning agrees exactly. Component-level Bayesian
optimality was independently checked in the predecessor; this study inherits
those identities and applies identical mixture weights. Bayesian/VFE belief
updating is the FEP-related mechanism. The action target remains declared
constrained task cost, without a new canonical EFE or unique-FEP claim.

## Acquisition, interpretation and economic failure

Compared with the previous full mixture, the new budget-feasible mixture
has a lower probability of purchasing no post-reversal feedback in every
profile. Yet its mean first-purchase delay and confident-adoption delay are
both longer, and it incurs more post-reversal errors and purchases. Eventually
obtaining evidence does not ensure timely or economical recovery.

For independent errors and reversal at task 7, mean delay to the first
purchase rises from .003197 to .257293 tasks, and recovery cost rises from
.076588 to .134036. The probability of buying no post-reversal evidence
actually falls, from .000247 to .000103. Acquisition timing, orientation
interpretation and the final bill must therefore remain distinct. These
diagnostics do not isolate an interpretation-only cause, since actions and
the histories observed also change.

The failure is an economic recovery failure under the hard stable budget.
Suppressing wrong confidence is useful but insufficient. Stable purchases
are reported without assuming the agent knew they were unnecessary. All
onset-specific costs, acquisition/adoption/inversion delays, missing-feedback
probabilities and pre/post purchases remain in RESULTS.json; averages do
not guarantee every onset or individual episode.

## Verification and next lead

Qualification passed 4,252 assertions in 2.482 seconds: five rational LP
fixtures, four positive/zero/negative margin fixtures, corrupted-witness
rejection, and 4,221 independent physical comparisons over all 273 short trees.
The runtime forecast was 180.887 seconds, so execution remained attached.
Main calculation took 15.573 seconds and independent readback 50.787 seconds
on one CPU at nice 10, library threads one, with bytecode disabled.

Readback passed 300,404 assertions, including source/graph identities,
1,650 independently reconstructed physical graph/world costs, 440 complete
diagnostic graph/world scores, both pool optimality certificates and nine
fixture certificates. It imports no new solver or evaluator. Main calculation
also passed 7,148 cost-reproduction assertions against sealed records. Selection was frozen
at 11:46:02.655684 UTC, before diagnostics at 11:46:02.672535 UTC. This ordering
does not turn exposed development profiles into holdouts.

All 34 input identities, four snapshots, fourteen selection-stage files and
eighteen manifested outputs verify. The sealed attempt occupies 38,786,129
bytes. Manifest SHA-256:
`29683bb76a1b2048938c8a4b29710d93a79511f89b8c892e3d78f210476e9f73`.
No scientific execution or verification attempt failed. A read-only terminal
display initially hit Python's large-integer string limit; its corrected
inspection and explanation are recorded in reporting provenance, without
altering exact results.

All generated files use
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-pool-feasibility-v1/`.
Exact reporting tables, certificate consequences and seven document snapshots
are separate under `reporting-2026-10-31/`. Source and small research notes
remain local. Both requested checks and independent verification are complete;
nothing remains running. Earlier sealed studies and negative results stand.

**Recommended next lead, not launched:** change policy generation to address
the certified pair of bottlenecks: stable alternating bursts and timely
recovery with independent errors. Simply reweighting this pool cannot work.
First specify a bounded candidate with those requirements in its training
objective, preserving paid feedback and the reliability intervention; freeze
it before genuinely new burst schedules. This study does not decide whether
better policy generation alone suffices or a different reliability model is
needed. No further run, model expansion, manuscript integration or sister
write is authorized by this completed study.
