"""Untouched causal, state-transplant, and pedigree audit for origin v1."""

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
    read_jsonl_gz,
    runtime_manifest,
    verify_checksums,
    write_checksums,
    write_json,
    write_jsonl_gz,
)
from .local_ph_config import LocalConditionSpec
from .rng import rng_for
from .wagner_ph_bridge_evolution import (
    _deserialize_genotype,
    _mutate_genotype,
    _serialize_genotype,
)
from .wagner_ph_origin_analysis import (
    analyze_origin_audit,
    render_origin_audit_report,
)
from .wagner_ph_origin_config import (
    EXPLICIT_TREATMENTS,
    ORIGIN_AUDIT_FORMAT,
    ORIGIN_TREATMENTS,
    OriginAuditSpec,
    OriginEvolutionSpec,
    treatment_objective,
)
from .wagner_ph_origin_evolution import (
    _risk,
    assay_origin_genotype,
    verify_origin_evolution,
)


AUDIT_REGISTRATION_FORMAT = "gre-wagner-ph-origin-audit-registration-v1"
AUDIT_MANIFEST_FORMAT = "gre-wagner-ph-origin-audit-manifest-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _primary_conditions(treatment: str) -> tuple[str, str]:
    if treatment_objective(treatment) == "passive_locked":
        return "candidate.renewal-off", "candidate.harsher-renewal-off"
    return "candidate.intact", "candidate.harsher"


def _heldout_metrics(
    assay: dict[str, Any], founder: dict[str, Any], treatment: str
) -> dict[str, Any]:
    selected_condition, harsher_condition = _primary_conditions(treatment)
    return {
        "primary_condition": selected_condition,
        "selected_g8": _risk(assay, selected_condition, 8),
        "selected_g12": _risk(assay, selected_condition, 12),
        "selected_g16": _risk(assay, selected_condition, 16),
        "harsher_g8": _risk(assay, harsher_condition, 8),
        "renewal_contrast_g8": _risk(
            assay, "candidate.intact", 8, "correct_rate"
        )
        - _risk(assay, "candidate.renewal-off", 8, "correct_rate"),
        "founder_g8": _risk(founder, selected_condition, 8),
    }


def _causal_conditions(spec: OriginEvolutionSpec) -> tuple[LocalConditionSpec, ...]:
    noise = spec.selected_noise.name
    values = (
        ("candidate.intact", "intact"),
        ("candidate.founder-write-off", "founder_write_off"),
        ("candidate.reader-off", "reader_off"),
        ("candidate.renewal-off", "renewal_off"),
        ("candidate.renewal-block-g1-g4", "renewal_block_g1_g4"),
        ("candidate.renewal-block-g9-g12", "renewal_block_g9_g12"),
        ("candidate.shuffle", "shuffle"),
        ("candidate.erase-g6", "erase_g6"),
        ("candidate.erase-g6-rescue-g7", "erase_g6_rescue_g7"),
        ("candidate.opposite-history-transplant", "opposite_history_transplant"),
    )
    return tuple(
        [
            LocalConditionSpec(name, "candidate", intervention, noise, name == "candidate.intact")
            for name, intervention in values
        ]
        + [LocalConditionSpec("zero", None, "zero", noise)]
    )


def _pedigree_conditions(spec: OriginEvolutionSpec) -> tuple[LocalConditionSpec, ...]:
    noise = spec.selected_noise.name
    return (
        LocalConditionSpec("candidate.intact", "candidate", "intact", noise, True),
        LocalConditionSpec(
            "candidate.renewal-off", "candidate", "renewal_off", noise
        ),
        LocalConditionSpec("zero", None, "zero", noise),
    )


def _causal_metrics(assay: dict[str, Any]) -> dict[str, float]:
    def correct(condition: str, generation: int) -> float:
        return _risk(assay, condition, generation, "correct_rate")

    intact_g8 = correct("candidate.intact", 8)
    intact_g12 = correct("candidate.intact", 12)
    zero_g8 = correct("zero", 8)
    erased = correct("candidate.erase-g6", 8)
    rescued = correct("candidate.erase-g6-rescue-g7", 8)
    erase_denominator = intact_g8 - zero_g8
    rescue_denominator = intact_g8 - erased
    return {
        "founder_write_off_g8": intact_g8
        - correct("candidate.founder-write-off", 8),
        "reader_off_g8": intact_g8 - correct("candidate.reader-off", 8),
        "renewal_off_g8": intact_g8 - correct("candidate.renewal-off", 8),
        "renewal_block_g1_g4_g8": intact_g8
        - correct("candidate.renewal-block-g1-g4", 8),
        "renewal_block_g9_g12_g12": intact_g12
        - correct("candidate.renewal-block-g9-g12", 12),
        "shuffle_g8": intact_g8 - correct("candidate.shuffle", 8),
        "erasure_reduction_g8": (intact_g8 - erased) / erase_denominator
        if erase_denominator > 0.0
        else 0.0,
        "rescue_fraction_g8": (rescued - erased) / rescue_denominator
        if rescue_denominator > 0.0
        else 0.0,
        "donor_following_g0": _risk(
            assay,
            "candidate.opposite-history-transplant",
            0,
            "wrong_rate",
        )
        - _risk(assay, "candidate.intact", 0, "wrong_rate"),
    }


def _quantile_parent_indices(population: list[dict[str, Any]], count: int) -> list[int]:
    ordered = sorted(
        range(len(population)),
        key=lambda index: (
            float(population[index]["training_score"]["fitness"]),
            str(population[index]["genotype_id"]),
        ),
    )
    positions = np.rint(np.linspace(0, len(ordered) - 1, count)).astype(int)
    return [ordered[int(position)] for position in positions]


def _pedigree_score(
    genotype: tuple[Any, Any],
    archived: dict[str, Any],
    evolution: OriginEvolutionSpec,
    audit: OriginAuditSpec,
    source_id: str,
    label: str,
) -> tuple[float, float]:
    assay = assay_origin_genotype(
        *genotype,
        archived["task"],
        evolution,
        source_id,
        label,
        audit.futures_per_history,
        (0, 8),
        ("forced_break",),
        master_seed=audit.master_seed,
        conditions_override=_pedigree_conditions(evolution),
    )
    score = _risk(assay, "candidate.intact", 8)
    contrast = _risk(assay, "candidate.intact", 8, "correct_rate") - _risk(
        assay, "candidate.renewal-off", 8, "correct_rate"
    )
    return score, contrast


def _pedigree_rows(
    archived: dict[str, Any],
    evolution: OriginEvolutionSpec,
    audit: OriginAuditSpec,
) -> list[dict[str, Any]]:
    treatment = str(archived["treatment"])
    if treatment not in EXPLICIT_TREATMENTS:
        return []
    population_index = int(archived["population_index"])
    rows: list[dict[str, Any]] = []
    indices = _quantile_parent_indices(
        archived["final_population"], audit.parents_per_population
    )
    for parent_rank, parent_index in enumerate(indices):
        parent_item = archived["final_population"][parent_index]
        root = _deserialize_genotype(parent_item)
        source_id = (
            f"origin-pedigree.population-{population_index:03d}.parent-{parent_rank:02d}"
        )
        root_score, root_contrast = _pedigree_score(
            root,
            archived,
            evolution,
            audit,
            source_id,
            f"{source_id}.root",
        )
        for child_index in range(audit.children_per_parent):
            random = rng_for(
                audit.master_seed,
                "origin-pedigree-child",
                treatment,
                population_index,
                parent_rank,
                child_index,
            )
            child = _mutate_genotype(root, root, random)
            child_serialized = _serialize_genotype(*child)
            child_score, child_contrast = _pedigree_score(
                child,
                archived,
                evolution,
                audit,
                source_id,
                f"{source_id}.child-{child_index:02d}",
            )
            retained_child = child_score >= audit.retention_fraction * max(
                root_score, 0.0
            ) and child_contrast > 0.0
            rows.append(
                {
                    "population_id": archived["population_id"],
                    "population_index": population_index,
                    "treatment": treatment,
                    "root_parent_rank": parent_rank,
                    "child_index": child_index,
                    "grandchild_index": None,
                    "pedigree_generation": 1,
                    "root_genotype_id": parent_item["genotype_id"],
                    "immediate_parent_genotype_id": parent_item["genotype_id"],
                    "descendant_genotype_id": child_serialized["genotype_id"],
                    "root_score": root_score,
                    "root_renewal_contrast": root_contrast,
                    "immediate_parent_score": root_score,
                    "immediate_parent_renewal_contrast": root_contrast,
                    "descendant_score": child_score,
                    "descendant_renewal_contrast": child_contrast,
                    "retained_from_immediate": retained_child,
                    "retained_from_root": retained_child,
                    "common_stream_id": source_id,
                }
            )
            for grandchild_index in range(audit.grandchildren_per_child):
                grand_random = rng_for(
                    audit.master_seed,
                    "origin-pedigree-grandchild",
                    treatment,
                    population_index,
                    parent_rank,
                    child_index,
                    grandchild_index,
                )
                grandchild = _mutate_genotype(child, child, grand_random)
                grandchild_serialized = _serialize_genotype(*grandchild)
                grandchild_score, grandchild_contrast = _pedigree_score(
                    grandchild,
                    archived,
                    evolution,
                    audit,
                    source_id,
                    f"{source_id}.child-{child_index:02d}.grandchild-{grandchild_index:02d}",
                )
                rows.append(
                    {
                        "population_id": archived["population_id"],
                        "population_index": population_index,
                        "treatment": treatment,
                        "root_parent_rank": parent_rank,
                        "child_index": child_index,
                        "grandchild_index": grandchild_index,
                        "pedigree_generation": 2,
                        "root_genotype_id": parent_item["genotype_id"],
                        "immediate_parent_genotype_id": child_serialized[
                            "genotype_id"
                        ],
                        "descendant_genotype_id": grandchild_serialized[
                            "genotype_id"
                        ],
                        "root_score": root_score,
                        "root_renewal_contrast": root_contrast,
                        "immediate_parent_score": child_score,
                        "immediate_parent_renewal_contrast": child_contrast,
                        "descendant_score": grandchild_score,
                        "descendant_renewal_contrast": grandchild_contrast,
                        "retained_from_immediate": grandchild_score
                        >= audit.retention_fraction * max(child_score, 0.0)
                        and grandchild_contrast > 0.0,
                        "retained_from_root": grandchild_score
                        >= audit.retention_fraction * max(root_score, 0.0)
                        and grandchild_contrast > 0.0,
                        "common_stream_id": source_id,
                    }
                )
    return rows


def _compute_audit_population(
    archived: dict[str, Any],
    evolution: OriginEvolutionSpec,
    audit: OriginAuditSpec,
) -> dict[str, Any]:
    treatment = str(archived["treatment"])
    population_index = int(archived["population_index"])
    selected = _deserialize_genotype(archived["selected"])
    founder = _deserialize_genotype(archived["founder"])
    source_id = f"origin-heldout.population-{population_index:03d}"
    selected_common = assay_origin_genotype(
        *selected,
        archived["task"],
        evolution,
        source_id,
        f"{source_id}.{treatment}.selected",
        audit.futures_per_history,
        audit.checkpoint_generations,
        audit.challenges,
        master_seed=audit.master_seed,
    )
    founder_common = assay_origin_genotype(
        *founder,
        archived["task"],
        evolution,
        source_id,
        f"{source_id}.{treatment}.founder",
        audit.futures_per_history,
        audit.checkpoint_generations,
        audit.challenges,
        master_seed=audit.master_seed,
    )
    full_causal = treatment in EXPLICIT_TREATMENTS
    causal_assay = None
    causal_metrics = None
    if full_causal:
        causal_assay = assay_origin_genotype(
            *selected,
            archived["task"],
            evolution,
            source_id,
            f"{source_id}.{treatment}.causal",
            audit.futures_per_history,
            audit.checkpoint_generations,
            audit.challenges,
            master_seed=audit.master_seed,
            conditions_override=_causal_conditions(evolution),
        )
        causal_metrics = _causal_metrics(causal_assay)
    pedigree = _pedigree_rows(archived, evolution, audit)
    result = {
        "format": ORIGIN_AUDIT_FORMAT,
        "population_id": archived["population_id"],
        "population_index": population_index,
        "treatment": treatment,
        "full_causal_panel": full_causal,
        "common_heldout_source_id": source_id,
        "common_streams_verified": source_id
        == f"origin-heldout.population-{population_index:03d}",
        "descendants_receive_no_inducing_cue": True,
        "selected_writer_active": selected[1].write_rate > 0.0,
        "selected_reader_active": selected[1].coupling > 0.0,
        "selected_common": selected_common,
        "founder_common": founder_common,
        "causal_assay": causal_assay,
        "causal_metrics": causal_metrics,
        "pedigree_rows": pedigree,
        **_heldout_metrics(selected_common, founder_common, treatment),
    }
    result["audit_digest"] = canonical_digest(
        {
            "selected": selected_common,
            "founder": founder_common,
            "causal": causal_assay,
            "pedigree": pedigree,
        }
    )
    return result


def _audit_task(
    args: tuple[str, str, dict[str, Any], dict[str, Any], str]
) -> dict[str, Any]:
    archive_text, output_text, evolution_value, audit_value, protocol_digest = args
    archive_path = Path(archive_text)
    output = Path(output_text)
    final_path = output / archive_path.name
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"origin audit registration differs: {final_path}")
    evolution = OriginEvolutionSpec.from_dict(evolution_value)
    audit = OriginAuditSpec.from_dict(audit_value)
    result = _compute_audit_population(read_json(archive_path), evolution, audit)
    result["protocol_digest"] = protocol_digest
    _atomic_json(final_path, result)
    return result


def run_origin_audit(
    evolution_directory: Path,
    audit: OriginAuditSpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    audit.validate()
    if workers < 1 or workers > 4:
        raise ValueError("origin audit permits one to four workers")
    evolution_directory = evolution_directory.resolve()
    verify_origin_evolution(evolution_directory)
    evolution_registration = read_json(evolution_directory / "registration.json")
    evolution = OriginEvolutionSpec.from_dict(evolution_registration["protocol"])
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_origin_audit(destination)
        return destination
    digest = canonical_digest(
        {"evolution": evolution.to_dict(), "audit": audit.to_dict()}
    )
    registration = {
        "format": AUDIT_REGISTRATION_FORMAT,
        "protocol_digest": digest,
        "evolution_protocol": evolution.to_dict(),
        "evolution_protocol_digest": evolution_registration["protocol_digest"],
        "audit_protocol": audit.to_dict(),
        "heldout_seed_is_untouched": True,
        "full_causal_treatments": list(EXPLICIT_TREATMENTS),
        "population_is_inferential_unit": True,
        "pedigree_branching": "four roots times two children times two grandchildren",
        "descendants_receive_no_inducing_cue": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and canonical_digest(
        read_json(registration_path)
    ) != canonical_digest(registration):
        raise ValueError("existing origin audit registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    units = destination / "populations"
    units.mkdir(exist_ok=True)
    archives = [
        evolution_directory / "populations" / f"{treatment}.population-{index:03d}.json"
        for treatment in ORIGIN_TREATMENTS
        for index in range(evolution.populations_per_treatment)
    ]
    tasks = [
        (str(path), str(units), evolution.to_dict(), audit.to_dict(), digest)
        for path in archives
    ]
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    executor: concurrent.futures.ProcessPoolExecutor | None = None
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_audit_task, tasks)
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        iterator = executor.map(_audit_task, tasks)
    try:
        for index, result in enumerate(iterator, start=1):
            results.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": "gre-wagner-ph-origin-audit-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"origin causal/pedigree audit {index}/{len(tasks)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    pedigree_rows = [row for value in results for row in value["pedigree_rows"]]
    write_jsonl_gz(destination / "pedigree.jsonl.gz", pedigree_rows)
    analysis = analyze_origin_audit(results, pedigree_rows, evolution, audit)
    _atomic_json(destination / "analysis.json", analysis)
    (destination / "report.md").write_text(
        render_origin_audit_report(analysis), encoding="utf-8"
    )
    _atomic_json(
        destination / "manifest.json",
        {
            "format": AUDIT_MANIFEST_FORMAT,
            "protocol_digest": digest,
            "population_count": len(results),
            "expected_population_count": evolution.population_count,
            "pedigree_row_count": len(pedigree_rows),
            "expected_pedigree_row_count": len(EXPLICIT_TREATMENTS)
            * evolution.populations_per_treatment
            * audit.parents_per_population
            * audit.children_per_parent
            * (1 + audit.grandchildren_per_child),
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_origin_audit(destination)
    return destination


def verify_origin_audit(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != AUDIT_REGISTRATION_FORMAT:
        raise ValueError("origin audit registration format mismatch")
    if manifest.get("format") != AUDIT_MANIFEST_FORMAT:
        raise ValueError("origin audit manifest format mismatch")
    evolution = OriginEvolutionSpec.from_dict(registration["evolution_protocol"])
    audit = OriginAuditSpec.from_dict(registration["audit_protocol"])
    digest = canonical_digest(
        {"evolution": evolution.to_dict(), "audit": audit.to_dict()}
    )
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("origin audit protocol digest mismatch")
    files = list((directory / "populations").glob("*.json"))
    if len(files) != evolution.population_count or int(manifest["population_count"]) != evolution.population_count:
        raise ValueError("origin audit population count mismatch")
    expected_rows = (
        len(EXPLICIT_TREATMENTS)
        * evolution.populations_per_treatment
        * audit.parents_per_population
        * audit.children_per_parent
        * (1 + audit.grandchildren_per_child)
    )
    rows = list(read_jsonl_gz(directory / "pedigree.jsonl.gz"))
    if len(rows) != expected_rows or int(manifest["pedigree_row_count"]) != expected_rows:
        raise ValueError("origin audit pedigree row count mismatch")
    archived_rows: list[dict[str, Any]] = []
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"origin audit population digest mismatch: {path.name}")
        expected = canonical_digest(
            {
                "selected": value["selected_common"],
                "founder": value["founder_common"],
                "causal": value["causal_assay"],
                "pedigree": value["pedigree_rows"],
            }
        )
        if value.get("audit_digest") != expected:
            raise ValueError(f"origin audit digest mismatch: {path.name}")
        archived_rows.extend(value["pedigree_rows"])
    def pedigree_key(value: dict[str, Any]) -> tuple[Any, ...]:
        return (
            str(value["treatment"]),
            int(value["population_index"]),
            int(value["root_parent_rank"]),
            int(value["child_index"]),
            int(value["pedigree_generation"]),
            -1
            if value["grandchild_index"] is None
            else int(value["grandchild_index"]),
        )

    if canonical_digest(sorted(rows, key=pedigree_key)) != canonical_digest(
        sorted(archived_rows, key=pedigree_key)
    ):
        raise ValueError("origin audit aggregate pedigree differs from population archives")
    return {
        "verified": True,
        "populations": evolution.population_count,
        "pedigree_rows": expected_rows,
        "checksums": len(checksums),
    }


def replay_origin_audit_population(
    directory: Path, population_id: str
) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    evolution = OriginEvolutionSpec.from_dict(registration["evolution_protocol"])
    audit = OriginAuditSpec.from_dict(registration["audit_protocol"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    evolution_archive = (
        directory.parent / "evolution" / "populations" / f"{population_id}.json"
    )
    if not evolution_archive.is_file():
        raise FileNotFoundError(
            f"origin replay requires sibling evolution archive: {evolution_archive}"
        )
    regenerated = _compute_audit_population(
        read_json(evolution_archive), evolution, audit
    )
    return {
        "population_id": population_id,
        "matches": archived.get("audit_digest") == regenerated["audit_digest"],
        "archived_digest": archived.get("audit_digest"),
        "regenerated_digest": regenerated["audit_digest"],
        "protocol_digest": canonical_digest(
            {"evolution": evolution.to_dict(), "audit": audit.to_dict()}
        ),
    }
