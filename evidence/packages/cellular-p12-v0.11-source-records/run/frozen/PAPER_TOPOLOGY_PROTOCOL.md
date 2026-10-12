# P4: same-memory location swap and separated communication compartments

Registered 2026-09-10 before P4 native integration. The user authorized the
location and connection tests after the P3 findings. Four bounded carrier-
replacement feasibility cases prepare, but do not launch, a later serial relay.
Config: `configs/paper_topology_v1.json`. No parameter search or outcome-driven
extension. Existing source and executed P1/P2/P3 files remain unchanged.

## Questions and limits

P3's centre samples never acquired M, so their later E state did not test
restoration. P4 puts the SAME genuine retained-M input at the edge and centre.
It also separates junction expression within the old patch from expression
across its boundary to new helpers. Is loss of corrective access, rather than
weakened internal reinforcement, responsible for P3's expression-only failure?
This is a hypothesis, not an established explanation.

Inputs are the three successful P3 edge acquisition banks (depol, nbrDepol,
hypol), deliberately chosen from known results before registration. They are
three deterministic exposure histories, not independent random replicates or
a held-out sample of all acquisition conditions. Each uses its actual final
17-component state after both acquired-state isolated holds. Original source
cells are not brought back. This is a paired counterfactual continuation of
the same inputs, not a new acquisition experiment.

The 2 x 2 sample uses indices [0,1,3,4] of the original nine; the 3 x 3 uses
all nine. Preserve order/orientation and original physical identities. In the
same 13 x 13 orthogonal, nonperiodic grid, patch origins are (0,5) and (5,5).
All other cells use the same common E stock from P3 reference preparation
(last returned snapshot, cell 168). Fresh M stock is reference cell 1.

## Fixed factorial panel

96 main cases = 3 held-M histories x 2 destinations x 2 patch sizes x 2 native
voltage modes (depol/hypol) x 2 internal powers (1/60) x 2 boundary powers (1/60).
miRNA Kd is 1.25e-14, contact 20,000 time units, OiET 0.5 and tness 1.
All helper-to-helper edges keep power 60 in this main panel.

Powers are limits on the native state-dependent overexpression factor, not
constant conductances. For edge e the unchanged native equation is evaluated
as `1 + tumorness_mix(e) * (power[e] - 1)`. A source-external wrapper supplies
the vector of preassigned edge powers to the unchanged native function and
restores its scalar bookkeeping value immediately afterwards. This per-edge
assignment is a NEW experimental intervention, not an original-paper feature.

Regions are fixed by cell identity: old-old, old-helper, helper-helper. They
do NOT change when a cell's E/M label changes. Native tumorness DOES update
continuously. All native transport physics and voltage gating remain present.
The expression gate scales all transported species; a regional intervention
can alter both electrical coupling and miRNA traffic, not miRNA alone.
Source hypol is a mode name (removal of an extra potassium gate), not a clamp.

Record the exact per-edge regions, powers and cut multipliers, initial/final
Vm and native voltage/expression gates. The raw `setup.power` is the restored
scalar reference/helper power, NOT a claim of spatially uniform power. The
compartment metadata and per-edge arrays describe the actual intervention.

## Restoration, withdrawal and onward assay

After contact, remove every helper and every regional/voltage intervention.
Preserve the actual LIVE native patch endpoint. Hold twice for 10,000 units
under common depol/power 1 with ALL junction transport and neighbour voltage
reading off. Take fixed local indices [0,1,side], even if unsuccessful.

The common P3 onward assay puts those three cells at indices 0/1/2 in a 2 x 2
grid and one fresh M cell at index 3. Run hypol/power 1/Kd 1.25e-14 for 20,000;
then remove all carriers and hold the recipient fully isolated under common
depol/power 1 for two 10,000-unit holds. No regulator reset or winner selection.

Primary outcome: genuinely acquired M in ALL input patch cells, then stable
E in ALL patch cells after withdrawal, plus stable E in the new recipient.
Secondary: the same criterion for the fixed three carriers. Stable means
final label plus >=95% late-quarter samples in BOTH holds. Use native E/M/X
two-unit miR200/Zeb mRNA difference. Report failures, partial outcomes, helper
M spread and retention without onward transfer without deleting any cases.

## Controls and causal contrasts

- Six gate cases: four P3 depol-history/edge/3 x 3 exact restoration replays
  (neither, voltage, expression, both), plus the two ordinary P3 onward assays.
  Replay all original NPZ arrays bit-for-bit; new per-edge diagnostic arrays
  are additional data, not substituted comparisons. A read-only P3 audit must
  first exactly match its saved 18,941-check, 465-integration audit.
- Twelve helper-power controls: all histories/destinations, side 3, both
  voltage modes, internal=boundary=helper=1. Compare to matching main cases
  whose helper power remains 60; do not silently call the latter uniform P3
  expression-only treatment.
- Six miRNA-blocked controls: each history/destination, side 3, depol,
  all powers 60. Block miRNA only; small-ion communication remains on.
- Six boundary-cut controls: same conditions, but multiply ALL transport
  across old-helper edges by zero, including added miRNA flux. Internal and
  helper-helper communication remain. No hidden neighbour voltage read exists
  under depol. Power 1 alone does NOT mean a disconnected junction.
- Sixteen finer continuations: depol acquisition input, side 3, all destinations,
  voltage modes and internal/boundary combinations. Halve initial step and both
  adaptive delta limits in every P4 trajectory phase. Historical P3 inputs
  remain identical, not re-prepared or refined. Require discrete outcome and
  phase endpoint-label agreement, and disclose concentration differences.

Independent analysis pairs locations for identical source/size/rules, internal
powers with boundary fixed, and boundary powers with internal fixed. These
are intervention contrasts within this model, not population success rates.
Location still changes contact counts and the surrounding graph: the old-helper
boundary has 3*side edges at the edge versus 4*side centrally. This panel does
NOT isolate contact count from wider geometry or explain P3 acquisition's
edge effect by itself. Border gate sums are potential coupling measures, not
directly measured net miRNA flux or proof of a unique molecular mechanism.

## Four replacement-capacity cases, not a serial relay

A separate fixed diagnostic uses a 2 x 3 grid: three old carriers in the top
row and three freshly initialized M recipients in the bottom row. Contact is
20,000 at hypol/power 1/Kd 1.25e-14, followed by removal of every old carrier
and two fully isolated common-rule holds of the three actual new cells.

The four prespecified inputs are ordinary E, ordinary M, actual restored E
from P3 depol/edge/side3/both, and actual failed-restoration M from its
expression-only counterpart. Use source patch indices [0,1,3], not cloned
evolved states. Ordinary reference initialization remains explicit.
Report how many of three recipients retain E/M. Stable E in all three is
a candidate three-to-three replacement capacity, not repeated renewal,
division or autonomous heredity. Negative capacity is an outcome and cannot
block or retune the independent location/connection panel. No second relay
round or outcome-selected follow-up is launched.

## Provenance and bounded execution

146 cases: 6 gate, 96 main, 12 helper-power, 6 blocked, 6 boundary-cut,
16 finer, 4 capacity. 858 native integrations. Freeze config, complete case
enumeration, all executed source/helpers, and exact P3 reference/bank/replay
inputs before integrating. Two fresh single-threaded workers concurrently.
Native revision `b2cb370aaecbc8299f259bc4251d5396c81f19a6` remains unchanged.

Per-case cap 7,200 seconds; panel 57,600 seconds (16 h). Supervisor runner,
audit and overall caps: 57,900/1,800/60,300 seconds. Require 5 GiB free before
each worker and native phase. No deletion, automatic retry, retuning, 3D,
proliferation, migration, tissue division or downstream launch. Runs expected
to exceed 10 minutes are detached, confirmed by a later advancing heartbeat.
This is a model intervention study, not wet-lab validation, clinical therapy,
independent implementation replication, a new attractor or autonomous PH.
