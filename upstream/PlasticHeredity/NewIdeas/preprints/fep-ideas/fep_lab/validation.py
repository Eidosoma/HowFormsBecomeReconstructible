from __future__ import annotations

from dataclasses import replace
from itertools import product
from pathlib import Path

import numpy as np

from .blanket import build_blanket_model, impulse_response
from .config import LabConfig
from .homeostat import build_homeostat_model
from .integrity import seal_directory, verify_seal, write_json
from .pymdp_backend import PymdpBackend, dependency_versions
from .reference import ReferenceBackend, entropy, variational_free_energy


def _check(name: str, passed: bool, **details: object) -> dict[str, object]:
    return {"name": name, "passed": bool(passed), **details}


def _expected_regime_entropy(model: object, action: int) -> float:
    categorical = model
    prior = categorical.B[:, :, action] @ categorical.D
    expected = 0.0
    for observation in product(*(range(value.shape[0]) for value in categorical.A)):
        likelihood = np.ones(categorical.n_states, dtype=np.float64)
        for modality, observed in zip(categorical.A, observation):
            likelihood *= modality[observed]
        evidence = float(prior @ likelihood)
        if evidence <= 0.0:
            continue
        posterior = prior * likelihood / evidence
        regime = np.asarray([posterior[:6].sum(), posterior[6:].sum()])
        expected += evidence * entropy(regime)
    return float(expected)


def validate_lab(
    config: LabConfig, output: Path, force: bool = False
) -> dict[str, object]:
    if verify_seal(output) and not force:
        from .integrity import read_json

        return read_json(output / "validation.json")
    output.mkdir(parents=True, exist_ok=True)
    reference = ReferenceBackend()
    production = PymdpBackend()
    checks: list[dict[str, object]] = []

    for scenario in ("epistemic", "known", "disturbed"):
        for variant in ("standard", "epistemic_lesion", "scrambled", "reversed"):
            model = build_homeostat_model(scenario, variant)  # type: ignore[arg-type]
            try:
                model.validate()
                passed = True
            except ValueError:
                passed = False
            checks.append(_check(f"normalized:{scenario}:{variant}", passed))

    model = build_homeostat_model("epistemic", "standard")
    observation = (2, 1)
    inferred = reference.infer_states(model, observation, model.D)
    likelihood = model.A[0][observation[0]] * model.A[1][observation[1]]
    checks.append(
        _check(
            "vfe_equals_negative_log_evidence",
            abs(inferred.vfe + inferred.log_evidence) <= 1e-10,
            error=abs(inferred.vfe + inferred.log_evidence),
        )
    )
    perturbed = 0.9 * inferred.posterior + 0.1 / model.n_states
    perturbed_vfe = variational_free_energy(perturbed, model.D, likelihood)
    checks.append(
        _check(
            "posterior_minimizes_vfe",
            perturbed_vfe >= inferred.vfe - 1e-10,
            optimum=inferred.vfe,
            perturbed=perturbed_vfe,
        )
    )

    rng = np.random.default_rng(774912)
    maximum_posterior_error = 0.0
    maximum_vfe_error = 0.0
    maximum_efe_error = 0.0
    maximum_policy_error = 0.0
    fixture_count = 0
    fixture_models = (
        build_homeostat_model("epistemic", "standard"),
        build_homeostat_model("epistemic", "epistemic_lesion"),
        build_homeostat_model("disturbed", "reversed"),
    )
    for fixture_model in fixture_models:
        priors = [fixture_model.D]
        priors.extend(rng.dirichlet(np.ones(fixture_model.n_states)) for _ in range(3))
        for prior in priors:
            for obs in product(*(range(value.shape[0]) for value in fixture_model.A)):
                left = reference.infer_states(fixture_model, obs, prior)
                right = production.infer_states(fixture_model, obs, prior)
                left_policy = reference.score_policies(fixture_model, left.posterior)
                right_policy = production.score_policies(fixture_model, right.posterior)
                maximum_posterior_error = max(
                    maximum_posterior_error,
                    float(np.max(np.abs(left.posterior - right.posterior))),
                )
                maximum_vfe_error = max(
                    maximum_vfe_error, abs(left.vfe - right.vfe)
                )
                maximum_efe_error = max(
                    maximum_efe_error,
                    float(np.max(np.abs(left_policy.neg_efe - right_policy.neg_efe))),
                )
                maximum_policy_error = max(
                    maximum_policy_error,
                    float(np.max(np.abs(left_policy.posterior - right_policy.posterior))),
                )
                fixture_count += 1
    checks.extend(
        (
            _check(
                "dual_engine_posterior",
                maximum_posterior_error <= 1e-8,
                maximum_error=maximum_posterior_error,
                fixtures=fixture_count,
            ),
            _check(
                "dual_engine_vfe",
                maximum_vfe_error <= 1e-8,
                maximum_error=maximum_vfe_error,
            ),
            _check(
                "dual_engine_neg_efe",
                maximum_efe_error <= 1e-7,
                maximum_error=maximum_efe_error,
            ),
            _check(
                "dual_engine_policy_posterior",
                maximum_policy_error <= 1e-7,
                maximum_error=maximum_policy_error,
            ),
        )
    )

    permutation = rng.permutation(model.n_states)
    relabeled = replace(
        model,
        A=tuple(value[:, permutation] for value in model.A),
        B=model.B[permutation][:, permutation, :],
        D=model.D[permutation],
    )
    relabeled_inference = reference.infer_states(relabeled, observation, relabeled.D)
    relabeled_policy = reference.score_policies(relabeled, relabeled_inference.posterior)
    original_policy = reference.score_policies(model, inferred.posterior)
    checks.append(
        _check(
            "state_relabeling_invariance",
            np.allclose(
                relabeled_inference.posterior,
                inferred.posterior[permutation],
                atol=1e-12,
                rtol=0.0,
            )
            and np.allclose(
                relabeled_policy.neg_efe,
                original_policy.neg_efe,
                atol=1e-12,
                rtol=0.0,
            ),
        )
    )

    intact = build_blanket_model("intact")
    broken = build_blanket_model("blanket_break")
    sensory_lesion = build_blanket_model("sensory_lesion")
    active_lesion = build_blanket_model("active_lesion")
    impulse_times = np.linspace(0.0, 8.0, 161)
    sensory_route = impulse_response(sensory_lesion, 0, impulse_times)[:, 1:]
    active_route = impulse_response(active_lesion, 2, impulse_times)[:, 0]
    checks.extend(
        (
            _check(
                "analytic_blanket_precision_zero",
                abs(intact.precision[0, 2]) < 1e-12,
                precision_entry=float(intact.precision[0, 2]),
            ),
            _check(
                "blanket_break_population_effect",
                abs(broken.population_partial_correlation) > 0.08,
                partial_correlation=broken.population_partial_correlation,
            ),
            _check(
                "sensory_lesion_removes_external_route",
                float(np.max(np.abs(sensory_route))) < 1e-12,
                maximum_downstream_response=float(np.max(np.abs(sensory_route))),
            ),
            _check(
                "active_lesion_removes_internal_external_route",
                float(np.max(np.abs(active_route))) < 1e-12,
                maximum_external_response=float(np.max(np.abs(active_route))),
            ),
        )
    )

    passive_entropy = _expected_regime_entropy(model, 0)
    sampled_entropy = _expected_regime_entropy(model, 3)
    checks.append(
        _check(
            "sampling_reduces_expected_regime_entropy",
            passive_entropy - sampled_entropy >= 0.20,
            passive_entropy=passive_entropy,
            sampled_entropy=sampled_entropy,
            reduction=passive_entropy - sampled_entropy,
        )
    )

    result: dict[str, object] = {
        "profile": config.profile,
        "dependencies": dependency_versions(),
        "checks": checks,
        "all_pass": all(bool(check["passed"]) for check in checks),
    }
    write_json(output / "validation.json", result)
    seal_directory(output, ["validation.json"])
    return result
