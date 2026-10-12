from __future__ import annotations

from pathlib import Path

from gre_sim.artifacts import canonical_digest, read_json, write_json, write_jsonl_gz
from gre_sim.local_ph_config import expected_local_records
from gre_sim.wagner_ph_renewal_analysis import analyze_renewal_frontier_path
from gre_sim.wagner_ph_renewal_campaign import prepare_completion_extension
from gre_sim.wagner_ph_renewal_config import RenewalCampaignSpec
from gre_sim.wagner_ph_renewal_evolution import (
    renewal_resource_cost,
    replay_renewal_population,
    run_renewal_audit,
    run_renewal_evolution,
    verify_renewal_audit,
    verify_renewal_evolution,
)
from gre_sim.wagner_ph_renewal_protocols import (
    renewal_campaign_spec,
    selected_evolution_spec,
)


def _prior_selection() -> dict:
    return read_json(Path("runs/wagner-ph-bridge-v1/evolution-selection.json"))


def test_renewal_contract_has_frontier_pairs_sixty_populations_and_six_hour_cap() -> None:
    spec = renewal_campaign_spec(_prior_selection())
    assert len(spec.frontier.study.conditions) == 50
    assert len(spec.frontier.environment_order) == 6
    assert expected_local_records(spec.frontier.study) == 512_000
    assert spec.evolution_template.population_count == 60
    assert spec.evolution_template.populations_per_treatment == 10
    assert spec.evolution_template.population_size == 32
    assert spec.evolution_template.generations == 32
    assert spec.mutation_audit.checkpoint_generations == (0, 4, 8, 12, 16)
    assert spec.mutation_audit.futures_per_history == 64
    assert spec.hard_wall_seconds == 21_600
    assert spec.soft_wall_seconds == 20_400
    assert spec.projected_wall_seconds <= spec.soft_wall_seconds
    assert sum(spec.stage_reservations_seconds) == 21_600


def _frontier_rows(spec) -> list[dict]:
    rows: list[dict] = []
    for source_index in range(3):
        source = f"source-{source_index}"
        for condition in spec.study.conditions:
            for generation in spec.study.checkpoint_generations:
                for challenge in spec.study.challenges:
                    correct = 0
                    if condition.name == "perfect-latch":
                        correct = 1
                    elif condition.name not in {"zero"}:
                        prefix = condition.name.split(".")
                        k = int(prefix[0][1:])
                        environment = prefix[1]
                        eligible = (
                            spec.environment_order.index(environment) >= 1 and k >= 5
                        )
                        if condition.intervention == "intact" and eligible and generation >= 8:
                            correct = 1
                    rows.append(
                        {
                            "future_id": f"{source}.{condition.name}.{generation}.{challenge}",
                            "source_id": source,
                            "condition": condition.name,
                            "generation": generation,
                            "challenge": challenge,
                            "history": "A",
                            "future_index": 0,
                            "correct_hold8": correct,
                            "wrong_hold8": 1 - correct,
                            "returned": correct,
                            "acquired": True,
                        }
                    )
    return rows


def test_frontier_selection_uses_gentlest_environment_then_smallest_capacity(
    tmp_path,
) -> None:
    frontier = renewal_campaign_spec(_prior_selection(), smoke=True).frontier
    path = tmp_path / "frontier.jsonl.gz"
    write_jsonl_gz(path, _frontier_rows(frontier))
    analysis = analyze_renewal_frontier_path(path, frontier)
    assert analysis["verdict"]["renewal_frontier_found"]
    assert analysis["selection"]["selected_environment"] == "mild-dilution"
    assert analysis["selection"]["selected_capacity"] == 5
    assert analysis["selection"]["next_harsher_environment"] == "moderate-dropout"


def test_cost_doubles_only_in_high_cost_treatment_and_hard_k5_is_labeled() -> None:
    spec = renewal_campaign_spec(_prior_selection()).evolution_template
    standard = renewal_resource_cost(spec.initial_carrier, spec, "renewal_standard_cost")
    high = renewal_resource_cost(spec.initial_carrier, spec, "renewal_high_cost")
    assert standard <= 0.10
    assert high == 2.0 * standard
    assert spec.hard_capacity == 5


def test_projection_above_soft_boundary_is_rejected() -> None:
    spec = renewal_campaign_spec(_prior_selection())
    value = spec.to_dict()
    value["projected_wall_seconds"] = value["soft_wall_seconds"] + 1
    try:
        RenewalCampaignSpec.from_dict(value)
    except ValueError as error:
        assert "projection" in str(error)
    else:  # pragma: no cover
        raise AssertionError("over-budget renewal projection was accepted")


def test_detached_supervisor_has_stale_detection_and_persistent_six_hour_ledger() -> None:
    script = Path("scripts/run-wagner-ph-renewal-detached.sh").read_text(
        encoding="utf-8"
    )
    assert "maximum_wall_seconds=21600" in script
    assert "GRE_WAGNER_PH_RENEWAL_PRIOR_CONSUMED_SECONDS" in script
    assert "heartbeat_age <= 90" in script
    assert "run-wagner-ph-renewal-detached.sh --child" in script
    assert "kill -TERM -- \"-$science_pgid\"" in script
    extension = Path(
        "scripts/resume-wagner-ph-renewal-extension-detached.sh"
    ).read_text(encoding="utf-8")
    assert "maximum_extension_seconds=7200" in extension
    assert "soft_extension_seconds=6600" in extension
    assert "original six-hour supervisor is not recorded as exhausted" in extension


def test_completion_extension_is_separate_digest_bound_and_idempotent(tmp_path) -> None:
    spec = renewal_campaign_spec(_prior_selection())
    registration = {
        "format": "gre-wagner-ph-renewal-campaign-v1",
        "protocol": spec.to_dict(),
    }
    write_json(tmp_path / "registration.json", registration)
    amendment = prepare_completion_extension(
        tmp_path,
        spec,
        original_consumed_seconds=21_540,
    )
    assert amendment["original_attempt_status"] == "time-budget-exhausted"
    assert amendment["original_registration_digest"] == canonical_digest(registration)
    assert amendment["total_cumulative_authorized_seconds"] == 28_740
    assert amendment["scientific_outcomes_examined_before_extension"] is False
    assert prepare_completion_extension(
        tmp_path,
        spec,
        original_consumed_seconds=21_540,
    ) == amendment


def test_json_roundtrip_registration_uses_canonical_not_container_type_equality(
    tmp_path,
) -> None:
    spec = renewal_campaign_spec(_prior_selection())
    path = tmp_path / "registration.json"
    write_json(path, {"protocol": spec.to_dict()})
    archived = read_json(path)
    rebuilt = {"protocol": spec.to_dict()}
    assert archived != rebuilt  # JSON arrays return as lists; frozen contracts use tuples.
    assert canonical_digest(archived) == canonical_digest(rebuilt)


def test_evolution_and_mutation_audit_smoke_seal_resume_and_replay(tmp_path) -> None:
    campaign = renewal_campaign_spec(_prior_selection(), smoke=True)
    selection = {
        "selected_environment": "mixed-moderate",
        "next_harsher_environment": "heavy",
        "selected_genome": campaign.frontier.study.genome("renewal-k5").to_dict(),
    }
    evolution_spec = selected_evolution_spec(campaign, selection)
    evolution = run_renewal_evolution(
        evolution_spec, tmp_path / "evolution", workers=1
    )
    assert verify_renewal_evolution(evolution)["populations"] == 6
    assert run_renewal_evolution(evolution_spec, evolution, workers=1) == evolution
    population = read_json(
        evolution / "populations" / "renewal_k5_feasibility.population-000.json"
    )
    assert population["selection_uses_target_label_inside_carrier"] is False
    assert population["hard_k5_constraint"] is True
    assert all(item["carrier"]["k"] <= 5 for item in population["final_population"])
    task_digests = {
        read_json(evolution / "populations" / f"{treatment}.population-000.json")[
            "task"
        ]["task_id"]
        for treatment in evolution_spec.treatments
    }
    assert task_digests == {"population-000"}
    replay = replay_renewal_population(
        evolution, "renewal_standard_cost.population-000"
    )
    assert replay["matches"]

    audit = run_renewal_audit(
        evolution,
        campaign.mutation_audit,
        tmp_path / "audit",
        workers=1,
    )
    verified = verify_renewal_audit(audit)
    assert verified["populations"] == 6
    assert verified["mutation_rows"] == 72
    assert run_renewal_audit(
        evolution, campaign.mutation_audit, audit, workers=1
    ) == audit
    analysis = read_json(audit / "analysis.json")
    assert analysis["population_is_inferential_unit"] is True
    assert analysis["raw_pearson_is_primary"] is False
    assert analysis["verdict"]["hard_k5_feasibility_is_engineering_only"] is True


def test_worker_count_does_not_change_smoke_evolution_results(tmp_path) -> None:
    campaign = renewal_campaign_spec(_prior_selection(), smoke=True)
    selection = {
        "selected_environment": "mixed-moderate",
        "next_harsher_environment": "heavy",
        "selected_genome": campaign.frontier.study.genome("renewal-k5").to_dict(),
    }
    spec = selected_evolution_spec(campaign, selection)
    serial = run_renewal_evolution(spec, tmp_path / "serial", workers=1)
    parallel = run_renewal_evolution(spec, tmp_path / "parallel", workers=2)
    for treatment in spec.treatments:
        name = f"{treatment}.population-000.json"
        left = read_json(serial / "populations" / name)
        right = read_json(parallel / "populations" / name)
        assert left["result_digest"] == right["result_digest"]
