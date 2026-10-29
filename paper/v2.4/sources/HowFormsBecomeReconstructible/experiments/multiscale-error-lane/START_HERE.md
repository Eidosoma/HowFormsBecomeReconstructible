# Execution handoff — CPU first, 12 CPUs

**Design prepared 24 October 2026. No scientific campaign is frozen or running.**

Copy/paste task for the execution agent:

> Work in `HowFormsBecomeReconstructible/experiments/multiscale-error-lane/`. Read README, PROTOCOL, design.json and LESSONS_AND_SOURCE_MAP. Build and qualify the ME000 reference-based tissue implementation, then prepare and run the bounded ME001 development study on the allocated 12 CPUs. The scientific questions are how spatial discrepancies are sensed, how those signals cause correction, and whether correction helps present expression and future reconstruction. Keep sensing and actuation independently intervenable. Do not give an operational controller target images, injury labels/masks, pristine records or future scores. Retain all native outcomes, failures and costs. Do not modify other lanes or the manuscript, launch ME002 automatically, or use the shared GH200 before a CPU/GPU equivalence check and resource coordination. Produce a concise result handoff with paired block estimates, harms, source hashes, independent checks, and an explicit advancement recommendation.

## 1. Implement and qualify the apparatus

1. Check applicable repository instructions and existing reservations. Verify the [source fingerprints](SOURCE_MANIFEST.json); copy the required source into a versioned local implementation or independently restate it. Never patch or monkeypatch legacy campaigns. Record every difference from L15/L17; this is an extension with a different intervention schedule, not an unchanged replication.
2. Run `python3 check_design.py`. Implement the native sheet update and an independent scalar reference. With identity sensing/action, match the source update order, centering, clipping, noise placement and reference update. Include a retained native anchor where available; absence of its archive must be reported, not replaced with a claimed reproduction.
3. Implement separate interfaces for the operational controller, damage generator, evaluator and packet boundary. The controller sees only its specified sensor messages and fixed public settings. The evaluator alone receives targets/history labels. Verify exact zero-initialization of outgoing Q and that only Q crosses replacement. Recreate fixed theta independently of target identity. A constant/off reader must make recipient trajectories packet-independent under common draws.
4. Reserve disjoint engineering, development and later confirmation identities before sampling. Use explicit RNG addresses for block, parent, damage and future; pair draws across arms without passing a condition name to the stochastic physics. Save reservations and declare the limits of the identity search.
5. Freeze code, design, numerical tolerances, output schema and qualification conditions before generating qualification or development outcomes. Validate finite states, immutable inputs, full-cohort enumeration, aliases, per-site scores, source-block pooling, serial-vs-parallel determinism and a small complete independent replay. Qualification must establish a working known-reference reader and a perturbation that actually changes state; set these checks before seeing their results. If calibration fails, retain it and stop the scientific campaign.

## 2. Benchmark the complete workload

Use engineering-only identities. Time **teaching, damage, every branch, capture, fresh readings, independent replay, saving and analysis**, not a single update kernel. Engineering outcomes cannot justify changing targets, effect thresholds or selecting good founders.

- Allocate up to **12 worker processes**, one CPU thread each; set BLAS/OpenMP thread counts to one. Do not nest process pools. Identify the allocated CPU set rather than assuming CPUs 0–11 are free.
- Parallelize independent source blocks. Batch matched arms/readouts inside a worker; use a predeclared batch size limited by measured memory. Workers save immutable shards; the coordinator writes manifests and summaries.
- Record measured peak RAM, free disk, wall time and total CPU time. Keep at least 20% RAM and disk headroom after the estimated campaign allocation. The draft ME001 wall-time ceiling is 48 hours; it is a planning bound, not a throughput prediction.
- If the complete forecast exceeds that ceiling, report the measured bottleneck and a revised pre-outcome design or longer-run requirement. Do not silently drop arms, future draws, unsuccessful cases or audit work.
- Store raw arrays outside git in a lane-specific run root supplied at launch. Commit compact tables, manifests, scripts and reports. Do not assume `/mnt/bioIce1` is mounted on the execution machine. Use atomic completion records, resumable immutable block shards, exclusive run locks and a detached process for long work. Never kill another lane's job.

## 3. Run ME001 and deliver the development result

Follow the frozen design. Do not stop early for a favorable effect, replace a failed founder or tune gains while reading results. Technical failures invalidate affected execution and must be reported separately from scientific failures; retries need an explicit lineage of manifests and cannot erase the first attempt.

Deliver `REPORT.md`, compact per-block and per-case tables, a source/run manifest, independent-check receipt and a manuscript handoff. Show:

- body-directed, reference-directed, reciprocal and inactive routes across body/record/both damage;
- sensing-versus-actuation contrasts, with algebraic aliases identified;
- sensor traces, sham false alarms and missed functionally consequential disturbances; distinguish injury detection from detection of useful-information loss;
- sign-only fidelity, amplitude eligibility, qualified agreement and own-versus-foreign specificity separately;
- current-body effects and fresh-recipient effects on the same cases, with rescue/harm counts;
- all four spatial error components, actual intervention dose, record bytes, reads/writes, messages and compute;
- failure of a signal to identify which source is trustworthy where that information is absent.

ME001 is development, not fresh confirmation of a selected policy. Propose at most one frozen operational selector for ME002, plus a strong fixed-route comparator and a local-information comparator, with an equal-budget assessment. Keep an explicit no-policy conclusion if the signals cannot support a useful choice.

## 4. Later ambition

ME002 tests the frozen selector on untouched blocks. ME003 adds many independent futures and up to sixteen replacement boundaries. ME004 challenges new pattern families, displaced pooling grids, larger sheets and delayed/local communication. These are separate prospective studies; a positive first result does not authorize declaring the others established.

For GH200 use, first compare float64 CPU and GPU trajectories under externally supplied identical random arrays, including near-threshold cases and all scores. Then distinguish ordinary numerical drift from scientifically consequential endpoint changes. Keep CPU as the reference, report precision and reduction order, and benchmark complete end-to-end throughput. Shared GPU access is not an exclusive allocation; schedule around other users and retain a CPU-only completion route.
