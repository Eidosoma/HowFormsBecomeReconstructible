# P7: ordinary M transmission works in unequal-group arrangements

Completed 2026-09-12 at **20:16:25 UTC**, about 2 h 4 min after launch.
Protocol: [PAPER_M_CALIBRATION_PROTOCOL.md](PAPER_M_CALIBRATION_PROTOCOL.md).
Run: `runs/paper-m-calibration-20260912T181247Z-hj82p5cg`.
Job: `runs/jobs/paper-m-calibration-20260912T181247Z-5ejg8qvm`.
Evidence: `summary.json`, `gate.json`, `independent_audit.json`, case records
and full-state NPZ trajectories in that run. A fresh read-only re-audit on
September 12 exactly matches the saved 14,506-check/295-integration report.

## Plain-language result

M-state cells can change fresh E-state cells so that the recipients keep M
after every donor is removed. It worked when three donors contacted one
recipient, and when six donors contacted three recipients. It did not work
with three donors and three recipients in the tested arrangements.

The successful recipients remained M through both isolated retention periods.
E-donor shams did not produce M, and blocking RNA transfer or cutting the
donor/recipient communication boundary prevented M acquisition. These are
working ordinary-M transmission conditions, not just transient responses
while a cue remains present.

## Main outcomes

| Arrangement | Qualified settings | Recipient outcome after donor removal |
| --- | --- | --- |
| 3 donors to 3 recipients, 2x3 | 0/4 | All three remain E |
| 3 donors to 1 recipient, 2x2 | 4/4 | Recipient acquires and retains M |
| 6 donors to 3 recipients, 3x3 | 4/4 | All three acquire and retain M |

Each row covers depol/hypol crossed with the two previously used Kd settings.
All eight positive settings satisfy the matched-control rule and finer
agreement. All 36 coarse sham/RNA-block/boundary-cut conditions leave the
fresh recipients retained E. The zero-Kd copies under the two nominal
anchors are physically duplicate controls, not independent dose evidence.

In the failed three-to-three arrangement, low-Kd depol preserves donor M
but does not transmit it to recipients. High-Kd depol and both tested hypol
settings instead convert the donors to E. Thus lowering RNA transport alone
does not rescue equal-group transmission; it can change donor retention
without changing the recipient's outcome.

## Verification

All **98 cases and 295 native integrations completed**. All **14,506
independent checks pass**, including the exact historical positive P3 replay,
negative P6 replay, common stock/bath checks, and the P6-matched new baseline.
All **48 finer comparisons agree** in the registered endpoints and outcomes.
Continuous numerical differences remain available in the audit.

The panel includes 48 coarse new conditions, all 48 refined, and two historical
replays. It is deterministic model comparison, not 98 independent biological
replicates. All execution, frozen-file, original-input and copied-input
integrity checks pass. No follow-on experiment launched automatically.

## What this does and does not establish

P6 lacked a working ordinary-M transmission control. P7 supplies that control
in two arrangements, allowing a more informative test of established E
carriers. It does not establish a special advantage of acquired M over ordinary
M, because the donors here were ordinary prepared stocks.

Numbers and topology change together. The results do not isolate a pure
donor-count effect, establish a general majority-vote law, or identify the
minimum necessary group size. Contact history and continuous regulatory states
could also matter in subsequent tests.

Three donors producing one new carrier, or six producing three, is not yet
a renewable same-sized relay: another identical step would need additional
carriers or a separately demonstrated expansion mechanism. No donor recycling,
division or silent supplementation was used. Even successful same-size
single transfer would require an explicit serial test before claiming renewal.

E/M are model regulatory states, not complete diagnoses. This is not wet-lab
validation, therapeutic evidence, autonomous reproduction or a unique PH law.

## Next authorized experiment

[P8 calibrated rewriting](PAPER_CALIBRATED_REWRITE_PROTOCOL.md) uses the working
six-to-three depol/high-Kd cue on actual round-6 E carriers, alongside fresh
and time-matched E controls. Remove every cue, test retention, and let the
three actual targets contact one fresh E probe. Separate writing/probe blocks
distinguish failure to rewrite from failure to pass on a rewritten state.
It tests rewriting plus one onward transfer, not a self-sustaining M relay.
