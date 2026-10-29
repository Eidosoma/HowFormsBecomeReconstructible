# TT044 — crossing receiving states and stochastic forcing

Authorized after reviewed TT043. This is development on its four exposed source
blocks (39010000, 39010016, 39010032, 39010048). TT043 already revealed a
late-minus-preserved success gap between continuing and fresh receiving profiles
even when feedback was off in both. This design is informed by those outcomes;
freeze before any new production crossed-condition outcomes.

Hold feedback off (c_m=0), memory updating native (rho=0.002), and writing off.
Supply the actual preserved T0 or late-written T1 packet. Cross two starting
states with two stochastic forcing streams, within each original block,
mixture/family/source/mask and source position:

- CC: continuing state, continuing forcing (the existing continuing baseline).
- CF: continuing state, fresh forcing.
- FC: fresh state, continuing forcing.
- FF: fresh state, fresh forcing (the existing fresh baseline).

The continuing state is the preserved body's V/ema/R at original update 1000.
The fresh state is a saved TT040 receiving birth, as retained in TT043. Copy
V/ema/R together without modification. Continuing forcing resumes the original
repair stream after exactly 1000 consumed Gaussian fields. Fresh forcing starts
the corresponding original assay stream. This changes the realized stochastic
stream, not its noise law or amplitude. Tissue parameters, physical update code,
duration and supplied packet remain identical across a conditional contrast.
All state/packet arrays are finite float64; the packet channel is the actual
16-by-16 theta field, 2048 bytes per record. No normalization, new injury,
teaching, repair or state reset is applied during continuation.

Use all four original fresh indices d in production, and the existing one per
excluded block in qualification. CF uses fresh forcing d with the single
continuing state; FC uses fresh starting state d with the single continuing
forcing; FF uses the original state-d/forcing-d pair. CC has no d dependence:
retain it once and reuse it only as a shared comparator. Do not count its reuse
as four body observations. This is a paired-index design, not the Cartesian
product of four fresh states and four fresh streams. It supplies no new
independent futures or state-local probability estimate. Pair all tasks and
interventions using their original within-block message-coupled forcing.

Observe all cells after 0, 1, 100, 500, 900 and 1000 updates. Retain all three
packet mixtures, common/residual families, own/foreign/neutral sources, all four
masks, tasks and histories, and target/donor/template/opposite credits. Keep
preservation, inherited original-packet readouts, every case and paired harm.
No selection by success, margin, warning, body difference or intervention gain.

## Outcomes and contrasts

The main panel is half-mixed/residual/own, all histories and masks, target
credit, at both 900 and 1000 updates. Estimate the late-minus-preserved effect
in each of CC/CF/FC/FF. Estimate how replacing the state changes that packet
effect under each forcing, how replacing the forcing changes it at each state,
and the state-by-forcing-by-packet interaction. Retain the FF-minus-CC packet
effect gap and both exact ordered decompositions: first change the state then
forcing, or first forcing then state. Do not assign a unique mediated fraction.

Also retain all six receiver-cell pairwise contrasts separately for each packet,
both state-by-forcing interactions at fixed packet, all checkpoints, continuous
target-versus-best-other margins, and 900-to-1000 within-arm changes. Coefficients
and the eight arm order are explicit in common.py and AXES.json. The result is
24 predeclared contrasts, not a significance gate or confirmation decision.
Show intact and fully replaced panels alongside the half-mixed panel.

Success credit is divided equally among tied winners and stored as integer
twelfths. Average masks and each cell's actual paired indices within a source
position. Retain harm/tie/gain counts for source-position means and individual
injuries. Also retain paired-index counts: one index for the CC-only packet
contrast, four for contrasts involving fresh states or fresh forcing. Repeated
CC values in a paired contrast remain shared comparators, not extra futures.
Retain explicit denominators. Continuous margins are descriptive secondary
outcomes and are not substituted for success credit.

Report four block effects, equal-nonempty-block means and pooled position means.
Four exposed blocks, not dependent positions/masks/paired indices, are population
units. State replacement bundles V/ema/R; it does not separately identify their
roles or a general mechanism. Fixed-stream interventions do not identify a noise
distribution effect. Sparse snapshots do not establish uninterrupted performance.
No new confirmation or serial-writing experiment follows automatically.

## Verification and bounded execution

Bind source states, packet bytes and baseline outputs to completed TT043
manifests. Copy its native kernel, independent equation audit and reference
equations unchanged; use feedback=False for every trajectory. Physical contexts
exclude labels and codebooks. Verify every new trajectory against independent
equations, RNG start/end and checkpoint digests, every held packet and scalar
score arithmetic. CC and FF must reproduce all six saved TT043 feedback-off
states and scores byte for byte, including R. Check that states pair across
forcing/packet and forcing pairs across state/packet. Preserve failed evidence.

Qualify one fixed excluded context serially, including all eight arms. Check
crossed-state custody, baseline replay, label/field rejection, one-ULP packet
mutation, incorrect stream position, factorial/decomposition arithmetic,
mask/index weighting, shared-CC denominators and unequal/empty-block aggregation.
Then run the full design on excluded blocks 608280 and 608281 with two workers;
require bitwise equality to the serial context and full independent replay.

Two normal-priority single-thread workers use CPUs 6/7 within the shared 12-CPU
ceiling. All writes stay in this lane. Study cap 8 GiB; free-space reserve 4 GiB.
Before dynamics, count distinct actual starting bytes and forcing identities,
deduplicating only physically identical work while retaining every labelled case.
Budget 1 MiB per complete physical batch, 1 GiB per phase for reductions/receipts,
and 64 MiB administration. Admission must cover qualification plus production
without deleting prior evidence. Check the cap and reserve between trajectories.

Forecast qualification as 1.5 times the measured eight-arm context duration times
the larger excluded block count divided by eight, plus 60 seconds. Require it
below one hour; deadline twice forecast, at least 600 seconds. Forecast production
as 1.5 times measured two-block qualification seconds, multiplied by the sum of
the maximum physical counts in the two production block pairs divided by the
smaller excluded block count, plus 60 seconds. Require forecast below four hours;
deadline twice forecast, at least 600 seconds. These are forecasts, not proved
runtime bounds.

The detached controller admits capacity once per phase, runs qualification once,
freezes if checks and budgets pass, then runs this authorized production once.
No waiting loop, automatic retry, extension or successor. One startup persistence
check, then leave long work unpolled until the user requests status. Prior
TT028/TT036/TT039/TT040/TT041/TT042/TT043 scientific classifications are unchanged.
