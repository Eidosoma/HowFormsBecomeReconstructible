# Manuscript handoff: specificity and fidelity in E014

This package answers the reviewer using E014's original unprescribed spatial
apparatus. It supplies a new post hoc analysis; it does not borrow the separate
guided-writer sign-only result or alter any original success criterion.

## Archive answer

All 128 requested files are present on this host at:

```text
/home/robert/Random-Replications/WhereDoFormsComeFrom/experiments/E014_long_renewal/runs/confirmation_v2/
  block_012000_factor_4.npz ... block_012063_factor_4.npz
  block_012000_factor_1.npz ... block_012063_factor_1.npz
```

The lineage files total **3,227,309,039 bytes**. The repository-level ignore rule
`**/*.npz` explains why summaries appear in another checkout while these files
do not. They have been checked against the original completion hashes.
The original run also contains the corresponding founder/source archives.

The two compressed CSVs in [data_v2](data_v2/) preserve all integer counts needed
for this analysis in under 2 MB. The [source index](data_v2/SOURCE_INDEX.json)
records every lineage-file hash, checked completion/audit receipts and extraction
checks. These are portable analytical extracts, not a complete backup of the
continuous fields or a substitute for the original simulation archive.

## Suggested replacement/extension beside §3.2

At sixteen rewrites, the compact record produces **64.38% qualified agreement**
with the own-founder prototype, compared with **63.00% for the matched foreign
record** and **68.27% for protected copying**. The incremental own-history
advantage is **1.387 percentage points [0.848, 1.954]**. This smaller contrast,
rather than total agreement, isolates the tested effect of which founder's
record initiated the chain. The foreign score is not a pure measure of the
background's contribution, and these scores do not count information bits.

A post hoc decomposition of the retained E014 fields separates matching signs
from amplitude qualification. Between three and sixteen rewrites, compact-record
sign agreement declines from **69.62% to 66.61%**, a change of **−3.005 points
[−3.630, −2.420]**. Over the same interval, the fraction of sites with
`|v| > 0.2` increases from **94.93% to 95.82%**, by **0.892 points
[0.734, 1.046]**. Qualified agreement declines from **66.91% to 64.38%**.
Its exact accounting identity is qualified agreement = sign agreement minus
matching-but-subthreshold sites: that latter fraction falls by 0.476 points,
partly offsetting the reduction in sign matching. The decline is therefore
associated with poorer coordinate-matched signs despite more frequent amplitude
qualification; it cannot be described simply as reduced activity amplitude.

Full-field records show the same marginal direction: sign agreement declines
by **6.024 points [5.337, 6.719]**, while amplitude qualification increases by
**0.639 points [0.488, 0.790]**. Qualified agreement falls by 5.638 points.
These are descriptive, pointwise 95% whole-block intervals on the original
64-block cohort. They do not measure translation-tolerant shape, spatial-detail
loss or a causal division of the dynamics into independent sign and amplitude
mechanisms.

An additional direct specificity check uses the same E014 fields: at sixteen
rewrites, compact own-record chains exceed foreign-record chains in **sign-only
agreement by 1.331 points [0.784, 1.922]**. Their amplitude-qualified fractions
differ by only **0.019 points [−0.082, 0.117]**. This post hoc comparison supports
a surviving distinction in coordinate-matched signs; the amplitude comparison
does not establish equivalence.

## Optional endpoint-accounting detail for E43

The paired after-three/after-sixteen fresh readers also permit a four-category
cross-tabulation at each coordinate. For compact records, the net qualified-score
change is −2.517 points from sign-only endpoint differences, +0.021 from
amplitude-only differences, and −0.033 from differences in both. These sum to
the observed −2.529 points. The amplitude-only and both-different intervals
include zero. For full fields, the corresponding net terms are −4.803, −0.402
and −0.433 points.

These are comparisons between fresh bodies under paired reader randomness,
not observed trajectories of the same cell, counts of all intervening crossings,
or a causal attribution. In particular, differences in both properties cannot
be uniquely assigned to signs or amplitudes. Marginal amplitude qualification can
increase while some previously correct, resolved sites become subthreshold.

## Suggested addition concerning the homogeneous pilot (E31)

The homogeneous-background development pilot has a much larger own-history
effect, **27.36 points [21.83, 32.50]**, yet only **13/32 founders (40.625%)** pass
formation, below the required 75%. The shared-heterogeneous pilot has a smaller
effect, **2.32 points [0.95, 3.90]**, while **26/32 founders (81.25%)** qualify.
Both settings pass the diversity component. Historical dependence and stable
formation are therefore separate achievements: a stronger history effect does
not rescue a failure to form qualified founder patterns. These eight-block
development results remain separate from E014's fresh 64-block study.

## Figure captions and assets

**Historical specificity and retained agreement.** Own-record, matched foreign-record
and protected-copy qualified agreement with the same own-founder prototype,
at fresh checkpoint reads after 1, 3, 8 and 16 completed rewrites. Both record
sizes use the same native 0–1 score scale; insets enlarge the same units.
The shaded own−foreign gap identifies the tested incremental history effect;
it is not a partition of total agreement into information quantities. Bands are
pointwise 95% whole-block intervals across all 64 blocks, with all 256 founders
and two recipient replicates retained. The explicitly reported paired-contrast
interval should not be inferred from overlap of the separate mean intervals.
Protected-copy probes are constant because their bytes and reader random draws
are shared across checkpoints. Checkpoint bodies never feed back into the lineage.

[PNG](products_v2/historical_specificity.png) ·
[SVG](products_v2/historical_specificity.svg) ·
[PDF](products_v2/historical_specificity.pdf)

**Sign and amplitude contributions to E014's observer.** Top: qualified agreement,
sign agreement and amplitude qualification for own-record fresh readers. Bottom:
the four exhaustive joint categories. All 256 sites stay in the denominator;
signs use `v>0`, and qualification uses strict `|v|>0.2`. Qualified agreement is
the intersection of the two properties, not generally the product of their
marginal rates. Intervals are descriptive, pointwise 95% block bootstrap intervals.

[PNG](products_v2/sign_amplitude.png) ·
[SVG](products_v2/sign_amplitude.svg) ·
[PDF](products_v2/sign_amplitude.pdf)

**Historical dependence does not establish formation.** The homogeneous and
shared-heterogeneous E001 pilot settings are compared on formation qualification
and the terminal own−foreign contrast after three rewrites. Each setting has
eight blocks and 32 retained founders. The homogeneous setting's larger contrast
coexists with failure of the formation threshold. Intervals are exploratory
whole-block intervals; these cases are not pooled with E014.

[PNG](products_v2/pilot_history_formation.png) ·
[SVG](products_v2/pilot_history_formation.svg) ·
[PDF](products_v2/pilot_history_formation.pdf)

The [separate lineage-read figure](products_v2/lineage_agreement.pdf) displays all
16 saved lineage reads against their correct completed-rewrite count, 0–15.
G1 is before the first rewrite. This stream is deliberately not spliced into the
fresh-checkpoint curve. The [report](products_v2/REPORT.md),
[native-unit table](products_v2/checkpoint_table.csv) and
[full summary](products_v2/summary.json) retain the other controls and estimates.

No parent manuscript was edited. These paragraphs and captions are ready for the
manuscript agent to integrate, retaining the post hoc and observer-specific limits.
