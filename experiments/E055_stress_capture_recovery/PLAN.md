# E055 draft design — not frozen

**Historical skeleton, superseded on 11 October 2026 by [PROTOCOL.md](PROTOCOL.md)
and [plan.py](plan.py).** The user has authorized implementation and execution;
the original open choices below are retained for provenance, not used as settings.

10 October 2026. Documentation only; implementation waits for the predecessor
evidence described in [DECISIONS.md](DECISIONS.md). Values and source choices
labelled open below are proposals, not experiment settings.

## Questions and scope

1. Does a transient activity disturbance alter reconstruction by a fresh body
   receiving the disturbed body's outgoing record?
2. Does recovery before capture change that transferred effect, after accounting
   for the ordinary effect of capture delay?
3. Does the effect differ between acquired and repeatedly renewed records?

These questions develop CG-01 from the
[candidate list](../EXPERIMENT_LEADS.md). E019 already tested capture timing;
E033–E035 distinguished reader timing and outgoing-record quality. The new
contrast is the controlled pulse-by-capture-time interaction and its transfer
to fresh recipients. A result would concern this body/record apparatus, not a
mechanism of mammalian ageing.

## Candidate source cohort

The first candidate is the complete audited E051 cohort: acquired records and
h32 full-rewrite records, with matched and independent rebuilding-noise histories
kept separate. Final source and primary history remain open until E053/E054 have
been assessed. Reuse of existing records would be declared mechanistic follow-up,
not fresh confirmation. E053 is a prerequisite for interpreting numerical
conditions, not an automatic requirement to use its records as inputs.

Retain every declared block and lineage, including initially unsuccessful cases.
Do not choose a source packet because it responds favourably to a pulse or a
recovery schedule. Repeated recipient slots of an acquired packet do not become
independent acquisitions. Differences between acquired and h32 records concern
those defined histories; do not presume that every later record is degraded.

## Smallest comparison

For each source record, use the same incoming packet, physical injury, starting
state and declared stochastic inputs in counterfactual pulse/sham bodies. Keep
the incoming record fixed during the read, as in the original apparatus. Capture
is a measurement/write into an outgoing buffer, with no feedback to that same
body. Thus two capture times can sample the same realised body trajectory.

| Candidate arm | Additional activity pulse | Outgoing record | Purpose |
| --- | --- | --- | --- |
| Sham, early capture | None | Ordinary writer at the pulse-end time | Baseline for early capture |
| Pulse, early capture | One declared pulse | Same writer at the pulse-end time | Can the pulse enter the next record? |
| Sham, late capture | None | Same writer after a fixed recovery interval | Baseline for capture delay itself |
| Pulse, late capture | Identical pulse | Same writer after the recovery interval | Does recovery alter the pulse-specific record effect? |
| Sham, protected transmission | None | Incoming values, with the same physical erasures | No-writing reference |
| Pulse, protected transmission | Identical pulse | The same protected packet | Control for unintended transmission outside the record |

Pulse amplitude, duration, location and timing are open. Prefer a rule-independent
perturbation of non-port activity so the pulse does not supply the task answer.
Specify the perturbation field's relation across cue episodes separately from
the baseline Gaussian-noise correlation. Changing intrinsic cue-noise pairing
and adding a pulse are distinct manipulations; neither should be hidden inside
the other. Freeze the pulse law on excluded technical inputs before science.

Every body is observed until the same final time, including arms whose outgoing
packet was captured earlier. Match total observation time, normal cue exposure,
injury availability and baseline random draws across comparisons. Declare the
same number of effective writes per outgoing branch. Retain whether clipping
or other nonlinearities change the actual delivered perturbation.

The protected packet receives the same declared physical erasures and record
channel as its control counterpart. It is an engineered transmission control,
not a model of biological maintenance. An optional erased-record assay can
provide a common lower reference, subject to the final panel budget.

## Fresh-reader boundary

Pass each outgoing packet to a completely reset recipient. Use one common final
reader, fixed injury conditions and new assay streams matched across record arms.
The additional pulse is absent there; ordinary assay noise remains present.
No activity field, recovery state, perturbation label, capture-time label or
founder target may cross the boundary as an undeclared input.

Record current-body observations at the same early/late windows, then score
fresh-reader function separately. A body's temporary failure, later recovery
and the effects of its outgoing record are not interchangeable observations.
If pulse and sham produce the identical protected packet, their common fresh
reader must also agree under identical assay inputs.

## Candidate estimands

Let `Q[p,t,h]` be mean next-body both-cue success for pulse condition `p`, capture
time `t` and source history `h`, with independent blocks as the inference unit.

`pulse_effect[t,h] = Q[pulse,t,h] - Q[sham,t,h]`

`recovery_interaction[h] = pulse_effect[late,h] - pulse_effect[early,h]`.

The interaction removes the ordinary effect of waiting longer to capture.
A positive value means delay changes the pulse-specific effect favourably;
it does not alone establish restoration. That stronger interpretation also
requires evidence of an initial perturbation effect, an interpretable recovery
in the current body, and the declared absolute/relative next-body criterion.
The needed thresholds and primary family remain open; no success classification
is set by this draft.

Compare pulse effects between acquired and h32 records without selecting cases
to equalise their initial success. Report their baseline performance and any
floor/ceiling limitation. Use block-paired contrasts with repeated founders,
recipients, cue episodes and record arms retained within each block. Choose one
primary history/reader/contrast family before intervention outcomes; explicitly
handle multiplicity for any additional confirmatory claims.

## Measurements to retain

The core outcomes are current-body and fresh-reader both-cue success, separate
cue margins, and task-aligned signed transfer. Preserve incoming and outgoing
packets, activity at pulse/capture/recovery times, masks, random-stream definitions
and enough intermediate evidence for independent replay.

Candidate record diagnostics are relative normalized couplings, sign agreement,
cycle parity, support/reachability, returning-edge repair, exact-zero fallback
use and denominators. E054 should help reduce this list to justified measurements.
Raw weight distance or total weight strength is not a measure of functional
damage under normalized reading. A single sampled nonzero cue contrast does not
establish reliable cue responsiveness under independent noise.

Retain actual perturbation exposure, clipping and sampling windows. Diagnostic
trials must not feed back into the lineage or select cases. Spatial own-founder
specificity is not measured by this functional design; that belongs to CG-02.

## Findings that would change the interpretation

| Possible observation | Supported interpretation or limitation |
| --- | --- |
| The pulse affects the current body but no outgoing-record assay | Transient expression effect; no demonstrated inheritance at the tested dose and window |
| Early capture transfers an effect, reduced after recovery relative to the matching shams | Evidence that capture timing controls transfer of the pulse effect |
| The current body recovers but its outgoing record still impairs a fresh reader | Current-state recovery is insufficient to establish recovery of the transmitted constraint |
| Protected pulse/sham arms differ in a deterministic common fresh assay despite identical packets | A boundary or pairing error to resolve before scientific interpretation |
| Late capture helps pulse and sham equally | An ordinary timing effect, not a pulse-specific recovery benefit |
| Renewed records are no more susceptible, or are less susceptible | The hypothesized increase in susceptibility with this renewal history is unsupported |

Null results need precision bounds, not an equivalence claim from a nonsignificant
contrast. Neither a single successful recovery nor a single inherited disturbance
establishes indefinite stability or irreversible loss.

## Parked extensions

Clustered versus spaced pulse trains could compare equal pulse count, amplitude,
integrated squared forcing, total elapsed time, final recovery interval and
write count. Following a small fixed number of additional read–write cycles
could test persistence. Neither extension is part of the initial comparison
unless explicitly selected and frozen before E055 outcomes. Later expansion
after seeing those outcomes must be labelled a new follow-up.

Because the record is fixed within a read, pulse spacing alone tests activity
recovery before capture. A claim about a slow maintenance-capacity threshold
would require explicit repeated updates or a separately declared slow repair
mechanism. The spatial recovery/specificity study (CG-02) and acquisition-quality
study (CG-03) stay outside E055's current scope.
