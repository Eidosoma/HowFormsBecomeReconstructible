# TT006 execution record

The user authorized the next study after TT005. TT006 reuses all 16 previously exposed TT003 short-history tables, adds 24 fixed synthetic examples and four constructed model challenges, and generates no native trajectories. The [protocol](PROTOCOL.md) and [plan](plan.json) fix the 44-case development panel, continuous five-parameter domain, confidence construction, 2,047-split work limit and one-hour conservative runtime ceiling. All native forecasts remain ABSTAIN pending observation-model qualification.

Eight mathematical checks pass. They cover independent hidden-path enumeration, exact binomial arithmetic, small-sample coverage, continuous-box enclosures, exhaustive corner extrema, early-stop coverage, incompatible histories and deliberate certificate corruption. Each frozen worker repeats them and retains its log.

## Excluded qualification and implementation revision

The first frozen fixture completed in 45.7378 seconds, including 30.7712 seconds of rational audit. Its two cases passed; the compatible perfect-history case retained broad long-term uncertainty and the constructed alternating case had an exactly certified empty region. The first benchmark completed in 139.0053 seconds, with 22.7020 seconds of region computation and 108.5668 seconds of rational audit. All four cases passed. Its conservative forecast, 3 × 139.0053 × 44/4 + 60 = 4,647.1746 seconds, exceeds the 3,600-second ceiling. No development panel was launched using it.

Preserved `jobs/fixture_v1`, `runs/fixture_v1`, `jobs/benchmark_v1` and `runs/benchmark_v1`. The working oracle now caches exact readability/identity corner extrema and combines their nonnegative extrema directly instead of repeating every pairwise product. An added check compares these extrema against exhaustive enumeration of all 32 parameter corners. The mathematical region, subdivision budget and development panel are unchanged. Also corrected display rounding to preserve inequality directions and padded plot limits to keep empty-region labels visible. The first plots' cosmetic clipping and nearest-rounding presentation are superseded; their unrounded machine-readable intervals and rational audits remain valid.

The second fixture passed in 44.5563 seconds, including 29.6663 seconds of audit; caching rational arithmetic alone was not the main saving. Profiling the same certificate with its arrays loaded once took 2.372 seconds under profiling. The audit had indexed the compressed NumPy archive inside its node loop, repeatedly decompressing entire arrays. It now materializes each certificate array once before the identical mathematical checks. No search or statistical setting changed. `fixture_v2` is preserved; no `benchmark_v2` was run.

The final frozen fixture `fixture_v3` passed in 15.6164 seconds (audit 0.7269 seconds). `benchmark_v3` passed in 31.7551 seconds (region computation 22.1045 seconds; audit 2.1423 seconds). Both figures were inspected. Compared all six technical regions with the first implementation: every confidence interval, fit, witness, forecast and parameter-box array is identical, excluding runtime fields. No search budget, statistical setting, source observation or development case was changed.

[QUALIFICATION.json](QUALIFICATION.json) verifies all 21 input files, completed qualification output hashes and storage. The conservative development forecast is **1,107.9196 seconds (18 minutes 28 seconds)**, below the unchanged one-hour ceiling. Storage reserve is 256 MiB, with more than 52 GiB free at preflight. Completed runs and source experiments are never overwritten.

## Development launch

Launched `development_v1` on 9 October 2026 using the persistent host launcher, PID **2473813**. The single post-launch check passed at **16:17:26 UTC**: the worker survived its launcher, was computing confidence regions, used CPU 7 and one numerical thread, and had stdin `/dev/null`. All 21 frozen inputs were unchanged. No development outcomes were opened during that check.

- Job, frozen inputs and console log: [jobs/development_v1](jobs/development_v1).
- One startup receipt: [PERSISTENCE_CHECK.json](jobs/development_v1/PERSISTENCE_CHECK.json).
- Durable status and eventual reports: [runs/development_v1](runs/development_v1).
- Expected outputs include all 44 case identities, deduplicated continuous-region certificates, rational audit, unfiltered forecast tables and a figure. Duplicate count tables are not counted as independent evidence.

The worker was left unpolled after startup until the user requested status. It had completed at **16:21:02 UTC on 9 October 2026**, in **248.7413 seconds (4 minutes 9 seconds)**. All 44 cases completed, with 33 distinct confidence regions, eight technical checks, the independent rational audit and the 264-row report check passing. No native trajectories were generated. The 18-minute-28-second preflight forecast was conservative.

The completion review verified all 76 output hashes, all 21 frozen input hashes and the job identity before opening the scientific results. Recorded development exposure, inspected the full figure and checked the interpretation against the unrounded region records. See the [interpretation](INTERPRETATION.md) and [closeout receipt](CLOSEOUT.json). Native forecasts remain ABSTAIN. No automatic restart or successor was created; no TT006 job remains outstanding.

## Execution policy

Use one CPU and one numerical thread. The development worker must run from its frozen input directory in a persistent host session, with stdin `/dev/null`, a unique console log, PID and durable `STATUS.json`, `COMPLETE.json` or `FAILED.json`. Make one post-launch persistence check. Do not poll automatically or launch a successor.
