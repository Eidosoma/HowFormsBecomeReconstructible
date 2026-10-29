# D192: direct snapshot access to body versus writer

17 October 2026. Fixed development design after [D191 closeout](FRESH_FOUNDERS_PANEL_RESULTS.md).
This document specifies the causal kernel and intended complete panel before
any D192 scientific outcomes. It is **not an execution freeze or a launch**.
First qualify the kernel; then qualify the complete saved-output executor,
freeze its inputs, and benchmark one complete excluded block. Budget and main
execution require a subsequent user advance. Do not edit D191 or earlier freezes.

## Question and cases

What do subsequent body observations contribute beyond a protected capture of
the contemporary post-damage body? Separate direct snapshot access to the body
from direct snapshot access to the writer, while preventing rewritten theta
from changing the body's reading during repair. This first experiment does
not establish that online rather than recorded body observations are necessary.

Use all D191 main histories **319100, 319101, 319102, 319103**, every message
and parent replicate, both common and residual records: 64 records/condition.
They are now **exposed development cases**, not fresh confirmatory cases.
Reuse their exact saved acquisition/boundary arrays and verify their D191
provenance. No reacquisition, favorable-case filter or cohort expansion.
The complete excluded timing block reuses D191 disposable **603191**, all 16
records. Kernel qualification uses synthetic/reduced inputs at **703192** only.
Never count either qualification or timing cases as main evidence.

## Fixed initial state and order of operations

For each packet family, `V_0 = body_own`, `ema_0 = 0`, incoming
`theta_0 = built[family]`. Preserve exact float64 arrays and the 2,048-byte
theta-only fresh-read boundary. `S = V_0.copy()` is protected for the complete
repair episode. No intact parent reference, label, target template, later
outcome or parent theta may enter repair. Scoring labels remain outside it.
Body reading always uses `theta_0`, never the current outgoing theta.

Unchanged physical parameters: 1,000 repair sweeps, writer rate 0.001,
record norm 0.3, native reference rate 0.002, coupling 0.2, tissue/rulebook,
noise and clipping. Retain checkpoints 0, 1, 50, 250, 500, 1000. Repair uses
the native `l22-active-form-boundary-v1:<index>:repair` stream, paired across
all body-simulating arms. No gate consumes additional RNG values.

Let the full reference start at `R_0=S`, `a_0=1`. At sweep t:

1. Body access is `R_(t-1)` when enabled, otherwise
   `R_(t-1) - a_(t-1)*S`. The native body step and centered
   `c_m * (body_reference - V_native)` feedback still run. In particular,
   **retain the −c_m V damping term**; setting c_m to zero is not this lesion.
2. Update the full reference with the actual resulting body:
   `R_t = R_(t-1) + rho*(V_t - R_(t-1))`.
   Update `a_t=(1-rho)*a_(t-1)`; define `U_t=R_t-a_t*S`.
3. Writer access is `R_t` when enabled, otherwise `U_t`. Update outgoing
   theta by the unchanged projected `(1-lam)*theta + lam*tanh(writer_input)`.

The body reads the **pre-update** reference; writing reads the **post-update**
reference. The both-on body/reference branch calls native blueprint_step with
its native rho, preserving exact floating-point order. The body-off branch
calls the same body physics with gated R and rho=0, discards that returned
reference, then performs the full-reference update above. It does not update
the full R from the already-gated R. Both-on must reproduce D186 captured/fixed
state arrays, packet and RNG digest byte-for-byte over the full schedule.

`U_t` algebraically contains later body observations; floating-point
subtraction is audited against an independent accumulated observation-only
recurrence with absolute tolerance 2e-12, never used to replace native R.
Save S, a, U, pre-step body input and post-step writer input at every declared
checkpoint, as well as native state and rolling input digests for every step.
Replay checks every step and exact saved inputs; no retrospective tolerance
increase. Initial checkpoint access fields mean the as-if initial accesses,
before any update; theta is still the unchanged incoming record.

## Complete condition panel

For each family, the core two-by-two gates are:

| Name | Direct S to body | Direct S to writer | Reference |
| --- | --- | --- | --- |
| B1W1 | On | On | Updating |
| B1W0 | On | Off | Updating |
| B0W1 | Off | On | Updating |
| B0W0 | Off | Off | Updating |

Gates remove **direct protected-snapshot access**, not all history. All cells
begin with the same history-containing V. Body-mediated snapshot effects in
later V and U are legitimate and remain. For a fixed body gate, changing the
writer gate must leave every V/ema/R byte unchanged because theta reading is
fixed. Outgoing records may differ.

Mandatory additional repair paths per family:

- `held_B1W1`: native fixed-reader held-reference bridge (rho=0).
- `held_B0W1`: no direct S drive to body; protected S still drives writer.
- `snapshot_only`: body-free writer using the same theta_0, S, lam, norm and
  1,000 update clock. It must produce exactly the same theta at every checkpoint
  as both held writer-on arms, independently of their body trajectories.
- `writer_off`: B1W1 with writing disabled; theta bytes must remain unchanged.
- `scrambled_B1W1`: identical initial body/packet but a protected S whose
  256 positions are permuted, with one permutation per replicate shared across
  messages and families. Seed namespace `d192-snapshot-routes-v1:<index>:snapshot_shuffle`.
  Preserve every value and full snapshot capacity. This changes only the
  protected capture, not V or theta. No outcome-based shuffle selection.
- `ordinary_fixed` and `ordinary_live`: unchanged D184 zero-reference bridges.
- `captured_live` and `captured_held_live`: unchanged D186 bridges, outside the
  fixed-reader gate factorial, retaining the historical embodiment comparators.

This is **13 named repair paths/family = 26**, including the two body-free
writer paths. Native fixed/average sidecar outputs are retained as two further
named packets/family (`ordinary_average`, `captured_average`), not silently
discarded or mistaken for matched protected-snapshot writing. Add unchanged
incoming packets/family, intact_parent, supplied_positive and reader_off:
**35 named read packets**. Exact packet/disabled-flag aliases may share one
physical read, with a complete mapping and honest cost accounting. No control
may be dropped because it is predictable or expensive.

## Fresh readout and analysis

Use the frozen fixed-theta readout: four paired draws per record, 1,000 sweeps,
checkpoints 0, 1, 1000. Two independent readout namespaces, nested under native
`l22-fixed-record-readout-v1`, are
`d192-snapshot-routes-v1:<index>:future_1` and `...:future_2`.
Build physical tissue from the integer index first. All arms in a future
share birth/noise streams; only theta and the explicit reader-off flag cross.
All 35 names appear in each future. These futures are new noise, not new founders.

Joint focal endpoints remain recognition and own-minus-partner preference,
with common/residual equally prominent. All seven D191 readout/shape endpoints
remain. Save absolute arm scores, per-record/per-draw data, every block/message
stratum, gain/harm/tie counts, both future means, equal-future/equal-block mean
and leave-one-block means. No pseudo-independent draw interval or selected
best arm. No success threshold, model fitting or claim of equivalence.

Freeze these signed comparisons for each family (first minus second):

- Direct body access with writer on: B1W1 − B0W1; with writer off: B1W0 − B0W0.
- Direct writer access with body on: B1W1 − B1W0; with body off: B0W1 − B0W0.
- Gate interaction: (B1W1 − B0W1) − (B1W0 − B0W0).
- Averaged body effect: half the sum of the two body comparisons; similarly
  averaged writer effect. Report these separately from conditional effects.
- Updating versus protected-only: B1W1 − snapshot_only and B0W1 − snapshot_only.
- Body-derived writing versus protected-only: B1W0 − snapshot_only and B0W0 − snapshot_only.
- Protected-only gain: snapshot_only − incoming.
- Gate gains: each of the four gate cells − incoming.
- Writer contribution: B1W1 − writer_off.
- Snapshot organization: B1W1 − scrambled_B1W1.
- Ordinary bridge differences: B1W1 − ordinary_fixed; captured_live − ordinary_live;
  captured_live − B1W1; captured_live − captured_held_live.
- Averaging comparisons: B1W1 − captured_average; ordinary_fixed − ordinary_average.
- Apparatus equalities: held_B1W1 − snapshot_only; held_B0W1 − snapshot_only;
  writer_off − incoming. Exact packet equality is required, not an inferred null.

There are **27 signed comparisons/family = 54**. A favorable body observation
effect supports a contribution under these settings, not autonomous repair,
necessity of online feedback, or complete form preservation. The snapshot-only
comparator prevents a live-vs-zero comparison from answering a stronger question.
Recorded/yoked-trace controls and live-theta mediation are later experiments.

## Qualification, costs and execution boundary

Qualify the kernel before any route-study outcomes: independent low-level
reference/body/writer replay, exact native bridges, wrong timing rejection,
snapshot identity/shuffle invariants, preserved damping, identical body states
across writer gates, held-writer independence under changed later bodies/noise,
writer-off identity, no input mutation, hidden-memory/label rejection, and
tamper detection for saved inputs/states/digests/packets. Test full 1,000-step
floating-point bridges using synthetic qualification inputs, not study cases.

Then implement/qualify the complete executor: pinned source provenance,
all paths/controls, theta-only fresh reads and replays, independent scalar
aggregation, exact output membership, write-once receipts, input/module closure,
crash retention and startup-only detachment. No full scientific run until this
qualification and execution freeze exist. The kernel alone is not a completed
experimental apparatus. No forecast or recipient policy is being fitted here.

External stage: `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-snapshot-routes-v1`.
Initial kernel-qualification cap **128 MiB**, including fixtures/logs/cache;
reserve 4 GiB free on the volume. A subsequent complete executor must calculate
and freeze its own bounded stage allocation before timing/main runs. Do not
silently enlarge this initial cap or remove failed artifacts to fit it.
S costs 2,048 bytes/record, in addition to native V/ema/R/theta and fixed theta_0;
a is a scalar shared across the batch. U and input fields are computed
diagnostics, not additional hidden information. Count temporary array memory,
body/writer sweeps, fresh reads, replay/verification time and retention separately.
Body-free snapshot_only receives no fictitious body simulation cost.

One process/thread, CPU 6, nice 10; code/docs only locally, all numerical data
and logs external. Any job forecast over ten minutes must detach with durable
logs and startup acknowledgement. No automatic progress polling, retry,
scientific main launch, audit or serial-renewal successor. User advances own
the next stage. L20/L22 remain STRESS_TESTED / MIXED.
