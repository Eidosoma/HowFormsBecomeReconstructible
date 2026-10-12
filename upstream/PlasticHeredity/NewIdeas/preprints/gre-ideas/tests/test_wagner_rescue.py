from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from gre_sim.artifacts import (
    canonical_digest,
    read_json,
    read_jsonl_gz,
    sha256_file,
    write_checksums,
    write_json,
)
from gre_sim.mechanism_dynamics import MechanismRulebook
from gre_sim.plastic_memory_dynamics import AttractorPair
from gre_sim.plastic_memory_protocols import calibration_spec
from gre_sim.wagner import WagnerRulebook
from gre_sim.wagner_rescue_campaign import expected_rescue_futures
from gre_sim.wagner_rescue_config import CueIntervention, WagnerRescueSpec
from gre_sim.wagner_rescue_dynamics import develop_with_intervention
from gre_sim.wagner_rescue_orchestrator import (
    run_full_wagner_rescue_campaign,
    verify_wagner_rescue_campaign,
)
from gre_sim.wagner_rescue_protocols import quick_rescue_spec, screen_spec
from gre_sim.wagner_rescue_selection import select_screen_finalists
from gre_sim.wagner_rescue_study import (
    recompute_rescue_analysis,
    replay_rescue_future,
    run_rescue_study,
    verify_rescue_run,
)


def test_rescue_config_roundtrip_and_screen_count() -> None:
    quick = quick_rescue_spec()
    assert WagnerRescueSpec.from_dict(quick.to_dict()) == quick
    assert expected_rescue_futures(screen_spec()) == 288_768


def test_legacy_plastic_memory_protocol_digest_is_unchanged() -> None:
    assert canonical_digest(calibration_spec().to_dict()) == (
        "b8ced905fffad8e058d2188f6b6ae12e4fafd428a3eebfb9e6ea25037afc054c"
    )


def test_cue_modes_separate_initialization_hard_field_and_injection() -> None:
    source = WagnerRulebook(
        np.zeros((2, 2), dtype=float),
        np.asarray([-0.1, -1.0]),
        np.asarray([0, 1]),
    )
    rulebook = MechanismRulebook(source, "wagner_sequential")
    pair = AttractorPair(0, 1, 0, 3)
    nodes = (0,)
    rng = np.random.default_rng(7)

    initialization = develop_with_intervention(
        rulebook,
        0,
        CueIntervention("initialization", 0.5, 1),
        pair.right_state,
        nodes,
        0.0,
        20,
        rng,
    )
    hard = develop_with_intervention(
        rulebook,
        0,
        CueIntervention("persistent_hard", 0.5, 1),
        pair.right_state,
        nodes,
        0.0,
        20,
        rng,
    )
    field = develop_with_intervention(
        rulebook,
        0,
        CueIntervention("target_field", 0.5, 1, 1.0),
        pair.right_state,
        nodes,
        0.0,
        20,
        rng,
    )
    injection = develop_with_intervention(
        rulebook,
        0,
        CueIntervention("target_injection", 1.0, 1),
        pair.right_state,
        (0, 1),
        0.0,
        20,
        rng,
    )

    assert initialization.final_state == 0
    assert hard.final_state == 1
    assert field.final_state == 1
    assert injection.final_state == 3
    assert injection.status == "injected"


def test_quick_rescue_run_resumes_recomputes_and_replays(tmp_path: Path) -> None:
    destination = tmp_path / "quick"
    run_rescue_study(quick_rescue_spec(), destination, workers=1)
    assert verify_rescue_run(destination)["verified"]
    assert recompute_rescue_analysis(destination)["matches"]
    first = next(read_jsonl_gz(destination / "futures.jsonl.gz"))
    assert replay_rescue_future(destination, first["future_id"])["matches"]
    checksum = sha256_file(destination / "SHA256SUMS")
    run_rescue_study(quick_rescue_spec(), destination, workers=1)
    assert sha256_file(destination / "SHA256SUMS") == checksum


def test_rescue_run_is_worker_invariant(tmp_path: Path) -> None:
    spec = replace(quick_rescue_spec(), source_count=2)
    serial = tmp_path / "serial"
    parallel = tmp_path / "parallel"
    run_rescue_study(spec, serial, workers=1)
    run_rescue_study(spec, parallel, workers=2)
    assert sha256_file(serial / "futures.jsonl.gz") == sha256_file(
        parallel / "futures.jsonl.gz"
    )
    assert read_json(serial / "analysis.json") == read_json(
        parallel / "analysis.json"
    )


def test_rescue_run_resumes_from_a_hashed_source(
    tmp_path: Path, monkeypatch
) -> None:
    import gre_sim.wagner_rescue_study as study

    destination = tmp_path / "interrupted"
    original = study.iter_rescue_source_results

    def interrupted(registry, spec, workers, progress):
        iterator = original(registry, spec, workers, progress)
        yield next(iterator)
        raise RuntimeError("injected rescue interruption")

    monkeypatch.setattr(study, "iter_rescue_source_results", interrupted)
    with pytest.raises(RuntimeError, match="injected rescue interruption"):
        run_rescue_study(quick_rescue_spec(), destination, workers=1)
    assert len(list((destination / "shards").glob("*.manifest.json"))) == 1

    monkeypatch.setattr(study, "iter_rescue_source_results", original)
    run_rescue_study(quick_rescue_spec(), destination, workers=1)
    assert verify_rescue_run(destination)["verified"]


def test_screen_selection_keeps_mechanism_diversity() -> None:
    cells = {}
    for index, mode in enumerate(
        ("initialization", "target_field", "persistent_hard")
    ):
        cells[mode] = {
            "condition": mode,
            "role": "candidate",
            "model": {
                "name": f"model-{index}",
                "variant": "wagner_sequential",
                "gamma_variance": 0.1 if index == 0 else 0.01,
            },
            "intervention": {
                "mode": mode,
                "fraction": 1.0,
                "dwell": 1,
                "field_strength": 1.0 if mode == "target_field" else 0.0,
            },
            "histories": {
                history: {"exact_acquisition": {"lower": 0.8}}
                for history in ("A", "B")
            },
            "metrics": {
                "cue_gain_over_no_cue": {"mean": 0.2, "lower": 0.1},
                "correct_minus_wrong": {"mean": 0.2, "lower": 0.1},
            },
            "screen_passed": True,
        }
    selection = select_screen_finalists({"cells": cells})
    assert {cell["intervention"]["mode"] for cell in selection["selected"]} == {
        "initialization",
        "target_field",
        "persistent_hard",
    }


def test_quick_full_rescue_orchestrator_seals_and_resumes(
    tmp_path: Path, monkeypatch
) -> None:
    import gre_sim.wagner_rescue_orchestrator as orchestrator

    parent = tmp_path / "parent"
    (parent / "calibration").mkdir(parents=True)
    write_json(
        parent / "campaign-manifest.json",
        {"completed": True, "stopped_at": "cue-calibration"},
    )
    write_json(
        parent / "cue-selection.json",
        {"models": {"wagner-primary": {"ready": False}}},
    )
    write_json(
        parent / "calibration" / "analysis.json",
        {
            "calibration": {
                "wagner-primary.cue-1x1.history-A": {
                    "mean": 0.5,
                    "lower": 0.4,
                    "interval": [0.4, 0.6],
                    "sources": 2,
                }
            }
        },
    )
    write_checksums(parent)

    def selected(analysis):
        cell = next(
            value
            for value in analysis["cells"].values()
            if value["role"] == "candidate"
        )
        return {
            "selected": [cell],
            "selected_condition_ids": [cell["condition"]],
            "screen_ready_any": False,
            "ranking": [cell["condition"]],
        }

    def candidate(analysis):
        cell = next(
            value
            for value in analysis["cells"].values()
            if value["role"] == "candidate"
        )
        return {
            "selected": cell,
            "selected_condition_id": cell["condition"],
            "passing_condition_ids": [],
            "ranking": [cell["condition"]],
        }

    monkeypatch.setattr(orchestrator, "screen_spec", quick_rescue_spec)
    monkeypatch.setattr(
        orchestrator, "replication_spec", lambda finalists: quick_rescue_spec()
    )
    monkeypatch.setattr(
        orchestrator, "validation_spec", lambda value: quick_rescue_spec()
    )
    monkeypatch.setattr(orchestrator, "select_screen_finalists", selected)
    monkeypatch.setattr(orchestrator, "select_replication_candidate", candidate)

    output = tmp_path / "campaign"
    run_full_wagner_rescue_campaign(parent, output, workers=1)
    assert verify_wagner_rescue_campaign(output)["verified"]
    checksum = sha256_file(output / "SHA256SUMS")
    run_full_wagner_rescue_campaign(parent, output, workers=1)
    assert sha256_file(output / "SHA256SUMS") == checksum
    assert read_json(output / "campaign-manifest.json")["completed"]
