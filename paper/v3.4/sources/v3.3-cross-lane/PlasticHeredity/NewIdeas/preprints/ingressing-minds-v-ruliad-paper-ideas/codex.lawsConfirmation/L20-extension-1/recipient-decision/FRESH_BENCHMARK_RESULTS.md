# D199 benchmark and separate saved audit passed

Benchmark reviewed 31 October 2026; audit completion verified on the user's
1 November status advance. [Main launch](FRESH_MAIN_LAUNCH.md).
[Contract](FRESH_V1.md), [qualification](FRESH_QUALIFICATION.md),
[current handoff](FRESH_STATUS.md).

The excluded disposable benchmark completed successfully at
**11:35:27.319116 UTC**, in **882.210882 seconds (14m42s)**, below its 45-minute
planning allowance. The benchmark worker was absent on the status check.
All four lives, eight F0 packets, 16 policy decisions, 576 reconstruction paths,
1,152 terminal rows and the complete control panel remain. Independent
generation-time replay and all **2,912 exact alias checks** passed.

All 16 choices were sealed at **11:20:57.212082 UTC**, before the descendant
barrier at **11:20:57.539150 UTC**. The entire block was sealed together.
The user-requested readback verified **1,748 frozen input hashes**, all **30
output hashes**, freeze/manifest linkage, source-choice timing and absence of
failure. No main sources, main output directory or execution seal existed.

## Disposable decisions are apparatus evidence only

This block is excluded from the prospective estimates and from policy fitting.
Its values are retained for transparency, not counted as a matching result.
The detailed rule and family rules chose the same actions on all 16 cases.

| Policy | Choices at 0.75 / 1.0 / 1.25 | Common-reader preference points |
| --- | ---: | ---: |
| Native | 0 / 16 / 0 | 37.878417969 |
| Common | 16 / 0 / 0 | 38.555908203 |
| Writer | 16 / 0 / 0 | 38.555908203 |
| Family | 8 / 0 / 8 | 38.647460938 |
| Family-by-writer | 8 / 0 / 8 | 38.647460938 |
| Record rule | 8 / 0 / 8 | 38.647460938 |

No inferential interval is produced for this single excluded block. These
observations do not change any feature, coefficient, baseline, coupling,
sample size or scientific comparison. D198 remains the latest decision
evidence used for development; the main prospective question is still open.

## Resource measurement and main budget

The measurement includes source acquisition/replay, policy inference and
sealing, all recipients and controls, independent descendant replay, saved
checks and I/O. One worker/thread on CPU6, nice10; peak RSS **193.519531 MiB**.
Before the separate audit, all retained D199 artifacts totaled **132,803,609
bytes (about 126.65 MiB)**, including qualification. All numerical files,
caches, logs and receipts remain on `/mnt/bioIce1`.

Applying the frozen budgeting rule to the measured complete block:

- Sixteen-block point estimate: **14,115.374108s (3h55m15s)**.
- Planning allowance: **17,944.217634s (4h59m04s)**.
- Additional main reservation: **4,429,185,024 bytes (4.125 GiB)**, including
  the declared summary allowance; stage cap remains 8 GiB plus a separate
  4 GiB free-volume reserve.

These are serial estimates, with no extra-worker speedup assumed. Main
execution was sealed and launched on 1 November; see the separate launch note.
Runtime estimates do not authorize adaptive cohort changes.

## Separate saved audit

After the user's status advance and successful receipt/hash review, the frozen
saved-only audit was launched detached. Startup acknowledged
**12:43:44.451331 UTC**, PID **3890818**, one CPU6/thread, nice10.
Log: `logs/benchmark_audit.log`; acknowledgement:
`logs/benchmark_audit_launch.json`; eventual receipt: `audits/benchmark.json`.

The audit completed **12:44:03.846074 UTC** on 31 October in **19.396375s**.
On the user's 1 November advance, completion was verified against the benchmark
and unchanged full proof, all 1,748 frozen inputs and 30 outputs. It checked
saved sources, decisions, trajectories, terminal values, statistics and output
membership without tissue stepping or model fitting. Peak audit RSS was
**114.167969 MiB**, one CPU6/thread, nice10. The 2,700s launch allowance was
conservative; actual audit runtime is now measured. No automatic polling or
successor occurred after audit startup.

The user advance then completed the separate execution seal and main launch,
documented in [FRESH_MAIN_LAUNCH.md](FRESH_MAIN_LAUNCH.md). The disposable remains
excluded from the prospective scientific comparison.

## Pinned benchmark evidence

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-recipient-decision-fresh-v1`.

| Artifact | SHA-256 |
| --- | --- |
| `FREEZE.json` | `c094b5740c2819359bb94c0cb457ab77da6d1af581225e8b9c739a73445a93ed` |
| `runs/benchmark/MANIFEST.json` | `f978e6b0dfa157a6199751ad68d8b733f8a5b2e7da33cb984506dbe941793b96` |
| `runs/benchmark/COMPLETE.json` | `0f667e400cf24b0257dd637f65ff614d12ba00112808da71c63015d3e6a12293` |
| `outputs/benchmark/CHOICES_SEAL.json` | `3c47d939a1a79e3edc0e335b407e4c832245d69ed48d830f9e23555b07af3eb1` |
| `outputs/benchmark/DESCENDANTS_STARTED.json` | `0d1694a1d1d680d31b7521db79ff4968aca1fe859c6ad2b24b97ca5ceab8d2d7` |
| `outputs/benchmark/REPORT.json` | `b8858107bbed9bbe012f1999a57c45edbe03a1a409b0fc6550b1a1d9d6605ca1` |
| `audits/benchmark.json` | `459e668758f12644b12e083ee7c7355da771a9bf09c88207871ded450263b115` |
