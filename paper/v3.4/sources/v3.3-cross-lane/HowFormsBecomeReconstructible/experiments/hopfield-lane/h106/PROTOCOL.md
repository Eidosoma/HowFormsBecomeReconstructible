# H106 — cue-guided access with a matched update budget

2 November 2026. Authorized after H105's verified split result and saved-state
diagnosis: projection preserves distinct, stable patterns but fresh reads
often settle elsewhere. The aim is to test access from inherited records and
surviving cues, then its consequence for actual supplying-body transmission.
H104's first-handoff gain and H105's failed absolute task qualification remain
separate. This is not a pruning reversal, new writer search or learned-reader
extension. No H101/H103 reserved confirmation inputs are acquired.

## Fixed apparatus and three access policies

Use H105's 64-neuron apparatus, eight Walsh cues, two founders, two lineages,
two assessment draws, balanced acquired output columns and symmetric Gaussian
base of scale .12/sqrt(64). Acquisition stays teacher-clamped at cue gain four
for eight sweeps. All subsequent standard matrices W use gain two, an intact
base and 20% undirected record-edge deletion. Cues are clamped throughout;
outputs are never teacher-clamped after acquisition. The threshold remains
plus/minus 1e-12, with zero drive retaining the current bit.

Freeze three policies before any outcomes:

1. **standard**: one ordinary sweep, then seven ordinary sweeps, without a reset.
   This must reproduce the previous eight-sweep reader exactly.
2. **cue_prepare**: one sweep with W's free-to-free block set to zero, then seven
   ordinary sweeps under the original W. Cue-to-free and cue-to-cue entries are
   retained in preparation; the matrix stays symmetric. Each free neuron is
   therefore initially guided by surviving cue drive alone, with threshold
   ties retaining its random birth value. No source pattern, task label or
   previous body state is available. The matrix switch is explicit and its
   energy change is recorded; monotonic energy is required within each phase,
   not across the externally changed matrix.
3. **two_start**: four ordinary sweeps from the first fresh birth and four from
   an independent second birth. For each query select the lower-energy final
   state under W; select the second only when E2 < E1 - 1e-12. Otherwise retain
   the first. Selection uses no target, source pattern or task score.

Each policy performs exactly eight full sweeps of the free coordinates per
query. All use the same complete eight-sweep order tape (split 1+7 or 4+4),
same W, correct cues and first birth. Two fresh births are frozen for every
condition, although only two_start uses the second. Full-W energies at both
phase endpoints are evaluated for every policy; only two_start uses them for
selection. Including phase initial/sweep energies, every policy performs
twelve energy evaluations per query. Record energy and update counts explicitly,
and retain per-policy measured access time outside the deterministic audit data.
The two-start control has two attempts with shorter trajectories: this is a
fixed comparison at equal update budget, not a claim of equal convergence.
Acquisition and the projection writer are unchanged.

## Actual histories and matched assessment crossing

Start three actual supplying policies from the identical acquired record:
standard, cue_prepare and two_start. At each of four actual handoffs, each
policy receives its own preceding record, creates activity through its own
access policy and writes a complete projection record using H104's unchanged
activity-only writer. The writer receives neither incoming record, outputs
from other policies, teacher targets nor recipient results. Each boundary's
two births, injury and order tapes are shared across policies and independent
between generations. Their later patterns can differ because their histories
differ. Only the record passes to a fresh body.

Also retain the own initial record by protected copying, the other founder's
initial record, and an erased record. These three benchmarks stay unchanged.
The six record branches are ordered standard, cue_prepare, two_start, copy,
donor, erased. Assess every branch under every access policy at G0--G4, using
identical two-birth, injury and update-order tapes across all branches and
horizons. All protected-record assessments must therefore stay exactly
constant across generations, separately under each reader. Assessment reads
do not supply a next record; the actual supplying bodies have separate tapes.

This crossing separates access on an identical record from changes in what
actual suppliers transmit. It also reports the coupled supplier/reader policy,
but that coupled score cannot substitute for either primary comparison below.
There are no warm starts at captured activity, saved ancestral activity or
oracle choices of restarts.

## Frozen fresh-network decisions

Root seed **106106**. Use four excluded engineering networks and **32 fresh
main networks**, with all 36 tapes and all sources frozen before acquisition.
A separate fixture input is excluded. There is no candidate selection or
adaptive cohort expansion. Networks are independent units; founders, lineages,
assessment draws and cues remain nested. Original-task query success remains
at least fourteen of sixteen correct output bits.

**FIXED_RECORD_ACCESS_GAIN**: on each G1--G4 record from the *standard-supplier
history*, cue_prepare must recover the exact output of that record's actual
supplier on a mean >=80% of queries. Against both standard and two_start on
that identical record, each mean gain must be >=5 percentage points, its
adjusted lower interval bound >0 and differences positive on >=16/32 networks.
These are eight primary fidelity contrasts. This tests access to whatever the
supplier actually wrote, not restoration of task information already missing.
Failure of any requirement yields **NO_QUALIFIED_FIXED_RECORD_ACCESS_GAIN**.

**FOUR_HANDOFF_SUPPLY_POLICY_GAIN**: assess all histories with the common
*standard reader*. At every G1--G4, cue_prepare-supplied records must have
original-task query success >=50%, protected-copy success >=50%, and gaps
>=25 points from both source controls. Against standard-supplied and
two_start-supplied records, each mean task gain must be >=5 points, adjusted
lower bound >0 and differences positive on >=16/32 networks. These are eight
primary task contrasts. The common reader isolates the effect of supplying
policy on inherited records; improved terminal access alone cannot pass it.
Failure yields **NO_QUALIFIED_FOUR_HANDOFF_SUPPLY_POLICY_GAIN**.

Use 20,000 paired whole-network bootstrap resamples from
`106106/main/inference`. The sixteen primary contrast intervals have level
**1 - .05/16 = .996875**, a nominal 95% family target. Both verdicts and every
gate are retained. The joint verdict is **ACCESS_AND_SUPPLY_TRANSFER_QUALIFIED**
only when both pass; otherwise **NO_JOINT_ACCESS_AND_SUPPLY_QUALIFICATION**.
Copying retains information unavailable to activity-only writing and remains
a benchmark. No superiority to copying, endpoint reversal, persistent retention
beyond four boundaries or arbitrary reconstruction of erased semantics is
implied by these criteria.

## Scores, costs and diagnostics

Report the full reader-by-history G0--G4 task panel: query success, exact queries,
complete eight-query tasks and bit accuracy. For the three actual histories at
G1--G4, report exact captured outputs/free patterns and bit fidelity, relative
to the immediately preceding supplier of that history. Such capture metrics
are omitted for G0 and protected benchmarks. Report source task correctness,
hidden-pattern diversity/overlap, captured-pattern static stability under the
full recipient matrix, endpoint fixed-point rates and selection frequencies.
Also score the preparation endpoint externally, to distinguish available cue
drive from what subsequent ordinary dynamics retain. These diagnostic scores
are not fed into any policy or writer. Report phase energy, switch work,
matched update counts and measured runtime. All nonprimary intervals are
descriptive 95% intervals and cannot rescue a failed primary.

If access improves without improving common-reader transmission, diagnose
supplier errors and resulting records before another search. If preparation
fails, retain the two-start result and fixed-point diagnostics without selecting
a new rule on these main networks. No automatic successor campaign.

## Numerical qualification and execution

Generalize the existing reader only to phase lengths one, four, seven and eight;
unchanged eight-sweep/1+7 operation must reproduce H105 on identical tapes.
Replay every phase independently in long double, preserving exact coordinate
decisions and sweep states. Keep field/energy errors <=2e-11 and guarded neural
decision margins >=5e-14. Full-W endpoint energies and restart selections are
independently verified. Exact duplicate endpoints may tie; nonduplicate
selection decisions require >=5e-14 distance from the frozen -1e-12 boundary.
Never relax a gate or discard a numerical failure. Retain raw arrays first.

Every projection packet is independently checked using exact-rational/
long-double Gram inversion, with entry error <=4e-14, rank eight, symmetry and
zero diagonal. Orthogonal cue columns still give XX' >=8I; no rank cutoff,
iterative fit, extra plasticity or optimized writer is introduced. Verify all
actual packet chains, source/control construction, matched assessment tapes,
protected-copy invariance, exact update-budget equality, no forbidden inputs,
energy selection/ties, score recounts, verdict boundaries and serialization.

Benchmark the same four complete engineering inputs serially and with four
workers. Four-worker choice requires exact arrays/audits/tables and >=1.15
speedup. Each phase obtains shared twelve-CPU admission from two eligible
snapshots and uses one numerical thread per worker. Watch forecasts below ten
minutes; detach longer forecasts or prolonged capacity waits with unique log,
PID and durable status. All writes remain in this lane. Parent sealed sources,
earlier verdicts and unused confirmation outcomes are preserved. No public
manuscript edit or private-source quotation.
