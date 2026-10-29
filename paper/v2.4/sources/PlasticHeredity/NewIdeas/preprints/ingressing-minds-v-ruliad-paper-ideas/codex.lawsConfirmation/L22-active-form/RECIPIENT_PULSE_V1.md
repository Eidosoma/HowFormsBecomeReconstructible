# D195: a recipient-specific disturbance after recording is sealed

27 October 2026. Fixed development design following the completed
[D194 diagnostic](YOKED_SEPARATION_RESULTS.md) and unchanged negative
[D193 panel](YOKED_REFERENCE_PANEL_RESULTS.md). This document precedes
qualification and any D195 scientific outcome. No favorable disturbance
search, alternate timing or later dose adjustment is authorized by this design.

## Question and intervention

Does own-body feedback improve the response to an event absent from a
previously sealed sister recording? Both focal paths contain a body and an
own-reference writer. This tests recipient contingency under a disturbance,
not the presence versus absence of embodiment or autonomous interface repair.

Reuse the exact D193 physical context, acquired source, initial state, writer,
carrier, repair noise A/B and both reader futures. Repair remains 1,000 sweeps;
only theta (2,048 bytes per record) crosses into a fresh reader. Generate and
independently verify the four undisturbed LL donor recordings first, then
seal them before any disturbed recipient. A receives B's same-history trace
and B receives A's. No disturbed trajectory becomes a donor.

**One fixed pulse, immediately before body step 501:** multiply V at rows
4 through 11 and columns 4 through 11 by -1, for every record. The central
8 by 8 patch covers 25% of the 16 by 16 body. Leave ema, own R, current theta,
fixed incoming body-read theta and protected starting snapshot S untouched.
The donor is not changed. Apply the same operator and timing in LL and YL;
the states can already differ, so equal operators do not imply equal absolute
displacements. Sign inversion preserves each body's pointwise absolute values
and total squared magnitude at the intervention. It need not preserve mean,
spatial arrangement or recognition. It consumes no RNG, reads no labels or
scores, and is an externally imposed perturbation rather than an autonomous
response. The size, location and midpoint timing are analyst choices, not a
biological calibration or a claim of minimal damage.

Retain pre-pulse, immediately post-pulse and post-step V/ema/R/theta, plus
the six original checkpoints. The first two event states must differ only in
the declared V patch. All pre-event checkpoints must exactly match the
corresponding undisturbed path; after the event, native update order resumes.
Synthetic qualification uses the same midpoint rule floor(sweeps/2)+1.

## Conditions, controls and scoring

For each family and repair role, retain eight paths:

| Path | Body reference | Pulse | Writer |
| --- | --- | --- | --- |
| LL | Own updating R | No | Own updating R |
| YL | Sealed sister trace | No | Own updating R |
| LL_pulse | Own updating R | Yes | Own updating R |
| YL_pulse | Sealed sister trace | Yes | Own updating R |
| writer_off | Own updating R | No | Disabled |
| writer_off_pulse | Own updating R | Yes | Disabled |
| trace_writer | No recipient body | Inapplicable | Sealed sister trace |
| snapshot_writer | No recipient body | Inapplicable | Protected S |

This is 32 paths: 24 body paths and eight body-free paths, including four
donors counted once. Writer-off packets must equal incoming theta; their
bodies must match the corresponding LL path. Recorded writing is exactly
the opposite undisturbed LL packet; role-pooled equality is structural.
Include both incoming packets, intact parent, supplied-positive and
reader-disabled controls: 37 named packets, two futures, four draws each.
Deduplicate only identical bytes and disabled flags within one future.

The primary signed contrast in **each family** is the disturbance interaction:

`(LL_pulse - YL_pulse) - (LL - YL)`.

The primary endpoint is terminal own-minus-partner preference; report own
recognition alongside it. Also report all four cell means, LL-YL separately
with and without the pulse, and each arm's change due to the pulse. A positive
interaction alone does not mean disturbed LL outperforms disturbed YL or
undisturbed LL; do not describe relative harm reduction as complete recovery.
Retain all seven original metrics, every record/draw, message, role, future,
gain/harm/tie count and signed comparison. The 16 comparisons per family also
include each focal cell minus snapshot writing, both writer-on/off comparisons,
both writer-off identities, trace-versus-snapshot, the structural pooled
trace-versus-LL identity, and snapshot-versus-incoming. No equivalence threshold,
fit, confidence claim from pseudo-replicated records or favorable-family pooling.

First execute the existing excluded benchmark history **603191**, all sixteen
records and both families. It is already exposed development material, not a
fresh test. Scientific main histories **319100-319103** stay disabled in this
executor. A later unchanged four-history panel needs its own qualified adapter
and launch, budgeted from the complete benchmark. A fresh transfer study would
need a separate registration. Qualification uses the inherited synthetic
index **703193**, reduced schedules and one parent per message only.

## Qualification, provenance and resources

Keep all D191-D194 source, code, protocols and freezes immutable. Reuse the
qualified D193 workflow in an isolated adapter; do not patch live module globals
belonging to earlier workflows. Disclose the reused workflow/statistics formats
and shared native physics. The new independent checker implements the pulse
and step ordering separately, verifies all state fields and packet bytes,
replays each donor and each new path, and checks scalar scores/aggregation.
Bind exact saved arrays and metadata to replay receipts. Saved-only audit must
not advance dynamics. Reject wrong timing, patch, route, provenance, omitted
cases, rehashed corruption, extra channels, changed resources and output reuse.

The complete benchmark includes source verification, donor generation/sealing,
recipient and reader execution, independent replay, all controls, scalar
aggregation, I/O and saved-output verification. The fixed reader futures and
unperturbed repairs use the original D193 addresses, allowing exact bridges;
they are not additional independent evidence. Old scientific outcomes are not
pooled into the new estimates. No source acquisition is regenerated.

New external stage:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-recipient-pulse-benchmark-v1`.
Cap **2 GiB**, including failed qualifications. Reserve **512 MiB** for the
benchmark and **512 MiB** per qualification admission, **64 MiB** headroom and
**4 GiB** free-volume reserve. Charge complete donor traces and extra event
arrays; no capacity-matching claim against a single snapshot. All numerical
data, fixtures, outputs, logs and caches remain external; code/docs only here.

One CPU/thread, **CPU6, nice10**. Initial complete-block allowance **20 minutes**
is conservative, not a measured ETA. Launch detached with durable logs and
startup acknowledgement. No automatic polling, post-completion audit, retry,
main launch or successor; the user's next status owns completion readback.
Qualification and freeze must complete before that launch. Retain failures.

Positive, null and harmful results all remain evidence about this particular
intervention. L20/L22 remain STRESS_TESTED / MIXED. The queued recipient
matching decision test still needs frozen choices on fresh cases against
the best common setting and simple family/writer choices after shared L22.
