import copy

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from laws_confirmation.doorkey_boundary import make_boundary_packet  # noqa: E402
from laws_confirmation.doorkey_carrier import (  # noqa: E402
    carrier_digest,
    empty_germ,
    read_germ,
    write_germ_from_local_evidence,
)
from laws_confirmation.doorkey_matched_disposition import (  # noqa: E402
    ARMS,
    CUTOFF_UPDATE,
    FOUNDERS,
    GENERATION,
    REGISTERED_CELLS,
    _apply_packet_prior,
    cell_specs,
    deep_digest,
    exact_blind_silence_alias_audit,
    expression_for,
    make_post_key_mask,
    matched_behavior_audit,
    run_with_expression,
    seed_row,
    segment_learning_auc,
    soma_environment_digests,
)
from laws_confirmation.doorkey_ppo import DoorKeyVectorEnv  # noqa: E402
from laws_confirmation.doorkey_ppo_v2 import (  # noqa: E402
    FeedbackPPOConfig,
    _apply_prior,
)
from laws_confirmation import doorkey_vertical_scout as frozen_vertical  # noqa: E402


def _correct_carrier() -> np.ndarray:
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    evidence[0, 1, 4] = 10.0
    evidence[0, 3, 5] = 10.0
    confirmation = np.asarray([[False, True, False, True]])
    carrier, committed = write_germ_from_local_evidence(
        evidence,
        empty_germ(1),
        confirmation_mask=confirmation,
    )
    assert np.array_equal(committed, confirmation)
    return carrier


def _small_config() -> FeedbackPPOConfig:
    return FeedbackPPOConfig(
        tile_embedding_size=2,
        hidden_size=8,
        action_embedding_size=2,
        num_envs=2,
        rollout_steps=4,
        ppo_epochs=1,
        minibatch_envs=1,
        max_episode_steps=8,
    )


def test_seed_registry_schedule_and_size_are_frozen():
    assert seed_row(1) == {"birth": 180_100_000, "training": 190_100_000}
    assert seed_row(3) == {"birth": 180_300_000, "training": 190_300_000}
    assert REGISTERED_CELLS == 24
    assert GENERATION == 4
    assert CUTOFF_UPDATE == 20
    assert len(ARMS) == 8
    with pytest.raises(ValueError):
        seed_row(0)


def test_post_key_mask_disables_only_pickup_and_reseals():
    correct = _correct_carrier()
    masked = make_post_key_mask(correct)
    decoded = read_germ(masked)
    assert masked.shape == (1, 64)
    assert decoded.address_valid.all()
    assert decoded.checksum_valid.all()
    assert decoded.active[0].tolist() == [False, False, False, True]
    assert decoded.prior_logits.argmax(axis=-1)[0, 3] == 5
    original = read_germ(correct)
    assert np.array_equal(
        masked.reshape(1, 4, 16)[0, 3], correct.reshape(1, 4, 16)[0, 3]
    )
    assert original.active[0].tolist() == [False, True, False, True]


def test_expression_schedule_has_exact_early_and_late_paths():
    correct = _correct_carrier()
    masked = make_post_key_mask(correct)

    def row(arm, update):
        return expression_for(
            arm,
            update,
            correct_carrier=correct,
            post_key_carrier=masked,
        )

    assert row("early_germ", 20)["germ_mode"] == "direct_prior"
    assert row("early_germ", 21)["germ_mode"] == "blind"
    assert row("early_controller", 0)["path"] == "external_controller"
    assert row("early_controller", 21) == {
        "path": "inherited_reader",
        "germ_mode": "direct_prior",
    }
    assert row("delayed_germ", 20)["germ_mode"] == "blind"
    assert row("delayed_germ", 21)["germ_mode"] == "direct_prior"
    assert row("post_key_germ", 100)["path"] == "masked_reader"
    assert row("carrier_blind", 0)["germ_mode"] == "blind"


def test_external_packet_prior_is_bit_exact_to_inherited_reader():
    config = _small_config()
    carrier = _correct_carrier()
    descendant = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(carrier), config, 1234
    )
    observations = torch.zeros((5, config.observation_width), dtype=torch.float32)
    observations[:, :9] = torch.tensor(
        [
            [6, 0, 0, 0, 2, 0, 0, 0, 0],
            [6, 0, 0, 0, 0, 0, 0, 0, 0],
            [6, 0, 0, 0, 3, 0, 0, 0, 0],
            [6, 0, 0, 0, 4, 0, 0, 0, 0],
            [6, 0, 0, 0, 2, 0, 0, 0, 0],
        ]
    )
    observations[2:4, 9] = 1.0
    observations[4, 10] = 1.0
    logits = torch.linspace(-1.0, 1.0, 40, dtype=torch.float32).reshape(5, 8)
    inherited_logits, inherited_active = _apply_prior(
        logits, descendant.learner, observations, "direct_prior"
    )
    external_logits, external_active = _apply_packet_prior(
        logits, descendant.learner, observations, carrier
    )
    assert torch.equal(inherited_logits, external_logits)
    assert torch.equal(inherited_active, external_active)


def test_matched_rollout_update_and_complete_state_are_exact():
    config = _small_config()
    correct = _correct_carrier()
    silence = empty_germ(1)
    germ_descendant = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(correct), config, 4321
    )
    controller_descendant = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(silence), config, 4321
    )
    germ_env = DoorKeyVectorEnv(2, 5678, 8, "terminal")
    controller_env = DoorKeyVectorEnv(2, 5678, 8, "terminal")
    germ_rollout, germ_completed = frozen_vertical.collect_vertical_rollout(
        germ_descendant, germ_env, config, "direct_prior"
    )
    tracker = {
        "calls": 0,
        "contexts": 0,
        "labels": {},
        "controller_carrier_sha256": {},
        "germ_unchanged_each_call": True,
        "germ_restored_after_every_context": True,
        "controller_unchanged_each_call": True,
    }
    expression = {
        "path": "external_controller",
        "germ_mode": "direct_prior",
        "carrier": correct,
        "label": "matched_correct_packet",
    }
    controller_rollout, controller_completed = run_with_expression(
        controller_descendant,
        expression,
        tracker,
        lambda mode: frozen_vertical.collect_vertical_rollout(
            controller_descendant, controller_env, config, mode
        ),
    )
    assert deep_digest(vars(germ_rollout)) == deep_digest(vars(controller_rollout))
    assert deep_digest(germ_completed) == deep_digest(controller_completed)
    germ_metrics = frozen_vertical.vertical_phase_ppo_update(
        germ_descendant, germ_rollout, config, "direct_prior"
    )
    controller_metrics = run_with_expression(
        controller_descendant,
        expression,
        tracker,
        lambda mode: frozen_vertical.vertical_phase_ppo_update(
            controller_descendant, controller_rollout, config, mode
        ),
    )
    assert deep_digest(germ_metrics) == deep_digest(controller_metrics)
    assert (
        soma_environment_digests(germ_descendant, germ_env)["aggregate"]
        == soma_environment_digests(controller_descendant, controller_env)["aggregate"]
    )
    assert carrier_digest(controller_descendant.learner.germ) == carrier_digest(silence)
    assert tracker["calls"] > 0
    assert tracker["germ_unchanged_each_call"]
    assert tracker["germ_restored_after_every_context"]
    assert tracker["controller_unchanged_each_call"]


def test_cell_specs_use_g3_outputs_and_only_registered_interventions():
    correct = _correct_carrier()
    source = {
        "parents": [
            {
                "founder": founder,
                "outgoing_carrier": correct.tolist(),
                "outgoing_carrier_sha256": carrier_digest(correct),
                "checkpoint": f"/source/founder_{founder}.pt",
                "checkpoint_sha256": f"checkpoint-{founder}",
                "config": {"same": True},
            }
            for founder in FOUNDERS
        ]
    }
    specs = cell_specs(source)
    assert len(specs) == REGISTERED_CELLS
    assert {(row["founder"], row["arm"]) for row in specs} == {
        (founder, arm) for founder in FOUNDERS for arm in ARMS
    }
    for founder in FOUNDERS:
        subset = {row["arm"]: row for row in specs if row["founder"] == founder}
        assert not read_germ(
            np.asarray(subset["early_controller"]["incoming_germ"], dtype=np.uint8)
        ).active.any()
        assert not read_germ(
            np.asarray(subset["silence"]["incoming_germ"], dtype=np.uint8)
        ).active.any()
        assert carrier_digest(
            np.asarray(subset["early_germ"]["incoming_germ"], dtype=np.uint8)
        ) == carrier_digest(correct)
        wrong = read_germ(
            np.asarray(subset["wrong_early"]["incoming_germ"], dtype=np.uint8)
        )
        assert wrong.active[0].tolist() == [False, True, False, True]
        assert wrong.prior_logits.argmax(axis=-1)[0, [1, 3]].tolist() == [5, 4]


def _synthetic_result(founder: int, arm: str, token: str = "same") -> dict:
    return {
        "founder": founder,
        "arm": arm,
        "early_behavior_sha256": token,
        "post_cutoff_behavior_sha256": token,
        "behavior_fingerprint": token,
        "cutoff_soma_environment_digests": {
            "actor_critic": token,
            "aggregate": token,
        },
        "final_soma_environment_digests": {
            "actor_critic": token,
            "aggregate": token,
        },
    }


def test_registered_classification_and_blind_alias_are_exact_not_thresholded():
    results = [_synthetic_result(founder, arm) for founder in FOUNDERS for arm in ARMS]
    outcome = matched_behavior_audit(results)
    assert outcome["classification"] == "DIRECT_ACTION_SHAPING_SUFFICIENT_3_OF_3"
    assert (
        outcome["disposition_classification"]
        == "NO_SEPARATE_GERM_DISPOSITION_DETECTED_3_OF_3"
    )
    assert exact_blind_silence_alias_audit(results)["passes"]

    changed = copy.deepcopy(results)
    target = next(
        row
        for row in changed
        if row["founder"] == 2 and row["arm"] == "early_controller"
    )
    target["final_soma_environment_digests"]["aggregate"] = "different"
    detected = matched_behavior_audit(changed)
    assert detected["classification"] == "GERM_SPECIFIC_LEARNING_PATH_DETECTED"

    failed_match = copy.deepcopy(results)
    target = next(
        row
        for row in failed_match
        if row["founder"] == 1 and row["arm"] == "early_controller"
    )
    target["early_behavior_sha256"] = "different"
    assert (
        matched_behavior_audit(failed_match)["classification"]
        == "BEHAVIOR_MATCH_FAILED"
    )


def test_segment_auc_uses_only_registered_window():
    evaluations = []
    for update, fraction in ((0, 0.0), (20, 0.25), (60, 0.5), (100, 1.0)):
        for mode in ("fixed_random", "deterministic"):
            evaluations.append(
                {
                    "update": update,
                    "action_mode": mode,
                    "world_count": 4,
                    "successes": int(4 * fraction),
                    "conditional_chain": [
                        {
                            "to": event,
                            "reached": int(4 * fraction),
                            "conditional_probability": fraction,
                        }
                        for event in (
                            "explore",
                            "find_key",
                            "retain_key",
                            "find_door",
                            "open_door",
                            "reach_goal",
                        )
                    ],
                }
            )
    auc = segment_learning_auc(evaluations, "fixed_random", 20, 100)
    assert auc["updates"] == [20, 60, 100]
    assert auc["events"]["open_door"]["reached_fraction_auc"] == pytest.approx(0.5625)
