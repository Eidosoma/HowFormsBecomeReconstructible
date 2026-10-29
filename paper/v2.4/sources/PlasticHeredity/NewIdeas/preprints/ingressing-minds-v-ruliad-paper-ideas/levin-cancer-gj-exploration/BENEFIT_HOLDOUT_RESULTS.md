# H4b — Longer held-out histories: conditional usefulness and a simple explanation

Completed 2026-09-09 at 04:56:09 UTC, after 19 h 55 min.
All 144 cases completed; the independent audit passed 423,639 checks,
the eight historical controls, and all eight selected fine comparisons.

Run: runs/benefit-holdout-20260908T090054Z-smh0zfm8.
Job: runs/jobs/benefit-holdout-20260908T090054Z-xznoprh5.
Source: the run's independent_audit.json.
Design: [BENEFIT_HOLDOUT_PROTOCOL.md](BENEFIT_HOLDOUT_PROTOCOL.md).

## Primary state-match scores

Means over epochs 2–12, four new schedules and paired E/M founders, before
any assigned contact-cost penalties:

| Environment | Rewritable inheritance | Inheritance only | Cue only | Neither |
| --- | ---: | ---: | ---: | ---: |
| Slow, reliable | .931818 | .681818 | .795455 | .5 |
| Fast, reliable | .727273 | .477273 | .795455 | .5 |
| Slow, sparse cues | .772727 | .681818 | .579545 | .5 |
| Slow, noisy cues | .818182 | .681818 | .681818 | .5 |

Relative to cue-only, rewritable inheritance wins in all four slow/reliable
histories, loses in three and ties in one fast history, wins in three and
loses in one sparse-cue history, and wins in all four noisy-cue histories.
Against inheritance-only, noisy updating wins in two histories and loses in
two; the mean advantage is not an across-history dominance claim.

Inherited information bridges missing observations when environmental states
are persistent, but can be stale when states change rapidly. Noisy-cue success
does not show bad-cue detection: all five realized erroneous cue events
(ten when counting the two founder polarities) produced wrong final states
in the rewritable policy at those events.

## Costs and explanatory limit

Mean parent-contact cost break-even versus cue-only is .136364 in the
slow/reliable and slow/noisy profiles, .193182 in slow/sparse, and -.068182
in fast/reliable. These are dimensionless penalties in the specified utility
formula, not measured energy or fitness. A negative boundary means no
nonnegative added parent cost can produce a mean advantage in that comparison.
The complete 64-point grids and per-history boundaries remain in the audit.

The prespecified binary reference agrees with the native cell labels at
ALL 6,592 compared pair-checkpoints across the 144 cases. No fitting was
performed. Thus the measured two-state outcomes need no richer explanation
than copying the previous state and replacing it with an available cue.
This does not establish equality of the continuous molecular mechanisms,
and it does not negate the physical transfer/retention shown by the model.

## Scope of the conclusion

This is a bounded, externally supplied state-matching assay. Four random
streams are not a population-scale study; founder polarities, numerical
refinements and benchmark controls are not extra independent environments.
It does not measure survival, growth, ATP, cell division, autonomous renewal,
new attractors or wet-lab efficacy.

The next user-requested direction is closer to the original paper:
[P1 population competition, removal and memory](PAPER_MEMORY_PROTOCOL.md).
It restores native voltage and junction-expression mechanisms in a cellular
neighbourhood and removes the artificial target-state task. It does not
automatically start H5 or a full 3D replication.
