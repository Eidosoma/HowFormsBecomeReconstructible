# Record-dependent reading: results and limits

**Completed 18 September 2026.** The user asked to continue exploring the
preservation question scientifically. The
[analytic specification](FEP_RECORD_DEPENDENT_READER_V1.md) preceded the
[checker](check_fep_record_dependent_reader.py) and its first, successful
execution. This is an exact finite-model result, not sampled empirical
evidence. Manuscript integration remains with the other agent.

## Main finding

The revised model closes the specific gap found by the
[preceding review](FEP_READER_PRESERVATION_REVIEW_2026-09-18.md): the agent no
longer knows the answer, and useful information must pass through a retained
record and its reader. Replacing the record with random content leaves every
allowed policy at chance, even with a perfect reader. Keeping the record
intact while making the reader uninformative also leaves performance at chance.

The specified state-preference objective can choose useful maintenance, but
its finite-preference entropy effect still limits task alignment. A separate
FEP-inspired objective that rewards learning the **stored bit** can maintain
a reader even after the record has lost all information about the **target**.
Reading data accurately and recovering useful information are different
properties in this model.

This establishes the declared causal dependence and objective differences
inside the model. The writing process, channel law and maintenance efficacy
are supplied; learned or sustained autonomous maintenance remains untested.

## What changed physically

The hidden target X is a fair bit. A previous writing process leaves record
`R=X XOR N`, where content damage N has probability eta. Maintenance changes
the reliability of a separate reader: `Y=R XOR E`, with
`P(E=0|a)=rho_a`. The controller sees only Y, then selects its faithful motor
report `D=f(Y)`. It never receives X, R or the realized faults directly.

There are eight policies: maintain or skip, followed by one of four binary
report maps. The same preselected policy is evaluated across both hidden
targets; a policy index cannot carry the correct answer. Maintenance leaves
the distribution of retained content unchanged. Disabling its physical effect
sets the maintained and unmaintained reader laws equal.

The saved blind-guess reference is the utility of ignoring Y with a constant
report and no maintenance; it is already represented among the eight policies.
The single read remains compulsory in all physical policy evaluations.

Two quantities express the separation:

```text
Retained target information: I(X;R) = log(2)-h(eta)
Accessible target information: I(X;Y|a) = log(2)-h(eta+(1-2*eta)*rho_a).
```

With intact content and a chance reader, the record retains one bit about X
but the agent obtains none. With random replacement and a perfect reader,
the agent learns one bit about R but none about X. No further inference or
choice of report can reconstruct a target independent of every available input.

Maintenance itself provides no observation. Unlike the preceding model, the
subsequent read does provide information. The full joint-state information is
one bit for every policy, while its relevance to X varies.

## FEP and task outcomes

The endpoint is expected correct reports minus maintenance cost. In the table,
beta is 4, a chance reader becomes perfect after maintenance, and the task
reward is one. State risk and its exact decomposition agree. The full-state
latent extension has exactly the Bayesian task ranking in this model.

| Record / maintenance price | Bayesian and full-state extension | State risk / exact | Task-target extension | Record-target extension |
|---|---:|---:|---:|---:|
| Intact / 0.10 | **0.90**, maintain | **0.90**, maintain | **0.90**, maintain | **0.90**, maintain |
| Intact / 0.40 | **0.60**, maintain | **0.50**, skip | **0.60**, maintain | **0.60**, maintain |
| Intact / 0.60 | **0.50**, skip | **0.50**, skip | **0.40**, maintain | **0.40**, maintain |
| Random replacement / 0.10 | **0.50**, skip | **0.50**, skip | **0.50**, skip | **0.40**, maintain |
| Content flip probability 0.25 / 0.30 | **0.50**, skip | **0.50**, skip | **0.50**, skip | **0.45**, maintain |

All optima in each displayed cell have that utility, so the contrasts do not
depend on the representative tie rule. These are net task scores, not success
probabilities. All seven objectives and complete tie sets are in the data;
the table groups two exact equalities for readability.

For the random-replacement case, maintenance improves information about R
from zero to `log(2)` nats, while information about X remains zero. The
record-target extension's maintain-minus-skip score is
`4*0.1-log(2) = -0.293147180560`, so it strictly chooses maintenance and pays
0.10 without changing its 0.50 success probability. The task-target extension
does not receive that information bonus and skips.

The partial-content case is also discriminating. At eta 0.25, a perfect
reader supplies only **0.130812035941 nats** about X, but **0.693147180560 nats**
about R. At price 0.30, the raw-record bonus makes maintenance optimal for its
objective even though utility falls from 0.50 to 0.45. The task-target
maintenance threshold is about **0.282703**, below that price; the record-target
threshold is about **0.423287**, above it.

These are differences between explicitly named objectives. The three latent
extensions are information-target variants, not interchangeable formulations
of all active inference. Their information rewards may be intentional even
when they reduce this external task endpoint.

## Why the predictions differ

For the fixed state `S=(X,R,E,a,D)` and preferred joint in the specification,
the physical entropy is `log(2)+h(eta)+h(rho_a)`. The separate content and
reader causes are retained; substituting the entropy of correctness alone
would silently change the state representation.

Let `s_a=max(P(Y=X|a),1-P(Y=X|a))`, the best achievable report accuracy;
`Delta_s=s_1-s_0`; `L_E=h(rho_0)-h(rho_1)`; and
`L_X=h(P(Y=X|0))-h(P(Y=X|1))`. Maintenance is selected below these prices:

| Objective | Maintenance threshold |
|---|---|
| Bayesian / full-state latent extension | `v*Delta_s` |
| State risk / exact decomposition | `v*Delta_s-L_E/beta` |
| Task-target latent extension | `v*Delta_s+L_X/beta` |
| Record-target latent extension | `v*Delta_s+L_E/beta` |

At threshold equality, both actions and every optimal report map are retained.
Outcome risk with the conditional KL omitted always skips positive-cost
maintenance here: marginalizing the preferred joint removes its latent-success
term. It also ignores report quality, so its tie sets must not be interpreted
as uniformly good task performance.

The entropy contribution is the established mechanism discussed in the
preceding review, not a newly discovered FEP principle. The contribution here
is to place the objective comparison in a task with separately testable record
and reader dependence and to expose the different information targets.

## Controls and boundary cases

- **Content loss:** all eight policies remain exactly at 0.50 accuracy after
  random replacement, including every maintained-reader policy.
- **Maintenance disabled:** all objectives skip the costly action when it
  cannot change the reader. Performance remains at chance.
- **Reader already intact:** every success-sensitive objective skips and
  reports correctly. The outcome-only score leaves report quality unresolved.
- **Known reversed reader:** every success-sensitive objective inverts its
  observation and achieves accuracy 1 without maintenance. A known invertible
  transformation does not constitute loss of usable information.
- **No task value:** the task- and record-target extensions still pay 0.10 for
  information, giving utility -0.10; the other objectives skip and obtain zero.
- **Interior probabilities:** at eta 0.10, reader alignment 0.70 versus 0.90,
  and price 0.10, Bayesian utility is 0.72 while state risk chooses 0.66.
  This disagreement does not require a perfect reader or completely lost input.

The three tie fixtures retain five optimal policies where an informative
maintenance option ties four chance report maps. At the state threshold the
state-optimal utility range is **0.50 to 0.673286795140**. At the task threshold,
all Bayesian/full-state optima have utility **0.50**. At the information
threshold, the task/record-extension range is **0.326713204860 to 0.50**.

## The remaining scientific limit

Each controller receives the correct error-rate parameters. It does not infer
whether the record is trustworthy. That distinction is material: for any
fixed policy, the observation distribution is the same in every regime,
`P(Y=0|a)=P(Y=1|a)=1/2`, and D is a known function of Y. If the regime were
hidden, a single such read could not update its prior odds. This identification
limit was derived in the specification before execution; fair output laws
were checked for all policies.

The next useful theoretical step is to identify what **additional evidence**
could distinguish reader reliability from record validity when those facts
are not supplied. That evidence needs an explicit source, reliability and
cost. Merely making a read more confident does not test whether the stored bit
still relates to the hidden target. No new diagnostic or repair campaign is
automatically queued by this result.

## Verification and record

The first execution passed **14 fixtures**, **112 physical policy
distributions**, **784 objective scores** and all **98 optimum sets**.
There were **3,567 numeric comparisons** and **464 structural checks**,
including posterior identities, retained versus accessible information,
content invariance under maintenance, erasure bounds and the reversal control.
The maximum residual was **1.7763568394002505e-15**, below the fixed `1e-12`
tolerance. Calculation took **0.015696879 seconds** on one standard-library
Python 3.10.12 process. These are arithmetic checks, not independent replicates.

The source syntax check preceded execution. No failed execution, exclusion,
retuning or numerical rerun occurred. The under-ten-second forecast justified
foreground execution below the four-CPU ceiling. The external mount was
verified before writing; no generated dataset was placed in the workspace.

The **133,237-byte** record is under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-record-dependent-reader-v1/attempt-01/`:

- [Results and complete policy scores](/mnt/bioIce1/fep-ideas/formal-checks/fep-record-dependent-reader-v1/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-record-dependent-reader-v1/attempt-01/RUN_LOG.txt)
- [Input/output manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-record-dependent-reader-v1/attempt-01/MANIFEST.json)

The manifest records hashes of the specification and checker before
verification, then identifies the two outputs. All four hashes were verified
after execution. Preserve those inputs and outputs. The report and project
status notes are outside the frozen calculation inputs. Earlier studies and
manuscript files were not edited; no sister-project search or fresh literature
search was required.

Reproduction must use a new output directory on the verified external mount:

```bash
python -B check_fep_record_dependent_reader.py \
  --output /mnt/bioIce1/fep-ideas/formal-checks/fep-record-dependent-reader-v1/reproduction-01
```
