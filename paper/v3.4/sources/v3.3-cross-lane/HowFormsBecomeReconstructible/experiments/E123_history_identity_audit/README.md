# E123 — external recovery of historical identity

**Amended retained-data audit launched 2 November 2026 at 18:40:10 UTC.**
`retained_v2`, PID **3450128**, one numerical thread on CPU **5**. Bounded
startup passed. Expected about **9m56s** (18:50 UTC), conservative **29m48s**
(19:10 UTC), from the repeated complete synthetic test plus source-verification
allowance. No automatic polling or restart. No final decoding result is yet
available from the status check that launched this replacement.

The original `retained_v1` stopped after **89.15 seconds** at 17:27:15 UTC:
a development fit exhausted its 300-iteration cap. Source ingestion completed,
but no final prediction seal or aggregate score was produced. The
[failed run and frozen inputs are preserved](analysis/retained_v1_failure_review.json).
The [numerical amendment](DECODER_AMENDMENT_V2.md) raises the cap uniformly to
2000, with the same convergence requirements and scientific comparison.
All four implicated inner fits converged in **306–364 iterations** in the
[bounded reproduction](analysis/optimizer_amendment_v2/RESULT.json).

The [design](DECODER_DESIGN_V1.md) and
[implementation freeze](DECODER_FREEZE_V1.json) preceded inspection of E122's
final scientific outcomes. E122 is now complete and verified. Primary: after
256 rewrites at 128 bytes, does joint record/body input improve held-out
acquisition-donor prediction beyond the record alone? Four matched candidates,
all 64 sources, whole-source validation, separate native reconstruction scores.
This remains a **post hoc** auxiliary analysis. V2's numerical amendment follows
the failed fit and E122 outcome inspection; it does not inherit V1's earlier
freeze date. The manuscript hold remains.

The revised full pipeline passed on 16 excluded synthetic groups in
**103.98 seconds**, including prediction sealing, scoring and 32,512
repeated-input probability checks. [V2 qualification](analysis/decoder_full_tests_002/RESULT.json),
[review](DECODER_REVIEW_V2.md), [freeze](DECODER_FREEZE_V2.json),
[forecast](analysis/decoder_forecast_v2.json), [startup](jobs/retained_v2/STARTUP.json).
The original V1 qualification and launch receipts remain intact.

Use E014's retained prototypes, packets and recipient fields to ask which of
four matched founders an external observer can identify. Keep representation
size, identity decoding and native reconstruction as separate measurements.
Use identical candidate dictionaries and inclusion sets across observers,
source-block validation, label-leakage checks and paired uncertainty.

The [first deliverable](HANDOFF.md) verifies all 192 E014 archives and 3,136
arrays, exports 12,288 native checkpoint count rows, and checks a 320-case
development interface. All original qualified counts reconcile exactly.
Inventory took 98.30 seconds; interface checks took 41.92 seconds, one thread.
The separately frozen pipeline produces block predictions, aggregate estimates
and a reproducible script.
Integrate with E122's protected-foreign and long-horizon exports by reusing
retained fields; additional simulations are outside this request.

[Plan](PLAN.md), [E014 archive and earlier decomposition](../E014_long_renewal/README.md),
[E122 source inventory](../E122_specificity_ceiling_and_tail/planning_inventory.json).

E122's [implemented export schema](../E122_specificity_ceiling_and_tail/DATA_DICTIONARY.md)
preserves these fields at native precision; its 256-rewrite scientific
continuation completed and passed closeout. The [verified raw-source registry](../E122_specificity_ceiling_and_tail/SOURCE_DATA.json)
contains current E014 hashes. E123 now independently verifies those sources
and follows the theory lane's common reporting format. Ingestion checks exact
E014/E122 overlap and accepts the completed protected-foreign fields; overlapping
cases and source blocks are counted once. The first-deliverable documentation
is retained in [its archive](analysis/delivery_v1_documents/INDEX.json).

[Export contract](EXPORT_CONTRACT.md), [verified handoff](HANDOFF.md),
[source manifest](analysis/inventory_v1/SOURCE_MANIFEST.json),
[passing checks](analysis/inventory_v1/INTERFACE_CHECK.json),
[prediction schema](PREDICTION_SCHEMA.json).
