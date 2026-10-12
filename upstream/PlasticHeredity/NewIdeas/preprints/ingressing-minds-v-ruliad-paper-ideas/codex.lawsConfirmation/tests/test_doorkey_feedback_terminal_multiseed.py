import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("torch")

from laws_confirmation.doorkey_feedback_terminal_multiseed import (
    REGISTERED_REPLICATES,
    SHAPED_REFERENCE_RUN,
    credit_routing_classification,
    paired_seed_summary,
    qualify_shaped_reference,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _summary(
    replicate: int,
    classification: str = "NO_CHAIN_COMPLETION",
    training_successes: int = 0,
    rate: float = 0.0,
) -> dict:
    spec = REGISTERED_REPLICATES[replicate]
    chain = [
        {
            "from": "episode_start",
            "to": "explore",
            "reached": 1,
            "eligible": 2,
            "conditional_probability": 0.5,
        },
        {
            "from": "explore",
            "to": "find_key",
            "reached": 0,
            "eligible": 1,
            "conditional_probability": 0.0,
        },
    ]
    return {
        **spec,
        "classification": classification,
        "training_successes": training_successes,
        "deterministic_success_rate": rate,
        "fixed_random_success_rate": rate,
        "final_chain": {
            "deterministic": chain,
            "fixed_random": chain,
        },
    }


def test_credit_routing_classification_separates_exposure_and_completion():
    completed = "CHAIN_COMPLETION_BOTH_MODES"
    assert (
        credit_routing_classification(
            [_summary(index, completed, 3, 0.25) for index in range(4)]
        )
        == "TERMINAL_CHAIN_ALL_SEEDS"
    )
    assert (
        credit_routing_classification(
            [
                _summary(0, completed, 1, 0.25),
                *[_summary(index) for index in range(1, 4)],
            ]
        )
        == "TERMINAL_CHAIN_SEED_SENSITIVE"
    )
    assert (
        credit_routing_classification(
            [_summary(index, training_successes=index) for index in range(4)]
        )
        == "TERMINAL_REWARD_OBSERVED_NO_EVALUATION_CHAIN"
    )
    assert (
        credit_routing_classification([_summary(index) for index in range(4)])
        == "NO_TERMINAL_REWARD_OBSERVED"
    )
    with pytest.raises(ValueError, match="at least one"):
        credit_routing_classification([])


def test_paired_seed_summary_checks_identity_and_preserves_chain():
    terminal = _summary(0, training_successes=2, rate=0.125)
    shaped = _summary(0, "CHAIN_COMPLETION_BOTH_MODES", 20, 0.75)
    result = paired_seed_summary(terminal, shaped)
    assert result["replicate"] == 0
    assert result["success_rate"]["deterministic"] == {
        "terminal": 0.125,
        "shaped": 0.75,
        "terminal_minus_shaped": -0.625,
    }
    assert result["chain_comparison"]["fixed_random"][1]["to"] == "find_key"

    wrong = dict(shaped, training_seed=999)
    with pytest.raises(ValueError, match="one seed"):
        paired_seed_summary(terminal, wrong)


def test_shaped_reference_gate_verifies_seed_table_and_all_hashes(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("frozen\n", encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}\n", encoding="utf-8")
    replication_path = tmp_path / "replication.json"
    replication_path.write_text(
        json.dumps(
            {
                "run_id": SHAPED_REFERENCE_RUN,
                "completed_cleanly": True,
                "seed_classification": "ALL_SEEDS_COMPLETE_BOTH_MODES",
                "replicate_summaries": [
                    {
                        "replicate": row["replicate"],
                        "birth_seed": row["birth_seed"],
                        "training_seed": row["training_seed"],
                    }
                    for row in REGISTERED_REPLICATES
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": SHAPED_REFERENCE_RUN,
                "input_sha256": {str(source): _sha256(source)},
            }
        ),
        encoding="utf-8",
    )
    hashes_path = tmp_path / "output_hashes.sha256"
    hashes_path.write_text(
        f"{_sha256(artifact)}  {artifact}\n", encoding="utf-8"
    )

    result = qualify_shaped_reference(
        replication_path, manifest_path, hashes_path
    )
    assert result["passes"], result

    source.write_text("changed\n", encoding="utf-8")
    changed = qualify_shaped_reference(
        replication_path, manifest_path, hashes_path
    )
    assert not changed["passes"]
    assert not changed["gates"]["all_shaped_inputs_verify"]
