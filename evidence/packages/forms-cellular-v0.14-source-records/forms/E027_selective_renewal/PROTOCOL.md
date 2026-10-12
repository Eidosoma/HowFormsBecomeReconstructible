# E027 — preserve surviving values and fill empty connections during renewal

Frozen before simulation, 21 September 2026. The user authorized a prospective
test of selective renewal following E026's final-packet intervention. E026's
83% hybrid borrowed restored values from full rebuilding; the present policy
must generate its own values across actual renewals on fresh cases.

## Local policy and cohort

Use **32 fresh blocks 24000–24031**, four founders and four lineages per founder:
128 founders and **512 lineages**. Excluded disposable fixtures and full-duration
benchmark use **900027**. All IDs were checked unused before preparation.
Keep every case; no selection, extension, threshold search or tuning.

At each of three renewals, physically erase edges incident to the same 24
scattered missing non-port cells used by the paired controls. Read the resulting
packet with local-strength compensation in the new body. Capture the usual
cue-averaged local products of tanh(3*activity), immediately after reading.
For each physically available coordinate, preserve its incoming value exactly
if it is nonzero; if it is exactly zero, use that coordinate's captured value.
All physically unavailable coordinates are zero in the outgoing packet.
The next generation receives that chain's own outgoing packet.

This is an explicit **copying-plus-infill policy**, with access to surviving
incoming weights for the copying component. The activity-only capture function
receives no record, label, mask, score or donor packet. No ancestral mask or
coordinate label is transmitted; the packet remains 512 float64 edges / 4096
bytes. Each decision uses only current availability and exact-zero incoming
weight. Tiny nonzero values are preserved, without an epsilon or strength
cutoff, until physically erased. Consequently, weak early repairs may be
frozen before they can mature. This bounded policy tests that tradeoff; failure
does not reject policies that allow weak repairs to be rewritten.

Keep E024/E025's acquisition, 16×16 lattice, gain 2, dt .2, noise .02,
birth SD .05, 2048 reading updates with amplification off for the first 256,
strict .25 margins and final-32-update observation window. Missing cells stay
absent throughout reading, immediate capture and the 128 holding updates.
Holding does not alter the outgoing packet. No output reteaching or assay
feedback enters renewal.

Retain eight chains in this fixed order:

1. Selective copying plus infill, with normalized reading.
2. The same selective rule with incoming reading blocked; surviving inherited
   values are still available to its copying component. Only its new values
   are produced without reading the packet.
3. Unchanged strength-compensated full rewriting.
4. Unchanged intact renewal reference with its fixed-four reader.
5. Protected copying.
6. Copying with cumulative matched erasures, the numerical no-infill policy.
7. Unchanged full rewriting with incoming reading blocked.
8. Unchanged full rewriting with outgoing writing blocked.

E025's baseline and degree-compensated branches are replaced by the two
selective branches; the six relevant reference/control chains remain unchanged.
The paired selective reading-blocked chain can retain function through copying.
It is not required to fail absolutely, or to differ at generation one when no
empty available coordinate has yet appeared. Signed zeros at erased edges are
functionally identical and do not count as retained nonzero weights.

Retain the initial packet and terminal assays after renewals one and three,
both fixed-four and local-strength receiving readers, three terminal injuries
(intact, scattered 24-cell loss, non-port 3×3 lesion), all seven arms (own,
foreign, shuffled, erased, untrained, communication-off, source-cut), and both
opposing cues. There are **34 terminal panels, 731136 terminal individual scores
and 18432 pre-capture body scores**. Retain all three boundary arrays, including
retained packets, retained/eligible coordinate masks, computed packets and
write states. Only outgoing packets cross generations; diagnostic arrays are
never fed back. Normalizers are recomputed after damage and controls, with zero
incoming drive at zero denominator. Rules, descendants, cues and panels stay
nested within 32 independent blocks.

## Primary and qualification

The single primary is the paired **selective-minus-full-rebuilding difference
in both-cue scattered-terminal success after three renewals**, both using the
local-strength terminal reader. Require its two-sided **95% whole-block
bootstrap lower bound >0**. This is a prospective superiority test of a new
policy; E026 suggested only a roughly three-point terminal-hybrid gain, so
E025's ten-point threshold for rebuilding versus copying is not used for this
different comparison. Report effect size and interval even if it fails.

Full qualification additionally requires all 13 flags:

- Selective intact and scattered both-cue lower bounds >.75 at both horizons
  one and three (four flags).
- All 24 original selective individual-cue/control gates at each horizon
  (two flags): six rule×injury accuracy lower bounds >.75 and 18 own-minus-control
  accuracy lower bounds >.10.
- All 24 original intact-renewal reference gates at each horizon under each
  terminal reader (four flags).
- Selective-minus-cumulative-erasure-copy scattered both-cue lower bound >.10
  at horizon three with the normalized receiver (one flag).
- Selective-minus-selective-reading-blocked scattered both-cue lower bound >0
  at horizon three with the normalized receiver (one flag).
- All 12 unchanged full-rebuilding minus reading/writing-blocked individual-cue
  lower bounds >.10 over both horizons and three injuries, using the normalized
  receiver (one combined flag).

Report primary superiority, the additional qualification conjunction and full
qualification separately. Preserve all failed gates. Report every group,
control, rule, margin, body outcome, receiving-reader effect, selective and full
rebuilding contrasts against every other chain, third-minus-first changes,
and the difference in receiver benefit between selective renewal and copying.
Use 10000 percentile resamples of whole blocks with stream
`["E027","bootstrap","selective"]`. All other intervals and qualification
gates are pointwise. No equivalence, noninferiority, population-certainty,
indefinite-renewal, autonomous-repair or unique-mechanism claim. No automatic
successor or pooled E026 observations.

## Verification and execution

Reuse the audited E023 terminal assay and scoring functions directly. Reuse
E016 teaching and E022 numerical reading/writing kernels and semantic streams:
E016 teaching, E022 develop/write by generation and assay/shuffle by horizon,
with E015 injury phases `E022_renewal_g{g}` and `E022_h{h}`. Fresh block IDs
provide independence; no outcome determines a seed, parameter or stopping rule.
The new body reader changes only the first two branches' denominators and the
declared reading block. Unchanged reference chains must reproduce E024 exactly
in disposable checks, including full trajectories and packet handoffs.

The independent auditor imports only earlier auditors. It replays teaching,
every body update, immediate capture, holding and every terminal update,
reconstructs masks and local denominators, and independently selects retained
versus new values using coordinate loops. It verifies source isolation,
own-chain handoffs, cumulative erasure, explicit copying access, all scores,
CSV rows, intervals and gates. Teaching sign symmetry tolerance remains 1e-10.

Seven short fixtures test exact-zero eligibility including tiny signed weights;
serial handoffs and unchanged reference trajectories; primary axes/direction;
explicit copy access and isolated activity capture; denominator/terminal replay;
zero-drive and no-infill identity; and independent end-to-end reporting/audit.
Estimate under two minutes from the previous 45-second suites. Freeze all
scientific code before fixtures; preserve every attempt and failure. Inspect
the audited fixture figure before benchmarking.

Run the excluded full-duration benchmark with one worker and one lineage per
founder. Its pre-run forecast is
`1.5*(E024_benchmark_worker_seconds+E024_benchmark_audit_seconds)+60`, using the
audited equal-sized six-body/34-panel workload with a 50% allowance for the new
selector. Benchmark storage is `1.5*E024_benchmark_bytes+1_GiB`.
The forecast exceeds 600 seconds, so detach it and await the user's status
request. Its outcomes cannot retune the design. After its audit, figure and
provenance pass, freeze the scientific runtime forecast as
`2.5*(E027_benchmark_worker_seconds+E027_benchmark_audit_seconds)*4*ceil(32/workers)+90`
and storage as `E027_benchmark_bytes*4*32+1_GiB` before launching the cohort.

Follow RUN_POLICY.md: at most 12 logical CPUs total and one numerical thread
per process; forecasts over ten minutes run detached with frozen inputs,
PID, log and durable status; the user requests status, without ongoing polling.
All writes stay inside experiments. Previous raw data, frozen code, manuscripts
and sister source trees remain unchanged.
