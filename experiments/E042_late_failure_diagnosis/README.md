# E042 — late failures preserve some usable capacity

**Complete and independently verified.** Exploratory diagnosis of all 32 E041
blocks / 512 lineages, eleven record policies, nine active bodies, 32 boundaries
and seven terminal horizons. No new trajectories or causal repair outcomes were
generated. The workflow finished **5 October 2026 at 12:59:19 UTC** in **127.94s**;
artifact closeout passed at **13:03:45 UTC**. The follow-up receiving intervention
[E043](../E043_late_reader_timing/README.md) completed independent verification
at **18:58 UTC**. The fixed delayed-reader schedule produced no established
overall benefit: 17 rescues and 14 losses, a net h32 gain of only 0.59 points.

Full bridge rewriting has **84/512** failures in the h32 scattered-terminal test.
Of those, **30/84 (35.71%) [23.53%,48.81%]** succeed with the exact same record
in an intact terminal test; 27 succeed under square injury, all within those 30.
The other **54/84** fail all three saved terminal contexts. Those failures do not
prove that no usable information remains. Injury, birth and noise differ between
contexts; this comparison is a capacity witness, not an isolated causal injury test.

All **84/84** failed full-rewriting records still connect every output to the
source through nonzero edges after the actual scattered test injury; **57/84
(67.86%) [52.69%,82.28%]** do so using only |weight|>0.5 edges. Thus simple
nonzero disconnection does not describe these failures. These undirected graph
measures omit signs and actual weight magnitudes; connectivity does not establish
that the stored routing information is correct or sufficient.

| h32 scattered-terminal outcome | Bridge preservation | Full bridge rewriting |
| --- | --- | --- |
| Both cues correct | 372/512 | 428/512 |
| At least one output strongly fixed to one sign under both cues | 137/512 | 34/512 |
| Both cues fully reversed | 0/512 | 3/512 |
| Other failures | 3/512 | 47/512 |
| Failed cases that succeed in another saved terminal context | 33/140 | 30/84 |
| Failed cases with all outputs connected through nonzero edges | 140/140 | 84/84 |
| Failed cases with all outputs connected through strong edges | 24/140 | 57/84 |

Preservation's failures are overwhelmingly locked outputs: **137/140 (97.86%)**.
Full rewriting has **34/84 (40.48%)** locked, **3/84** fully reversed and **47/84**
other failures. The last category is a remainder, not evidence for a single weak-signal
mechanism. Under intact receiving, full rewriting's 54 failures comprise seven
locked, three reversed and 44 other cases. Output labels describe saved responses,
not proven attractors. E041 establishes the policy benefit; this reused-case
classification does not by itself establish its mechanism.

Repair continues. At generation32 both bridge policies restore **37,604 of 37,932
returning connections (99.14%) [99.02%,99.24%]** to a nonzero value; none are
immediately strong. Among 30,862 available weak connections that returned in the
preceding body, full rewriting promotes **20,315 (65.83%) [63.97%,67.65%]** to
strong versus **17,053 (55.26%) [53.01%,57.54%]** for preservation. These are
repeated connection observations, with uncertainty resampling complete blocks.
They support continued repair and maturation rather than a complete loss of
reconnection capacity; the conditional comparison is descriptive.

Full rewriting's g32 outgoing packets average **312.52 strong edges** versus
296.48 for preservation. Failed rewriting cases average 294.10 versus 316.13 in
successful cases. Their latest rewrite weakens 11.92 previously strong available
edges versus 3.19 in successes, while weak promotions are similar (59.11 versus
59.92). These associations cannot establish whether weakening causes failure or
reflects an already unsuccessful reading body. Sign changes from acquisition
are similar overall (204.17 versus 203.70), and need not be functionally wrong.

Some failed challenges are followed by working bodies. Of full-rewriting records
that fail a scattered terminal assay, the next rebuilding body succeeds for
**12/26 at h8**, **23/44 at h16**, and **11/52 at h24**. At h32 no later body was
saved: follow-up is missing, not zero success. Only **205/512** rewriting lineages
have no observed body failure throughout all 32 challenges, despite 438/512 bodies
succeeding at g32. First failures can be followed by recovery under fresh damage,
birth and noise; this is not an irreversible survival process.

**Follow-up test:** hold the late E041 records fixed and compare the original reader,
extra total reading time, and extra cue-settling before amplification with the
same total time as that control. This would isolate a reader-timing intervention
and test accessible capacity without altering record contents. Baseline outcomes
must reproduce E041; all cases and controls stay included. It would be a causal
assay on reused records, with a separately frozen design, not a fresh serial
confirmation or proof of an indefinitely durable repair. That comparison is
complete and independently verified as [E043](../E043_late_reader_timing/README.md),
including all 512 lineages at h24 and h32 and paired counts of rescues and losses.
Its timing improvement criterion failed; this does not show that all remaining
information is absent or that every possible receiving intervention would fail.

Eight synthetic checks passed, including physical injury masks, tiny edges,
conditional ratios, appended body/policy indexing and missing h32 follow-up.
Every packet/repair count, graph, output class, history and joint witness was
independently checked; all E041 body/terminal success means reproduced exactly.
All **13,483 summaries** and whole-block intervals were independently recalculated.
E042 uses its own exploratory bootstrap namespace; its intervals do not replace
E041's frozen inference. Both figures were inspected.

Artifact closeout verified all **17 benchmark and 79 scientific original outputs**,
all **12 frozen inputs**, source provenance, operational receipts and figure
hashes. Scientific retention is **32,660,509 bytes**, below the 855,770,912-byte
forecast including reserve. All parent experiments and preprints remain unchanged
apart from links in writable experiment documentation.

- [Detailed report](runs/diagnosis_v1/REPORT.md)
- [All statistics and definitions](runs/diagnosis_v1/summary.json)
- [Figure](figures/diagnosis_v1/diagnosis.png)
- [Independent verification](runs/diagnosis_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
- [Frozen protocol](PROTOCOL.md)
- [Pinned evidence](SOURCE_DATA.json)
- [Technical validation](analysis/technical_v1.json)
- [Forecast](analysis/forecast_v1.json)
- [Completed job status](jobs/diagnosis_v1/status.json)
- [Confirmed E041 results](../E041_full_rewrite_confirmation/README.md)
