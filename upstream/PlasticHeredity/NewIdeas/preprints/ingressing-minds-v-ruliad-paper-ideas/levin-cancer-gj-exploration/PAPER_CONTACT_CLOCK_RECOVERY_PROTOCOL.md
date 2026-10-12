# P10R: bounded-clock recovery of the common-graph timing experiment

Registered on 2026-09-14 before P10R biological integrations. User authorized
correction/verification of the timing problem and renewed comparisons. The failed
P10 attempt, all P1-P10 executed files and native checkout remain unchanged.

## What failed, and what is being changed

P10 ran all 60 initial cases but stopped at the screen audit (2026-09-14 02:25:47 UTC).
Six isolation phases had one saved sample at 5,000,000 or 10,000,000 units instead
of a 10,000-unit hold. Ten phases in total had their last saved time more than 10%
past the requested horizon; the old audit caught six, not all ten. The adaptive
Euler loop can propose very large steps near equilibrium and does not cap them
at its requested end time. Coarse/fine label agreement does not resolve this.

P10R changes the numerical clock and observation sampling, NOT biological parameters,
wiring, contact schedules, founder choice, selection priority or retention threshold.
Use the pinned native sim_slopes function and the native explicit Euler update and
adaptive relative-concentration/voltage proposal. A source-external adapter then
caps each step at (a) the next observation, (b) the requested phase boundary and
(c) a declared maximum step. No native file is edited.

Maintain time as integer multiples of the base timestep to reach the endpoint
without cumulative clock drift. Observe the actual live state at time zero, every
100 units, and the exact phase endpoint; never fabricate samples by repeating a
final state or relabel a sample taken beyond the window. Maximum actual step is
100 units coarse and 50 fine. Fine additionally halves the base timestep and both
native adaptive increments, as in P10. These settings are frozen before any P10R
scientific output and are not adjusted based on desired state labels.

Save every proposed and accepted step in the raw phase artifact. The independent
audit verifies exact observed times, exact final time, positive integer advances,
sum of steps, the step cap and clipping at EVERY observation/phase boundary.
Both 10k retention holds now supply 26 regularly spaced late samples (>=7500).
The same >=95% late-sample and live-endpoint criteria apply separately to both holds.

This is a numerical-method change. It is not an unchanged-native-integrator
replication. It cannot retroactively validate the failed attempt, and a bound on
time steps alone is not a mathematical proof of numerical convergence.

## Fixed staged experiment

1. Freeze a complete auditable copy of P10's 60 cases, its frozen execution files,
   inputs and saved gate/calibration/screen audits. Re-audit the failure without
   editing it, requiring exactly its six recorded failed checks. Verify the ten
   >10% overshoot phases. Also freshly re-audit the original P9.
2. Run the same two exact P7 historical replays with the ORIGINAL native integrator.
   These remain source-reproduction checks, explicitly distinguished from P10R.
3. Twelve targeted clock probes: six coarse P10 pre-hold starts, each rerun in
   coarse and fine P10R clocks through two isolated 10k holds. Sources: simultaneous
   open in both M founders, sequential cut in both, and 50% overlap open in both.
   Take ALL 17 concentrations and all three actual pupil identities from the INITIAL
   array of the old r01_isolated_1 phase, not its overshot final array. Each fine
   probe shares its coarse probe's frozen coarse input. These are post-failure
   diagnostics, not new lineages or independent replication. Require correct
   clocks and coarse/fine endpoint/retention agreement; do not require reproduction
   of the old possibly invalid state outcome. Failed diagnostics stop the panel.
4. Repeat all eight common-graph calibration cases with the bounded clock.
   Require open ordinary-M -> retained MEE, EEE in RNA/cut/sham controls, and
   preserved M teachers. A technically valid negative calibration is a valid stop.
5. Repeat the ENTIRE 50-case timing screen with the bounded clock: all seven schedules,
   both M founders, every E sham and sequential RNA/cut controls, coarse and fine.
   Restart main trajectories from the unchanged registered P9/ordinary reference
   sources, NOT from P10's successful screen endpoints. Do not mix old and new
   numerical methods in selecting schedules.
6. Apply the original common-to-both-founders selection rule to the NEW screen:
   eligible sequential plus first eligible alternative in priority simultaneous,
   overlap_50, overlap_25, uneven, gaps_10, short_10. At most two schedules.
   Continue their ACTUAL new screen pupils through rounds 2-6 under open, RNA-block,
   and cut conditions at both resolutions. Fine continuations use their own fine
   screen starts. No automatic substitute schedule after a continuation fails.

All inherited P10 details in [PAPER_CONTACT_SCHEDULE_PROTOCOL.md](PAPER_CONTACT_SCHEDULE_PROTOCOL.md)
remain fixed except numerical clocks/sampling and the explicit added diagnostic
stage. One six-cell eight-edge graph, 80k contact window plus two 10k holds, no
pupil resetting while waiting, no teacher retained across handovers, no selecting
a successful subset, no donor supplementation and no pooling. All seven schedules
are tested again. Equal open-contact time is not equal molecular flux.

## Counts, stopping, provenance and limits

Two native replays + twelve clock probes + eight calibrations = minimum 22 cases
for a valid graph-ineligible stop. A complete screen brings the total to 72; at
most 24 continuations gives 96. Integration-call bounds: 54 after calibration,
390 through the screen, maximum 1,230. Only six calls in the two historical
replays use the original native integration loop; the others use native equations
under the explicitly changed clock adapter. Shared screen prefixes are counted once.

Freeze 84 local files plus the 36-file native manifest and 734 historical input
files, including the failed attempt archive. Keep input/source/frozen/phase/result
hashes, full identity/state continuity, gate equations, timing traces, eligibility,
selection, stopping and finer comparisons independently auditable. Diagnostic
outcomes and old screen labels are excluded from schedule selection.

Two single-threaded workers; four-hour per-case and eighteen-hour panel caps.
The detached supervisor first runs the full software-only regression suite with
a 1,800-second cap; no biological simulation starts unless that suite passes.
Runner/audit/overall supervisor bounds are 65,100 / 1,800 / 69,000 seconds,
including verification in the overall bound. Require 5 GiB free before workers
and phases. Launch detached after focused recovery tests pass; the user polls.
No retries, parameter searches or automatic
follow-on. A clock/fine/integrity failure stops and remains failed.

This recovery is not evidence for autonomous reproduction, a unique PH mechanism,
an acquired-history advantage, wet-lab biology or therapy. The historical P9
founder prefix remains a fixed input, not a newly time-corrected replication.
