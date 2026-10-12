# D186 early capture: recovery with a trade-off

12 October 2026. The complete 64-record development panel supports a bounded
early-capture benefit: the hard identical-record condition improves from
50 to 77.734375 percent recognition, with gains in every block and partial
recovery of both previously missing identities. Conventional averaging helps
less. However, captured live repair performs worse than ordinary repair on
already-informative records, and better recognition does not preserve the
complete original record. Both findings belong to the result.

The [protocol](CAPTURE_V1.md), [panel execution contract](CAPTURE_PANEL_EXECUTION_V1.md)
and all frozen scientific files remain unchanged. All four exposed blocks
30056–30059, four messages and four replicates remain: 64 records, 272 repair
paths, 372 named reads and 288 unique assays. Each record has four reader
draws; these are not independent founders. The disposable benchmark is excluded.
This is development evidence, not fresh-cohort confirmation or a forecast test.

## What changes, and what crosses the boundary

At repair birth, capture copies the allowed post-injury body V into the existing
working reference R once. It includes the fresh half of the injured body, not
an intact parent backup. The ordinary update rates and 1000-sweep horizons do
not change. R affects maintenance and writing together; their contributions
are not separately isolated by this intervention. Only the ordinary 2048-byte
theta record enters a fresh reader. Neither V nor R crosses that boundary.

Fixed reading holds body feedback on the incoming record while writing an
outgoing record. Matched conventional averaging receives the same body stream
and the extra birth observation when capture is enabled. It still makes 1000
writes, with no birth write or increased rate. A held reference is protected
working memory, reported separately, not a disabled-information control.

## Hard identical-record case

Recognition is intended-message accuracy in actual fresh bodies; preference
is own accuracy minus fixed-partner accuracy. Record correlation compares
theta with its own acquired parent theta, not with the fresh body.

| Treatment | Recognition percent | Preference points | Own-parent record correlation |
| --- | ---: | ---: | ---: |
| Common input, unchanged | 50.0000 | 0.0000 | 0.795862 |
| Ordinary reference, live feedback | 50.0000 | 0.0000 | 0.740144 |
| Ordinary reference, fixed reading | 50.0000 | 0.0000 | 0.746873 |
| Ordinary reference, conventional averaging | 50.0000 | 0.0000 | 0.726984 |
| Captured reference, live feedback | 77.7344 | 55.8594 | 0.744412 |
| Captured reference, fixed reading | 73.4375 | 46.8750 | 0.789771 |
| Captured reference, matched averaging | 64.0625 | 28.1250 | 0.777901 |
| Captured reference held throughout repair | 75.0000 | 52.3438 | 0.698648 |

| Block | Unchanged input | Captured live | Captured fixed | Captured averaging | Captured held reference |
| --- | ---: | ---: | ---: | ---: | ---: |
| 30056 | 50.0000 | 75.0000 | 65.6250 | 62.5000 | 70.3125 |
| 30057 | 50.0000 | 62.5000 | 59.3750 | 56.2500 | 64.0625 |
| 30058 | 50.0000 | 87.5000 | 81.2500 | 68.7500 | 81.2500 |
| 30059 | 50.0000 | 85.9375 | 87.5000 | 68.7500 | 84.3750 |

All entries above are recognition percentages. Captured live beats matched
averaging in all four blocks, but does not beat fixed reading or the protected
reference in every block. Four positive block effects are not a new independent
replication, a significance test or a registered success threshold.

| Treatment | Message 0 | Message 1 | Message 2 | Message 3 |
| --- | ---: | ---: | ---: | ---: |
| Common input / ordinary live | 0.0000 | 100.0000 | 100.0000 | 0.0000 |
| Captured live | 56.2500 | 98.4375 | 100.0000 | 56.2500 |
| Captured fixed | 56.2500 | 100.0000 | 100.0000 | 37.5000 |
| Captured averaging | 56.2500 | 100.0000 | 100.0000 | 0.0000 |
| Captured held reference | 57.8125 | 93.7500 | 95.3125 | 53.1250 |

Both formerly missing identities recover partly under captured live repair
in every block. Matched averaging recovers message 0 but leaves message 3
unrecognized. Nevertheless, common-record correlation declines from input
to captured live in every block: pooled 0.795862 to 0.744412. Recovering the
coarse identity is not full shape preservation.

## Already-informative records: the limitation

| Treatment | Recognition percent | Preference points | Own-parent record correlation |
| --- | ---: | ---: | ---: |
| Informative residual input, unchanged | 83.9844 | 76.9531 | 0.300000 |
| Ordinary reference, live feedback | 87.8906 | 83.2031 | 0.474446 |
| Ordinary reference, fixed reading | 86.3281 | 80.4688 | 0.450969 |
| Ordinary reference, conventional averaging | 87.8906 | 83.2031 | 0.484678 |
| Captured reference, live feedback | 84.7656 | 79.2969 | 0.550639 |
| Captured reference, fixed reading | 87.8906 | 83.5938 | 0.560540 |
| Captured reference, matched averaging | 87.5000 | 83.2031 | 0.546061 |
| Captured reference held throughout repair | 83.2031 | 76.9531 | 0.542601 |

| Block | Residual input | Ordinary live | Captured live | Captured fixed | Captured averaging |
| --- | ---: | ---: | ---: | ---: | ---: |
| 30056 | 95.3125 | 93.7500 | 93.7500 | 96.8750 | 93.7500 |
| 30057 | 85.9375 | 92.1875 | 90.6250 | 92.1875 | 92.1875 |
| 30058 | 76.5625 | 84.3750 | 78.1250 | 84.3750 | 84.3750 |
| 30059 | 78.1250 | 81.2500 | 76.5625 | 78.1250 | 79.6875 |

Captured live loses 3.125 percentage points to ordinary live: equal in one
block, lower in three. Its small gain over unchanged input must not conceal
this stronger comparator loss. Higher continuous record correlation coexists
with lower recognition. Neither metric can substitute for the other.

The feedback comparison is a useful next clue. Captured live is 3.125 points
below captured fixed on residual records, versus 4.296875 points above fixed
on common records. This motivates an all-case saved-state diagnostic; it
does not yet explain the trajectory or separate R's maintenance/writing routes.

## Controls and evidence checks

In the common case, swapping to the partner body reverses captured-live
preference exactly (+55.859375 to −55.859375 points). Disabling writing leaves
the original packet and 50-percent recognition unchanged. Scrambling the own
body reduces recognition to 48.046875 percent and preference to +13.28125
points: organization matters, but the control does not eliminate all signal.
Erasing body history yields 33.59375-percent recognition and zero within-pair
preference. The analogous residual controls, every native comparison, all
93 named conditions and all 44 contrasts are retained in the full summary.

Intact parent and supplied-positive controls reach 100 percent in every block
and message. Disabled reading gives 25 percent pooled in every balanced block,
not necessarily in each message stratum. The original 144 D184 repair paths
and 204 readouts reproduce their saved arrays/scores exactly. All source
arrays match D079/D183; all 2,276 alias checks pass.

Every repair and unique read was independently replayed during execution,
sharing the native physical API rather than constituting clean-room physics.
The user-requested saved-only audit subsequently passed in 76.155 seconds,
rechecking all 1,392 frozen inputs, 1,157 outputs, four block receipts, full
panel membership, source/baseline bridges, scalar scores and summary. That
audit introduced no new dynamics and wrote no audit receipt; its successful
return is recorded in the conversation. The original COMPLETE binds the
execution's own saved verification and replay proofs.

## Cost, receipts and limits

Main completion: **2026-10-12 18:41:32.249125 UTC**. Actual runtime
**1672.506505 seconds (27m52.5s)**, one numerical thread on CPU 6 at nice 10.
The worker exited. Main outputs occupy **461,158,580 bytes (439.80 MiB)**;
uncompressed arrays total 714,981,888 bytes. Peak process RSS was
180,543,488 bytes (172.18 MiB). Stage retention at the user status check was
1,836,393,366 bytes (about 1.71 GiB), including both retained qualifications,
within the 2.5 GiB cap. All numerical files remain external; none was deleted.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-early-capture-panel-v1`.
Run: `l22_early_capture_v1_panel_attempt1`.
Full results: `outputs/<run>/SUMMARY.json`; individual scores, all saved
states and replay proofs: `outputs/<run>/tissue_<block>/`.

- Freeze SHA-256: `43577272aa18e5d07ca570fde0781b541aa6aa1914550f89bd1bedb0598fe3b9`.
- Manifest SHA-256: `be8b9faa8d864e56df579c71306030f2d0156334ed72cbec10c5507821b5fc0e`.
- COMPLETE SHA-256: `62df1ba07cfdaa45ca258890e717c1fcdd20671eb5f6595fc4d4021dd5c5c0e6`.
- Summary SHA-256: `adb4aa00678fe263a4cffd9aa8b92081bf160c90298cc0a986d9947fc70918ab`.

L20/L22 remain STRESS_TESTED / MIXED. This result supports a bounded source of
useful body-derived correction, not autonomous interface repair, a unique
mechanism, complete pattern preservation, prospective prediction superiority
or three-boundary renewal. The next approved step is retrospective diagnosis,
not a rate sweep, new pass threshold, new cohort or automatic renewal run.
