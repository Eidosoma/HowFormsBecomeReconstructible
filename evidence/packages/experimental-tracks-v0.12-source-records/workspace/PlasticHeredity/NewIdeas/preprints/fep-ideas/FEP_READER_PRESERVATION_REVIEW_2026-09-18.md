# Scientific review: what the preservation example establishes

**Completed 18 September 2026.** Internal review authorized by the user's
"lets go" after the preservation result. This is a review of the model,
implementation, saved evidence and relevant primary texts, not independent
peer review. No scientific calculation was rerun or extended. Manuscript
integration remains with the other agent.

**Verdict:** retain the exact objective comparison, but narrow its scientific
interpretation to **choosing the reliability of a supplied readout channel**.
The positive maintenance choice and the finite-preference disagreement are
valid within the specification. The model does not establish that a retained
record is necessary for performance, or that an agent maintains a decoder
needed to interpret that record. The entropy mechanism also has a direct
literature precedent. A larger parameter sweep would not resolve these limits.

## 1. Evidence and mathematics checked

Reviewed the [specification](FEP_READER_PRESERVATION_V1.md),
[report](FEP_READER_PRESERVATION_V1_REPORT.md),
[checker](check_fep_reader_preservation.py), saved policy rows and
[manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-preservation-v1/attempt-01/MANIFEST.json).
Recomputed the two input and two output hashes; all four match the manifest.
Inspected the physical flip/report construction, permitted policy inputs,
preference normalization, direct scores, analytic assertions and tie sets.

The saved run contains eleven fixtures, 44 policy distributions, 220 scores
and 55 optimum sets. Its reported maximum residual is 3.553e-15, and the
exact-decomposition residual is 8.882e-16. Those are recorded checks from the
completed run, not 838 arithmetic comparisons repeated by this review.
The 44,602-byte external record remains unchanged.

Direct algebra confirms, with the original definitions:

```text
J_state = J_exact = K-beta*U-h(rho_a)
J_latent = K-beta*U
Delta J_state = beta*(c-v*(rho_1-rho_0)) + h(rho_0)-h(rho_1).
```

At a fixed maintenance choice, complementary report preparations have equal
entropy; their state-score difference is `beta*v*(2*rho_a-1)`. This confirms
the best-preparation and tie rules. Consequently the original maintenance
thresholds and the strict utility disagreement survive this review. No
numerical correction or invalidation of the sealed result is warranted.

## 2. The retained content is not an identified causal resource

The model conditions on a known message `m`. Substitution into its success
equation gives

```text
d = m XOR b XOR F
g = 1[d=m] = 1[b=F].
```

Thus the objective, task score and optimal choices depend on maintenance,
report preparation and channel error, but not on the message value. There is
an equivalent decision problem with no represented record: choose whether
to improve a binary output channel, then whether to invert its output.
Every saved policy score is preserved by that reduction.

Symmetry between message labels would be appropriate in a stronger memory
model too; symmetry alone is not the problem. Here there is also no independent
record-access variable or intervention that destroys the stored content while
holding the desired answer fixed. The controller is already given that answer.
The computation cannot tell whether a particular retained record matters.

Calling the channel a reader is an admissible physical interpretation, but
the calculation does not distinguish it from a noisy actuator. Its error is
sampled under a supplied action-dependent reliability; acquisition of a
calibration, persistence of that calibration, identification of damage, and
repair of an interpretation relation are absent.

The result therefore supports the narrow statement that an EFE-derived
objective can select a supplied reliability intervention. It does not yet
establish preservation of record-dependent interpretation. The pivot's main
question remains open even though the objective calculation is correct.

## 3. Preference, observation and state assumptions

### Distributional preferences differ from expected utility

For finite beta, state risk minimizes divergence from an entire preferred
distribution. It does not optimize only mean success minus cost. The success
preference has mass `C_G(1)=1/(1+exp(-beta*v))`, rather than a requirement for
certain success. Less variable predictions can therefore incur an entropy
penalty relative to the task planner.

The example's disagreement is a genuine difference between the declared
objectives. It is not a failure to minimize the FEP score, an inference error,
or a contradiction of a universal reward-optimality guarantee. The comparison
holds physical access and task coefficients fixed; it does not make the two
internal optimization criteria identical. Beta is preference strength, not a
separately specified action-selection temperature. Its units must track those
of v and c; rescaling task units without adjusting beta changes preferences.

### Zero information gain follows from the observation contract

The only outcome is the known action pair `(a,b)`. With a fixed policy it is
constant, so `I(S;O | policy)=0`. The actual report, success and fault are
withheld. This is a valid deliberate control for maintenance without learning,
but not a claim that real reading or maintenance generally lacks information
gain. The example contains no perception/update loop.

The latent extension reduces exactly to expected task utility under this
contract; its positive result does not identify a contribution from epistemic
value. Conversely, the induced outcome preference integrates out success:
`C_O(a,b)=C_A(a)*C_B(b)`. Its tendency to skip follows from losing the success
term when the conditional KL is dropped. This is a useful approximation
control, not a separately demonstrated failure of every outcome-based agent.

### Relabeling is checked; arbitrary state changes are not

For known m, success and fault coordinates are in one-to-one correspondence
when actions are retained. Transforming the preferred joint consistently
preserves the score, as checked in the saved calculation. The entropy result
is therefore not caused by naming the bit "success" instead of "fault".

Adding unrepresented physical variables or changing their preferred conditional
distribution is a different model. The supplied eight-state representation
does not establish invariance under all possible descriptions of a reader.

## 4. Deterministic policies and randomized selection

The four deterministic policies exhaust the allowed decisions for each known
message and empty feedback history. They do not instantiate a general active
inference policy posterior. Two randomization conventions must be separated.

If a controller draws policy pi with probabilities w and evaluates the
**conditional** score of the policy it knows it selected, its average score
is `sum_pi w_pi*J(pi)`. A mixture cannot improve on the best component for
that same score. Under this convention, allowing random draws does not remove
the strict maintenance disagreement; mixing tied policies leaves the reported
utility bounds valid.

If instead one inserts the **unconditional mixture** into the same state KL,
the action pairs give component distributions disjoint support. Therefore

```text
KL(sum_pi w_pi*Q_pi(S) || C_S)
    = sum_pi w_pi*KL(Q_pi(S) || C_S) - H(w).
```

That criterion includes an additional policy-entropy term and can prefer a
mixture. With actions also counted as outcomes, its apparent information is
`I(S;O)=H(w)`, even though no external data were received. Conditional on the
agent's own policy draw, that information is zero. This is an accounting
distinction, not evidence obtained by the maintenance action.

These are analytic clarifications introduced during review, not new fixtures
in the frozen run. They rule out silently transferring the deterministic
result to an unspecified softmax or stochastic agent. A separate policy prior
or selection rule must be declared if introduced later.

## 5. Literature scope

Three versioned primary texts were reopened and the passages below checked
on 18 September. All were accessible. This targeted check is not a systematic
novelty review, and no sister project was searched.

Da Costa et al.'s synthesis, section 7, equations 13–16, explicitly distinguishes
state risk, observation ambiguity and the conditional posterior divergence
in the outcome decomposition. It supports the functional used here and the
need to retain that divergence. It does not turn our supplied readout action
into an autonomous maintenance mechanism.
[Primary source](https://arxiv.org/html/2001.07203v2#S7)

Da Costa et al.'s reward-maximisation analysis, section 3.2, equation 5,
already writes the state KL as expected preference cost minus future-state
entropy. Section 4.1, Lemma 14, and section 5.2, Proposition 18, state limiting
reward-alignment results with explicit conditions. Our finite-beta example
illustrates that established tradeoff; it does not discover the entropy term
or refute the limiting statements. Its present contribution is a small,
reproducible application with an explicit reliability interpretation.
[Primary source](https://arxiv.org/html/2009.08111v4)

Millidge, Tschantz and Buckley, section 3 and its factorization footnote,
make the biased joint, posterior assumptions and distribution over policies
explicit. This reinforces the need to state which functional and policy
selection procedure is being tested. The local latent-success extension
remains separately labeled.
[Primary source](https://arxiv.org/html/2004.08128v5#S3)

## 6. Current claim and the next useful design

Use this statement in current project summaries:

> A specified state-preference objective can pay for a supplied readout
> reliability improvement without acquiring information. At finite preference
> strength, changes in forecast entropy can make its maintenance threshold
> differ from the threshold for expected task utility. The current example
> does not establish that a retained record or learned decoder is necessary.

Keep both the useful low-cost case and the contrary case. Do not describe this
as demonstrated autonomous information preservation, a uniquely FEP benefit,
or a new general entropy theorem. The original report is retained with a
visible link to this qualification; the frozen specification, checker and
external data remain unchanged. Manuscript revisions belong to the other agent.

The next proposed local deliverable is **one analytic design in which task
success actually depends on reading retained content**. Before implementation,
it should satisfy these concrete requirements:

1. The later target is not already supplied to the decision maker. Its useful
   information must come through the retained record and a specified decoder.
   State exactly which message, calibration and history variables survive;
   no hidden copy in the planner or policy index may bypass that limit.
2. Separate stored content from reader compatibility. Hold the record fixed
   while disrupting the reader, and separately destroy record information
   while holding the target and reader fixed. An intact reader must not
   restore information absent from the record or other declared resources.
3. Include an intervention that prevents the maintenance action from changing
   the reader, plus matched always/never-maintain and Bayesian controls. The
   question concerns a specified FEP objective's choices, not a repair method's
   superiority over another project's apparatus.
4. Declare the physical model, preferred joint, observations and policy
   conditioning before deriving scores. Maintenance itself may reveal nothing,
   while a later read supplies information; the present whole-episode
   zero-information assertion must not be carried over automatically.
5. Derive the task-value and FEP predictions before any run. If the objectives
   coincide, record that equivalence. If the proposed model still contains no
   way to test dependence on the retained content, revise the design before
   computation rather than enlarge the parameter grid.

This remains a prospective specification task. It does not authorize or
launch a successor numerical campaign, and even a successful design would
not by itself establish learned or sustained autonomous maintenance.
