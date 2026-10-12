from laws_confirmation.a1 import (
    PARTICLE_RULES,
    RAW_CHAMPIONS,
    RAW_RULES,
    WIDTH_NOISES,
    adjudicate,
    campaign_tasks,
    condition_summary,
    design_contract,
)
from laws_confirmation.eca_math import CLASS_1, CLASS_3_CORE, wolfram_class
from laws_confirmation.eca_sim import ConditionResult, LaunchResult


def test_stage_d_design_dimensions_and_namespace_are_frozen():
    design = design_contract()
    assert len(RAW_RULES) == 88
    assert len(PARTICLE_RULES) == 28
    assert len(campaign_tasks()) == 464
    assert design["raw_cells"] == 880
    assert design["particle_cells"] == 280
    assert design["total_cells"] == 1160
    assert design["total_futures"] == 2_375_680
    assert "benchmark" not in design["namespace"]
    assert "scientific" in design["namespace"]


def test_condition_summary_preserves_launch_clusters_and_splits():
    launches = tuple(
        LaunchResult(
            launch_index=index,
            strict_count=1 if index in (0, 16) else 0,
            break_by_8_count=2,
            survival_sum=64 * 20,
            first_generation_times=(4,) * 64,
            form_support=3 if index % 2 else 5,
            form_n_futures=4,
            total_sweeps=100,
            death_counts={"timeout": 1},
        )
        for index in range(32)
    )
    result = ConditionResult(
        rule=110,
        observer="raw4",
        width=64,
        flip_noise=0.01,
        copy_error=0.015,
        n_futures=2048,
        strict_count=2,
        break_by_8_count=64,
        survival_sum=64 * 20 * 32,
        total_sweeps=3200,
        launches=launches,
    )
    summary = condition_summary(result, 1.25)
    assert summary["partitions"]["combined"]["n_futures"] == 2048
    assert summary["partitions"]["primary"]["strict"]["count"] == 1
    assert summary["partitions"]["holdout"]["strict"]["count"] == 1
    assert summary["partitions"]["combined"]["form_library"] == [3, 5]
    assert len(summary["per_launch"]) == 32


def _synthetic_condition(observer: str, rule: int) -> dict:
    raw_capable = observer == "raw4" and rule == 35
    particle_capable = observer == "particle4" and (
        rule in {18, 110, 122} or rule in RAW_CHAMPIONS
    )
    rate = 0.02 if raw_capable or particle_capable else 0.0
    count = int(rate * 2048)
    split_count = int(rate * 1024)
    library_size = 0 if rule == 110 else 1

    def partition(n_futures: int, strict_count: int) -> dict:
        return {
            "n_futures": n_futures,
            "strict": {"count": strict_count, "rate": rate},
            "form_library_size": library_size,
        }

    return {
        "flip_noise": None,
        "partitions": {
            "combined": partition(2048, count),
            "primary": partition(1024, split_count),
            "holdout": partition(1024, split_count),
        },
        "per_launch": [
            {"launch_index": index, "strict_rate": rate} for index in range(32)
        ],
    }


def test_full_synthetic_adjudication_wires_every_cell_and_split():
    panels = []
    for observer, rules in (("raw4", RAW_RULES), ("particle4", PARTICLE_RULES)):
        for rule in rules:
            for width, noises in WIDTH_NOISES.items():
                conditions = []
                for eta in noises:
                    condition = _synthetic_condition(observer, rule)
                    condition["flip_noise"] = eta
                    conditions.append(condition)
                panels.append(
                    {
                        "observer": observer,
                        "rule": rule,
                        "width": width,
                        "wolfram_class": wolfram_class(rule),
                        "conditions": conditions,
                    }
                )
    result = adjudicate(panels)
    gates = result["gates"]
    assert gates["raw_registered_regime_replication"] is True
    assert gates["raw_holdout_regime_extension"] is True
    assert gates["raw_width_regime_replication"] is True
    assert gates["raw_class1_exclusion"] is True
    assert gates["raw_core3_exclusion"] is True
    assert gates["particle_rule122_counterexample"] is True
    assert gates["particle_rule110_redemption"] is True
    assert gates["particle_champions_stable"] is True
    assert gates["raw_rule110_exact_zero_anchor"] is True
    assert gates["raw_rule110_below_band_panel"] is True
    assert gates["raw_rule110_library_top_decile"] is False
    assert not result["raw_class1_capable_entries"]["combined"]
    assert not result["raw_core3_capable_entries"]["combined"]
    assert not result["particle_class1_capable_entries"]["combined"]
