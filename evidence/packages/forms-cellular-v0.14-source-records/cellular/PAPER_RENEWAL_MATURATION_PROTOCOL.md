# P17 — Isolated retention versus continued renewal

Registered 2026-09-20 before new scientific integrations. The user authorized
the P17 lead after P16 closeout. P16's stored 100-unit trajectories show EEE
after the first replacement but MME after the second and MMM after the third
for both historical founders and resolutions. This motivates a direct fork
between isolated retention and further turnover; it is not evidence that a
particular maturation mechanism has already been identified.

## Sources and fixed timing grid

Use the same prechallenge founders and six incoming M perturbations as P16,
from its audited archive. Actual written/ordinary P15 onward recipient trios
continue at logical time 1,180,000, with their full 17-variable states and IDs.
The ordinary-E stock benchmark starts at zero and is not age/state matched.
Do not select only successful P16 final descendants: that would change the
timing comparison. Each numerical resolution uses its own historical states.

Fix **tau = 100, 300, 1,000, 3,000, 10,000, 20,000**. The endpoints reproduce
P16's failed/successful single-cell timing anchors. Four intermediate intervals
are new. Reuse namespace `P16_turnover_limit_v1`, seed 501, cycle/site draws
0–5, changing only incoming M ZEB protein by the same fixed integer percentage
in [-25,25]. Every incoming cell must initially classify M. Preserve the
native 1×3 orthogonal, nonperiodic chain, depol gating, power 60 and Kd=1.25e-14.
No surrounding tissue, new state variable or native equation change is added.

Cross all six intervals, all three founders and both resolutions with open
RNA transport and RNA blockade (Kd=0; ionic coupling remains). Blockade applies
from the first replacement throughout connected turnover. It is a counterfactual
history, not a block imposed only after correction has occurred.

## Exact-state fork after one replacement

First replace position 0 with incoming M draw 0 and evolve for tau. Save the
actual full trio once. Both subsequent arms begin from that identical endpoint,
with identical IDs and logical time, regardless of labels or later success:

1. **Isolate:** disable every junction and evolve all three separately for two
   10,000-unit holds. The focal outcome is retention of E by the actual incoming
   cell at position 0, without communication from the two old carriers. Record
   every cell's hold labels and late occupancy as well as whole-trio retention.
   Keeping the old cells as disconnected columns preserves numerical geometry;
   they cannot communicate with the focal cell. They are not used for an onward
   assay, since that would confound the newcomer's state with old E donors.
2. **Renew:** immediately replace position 1, then 2, 0, 1, 2, evolving for tau
   after each replacement. Preserve all surviving columns without resetting.
   Combined with the shared prefix this introduces six M cells, replaces every
   site twice and spans 6 tau. Then isolate the actual final trio twice for
   10,000. No original founder remains. Record the first newcomer's fate after
   the second replacement separately from success of the entire renewal chain.

E retention requires an E endpoint and at least 95% E occupancy per cell in
the final quarter of BOTH isolated holds. Continued renewal requires all three
final cells to retain E; continuous correction additionally requires the same
endpoint/late-window criterion at every replacement, including the shared
prefix. Never replace failed states with successful cells.

Report, per founder/interval/route and both resolutions: label of the newcomer
at the fork, focal isolated retention, continued-renewal retention, and the four
possible retention/renewal combinations. An E-looking cell that loses E in
isolation differs from one that retains E alone but fails during continued
turnover. Neither finding alone proves a specific molecular mechanism.

All turnover windows use tau. Thus the experiment compares complete schedules;
it does not isolate the first waiting interval from all later waiting intervals.
There is no assumption of monotonicity or an exact threshold between samples.

## Baseline, controls and bounded onward follow-up

Baseline includes six exact P16 capacity replays (ordinary-E trios, open/RNA/cut
readouts at both resolutions), six exact P16 maximum-age no-turnover controls,
and twelve whole-trio replacement controls (all six intervals, both resolutions).
Wipe replaces all three cells with the matched M states twice, waiting 3 tau
per event, then applies the two isolated holds. Its states after the first wipe
are independent of founder history; one stock-based wipe pair per interval
serves all founder contrasts and is not counted as separate lineage evidence.
The 100/20,000 wipe anchors must exactly replay their P16 raw arrays.

All 72 prefixes and all 144 forks run unconditionally after technical gates.
Open 100/20,000 prefix/renewal trajectories and RNA-blocked 20,000 trajectories
must replay the corresponding P16 arrays exactly, despite the registered split
into cases. These are continuity controls, not independent biological repeats.

After the full fork panel, choose TWO intervals by this fixed rule: find the
smallest tau where both actual historical founders retain E after renewal at
both resolutions. If there is a preceding grid point, choose it and that tau
(`shared_boundary`). If the first grid point succeeds, choose 100 and 300
(`left_censored`). If none succeeds, choose 100 and 20,000 (`no_shared_renewal`).
The stock benchmark and isolated-focal results do not choose the interval.
Keep the full grid visible; no threshold or monotonicity is assumed.

At BOTH chosen intervals, every founder's actual final renewed trio from BOTH
RNA routes supplies ALL open/RNA/cut onward readouts at BOTH resolutions,
including failed trios. In a 2×3 sheet, contact three fresh unperturbed M cells
for 20,000 at power 60, remove all donors and isolate recipients twice for
10,000. Use the same retention criterion. Continue actual donor states, IDs
and clock. Selection determines conditions, not a cell subset or independent
confirmation. A successful readout cannot repair failed earlier retention.

Control-qualified transmission requires positive open and negative matched
RNA/cut readouts at both resolutions. A control-qualified renewal-and-onward
chain also needs successful renewed-trio retention and negative matched wipe
retention. Benchmark support additionally needs a qualified ordinary-E capacity
assay. Report RNA-dependent renewal only for positive open renewal with negative
RNA-blocked renewal at both resolutions. Report focal RNA-dependence separately.
Scientific negatives never suppress an arm or onward case; only technical
failures stop progression. No further pair-loss/rescue panel is included here.

## Execution and stopping

| Stage | Cases | Integrations |
| --- | ---: | ---: |
| Baseline | 24 | 84 |
| Shared first-replacement prefixes | 72 | 72 |
| Isolation/renewal forks | 144 | 648 |
| Selected unconditional onward assays | 72 | 216 |
| Total | **312** | **1,020** |

There are **156 numerical pairs**. The first 240 cases are fixed immediately;
72 onward descriptors resolve from the registered selection algorithm. These
are forks of one source per origin plus a stock benchmark, not independently
sampled populations. Isolated retention, renewability, ancestry advantage and
autonomous reproduction remain distinct claims.

Preserve pinned BITSEY revision b2cb370aaecbc8299f259bc4251d5396c81f19a6 and
P16's bounded Euler clock: sample min(100,H/20), maximum step min(100,H/100),
half the maximum/base/adaptive limits for fine runs. Save actual integer steps,
proposals, sample ticks and live states. Use the unchanged P16 phase/clock
auditor, plus independent P17 source, fork, identity, schedule, selection,
replay and outcome reconstruction. Require endpoint/discrete fine agreement;
continuous differences are reported, not treated as a convergence proof.

Archive every auditable P16 input and freeze all execution files. Re-audit
original and archived P16 against its saved 70,715-check report before new
science and again in the final independent audit. Full software regression
must pass first. Preserve all executed predecessors and artifacts unchanged.

Two single-threaded workers; six-hour case cap; 24-hour scientific-run cap
including preflight; two-hour full-regression cap; six-hour final-audit cap;
34-hour overall supervisor cap; at least five GiB free disk. These are limits,
not an ETA. Launch detached, verify an advancing heartbeat and return for
polling. No retries, added intervals, extra seeds or automatic downstream launch.
