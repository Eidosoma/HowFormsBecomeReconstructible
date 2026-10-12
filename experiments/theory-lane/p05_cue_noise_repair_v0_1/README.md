# Cue-noise follow-up to repeated repair

Cross baseline and the unchanged repeated recipient repair with ongoing cue-noise correlations 1, .999 and 0. All 256 exposed starting records continue through generations 15–32. The matched arms replay the completed serial experiment; the four mismatched arms supply new continuation outcomes.

The primary forecast is a positive repeated-repair advantage in uninterrupted success under independent cue noise. Report absolute performance as well as paired differences so that baseline improvement is distinguishable from repair deterioration.

The [protocol](PROTOCOL.md), [prediction](PREDICTION.json), [configuration](config.json) and [exposure record](EXPOSURE_AND_DECISIONS.json) specify the comparison. Sources, tests and a benchmark using known outcomes must pass before `freeze.py` and `launch.py`. The launcher enforces one-worker CPU admission and starts a detached frozen copy. The run writes durable status, raw evidence, verification and its report under `runs/pilot_v1`. No automatic scientific polling or successor is authorized.
