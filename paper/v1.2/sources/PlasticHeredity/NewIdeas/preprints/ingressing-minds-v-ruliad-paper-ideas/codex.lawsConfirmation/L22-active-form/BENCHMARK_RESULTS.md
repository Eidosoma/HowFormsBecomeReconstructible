# D184 disposable benchmark results

12 October 2026. The complete disposable benchmark passed its apparatus and
saved-evidence checks. Its identical-record comparison shows body-dependent
changes in continuous shape scores, but **no improvement in correct-message
recognition**. This one block qualifies the machinery and measures cost; it
does not establish useful active repair or settle L22.

The benchmark used tissue 603184, four messages, four acquired records per
message and four fresh readers per record. It remains excluded from the
planned four-block panel. Its outcomes did not change scientific settings
or select the pilot's cases.

## Results and interpretation

Recognition is the mean fraction of fresh readers selecting the intended
message, with ties divided equally. Preference is intended minus paired-
alternative recognition. Projection gap is a continuous shape score, not a
probability or percentage point.

| Common incoming record condition | Recognition | Preference | Projection gap | Correlation with original record |
| --- | ---: | ---: | ---: | ---: |
| Unchanged incoming record | 50.00% | 0.000000 | 0.000000 | 0.796553 |
| Own body and live writer | 50.00% | 0.000000 | 0.077682 | 0.818494 |
| Partner body and live writer | 50.00% | 0.000000 | -0.077682 | 0.664138 |
| Own spatially scrambled body and live writer | 50.00% | 0.000000 | 0.069309 | 0.814320 |
| History erased body and live writer | 50.00% | 0.000000 | 0.000000 | 0.724917 |
| Own body and fixed reader native writer | 50.00% | 0.000000 | 0.066411 | 0.817182 |
| Own body and conventional averaging | 50.00% | 0.000000 | 0.089221 | 0.809300 |

The 50 percent average hides a fixed asymmetry: messages 0 and 3 score zero,
while messages 1 and 2 score one, for unchanged input, own live, partner live
and conventional averaging alike. Repair does not recover either missing
message direction. The body affects continuous scores without changing which
paired message the fresh reader chooses.

Own versus partner body improves projection gap in all four message strata:
0.222315, 0.088411, 0.222315 and 0.088411. Against unchanged input, the gains
are 0.152662, 0.102842, 0.069653 and -0.014430. Packet correlation gains
against unchanged input are also mixed across messages. A favorable pooled
score or changed packet alone does not establish missing-content correction.

Conventional averaging has a slightly larger pooled projection gain than
live native repair, while native repair has the larger packet correlation.
Recognition is identical. The metrics do not identify a consistent winner
or demonstrate a live-loop or RDT-specific advantage. Fixed-reader native
writing versus averaging is the more directly matched comparison because
both see exactly the same activity stream.

Keep residual-record and native-reset results separate. Residual input
recognition is 92.1875 percent, versus 87.5 percent after zero-reset own live
repair and 89.0625 percent under the native reset. Continuous projection and
packet correlation improve despite these recognition losses.

Intact acquired and supplied-positive records score 100 percent in every
message stratum. Disabled reading scores 25 percent over balanced messages;
its conditional scores are 25, 18.75, 31.25 and 25 percent. Uninformed
trajectories are identical across intended labels. Per-message chance need
not equal the balanced-panel chance rate.

## Verification and measured cost

The benchmark started at 13:29:32.761347 UTC and completed at
13:34:07.669752 UTC on 12 October: **274.908405 seconds**, or 4m35s.
Its inner block timer is 271.753350 seconds. The full cost includes final
hashing and array-size calculation. One worker used one numerical thread
on CPU 0.

All 36 repair paths, 40 unique fresh assays, 51 named conditions and 289 exact
alias checks passed. Independent replay gives exactly zero native and fresh-
reader state discrepancy. Maximum conventional-mean discrepancy is
4.884981308350689e-15, below the frozen 2e-12 tolerance. The checker shares
the original physical equations; it is not a clean-room implementation.

The user-requested status readback verified all 252 frozen inputs, 161 output
hashes, the exact file set, receipt linkage, source boundary, packet mappings
and scalar endpoints for all 51 arms. All twenty contrasts were independently
recomputed from saved rows. No new dynamics ran for that readback. The new
executor's qualification also checks each repair output against its saved
fresh-reader mapping.

Compressed benchmark outputs occupy **62,112,356 bytes** (59.23 MiB).
Uncompressed arrays total **97,775,744 bytes** (93.25 MiB). Peak process RSS
was **125,538,304 bytes** (119.72 MiB). The entire pilot stage occupied
195,115,556 bytes (186.08 MiB) at the status check, before panel-qualification
fixtures. All data are external; no older evidence was deleted.

## Evidence and next gate

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-active-form-pilot-v1`.
Benchmark run: `l22_active_form_pilot_v1_benchmark_attempt1`.
Its `outputs/<run>/` retains every array, record, contrast, read mapping and
CHECK receipt; `runs/<run>/` retains MANIFEST and COMPLETE. All 188
pre-benchmark qualification tests passed; earlier test attempts are preserved.

Freeze SHA-256:
`a99f02583a871d65b4c6c3a9f44c982b8f6e5b5b1659417d3e125bb24159e32f`.
Manifest SHA-256:
`739457512634240c5672ba4f2b97af1984bb4b6f06dc561698f26a8417789815`.
Completion SHA-256:
`128d974aaf3b9d1da2499a09041504ca8336d430909665cf0d2c9f1852d82805`.

The user approved the unchanged 64-record panel after this status report.
Its [execution contract](PANEL_EXECUTION_V1.md) and [panel status](PANEL_STATUS.md)
keep qualification, launch and results distinct. Four workers, a conservative
12m10s detached allowance and the unchanged 1 GiB stage cap are planned.
Fresh confirmation, prediction fitting and serial renewal remain conditional.
L20 and L22 remain STRESS_TESTED / MIXED.
