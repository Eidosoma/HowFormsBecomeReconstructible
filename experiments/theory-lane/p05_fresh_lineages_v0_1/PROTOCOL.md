# Frozen repair on new lineages

Test whether the established recipient-only completion rule improves reconstruction
on newly generated lineages without selecting failed cases. The earlier 64-case
panel is exposed development data: completion achieved 33.55%, outgoing 22.41%,
and matched sign shuffling 8.12%, with equal block weighting. No repair parameter
changes are permitted. This is a prospective new-lineage validation of one
conventional rule in the same simulator, not an independent hypothesis discovery,
external replication or a distinctive RDT prediction.

## Population and development

Generate blocks 81000 through 81015 only after freezing the entire executable
protocol. The developmental seed identity is the string
P05_fresh_lineages_v0_1:<block>, passed to the original E016 teaching and E015/E022
renewal stream contracts. This new namespace separates lineages from existing
integer-seeded cohorts. The accessible exposure search found no prior use of this
namespace; no comprehensive programme-wide exposure register was located.

Each block has all four founders and four recipients, giving 16 records. Assign
history by (block-81000) modulo four: exact writing; tolerance at generation 3;
tolerance at 3,5,7,9,11,13; or tolerance at 3,9,10,11,12,13. Every other generation
uses the original writer, including generation 14. There are four independent
blocks per history, 256 records total. Histories are balanced between blocks;
they are not paired history counterfactuals within a block.

Use the native consistent teaching regime: 512 teaching steps, the last 128
captured, with matched opposite-polarity cue episodes. Use the unchanged renewal
equations, 2048 reader steps, 1024 settling steps, 24 missing non-port cells, dt .2,
noise .02, birth SD .05, writer beta 3, and tolerance 1e-4. Save teaching states,
every generation's incoming/outgoing packets, bodies, masks, resets and port means.
Holding is omitted as in the replay-validated preceding engine: capture precedes
holding, its body is discarded, and its independent stream does not feed renewal.

Enroll every generation-14 outgoing record regardless of the body's success,
sign structure, repair changes or any assessment result. No extension to reach a
desired number of failures. The primary repair receives only O and its unchanged
optimizer options. The incoming packet and developmental body enter audit and
secondary classification, never repair construction.

## Fixed repair and assessment

Copy repair.py, optimizer.py and sign_graph.py byte-for-byte from the completed
recipient-only assay. Keep 16 starts, at most 64 checkerboard sweeps, seed
2026101004, input pins and tie rules. Fill every exactly zero lattice edge with
the median absolute nonzero O weight times the inferred endpoint-sign product;
preserve every observed weight. An erased record remains erased.

Assess four records: outgoing O, recipient completion, sign-shuffled completion,
and erased. Shuffle only the added edge signs with the same support, magnitudes
and sign counts, using [assessment namespace, block, "shuffle", history, founder,
recipient]. Do not discard unchanged shuffles.

Use eight fresh uniformly sampled 24-cell non-port injuries and reset/noise draws
per record, paired across all four variants. Namespace is
P05_fresh_lineages_v0_1_assessment; injury keys append block, "injury", replicate,
founder//2, recipient; read keys append block, "read", replicate. Cue noise remains
matched. Use the unchanged native 2048-step reader and strict minimum task margin
>.25 across means over the last 32 updates. Score intended and opposite mappings;
mixed or weak outputs pass neither. No assessment-time writing or further renewal.
There are 8192 scientific paired-cue contexts, 2048 per variant.

## Forecast and analysis

The primary directional forecast is positive completion-minus-outgoing intended
success across the entire cohort. Zero or negative fails this forecast on the
declared population. A positive estimate with a descriptive interval spanning zero
leaves benefit unresolved. Favorable failed-body or history subgroups cannot
replace the primary result. The matched shuffled-sign contrast is secondary and
tests the contribution of inferred sign placement under matched edge resources.

Average the eight draws within each record, 16 records within each block, and
16 blocks equally. Report every block and the four history means. For descriptive
95% uncertainty, perform 20000 paired whole-block bootstrap resamples, resampling
four blocks with replacement within each history; PCG64 seed 2026101006. This
preserves the balanced target mixture. The 16 blocks are the inference units;
individual trajectories are not independent replicates. Sample size is a bounded
feasibility choice, not a claim of power for a minimum useful effect.

Also report opposite-task success, rescued/harmed paired counts and summaries
conditional on generation-14 body passing or failing the native endpoint before
repair. These subgroups receive counts and pooled descriptive rates without a
separate significance claim. Include zero-count subgroups explicitly. Report
history-specific results without selecting a winner or changing the rule.
No superiority margin, equivalence or noninferiority test is invented.

No novel historical information is created: O already contains learned structure.
The lattice, input locations, algorithm, reader and additional edge resources are
supplied. This tests one subsequent reconstruction, not serial repair, autonomous
apparatus maintenance, general task composition or universal recoverability.

## Verification and execution

Before freezing, replay the known block-34000 consistent teaching, a native
original-writer renewal, and a duplicate native assessment. Test a synthetic
negative primary, opposite outcomes, empty subgroups and corrupted summaries.
Independently check acquisition with a flat implementation, all captures from
saved bodies with the separate writer equations, all 256 optimizers with the
Prim-based implementation, and every repair with scalar grid construction.
For each new block, audit one incoming generation-14 read and all four assessment
records at fresh draw 4 using the separate native reader. Recompute raw-window
scores, CSV rows, block and history summaries, stratified bootstrap and paired
counts without importing the production analysis.

Benchmark known block-34000 teaching, one single-history renewal and four duplicate
known incoming records at the planned eight-draw batch shape. Estimate total work
from 16 teachings, 16*14 renewals, 16 assessments, 256 checked optimizers and native
audits; multiply measured compute by 1.5 and add 180 seconds for evidence handling.
Require forecast <=3600 single-thread seconds. Preserve an over-budget benchmark;
do not silently shrink the cohort or discard a history.

Freeze inputs before generating any new lineage or outcome. One worker, numerical
libraries one thread, within the shared 12-CPU ceiling. Detach jobs over 600 seconds
with stdin closed, PID/log and durable RUNNING/COMPLETE/FAILED state. Generate,
repair, analyze and verify automatically to completion, without polling or an
automatic successor. Preserve failed runs and all historical results.
