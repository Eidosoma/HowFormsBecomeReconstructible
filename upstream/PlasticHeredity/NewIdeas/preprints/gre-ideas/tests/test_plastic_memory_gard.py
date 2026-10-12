from __future__ import annotations

from pathlib import Path

import numpy as np

from gre_sim.artifacts import write_jsonl_gz
from gre_sim.plastic_memory_gard import (
    _analyze,
    _composition_counts,
    _force_break,
    _load_sim,
    _resolve_sim_path,
    _simulate_source,
    _summarize,
)


def test_frozen_gard_adapter_is_read_only_and_endpoints_work() -> None:
    sibling = Path(__file__).resolve().parents[1].parent / "strict-8-paper-preparations"
    sim_path = _resolve_sim_path(sibling)
    sim = _load_sim(sim_path)
    assert sim.NG == 100
    form_a = np.zeros(100)
    form_b = np.zeros(100)
    form_a[:20] = 1.0
    form_b[20:40] = 1.0
    state = _composition_counts(form_a, 40)
    assert int(state.sum()) == 40
    broken = _force_break(state, form_a, form_b)
    assert sim.cosine_h(state.astype(float), broken.astype(float)) <= 0.85

    daughters = np.tile(state, (8, 1))
    trajectory = {
        "daughters": daughters,
        "H": np.full(8, 0.95),
        "died": False,
        "n_done": 8,
    }
    summary = _summarize(trajectory, form_a, form_b)
    assert summary["correct_hold8"]
    assert not summary["wrong_hold8"]


def test_gard_confirmation_analysis_streams_and_requires_absolute_transfer(
    tmp_path: Path,
) -> None:
    records = []
    for model in ("gard-02", "gard-03"):
        candidate = model.removeprefix("gard-")
        for source_index in range(4):
            source = f"{model}.source-{source_index}"
            for history in ("A", "B"):
                for half, future_index in (("A", 0), ("B", 2)):
                    digest = f"{model}.{source}.{history}.{future_index}"
                    for carrier, correct in (
                        ("self_continuation", True),
                        ("state_transplant", True),
                        ("reset_both", False),
                    ):
                        records.append(
                            {
                                "future_id": f"{digest}.{carrier}",
                                "condition": "gard-state-primary",
                                "source_id": source,
                                "model": model,
                                "candidate": candidate,
                                "history": history,
                                "cue_fraction": 1.0,
                                "cue_dwell": 4,
                                "carrier": carrier,
                                "washout_age": 0,
                                "challenge": "neutral_damage",
                                "future_index": future_index,
                                "half": half,
                                "acquired": True,
                                "control_match_exact": True,
                                "form_destination": history if correct else "other",
                                "trace_digest": (
                                    digest
                                    if carrier
                                    in {"self_continuation", "state_transplant"}
                                    else None
                                ),
                                "correct_hold8": correct,
                            }
                        )
    path = tmp_path / "gard-futures.jsonl.gz"
    write_jsonl_gz(path, records)
    analysis = _analyze(path, calibration=False)
    assert analysis["record_count"] == len(records)
    assert analysis["self_transplant_equivalence"]["equal"]
    assert all(gate["passed"] for gate in analysis["gates"].values())


def test_gard_source_simulation_uses_compact_condition_blocks(
    tmp_path: Path,
) -> None:
    fake = tmp_path / "fake_gard.py"
    fake.write_text(
        "import numpy as np\n"
        "NG = 4\n"
        "def run_fissions(state, beta, candidate, n, rng):\n"
        "    state = np.asarray(state, dtype=np.int64)\n"
        "    return {'final': state.copy(), 'daughters': np.tile(state, (n, 1)), "
        "'H': np.ones(n), 'died': False, 'n_done': n}\n",
        encoding="utf-8",
    )
    source = {
        "source_id": "fake-world",
        "beta": np.eye(4).tolist(),
        "forms": [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
        "base": [10, 10, 0, 0],
        "permutation": [1, 0, 3, 2],
    }
    protocol = {
        "seed_label": "fake-confirmation",
        "cue_by_candidate": {"02": [[1.0, 1]], "03": [[1.0, 1]]},
        "conditions": [
            {
                "name": "gard-state-primary",
                "carriers": [
                    "self_continuation",
                    "state_transplant",
                    "reset_both",
                    "destination_matched_donor",
                    "state_pattern_shuffle",
                ],
                "washout_ages": [0],
                "challenges": ["neutral_damage"],
                "futures_per_cell": 4,
            }
        ],
        "horizon": 8,
    }
    records = _simulate_source((source, str(fake), protocol))
    assert len(records) == 2 * 2 * 5 * 4
    assert len({record["future_id"] for record in records}) == len(records)
    paired = {}
    for record in records:
        if record["carrier"] not in {"self_continuation", "state_transplant"}:
            continue
        key = (
            record["model"],
            record["history"],
            record["future_index"],
        )
        paired.setdefault(key, {})[record["carrier"]] = record["trace_digest"]
    assert paired and all(
        values["self_continuation"] == values["state_transplant"]
        for values in paired.values()
    )
