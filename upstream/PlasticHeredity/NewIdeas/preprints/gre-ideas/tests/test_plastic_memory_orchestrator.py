from __future__ import annotations

from pathlib import Path

from gre_sim.artifacts import read_json, sha256_file, verify_checksums
from gre_sim.plastic_memory_evolution import (
    confirmatory_evolution_spec,
    quick_evolution_spec,
)
from gre_sim.plastic_memory_orchestrator import (
    _confirmed_carriers,
    run_full_plastic_memory_campaign,
)
from gre_sim.plastic_memory_protocols import MARK_GRID, quick_spec
from gre_sim.plastic_memory_config import CueDose


def test_quick_full_memory_orchestrator_auto_confirms_and_resumes(
    tmp_path: Path, monkeypatch
) -> None:
    spec = quick_spec()
    monkeypatch.setattr(
        "gre_sim.plastic_memory_orchestrator.calibration_spec", lambda: spec
    )
    monkeypatch.setattr(
        "gre_sim.plastic_memory_orchestrator.discovery_spec", lambda cues: spec
    )
    monkeypatch.setattr(
        "gre_sim.plastic_memory_orchestrator.confirmation_spec",
        lambda cues, marks: spec,
    )
    monkeypatch.setattr(
        "gre_sim.plastic_memory_orchestrator.select_calibrated_cues",
        lambda analysis: {
            "all_primary_ready": True,
            "models": {
                "boolean-primary": {
                    "ready": True,
                    "cue": {"fraction": 1.0, "dwell": 2},
                },
                "wagner-primary": {
                    "ready": True,
                    "cue": {"fraction": 1.0, "dwell": 2},
                },
            },
        },
    )
    monkeypatch.setattr(
        "gre_sim.plastic_memory_orchestrator.select_mark_candidates",
        lambda analysis: {
            "models": {
                "boolean-primary": {"selected": None, "passing": []},
                "wagner-primary": {"selected": None, "passing": []},
            },
            "common_selected": None,
        },
    )
    monkeypatch.setattr(
        "gre_sim.plastic_memory_orchestrator._advance_from_discovery", lambda analysis: True
    )
    monkeypatch.setattr(
        "gre_sim.plastic_memory_orchestrator.exploratory_evolution_spec",
        lambda cues: quick_evolution_spec(),
    )
    monkeypatch.setattr(
        "gre_sim.plastic_memory_orchestrator._confirmed_carriers",
        lambda analysis, marks: (),
    )
    destination = tmp_path / "campaign"
    run_full_plastic_memory_campaign(
        destination, workers=2, gard_root=None, include_evolution=True
    )
    verify_checksums(destination)
    manifest = read_json(destination / "campaign-manifest.json")
    assert manifest["confirmation_launched"]
    assert (destination / "confirmation" / "SHA256SUMS").is_file()
    assert (destination / "evolution-exploratory" / "SHA256SUMS").is_file()
    digest = sha256_file(destination / "SHA256SUMS")
    run_full_plastic_memory_campaign(
        destination, workers=2, gard_root=None, include_evolution=True
    )
    assert sha256_file(destination / "SHA256SUMS") == digest


def test_state_and_mark_confirmations_are_both_retained_for_evolution() -> None:
    mark = MARK_GRID[0]
    analysis = {
        "state_transfer_gates": {"boolean-primary": {"passed": True}},
        "mark_transfer_gates": {
            "boolean-primary": {mark.name: {"passed": True}}
        },
    }
    confirmed = _confirmed_carriers(
        analysis, {"boolean-primary": mark.name}
    )
    assert {(carrier, setting.name) for _, carrier, setting in confirmed} == {
        ("state", "none"),
        ("slow_mark", mark.name),
    }
    spec = confirmatory_evolution_spec(
        {"boolean-primary": CueDose(1.0, 4)}, confirmed
    )
    assert len(spec.cells) == 6
    assert len({cell.name for cell in spec.cells}) == 6
