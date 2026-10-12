# One repair versus recurring repair under independent cue noise

Simulate repair at generation 15 only, then follow all 256 starting records through generation 32 without further repair. Compare with the verified baseline and repeated-repair trajectories from the completed cue-noise experiment, using the same injuries, resets and independent ongoing noise.

The primary forecast is a positive repeated-minus-one-time difference in uninterrupted success. The repeated control already preserved all 234 first-pass lineages, so the new uncertainty is how many later failures occur after withdrawal. A nonnegative ordering is already implied by the common first step; zero fails the strict positive forecast. This is an exposed-cohort mechanism and resource follow-up.

See the [protocol](PROTOCOL.md), [prediction](PREDICTION.json), [configuration](config.json) and [exposure decisions](EXPOSURE_AND_DECISIONS.json). `prepare_sources.py` binds and copies both old controls. Validation and a benchmark restricted to known outcomes precede `freeze.py` and `launch.py`. The detached run writes its report under `runs/pilot_v1` without automatic scientific polling or a successor.
