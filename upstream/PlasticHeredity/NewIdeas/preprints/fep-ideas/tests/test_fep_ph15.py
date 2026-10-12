from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from fep_ph15.analysis import safe_spearman
from fep_ph15 import campaign
from fep_ph15.campaign import analyze_stage, run_all, status
from fep_ph15.config import MASTER_SEED, SCREEN_BUDGETS, profile_config
from fep_ph15.environment import GardGoalAlignmentEnvironment, apply_molecular_dose
from fep_ph15.models import ModelCounts, model_from_counts, with_preferences
from fep_ph15.screen import (
    actionability_label,
    choose_actuator,
    screen_seed_domains,
    select_challenges,
)
from fep_ph15.simulation import BehaviorTrace, fitted_thresholds
from fep_ph15.types import ActionChannel, ActuatorSetting, PreferenceMode
from fep_ph15.validation import _design, validate_experiment
from fep_ph15.worker import cohort_seed_domains
from fep_ph1.gard import generate_beta, generate_initial_composition


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _model(config):
    counts = ModelCounts.empty()
    for state in range(9):
        observation = (state % 4, state % 3, state % 3, state % 4)
        counts.add_initial(state, observation)
        for action in range(4):
            counts.add_transition(state, action, (state + action + 1) % 9, observation)
    return model_from_counts(counts, config, PreferenceMode.BALANCED)


def test_full_contract_is_four_hours_and_fresh() -> None:
    config = profile_config("full")
    assert config.master_seed == MASTER_SEED
    assert config.wall_time_limit_seconds == 14_400
    assert config.graceful_stop_seconds == 13_800
    assert config.registration_projection_ceiling_seconds == 11_700
    assert config.screen_matrices == 24
    assert config.development_matrices == 32
    assert config.branches == 4 and config.horizon == 48
    assert config.evaluation_matrices == 80


def test_uptake_ordering_and_molecular_dose_contracts() -> None:
    config = profile_config("smoke")
    beta = generate_beta(config.gard, np.random.default_rng(41))
    initial = generate_initial_composition(config.gard, np.random.default_rng(42))
    environment = GardGoalAlignmentEnvironment(
        config, _design(config, ActionChannel.UPTAKE), beta, initial, 43, 44, 45
    )
    environment.regime = 0
    assert environment.exposure_multiplier(1) == 1.20
    assert environment.exposure_multiplier(0) == 0.70
    assert environment.exposure_multiplier(2) == 0.45
    waited = environment.step(0)
    assert waited.physical_action_cost == 0.0
    environment = GardGoalAlignmentEnvironment(
        config, _design(config, ActionChannel.UPTAKE), beta, initial, 43, 44, 45
    )
    adapted = environment.step(1)
    assert adapted.physical_action_cost > 0.0
    environment = GardGoalAlignmentEnvironment(
        config, _design(config, ActionChannel.UPTAKE), beta, initial, 43, 44, 45
    )
    environment.regime = 2
    assert environment.exposure_multiplier(0) == 0.50
    assert environment.exposure_multiplier(1) == 0.40
    assert environment.exposure_multiplier(3) == 0.475

    scores = np.linspace(-1.0, 1.0, config.gard.n_types)
    edited, edits = apply_molecular_dose(initial, scores, 8)
    repeated, repeated_edits = apply_molecular_dose(initial, scores, 8)
    assert edited.sum() == initial.sum()
    assert np.all(edited >= 0)
    assert len(edits) == 8
    assert np.array_equal(edited, repeated)
    assert edits == repeated_edits


def test_challenge_selection_ties_and_nonactionable_retention() -> None:
    growth = np.asarray([[[[50, 70, 90, 110]], [[60, 80, 100, 130]]]], dtype=np.int32)
    completed = np.ones_like(growth, dtype=np.int8)
    selection = select_challenges(growth, completed)
    assert selection == select_challenges(growth, completed)
    assert selection.hard_budget in SCREEN_BUDGETS
    assert selection.transition_budget in SCREEN_BUDGETS
    assert selection.hard_budget != selection.transition_budget
    settings = (
        ActuatorSetting("direct", 1, "NON_ACTIONABLE", 0.0, 0.0),
        ActuatorSetting("inverted", 1, "NON_ACTIONABLE", 0.0, 0.0),
    )
    selected = choose_actuator(
        ActionChannel.UPTAKE,
        settings,
        np.asarray([[0.2, 0.2], [0.1, 0.1]]),
        np.asarray([0.3, 0.3]),
    )
    assert selected.polarity == "direct"
    assert selected.actionability == "NON_ACTIONABLE"
    assert actionability_label(0.11, 0.09) == "ACTIONABLE"
    assert actionability_label(-0.01, 0.01) == "MIXED"


def test_preferences_firewall_seeds_and_constant_statistics() -> None:
    config = profile_config("smoke")
    balanced = _model(config)
    growth = with_preferences(balanced, PreferenceMode.GROWTH, information_gain=True)
    assert np.array_equal(balanced.C[0], growth.C[0])
    assert np.array_equal(balanced.C[1], np.asarray((-0.5, 0.0, 0.5)))
    assert np.all(growth.C[1] == 0.0)
    assert np.all(balanced.C[2] == 0.0) and np.all(balanced.C[3] == 0.0)
    seeds = [*screen_seed_domains(config).values(), *cohort_seed_domains(config).values()]
    assert len(seeds) == len(set(seeds))
    result = safe_spearman(np.ones(4), np.arange(4.0))
    assert result["rho"] is None
    assert result["p_exploratory"] is None
    assert result["undefined_reason"] == "constant_predictor"


def test_short_development_trace_keeps_growth_thresholds_positive() -> None:
    trace = BehaviorTrace(
        regimes=np.asarray([0, 0, 0], dtype=np.int8),
        raw_growth=np.asarray([0, 0, 1], dtype=np.int32),
        raw_similarity=np.ones(3),
        raw_alignment=np.full(3, 0.5),
        cues=np.zeros(3, dtype=np.int8),
        terminal=np.zeros(3, dtype=np.int8),
        actions=np.asarray([0, 0], dtype=np.int8),
    )
    thresholds = fitted_thresholds([trace])
    assert thresholds.growth[0] >= 1.0
    assert thresholds.growth[1] > thresholds.growth[0]


def test_validation_includes_physical_identity_and_reference_agreement(tmp_path: Path) -> None:
    result = validate_experiment(profile_config("smoke"), tmp_path, "test-source")
    assert result["all_pass"] is True
    checks = {value["name"]: value for value in result["checks"]}
    assert checks["neutral_retained_identity_02"]["passed"]
    assert checks["neutral_retained_identity_03"]["passed"]
    assert checks["action_lesion_noop_physics_identity"]["passed"]
    assert checks["inference_reference_agreement"]["passed"]
    assert checks["preference_and_heldout_event_firewall"]["passed"]


def test_complete_smoke_exercises_all_paths_and_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = profile_config("smoke")
    try:
        analyze_stage(tmp_path, config)
    except (FileNotFoundError, RuntimeError):
        pass
    else:
        raise AssertionError("analysis must not run before exact replay")
    result = run_all(tmp_path, config)
    metrics = json.loads((result / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["decision"]["integrity_verdict"] == "VALID"
    assert metrics["decision"]["scientific_status"] == "WORKFLOW_ONLY"
    assert metrics["decision"]["positive_negative_classifier"] is None
    assert len(list((tmp_path / "smoke" / "screen" / "cells").glob("*.json"))) == 8
    assert len(list((tmp_path / "smoke" / "simulation" / "cells").glob("*.json"))) == 32
    screen_replay = json.loads((tmp_path / "smoke" / "screen-replay" / "replay.json").read_text())
    replay = json.loads((tmp_path / "smoke" / "replay" / "replay.json").read_text())
    assert screen_replay["all_exact"] is True
    assert replay["all_exact"] is True
    controller_counts = set()
    for path in (tmp_path / "smoke" / "simulation" / "cells").glob("*.json"):
        controller_counts.add(len(json.loads(path.read_text())["controllers"]))
    assert controller_counts == {10, 13}
    state = status(tmp_path, "smoke")
    assert all(state[name] for name in ("validation", "screen", "screen_replay", "registered", "fit", "simulation", "replay", "analysis"))
    assert state["current_stage"] == "complete"
    assert state["eta_seconds"] == 0.0
    assert state["runner_alive"] is False
    assert state["registered_source_current"] is True
    monkeypatch.setattr(
        campaign,
        "elapsed_seconds",
        lambda _run_root, value: float(value.registration_projection_ceiling_seconds),
    )
    with pytest.raises(RuntimeError, match="elapsed clock plus projected"):
        campaign.register(tmp_path, config)


def test_detached_scripts_have_valid_shell_syntax() -> None:
    paths = [
        PROJECT_ROOT / "scripts" / name
        for name in (
            "run_fep_ph15_campaign.sh", "run_fep_ph15_detached.sh",
            "status_fep_ph15.sh", "control_fep_ph15.sh",
        )
    ]
    subprocess.run(["bash", "-n", *map(str, paths)], check=True)
    launcher = paths[1].read_text(encoding="utf-8")
    assert "tmux new-session -d" in launcher
    assert "startup handshake" in launcher
