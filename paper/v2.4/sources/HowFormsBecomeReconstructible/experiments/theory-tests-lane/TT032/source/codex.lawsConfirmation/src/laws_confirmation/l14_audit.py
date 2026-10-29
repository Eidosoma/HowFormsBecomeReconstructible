"""Retrospective engineering-cost and search-history ledger for L14."""

from __future__ import annotations

import ast
from collections import deque
import csv
import io
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import sha256_file


MILESTONES: tuple[dict[str, Any], ...] = (
    {
        "label": "heredity",
        "experiment": 26,
        "package": "voltage_web",
        "endpoint": "passing conserved-sheet heredity screen plus parental regeneration",
        "interpretation": "registered pass in one engineered substrate; not an any-substrate result",
        "result_files": (
            "results/full/screen.json",
            "results/full/regeneration.json",
        ),
    },
    {
        "label": "selfhood",
        "experiment": 30,
        "package": "anatomical_homeostasis",
        "endpoint": "recovery of a 15-dimensional compositional census after neutral insults",
        "interpretation": "one of three gates passed; position was not restored",
        "result_files": ("results/full/homeo_summary.json",),
    },
    {
        "label": "learning",
        "experiment": 33,
        "package": "tissue_training",
        "endpoint": "positive paired trained-minus-naive conversion residue",
        "interpretation": "all three registered learning gates failed",
        "result_files": ("results/full/train_summary.json",),
    },
    {
        "label": "anatomy",
        "experiment": 49,
        "package": "triangle_final",
        "endpoint": "position-resolved displaced-charge repair under a self-blueprint",
        "interpretation": "repair and knife passed; arbitrary adoption and imprint steering failed",
        "result_files": ("results/full/triangle_summary.json",),
    },
)


AUDIT_PACKAGES = (
    "eca_atlas",
    "voltage_web",
    "anatomical_homeostasis",
    "improvisation",
    "tissue_training",
    "ladder_web",
    "stress_wire",
    "persuadability",
    "james_test",
    "excitable_web",
    "lightcone_2",
    "persuadability_2",
    "james_test_2",
    "growing_web",
    "lightcone_3",
    "persuadability_3",
    "james_test_3",
    "blueprint_web",
    "triangle_final",
)


SEARCH_EFFORT: tuple[dict[str, Any], ...] = (
    {
        "package": "eca_atlas",
        "documented_rounds": 2,
        "prior_unsuccessful_or_revised": 1,
        "calibration_cells": None,
        "basis": "numbered dev-screen record",
    },
    {
        "package": "voltage_web",
        "documented_rounds": 5,
        "prior_unsuccessful_or_revised": 4,
        "calibration_cells": None,
        "basis": "numbered dev-screen record; conservation is round 5",
    },
    {
        "package": "tissue_training",
        "documented_rounds": 2,
        "prior_unsuccessful_or_revised": 1,
        "calibration_cells": None,
        "basis": "numbered training-stimulus calibration",
    },
    {
        "package": "ladder_web",
        "documented_rounds": 4,
        "prior_unsuccessful_or_revised": 3,
        "calibration_cells": None,
        "basis": "numbered ladder development record",
    },
    {
        "package": "excitable_web",
        "documented_rounds": 3,
        "prior_unsuccessful_or_revised": 2,
        "calibration_cells": None,
        "basis": "numbered amplifier calibration record",
    },
    {
        "package": "lightcone_2",
        "documented_rounds": 2,
        "prior_unsuccessful_or_revised": 1,
        "calibration_cells": None,
        "basis": "discovery-log coupling rounds",
    },
    {
        "package": "growing_web",
        "documented_rounds": 2,
        "prior_unsuccessful_or_revised": 1,
        "calibration_cells": None,
        "basis": "dense-update pathology followed by thinned proposals",
    },
    {
        "package": "lightcone_3",
        "documented_rounds": 2,
        "prior_unsuccessful_or_revised": 1,
        "calibration_cells": None,
        "basis": "magnitude-reader/census-metric round followed by revised round",
    },
    {
        "package": "persuadability_3",
        "documented_rounds": 2,
        "prior_unsuccessful_or_revised": 1,
        "calibration_cells": None,
        "basis": "jointly recorded Wave-10 revision",
    },
    {
        "package": "james_test_3",
        "documented_rounds": 2,
        "prior_unsuccessful_or_revised": 1,
        "calibration_cells": None,
        "basis": "two recorded engine rounds",
    },
    {
        "package": "blueprint_web",
        "documented_rounds": None,
        "prior_unsuccessful_or_revised": None,
        "calibration_cells": 9,
        "basis": "3 x 3 freedom-calibration square; cells are not rounds",
    },
    {
        "package": "triangle_final",
        "documented_rounds": 1,
        "prior_unsuccessful_or_revised": 0,
        "calibration_cells": None,
        "basis": "one theorem trial after E48 calibration",
    },
)


LAW_DEPENDENCIES = (
    "L01_boundary_of_order.md",
    "L02_heredity_not_computation.md",
    "L05_conservation_selfhood.md",
    "L07_learning_cheapest_cognition.md",
    "L09_triangle_resolution.md",
    "L13_interpolation_extrapolation.md",
    "L15_timescale.md",
    "L16_landlord_tenant.md",
)


NARRATIVE_INPUTS = (
    "LAWS.md",
    "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
    "RULIAD_DISCUSSION.md",
    "WAVE7_PROPHECIES.md",
    "WAVE8_PROPHECIES.md",
    "WAVE9_PROPHECIES.md",
    "WAVE10_PROPHECIES.md",
    "WAVE11_PROPHECIES.md",
)


def _read_text(tracker: InputTracker, path: Path) -> str:
    return tracker.add(path).read_text(encoding="utf-8")


def _read_json(tracker: InputTracker, path: Path) -> dict[str, Any]:
    value = tracker.json(path)
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_relative(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()))


def _history(repo_root: Path, path: Path) -> list[dict[str, str]]:
    relative = _repo_relative(repo_root, path)
    output = _git(
        repo_root,
        "log",
        "--reverse",
        "--date=iso-strict",
        "--format=%H%x09%aI%x09%cI",
        "--",
        relative,
    )
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line:
            continue
        commit, authored, committed = line.split("\t")
        rows.append(
            {
                "commit": commit,
                "authored_utc": authored,
                "committed_utc": committed,
            }
        )
    return rows


def _strict_ancestor(repo_root: Path, earlier: str, later: str) -> bool:
    if earlier == later:
        return False
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", earlier, later],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _logical_line_count(text: str) -> int:
    return sum(bool(line.strip()) and not line.lstrip().startswith("#") for line in text.splitlines())


def _is_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id == "dataclass":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "dataclass":
            return True
    return False


def _dataclass_field_count(tree: ast.AST) -> int:
    result = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not _is_dataclass(node):
            continue
        result += sum(isinstance(child, ast.AnnAssign) for child in node.body)
    return result


def _registered_gate_count(text: str) -> int | None:
    lines = text.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(r"^##\s+.*\bgates?\b", line, flags=re.IGNORECASE)
        ),
        None,
    )
    if start is None:
        return None
    count = 0
    for line in lines[start + 1 :]:
        if count and line.startswith("## "):
            break
        if re.match(r"^\d+\.\s", line):
            count += 1
    return count


def _module_map(ideas_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for package_root in sorted(path for path in ideas_root.iterdir() if path.is_dir()):
        source_root = package_root / "src"
        if not source_root.is_dir():
            continue
        candidates = [
            path
            for path in source_root.iterdir()
            if (path.is_dir() and (path / "__init__.py").is_file())
            or (path.is_file() and path.suffix == ".py")
        ]
        for candidate in candidates:
            module = candidate.stem if candidate.is_file() else candidate.name
            if module in result and result[module] != package_root.name:
                raise ValueError(
                    f"duplicate internal top-level module {module}: "
                    f"{result[module]} and {package_root.name}"
                )
            result[module] = package_root.name
    return result


def _imports_from_tree(tree: ast.AST) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            result.add(node.module.split(".", 1)[0])
    return result


def build_dependency_graph(
    ideas_root: Path,
    roots: Iterable[str],
    tracker: InputTracker,
) -> tuple[dict[str, set[str]], dict[str, list[Path]]]:
    """Parse internal imports recursively from the requested historical roots."""

    modules = _module_map(ideas_root)
    known_packages = set(modules.values())
    queue = deque(dict.fromkeys(roots))
    graph: dict[str, set[str]] = {}
    source_paths: dict[str, list[Path]] = {}
    while queue:
        package = queue.popleft()
        if package in graph:
            continue
        root = ideas_root / package
        if not root.is_dir():
            raise FileNotFoundError(root)
        paths = sorted((root / "src").rglob("*.py"))
        if not paths:
            raise ValueError(f"historical package has no Python source: {root}")
        dependencies: set[str] = set()
        for path in paths:
            text = _read_text(tracker, path)
            tree = ast.parse(text, filename=str(path))
            for imported in _imports_from_tree(tree):
                dependency = modules.get(imported)
                if dependency in known_packages and dependency != package:
                    dependencies.add(dependency)
        graph[package] = dependencies
        source_paths[package] = paths
        queue.extend(sorted(dependencies - graph.keys()))
    return graph, source_paths


def dependency_closure(root: str, graph: Mapping[str, set[str]]) -> tuple[str, ...]:
    visited: set[str] = set()
    queue = [root]
    while queue:
        package = queue.pop()
        if package in visited:
            continue
        visited.add(package)
        queue.extend(sorted(graph.get(package, set()) - visited))
    return tuple(sorted(visited))


def _package_history(repo_root: Path, package_root: Path) -> dict[str, Any]:
    history = _history(repo_root, package_root)
    result_history = _history(repo_root, package_root / "results")
    return {
        "package_commits": len(history),
        "first_package_commit": history[0] if history else None,
        "last_package_commit": history[-1] if history else None,
        "result_commits": len(result_history),
        "first_result_commit": result_history[0] if result_history else None,
        "last_result_commit": result_history[-1] if result_history else None,
    }


def package_metrics(
    ideas_root: Path,
    repo_root: Path,
    package: str,
    dependencies: Iterable[str],
    source_paths: Sequence[Path],
    tracker: InputTracker,
) -> dict[str, Any]:
    root = ideas_root / package
    expectation = root / "EXPECTATIONS.md"
    expectation_text: str | None = None
    if expectation.is_file():
        expectation_text = _read_text(tracker, expectation)
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        tracker.add(pyproject)

    tests = sorted((root / "tests").rglob("*.py")) if (root / "tests").is_dir() else []
    source_texts = {path: _read_text(tracker, path) for path in source_paths}
    test_texts = {path: _read_text(tracker, path) for path in tests}
    dataclass_fields = sum(
        _dataclass_field_count(ast.parse(text, filename=str(path)))
        for path, text in source_texts.items()
    )

    result_root = root / "results/full"
    result_files = sorted(path for path in result_root.rglob("*") if path.is_file()) if result_root.is_dir() else []
    elapsed: list[dict[str, Any]] = []
    invalid_json: list[str] = []
    for path in result_files:
        tracker.add(path)
        if path.suffix.lower() != ".json":
            continue
        try:
            payload = _read_json(tracker, path)
        except (json.JSONDecodeError, TypeError):
            invalid_json.append(str(path))
            continue
        value = payload.get("elapsed_seconds")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            elapsed.append(
                {
                    "path": str(path),
                    "elapsed_seconds": float(value),
                }
            )

    result = {
        "package": package,
        "direct_internal_dependencies": sorted(set(dependencies)),
        "direct_internal_dependency_count": len(set(dependencies)),
        "source_files": len(source_paths),
        "test_files": len(tests),
        "source_logical_lines": sum(_logical_line_count(text) for text in source_texts.values()),
        "test_logical_lines": sum(_logical_line_count(text) for text in test_texts.values()),
        "dataclass_fields": dataclass_fields,
        "registered_gate_count": (
            _registered_gate_count(expectation_text)
            if expectation_text is not None
            else None
        ),
        "expectations_present": expectation_text is not None,
        "result_files": len(result_files),
        "result_bytes": sum(path.stat().st_size for path in result_files),
        "elapsed_json_records": len(elapsed),
        "retained_elapsed_seconds_sum": sum(row["elapsed_seconds"] for row in elapsed),
        "elapsed_records": elapsed,
        "invalid_json_files": invalid_json,
    }
    result.update(_package_history(repo_root, root))
    return result


def aggregate_package_metrics(
    packages: Sequence[str], metrics: Mapping[str, Mapping[str, Any]], graph: Mapping[str, set[str]]
) -> dict[str, Any]:
    additive = (
        "source_files",
        "test_files",
        "source_logical_lines",
        "test_logical_lines",
        "dataclass_fields",
        "result_files",
        "result_bytes",
        "elapsed_json_records",
        "retained_elapsed_seconds_sum",
    )
    result: dict[str, Any] = {
        "packages": list(packages),
        "package_count": len(packages),
        "internal_dependency_edges": sum(
            dependency in packages
            for package in packages
            for dependency in graph.get(package, set())
        ),
    }
    for field in additive:
        result[field] = sum(metrics[package][field] for package in packages)
    return result


def _gate_booleans(payload: Mapping[str, Any]) -> dict[str, bool]:
    result = {
        str(key): value
        for key, value in payload.items()
        if str(key).startswith("gate_") and isinstance(value, bool)
    }
    nested = payload.get("gates")
    if isinstance(nested, Mapping):
        result.update(
            {
                str(key): value
                for key, value in nested.items()
                if str(key).startswith("gate_") and isinstance(value, bool)
            }
        )
    return dict(sorted(result.items()))


def _milestone_values(label: str, payloads: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if label == "heredity":
        screen, regeneration = payloads
        return {
            "screen_grid_cells": len(screen["grid"]),
            "passing_screen_cells": int(screen["n_passing"]),
            "parental_regeneration_gate": bool(regeneration["gate_regeneration"]),
        }
    payload = payloads[0]
    gates = payload.get("gates", {})
    if label == "selfhood":
        return {
            "types_passing": int(gates["n_types_passing"]),
            "rewritten_mean": float(gates["rewritten_mean"]),
            "wild_mean": float(gates["wild_mean"]),
        }
    if label == "learning":
        return {
            "training_effect": float(gates["training_effect"]),
            "trained_conversion": float(gates["trained_conversion"]),
            "naive_conversion": float(gates["naive_conversion"]),
            "effect_by_delay": gates["effect_by_delay"],
        }
    if label == "anatomy":
        return {
            "adoption_final_agreement": float(gates["adoption_final_agreement"]),
            "steering_rate_T": float(gates["steer"]["T"]),
            "transport_D": gates["transport"]["D"],
            "transport_T": gates["transport"]["T"],
            "transport_T_lesion": gates["transport"]["T_lesion"],
        }
    raise ValueError(label)


def milestone_ledger(
    ideas_root: Path,
    repo_root: Path,
    tracker: InputTracker,
    metrics: Mapping[str, Mapping[str, Any]],
    graph: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    round_lookup = {row["package"]: row for row in SEARCH_EFFORT}
    base_closure = set(dependency_closure("voltage_web", graph))
    rows: list[dict[str, Any]] = []
    for milestone in MILESTONES:
        package = str(milestone["package"])
        closure = dependency_closure(package, graph)
        payloads = [
            _read_json(tracker, ideas_root / package / relative)
            for relative in milestone["result_files"]
        ]
        gates: dict[str, bool] = {}
        for payload in payloads:
            duplicate = set(gates) & set(_gate_booleans(payload))
            if duplicate:
                raise ValueError(f"duplicate milestone gate names for {package}: {sorted(duplicate)}")
            gates.update(_gate_booleans(payload))
        aggregate = aggregate_package_metrics(closure, metrics, graph)
        added = tuple(sorted(set(closure) - base_closure))
        added_aggregate = aggregate_package_metrics(added, metrics, graph) if added else {
            "packages": [],
            "package_count": 0,
            "source_logical_lines": 0,
            "test_logical_lines": 0,
            "dataclass_fields": 0,
            "result_files": 0,
            "result_bytes": 0,
            "elapsed_json_records": 0,
            "retained_elapsed_seconds_sum": 0.0,
            "source_files": 0,
            "test_files": 0,
            "internal_dependency_edges": 0,
        }

        expectation_history = _history(repo_root, ideas_root / package / "EXPECTATIONS.md")
        result_histories = [
            _history(repo_root, ideas_root / package / relative)
            for relative in milestone["result_files"]
        ]
        first_results = [history[0] for history in result_histories if history]
        first_expectation = expectation_history[0] if expectation_history else None
        preregistered_snapshot = bool(first_expectation and first_results) and all(
            _strict_ancestor(repo_root, first_expectation["commit"], result["commit"])
            for result in first_results
        )
        round_record = round_lookup.get(package, {})
        row = {
            **milestone,
            "gate_booleans": gates,
            "registered_gate_count": metrics[package]["registered_gate_count"],
            "retained_gate_pass_count": sum(gates.values()),
            "retained_gate_boolean_count": len(gates),
            "all_retained_gate_booleans_pass": bool(gates) and all(gates.values()),
            "values": _milestone_values(str(milestone["label"]), payloads),
            "documented_root_rounds": round_record.get("documented_rounds"),
            "root_prior_unsuccessful_or_revised": round_record.get(
                "prior_unsuccessful_or_revised"
            ),
            "direct_metrics": dict(metrics[package]),
            "dependency_closure": list(closure),
            "closure_metrics": aggregate,
            "packages_added_over_heredity_base": list(added),
            "added_over_heredity_base_metrics": added_aggregate,
            "first_expectations_commit": first_expectation,
            "first_result_commits": first_results,
            "repository_verifiable_expectations_only_snapshot": preregistered_snapshot,
        }
        rows.append(row)
    return rows


def _grid_cells(payload: Mapping[str, Any]) -> int | None:
    grid = payload.get("grid")
    return len(grid) if isinstance(grid, list) else None


def search_effort_ledger(ideas_root: Path, tracker: InputTracker) -> list[dict[str, Any]]:
    eca_screens = (
        _read_json(tracker, ideas_root / "eca_atlas/results/full/screen_round1_mean3.json"),
        _read_json(tracker, ideas_root / "eca_atlas/results/full/screen.json"),
    )
    voltage_screens = tuple(
        _read_json(tracker, ideas_root / f"voltage_web/results/full/{name}")
        for name in (
            "screen_round1.json",
            "screen_round2.json",
            "screen_round3.json",
            "screen_round4.json",
            "screen.json",
        )
    )
    blueprint = _read_json(
        tracker, ideas_root / "blueprint_web/results/full/calibration_square.json"
    )
    computed = {
        "eca_atlas": {
            "retained_screen_files": 2,
            "retained_grid_cells": sum(_grid_cells(payload) or 0 for payload in eca_screens),
            "retained_nonpassing_screens": sum(int(payload["n_passing"]) == 0 for payload in eca_screens),
        },
        "voltage_web": {
            "retained_screen_files": 5,
            "retained_grid_cells": sum(_grid_cells(payload) or 0 for payload in voltage_screens),
            "retained_nonpassing_screens": sum(int(payload["n_passing"]) == 0 for payload in voltage_screens),
        },
        "blueprint_web": {
            "retained_screen_files": 1,
            "retained_grid_cells": len(blueprint["square"]),
            "retained_nonpassing_screens": None,
        },
    }
    rows = []
    for frozen in SEARCH_EFFORT:
        row = dict(frozen)
        row.update(
            computed.get(
                str(frozen["package"]),
                {
                    "retained_screen_files": None,
                    "retained_grid_cells": None,
                    "retained_nonpassing_screens": None,
                },
            )
        )
        rows.append(row)
    return rows


def search_ladder(ideas_root: Path, tracker: InputTracker) -> list[dict[str, Any]]:
    baseline = _read_json(
        tracker, ideas_root / "improvisation/results/full/transport_posthoc.json"
    )
    field = _read_json(tracker, ideas_root / "ladder_web/results/full/lightcone_summary.json")
    wave = _read_json(tracker, ideas_root / "lightcone_2/results/full/cone2_summary.json")
    motion = _read_json(tracker, ideas_root / "lightcone_3/results/full/cone3_summary.json")
    blueprint = _read_json(
        tracker, ideas_root / "triangle_final/results/full/triangle_summary.json"
    )
    rows = [
        {
            "stage": 1,
            "label": "passive conserved sheet",
            "experiments": "E30/E31",
            "packages": ["anatomical_homeostasis", "improvisation"],
            "added_construction": "conservation, bistability, coupling",
            "task_registration": "posthoc transport assay after the registered detour task proved vacuous",
            "repair_transport_pass": False,
            "key_metric": {
                condition: float(values["profile_error_after_60_sweeps"])
                for condition, values in baseline["rows"].items()
            },
        },
        {
            "stage": 2,
            "label": "sparse reference/field/stress",
            "experiments": "E35-E38",
            "packages": ["ladder_web", "stress_wire", "persuadability", "james_test"],
            "added_construction": "anchors, organizer interpolation, comparator and stress wire",
            "task_registration": "registered",
            "repair_transport_pass": bool(field["gates"]["gate_p35_2_anchors"])
            or bool(field["gates"]["gate_p35_3_morphogen"]),
            "key_metric": {
                rung: float(values["spatial_cone_median"])
                for rung, values in field["gates"]["lightcone"].items()
            },
        },
        {
            "stage": 3,
            "label": "excitable license",
            "experiments": "E39-E42",
            "packages": ["excitable_web", "lightcone_2", "persuadability_2", "james_test_2"],
            "added_construction": "two excitable channels and error-triggered wave coupling",
            "task_registration": "registered; coupling revised before final E40 run",
            "repair_transport_pass": bool(wave["gates"]["gate_p40_1_spatial_on"]),
            "key_metric": {
                rung: {
                    "spatial_cone": float(values["spatial_cone_median"]),
                    "transport_recovery": float(values["transport_recovery_max_d"]),
                }
                for rung, values in wave["gates"]["lightcone2"].items()
            },
        },
        {
            "stage": 4,
            "label": "moving cells",
            "experiments": "E43-E46",
            "packages": ["growing_web", "lightcone_3", "persuadability_3", "james_test_3"],
            "added_construction": "Kawasaki swaps, adhesion, organizer chemotaxis",
            "task_registration": "registered; metric and receptor implementation revised before round 2",
            "repair_transport_pass": bool(motion["gates"]["gate_p44_1_spatial_on_H"]),
            "key_metric": {
                rung: {
                    "spatial_cone": float(values["spatial_cone_median"]),
                    "transport_recovery": float(values["transport_recovery_max_d"]),
                }
                for rung, values in motion["gates"]["lightcone3"].items()
            },
        },
        {
            "stage": 5,
            "label": "slow self-reference",
            "experiments": "E48/E49",
            "packages": ["blueprint_web", "triangle_final"],
            "added_construction": "full-field R, EMA rate rho, comparator gain c_m, whole-R inheritance",
            "task_registration": "E49 expectations precede its retained result in Git",
            "repair_transport_pass": bool(blueprint["gates"]["gate_p49_1_transport"]),
            "key_metric": blueprint["gates"]["transport"],
            "arbitrary_adoption_pass": bool(blueprint["gates"]["gate_p49_2_freedom"]),
            "imprint_steering_pass": bool(blueprint["gates"]["gate_p49_3_imprint_steering"]),
        },
    ]
    passes = [row["stage"] for row in rows if row["repair_transport_pass"]]
    if passes != [5]:
        raise ValueError(f"unexpected retained transport ladder pass pattern: {passes}")
    return rows


def calculate_min_energy_table(
    details: Mapping[str, Mapping[str, Mapping[str, Any]]], threshold: float = 0.5
) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for condition, ladder in details.items():
        working = [
            float(entry["energy"])
            for entry in ladder.values()
            if float(entry["rate"]) >= threshold
        ]
        result[condition] = min(working) if working else None
    return dict(sorted(result.items()))


def intervention_energy_audit(payload: Mapping[str, Any]) -> dict[str, Any]:
    calculated = calculate_min_energy_table(payload["details"])
    reported = payload["gates"]["min_energy_table"]
    keys_match = set(calculated) == set(reported)
    value_matches = {
        key: (
            calculated[key] is None
            and reported[key] is None
            or calculated[key] is not None
            and reported[key] is not None
            and abs(float(calculated[key]) - float(reported[key])) <= 1e-12
        )
        for key in sorted(set(calculated) & set(reported))
    }
    working = {key: value for key, value in calculated.items() if value is not None}
    return {
        "success_rate_threshold": 0.5,
        "calculated_min_energy_table": calculated,
        "reported_min_energy_table": reported,
        "keys_match": keys_match,
        "value_matches": value_matches,
        "all_values_match": keys_match and all(value_matches.values()),
        "working_rung_lever_pairs": working,
        "working_pair_count": len(working),
        "total_pair_count": len(calculated),
        "coverage_fraction": len(working) / len(calculated),
        "information_migrates_to_cheapest_on_D": bool(
            payload["gates"]["gate_p37_2_information_wins_on_D"]
        ),
        "reinforcement_monotonically_cheapens": bool(
            payload["gates"]["gate_p37_3_reinforcement_cheapens"]
        ),
        "is_common_price_for_four_l14_competencies": False,
        "interpretation": (
            "quadratic intervention energy is defined for E37 persuadability only; "
            "15 of 16 rung/lever pairs have no working price"
        ),
    }


def timescale_audit(
    calibration: Mapping[str, Any], triangle: Mapping[str, Any]
) -> dict[str, Any]:
    square = calibration["square"]
    parsed = [
        (float(key.split("|")[0]), float(key.split("|")[1]), value)
        for key, value in square.items()
    ]
    rho_values = sorted({rho for rho, _, _ in parsed})
    gain_values = sorted({gain for _, gain, _ in parsed})
    chosen_rho, chosen_gain = (float(value) for value in str(calibration["chosen"]).split("|"))
    freedom_at_chosen_gain = {
        str(rho): {
            "freedom_pass": bool(value["freedom_pass"]),
            "conversion": float(value["conversion"]),
        }
        for rho, gain, value in parsed
        if gain == chosen_gain
    }
    return {
        "calibration_rho_values": rho_values,
        "calibration_gain_values": gain_values,
        "calibration_cells": len(parsed),
        "chosen_rho": chosen_rho,
        "chosen_gain": chosen_gain,
        "chosen_rho_is_slowest": chosen_rho == min(rho_values),
        "freedom_at_chosen_gain_by_rho": freedom_at_chosen_gain,
        "all_tested_rhos_pass_freedom_at_chosen_gain": all(
            row["freedom_pass"] for row in freedom_at_chosen_gain.values()
        ),
        "repair_endpoint_rho_values": [chosen_rho],
        "repair_transport_pass_at_chosen_point": bool(
            triangle["gates"]["gate_p49_1_transport"]
        ),
        "rho_varied_on_repair_endpoint": False,
        "resolution_varied_independently_on_repair_endpoint": False,
        "reference_provenance_varied_independently_on_repair_endpoint": False,
        "theta_landscape_varied_independently_on_repair_endpoint": False,
        "time_identified_as_the_causal_price": False,
        "interpretation": (
            "E48 crosses rho and gain for heredity/freedom, but E49 tests repair "
            "only at rho=0.002 with a full-field self-reference; speed, resolution, "
            "provenance, gain, and theta are not separated on the repair endpoint"
        ),
    }


def _law_verdict(text: str) -> str | None:
    match = re.search(r"^overall_verdict:\s*([^\n]+)$", text, flags=re.MULTILINE)
    return match.group(1).strip().strip('"') if match else None


def _claim_adjudication(
    milestones: Sequence[Mapping[str, Any]],
    ladder: Sequence[Mapping[str, Any]],
    energy: Mapping[str, Any],
    timescale: Mapping[str, Any],
    dependency_verdicts: Mapping[str, str | None],
) -> list[dict[str, str]]:
    by_label = {str(row["label"]): row for row in milestones}
    return [
        {
            "claim": "Heredity is cheap in any boundary-of-order multi-attractor physics.",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2",
            "reason": (
                f"The conserved sheet is a positive construction but required five documented "
                f"development screens, four nonpassing; L1 is already "
                f"{dependency_verdicts.get('L01_boundary_of_order.md')}. No natural-frequency "
                "or common-cost denominator exists."
            ),
        },
        {
            "claim": "Selfhood is cheap because conservation plus bistability suffices.",
            "verdict": "NOT_CONFIRMED_AS_A_PRICE_CLAIM",
            "evidence_level": "E3",
            "reason": (
                f"E30 passes {by_label['selfhood']['retained_gate_pass_count']}/"
                f"{by_label['selfhood']['retained_gate_boolean_count']} gates on a coarse "
                "compositional endpoint and restores no position. Sufficiency for that bounded "
                "effect does not measure cheapness or general selfhood."
            ),
        },
        {
            "claim": "Learning is cheap because conserved traces suffice.",
            "verdict": "NOT_CONFIRMED_AS_A_PRICE_CLAIM",
            "evidence_level": "E3",
            "reason": (
                f"E33 has a positive +{by_label['learning']['values']['training_effect']:.4f} "
                "residue after two calibrations, but 0/3 registered gates pass. L7's completed "
                f"verdict is {dependency_verdicts.get('L07_learning_cheapest_cognition.md')}."
            ),
        },
        {
            "claim": "Position-resolved repair required additional address/reference machinery in the tested model family.",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                f"The same transport lineage records {len(ladder)-1} nonpassing mechanism "
                "stages before the full-field self-reference passes repair at stage 5. The "
                "result does not establish necessity outside this construction genealogy."
            ),
        },
        {
            "claim": "The price ordering survives engineering effort, search effort, task difficulty, and endpoint power.",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2",
            "reason": (
                "The tasks, observers, dimensions, thresholds, development histories, and "
                "mechanisms differ; stages are sequential and outcome-adaptive. The ledger "
                "contains no matched design or adjustment model."
            ),
        },
        {
            "claim": "Cheap and expensive correspond to one measurable price.",
            "verdict": "NOT_EMPIRICAL_AS_WRITTEN",
            "evidence_level": "E1",
            "reason": (
                f"No common unit is registered. E37 prices only intervention energy and has "
                f"working values for {energy['working_pair_count']}/{energy['total_pair_count']} "
                "rung/lever pairs, not the four L14 competencies."
            ),
        },
        {
            "claim": "Anatomy is bought specifically with TIME: a slower self-reference over a still slower frozen layer.",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2",
            "reason": (
                "The repair endpoint uses one rho and co-varies speed with full-field resolution, "
                "self provenance, comparator gain, and theta. L15/L16 remain separate first-pass "
                f"dependencies; causal-time identification is {timescale['time_identified_as_the_causal_price']}."
            ),
        },
    ]


def run_l14_audit(
    plastic_root: Path, workspace: Path
) -> tuple[
    dict[str, Any],
    list[Path],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[Path, str],
]:
    ideas_root = plastic_root / IDEAS_RELATIVE
    if not ideas_root.is_dir():
        raise FileNotFoundError(ideas_root)
    tracker = InputTracker()

    protocol = workspace / "protocols/L14_PRICE_ORDER_LEDGER_V1.md"
    tracker.add(protocol)
    narrative_text = {
        name: _read_text(tracker, ideas_root / name) for name in NARRATIVE_INPUTS
    }
    dependency_verdicts = {
        name: _law_verdict(_read_text(tracker, workspace / "laws" / name))
        for name in LAW_DEPENDENCIES
    }

    repo_root = Path(_git(plastic_root, "rev-parse", "--show-toplevel"))
    graph, source_paths = build_dependency_graph(
        ideas_root, AUDIT_PACKAGES, tracker
    )
    package_names = tuple(sorted(graph))
    metrics = {
        package: package_metrics(
            ideas_root,
            repo_root,
            package,
            graph[package],
            source_paths[package],
            tracker,
        )
        for package in package_names
    }
    package_rows = [metrics[package] for package in package_names]

    milestones = milestone_ledger(
        ideas_root, repo_root, tracker, metrics, graph
    )
    search_rows = search_effort_ledger(ideas_root, tracker)
    ladder = search_ladder(ideas_root, tracker)
    persuadability = _read_json(
        tracker, ideas_root / "persuadability/results/full/persuade_summary.json"
    )
    energy = intervention_energy_audit(persuadability)
    calibration = _read_json(
        tracker, ideas_root / "blueprint_web/results/full/calibration_square.json"
    )
    triangle = _read_json(
        tracker, ideas_root / "triangle_final/results/full/triangle_summary.json"
    )
    timescale = timescale_audit(calibration, triangle)

    # These source assertions are required to be present, but their rhetoric is
    # never promoted to a measured cost variable.
    phrase_checks = {
        "laws_contains_price_order": "price order of miracles" in narrative_text["LAWS.md"].lower(),
        "discussion_claims_knows_price_by_measurement": (
            "knows the price list by measurement" in narrative_text["RULIAD_DISCUSSION.md"]
        ),
        "discussion_claims_anatomy_priced_in_time": (
            "Anatomy: priced in TIME" in narrative_text["RULIAD_DISCUSSION.md"]
        ),
    }
    if not all(phrase_checks.values()):
        raise ValueError(f"L14 source phrase check failed: {phrase_checks}")

    claims = _claim_adjudication(
        milestones, ladder, energy, timescale, dependency_verdicts
    )
    frozen_input_hashes = {
        path: sha256_file(path) for path in sorted(tracker.paths)
    }
    audit = {
        "schema_version": 1,
        "law": "L14",
        "audit_kind": "outcome-known retained engineering-cost and search-history ledger",
        "work_state": "RECALCULATED",
        "overall_verdict": "MIXED",
        "scientific_futures_generated": 0,
        "simulator_replays": 0,
        "price_scalar_defined": False,
        "scalar_ranking_prohibited_by_protocol": True,
        "repository_root": str(repo_root),
        "ideas_root": str(ideas_root),
        "input_file_count": len(tracker.paths),
        "source_phrase_checks": phrase_checks,
        "dependency_verdicts": dependency_verdicts,
        "package_count": len(package_rows),
        "package_metrics": package_rows,
        "milestones": milestones,
        "search_effort": search_rows,
        "positional_repair_search_ladder": ladder,
        "mechanism_stages_before_first_repair_pass": len(ladder) - 1,
        "intervention_energy": energy,
        "timescale": timescale,
        "claims": claims,
        "limitations": [
            "No time sheets, person-hours, complete failed-run census, or total CPU ledger exists.",
            "Retained elapsed_seconds fields mix shard runtimes, aggregation runtimes, parallel work, and superseded rounds.",
            "Git commits batch whole waves and are timestamps/provenance markers, not labor units.",
            "Later stages depend on earlier code and were designed after earlier outcomes; they are not independent trials.",
            "Milestone endpoints differ in dimensionality, threshold, task validity, and gate structure.",
            "All dynamics were deliberately engineered; repository construction effort cannot estimate spontaneous occurrence in nature.",
            "The L15 timescale and L16 landlord/tenant interpretations have not yet received their own first-pass adjudications.",
        ],
        "strongest_supported_wording": (
            "In the conserved-voltage-sheet implementation history, coarse compositional "
            "heredity/homeostasis and a narrow training-history effect appeared before "
            "position-resolved repair. Four successive mechanism stages failed the shared "
            "displaced-charge transport problem; a fifth, adding an inherited full-field "
            "self-reference, passed repair but not arbitrary reprogramming. This is a bounded "
            "engineering history, not a universal or scalar price order, and the retained "
            "design does not isolate reference speed as the causal purchase."
        ),
    }
    return (
        audit,
        sorted(tracker.paths),
        package_rows,
        milestones,
        search_rows,
        ladder,
        frozen_input_hashes,
    )


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def rows_csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(fields), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: _csv_value(row.get(field)) for field in fields})
    return buffer.getvalue()


def package_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(
        rows,
        (
            "package",
            "direct_internal_dependencies",
            "direct_internal_dependency_count",
            "source_files",
            "test_files",
            "source_logical_lines",
            "test_logical_lines",
            "dataclass_fields",
            "registered_gate_count",
            "result_files",
            "result_bytes",
            "elapsed_json_records",
            "retained_elapsed_seconds_sum",
            "package_commits",
            "result_commits",
            "first_package_commit",
            "first_result_commit",
        ),
    )


def milestone_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    flattened = []
    for row in rows:
        flattened.append(
            {
                **row,
                "closure_package_count": row["closure_metrics"]["package_count"],
                "closure_source_logical_lines": row["closure_metrics"]["source_logical_lines"],
                "closure_test_logical_lines": row["closure_metrics"]["test_logical_lines"],
                "closure_dataclass_fields": row["closure_metrics"]["dataclass_fields"],
                "closure_result_files": row["closure_metrics"]["result_files"],
                "closure_result_bytes": row["closure_metrics"]["result_bytes"],
                "closure_retained_elapsed_seconds_sum": row["closure_metrics"][
                    "retained_elapsed_seconds_sum"
                ],
                "added_package_count": row["added_over_heredity_base_metrics"][
                    "package_count"
                ],
                "direct_source_logical_lines": row["direct_metrics"][
                    "source_logical_lines"
                ],
            }
        )
    return rows_csv(
        flattened,
        (
            "label",
            "experiment",
            "package",
            "endpoint",
            "interpretation",
            "registered_gate_count",
            "retained_gate_pass_count",
            "retained_gate_boolean_count",
            "all_retained_gate_booleans_pass",
            "gate_booleans",
            "values",
            "documented_root_rounds",
            "root_prior_unsuccessful_or_revised",
            "direct_source_logical_lines",
            "dependency_closure",
            "closure_package_count",
            "closure_source_logical_lines",
            "closure_test_logical_lines",
            "closure_dataclass_fields",
            "closure_result_files",
            "closure_result_bytes",
            "closure_retained_elapsed_seconds_sum",
            "packages_added_over_heredity_base",
            "added_package_count",
            "repository_verifiable_expectations_only_snapshot",
        ),
    )


def search_effort_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(
        rows,
        (
            "package",
            "documented_rounds",
            "prior_unsuccessful_or_revised",
            "calibration_cells",
            "retained_screen_files",
            "retained_grid_cells",
            "retained_nonpassing_screens",
            "basis",
        ),
    )


def search_ladder_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(
        rows,
        (
            "stage",
            "label",
            "experiments",
            "packages",
            "added_construction",
            "task_registration",
            "repair_transport_pass",
            "arbitrary_adoption_pass",
            "imprint_steering_pass",
            "key_metric",
        ),
    )


def _fmt_seconds(value: float) -> str:
    return f"{value:,.2f}"


def _fmt_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024**2:
        return f"{value / 1024:.1f} KiB"
    return f"{value / 1024**2:.1f} MiB"


def markdown_report(audit: Mapping[str, Any]) -> str:
    milestones = audit["milestones"]
    lines = [
        "# L14 price-order retained ledger",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known static/recalculation audit; zero simulator replays and zero scientific futures.",
        "",
        "## Plain-language result",
        "",
        "There is a real engineering story here, but there is no measured price list.",
        "",
        "Within the conserved-voltage-sheet genealogy, position-resolved repair did arrive last. "
        "The record contains four nonpassing construction stages before the self-blueprint stage "
        "passes the displaced-charge repair gate. That supports a narrow statement: this particular "
        "anatomy endpoint required machinery absent from the earlier implementations.",
        "",
        "The larger order does not survive audit. The hereditary voltage sheet itself took five "
        "documented development screens, four of them nonpassing. The selfhood milestone passes "
        "only a coarse compositional-recovery gate. The original training experiment has a positive "
        "effect but fails all three registered learning gates. Tasks and endpoints are unequal, the "
        "stages are outcome-adaptive, and no common unit combines code, search, compute, intervention "
        "energy, or biological difficulty.",
        "",
        "The final 'priced in time' clause is also not isolated. E48 varies reference speed for a "
        "freedom screen, but E49 measures repair at only one speed while simultaneously adding a "
        "full-resolution, self-written reference and comparator. Time may matter; this experiment "
        "does not identify it as the price.",
        "",
        "## Common-family milestone ledger",
        "",
        "The elapsed column is the sum of every retained top-level `elapsed_seconds` record in the "
        "dependency closure. It mixes shards, fast aggregation summaries, parallel work, and "
        "superseded rounds; it is shown only to expose why it cannot be a cost scalar.",
        "",
        "| Milestone | E/package | Retained gates | Root rounds | Direct source lines | Closure packages | Closure source lines | Config fields | Retained result bytes | Logged seconds* |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in milestones:
        closure = row["closure_metrics"]
        rounds = row["documented_root_rounds"]
        lines.append(
            "| {label} | E{experiment} `{package}` | {passed}/{total} | {rounds} | "
            "{direct_lines} | {packages} | {closure_lines} | {fields} | {result_bytes} | {seconds} |".format(
                label=row["label"],
                experiment=row["experiment"],
                package=row["package"],
                passed=row["retained_gate_pass_count"],
                total=row["retained_gate_boolean_count"],
                rounds="—" if rounds is None else rounds,
                direct_lines=row["direct_metrics"]["source_logical_lines"],
                packages=closure["package_count"],
                closure_lines=closure["source_logical_lines"],
                fields=closure["dataclass_fields"],
                result_bytes=_fmt_bytes(closure["result_bytes"]),
                seconds=_fmt_seconds(closure["retained_elapsed_seconds_sum"]),
            )
        )
    lines.extend(
        [
            "",
            "A larger closure is visible for the anatomy package, but closure size reflects code "
            "reuse and the historical architecture, not a calibrated scientific difficulty scale. "
            "The selfhood and learning branches also inherit the same expensive E26 substrate.",
            "",
            "### Endpoint asymmetry",
            "",
        ]
    )
    for row in milestones:
        lines.append(
            f"- **{str(row['label']).capitalize()} (E{row['experiment']}):** "
            f"{row['endpoint']}; {row['interpretation']}. Gate map: "
            f"`{json.dumps(row['gate_booleans'], sort_keys=True)}`."
        )

    lines.extend(
        [
            "",
            "## Positional-repair search ladder",
            "",
            "| Stage | Construction | Experiments | Transport result | Key retained reading |",
            "|---:|---|---|---|---|",
        ]
    )
    for row in audit["positional_repair_search_ladder"]:
        result = "PASS (repair only)" if row["repair_transport_pass"] else "no pass"
        metric = json.dumps(row["key_metric"], sort_keys=True, separators=(",", ":"))
        lines.append(
            f"| {row['stage']} | {row['label']} | {row['experiments']} | {result} | `{metric}` |"
        )
    lines.extend(
        [
            "",
            "The final stage does not pass arbitrary reprogramming: adoption is `0.4894` against "
            "the `0.8` gate and imprint steering is `0.0`. Calling it an anatomy purchase is "
            "defensible only for repair of a natively supported pattern.",
            "",
            "## Explicitly documented search effort",
            "",
            "Only named rounds are counted. A blank is unknown, not zero effort; calibration cells "
            "are kept separate from rounds.",
            "",
            "| Package | Rounds | Prior unsuccessful/revised | Calibration cells | Retained grid cells | Basis |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in audit["search_effort"]:
        def show(value: Any) -> str:
            return "—" if value is None else str(value)

        lines.append(
            f"| `{row['package']}` | {show(row['documented_rounds'])} | "
            f"{show(row['prior_unsuccessful_or_revised'])} | {show(row['calibration_cells'])} | "
            f"{show(row['retained_grid_cells'])} | {row['basis']} |"
        )

    energy = audit["intervention_energy"]
    lines.extend(
        [
            "",
            "## The one explicit price axis does not generalize",
            "",
            "E37 defines quadratic intervention energy on four levers across four machinery rungs. "
            f"Independent thresholding reproduces its table exactly, but only "
            f"{energy['working_pair_count']}/{energy['total_pair_count']} pairs have any working "
            f"price: `{json.dumps(energy['working_rung_lever_pairs'], sort_keys=True)}`. The predicted "
            "migration to cheap information on rung D fails, as does monotonically cheaper "
            "reinforcement. This is a persuadability-energy assay, not a price shared by heredity, "
            "selfhood, learning, and anatomy.",
            "",
            "## Time is not isolated",
            "",
        ]
    )
    timescale = audit["timescale"]
    lines.extend(
        [
            f"E48's calibration contains {timescale['calibration_cells']} cells: rho "
            f"`{timescale['calibration_rho_values']}` crossed with gain "
            f"`{timescale['calibration_gain_values']}`. At chosen gain "
            f"`{timescale['chosen_gain']}`, all three rho values pass the freedom screen. The "
            f"slowest (`{timescale['chosen_rho']}`) was selected, and only that rho was carried "
            "into E49's repair test.",
            "",
            timescale["interpretation"] + ".",
            "",
            "## Clause adjudication",
            "",
            "| Clause | Verdict | Level | Reason |",
            "|---|---|---:|---|",
        ]
    )
    for claim in audit["claims"]:
        lines.append(
            f"| {claim['claim']} | `{claim['verdict']}` | {claim['evidence_level']} | {claim['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Why no scalar ranking is reported",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in audit["limitations"])
    lines.extend(
        [
            "",
            "## Strongest wording supported",
            "",
            audit["strongest_supported_wording"],
            "",
            "## Machine record",
            "",
            f"The audit hashed {audit['input_file_count']} inputs and inventoried "
            f"{audit['package_count']} direct or transitive historical packages. See the sibling "
            "JSON and CSV ledgers for exact paths, dependency closures, Git records, bytes, and "
            "retained elapsed metadata.",
            "",
        ]
    )
    return "\n".join(lines)
