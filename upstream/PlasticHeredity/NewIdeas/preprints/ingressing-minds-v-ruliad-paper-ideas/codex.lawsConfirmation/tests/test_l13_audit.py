from pathlib import Path

import pytest

from laws_confirmation.l13_audit import (
    EXPECTED_REGISTER_IDS,
    REGISTER_FILES,
    clauses_csv,
    parse_register,
    records_csv,
    run_l13_audit,
)


PLASTIC_ROOT = Path(__file__).resolve().parents[5]
IDEAS_ROOT = (
    PLASTIC_ROOT / "NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas"
)


def test_l13_register_parser_expands_grouped_batteries_and_headlines():
    expected_outcomes = {
        7: {"fulfilled": 8, "reversed": 2, "failed": 7},
        8: {"fulfilled": 4, "reversed": 1, "failed": 10},
        9: {"fulfilled": 8, "reversed": 0, "failed": 9},
        10: {"fulfilled": 13, "reversed": 1, "failed": 9},
    }
    # Wave 9/10 totals above include the failed dependent headline.
    for wave, filename in REGISTER_FILES.items():
        rows, metadata = parse_register(IDEAS_ROOT / filename, wave)
        assert {row["id"] for row in rows} == set(EXPECTED_REGISTER_IDS[wave])
        assert metadata["asserted_written_date"] == "2026-08-20"
        counts = {
            outcome: sum(row["outcome"] == outcome for row in rows)
            for outcome in ("fulfilled", "reversed", "failed")
        }
        assert counts == expected_outcomes[wave]


@pytest.fixture(scope="module")
def l13_result():
    return run_l13_audit(PLASTIC_ROOT)


def test_l13_complete_census_and_result_hidden_classification(l13_result):
    audit, _paths, records, clauses, _hashes = l13_result
    assert audit["census"]["records_total_including_composites"] == 77
    assert audit["census"]["component_predictions"] == 75
    assert audit["census"]["composite_headlines"] == 2
    assert audit["census"]["gate_clauses"] == 129
    assert len(records) == 77
    assert len(clauses) == 129
    assert audit["census"]["classification_counts"] == {
        "composite_headline": 2,
        "direct_replication_or_integrity": 10,
        "new_task_domain": 24,
        "sealed_retest": 15,
        "within_domain_extension": 26,
    }
    assert audit["census"]["numerical_credences_present"] == 0
    assert audit["summaries"]["dependency"]["voltage_sheet_family_rows"] == 66


def test_l13_denominator_sensitivities_retain_majority_miss_pattern(l13_result):
    audit = l13_result[0]
    summaries = audit["summaries"]
    battery = summaries["source_coarse_split"]["named_battery_entries"]
    nonbattery = summaries["source_coarse_split"]["wave7_10_nonbattery_components"]
    new_domain = summaries["by_result_hidden_class"]["new_task_domain"]
    extensions = summaries["new_plus_within_domain_extrapolation"]

    assert (battery["fulfilled"], battery["total"]) == (15, 15)
    assert (nonbattery["literal_misses"], nonbattery["total"]) == (37, 60)
    assert nonbattery["literal_miss_fraction"] == pytest.approx(37 / 60)
    assert (new_domain["literal_misses"], new_domain["total"]) == (19, 24)
    assert (extensions["literal_misses"], extensions["total"]) == (37, 50)
    assert nonbattery["mostly_missed"] is True
    assert new_domain["mostly_missed"] is True
    assert extensions["mostly_missed"] is True


def test_l13_scorecard_tallies_are_not_silently_repaired(l13_result):
    tally = l13_result[0]["author_tally_audit"]
    assert tally["Wave7"]["author_stated"]["total"] == 15
    assert tally["Wave7"]["literal_expanded_rows"]["total"] == 17
    assert tally["Wave8"]["matches"] is True
    assert tally["Wave9"]["difference_literal_minus_stated"]["fulfilled"] == 1
    assert tally["Wave9"]["difference_literal_minus_stated"]["failed"] == -1
    assert tally["Wave10"]["difference_literal_minus_stated"]["fulfilled"] == 1
    assert tally["Wave10"]["difference_literal_minus_stated"]["failed"] == -1


def test_l13_all_battery_booleans_recalculate_but_original_gates_do_not_all(l13_result):
    batteries = l13_result[0]["sealed_batteries"]
    assert batteries["all_fifteen_calculated_pass"] is True
    assert batteries["all_component_and_rollup_booleans_match"] is True
    for name in ("E18", "E34", "E47"):
        assert batteries[name]["all_calculated_pass"] is True
        assert batteries[name]["components_match"] is True
        assert batteries[name]["rollup_matches"] is True
        assert batteries[name]["rollup_count_matches"] is True
    sensitivity = batteries["E47"]["original_gate_sensitivity"]
    assert sensitivity["P33.1_ratio"] == pytest.approx(1.3542270923000164)
    assert sensitivity["P33.1_ratio_would_pass_1_5"] is False
    assert sensitivity["P39.1_cue_normalized_ratio_available"] is False


def test_l13_git_history_distinguishes_asserted_from_repository_sealing(l13_result):
    provenance = l13_result[0]["provenance"]
    assert provenance["battery_pre_result_snapshots_verified"] == 2
    assert provenance["batteries"]["E18"]["repository_verifiable_pre_result_snapshot"] is True
    assert provenance["batteries"]["E34"]["repository_verifiable_pre_result_snapshot"] is True
    assert provenance["batteries"]["E47"]["repository_verifiable_pre_result_snapshot"] is False
    assert provenance["all_four_registers_have_clean_pre_result_commits"] is False
    assert provenance["asserted_date_mismatches"] == ["Wave7", "E34"]
    assert all(
        row["prediction_and_at_least_one_result_first_appear_same_commit"]
        for row in provenance["registers"].values()
    )


def test_l13_atomic_gate_census_exposes_vacuity_and_gate_substitution(l13_result):
    audit, _paths, records, clauses, _hashes = l13_result
    by_id = {row["id"]: row for row in records}
    assert by_id["P37.1"]["outcome"] == "fulfilled"
    assert by_id["P37.1"]["registered_gate_fully_substantively_supported"] is False
    assert [
        clause["reported_status"] for clause in by_id["P37.1"]["gate_clauses"]
    ] == ["fail", "pass", "pass"]
    assert by_id["P39.1"]["outcome"] == "fulfilled"
    assert {
        clause["reported_status"] for clause in by_id["P39.1"]["gate_clauses"]
    } == {"not_scored"}
    assert by_id["P36.4"]["structurally_vacuous"] is True
    assert len(audit["gate_changes"]) == 11
    assert audit["misderivations"]["miss_count"] == 37
    assert audit["misderivations"]["prospective_diagnosis_count"] == 0
    assert audit["misderivations"]["every_miss_specific_non_posthoc"] is False
    assert len({row["clause_id"] for row in clauses}) == len(clauses)


def test_l13_machine_readable_csvs_have_one_header_and_complete_rows(l13_result):
    _audit, _paths, records, clauses, _hashes = l13_result
    assert len(records_csv(records).splitlines()) == len(records) + 1
    assert len(clauses_csv(clauses).splitlines()) == len(clauses) + 1
