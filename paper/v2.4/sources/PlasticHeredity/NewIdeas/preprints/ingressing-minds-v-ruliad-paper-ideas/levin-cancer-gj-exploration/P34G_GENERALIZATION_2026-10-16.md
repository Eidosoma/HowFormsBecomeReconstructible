# P34G sequence generalization launched

P34G started at **12:28:42 UTC on October 16, 2026**. All **23 prelaunch
software checks passed**, the inherited-prefix audit passed, and six native
simulation workers are running the new sequence preparations. Startup review
confirmed advancing worker CPU time and one numerical-library thread per
worker. There are no new scientific outcomes yet.

The planning estimate is **9.8–14.7 hours**, approximately **22:16 UTC on
October 16 through 03:09 UTC on October 17**. The absolute 16-hour cutoff is
**04:28:42 UTC on October 17**; simulations stop at **03:43:42 UTC** to leave
45 minutes for auditing. Each case also has a six-hour cap. A failed gate,
worker error, exhausted budget or less than 5 GiB free stops the attempt,
preserving partial results. There is no automatic retry or extension.

P34T established two successful component rescue routes in one known sequence.
P34G asks whether protein-only and RNA-plus-ion substitution also support
recovery and subsequent transmission under **two new incoming-cell sequences**.
It includes the refreshed open-state and full-pause-state comparisons, plus
protein-only readouts with donor–recipient connections cut. Every parent gets
its readout, even when retention fails.

| Factor | Registered choice |
|---|---|
| New sequence seeds | 34001 and 34002, fixed before scientific outcomes |
| Incoming variation | Stock-M ZEB protein changes from -25% to +25%; other rows unchanged |
| Component masks | 0: open; 1: protein; 6: RNA and ions; 7: all primary blocks |
| Preparation and continuation precision | Matching q128 and q256 |
| Parent continuation | Complete original challenge, replacement and isolation windows |
| Transmission | Actual final donors; fresh recipients retain E after donor removal |
| History and earlier source bundle | Ordinary history, fixed coarse historical inputs |

The first arrival and both open/paused preparations are newly simulated for
each sequence and resolution. The two earlier q128/q256 prefixes are reused
from qualified P34D evidence preserved in P34T. No successful parent trajectory
from the known sequence is substituted for a new-sequence parent.

The inventory is **46 cases / 470 phases**, comprising **44 new cases and
468 integrations**, plus the two reused prefixes. Four cumulative stages
qualify the archive, sources, parents and onward readouts. The completed panel
requires **23 numerical comparisons**, preserving the original 0.01 scaled
error limit and exact behavioral, diagnostic and phase-label agreement rules.
Both successful and unsuccessful biological outcomes remain reportable.

The software checks exercised the complete panel with explicitly labeled
fixtures, independent reconstruction of incoming draws and component states,
actual-parent readouts, altered-input rejection, negative outcomes,
sequence-specific denominators, six-worker limits and deadline/resource guards.
Actual short native phases checked both resolutions under open/cut six-cell
contact and both new incoming sequences. All 23 checks passed on the first
preparation attempt in 232.659 seconds; fixtures cannot qualify as science.

Startup review verified all **365 registered source files**, frozen copies,
registered dependencies, fixed draws, prerequisite hashes and the inherited
gate. About **343.3 GiB** remained in the dedicated external store. All large
artifacts, caches, logs, frozen sources and fixtures are under `/mnt/workspaces`.
The native solver and previously registered experiments were not edited.

There are only two new incoming sequences in one history. Numerical variants
are accuracy checks, not independent biological replications. P34T's known
sequence does not enter the new denominator. This panel cannot establish broad
population reliability, autonomous maintenance or acquired-record renewal.
**P34A remains incomplete and unqualified.** No later experiment launches
automatically.

- [Registered protocol](p34_sequence_generalization/PROTOCOL.md)
- [Fixed incoming draws](p34_sequence_generalization/draws.json)
- [Registration](/mnt/workspaces/levin-cancer-gj-exploration/p34-pause-state-components/sequence-generalization/jobs/20261016T122842Z-yfs0oixv/registration.json)
- [Runtime estimate](/mnt/workspaces/levin-cancer-gj-exploration/p34-pause-state-components/sequence-generalization/jobs/20261016T122842Z-yfs0oixv/runtime-estimate.json)
- [Live status](/mnt/workspaces/levin-cancer-gj-exploration/p34-pause-state-components/sequence-generalization/jobs/20261016T122842Z-yfs0oixv/status.json)
- [Startup integrity review](storage/p34g-startup-integrity.json)
- [Qualified P34T results](P34T_RESULTS_2026-10-16.md)

Read progress with `.venv/bin/python -B storage/p34g-status.py`.

Registration SHA-256:
`87e70d23f8bcca97c3b71ed31074dbd78858102207cd592217a0bf4446bd97e3`.
