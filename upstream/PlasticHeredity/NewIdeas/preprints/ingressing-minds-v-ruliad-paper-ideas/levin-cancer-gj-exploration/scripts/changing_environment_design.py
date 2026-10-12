"""Frozen H4 v1 design. Task truth is separated from visible simulation inputs."""

import numpy as np

from memory_metrics import opposite
from run_pilot import REVISION

PREDECESSOR = "runs/reliability-confirmation-recovery-20260907T173445Z-a4rd3ibl"
POLICIES = dict(rewritable=(True, True), fixed=(True, False), reactive=(False, True), neither=(False, False))
REGIMES = dict(constant="AAAAAA", slow="AAABBB", rapid="ABABAB", misleading="AAABBB")
SEEDS = [2026090801, 2026090811]
FIXED = dict(revision=REVISION, input_run=PREDECESSOR, epochs=6, workers=2,
    worker_timeout_seconds=1800, total_budget_seconds=28800, packet_size=2, write_kd=2e-15,
    contact_horizon=1000, retention_horizons=[10000, 10000], recovery_horizon=5000,
    perturbation_fraction=.2, late_label_fraction=.95, minimum_challenge_distance=.1,
    recovery_absolute_tolerance=.02, recovery_distance_ratio=.2,
    cue_count=5, cue_horizon=100, cue_holds=[10000, 10000], seeds=SEEDS,
    nominal_epoch_duration=42100, costs=[0, .1, .3], minimum_free_bytes=5*1024**3)


def case_spec(policy, regime, seed, founder, fine=False):
    inherit, update = POLICIES[policy]
    return dict(id=f"{policy}__{regime}__{seed}__{founder}"+("_fine" if fine else ""),
        kind="main", policy=policy, regime=regime, seed=seed, state=founder,
        parent_enabled=inherit, cue_enabled=update, fine=fine)


def fixed_cases():
    cases = [case_spec(p, r, s, a) for r in REGIMES for s in SEEDS for a in ("M", "E") for p in POLICIES]
    cases += [case_spec(p, "misleading", SEEDS[1], a, True) for a in ("M", "E") for p in POLICIES]
    cases += [dict(id="benchmark__"+a+("_fine" if f else ""), kind="benchmark", state=a, fine=f)
        for a in ("M", "E") for f in (False, True)]
    return cases


def validate_config(config):
    if config != dict(FIXED, cases=fixed_cases()):
        raise ValueError("H4 v1 configuration differs from the frozen design")


def source_case(case):
    return dict(id=case["id"]+":source", state=case["state"],
        family="protein_m_pair" if case["state"] == "M" else "pooled_rewritten_e_pair",
        fine=case["fine"] if case["kind"] == "benchmark" else False)


def schedule(case):
    rng = np.random.Generator(np.random.PCG64(case["seed"]))
    order = rng.permutation(np.arange(2, 7)).tolist()
    available = [1]+sorted(order[:3])
    corrupt_order = rng.permutation(np.asarray(order[:3])).tolist()
    corrupt = set(corrupt_order[:2]) if case["regime"] == "misleading" else set()
    truth = [case["state"] if x == "A" else opposite(case["state"]) for x in REGIMES[case["regime"]]]
    visible = [None if i not in available else (opposite(label) if i in corrupt else label)
        for i, label in enumerate(truth, 1)]
    return dict(generator="PCG64", seed=case["seed"], availability_order=order,
        corruption_order=corrupt_order, available_epochs=available, corrupted_epochs=sorted(corrupt),
        hidden_truth=truth, visible_cues=visible, bootstrap_epoch=1)


def handover_plan(epoch, connected, benchmark=False):
    start = 0 if benchmark else 42100*(epoch-1)
    return dict(round=epoch, contacts=[1000, 1000], active_columns=[0, 1],
        write_kd=2e-15, connected=connected, nominal_start=start, nominal_end=start+22000,
        shock_factors=np.ones((2, 3, 2)).tolist())
