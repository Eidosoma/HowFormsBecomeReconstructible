# E046 — failure chronology

**Complete and independently verified, 7 October 2026 at 17:13 UTC.**
The saved-data workflow took **35.93 seconds**; all 32 blocks,
512 lineages, 16,384 saved rebuilding bodies and **4,522 fixed summaries** were
checked. Artifact closeout passed at **2026-10-07T17:15:19.968812+00:00**. No new trajectory, causal
intervention, active job or automatic successor remains.

The main finding is that a first failed body is often followed by recovery.
Large weakening is usually written after that failed response. The next causal
question is whether changing that early write helps recovery or hinders it.

| Original h32 scattered terminal group | Lineages | Ever a failed rebuilding body | Ever 3 consecutive failures | Final rebuilding body failed | Recovered within 3 after first failure, complete follow-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| All | 512 | 307 | 94 | 74 | 243/281 (86.48%) |
| Terminal success | 428 | 236 | 43 | 12 | 212/221 (95.93%) |
| Terminal failure | 84 | 71 | 51 | 62 | 31/60 (51.67%) |

A recovery means at least one successful subsequent body, not uninterrupted
success thereafter. Six first failures occur at g32 and have no next body;
26 occur after g29 and lack complete three-step follow-up. Next-body recovery
is **174/301 (57.81% [50.69,65.00])**. Among 281 cases with three following bodies,
at least one recovery occurs in **86.48% [81.88,90.84]**. There are 478 observed
failure episodes: 404 end in observed recovery and 74 remain open at g32. Closed
spells are mostly short: 261 last one body, 95 last two. Open spells are censored,
not permanent failures; 205 lineages never have a failed body in this interval.

First failures occur at mean generation **17.07 [16.05,18.12]** among affected
lineages. First failure alone poorly distinguishes the final groups: **236/428**
terminal successes had at least one earlier body failure. Repeated failure is
more associated with the later endpoint: **51/84** terminal failures had a run
of at least three failures, compared with **43/428** terminal successes. The
62 terminal-failure lineages whose final body also fails have an open final spell
averaging **10.69 [7.81,13.80]** bodies; the corresponding 12 terminal-success
lineages average **2.08 [1.50,2.60]**. These are outcome-conditioned descriptions,
not predictive validation or proof of irreversibility.

The event timing gives a sharper lead:

| Event | Strong edges weakened in preceding write | Strong edges weakened after the failed reading |
| --- | ---: | ---: |
| First body failure (307 cases) | 4.11 [2.90,5.36] | 53.80 [47.46,60.59] |
| Start of first three-failure run (94 cases) | 3.97 [2.25,6.08] | 75.84 [61.14,90.77] |

The large current-write change follows the recorded failed body response, so it
cannot cause that already-recorded reading failure. It may still affect later
bodies, beneficially or harmfully. Across all 478 new-failure transitions the
same temporal pattern appears: **4.01** preceding versus **52.26** following
strong weakenings. Recoveries often follow a substantially weakened record;
that observation alone cannot establish that weakening helps recovery.

Physical strong-edge loss at first failure averages **56.60 [55.72,57.50]**, versus
57.35 one generation before. Counts alone do not identify which links matter;
injury location, packet content, birth and noise change across generations.
The plots of three-failure onset necessarily show failed bodies at offsets 0–2:
that persistence is part of the event definition, not an independent finding.
Event-window eligibility changes near the beginning/end of observation.

**Next proposed causal test:** intervene on the outgoing record immediately
after a lineage's first failed rebuild, comparing unchanged, targeted rollback
and equal-count random rollback, then measure the next rebuilding body. The
301 cases with an observed next body provide a baseline that can be reproduced
exactly. This would test whether the early write propagates failure or assists
recovery; it would be a post hoc test on selected onset cases, not a fresh serial
qualification. Freeze the details before running. No such test has started.

Ten inputs froze at **2026-10-07T17:11:32.415735+00:00**. All ten synthetic checks
and the complete independently checked excluded R2 benchmark passed at
**2026-10-07T17:11:46.698756+00:00**. The benchmark took 7.257360s;
the conservative full-analysis forecast was 181.141917s, below
the detached-execution threshold. Both figures were inspected. All 32 body
success means and three h32 terminal means reproduce E042 exactly. Its source
measurements/dynamics retain their prior E041/E042 audit; this analysis newly
verifies chronology, observation masks, event windows, spell counts and summaries.

Closeout verified all **15 benchmark and 77 scientific original outputs**, all
**10 frozen inputs**, source provenance, operational receipts and figure hashes.
Scientific retention is **7,625,035 bytes**, below the
325,580,000-byte reserve-inclusive forecast;
**69,094,125,568 bytes** were available. No original output or frozen
input changed. All intervals are exploratory, pointwise whole-block intervals;
repeated bodies are not independent replicates. E041's finite qualification and
E045's negative late rollback result remain unchanged.

[Report](runs/chronology_v1/REPORT.md), [figure](figures/chronology_v1/chronology.png),
[independent verification](runs/chronology_v1/INDEPENDENT_AUDIT.json),
[artifact closeout](analysis/closeout_v1.json),
[protocol](PROTOCOL.md), [source pins](SOURCE_DATA.json),
[technical checks](analysis/technical_v1.json).

Subsequent user-authorized test: [E047 onset rollback](../E047_onset_rollback/README.md)
completed independent verification on 7 October at 20:24 UTC. Targeted rollback
raised next-body recovery from 174/301 to 193/301, +6.31 points [0.68,12.50],
with 55 rescues and 36 losses; random rollback reached 84/301. The positive
signal did not meet the frozen requirement that the lower bound exceed five
points. Partial restoration is the next proposed lead; no further test has started.
