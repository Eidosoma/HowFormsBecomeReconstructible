from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from laws_confirmation import doorkey_common_state_continuation as assay
from laws_confirmation.doorkey_env import Action, DoorKeyEnv, TRANSFORMS, oracle_plan
from laws_confirmation.doorkey_matched_disposition import deep_digest
from laws_confirmation.doorkey_ppo_v2 import FeedbackPPOConfig, FeedbackRecurrentActorCritic, START_ACTION


@pytest.fixture(scope="module")
def bank():
    torch.set_num_threads(1)
    return assay.build_prefix_bank(2, 400_000_000)


def new_model(seed=7):
    with torch.random.fork_rng():
        torch.manual_seed(seed)
        return FeedbackRecurrentActorCritic(FeedbackPPOConfig(hidden_size=8, tile_embedding_size=2, action_embedding_size=2))


class ConstantActor:
    config = SimpleNamespace(hidden_size=2)

    def __init__(self, action=None):
        self.action = action

    def forward_step(self, observations, hidden, starts, previous_actions, previous_rewards):
        logits = torch.zeros((len(observations), 8))
        if self.action is not None:
            logits.fill_(-1000.)
            logits[:, self.action] = 0.
        return logits, torch.zeros(len(observations)), hidden + 1


def test_registry_counts_and_seed_separation():
    assert assay.REGISTERED_EPISODES == 36_864
    assert assay.EPISODES_PER_STAGE == 1024
    assert assay.STAGES == ("birth", "key_acquired", "door_ready", "door_opened")
    assert assay.ARMS == ("correct", "empty", "shuffled")
    assert assay.WORKERS == 3 and assay.BATCH_SIZE <= 128
    assert assay.LAYOUT_SEED != 380_000_000 and assay.ACTION_SEED != 390_000_000


def test_all_prefixes_are_real_oracle_histories_and_share_rotated_seeds(bank):
    assert assay.audit_prefix_bank(bank)["passes"]
    assert len(bank["entries"]) == 2 * 4 * 4
    for entry in bank["entries"]:
        env = entry["environment"]
        plan = oracle_plan(env.layout)
        stop = {"birth": 0, "key_acquired": plan.index(Action.PICKUP) + 1,
                "door_ready": plan.index(Action.OPEN), "door_opened": plan.index(Action.OPEN) + 1}[entry["stage"]]
        assert entry["prefix_steps"] == stop
        assert entry["remaining_steps"] == 128 - stop
        assert entry["history"]["actions"].tolist() == [int(a) for a in plan[:stop]]
        assert entry["history"]["observations"].shape == (stop, 13)
        assert not entry["history"]["rewards"].any()
        assert entry["layout_seed"] == bank["layout_seed"] + entry["seed_block"]
        assert not env.terminated and not env.truncated


@pytest.mark.parametrize("field", ["remaining_steps", "state_sha256", "history_sha256", "layout_seed"])
def test_prefix_audit_rejects_tampering(bank, field):
    altered = deepcopy(bank)
    altered["entries"][0][field] = -1
    assert not assay.audit_prefix_bank(altered)["passes"]


def test_prefix_audit_rejects_duplicate_missing_inventory(bank):
    altered = deepcopy(bank)
    altered["entries"][-1] = altered["entries"][0]
    assert not assay.audit_prefix_bank(altered)["passes"]


def test_teacher_forced_memory_matches_independent_single_episode_fold(bank):
    model = new_model()
    entries = bank["entries"][:9]  # Mixed lengths, including zero.
    hidden, previous_actions, previous_rewards, starts = assay.replay_prefix_hidden(model, entries)
    with torch.no_grad():
        for i, entry in enumerate(entries):
            h = torch.zeros(1, model.config.hidden_size)
            a = torch.tensor([START_ACTION])
            r = torch.zeros(1)
            start = torch.ones(1, dtype=torch.bool)
            for obs, action, reward in zip(entry["history"]["observations"], entry["history"]["actions"], entry["history"]["rewards"]):
                _, _, h = model.forward_step(torch.from_numpy(obs[None]), h, start, a, r)
                a = torch.tensor([int(action)])
                r = torch.tensor([float(reward)])
                start.fill_(False)
            torch.testing.assert_close(hidden[i], h[0], rtol=1e-6, atol=1e-7)
            assert previous_actions[i] == a[0] and previous_rewards[i] == r[0] and starts[i] == start[0]
    # Birth recurrence is untouched; a supplied history produces nonzero memory.
    assert not hidden[0].any() and starts[0]
    assert hidden[1].any() and not starts[1]


def test_actors_reconstruct_their_own_memory_not_a_shared_hidden_state(bank):
    entries = bank["entries"][:4]
    h1 = assay.replay_prefix_hidden(new_model(7), entries)[0]
    h2 = assay.replay_prefix_hidden(new_model(8), entries)[0]
    assert torch.equal(h1[0], h2[0])
    assert not torch.equal(h1[1:], h2[1:])


def test_uniform_streams_are_private_stage_invariant_and_reproducible(bank):
    before_np, before_torch = deep_digest(np.random.get_state()), deep_digest(torch.get_rng_state())
    samples = []
    for entry in bank["entries"][:4]:
        samples.append(assay.action_uniforms(assay.episode_index(entry, 2), 440_000_000))
    assert all(np.array_equal(samples[0], s) for s in samples)
    assert not np.array_equal(samples[0], assay.action_uniforms(1, 440_000_000))
    assert before_np == deep_digest(np.random.get_state())
    assert before_torch == deep_digest(torch.get_rng_state())


def test_wait_controller_uses_only_remaining_budget_and_gets_no_prefix_credit(bank):
    entry = next(e for e in bank["entries"] if e["stage"] == "door_opened")
    before = deep_digest(bank)
    row = assay.continue_batch(ConstantActor(Action.WAIT), [entry], [0], 440_000_000)[0]
    assert row["prefix_event_steps"]["open_door"] == entry["prefix_steps"]
    assert row["continuation_counts"]["openings"] == 0
    assert row["continuation_counts"]["acquisitions"] == 0
    assert row["continuation_steps"] == entry["remaining_steps"]
    assert row["episode_steps"] == 128 and row["truncated"] and not row["success"]
    assert row["goal_cost_censored_at_budget"] == entry["remaining_steps"]
    assert deep_digest(bank) == before


def test_actions_use_absolute_step_uniforms_not_continuation_age(bank):
    entry = next(e for e in bank["entries"] if e["stage"] == "door_opened")
    row = assay.continue_batch(ConstantActor(), [entry], [3], 440_000_000)[0]
    draws = assay.action_uniforms(assay.episode_index(entry, 3), 440_000_000)
    expected = np.floor(draws[entry["prefix_steps"]:row["episode_steps"]] * 8).astype(int).tolist()
    assert row["continuation_actions_sha256"] == deep_digest(expected)
    wrong_offset = np.floor(draws[:row["continuation_steps"]] * 8).astype(int).tolist()
    assert row["continuation_actions_sha256"] != deep_digest(wrong_offset)


def test_actor_panel_replays_exactly_and_cannot_modify_bank_or_weights(bank):
    model = new_model()
    before = deep_digest(model.state_dict()), deep_digest(bank), deep_digest(torch.get_rng_state())
    first = assay.evaluate_panel(model, bank, 440_000_000)
    second = assay.evaluate_panel(model, bank, 440_000_000)
    assert first == second
    assert len(first) == 2 * 4 * 4 * 4
    assert before == (deep_digest(model.state_dict()), deep_digest(bank), deep_digest(torch.get_rng_state()))
    assert all(r["prefix_steps"] + r["continuation_steps"] == r["episode_steps"] <= 128 for r in first)


def synthetic_rows(block_differences):
    left, right = [], []
    for block, difference in enumerate(block_differences):
        for transform in TRANSFORMS:
            for stream in range(4):
                common = {"seed_block": block, "layout_seed": 500 + block, "transform": transform,
                          "action_stream": stream, "stage": "door_opened", "prefix_steps": 10,
                          "remaining_steps": 118, "state_sha256": "s", "history_sha256": "h",
                          "uniform_stream_sha256": "u", "prefix_event_steps": {}, "prefix_auxiliary_steps": {},
                          "goal_cost_censored_at_budget": 118}
                left.append(common | {"success": difference > 0})
                right.append(common | {"success": difference < 0})
    return left, right


def test_bootstrap_resamples_whole_layout_blocks_and_preserves_pairing():
    left, right = synthetic_rows([1, -1])
    result = assay.paired_contrast(left, right, 1, interval=True, expected_blocks=2)
    assert result["difference"] == 0
    assert result["block_differences"] == [1., -1.]
    assert result["paired_block_bootstrap_95"] == [-1., 1.]
    assert result["correct_only"] == result["control_only"] == 16
    assert result == assay.paired_contrast(left, list(reversed(right)), 1, interval=True, expected_blocks=2)


@pytest.mark.parametrize("field", ["remaining_steps", "state_sha256", "history_sha256", "uniform_stream_sha256", "stage"])
def test_paired_comparison_rejects_history_state_time_or_stream_mismatch(field):
    left, right = synthetic_rows([1, -1])
    right[0][field] = "wrong"
    with pytest.raises(ValueError, match="mismatch"):
        assay.paired_contrast(left, right, 1, interval=True, expected_blocks=2)


def test_paired_comparison_rejects_duplicate_or_missing_rotation_stream():
    left, right = synthetic_rows([1, -1])
    with pytest.raises(ValueError):
        assay.paired_contrast(left, right[:-1], 1, interval=True, expected_blocks=2)
    with pytest.raises(ValueError):
        assay.paired_contrast(left + [left[0]], right + [right[0]], 1, interval=True, expected_blocks=2)
    with pytest.raises(ValueError):
        assay.paired_contrast(left[:-1], right[:-1], 1, interval=True, expected_blocks=2)


def test_frozen_classification_requires_all_founders_and_strictly_positive_bounds():
    rows = [{"founder": f, "difference": .1, "paired_block_bootstrap_95": [.01, .2]} for f in assay.FOUNDERS]
    assert assay.classification(rows, True) == "COMMON_STATE_GOAL_LEAD_3_OF_3"
    rows[0]["paired_block_bootstrap_95"][0] = 0
    assert assay.classification(rows, True) == "DIRECTIONAL_GOAL_LEAD_UNCERTAIN"
    rows[0]["difference"] = 0
    assert assay.classification(rows, True) == "NO_REPLICATED_COMMON_STATE_GOAL_LEAD"
    assert assay.classification(rows, False) == "INVALID_STRUCTURAL_FAILURE"
    assert assay.classification(rows[:2], True) == "INVALID_STRUCTURAL_FAILURE"


def test_run_refuses_completed_target_without_overwriting_status(tmp_path):
    run = tmp_path / "runs" / assay.RUN_ID
    run.mkdir(parents=True)
    (run / "STATUS.json").write_text('{"status":"COMPLETE"}')
    with pytest.raises(FileExistsError):
        assay.prepare_run(tmp_path)
    assert (run / "STATUS.json").read_text() == '{"status":"COMPLETE"}'
