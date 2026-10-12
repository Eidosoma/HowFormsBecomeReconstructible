import pytest

pytest.importorskip("torch")

from laws_confirmation.doorkey_feedback_scout import (
    _causal_comparison,
    _classification,
    _deepest_reached,
)


@pytest.mark.parametrize(
    ("deterministic", "fixed_random", "expected"),
    [
        (1, 1, "CHAIN_COMPLETION_BOTH_MODES"),
        (1, 0, "CHAIN_COMPLETION_DETERMINISTIC_ONLY"),
        (0, 1, "CHAIN_COMPLETION_FIXED_RANDOM_ONLY"),
        (0, 0, "NO_CHAIN_COMPLETION"),
    ],
)
def test_chain_completion_classification(deterministic, fixed_random, expected):
    assert _classification(deterministic, fixed_random) == expected


def test_causal_comparison_and_deepest_reached():
    older = [
        {
            "from": "episode_start",
            "to": "explore",
            "reached": 4,
            "eligible": 4,
            "conditional_probability": 1.0,
        },
        {
            "from": "explore",
            "to": "find_key",
            "reached": 1,
            "eligible": 4,
            "conditional_probability": 0.25,
        },
    ]
    newer = [
        {
            "from": "episode_start",
            "to": "explore",
            "reached": 4,
            "eligible": 4,
            "conditional_probability": 1.0,
        },
        {
            "from": "explore",
            "to": "find_key",
            "reached": 3,
            "eligible": 4,
            "conditional_probability": 0.75,
        },
    ]
    comparison = _causal_comparison(older, newer)
    assert comparison[1]["reached_count_difference"] == 2
    assert comparison[1]["conditional_probability_difference"] == 0.5
    assert _deepest_reached(newer) == "find_key"


def test_causal_comparison_rejects_changed_event_order():
    row = {
        "from": "episode_start",
        "to": "explore",
        "reached": 1,
        "eligible": 1,
        "conditional_probability": 1.0,
    }
    changed = {**row, "to": "find_key"}
    with pytest.raises(ValueError, match="event order"):
        _causal_comparison([row], [changed])
