from pathlib import Path

import pytest

pytest.importorskip("torch")

from laws_confirmation.doorkey_carrier_conformance import run_torch_differential


def test_numpy_carrier_is_byte_exact_against_authoritative_torch_source():
    workspace = Path(__file__).resolve().parents[1]
    reference = (
        workspace.parent.parent / "ai-11-rl-frontier/src/phrl/slot_germ.py"
    )
    result = run_torch_differential(reference, trials=64, seed=2_314_640)
    assert result["schema_equal"]
    assert result["max_prior_absolute_difference"] == 0.0
    assert result["mismatch_count"] == 0, result["first_mismatches"]
    assert result["byte_exact"]

