# Follow-up leads from the completed P02 analysis

Exploratory, outcome-informed audit requested by the user's "any leads further".
All source outcomes and the P02 aggregate results are already exposed. Preserve
P02's frozen comparisons and conclusions. No fitting, simulation, changed
caliper, feature selection, threshold tuning or model promotion is performed.

Before this audit's calculations, fix these questions:

1. Does the forecast improvement occur among currently passing bodies, or among
   bodies already failing? Use only the existing current strict margin >0.25
   indicator. Report both strata, every model, every block, row-weighted and
   equal-block scores, and each stratum's contribution to the original total
   Brier difference. Do not create further outcome-selected subgroups.
2. Compare the already saved secondary signed model with the simpler
   expression-and-history model. This cross-model comparison is post hoc;
   P02's primary comparison stays unchanged. Also show both original contrasts.
3. On the unchanged 84 close-output pairs, compare choices based on the saved
   excluded-block probabilities of the expression/history model, the secondary
   signed model and the primary signed model. Compare with P02's recorded
   current-margin, raw-signed-transfer and constant-history choices. Exact ties
   split choices evenly. Report all pair yields, hindsight regret and the nine
   terminal-discordant pairs, not only a favorable subset.

Passing at generation 14 and passing the final fresh scattered assay are
different endpoints. Their contingency table is not an estimate of probability
of recovery/loss under an identical repeated challenge. The new strata and
comparisons cannot establish confirmation, individual-state continuation
probabilities, causal mediation, or a general damage/resource boundary.

If the increment occurs mainly among already failing bodies, the appropriate
lead is a narrower prediction of later assay outcome among such states. If it
also holds among passing bodies, it warrants further assessment of reserve
beyond current output. Neither result licenses selecting a new predictor on
these same folds and calling it validated.

All calculations reuse the frozen record and prediction CSVs, bind their hashes,
and recompute stored Brier errors directly from probabilities and outcomes.
The nine-pair decision calculation also cross-checks the previous raw-feature
decision totals. This small descriptive calculation is expected to finish in
seconds and creates no long task.
