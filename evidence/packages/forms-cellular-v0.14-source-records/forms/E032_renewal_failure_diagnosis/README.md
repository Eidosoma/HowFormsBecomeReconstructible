# E032 — what deteriorates during repeated rebuilding?

**Complete and independently verified.** Exploratory analysis of the same
32 E031 blocks and 512 lineages; no new trajectories were simulated.

The strong-connection count settles near 318 rather than continuing to vanish.
At generation 16, physical injury removes 56.27 strong edges per lineage and
refreshing creates 56.40. All output cells remain reachable from the source
through strong connections in 87.89% of candidate records, versus 14.84% under
full rewriting. These graphs omit signs and weak edges and are diagnostic,
not models of the actual reader.

Despite that retained connectivity, many outputs stop switching sign with the
cue. At generation 16, **333/512 (65.04%)** scattered-terminal cases have at
least one output strongly stuck on one sign under both cues: **333/398 failed
cases (83.67%)**. There are 114 both-correct cases, 14 fully reversed and 51 other
failures. The current renewal body shows the same kind of failure in 313/512
cases. This describes measured outputs, not a proven dynamical attractor.

Connection signs drift: candidate packets average 193.04 nonzero edges with
signs different from the acquired record at generation 16, versus 153.68 at generation 8.
However, successful and failed generation 16 bodies both average about 193
changed signs. Sign counts alone do not explain which cases fail, and a sign
change need not be functionally incorrect. Successful body performance can
recover after earlier failure; only 9/512 lineages have no observed body failure
through generation 16, although 148/512 bodies succeed at generation 16.

[E033](../E033_delayed_expression/README.md) completed independent verification
on 27 September at 19:48 UTC. Delayed amplification with unchanged packets
raises h16 normalized scattered success from 22.27% to 36.72%, passing its
matched-time improvement criterion while still failing absolute reliability.
[E034](../E034_settled_rebuilding/README.md) found that the timing change during
one renewal improves next-record success by 6.05 points [3.12, 8.98], missing its
predefined lower-bound-above-five criterion. Neither expression recovery
nor a one-boundary benefit establishes successful long-term serial maintenance.

Five arithmetic/graph/history checks passed. The excluded benchmark took 9.35s,
forecasting 120.03s. The all-case analysis and independent verification completed
in 85.02s: extraction 17.87s and independent measurement replay 24.19s. All 8,090
pointwise summaries, per-block numerators/denominators and source E031 score
means were verified. Closeout passed on 27 September at 16:33:45 UTC, checking
all 14 benchmark and 45 scientific original outputs, 10 frozen inputs and figures.
No previous scientific inputs or evidence changed; approximately 796MB was free.

- [Detailed report](runs/diagnosis_v1/REPORT.md)
- [Full statistics](runs/diagnosis_v1/summary.json)
- [Figure](figures/diagnosis_v1/diagnosis.png)
- [Independent verification](runs/diagnosis_v1/INDEPENDENT_AUDIT.json)
- [Closeout](analysis/closeout_v1.json)
- [Frozen diagnostic protocol](PROTOCOL.md)
