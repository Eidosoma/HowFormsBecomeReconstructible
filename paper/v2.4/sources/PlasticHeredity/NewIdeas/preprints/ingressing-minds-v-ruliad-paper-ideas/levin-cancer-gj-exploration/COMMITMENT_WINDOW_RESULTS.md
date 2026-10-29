# Commitment window: delayed commitment versus transient switching

Status: **complete**, 2026-09-06. All 30 branches executed validly; all
5,949 independent saved-array checks and 182 software tests pass. All ten
new fine variants agree on all six outcomes and every compared endpoint
label. No retries, retuning or additional stopping points were used.

Run: `runs/commitment-window-20260906T154216Z-6k4vdcff`.
Started 15:42:16 UTC; completed approximately 16:16:45 UTC.
Protocol: [COMMITMENT_WINDOW_PROTOCOL.md](COMMITMENT_WINDOW_PROTOCOL.md).
Config: [configs/commitment_window_v1.json](configs/commitment_window_v1.json).
Full audit: `runs/commitment-window-20260906T154216Z-6k4vdcff/independent_audit.json`.

## Main result in simple terms

A cell's current label does not tell us whether a change will stick.

For E-return, three short contacts are enough at the tested setting: the
receivers still look M-like when the cues stop, but finish changing to E
on their own and pass E through two fresh-cell replacements. Four contacts
give the same delayed inheritance, starting from an intermediate label.

For M-return, five contacts (historical) and six contacts (new) produce
M-labelled receivers that revert to E once the cues are gone. Eight contacts
produce retained M that passes through both fresh replacements. Ten contacts
were already known to succeed.

Thus visible switching can occur **after commitment** in one direction and
**before commitment** in the other. Commitment here means success under this
specified cue-removal, retention and renewal assay—not irreversibility under
every possible future intervention.

## Fixed stopping-point map

Each arrow sequence is: **label at cue removal → label at both isolated hold
endpoints → outgoing round-four pair → outgoing round-five pair**. A single
letter means both cells have that label; the two cells are not independent
biological replicates. E-return is E→M→E; M-return is M→E→M.

| Contacts before removal | E-return labels | Durable E update? | M-return labels | Durable M update? |
| --- | --- | --- | --- | --- |
| 2, new | M → M → M → M | No | E → E → E → E | No |
| 3, new | M → E → E → E | Yes, delayed | E → E → E → E | No |
| 4, new | X → E → E → E | Yes, delayed | E → E → E → E | No |
| 5, historical | E → E → E → E | Yes, prompt | M → E → E → E | No: transient switch |
| 6, new | E → E → E → E | Yes, prompt | M → E → E → E | No: transient switch |
| 8, new | E → E → E → E | Yes, prompt | M → M → M → M | Yes, prompt |
| 10, historical | E → E → E → E | Yes, prompt | M → M → M → M | Yes, prompt |

All ten **new** age-matched blocked-history controls are negative for target
writing/renewal. Every new active case has a finer repeat; all ten agree.
Five-contact outcomes are reused baseline R1C1 active crossover branches,
not fully fine acquisition repeats. Ten-contact baseline/fine active and
baseline blocked branches are also reused, not rerun.

The earliest successful **sampled** stops are three for E and eight for M,
with preceding sampled failures at two and six respectively. There is no
success-to-failure reversal among the sampled points. This is not proof of
global monotonicity or an exact minimum: counts 1, 7 and 9 were not included
in this panel, and states between contact endpoints were not mapped. These
are conditional distinctions for one cue strength, spacing, model and
source bank, not universal pulse requirements.

## Why a label can miss commitment

The unchanged [classifier](scripts/memory_metrics.py) uses
`delta = miR200_total - Zeb_mRNA_total`: E for delta > 2, M for delta < -2,
and X otherwise. X is an intermediate classification interval, not evidence
of a third stable attractor.

This label summarizes two variables; the full 17-variable cell state also
contains protein, ionic and derived variables. The label is not a direct
test of where the isolated dynamics will settle. Different complete states
can share the same M label but have different futures.

In particular, E-return at stop three and M-return at stop six both have
a current M label, yet neither label by itself specifies the retained
outcome. Within M-return, the stop-six and stop-eight receivers are both
M-labelled but differ in whether M survives and is inherited. No particular
variable has yet been shown to cause that commitment difference.

The four-contact removal is before gap four: its X label is consistent with
the preceding crossover finding E at the later gap-four checkpoint. The new
three-contact result moves the earliest demonstrated sampled E commitment
earlier; it does not contradict the old pulse-END observation that both E
labels first appeared at pulse five while the ten-contact train continued.

## What was run and what was reused

Exactly 30 new branches: five stops (2, 3, 4, 6, 8), two directions, and
baseline active, baseline blocked and fine active histories at each stop.

Full canonical `final` 17×6 groups were selected from the completed spacing
run `runs/pulse-spacing-20260906T130210Z-8pyjjxct`. Each group contains one
receiver and the same five evolving cue cells used throughout that history.
Each prefix has N contacts of 10 nominal units and N−1 gaps of 10 units.
Blocked histories have all GJ transport off, while intracellular dynamics
continue. They are age-matched histories, not newborn controls.

At removal, only the complete receiver columns continue. All ten cue
placements are discarded. Each receiver is isolated for 10000 + 10000
units with no added contact, gap, reference edit or reset. The actual held
pair seeds the unchanged fresh-pair relay, even for negative outcomes.
All onward contacts are active. Challenge/shadow forks never continue.

The older 18-instance lineage ledger plus two qualified receiver IDs and ten
cue IDs give 30 exclusions per branch. Four fresh recipient IDs per branch
are disjoint. Reused checkpoint placements are deterministic counterfactual
forks, not independent replicates or evidence for molecular turnover.

Fine cases use the spacing run's **fine prefixes**, then fine new holds and
relays: half the numerical step and adaptive increment limits. The older
incoming lineage/reference bank is not refined. This differs from the
preceding crossover, whose fine variants all began from baseline histories.
Blocked histories are baseline only.

Nominal removal age is 20N−10. Starting from nominal source time 89000,
round four spans [109000 + age, 131000 + age] and round five spans
[131000 + age, 153000 + age]. Native integration can overshoot a requested
horizon; continuation uses the live canonical endpoint, not the last saved
sample or an invented exact timestamp.

## Outcomes, verification and numerical agreement

The six predeclared outcomes remain separate. Among the 30 new branches:

| Outcome | Positive branches |
| --- | ---: |
| Target label at removal (`contact_acquired`) | 8 |
| Target retained after cue removal (`postcue_state_written`) | 10 |
| Target transmitted through both replacements | 10 |
| Durable rewrite: postcue retention plus both replacements | 10 |
| Prompt durable rewrite | 6 |
| Delayed durable rewrite | 4 |

The four delayed cases are E-return stops three and four, baseline and fine.
Twenty branches are negative for durable rewriting. The two new transient
M cases are stop six, baseline and fine. A legacy `retained_switch` false
value does not override a separately valid delayed-writing outcome.

Independent checks total 2,700 source/exposure, 2,820 relay, 420 branch and
nine historical-consistency checks. Both preceding panels were independently
re-audited before launch (16,296 + 6,269 checks, counted separately), and the
historical baseline fifth-contact continuation was checked as bitwise exact.

Eighty input files were copied and hashed: twelve lineage/reference files,
two summaries, six history metadata files and sixty group checkpoints.
Original/copy hashes, all frozen/executing files, the combined predecessor
audit and native source remain intact. Native revision is unchanged:
`b2cb370aaecbc8299f259bc4251d5396c81f19a6`.

All ten fine variants agree on all six outcomes and compared endpoint labels.
Maximum normalized regulator differences are approximately:

- checkpoint receivers/groups: 0.00167898;
- receivers after both holds: 4.74896e-8;
- outgoing round four: 1.25434e-15;
- outgoing round five: 1.14031e-15.

These are comparisons, not statistical confidence intervals or a general
solver-convergence proof. The maximum full-vector checkpoint difference is
0.109823; after holds it is 0.0256540, and over the two relay endpoints it is
0.0381057.

All 120 fresh recipients pass their local recovery tests, including recovery
of the old state in negative branches. Worst final normalized recovery
distance is 2.96039e-7, ratio 1.48019e-6 from an initial distance of 0.2
(E-return stop two baseline, round five, child one, recovering M).
Endpoint-label occupancy in the last quarter of every new receiver/child
hold is 1.0. Maximum ionic hold drift is 6.91667: label persistence is not
whole-state equilibrium.

## Execution cost and reproduction

New work: **780 integrations**, 185,141 returned snapshots, 120 fresh
recipients, 60 complete pair replacements and 60 historical receiver
placements. Three hundred historical cue placements were removed at
selection; no new cue cells or priming integrations were added. Eight
historical benchmark branches are reported separately.

Wall time was 2069.224 seconds (~34.5 minutes), new integration CPU time
4054.973 seconds. Branches took 110.8–185.0 seconds. Two single-threaded
workers, a 900-second branch cap and a 3600-second suite cap were retained.
The run exited zero, without retries, rescue, retuning or additional stops.

All 182 software tests passed before launch and after completion. Two
existing upstream invalid-escape SyntaxWarnings remain; no upstream code
was changed.

See [RUNNING.md](RUNNING.md), section 22. To audit the retained run:

```bash
.venv/bin/python -B scripts/analyze_commitment_window.py runs/commitment-window-20260906T154216Z-6k4vdcff --compact
```

Omit `--compact` for every check. Raw runs remain ignored by Git; reproducible
code/config/protocol and this report are trackable. A fresh checkout needs
the documented predecessor regeneration and protocol/path adaptation.

During this run, the user requested that **future runs expected to exceed
10 minutes be launched detached**, with logs and a status command for them
to poll. This preference is recorded in RUNNING.md. The user explicitly
asked to let this already-running panel continue as launched.

## What this adds to PH, and the next question

The new result is delayed writing of finite renewable regulatory content:
experience can change what the receivers will retain and teach fresh cells
before the coarse E/M label reflects that change. Conversely, a visible
switch can precede durable writing and fail to be inherited.

This strengthens the distinction between current appearance, retained
state and inherited content. It does not establish an extra PH force,
changed learning rules, autonomous reproduction, adaptive benefit, a new
attractor, a new law of physics or wet-lab efficacy. The native E/M dynamics
are unchanged, and cues, fresh cells and the renewal schedule remain external.
Unchanged old-state recipients in negative branches do not independently
demonstrate old-state transmission.

A useful next experiment would test which carried state components separate
the same-labelled, noncommitted M checkpoint at six contacts from the
committed M checkpoint at eight. That would require predeclared causal
interventions and controls, not just correlations between the two snapshots.
Alternatively, seven contacts could refine the sampled window, but is not
needed to establish the visible-versus-committed distinction already observed.

No follow-up experiment has been implemented or launched.
