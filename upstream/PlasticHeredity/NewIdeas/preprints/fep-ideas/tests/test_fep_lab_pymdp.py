from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pymdp")

from fep_lab.batch import run_batch
from fep_lab.homeostat import HomeostatEnvironment, build_homeostat_model
from fep_lab.pymdp_backend import PymdpBackend
from fep_lab.reference import ReferenceBackend


def test_pymdp_matches_independent_reference() -> None:
    model = build_homeostat_model()
    observation = HomeostatEnvironment().reset(np.random.default_rng(8)).observation
    reference = ReferenceBackend()
    production = PymdpBackend()
    left = reference.infer_states(model, observation, model.D)
    right = production.infer_states(model, observation, model.D)
    left_policy = reference.score_policies(model, left.posterior)
    right_policy = production.score_policies(model, right.posterior)

    assert np.allclose(left.posterior, right.posterior, atol=1e-8, rtol=0.0)
    assert abs(left.vfe - right.vfe) < 1e-8
    assert np.allclose(left_policy.neg_efe, right_policy.neg_efe, atol=1e-7, rtol=0.0)
    assert np.allclose(left_policy.posterior, right_policy.posterior, atol=1e-7, rtol=0.0)


def test_action_lesion_is_pathwise_identical_to_noop() -> None:
    backend = PymdpBackend()
    lesion = run_batch("epistemic", "action_lesion", backend, 4, 4, 91, 92)
    no_op = run_batch("epistemic", "no_op", backend, 4, 4, 91, 93)

    assert np.array_equal(lesion.states, no_op.states)
    assert np.array_equal(lesion.observations, no_op.observations)
    assert np.all(lesion.executed_actions == 0)
    assert np.allclose(
        lesion.neg_efe,
        lesion.expected_utility + lesion.state_info_gain,
        atol=1e-12,
        rtol=0.0,
    )
    assert np.allclose(lesion.vfe, -lesion.log_evidence, atol=1e-10, rtol=0.0)
