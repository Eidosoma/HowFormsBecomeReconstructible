# State transmission survives complete cell replacement

Date: 2026-09-06. New BITSEY relay experiment; not a wet-lab finding or a claim
of autonomous reproduction.

Status: all eight three-round lineages completed validly; final array and
provenance checks passed, including both fine-setting lineages.

## Main result

Both learned-state lineages sustained **three successive complete donor-pair
replacements**. Each pair instructed two independently initialized fresh cells,
was removed, and was replaced only by those two newly instructed cells. Those
new cells could perform the next round of transmission. After the first round,
no founding donor remained in the continuing lineage.

In short: `founders → new pair 1 → new pair 2 → new pair 3`.
Each arrow replaces both cell carriers; it does not duplicate the old pair.
This is stronger than the previous one-contact result: the state can outlast
its original cell carriers under this externally scheduled protocol.

E and M are the model's regulatory-state labels, not complete healthy/cancer
diagnoses. Each table entry gives the two **new** cells' post-hold states.

| Founder condition | New pair after round 1 | After round 2 | After round 3 |
| --- | --- | --- | --- |
| Acquired E, active | EE | EE | EE |
| Acquired M, active | MM | MM | MM |
| Ordinary E, active | EE | EE | EE |
| Ordinary M, active | MM | MM | MM |
| Acquired E, blocked contact | MM | MM | MM |
| Acquired M, blocked contact | EE | EE | EE |
| Acquired E, finer settings | EE | EE | EE |
| Acquired M, finer settings | MM | MM | MM |

All active recipients, including the fine variants, acquired the desired state,
retained it without their old donors and passed the prescribed local recovery challenge. The
blocked recipients kept their independently initialized opposite state. The
blocked lineages continued from these actual outputs without rescue; the
founder state was absent from every replacement packet.

Ordinary same-state founders also sustained transmission. Thus learning can
place the system into a transmissible state, but this experiment does not show
an extra transmission advantage of having learned that state over already
being in it. Ordinary bistability and intercellular communication remain a
candidate explanation; a special new hereditary mechanism is not established.

## What makes this a replacement test

The [protocol](RENEWAL_PROTOCOL.md) and [configuration](configs/renewal_v1.json)
were fixed before execution. Each lineage starts with the first two qualified
donor histories of its relevant type from the prior group experiment. They
are unchallenged, donor-free checkpoints, not original writing cells.

Within a round, the current pair contacts fresh A for 1000 model time units,
then fresh B for another 1000, with per-edge miRNA Kd=2e-15. The two donors'
**post-A states**, not their saved pre-A states, enter the B contact. The first
fresh cell waits alone while B is written; its uncoupled 1000-unit wait is
integrated separately. All old donors are then excluded from the forward
lineage. A and B each undergo two isolated 10000-unit holds.

Only the two new, unchallenged post-hold states form the next packet. Both have
new IDs and actual fresh-target histories; neither is an old donor renamed as
a child. Numerical equality of some variables is not used as an identity test.
Saved state transitions supplement the ID bookkeeping. No failed round is
reseeded, repaired, or replaced with a successful branch.

Each new cell also receives a diagnostic 20%-toward-opposite regulatory impulse,
compared with an untouched 5000-unit shadow. **Neither diagnostic endpoint is
passed to the next round.** The continuing lineage uses its prechallenge packet,
so recovery testing cannot covertly restore the inherited state.

The source and parameters are unchanged: revision
`b2cb370aaecbc8299f259bc4251d5396c81f19a6`, Snail 72, medium-size cells,
native non-iterative binding approximation, no added voltage/connexin gates
or regulatory target clamping. Every active contact is a two-edge star; waits,
holds and diagnostic branches are isolated one-cell systems.

## Verification and numerical limits

- All eight lineage workers completed in **672.960 wall seconds** (~11.2 minutes),
  using at most two simulation processes. The 24 replacement rounds involved
  48 fresh recipients, 264 integration calls and 62,855 returned snapshots.
- All 1,168 saved-array/lineage checks passed. They include founder provenance,
  fresh target starts, post-A donor continuity into B, A's isolated wait,
  each hold and diagnostic fork, exact next-packet construction, old-ID
  exclusion, and previous-output to next-input state continuity. Input and
  frozen-file hashes also passed. These are audit checks, not statistical
  samples or confidence estimates.
- All saved concentration states/snapshots checked finite and nonnegative.
  This does not audit every internal solver step. Native sampled and live
  terminal states are both retained; their distinction is preserved.
- All returned late-quarter hold samples kept the appropriate post-hold label.
  Maximum normalized challenge/shadow regulatory distance was 1.54935e-11,
  below the fixed 0.02 bound. Recovery after a failed blocked transfer was
  recovery of the target's original state, not successful transmission.
- Both fine lineages agreed at every round. Maximum baseline/fine outgoing
  packet regulatory distance was 1.25435e-15, but full-vector differences
  reached 0.01955 scaled units. Two numerical settings do not prove solver
  convergence or full-state equality.
- Maximum learned/ordinary outgoing packet regulatory distance was 1.14032e-15;
  full-vector differences reached 0.01327. The tested transmission criterion
  shows no special advantage of acquisition history, not a proof that every
  aspect of those cell states is identical.
- Intracellular ion drift between the two holds reached 6.95424 scaled units.
  Stable regulatory memory is not complete physiological stationarity.
- All 29 unit tests passed, including five new relay/identity tests. Upstream,
  prior results, input artifacts and frozen execution files remained unchanged.
  No failure-dependent restoration, parameter retry or extra round was added.

The schedule advances the continuing lineage by 22000 nominal model time units
per round, or 66000 over three rounds; diagnostic forks are outside that forward
path. Cells differ slightly in age because A is introduced before B. As in
earlier runs, the native integrator can overshoot requested durations, so this
is a nominal timing ledger, not exact continuous-time synchronization.

## Interpretation for PH

This supports a **finite, cell-level carrier-replacement result**: an acquired
regulatory state can be installed in fresh cells, which in turn install it in
further fresh cells after every old donor has left the lineage. The tested
packet width stays at two cells, with three externally managed replacements.

It does not establish autonomous reproduction. We supply already existing fresh
cells, choose contact timing, isolate them and assemble the next pair. There
is no division, spontaneous creation of new cell bodies or endogenous control
of the transfer schedule. The model also does not tag individual molecules:
cell-carrier replacement is not proof of complete molecular-material turnover
or exclusion of every form of molecular cargo carryover.

Three rounds are a finite observation, not an indefinite-transmission law.
Identical deterministic target preparations do not establish robustness to
natural variation, noise, injury or different environments. No claim about
wet-lab heredity, therapeutic efficacy, a new law of physics or the broader PH
ontology follows from this relay alone. Nor should ordinary bistability be
treated as disqualifying the observed replacement result: it may be precisely
the mechanism supporting it.

A useful next causal test would perturb or erase the candidate carried
regulatory state mid-relay, and test a narrowly specified rescue, alongside
controls preserving other cellular variables. A separate tagged-cargo or
turnover analysis would address persistence of original molecules. Neither
extension was run here, and no longer lineage was started automatically.

## Artifacts and reproduction

Run: `runs/renewal-20260906T010102Z-v4d9ph19/`.
Founder bank: `runs/group-transfer-20260906T003546Z-pptx2s51/bank/`.

The run preserves input source paths/hashes, frozen pre-run scripts/protocol/
configuration, per-lineage identity ledgers, all incoming/outgoing packets,
both contact histories, each first-child wait and every hold/shadow/challenge
trajectory. Original group artifacts, source checkout and earlier probes are
not modified. Raw runs, upstream and the environment remain ignored by Git.

[RUNNING.md](RUNNING.md) gives commands and input-regeneration instructions.
The read-only [analyzer](scripts/analyze_renewal.py), added during execution,
checks saved-array continuity, fresh targets, complete old-ID exclusion,
unchallenged packet selection, and independently recomputed outcomes.
