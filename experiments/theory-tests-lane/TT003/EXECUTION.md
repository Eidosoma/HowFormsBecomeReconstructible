# TT003 execution record

`pilot_v2` completed successfully on 8 October 2026 at 20:58:06 UTC, in 738.87 seconds. All 112 event batches passed the separate dynamics replay, covering 1,536 fresh paired-cue assays and 256 renewal bodies. The user's next status request at 21:56 UTC triggered inspection of completion and results. All 123 output and 43 frozen input identities verified; the [interpretation](INTERPRETATION.md) records the findings and limits. No successor job is running from this review.

The successful attempt launched at 20:45:48 UTC. Its single post-launch persistence check at 20:46:41 UTC verified that the detached worker survived its launcher, passed all 10 technical checks, and saved 16 of 112 simulation batches. It then continued on one CPU without automatic polling, completed simulation and replay, and generated its report and figures.

The initial `pilot_v1` launch at 19:41:48 UTC stopped during technical checks before any pilot observations were saved. The user's subsequent status request revealed a stale RUNNING record and a truncated check log. A host process check found no TT003 worker. Command PID-namespace teardown is the inferred cause; the exact exit signal and termination time were not recorded. The original startup check was insufficient to establish persistence. The interrupted attempt and its original status are retained in [the recovery record](recovery/pilot_v1/INTERRUPTION.json). This is an execution failure, not a scientific result.

The retry uses the same 43 qualified input files and identical seeds. Only the launch environment and unique job/run destination changed. It runs outside the short-lived command sandbox; [the persistence check](jobs/pilot_v2/PERSISTENCE_CHECK.json) records the host process identity, detached session, closed stdin, one-CPU affinity and progress after launcher exit.

The [protocol](PROTOCOL.md) selects eight packets by fixed indices from already exposed E041 blocks 32000 and 32001: opposed-rule founders 0/1 at source depths 0/32. Sixteen short paths per packet supply 1,536 fresh paired-cue assays and 256 paired-cue renewal bodies. Every stored event receives a separate dynamics replay before analysis. Erased, random, foreign and disabled-reader controls, protected copying and duplicate fresh assays address the observation contract. This is development feasibility with only two independent source blocks; it cannot establish population robustness or confirm RDT.

Before launch, all 10 adapter checks passed, including exact agreement with the original E041 fresh-assay and full-rewrite routines, input immutability, assay/renewal stream separation, capture timing and detection of corrupted evidence. The complete excluded fixture passed in 4.881 seconds and replayed all 28 stored events. The excluded benchmark passed in 8.738 seconds, also replaying all 28 events. Its simulation, audit and analysis took 2.097, 2.163 and 2.806 seconds respectively. The generated fixture figure was visually inspected. These engineered technical inputs are excluded from scientific evidence.

The frozen scaling rule forecast 6,644.49 seconds, approximately 1 hour 51 minutes, including the separate audit and a threefold simulation/audit allowance. Actual successful-run time was 738.87 seconds: 366.86 simulation, 366.06 audit and 4.20 analysis, plus startup and checks. The conservative forecast substantially overestimated runtime; no forecast or benchmark was changed after observing this. The worker used one CPU and one numerical thread; it reserved at least 512 MiB of free storage before launch.

- [Frozen job manifest](jobs/pilot_v2/job.json): command, qualification identities, runtime estimate and hashes of all 43 input files.
- [Launch receipt](jobs/pilot_v2/STARTUP.json): bounded startup result; automatic polling is disabled.
- [Process record](jobs/pilot_v2/PID.json): PID in the launch environment.
- `jobs/pilot_v2/console.log`: worker output, written without a monitoring process.
- `runs/pilot_v2/STATUS.json`: current machine-readable phase; inspect only when requested.
- `runs/pilot_v2/COMPLETE.json` or `FAILED.json`: durable final outcome. `RUNNING.json` is the retained historical launch record, so its presence alone does not establish current execution.
- On success, `runs/pilot_v2/REPORT.md`, `summary.json`, `observations.npz`, plots, event arrays and `DYNAMICS_AUDIT.json` are generated automatically. The completion record binds retained evidence by hash.

Results were first inspected after the user's 21:56 UTC status request, with outcome access recorded before reading the report. Saved depth-32 model outputs are unvalidated point extrapolations; this pilot generated no long continuation and supplies no calibrated uncertainty. Launches, interruption, source access and result access are recorded in the lane exposure register. Earlier TT001/TT002 results and the source experiments remain unchanged.
