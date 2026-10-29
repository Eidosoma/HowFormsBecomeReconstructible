# E077 — fresh confirmation of the reconstruction tradeoff

**Complete: all four prospective directions confirmed on 32 fresh blocks.**
Finished **17 October 2026 at 13:01:42 UTC**, **2 h 0 min 47 s**, four workers.
Independent replay and artifact closeout passed; all **1,690 outputs, 50 frozen
inputs and 1,562 summaries** verified. Figure inspected.

Mixture success rises **55.76% → 63.18%** with immediate pruning. After one
rewrite, intact/pruned histories score **62.79% / 55.86%**. Substituting selected
magnitudes into the pruned output reduces success to **27.64%**; substituting
matching signs and magnitudes raises it to **63.77%**. All four adjusted 98.75%
intervals have the predicted directions. Joint substitution has **100 gains
and 19 losses**; pruning harms **117 distinct cases** at either endpoint.
[Interpretation, intervals and individual effects](INTERPRETATION.md),
[report](runs/confirmation_v1/REPORT.md), [figure](runs/confirmation_v1/tradeoff.png),
[independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json).

Test one prediction on 32 untouched source blocks: pruning helps immediately
but hurts after one ordinary rewrite; magnitude-only substitution in the
pruned output hurts, while joint sign/magnitude substitution helps. Four signed
primary contrasts use adjusted 98.75% whole-block intervals. All four directions
must hold; every individual gain and harm remains visible.

Regenerate the established source history with new block IDs 41000–41031.
Retain native/mixture, sham/pulse and erased comparisons, four founders and four
recipients. Evaluate 26 terminal slots across the two endpoints. Only one
additional ordinary rewrite and two component substitutions follow the source
boundary; no longer horizon or outcome-dependent extension.

[Protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md),
[decisions](DECISIONS.md), [source registry](SOURCE_DATA.json),
[reviewer motivation](../REVIEWER_2026-10-16_RECONSTRUCTION_TRADEOFF.md).

All nine development checks passed in **5.265 seconds** after correcting test
assertions; original failed logs and the abandoned development snapshot remain
in `analysis/`. The active snapshot is **[freeze_v2](analysis/freeze_v2/manifest.json)**,
with **50 inputs/dependencies** frozen before retained qualification. Fixture
and benchmark passed in **8.4849 / 32.7367 seconds**, each with **66 controls**
including the overall pass field, **109 outputs and 1,562 summaries** checked,
every source/writer/reader state replayed and individual tables verified. Both
technical figures inspected; scientific flags null.

The full source/writer/reader/audit benchmark initially suggested 40 minutes
with eight workers. Launch inventory found four other busy CPU slots and used
four workers on CPUs 0–3. Central forecast **78 min 37 s** (finish 12:19:32 UTC);
conservative allowance **3 h 51 min 52 s** (through 14:52:47 UTC). Actual runtime
was about 42 minutes above central and within the conservative allowance.
No scientific scope or criterion changed. Storage reserve was 2,878,799,872 bytes;
retained scientific outputs occupy 1,232,273,549 bytes.

[Development checks](analysis/development_tests_v3.log),
[qualification](analysis/technical_v1.json), [forecast](analysis/forecast_v1.json),
[launch](jobs/confirmation_v1/launch.json), [startup](jobs/confirmation_v1/startup.json).

Status checks occur on user request. No automatic scientific polling, restart,
extension or successor. Manuscript integration remains with the other agent.
