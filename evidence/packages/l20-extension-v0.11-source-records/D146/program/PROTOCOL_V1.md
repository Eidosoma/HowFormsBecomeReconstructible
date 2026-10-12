# D146 — equal extra reconstruction time: reading versus rewriting

Approved 2026-09-18 after the D145 saved-state review. That review is post-hoc
and motivates this new prospective comparison; it does not predict its result.
Freeze protocol, qualified code and the complete address schedule before any
main founder or outcome. No exclusions, fitted rules, thresholds or early stopping.

## Question and sole primary

With compatible feedback fixed, does spending an additional 300 updates per
replacement on fresh-body reading outperform spending them on rewriting?

| Timing | Lineage reading | Lineage writing | Total per replacement | Final fresh assay |
|---|---:|---:|---:|---:|
| `base` | 300 | 1000 | 1300 | 300 |
| `read` | 600 | 1000 | 1600 | 300 |
| `write` | 300 | 1300 | 1600 | 300 |

The sole primary is **B `read` minus B `write` own-minus-alternative preference
after replacement 3**, measured by the unchanged 300-step fresh assay. Use
strict abs(V)>0.2, sign V>0, all 256 cells in the denominator. Average two
noise replicas and four lives within each of 16 founder blocks. Use 10,000
whole-block bootstrap draws, seed 14620260918; report absolute scores, paired
difference and 95% interval. Lower bound >0 favors read allocation; upper bound
<0 favors write allocation; otherwise unresolved, not equivalence.

This is relative allocation, not automatic improvement. Report each arm against
`base` and protected copying prominently: both equal-budget arms could be worse
than the original timing. No new score or fidelity pass threshold.

## Fresh cohort and unchanged apparatus

16 fresh blocks **93000–93015**, four lives, both target families, two replicas;
128 newly acquired record–host pairs. Disposable block **514246** only.
Namespace `l20-extension1-phase-budget-v1`. No D141–D145 founders, acquired
records, learned states or dynamics streams reused. Literal existing parent
settling, teaching, pre-reading and ordinary source-writing create F0 with
the original configuration, unaffected by descendants' assigned timing.

Original 2048-byte record, 4096-byte public guide, norm 0.3, writer lambda .001,
reference rho .002 and noise sigma .3 remain fixed. No guide refit or learned
address rule. Each family gets the same externally supplied, nonzero ideal-
preserving shift pool as D145 (A15/B31). Uniform draws with replacement,
lexicographically ordered pools, new shift each generation. The **same assigned
shift** applies to all three timings and their matched controls for a given
block/life/replica/family/generation. No favorable offset selection.

Seal all main addresses before founders. Separate address and dynamics streams.
Within a replica and generation, share birth and read-noise prefixes across all
conditions; share write-noise prefixes in a separate stream, independent of
read duration. Longer reading must not advance the writer's noise stream.
All final assays use common matched noise but a namespace separate from actual
lineage births/reads. Generations, replicas, lives and blocks stay separate.

## Panel, bottleneck and controls

For EACH timing, keep intact, protected-copy, lineage-read-off and write-off
conditions in BOTH families: 24 conditions per replica/life/block. Timing
changes only phase duration, not dynamics, gain or record encoding.

Each of three replacements routes incoming bytes using the fixed guide,
initializes a fresh V/EMA/R body, reads for the assigned duration, erases direct
packet access, initializes writer theta to zero and rewrites for the assigned
duration. Only outgoing record bytes enter the next fresh body. Public host
parameters and guide remain fixed; no body, optimizer or recurrent state passes.

A separate fresh 300-step assay reads each outgoing packet and never enters
the lineage. Copy passes original F0 unchanged. Write-off transmits zeros;
read-off disables lineage input, not the external assay. Controls run full
matched bookkeeping. Copy and write-off terminal aliases across timings are
required apparatus properties, never extra independent evidence.

G1 ordinary read prefixes match; base/write G1 writing matches through step
1000. The read arm intentionally has a different writing-start state. Later
inherited packets legitimately diverge: never force later states equal.

Saved lineage read times are (0,1,100,101,200,300) at 300 steps and
(0,1,100,101,300,600) at 600. Saved write times are (0,1,300,500,1000) at
1000 steps and (0,1,300,1000,1300) at 1300. Times are reported per condition;
never average mismatched timestamps as if they were identical. Assay times
(0,1,100,300). Checkpoint additions do not alter dynamics or RNG consumption.

Accounting: 24×2×4×16 = **3072 labelled lineages**, **9216 generation paths**,
**4608 enabled rewrites** (intact and read-off), **18432 reader paths/selectors**.
There are only 16 independent founder blocks; all cases/stages remain retained.

At every generation and for each timing/family, report copy-minus-write-off,
intact-minus-read-off and intact-minus-write-off preference: **54 checks**.
All lower pointwise bounds >0 qualifies the apparatus. Failure narrows
interpretation, never suppresses the numerical primary or triggers tuning.

## Secondary reporting

Keep all 72 condition/family/generation summaries and 66 non-base-versus-base
contrasts, six direct read-minus-write comparisons, eighteen intact-minus-copy
comparisons, 24 within-condition G3-minus-G1 changes and both-family changes
in the read-minus-write advantage. Retain all individual values/block means,
incoming/outgoing record shape, writing-end and assay-reference shape, all
saved profiles, guide labels, negative/zero outcomes and address coverage.
All secondary intervals are pointwise/unadjusted, not extra primary wins.
Continuous shape is template correlation, not fraction of information preserved.

## Qualification, freeze, benchmark and resources

Pin completed D145 and its saved-state review, including their immutable
scientific files, result reports and audit receipts. D145 COMPLETE SHA256:
`adf150141ae7c5b200de105f480ce6544edc9bdcb9a5d3fb8e56477efaa03d88`.
Review COMPLETE SHA256:
`dc01aa9034ac2f6640183ff112bae5233d3796f4e3c487e7f74902eb2daebb11`.
All earlier frozen files and results remain untouched.

Qualify independent dynamics replay and independent statistical reconstruction,
actual JSON/array round trips, timing corruption rejection, original-duration
bridge, shared noise prefixes/addresses, constant final assay, every-boundary
byte continuity and fresh resets, assay isolation, G3-vs-G1 primary selection,
sixteen-block normalization, and allocation wins despite both arms losing to
base. No main cohort generation before qualification/freeze/benchmark/seal.

Benchmark one complete disposable four-life block, including full independent
replay, controls, saved checks and a clearly non-evidential repeated-block
statistics fixture. Benchmark forecast = 4×qualified full-life seconds +90.
Main forecast =16×checked-block seconds +2×hash seconds +180, no parallel
speed credit. Byte budget =16×uncompressed-block bytes +benchmark bytes +64MiB,
maximum 2GiB plus 4GiB external free reserve. No speedup assumption or resizing
the cohort to fit a favorable budget.

At most six CPUs, numerical threads one. Data/logs/fixtures/caches only under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`.
Stages forecast above 600s detach with durable logs/null stdin/new session and
one bounded startup acknowledgement (at most 55s). No automatic polling, retry
or successor; the user advances detached stages. No automatic main launch
after a detached benchmark. Preserve failures and use single-use output paths.

Run ID `l20_extension1_phase_budget_v1_attempt1`. A favored allocation applies
only to these fixed budgets, two familiar families and supplied geometry. It
does not establish optimal timing, autonomous repair, unlimited renewal or
lossless preservation. L20 STRESS_TESTED / MIXED and D141–D145 are unchanged.
