# What evidence can validate a reader and its record?

**Completed 18 September 2026.** The [prospective specification](FEP_READER_EVIDENCE_V1.md)
preceded the [checker](check_fep_reader_evidence.py) and its first, successful
execution. This is an analytic and exact finite-model result, not sampled
empirical evidence. Manuscript integration remains with the other agent.

## Main finding

Repeated reads can reveal reader inconsistency, but cannot establish whether
the record still carries information about its target. For that, this model
requires evidence connected to the target through another route whose
reliability and independence are supplied explicitly. A copy of the same
record cannot provide that grounding.

With those resources and their prices declared, Bayesian planning and the
state-preference FEP objective buy useful evidence in the principal example.
A separate FEP-inspired objective that rewards learning the hidden mechanism
buys additional diagnostic information without improving the final answer.
The distinction is between the declared objectives, not a verdict on FEP as
a whole or evidence of an advantage unique to FEP.

## Identifiability before optimization

The target X is fair, and the saved record is `R=X XOR N`, with content error
probability eta. Holding the reader law fixed, R has the same fair marginal
at every eta. Therefore any adaptive protocol observing only R through reader
channels has the same history distribution at every eta. Even perfect access
to R cannot reveal how reliably R was related to X. This argument assumes
the declared fair target and separate reader mechanism.

Two independent reads of the unchanged record do reveal reader consistency:
their agreement probability is `rho^2+(1-rho)^2`. This alone cannot distinguish
reliable native reading from reliable reversal. Persistent or correlated
reader faults also violate the independent-repeat assumption.

An independent reference Z with known accuracy kappa adds the missing
relationship to X. In sign notation the two relevant correlations are

```text
read/read:      (2*rho-1)^2
read/reference: (1-2*eta)*(2*rho-1)*(2*kappa-1).
```

Together they identify eta and rho at the population-law level when native
polarity is assumed and both reader and reference are above chance. One
read/reference correlation alone identifies only a product. A chance reader
or chance reference prevents this identification. These are claims about
distinguishable laws across independent targets under stable rates, not a
promise to diagnose one record with certainty.

## Unknown causes and paid evidence

The finite example includes four equally likely mechanisms: content intact
or randomly replaced, independently crossed with reader intact or random.
Thus diagnosing the reader does not settle the content question by excluding
the possibility that both are damaged. The agent knows the candidate family
and prior, but not the actual mechanism.

After a compulsory first read, the chosen bundle can include a second read
priced 0.05, an independent reference priced 0.10, or both. Bundle choice
occurs before observations. The reference is 75% accurate. Every controller
may report directly from that reference; no restriction forces it to repair
or use the old record. There is one final report and no later task.

The principal example gives the following values. Information is in nats;
content information concerns the intact/replacement mechanism C, not whether
one randomly replaced bit happens to equal X.

| Evidence | Best accuracy | Net task score | Information about both mechanisms | Information about content mechanism |
|---|---:|---:|---:|---:|
| First read | 0.625 | 0.625 | 0 | 0 |
| Add repeat | 0.625 | 0.575 | 0.215762 | 0 |
| Add independent reference | 0.750 | **0.650** | 0.024870 | 0.007959 |
| Add both | 0.750 | 0.600 | 0.237999 | 0.010772 |

The repeat changes beliefs about the reader, but does not improve the optimal
answer in this setting. The reference improves the answer even though it
provides much less information about the joint mechanism. More diagnostic
information is not automatically more useful information for this task.

One triple also leaves substantial uncertainty. If both reads and the
reference agree, the posterior probability of intact content is only **4/7**,
up from 1/2; the probability of an intact reader is **5/7**. Reader disagreement
identifies the random-reader class within the supplied family but leaves the
content prior unchanged. These are mechanism probabilities. The saved output
separately records the probability that R actually equals X.

## FEP choices and their scope

At beta=4, Bayesian planning, state risk, its exact state/outcome decomposition
and the task-information extension all choose the reference bundle and report
Z. Their net score is **0.65**. The full-state and regime-information extensions
choose both extra signals and score **0.60**. Each principal optimum is unique.

For the regime extension, the repeat adds 0.213129091696 nats after the
reference. Its acquisition threshold is therefore
`k < 0.213129091696/4 = 0.053282272924` when terminal accuracy is unchanged.
The declared price 0.05 lies below that threshold. The result is a specific
finite-preference incentive; a modest price increase changes the choice.
This diagnostic knowledge could matter in a future task, but no such task
exists in this endpoint.

State risk agrees with Bayesian utility here because the three candidate
signals are generated before access and included in a fixed hidden state.
Buying access changes observation, not physical-state entropy. This is an
explicit representation and timing choice, not a general equivalence theorem.
The exact conditional-KL decomposition was checked directly; exact physical
inference was not used to discard that term.

The full-state extension rewards information about the buffered signals,
including noise. The task and regime variants specify other information
targets. These extensions retain the qualification established by the earlier
[formulation audit](FEP_FORMULATION_AUDIT_2026-09-18.md): they are declared
EFE-inspired variants, not interchangeable published formulations.

## Controls and limits

- **Copied reference:** Z=R has the same 0.75 marginal accuracy under the
  principal prior, yet every observation leaves the content-mechanism prior
  unchanged. It can improve access to R and diagnose the reader. The regime
  extension buys only this reference and scores 0.65; the full-state extension
  still buys both and scores 0.60. Equal average accuracy does not imply equal
  diagnostic meaning.
- **Chance reference:** Bayesian/state/task objectives skip extra evidence
  and score 0.625. The regime extension buys a repeat and scores 0.575. The
  full-state extension buys both, including the independent random bit, and
  scores 0.525. None gains evidence about the content mechanism.
- **Known erased content, independent reference:** the reference restores
  0.75 report accuracy through new external information, giving net 0.65 for
  Bayesian/state/task objectives. This does not reconstruct the lost record.
- **Known erased content, copied reference:** all 292 policies remain at
  0.50 accuracy. Bayesian/state/task objectives skip and score 0.50; the
  regime extension scores 0.45 and the full-state extension 0.35 after their
  extra evidence costs.
- **Expensive evidence:** at a price of 1 for each extra signal, every
  objective selects only the first read and scores 0.625.
- **Price tie:** at reference price 0.125, Bayesian/state/exact objectives
  retain both the first-read and reference policies, each scoring 0.625. The
  task extension strictly selects the reference at that same utility. All
  report-map ties, including chance cases, remain in the saved optimum sets.

The model does not establish the reference's calibration or independence,
discover an adequate model family, estimate continuous rates from a sampled
dataset, choose adaptive acquisition, or maintain a reader. No maintenance
action is included in this evidence-design step. The mathematical contribution
is to specify the missing evidence and its decision consequences without
giving the agent a hidden fault label or prohibiting a useful direct route.

The next useful local step is an analytic two-record design: determine whether
paid calibration on one record can improve maintenance decisions on a later
record under a declared persistent mechanism. Include a mechanism-reset
control, all evidence and maintenance costs, and direct reference use as an
alternative. That would test whether diagnosis acquires future task value;
no such successor has been implemented or run here.

## Verification and preserved record

All **2,044 policy distributions**, **12,264 scores** and **42 complete optimum
sets** across seven fixtures passed. Six additional channel settings checked
the sign law, moment inversion and its degenerate limits. Finite observation
laws also verified content nonidentifiability for reader-only and shared-record
access. The proof for arbitrary adaptive access is analytic, not an exhaustive
enumeration of such protocols.

There were **28,533 numeric comparisons** and **4,151 structural checks**.
The maximum residual was **1.7763568394002505e-15**, below the fixed 1e-12
tolerance. Calculation took **0.806548762 seconds**, with one standard-library
Python 3.10.12 process. No failed execution, retuning or numerical rerun
occurred. A syntax check preceded execution; input identities were recorded
before the calculation, and all input/output hashes were verified afterward.

The **785,586-byte** record is on the verified external mount:

- [All policy scores, posteriors and optima](/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-evidence-v1/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-evidence-v1/attempt-01/RUN_LOG.txt)
- [Frozen input and output manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-evidence-v1/attempt-01/MANIFEST.json)

Preserve the specification, checker and outputs. The report and status notes
are outside the frozen calculation inputs. Earlier sealed work and manuscript
files were not changed. No sister-project or fresh literature search was
needed for these derivations. Reproduction must use a new directory on the
mounted external drive; no further run is queued.
