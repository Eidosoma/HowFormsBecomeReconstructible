import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("torch")

from laws_confirmation.doorkey_feedback_multiseed import (
    ANCHOR_RUN,
    _aggregate_classification,
    _distribution,
    _first_completion_update,
    qualify_anchor,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_first_completion_and_distribution_helpers():
    evaluations = [
        {"update": 0, "action_mode": "fixed_random", "successes": 0},
        {"update": 10, "action_mode": "fixed_random", "successes": 0},
        {"update": 20, "action_mode": "fixed_random", "successes": 2},
        {"update": 30, "action_mode": "deterministic", "successes": 0},
    ]
    assert _first_completion_update(evaluations, "fixed_random") == 20
    assert _first_completion_update(evaluations, "deterministic") is None
    assert _distribution([0.0, 0.25, 0.5, 1.0]) == {
        "minimum": 0.0,
        "median": 0.375,
        "maximum": 1.0,
        "mean": 0.4375,
    }


def test_seed_classification_helper():
    assert (
        _aggregate_classification(
            [{"classification": "CHAIN_COMPLETION_BOTH_MODES"}] * 4
        )
        == "ALL_SEEDS_COMPLETE_BOTH_MODES"
    )
    assert (
        _aggregate_classification(
            [
                {"classification": "CHAIN_COMPLETION_BOTH_MODES"},
                {"classification": "NO_CHAIN_COMPLETION"},
            ]
        )
        == "MIXED_SEED_CHAIN_COMPLETION"
    )
    assert (
        _aggregate_classification([{"classification": "NO_CHAIN_COMPLETION"}] * 2)
        == "NO_SEED_COMPLETES_CHAIN"
    )


def test_anchor_gate_checks_sources_and_outputs(tmp_path):
    workspace = Path(__file__).resolve().parents[1]
    source = Path(__file__).resolve()
    anchor = tmp_path / "extension.json"
    anchor.write_text(
        json.dumps(
            {
                "completed_cleanly": True,
                "first_100_replay_pass": True,
                "run_id": ANCHOR_RUN,
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "MANIFEST.json"
    manifest.write_text(
        json.dumps({"input_sha256": {str(source): _sha256(source)}}),
        encoding="utf-8",
    )
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("frozen\n", encoding="utf-8")
    hashes = tmp_path / "output_hashes.sha256"
    hashes.write_text(f"{_sha256(artifact)}  {artifact}\n", encoding="utf-8")

    result = qualify_anchor(workspace, anchor, manifest, hashes)
    assert result["passes"], result

    manifest.write_text(json.dumps({"input_sha256": {str(source): "0" * 64}}))
    changed = qualify_anchor(workspace, anchor, manifest, hashes)
    assert not changed["passes"]
    assert not changed["gates"]["all_anchor_workspace_inputs_unchanged"]
