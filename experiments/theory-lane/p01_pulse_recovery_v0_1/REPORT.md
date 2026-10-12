# The pulse preserves function without restoring the original network

Completed 9 October 2026. The saved pulse histories support a narrower mechanism
than a simple return toward the original record. Returning to the original
writer prevents the large deterioration seen under repeated tolerance writing,
but the normalized reader network does not converge back to the paired original
trajectory in either declared early comparison. The earlier negative P01
forecast results remain unchanged.

This is a development analysis of the same eight exposed blocks, 128 lineages
per policy, with no new native simulation and no fitted prediction model. It
uses all saved generations 3–32 and retains all five writer policies. The
[definitions](PROTOCOL.md) and executable analysis were fixed before extracting
the new measurements. Outcomes and hypotheses were already known, so that
timing does not establish prospective confirmation.

## What the controlled pulse shows

At generation 3 all policies act on the same pre-write body. The pulse P and
repeated-tolerance policy T produce identical outgoing packets. Their
generation-4 bodies and scores are also identical. P then returns to original
writing; T continues tolerance writing. All masks and random draws remain
matched. These equalities and every outgoing writer calculation were checked
against the saved arrays byte for byte.

Let D be the mean row L1 distance between a branch's normalized outgoing reader
and the same-generation original branch, averaged over live non-input cells.
It measures a change in relative inputs, not task loss or raw packet bytes.

| Outgoing generation | Single pulse D | Repeated tolerance D |
|---|---:|---:|
| 3: first altered record | 0.03267 | 0.03267 |
| 4: first original rewrite in P | 0.04377 | 0.08649 |
| 6: third original rewrite in P | 0.03884 | 0.22114 |
| 16 | 0.07754 | 0.83302 |
| 32 | 0.13270 | 1.06923 |

P's distance increases from generation 3 to 4 in **all eight blocks**, by a mean
0.01109. From 3 to 6 it increases by 0.00616, with six blocks increasing and two
decreasing. Thus both fixed comparisons fail to show average return toward the
original reader. Distance subsequently remains much smaller than under T, but
does not decay toward zero over the observed horizon.

The absolute difference in 64-step signed cue transfer from O also grows: from
0.001108 at generation 3 to 0.005064 at 4 and 0.002449 at 6. Seven of eight blocks
increase in the first comparison and six in the second. There is some recovery
from the generation-4 discrepancy by generation 6, but changing the reference
to that peak would replace the declared comparisons. Both results are retained.

Nor is an immediate increase in this transfer score a sufficient explanation
of P's eventual benefit: at generation 4, P's mean signed transfer is 0.06846,
slightly below T's 0.06898, despite P's much better final success. By generation
6 the respective scores are 0.07471 and 0.06442. These are fixed linear
diagnostics of an outgoing record, not native probabilities or a validated
early predictor.

## Performance remains high while repeated writing deteriorates

| Generation | Original body success | Single-pulse body success | Repeated-tolerance body success |
|---|---:|---:|---:|
| 4 | 128/128 | 126/128 | 126/128 |
| 6 | 128/128 | 127/128 | 120/128 |
| 8 | 120/128 | 117/128 | 100/128 |
| 16 | 118/128 | 116/128 | 27/128 |
| 32 | 117/128 | 113/128 | 6/128 |
| Separate h32 terminal assay | 120/128 | 116/128 | 3/128 |

Each body's score is measured before its outgoing write. The terminal assay
reconstructs a separate body from the final record under its own declared
damage/randomness; it must not be substituted for generation-32 body success.

The fraction of nonzero-contrast edges susceptible to the tolerance substitution
starts at 1.20% for all branches. At generation 32 it is 55.43% on T bodies,
4.93% on P bodies and 4.75% on O bodies. P only actually uses the tolerance
writer at generation 3; its later percentages are hypothetical susceptibility,
not additional interventions. This is consistent with feedback in which
continued substitutions create bodies vulnerable to further substitutions.
It does not identify that feedback as the unique cause of the losses.

The secondary magnitude-restored branch remains informative: its final reader
distance from O is 0.64562, while terminal success is 106/128. Global distance
from the original implementation therefore cannot be equated with loss of the
task. The sign-restored policy retains only 19/128 terminal successes.

![Native function and outgoing-reader changes over time](results/recovery_timecourses.png)

All curves are equal-block means. The complete block trajectories are retained
in [analysis.json](results/analysis.json) and [block_timecourses.csv](results/block_timecourses.csv).
The figure is also available as [SVG](results/recovery_timecourses.svg) and
[PDF](results/recovery_timecourses.pdf).

## Rare pulse harm and different meanings of persistence

Two lineages fail in the pulse body at generation 4 while their original
counterparts pass. One passes again at generation 5; the other never passes a
later pulse body through generation 32. The latter already had a failed common
body before the generation-3 write: original writing rescues that lineage,
whereas the pulse prevents that observed recovery. The claim is finite-horizon
nonrecovery, not irreversible failure.

The pulse loses four terminal successes relative to O and gains none. Three of
these four harmed lineages pass their early bodies at generations 3, 4 and 6.
Their first observed pulse-body failures after the intervention occur at
generations 8, 18 and 23. The fourth is the early persistent failure above.
All four are retained individually in the analysis. Early normal expression
therefore misses three of the four terminal harms in this small, outcome-defined
group; this is not an independently validated risk classifier.

Uninterrupted expression and terminal reconstruction differ substantially even
under O. Over generations 4–32, only 52/128 original lineages pass every body,
although 120/128 pass the terminal assay. Of the 76 that fail at least one body,
69 pass the terminal assay. Corresponding pulse counts are 49 uninterrupted,
116 terminal successes and 68 terminal successes among 79 with a body failure.
Damage varies between bodies, so these counts do not estimate recovery from
one fixed challenge. They directly prohibit treating the terminal rate as the
probability of uninterrupted performance.

## Scientific decision

Keep the finite causal result: stopping tolerance writing after one event
preserves much of the function lost under its continuation. Reject the simple
reading that this requires rapid contraction toward the original normalized
network, or an immediate improvement in the 64-step cue-transfer score. The
single-pulse branch preserves competence across altered implementations in
this domain. That distinction is compatible with RDT's functional-family idea,
but compatibility alone earns no predictive claim.

The next discriminating question is whether **spacing equal numbers of
tolerance writes changes the outcome when the first and last pulse and the
final recovery interval are held fixed**. An explicit, unrun six-event design is
recorded in [NEXT_EXPERIMENT_DRAFT.md](NEXT_EXPERIMENT_DRAFT.md). It tests timing
and intervening original writes without assuming they restore the original
network. A long-horizon predictor still needs frozen forecasts and a separate
evaluation against strong baselines on unseen continuations.

## Verification and reproducibility

Extraction took 29.27 seconds and produced 19,200 lineage-generation-policy
rows. All source file and array commitments match; original histories agree
across pilots; all actual writer packets, native scores and stored writer
diagnostics recompute exactly. Four synthetic checks compare graph calculations
with explicit matrices and verify strict scoring and the distinction between
an action on one body and divergence between histories.

A [separate verifier](verify.py), importing neither the extraction nor analysis
implementation, reconstructs the summaries, eight recovery contrasts and 60
paired body comparisons. It additionally constructs explicit 256-node matrices
for 25 fixed native contexts to verify signed/unsigned transfer and distances.
It passed. The [verification receipt](results/verification.json), raw
[lineage table](results/lineages.csv), figure provenance and final snapshot
retain the evidence. No prior artifact was edited, new cohort opened, or long
simulation launched. The remaining 24 E051 blocks remain exposed from the
previous review, not potential theory-lane holdouts.
