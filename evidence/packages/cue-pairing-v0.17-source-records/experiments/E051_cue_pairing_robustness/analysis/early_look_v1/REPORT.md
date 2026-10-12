# E051 requested early look — 8 October 2026

**Descriptive, incomplete and not yet independently replayed.** The first
scheduled batch, blocks 34000–34007, has completed all 32 rebuilding generations
and terminal assays. These eight of the planned 32 independent blocks supply
128 of the planned 512 lineages per condition. The cohort was chosen from
completion status before inspecting outcomes. All conditions use the same
cohort. No confidence intervals, primary gates, stopping rule or tuning decision
are issued from this look.

The table gives **both-cue successes out of 128** after 32 rebuilds, using the
prespecified scattered-damage terminal assay. Initial states remain matched in
the noise rows; update noise remains matched in the reset rows. Teaching and
terminal-assay cue pairing remain unchanged throughout.

| Rebuilding cue pairing | Original exact rewrite | Fixed tolerance 1e-4 | Ordinary rewrite | Pure contrast | Exact preservation |
| --- | ---: | ---: | ---: | ---: | ---: |
| Matched noise and reset | 120 | 3 | 31 | 0 | 99 |
| Noise correlation .999 | 126 | 80 | 120 | 126 | 122 |
| Noise correlation .99 | 126 | 99 | 124 | 126 | 126 |
| Noise correlation .9 | 125 | 108 | 124 | 125 | 126 |
| Independent noise | 126 | 122 | 127 | 126 | 128 |
| Reset correlation .99 | 119 | 3 | 30 | 0 | 99 |
| Independent reset | 118 | 4 | 25 | 0 | 99 |

For the original writer, the matched reference is 93.75%; nearly matched and
independent noise are each 98.4375%. The mild reset perturbation is 92.96875%
and independent resets are 92.1875%. These descriptive differences do not
establish improvement or the protocol's five-part robustness conclusion.

The fixed tolerance is unfavorable under matched cues: 3/128 (2.34375%) versus
120/128 (93.75%) for the original rule. At noise correlation .999 it reaches
80/128 (62.5%) versus 126/128 (98.4375%). This concerns the one prespecified
tolerance, not every possible tolerance. Under independent noise it reaches
122/128 (95.3125%). No threshold is changed in response to these observations.

The saved diagnostics show the expected branch sensitivity: over boundaries
2–32, ordinary fallback selects 100% of available returning edges for the
paired original writer and 0% in each noise-mismatch arm. Those arms nevertheless
have high terminal success in this subset. Nonzero returning-edge writing and
connectivity can therefore coexist with no use of the exact-zero fallback.
This is an early indication that the supplied paired mechanism and unpaired
operation can differ without a corresponding performance collapse.

Pure-contrast writing has 0/128 terminal successes under matched cues and
126/128 with either .999-correlated or independent noise. Ordinary rewriting
and preservation also improve descriptively under noise mismatch; the pattern
does not isolate one causal explanation for performance. Initial-state mismatch
alone leaves returning-edge exact-zero/fallback rates at 100% here. Whether
normalized reading makes tiny noise-written weights useful remains a question
for the separate numerical-robustness design, not a conclusion of this look.

All 20 live and frozen scientific input hashes match. Recomputed strict-margin
scores from the saved mean-port arrays at all five assay horizons in all eight
blocks agree with the exported case scores (40 arrays); mean-port commitments
also match. This checks the reported counts, not the dynamics that produced them.
The full cohort and independent trajectory replay remain pending. The scientific
run, protocol, planned sample size and parent manuscripts are unchanged.

[Snapshot with all horizons, block counts and input hashes](snapshot.json),
[analysis script](summarize.py), [frozen protocol](../../PROTOCOL.md).
