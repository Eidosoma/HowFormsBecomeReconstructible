"""Cross-fitted predictor and causal architecture decomposition."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .rng import rng_for
from .wagner_ph_architecture_config import ARCHITECTURE_FORMAT, ArchitectureSpec
from .wagner_ph_architecture_genome import (
    ArchitectureInterpreter,
    Genome,
    effective_genotype,
    initialize_interpreter,
    mutate_genome,
    mutation_delta,
    serialize_genome,
)
from .wagner_ph_architecture_predictor import (
    fit_cross_fitted_predictor,
    verify_predictor,
)
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import (
    deserialize_genotype as deserialize_base_genotype,
    mutate_carrier,
)
from .wagner_ph_cooption_experiment import simulate_ecology_condition
from .wagner_ph_resilience_genome import deserialize_genome as deserialize_resilience_genome


DIAGNOSIS_FORMAT = f"{ARCHITECTURE_FORMAT}-diagnosis"
TRANSPLANT_CONDITIONS = tuple(
    f"carrier_{carrier}.topology_{topology}.repair_{repair}"
    for carrier in ("repair", "ordinary")
    for topology in ("repair", "ordinary")
    for repair in ("on", "off")
)
MEDIAN_CONDITIONS = ("median3_independent", "mean3_independent", "median3_concerted")


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _information(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: ArchitectureSpec,
    scope: str,
) -> float:
    rulebook, carrier = effective_genotype(genome)
    values = {
        intervention: simulate_ecology_condition(
            rulebook,
            task,
            carrier,
            kernel,
            intervention,
            spec.predictive_persistence,
            0.0,
            spec.diagnosis_futures_per_history,
            kernel.lineage_generations,
            (kernel.lineage_generations,),
            scope,
            master_seed=spec.diagnosis_seed,
        )
        for intervention in ("natural", "independent_history")
    }
    generation = str(kernel.lineage_generations)
    return float(
        values["natural"]["checkpoints"][generation]["correct_rate"]
        - values["independent_history"]["checkpoints"][generation]["correct_rate"]
    )


def _rank_final(population: dict[str, Any], count: int) -> list[dict[str, Any]]:
    return sorted(
        population["final_population"],
        key=lambda value: (-float(value["selection_score"]["fitness"]), str(value["genotype_id"])),
    )[:count]


def _fixed_repair_child(
    genome: Genome,
    strength: float,
    interpreter_random: np.random.Generator,
    carrier_random: np.random.Generator,
    spec: ArchitectureSpec,
) -> Genome:
    child = mutate_genome(
        genome, genome, "mh_repair_ordinary", interpreter_random, spec
    )
    carrier = mutate_carrier(
        genome[1], genome[1], "independent", carrier_random
    )
    return ArchitectureInterpreter(child[0].copies, "repair", strength), carrier


def _task_diagnosis(args: tuple[Any, ...]) -> dict[str, Any]:
    ordinary_text, repair_text, spec_value, kernel_value, output_text, digest = args
    ordinary_population, repair_population = read_json(Path(ordinary_text)), read_json(Path(repair_text))
    spec = ArchitectureSpec.from_dict(spec_value); kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(repair_population["population_index"])
    if task_index != int(ordinary_population["population_index"]):
        raise ValueError("diagnostic populations are not task paired")
    if canonical_digest(repair_population["task"]) != canonical_digest(
        ordinary_population["task"]
    ):
        raise ValueError("diagnostic populations do not share the same task")
    final_path = Path(output_text) / f"task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("architecture diagnosis registration differs")
    ordinary_roots = _rank_final(ordinary_population, spec.diagnosis_roots_per_task)
    repair_roots = _rank_final(repair_population, spec.diagnosis_roots_per_task)
    rows, roots = [], []
    for root_index, (ordinary_value, repair_value) in enumerate(zip(ordinary_roots, repair_roots)):
        ordinary_rulebook, ordinary_carrier = deserialize_base_genotype(ordinary_value)
        old_repair, repair_carrier = deserialize_resilience_genome(repair_value)
        repair_rulebook = old_repair.effective_rulebook()
        strength = float(old_repair.repair_strength)
        root_record = {
            "root_index": root_index,
            "ordinary_source": ordinary_value,
            "repair_source": repair_value,
            "evolved_repair_strength": strength,
            "conditions": [],
        }
        for carrier_name, carrier in (("repair", repair_carrier), ("ordinary", ordinary_carrier)):
            for topology_name, rulebook in (("repair", repair_rulebook), ("ordinary", ordinary_rulebook)):
                for repair_name, used_strength in (("on", strength), ("off", 0.0)):
                    condition = f"carrier_{carrier_name}.topology_{topology_name}.repair_{repair_name}"
                    root_genome = initialize_interpreter(rulebook, "repair", used_strength), carrier
                    root_scope = f"architecture-diagnosis.task-{task_index:03d}.root-{root_index:02d}.transplant"
                    root_information = _information(root_genome, repair_population["task"], kernel, spec, root_scope + ".distance-00")
                    chains = []
                    for lineage_index in range(spec.diagnosis_chains_per_root):
                        current, chain = root_genome, []
                        for distance in range(1, 5):
                            child = _fixed_repair_child(
                                current,
                                used_strength,
                                rng_for(spec.diagnosis_seed, "architecture-transplant-mutation", task_index, root_index, lineage_index, distance),
                                rng_for(spec.diagnosis_seed, "architecture-diagnostic-carrier-mutation", task_index, root_index, lineage_index, distance),
                                spec,
                            )
                            information = None
                            if distance in spec.pedigree_depths:
                                information = _information(child, repair_population["task"], kernel, spec, root_scope + f".lineage-{lineage_index:02d}.distance-{distance:02d}")
                                rows.append({
                                    "panel": "transplant",
                                    "condition": condition,
                                    "task_index": task_index,
                                    "root_index": root_index,
                                    "lineage_index": lineage_index,
                                    "distance": distance,
                                    "root_information": root_information,
                                    "descendant_information": information,
                                    "eligible_positive_root": root_information > 0.0,
                                    "retained": root_information > 0.0 and information >= spec.retention_fraction * root_information,
                                })
                            chain.append({
                                "distance": distance,
                                "genotype": serialize_genome(child),
                                "mutation_delta": mutation_delta(current, child),
                                "information": information,
                            })
                            current = child
                        chains.append({"lineage_index": lineage_index, "chain": chain})
                    root_record["conditions"].append({
                        "condition": condition,
                        "root": serialize_genome(root_genome),
                        "root_information": root_information,
                        "chains": chains,
                    })
        for condition in MEDIAN_CONDITIONS:
            architecture = "mean3" if condition.startswith("mean3") else "median3"
            arm = "mh_mean3_ordinary" if architecture == "mean3" else "mh_median3_ordinary"
            root_genome = initialize_interpreter(repair_rulebook, architecture), repair_carrier
            root_scope = f"architecture-diagnosis.task-{task_index:03d}.root-{root_index:02d}.decoder"
            root_information = _information(root_genome, repair_population["task"], kernel, spec, root_scope + ".distance-00")
            chains = []
            for lineage_index in range(spec.diagnosis_chains_per_root):
                current, chain = root_genome, []
                for distance in range(1, 5):
                    mechanism = "concerted" if condition.endswith("concerted") else "natural"
                    child = mutate_genome(
                        current,
                        current,
                        arm,
                        rng_for(spec.diagnosis_seed, "architecture-decoder-mutation", task_index, root_index, lineage_index, distance),
                        spec,
                        mechanism=mechanism,
                    )
                    child = (
                        child[0],
                        mutate_carrier(
                            current[1],
                            current[1],
                            "independent",
                            rng_for(
                                spec.diagnosis_seed,
                                "architecture-diagnostic-carrier-mutation",
                                task_index,
                                root_index,
                                lineage_index,
                                distance,
                            ),
                        ),
                    )
                    information = None
                    if distance in spec.pedigree_depths:
                        information = _information(child, repair_population["task"], kernel, spec, root_scope + f".lineage-{lineage_index:02d}.distance-{distance:02d}")
                        rows.append({
                            "panel": "decoder",
                            "condition": condition,
                            "task_index": task_index,
                            "root_index": root_index,
                            "lineage_index": lineage_index,
                            "distance": distance,
                            "root_information": root_information,
                            "descendant_information": information,
                            "eligible_positive_root": root_information > 0.0,
                            "retained": root_information > 0.0 and information >= spec.retention_fraction * root_information,
                        })
                    chain.append({
                        "distance": distance,
                        "genotype": serialize_genome(child),
                        "mutation_delta": mutation_delta(current, child),
                        "information": information,
                    })
                    current = child
                chains.append({"lineage_index": lineage_index, "chain": chain})
            root_record["conditions"].append({
                "condition": condition,
                "root": serialize_genome(root_genome),
                "root_information": root_information,
                "chains": chains,
            })
        roots.append(root_record)
    result = {
        "format": DIAGNOSIS_FORMAT,
        "protocol_digest": digest,
        "task_index": task_index,
        "task": repair_population["task"],
        "roots": roots,
        "rows": rows,
        "row_count": len(rows),
        "common_mutation_and_assay_streams_across_counterfactuals": True,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(final_path, result); return result


def _condition_summary(
    rows: list[dict[str, Any]],
    condition: str,
    distance: int,
    spec: ArchitectureSpec,
) -> dict[str, Any]:
    selected = [row for row in rows if row["condition"] == condition and row["distance"] == distance]
    task_values = {}
    for task_index in range(spec.task_count):
        eligible = [row for row in selected if row["task_index"] == task_index and row["eligible_positive_root"]]
        task_values[str(task_index)] = float(np.mean([row["retained"] for row in eligible])) if eligible else 0.0
    return {
        "task_retention": task_values,
        "interval": _interval(
            task_values.values(), spec.diagnosis_seed,
            f"architecture-diagnosis.{condition}.distance-{distance}",
            spec.bootstrap_repetitions, spec.interval_level,
        ),
    }


def _paired_contrast(
    summaries: dict[str, Any],
    left: str,
    right: str,
    distance: int,
    spec: ArchitectureSpec,
    label: str,
) -> dict[str, Any]:
    lvalues = summaries[left][str(distance)]["task_retention"]
    rvalues = summaries[right][str(distance)]["task_retention"]
    values = {key: float(lvalues[key]) - float(rvalues[key]) for key in lvalues}
    return {
        "task_values": values,
        "interval": _interval(values.values(), spec.diagnosis_seed, label, spec.bootstrap_repetitions, spec.interval_level),
    }


def _analysis(results: list[dict[str, Any]], predictor: dict[str, Any], spec: ArchitectureSpec) -> dict[str, Any]:
    rows = [row for value in results for row in value["rows"]]
    summaries = {
        condition: {
            str(distance): _condition_summary(rows, condition, distance, spec)
            for distance in spec.pedigree_depths
        }
        for condition in TRANSPLANT_CONDITIONS + MEDIAN_CONDITIONS
    }
    def factorial_for(carrier: str) -> dict[str, Any]:
        factorial = {}
        for distance in spec.pedigree_depths:
            prefix = f"carrier_{carrier}"
            repair_on_repair = f"{prefix}.topology_repair.repair_on"
            repair_off_repair = f"{prefix}.topology_repair.repair_off"
            repair_on_ordinary = f"{prefix}.topology_ordinary.repair_on"
            repair_off_ordinary = f"{prefix}.topology_ordinary.repair_off"
            repair_effect = _paired_contrast(
                summaries,
                repair_on_repair,
                repair_off_repair,
                distance,
                spec,
                f"architecture.factorial.{carrier}.repair.d{distance}",
            )
            topology_effect = _paired_contrast(
                summaries,
                repair_off_repair,
                repair_off_ordinary,
                distance,
                spec,
                f"architecture.factorial.{carrier}.topology.d{distance}",
            )
            interaction_values = {
                key: (
                    float(summaries[repair_on_repair][str(distance)]["task_retention"][key])
                    - float(summaries[repair_off_repair][str(distance)]["task_retention"][key])
                )
                - (
                    float(summaries[repair_on_ordinary][str(distance)]["task_retention"][key])
                    - float(summaries[repair_off_ordinary][str(distance)]["task_retention"][key])
                )
                for key in summaries[repair_on_repair][str(distance)]["task_retention"]
            }
            factorial[str(distance)] = {
                "repair_main_on_repair_topology": repair_effect,
                "topology_main_with_repair_off": topology_effect,
                "topology_by_repair_interaction": {
                    "task_values": interaction_values,
                    "interval": _interval(
                        interaction_values.values(),
                        spec.diagnosis_seed,
                        f"architecture.factorial.{carrier}.interaction.d{distance}",
                        spec.bootstrap_repetitions,
                        spec.interval_level,
                    ),
                },
            }
        return factorial
    decoder = {
        "median_minus_mean": {
            str(distance): _paired_contrast(summaries, "median3_independent", "mean3_independent", distance, spec, f"architecture.decoder.median-minus-mean.d{distance}")
            for distance in spec.pedigree_depths
        },
        "median_independent_minus_concerted": {
            str(distance): _paired_contrast(summaries, "median3_independent", "median3_concerted", distance, spec, f"architecture.decoder.independent-minus-concerted.d{distance}")
            for distance in spec.pedigree_depths
        },
    }
    result = {
        "format": f"{DIAGNOSIS_FORMAT}-analysis",
        "predictor": predictor,
        "condition_summaries": summaries,
        "primary_repair_carrier_factorial": factorial_for("repair"),
        "ordinary_carrier_sensitivity_factorial": factorial_for("ordinary"),
        "decoder_contrasts": decoder,
        "diagnostic_only": True,
    }
    result["analysis_digest"] = canonical_digest(result); return result


def run_architecture_diagnosis(
    spec: ArchitectureSpec,
    reference: Path,
    resilience: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    reference, resilience, destination = reference.resolve(), resilience.resolve(), destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_architecture_diagnosis(destination); return destination
    predictor = fit_cross_fitted_predictor(reference, spec)
    kernel = spec.kernel()
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "reference_checksum": sha256_file(reference / "SHA256SUMS"),
        "resilience_checksum": sha256_file(resilience / "SHA256SUMS"),
        "predictor_digest": predictor["predictor_digest"],
    }
    digest = canonical_digest(payload)
    registration = {
        "format": f"{DIAGNOSIS_FORMAT}-registration",
        "protocol_digest": digest,
        **payload,
        "reference": str(reference),
        "resilience": str(resilience),
        "predictor": predictor,
    }
    if (destination / "registration.json").is_file() and read_json(destination / "registration.json") != registration:
        raise ValueError("existing architecture diagnosis registration differs")
    if not (destination / "registration.json").is_file():
        _atomic_json(destination / "registration.json", registration)
    shards = destination / "tasks"; shards.mkdir(exist_ok=True)
    ordinary = sorted((reference / "development" / "evolution" / "populations").glob("individual_reset.population-*.json"))[: spec.task_count]
    repair = sorted((resilience / "development" / "evolution" / "populations").glob("lineage4_repair.population-*.json"))[: spec.task_count]
    if len(ordinary) != spec.task_count or len(repair) != spec.task_count:
        raise ValueError("architecture diagnosis source tasks are incomplete")
    work = [(str(a), str(b), spec.to_dict(), kernel.to_dict(), str(shards), digest) for a, b in zip(ordinary, repair)]
    started = time.monotonic(); completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_task_diagnosis, work); executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))
        futures = [executor.submit(_task_diagnosis, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, value in enumerate(iterator, 1):
            completed.append(value)
            _atomic_json(destination / "progress.json", {"completed_tasks": index, "total_tasks": len(work), "elapsed_seconds": time.monotonic() - started})
            if progress:
                progress(f"interpreter-architecture diagnosis {index}/{len(work)} tasks")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: value["task_index"])
    analysis = _analysis(completed, predictor, spec); _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "manifest.json", {
        "format": f"{DIAGNOSIS_FORMAT}-manifest",
        "protocol_digest": digest,
        "tasks": len(completed),
        "rows": sum(value["row_count"] for value in completed),
        "elapsed_seconds": time.monotonic() - started,
        "runtime": runtime_manifest(),
    })
    write_checksums(destination); verify_architecture_diagnosis(destination); return destination


def verify_architecture_diagnosis(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = ArchitectureSpec.from_dict(registration["spec"])
    if registration.get("format") != f"{DIAGNOSIS_FORMAT}-registration":
        raise ValueError("architecture diagnosis registration format mismatch")
    if manifest.get("format") != f"{DIAGNOSIS_FORMAT}-manifest":
        raise ValueError("architecture diagnosis manifest format mismatch")
    if sha256_file(Path(registration["reference"]) / "SHA256SUMS") != registration["reference_checksum"]:
        raise ValueError("sealed depth reference changed")
    if sha256_file(Path(registration["resilience"]) / "SHA256SUMS") != registration["resilience_checksum"]:
        raise ValueError("sealed resilience reference changed")
    payload = {key: registration[key] for key in ("spec", "kernel", "reference_checksum", "resilience_checksum", "predictor_digest")}
    if canonical_digest(payload) != registration["protocol_digest"] or manifest["protocol_digest"] != registration["protocol_digest"]:
        raise ValueError("architecture diagnosis protocol mismatch")
    verify_predictor(registration["predictor"])
    if registration["predictor"]["predictor_digest"] != registration["predictor_digest"]:
        raise ValueError("architecture diagnosis predictor mismatch")
    files = sorted((directory / "tasks").glob("task-*.json"))
    expected_rows = spec.task_count * spec.diagnosis_roots_per_task * spec.diagnosis_chains_per_root * len(spec.pedigree_depths) * (len(TRANSPLANT_CONDITIONS) + len(MEDIAN_CONDITIONS))
    values = [read_json(path) for path in files]
    rows = sum(value["row_count"] for value in values)
    for value in values:
        payload = dict(value)
        archived = payload.pop("result_digest", None)
        if (
            value.get("protocol_digest") != registration["protocol_digest"]
            or archived != canonical_digest(payload)
        ):
            raise ValueError("architecture diagnosis task digest mismatch")
    analysis = read_json(directory / "analysis.json")
    analysis_payload = dict(analysis)
    analysis_digest = analysis_payload.pop("analysis_digest", None)
    if analysis_digest != canonical_digest(analysis_payload):
        raise ValueError("architecture diagnosis analysis digest mismatch")
    if (
        len(files) != spec.task_count
        or rows != expected_rows
        or manifest["rows"] != expected_rows
        or manifest["tasks"] != spec.task_count
        or manifest["protocol_digest"] != registration["protocol_digest"]
    ):
        raise ValueError("architecture diagnosis is incomplete")
    return {"verified": True, "tasks": len(files), "rows": rows, "checksums": len(checksums)}
