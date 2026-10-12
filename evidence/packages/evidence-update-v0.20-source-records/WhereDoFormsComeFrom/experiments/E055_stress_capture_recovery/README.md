# E055 — stress, recovery and capture

**Complete and independently verified, 11 October 2026 at 17:54 UTC.**
The full run took **1h06m**, including independent replay, ahead of the 18:15 UTC
forecast. All 32 blocks, **825 summaries**, **64,512 terminal cue observations**
and **18,432 current-body boundary cue observations** passed the audit. Controls
passed. The scientific figure was inspected and artifact closeout passed at
**18:56 UTC**, verifying 253 original outputs and all 26 frozen inputs.

**Primary result: transfer protection was not established.** The independent-noise
history retained almost all function even when captured immediately after the
pulse: next-body scattered-injury success was **96.29% versus 96.48% sham**.
The pulse effect was −0.20 percentage points (95% interval −0.59 to 0.00).
After recovery both arms scored 96.48%; the pulse-specific benefit of waiting
was +0.20 points (0.00 to 0.59). Neither the early-damage nor recovery-benefit
requirement exceeded five points. Late-function requirements passed. Current-body
success remained 96.68%, so the stronger joint recovery claim also failed.

| Record history | Early sham | Early pulse | Late sham | Late pulse |
| --- | ---: | ---: | ---: | ---: |
| Acquired | 100.00% | 100.00% | 100.00% | 100.00% |
| h32 shared-noise rewrite | 89.06% | 84.96% | 89.26% | 88.48% |
| h32 independent-noise rewrite (primary) | 96.48% | 96.29% | 96.48% | 96.48% |

These are fresh-recipient results under scattered injury, 512 lineages per
history. **The secondary shared-noise history provides a smaller lead:** early
loss −4.10 points (−6.25 to −2.15), late loss −0.78 (−1.95 to +0.20), and a
sham-adjusted benefit of later capture of **+3.32 points (+1.37 to +5.47)**.
These are secondary pointwise intervals, not a replacement primary claim or
proof of complete restoration. Current-body success changed by only −0.20
points at pulse end, suggesting that apparently adequate current performance
can coexist with a more vulnerable outgoing record.

The pulse was delivered without clipping and changed body states and outgoing
couplings. Relative to the time-matched sham, mean sign-disagreement counts in
the shared-noise records declined from 9.47 at early capture to 4.16 after
recovery; independent-noise records declined from 3.76 to 0.09. Pulse/sham
support was unchanged. These are descriptive mechanism clues, not a causal
separation of sign and magnitude effects. Protected pulse/sham packets and
recipient trajectories agreed exactly; erased records gave 0% success.

[Audited report](runs/capture_v1/REPORT.md),
[full intervals and diagnostics](runs/capture_v1/summary.json),
[independent audit](runs/capture_v1/INDEPENDENT_AUDIT.json),
[figure](figures/capture_v1/capture_recovery.png),
[artifact closeout](analysis/closeout_v1.json).

The user authorized implementation and execution after both predecessor closeouts
passed. Twenty synthetic checks and both retained technical runs passed. Each
independent audit replayed source extraction, pulse fields, every body/recipient
state hash, writing, diagnostics, scores and **825 statistical summaries**. Both
technical figures were inspected; technical scientific classifications remain null.

[Job status](jobs/capture_v1/status.json),
[launch verification](analysis/scientific_launch_verification_v1.json),
[frozen manifest](jobs/capture_v1/manifest.json),
[runtime/storage forecast](analysis/forecast_v1.json).

The question is whether a temporary disturbance of a body becomes a persistent
change in its outgoing record, and whether allowing recovery before capture
changes that inheritance. Compare acquired and repeatedly renewed records,
keeping current-body recovery separate from next-body reconstruction.

The fixed design uses all 32 E051 blocks, 512 lineages per history: acquired,
h32 shared-noise full rewrite and h32 independent-noise full rewrite. This reuses
existing records without selecting successful cases. The primary history is
independent-noise full rewrite; all current bodies receive independent intrinsic
cue noise, separating source history from the current writer environment.

After 2048 reading steps, apply one 32-step pulse to 64 randomly chosen living
non-port cells, identically across cues and without task-rule information. Capture
at pulse end and after 512 recovery steps, with time-matched shams. Two protected
packet arms and an erased packet complete seven outgoing arms. All are evaluated
by the same fresh reader under intact, scattered and square injuries.

The primary claim requires early inherited damage, a pulse-specific benefit of
later capture, late performance within five points of sham, and adequate absolute
late performance. Current-body recovery is scored separately and is also required
for the stronger joint recovery label. A favourable interaction alone is insufficient.

Float64 and the original zero-floor normalized reader are retained. E053's failed
combined-stress qualification is not treated as a pass. The pulse law, sample,
windows and criteria were selected before E055 outcomes; E054 informs separate
sign, support and relative-coupling diagnostics. This one-boundary experiment does
not test indefinite repair, serial persistence or biological ageing.

- [Frozen protocol](PROTOCOL.md) and [executable settings](plan.py).
- [Original planning skeleton](PLAN.md), retained as historical context.
- [Decisions and dependencies](DECISIONS.md), including predecessor findings.
- [Source provenance](SOURCE_DATA.json), [production model](model.py), and
  [independent replay](audit_model.py).
- [Twenty executable checks](tests.py) and [passing result](analysis/tests_v1.log).
- [Reading note](../READING_2026-10-10_CELLULAR_IDENTITY_GRAMMAR.md) and
  [experiment leads](../EXPERIMENT_LEADS.md): motivation and deferred alternatives.

The fixture completed in **7.35 seconds**, with simulation/replay workers taking
2.00/1.69 seconds. The full benchmark completed in **10.65 seconds**, with workers
taking 2.96/3.37 seconds. The padded forecast scales both components by reader/body
duration, recipient count and four worker waves, then applies a threefold margin.
Storage reserve is **0.85 GB**, below the **36.45 GB** free at launch. Three other
busy single-thread workers were observed, keeping the launch within the shared
twelve-CPU ceiling.

The scientific archive retains **442,374,090 bytes**. The detached workflow has
no automatic polling, restart or successor. E053/E054's frozen methods and results
are unchanged; no successor was launched at this status check.

[Technical readiness](analysis/technical_v1.json),
[fixture audit](runs/fixture_v1/INDEPENDENT_AUDIT.json),
[benchmark audit](runs/benchmark_v1/INDEPENDENT_AUDIT.json).
