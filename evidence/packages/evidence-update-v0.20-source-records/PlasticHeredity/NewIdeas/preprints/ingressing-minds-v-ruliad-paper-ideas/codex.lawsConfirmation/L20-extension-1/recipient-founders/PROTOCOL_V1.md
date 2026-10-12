# D182 Fresh founder recurrence protocol v1

2026-10-10. Fixed before new founder acquisition or descendant outcomes.
Status: scientific design, not a qualified executor or a launched experiment.
[D181 result](../recipient-repeats/POPULATION_RESULTS.md),
[inherited comparison](../recipient-repeats/PROTOCOL_V1.md).

## Question and scope

Does the small record-by-recipient pattern seen with aligned writing recur
in newly acquired records, rather than only in the four repeatedly studied
founder blocks? This is a bounded fresh-founder follow-up of a lead selected
after D180, not a challenge-versus-passive prediction competition.

Keep common-reader B ordinary as the focal descriptive comparison and aligned
B as the named secondary lead. Report ordinary first and both together, followed
by every other group. More consistent aligned signs would not by themselves
establish a larger aligned interaction. No fitted predictor, challenge, new
threshold, recipient setting, guide or writer mechanism is added.

The new panel is the same size as D181: four founder blocks, four lives per
block, both families and four futures per record. Four new blocks can test
recurrence beyond the original sources; they cannot establish broad population
generality or a precise population interval. Lives, futures, assay aliases
and overlapping record pairs are not additional independent founders.

## New founders and the exact starting record

Fix main IDs **120000, 120005, 120010, 120015**, a predetermined stride-five
panel in a new ID band, not selected by fidelity or performance. Disposable
source ID **514260** is separate. Retain every life 0--3 and both families:
**32 main F0 records**, plus eight disposable records. These IDs had no matches
in this workspace's code/docs before this protocol. Freshness also depends on
the new founder RNG namespace, not the numeric IDs alone.

Founder namespace: **l20-extension1-recipient-founders-v1**. Use the inherited
SHA-256 first-128-bit little-endian seed and PCG64 generator, keyed by source
index, life and phase. Phases are parent_birth, parent_settle, teaching,
source_birth, source_read, source_shift and source_write. A/B teaching and
source-writing modes share their phase streams as in the original recipe.

Use the unchanged D141 founder recipe in
[heldout_system.generate_founders](../src/l20_extension1/heldout_system.py),
through a separate adapter with only cohort/namespace guards changed:

1. Construct the native source context for the new source index. Generate its
   native threshold field and projected initial theta, parent birth, and
   120-step settling trace from new streams.
2. Acquire each supplied A/B target for 1,000 steps using the existing teaching
   rule. Read that acquired packet for 300 steps in a fresh source body.
3. Run the original translated and aligned 1,000-step source writers from the
   same source start, retaining both for provenance and independent replay.
4. Set the actual incoming F0 to **encode(written_fields[family, 0])**, the
   translated/ordinary writer's exported field. Do not substitute the earlier
   acquired-theta packet named founder_packets inside the founder archive.

All descendants, including aligned descendants, receive the same ordinary
F0 bytes. The aligned source branch is not an alternative starting record.
No old acquired field, parent body, source start or F0 packet is reused.
Qualification may bridge an explicitly labelled old disposable source only;
old sources cannot enter the main cohort.

Keep the full twelve-field founder trace and metadata, plus a separate source
bundle containing only founder_packets, guide and targets in the inherited
shapes. That bundle's founder_packets means the post-writing F0 defined above.
Record this naming distinction explicitly. The descendant loader whitelists
only those three arrays; it cannot access founder histories or alternate writes.

Freeze protocol, scientific code, cohort and seeds before any new acquisition.
After generating and independently checking all four main source blocks, seal
all **32 F0 byte hashes together**, the guide, targets, source archives and
metadata before the first main descendant outcome. The executor must refuse a
missing, changed, extra or duplicate source. Retain low-fidelity, wrong-label
and weak records; no screening or replacements. A structural or nonfinite
failure stops the stage with its artifacts retained, not a new random seed.

The source contexts follow the original index-based construction; their
metadata may differ from old donors. This is fresh acquisition under the same
recipe, not a test of novel functional categories or recipient physiology.
Only context metadata was inspected during design; no new acquired records
or tissue trajectories were generated.

## Unchanged reconstruction and controls

Keep the D131 guide with SHA-256
59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c.
It is supplied apparatus, not a refitted or inherited guide. Both target
families, the 2,048-byte carrier, projection norm 0.3, teaching, observation
threshold, feedback, durations, resets and checkpoints are unchanged.

Recipients always use context **514240**, not the new source context, with
only coupling replaced by **0.75, 1.0 or 1.25**. That setting applies to both
serial reading and writing for three complete replacements. Reading is 300
steps, writing 1,000; destroy body state between generations but preserve a
body's read-to-write continuity. The common terminal reader has coupling 1.0;
the native terminal reader has the lineage's coupling. Neither returns to it.

Keep all six conditions: ordinary, aligned, protected_copy, ordinary_read_off,
aligned_read_off, write_off. Copying preserves exact incoming bytes; write-off
exports zero. Keep the disabled writer paths as bookkeeping. Final assessment
readers are enabled. Preserve all copy, zero, common/native and A/B read-off
aliases and all five inherited control contrasts. Never enter controls into
the record/recipient decomposition.

The namespace for descendant randomness stays
**l20-extension1-recipient-coupling-v1**, with future IDs **2,3,4,5** and D181's
fourteen phase names. New source indices make the full main and disposable
addresses distinct from all D180/D181 addresses, despite reused future labels.
Family, coupling, condition and assay are absent from seeds. Fixed paired
randomness across comparisons remains; source and future streams are separate.
Qualification verifies all 140 founder and 1,120 future phase prefixes across
the main/disposable panel, including separation from the prior addresses.

## Fixed scores and analysis

Use the unchanged terminal qualified own-minus-alternative preference after
three replacements and a fresh 300-step read. Preference points are 100 times
this score, not success percentages. The common-reader result measures
retained record usefulness to one reference reader, not universal information.

For all eight common/native by A/B by ordinary/aligned groups, reuse D181's
record, recipient and interaction decomposition without mathematical changes.
Keep each future's absolute mean and nonnegative partitions; the six signed
cross-future products; their mean; fixed disjoint pairs **(2,3)** and **(4,5)**;
all donor descriptions and leave-one-donor/leave-one-future recalculations.
Keep negative estimates. No variance percentages, prediction ceiling, p-value,
population confidence interval or arbitrary pass fraction is introduced.

Retain Spearman correlations with tied ranks, all 120 overlapping record-pair
orders per group/setting pair, four-future-consistent reversals and the two
fixed-pair consistency descriptions. Undefined correlations stay undefined.
No requirement to reproduce the old count of three reversals: those concerned
different records. Interaction can recur without any rank reversal.

Show fresh-only results next to D180 and D181, separately labelled, never
pooled. Report whether aligned interaction signs recur in both fixed pairs,
their magnitudes, all six products, omissions and absolute effects. This is a
descriptive pattern, not a newly invented binary confirmation gate. A mixed
or negative result is retained, not a reason to add founders, alter the grid
or promote a favorable family, writer or assay.

Report every control cell/contrast, F0 and F3 own and own-minus-alternative
shape correlation, every guide label/address including unassigned labels,
body RMS and terminal clipping. Recognition is not shape preservation; a
terminal clipping check does not exclude clipping at intermediate times.

## Counts and retained evidence

| Quantity | Main panel | Complete disposable block |
| --- | ---: | ---: |
| New founder blocks / lives | 4 / 16 | 1 / 4 |
| Acquisitions / source pre-readers | 32 / 32 | 8 / 8 |
| Source writers including both modes | 64 | 16 |
| Post-writing F0 records | 32 | 8 |
| Main / control lineages | 768 / 1,536 | 192 / 384 |
| All labelled lineages | 2,304 | 576 |
| Serial read/write pairs | 6,912 | 1,728 |
| Common/native terminal assays | 4,608 | 1,152 |

Main summary counts remain eight groups, 32 donor descriptions, 32 donor
omissions, 32 future omissions, 48 pair-component estimates, 24 four-future
and 48 fixed-pair ranking descriptions, 1,152 control cells and 960 contrasts.
Retain full inherited checkpoints and all F0/F1/F2/F3 bytes, not full movies.
Also retain the newly generated founder/source traces; do not deduplicate them
by discarding evidence. Old D180/D181 files remain untouched and separate.

## Qualification and resource gates

Use a new adapter, independent replay and orchestration. Do not edit the frozen
D141/D180/D181 guards or scientific files to admit new IDs. Check founder
adapter AST equivalence to D141's acquisition recipe, allowing only guards and
namespace changes, and descendant/analysis equivalence to D181 with declared
ID/schema changes only. The independent founder checker already accepts an
explicit tag; wrap it with new cohort/config/byte-source guards, not looser
physics tolerances. Independent descendant statistics still require complete
panels with the new IDs and the proper denominators.

Qualify a complete disposable life, including new founder acquisition, source
writers, all 144 descendant lineages, independent replay, saved-row checks
and serialization. Use synthetic panels for missing/extra/reordered sources,
bad seals, false freshness, source leakage, seed pairing, aliases, signed
negative components, rank ties, omission denominators and failure retention.
Bridge labelled old disposable paths without admitting them to new results.

Then benchmark **one complete serial disposable block**: source construction,
all eight F0 records, 576 lineages, all controls, independent replay, I/O and
saved checks. Do not generate main founders during qualification/benchmark.
Review its audit and measured costs before freezing the population wrapper.
Benchmark completion never automatically launches the main panel.

All numeric files, fixtures, logs, receipts and caches are under
/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1, using stem
**l20_extension1_recipient_founders**. Only code/docs stay here. Fix **1 GiB for
this new stage**, including design/qualification, benchmark, all source and
descendant outputs, failures and audits, plus **4 GiB free-volume reserve**.
Existing D180/D181 storage is retained separately, not hidden or deleted.

Prior costs are planning anchors, not a fresh benchmark: D181's serial block
took 1,131.91s; its four-worker population took 31m01s. New acquisition/replay
adds work. The older D141 complete disposable block took 158.61s, including
more than acquisition alone. Adding that whole cost gives a deliberately
conservative historical planning allowance of about 21m31s per new serial
block and about 89 minutes for four blocks plus launch/check overhead, with
no parallel-speedup credit. It is not an ETA or a measured bound for new code.

Before the new benchmark, use 4 * measured complete checked-life seconds +
2 * source-hash seconds + 120. Before main, use 4 * measured complete checked-
block seconds + 2 * source-hash seconds + 180. Storage is 4 * measured complete
uncompressed block bytes, **including founders and F0 bundles**, plus all
retained new-stage files and 64 MiB headroom. Recheck immediately before launch.
If the 1 GiB cap cannot hold, stop for a separately documented design decision;
do not drop controls, clean fixtures, change samples or raise it silently.

Use at most six CPUs, one numerical thread per worker; serial benchmark uses
one worker, main may use four. Every stage forecast above 600s runs detached
with durable logs and startup acknowledgement only, with no automatic progress
polling, retry or successor. Separate saved-only audits forbid new dynamics.

## What this could establish and the next step

Recurrence would strengthen the claim that record-recipient dependence is
not peculiar to the old four founders, under this fixed apparatus. It would
not demonstrate autonomous learning dispositions, interface repair, unseen
functional concepts, exact preservation, biological generality or a superior
predictor. Coupling still changes reading and writing together.

The original challenge-prediction question stays separate. A later forecast
comparison needs its own fixed models, matched observation budgets, whole-
founder validation and strong starting-only baseline. D141/D162 uncertainty,
D174/D176 negative findings and L20 STRESS_TESTED / MIXED remain unchanged.

Next: implement and qualify the new-source adapter and independent replay,
then measure the complete disposable block. This design does not launch it.
