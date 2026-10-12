# P7: ordinary-M transmission calibration

Registered 2026-09-12, before new native integrations. This is an extension,
not a new paper replication or a test of clinical intervention.

## Question and motivation

P6's ordinary M donors failed to change fresh E recipients, and themselves
became E. Its negative rewriting result therefore does not isolate resistance
of established lineages. P1/P3 acquisition used miRNA transport coefficient
8.801117367933935e-16, whereas P6 used 1.25e-14 (about 14.2 times higher).
Transport strength need not monotonically favor M. Test these two prior
settings, two native voltage modes, and three fixed group arrangements.
No outcome-dependent retuning, stronger signals, longer holds, or new donor
histories will be introduced within this panel.

## Frozen design

Native bitsey revision: b2cb370aaecbc8299f259bc4251d5396c81f19a6, unmodified.
Config: configs/paper_m_calibration_v1.json. Two historical replay gates:

1. P3 bank__depol__edge, from paper-sheet-20260909T210234Z-6u875ntn:
   original 13x13 preparation, acquisition and two isolated holds; four calls.
   All raw arrays must match, including nine originally E cells acquiring M.
2. P6 assay__M, from paper-rewrite-20260912T121215Z-971x3guc:
   ordinary three-to-three contact and two isolated holds; three calls.
   All raw arrays must match its negative outcome, including donors becoming E.

Both full original reports must first pass a read-only re-audit exactly
matching the saved reports (P3: 18,941 checks/465 calls; P6: 56,484/1,194).
The historical positive and negative gates validate reproducibility, not
success of any new condition. Preserve each replay's original factory,
trajectory, identifiers and diagnostic array schema.
The common P3/P6 reference stocks and bath must be exactly equal. The new
coarse 3-to-3/depol/high-Kd/M_open case also repeats P6's negative assay;
its raw arrays must agree, despite different human-readable cell identifiers.
It is a matched historical baseline, not independent new evidence.

New factorial, in fixed priority order:

| Factor | Values |
| --- | --- |
| Layout | 3 donors to 3 recipients, 2x3; 3 to 1, 2x2; 6 to 3, 3x3 |
| Native mode | depol; hypol |
| miRNA Kd anchor | low 8.801117367933935e-16; high 1.25e-14 |
| Condition | M_open; E_sham; M_rna; M_cut |
| Numerics | original; all phases refined |

Donors occupy the first contiguous row-major indices, recipients the rest.
In 3-to-1 this makes an L-shaped donor group. Layout comparisons change
topology as well as numbers; do not infer a pure donor-number effect.
All stocks come from the existing P3 reference's last preparation snapshot,
E column 168 and M column 1. These are ordinary prepared stocks, not acquired
M, restored E, or advanced lineage histories. Every new recipient starts E.

Contact lasts 20,000 native time units, power 60, OiET .5 and tness 1.
M_open uses ordinary M donors. E_sham substitutes ordinary E donors.
M_rna sets miRNA Kd to zero but retains small-ion transport. Its low/high
anchor copies are physically duplicate controls, not independent evidence
for an effect of Kd. M_cut uses the unchanged P4 regional gate to remove
all gap-junction flux across the donor/recipient boundary, preserving
within-group routes. Membership is fixed by donor identity, not E/M label.
Both modes exclude neighbor-voltage reading. nbrDepol is deliberately
absent because a junction cut alone would leave its separate neighbor-reading
route active. hypol denotes absence of the added state-dependent potassium
gate; it is not a calibrated voltage clamp.

After contact remove EVERY donor. Retain EVERY actual recipient's full 17
live state variables, with no resetting or selection. Isolate each recipient
completely (all junction flux zero, no neighbor reading) for two 10,000-unit
holds under depol/power 1. Hold shape is 1 x recipient count; no exchange is
possible even where nominal edges exist. The second hold starts from the
first hold's live state, not its last returned snapshot.

There are 48 coarse new cases and all 48 are repeated with half timestep
and half both adaptive increment limits in all three phases. Total:
98 cases, 295 newly executed native integrations, 96 new one-handover cases.
Historical stocks and reused datasets are not independent random replicates.

## Readouts and decision rule

Report initial and contact-end donor/recipient labels, both retained E and M
counts, final recipient labels, partial acquisition and transient switching.
Retained state requires the native two-unit E/M classification at the live
endpoint AND at least 95% of late-quarter recorded samples, in BOTH holds.
Count acquisition only in recipients verified initially E. Disclose donor
conversion, not just recipient outcomes.

A qualified condition requires all recipients retained M in M_open, all
retained E in E_sham, M_rna and M_cut, and matching outcome/endpoint labels
in all four finer counterparts. Report all candidates in prespecified layout,
mode and Kd order. Continuous numerical differences remain visible even if
labels agree. No positive new result is required for a valid experiment.
Numerical disagreement prevents interpreting that comparison as settled.

Three-to-three candidates are especially relevant to a future same-size
relay. A 3-to-1 or 6-to-3 success does not supply enough next-generation
donors to repeat itself without an additional operation. Even a 3-to-3
success is one handover, not demonstrated serial renewal or rewriting.

## Audit, bounds and exclusions

Independent audit reconstructs case inventory, geometry, native voltage and
expression gates, diffusion controls, numerics, common bath, identity and
full-state transfer. Check raw replay equality, all 48 finer pairs, both
holds, and complete execution/input manifests. Freeze 55 local files;
execution manifest includes 36 pinned native Python files. Copy 21 exact
historical inputs, sufficient to independently audit both source branches.
Software fixtures replace integration only; their outcomes are not evidence.

Two single-threaded workers; 7,200-second case cap and 28,800-second panel
cap. Supervisor runner/audit/overall caps 29,100/1,800/31,500 seconds.
Require 5 GiB free before workers and phases. Run detached; user polls.
No automatic retry, deletion, onward relay, halfway rewrite, stress panel,
cell division, migration, fitness, self-scheduling or downstream launch.
No claim of unique PH, new physical law, wet-lab validation or therapy.
