# D192 snapshot routes: benchmark complete and saved-audited

**18 October 2026 update:** excluded benchmark COMPLETE at 16:05:36 UTC on
17 October; runtime 3m43s. The separate user-requested saved-only audit passed:
181 output files, all 26 repairs, 70 named / 54 unique reads and 54 comparisons.
[Results](SNAPSHOT_ROUTES_BENCHMARK_RESULTS.md),
[complete tables](SNAPSHOT_ROUTES_BENCHMARK_TABLES.md).

The unchanged four-block continuation is now **COMPLETE / SAVED-AUDITED**,
in 7m50s: [closeout](SNAPSHOT_ROUTES_PANEL_RESULTS.md),
[complete tables](SNAPSHOT_ROUTES_PANEL_TABLES.md),
[completed handoff](SNAPSHOT_ROUTES_PANEL_STATUS.md).
Current work is [D193 recipient-contingent feedback](YOKED_REFERENCE_STATUS.md).
**All launch/procedure entries below are the historical benchmark record**;
they do not describe a still-running benchmark or authorize another attempt.

## Historical benchmark launch and qualification

17 October 2026. The user approved continuing after D191's saved-audited
fresh-founder result. [D191 closeout](FRESH_FOUNDERS_PANEL_RESULTS.md) and
[complete tables](FRESH_FOUNDERS_PANEL_TABLES.md) are documented. No frozen
D191 code, protocol, data, control, cohort or cap was changed.

**Benchmark DETACHED / STARTUP ACKNOWLEDGED at 16:01:53.863366 UTC, PID
3962875.** This is startup, not completion or a scientific result. One process/
numerical thread, CPU 6, nice 10. No post-start progress/log/output/completion/
process/storage inspection. No automatic polling, audit, retry, main launch
or successor. The four-block main cohort remains disabled in this executor.

[Complete benchmark execution contract](SNAPSHOT_ROUTES_BENCHMARK_V1.md),
[block workflow](../src/laws_confirmation/l22_snapshot_routes_run.py),
[independent workflow checker](../scripts/check_l22_snapshot_routes_run.py),
[freeze/launcher/audit](../src/laws_confirmation/l22_snapshot_routes_benchmark.py).

## Complete-workflow qualification and freeze

First attempt: **124 tests passed in 27.58s**, but the qualification driver's
final resource check rejected retained pytest `current` symlinks and deliberate
negative-test links. Attempt marked FAILED at 15:58:52 UTC; every artifact
remains. This was a qualification-wrapper failure, not scientific failure.

The corrected resource check permits only qualification-fixture links that
resolve inside their own fixture tree. Scientific paths still reject symlinks;
the negative escape test remains. Added a specific fixture-alias regression.
No kernel, physics, source selection, gate, endpoint, readout or threshold changed.

`workflow_attempt2`: **125 passed**, zero failures/errors/skips; XML **30.087s**,
console 30.10s, complete driver **32.392s**. Completed 16:00:20.051814 UTC.
All **84 input hashes** and **3,479 retained artifact hashes** were reverified,
including manifest/XML/log/COMPLETE linkage. Complete reduced source/repair/
read/replay/saved-audit workflow passed, with every path/control/comparison.
Stored corruption after updated file hashes, source identities, packet/birth
isolation, missing/extra files, altered settings, crash retention, admission,
closure and startup-only detachment were exercised. Qualification is not a
positive embodiment result. The original 67-test kernel certificate is intact.

Qualification files under the benchmark root:
`qualification/workflow_attempt2/{MANIFEST.json,COMPLETE.json,tests.xml,tests.log}`.

- MANIFEST SHA-256: `49fd7176ea66b351a3f3f57efad3075b842b7483e34fdec7bb7926e707e839c1`.
- COMPLETE SHA-256: `daa5287d0046bd3e9d3c1889d3eeae49f614463eda8756f432df4a6c391be311`.
- XML SHA-256: `d75b7ee8abec750d11456fb4d26da03112b6ec3eee731f1be2ec4317072124ca`.
- Log SHA-256: `7b4028d223d0e9e6195ad4bf863a5cb0d215c1fdaa24c1cd64d8cbce1a849e05`.

Execution freeze completed **16:01:01.559123 UTC**, binding **7,292 inputs /
68 imported repository modules**: scientific/execution contracts, unchanged
kernel, new workflow/checker/tests, passed qualification, old D191 source and
ancestral evidence, and retained fixtures. No unqualified main executor.

FREEZE SHA-256:
`9f5ddd7d1e42874512a42b637860e6e08ca5dfaaeb24f2e753cf0542af12715f`.

## What was launched and resource boundary

Reused excluded block **603191**, all sixteen records and both packet families,
with no new parent acquisition or outcome selection. All **26 repair paths**,
including two body-free writers; **35 named theta packets in each of two
future streams (70 named reads)**; **54 signed comparisons**. Twelve saved
native bridges plus two fixed/held native bridges, every repair/read replay,
independent scoring and execution-time saved verification are part of the job.
Protected snapshot comparators, shape loss and harms remain visible.

Separate external root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-snapshot-routes-benchmark-v1`.
Run: `l22_snapshot_routes_v1_benchmark_attempt1`.

- Log: `logs/l22_snapshot_routes_v1_benchmark_attempt1.log`.
- Startup receipt: `logs/l22_snapshot_routes_v1_benchmark_attempt1_launch.json`.
- Freeze: `FREEZE.json`.
- Execution MANIFEST and eventual COMPLETE/FAILED: `runs/l22_snapshot_routes_v1_benchmark_attempt1/`.
- Saved arrays, costs and summaries: `outputs/l22_snapshot_routes_v1_benchmark_attempt1/`.

**20-minute initial planning allowance**, not a measured runtime, timeout or
evidence of progress. One CPU6/thread at nice10. All data/logs/fixtures/caches
external; only code/docs locally. Analytical uncompressed/all-name bound
**192,601,856 bytes (183.679 MiB)** includes 32 MiB for JSON/container overhead.
Reserve **256 MiB** output plus **64 MiB** headroom, **1 GiB** total stage cap,
and separate **4 GiB** free-volume reserve. Freeze-time retained files
**484.341 MiB** include both qualification attempts; planning total **804.341
MiB**, below 1,024 MiB. No alias/compression discount or deletion to fit.
The original kernel stage retains its separate 128 MiB cap; earlier caps stay fixed.

## Next user-owned status check

On the next user request, inspect COMPLETE/FAILED and the log. If complete,
run the separate saved-only audit with the same one-thread/CPU6/nice10 settings,
disabled bytecode, PYTHONPATH=src and benchmark-root TMPDIR/cache:

`python -m laws_confirmation.l22_snapshot_routes_benchmark --audit`

Bind freeze, manifest, output hashes, exact membership and replay certificates;
check the complete source/repair/packet/read/control panel and independently
recomputed scores. Then report all comparisons, both families, both endpoints,
shape fidelity and computation/storage costs. Do not infer evidence from
startup or select the best gate after looking at the disposable. If failed,
retain all partial artifacts, diagnose and discuss any retry; never replace
the source or settings silently. Do not poll or launch a successor automatically.

After user-owned saved audit, measured full-block cost may support a separately
qualified/frozen four-block wrapper. It must preserve all exposed histories,
block/message and omission summaries; no main run or fresh confirmation is
authorized by this benchmark alone.

## What is ready

The [fixed D192 design](SNAPSHOT_ROUTES_V1.md) specifies all four direct-access
gate cells, fixed body theta reading, protected snapshot-only writing,
held/ordinary/live/disabled/scrambled controls and complete reporting.
Both common/residual families and every record in 319100–319103 remain;
these are now exposed development histories. Reused disposable 603191 stays
excluded. Two fresh noise sets do not create fresh founders.

- [Kernel](../src/laws_confirmation/l22_snapshot_routes.py): 26 named repair
  paths, including two body-free writers; 54 fixed signed comparisons.
- [Independent route checker](../scripts/check_l22_snapshot_routes.py):
  explicitly reconstructs body/reference/writer order from the frozen ladder
  physics, without importing the new intervention code.
- [Tests](../tests/test_l22_snapshot_routes.py): hidden inputs, source/shuffle
  identity, preserved damping, exact writer/body separation, native bridges,
  costs and tamper detection, plus reproducible D191 table rendering.
- [Bounded qualification driver](../scripts/qualify_l22_snapshot_routes_kernel.py):
  write-once external manifest/log/XML/receipt; one low-priority CPU/thread.

## Historical kernel qualification (unchanged)

`kernel_attempt1`: **67 passed**, zero failures/errors/skips; pytest **4.88s**,
complete driver **6.431s**. All **56 input hashes** remain unchanged and the
manifest/XML/log/COMPLETE linkage was checked after completion. No D192
scientific source or readout was generated. All dynamics were synthetic
qualification tests at 703192; qualification is not evidence of a repair benefit.

Checks include exact **1,000-step** captured/fixed, held/fixed and writer-off
native bridges; native averaging bridge for B1W1; independent replay of every
path; post-update writer timing; preserved −c_m V damping; identical body,
ema and reference bytes when only the writer gate changes; exact identity
between the body-free writer and held-reference writing despite different
later bodies/noise; value-preserving snapshot scramble; rejected packet,
route-input, state, metadata, RNG and extra-field tampering.

Qualification data:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-snapshot-routes-v1/qualification/kernel_attempt1/`.

- MANIFEST SHA-256: `1474b4359841ee8cbc1f9a363fa76a68058390bd783a128cb62b91cadd5f9b16`.
- COMPLETE SHA-256: `9b74bfe3a3dca3453e2e7b854a42ff7f6ec277651154b0f75f6ed4361b583140`.
- XML SHA-256: `253d91e14198f75b5aff897340729de2acffdf5c96150d184f3cdf1599416df4`.
- Log SHA-256: `ecc462d12bac734e50039684df6c226cad1f40b9154146b407e2abec932ef5e9`.

Kernel-stage retention after its receipt: **30,282 bytes (~30 KB)**, below
its separate qualification-only 128 MiB cap. That test worker exited. The
later complete-workflow qualification and benchmark described above use a
different bounded external stage; no old kernel output was overwritten.

## Claim boundary

This is a causal-source test, not a new prediction contest. Any gate lesion
removes direct snapshot access, not all history in the initial body. A positive
body contribution need not establish online necessity; recorded/yoked traces
remain a later question. Protected information is not presumed inferior.
After shared L22, the [recipient decision test](../L20-extension-1/recipient-founders/DECISION_TEST_PLAN.md)
still requires frozen deployable choices and fresh-case utility against
common/family/writer baselines. L20/L22 remain STRESS_TESTED / MIXED.
