from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


AMENDMENT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "amend_experiment_2_terminal_shortfalls.py"
)
SPEC = importlib.util.spec_from_file_location("experiment_2_amendment", AMENDMENT_PATH)
assert SPEC is not None and SPEC.loader is not None
AMENDMENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AMENDMENT)
_resolution_status = AMENDMENT._resolution_status


def test_amended_resolution_accepts_full_and_terminal_attempts() -> None:
    complete = np.asarray([[1, 0], [1, 0]], dtype=np.int8)
    lengths = np.asarray([[32, 26], [32, 14]], dtype=np.int16)

    result = _resolution_status(complete, lengths, horizon=32)

    assert result["all_attempts_resolved"] is True
    assert result["all_streams_reached_horizon"] is False
    assert result["terminal_indices"].tolist() == [[0, 1], [1, 1]]


@pytest.mark.parametrize(
    ("complete", "lengths", "message"),
    [
        ([1], [31], "inconsistent"),
        ([0], [32], "inconsistent"),
        ([0], [-1], "inconsistent"),
        ([2], [32], "outside"),
    ],
)
def test_amended_resolution_rejects_malformed_attempts(
    complete: list[int], lengths: list[int], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _resolution_status(
            np.asarray(complete, dtype=np.int8),
            np.asarray(lengths, dtype=np.int16),
            horizon=32,
        )


def test_amended_resolution_rejects_shape_and_type_drift() -> None:
    with pytest.raises(ValueError, match="shape"):
        _resolution_status(
            np.asarray([1, 0], dtype=np.int8),
            np.asarray([[32, 14]], dtype=np.int16),
            horizon=32,
        )
    with pytest.raises(ValueError, match="integers"):
        _resolution_status(
            np.asarray([1, 0], dtype=np.int8),
            np.asarray([32.0, 14.0]),
            horizon=32,
        )
    with pytest.raises(ValueError, match="positive integer"):
        _resolution_status(
            np.asarray([1], dtype=np.int8),
            np.asarray([32], dtype=np.int16),
            horizon=0,
        )
