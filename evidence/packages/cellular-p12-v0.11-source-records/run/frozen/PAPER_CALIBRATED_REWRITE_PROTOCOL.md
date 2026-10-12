# P8: calibrated rewriting of established E carriers, then one onward transfer

Registered 2026-09-12 before new native integrations. Extension of the native
bitsey model, revision b2cb370aaecbc8299f259bc4251d5396c81f19a6, unmodified.
Config: configs/paper_calibrated_rewrite_v1.json.

## Question and choice of conditions

P7 found retained M acquisition in all tested 6-to-3 and 3-to-1 arrangements,
but none in 3-to-3. P6's three-cell M cue failed even against ordinary fresh
E targets, so it could not identify special resistance of established E
lineages. P8 uses six ordinary M cue cells against three targets, then tests
the actual targets against one fresh E recipient after every cue is removed.

Use native depol, power 60, Kd 1.25e-14, OiET .5, tness 1 for both contacts.
This setting succeeded in both necessary P7 arrangements and preserves P6's
depol/high-Kd setting. It is a fixed post-P7 selection, not a claim of optimality
or tuning on P8 results. Lower Kd and hypol are not retested here. Geometry
and donor count changed together relative to P6: no pure number-effect claim.

## Targets and controls

Four target backgrounds, always three cells:

1. fresh_E: ordinary E stocks from the archived native P3 preparation.
2. aged_E: the same stocks kept fully isolated for 40,000 additional native
   units (20,000 + 10,000 + 10,000), with coarse and finer preparation banks.
3. ordinary_E: actual round-6 carriers from P5's ordinary-E-founded lineage.
4. restored_E: actual round-6 carriers from P5's restored-E-founded lineage.

The round-6 cells are themselves only one 40,000-unit handover old: earlier
carriers were removed each generation. They are NOT 240,000-unit-old cells.
aged_E matches that elapsed age but not the lineage's exposure, original M
state, or contact environment. Any history association must be interpreted
with those differences in mind, not as a mysterious intrinsic memory effect.
All 17 live variables and recorded identities of archived carriers are used.

Seven conditions per background:

| Condition | Writing stage | Onward stage |
| --- | --- | --- |
| M_open | Six ordinary M cues, open | Open |
| E_sham | Six ordinary E cues, open | Open |
| M_write_rna | Six M cues, miRNA Kd zero | Open |
| M_write_cut | Six M cues, boundary junction flux cut | Open |
| no_cue | Targets alone, all junctions disabled | Open |
| M_probe_rna | Six M cues, open | miRNA Kd zero |
| M_probe_cut | Six M cues, open | Boundary junction flux cut |

RNA blocking retains small-ion junction transport. Boundary cuts use the
unchanged P4 regional wrapper and disable all junction flux across the
specified group boundary, preserving within-group routes. Native depol has
no separate neighbor-voltage-reading route. No pulse, clamp, survival filter,
new gene rule or outcome-dependent choice is introduced.

## Sequence

Writing: 3x3 orthogonal, nonperiodic sheet; six cues in the first two rows,
three actual target cells in the last row. Expose for 20,000 native units.
For no_cue use the three targets alone with complete isolation for the same
duration. Remove ALL six cues and preserve ALL three targets' live states.
Hold each target completely isolated for 10,000 units twice, under depol,
power 1, zero junction transport and no neighbor reading.

Onward: put the three actual held targets into the first three row-major
positions of a 2x2 sheet, with one fresh E cell in the fourth position.
Contact for 20,000 units using the registered route. Remove ALL three targets,
then hold the actual new recipient completely isolated for 10,000 units twice.
Continue this probe even after partial or failed rewriting. Do not substitute
ordinary M, reset variables, select the best carriers, or retain cue cells.

This is one onward transfer after rewriting. Three carriers produce one
recipient, so it is not renewable same-size inheritance, a six-round M relay,
cell reproduction, or autonomous scheduling.

## Gates, numerics and readouts

First re-audit the complete original P7 and P5 runs read-only, exactly matching
their saved reports (14,506 checks/295 integrations and 42,065/804).
Replay three coarse P7 cases with the unchanged P7 trajectory: depol/high-Kd
M_open at 6-to-3, 3-to-1 and 3-to-3. Every raw array must match; two known
positive transmissions and the known negative baseline are required gates.
Independently check the archived round-5 endpoint and round-6 acquisition,
removal and retention for both P5 lineages, against their frozen records and
saved six-round outcomes. Historical prefixes are reused, not new replicates.

Then generate both isolated aged-E banks. Verify the cells remain retained E
before allowing the rewriting panel. This is an explicit eligibility gate,
not an instruction to rerun or retune an unsuccessful aging preparation.
All three aging phases are refined in the fine bank. Finer aged_E branches
use that bank. Historical P5 and prepared P3 inputs remain fixed; their
ancestry is not rerun at finer resolution.

All 28 main conditions have finer counterparts, halving the timestep and
both adaptive increment limits in every new phase. Thus 29 finer comparisons
include the aging bank. Report continuous endpoint differences and label/
outcome agreement; disagreement blocks settled interpretation.

61 cases / 351 new native integrations: three replays (9), two age banks (6),
28 coarse rewriting-plus-probe branches and 28 refined (336). Frozen manifest:
62 local files plus 36 native Python files. Archive 50 exact historical files.
The fresh_E/M_open writing phase and holds also exactly repeat P7's 6-to-3
case, apart from metadata identifiers. That agreement is a baseline check,
not independent evidence of a new phenomenon.

Retained E/M requires its native two-unit classification at the live endpoint
and in at least 95% of late-quarter samples in BOTH isolated holds. Report
target and cue contact labels, every retained target, and the final recipient.
Complete rewriting requires all three originally E targets retained M.
Complete rewriting-plus-transfer additionally requires the initially E fresh
recipient retained M. Partial rewriting cannot be promoted to full success
just because its probe later becomes M. Report writing and onward failure
separately and compare sham, no-cue and stage-specific blocks.

A control-qualified chain requires M_open writing and onward acquisition,
negative E_sham/no_cue/writing-block controls, and retained-M targets but no
onward M acquisition in the probe-block controls, with finer agreement.
Report every background regardless of qualification. Positive new rewriting
or transfer is NOT required for an execution/audit pass.

## Bounds and claims

Two single-threaded workers; 7,200-second case cap and 28,800-second panel cap.
Supervisor runner/audit/overall caps: 29,100/1,800/31,500 seconds. Require
5 GiB free before workers and phases. Detached run; user polls.
No automatic retries, deletion, additional doses, onward generations, stress
panel, return-to-E intervention, fitness, division, migration or follow-on.
Software fixtures replace integration; their outcomes are not scientific data.
E/M are regulatory model states, not complete clinical diagnoses. Do not infer
unique PH, wet-lab validation, a new law of physics or therapy from this panel.
