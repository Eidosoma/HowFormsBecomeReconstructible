# D178 — recipient-coupling pilot proposal v1

Date: 2026-10-08. Status: **design, not executor qualification or run approval**.
This document fixes the proposed scientific comparison before its new outcomes.
Implementation changes to the science require a dated addendum, not silent edits.
[Stage overview](README.md); [preceding D177 result](../record-recipient/RESULTS.md).

## 1. Question and scope

Can differences in reconstruction be attributed to reproducible record quality,
a recipient that is generally favorable, or compatibility between a particular
record and a recipient? This is a mechanistic prerequisite for deciding what
a later predictor should predict, not another challenge/predictor competition.

D177 established that the existing recipient-index differences do not supply
the intended contrast. Index and threshold spread are unused by reset readers;
a uniform well offset is canceled by mean subtraction. Deliberately varying an
active coupling parameter is a **new model extension**. No claim that native
recipient diversity has been discovered, or that this is biological variation.

Source trail (existing code is read-only):

- [Reset reader, writer, record and guide](../../src/laws_confirmation/l20_guide_renewal.py).
- [Active cell dynamics](../../../ladder_web/src/ladder_web/engine.py).
- [Reference feedback](../../../blueprint_web/src/blueprint_web/engine.py).
- [Inherited outcome definition](../../src/laws_confirmation/l20_three_rewrite.py).
- [D141 source packet construction](../src/l20_extension1/heldout_system.py).
- [Existing independent physics](../../scripts/audit_l15_repair_speed_outputs.py).

Coupling multiplies local neighbor-minus-cell drift and survives spatial
centering. Unlike changing reference-update speed, it does not change the
reference-memory clock. D177's synthetic 0.75 sensitivity check established
activity, not a favorable serial outcome or a validated operating regime.

## 2. Fixed recipients and source panel

Recipient coupling: **0.75, 1.0, 1.25**, an engineering bracket of +/-25% around
the current value. These are not biological ranges or optimized settings.
Every recipient starts from the exact context for index 514240; replace only
tissue.coupling. The same setting applies during every serial read and write
in that lineage. No alternating recipient types across boundaries in this pilot.

Keep dt=0.2, sigma=0.3, reference rho=0.002, writing feedback c_m=0.2, EMA rate,
geometry, read/write duration, record projection, routing and guide unchanged.
Reader feedback c_m remains zero. Do not substitute source-founder context or
vary well asymmetry along with coupling. No new anchors or stress fields.

Select donor IDs **90000, 90005, 90010, 90015** mechanically: evenly spaced
through the existing 90000--90015 cohort. Retain all four lives and both target
families in each block: **32 records, 16 per family**. These founders have already
been studied. No promising-record filter, new parent acquisition, fresh-founder
claim, or substitution after observing any new outcome.

Inputs are the exact uint8 founder_packets[life, family] in D141's saved lineage
archives. These F0 packets are the source's ordinary/translated written records,
not its pre-writing acquired theta. Aligned and ordinary descendants start
from the same bytes. Each packet is 2,048 bytes (16x16 little-endian float64);
this tissue experiment is not the earlier 64-byte DoorKey germ.

Use only founder_packets, guide, targets and provenance metadata from these
archives. Do not use saved later states, diagnostics, forecasts or outcomes.
The design checker hashes archive files but reads only array headers, not
numerical payloads. A future executor must whitelist the three arrays explicitly.

Fixed D131 guide SHA-256:
59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c.
The guide is shared external apparatus, not newly inherited or fitted.

## 3. Futures, boundaries and controls

Two independent future replicas per record. Fix the new RNG namespace to
l20-extension1-recipient-coupling-v1, with phase strings
replica{r}:g{g}:birth/read/source_shift/source_write and
replica{r}:terminal:birth/read (r=0,1; g=1,2,3).
Use the inherited SHA-256/PCG64 generator with source block ID and life.

Exclude recipient setting, family, writer and control from seed construction:
at fixed block/life/replica, all receive paired noise and shifts. Different
replicas have independent streams. No old outcome stream is reused in the
pilot. Terminal native/common assays share terminal streams but not bodies.
Generate shift with the existing integer 1..255 mapped to a 16x16 translation.

Each of three replacements: frozen learned guide routes the incoming packet;
a completely fresh body reads it for 300 steps; a writer continues that body's
V/EMA/R for 1,000 steps with theta initialized to zero; export the declared
packet; destroy all body state before the next reader. Do not reset between
a body's own read and write. No previous packet, target label or guide access
inside the writer. Normal output is project(tanh(R_final), norm=0.3).

Every record, setting and replica has this complete panel:

| Condition | Serial reading | Writer geometry / theta update | Outgoing carrier |
| --- | --- | --- | --- |
| ordinary | Enabled | Translated / enabled | Normal exported record |
| aligned | Enabled | Aligned / enabled | Normal exported record |
| protected_copy | Enabled | Translated / disabled | Exact incoming bytes |
| ordinary_read_off | Disabled | Translated / enabled | Normal exported record |
| aligned_read_off | Disabled | Aligned / enabled | Normal exported record |
| write_off | Enabled | Translated / disabled | All-zero record |

All conditions use the same frozen learned routing. Retain full read/write
bookkeeping, including disabled writers. Copying is an apparatus reference,
not renewal. Write-off's zero outgoing record is the existing disabling
convention; do not export its otherwise available R. With theta identically
zero, an aligned write-off would duplicate the translated path and is omitted.

Final assessment readers are enabled even for serial read-off/write-off
conditions: the question is what the resulting record can now express.
Controls are excluded from the main record/recipient decomposition. Report
them all, including copy minus write-off, and each enabled writer minus its
read-off and write-off references, by family, coupling, replica and block.

No diagnostic shuffle, feedback pulse, intervention selection, rescue grid,
forecast fit or held-out forecasting contest is added here.

## 4. Same judge, plus actual recipient expression

After the third export, read each final packet in two independent fresh bodies:

1. Common reader: canonical context 514240 with coupling 1.0.
2. Native reader: the same context with that lineage's coupling.

Apply the same frozen learned guide before each read and use paired terminal
birth/noise streams. Neither assay body returns to the lineage. The score is
the existing terminal (step 300) qualified own-minus-alternative preference:
the fraction of all 256 sites matching the target sign with abs(V)>0.2 minus
the analogous fraction for the alternative. Keep its denominator and threshold
unchanged, and report absolute scores, not just differences.

The **common-reader score is focal**. It compares retained record utility in
one reference reader, not universal information or exact shape preservation.
The native-reader score is mandatory secondary evidence about expression.
Do not promote it to focal after seeing results. Also retain guide family/
placement, F0 and F3 best-own and own-minus-alternative shape correlation, body
RMS, and clipped-site fraction. Stable labels do not imply exact retained form.

At coupling 1.0, common/native readouts must agree exactly: these are aliases,
not independent observations. With paired terminal streams, protected-copy
common scores are aliases across couplings; write-off common scores are also
aliases. Serial read-off trajectories across A/B are aliases under matched
noise, although their own-minus-alternative scoring changes sign. Audit these
relationships rather than counting condition labels as independent data.

A common-reader interaction concerns records produced by different recipient
dynamics. This design does not localize the effect to reading versus writing:
coupling changes both. It does not test changing hosts between generations.

## 5. Prespecified descriptive analysis

Keep all four groups: A ordinary, A aligned, B ordinary, B aligned. B ordinary
is the focal descriptive group because earlier repetition work found more
future variability there; it is not chosen from this pilot's results.

For each group and common-reader score, y[i,h,r] has 16 records, three couplings
and two replicas. For each replica separately define:

- m[r] = mean over records and couplings.
- a[i,r] = mean over couplings minus m[r].
- b[h,r] = mean over records minus m[r].
- c[i,h,r] = y[i,h,r] - m[r] - a[i,r] - b[h,r].

Report cross-replica products:

- S_record = mean_i(a[i,0] * a[i,1]).
- S_recipient = mean_h(b[h,0] * b[h,1]).
- S_interaction = mean_ih(c[i,h,0] * c[i,h,1]).
- S_total = mean_ih((y[i,h,0]-m[0]) * (y[i,h,1]-m[1])).

The first three sum to the fourth. Their denominators are finite-panel means,
not population variance denominators. Conditional independence of the two
future replicas removes unreplicated zero-mean noise in expectation, not in
each finite realization. These are **signed, noisy descriptive estimates**.
Keep negatives; do not clip them or report a percentage decomposition/noise
ceiling. Report replica-specific nonnegative partitions and absolute means too.

Separately describe rankings for each of the three recipient pairs: Spearman
correlation across records of two-replica means, average ranks for exact ties,
undefined for a constant vector; plus counts of reversed, unchanged and tied
record-pair orderings (120 pairs per 16-record group). A replication-consistent
reversal requires both replicas to agree on ordering at each recipient and
the two recipients to disagree. Preserve ties and nonreplicated reversals.

These correlated pairs are not 120 independent tests. Interaction need not
reverse rankings: recipient-dependent effect sizes can also generate it.
No arbitrary 80% requirement, p-value, population bootstrap interval or
equivalence claim from four donor blocks. Show all four donor-block summaries
and four leave-one-block component recalculations as descriptive sensitivity.
The four lives within a block are not four independent founders.

Repeat the fixed descriptions for native-reader scores, labeled secondary.
No result-selected subgroup, setting, output metric, fit or interaction feature.
This is a small reused-founder development panel, not a prediction validation.

## 6. Denominators, retention and resource gates

| Work item | Count |
| --- | ---: |
| Donor blocks / lives per block / families | 4 / 4 / 2 |
| F0 records | 32 |
| Recipient settings / future replicas | 3 / 2 |
| Main lineages (two enabled writers) | 384 |
| Control lineages (four conditions) | 768 |
| Total labelled lineages | 1,152 |
| Serial readers / writer paths (three generations) | 3,456 / 3,456 |
| Enabled / disabled writer paths | 2,304 / 1,152 |
| Final labelled assays (common plus native) | 2,304 |
| Main comparison scores per family/writer group | 96 |
| Full disposable-block benchmark lineages | 288 |

There are 384 common/native alias pairs at coupling 1.0, plus the control
aliases described above. Labels and repeated assay calls are not new founders.
The two terminal assays can initially both be calculated for audit simplicity;
deduplication, if implemented, must preserve explicit alias metadata.

Save F0/F1/F2/F3 bytes, routes/scores/shifts, reader checkpoints
(0,1,100,101,300), writer checkpoints (0,1,300,1000), terminal checkpoints
(0,1,100,300), context/RNG/reset metadata and all measurements. No entire
step-by-step movie. Retain all cases, including poor or degenerate behavior.
Independent replay and saved-only rechecking are required before interpretation.

Proposed **1 GiB total new-stage storage cap**, including qualification fixtures,
benchmark, main outputs, manifests, logs and audits; keep an additional 4 GiB
free on the data volume. Existing source files are not copied. All numerical
files, receipts and caches stay under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation/L20-extension-1. Only code/docs in this repository.

Use at most six CPUs (affinity 0--5), one numerical thread per worker. First
qualify a complete disposable life, then benchmark one complete **serial**
disposable block at source ID 514240: all four lives, both families, all three
settings, both replicas, all six conditions, both terminal assays, independent
replay, serialization, reload and saved-output checks. No pilot outcome
selection in the disposable stage. Keep disposable artifacts.

Before that block, bound time by 4*checked_life_seconds +
2*source_hash_seconds + 120. Before the four-block pilot, bound time by
4*checked_block_seconds + 2*source_hash_seconds + 180.
Take no parallel speedup credit in either conservative bound.
Bound storage by 4*uncompressed_block_bytes +
retained_qualification_and_benchmark_bytes + 64 MiB.
If it exceeds the cap, stop for a resource/design decision; do not silently
drop controls, checkpoints, records or replicas. These are budgeting rules,
not measured runtime or storage promises.

Any stage forecast above 600 seconds runs detached with a durable log,
single-use run directory, PID/start acknowledgement and no automatic polling,
retry or successor. User requests advance/status checks. No simulation,
benchmark or population run has launched at this design stage.

## 7. Qualification and stopping rules

Before execution, freeze a separate executor and its inputs. Required checks:

- Verify inherited source/guide/F0 hashes; no later source arrays admitted.
- New context adapter changes only coupling; canonical 1.0 matches the old
  disposable baseline under a qualification-only old-stream bridge.
- New independent replay adapter verifies the original base context before
  replacing coupling. Do not relax the old checker's coupling==1 guard or edit
  D140/D141/D177 code/protocols to make the new model pass.
- Verify fixed seeds, paired phase streams, replica separation, generation
  reset, read-to-write continuity, packet-only inheritance and order invariance.
- Route choice remains label-blind; target labels are used only for scoring.
- Check all common/native, copying, zero-output and read-off aliases.
- Independently replay changed-coupling reader and writer paths and measurements.
- Check signed component identities against an independent matrix projection;
  constant, negative, additive and interaction cases; ranking ties/reversals.
- Test bad headers, mutated inputs, nonfinite states, duplicate conditions,
  missing blocks, receipt overwrite refusal and detached cold-start behavior.

Structural or numerical failures stop execution with artifacts retained.
Poor biological-looking performance, small effects, or control overlap are
results, not reasons to discard cases or optimize the grid. Report control
separation and degeneracy explicitly; if a setting cannot support the task,
record an apparatus-limited comparison rather than a portability conclusion.
No automatic larger cohort, extra replicas, dose sweep or predictor fitting.

## 8. Interpretation and next decision

Stable record rankings across this bracket would motivate a later attempt to
predict portable record quality. Reproducible compatibility would motivate
recipient-aware predictions. Mostly unreplicated variation would instead warn
that one realized future is a noisy forecasting target. Two futures cannot
establish that last explanation definitively. A generally favorable recipient
alone is not record-specific compatibility.

Any later predictor still needs matched cheap baselines, whole-founder
development, a frozen fresh test and an observation-budget comparison. Nothing
here rescues D141/D162 uncertainty or D174/D176 negative development findings.
No autonomous repair, complete shape preservation, universal law or biological
validation claim follows. L20 stays STRESS_TESTED / MIXED pending new evidence.

Current next step: implement and qualify this bounded proposal, then obtain a
complete disposable benchmark. The design itself does not launch that work.
