# Experiment leads

Updated 12 October 2026. Candidate list, not a frozen protocol or a launch queue.
The experiment table, including completed E055/E056 and running E057, is in [README.md](README.md).
CG identifiers below identify ideas; CG-01 is now implemented as E055. Its
[frozen protocol](E055_stress_capture_recovery/PROTOCOL.md) controls that experiment.
Existing numerical criteria and frozen predecessor designs are unchanged.

## Current priority

E053 and [E054](E054_record_interventions/README.md) completed independent audit
and closeout. E054 found strong sign sensitivity in both rewriting histories,
with much greater magnitude sensitivity in the shared-noise history.
The new [cellular-identity reading note](READING_2026-10-10_CELLULAR_IDENTITY_GRAMMAR.md)
adds three candidates for subsequent work; it does not expand E054.

After reviewing both predecessors, the user authorized
[E055 stress, recovery and capture](E055_stress_capture_recovery/README.md).
It completed on 11 October at 17:54 UTC, with independent audit and artifact
closeout passing. The primary independent-noise history tolerated this pulse:
the planned damage-and-recovery claim was not established. The shared-noise
history showed a smaller secondary capture-timing effect. The other two
candidates remain separate; no successor was launched on this status check.

**Completed [E056](E056_sign_magnitude_substitution/README.md):** separate the signs and magnitudes
of E055's paired pulse/sham outgoing records. The shared-noise history is the
focal follow-up because its secondary timing effect is now known; acquired and
independent-noise histories remain comparison groups. This is an outcome-informed
mechanism study on reused records, not fresh confirmation. Independent scientific
replay passed on 12 October at 00:08 UTC and artifact closeout passed at 11:11 UTC.
All 32 blocks and 1,506 summaries were verified. The early shared-noise panel
scored 90.04% sham, 87.50% pulse, 87.50% with restored signs and 90.04% with restored
magnitudes. Both conditional magnitude gains were **+2.54 points [0.98, 4.30]**
using the frozen family-adjusted 99% intervals. Both sign effects were
**0 [−0.98, 0.98]** and the observed interaction **0 [0, 0]**; all three remain
unresolved under the frozen strict rules. This supports an effect of magnitude
placement in these records, without making signs generally irrelevant or
establishing complete restoration or autonomous repair.

At each of the early and late captures, let C be the matched unstressed record
and P the pulse record. Compare the following four packets under identical fresh
readers and injuries, retaining every source case:

| Signs from | Magnitudes from | Interpretation |
| --- | --- | --- |
| C | C | Original unstressed record |
| P | P | Original pulse record |
| C | P | Restore unstressed signs while retaining pulse magnitudes |
| P | C | Restore unstressed magnitudes while retaining pulse signs |

Construct each hybrid as sign(source of signs) times abs(source of magnitudes).
Verify identical support before interpreting this factorization; do not silently
drop mismatching cases. Retain functional success, cue margins, signed transfer,
port-relative sign alignment and normalized coupling. The sign substitution
preserves the chosen magnitudes and normalization denominators; magnitude
substitution changes the denominators and relative couplings, so raw weight mass
is not a sufficient explanation. Estimate both conditional substitution effects
and their interaction with paired whole-block inference fixed before outcomes.
Recovery of a hybrid would establish the effect of that controlled substitution,
not an autonomous repair process: the matched unstressed reference is supplied.

This is narrower than a generic connectivity test. E055's pulse/sham support,
reachability and cycle rank were unchanged; all four captured shared-noise arms
had zero fallback use and zero negative basis-cycle counts. Sign differences
therefore do not by themselves demonstrate inconsistent sign loops. The writer's
non-fallback products d_i*d_j enforce positive cycle products; cue/port alignment
and the placement of relative magnitudes still matter. E056 now supplies direct
substitution evidence for a magnitude contribution to the early pulse loss.

**Running [E057](E057_fresh_capture_confirmation/README.md):** confirm the
shared-noise timing effect and magnitude substitution on 32 newly generated
source blocks, keeping E055's pulse and windows and E056's interventions
unchanged. The [frozen joint claim](E057_fresh_capture_confirmation/PROTOCOL.md)
has four directional contrasts, each with a 98.75% family-adjusted interval.
Fresh acquisitions and two 32-renewal chains precede the pulse and substitutions.
It launched with eight workers on 12 October at 11:39 UTC after sixteen checks,
both full technical chains, independent replay and figure inspection. The padded
finish including scientific audit is around 17:00 UTC. The new E056 readers give a secondary
sham-adjusted timing benefit of +2.34 points [0.98, 3.91], pointwise 95%, but reuse
the same sources. Serial persistence or autonomous rewriting after capture is a
subsequent question. Keep E055's failed primary claim separate from these new,
explicitly motivated hypotheses. E057 was launched only after the user's subsequent
“lets go” instruction; no later experiment is queued automatically.

| Priority | Candidate | Distinguishing question | Status |
| --- | --- | --- | --- |
| Completed predecessor | E054 | Which signs, magnitudes and connections support fresh reconstruction? | Complete and independently audited; closeout passed 11 October 16:16 UTC |
| Completed first test | CG-01 / [E055](E055_stress_capture_recovery/README.md): stress, recovery and capture | When does a temporary body disturbance become a persistent change in the next record? | Audited primary claim not established; secondary shared-noise early loss 4.10 points, sham-adjusted recovery benefit 3.32 [1.37, 5.47]. Mechanism and fresh confirmation remain leads |
| Completed mechanism test | [E056](E056_sign_magnitude_substitution/README.md): paired sign/magnitude substitutions | Which changes in the pulse-written record cause its reduced fresh-reader performance? | Audited and closed: both primary magnitude substitutions improve success by 2.54 points [0.98, 4.30], family-adjusted 99%; no average sign benefit established. Reused sources, no autonomous repair |
| 1 | [E057](E057_fresh_capture_confirmation/README.md): fresh confirmation of capture timing and magnitude substitution | Do the timing benefit and the effect of restoring magnitudes repeat on newly generated records? | Running on 32 fresh blocks, eight workers; four primary directional requirements frozen before outcomes. Technical qualification and startup passed; padded finish around 12 October 17:00 UTC including audit |
| 2 | CG-02: recovery and historical specificity | Does renewed formation restore a particular history or only restore generic reconstruction? | Proposed; spatial branch, separate from routing function |
| 3 | CG-03: establishment and later susceptibility | Does initial writing alter recovery under a later common challenge beyond initial performance alone? | Proposed; requires fresh acquisition |

## CG-01 — temporary perturbation versus inherited change

**E055 result.** Independent-noise records retained 96.29% fresh scattered-injury
success at early pulse capture versus 96.48% sham, with both at 96.48% late.
Shared-noise records changed from 84.96% versus 89.06% early to 88.48% versus
89.26% late. The secondary sham-adjusted delay benefit was +3.32 points
(pointwise 95% interval +1.37 to +5.47). Current-body success barely changed.
Support stayed fixed while signs and relative couplings changed. This motivates
testing which written changes transmit the loss, and confirming the secondary
history/timing effect on fresh source blocks. It does not justify increasing the
pulse until the original primary criterion passes or claiming biological repair.

**Prediction.** A controlled pulse can disappear from the current body's activity
yet remain consequential if it was captured into the outgoing record. Recovery
before capture may reduce that persistent effect, with a different response for
acquired versus repeatedly renewed records. Both directions remain possible:
E019 already shows that simply waiting longer to capture can be harmful.

**Implemented first test.** E055 reuses all 32 E051 blocks of acquired and h32
full-rewrite records, with shared and independent rebuilding-noise histories kept
separate. This is mechanistic reuse, not fresh confirmation. Pulse amplitude,
duration and coverage were fixed from the model's activity scale before outcomes,
without a dose search. The pulse is independent of the hidden task rule and
record outcome and identical across cue episodes. Current-body intrinsic cue
noise is independent for every history, separating inherited history from the
new writer environment. Hold the incoming record fixed while observing the body,
as the original reader does.

Compare a pulse and a sham at the same time. Capture at the pulse endpoint or
after a fixed recovery interval; give each capture schedule its own sham. Use
the same total observation time and external input exposure, with identical
injury availability. Also pass forward an unchanged-record control subject to
the same physical erasures. This is a protected transmission control, not a
model of biological maintenance. Reset the recipient completely and test every
outgoing packet with the same fresh, unstressed reader.

The focal effect is the pulse-minus-sham change in **next-body** function at
each capture time. Compare those changes across record histories. Record current
body recovery, both-cue success, cue margins, signed transfer, normalized
couplings and sign/connectivity changes. Use held-out diagnostic cue trials if
estimating reliable cue sensitivity; a single nonzero contrast under independent
noise is not sufficient.

**What would weaken the hypothesis?** A disturbance affects only the current
body and leaves no fresh-reader effect; or recovery timing has no pulse-specific
benefit after its matched sham correction. Greater susceptibility of renewed
records is a separate interaction to test, not an assumed outcome.

**Second stage only if useful.** Clustered versus spaced identical pulse trains,
with equal pulse count, amplitude, integrated squared forcing, total elapsed
time, write count and final recovery interval, followed through a small fixed
number of actual read–write cycles. Define schedules before outcomes. A spacing
effect while records stay fixed tests fast recovery before capture; it does not
by itself demonstrate a slow maintenance-capacity threshold. Such a claim needs
explicit repeated updating or a separately declared slow maintenance mechanism.

**Why new?** E019 and E033–E035 changed timing; E051 changed cue pairing; E054
changed stored content without rewriting. This test isolates whether a transient
perturbation is transferred by the writer into future reconstruction.

## CG-02 — renewed formation versus recovery of a particular history

**Prediction.** An intervention may restore stable formation or total agreement
without restoring the extra information supplied by an own founder's history.
This is the relevant distinction when interpreting a reset as rejuvenation.

**Smallest useful test.** Use all E014 blocks at declared saved horizons, such
as after3 and after16, retaining each own/foreign lineage pair and its shared
background. Ordinary continuation is the autonomous body-written renewal arm.
Contrast it with a change confined to the current body's relaxation and with
restarting the original unprescribed formation process under the same background
using new initial states/noise, without access to the founder prototype or
original packet.
The relaxation arm leaves the transmitted record unchanged. Fix intervention
duration and subsequent reader conditions, with time-matched controls.

Include protected own-record restoration as an **external-memory positive
control**, matched foreign-record restoration under the same background, and
erasure. Access to the saved original packet is restricted to those explicit
controls. Re-running the original random seed would also supply historical
information and is not an autonomous reconstruction condition.

Score every arm against the same own-founder prototype. Report own and foreign
qualified agreement, their paired difference, protected-copy agreement, sign
agreement, amplitude qualification and formation separately. Fresh checkpoint
bodies must not feed back into the chain. Observe another fixed boundary after
the intervention to distinguish immediate recovery from transferable recovery.

**Interpretation.** Higher total agreement with no increase in own–foreign
advantage means restored reconstruction without demonstrated restoration of
that history. Recovery of both would be a stronger result, provided it does not
depend on external access to the lost founder. Missing an effect is not proof
that recovery is impossible. Routing-task competence belongs to a separate
functional assay; the spatial score must not be relabelled as routing success.

**Why new?** E014 measures decay and retained specificity; the new contrast
intervenes on recovery and asks whether those two quantities recover together.
It also tests the limits of the review's maintenance-versus-rewriting distinction
without equating numerical rewriting to a molecular reprogramming treatment.

## CG-03 — establishment quality and later susceptibility

**Prediction.** The way a record is first established can affect resistance and
recovery during later challenges, even when an initial coarse performance score
looks similar. More acquisition time is only a manipulation, not proof of better
writing or a deeper attractor.

**Smallest useful test.** On fresh independent blocks, vary acquisition duration
or temporal coordination before a common later reader/writer regime. Start with
one manipulated axis. Include a control spending the added elapsed time in
ordinary relaxation instead of extra instructed acquisition. In the functional
branch, disclose any difference in teaching exposure; extra target information
cannot be attributed solely to maintenance quality. Retain every acquisition,
including failures, and pair later injuries and noise across treatments.

Cross acquisition settings with an unstressed condition and one fixed later
challenge chosen before scientific outcomes. Measure initial performance,
recovery probability under a frozen perturbation ensemble, and performance after
a short fixed sequence of rewrites. Report baseline differences and the paired
acquisition-by-challenge interaction. Avoid selecting successful cases to make
starting performance appear matched; any matched-baseline subset is secondary.

An operational buffering measure is the probability of returning to a declared
response class within a fixed recovery time after prescribed perturbations.
Neither raw weight magnitude nor a binary successful read estimates basin depth.
The normalized reader makes global positive weight scaling a particularly poor
proxy for stronger constraints.

**What would weaken the hypothesis?** Added acquisition time changes initial
performance but not subsequent susceptibility; or the apparent protection is
accounted for by extra teaching exposure or reader timing. A positive result
would concern this acquisition schedule, not the cross-species relation between
developmental duration and lifespan.

## Shared requirements before any candidate becomes an experiment

Fix the source cohort, perturbation law, observer, primary contrast, interval
procedure and stopping horizon before intervention outcomes. Choose doses using
excluded fixtures, retain all declared cases, resample independent blocks and
separate exploratory reuse from later fresh confirmation. Match both physical
damage and computational/teaching exposure where the contrast requires it.
Record any unavoidable mismatch rather than calling different interventions
equivalent by construction.

Benchmark the actual proposed scope, including independent replay, before giving
a runtime estimate or launching. Follow [RUN_POLICY.md](RUN_POLICY.md). No new
simulation or automatic successor was started while adding these leads.
