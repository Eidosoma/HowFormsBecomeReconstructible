# Paid checking v1 — execution checkpoint

**Completed 17 October 2026; verified and reported 18 October.**
See the [final report](FEP_PAID_CHECKING_V1_REPORT.md). Main execution finished
at 19:33:58 UTC on 17 October after 4h27m30s; independent saved-data verification
passed 4,959,630 assertions by 19:40:13 UTC. All 81 frozen inputs, three snapshots
and 231 manifest-listed outputs verify. No scientific run or required numerical
verification remains pending.

Reversal recovery improves .124026790 → .100231757 (19.19%), but the new interval
[.099320111, .101143404] spans always purchasing at .1. The paired gate passes;
the absolute and joint gates fail. Stable cost rises .081958333 → .088285880
(7.72%). The completed report retains the full costs, diagnostics and harms.

**Historical launch:** detached at 15:06:28 UTC on 17 October, startup verified
at 15:06:33 UTC. No main outcomes had been inspected at launch. The records
below preserve the launch and the subsequent requested progress check.

**Requested status check, 17 October at 15:45–15:46 UTC:** 32/216 chunks
completed (14.8%), representing 128 paired blocks and 3,200 paired episodes,
after about 39 minutes. The latest logged completion was at 15:45:21 UTC.
No run/readback failure record or completion manifest is present yet; no
scientific outcomes were inspected. A scoped host-process check at 15:46:36 UTC
confirmed the original coordinator and all four workers, matching start-time
identities, CPUs 0–3 and nice 10. Each worker has one thread and was runnable.
The current pace suggests roughly another 3¾ hours, subject to variation across
the remaining physical laws. All output remains on the external FEP store.

The [prospective specification](FEP_PAID_CHECKING_V1.md) tests whether earlier
paid evidence closes the structured controller's remaining reversal-recovery
gap. Both arms use the frozen 401-component model and CT4 task-cost planner.
The intervention allows at most one consecutive task without purchased
feedback. Its clock uses only its own past purchases, not the physical onset.
The planner does not anticipate the external rule in future branches.

Every actual purchase costs .1, including forced checks; overlapping planner
and rule purchases are charged once. Compare with the previous structured
controller and always purchasing. Success requires both a negative upper
paired 95% interval endpoint and an absolute recovery-cost upper endpoint below
.1. Stable/non-reversal harms remain separate and visible.

The fixed fresh cohort has 27 bases, 32 blocks per base, stable plus six change
families at onsets 13/38/63/88: 864 independent paired blocks, 21,600 paired
episodes and 4,320,000 policy decisions in 216 chunks. No earlier outcomes are
pooled; the supplied-feedback and completed autonomous results stay separate.

## Frozen inputs and qualification

The freeze was written at **15:00:01 UTC**, before main observations. It records
**81 input identities and three snapshots**. New seeds are distinct from all
11 earlier seed manifests and the synthetic qualification/benchmark streams.

Qualification passed on the first attempt in **50.08 seconds**: **4,264 runner
checks, 69 reused accounting checks and 23,169 independent readback checks**.
These include the checking clock, overlapping purchases, paid-label masks,
batch/scalar histories, unchanged structured baseline, disabled-rule identity,
terminal truncation, cost/regret reconstruction and serial/four-worker
fingerprints. The four synthetic workers used CPUs 0–3, nice 10 and one thread.

Interval qualification uses unequal dimensions and nonconstant blocks, an
explicit scalar loop over bases/blocks/conditions, different within-base block
permutations and an analytic variance fixture. It detects the old indexing
defect. The runner verifies cost-component variance closure. The prior pooled
analyzer is not used; its frozen source and disclosed correction are preserved.

FREEZE SHA-256:
`edeb8e6aefba5f534a529d7180b0e03cdb74e8ae259202e339dd0ae1a1078b20`.
QUALIFICATION SHA-256:
`8b5d4b789c62b919bdd7ce386d1d947a2f351c1e94ea606c7d7bf91d7514d0d6`.
Runner SHA-256:
`0b6fc6d0de2b2023780350a48e7b55e22aaf34d706f8192379bd2128d1cb0d79`.
Readback SHA-256:
`7b622a7913c2c6b50c8df70b059ed64ab9230092797d1ed1233efd90783fdb75`.

## Execution and storage

The four-worker benchmark used four synthetic blocks per worker and took
**287.00 seconds**. Linear scaling suggests **4 hours 18 minutes**; the fixed
conservative formula, `120 + 3 * benchmark_seconds * 864 / 16`, gives
**46,614.23 seconds (12 hours 57 minutes)**. The seven-day feasibility ceiling
passes. These are estimates, not observed completion times.

The detached coordinator PID/session/process group is **3948030** (start ticks
86757998), with workers **3948032–3948035**. Launch verification confirmed CPUs
0–3, nice priority 10, four workers with one numerical thread each, and the
coordinator's three management threads. All 81 frozen inputs still verify.
Qualification, preparation and startup verification passed on the first
scientific attempt, with no experiment correction or restart.

BENCHMARK SHA-256:
`0fd23456eabfd4c85cd0c9809e997f1f8d593e8e27aa7f242f289d20fef4330c`.

All generated records use
`/mnt/bioIce1/fep-ideas/formal-checks/fep-paid-checking-v1/attempt-01/`.
The durable logs are its siblings `attempt-01-prepare.log` and
`attempt-01-detached.log`. The ongoing detached stdout log is outside the
attempt so it cannot change a sealed output hash. Launch identity and resource
checks are in `LAUNCH.json`, `STARTED.json` and `LAUNCH_VERIFIED.json`.
The external ext4 mount on `/dev/sdc1` was verified with about 67 GB available.
All source and small notes remain in `fep-ideas/`.

After completion, the runner aggregated and invoked the independent saved-data
readback. It reconstructed actions, paid costs, diagnostic components and every
reported interval without running scientific policies. The readback passed in
374.88 seconds. No numerical failure, correction or restart occurred. No
automatic progress polling, retuning, gap sweep or successor is scheduled.

The final report and six live notes close this study. Reporting provenance uses
`reporting-2026-10-18/` outside the sealed main attempt. Preserve every unfavorable
condition and all paid checking costs. Do not extend the cohort, change the rule
or combine this fresh sample with earlier results. The proposed analytic design
for planning future checks has not been launched.

This is an acquisition intervention within the FEP track. It changes the
checking policy while holding inference and the planner fixed; it does not
introduce a canonical EFE or claim that the model discovered reversal structure.
Any improvement can combine immediate error avoidance and later learning.
