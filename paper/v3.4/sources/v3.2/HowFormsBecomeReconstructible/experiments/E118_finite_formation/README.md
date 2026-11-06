# E118 — finite formation and renewal

**Complete and verified; primary not established.** `formation_v1` finished
**31 October 19:07:30 UTC** in **5h34m48.97s** on four workers, close to its
5h21m forecast. Closeout passed **1 November 10:46:57 UTC**: **2,777 outputs /
48 frozen inputs** verified; figure inspected. All 32 fresh sources, 20,480
condition rows and every endpoint/harm remain. All new trajectories were
independently replayed; 5.759 GB retained.

Finite formation does **not** rescue this recipe at the tested settings.
Combined mixture success is only **7.18/6.84%** intact/pruned immediately and
**6.84/4.93%** after writing, versus **49.02/54.74%** and **54.44/49.80%** under
original rules. The original pruning pattern repeats: **+5.713 [4.053, 7.471]**
points immediately, then **−4.639 [−7.275, −2.100]**. Combined finite pruning
is **−0.342 [−0.879, 0.244]**, then **−1.904 [−2.686, −1.172]**: only later
harm passes the ten-gate primary. All four success-floor gates and all four
retention gates fail.

Tolerance alone and grid alone cause the largest losses; floor-only mixture
success is 28–35%. Native combined performance also falls to 5–9%.
Removing only the final reader floor changes no combined individual success
classification. These results identify a limit of the tested formulation,
without proving that every finite formulation must fail.

[Interpretation](INTERPRETATION.md), [report](runs/formation_v1/REPORT.md),
[statistics](runs/formation_v1/summary.json),
[figure](runs/formation_v1/finite_formation.png), [closeout](analysis/closeout_v1.json).

All **13 checks passed**. The complete excluded original-rule projection
matched the archived acquisition, all 32 ancestry boundaries, pulse,
continuations, recovery, pruning writer and both terminal draws exactly.
The latest check run took **103.74 seconds**. Fresh-source registration found
no collision across **462 prior manifests** and verified **44 excluded files**.
The full-width benchmark completed **13:10:18 UTC**, in **5m40.64s** on one
worker. Its checks passed, with **226 outputs / 45 frozen inputs** verified
and its figure inspected. It retained 1,280 condition rows, 256 context/draw
identities and 768 erased controls; every new step was independently replayed.
Those shortened schedules are technical evidence, not a scientific primary
outcome. Qualification and scientific freeze passed **13:31:59 UTC**, before
any scientific acquisition; the launch pins **48 inputs**.

The test generated records under their assigned rules from the first
acquired packet through 32 renewal cycles, the sham/pulse histories, mixture
construction, recovery, pruning and one further rewrite. Five conditions keep
the original formulation, tolerance alone, denominator floor alone, storage
grid alone and their combination distinguishable. All donors come from the
same condition's own history.

Teaching uses a fixed unit scaffold and has no learned-weight feedback. The
grid therefore applies to its first committed acquired record and every later
commit; no tolerance or strength-floor operator exists in teaching itself.
Later readers and cue-contrast captures use their condition's declared rules.

Each formulation prunes its own pre-channel recovery tags, retaining tags erased
by the grid as no-ops. The comparison concerns the whole formulation and its
pruning policy; it does not hold selected coordinates equal across histories.
All absolute endpoints, both pruning effects and individual harms remain.

The frozen scientific cohort is 32 fresh sources, 1180000–1180031, with four
recipients and two terminal injury draws. The combined mixture arm must meet
the same ten requirements as E116: the immediate-benefit/later-harm reversal,
all four lower success bounds above 50%, and retention within five points of
the matched original-rule endpoints. No alternative primary or automatic
sample extension is allowed.

Independent replay, excluded original-reference checks and full-width timing
passed before scientific freeze and launch. Long work runs detached, with
status checked on request. There is no automatic successor.

[Protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md),
[settings](plan.py), [source registry](SOURCE_DATA.json),
[checks](analysis/tests_attempt_002.json),
[benchmark forecast](analysis/benchmark_forecast_v1.json),
[benchmark startup](jobs/benchmark_v1/startup.json),
[qualification](analysis/qualification_v1.json), [freeze](SAMPLE_FREEZE.json),
[scientific forecast](analysis/forecast_v1.json),
[scientific startup](jobs/formation_v1/startup.json), [decisions](DECISIONS.md).

Next: a bounded saved-lineage diagnosis to locate the first loss of function
and normalized coupling, retaining every source and both endpoints. No new
long trajectories are needed for that diagnosis. No successor launched at closeout.
