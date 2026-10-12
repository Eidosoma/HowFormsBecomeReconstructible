"""Stage-A/B retained-artifact audit for L01 and L02."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from .eca_math import (
    CLASS_1,
    CLASS_3_CORE,
    DISPUTED,
    atlas_null_variants,
    canonical_rules,
    draw_pairs,
    eca_edges,
    exhaustive_metric_association,
    life_edges,
    seed_rng,
    source_metric_association,
    unimodal,
    wolfram_class,
)
from .stats import average_ranks, close, mean, median, minimum_ranks, spearman


IDEAS_RELATIVE = Path("NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas")


class InputTracker:
    def __init__(self) -> None:
        self.paths: set[Path] = set()

    def add(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        self.paths.add(resolved)
        return resolved

    def json(self, path: Path) -> Any:
        with self.add(path).open(encoding="utf-8") as handle:
            return json.load(handle)

    def csv(self, path: Path) -> list[dict[str, str]]:
        with self.add(path).open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


def _load_shards(
    tracker: InputTracker,
    directory: Path,
    pattern: str,
    expected_shards: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(directory.glob(pattern))
    if len(paths) != expected_shards:
        raise ValueError(
            f"expected {expected_shards} shards matching {directory / pattern}, found {len(paths)}"
        )
    payloads = [tracker.json(path) for path in paths]
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"shard config digests differ in {directory}: {sorted(digests)}")
    shard_ids = sorted(int(payload["shard"]) for payload in payloads)
    if shard_ids != list(range(expected_shards)):
        raise ValueError(f"non-complete shard IDs in {directory}: {shard_ids}")
    entries = [entry for payload in payloads for entry in payload["entries"]]
    return entries, {
        "n_shards": len(paths),
        "config_digest": next(iter(digests)),
        "shard_ids": shard_ids,
        "n_entries": len(entries),
    }


def _top_decile_share(census: Mapping[int, int]) -> float:
    ordered = sorted(census.values(), reverse=True)
    take = max(1, len(ordered) // 10)
    return sum(ordered[:take]) / max(sum(ordered), 1)


def _field_matches(
    calculated: Mapping[str, Any], reported: Mapping[str, Any], fields: Iterable[str]
) -> dict[str, bool]:
    matches: dict[str, bool] = {}
    for field in fields:
        left, right = calculated.get(field), reported.get(field)
        if isinstance(left, bool) or isinstance(right, bool):
            matches[field] = bool(left) == bool(right)
        elif isinstance(left, (int, float)) or isinstance(right, (int, float)):
            matches[field] = close(left, right)
        else:
            matches[field] = left == right
    return matches


def _libraries(entries: Iterable[dict[str, Any]]) -> tuple[dict[int, set[int]], Counter[int]]:
    libraries: dict[int, set[int]] = {}
    census: Counter[int] = Counter()
    for entry in entries:
        rule = int(entry["rule"])
        supports = [int(mask) for mask in entry["supports"] if int(mask) != 0]
        libraries[rule] = set(supports)
        census.update(supports)
    return libraries, census


def _csv_numeric_match_counts(
    rows: list[dict[str, str]],
    entries: Mapping[int, dict[str, Any]],
    libraries: Mapping[int, set[int]],
    fields: Iterable[str],
) -> dict[str, Any]:
    by_rule = {int(row["rule"]): row for row in rows}
    counts = {}
    mismatches = {}
    for field in fields:
        bad = []
        for rule, entry in entries.items():
            expected = len(libraries[rule]) if field == "library_size" else entry[field]
            observed = float(by_rule[rule][field])
            if not close(float(expected), observed):
                bad.append(rule)
        counts[field] = len(entries) - len(bad)
        mismatches[field] = bad
    return {"exact_match_counts": counts, "mismatch_rules": mismatches}


def audit_e19(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "eca_atlas")
    result_root = root / "results/full"
    entries_list, integrity = _load_shards(
        tracker, result_root / "work", "atlas_shard_*_of_11.json", 11
    )
    entries = {int(entry["rule"]): entry for entry in entries_list}
    rules = canonical_rules()
    if len(entries) != len(entries_list):
        raise ValueError("E19 contains duplicate rules")
    if tuple(sorted(entries)) != rules:
        raise ValueError("E19 shard rules do not equal the independently generated 88 orbits")

    summary = tracker.json(result_root / "atlas_summary.json")
    csv_rows = tracker.csv(result_root / "eca_rules.csv")
    tracker.add(root / "EXPECTATIONS.md")
    for path in sorted((root / "src").rglob("*.py")):
        tracker.add(path)

    libraries, census = _libraries(entries_list)
    strict = {rule: float(entry["strict"]) for rule, entry in entries.items()}
    break8 = {rule: float(entry["break_by_8"]) for rule, entry in entries.items()}
    edges = eca_edges(rules)

    # Reproduce the source's one RNG stream: random null pairs first, then its
    # 1,024 metric-law pairs.
    rng = seed_rng("eca-atlas-random-v1", len(edges))
    random_pairs = draw_pairs(rules, rng, max(len(edges), 256))
    source_metric = source_metric_association(rules, libraries, rng=rng)
    nulls = atlas_null_variants(libraries, edges, rules, random_pairs, strict)

    core_min = min(break8[rule] for rule in CLASS_3_CORE)
    clean_values = [
        break8[rule]
        for rule in rules
        if rule not in CLASS_3_CORE
        and rule not in DISPUTED
        and wolfram_class(rule) < 3
    ]
    clean_median = median(clean_values)
    ranks = average_ranks([strict[rule] for rule in rules], descending=True)
    rule110_average_rank = ranks[rules.index(110)]
    library_sizes = [len(libraries[rule]) for rule in rules]
    library_minimum_ranks = minimum_ranks(library_sizes, descending=True)
    library_average_ranks = average_ranks(library_sizes, descending=True)
    rule110_index = rules.index(110)
    top_decile_bar = math.ceil(len(rules) / 10)
    calculated = {
        "n_forms": len(census),
        "smoothness_ratio": nulls["source_convention"]["ratio"],
        "gate_smoothness": nulls["source_convention"]["ratio"] >= 2.0,
        "heavy_tail_share": _top_decile_share(census),
        "gate_heavy_tail": _top_decile_share(census) >= 0.35,
        "metric_rho_descriptors": source_metric["rho_descriptors"],
        "metric_rho_hamming": source_metric["rho_hamming"],
        "gate_metric": source_metric["rho_descriptors"] > source_metric["rho_hamming"],
        "core3_min_break8": core_min,
        "clean12_median_break8": clean_median,
        "gate_class3_separation": core_min > clean_median,
        "rule110_strict": strict[110],
        "rule110_average_tie_rank": rule110_average_rank,
        "rule110_source_integer_rank": int(rule110_average_rank),
        "gate_rule110_top_decile": int(rule110_average_rank) <= top_decile_bar,
        "rule110_library_size": library_sizes[rule110_index],
        "rule110_library_minimum_tie_rank": library_minimum_ranks[rule110_index],
        "rule110_library_average_tie_rank": library_average_ranks[rule110_index],
        "rule110_library_top_decile": library_minimum_ranks[rule110_index]
        <= top_decile_bar,
        "top_decile_rank_bar": top_decile_bar,
        "empty_library_rules": sum(not libraries[rule] for rule in rules),
    }
    reported = summary["gates"]
    match_fields = (
        "n_forms",
        "smoothness_ratio",
        "gate_smoothness",
        "heavy_tail_share",
        "gate_heavy_tail",
        "metric_rho_descriptors",
        "metric_rho_hamming",
        "gate_metric",
        "gate_class3_separation",
        "rule110_strict_rank",
        "gate_rule110_top_decile",
    )
    comparison_calculated = dict(calculated)
    comparison_calculated["rule110_strict_rank"] = calculated["rule110_source_integer_rank"]
    integrity.update(
        expected_entries=88,
        unique_entries=len(entries),
        complete_orbits=True,
        summary_digest_matches=summary.get("config_digest") == integrity["config_digest"],
        csv=_csv_numeric_match_counts(
            csv_rows,
            entries,
            libraries,
            ("strict", "break_by_8", "median_gen_sweeps", "mean_survival", "library_size"),
        ),
    )
    return {
        "integrity": integrity,
        "calculated": calculated,
        "reported_gates": reported,
        "reported_match": _field_matches(comparison_calculated, reported, match_fields),
        "null_sensitivity": nulls,
        "metric_sensitivity": {
            "source_sample": source_metric,
            "exhaustive_all_pairs": exhaustive_metric_association(
                rules, libraries, exclude_empty_empty=False
            ),
            "exhaustive_excluding_empty_empty": exhaustive_metric_association(
                rules, libraries, exclude_empty_empty=True
            ),
        },
    }


def _phase_rows(entries: Iterable[dict[str, Any]]) -> dict[tuple[float, int], dict[str, Any]]:
    rows = {}
    for entry in entries:
        key = (float(entry["eta"]), int(entry["rule"]))
        if key in rows:
            raise ValueError(f"duplicate phase cell: {key}")
        rows[key] = entry
    return rows


def audit_e22(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "eca_phase")
    result_root = root / "results/full"
    entries, integrity = _load_shards(
        tracker, result_root / "work", "grid_shard_*_of_16.json", 16
    )
    rows = _phase_rows(entries)
    rules = canonical_rules()
    etas = (0.0025, 0.005, 0.01, 0.02, 0.04)
    expected_keys = {(eta, rule) for eta in etas for rule in rules}
    if set(rows) != expected_keys:
        raise ValueError("E22 phase cells are incomplete or unexpected")

    summary = tracker.json(result_root / "phase_summary.json")
    width_axis = tracker.json(result_root / "width_axis.json")
    csv_rows = tracker.csv(result_root / "phase.csv")
    tracker.add(root / "EXPECTATIONS.md")
    for path in sorted((root / "src").rglob("*.py")):
        tracker.add(path)

    lo, hi = 0.005, 0.5
    per_eta = []
    ever_capable = set()
    for eta in etas:
        band = [rule for rule in rules if lo <= float(rows[(eta, rule)]["strict"]) <= hi]
        ever_capable.update(band)
        per_eta.append(
            {
                "eta": eta,
                "n_band": len(band),
                "band_class2_fraction": mean(wolfram_class(rule) == 2 for rule in band),
                "core3_in_band": sum(rule in CLASS_3_CORE for rule in band),
                "class1_in_band": sum(rule in CLASS_1 for rule in band),
                "band_rules": band,
            }
        )
    gate_regime = all(
        cell["n_band"] > 0
        and cell["band_class2_fraction"] > 0.5
        and cell["core3_in_band"] == 0
        for cell in per_eta
    )

    tolerance_results = {}
    for tolerance in (0.0, 0.002, 0.005, 0.01):
        flags = []
        for rule in sorted(ever_capable):
            values = [float(rows[(eta, rule)]["strict"]) for eta in etas]
            flags.append(unimodal(values, tolerance))
        tolerance_results[str(tolerance)] = {
            "n_unimodal": sum(flags),
            "n_ever_capable": len(flags),
            "fraction": mean(flags),
            "gate_two_thirds": mean(flags) >= 2 / 3,
        }

    peak_counts = {"lower_boundary": 0, "interior": 0, "upper_boundary": 0}
    peak_eta_by_rule = {}
    for rule in sorted(ever_capable):
        values = [float(rows[(eta, rule)]["strict"]) for eta in etas]
        peak_index = max(range(len(values)), key=values.__getitem__)
        peak_eta_by_rule[str(rule)] = etas[peak_index]
        if peak_index == 0:
            peak_counts["lower_boundary"] += 1
        elif peak_index == len(etas) - 1:
            peak_counts["upper_boundary"] += 1
        else:
            peak_counts["interior"] += 1

    calculated = {
        "gate_regime_robustness": gate_regime,
        "per_eta": per_eta,
        "gate_ridge_law_at_source_tolerance": tolerance_results["0.01"]["gate_two_thirds"],
        "unimodal_fraction_at_source_tolerance": tolerance_results["0.01"]["fraction"],
        "n_ever_capable": len(ever_capable),
        "peak_eta_by_rule": peak_eta_by_rule,
        "peak_location_counts": peak_counts,
        "gate_class1_awakening": any(cell["class1_in_band"] for cell in per_eta),
        "awakened_class1": sorted(
            {rule for cell in per_eta for rule in cell["band_rules"] if rule in CLASS_1}
        ),
        "rule110_by_eta": [
            {
                "eta": eta,
                "strict": float(rows[(eta, 110)]["strict"]),
                "break_by_8": float(rows[(eta, 110)]["break_by_8"]),
            }
            for eta in etas
        ],
        "designated_core3_strict_max": max(
            float(rows[(eta, rule)]["strict"])
            for eta in etas
            for rule in CLASS_3_CORE
        ),
    }
    reported = summary["gates"]
    reported_projection = {
        "gate_regime_robustness": reported["gate_regime_robustness"],
        "gate_ridge_law_at_source_tolerance": reported["gate_ridge_law"],
        "unimodal_fraction_at_source_tolerance": reported["unimodal_fraction"],
        "n_ever_capable": reported["n_ever_capable"],
        "gate_class1_awakening": reported["gate_class1_awakening"],
        "awakened_class1": reported["awakened_class1"],
        "rule110_by_eta": reported["rule110_by_eta"],
    }
    integrity.update(
        expected_entries=440,
        unique_entries=len(rows),
        complete_grid=True,
        summary_digest_matches=summary.get("config_digest") == integrity["config_digest"],
        csv_rows=len(csv_rows),
    )
    width_rows = width_axis.get("rows", [])
    width_by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in width_rows:
        width_by_rule[str(int(row["rule"]))].append(
            {
                "width": int(row["width"]),
                "strict": float(row["strict"]),
                "break_by_8": float(row["break_by_8"]),
                "median_gen_sweeps": float(row["median_gen_sweeps"]),
            }
        )
    width_sensitivity = {}
    for rule, panel in sorted(width_by_rule.items(), key=lambda item: int(item[0])):
        panel.sort(key=lambda row: row["width"])
        strict_values = [row["strict"] for row in panel]
        width_sensitivity[rule] = {
            "widths": [row["width"] for row in panel],
            "strict_min": min(strict_values),
            "strict_max": max(strict_values),
            "strict_range": max(strict_values) - min(strict_values),
            "strict_zero_at_every_width": all(value == 0 for value in strict_values),
            "strict_monotone_nonincreasing": all(
                right <= left for left, right in zip(strict_values, strict_values[1:])
            ),
            "strict_monotone_nondecreasing": all(
                right >= left for left, right in zip(strict_values, strict_values[1:])
            ),
        }
    return {
        "integrity": integrity,
        "calculated": calculated,
        "reported_projection": reported_projection,
        "reported_match": _field_matches(
            calculated,
            reported_projection,
            reported_projection.keys(),
        ),
        "unimodality_tolerance_sensitivity": tolerance_results,
        "width_axis": dict(width_by_rule),
        "width_sensitivity": width_sensitivity,
    }


def audit_e24(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "life_family")
    result_root = root / "results/full"
    entries_list, integrity = _load_shards(
        tracker, result_root / "work", "family_shard_*_of_32.json", 32
    )
    entries = {int(entry["rule"]): entry for entry in entries_list}
    if len(entries) != 1024 or len(entries) != len(entries_list):
        raise ValueError("E24 does not contain exactly 1,024 unique rules")
    rules = tuple(sorted(entries))
    summary = tracker.json(result_root / "family_summary.json")
    csv_rows = tracker.csv(result_root / "family.csv")
    tracker.add(root / "EXPECTATIONS.md")
    for path in sorted((root / "src").rglob("*.py")):
        tracker.add(path)

    libraries, census = _libraries(entries_list)
    strict = {rule: float(entry["strict"]) for rule, entry in entries.items()}
    edges = life_edges(rules)
    rng = seed_rng("life-family-null-v1", len(edges))
    random_pairs = draw_pairs(rules, rng, max(len(edges), 512))
    nulls = atlas_null_variants(libraries, edges, rules, random_pairs, strict)

    notations = {rule: str(entry["notation"]) for rule, entry in entries.items()}
    life_rule = next(rule for rule, notation in notations.items() if notation == "B3/S23")
    library_sizes = [len(libraries[rule]) for rule in rules]
    library_ranks = minimum_ranks(library_sizes, descending=True)
    life_rank = library_ranks[rules.index(life_rule)]
    in_band = {rule: 0.005 <= strict[rule] <= 0.5 for rule in rules}
    clocks = np.asarray([float(entries[rule]["median_gen_sweeps"]) for rule in rules])
    q25, q75 = np.quantile(clocks, (0.25, 0.75))
    capable_clock = median(
        float(entries[rule]["median_gen_sweeps"]) for rule in rules if in_band[rule]
    )
    calculated = {
        "n_edges_in_sample": len(edges),
        "smoothness_ratio": nulls["source_convention"]["ratio"],
        "gate_smoothness": nulls["source_convention"]["ratio"] >= 2.0,
        "heavy_tail_share": _top_decile_share(census),
        "gate_heavy_tail": _top_decile_share(census) >= 0.35,
        "n_forms": len(census),
        "life_library_rank": life_rank,
        "life_library_top_decile": life_rank <= math.ceil(len(rules) / 10),
        "life_strict": strict[life_rule],
        "life_in_band": in_band[life_rule],
        "gate_life_rare_book": life_rank <= math.ceil(len(rules) / 10) and in_band[life_rule],
        "capable_median_clock": capable_clock,
        "family_clock_iqr": [float(q25), float(q75)],
        "gate_boundary_of_order": bool(q25 < capable_clock < q75),
        "empty_library_rules": sum(not libraries[rule] for rule in rules),
        "clock_floor_four_fraction": mean(clocks == 4.0),
    }
    reported = summary["gates"]
    fields = (
        "n_edges_in_sample",
        "smoothness_ratio",
        "gate_smoothness",
        "heavy_tail_share",
        "gate_heavy_tail",
        "n_forms",
        "life_library_rank",
        "life_strict",
        "life_in_band",
        "gate_life_rare_book",
        "capable_median_clock",
        "family_clock_iqr",
        "gate_boundary_of_order",
    )
    integrity.update(
        expected_entries=1024,
        unique_entries=len(entries),
        complete_sample=True,
        summary_digest_matches=summary.get("config_digest") == integrity["config_digest"],
        csv=_csv_numeric_match_counts(
            csv_rows,
            entries,
            libraries,
            ("strict", "break_by_8", "median_gen_sweeps", "library_size"),
        ),
    )
    return {
        "integrity": integrity,
        "calculated": calculated,
        "reported_gates": reported,
        "reported_match": _field_matches(calculated, reported, fields),
        "null_sensitivity": nulls,
    }


def audit_e34(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "sealed_battery_2")
    result_root = root / "results/full"
    tracker.add(root / "EXPECTATIONS.md")
    for path in sorted((root / "src").rglob("*.py")):
        tracker.add(path)
    battery = tracker.json(result_root / "battery_verdict.json")
    component_names = ("ladder", "redemption", "regime", "worm", "placements")
    components = {
        name: tracker.json(result_root / f"component_{name}.json")
        for name in component_names
    }
    digests = {battery.get("config_digest")} | {
        component.get("config_digest") for component in components.values()
    }
    recalculated = {
        "ladder": components["ladder"]["core3_min_break8"]
        > components["ladder"]["clean12_median_break8"],
        "redemption": all(bool(value) for value in components["redemption"]["in_band"].values()),
        "regime": components["regime"]["n_band"] > 0
        and components["regime"]["band_class2_fraction"] > 0.5
        and components["regime"]["core3_in_band"] == 0,
        "worm": components["worm"]["conversion"] >= 0.10
        and components["worm"]["conversion"]
        >= 3 * max(components["worm"]["reverse"], 1e-9),
        "placements": bool(components["placements"]["eca"]["gate"])
        and bool(components["placements"]["tissue"]["gate"]),
    }
    component_gate_match = {
        name: bool(recalculated[name]) == bool(components[name]["gate"])
        for name in component_names
    }
    battery_match = {
        name: bool(recalculated[name]) == bool(battery["verdict"][name])
        for name in component_names
    }
    return {
        "integrity": {
            "one_config_digest": len(digests) == 1,
            "config_digest": next(iter(digests)) if len(digests) == 1 else sorted(digests),
            "n_components": len(components),
        },
        "reported": components,
        "recalculated_gate_from_aggregates": recalculated,
        "component_gate_match": component_gate_match,
        "battery_verdict_match": battery_match,
        "lower_level_sufficiency": {
            "ladder": "aggregate core minimum and clean median only; no per-rule values retained here",
            "regime": "aggregate band count/class fraction/core count only; no per-rule values retained here",
            "redemption": "four rule-level strict rates and band booleans retained",
            "worm": "aggregate conversion and reverse means only; no tissue-level outcomes retained here",
            "placements": "aggregate distances/null quantiles only; no entity-level cloud retained here",
        },
    }


def _csv_by_key(
    rows: Iterable[dict[str, str]], keys: tuple[str, ...]
) -> dict[tuple[Any, ...], dict[str, str]]:
    result = {}
    for row in rows:
        key_parts: list[Any] = []
        for key in keys:
            value: Any = row[key]
            if key == "rule":
                value = int(value)
            elif key == "eta":
                value = float(value)
            key_parts.append(value)
        result[tuple(key_parts)] = row
    return result


def _compare_csv_fields(
    left_rows: list[dict[str, str]],
    right_rows: list[dict[str, str]],
    keys: tuple[str, ...],
    fields: tuple[str, ...],
) -> dict[str, Any]:
    left = _csv_by_key(left_rows, keys)
    right = _csv_by_key(right_rows, keys)
    common = sorted(set(left) & set(right))
    result: dict[str, Any] = {
        "n_left": len(left),
        "n_right": len(right),
        "n_common": len(common),
        "left_only": [list(key) for key in sorted(set(left) - set(right))],
        "right_only": [list(key) for key in sorted(set(right) - set(left))],
        "fields": {},
    }
    for field in fields:
        left_values = [float(left[key][field]) for key in common]
        right_values = [float(right[key][field]) for key in common]
        differences = [abs(a - b) for a, b in zip(left_values, right_values)]
        result["fields"][field] = {
            "exact_matches": sum(a == b for a, b in zip(left_values, right_values)),
            "mean_absolute_error": mean(differences),
            "max_absolute_error": max(differences, default=math.nan),
            "spearman": spearman(left_values, right_values),
        }
    return result


def _compare_string_fields(
    left_rows: list[dict[str, str]],
    right_rows: list[dict[str, str]],
    keys: tuple[str, ...],
    left_field: str,
    right_field: str,
) -> dict[str, Any]:
    left = _csv_by_key(left_rows, keys)
    right = _csv_by_key(right_rows, keys)
    common = sorted(set(left) & set(right))
    left_available = bool(left_rows) and left_field in left_rows[0]
    right_available = bool(right_rows) and right_field in right_rows[0]
    if not (left_available and right_available):
        return {
            "available": False,
            "n_common": len(common),
            "left_field": left_field,
            "right_field": right_field,
            "reason": "one or both retained CSV schemas omit the requested field",
        }
    return {
        "available": True,
        "n_common": len(common),
        "left_field": left_field,
        "right_field": right_field,
        "exact_matches": sum(
            left[key][left_field] == right[key][right_field] for key in common
        ),
    }


def audit_cross_implementation(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    ideas = plastic_root / IDEAS_RELATIVE
    fable_atlas = tracker.csv(ideas / "eca_atlas/results/full/eca_rules.csv")
    fable_phase = tracker.csv(ideas / "eca_phase/results/full/phase.csv")
    fable_particle = tracker.json(ideas / "particle_observer/results/full/particle_gates.json")
    fable_named_life = tracker.json(ideas / "glider_test/results/full/observer.json")
    fable_life_family = tracker.csv(ideas / "life_family/results/full/family.csv")
    fable_life_summary = tracker.json(ideas / "life_family/results/full/family_summary.json")

    codex_root = ideas / "codex.reconstructionsAndStressTesting"
    result_root = codex_root / "results/golden-reconciliation"
    codex_atlas = tracker.csv(result_root / "atlas/eca_rules.csv")
    codex_phase = tracker.csv(result_root / "phase/phase.csv")
    codex_particle = tracker.json(result_root / "particle/particle_gates.json")
    codex_named_life = tracker.json(result_root / "life/observer.json")
    supplied_atlas_comparison = tracker.json(result_root / "atlas/reference_comparison.json")
    supplied_phase_comparison = tracker.json(result_root / "phase/reference_comparison.json")
    manifest = tracker.json(result_root / "MANIFEST.json")

    campaign_root = codex_root / "results/ca-campaign-round-1"
    campaign = tracker.json(campaign_root / "RESULTS.json")
    campaign_manifest = tracker.json(campaign_root / "MANIFEST.json")
    tracker.add(campaign_root / "REPORT.md")
    codex_life_family = tracker.csv(
        campaign_root / "life-family/frozen-b48/family.csv"
    )
    codex_life_summary = tracker.json(
        campaign_root / "life-family/frozen-b48/family_summary.json"
    )
    for relative in (
        "plastic_ca/eca.py",
        "plastic_ca/config.py",
        "plastic_ca/life.py",
        "plastic_ca/life_family.py",
        "plastic_ca/ca_campaign.py",
        "plastic_ca/metrics.py",
        "plastic_ca/reconciliation.py",
        "plastic_ca/rng.py",
        "plastic_ca/data/e19_golden_traces.json",
    ):
        tracker.add(codex_root / relative)

    atlas = _compare_csv_fields(
        fable_atlas,
        codex_atlas,
        ("rule",),
        ("strict", "break_by_8", "median_gen_sweeps", "mean_survival", "library_size"),
    )
    atlas["library_strings"] = _compare_string_fields(
        fable_atlas, codex_atlas, ("rule",), "library", "library"
    )

    phase = _compare_csv_fields(
        fable_phase,
        codex_phase,
        ("eta", "rule"),
        ("strict", "break_by_8", "median_gen_sweeps"),
    )
    fable_class4 = {str(key): value for key, value in fable_particle["gates"]["class4_strict"].items()}
    codex_class4 = {str(key): value for key, value in codex_particle["gates"]["class4_strict"].items()}
    particle = {
        "fable_class4_strict": fable_class4,
        "codex_class4_strict": codex_class4,
        "absolute_differences": {
            rule: abs(float(fable_class4[rule]) - float(codex_class4[rule]))
            for rule in sorted(set(fable_class4) & set(codex_class4), key=int)
        },
        "fable_gates": {
            key: value for key, value in fable_particle["gates"].items() if key.startswith("gate_")
        },
        "codex_gates": {
            key: value for key, value in codex_particle["gates"].items() if key.startswith("gate_")
        },
    }

    named_life_gate_fields = (
        "gate_distinct_forms",
        "gate_fidelity_absolute",
        "gate_persistence",
    )
    named_life = {
        "fable_gates": {
            key: fable_named_life["gates"][key] for key in named_life_gate_fields
        },
        "codex_gates": {
            key: codex_named_life["gates"][key] for key in named_life_gate_fields
        },
        "gate_verdict_matches": _field_matches(
            codex_named_life["gates"],
            fable_named_life["gates"],
            named_life_gate_fields,
        ),
        "form_supports": {
            name: {
                "fable": int(fable_named_life["named"][name]["form_support"]),
                "codex": int(codex_named_life["named"][name]["form_support"]),
                "exact": int(fable_named_life["named"][name]["form_support"])
                == int(codex_named_life["named"][name]["form_support"]),
            }
            for name in ("glider", "blinker", "toad")
        },
    }

    life_family = _compare_csv_fields(
        fable_life_family,
        codex_life_family,
        ("rule",),
        ("strict", "break_by_8", "median_gen_sweeps", "library_size"),
    )
    life_family["library_strings"] = _compare_string_fields(
        fable_life_family,
        codex_life_family,
        ("rule",),
        "library",
        "support_masks",
    )
    life_gate_fields = (
        "gate_smoothness",
        "gate_heavy_tail",
        "gate_life_rare_book",
        "gate_boundary_of_order",
    )
    life_family["fable_gates"] = {
        key: fable_life_summary["gates"][key] for key in life_gate_fields
    }
    life_family["codex_gates"] = {
        key: codex_life_summary["gates"][key] for key in life_gate_fields
    }
    life_family["gate_verdict_matches"] = _field_matches(
        codex_life_summary["gates"], fable_life_summary["gates"], life_gate_fields
    )

    campaign_life = campaign["life_family"]
    condition_summary_matches = {}
    condition_gate_summary = {}
    retained_condition_names = sorted(campaign_life["conditions"])
    for condition in retained_condition_names:
        stored_summary = tracker.json(
            campaign_root / f"life-family/{condition}/family_summary.json"
        )
        campaign_gates = campaign_life["conditions"][condition]["gates"]
        stored_gates = stored_summary["gates"]
        condition_summary_matches[condition] = _field_matches(
            stored_gates, campaign_gates, campaign_gates.keys()
        )
        condition_gate_summary[condition] = {
            "n_rules": int(campaign_life["conditions"][condition]["n_rules"]),
            "gate_smoothness": bool(stored_gates["gate_smoothness"]),
            "gate_heavy_tail": bool(stored_gates["gate_heavy_tail"]),
            "gate_life_rare_book": bool(stored_gates["gate_life_rare_book"]),
            "gate_boundary_of_order": bool(stored_gates["gate_boundary_of_order"]),
            "life_strict": float(stored_gates["life_strict"]),
            "life_library_rank": int(stored_gates["life_library_rank"]),
        }
    robustness_fields = (
        "clock_rescued",
        "family_laws_robust",
        "launch_robustness",
        "life_remains_maintainer",
        "scale_stability",
    )
    life_family["campaign"] = {
        "profile": campaign.get("profile"),
        "cleanroom_record": campaign.get("cleanroom"),
        "reported_retained_comparison": campaign_life.get("retained_comparison"),
        "robustness_gates": {
            field: bool(campaign_life["campaign_gates"][field])
            for field in robustness_fields
        },
        "condition_gate_summary": condition_gate_summary,
        "condition_summary_matches_campaign": condition_summary_matches,
        "manifest": campaign_manifest,
    }
    return {
        "independent_recalculation": {
            "atlas": atlas,
            "phase": phase,
            "particle": particle,
            "named_life": named_life,
            "life_family": life_family,
        },
        "supplied_comparisons": {
            "atlas": supplied_atlas_comparison,
            "phase": supplied_phase_comparison,
        },
        "dependency_record": {
            "contract_digest": manifest.get("contract_digest"),
            "historical_workers": manifest.get("workers"),
            "cleanroom_exclusions": manifest.get("cleanroom_exclusions"),
            "evidence": manifest.get("evidence"),
            "reference_root": manifest.get("reference_root"),
            "independence_dimensions": {
                "scientific_implementation": (
                    "separate plastic_ca source tree; golden manifest records sibling "
                    "source, tests, and scripts as excluded"
                ),
                "stochastic_outcomes": (
                    "new futures were generated, but exact-atlas reconstruction uses the "
                    "same disclosed rng_tag and a reconciled RNG/execution contract"
                ),
                "launch_states": (
                    "the same 16 disclosed ECA launch rows are embedded in the reconciled contract"
                ),
                "observer_endpoint": (
                    "the thresholds, final4 endpoint, generation boundary, and form-pooling "
                    "contract were intentionally matched"
                ),
                "human_supplied_contract": (
                    "supplied JSON/Markdown outcomes and a code-free golden-trace fixture "
                    "were used during semantic reconciliation"
                ),
                "life_campaign_source_record": campaign.get("cleanroom"),
            },
            "semantic_reconciliation_note": (
                "The implementation excluded sibling source/tests/scripts but used supplied outputs "
                "and a vendored code-free golden-trace fixture to reconcile execution semantics. "
                "Implementation independence and contract/data independence must therefore be scored separately."
            ),
        },
    }


def run_retained_audit(plastic_root: Path) -> tuple[dict[str, Any], set[Path]]:
    plastic_root = plastic_root.resolve()
    tracker = InputTracker()
    tracker.add(plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md")
    tracker.add(plastic_root / IDEAS_RELATIVE / "LAWS.md")
    audit = {
        "schema_version": 2,
        "scope": "L01/L02 Stage A retained-artefact recalculation and Stage B dependency comparison",
        "plastic_heredity_root": str(plastic_root),
        "e19": audit_e19(plastic_root, tracker),
        "e22": audit_e22(plastic_root, tracker),
        "e24": audit_e24(plastic_root, tracker),
        "e34": audit_e34(plastic_root, tracker),
        "cross_implementation": audit_cross_implementation(plastic_root, tracker),
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, tracker.paths


def markdown_report(audit: Mapping[str, Any]) -> str:
    e19 = audit["e19"]
    e22 = audit["e22"]
    e24 = audit["e24"]
    e34 = audit["e34"]
    cross = audit["cross_implementation"]["independent_recalculation"]
    life_cross = cross["life_family"]

    def fmt(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    widest_rule, widest_panel = max(
        e22["width_sensitivity"].items(),
        key=lambda item: item[1]["strict_range"],
    )
    all_condition_summaries_match = all(
        all(fields.values())
        for fields in life_cross["campaign"]["condition_summary_matches_campaign"].values()
    )

    lines = [
        "# L01/L02 retained-artifact audit v1.1",
        "",
        "This report recalculates retained artefacts. It is not a fresh simulation replication.",
        "",
        "## Integrity",
        "",
        f"- Input files hashed: {audit['input_file_count']}",
        f"- E19: {e19['integrity']['unique_entries']}/88 unique canonical rules across {e19['integrity']['n_shards']} shards",
        f"- E22: {e22['integrity']['unique_entries']}/440 rule×noise cells across {e22['integrity']['n_shards']} shards",
        f"- E24: {e24['integrity']['unique_entries']}/1,024 sampled rules across {e24['integrity']['n_shards']} shards",
        f"- E34: one shared config digest: {e34['integrity']['one_config_digest']}",
        "",
        "## E19",
        "",
        f"- Class-3-core minimum break-by-8: {fmt(e19['calculated']['core3_min_break8'])}",
        f"- Clean class-1/2 median: {fmt(e19['calculated']['clean12_median_break8'])}",
        f"- Rule 110 strict rate: {fmt(e19['calculated']['rule110_strict'])}",
        f"- Rule 110 strict-capability average tie rank: {fmt(e19['calculated']['rule110_average_tie_rank'])}/88; registered top-decile gate: {e19['calculated']['gate_rule110_top_decile']}",
        f"- Rule 110 form library: {e19['calculated']['rule110_library_size']} forms; minimum tie rank {e19['calculated']['rule110_library_minimum_tie_rank']}/88; top decile: {e19['calculated']['rule110_library_top_decile']}",
        f"- Registered class-3-separation gate: {e19['calculated']['gate_class3_separation']}",
        f"- Registered heavy-tail gate: {e19['calculated']['gate_heavy_tail']}",
        f"- Registered descriptor-beats-Hamming gate: {e19['calculated']['gate_metric']} ({fmt(e19['calculated']['metric_rho_descriptors'])} vs {fmt(e19['calculated']['metric_rho_hamming'])})",
        f"- Source-convention smoothness: {fmt(e19['null_sensitivity']['source_convention']['ratio'])}",
        f"- Smoothness excluding empty-empty pairs: {fmt(e19['null_sensitivity']['exclude_empty_empty']['ratio'])}",
        f"- Smoothness among non-empty libraries: {fmt(e19['null_sensitivity']['both_nonempty']['ratio'])}",
        f"- Capability-matched non-empty smoothness: {fmt(e19['null_sensitivity']['both_nonempty_capability_matched']['ratio'])}",
        f"- All reported summary fields reproduced: {all(e19['reported_match'].values())}",
        "",
        "## E22",
        "",
        f"- Registered five-point regime gate: {e22['calculated']['gate_regime_robustness']}",
        f"- Registered class-1-awakening gate: {e22['calculated']['gate_class1_awakening']}",
        f"- Ever-capable rules: {e22['calculated']['n_ever_capable']}",
        f"- Peak locations: {e22['calculated']['peak_location_counts']}",
        f"- Unimodal fraction at tolerance 0.01: {fmt(e22['calculated']['unimodal_fraction_at_source_tolerance'])}",
        f"- Unimodal fraction at tolerance 0: {fmt(e22['unimodality_tolerance_sensitivity']['0.0']['fraction'])}",
        f"- Largest retained width-panel strict-rate range: rule {widest_rule}, {fmt(widest_panel['strict_range'])}",
        f"- All reported projection fields reproduced: {all(e22['reported_match'].values())}",
        "",
        "## E24",
        "",
        f"- Conway Life library rank: {e24['calculated']['life_library_rank']}/1024",
        f"- Conway Life library is top decile: {e24['calculated']['life_library_top_decile']}",
        f"- Conway Life strict rate: {fmt(e24['calculated']['life_strict'])}",
        f"- Registered Life rare-book gate: {e24['calculated']['gate_life_rare_book']}",
        f"- Boundary-of-order clock gate: {e24['calculated']['gate_boundary_of_order']}",
        f"- Clock floor fraction: {fmt(e24['calculated']['clock_floor_four_fraction'])}",
        f"- Source-convention smoothness: {fmt(e24['null_sensitivity']['source_convention']['ratio'])}",
        f"- Smoothness excluding empty-empty pairs: {fmt(e24['null_sensitivity']['exclude_empty_empty']['ratio'])}",
        f"- Smoothness among non-empty libraries: {fmt(e24['null_sensitivity']['both_nonempty']['ratio'])}",
        f"- All reported summary fields reproduced: {all(e24['reported_match'].values())}",
        "",
        "## E34",
        "",
        f"- Aggregate component gates reproduced: {all(e34['component_gate_match'].values())}",
        f"- Battery verdict reproduced from aggregates: {all(e34['battery_verdict_match'].values())}",
        "- Ladder, regime, worm, and placement files mostly retain aggregate summaries rather than lower-level outcomes.",
        "",
        "## Separate implementation",
        "",
        f"- Raw atlas strict exact matches: {cross['atlas']['fields']['strict']['exact_matches']}/88",
        f"- Raw atlas library-string exact matches: {cross['atlas']['library_strings']['exact_matches']}/88",
        f"- Five-noise strict Spearman: {fmt(cross['phase']['fields']['strict']['spearman'])}",
        f"- Five-noise strict MAE: {fmt(cross['phase']['fields']['strict']['mean_absolute_error'])}",
        f"- Particle gate verdicts, Fable vs Codex: {cross['particle']['fable_gates']} vs {cross['particle']['codex_gates']}",
        f"- Named-Life gate verdicts all match: {all(cross['named_life']['gate_verdict_matches'].values())}; form-support IDs all exact: {all(value['exact'] for value in cross['named_life']['form_supports'].values())}",
        f"- Life-family common rules: {life_cross['n_common']}/1024; strict Spearman {fmt(life_cross['fields']['strict']['spearman'])}; library-size Spearman {fmt(life_cross['fields']['library_size']['spearman'])}",
        f"- Life-family raw support-string comparison available: {life_cross['library_strings']['available']} (the retained Fable CSV omits support masks)",
        f"- Life-family four frozen gate verdicts all match: {all(life_cross['gate_verdict_matches'].values())}",
        f"- Life-family follow-up robustness gates: {life_cross['campaign']['robustness_gates']}",
        f"- Separate condition summaries match the campaign aggregate: {all_condition_summaries_match}",
        "- The Codex implementation used supplied outputs and code-free golden traces for semantic reconciliation; this is strong implementation reproduction, not independence of the scientific contract.",
        "",
        "## Interpretation boundary",
        "",
        "- These recalculations can verify retained summaries and expose convention sensitivity.",
        "- They cannot upgrade L1's all-substrate/only-if language or L2's near-orthogonality claim.",
        "- Fresh futures remain prohibited until the Stage-D contract is frozen.",
        "",
    ]
    return "\n".join(lines)
