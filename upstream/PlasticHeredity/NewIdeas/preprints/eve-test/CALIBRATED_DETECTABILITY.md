# OBS-010: false alarms controlled, but restricted-panel power is insufficient

Version 1.0 — 2026-09-06. [Frozen plan](CALIBRATED_DETECTABILITY_PLAN.md),
[input](data/calibrated_detectability_input.json), [result index](data/calibrated_detectability.json).

## Outcome: no-go for the current matched-fitting approach

**Calibration works for the tested synthetic nulls. Detection of smaller
differences does not.** All 22 selected cells pass the false-positive and
sanity checks, but three of the four context/kind blocks miss the required
power even for a large 50-percentage-point prevalence gap. Stop this approach
with the present cache; no new threshold or feature search follows here.
This is not evidence that PH is absent or that every EVE study is impossible.

The following are ranges across the 22 cells, not pooled probabilities:

| Planted practice prevalence, A vs B | Expected contrast | Detection frequency range | Cells clearing ≥80% detection with simultaneous uncertainty bounds |
|---|---:|---:|---:|
| 55% vs 45% | 0.01 | 1.8–7.0% | 0 / 22 |
| 60% vs 40% | 0.04 | 6.65–19.6% | 0 / 22 |
| 65% vs 35% | 0.09 | 19.05–44.9% | 0 / 22 |
| 75% vs 25% | 0.25 | 76.0–94.85% | 17 / 22 |

For the 50-point gap, twenty cells have point estimates of at least 80%,
but only seventeen clear the predeclared uncertainty requirement. The two
lowest point estimates are 76.0% and 78.95%. Thus the large-effect failure
is partly about reliable qualification across the fixed panel, not a claim
that large differences are undetectable everywhere. Smaller-gap detection
is substantially inadequate even before applying uncertainty bounds.

| Context / comparison | Large-gap qualifying cells | Required | Decision |
|---|---:|---:|---|
| 2023 same-corporation splits | 4 / 6 | 5 | Fail |
| 2023 corporation pairs | 3 / 4 | 4 | Fail |
| 2024 same-corporation splits | 4 / 6 | 5 | Fail |
| 2024 corporation pairs | 6 / 6 | 5 | Pass |

No failed cell is dropped and the favourable 2024 pair block is not promoted
to an overall pass. No tested prevalence gap clears all blocks.

## False-positive control

Cutoffs calibrated on 2,000 balanced-null worlds per cell range from
**0.0843657 to 0.1639763**, above the old 0.05 practical-effect floor.
Verification uses 2,000 fresh worlds per cell and never changes those cutoffs.

| Verification null | Observed false-positive range | Largest simultaneous upper bound |
|---|---:|---:|
| 50% vs 50% prevalence | 1.3–3.3% | 4.9797% |
| 10% vs 10% prevalence | 0–0.10% | 0.6665% |
| 90% vs 90% prevalence | 0–0.15% | 0.7638% |

All three upper bounds are below 5% in every cell. The homogeneous control
has zero detections and maximum error 2.22e-16; maximal difference is detected
in every world. These checks concern independent binary character labels
on fixed ship schedules. They do **not** calibrate real doctrine, battles,
alternative accounts, selection bias or temporal inheritance.

## Design and interpretation

Keep all 22 quota-feasible cells from OBS-009: twelve states and ten unordered
pair-windows. The states cover one corporation per context, each for six
fortnights; the pair frames contain four and six windows. Regenerate the
original 400 forty/forty character panels in each cell and verify all 8,800
against the prior snapshot. Every new world selects one of those panels
uniformly with replacement. Full ship probabilities, quotas, IDs and support
rules are unchanged; recorded fitting identities are not read or scored.

For each cell, calibrate on balanced binary labels using the 1,951st ordered
contrast out of 2,000, the prespecified conservative 97.5% order statistic.
Use the larger of that value and 0.05. Detection requires **strictly greater**
contrast, so ties do not count. Save and hash every cutoff before any
verification label is generated. Separate seed namespaces govern the two
phases; each verification world shares character uniforms across all nine
scenarios, preserving character-level correlation across ship types.

Clopper–Pearson intervals describe Monte Carlo detection frequencies conditional
on the fixed panel mixture and this calibration. For the 154 cell/scenario
rates used in the gates, each interval uses tail probability 0.05/308.
The union-bound construction supplies at least 95% simultaneous coverage
without assuming independence between cells or scenarios. Ordinary 95%
intervals are also retained. None is a real-data causal confidence interval.

A go requires all null/sanity checks and a simultaneous lower detection
bound of at least 80% in at least 80% of cells in each context/kind block,
for the 50-point gap. Smaller gaps are fixed diagnostics, not alternative
ways to bypass that rule. Neither the new decision cutoffs nor a favourable
cell repair the old five-point precision or whole-frame coverage failures.
The restricted target is still not a stable longitudinal population.

## Verification and records

All **88,000 world rows** are retained: 44,000 calibration and 44,000 verification
worlds, comprising **440,000 scenario comparisons**. No world is unobservable
on this already restricted panel. These are simulations, not new characters,
corporations, lineage replications or empirical PH observations.

**527 tests pass**, including 22 new tests of source/contract pins, fixed panels,
phase-separated labels, cutoff ranks/ties, exact-binomial calculations,
simultaneous intervals, block denominators and a complete synthetic audit.
Independent checks recount all 1,188 original calendar eligibility rows and
all 8,800 panels' IDs, hashes and directly enumerated matching support.
They regenerate every new panel index and label hash, check every value's
range/identity and detection flag, recompute all cutoffs, all 198 ordinary
and 154 simultaneous intervals, summaries and go/no-go gates. Separate direct
character-pair arithmetic checks 660 first/middle/last scenario comparisons.
This is sampled independent value checking, not recalculation of every value.

[Primary snapshot](data/pilot/calibrated_detectability_20260906T172112Z_d2zn2l70/manifest.json),
[calibration seal](data/pilot/calibrated_detectability_20260906T172112Z_d2zn2l70/calibration_seal.json),
[verification summaries](data/pilot/calibrated_detectability_20260906T172112Z_d2zn2l70/verification_summaries.json),
[decision](data/pilot/calibrated_detectability_20260906T172112Z_d2zn2l70/decision.json)
and [audit](data/pilot/calibrated_detectability_20260906T172112Z_d2zn2l70/audit.json)
are preserved. [Full replay](data/pilot/calibrated_detectability_20260906T172257Z_f5znpqwb/manifest.json)
regenerates every panel and new synthetic world from the pinned OBS-009
schedule and reproduces **25 non-audit files byte-for-byte**, including both
compressed streams. Freeze, calibration-seal and audit timestamps/replay
labels differ; all seal hashes are verified separately. This is implementation
verification on the same data, not independent scientific replication.
Compilation, whitespace and preserved-boundary checks pass.

## Stopping boundary

The promised go/no-go experiment is complete: **no-go**. No automatic LinkNet
measurement or further threshold/feature search is started. The result
narrows our optimism: this approach can detect very large toy differences
in some well-observed subsets, but does not provide the reliable, broadly
supported practice measurement needed for the proposed inheritance study.
An independently motivated different question or more informative observations
would require a new decision, not a reinterpretation of this failed contract.

No metadata search, network request, raw combat scan, download, history or
external contact. No real fitting outcome, empirical observer validation,
LinkNet qualification, new PH continuity cutoff, temporal/coherent-eight
endpoint or carrier claim. Original cases, flow gates, reserved outcomes,
earlier results, old cutoff and preprint remain unchanged.
