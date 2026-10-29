# One-hour cached continuation pilot

The long 304-block study was stopped at the user’s request, before any continuation outcomes were generated. Its completed measurements and partial work remain preserved. The current lane preference is one hour when scientifically useful, with six hours as the general ceiling.

A separate, smaller pilot is now launched as `pilot_v1`, detached on one numerical thread. Its estimated wall time is 31.1 minutes and its hard limit is 60 minutes, including cache verification, continuations and analysis. There is no automatic extension, retry, polling or successor run. The single startup check confirmed a live detached process and durable RUNNING status.

The pilot reuses all 63 selected records from the completed fresh precision screen: 31 currently failing and 32 currently passing records across 16 acquisition blocks. Each block contains both expression classes. All 272 used source files were verified, the original boundary-only selection was reproduced, and the first-repeat predictions were independently recomputed from retained windows and fixed coefficients. These records had no continuation outcomes in the verified source run. The partially completed 304-block cohort is excluded.

Only the predeclared first measurement repeat is used: 32 successor probes, eight direct probes, and the same frozen candidate, retained-eight-probe and TT008 model coefficients. No averaging across repeats, choosing the better repeat, refitting or recalibration is permitted. Reused measurements retain their original cost accounting; no new acquisition or probe measurements are needed.

All 126 record/regime forecasts must be verified and sealed before new futures begin. Each record receives 18 full original-writer rewrites followed by a fresh terminal read, under matched and independent birth and ongoing cue-noise conditions. A new future namespace separates these draws from every earlier measurement. The run performs 2,394 primary native reads and 608 separate flat audit reads. The audit path propagates its own outgoing packets through every generation.

Inference gives each acquisition block equal weight and gives its currently failing and passing classes equal weight. This accounts for the earlier precision screen’s selection and its one class containing only one available record. It changes the estimand from the cancelled all-64-record comparison. Paired block Brier improvements, fixed margins and block-t limits are reported against both comparators in both noise regimes. All records and both regimes must finish before an inferential result is produced. Weighted calibration and class-specific scores are descriptive.

This is a selected-panel forecasting pilot with limited power, not a replacement for the 304-block comparison. It can reveal large predictive failures or useful directional evidence; it cannot promise to resolve small advantages or establish an RDT-specific law. Outcomes remain pending.

Eleven qualification checks passed, including cache identity and first-repeat selection, unequal class-size weighting, independent statistical arithmetic, invalid-cohort rejection, the forecast barrier, reduced-step synthetic continuation for batches of three and four records, and the hard deadline. The native reader, writer, continuation code and separate dynamics audit were copied unchanged from the qualified predecessor.

Artifacts: [protocol](protocol.json), [cache verification](CACHE_VERIFICATION.json), [qualification](QUALIFICATION.json), [test output](runs/qualification_v1/pytest.log), [job](jobs/pilot_v1/JOB.json), [single startup receipt](jobs/pilot_v1/STARTUP.json), and [long-run stop record](../rdt_successor_outcome_v0_2/OUTCOME_STOP.json).
