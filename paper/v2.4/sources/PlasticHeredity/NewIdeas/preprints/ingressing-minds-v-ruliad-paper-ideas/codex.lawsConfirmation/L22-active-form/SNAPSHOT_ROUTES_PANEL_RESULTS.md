# D192 closeout: body access and writer access are different contributions

18 October 2026. **COMPLETE / SAVED-AUDITED.**
[Unchanged panel contract](SNAPSHOT_ROUTES_PANEL_V1.md),
[qualification](SNAPSHOT_ROUTES_PANEL_QUALIFICATION.md),
[complete mechanically generated tables](SNAPSHOT_ROUTES_PANEL_TABLES.md).

## Plain-language result

Updating from a body is useful in some circumstances, but not always. For
residual records, both-on updating improved later recognition over writing
from a protected snapshot alone. For common records, snapshot-only writing
did better. Giving the snapshot to the body and giving it to the writer are
not interchangeable. Recognition also does not measure complete shape fidelity.

This identifies conditional contributions of body-derived information. It
does **not** establish that the body must remain present rather than have its
observations recorded and replayed. That distinction motivates D193.

## Cases and comparison

All four exposed D191 histories 319100–319103, all 64 records/condition,
both families, all controls, and all 54 predeclared comparisons remain.
Two fresh read-noise sets, four draws each, are weighted equally; block means
are weighted equally. No old read outcomes or disposable 603191 are pooled.
These are development cases: **zero new founders**, no confirmatory interval,
no fitted policy, no case or gate selection, and no serial renewal.

`B` controls direct protected-snapshot access to body dynamics; `W` controls
direct snapshot access to the writer. Body-mediated history is not erased
when direct access is off. Every factorial body reads fixed incoming theta.
The snapshot-only writer has no running body. The same unchanged writer,
schedule, normalization and final 2,048-byte packet boundary apply.

| Condition | Common recognition | Common preference | Residual recognition | Residual preference |
| --- | ---: | ---: | ---: | ---: |
| B0W0 | 50.00000% | 0.00000 | 88.671875% | 83.203125 |
| B0W1 | 54.68750% | 9.37500 | 91.796875% | 88.0859375 |
| B1W0 | 55.46875% | 10.93750 | 91.6015625% | 87.890625 |
| B1W1 | 62.3046875% | 24.609375 | 91.015625% | 85.93750 |
| Protected snapshot only | 69.53125% | 39.453125 | 87.109375% | 79.296875 |

Preference is own-minus-partner recovery, shown in percentage-point units.
It is retained alongside recognition, not replaced by a favorable endpoint.

## Principal effects and harms

**Both-on versus protected snapshot.** Residual recognition improves
**3.90625 points**, preference **6.640625 points**. All four block means and
both future means improve on both endpoints; all omission means remain
positive. Of the 64 record means, **15 improve, 4 worsen, 45 tie** on each
endpoint. This is a coherent conditional result, not benefit to every record.

Common recognition instead falls **7.2265625 points**, preference
**14.84375 points**. Three block means worsen and one ties; both futures
worsen. **2 records improve, 11 worsen, 51 tie** on each endpoint. Do not
pool the two families into a universal active-form advantage.

**Direct body access, writer access on (B1W1−B0W1).** Common recognition
gains **7.6171875 points**, preference **15.234375**, with 6/0/58
recognition gains/harms/ties. Residual recognition loses **0.78125 points**,
preference **2.1484375**, with 4/7/53 gains/harms/ties. The residual block
effects are mixed, and one recognition omission mean is exactly zero.

That residual harm is conditional: with writer access **off**, direct body
access (B1W0−B0W0) improves residual recognition **2.9296875 points** and
preference **4.6875 points**. Both families have positive average body and
writer main effects, but the residual interaction is negative: **−3.7109375
recognition / −6.8359375 preference points**. Two individually helpful
routes need not help when combined.

B0W1 exceeds snapshot-only residual recognition by **4.6875 points** and
preference by **8.7890625**, with 19/4/41 recognition gains/harms/ties.
One block's recognition change is negative. This is a predeclared arm,
**not** a newly selected best policy or held-out matching result.

## Recognition, shape and other controls

Both-on common theta/parent correlation is **0.789641**, above snapshot-only
**0.689894**, despite its lower recognition. For residual records the
corresponding correlations are **0.544050** and **0.525515**. Higher coarse
recognition and higher full-pattern similarity remain distinct achievements;
none is complete preservation. All seven endpoints remain in the tables.

Allowing rewritten theta to feed back into the body (captured-live minus
fixed-reader B1W1) changes common recognition by **+7.03125 points** and
residual by **−2.34375**. Compared with its held-reference counterpart,
captured-live changes common recognition by **−0.1953125** (future signs
differ) and residual by **+1.5625**. These are separate interventions;
do not attribute all differences to one meaning of “live.”

Organized versus shuffled capture improves both-on recognition **12.5
common / 6.8359375 residual points**. Protected-only, both fixed-reader
held-reference paths and captured-held-live produce exactly the same outgoing
theta; writer-off equals incoming theta. Intact and supplied-positive controls
recognize 100%; reader-off recognizes 25% with zero preference. Every bridge,
independent replay and independent scalar check passes. The full tables
include unfavorable comparisons, both future streams, every block/message
stratum and every leave-one-block mean.

## Execution and audit

Execution completed **2026-10-18 15:45:20.260609 UTC**, in **469.928082429 s
(7m50s)**. One CPU 6 / numerical thread, nice 10; peak RSS **204,820,480
bytes**. Uncompressed saved arrays: **529,776,128 bytes**. External stage
retention at COMPLETE: **1,082,762,685 bytes (~1.008 GiB)**, including both
qualification attempts, below the unchanged 2 GiB cap. No data were deleted.

The separate user-requested saved-only audit passed: **725 outputs**, all
**104 repair paths** (8 body-free), **280 named / 216 unique reads**, **48
native saved bridges**, **8 held-fixed bridges**, **54 comparisons**,
equal block/future weighting and the three-block omission divisor. The
execution freeze binds 12,775 inputs / 75 repository modules. No dynamics
were rerun for the saved audit or this report.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-snapshot-routes-panel-v1`.
Run: `l22_snapshot_routes_v1_panel_attempt1`. Exact freeze, manifest,
COMPLETE and summary hashes are pinned by the
[report generator](../scripts/report_l22_snapshot_routes_panel.py) and printed
in the complete tables. Frozen protocols, code, failures and outputs remain
unchanged. No job is launched by this closeout.

## Next causal question

The same observations necessarily produce the same output under this
deterministic writer. Exact replay is therefore an apparatus check, not a
test for whether embodiment adds value. A stronger next contrast is a body
whose reference responds to **its own changing state** versus a matched body
guided by a prerecorded trace from a sister run with independent repair
noise. Both writers still observe their actual recipient body.

The proposed [D193 design](YOKED_REFERENCE_V1.md) makes this distinction
explicit, keeps both families, and separately blocks the body and writer
routes. A richer trace has a much larger information budget than one
snapshot; all trace-generation and storage costs must be disclosed.
L20/L22 remain **STRESS_TESTED / MIXED**. Prospective recipient matching,
autonomous repair and renewable serial transmission are still unestablished.
