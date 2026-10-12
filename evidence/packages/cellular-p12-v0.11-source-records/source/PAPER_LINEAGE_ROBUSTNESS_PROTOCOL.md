# P12: robustness of editable state inheritance

Registered 2026-09-16 before any P12 biological integration. Prior P1-P11
executed code, configurations, protocols and artifacts remain immutable.

## Question and controlled perturbations

Does the P11 editable lineage survive irregular contact spacing and modest
variation in incoming cells? This is an exploratory simulation stress test,
not autonomous reproduction, a wet-lab result or a unique-PH mechanism test.
Repeated M-E-M switching and state-triggered scheduling are NOT part of P12.

Keep the pinned native biological equations, six-cell/eight-edge relay graph,
six-cue/three-target writer, power 60, Kd 1.25e-14, and P10R bounded explicit
Euler method. Coarse/fine max steps 100/50; every 100-unit sample and exact
endpoint are retained. Fine also halves base step and adaptive increments.
Every cell evolves while waiting; never reset or replace a waiting pupil.

Timing stress changes SPACING, not contact dose or contact order. Each pupil
still receives exactly 20k open contact, in order 0,1,2, inside an 80k window.
Insert three independently drawn nonnegative gaps: before pupil 0 and between
the three contacts. Mild gaps are 0..2k, strong 0..5k, on a 100-unit grid.
The final idle period is 20k minus the three gaps, always nonnegative. Every
round still takes 80k contact-window time plus two isolated 10k holds. This
does not test random overlap, order reversal or all timing distributions.

Cell stress multiplies ONLY incoming ZEB protein by a cell-specific factor.
Mild integer-percent changes are -10..+10%; strong -25..+25%. Other 16 state
components, native equations, bath, ions, snail, cue cells and existing carriers
are unchanged. ZEB protein is not one of the two RNA totals used by the native
E/M/X classifier; starting labels are checked, never selected or redrawn.
This tests one narrow kind of within-state heterogeneity, not genetic variation
or a stochastic biochemical noise model. Initial fresh founder targets and each
fresh recipient trio are varied in combined trials; the current live carriers
are NEVER re-randomized. The six writing cues remain standardized.

All random words are fixed in configs/paper_lineage_robustness_draws_v1.json.
For each seed, role and cell, take the first 16 hexadecimal digits of SHA256 of
"P12_lineage_robustness_v1|SEED|DOMAIN|INDEX". Domains are timing:r01..r06 and
protein:founder,r01..r06. Map words by integer multiplication/division onto the
registered uniform grids. Common words pair strengths, labels, routes, histories
and numerical resolutions; these paired comparisons are not independent trials.
Seeds 101,102 are screening draws; 201,202,203 are untouched combined-test draws.

## Fixed stages and case ceiling

1. Baseline: four zero-stress single-handover replays, ordinary M and rewritten
   ordinary E, coarse/fine. Rehome P11's actual held ordinary M founders or actual
   E-rewritten round-3 carriers, and reproduce respectively P11 before/r01 and
   after/r04. Require exact live-state agreement with all six archived phases.
   Full P11 provenance and its completed editable lineages are separately audited.
2. Timing screen: 32 cases. Two levels x two labels x two screening seeds x
   two resolutions for open contact (16); matched RNA and boundary-cut controls
   for seed 101 at each level/label/resolution (16).
3. Cell screen: the same 32-case layout, now changing ZEB protein only.
   Complete this independent factor screen even if no timing level qualified.
   A level qualifies only if both open seeds, BOTH directions and BOTH numerical
   resolutions succeed, and all registered controls at that level remain opposite.
   Select strong if it qualifies, otherwise mild, otherwise none. No new levels,
   retuning or post-result seed replacement. If either factor has no qualifying
   level, stop with a valid negative screen report and no combined tests.
4. Combined tests: 12 cases = three HELD-OUT seeds x written/ordinary histories
   x two resolutions, at the independently selected timing and cell levels.
   Start from the corresponding P11 bounded-clock stock (a shared audited stock,
   not independent biological founders). Newly simulate the initial M writing
   or time-matched ordinary-M aging, all three M handovers, temporary E writing
   of the actual current carriers, then all three E handovers into fresh M cells.
   This is 680k new logical time per complete trial. Never seed from a historical
   dynamic lineage endpoint. Stop a trial after its first incomplete block;
   all failed trials stay in the denominator. Fine has its own fine stock/state.
5. Matched controls: 78 cases, six for EACH combined seed/history/resolution,
   plus a no-cue initial-founder control for each written trial (six more).
   From that trial's actual available prefixes, separately assay before-RNA,
   before-cut, after-RNA, after-cut, rewrite-M-sham and rewrite-no-cue.
   Before controls rehome its actual held founder and repeat its first M handover.
   After controls rehome its actual held E-rewritten carriers and repeat its first
   E handover. Rewriting controls use its actual M round-3 carriers and reproduce
   the writing/withdrawal/hold procedure, with M cues or no cues. Thus controls
   share exact challenge draws and live prefixes, not separately tuned donors.
   Founder-no-cue controls retain the identical varied initial E targets without
   M cues for 40k; they must remain E and run even if the main trial fails early.
   If an upstream prefix never qualified, record an explicit structural skip:
   no manufactured substitute prefix, no phases and null ion-index metadata
   because no cell system was configured. A skipped control cannot qualify a trial.
   These are counterfactual forks, not extra independent lineage replicates.

Maximum 158 registered cases / 1,746 integrations; baseline failure can stop at
4, absent screening levels stops at 68, and controls can have zero integrations
when their registered source prefix is unavailable. Baseline technical/biological
failure stops before screens. Any technical or coarse/fine disagreement stops
progress and is not relabelled as a clean scientific negative.

## Success, identity and reporting

Every handover removes ALL three teachers. Retain all three pupils, never a
successful subset. Both 10k holds need the desired endpoint and >=95% of the
26 samples at or after 7.5k. Each pupil must still have the opposite label
immediately before its first scheduled contact; spontaneous pre-contact changes
do not qualify as teaching. A writer removes every cue before both holds.

A full trial requires M writing/aging, three M handovers, E rewriting and three
E handovers. Control-qualified success further needs all its matched controls
to be available and negative at both numerical resolutions. Report exact counts
out of THREE challenge seeds for each history, per-seed outcomes, failure stages,
and raw versus control-qualified success separately. Do not call 3/3 a precise
population success probability. Report the paired history differences without
assuming or claiming an acquired-history advantage.

The input archive contains the complete auditable P11 run and its history.
Freshly re-audit original and archived P11 before new integrations, and again
in the independent final audit. Hash all inputs, execution files and native source.
Auditor independently reconstructs case registration, random draws, schedules,
initial-state changes, geometry, gate physics, exact clock traces, source bindings,
whole-cell continuity, stopping decisions, selection and success denominators.

## Runtime and execution

Use two single-thread workers, four-hour per-case and 24-hour scientific-panel
caps. The larger cap accommodates paired randomized trials and matched controls;
it is not an ETA. Require 5 GiB free; no automatic retry or downstream launch.
Run the full regression FIRST in the detached supervisor (45-minute limit),
then science only on a pass, then a final independent audit (30-minute limit).
Runner/total watchdogs: 86,700 / 92,100 seconds. Freeze all new execution and
protocol files on launch. The user polls. Synthetic software fixtures are not
biological pilots and cannot supply evidence for the hypothesis.
