# Targeted reliability policies after the frozen-pool certificate

Prospective specification, 31 October 2026. The user's next “lets go” approves
the policy-generation lead after the [pool certificate](FEP_BURST_POOL_FEASIBILITY_V1_REPORT.md).
Preserve that negative result. This is one bounded successor with both FEP checks.

## Question and generative change

Can representing the binding alternating-error mechanism generate useful
policies outside the failed pool, without increasing the model's state count?
Does a development improvement transfer to new burst schedules?

Keep T=10, rho=1/2, uniform reversal onset over all ten tasks, stationary
error marginal .05, purchased accurate target cost .1, unaided error cost 1,
hidden unpurchased targets/losses, and K=19568652557/204800000000. No true
orientation, error bit, profile identity or free feedback is supplied online.

Replace only the second persistence-class law in the generating model:
previously constant .75, now .9,0,.9,0,.9,0,.9,0,.9 on the nine transitions.
The first class remains independent errors, both with prior probability 1/2.
This changes the generative assumptions and generation distribution; it is
not merely new mixture weights or proof that the old model could solve the
task. There remain 44 hidden states: class, reversal onset and current error.
The class is fixed per episode; its transition law depends on task time.

At transition t use P(z_next=1|z)=.05*(1-a[e,t])+a[e,t]*z, including unbought
steps. Every physical marginal stays .05. Bayesian/VFE inference updates the
joint posterior; utility weights do not change it. `q_pattern` denotes the
alternating-class probability. This supplied vocabulary is not structure
learning. The action target remains constrained task cost, not a new EFE.

## Generation, selection and controls

Generate full and paired reliability-freezing planners at mu={0,1,2,4,8,16}.
Use exact full-horizon Bellman planning for mean(B+R)+mu*mean(S) over the two
generating profiles. Every onset carries loss, with per-task multiplier
`1/T + 1[0<tau<=t]/(rho*(T-tau+1)) + mu*1[tau=infinity]/((1-rho)*T)`.
Use B,F,R action ties and a 250,000-state ceiling per cache. Save complete
compressed Bellman tables. For the ablation preserve the updated onset
marginal but reset conditional class/error state to equal classes and
Bernoulli(.05), in real and imagined updates. Orientation learning and
observation access remain. Its effective planning observations are independent
.05 errors: require actions, orientation beliefs and subjective values to
reproduce the previous ablated mu policies. Reliability-model changes should
not alter the ablated task; retain duplicate policies as named identities.

Append each family's six new graphs to its frozen seven-policy pool, keeping
the original floor. Order old mu policies first, new mu policies second,
floor last. Each pool has thirteen named components. Over all ten exposed
profiles, solve the predecessor's exact hard-budget/common-margin program:
S<=K, S+delta<=K, R+delta<=.1, R+delta<=R_hybrid, simplex weights. One global
episode mixture is independent of true states/profile. Eliminating the floor
and shifting delta by +1 gives thirteen nonnegative variables and 41 rows.
Use the frozen Bland simplex, 2,000 pivots, and independent primal/dual
certification. Reproduce both original seven-policy optima first. The floor
and strict-margin equivalence proof are inherited unchanged.

Optimize both expanded pools separately. Also map the full-selected weights
to paired ablated graphs unchanged for the causal intervention. Preserve
old-only and expanded margins, new-component weights and every development
gate. Expansion cannot worsen the optimum. If delta stays nonpositive, call
the selected mixture a failed development diagnostic and still complete its
frozen transfer and FEP checks. Do not add candidates or retune after outcomes.

Retain the previous feasibility-selected full mixture, previous full-onset
mixture, independence-assuming joint/fixed reserve mixtures, hybrid, always
purchasing, conservative rule and previously selected best fixed schedule.
The schedule is the sealed all-1,024-schedule optimum buying tasks 2–10 with
its original posterior; do not claim it is newly optimal under this model.
No schedule is retuned. Independently audit matched ordinary Bayesian
planning for all twelve new planners with identical information/objectives.
Its selected mixture must agree exactly; equality is legitimate.

## Freeze and transfer profiles

Freeze all selected graphs, weights, generating evidence and controls before
any full-horizon evaluation of these eight profiles. Check novelty against
sealed earlier burst rosters, without new policy scoring. Values 0/.9 and all
onsets were known; these temporal arrangements are new. Constants .1/.7 were
absent from earlier burst studies. Qualification may use short prefixes.

| New profile | Nine transition persistences |
| --- | --- |
| constant_10 | .1,.1,.1,.1,.1,.1,.1,.1,.1 |
| constant_70 | .7,.7,.7,.7,.7,.7,.7,.7,.7 |
| onset_after_3 | 0,0,.9,.9,.9,.9,.9,.9,.9 |
| offset_after_3 | .9,.9,0,0,0,0,0,0,0 |
| onset_after_7 | 0,0,0,0,0,0,.9,.9,.9 |
| offset_after_7 | .9,.9,.9,.9,.9,.9,0,0,0 |
| paired_low | 0,0,.9,.9,0,0,.9,.9,0 |
| paired_high | .9,.9,0,0,.9,.9,0,0,.9 |

Evaluate unchanged worlds and all ten reversal onsets; the onset prior stays
unchanged in generation/testing. Separate development from transfer. Primary
transfer success requires S<=K, R<.1 and R<R_hybrid in every new profile.
Deployment readiness additionally requires every development gate. No
continuous-range, arbitrary-profile or individual-onset guarantee follows.

## Both FEP checks

Measure pre-action wrong-orientation confidence >=95%, actual wrongly
confident errors, orientation Brier loss, mean confidence and repeated wrong
purchased-label updates. Compare the full mixture with its independent-error
reference, retaining all signs and non-monotone effects. Score the realized
component's beliefs, not an averaged posterior.

For reliability freezing report lower R and lower B+R per profile and both
stable budgets. Keep separately optimized ablated-pool outcomes distinct.
Controllers share physical distributions but may buy different subsets.
Include fees, stable/pre/post purchases, acquisition/missing-feedback measures,
confident-adoption and first-inversion delays. Stable purchases are not
automatically unnecessary. Separate acquisition, interpretation and economic
failure, retain per-onset harm and do not equate confidence with useful action.

## Qualification, resources and closure

Freeze protocol, new sources, imported helpers and predecessor inputs before
qualification. Cross-check time-dependent filters with independent rational
Bayesian propagation; verify stationary marginals and the onset-preserving
reliability reset. Compare full/frozen Bellman optima with all short contingent
trees through T=3, including exact objective/physical-cost identity and the
ablation's independent-law subjective cost. Qualify expanded LP construction
and reproduce predecessor witnesses/costs. Reuse frozen physical path/flow
helpers unchanged. Independently audit every new Bellman state, graph action,
posterior field/edge, ablated identity, old/expanded LP witness, freeze order,
physical/diagnostic result and mixture. Import no new planner in the auditor.

Benchmark full/frozen T=7,mu=4 planning and T=7 diagnostic verification at the
known generating profiles. Forecast main workflow plus verification as
`480 + 4*6*3^3*(11/8)*oracle_seconds
 + 4*18*34*(11/8)*2^3*diagnostic_seconds`.
Here oracle_seconds times both planners; diagnostic_seconds is the mean time
per graph/profile of independent integer forward diagnostics. The 34-graph
bound covers all candidates/controls; 480 seconds covers path traces,
selection and inherited-record checks. Log benchmark overhead separately.
Do not change this formula or study design after observing candidate outcomes.

Use the 7,200-second forecast ceiling. Default one CPU at nice 10, at most
four; library threads one, python -B. Forecasts over 600 seconds run detached
with durable logs, one startup check and no automatic polling. All generated
data use `/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-targeted-v1/`; source
and research notes remain here. Close the report and six live notes or an
explicit detached checkpoint. Preserve failed attempts and all earlier work.
No later successor, main-model integration, manuscript or sister write is
authorized by this study.
