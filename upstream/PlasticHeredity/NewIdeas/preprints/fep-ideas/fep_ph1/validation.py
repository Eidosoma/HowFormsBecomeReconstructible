from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from fep_lab.integrity import seal_directory, write_json
from fep_lab.pymdp_backend import PymdpBackend
from fep_lab.reference import ReferenceBackend

from .config import CANDIDATES, ExperimentConfig, regime_specs
from .environment import EnvironmentDesign
from .gard import (
    advance_fission,
    apply_ranked_substitution,
    generate_beta,
    generate_initial_composition,
    normalized_gate,
    simultaneous_permutation,
    variance_restored_log_morph,
)
from .inference import FastInferenceBackend
from .models import (
    ModelCounts,
    adjust_policy_costs,
    model_from_counts,
)
from .simulation import controller_for, run_episode
from .types import ActionChannel, ControllerName, EnvironmentFamily, ObservationThresholds


NEUTRAL_REFERENCE = {
    "02": (
        "d8b3a4014886748e1c13a08d7d1a9ca0a4c6065801b0fbaa2b7367782790e20a",
        "b8d429ac476455badaf0935fa256ea5403a51a89327bd22a93f16e38706b1b0b",
    ),
    "03": (
        "d841d340312c7cc7b77ae2459172e1f4e618191aec72237f91e19ba7c12de255",
        "213abc36bc855e6a6dfbb381e871152877ddf7ddae4141605fe2874cff32def9",
    ),
}


def _check(name: str, passed: bool, **evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def _neutral_digest(config: ExperimentConfig, candidate: str) -> tuple[str, str]:
    beta = generate_beta(config.gard, np.random.default_rng(101))
    current = generate_initial_composition(config.gard, np.random.default_rng(102))
    rng = np.random.default_rng(103)
    digest = hashlib.sha256()
    for _ in range(8):
        record = advance_fission(
            current, beta, config.gard, CANDIDATES[candidate], rng
        )
        digest.update(np.ascontiguousarray(record.parent).tobytes())
        digest.update(np.ascontiguousarray(record.daughter).tobytes())
        digest.update(np.asarray((record.h,), dtype=np.float64).tobytes())
        digest.update(np.asarray((record.growth_steps,), dtype=np.int64).tobytes())
        current = record.daughter
    rng_digest = hashlib.sha256(
        json.dumps(rng.bit_generator.state, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return digest.hexdigest(), rng_digest


def _uniform_counts() -> ModelCounts:
    counts = ModelCounts.empty()
    for state in range(9):
        observation = (state % 4, state % 3, (state // 3) % 3, state % 4)
        counts.add_initial(state, observation)
        for action in range(4):
            counts.add_transition(state, action, (state + action + 1) % 9, observation)
    return counts


def validate_experiment(
    config: ExperimentConfig, output: Path, source_digest: str | None = None
) -> dict[str, Any]:
    config.validate()
    checks: list[dict[str, Any]] = []
    for candidate in ("02", "03"):
        observed = _neutral_digest(config, candidate)
        checks.append(
            _check(
                f"neutral_retained_identity_{candidate}",
                observed == NEUTRAL_REFERENCE[candidate],
                record_digest=observed[0],
                rng_digest=observed[1],
            )
        )

    beta = generate_beta(config.gard, np.random.default_rng(201))
    order = np.random.default_rng(202).permutation(config.gard.n_types)
    permuted = simultaneous_permutation(beta, order)
    morphed = variance_restored_log_morph(beta, permuted, 0.35)
    base_log = np.log(beta)
    morph_log = np.log(morphed)
    checks.append(
        _check(
            "catalytic_morph_preserves_log_moments",
            abs(float(base_log.mean() - morph_log.mean())) < 1e-12
            and abs(float(base_log.std() - morph_log.std())) < 1e-12,
            mean_difference=float(morph_log.mean() - base_log.mean()),
            sd_difference=float(morph_log.std() - base_log.std()),
        )
    )
    gate = normalized_gate(np.linspace(-1.0, 1.0, 100), 1, config.gate_strength)
    checks.append(
        _check(
            "uptake_gate_mean_normalized",
            abs(float(gate.mean()) - 1.0) < 1e-12 and np.all(gate > 0.0),
            mean=float(gate.mean()),
        )
    )
    composition = generate_initial_composition(config.gard, np.random.default_rng(203))
    edited, remove, add = apply_ranked_substitution(
        composition, np.linspace(-1.0, 1.0, config.gard.n_types)
    )
    checks.append(
        _check(
            "molecular_action_mass_conserving",
            int(edited.sum()) == int(composition.sum())
            and np.all(edited >= 0)
            and remove >= 0
            and add >= 0,
            l1_change=int(np.abs(edited - composition).sum()),
        )
    )

    counts = _uniform_counts()
    model = model_from_counts(counts, config)
    reference = ReferenceBackend()
    production = PymdpBackend()
    observation = (0, 0, 0, 0)
    left_state = reference.infer_states(model, observation, model.D)
    right_state = production.infer_states(model, observation, model.D)
    left_policy = adjust_policy_costs(
        model, reference.score_policies(model, left_state.posterior), config
    )
    right_policy = adjust_policy_costs(
        model, production.score_policies(model, right_state.posterior), config
    )
    fast = FastInferenceBackend(model, config)
    fast_state = fast.infer_states(observation, model.D)
    fast_policy = fast.score_policies(fast_state.posterior)
    dual_pass = (
        np.allclose(left_state.posterior, right_state.posterior, atol=1e-8, rtol=0.0)
        and np.allclose(left_policy.neg_efe, right_policy.neg_efe, atol=1e-7, rtol=0.0)
        and np.allclose(left_policy.posterior, right_policy.posterior, atol=1e-7, rtol=0.0)
        and np.allclose(left_state.posterior, fast_state.posterior, atol=1e-12, rtol=0.0)
        and np.allclose(left_policy.neg_efe, fast_policy.neg_efe, atol=1e-12, rtol=0.0)
        and np.allclose(left_policy.posterior, fast_policy.posterior, atol=1e-12, rtol=0.0)
    )
    checks.append(
        _check(
            "dual_backend_inference_and_costed_efe",
            dual_pass,
            posterior_max_difference=float(
                np.max(np.abs(left_state.posterior - right_state.posterior))
            ),
            efe_max_difference=float(
                np.max(np.abs(left_policy.neg_efe - right_policy.neg_efe))
            ),
            fast_efe_max_difference=float(
                np.max(np.abs(left_policy.neg_efe - fast_policy.neg_efe))
            ),
        )
    )

    design = EnvironmentDesign(
        EnvironmentFamily.CATALYTIC,
        ActionChannel.UPTAKE,
        regime_specs()[0],
        "02",
        300,
        301,
    )
    initial = generate_initial_composition(config.gard, np.random.default_rng(302))
    variants = {
        "reward_pooled": model,
        "reward_local": model,
        "scrambled": model,
        "reversed": model,
    }
    lesion_controller = controller_for(
        ControllerName.ACTION_LESION, config, model, model, variants
    )
    noop_controller = controller_for(
        ControllerName.NOOP, config, model, model, variants
    )
    process_seeds = (303, 304, 305)
    lesion = run_episode(
        config,
        design,
        beta,
        initial,
        ObservationThresholds(),
        ControllerName.ACTION_LESION,
        lesion_controller,
        process_seeds,
        306,
    )
    noop = run_episode(
        config,
        design,
        beta,
        initial,
        ObservationThresholds(),
        ControllerName.NOOP,
        noop_controller,
        process_seeds,
        307,
    )
    lesion_exact = all(
        np.array_equal(lesion[name], noop[name], equal_nan=True)
        for name in (
            "completed",
            "growth_steps",
            "similarity",
            "result_regime",
            "executed_actions",
            "compositions",
        )
    )
    checks.append(
        _check(
            "action_lesion_physics_matches_noop",
            lesion_exact and np.all(lesion["executed_actions"] == 0),
        )
    )

    objective_modules = ("models.py", "controllers.py", "environment.py", "worker.py")
    protocol_sources = " ".join(
        (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")
        for name in objective_modules
    ).lower()
    firewall_pass = "strict_8" not in protocol_sources and "strict-8" not in protocol_sources
    checks.append(_check("strict_event_objective_firewall", firewall_pass))

    result = {
        "schema": "fep-ph1-validation-v1",
        "profile": config.profile,
        "source_digest": source_digest,
        "all_pass": all(check["passed"] for check in checks),
        "checks": checks,
        "claim_boundary": (
            "Engineered active-inference/GARD coupling validation; not evidence that "
            "unmodified GARD performs active inference or has an emergent blanket."
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "validation.json", result)
    seal_directory(output, ["validation.json"])
    return result
