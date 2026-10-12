# L22: fresh-parent writing replication, v1

D073, approved by the user's “let's go” on 2026-09-08. Fixed before new
scientific parent or readout futures. Run `l22_fresh_writing_replication_v1_attempt1`.

## Question and unchanged scope

D072 independently confirmed greater reading reliability for outcome-known
D071 records: .917480 live-written versus .866943 damaged, improving all
sixteen retained tissues. Fixed-reader-written theta gave .904785; extra
live feedback missed the twelve-positive-tissue rule. Test whether **fresh
parent acquisition and writing on new tissues** reproduce useful records,
using the same sixteen-readout instrument and the same three comparisons.

Use sixteen new tissue indices **30024–30039**, four fixed balanced half-plane
messages and four paired parent replicates per message. A pre-registration
search found no overlap in this workspace's existing run manifests or
per-tissue output directories. Check that reservation again before preparing
the run. No parent filtering, replacement tissues, selected records or
historical outcomes enter the new scientific estimates. Prior runs are
verified provenance, not sources of scientific packets.

Retain the original rulebook distribution, D070/D071 parent, fission, damage,
recovery and one-readout RNG namespace `l22-source-recovery-v1:{tissue}:{phase}`.
New tissue indices give new streams. Retain D072's new-readout namespace
`l22-fixed-record-readout-v1:{tissue}:{phase}`, with phases `assay_birth` and
`assay`, sixteen draws, and fixed message/parent/draw ordering. No changes to
noise, norm, writer, comparator, reader strength or topology distribution.
No DoorKey, PX, threshold sweep or multigeneration study is included.

## Fresh acquisition and all original writing controls

Call the frozen D071 experiment with native configuration: four replicates,
120 settle/1000 imprint sweeps, one half-body fission, correlation-.3
norm-matched theta damage, then 1000 recovery sweeps. Theta std=.3, theta
write rate=.001, native rho=.002 and comparator=.2. Keep its ten recovery
conditions: loop, writer_off, theta_read_off, reference_write_off,
fixed_damaged_reader, scrambled_loop, scrambled_fixed_reader, body_writer_off,
wrong_fixed_reader and the separately labelled intact-reference backup.
All non-backup conditions start with R exactly zero. R can be written later.

Retain the original parent-preparation/native-backup anchors, loop/fixed full
replays, common boundary/damage, wrong-reference routing, body/trace aliases,
and loop/fixed first-step equality. Retain all 26 raw D071-format artifacts,
including 0/1/50/250/500/1000 states and per-step normalized-writing observer
traces, plus its full thirteen one-readout assays. These single-readout
results and auxiliary recovery controls are diagnostics and integrity
checks, **not additional primary hypothesis tests**.

Newly written theta must come only from this run's own saved writing cell.
Save a 27-entry writing manifest covering the 26 NPZs and experiment JSON,
verify it before and after readout, and check the four packet byte hashes
against the current writing result. No previous-run parent or theta can be
loaded as a scientific input. Native writer-off theta must be exactly the
same as the damaged packet; each original readout is retained.

## Calibration before any scientific parents

First qualify **both** the legacy one-readout instrument and the sixteen-draw
instrument on all sixteen tissues, using their unchanged frozen calibration
functions. Each aligned-theta instrument must score >.25 on every tissue and
have equal-tissue mean >=.75. Off controls must be exactly .25 and message-
independent, and positive replays must be exact. If either instrument fails,
stop before parent preparation. Structural failures invalidate the attempt;
do not replace seeds, repair failed scientific output or alter criteria.

After calibration, acquire/write all sixteen tissue cells, then run their
multi-readout assays. Preserve this stage order and all intermediate data.
Positive interpretation also requires sixteen-draw parent-theta readout
>.25 in every tissue and equal-tissue mean >=.75. A weak legacy one-readout
parent score is diagnostic, not a second outcome-selected eligibility gate.

## Unchanged theta-only readout

Use D072's frozen six-arm readout: damaged, fixed-reader-written, live-loop-
written, pre-damage parent, cyclic wrong-donor live theta, and live theta
with the reader off. Each original record is copied into sixteen fresh
centered .2-Gaussian bodies. Only 256 float64 theta entries (2048 bytes per
world) pass; V/EMA/R and fixed recovery-reader copies do not. Hold theta,
R=0, reference comparison/R writing off, 1000 native sweeps, matched random
streams across arms/messages, independent marginal parent/draw streams.

Retain full readout states 0/1/1000, final per-draw observers, packet hashes,
RNG digests, full live replay, exact wrong-donor permutation and reader-off
aliases. Four legacy-wrapper replays must exactly match the single-readout
states just generated in the same fresh writing cell. The reused D072
helper's `four_historical_readout_anchors` key means implementation concordance
here, **not replay of old D071 data**. Legacy draws are excluded from new
readout estimates. No rewriting occurs during the readouts.

## Three fixed functional comparisons

At sweep 1000, average sixteen readouts per original record, then all sixteen
records per tissue, with equal tissue weights. Compare:

1. live-loop-written minus damaged;
2. fixed-reader-written minus damaged;
3. live-loop-written minus fixed-reader-written.

Use 10,000 paired whole-tissue bootstrap draws, seeds **20260908097301–303**,
quantiles **.05/6 and 1-.05/6**, and both a strictly positive lower endpoint
and at least **12/16 positive tissue differences** for each comparison.
Do not pool D070–D072 or treat 4096 readouts per arm as independent tissue
evidence. Report all three unchanged, including positive averages that fail
the consistency requirement.

Conditional on structural, calibration and parent readability qualification:

- Neither writing-versus-damaged comparison qualifies:
  `NO_QUALIFIED_FRESH_WRITING_BENEFIT`.
- Fixed-versus-damaged qualifies, live-versus-damaged does not:
  `FIXED_READER_WRITING_REPLICATION_ONLY`.
- Live-versus-damaged qualifies, extra live-versus-fixed does not:
  `FRESH_WRITING_RELIABILITY_REPLICATED`.
- Live-versus-damaged and extra live-versus-fixed qualify:
  `FRESH_FEEDBACK_RELIABILITY_REPLICATED`.

Retain D072's descriptive per-record accuracy/variance decomposition,
always-correct/incorrect/varying counts, paired corrected/worsened draws,
confusions, margins, sign/amplitude fidelity and body means/norms. Retain all
D071 auxiliary writer/source metrics descriptively. None replaces a failed
primary, identifies a universal mechanism or demonstrates long-horizon
renewal. Earlier labels and failed criteria remain unchanged; no automatic
numbered-law verdict upgrade.

## Independent verification and resources

Use unchanged frozen dynamics and readout helpers with local contexts, never
patched globals. A new auditor composes the independent D071 saved-writing
checker and D072 saved-readout checker, independently cross-checks all new
packets against this run's writing data, then independently computes the
new panel's bootstrap comparisons and fixed labels. It performs no new
dynamics and does not claim to reconstruct unsaved spatial movies. Freeze
new code/protocol/launcher/auditor/tests and the complete D072 provenance
chain plus its final review before scientific futures. Strict JSON, unique
run IDs, exclusive locks and complete input/output manifests are required.

Counts for a qualified run: 256 fresh parent lives; 2560 recovery lives;
3328 legacy diagnostic readouts; 768 legacy calibration lives including
replay; 1024 writing integrity lives including source anchors/replays;
24,576 primary readouts; 12,288 new calibration lives including replay;
4096 live-readout replay lives; 1024 legacy-wrapper replay lives. Total
**49,920 lives**, not independent samples. All sixteen writing cells must
finish before new readout jobs; do not resume a failed immutable attempt.

All data, JSON, logs, bytecode, test temporaries and outputs stay under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation`. Only code/docs here.
At most four logical CPUs/workers and one numerical thread, pinned Python
3.13 / NumPy 2.5.2. Reserve 2 GiB output plus 1 GiB free margin.

Benchmark disposable tissue **400100**, two parents/message, two readout
draws and 32 settle/imprint/recovery/readout sweeps. Separately time (a)
legacy calibration plus the entire writing cell, and (b) new calibration
plus the entire new readout cell, with synthetic/current disposable packets
only. For benchmark only, the four original-assay wrapper checks can be
recomputed in memory. Fixed conservative projection in seconds:
**writing_seconds × 437.5 + readout_seconds × 3500 + 60**. The factors are
(4/2), (1000/32), ceil(16/4), and 1.75, with (16/2) additionally applied to
the readout component. This conservatively also scales its smaller legacy
component. Report timing/gates, not benchmark effect sizes.

Above **600 seconds**, detach, hand off PID/log/status and stop without
polling until the user returns. Otherwise finish foreground. Separately
benchmark the independent saved-array audit on fixed tissue **30024**;
project elapsed × 16 × 1.5 + 60 with the same detach/no-poll rule. No later
study is automatically authorized.
