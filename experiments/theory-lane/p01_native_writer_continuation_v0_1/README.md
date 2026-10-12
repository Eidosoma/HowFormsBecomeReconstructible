# Controlled native continuation: run handoff

The pilot branches a common generation-3 body into original, tolerance and sign-restored writers, then continues the native dynamics through generation 32. It uses eight previously exposed blocks and matched cue noise. This is a development intervention; the preceding first- and third-generation P01 forecast negatives remain unchanged.

The [protocol](PROTOCOL.md) and [configuration](config.json) fix the cohort, interventions, endpoint and analysis. The [technical benchmark](benchmark/COMPLETE.json) reproduces the full-length generation-4 renewal and h32 assays byte for byte from saved control packets. It uses a duplicate original arm instead of the new intervention. Eight deterministic tests, including the synthetic automatic reporting pipeline, passed; [tests.log](tests.log) retains their result.

Measured times were 7.93 seconds for a three-arm renewal and 28.93 seconds for the terminal assay. The conservative pilot forecast is 3,228 seconds, about 54 minutes, on one numerical worker with one thread. The actual duration can differ. The forecast is below the declared one-hour CPU ceiling; no full-cohort or confirmation sweep is authorized by this package.

The launcher freezes 264 native input-file identities and copies its code, configuration, protocol, tests, benchmark evidence and native source references into the run. Every original/tolerance continuation must replay exactly, and the worker stops on any failure. It saves every new boundary, checks strict scoring, calculates paired effects and independently verifies the terminal tables before declaring completion.

The worker starts in a detached OS session with closed stdin and its own log. A quiet launcher waits for that child in a persistent execution session so sandbox cleanup cannot end the worker prematurely. That wait consumes no polling tokens. There is one numerical process; the launcher is a sleeping supervisor. Do not poll automatically. Read status or results only when the user requests it or a completion notification arrives.

The run directory is `runs/pilot_v1`. After launch, its `LAUNCH.json` and `PID` identify the worker. `STATUS.json` records its current phase, `console.log` records completed blocks, `FAILED.json` records any error, and `COMPLETE.json` marks verified completion. At completion, `REPORT.md`, `analysis.json`, `terminal_lineages.csv` and `generation_block_summaries.csv` contain the results. These result files are created by the worker; they are not evidence of a completed pilot before the completion marker exists.

To verify a completed run from the theory-lane directory:

```bash
python3 -B p01_native_writer_continuation_v0_1/verify.py \
  p01_native_writer_continuation_v0_1/runs/pilot_v1
```

The immutable launch snapshot and native byte replay support this selected intervention calculation. They do not supply an external preregistration, an independent laboratory, a full E051 audit or a validated long-horizon predictor. Earlier packages remain frozen.
