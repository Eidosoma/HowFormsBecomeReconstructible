# P5 — Twelve-handover continuation of the 2D carrier-replacement assay

Registered 2026-09-11 before any native P5 integration. The user approved the
recommended repeated 2D relay. Midway rewriting, missing-carrier/timing stress
panels, broader geometry experiments and autonomous scheduling are NOT included.

## Question

P4 showed one three-to-three E-writing handover for restored E founders and
ordinary E founders. Do the actual new recipients keep this ability after
repeated complete replacement of their carrier group? This extends earlier
line-based relays to the paper-linked 2D assay; it is not the project's first
serial-memory test.

Use the actual three recipient states after P4's two isolated holds as the
starting carriers, not three freshly initialized E cells. Preserve all 17
native components and original recipient identities. P4 counts as historical
round 1; P5 simulates rounds 2 through 12, eleven new handovers. Historical
round 1 is not an independent P5 replicate.

Four fixed ancestries are capacity__ordinary_E, capacity__ordinary_M,
capacity__restored_E and capacity__failed_M from P4 run
paper-topology-20260910T135736Z-_g47fgl8. These names describe the P4 founder
history. In particular, the ordinary_E continuation starts from P4's ACTUAL
new E recipients, not ordinary E initializer clones. The restored_E ancestry
traces through actual P3 acquisition and restoration. All were chosen from
known results, not as random replicates or held-out histories.

M-founded controls start with new recipients that were already M before
contact and remained M. Their persistence is a negative control for E writing,
NOT evidence that those recipients acquired a novel M memory.

## Fixed repeated handover

At each new round:

1. Move all three current carriers, preserving order, to the top row of a
   2 x 3 orthogonal nonperiodic grid. Initialize exactly three fresh M recipients
   in the bottom row from the unchanged P3 2D reference preparation stock
   stored in P4 inputs (last returned snapshot, cell 1).
2. Contact for 20,000 native time units under hypol, power 1, tness 1, OiET 0.5
   and miRNA Kd 1.25e-14 in the open condition. The native voltage-dependent
   gap-junction gate remains active. hypol is the source's identifier for
   removing an extra potassium gate, NOT a calibrated voltage clamp.
3. Remove every incoming carrier. Move the actual three recipients into a
   1 x 3 array with ALL junction transport and neighbour-voltage reading off.
   Hold twice for 10,000 units under common depol/power 1/Kd 0.
4. Use ALL three actual live endpoints as the next carriers, including
   failures or mixed states. No resetting, averaging, winner selection,
   phenotype-based branching or return of earlier donors.

The original P4 recipients retain IDs new:00..02. Subsequent fresh groups have
IDs relay:02:00..02 through relay:12:00..02. All outgoing IDs disappear at
withdrawal; none return in later rounds. Relocation from the lower row to the
next upper row is an explicit externally scheduled rehoming step, not growth
or spontaneous movement. Baths and fresh cells are externally supplied.
The contact/hold voltage schedule is reapplied each round; there is no claim
of intervention-free or autonomous renewal.

## Cases and controls

28 fixed cases, 804 native integrations:

- Four exact P4 capacity replays, including all raw arrays and all three phases,
  must pass before continuations begin. Replays do not replace the archived
  P4 input states used to start the lineages.
- Twelve coarse continuations: four ancestries x three communication routes.
  Each has eleven rounds x three native integrations.
- Twelve finer continuations: the entire coarse factorial repeated with half
  the starting time step and both adaptive delta limits in EVERY new phase.
  P4's historical input remains identical and coarse; these checks do not
  refine the historical acquisition/restoration/first-handover prefix.

The three routes, fixed for every new handover within a case:

- open: native small-ion and miRNA communication.
- rna_blocked: miRNA Kd 0, with small-ion communication retained everywhere.
- border_cut: native Kd, but expression-gate multipliers are zero on ALL
  donor-recipient edges. Both added miRNA flux and small-ion flux are cut;
  donor-donor and recipient-recipient edges remain intact.

All powers are 1, so there is no state-dependent overexpression intervention.
The fixed-role per-edge wrapper is unchanged from P4. Roles do not change
with E/M labels. The border cut is an experimental extension, not a literal
native paper parameter. No E helper cell is supplied after the P4 prefix.

Every case runs all eleven new rounds unless a technical/runtime failure
prevents execution. Scientific loss of the state is an outcome, not a reason
to stop early or change the protocol. No stress or rewriting follow-on starts.

## Readouts and interpretation

For every round, record carrier-start, post-contact and recipient-final E/M/X
labels; full arrays; cell identities; native topology, voltage and gate
diagnostics; and stable E/M counts. Stable means the final label plus >=95%
late-quarter samples in BOTH isolated holds. A single favorable final frame
does not establish persistence.

Primary: all three new recipients acquire and retain E in every round through
12, including the archived prefix. Report the first failed E round, the longest
unbroken E prefix, subsequent recovery if any, final counts, and all failed or
mixed rounds. Report the eleven newly simulated rounds separately from the
one historical round. Four open coarse cases are the main lineages; eight
coarse blocked/cut cases are controls; finer copies are numerical checks, not
additional biological replicates.

The E lineage's state should disappear from fresh M recipients when its
communication route cannot convey it; all controls are reported, including
unexpected positive controls. Technical quality does not require a favorable
new scientific outcome. Ordinary-founder success is equally important: if it
matches restored-founder success, there is no demonstrated special advantage
of the acquired-and-restored history. Simple state-copying dynamics remain an
alternative explanation, not a mechanism excluded by repeated turnover.

This tests finite E-state renewal with complete externally supplied carrier
replacement. It does not demonstrate new attractors, learning-rule inheritance,
cell division, biological fitness, open-ended evolution, autonomous heredity,
clinical treatment, wet-lab validation, or full original-paper replication.

## Provenance and bounds

Before native integration, perform a read-only P4 audit that must exactly
match its saved 42,565-check/858-integration report. Freeze all execution files,
the protocol, config, exact case list and required P4/P3 inputs. Native revision
b2cb370aaecbc8299f259bc4251d5396c81f19a6 and all executed predecessors remain
unchanged. Four raw-array replays gate the new relay panel.

Two fresh single-threaded worker processes concurrently. Per-case cap 7,200 s;
panel cap 28,800 s (8 hours). Supervisor runner/audit/overall caps:
29,100/1,800/31,500 s. Require 5 GiB free before workers and phases. No data
deletion, retry, parameter retuning or downstream experiment. Long runs are
detached and confirmed by a later advancing heartbeat; the user polls.

