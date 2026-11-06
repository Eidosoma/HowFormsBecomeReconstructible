# Two authorised FEP studies of correlated evidence

The user explicitly authorised both studies on 30 October 2026. FEP 1 refines
the main lane's existing burst-error proposal, so it is one shared experiment,
not a duplicate campaign. FEP 2 follows within this same authorisation. Neither
changes the current main-lane controller or integrates into the larger model.

1. [FEP 1: correlated errors and false confidence](FEP_BURST_CONFIDENCE_V1.md).
   Freeze the existing controllers and weights. Preserve a 5% error marginal
   on each task while varying serial dependence. Evaluate costs, purchases,
   wrong confidence and orientation beliefs with exact enumeration.
2. FEP 2: infer persistent error episodes and test whether that inference helps
   action. Specify its candidate pool, training/held-out split, conservative
   and fixed-schedule controls, matched Bayesian planner and reliability-state
   ablation before constructing candidates. Freeze selected candidates before
   evaluating new burst durations and held-out reversal timings.

Keep T=10, the original purchase/error costs and budget, hidden unbought
targets/losses, and the original deployment reversal prior. The candidate's
training loss may use a predeclared subset of onsets to reserve genuinely
unscored timings; distinguish this selection distribution from deployment.
All policies retain a generative model permitting every original onset.
No true error state, persistence class or orientation is supplied online.

Main-lane results remain intact. These studies concern functional robustness
and reliability inference within the FEP track. Agreement with a matched
Bayesian planner is legitimate; it is not a negative FEP result. The action
criterion remains constrained task cost unless an explicit alternative is
derived and separately specified.

Source and research-note writes stay in `fep-ideas/`. Generated data and
logs use only `/mnt/bioIce1/fep-ideas/`. Sisters and manuscripts remain
read-only. Use at most four CPUs, preferably one at nice 10. Runs forecast
above ten minutes must detach with durable logs, one startup check and no
automatic polling. Preserve all attempts and negative findings. Complete
both authorised studies or leave a concrete detached checkpoint; no further
successor is implied.
