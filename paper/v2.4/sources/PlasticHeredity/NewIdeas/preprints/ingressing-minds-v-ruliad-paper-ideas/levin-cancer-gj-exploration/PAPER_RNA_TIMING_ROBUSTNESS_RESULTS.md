# P22: RNA identity, communication timing and renewal robustness

Completed **September 28, 2026 at 14:52:38 UTC**, **20 hours 57 minutes
2 seconds** after launch. All **544 cases / 2,944 integrations / 219,181
independent checks / 272 numerical comparisons** pass. Both source histories
agree on every reported comparison. The six stage gates and fresh P21
predecessor checks pass. P22 is complete; no subsequent experiment is running.

The model separates two routes to successful renewal. Preparing the newcomer
through either ZEB protein or the RNA pair withstands both new incoming-cell
sequences and four total replacement cycles. Preparing the surviving neighbour
through its RNA pair works on the historical sequence but fails on both new
sequences. The timing intervention also reveals an alternative route: block
RNA communication only during the first 100 units, then restore it, and the
otherwise failing unprepared assembly retains E through the remaining renewal.
That timing rescue has not received an onward-transmission assay.

The registered design is in [the protocol](PAPER_RNA_TIMING_ROBUSTNESS_PROTOCOL.md).
All state substitutions and schedules were fixed before P22 scientific runs;
later panels were not selected from new outcomes. These are finite, externally
scheduled interventions in a computer model.

## RNA substitutions

The table applies to both written/ordinary histories and both resolutions.
Protein and ions remain at their before-preparation values in these RNA arms.
“Chain” requires final E retention, transmission to fresh recipients under
open coupling, negative RNA-blocked/cut readouts, and inherited capacity/wipe
controls. First-cell behavior is measured on the common 0,15,...,300 grid.

| Location | Prepared RNA state | Final E retention | Qualified chain | First-cell behavior |
|---|---|---|---|---|
| Neither | Neither RNA changed | Fail | Fail | No recovery by 300 |
| Newcomer | miR200 alone | Pass | Pass | Recovery to E |
| Newcomer | Zeb mRNA alone | Pass | Pass | Recovery to E |
| Newcomer | Both RNA totals | Pass | Pass | E at every sampled time |
| Surviving neighbour | miR200 alone | Pass | Pass | Recovery to E |
| Surviving neighbour | Zeb mRNA alone | Fail | Fail | No recovery by 300 |
| Surviving neighbour | Both RNA totals | Pass | Pass | Recovery to E |

Either single RNA-state substitution is sufficient in the newcomer. Neither
is individually necessary when the other prepared RNA state is available.
The pair produces sampled resistance, while either single substitution allows
loss of sampled E followed by recovery. Final rescue and resistance throughout
the first challenge are therefore different outcomes.

In the surviving neighbour, the miR200 substitution is sufficient. Returning
miR200 to its before value while retaining prepared Zeb mRNA loses rescue;
returning Zeb mRNA to before while retaining prepared miR200 does not. This
necessity is scoped to the tested RNA-pair background with unprepared protein
and ions. It does not identify a unique memory molecule or establish miR200
sufficiency across arbitrary cell states. The native transport law already
permits free miR200 transport and excludes direct Zeb mRNA/ZEB transport.

## Communication windows

All 16 segmented-open controls match the corresponding unsegmented controls
on the registered categorical outcomes and full-window observations. Timing
interventions affect the whole three-cell network during the first challenge;
normal coupling resumes afterward. Ionic coupling remains during RNA-only
blocks. Timing parents have retention assays but no onward assays.

The table gives **final E retention**, with identical findings in both
histories/resolutions. Each column changes only the first 300-unit challenge.

| Prepared route | Open | RNA off 0–100 | RNA off 100–200 | RNA off 200–300 | RNA off 0–300 | All coupling off 0–300 |
|---|---|---|---|---|---|---|
| None | Fail | Pass | Fail | Fail | Fail | Fail |
| Newcomer protein | Pass | Pass | Pass | Pass | Fail | Fail |
| Newcomer RNA pair | Pass | Pass | Pass | Pass | Fail | Fail |
| Neighbour RNA pair | Pass | Pass | Fail | Pass | Fail | Fail |

An early, temporary RNA block rescues the otherwise failing all-before group.
It also changes the neighbour-prepared route from sampled recovery to sampled
resistance. Blocking the middle window instead abolishes the neighbour route's
recovery and final retention. A late block preserves that route's recovery.
These contrasts identify dependence on the tested communication windows;
they do not establish an exact switching time or a particular sending edge.

Blocking RNA for all 300 units, or isolating the trio for all 300, keeps the
first newcomer E at every common sample for every route. Nevertheless, every
one of those groups fails later final retention. Protection of the first
newcomer during this challenge is insufficient to sustain the subsequent
replacement process. The early-block rescue depends on the tested schedule
that restores communication; permanently suppressing communication is not
supported as a rescue by these results.

## New incoming sequences and longer renewal

Five remaining replacements complete two total cycles; eleven complete four,
including the first archived replacement at the fork. The preparation
intervention occurs once. Later incoming cells receive no prepared components.
Each entry below gives both **final retention and qualified onward chain**;
the two outcomes agree for every condition shown. Histories/resolutions agree.

| Route | Historical, 2 cycles | Historical, 4 cycles | Seed 17021, 2 cycles | Seed 17021, 4 cycles | Seed 17022, 2 cycles | Seed 17022, 4 cycles |
|---|---|---|---|---|---|---|
| None | Fail | Fail | Fail | Fail | Fail | Fail |
| Newcomer protein | Pass | Pass | Pass | Pass | Pass | Pass |
| Newcomer RNA pair | Pass | Pass | Pass | Pass | Pass | Pass |
| Neighbour RNA pair | Pass | Pass | Fail | Fail | Fail | Fail |

The newcomer protein and RNA-pair routes retain their protection across all
registered draw/length combinations. The neighbour route withstands extra
cycles on the historical sequence but fails under both new sequences, already
showing no first-cell E recovery by the end of the first challenge. Its failure
under these sequences is not solely a consequence of the longer schedule.
The single-RNA substitutions were not included in this robustness panel.

Incoming variation changes only stock-M ZEB protein, within ±25%. At the first
new replacement, the historical draw is −12%, versus +13% and +9% for the new
sequences. Those observations motivate a first-incoming-protein comparison,
but P22 does not isolate every draw position or establish a dose threshold.
There are two held-out sequences and one source per history/resolution, not
independent biological replicates or a population success-rate estimate.

## Coverage and limits

| Parent panel | Parents | Final E retention | Passed every replacement-window E criterion |
|---|---:|---:|---:|
| Replay | 16 | 12 | 0 |
| Single RNA | 16 | 12 | 0 |
| Timing controls | 16 | 12 | 0 |
| Timing interventions | 80 | 36 | 0 |
| Robustness | 80 | 44 | 0 |

Every one of the 112 non-timing parents, including failures, receives all
three readouts. **68/112 open readouts transmit E; 0/112 RNA-blocked and 0/112
cut readouts do.** Exactly the same 68 assayed parents retain E. These counts
include paired numerical runs and related interventions, so they are not
independent replicate success rates. All 208 parents replace their original
carriers, but none meets the stricter every-replacement-window E criterion.

The outcomes support conditional renewal and onward transmission within this
model. They do not establish autonomous reproduction, cell division, an
acquired-history advantage, a unique molecular carrier, or biological cancer
control. Written and ordinary histories remain indistinguishable on the
registered categorical comparisons.

## Evidence and closeout

Both software gates pass: 55 tests before launch (408.243 s), and 55 against
frozen source (412.690 s). Frozen-suite SHA-256:
`69ccb0cfb8deff28df606aa180f17b203b78d07812d25b86913587444dc78a4a`.
The initial prelaunch software-path error remains documented separately;
it preceded scientific execution and affected no completed historical run.

Job:
`/mnt/workspaces/levin-cancer-gj-exploration/p22-rna-timing-robustness/jobs/p22-20260927T175518Z-24c3dtmy`.
Run:
`/mnt/workspaces/levin-cancer-gj-exploration/p22-rna-timing-robustness/runs/p22-20260927T180252Z-fpod_fmq`.
Final audit SHA-256:
`6e0b92f4b6942359bf96571232c242333cf61f9fe6b7d2558ebb3b96bc696be0`.

The [September 28 closeout](storage/p22-completion-integrity-20260928.json)
passes all twelve completion checks and all ten provenance flags. It verifies
544 result files, 2,944 raw phases and 416 assembly files, together with 218
execution sources, 14,781 registered inputs and saved stage/audit/log evidence.
This verifies the completed mathematical audit's evidence without rerunning
that hours-long audit or any integration. External free space is about
5.80 GiB. Executed sources, configuration, draws and protocol remain frozen.
The terminal heartbeat is expected to stop; no relaunch is needed.

The clearest subsequent question is whether the early-block rescue also
transmits onward and survives new incoming sequences. A complementary question
is whether changing only the first incoming protein draw explains the fragile
neighbour route. These are follow-up proposals, not registered or launched
experiments.
