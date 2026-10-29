# H1 handover rescue: completed result

2026-09-06. Completed and independently audited at 21:57:34 UTC.
Run: `runs/handover-rescue-20260906T212435Z-du3ovank`.
Job: `runs/jobs/handover-rescue-20260906T212435Z-534ztvu6`.

## Plain-language result

Giving one carrier more time or changing its communication strength did not
rescue onward M transmission anywhere in this fixed panel. Two carriers
succeeded at normal communication strength, but not at the weaker setting.
Keeping a state in isolation and successfully passing it onward are different
requirements.

There is an important wrinkle: during some failed handovers, the original
M donor itself becomes E. The interaction is reciprocal; the donor can change
as well as the intended recipient. Whether that changed original donor now
holds a persistent, transmissible E state requires the separate H2 experiment.

## Fixed panel and all outcomes

Three backgrounds: the protein-stabilized acquired-state route, the
RNA-stabilized acquired-state route, and ordinary prepared M. Each starts from
its audited held checkpoint, before any H1 handover. All seven settings are
repeated with finer numerics for both acquired routes.

| Setting | Active donors | Each contact's nominal duration | miRNA Kd | Renewed M through both rounds, all three backgrounds |
| --- | --- | --- | --- | --- |
| Pair, normal | 2 | 1000 | 2e-15 | Yes |
| Single, normal | 1 | 1000 | 2e-15 | No |
| Single, longer | 1 | 2000 | 2e-15 | No |
| Single, longest | 1 | 4000 | 2e-15 | No |
| Single, stronger | 1 | 1000 | 4e-15 | No |
| Single, weaker | 1 | 1000 | 1e-15 | No |
| Pair, weaker | 2 | 1000 | 1e-15 | No |

Every tested fine outcome and donor/recipient endpoint label agrees with its
baseline counterpart. Across 35 executions, five succeed (three baseline pair
cases plus their two fine repeats), and thirty fail. These are conditions and
numerical comparisons, not 35 independent biological replicates.

All failures first fail strict M transmission in round 4, the first new H1
handover. None becomes a successful delayed-only M relay after settling.
Actual resulting recipients, including failures, still enter round 5.

## What happened to the donors?

For both acquired routes, the normal single donor is M after its first
encounter but E after the second. The longer and longest single-donor
encounters have the same endpoint-label sequence. Stronger single-donor
communication produces E already after the first encounter.

By contrast, the weakly communicating single donor remains M at both
contact endpoints, but does not successfully instruct the fresh E targets.
Weakly communicating pairs likewise retain M labels while failing to write M.
Normal pairs keep M and successfully write it.

Ordinary single M donors remain M-labelled at the two contact endpoints for
normal/longer/longest duration; stronger communication changes them to E.
This background difference is not evidence for an extra hidden memory:
the complete starting states differ, even when their coarse labels match.

Thus a failed handover can involve insufficient influence on the recipient,
a changed donor, or both. Prior isolated retention does not imply resistance
to every subsequent contact. Fresh E targets staying E is not independent
evidence that a donor transmitted E to them.

## Audit, resources and limits

- All 35 cases are execution-valid; no retries.
- All 12,189 independent saved-data checks pass.
- Original, copied, frozen, executed-file and predecessor-audit hashes pass.
- All eight unchanged historical controls reproduce round arrays bitwise.
- All fourteen fine comparisons agree in outcomes and endpoint labels.
- 770 new integrations; 186,843 snapshots.
- 140 fresh recipients; 70 complete pair replacements; 70 initial placements.
- 50 removed carriers; no new priming cues or initial holds.
- Runner elapsed: 1971.211 seconds, about 32.9 minutes.
- Integration CPU: 3833.570 seconds.
- All recipients locally recover around their own final state, including
  negative E outcomes; maximum normalized recovery distance: 9.589739e-6.

The downstream-design gate is true because the data, provenance, controls and
numerics pass, not because a single-carrier rescue was found.

Matching nominal donor-contact time or Kd-time did not match outcomes.
Those quantities are not measured molecular delivery or energetic costs.
This finite grid does not prove a universal two-cell minimum or that no
other one-cell protocol could succeed. Ordinary M shares the transmission
limitation; no special fitness advantage of an acquired history was shown.

These remain externally arranged fixed-model relays, not autonomous
reproduction, new attractors, new physical laws or wet-lab heredity.

## Next experiment

[REWRITE_TRADEOFF_PROTOCOL.md](REWRITE_TRADEOFF_PROTOCOL.md) uses H1's reciprocal
contact finding to ask whether a smaller original M group is easier to rewrite
toward E. It retains the original incumbent, removes all cues, and tests that
incumbent on fresh M recipients. Both exposure widths then use the same
one-carrier readout. This H1-informed exploration is not independent
confirmation of a hypothesis selected from H1.

Launch and polling: [RUNNING.md, section 26](RUNNING.md#26-h2-rewriting-context-and-common-readout).

