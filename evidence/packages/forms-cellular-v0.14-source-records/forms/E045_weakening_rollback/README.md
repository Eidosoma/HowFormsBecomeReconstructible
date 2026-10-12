# E045 — targeted rollback of last-write weakening

**Complete and independently verified, 7 October 2026 at 11:51 UTC.**
**The predefined targeted rollback benefit was not established.** All 512 existing
E041 lineages were retained. Independent reconstruction of every edit and replay
of all 258,048 individual-cue scores passed. Artifact closeout passed at
**2026-10-07T16:35:10.917783+00:00**. No active job or automatic successor remains.

In simple terms, undoing the latest weakening was not a useful general fix under
this test. It rescued four scattered-injury failures but caused two successes to
fail. The earlier association between weakening and persistent failure does not
translate into a substantial benefit from this final-step intervention.

| h32 normalized receiver | Unchanged | Targeted rollback | Random rollback |
| --- | ---: | ---: | ---: |
| Scattered injury, both cues | 428/512 (83.59%) | 430/512 (83.98%) | 426/512 (83.20%) |
| Intact | 458/512 (89.45%) | 452/512 (88.28%) | 453/512 (88.48%) |
| Square injury | 454/512 (88.67%) | 456/512 (89.06%) | 452/512 (88.28%) |

The primary h32 scattered targeted-minus-original gain is **+0.39 percentage
points [−0.59, +1.37]**, failing the required lower bound above five points.
Targeted-minus-random is **+0.78 [−0.20, +1.76]**, failing the required lower bound
above zero. Both were required. At h24, scattered success is **89.84% unchanged,
89.45% targeted and 89.06% random**. This earlier secondary horizon also shows no
observed improvement over unchanged records.

At h32, targeted versus original retains 426 successes and 80 failures, rescues
four and loses two. Versus random rollback it rescues six and loses two, with
424 shared successes and 80 shared failures. In the intact h32 test targeted
rollback loses six successes and rescues none. All normalized variants/horizons
still pass the 24 original context gates; targeted h32 scattered absolute
both-cue reliability has a lower bound of 81.05%, above 75%. These absolute
checks are separate from the failed improvement criterion.

The intervention changes **163/512 lineages** at h32 and restores **2,365
coordinates** in each rollback variant. Random selection overlaps **534** targeted
coordinates. At h24, 148 lineages change, with 2,363 coordinates per intervention
and 457 overlapping selections. All physically erased edges and incoming weak/
zero coordinates, including new repairs, remain unchanged. The random pool
includes the target and matches count, not absolute strength gain or sign change.
Restoring incoming values changes sign and magnitude together. Original receiving
means reproduce E041 bit for bit; the new bootstrap intervals do not replace
E041's original inference.

This is a post hoc final-packet intervention on existing histories. It does not
rule out accumulated earlier writing damage, loss of cue information, or other
repair mechanisms. E041's qualified 32-renewal result and E043's failed timing
criterion remain unchanged. The next proposed lead is to trace the onset of
persistent body-reading failures across saved earlier generations, then use that
chronology to select a separately frozen causal test. No such follow-up has started.

Twenty-one inputs froze before any new trajectories. Twelve excluded checks,
the complete fixture and the benchmark passed, including independent replay and
corrupted-evidence rejection. Scientific simulation took **55m29s**, independent
replay **52m24s**, total workflow **1h47m57s**. The run finished about an hour before
the 12:52 UTC benchmark estimate. Artifact closeout verified all **31 fixture,
31 benchmark and 248 scientific original outputs**, all 21 frozen inputs, source
provenance, operational receipts and figure hashes. The scientific figure was
visually inspected. Scientific retention is **21,137,861 bytes**, below
the 265,889,408-byte reserve-inclusive forecast;
**69,113,208,832 bytes** were available at closeout. No original output
or frozen input changed, and closeout ran no new trajectories.

[Full report](runs/rollback_v1/REPORT.md),
[independent replay](runs/rollback_v1/INDEPENDENT_AUDIT.json),
[figure](figures/rollback_v1/rollback.png),
[artifact closeout](analysis/closeout_v1.json),
[protocol](PROTOCOL.md), [pinned sources](SOURCE_DATA.json),
[technical validation](analysis/technical_v1.json),
[benchmark forecast](analysis/forecast_v1.json),
[verified launch](analysis/scientific_launch_verification_v1.json).

Follow-up, **7 October 2026**: [E046](../E046_failure_chronology/README.md) completed the saved failure chronology. Most first failures recover within three observed rebuilds; the large weakening burst is written after the first failed response. The proposed next intervention moves rollback to that onset and tests the next body. No new causal test has started.
