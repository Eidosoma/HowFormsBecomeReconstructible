from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fep_surprise_25.campaign import (
    benchmark as base_benchmark,
    register as base_register,
    screen as base_screen,
    validate_stage as base_validate,
)
from fep_surprise_25.config import profile_config as base_profile_config
from fep_surprise_25a.campaign import config_for_source, run_all, status
from fep_surprise_25a.config import (
    GRACEFUL_STOP_SECONDS,
    SCIENTIFIC_BUDGET_SECONDS,
    profile_config,
    reference_lineages,
)
from fep_surprise_25a.worker import (
    Cell25Spec,
    ReferenceShortfall,
    _fit_observer_amended,
    deterministic_reference_indices,
)


def _source_screen(root: Path) -> None:
    config = base_profile_config("smoke")
    base_validate(root, config)
    base_benchmark(root, config, workers=2)
    base_register(root, config)
    base_screen(root, config, workers=2)


def test_amendment_full_budget_and_reference_cohorts_are_frozen() -> None:
    config = profile_config("full")
    assert config.scientific_budget_seconds == SCIENTIFIC_BUDGET_SECONDS
    assert config.graceful_stop_seconds == GRACEFUL_STOP_SECONDS
    assert config.confirmation.minimum_reference_states == 1200
    assert config.confirmation.training_subsample == 600
    assert reference_lineages("full", "native") == 16
    assert reference_lineages("full", "sigma_500") == 96


def test_reference_selector_is_deterministic_and_preserves_lineages(tmp_path: Path) -> None:
    lineages = np.repeat(np.arange(8), 30)
    fissions = np.tile(np.arange(30), 8)
    spec = Cell25Spec(189, "02", "stable", tmp_path / "screen", tmp_path)
    first, metadata = deterministic_reference_indices(
        lineages, fissions, 80, "1" * 64, spec, "sigma_500"
    )
    second, _ = deterministic_reference_indices(
        lineages, fissions, 80, "1" * 64, spec, "sigma_500"
    )
    assert np.array_equal(first, second)
    assert len(first) == 160
    assert set(np.unique(lineages[first])) == set(range(8))
    assert metadata["available_by_half"] == [120, 120]
    with pytest.raises(ReferenceShortfall, match="AMENDMENT_REFERENCE_SHORTFALL_NO_VERDICT"):
        deterministic_reference_indices(
            lineages, fissions, 121, "1" * 64, spec, "sigma_500"
        )


def test_observer_fit_uses_numeric_parity_even_when_lineage_ids_have_gaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage_ids = np.asarray([0, 2, 4, 8, 1, 3, 7, 11], dtype=np.int16)
    parents = np.tile(np.arange(1, 101), (8, 1))
    parents = np.asarray([row * 0 for row in parents], dtype=np.int64)
    parents[:, 0] = 80
    phases = np.repeat(parents[:, None, :], 5, axis=1)
    observed: list[tuple[set[int], int]] = []

    def fake_fit(
        training_counts: np.ndarray,
        training_lineages: np.ndarray,
        calibration_phase_counts: np.ndarray,
        **kwargs: object,
    ) -> object:
        observed.append((set(training_lineages.tolist()), len(calibration_phase_counts)))
        return object()

    monkeypatch.setattr("fep_surprise_15.observers._fit_half", fake_fit)
    result = _fit_observer_amended(
        parents,
        phases,
        lineage_ids,
        pseudocount=0.5,
        reference_mass=80,
        pca_variance=0.95,
        pca_min=2,
        pca_max=20,
        knn_k=20,
        mixture_k_max=6,
        training_subsample=600,
        seed=25,
    )
    assert result.halves[0] is not result.halves[1]
    assert observed == [({0, 2, 4, 8}, 4), ({1, 3, 7, 11}, 4)]


def test_complete_amendment_smoke_reuses_only_the_sealed_screen(tmp_path: Path) -> None:
    source = tmp_path / "source"
    amendment = tmp_path / "amendment"
    _source_screen(source)
    source_files_before = {
        str(path.relative_to(source)): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }
    config = config_for_source(source, "smoke")
    results = run_all(source, amendment, config, workers=2)
    assert len(results) == 8
    source_files_after = {
        str(path.relative_to(source)): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }
    assert source_files_after == source_files_before

    confirmation = amendment / "smoke" / "confirmation"
    designs = sorted((confirmation / "cells").glob("*_design.joblib"))
    futures = sorted((confirmation / "cells").glob("*_futures.joblib"))
    assert len(designs) == 6
    assert len(futures) == 6
    metrics = json.loads(
        (amendment / "smoke" / "analysis" / "metrics.json").read_text()
    )
    assert metrics["decision"]["integrity_verdict"] == "VALID_WITH_PREOUTCOME_AMENDMENT"
    assert metrics["decision"]["regime_verdict"] == "NONSCIENTIFIC_PROFILE"
    assert metrics["decision"]["amendment_secondary_not_a_primary_rescue"] is True
    state = status(source, amendment, "smoke")
    assert all(
        state[name]["sealed"]
        for name in (
            "source_audit",
            "validation",
            "benchmark",
            "registration",
            "confirmation",
            "confirmation_replay",
            "analysis",
        )
    )
