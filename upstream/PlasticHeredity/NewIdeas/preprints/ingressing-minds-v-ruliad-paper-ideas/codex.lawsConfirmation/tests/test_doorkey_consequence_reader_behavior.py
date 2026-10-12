from __future__ import annotations

from copy import deepcopy
import json

import numpy as np
import pytest
import torch

from laws_confirmation import doorkey_consequence_predictor as predictor
from laws_confirmation import doorkey_consequence_reader_behavior as behavior
from laws_confirmation import doorkey_vertical_scout as vertical
from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_carrier import (
    empty_germ,
    read_germ,
    write_germ_from_local_evidence,
)
from laws_confirmation.doorkey_matched_disposition import (
    deep_digest,
    soma_environment_digests,
)
from laws_confirmation.doorkey_phase_value_credit import (
    actor_advantage_for_arm,
    _forward_sequence_values,
)
from laws_confirmation.doorkey_ppo import DoorKeyVectorEnv
from laws_confirmation.doorkey_ppo_v2 import FeedbackPPOConfig


def _packet():
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    evidence[0, 1, 4] = 10
    evidence[0, 3, 5] = 10
    return write_germ_from_local_evidence(
        evidence,
        empty_germ(1),
        confirmation_mask=np.array([[False, True, False, True]]),
    )[0]


def _config():
    return FeedbackPPOConfig(
        hidden_size=8,
        tile_embedding_size=2,
        action_embedding_size=2,
        num_envs=2,
        rollout_steps=8,
        minibatch_envs=1,
        ppo_epochs=1,
        max_episode_steps=16,
    )


def _new(arm="correct"):
    packet = _packet()
    if arm == "wrong":
        packet = vertical.initial_carriers(packet)["wrong_frozen"]
    elif arm == "empty":
        packet = empty_germ(1)
    config = _config()
    descendant = vertical.make_vertical_descendant(
        make_boundary_packet(packet), config, 101
    )
    reader = predictor.ConsequenceReader(packet, 303, arm)
    environments = DoorKeyVectorEnv(
        config.num_envs, 202, config.max_episode_steps, "terminal"
    )
    return (
        descendant,
        reader,
        environments,
        predictor.TransitionRecorder(environments),
        config,
    )


def _examples():
    obs = torch.zeros((64, 13))
    obs[:, 4] = 6
    obs[:16, 10] = 1
    obs[32:, 9] = 1
    obs[32:48, 1] = 3
    actions = torch.tensor([4] * 32 + [5] * 32)
    outcomes = torch.zeros((64, 2))
    outcomes[:16, 0] = 1
    outcomes[32:48, 1] = 1
    return obs, actions, outcomes


def test_frozen_registry_has_fresh_seeds_and_exact_packets():
    assert behavior.REGISTERED_CELLS == 15
    assert behavior.REGISTERED_TRANSITIONS == 6_144_000
    assert behavior.MAX_WORKERS == 4
    assert behavior.MATCHED_UPDATES == 60
    assert behavior.PRACTICAL_MARGIN == 0.05
    assert behavior.seed_row(1) == {
        "birth": 300_100_000,
        "training": 310_100_000,
        "head": 320_100_000,
    }
    assert behavior.seed_row(3) == {
        "birth": 300_300_000,
        "training": 310_300_000,
        "head": 320_300_000,
    }
    with pytest.raises(ValueError):
        behavior.seed_row(0)
    source = {
        "parents": [
            {
                "founder": f,
                "incoming_germ": _packet().tolist(),
                "parent_checkpoint": f"parent{f}",
                "parent_checkpoint_sha256": "p",
                "source_result": "s",
                "source_result_sha256": "s",
            }
            for f in (1, 2, 3)
        ]
    }
    specs = behavior.cell_specs(source)
    assert len(specs) == 15
    for spec in specs:
        packet = np.array(spec["incoming_germ"], np.uint8)
        assert packet.shape == (1, 64) and packet.nbytes == 64
        read = read_germ(packet)
        if spec["arm"] == "wrong":
            assert read.prior_logits[0, [1, 3]].argmax(-1).tolist() == [5, 4]
        elif spec["arm"] == "empty":
            assert not read.active.any()
        else:
            assert np.array_equal(packet, _packet())


def test_null_ppo_matches_frozen_phase_update_bitwise_across_two_rollouts():
    descendant, reader, env, recorder, config = _new("empty")
    reference, _, reference_env, _, _ = _new("empty")
    for update in (60, 61):
        row, rollout, _ = behavior.training_step(
            descendant, reader, env, recorder, config, update
        )
        frozen_rollout, _ = vertical.collect_vertical_rollout(
            reference, reference_env, config, "blind"
        )
        assert deep_digest(vars(rollout)) == deep_digest(vars(frozen_rollout))
        frozen_metrics = vertical.vertical_phase_ppo_update(
            reference, frozen_rollout, config, "blind"
        )
        assert row["behavior"]["ppo"] == frozen_metrics
        assert soma_environment_digests(descendant, env) == soma_environment_digests(
            reference, reference_env
        )
        assert row["credit"]["applied_nonzero_steps"] == 0
        assert row["passes"]


def test_schedule_uses_learned_policy_centered_credit_only_after_update_60():
    descendant, reader, env, recorder, config = _new()
    reader.fit(*_examples())
    rollout, _ = vertical.collect_vertical_rollout(
        descendant, recorder, config, "blind"
    )
    base, _ = actor_advantage_for_arm(rollout, "phase_actor")
    before = reader.digest()
    prefix, _, prefix_audit = behavior.learned_actor_advantage(
        descendant, reader, rollout, config, 60
    )
    enabled, _, enabled_audit = behavior.learned_actor_advantage(
        descendant, reader, rollout, config, 61
    )
    assert torch.equal(prefix, base)
    assert prefix_audit["applied_nonzero_steps"] == 0
    assert enabled_audit["applied_nonzero_steps"] > 0
    assert enabled_audit["blind_log_probabilities_exact"]
    assert enabled_audit["policy_centering_max_error"] < 1e-6
    assert reader.digest() == before
    assert not enabled.requires_grad
    with torch.no_grad():
        logits, _, _ = _forward_sequence_values(
            descendant,
            rollout.observations,
            rollout.initial_hidden,
            rollout.episode_starts,
            rollout.previous_actions,
            rollout.previous_rewards,
        )
        probabilities = torch.log_softmax(logits.reshape(-1, 8), -1).exp()
        table = reader.credit_table(rollout.observations, probabilities)
        choices = rollout.actions.reshape(-1)
        expected = (
            table.gather(2, choices[:, None, None].expand(-1, 2, 1))
            .squeeze(-1)
            .sum(1)
            .reshape_as(base)
        )
    assert torch.equal(enabled, base + expected)
    with pytest.raises(ValueError):
        behavior.learned_actor_advantage(descendant, reader, rollout, config, 0)


def test_head_changes_actor_only_through_explicit_advantage_and_ppo_cannot_train_head():
    descendant, reader, env, recorder, config = _new()
    reader.fit(*_examples())
    rollout, _ = vertical.collect_vertical_rollout(
        descendant, recorder, config, "blind"
    )
    reference = deepcopy(descendant)
    before_head = reader.digest()
    advantage, signals, audit = behavior.learned_actor_advantage(
        descendant, reader, rollout, config, 61
    )
    metrics = behavior.ppo_update_with_advantage(
        descendant, rollout, config, advantage, signals
    )
    vertical.vertical_phase_ppo_update(reference, rollout, config, "blind")
    assert audit["applied_nonzero_steps"] > 0
    assert deep_digest(descendant.learner.model.state_dict()) != deep_digest(
        reference.learner.model.state_dict()
    )
    assert reader.digest() == before_head
    assert all(p.grad is None for p in reader.model.parameters())
    assert np.isfinite(metrics["grad_norm"])
    with pytest.raises(ValueError, match="detached"):
        behavior.ppo_update_with_advantage(
            descendant, rollout, config, advantage.requires_grad_(), signals
        )


def test_all_five_conditions_have_exact_prefix_and_three_nulls_stay_exact_after_activation():
    cells = {arm: _new(arm) for arm in behavior.ARMS}
    for _, reader, _, _, _ in cells.values():
        reader.fit(*_examples())
    histories = {arm: [] for arm in cells}
    for update in (1, 60, 61):
        for arm, args in cells.items():
            row, _, _ = behavior.training_step(*args, update)
            histories[arm].append(row)
        reference = histories["empty"][-1]["behavior"]
        for arm in behavior.ARMS if update <= 60 else behavior.NULL_ARMS:
            assert histories[arm][-1]["behavior"] == reference
        if update <= 60:
            assert cells["correct"][1].digest() == cells["reader_off"][1].digest()
    assert histories["correct"][-1]["credit"]["applied_nonzero_steps"] > 0
    assert histories["correct"][-1]["behavior"] != histories["empty"][-1]["behavior"]


def test_prefit_state_and_advantage_stay_fixed_while_current_labels_are_learned_later():
    args = _new()
    reader = args[1]
    reader.fit(*_examples())
    before = reader.digest()
    first, _, _ = behavior.training_step(*args, 61)
    assert first["credit"]["reader_prefit_sha256"] == before
    assert first["predictor_before_sha256"] == before
    assert first["predictor_after_sha256"] != before
    assert first["gates"]["fixed_advantage_not_mutated"]
    assert first["gates"]["ppo_does_not_train_head"]
    assert first["gates"]["head_fit_does_not_change_actor_gradients"]
    second, _, _ = behavior.training_step(*args, 62)
    assert second["credit"]["reader_prefit_sha256"] == first["predictor_after_sha256"]


def test_complete_checkpoint_restores_predictor_buffer_rng_optimizer_and_actor_state(
    tmp_path,
):
    descendant, reader, env, recorder, config = _new()
    reader.fit(*_examples())
    _, rollout, outcomes = behavior.training_step(
        descendant, reader, env, recorder, config, 61
    )
    spec = {"arm": "correct", "birth_seed": 101, "training_seed": 202, "head_seed": 303}
    payload = behavior.checkpoint_payload(
        descendant, reader, env, config, spec, rollout, outcomes
    )
    expected_digest = deep_digest(payload)
    path = tmp_path / "checkpoint.pt"
    torch.save(payload, path)
    loaded = torch.load(path, weights_only=False)
    assert deep_digest(loaded) == expected_digest
    restored, restored_reader, restored_env, restored_config = (
        behavior.restore_checkpoint(loaded)
    )
    assert config == restored_config
    assert soma_environment_digests(descendant, env) == soma_environment_digests(
        restored, restored_env
    )
    assert reader.digest() == restored_reader.digest()
    assert {p.data_ptr() for p in reader.model.parameters()}.isdisjoint(
        {p.data_ptr() for p in restored_reader.model.parameters()}
    )
    assert reader.buffer[0][0].data_ptr() != restored_reader.buffer[0][0].data_ptr()
    original_next, _, _ = behavior.training_step(
        descendant, reader, env, recorder, config, 62
    )
    restored_next, _, _ = behavior.training_step(
        restored,
        restored_reader,
        restored_env,
        predictor.TransitionRecorder(restored_env),
        config,
        62,
    )
    assert original_next == restored_next
    assert deep_digest(loaded) == expected_digest


def test_evaluation_is_germ_blind_and_does_not_touch_learning_state():
    args = _new()
    descendant, reader, env, _, config = args
    reader.fit(*_examples())
    _, _, _ = behavior.training_step(*args, 61)
    before_actor = soma_environment_digests(descendant, env)
    before_head = reader.digest()
    summaries, worlds, unchanged = behavior.evaluate(
        descendant, reader, env, config, 61
    )
    assert unchanged
    assert [s["world_count"] for s in summaries] == [32, 128]
    assert all(s["germ_mode"] == "blind" for s in summaries)
    assert set(worlds) == {"deterministic", "fixed_random"}
    assert before_actor == soma_environment_digests(descendant, env)
    assert before_head == reader.digest()


def _mock_results():
    results = []
    for founder in behavior.FOUNDERS:
        for arm in behavior.ARMS:
            auc = {
                "fixed_random": {
                    "events": {
                        "open_door": {
                            "reached_fraction_auc": 0.2 if arm == "correct" else 0.1
                        }
                    }
                }
            }
            results.append(
                {
                    "founder": founder,
                    "arm": arm,
                    "completed_cleanly": True,
                    "birth_soma_environment_digests": {"aggregate": "same"},
                    "initial_head_sha256": "fresh",
                    "history": [
                        {
                            "update": i,
                            "behavior": {"rollout_sha256": f"r{i}", "value": 0},
                            "predictor_after_sha256": f"h{i}",
                        }
                        for i in range(1, 101)
                    ],
                    "evaluations": [
                        {"update": i, "action_mode": mode, "successes": 0}
                        for i in range(0, 101, 10)
                        for mode in ("deterministic", "fixed_random")
                    ],
                    "evaluation_world_rows": {str(i): {} for i in range(0, 101, 10)},
                    "final_soma_environment_digests": {"aggregate": "same"},
                    "learning_auc": deepcopy(auc),
                    "post_prefix_auc": deepcopy(auc),
                }
            )
    return results


def test_exact_audit_detects_prefix_and_null_drift_but_allows_later_correct_effect():
    results = _mock_results()
    assert behavior.exact_apparatus_audit(results)["passes"]
    correct = next(r for r in results if r["founder"] == 3 and r["arm"] == "correct")
    correct["history"][60]["behavior"]["value"] = 1
    assert behavior.exact_apparatus_audit(results)["passes"]
    correct["history"][59]["behavior"]["value"] = 1
    assert not behavior.exact_apparatus_audit(results)["passes"]
    results = _mock_results()
    reader_off = next(
        r for r in results if r["founder"] == 1 and r["arm"] == "reader_off"
    )
    reader_off["history"][60]["behavior"]["value"] = 1
    assert not behavior.exact_apparatus_audit(results)["passes"]
    assert not behavior.exact_apparatus_audit(results[:-1])["passes"]


def test_classification_uses_strict_margin_and_all_founders_plus_shuffle():
    results = _mock_results()
    assert (
        behavior.registered_classification(results, {"passes": True})["label"]
        == "LEARNED_CONSEQUENCE_BENEFIT_3_OF_3"
    )
    correct = next(r for r in results if r["founder"] == 2 and r["arm"] == "correct")
    empty = next(r for r in results if r["founder"] == 2 and r["arm"] == "empty")
    correct["post_prefix_auc"]["fixed_random"]["events"]["open_door"][
        "reached_fraction_auc"
    ] = 0.05
    empty["post_prefix_auc"]["fixed_random"]["events"]["open_door"][
        "reached_fraction_auc"
    ] = 0
    outcome = behavior.registered_classification(results, {"passes": True})
    assert not outcome["founders"][1]["practical_margin_pass"]
    assert outcome["label"] == "LEARNED_CONSEQUENCE_BENEFIT_NOT_3_OF_3"
    assert (
        behavior.registered_classification(results, {"passes": False})["label"]
        == "INVALID_STRUCTURAL_FAILURE"
    )
    results = _mock_results()
    shuffled = next(r for r in results if r["founder"] == 1 and r["arm"] == "shuffled")
    shuffled["post_prefix_auc"]["fixed_random"]["events"]["open_door"][
        "reached_fraction_auc"
    ] = 0.2
    assert (
        behavior.registered_classification(results, {"passes": True})["label"]
        == "LEARNED_CONSEQUENCE_BENEFIT_NOT_3_OF_3"
    )


@pytest.mark.parametrize("status", ["COMPLETE", "FAILED", "RUNNING"])
def test_refusing_initialized_run_does_not_overwrite_its_status(tmp_path, status):
    run = tmp_path / "runs" / behavior.RUN_ID
    run.mkdir(parents=True)
    text = json.dumps({"status": status, "original": True})
    (run / "STATUS.json").write_text(text)
    with pytest.raises(RuntimeError, match="refusing"):
        behavior.run_study(tmp_path)
    assert (run / "STATUS.json").read_text() == text
    assert not (run / "FAILED").exists()
    assert not (run / "EXECUTION.lock").exists()
