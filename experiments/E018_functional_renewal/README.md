# E018 — functional renewal

Status: **complete; independent audit and closeout passed. Functional renewal
did not qualify.** All 32 fresh blocks (16000–16031), 128 founders, 512 lineages
and 193536 individual condition/cue scores were retained. No job remains running.

The reader and learned acquisition are unchanged from E017's successful setup.
At replacement, incoming weights are erased after reading; current body activity
writes a new record during 128 updates on a unit-positive scaffold. Only inputs
remain clamped. Each boundary transmits 4096 bytes. Protected copying preserves
the original bytes; separate conditions disable incoming reading or outgoing
writing. Fresh assays never train or select the next generation.

Success under **both opposing inputs**, % [95% whole-block bootstrap]:

| Replacements | Record | Intact | Scattered loss | Square lesion | Original gates |
| --- | --- | --- | --- | --- | --- |
| 0 | Original | 99.8 [99.4, 100] | 80.1 [74.4, 85.2] | 99.8 [99.4, 100] | 24/24 |
| 1 | Body-written | 27.1 [17.2, 37.3] | 19.1 [12.1, 26.8] | 27.1 [17.2, 37.3] | 15/24 |
| 1 | Protected copy | 100 observed | 85.5 [81.1, 89.8] | 100 observed | 24/24 |
| 3 | Body-written | 27.1 [17.2, 37.3] | 19.7 [12.7, 27.0] | 26.8 [17.0, 36.9] | 15/24 |
| 3 | Protected copy | 99.8 [99.4, 100] | 81.6 [77.5, 85.4] | 99.4 [98.6, 100] | 24/24 |

The single primary endpoint, intact both-cue success after three rewrites, was
**27.15% [17.19, 37.31]**. Its lower bound failed the required >75% threshold.
The paired deficit against protected copying was **72.66 percentage points
[62.11, 82.81]** at that horizon, a secondary comparison.

Full qualification also failed. At each renewal horizon, all six original
rule-by-damage absolute reliability gates and all three input-isolation
advantage gates failed; 15/24 original gates passed. Ten of twelve additional
reading/writing-dependence gates passed, with the scattered-loss contrasts
against read-blocked renewal failing the required >10-point lower bound.
These gates concern individual-cue accuracy, distinct from the primary paired-
input endpoint. Initial and copied records passed all 24 original gates.

Disabling reading or writing gave zero both-cue successes at both horizons
under all three damage conditions. Partial function therefore survives this
activity-mediated route, but reliable inheritance remains unestablished.
Input-isolated and communication-off assay controls likewise had zero both-cue
successes; input isolation was exact at every update.

The major cohort-level loss is already present after the first replacement.
A subsequent [saved-data review](../REVIEW_2026-09-19.md) inspected all first-
boundary trajectories: correct both-cue outputs fell from 511/512 lineages before
writing to 143/512 by update four and 139/512 by update eight. The final writing
window and fresh-body first-renewal assay identify the same 139 successes.
The one- and three-replacement intact assays also identify those same lineages.
Writing-step scores are descriptive state measurements, not new functional
assays; they localize observed deterioration without isolating its cause or
establishing long-term stability. Immediate versus delayed body-derived capture
is the next test; the subsequently authorized
[E019](../E019_capture_timing/README.md) has qualified immediate capture on a
fresh cohort, establishing reliable transmission across one replacement.

Only the single primary endpoint was prespecified as primary; other intervals
and gates are pointwise. Renewal bodies were intact, with damage applied only
to independent final assays. The writer boundary, scaffold, cues and clock are
supplied machinery for elementary instructed routing. These results do not
establish active repair, autonomous goals or independently active patterns.

The workflow finished on 2026-09-19 at 11:38:59 UTC: simulation/reporting
1247.16 seconds, independent audit 1288.69 seconds, total **42.29 minutes**,
within the 74.51-minute conservative forecast. It used at most 12 CPUs, one
numerical thread per worker. Exact independent replay verified every teaching,
renewal and assay update, record boundary, score, interval and gate. Closeout
verified frozen inputs and original outputs for both runs, fixture evidence,
workflow references, figure provenance and unchanged E014–E017 frozen inputs.
The scientific figure was visually inspected. No retuning or exclusions occurred;
all writes remained in experiments.

[Scientific report](runs/renewal_v1/REPORT.md),
[figure](figures/renewal_v1/functional_renewal.png),
[independent audit](runs/renewal_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json), [frozen protocol](PROTOCOL.md),
[final status](jobs/renewal_v1/status.json), [workflow log](jobs/renewal_v1/workflow.log).
