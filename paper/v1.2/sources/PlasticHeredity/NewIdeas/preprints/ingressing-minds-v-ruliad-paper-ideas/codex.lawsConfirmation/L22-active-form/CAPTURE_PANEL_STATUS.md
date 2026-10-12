# D186 early capture panel status

12 October 2026. **Detached startup acknowledged at 18:13:39.747391 UTC,
PID 2187755.** One sequential process, one numerical thread, CPU 6, nice 10.
This records startup, not progress or a panel result. No automatic polling,
retry or successor. The user approved this unchanged panel after reviewing
the [completed benchmark](CAPTURE_BENCHMARK_RESULTS.md). See the
[execution contract](CAPTURE_PANEL_EXECUTION_V1.md) and [qualification](CAPTURE_PANEL_QUALIFICATION.md).

The first full qualification passed all 382 tests. The subsequent pre-freeze
storage gate rejected the initial 1.5 GiB estimate: retaining all fixtures,
full uncompressed output allowance and headroom required 1,697,394,560 bytes.
Only the execution cap changes, to 2.5 GiB including both qualification
attempts. All evidence is retained; no scientific setting, case or control
changes. The original benchmark stage and its 1 GiB cap remain untouched.

The repeat full qualification passed **382 tests in 120.32 seconds**. Freeze
at **18:13:11.109141 UTC** binds **1,392 inputs** and all **50 imported repository
modules**. Every input and the exact module set were reverified before startup.
Freeze SHA-256:
`43577272aa18e5d07ca570fde0781b541aa6aa1914550f89bd1bedb0598fe3b9`.

Prelaunch retention was 1,374,270,712 bytes (1310.61 MiB), including both
complete qualification attempts. The 943,325,184-byte output bound plus
64 MiB headroom brings the total planning allowance to **2,384,704,760 bytes**
(2274.23 MiB, 2.221 GiB), within 2.5 GiB. A separate 4 GiB free-volume reserve
also passed. All numerical files remain external; no existing evidence was
deleted and no other agent's job or priorities were changed.

The panel retains all four exposed blocks 30056–30059, all 64 records,
272 repair paths, 372 named reads and 44 contrasts per block. Every repair
and unique fresh read is independently replayed. The original 144 D184
repair paths and 204 named readouts must reproduce their saved arrays and
scores exactly. This is exposed development, not fresh-cohort confirmation.

One sequential process on CPU 6, nice 10, one numerical thread. The measured
serial reference is 21m27s; conservative allowance 45m54s, not a timeout.
The main panel runs detached, with no automatic polling, retry or successor.
No capture result establishes autonomous interface repair, full shape
preservation, prospective prediction improvement or serial renewal.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-early-capture-panel-v1`.
Run: `l22_early_capture_v1_panel_attempt1`.

- Qualification: `logs/qualification_attempt1.xml` and `logs/qualification_attempt2.xml`.
- Storage gate history: `logs/pre_freeze_storage_gate_attempt1.json`.
- Freeze: `runs/FREEZE_<run>.json`.
- Launch receipt and durable log: `logs/<run>_launch.json` and `logs/<run>.log`.
- Manifest, block receipts and COMPLETE/FAILED: `runs/<run>/`.
- Arrays, scores, full replay proofs and summary: `outputs/<run>/`.
- Static documentation handoff: `logs/<run>_launch_handoff_v1.json`.

## Next user status check

Read COMPLETE/FAILED and the durable log. If complete, verify the frozen inputs,
every output and block receipt, manifest/freeze links, exact membership, full
replay proofs, original-source/old-panel bridges, scalar scores and the summary.
The read-only `--verify` entry point repeats saved checks without new dynamics.
Report every block/message, both positive and negative components, and all
conventional/protected-memory comparators. Measure actual runtime, retained and
uncompressed bytes, and peak RSS. Do not fit a predictor or begin renewal.

L20/L22 remain STRESS_TESTED / MIXED. No post-start output, completion, process
or storage inspection was performed for this launch handoff. Do not infer a
result or completion from elapsed wall time.
