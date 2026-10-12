# E014 reviewer deliverable — 10 October 2026

[Manuscript-ready text and captions](HANDOFF.md) ·
[Full numerical report](products_v2/REPORT.md) ·
[Independent audit](products_v2/AUDIT.json)

All requested E014 raw fields were found at
`E014_long_renewal/runs/confirmation_v2/` on this host. The 128 lineage archives
are excluded from git by `**/*.npz`. Their original hashes match. This package
commits the compact analytical extracts and reproducible outputs so a separate
checkout does not need the 3.23 GB raw fields to rebuild the analysis.

At sixteen rewrites, compact own/foreign/protected qualified agreement is
**64.383% / 62.996% / 68.266%**. The own-history contrast is **1.387 points**,
not the total agreement. From three to sixteen rewrites, sign agreement falls
**3.005 points** while amplitude qualification rises **0.892 points**.
Qualified agreement falls **2.529 points**. This is a direct post hoc decomposition
of E014, with all cases and the original observer retained.

The homogeneous pilot provides a separate illustration: its **27.36-point**
history effect coexists with only **13/32** founders meeting formation requirements.
A strong history effect and qualified formation are separate achievements.

## Figures

| Figure | PNG | SVG | PDF |
| --- | --- | --- | --- |
| Own, foreign and protected agreement across fresh checkpoints | [PNG](products_v2/historical_specificity.png) | [SVG](products_v2/historical_specificity.svg) | [PDF](products_v2/historical_specificity.pdf) |
| Sign/amplitude decomposition and joint categories | [PNG](products_v2/sign_amplitude.png) | [SVG](products_v2/sign_amplitude.svg) | [PDF](products_v2/sign_amplitude.pdf) |
| All 16 lineage reads, plotted separately | [PNG](products_v2/lineage_agreement.png) | [SVG](products_v2/lineage_agreement.svg) | [PDF](products_v2/lineage_agreement.pdf) |
| Pilot history effect versus formation qualification | [PNG](products_v2/pilot_history_formation.png) | [SVG](products_v2/pilot_history_formation.svg) | [PDF](products_v2/pilot_history_formation.pdf) |

All agreement panels use native score units. The checkpoint figure shows the
full 0–1 scale with same-unit detail insets. G1 precedes the first rewrite;
lineage reads are not spliced into the distinct fresh-checkpoint reader stream.

## Data and checks

- [Cell counts](data_v2/cell_counts.csv.gz): 204,800 rows covering both record
  budgets, all 64 blocks, 20 stages, four founders, two recipients and ten arms.
  Each row has four exhaustive integer categories summing to 256 cells.
- [Endpoint counts](data_v2/endpoint_counts.csv.gz): 163,840 rows forming the
  4×4 after-three/after-sixteen category table for each matched reader/arm.
- [Source index](data_v2/SOURCE_INDEX.json): archive paths, individual raw hashes,
  original completion/audit hashes and extraction provenance.
- [Native-unit figure table](products_v2/checkpoint_table.csv) and
  [3,180 summaries](products_v2/summary.json): all controls and pointwise intervals.
- [Five exact score/inference checks](TESTS.json), [analysis plan](PLAN.md), and
  [full independent recount](products_v2/AUDIT.json).
- [Portable rebuild check](PORTABLE_CHECK.json): the analysis, independent
  aggregation and all twelve figure exports rebuilt in a separate directory
  containing only the compact extracts, scripts and nine committed dependencies,
  with no NPZ files. All 3,180 estimates, pilot context and checkpoint CSV match.

All 204,800 original individual qualified scores and 480 historical mean/interval
summaries reproduce exactly. A second label/histogram implementation independently
recounts all 128 raw lineage files and endpoint tables; all 3,180 means and
intervals agree exactly. The pilot's original audit and its formation/contrast
calculations are also checked. No new dynamics were run and no cases were removed.

Q is the intersection of matching signs and `|v|>.2`, with all 256 cells in the
denominator. In general it is not the product of the marginal sign and amplitude
rates. New intervals are descriptive and pointwise, resampling whole blocks.
Endpoint cross-tabs compare fresh bodies, not within-cell trajectories or a
unique causal attribution. Spatial-detail loss is not measured by these scores.

## Reproduce from a git checkout without the raw NPZ files

From `WhereDoFormsComeFrom/experiments`, using an unused output directory:

```bash
bash run_python.sh E014_long_renewal/analysis/reviewer_specificity_v1/derive.py --data E014_long_renewal/analysis/reviewer_specificity_v1/data_v2 --output E014_long_renewal/analysis/reviewer_specificity_v1/products_rebuilt
bash run_python.sh E014_long_renewal/analysis/reviewer_specificity_v1/audit.py --data E014_long_renewal/analysis/reviewer_specificity_v1/data_v2 --products E014_long_renewal/analysis/reviewer_specificity_v1/products_rebuilt
bash run_python.sh E014_long_renewal/analysis/reviewer_specificity_v1/plot.py --products E014_long_renewal/analysis/reviewer_specificity_v1/products_rebuilt
```

`run_python.sh` uses the workspace's NumPy/Matplotlib environment. An equivalent
Python environment with those packages can execute the same scripts. Every script
caps numerical work to one CPU and keeps output under this analysis directory.
The portable audit checks the derived counts and inference; add `--raw` only
where the original NPZ archive exists to repeat the full raw recount.

To re-extract from the full local archive, run `extract.py --output` with another
unused directory under this package. Relevant raw arrays are `prototype`,
`generation_read[...,0,:,:]` and `checkpoint_read[...,0,:,:]`; state component0
is activity, not the EMA or reference state. `checkpoint_numbers` is [1,3,8,16].
Arms0/1/7 are own rewriting, foreign-record renewal and protected copying.

## Preserved technical attempts

The first extraction stopped before generating data because E001's older audit
receipt calls its completion digest `audited_complete_sha256`. The extractor now
validates that schema as well as E014's `complete_sha256`. See
[data_v1 failure](data_v1/FAILED.json).

An initial derivation was invoked before extraction finished and stopped without
producing estimates. See [products_v1 failure](products_v1/FAILED.json).
The successful outputs are `data_v2` and `products_v2`; neither failure changed
the observer, cohort or analysis questions.

E053 was not polled or changed, E054 was not launched, and parent manuscripts
were not edited. The handoff supplies the material for the manuscript agent.
