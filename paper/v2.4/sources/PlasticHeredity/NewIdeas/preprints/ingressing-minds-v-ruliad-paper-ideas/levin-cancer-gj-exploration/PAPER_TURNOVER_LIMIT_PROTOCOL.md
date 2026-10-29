# P16 — Turnover timing and surviving carriers

Registered before new scientific integrations, following user authorization
to pursue the next lead after P15. This experiment asks how quickly the actual
renewed patch can lose carriers and still retain and transmit E.

## Founders and native model

Use the actual final recipient trios from P15
`onward__{written,ordinary}__actual__patch__open[__fine]/isolated_2`.
Each resolution continues its own full 17-variable states and IDs at logical
time **1,180,000**. These are already three isolated cells; no tissue is reduced
or reset at this fork. Re-enable the two native edges of a 1×3 nonperiodic,
orthogonal chain, native depol gating, expression power 60 and miRNA
Kd=1.25e-14. There is no background tissue or external E cue.

An ordinary-E stock trio provides a third founder benchmark at logical time
zero. It uses the same archived stock as P15 and is not matched for prior age
or full state. There is one historical source per origin, not new replicated
lineages. All schedules are externally imposed; native BITSEY equations remain
pinned at b2cb370aaecbc8299f259bc4251d5396c81f19a6.

## Fixed screen

Cross all three founders and both resolutions with per-cell intervals
**tau = 1, 10, 100, 20,000** and four schedules. Positions below are zero-based.

| Schedule | One cycle, repeated twice |
| --- | --- |
| single | Replace 0, wait tau; replace 1, wait tau; replace 2, wait tau |
| pair_center | Replace 0 and 2, wait 2 tau; replace 1, wait tau |
| pair_edge | Replace 0 and 1, wait 2 tau; replace 2, wait tau |
| wipe | Replace all three, wait 3 tau |

Every schedule introduces six M cells, replaces each site twice, and spans
6 tau. Only the scheduled columns and IDs change. Surviving cells evolve
continuously. Pair schedules test a centre or edge survivor, so results do
not isolate batch size from geometry. Wipe is the complete-carrier-loss control.

Six fixed incoming states are generated from archived M stock by changing only
ZEB protein by an integer percentage in [-25,25]. SHA-256 words use namespace
`P16_turnover_limit_v1`, seed 501, and cycle/site index 0–5. The same percentage
perturbation for each cycle/site is used across schedules, rates, histories and
resolutions; coarse/fine runs retain their respective archived stock vectors.
Every incoming cell must initially classify M. No random source
search or retuning is allowed.

Immediately after the challenge, isolate all three actual remaining cells for
two 10,000-unit holds. The primary screen criterion is all three cells E at
both endpoints and at least 95% E occupancy per cell in each hold's last
quarter. Record every replacement window's endpoint and late occupancy
separately. A delayed recovery can pass final retention but cannot count as
continuous correction at every handover. All original carriers must be gone.

## Baseline, registered selection and follow-up controls

Before the screen, run six ordinary-E capacity cases: open/RNA-blocked/cut
three-to-three contact for 20,000, followed by two isolated 10,000-unit holds,
at both resolutions. Require exact raw numerical replay of P15's six stock-E
capacity assays. Also run six no-turnover controls: every founder at each
resolution stays connected for 120,000 (= maximum screen duration), then
undergoes the same two isolated holds. These bound the longest age exposure;
they are not age-matched controls for every short interval.

After the full valid screen, separately for each non-wipe schedule, select the
smallest tested tau where BOTH historical founders retain E at BOTH resolutions.
Stock E does not choose the interval. If none qualifies, select tau=20,000 with
reason `no_shared_retention`. This algorithm is fixed before outcomes. It
selects a follow-up condition, not a successful cell subset or independent
confirmation. No monotonicity or precise threshold is assumed.

At that selected tau, run matched RNA-blocked turnover for all three founders
and both resolutions (Kd=0 during challenge; ionic coupling remains). Then
EVERY selected open and RNA-blocked final trio supplies open/RNA/cut onward
assays, including scientific failures. Preserve actual full donor states and
IDs, add three fresh unperturbed M recipients in a 2×3 native sheet, contact
for 20,000 at power 60, remove all donors, and isolate recipients twice for
10,000. The source clock continues without resetting. Wipe has retention
assays at every rate but no onward follow-up in this bounded panel.

Onward success uses the same two-hold E criterion. Report retention, continuous
correction, onward transmission and their conjunction separately. A qualifying
RNA-dependence contrast needs positive selected-open retention and negative
matched blocked retention in both resolutions. Control-qualified transmission
also needs negative matched RNA/cut readouts; benchmark support additionally
needs positive ordinary-E capacity and negative capacity controls. Missing or
positive controls cannot qualify a chain. A control-qualified retention-and-onward
chain additionally requires negative E retention in the matched wipe screen at
the selected tau, founder and both resolutions. Report carrier-dependent retention
separately; wipe outcomes do not alter the follow-up selection rule.
Scientific negatives never suppress
scheduled controls or readouts. A failed baseline is reported, not used to
discard the screen. Technical audit failures stop progression.

## Clock, audits and bounded execution

Retain the existing integer-tick bounded native Euler implementation. For a
phase of horizon H, sample every min(100,H/20) units and cap steps at
min(100,H/100) units (half that cap in fine runs). Fine runs also halve the
native base step and adaptive increment limits. Thus short phases have at
least 21 samples; 10,000/20,000-unit phases retain P15 clock settings. Record
actual steps, proposals, sample ticks and live initial/final states. No
interpolation or timestamp relabelling. A new independent audit verifies the
phase-specific clock; predecessor audit code remains unchanged.

All discrete outcomes and phase-end labels must agree within every fine pair.
Continuous differences are reported; this is not a convergence proof or an
exact switching-time estimate. Failed fine agreement is a technical failure.

Stages and fixed total, including numerical pairs:

| Stage | Cases | Integrations |
| --- | ---: | ---: |
| Baseline | 12 | 36 |
| Full screen | 96 | 576 |
| Selected RNA controls | 18 | 120 |
| Unconditional onward assays | 108 | 324 |
| Total | **234** | **1,056** |

There are **117 fine comparisons**. The first 108 cases are fixed immediately;
the remaining 126 descriptors resolve from the registered selection algorithm.
Archive all auditable P15 inputs, and independently re-audit original and
archived P15 against its saved 24,043-check report before new science and again
in the final audit. Reconstruct every source transfer, replacement, survivor,
ID, topology, clock, classification, selection, control and replay from raw data.

Full software regression runs first. Two single-threaded workers; six-hour
case cap; 24-hour scientific-run cap including preflight; 90-minute regression
cap; three-hour final-audit cap; 30-hour overall supervisor cap; require five
GiB free disk. Limits are not an ETA. Launch detached, verify an advancing
heartbeat and return for polling. No retries, extra seeds, grid extensions or
automatic downstream launch. Freeze every execution/config/protocol/test file
at launch. Previously executed files and artifacts are never edited.
