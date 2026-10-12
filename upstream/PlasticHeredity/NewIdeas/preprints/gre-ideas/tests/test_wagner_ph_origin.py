from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gre_sim.artifacts import canonical_digest, read_json, write_json
from gre_sim.local_ph_dynamics import LocalCarrierState, blank_local, read_local, write_local
from gre_sim.wagner import WagnerRulebook
from gre_sim.wagner_ph_bridge_evolution import _recombine_carrier
from gre_sim.wagner_ph_origin_audit import (
    replay_origin_audit_population,
    run_origin_audit,
    verify_origin_audit,
)
from gre_sim.wagner_ph_origin_campaign import prepare_completion_extension
from gre_sim.wagner_ph_origin_evolution import (
    origin_resource_cost,
    origin_training_score,
    replay_origin_population,
    run_origin_evolution,
    verify_origin_evolution,
)
from gre_sim.wagner_ph_origin_protocols import (
    origin_audit_spec,
    origin_campaign_spec,
    origin_evolution_template,
)
from gre_sim.wagner_ph_origin_screen import analyze_origin_screen


def test_origin_contract_is_six_by_six_cpu_only_and_four_hour_bounded() -> None:
    spec = origin_campaign_spec()
    assert spec.evolution_template.population_count == 36
    assert spec.evolution_template.population_size == 24
    assert spec.evolution_template.generations == 28
    assert spec.maximum_workers == 4
    assert spec.hard_wall_seconds == 14_400
    assert spec.soft_wall_seconds == 13_500
    assert spec.projected_wall_seconds <= spec.soft_wall_seconds
    assert sum(spec.stage_reservations_seconds) == 14_400
    dormant, weak = spec.evolution_template.scaffolds
    assert (dormant.write_rate, dormant.coupling, dormant.k) == (0.0, 0.0, 1)
    assert (weak.write_rate, weak.coupling, weak.k) == (0.10, 0.10, 1)
    smoke = origin_campaign_spec(smoke=True)
    assert smoke.screen.master_seed != spec.screen.master_seed
    assert smoke.evolution_template.master_seed != spec.evolution_template.master_seed
    assert smoke.audit.master_seed != spec.audit.master_seed


def test_zero_writer_and_reader_are_inert_but_mutation_can_activate() -> None:
    dormant = origin_evolution_template(smoke=True).scaffold("dormant")
    mask = (0,)
    written = write_local(blank_local(10), (1023,), dormant, mask)
    assert written == blank_local(10)
    marked = LocalCarrierState((1.0,) * 10)
    assert read_local(17, marked, dormant.coupling, np.random.default_rng(1)) == 17
    random = np.random.default_rng(9)
    descendants = [_recombine_carrier(dormant, dormant, random) for _ in range(100)]
    assert any(value.write_rate > 0.0 for value in descendants)
    assert any(value.coupling > 0.0 for value in descendants)


def _fixed_assay() -> dict:
    def cell(risk: float, correct: float) -> dict:
        return {
            "0": {"forced_break": {"risk_gain": 0.0, "correct_rate": 0.0}},
            "8": {
                "forced_break": {"risk_gain": risk, "correct_rate": correct}
            },
        }

    return {
        "cells": {
            "candidate.intact": cell(0.60, 0.80),
            "candidate.renewal-off": cell(0.20, 0.40),
            "candidate.harsher": cell(0.30, 0.50),
            "candidate.harsher-renewal-off": cell(0.10, 0.20),
            "zero": cell(0.0, 0.20),
            "zero.harsher": cell(0.0, 0.20),
        }
    }


def test_objectives_differ_only_by_registered_access_and_weighting(monkeypatch) -> None:
    spec = origin_evolution_template(smoke=True)
    carrier = spec.scaffold("weak")
    genotype = (WagnerRulebook.random(10, np.random.default_rng(3)), carrier)
    monkeypatch.setattr(
        "gre_sim.wagner_ph_origin_evolution.assay_origin_genotype",
        lambda *args, **kwargs: _fixed_assay(),
    )
    task: dict = {}
    explicit = origin_training_score(
        genotype, task, spec, "weak_explicit_renewal", 0, 0
    )
    permissive = origin_training_score(
        genotype, task, spec, "weak_permissive_performance", 0, 0
    )
    passive = origin_training_score(
        genotype, task, spec, "weak_passive_locked", 0, 0
    )
    cost = origin_resource_cost(carrier, spec)
    assert explicit["fitness"] == pytest.approx(0.475 - cost)
    assert permissive["fitness"] == pytest.approx(0.50 - cost)
    assert passive["fitness"] == pytest.approx((1.0 / 6.0) - cost)
    assert {value["resource_cost"] for value in (explicit, permissive, passive)} == {
        cost
    }


def _screen_assay(qualifies: bool) -> dict:
    cells: dict[str, dict] = {}
    for condition in ("candidate.intact", "candidate.renewal-off"):
        generations = {}
        for generation in (0, 8, 12):
            events = {}
            for challenge in ("forced_break", "release_only"):
                if condition == "candidate.intact":
                    gain = 0.35 if qualifies else 0.05
                    correct = 0.75 if qualifies else 0.45
                else:
                    gain = 0.10
                    correct = 0.55 if qualifies else 0.44
                events[challenge] = {
                    "risk_gain": gain,
                    "correct_rate": correct,
                }
            generations[str(generation)] = events
        cells[condition] = generations
    return {"cells": cells}


def test_screen_mechanically_selects_first_qualified_and_freezes_neighbor() -> None:
    spec = origin_campaign_spec(smoke=True).screen
    results = []
    for environment_index, environment in enumerate(spec.environments):
        for population in range(spec.parent_populations):
            results.append(
                {
                    "environment": environment.name,
                    "population_index": population,
                    "assay": _screen_assay(environment_index >= 2),
                }
            )
    analysis = analyze_origin_screen(results, spec)
    assert analysis["selection"]["selected_environment"] == spec.environments[2].name
    assert analysis["selection"]["next_harsher_environment"] == spec.environments[3].name
    assert analysis["selection"]["primary_screen_passed"] is True


def test_origin_smoke_seals_resumes_replays_and_audits_pedigrees(tmp_path: Path) -> None:
    evolution_spec = origin_evolution_template(smoke=True)
    evolution = run_origin_evolution(
        evolution_spec, tmp_path / "evolution", workers=2
    )
    assert run_origin_evolution(evolution_spec, evolution, workers=1) == evolution
    assert verify_origin_evolution(evolution)["populations"] == 6
    assert replay_origin_population(
        evolution, "dormant_explicit_renewal.population-000"
    )["matches"]

    audit = run_origin_audit(
        evolution,
        origin_audit_spec(smoke=True),
        tmp_path / "audit",
        workers=2,
    )
    verification = verify_origin_audit(audit)
    assert verification["populations"] == 6
    assert verification["pedigree_rows"] == 48
    assert replay_origin_audit_population(
        audit, "dormant_explicit_renewal.population-000"
    )["matches"]
    result = read_json(
        audit
        / "populations"
        / "dormant_explicit_renewal.population-000.json"
    )
    assert result["descendants_receive_no_inducing_cue"] is True
    assert result["full_causal_panel"] is True
    assert len(result["pedigree_rows"]) == 24
    assert set(result["causal_metrics"]) == {
        "founder_write_off_g8",
        "reader_off_g8",
        "renewal_off_g8",
        "renewal_block_g1_g4_g8",
        "renewal_block_g9_g12_g12",
        "shuffle_g8",
        "erasure_reduction_g8",
        "rescue_fraction_g8",
        "donor_following_g0",
    }


def test_origin_detached_supervisor_has_strict_persistent_four_hour_ledger() -> None:
    runner = Path("scripts/run-wagner-ph-origin-detached.sh").read_text(
        encoding="utf-8"
    )
    status = Path("scripts/status-wagner-ph-origin.sh").read_text(encoding="utf-8")
    assert "maximum_wall_seconds=14400" in runner
    assert "soft_wall_seconds=13500" in runner
    assert "GRE_WAGNER_PH_ORIGIN_PRIOR_CONSUMED_SECONDS" in runner
    assert "GRE_WAGNER_PH_ORIGIN_SOFT_DEADLINE_EPOCH" in runner
    assert "time-budget-exhausted" in runner
    assert "sleep 60" in runner and "kill -KILL" in runner
    assert "extension" not in runner.lower()
    assert "heartbeat age" in status

    extension = Path(
        "scripts/resume-wagner-ph-origin-extension-detached.sh"
    ).read_text(encoding="utf-8")
    assert "maximum_extension_seconds=14400" in extension
    assert "soft_extension_seconds=13500" in extension
    assert "original four-hour supervisor is not recorded as exhausted" in extension
    assert "GRE_WAGNER_PH_ORIGIN_EXTENSION_PRIOR_CONSUMED_SECONDS" in extension
    assert "completion extension status" in status


def test_origin_completion_extension_is_transparent_digest_bound_and_idempotent(
    tmp_path: Path,
) -> None:
    spec = origin_campaign_spec()
    registration = {
        "format": "gre-wagner-ph-origin-campaign-v1",
        "protocol": spec.to_dict(),
    }
    write_json(tmp_path / "registration.json", registration)
    populations = tmp_path / "evolution" / "populations"
    populations.mkdir(parents=True)
    write_json(
        populations / "dormant_explicit_renewal.population-000.json", {"done": True}
    )
    write_json(
        populations
        / "dormant_explicit_renewal.population-001.checkpoint.json",
        {"generation": 12},
    )
    amendment = prepare_completion_extension(
        tmp_path,
        spec,
        original_consumed_seconds=14_341,
    )
    assert amendment["original_attempt_status"] == "time-budget-exhausted"
    assert amendment["original_registration_digest"] == canonical_digest(registration)
    assert amendment["total_cumulative_authorized_seconds"] == 28_741
    assert amendment["completed_evolution_populations_before_extension"] == 1
    assert amendment["partial_evolution_checkpoints_before_extension"] == 1
    assert amendment["screen_outcome_examined_before_extension"] is True
    assert amendment["evolution_scores_examined_before_extension"] is False
    assert amendment["audit_outcomes_examined_before_extension"] is False
    assert amendment["final_verdict_existed_before_extension"] is False
    assert prepare_completion_extension(
        tmp_path,
        spec,
        original_consumed_seconds=14_341,
    ) == amendment


def test_origin_cli_maps_soft_timeout_to_budget_exhaustion(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "gre_sim.wagner_ph_origin_cli.run_wagner_ph_origin_campaign",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("soft boundary")),
    )
    from gre_sim.wagner_ph_origin_cli import campaign_main

    assert campaign_main(
        ["--parent", str(tmp_path / "parent"), "--output", str(tmp_path / "out")]
    ) == 124
