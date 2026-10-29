# After D191: captured information and ongoing embodiment

**18 October update:** the [D192 four-block panel](SNAPSHOT_ROUTES_PANEL_RESULTS.md)
is complete and saved-audited. Both-on updating improves residual recognition
over protected snapshot writing but harms common recognition; full-pattern
similarity is a separate outcome. The route contributions are conditional.
Current continuation: [D193 own-feedback versus recorded sister feedback](YOKED_REFERENCE_V1.md),
with [kernel qualification](YOKED_REFERENCE_STATUS.md). The notes below are
historical design motivation, not a pending D192 launch instruction.

16 October 2026 design notes; updated handoff 17 October. **D191 is now
complete and saved-audited.** Its [main results](FRESH_FOUNDERS_PANEL_RESULTS.md)
retain the modest residual direction benefit and larger common harm on fresh
histories. Protected held capture scores common recognition slightly above
captured live repair while full shape correlation is lower. That leaves the
route ambiguity below unresolved.

The successor [D192 design](SNAPSHOT_ROUTES_V1.md) now fixes the core routes,
complete intended controls, exposed source cohort and comparisons. Its
[complete-workflow qualification](SNAPSHOT_ROUTES_STATUS.md) passed 125 tests;
the excluded benchmark completed in 3m43s and passed the user-requested saved
audit on 18 October. [Results](SNAPSHOT_ROUTES_BENCHMARK_RESULTS.md) retain
opposite conditional body-access effects across families and the strong
protected-only comparator. The user approved the unchanged
[four-block continuation](SNAPSHOT_ROUTES_PANEL_STATUS.md). These original
notes are not a substitute for its qualified execution contract. D191's
founders, settings, controls, code and frozen evidence remain unchanged.

## Why another comparison is needed

The D186/D191 held-reference arm preserves a snapshot of the contemporary
post-damage body, not an intact pre-damage parent. In the D191 disposable it
matches captured live repair's common recognition/preference, while giving
lower shape correlation. [Benchmark](FRESH_FOUNDERS_BENCHMARK_RESULTS.md).
This cannot establish a need for ongoing maintenance: the held reference
influences both the body and the writer.

The actual implementation makes the ambiguity precise:

- [Reference feedback](../../blueprint_web/src/blueprint_web/engine.py) adds
  centered `c_m * (R - V)` after the native body step and then refreshes R.
- [Source step](../src/laws_confirmation/l22_source_recovery.py) writes
  `project((1-lam)*theta + lam*tanh(R), norm)` using the resulting reference.
- [Captured repair](../src/laws_confirmation/l22_early_capture.py) initializes
  R to V at birth. The held arm sets rho to zero, so the writer can repeatedly
  consult that exact captured field without needing later body observations.

Thus protected information can enter a later body through R directly, through
new theta written from R, and through subsequent body-derived reference updates.
The question is what the ongoing body adds **over a protected snapshot with a
matched writer**, not whether any arm containing a body succeeds.

## Proposed route separation

Keep one exact protected snapshot `S = V_birth` in every condition, with equal
byte capacity and availability. Never give a condition the old parent R,
target code, later outcome or a better pre-damage image. Keep incoming theta,
initial V, noise, durations, norms and writer clock matched.

Start with **fixed theta reading during repair**, so direct snapshot-to-writer
access cannot silently become snapshot-to-body access through rewritten theta.
Outgoing theta still changes and is tested in a separate fresh reader. The
existing captured/fixed condition provides the unmodified bridge. Live theta
feedback can be a separate, explicitly labelled mediation condition later.

For the updating-reference condition, distinguish the original snapshot term
from subsequent body observations algebraically:

`R_t = (1-rho)^t S + U_t`, with `U_0 = 0` and
`U_t = (1-rho) U_(t-1) + rho V_t`.

Freeze two direct-access gates, giving four cells:

| Snapshot supplied directly to body feedback | Snapshot supplied directly to writer | What remains |
| --- | --- | --- |
| Yes | Yes | Native captured/fixed route, requiring an exact bridge |
| Yes | No | Snapshot can guide the body; writing must use later body-derived reference content |
| No | Yes | Direct snapshot writing without its direct reference drive into the body |
| No | No | Initial body history and subsequent observations, without either direct snapshot route |

At the appropriate step, remove only the known decaying snapshot contribution
from the gated recipient of R. Do **not** set `c_m = 0`: that would also remove
the `-c_m V` damping term. Keep damping, centering, clipping, RNG consumption
and step order identical. Implement the both-on branch through the exact old
native equations and qualify its byte-for-byte bridge; do not substitute a
numerically different recurrence and assume equivalence over 1,000 steps.

These are gates on **direct access to the protected snapshot**, not deletion
of all historical information. Initial V is identical across cells and later
V may legitimately contain snapshot-mediated effects. That mediation is the
point of the experiment and must not be described as a no-history control.

## Necessary comparators and checks

Include the existing held-reference condition and a body-independent snapshot
writer that iterates the same projected theta update with S. In the held case
the direct writer should be exactly independent of later body trajectories;
failure of that equality is an apparatus problem, not evidence for embodiment.
The writer-only computation can be checked without simulating a body, while
any matched-cost body simulation must be charged honestly.

Retain both common and residual records, ordinary/fixed/captured native bridges,
intact/supplied controls, reader-off, writer-off and a wrong-source or scrambled
snapshot control with unchanged capacity. Preserve a body-derived writer and
the protected-snapshot-only writer as distinct baselines. A later benefit of
body observations must be measured against the latter, not only against zero.
An open-loop/yoked body trace can then test whether online feedback is needed
or whether recorded observations suffice; this is a further contrast, not an
unlabelled change to the initial route test.

Use unchanged theta-only fresh readout with recognition **and** preference,
continuous full-shape measures and all harms. Record source provenance,
snapshot identity, reference decomposition, writer inputs, costs and every
gate's leakage checks. Labels and guide-derived assessments remain outside
repair. A favorable arm alone establishes neither necessity nor autonomy.

Before execution: choose and freeze the minimal complete condition panel,
source cohort status (exposed or fresh), exact time indexing, state accounting,
contrasts and noise rule; qualify source/route/replay/scalar checks; benchmark a
complete disposable block; budget and freeze. No outcome-based selection from
D191, and no automatic serial-renewal study. One low-priority CPU unless the
user changes the limit; external data only; long runs detached without polling.

This plan is intentionally not yet a scientific registration. The later
registered contract must resolve each implementation detail before any new
route-study outcome. It does not promise that active embodiment will win.
