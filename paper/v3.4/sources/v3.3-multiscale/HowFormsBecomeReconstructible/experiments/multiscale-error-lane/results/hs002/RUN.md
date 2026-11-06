# HS002 phase B: the run record (fork H1, 1 November 2026)

The frozen reader's outputs are `summary.json`, `TABLES.md` and `predictions_scored.json` (the development, 128
blocks at both budgets) and the `_e014` files (the reported continuation of E014's 64 published lineages at 2,048
bytes). `EXPORT_MANIFEST.json` is the identity export's manifest at the development's eight new checkpoints.
Rewrites 1-256 are HS001's frozen shards; 320-1,024 are HS002's continuation of the same lineages from HS001's saved
rewrite-256 records. Units: percentage points of E014's qualified agreement Q against the own founder; 95%
whole-block intervals with E014's generator (10,000 resamples). Every curve is read by rule AH (`hs002.fit.reading`),
with the drift bound and the reading as first declared beside it.

## Commits and stages

- **Freeze:** ac7e5f8eb3 (19:03:33Z, pushed 19:03:38Z), design digest a749f0b50ac4, 27 source hashes.
- **Preflight:** 950020-950021, 19:05:10-19:14:40Z on 2 workers, 1,140 CPU-s, peak worker RSS 45.5 MB. A first
  launch at 19:03:54Z, over the load gate, was stopped before any task finished (the slips).
- **Q1-Q10:** PASS, all ten, 19:27:11-19:53:36Z, 1,581 CPU-s on one core. Receipt commit 98f50016e6 (committed
  about 19:55:08Z, pushed 19:55:11Z); it names the freeze commit in the registration's header.
- **The load gate, then the PI's word.** From 19:55:48Z the development waited for the load gate (the 1-minute load
  less A3's running workers below 46); other users' jobs held the net load at 58.6-65.4 in the waiting lines. The
  lead asked the PI whether to raise the limit so HS002 could start sooner. The PI replied **"lets go"** (about
  20:43Z), then **"lets work in parallel"** (about 20:44Z), relayed by the lead, and the gate was lifted for HS002's
  development and E014's continuation. The waiting launcher was stopped by PID (it had launched nothing). Both
  stages ran without the gate at nice 10, which keeps them behind the other users' jobs, on cores in 37-71.
- **Development:** 951000-951127 (128 blocks, both budgets), 20:45:22-22:31:04Z on 12 workers, 128 of 128 tasks:
  73,422 CPU-s (20.40 CPU-hours), 6,342 s of wall, peak worker RSS 54.1 MB, 767 MB written (the identity export
  included).
- **The cap check** before E014's continuation: the development plus E014's forecast from it, 25.49 CPU-hours,
  within 30.
- **E014's continuation:** 12000-12063 (64 blocks, 2,048 bytes), 22:31:09-22:59:07Z on 12 workers, 64 of 64 tasks:
  17,953 CPU-s (4.99 CPU-hours), 1,678 s of wall, peak worker RSS 45.5 MB, 90 MB written. No identity export, as
  registered.
- **The frozen reader:** 23:00:19-23:02:12Z, two single processes, 156 CPU-s.
- **In all:** the development and E014's continuation 91,375 CPU-s, **25.38 CPU-hours** (Q9's forecast 25.34 on the
  preflight, 25.03 at the freeze), against the cap of 30. Phase B with the preflight, the checks and the reader:
  94,252 CPU-s (26.18 CPU-hours). Phase A: about 2.6 CPU-hours (the registration).

## Registered statements (128 development blocks): 3 of 3 HOLD

| Part | Value [95%] | Threshold | |
|---|---|---|---|
| H1, 2,048 B, Q(rewrite) - Q(erased) at 1,024 | +16.465 [+15.354, +17.608] | >= 8 | holds |
| H1, 2,048 B, Q(foreign) - Q(erased) at 1,024 | +15.546 [+14.369, +16.734] | >= 8 | holds |
| H1, 128 B, Q(rewrite) - Q(erased) at 1,024 | +17.883 [+16.782, +18.976] | >= 9 | holds |
| H1, 128 B, Q(foreign) - Q(erased) at 1,024 | +16.719 [+15.539, +17.897] | >= 7 | holds |
| H2, 128 B, D(1024) - D(256) | -0.018 [-0.042, +0.005] | in [-0.3, +0.3] | holds, both sides |
| H3, 2,048 B, Q(rewrite) - Q(copy) at 1,024 | -13.240 [-13.914, -12.537] | <= -8 | holds |
| H3, 128 B, Q(rewrite) - Q(copy) at 1,024 | -3.458 [-4.003, -2.944] | <= -1 | holds |

Formation qualified 83.59% of founders.

## The prespecified measurements (the answer to "a plateau or a slow drift"), development

| | 2,048 bytes (registered, M-a to M-d) | 128 bytes (reported) |
|---|---|---|
| The reference Delta_P (HS001's, constant) | +2.198 [+1.941, +2.458] (124 of 128 blocks positive; resolved) | +1.387 [+1.133, +1.649] (106 of 128; resolved) |
| D after 1, 16, 256, 512, 1,024 | +1.997, +1.260, +1.012, +0.816, +0.919 [+0.603, +1.244] | +1.393, +1.216, +1.182, +1.170, +1.163 [+0.823, +1.513] |
| **M-a, D's reading (rule AH)** | **a plateau within 1,024 rewrites.** Drift bound: a decay toward zero needs a half-life of at least 11,152 rewrites. As first declared: a plateau | **a plateau within 1,024 rewrites.** At least 13,604. As first declared: a plateau |
| M1 | c +0.958 [+0.640, +1.253], a +0.888, h 8.37 [4.17, 122.21] (identified) | c +1.181 [+0.836, +1.520], a +0.216, h 2.88 [0.56, 50.92] (identified) |
| M2 | c +0.823 [+0.475, +1.124]; h2 177.93 [21.81, 549.90], not identified, so M2's c does not count | c +1.172 [+0.824, +1.520]; h2 35.91 [0.58, 66.81], identified, c above zero |
| M0 (decay to zero) | half-life 851 [462, 1,449]; SSE(M0) - SSE(M1) +0.911 [+0.194, +1.926] | half-life 8,092 [2,619, 100,000]; SSE(M0) - SSE(M1) +0.064 [+0.003, +0.350] |
| **M-b, model-free** | D(1024) - D(512) **+0.103 [-0.026, +0.242]**; D(1024) - D(256) -0.093 [-0.273, +0.089]; late mean (768, 896, 1,024) +0.856 [+0.553, +1.165] | -0.007 [-0.030, +0.016]; -0.018 [-0.042, +0.005]; +1.170 [+0.831, +1.516] |
| **M-c, R_H** after 1, 16, 256, 512, 1,024 | 0.908, 0.573, 0.461, 0.371, **0.418 [0.288, 0.543]** | 1.004, 0.877, 0.852, 0.844, **0.839 [0.640, 1.044]** |
| R_H's reading | **a plateau within 1,024 rewrites:** M1 c +0.436 [+0.307, +0.543]; R_H(1024) - R_H(512) +0.047 [-0.012, +0.110]; at least 11,259. As first declared: a plateau | a plateau: c +0.851 [+0.652, +1.051]; -0.005 [-0.022, +0.012]; at least 13,220. As first declared: a plateau |
| **M-d, basins** (concordance excess at 1,024: rewrite, foreign; erased, background) | **kept to 1,024:** +6.984 [+5.352, +8.646], +6.898 [+5.288, +8.548]; -0.715 [-2.816, +1.310], -0.703 [-2.080, +0.716] | kept: +7.959 [+6.217, +9.688], +7.751 [+6.095, +9.416]; -1.265 [-3.198, +0.696], +0.321 [-0.960, +1.628] |
| Reported: the floor Q(rewrite) - Q(erased) at 256, 512, 1,024 | +17.067, +16.689, +16.465 | +17.902, +17.889, +17.883 |
| The floor's reading | **a slow drift:** X(1024) - X(512) -0.224 [-0.370, -0.087]; X(1024) - X(256) -0.602 [-0.840, -0.385]; M1 c +17.063 [+15.978, +18.178], h 5.68 [5.20, 6.23]; M2 c +16.535 [+15.424, +17.663], h2 139.28 [72.29, 213.80] (identified); a decay toward zero would need a half-life of at least 15,844 rewrites. As first declared: a slow drift | a plateau: -0.006 [-0.039, +0.027]; M1 c +17.917 [+16.824, +19.000], h 2.81 [2.31, 3.53]; at least 164,597. As first declared: a plateau |

- **The readings, by the frozen rules:**
  - At 2,048 bytes the founder-specific contrast D reads as a plateau within 1,024 rewrites. D falls from +2.0
    after one rewrite to +1.012 at 256 and +0.816 at 512, then holds: +0.816, +0.818, +0.832 and +0.919 at
    640-1,024. The second half's change, +0.103 [-0.026, +0.242], excludes a fall of more than 0.026, and a decay
    toward zero would need a half-life of at least 11,152 rewrites. A slower drift is not excluded (the plateau's
    registered meaning), and for a curve whose asymptote is zero a cohort-wide block-level offset reads as a
    plateau at about 2.5% a cohort (the registered caveat).
  - HS001's flag (M2 absorbing the plateau into a slow second timescale) is resolved in this sense: over 1,024
    rewrites M2 keeps its c above zero, +0.823 [+0.475, +1.124]. Its slow timescale, h2 178 [22, 550], is not
    identified under the rule, so M2 counts neither way.
  - About 0.42 of the protected records' readable specificity remains after 1,024 rewrites at 2,048 bytes (R_H
    0.418 [0.288, 0.543], its plateau 0.436), against 0.461 at 256.
  - At 128 bytes the curve is flat from 256 to 1,024 (H2 holds), and about 0.84 remains.
  - The founder-free floor at 2,048 bytes still falls slowly: a slow drift by rule AH, -0.224 [-0.370, -0.087] over
    the second half, while it stays far above its threshold (H1, +16.465). The record-versus-no-record contrast
    drifts; the founder-specific contrast is not shown to.
  - Basins are kept to 1,024 at both budgets.
  - Every reading under rule AH equals the reading as first declared, here and in E014's continuation.

## E014's continuation (64 published lineages, 2,048 bytes; reported, not registered)

| | 2,048 bytes |
|---|---|
| The reference | +2.618 [+2.198, +3.070] (64 of 64 blocks positive; resolved) |
| D after 1, 16, 256, 512, 1,024 | +2.103, +1.402, +0.987, +1.138, **+1.263 [+0.730, +1.830]** |
| D's reading | **a plateau within 1,024 rewrites:** M1 c +1.104 [+0.631, +1.594], a +0.972, h 7.23 [3.61, 15.22]; M2's h2 not identified (its upper bound at the grid's edge, 129,999), so M2 does not count; at least 8,502. As first declared: a plateau |
| Model-free | D(1024) - D(512) +0.125 [-0.047, +0.317]; D(1024) - D(256) **+0.276 [+0.038, +0.494]** (a rise); late mean +1.254 [+0.729, +1.800] |
| R_H after 1, 16, 256, 512, 1,024 | 0.803, 0.536, 0.377, 0.435, **0.483 [0.298, 0.659]**; a plateau: c +0.422 [+0.260, +0.581]; at least 7,965. As first declared: a plateau |
| The floor at 256, 512, 1,024 | +16.505, +16.295, +16.218; a plateau: M1 c +16.587 [+14.959, +18.198]; X(1024) - X(512) -0.077 [-0.304, +0.141]; at least 18,865. As first declared: a plateau |
| Basins (concordance excess at 1,024) | kept to 1,024: rewrite +8.192 [+5.916, +10.627], foreign +7.509 [+5.052, +10.201]; erased +2.734 [-0.025, +5.483] (its interval just includes zero), background -1.138 [-3.100, +0.951] |

Formation qualified 75.39% of founders. The published cohort agrees in kind with the development at 2,048 bytes: D
and R_H plateau, with no fall in the second half; here D rose from 256 to 1,024.

## Files

- **In git** (each 256 KB or less): this record; `summary.json` (175,836 B), `TABLES.md`, `predictions_scored.json`,
  `EXPORT_MANIFEST.json` (74,926 B); `summary_e014.json` (86,779 B), `TABLES_e014.md`.
- **On scratch** (`/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/hs002/`): the shards, raw records and
  done files of both stages; the identity export (`development/export/`, 128 files; its manifest is here); the
  reader's `arrays.npz` (3.1 MB and 0.9 MB); `progress.md`; the launchers and the gate (`tools/`).

## Slips (disclosed)

- **The preflight first launched over the load gate** at 19:03:54Z: a net load of 46.97 by my count (60.97 less 14
  A3 processes), 48.97 by the rule's (less A3's 12 running workers), against 46. I stopped it by PID at 19:04:16Z,
  before any task finished. Its root is kept as `preflight_stopped_over_gate/` (coordinator.pid and
  manifest_start.json only).
- **A relaunch at 19:04:35Z failed at once, with nothing run.** The module environment that activate.sh loads sets
  STAGE=2026, which overwrote the launcher's STAGE argument, so run.py refused `--stage 2026`. progress.md's line
  "2026 launched on cores 42,44" is that failed launch. By the rule's count it would also have been over the gate
  (46.71).
- **The launchers' gate counted A3's 14 processes** (its coordinator, 12 workers and a shell), not its 12 running
  workers, so it was lenient by 2. It was fixed (`tools/gate.py`) before any later launch. The 19:05:10Z preflight
  launch was under the gate by either count (41.27, or 43.27 by the rule's).
- **My stream stalled** from about 19:05Z until the lead's message at about 19:20Z. The preflight ran unattended and
  finished normally.
- **Q1-Q10 first waited on the gate** (19:22:58-19:26:51Z). On the lead's word, single-process stages run without
  it.
- **A label in the frozen tables:** in `TABLES.md` and `TABLES_e014.md` the model-free line under R_H and under the
  floor reads "D(1024) - D(512)" and "D(1024) - D(256)". The values are that curve's own changes (`hs002.fit.summarise`
  on the curve read); only the label names D. This record writes X for them.
- **Phase A's slip** (a mis-split core list delayed the 128-byte bridge by a minute) is in the registration.
