# RDT-P01 v0.2: can short probes forecast continued reconstruction?

**Status: DRAFT_NOT_REGISTERED.** This package contains derivations, constructed development calculations and a native test specification. It contains no new native-system experiment or confirmatory result. It develops P01; it does not complete P02–P08 or the entire theory charter.

The useful result so far is a narrowing. A reconstruction operator alone supplies no new prediction. An unrestricted four-state model is an ordinary Markov model, and a simpler model separating expression recovery from identity loss performs better in our first constructed examples. A constrained version can be fitted from observable responses, but it also fails: short data can miss rare identity loss and badly overpredict persistence. P01 therefore needs a stated model class, an uncertainty calculation and a serious competing predictor. High present expression, a stable attractor, or a mechanically active writing branch cannot substitute for these.

The proposed empirical claim is now specific: **under one fixed renewal and assay contract, two stationary relaxation modes inferred from short response histories may predict the later probabilities of expressing either of two opposed taught rules or neither.** Its mathematics is a conventional structured hidden Markov model. Any contribution would be the validity and economy of this reduction in the native systems, which remain untested.

Read the [native protocol and evaluator handoff](PROTOCOL.md), [prediction manifest](prediction_manifest.json), [prior-art comparison](PRIOR_ART.md), and [evidence, exposure and decision registers](registers.json) alongside this argument. The [observable development figure](results/observable_forecasts.png) displays both a useful fit and the damaging failure.

## 1. The forecast and its boundary

Write a complete retained boundary state as \(z=(r,b,\theta,e,u)\): record, surviving body, reader/writer organization, persistent environmental information and resources. A component belongs in this state if it affects the future and is neither independently reset nor fixed by the declared apparatus \(m\). A prescribed schedule requires a time index or time-dependent kernels. Correlated noise requires its persistent state. Naming a packet is not a proof of sufficiency.

For the inspected E041 full-rewrite implementation, the candidate retained state is the 512 reciprocal weights, allocated as 4096 bytes of float64 data. Bodies are discarded and freshly developed. Ports, lattice, dynamics, writer formula, supplied cues, noise law, damage distribution and available computation belong to the supplied apparatus. This gives a conditional reconstruction claim, not autonomy of the reader or writer. Other policies require a fresh boundary audit.

Let \(K(z,dz')\) be one completed renewal and \(q_A(z)\) the probability that a separate fresh-body assay expresses the declared ancestral rule A. With row-stochastic kernels acting on column functions,

\[
C_H^A(z;m)=(K^Hq_A)(z). \tag{1}
\]

Equation (1) is a definition, not an empirical law. The apparatus, observer, damage and resource contract are held fixed in this notation. A chronological intervention sequence \(u,v\) gives \(K_uK_vq\), not the reverse product.

These endpoints must remain distinct:

| Quantity | Operational meaning |
|---|---|
| Present expression | Fresh assay at the current boundary, \(q_A(z)\). |
| Terminal reconstruction | Rule A is expressed after H renewals, regardless of intermediate failures. |
| Historical specificity | \(C_H^A(z_A;m)-C_H^A(z_B;m)\), comparing own and foreign records under the same apparatus and assay. |
| Uninterrupted performance | Every one of H declared within-cycle assays passes. |
| Recovery | A specified failure is followed by a specified success event within a declared window; censoring is retained. |
| Adaptability | Acquisition and retention of further competence under a separately specified learning test. |
| Viability | A declared survival or reproduction consequence, not resemblance alone. |

If cycle success \(Y\) shares randomness with its successor, retain the joint kernel \(J(z,y,dz')\). Define \(A(z,dz')=J(z,1,dz')\). Then uninterrupted performance is \(A^H\mathbf1\); uninterrupted performance **and** a conditionally independent terminal assay is \(A^Hq_A\). Missing row mass is failure. Replacing A by \(\Pr(Y=1\mid z)K\) requires conditional independence and is wrong in counterexample CE10. Terminal marginal forecasts cannot be multiplied to obtain an all-cycle forecast.

## 2. What a reduced forecast would have to earn

Choose a frozen partition \(\phi:z\mapsto i\) and lift \(Lf(z)=f(\phi(z))\). Suppose every microscopic state reached during the forecast satisfies

\[
\|\phi_*K(z,\cdot)-\widehat P(\phi(z),\cdot)\|_{TV}\le\epsilon_K,
\qquad |q_A(z)-L\widehat q_A(z)|\le\epsilon_q. \tag{2}
\]

Here TV is half the L1 distance. For a Markov \(\widehat P\) and a readout in [0,1],

\[
\left|K^Hq_A-L\widehat P^H\widehat q_A\right|
\le \epsilon_q+\epsilon_K\sum_{j=0}^{H-1}
\operatorname{osc}(\widehat P^j\widehat q_A)
\le\epsilon_q+H\epsilon_K, \tag{3}
\]

with either bound capped at one. To check it, expand

\[
K^Hq_A-L\widehat P^H\widehat q_A
=K^H(q_A-L\widehat q_A)
+\sum_{j=0}^{H-1}K^{H-1-j}(KL-L\widehat P)\widehat P^j\widehat q_A.
\]

Markov operators contract the sup norm; integration against a difference of probability measures is bounded by TV times oscillation. Applying these two facts proves (3). The same result applies to uninterrupted performance after adding an absorbing failure state to A. Specificity differences add the two endpoint error bounds. This is standard finite-state reduction mathematics; [Markov aggregation with transient error bounds](https://arxiv.org/html/2403.07618v2) is a close precedent, not a competitor to be omitted.

The difficult premise is (2), not matrix exponentiation. Separate
\(\epsilon_K\le\epsilon_{\rm representation}+\epsilon_{\rm sampling}\).
Sampling a few microstates inside a bin does not bound its remaining heterogeneity. A data-dependent partition also requires independent calibration or a valid selection correction. Fast global mixing can tighten prediction-error bounds while erasing the very ancestral distinction we want to preserve.

For R fixed rows, D categorical outcomes and n independent samples per row, an elementary simultaneous sampling radius is

\[
\epsilon_{\rm sampling}=
\min\!\left(1,\sqrt{\frac{\log[R(2^D-2)/\delta]}{2n}}\right). \tag{4}
\]

Indeed TV is the maximum signed discrepancy over subsets of categories. Hoeffding's one-sided bound applies to each subset; a union bound over the \(2^D-2\) nontrivial subsets and R rows gives (4). For a joint success/successor row, D=2k. This bound concerns fixed reference-row distributions, not unsampled states, correlated trajectories or unknown apparatuses. Readout estimation has its own uncertainty.

The illustrative configuration R=4, D=8, \(\delta=.05\), known readout and zero representation defect requires **507,872 observations per row** for the coarse \(H\epsilon_K\le .1\) guarantee at H=32. This is a conservative sufficient bound, **not a lower bound, necessary sample size or native recommendation**. It shows why “short probes” can be shallow but still expensive. The sharper bound remains uninformative in much of the present small toy calculation.

There is also an exact obstruction. Two time-homogeneous chains can have identical complete transcripts from the allowed start through L renewals and disagree only on the next transition of the deepest visited state. Give one an absorbing successful successor and the other an absorbing failed successor. At H=L+1 their success probabilities are one and zero. Any predictor using only those depth-L transcripts must have expected absolute error at least one half on one model. CE11 implements L=4. This statement concerns restricted probe access; it does not deny prediction from a fully known transition law or arbitrary reset access. P01 needs restrictions beyond the probe depth.

## 3. A restricted observable law

For a *single fixed record and apparatus*, classify a paired-cue response as A, the opposed rule B, or neither. The original strict margins make A and B mutually exclusive. At depth h define

\[
r_h=\Pr(O_h=A)+\Pr(O_h=B),\quad
s_h=\Pr(O_h=A)-\Pr(O_h=B),\quad
\chi_h=s_h/r_h. \tag{5}
\]

The candidate marginal law is

\[
r_H=\pi+(r_0-\pi)\mu^H,\qquad
\chi_H=\chi_0\lambda^H, \tag{6}
\]
\[
\Pr(O_H=A)=\tfrac12r_H(1+\chi_H),\quad
\Pr(O_H=B)=\tfrac12r_H(1-\chi_H),\quad
\Pr(O_H=\varnothing)=1-r_H. \tag{7}
\]

This version restricts \(\pi,r_0,\mu,\lambda\in[0,1]\), \(\chi_0\in[-1,1]\). It excludes oscillatory modes, changing rates and a persistent preference for A over B after all initial identity bias is lost. Protected identity is the special case \(\lambda=1\). These exclusions are substantive and cannot be relaxed after a failed test while retaining the original version's claim.

An exact realization uses independent binary chains: identity flips with probability \(p=(1-\lambda)/2\); readiness is lost with probability \(a=(1-\pi)(1-\mu)\) and recovered with probability \(b=\pi(1-\mu)\). Readable identities emit A or B; either unreadable identity emits neither. Initial identity and readiness are independent. Their transition matrix is the Kronecker product of two two-state matrices. Diagonalizing these matrices gives (6)–(7). This is ordinary Markov/hidden-Markov reasoning, not newly discovered RDT mathematics.

The path-likelihood implementation adds a stronger hypothesis than the marginal equations: the entire short response process follows this four-state hidden Markov model with deterministic emissions. Noisy native assays need not meet that assumption. A good fit of marginal means does not validate the joint model. Native calibration must examine both; changing the emission model requires a new version.

Here r measures expression of either rule. The latent readiness bit is a modelling device, not a measurement of the manuscript's distinct transmission-readiness endpoint.

For exact nondegenerate marginal probabilities at depths 0,1,2,

\[
\mu=\frac{r_2-r_1}{r_1-r_0},\quad
\pi=\frac{r_1-\mu r_0}{1-\mu},\quad
\lambda=\frac{\chi_1}{\chi_0},\qquad
\chi_2=\chi_0\lambda^2. \tag{8}
\]

The last equality is a checkable restriction. Zero readability, zero initial bias and stationary readability obstruct this particular inversion; rates can be unidentified even when a forecast under the assumed law is identified. Stationary marginal readability does not rule out identification from temporal correlations. The code rejects degenerate exact inversion rather than clipping invalid rates. Sampled proportions require estimation and uncertainty, not literal use of (8). In particular,

\[
\frac{\partial\Pr(O_H=A)}{\partial\lambda}
=\tfrac12r_H\chi_0 H\lambda^{H-1}, \tag{9}
\]

so small uncertainty near \(\lambda=1\) can produce substantial long-horizon uncertainty. Optimizer convergence is no guarantee of identification.

The within-record contrast \(s_H\) is **not** the own-minus-foreign-record historical specificity in section 1. To predict the latter, assay and fit both records separately under the same apparatus, then subtract their A forecasts. They coincide in the symmetric constructed example for a specific reason; they are not interchangeable definitions.

## 4. Development results, including failures

All parameters, seeds and sample budgets below are illustrative. The designer knew the generative law. Forecast files were saved before evaluation and carry code hashes, but that ordering does not make these blinded or confirmatory tests. Full counts and optimizer attempts are retained in [results](results/).

First, 512 independent one-step resets from each of four *known hidden states* were supplied to every estimator, 2048 observations per case. Both cases have identical current expression and readiness dynamics (loss .15, recovery .6); identity-flip probabilities are .005 and .04. Root-mean-square terminal-A forecast errors over the declared positive horizons are:

| Constructed case | Four-state joint model / ordinary Markov | Simpler independent factors | Output-only Markov |
|---|---:|---:|---:|
| Slow identity loss | .05469 | **.01504** | .15329 |
| Faster identity loss | .07849 | **.01920** | .09981 |

The full joint model and ordinary four-state model are identical. The simpler factor model wins both comparisons here because its structure matches the constructed generator. This is evidence against claiming benefit from the unrestricted RDT label. At H=32 the true A probabilities are .68999 and .42775 despite equal present expression and equal readiness-restoration rates. Restoration alone does not identify continuation.

After seeing that result, we introduced the observable model. This outcome-informed revision is recorded. Each of three cases supplies 512 independent two-renewal trajectories, observing only A/B/neither at depths 0,1,2. A fixed set of eight likelihood-optimizer starts is retained. Long-depth truth is computed analytically, not estimated from simulation.

| Constructed case | True A at 32 | Two-mode forecast | Output Markov forecast | Two-mode RMSE, depths >2 |
|---|---:|---:|---:|---:|
| Slow loss, initially readable | .68999 | .75400 | Unsupported row | .05653 |
| Faster loss, initially readable | .42775 | .44208 | .65567 | .01787 |
| Slow loss, initially poorly expressed | .68999 | .82006 | .81196 | .11929 |

The first execution stopped because an output transition row had no observations. We retained the same seed and cases, recorded the failure, and changed reporting to preserve the unsupported baseline without imputation. The third case fitted \(\widehat\lambda=1\) despite true \(\lambda=.99\); its output-only comparator has lower RMSE (.11105). The two-mode model therefore fails a useful point-forecast check **even when its structural assumptions are true**. This is a finite-information/estimation failure, not a disproof of its exact algebra. No sampling confidence intervals or cross-seed superiority claim are established. A conventional HMM with the same structure ties every prediction by construction.

The implementation passes 18 checks, including explicit path enumeration, joint success dependence, chronological intervention composition, random finite aggregation bounds, binomial coverage of the elementary sampling bound, observable/hidden-model agreement and exact inversion. Tests validate these calculations; they do not validate a native reduction.

## 5. Counterexamples and the E051 update

The executable [counterexample record](results/development_v1.json) preserves eleven cases:

| ID | Construction | Claim it defeats |
|---|---|---|
| CE01 | Every state contracts to the same prototype. | Stability implies historical specificity. |
| CE02 | One perfectly retained identity bit has a useless reader. | Record information alone implies expression. |
| CE03 | A successful state writes a failing successor. | Present expression implies continuation. |
| CE04 | A currently failed state reaches a successful successor. | Present failure implies irrecoverability. |
| CE05 | A matrix with spectral radius .5 amplifies a finite perturbation outside the safe region. | Local eigenvalues certify safety. |
| CE06 | An external guide contains the erased ancestral bit. | Improved output demonstrates information in the packet. |
| CE07 | Two components copy each other's defect indefinitely. | Mutual maintenance implies useful adaptation. |
| CE08 | Twenty nuisance bits lose to one task-relevant bit. | Total memory predicts task value. |
| CE09 | Identical present output hides different successor laws. | A perfect present readout is a sufficient state reduction. |
| CE10 | Passing a cycle causes next-cycle failure. | Marginal pass probabilities can replace the joint kernel. |
| CE11 | A hidden countdown fails just beyond the probe horizon. | Finite short probes give unrestricted long-horizon guarantees. |

The user's E051 interim report arrived during this development: 8/32 blocks, 128 lineages per condition, original-writer terminal success 120/128 for matched cues, 126/128 for correlation .999, 126/128 for independent cue noise, and 119/128 for initial-state mismatch. The fixed \(10^{-4}\) tolerance reportedly yields 3/128 and 80/128 under matched and slightly mismatched noise. These are **user-reported aggregates**, not a raw-output audit by this lane. The report also says mismatch disables the returning-edge fallback, teaching/test cues remain matched, and the full cohort and independent dynamics audit are pending. Exact counts and qualifications are retained in [the evidence register](registers.json).

The preliminary implication is narrow but consequential: a changed writing branch need not produce a large terminal-performance loss under that contract. The partial counts do not establish equivalence, beneficial noise, uninterrupted success, or invariance to teaching/test randomness. Block dependence and condition pairing prevent treating 128 outcomes as 128 independent experimental units without the design. The tolerance result weighs against that particular modification; it is not evidence against every tolerance rule. These outcomes are development exposure for our theory and cannot retroactively confirm it.

Mechanistic differences and predictive differences are separate questions. Two distinct microscopic kernels can share all aggregated row probabilities and therefore every forecast of an aggregated readout. That exact possibility explains why a branch count alone is an inadequate universal predictor; it does not establish what happened in E051. A useful follow-up would relate each writing change to the successor response distribution and eventual failures under a declared assay contract.

## 6. Strongest formulation and next decision

In a closed chain without further ancestry-correlated inputs, data processing prevents creation of new information about unknown ancestral identity. A finite irreducible aperiodic chain eventually loses dependence on its initial state. Improved expression can still result from recovery, denoising or a supplied reader. In (6), readiness may recover while identity bias decays. If \(\lambda<1\), the final readable population approaches equal probabilities for A and B; indefinite specificity is not predicted. Neither this limit nor a finite successful run establishes inherited learning, autonomous machinery or collective individuality.

**Strongest current formulation:** a short, measurable response history may admit a compact fixed-rate forecast of terminal reconstruction, provided that reduction error and rare-loss uncertainty are controlled. The proposed two-mode model is one explicit, rejectable candidate.

**Weakest assumption:** effective identity loss and expression recovery are independent stationary modes over the requested horizon, with the stated observation process. The native weight dynamics may couple these processes, drift between basins, or hide delayed failure.

**Most damaging feasible test:** fit only short histories for preselected packets and apparatuses, freeze predictions and intervals, then evaluate longer continuations. Include low-expression recoverable packets and matched-expression packets with different histories. If their later failure or recovery distributions systematically escape calibrated intervals, reject this version. Equal-probe conventional HMMs and strong passive/native predictors must be allowed to win.

**Next theoretical decision:** determine from bounded native development whether the two-mode restrictions and uncertainty estimates survive at all. If they do not, retain the failure and justify any richer state description against its measurement cost before making a new version. Do not patch rates after looking at long outcomes. The protocol leaves empirical margins and sample sizes unset until that work can justify them.
