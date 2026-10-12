import numpy as np
import pytest

from laws_confirmation.doorkey_env import (
    Action,
    CAUSAL_CHAIN,
    DoorKeyEnv,
    TRANSFORMS,
    make_layout,
    oracle_plan,
    run_actions,
)


def test_oracle_completes_ordered_chain_across_seeds_and_rotations():
    for seed in range(12):
        for transform in TRANSFORMS:
            layout = make_layout(seed, transform)
            plan = oracle_plan(layout)
            env = run_actions(layout, plan)
            assert env.terminated
            assert not env.truncated
            assert env.chain_complete_and_ordered()
            steps = [env.event_steps[event] for event in CAUSAL_CHAIN]
            assert all(left < right for left, right in zip(steps, steps[1:]))
            assert sum(row["acquired"] for row in env.transition_trace) == 1
            assert sum(row["opened"] for row in env.transition_trace) == 1


def test_environment_replay_is_exact_and_observation_is_public_shape():
    layout = make_layout(731, "rot270")
    actions = oracle_plan(layout)
    first = run_actions(layout, actions)
    second = run_actions(layout, actions)
    assert first.state_signature() == second.state_signature()
    assert first.transition_trace == second.transition_trace
    observation = first.observation()
    assert observation.tiles.shape == (3, 3)
    assert observation.tiles.dtype == np.uint8
    assert observation.vector().shape == (13,)
    assert observation.vector().dtype == np.float32


def test_closed_door_needs_retained_key_and_drop_breaks_that_state():
    layout = make_layout(9)
    env = DoorKeyEnv(layout)
    plan = oracle_plan(layout)
    pickup_index = plan.index(Action.PICKUP)
    for action in plan[:pickup_index]:
        env.step(action)
    _, _, _, _, pickup_info = env.step(Action.PICKUP)
    assert pickup_info["acquired"]
    assert env.state.has_key
    env.step(Action.DROP)
    assert not env.state.has_key
    assert env.state.key_position == env.state.position
    assert env.event_steps["retain_key"] is None

    # A fresh agent adjacent to the door cannot open it without the key.
    fresh = DoorKeyEnv(layout)
    fresh.state = fresh.state.__class__(
        position=next(
            position
            for position in (
                (layout.door[0] - 1, layout.door[1]),
                (layout.door[0] + 1, layout.door[1]),
                (layout.door[0], layout.door[1] - 1),
                (layout.door[0], layout.door[1] + 1),
            )
            if position not in layout.walls
        ),
        has_key=False,
        key_position=layout.key,
        door_open=False,
    )
    _, _, _, _, info = fresh.step(Action.OPEN)
    assert not info["opened"]
    assert not fresh.state.door_open


def test_invalid_action_and_post_terminal_step_are_rejected():
    layout = make_layout(44)
    env = DoorKeyEnv(layout)
    with pytest.raises(ValueError):
        env.step(99)
    completed = run_actions(layout, oracle_plan(layout))
    with pytest.raises(RuntimeError):
        completed.step(Action.WAIT)

