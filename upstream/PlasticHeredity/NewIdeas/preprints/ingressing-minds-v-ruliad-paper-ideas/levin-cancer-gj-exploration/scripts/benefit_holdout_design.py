"""Prespecified H4b stochastic histories; no native outcome selects a schedule."""

import numpy as np

from changing_environment_design import FIXED as H4_FIXED, POLICIES
from analyze_changing_environment import expected_schedule as h4_schedule

PREDECESSOR = "runs/changing-environment-20260907T191331Z-bvq74cne"
SEEDS = [20260908101, 20260908102, 20260908103, 20260908104]
PROFILES = dict(slow_reliable=(.15, .60, 0.), fast_reliable=(.75, .60, 0.),
    slow_sparse=(.15, .25, 0.), slow_noisy=(.15, .60, .25))
COSTS = [0., .025, .05, .075, .1, .15, .2, .3]
FIXED = dict(H4_FIXED, input_run=PREDECESSOR, epochs=12, prefix_epochs=2, prefix_cases=8,
    seeds=SEEDS, profiles={k: list(v) for k, v in PROFILES.items()}, costs=COSTS,
    worker_timeout_seconds=3600, total_budget_seconds=86400,
    planned_cases=144, planned_integrations=28016, planned_fresh_recipients=3296,
    prefix_gate_required=True, binary_reference_rule=True)


def case_spec(policy, profile, seed, state, fine=False):
    parent, cue = POLICIES[policy]
    return dict(id=f"holdout__{policy}__{profile}__{seed}__{state}"+("_fine" if fine else ""),
        kind="main", policy=policy, profile=profile, seed=seed, state=state,
        parent_enabled=parent, cue_enabled=cue, fine=fine)


def prefix_case(policy, state):
    parent, cue = POLICIES[policy]
    return dict(id=f"prefix__{policy}__{state}", kind="prefix", policy=policy,
        state=state, fine=False, parent_enabled=parent, cue_enabled=cue,
        legacy_case_id=f"{policy}__misleading__2026090811__{state}")


def fixed_cases():
    cases = [prefix_case(p, a) for a in ("M", "E") for p in POLICIES]
    cases += [case_spec(p, r, s, a) for r in PROFILES for s in SEEDS for a in ("M", "E") for p in POLICIES]
    cases += [case_spec(p, "slow_noisy", SEEDS[-1], a, True) for a in ("M", "E") for p in POLICIES]
    return cases


def validate_config(config):
    if config != dict(FIXED, cases=fixed_cases()):
        raise ValueError("H4b v1 configuration differs from its fixed specification")


def schedule(case):
    if case["kind"] == "prefix":
        old = h4_schedule(dict(seed=2026090811, regime="misleading", state=case["state"]))
        return dict(generator="historical_H4_prefix", legacy_case_id=case["legacy_case_id"],
            hidden_truth=old["hidden_truth"][:2], visible_cues=old["visible_cues"][:2], bootstrap_epoch=1)
    flips, availability, error = PROFILES[case["profile"]]
    raw = np.random.Generator(np.random.PCG64(case["seed"])).random((11, 3))
    other = {"E": "M", "M": "E"}
    truth, visible = [case["state"]], [case["state"]]
    for uf, ua, ue in raw:
        truth.append(other[truth[-1]] if uf < flips else truth[-1])
        visible.append((other[truth[-1]] if ue < error else truth[-1]) if ua < availability else None)
    return dict(generator="PCG64", seed=case["seed"], raw_uniform=raw.tolist(),
        columns=["world_flip", "cue_available", "cue_incorrect"],
        probabilities=dict(flip=flips, available=availability, incorrect=error),
        hidden_truth=truth, visible_cues=visible, bootstrap_epoch=1,
        resampling=False, forced_post_bootstrap_events=False)


def protocol_counts(cases=None):
    cases = fixed_cases() if cases is None else cases
    epochs = sum(len(schedule(c)["visible_cues"]) for c in cases)
    cues = sum(sum(x is not None for x in schedule(c)["visible_cues"]) for c in cases)
    return dict(cases=len(cases), integrations=epochs*17, fresh_recipients=epochs*2, cue_cells=cues*10)
