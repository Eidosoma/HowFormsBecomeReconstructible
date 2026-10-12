# Second reviewer: E041 robustness and a more specific mechanism

8 October 2026. Assessment of the supplied review against the local writer,
reader, E051 protocol and completed mechanism studies. No new trajectories,
interventions or E051 progress checks were performed for this assessment.

The reviewer identifies two distinct needs: characterize the conditions under
which the supplied mechanism works, and explain which changes to records make
it work. Both are more informative next steps than extending the same mechanism
to a longer horizon. The review correctly treats dependence on paired cue
episodes as an open robustness question, rather than a demonstrated artifact.

## What E051 covers

| Proposed test | Frozen E051 coverage |
| --- | --- |
| Cue-noise correlation | Yes: 1, .999, .99, .9 and 0, with identical initial activity |
| Shared versus independent initial activity | Yes: correlation 1, .99 and 0, with identical update noise |
| Exact-zero versus small-threshold fallback | Yes: original rule versus one fixed product threshold, 1e-4; not a threshold sweep |
| Numerical precision | No: original floating-point computation/record representation retained |
| Record quantization or additive record noise | No |
| Positive floor on strength normalization | No |
| Simultaneous reset and noise mismatch | No |

E051 already retains returning-edge fallback use, repair magnitudes, nonzero
connectivity and functional outcomes. It does not establish the causal role of
those intermediate changes. Teaching, holding and terminal assays retain their
original definitions. The running protocol remains frozen.

## Algebra that can enter the paper now

For the transformed activities x used by the writer, write

`m_i = (x_i_plus + x_i_minus)/2`, `d_i = (x_i_plus - x_i_minus)/2`.

Expanding `x_plus = m+d` and `x_minus = m-d` gives

`c_ij = ((m_i+d_i)(m_j+d_j) + (m_i-d_i)(m_j-d_j))/2`

`     = m_i*m_j + d_i*d_j`.

The cross terms cancel. This is an algebraic identity in real arithmetic;
separate floating-point evaluation orders need not be byte identical. For
`q_ij = d_i*d_j`, the original bridge is equivalently

`b_ij = q_ij + 1[q_ij == 0] * m_i*m_j`

in that algebraic description. Thus the writer suppresses the shared-response
coactivity term on edges with a nonzero cue product, while allowing it on
zero-product edges. The code implements its branch with the original ordinary
coactivity expression, not this rearrangement. See
[capture](E041_full_rewrite_confirmation/model.py), lines 33–43.

Under paired cue histories, d contrasts the response to different cues with
the other stochastic inputs held fixed. With unpaired histories, d also contains
trial-specific variation. Calling all of that variation a causal cue response
would overstate what the two samples identify.

This decomposition motivates a mechanism; it does not explain the measured
rewriting advantage on its own. **Both bridge preservation and full bridge
rewriting use the same decomposition when they capture.** Their difference is
whether available old strong values bypass replacement. The relevant further
question is which retained interactions help or conflict with the organization
expressed by the current body.

There is an additional exact sign prediction. Around any closed loop composed
entirely of nonzero cue-product edges,

`product_over_loop(q_ij) = product_over_loop(d_i**2) > 0`.

Consequently those edges have consistent signs around every loop, regardless
of whether d represents useful cue information or sampled noise. In floating
arithmetic, evaluate the parity of negative edges rather than multiplying tiny
magnitudes. Nonzero rounded cue products retain the endpoint sign relationship;
underflow can remove an edge, so the statement applies to surviving nonzero
cue-product edges. Measuring sign consistency only
inside this newly written cue-product subnetwork would largely check a property
imposed by construction. The informative measurements concern its alignment
with the task, older retained edges, and cycles traversing fallback connections.
Tolerance-based fallback can modify additional edges, so it need not have the
same property across the whole available graph.

Suggested manuscript wording:

> Ordinary two-cue coactivity decomposes into a shared-response product and a
> response-difference product, c_ij = m_i m_j + d_i d_j. Away from its fallback,
> the supplied writer retains only the latter. This suggests that rewriting can
> favor organization expressed in the cue contrast while removing other
> inherited interactions. The decomposition is algebraic; the present performance
> comparison does not establish that this removal causes the gain. Both bridge
> policies use the same capture rule, and differ in whether strong inherited
> values are retained instead of replaced.

## Strength normalization is a separate, related dependency

For `D_i = sum_j abs(w_ij) > 0`, replacing every surviving incident weight by
`alpha*w_ij`, for alpha>0, leaves `sum_j w_ij*v_j / D_i` unchanged in real
arithmetic. Scaling the entire graph is a compatible way to apply this at every
node while retaining reciprocal edges. Scaling a single edge in a mixed-strength
neighborhood generally changes the drive. The implementation divides whenever
the denominator is positive and uses zero drive only when it is zero:
[reader](E022_reader_compensation/model.py), lines 53–57.

The simulation already uses finite floating-point numbers; the open question is
sensitivity to representation and numerical thresholds, not an absence of
finite precision altogether. Scale invariance of this reader equation also
does not imply invariance of every policy: preservation's abs(w)>.5 threshold,
quantization, record perturbations and numerical underflow can break it.

This explains why E051 needs actual performance measurements. Tiny noise-driven
cue products can remain effective where all surviving inputs are similarly
weak. A small written weight alone does not establish that repair failed.

A useful next robustness study would separate:

1. Activity/arithmetic precision, which can change cue differences and the
   exact-zero branch itself.
2. Quantization of the stored record, initially leaving reader arithmetic
   unchanged, which isolates loss of small transmitted values.
3. Additive record noise with a frozen absolute scale and explicit treatment of
   exact zeros. Protect physical erasures; separately identify any variant that
   creates new nonzero connections from zero slots.
4. A denominator floor, explicitly `max(D_i, epsilon)`, distinct from adding
   epsilon to every denominator. This attenuates weak total input below a fixed
   scale. Include zero-floor baseline and prespecified positive floors.

Preserve each initial acquired record and matched treatment futures. Test both
paired and imperfectly paired cue conditions so an interaction between weak
noise-written connections and normalization can be detected. Use unchanged
reference conditions and frozen functional criteria. Calibrate numerical ranges
on excluded technical inputs; a broad sensitivity grid remains secondary unless
specific contrasts are registered for confirmation. No new robustness run has
been launched by this assessment.

## Mechanism work that builds on the existing evidence

[E044](E044_transition_diagnosis/README.md) already found returning-edge repair
near 99% in the persistently failing group. Connectivity restoration alone is
therefore an insufficient explanation. [E046](E046_failure_chronology/README.md)
placed the largest weakening burst after the first failed body, ruling it out
as the cause of that already-recorded response while leaving effects on later
bodies open.

[E048](E048_partial_rollback/README.md) provides a useful constraint on the
discarding-old-interactions hypothesis: on selected first-failure cases, restoring
half the lost signed value improved next-body recovery to 69.1%, versus 57.8%
unchanged and 64.1% after full restoration. Some information in the prior values
can therefore be useful. This intervention changes sign and magnitude together;
it does not isolate shared-response coactivity, sign consistency, or the cause
of E041's full-rewriting-versus-preservation advantage. The subsequent
[E049](E049_rollback_persistence/README.md) third-body joint criterion did not
pass. A balanced hypothesis is that selective removal and selective retention
have different benefits, which blanket policies combine imperfectly.

For a focused mechanism analysis, quantify shared and difference products,
conflict between inherited edge signs and current cue contrasts, and where
fallback edges connect to the existing cue-responsive network. Avoid defining
cue responsiveness as any nonzero sampled d under independent noise; almost all
cells can then qualify. Use a prespecified response criterion or repeated
diagnostic trials to distinguish sampling variation from a reliable cue effect.

Then intervene on the identified component. For example, correcting selected
edge signs while holding their absolute magnitudes, locations and number fixed
preserves local strength denominators and topology. Matched control edits and
future task performance would test sign alignment more specifically than a
combined sign/magnitude rollback. Correlations with reconstruction are useful
for forming this hypothesis but cannot replace its intervention.

E041's compact boundary files retain packets and output means, with hash
commitments to full body activity; a whole-body m/d decomposition requires
replay of those bodies. E051 retains full end activities directly, enabling
such post-run analyses without rerunning its dynamics. Any analysis designed
after examining its outcomes remains exploratory.

## Regeneration operator

The stochastic record-to-record transition is the relevant unit for long-term
inheritance. A stable response while a record is fixed need not write a successor
with the same behavior. Conversely, different byte-level records can preserve
the same routing rule. Strength normalization supplies one concrete reason why
raw record difference can exaggerate functional difference.

A useful predictive task is to choose starting-record differences before
outcomes, follow them under matched future damage/noise, and predict which
distinctions persist on held-out blocks. Report raw record distance, normalized
interaction differences and task-response distinctions separately. Inference
concerns distributions of finite trajectories, not proof of an indefinitely
stable state from 32 generations. Matching future randomness across record
treatments is distinct from giving the writer matched cue episodes.

Immediate priorities: incorporate the algebra with its limits; finish E051;
prepare the separate precision/normalization comparison; then use a targeted
mechanism intervention to distinguish helpful retention from harmful retention.
The operator view supplies the longer-term predictive goal.
