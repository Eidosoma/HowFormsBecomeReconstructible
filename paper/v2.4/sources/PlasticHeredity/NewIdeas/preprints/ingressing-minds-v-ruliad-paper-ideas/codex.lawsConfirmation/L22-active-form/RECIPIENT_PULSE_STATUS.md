# D195 recipient disturbance: benchmark handoff

28 October 2026. [Fixed scientific design](RECIPIENT_PULSE_V1.md),
[205-test qualification and exact identities](RECIPIENT_PULSE_QUALIFICATION.md).

**COMPLETE / separately SAVED-AUDITED.**
Execution completed **27 October, 13:25:46.589412 UTC**, in **149.049467455 s
(2 min 29 s)**. The user-triggered saved-only audit passed **28 October,
15:02:51.597171 UTC** in 15.149236542 s. No FAILED receipt; PID 2684746 is
absent. [Full interpretation](RECIPIENT_PULSE_RESULTS.md),
[complete generated tables](RECIPIENT_PULSE_TABLES.md).

Primary preference interaction: **−3.125 points common / −0.78125 residual**;
recognition interaction **−1.5625 / −0.78125 points**. Both have 0 record
gains / 2 harms / 14 ties, concentrated in message 3, replicates 1 and 3.
Own-feedback's advantage shrinks after the pulse in both families. The
common pulse harms both arms; the residual pulse slightly improves both,
more under recorded feedback. Residual LL still has a small absolute lead.
This is a negative primary pilot, not an equivalence or universal-body claim.

Freeze at 13:21:16.538235 UTC: 16,283 inputs / 80 repository modules.
SHA-256 `ded7aadbdb12128fa61d5eeda2f36fccbf1c32f20de77214e1e562811088ade1`.
All 205 checks passed on qualification attempt 1. All 245 saved output files,
32 paths, 74 named / 46 distinct reads, 32 comparisons, original bridges and
controls passed the separate audit. Prior D193/D194 results are unchanged.

The pulse reverses V in the central 8 by 8 patch immediately before sweep
501. It leaves memory/reference/writer/record state untouched at intervention
and consumes no RNG. Own-feedback LL and recorded-feedback YL each have an
undisturbed and disturbed arm. Both families and all sixteen excluded 603191
records remain. All donor recordings are sealed before any recipient begins.

Primary signed comparison in each family:
`(LL_pulse - YL_pulse) - (LL - YL)` on terminal own-minus-partner preference,
with recognition, every cell mean, pulse harms and all original metrics.
A positive interaction is not automatically an absolute own-feedback benefit
or full recovery. This is exposed development, not fresh-founder confirmation.

The complete benchmark retains 32 paths, 37 named packets, two reader futures
and all controls. Only theta enters fresh readers. Original noise addresses
allow exact apparatus bridges; old results are not pooled into estimates.
The original D193/D194 negative result is not revised by this experiment.

External stage:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-recipient-pulse-benchmark-v1`.
Run name: `l22_recipient_pulse_v1_benchmark_attempt1`.
Durable log: `logs/l22_recipient_pulse_v1_benchmark_attempt1.log`.
Startup receipt: `logs/l22_recipient_pulse_v1_benchmark_attempt1_launch.json`.
Completion/failure: `runs/l22_recipient_pulse_v1_benchmark_attempt1/`.
Scientific arrays/proofs: `outputs/l22_recipient_pulse_v1_benchmark_attempt1/`.

One CPU/thread, CPU6, nice10; all data/logs/fixtures/caches external.
Peak RSS **397.766 MiB**, uncompressed arrays **236.821 MiB**, stage retained
before COMPLETE **686.541 MiB**, including qualification. Stage cap 2 GiB;
512 MiB benchmark reservation, 64 MiB headroom, 4 GiB free-volume reserve.
The actual 149.049 s runtime replaces the original conservative 20-minute
planning allowance for budgeting later work.

Startup was acknowledged 27 October at 13:23:17.547333 UTC. No automatic
progress polling occurred; the user's 28 October continuation triggered
readback and the saved-only audit. Audit receipt:
`audits/status_2026-10-28_attempt1.json`.
No simulation, retry, main launch or successor was run during readback.

**28 October continuation:** the unchanged four-history panel is now
qualified, frozen and launched detached. All 274 checks passed; startup
acknowledged **15:36:02.043359 UTC, PID 2993939**, one CPU6/thread, nice10.
[Panel handoff](RECIPIENT_PULSE_PANEL_STATUS.md),
[fixed panel contract](RECIPIENT_PULSE_PANEL_V1.md),
[qualification](RECIPIENT_PULSE_PANEL_QUALIFICATION.md).
Four measured blocks imply a 596.198 s serial reference; the conservative
allowance is 1,372.396 s (22 min 52 s). No panel result has been inspected
and no automatic polling follows launch. The present benchmark result stays
excluded from panel means; all scientific freezes and outputs are unchanged.

Commands use `python -m laws_confirmation.l22_recipient_pulse_benchmark`,
the existing external environment, `PYTHONPATH=src`, disabled bytecode and
one-thread numerical settings, CPU6/nice10, external TMPDIR/cache.
`--launch-benchmark` acknowledges startup only; `--audit` reads saved outputs
without advancing dynamics. Main histories 319100-319103 remain disabled.

L20/L22 remain **STRESS_TESTED / MIXED**. After shared L22, the queued
[recipient decision test](../L20-extension-1/recipient-founders/DECISION_TEST_PLAN.md)
still needs frozen choices on fresh cases versus the best common setting
and simple family/writer choices. Another interaction is not useful matching.
