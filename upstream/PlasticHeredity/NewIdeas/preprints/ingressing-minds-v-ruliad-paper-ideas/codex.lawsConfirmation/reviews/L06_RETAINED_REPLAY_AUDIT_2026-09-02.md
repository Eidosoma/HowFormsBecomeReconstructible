# L06 retained/replay evidence adjudication

**Date:** 2026-09-02  
**Scope:** E29's fidelity-versus-rewritability result and E32's conserved
wild/rewritten graft contest.  
**Work state:** `STRESS_TESTED`; E29's missing 80 fidelity rows were recreated
by exact historical-namespace replay, and E32's retained tissue counts were
independently recalculated. Fixed outcome-known cohort, influence, clustering,
denominator, and measurement-validity diagnostics were then applied.  
**Overall verdict:** `MIXED`. The narrow across-configuration correlation is
real and exactly reproducible. The data do not identify one latent competence
axis, E32 does not measure stable compromise, its share design is spatially
confounded, and neither biological prediction has been tested.

## Plain-language result

E29's reported number is sound: replaying the same 10,240 historical futures
recreates the 80 missing fidelity values and reproduces Spearman
`rho = 0.4717413`. No single row or tissue creates it. But the 80 rows combine
three coupling cohorts with different means and an unbalanced layout. The
over-coupled cohort is highest in both fidelity and conversion. Within each
cohort the correlations are small and mixed in sign; after removing cohort
rank means the correlation is only `0.128`. A conditional permutation test
does not distinguish the remaining alignment from within-cohort exchangeability
(`p = 0.316`, outcome-known diagnostic).

This supports `these two measurements positively covary across this pooled
configuration table`. It does not establish a single underlying faculty.
There are only two observables, no fitted latent-variable model, no competing
model, and no held-out positive test. The prospective E29 hypothesis was the
opposite—a negative maintainer/switcher trade-off—and that gate failed. The
source fairly anticipated this possible reversal, but naming a reversal in
advance is not the same as specifying and passing a positive-axis test.

E32 does not support the other half of L6. It counted relative winners and
both-parent-distinct chimeras; it never defined or counted stable compromise.
Only 195/1,536 grafts met the relative winner rule, zero met the chimera rule,
and 1,341 were simply unresolved. Those unresolved grafts may include dead,
tied, switching, incoherent, or intermediate trajectories. The retained files
contain no trajectory, alive-state, similarity, or analog-charge rows with
which to separate them.

At nominal 50/50, rewritten tissue won 48 of 75 resolved contests (`0.64`),
missing the registered `>=0.65` bar by one contest. That is a suggestive
bounded preference among the selected resolved subset, not evidence that the
remaining 437 grafts compromised. The share ladder also fixes wild tissue on
the left and rewritten tissue on the right, while rounding 35/65% to 37.5/62.5%.
Area, spatial identity, and parent identity therefore cannot be separated.

## Reproducibility record

| Item | Record |
|---|---|
| Definitive immutable run | `l06_retained_replay_audit_v1_attempt2` |
| Frozen protocols | [`v1`](../protocols/L06_RETAINED_REPLAY_AUDIT_V1.md), [`v1.1 amendment`](../protocols/L06_RETAINED_REPLAY_AUDIT_V1_1_AMENDMENT.md) |
| Contract digest | `e6ef24b8217fed03a89126b76b863531dc19519a725b463537f6fba0f5879a79` |
| Inputs hashed | 99; every recorded hash rechecked successfully |
| Runtime | 123.997 seconds |
| Resources | one worker; BLAS/OpenMP thread limits all one |
| Fresh scientific futures | 0 |
| Historical-namespace futures replayed | 10,240 (`80 x 4 x 32`) |
| Test suite | 61 passed |
| Machine-readable result | [`audit.json`](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l06_retained_replay_audit_v1_attempt2/audit.json) |
| Input hashes | [`input_hashes.sha256`](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l06_retained_replay_audit_v1_attempt2/input_hashes.sha256) |
| Run status | [`STATUS.json`](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l06_retained_replay_audit_v1_attempt2/STATUS.json) |

SHA-256 values are
`4da5501316be726bdc71e13b681ef8e27392fbe3f47af39b3b3e994ac920c349`
for `audit.json` and
`e001bb41eb7dccc0dc3199e563f8ef0295fe1ca4f10a19d50a34b5dc47d1284c`
for the input-hash manifest. All 18 source-code hashes and both protocol
hashes in the run manifest also recheck exactly.

Attempt 1, `l06_retained_replay_audit_v1`, remains immutable. It correctly
replayed every source result but labelled an upper-tail conditional
permutation probability as two-sided because the stratified null is not
centred at zero. The amendment was frozen before calculating the corrected
value. Attempt 2 repeats the complete historical replay and supersedes
attempt 1 for adjudication; no scientific conclusion changed.

This is an outcome-known exact replay and retained-data audit, not a fresh
replication. The additional diagnostics were fixed before reconstructing the
80 row values but after the retained aggregate `rho` and E32 counts were
known.

## E29: the pooled correlation reproduces

The eight E27 shards contain exactly 80 unique conversion rows: 48 band, 16
under-coupled, and 16 over-coupled. Their independently transcribed config
digest and E29's digest both match the retained files. The audit invokes the
shared simulator with the exact source namespace
`gps-axis-v1:<cohort>:<tissue>:<seed>` and separately reconstructs Spearman
ranks and the 512-shuffle source null.

| Source field | Retained | Replayed |
|---|---:|---:|
| Configurations | 80 | 80 |
| Fidelity/rewritability `rho` | 0.47174128841349267 | 0.4717412884134926 |
| Shuffled-null q05 | -0.19172912955568794 | -0.19172912955568794 |
| Negative trade-off gate | false | false |

Every field matches at the audit tolerance. The source null was designed to
test whether the correlation was unusually negative. It supplies no
prospectively declared positive threshold; the positive-axis reading is a
transparent, outcome-known reversal.

The pooled effect is not a single-point accident:

- the 4,096-resample tissue-cluster interval for the pooled `rho` is
  `[0.2901, 0.6287]`;
- deleting any one row leaves `rho` in `[0.4519, 0.4998]`; and
- deleting any tissue index, preserving the fact that indices 0–15 contribute
  three cohort rows, leaves `rho` in `[0.4384, 0.4998]`.

These diagnostics confirm a stable pooled-table association. They do not
resolve what produces it.

## E29: cohort structure carries most of the interpretation

| Cohort/subset | n | Fidelity mean | Conversion mean | Within-subset `rho` |
|---|---:|---:|---:|---:|
| Band, all rows | 48 | 0.947495 | 0.199435 | +0.173448 |
| Band, tissue indices 0–15 | 16 | — | — | -0.249633 |
| Under-coupled | 16 | 0.956889 | 0.190430 | -0.148152 |
| Over-coupled | 16 | 0.966913 | 0.314751 | +0.158824 |
| Balanced three-cohort rows, indices 0–15 | 48 | — | — | +0.647744 |

The balanced-subset value remains high because balancing row counts does not
remove coupling identity: the same between-cohort ordering is still present.
After globally ranking both variables and residualising each on cohort
indicators, `rho` falls to `0.127695`.

The fixed conditional permutation keeps cohort membership and shuffles
conversion only within cohort. Its raw-`rho` null has mean `0.420337` and 95%
range `[0.320741, 0.519966]`; preserving cohort alone therefore produces a
substantial positive pooled statistic. The observed `0.471741` has upper-tail
`p=0.158165` and corrected equal-tail two-sided `p=0.316329`. This is not
evidence that the true within-cohort association is zero; it shows that this
small table does not distinguish an extra within-cohort axis signal from the
cohort-preserving null.

Coupling is exactly determined by cohort, and only tissue indices 0–15 occur
under all three coupling levels. The design cannot tell whether coupling
causes both measurements, tissue properties create an axis, or another common
cause operates. A positive bivariate correlation is compatible with all of
those structures.

## Why one latent competence axis is not identified

Calling a statistical axis usually requires several indicators and a model
that can be checked against alternatives. E29 has two variables and one
correlation. A one-factor model for only two indicators is not independently
identified without strong additional constraints; direct dependence and
unmeasured common causes fit the same observation. The code contains no factor
analysis, measurement model, intervention on the proposed faculty, or held-out
prediction derived from it.

The safe conclusion is covariance in a pooled configuration family. `Memory`,
`competence`, and `great regeneration` are broader constructs than the actual
inputs: mean parent/daughter texture-census cosine and E27 zap-conversion
fraction in one 16x16 simulator.

## E32: all registered aggregates reproduce, all gates fail

All four shards share the expected digest and contain 16 unique tissue rows.
Every stored total, rate, and gate independently reconstructs.

| Nominal wild share | Effective wild columns | Resolved | Unresolved | Rewritten wins among resolved |
|---:|---:|---:|---:|---:|
| 0.35 | 6/16 = 0.375 | 66/512 = 0.1289 | 446/512 | 28/66 = 0.4242 |
| 0.50 | 8/16 = 0.500 | 75/512 = 0.1465 | 437/512 | 48/75 = 0.6400 |
| 0.65 | 10/16 = 0.625 | 54/512 = 0.1055 | 458/512 | 31/54 = 0.5741 |
| **All** | — | **195/1,536 = 0.1270** | **1,341/1,536 = 0.8730** | — |

The depth gate fails because `48/75 = 0.64`, below 0.65. A naive exact
binomial test against equal wins gives `p=0.0203`, but grafts reuse one
tissue's harvested parent pool and are not independent trials. At tissue
level, rewritten has more wins in 10 tissues, wild in one, and five tie. The
equal-tissue mean is 0.6785, and a descriptive tissue-cluster interval for the
pooled rate is `[0.5643, 0.7324]`. Thus a rewritten preference among resolved
50/50 contests is worth a clean confirmation, but it neither passes the
registered bar nor describes the unresolved majority.

The share ladder fails (`0.424, 0.640, 0.574`). More importantly, every graft
uses wild columns on the left and rewritten columns on the right. The source
itself notes that the one-head field and posterior rewrite are positioned.
No orientation swap, interleaving, or randomized column assignment separates
fragment area from anatomical content. The rounded effective shares also
differ from the labels.

## E32 did not operationalise compromise

The scorer provides two independently computed flags:

1. A winner must remain alive and be strictly closer to the same parent than
   the other for the final four generations. There is no minimum resemblance
   to the winning parent.
2. A chimera must remain alive for eight generations, remain coherent across
   that window, and have cosine similarity `<=0.85` to both parents.

There is no `compromise`, `intermediate`, or `close to both` classifier. The
two flags are not coded as an exhaustive, mutually exclusive partition, and
the retained shard rows contain only their aggregate counts. In particular,
`n - resolved` does not establish survival, stability, coherence, proximity
to both parents, or an averaged analog state.

The discovery log's claim that the other 87% settled into stable intermediate
textures cannot be derived from the retained files or from the implemented
scorer. Zero chimeras is a failed registered prediction, not positive evidence
for an unmeasured fourth category. Likewise, no parent/graft analog-voltage
values were retained and no weighted-average prediction was scored, so
physical conservation cannot be credited as the demonstrated cause of an
`averaged self`.

## Clause adjudication

| Atomic claim | Highest current evidence | Verdict |
|---|---:|---|
| Fidelity and rewritability positively covary across the pooled 80 tested configurations | E4 exact historical replay | `CONFIRMED_WITH_NARROWER_WORDING`; `rho=0.471741`, stable under row/tissue deletion |
| E29 prospectively rejected a maintainer/switcher trade-off in favour of a positive axis | E2/E4 | `NOT_CONFIRMED`; the registered negative gate failed, while no positive threshold or held-out test was specified |
| The covariance identifies one latent memory-competence axis | E2/E4-derived stress | `NOT_CONFIRMED`; two indicators do not identify that model, and cohort-adjusted association is weak |
| Rewritten tissue tends to win resolved 50/50 E32 contests | E3 retained recalculation | `CONFIRMED_WITH_NARROWER_WORDING`; 48/75, but the registered 0.65 bar fails and clustering/conditioning matter |
| Conserved graft conflicts resolve mainly by stable compromise | E2/E3 | `NOT_CONFIRMED`; compromise was not implemented or retained; 87.3% is unresolved, not classified |
| The graft result is independent of share, position, bulk averaging, and threshold choices | E2 code audit | `NOT_CONFIRMED`; fixed orientation confounds share, analog averaging is untested, and threshold sensitivity is unrecoverable |
| Great regeneration predicts easy reprogramming across real organisms | E0 | `UNTESTED`; no organism-level data |
| Biological graft conflicts should average | E0 | `UNTESTED`; the simulation itself did not measure averaging |

## Strongest wording that survives

> In one pooled family of 80 configurations of a 16x16 stochastic voltage-sheet
> simulator, an exact historical replay reproduces a positive Spearman
> association (`rho=0.472`) between mean texture fidelity and E27 zap
> conversion. Much of the association follows the three coupling cohorts, and
> a single latent competence variable is not identified. In a separate fixed-
> orientation graft assay, only 12.7% of grafts met a relative winner rule;
> rewritten tissue won 48/75 resolved nominal-50/50 contests. The assay did not
> classify stable compromise or test biological regeneration and grafting.

## Deferred closer-pass tests

After the programme-wide first pass, L6 merits two clean confirmations:

1. Run a balanced tissue x coupling factorial on a fresh namespace, with a
   positive association hypothesis and threshold frozen before the run.
   Estimate fidelity and rewritability uncertainty rather than treating each
   noisy fraction as exact, and reserve complete tissues as a held-out set.
2. Add at least a third independently motivated competence indicator, specify
   a measurement model prospectively, and compare a one-factor model with
   direct-coupling and multi-factor alternatives. A coupling intervention can
   test common-cause structure more directly than another pooled correlation.
3. Redesign grafts with wild/rewrite left-right swaps, randomized or
   interleaved positions, exact fragment shares, independent parent pools, and
   retained individual trajectories. Define mutually exclusive winner,
   stable-close-to-both, stable-distinct-from-both, unstable, and death
   outcomes before running.
4. Record analog voltage and position-sensitive texture alongside the census;
   test an explicit weighted-parent prediction across shares and freeze
   threshold/horizon sensitivity on development data before a held-out run.
   Treat organismal statements as separate biological hypotheses.

These runs should be benchmarked first. Any job expected to exceed ten
minutes must be detached and use no more than four CPUs.
