from __future__ import annotations

import numpy as np

from fep_lab.blanket import (
    build_blanket_model,
    estimate_blanket_statistics,
    simulate_blanket,
)
from fep_lab.homeostat import HomeostatEnvironment, build_homeostat_model
from fep_lab.reference import ReferenceBackend, variational_free_energy


def test_homeostat_model_is_normalized_and_vfe_matches_evidence() -> None:
    model = build_homeostat_model()
    model.validate()
    environment = HomeostatEnvironment()
    observation = environment.reset(np.random.default_rng(4)).observation
    backend = ReferenceBackend()
    inference = backend.infer_states(model, observation, model.D)

    assert abs(inference.vfe + inference.log_evidence) < 1e-10
    likelihood = model.A[0][observation[0]] * model.A[1][observation[1]]
    perturbed = 0.9 * inference.posterior + 0.1 / model.n_states
    assert variational_free_energy(perturbed, model.D, likelihood) >= inference.vfe


def test_reference_policy_scoring_is_relabeling_invariant() -> None:
    model = build_homeostat_model()
    backend = ReferenceBackend()
    observation = (2, 1)
    inference = backend.infer_states(model, observation, model.D)
    policies = backend.score_policies(model, inference.posterior)
    assert np.isclose(policies.posterior.sum(), 1.0)
    assert policies.neg_efe.shape == (16,)
    assert policies.state_info_gain.max() > 0.0


def test_blanket_population_and_breaking_lesion() -> None:
    intact = build_blanket_model("intact")
    broken = build_blanket_model("blanket_break")

    assert abs(intact.precision[0, 2]) < 1e-12
    assert abs(intact.population_partial_correlation) < 1e-12
    assert abs(broken.population_partial_correlation) > 0.08


def test_blanket_simulation_is_exactly_reproducible() -> None:
    model = build_blanket_model()
    left = simulate_blanket(model, 16, 256, 0.05, np.random.default_rng(55))
    right = simulate_blanket(model, 16, 256, 0.05, np.random.default_rng(55))

    assert np.array_equal(left, right)
    assert "conditional_mutual_information" in estimate_blanket_statistics(left)
