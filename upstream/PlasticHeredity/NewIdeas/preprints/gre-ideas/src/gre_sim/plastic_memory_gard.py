"""Conditional, source-hashed GARD composition-transplant mirror."""

from __future__ import annotations

import collections
import concurrent.futures
import hashlib
import importlib.util
import math
import multiprocessing
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .artifacts import (
    canonical_digest,
    read_json,
    read_jsonl_gz,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
    write_jsonl_gz,
)
from .plastic_memory_protocols import GARD_MIRROR_SEED
from .rng import digest_parts, rng_for


_SIM_MODULE: Any | None = None
_SIM_PATH: str | None = None


def _resolve_sim_path(gard_root: Path) -> Path:
    root = gard_root.resolve()
    direct = root / "sim.py"
    candidates = [
        direct,
        root.parent / "replication" / "sim.py",
        root.parents[2] / "replicators.13.8.2026.fable" / "replication" / "sim.py"
        if len(root.parents) >= 3
        else direct,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "could not locate the frozen GARD replication/sim.py from " f"{gard_root}"
    )


def _load_sim(path: str | Path) -> Any:
    global _SIM_MODULE, _SIM_PATH
    resolved = str(Path(path).resolve())
    if _SIM_MODULE is not None and _SIM_PATH == resolved:
        return _SIM_MODULE
    module_name = "gre_plastic_memory_frozen_gard_sim"
    specification = importlib.util.spec_from_file_location(module_name, resolved)
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot load frozen GARD simulator: {resolved}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    _SIM_MODULE = module
    _SIM_PATH = resolved
    return module


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _normalize(value: np.ndarray) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    norm = float(np.linalg.norm(array))
    return array / max(norm, 1e-12)


def _meanfield_forms(beta: np.ndarray, sim: Any, seed: int) -> list[np.ndarray]:
    """Outcome-blind fast menu map, frozen for this mirror only."""

    rng = np.random.default_rng(seed)
    ends = []
    for _ in range(16):
        x = rng.dirichlet(np.ones(sim.NG))
        for _ in range(2000):
            bn = 1.0 + beta @ x
            join = sim.KF * sim.RHO * 60.0 * bn
            leave = sim.KB * 60.0 * x * bn
            velocity = (join - leave) - x * np.sum(join - leave)
            x = np.maximum(x + (2e-4 / max(float(np.max(np.abs(velocity))), 1e-12)) * velocity, 0.0)
            total = float(np.sum(x))
            if total <= 0.0:
                break
            x /= total
        if np.sum(x) > 0:
            endpoint = _normalize(x)
            if not any(float(endpoint @ form) >= 0.95 for form in ends):
                ends.append(endpoint)
    return ends


def _choose_forms(forms: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray] | None:
    candidates = []
    for left_index, left in enumerate(forms):
        for right in forms[left_index + 1 :]:
            similarity = float(left @ right)
            if similarity <= 0.85:
                candidates.append((similarity, left, right))
    if not candidates:
        return None
    _, left, right = min(candidates, key=lambda value: value[0])
    return left, right


def _composition_counts(form: np.ndarray, mass: int) -> np.ndarray:
    weights = np.maximum(np.asarray(form, dtype=float), 0.0)
    weights /= max(float(np.sum(weights)), 1e-12)
    raw = mass * weights
    counts = np.floor(raw).astype(np.int64)
    remainder = mass - int(np.sum(counts))
    if remainder:
        order = np.argsort(-(raw - counts), kind="stable")
        counts[order[:remainder]] += 1
    return counts


def _build_registry(
    sim_path: Path,
    count: int,
    seed_label: str,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    sim = _load_sim(sim_path)
    sources = []
    proposal = 0
    maximum = max(100_000, count * 1000)
    while len(sources) < count and proposal < maximum:
        beta = sim.make_beta(rng_for(GARD_MIRROR_SEED, seed_label, "beta", proposal))
        forms = _meanfield_forms(
            beta,
            sim,
            int(rng_for(GARD_MIRROR_SEED, seed_label, "menu", proposal).integers(2**32)),
        )
        pair = _choose_forms(forms)
        proposal += 1
        if pair is None:
            continue
        source_id = f"gard-{seed_label}.{len(sources):04d}"
        base = sim.make_initial_state(
            rng_for(GARD_MIRROR_SEED, seed_label, "base", proposal - 1)
        )
        permutation = rng_for(
            GARD_MIRROR_SEED, seed_label, "permutation", proposal - 1
        ).permutation(sim.NG)
        sources.append(
            {
                "source_id": source_id,
                "proposal_index": proposal - 1,
                "beta": beta.tolist(),
                "forms": [pair[0].tolist(), pair[1].tolist()],
                "base": base.tolist(),
                "permutation": permutation.tolist(),
            }
        )
        if progress is not None and len(sources) % 8 == 0:
            progress(f"mapped GARD forms {len(sources)}/{count}")
    if len(sources) != count:
        raise RuntimeError(
            f"mapped only {len(sources)}/{count} two-form GARD worlds after {proposal} proposals"
        )
    return {
        "format": "gre-plastic-memory-gard-registry-v1",
        "seed_label": seed_label,
        "accepted": count,
        "proposals": proposal,
        "sources": sources,
    }


def _replace_toward(
    state: np.ndarray,
    target: np.ndarray,
    fraction: float,
    rng: np.random.Generator,
) -> np.ndarray:
    current = np.asarray(state, dtype=np.int64).copy()
    mass = int(np.sum(current))
    amount = min(mass, max(1, int(round(fraction * mass))))
    removed = rng.multivariate_hypergeometric(current, amount)
    probabilities = np.maximum(np.asarray(target, dtype=float), 0.0)
    probabilities /= max(float(np.sum(probabilities)), 1e-12)
    added = rng.multinomial(amount, probabilities)
    return current - removed + added


def _train(
    source: dict[str, Any],
    sim: Any,
    candidate: str,
    history_index: int,
    fraction: float,
    dwell: int,
    future_index: int,
    seed_label: str,
) -> tuple[np.ndarray, bool]:
    beta = np.asarray(source["beta"], dtype=float)
    form = np.asarray(source["forms"][history_index], dtype=float)
    state = np.asarray(source["base"], dtype=np.int64).copy()
    acquired = False
    for cycle in range(dwell):
        cue_rng = rng_for(
            GARD_MIRROR_SEED,
            seed_label,
            source["source_id"],
            candidate,
            history_index,
            future_index,
            "cue",
            cycle,
        )
        state = _replace_toward(state, form, fraction, cue_rng)
        dynamics_rng = rng_for(
            GARD_MIRROR_SEED,
            seed_label,
            source["source_id"],
            candidate,
            history_index,
            future_index,
            "training",
            cycle,
        )
        trajectory = sim.run_fissions(state, beta, candidate, 1, dynamics_rng)
        state = np.asarray(trajectory["final"], dtype=np.int64)
        acquired = float(_normalize(state) @ _normalize(form)) > 0.90
    return state, acquired


def _force_break(state: np.ndarray, target: np.ndarray, opposite: np.ndarray) -> np.ndarray:
    current = np.asarray(state, dtype=np.int64).copy()
    mass = int(np.sum(current))
    opposite_counts = _composition_counts(opposite, mass)
    for fraction in (0.25, 0.50, 0.75, 1.0):
        amount = int(round(fraction * mass))
        candidate = current.copy()
        removal_order = np.argsort(-candidate, kind="stable")
        remaining = amount
        for index in removal_order:
            take = min(int(candidate[index]), remaining)
            candidate[index] -= take
            remaining -= take
            if remaining == 0:
                break
        addition = _composition_counts(opposite, amount)
        candidate += addition
        if float(_normalize(candidate) @ _normalize(target)) <= 0.85:
            return candidate
    return opposite_counts


def _summarize(
    trajectory: dict[str, Any], target: np.ndarray, wrong: np.ndarray, strict_run: int = 8
) -> dict[str, Any]:
    daughters = np.asarray(trajectory["daughters"], dtype=float)
    hs = np.asarray(trajectory["H"], dtype=float)
    target = _normalize(target)
    wrong = _normalize(wrong)
    if len(daughters):
        normalized = np.asarray([_normalize(row) for row in daughters])
        correct = normalized @ target > 0.90
        incorrect = normalized @ wrong > 0.90
    else:
        normalized = np.empty((0, len(target)))
        correct = np.zeros(0, dtype=bool)
        incorrect = np.zeros(0, dtype=bool)

    def maximum_hold(mask: np.ndarray, coherent: bool) -> int:
        maximum = 0
        run_start = 0
        for index, valid in enumerate(mask):
            if not valid or hs[index] <= 0.90:
                run_start = index + 1
                continue
            window = normalized[run_start : index + 1]
            if coherent and len(window) > 1 and float(np.min(window @ window.T)) <= 0.90:
                run_start = index
            maximum = max(maximum, index - run_start + 1)
        return maximum

    correct_run = maximum_hold(correct, True)
    wrong_run = maximum_hold(incorrect, True)
    generic_run = 0
    current = 0
    for inherited in hs > 0.90:
        current = current + 1 if inherited else 0
        generic_run = max(generic_run, current)
    destination = "other"
    for start in range(max(0, len(correct) - 2)):
        if bool(np.all(correct[start : start + 3])):
            destination = "correct"
            break
        if bool(np.all(incorrect[start : start + 3])):
            destination = "wrong"
            break
    return {
        "form_destination_relative": destination,
        "correct_hold_run": correct_run,
        "wrong_hold_run": wrong_run,
        "generic_hold_run": generic_run,
        "correct_hold8": correct_run >= strict_run,
        "wrong_hold8": wrong_run >= strict_run,
        "generic_hold8": generic_run >= strict_run,
        "returned": bool(np.any(correct)),
        "died": bool(trajectory["died"]),
        "n_done": int(trajectory["n_done"]),
    }


def _trajectory_digest(trajectory: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    daughters = np.ascontiguousarray(trajectory["daughters"])
    inheritance = np.ascontiguousarray(trajectory["H"])
    digest.update(str(daughters.dtype).encode("ascii"))
    digest.update(np.asarray(daughters.shape, dtype=np.int64).tobytes())
    digest.update(daughters.tobytes())
    digest.update(str(inheritance.dtype).encode("ascii"))
    digest.update(np.asarray(inheritance.shape, dtype=np.int64).tobytes())
    digest.update(inheritance.tobytes())
    digest.update(bytes((bool(trajectory["died"]),)))
    digest.update(int(trajectory["n_done"]).to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def _simulate_source(
    args: tuple[dict[str, Any], str, dict[str, Any]]
) -> list[dict[str, Any]]:
    source, sim_path, protocol = args
    sim = _load_sim(sim_path)
    beta = np.asarray(source["beta"], dtype=float)
    records: list[dict[str, Any]] = []
    seed_label = str(protocol["seed_label"])
    training_cache: dict[
        tuple[str, int, float, int, int], tuple[np.ndarray, bool]
    ] = {}
    if "conditions" in protocol:
        blocks = protocol["conditions"]
    else:
        blocks = [
            {
                "name": "legacy-grid",
                "carriers": protocol["carriers"],
                "washout_ages": protocol["washout_ages"],
                "challenges": protocol["challenges"],
                "futures_per_cell": protocol["futures_per_cell"],
            }
        ]
    for candidate in ("02", "03"):
        cue_doses = protocol.get("cue_by_candidate", {}).get(
            candidate, protocol.get("cue_doses", [])
        )
        for history_index, history in enumerate(("A", "B")):
            target = np.asarray(source["forms"][history_index], dtype=float)
            wrong = np.asarray(source["forms"][1 - history_index], dtype=float)
            for raw_fraction, raw_dwell in cue_doses:
                fraction = float(raw_fraction)
                dwell = int(raw_dwell)

                def trained(future_index: int) -> tuple[np.ndarray, bool]:
                    key = (candidate, history_index, fraction, dwell, future_index)
                    if key not in training_cache:
                        if protocol.get("writer_mode") == "exact_composition":
                            mass = int(np.sum(np.asarray(source["base"], dtype=np.int64)))
                            training_cache[key] = (
                                _composition_counts(form, mass),
                                True,
                            )
                        else:
                            training_cache[key] = _train(
                                source,
                                sim,
                                candidate,
                                history_index,
                                fraction,
                                dwell,
                                future_index,
                                seed_label,
                            )
                    state_value, acquired_value = training_cache[key]
                    return state_value.copy(), acquired_value

                for block in blocks:
                    block_name = str(block["name"])
                    futures_per_cell = int(block["futures_per_cell"])
                    for carrier in block["carriers"]:
                        for age_value in block["washout_ages"]:
                            age = int(age_value)
                            for challenge in block["challenges"]:
                                for future_index in range(futures_per_cell):
                                    state, acquired = trained(future_index)
                                    trained_state = state.copy()
                                    control_match_exact = True
                                    if carrier == "reset_both":
                                        state = np.asarray(
                                            source["base"], dtype=np.int64
                                        ).copy()
                                    elif carrier == "destination_matched_donor":
                                        half = futures_per_cell // 2
                                        start = 0 if future_index < half else half
                                        donor = start + (
                                            (future_index - start + 1) % half
                                        )
                                        control_match_exact = False
                                        for offset in range(1, half):
                                            candidate_index = start + (
                                                (future_index - start + offset) % half
                                            )
                                            candidate_state, _ = trained(candidate_index)
                                            similarity = float(
                                                _normalize(candidate_state)
                                                @ _normalize(target)
                                            )
                                            if similarity > 0.90:
                                                donor = candidate_index
                                                control_match_exact = True
                                                break
                                        state, _ = trained(donor)
                                    elif carrier == "state_pattern_shuffle":
                                        permutation = np.asarray(
                                            source["permutation"], dtype=np.int64
                                        )
                                        state = state[permutation]
                                        control_match_exact = not np.array_equal(
                                            state, trained_state
                                        )
                                    elif carrier not in {
                                        "self_continuation",
                                        "state_transplant",
                                    }:
                                        raise ValueError(carrier)
                                    if age:
                                        state = np.asarray(
                                            sim.run_fissions(
                                                state,
                                                beta,
                                                candidate,
                                                age,
                                                rng_for(
                                                    GARD_MIRROR_SEED,
                                                    seed_label,
                                                    source["source_id"],
                                                    candidate,
                                                    history,
                                                    future_index,
                                                    "washout",
                                                    age,
                                                ),
                                            )["final"],
                                            dtype=np.int64,
                                        )
                                    if challenge == "neutral_damage":
                                        state = _replace_toward(
                                            state,
                                            np.ones(sim.NG),
                                            0.20,
                                            rng_for(
                                                GARD_MIRROR_SEED,
                                                seed_label,
                                                source["source_id"],
                                                candidate,
                                                history,
                                                future_index,
                                                "damage",
                                                age,
                                            ),
                                        )
                                    elif challenge == "forced_break":
                                        state = _force_break(state, target, wrong)
                                    elif challenge != "release_only":
                                        raise ValueError(challenge)
                                    trajectory = sim.run_fissions(
                                        state,
                                        beta,
                                        candidate,
                                        int(protocol["horizon"]),
                                        rng_for(
                                            GARD_MIRROR_SEED,
                                            seed_label,
                                            source["source_id"],
                                            candidate,
                                            history,
                                            future_index,
                                            "post",
                                            age,
                                            challenge,
                                        ),
                                    )
                                    summary = _summarize(trajectory, target, wrong)
                                    relative = summary.pop(
                                        "form_destination_relative"
                                    )
                                    form_destination = (
                                        history
                                        if relative == "correct"
                                        else ("B" if history == "A" else "A")
                                        if relative == "wrong"
                                        else "other"
                                    )
                                    future_id = digest_parts(
                                        "gre-plastic-memory-gard-v1",
                                        seed_label,
                                        block_name,
                                        source["source_id"],
                                        candidate,
                                        history,
                                        fraction,
                                        dwell,
                                        carrier,
                                        age,
                                        challenge,
                                        future_index,
                                    )
                                    records.append(
                                        {
                                            "future_id": future_id,
                                            "condition": block_name,
                                            "source_id": source["source_id"],
                                            "model": f"gard-{candidate}",
                                            "candidate": candidate,
                                            "history": history,
                                            "cue_fraction": fraction,
                                            "cue_dwell": dwell,
                                            "writer_mode": protocol.get(
                                                "writer_mode", "replacement_cue"
                                            ),
                                            "carrier": carrier,
                                            "washout_age": age,
                                            "challenge": challenge,
                                            "future_index": future_index,
                                            "half": (
                                                "A"
                                                if future_index
                                                < futures_per_cell // 2
                                                else "B"
                                            ),
                                            "acquired": acquired,
                                            "control_match_exact": (
                                                control_match_exact
                                            ),
                                            "form_destination": form_destination,
                                            "trace_digest": (
                                                _trajectory_digest(trajectory)
                                                if carrier
                                                in {
                                                    "self_continuation",
                                                    "state_transplant",
                                                }
                                                else None
                                            ),
                                            **summary,
                                        }
                                    )
    records.sort(
        key=lambda value: (
            value["model"],
            value["condition"],
            value["history"],
            value["cue_fraction"],
            value["cue_dwell"],
            value["carrier"],
            value["washout_age"],
            value["challenge"],
            value["future_index"],
        )
    )
    return records


def _bootstrap(values: list[float], label: str, tests: int = 1) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if not len(array):
        return {"mean": None, "lower": None, "sources": 0}
    rng = rng_for(GARD_MIRROR_SEED, "gard-bootstrap", label)
    indices = rng.integers(0, len(array), size=(4096, len(array)))
    means = np.mean(array[indices], axis=1)
    return {
        "mean": float(np.mean(array)),
        "lower": float(np.quantile(means, 0.05 / max(1, tests))),
        "interval": [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))],
        "sources": len(array),
    }


def _analyze(records_path: Path, calibration: bool) -> dict[str, Any]:
    if calibration:
        grouped: dict[tuple[str, float, int, str], list[float]] = (
            collections.defaultdict(list)
        )
        source_totals: dict[tuple[str, float, int, str, str], list[float]] = collections.defaultdict(
            lambda: [0.0, 0.0]
        )
        record_count = 0
        for record in read_jsonl_gz(records_path):
            record_count += 1
            key = (
                record["model"],
                record["cue_fraction"],
                record["cue_dwell"],
                record["history"],
                record["source_id"],
            )
            source_totals[key][0] += float(record["acquired"])
            source_totals[key][1] += 1.0
        for key, value in source_totals.items():
            grouped[key[:4]].append(value[0] / value[1])
        rates = {
            f"{model}.cue-{fraction:g}x{dwell}.history-{history}": _bootstrap(
                values, f"calibration.{model}.{fraction}.{dwell}.{history}"
            )
            for (model, fraction, dwell, history), values in grouped.items()
        }
        selected = {}
        for model in ("gard-02", "gard-03"):
            candidates = []
            for fraction, dwell in {(key[1], key[2]) for key in grouped if key[0] == model}:
                means = {
                    history: rates[f"{model}.cue-{fraction:g}x{dwell}.history-{history}"]["mean"]
                    for history in ("A", "B")
                }
                if min(means.values()) >= 0.80 and abs(means["A"] - means["B"]) <= 0.10:
                    candidates.append((fraction * dwell, fraction, dwell, means))
            selected[model] = (
                {"ready": False, "cue": None}
                if not candidates
                else {
                    "ready": True,
                    "cue": {
                        "fraction": min(candidates, key=lambda value: value[:3])[1],
                        "dwell": min(candidates, key=lambda value: value[:3])[2],
                    },
                }
            )
        return {
            "format": "gre-plastic-memory-gard-calibration-v1",
            "record_count": record_count,
            "rates": rates,
            "selection": selected,
        }

    RateKey = tuple[str, str, str, int, str, str]
    DestinationKey = tuple[str, str, str, str]
    source_rates: dict[RateKey, list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    destinations: dict[DestinationKey, collections.Counter[str]] = (
        collections.defaultdict(collections.Counter)
    )
    equivalence_pairs: dict[tuple[Any, ...], dict[str, str]] = {}
    control_matches: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    record_count = 0
    for record in read_jsonl_gz(records_path):
        record_count += 1
        model = str(record["model"])
        source = str(record["source_id"])
        carrier = str(record["carrier"])
        age = int(record["washout_age"])
        challenge = str(record["challenge"])
        half = str(record["half"])
        rate = source_rates[(model, source, carrier, age, challenge, half)]
        rate[0] += float(record["correct_hold8"])
        rate[1] += 1.0
        if carrier == "state_transplant" and age == 0 and challenge == "neutral_damage":
            destinations[(model, source, str(record["history"]), half)][
                str(record["form_destination"])
            ] += 1
        if carrier in {"self_continuation", "state_transplant"}:
            key = (
                record["condition"],
                model,
                source,
                record["history"],
                age,
                challenge,
                record["future_index"],
            )
            equivalence_pairs.setdefault(key, {})[carrier] = str(
                record["trace_digest"]
            )
        if carrier in {"destination_matched_donor", "state_pattern_shuffle"}:
            values = control_matches[carrier]
            values[0] += int(bool(record["control_match_exact"]))
            values[1] += 1

    complete_pairs = [value for value in equivalence_pairs.values() if len(value) == 2]
    pair_matches = sum(
        value["self_continuation"] == value["state_transplant"]
        for value in complete_pairs
    )
    equivalence = {
        "pairs": len(complete_pairs),
        "matches": pair_matches,
        "equal": bool(complete_pairs) and pair_matches == len(complete_pairs),
    }

    def carrier_rate(
        model: str,
        source: str,
        carrier: str,
        age: int,
        challenge: str,
        half: str | None = None,
    ) -> float | None:
        selected_halves = (half,) if half is not None else ("A", "B")
        values = [
            source_rates.get((model, source, carrier, age, challenge, item))
            for item in selected_halves
        ]
        if any(value is None or value[1] == 0 for value in values):
            return None
        return float(
            sum(value[0] for value in values if value is not None)
            / sum(value[1] for value in values if value is not None)
        )

    def crossfit_gain(model: str, source: str) -> float | None:
        categories = ("A", "B", "other")
        gains = []
        for mapping_half, evaluation_half in (("A", "B"), ("B", "A")):
            mapping = {
                history: destinations.get(
                    (model, source, history, mapping_half), collections.Counter()
                )
                for history in ("A", "B")
            }
            evaluation = {
                history: destinations.get(
                    (model, source, history, evaluation_half), collections.Counter()
                )
                for history in ("A", "B")
            }
            if not all(
                sum(mapping[history].values())
                and sum(evaluation[history].values())
                for history in ("A", "B")
            ):
                continue
            pooled = mapping["A"] + mapping["B"]
            baseline = {
                category: (pooled[category] + 0.5)
                / (sum(pooled.values()) + 1.5)
                for category in categories
            }
            loss = 0.0
            base_loss = 0.0
            observations = 0
            for history in ("A", "B"):
                probability = {
                    category: (mapping[history][category] + 0.5)
                    / (sum(mapping[history].values()) + 1.5)
                    for category in categories
                }
                for category, amount in evaluation[history].items():
                    loss += -math.log(probability[category]) * amount
                    base_loss += -math.log(baseline[category]) * amount
                    observations += amount
            if observations:
                gains.append((base_loss - loss) / observations)
        return float(np.mean(gains)) if gains else None

    gates: dict[str, Any] = {}
    persistence: dict[str, Any] = {}
    for model in ("gard-02", "gard-03"):
        sources = sorted(
            {
                source
                for candidate_model, source, carrier, age, challenge, _half in source_rates
                if candidate_model == model
                and carrier in {"state_transplant", "reset_both"}
                and age == 0
                and challenge == "neutral_damage"
            }
        )
        risks: list[float] = []
        crossovers: list[float] = []
        gains: list[float] = []
        reliable_halves: list[tuple[float, float]] = []
        for source in sources:
            transferred = carrier_rate(
                model, source, "state_transplant", 0, "neutral_damage"
            )
            baseline = carrier_rate(model, source, "reset_both", 0, "neutral_damage")
            if transferred is None or baseline is None:
                continue
            probabilities: dict[tuple[str, str], float] = {}
            valid = True
            for history in ("A", "B"):
                counts = (
                    destinations.get((model, source, history, "A"), collections.Counter())
                    + destinations.get((model, source, history, "B"), collections.Counter())
                )
                total = sum(counts.values())
                if not total:
                    valid = False
                    break
                for destination in ("A", "B"):
                    probabilities[(history, destination)] = counts[destination] / total
            gain = crossfit_gain(model, source)
            left = carrier_rate(
                model, source, "state_transplant", 0, "neutral_damage", "A"
            )
            right = carrier_rate(
                model, source, "state_transplant", 0, "neutral_damage", "B"
            )
            if not valid or gain is None or left is None or right is None:
                continue
            risks.append(transferred - baseline)
            crossovers.append(
                0.5
                * (
                    probabilities[("A", "A")]
                    - probabilities[("B", "A")]
                    + probabilities[("B", "B")]
                    - probabilities[("A", "B")]
                )
            )
            gains.append(gain)
            reliable_halves.append((left, right))
        if len(reliable_halves) < 3:
            reliability = None
        else:
            left_values, right_values = np.asarray(reliable_halves, dtype=float).T
            if np.std(left_values) == 0.0 or np.std(right_values) == 0.0:
                reliability = (
                    1.0 if np.array_equal(left_values, right_values) else 0.0
                )
            else:
                reliability = float(np.corrcoef(left_values, right_values)[0, 1])
        metrics = {
            "risk_difference": _bootstrap(risks, f"{model}.risk", 6),
            "crossover": _bootstrap(crossovers, f"{model}.crossover", 6),
            "log_loss_gain": _bootstrap(gains, f"{model}.gain", 6),
        }
        criteria = {
            "risk_difference_at_least_0_05": (
                metrics["risk_difference"]["mean"] is not None
                and metrics["risk_difference"]["mean"] >= 0.05
            ),
            "risk_difference_lower_above_zero": (
                metrics["risk_difference"]["lower"] is not None
                and metrics["risk_difference"]["lower"] > 0
            ),
            "crossover_at_least_0_05": (
                metrics["crossover"]["mean"] is not None
                and metrics["crossover"]["mean"] >= 0.05
            ),
            "crossover_lower_above_zero": (
                metrics["crossover"]["lower"] is not None
                and metrics["crossover"]["lower"] > 0
            ),
            "log_loss_gain_at_least_0_02": (
                metrics["log_loss_gain"]["mean"] is not None
                and metrics["log_loss_gain"]["mean"] >= 0.02
            ),
            "log_loss_gain_lower_above_zero": (
                metrics["log_loss_gain"]["lower"] is not None
                and metrics["log_loss_gain"]["lower"] > 0
            ),
            "split_half_reliability_at_least_0_80": (
                reliability is not None and reliability >= 0.80
            ),
            "self_transplant_equivalence": equivalence["equal"],
        }
        gates[model] = {
            "metrics": metrics,
            "split_half_reliability": reliability,
            "criteria": criteria,
            "passed": all(criteria.values()),
        }
        for age in (0, 1, 2, 4, 8):
            for challenge in ("release_only", "neutral_damage", "forced_break"):
                values = []
                for source in sorted(
                    {key[1] for key in source_rates if key[0] == model}
                ):
                    transferred = carrier_rate(
                        model, source, "state_transplant", age, challenge
                    )
                    baseline = carrier_rate(
                        model, source, "reset_both", age, challenge
                    )
                    if transferred is not None and baseline is not None:
                        values.append(transferred - baseline)
                if values:
                    label = f"{model}.age-{age}.{challenge}"
                    persistence[label] = _bootstrap(values, f"persistence.{label}")
    return {
        "format": "gre-plastic-memory-gard-confirmation-v1",
        "record_count": record_count,
        "gates": gates,
        "persistence": persistence,
        "self_transplant_equivalence": equivalence,
        "control_match_rates": {
            carrier: values[0] / values[1]
            for carrier, values in sorted(control_matches.items())
            if values[1]
        },
    }


def _run_stage(
    sim_path: Path,
    destination: Path,
    registry: dict[str, Any],
    protocol: dict[str, Any],
    workers: int,
    progress: Callable[[str], None] | None,
) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_checksums(destination)
        return destination
    started = time.monotonic()
    progress_path = destination / "progress.json"
    prior_elapsed = 0.0
    if progress_path.is_file():
        try:
            prior_elapsed = max(
                0.0, float(read_json(progress_path).get("elapsed_seconds", 0.0))
            )
        except (OSError, ValueError, TypeError):
            prior_elapsed = 0.0
    protocol_digest = canonical_digest(protocol)
    registration = {"protocol": protocol, "digest": protocol_digest}
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing GARD mirror stage registration differs")
    else:
        _atomic_json(registration_path, registration)
    registry_path = destination / "rulebooks.json"
    if registry_path.is_file():
        if canonical_digest(read_json(registry_path)) != canonical_digest(registry):
            raise ValueError("existing GARD mirror registry differs")
    else:
        _atomic_json(registry_path, registry)

    if "conditions" in protocol:
        blocks = protocol["conditions"]
    else:
        blocks = [
            {
                "carriers": protocol["carriers"],
                "washout_ages": protocol["washout_ages"],
                "challenges": protocol["challenges"],
                "futures_per_cell": protocol["futures_per_cell"],
            }
        ]
    per_history = sum(
        len(block["carriers"])
        * len(block["washout_ages"])
        * len(block["challenges"])
        * int(block["futures_per_cell"])
        for block in blocks
    )
    cue_count = sum(
        len(
            protocol.get("cue_by_candidate", {}).get(
                candidate, protocol.get("cue_doses", [])
            )
        )
        for candidate in ("02", "03")
    )
    expected = len(registry["sources"]) * 2 * cue_count * per_history
    expected_per_source = 2 * cue_count * per_history
    shards = destination / "shards"
    shards.mkdir(exist_ok=True)
    completed: set[str] = set()
    completed_records = 0
    for source in registry["sources"]:
        source_id = str(source["source_id"])
        shard = shards / f"{source_id}.jsonl.gz"
        shard_manifest = shards / f"{source_id}.manifest.json"
        if not shard.is_file() or not shard_manifest.is_file():
            continue
        try:
            value = read_json(shard_manifest)
            valid = (
                value.get("source_id") == source_id
                and value.get("protocol_digest") == protocol_digest
                and value.get("sha256") == sha256_file(shard)
                and int(value.get("record_count", -1)) == expected_per_source
            )
        except (OSError, ValueError, TypeError):
            valid = False
        if valid:
            completed.add(source_id)
            completed_records += int(value["record_count"])
    pending = [
        source
        for source in registry["sources"]
        if source["source_id"] not in completed
    ]
    if progress is not None:
        progress(
            f"GARD mirror resume: {len(completed)}/{len(registry['sources'])} "
            f"worlds, {completed_records:,}/{expected:,} futures sealed"
        )
    args = [(source, str(sim_path), protocol) for source in pending]
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        active: dict[int, concurrent.futures.Future[list[dict[str, Any]]]] = {}
        next_submit = 0
        window = max(workers, workers * 2)
        while next_submit < min(window, len(args)):
            active[next_submit] = executor.submit(
                _simulate_source, args[next_submit]
            )
            next_submit += 1
        for index, source in enumerate(pending):
            records = active.pop(index).result()
            source_id = str(source["source_id"])
            shard = shards / f"{source_id}.jsonl.gz"
            temporary = shards / f".{source_id}.jsonl.gz.tmp"
            count = write_jsonl_gz(temporary, records)
            if count != expected_per_source:
                raise RuntimeError(
                    f"GARD world {source_id} produced {count} records; "
                    f"expected {expected_per_source}"
                )
            temporary.replace(shard)
            _atomic_json(
                shards / f"{source_id}.manifest.json",
                {
                    "format": "gre-plastic-memory-gard-shard-v1",
                    "source_id": source_id,
                    "protocol_digest": protocol_digest,
                    "record_count": count,
                    "sha256": sha256_file(shard),
                },
            )
            completed.add(source_id)
            completed_records += count
            elapsed_now = prior_elapsed + time.monotonic() - started
            records_per_second = completed_records / max(elapsed_now, 1e-9)
            _atomic_json(
                progress_path,
                {
                    "format": "gre-plastic-memory-gard-progress-v1",
                    "completed_worlds": len(completed),
                    "total_worlds": len(registry["sources"]),
                    "completed_records": completed_records,
                    "expected_records": expected,
                    "elapsed_seconds": elapsed_now,
                    "records_per_second": records_per_second,
                    "eta_seconds": (
                        (expected - completed_records) / records_per_second
                        if records_per_second > 0
                        else None
                    ),
                },
            )
            if progress is not None:
                progress(
                    f"checkpointed GARD mirror world "
                    f"{len(completed)}/{len(registry['sources'])}"
                )
            if next_submit < len(args):
                active[next_submit] = executor.submit(
                    _simulate_source, args[next_submit]
                )
                next_submit += 1

    def merged():
        for source in registry["sources"]:
            yield from read_jsonl_gz(shards / f"{source['source_id']}.jsonl.gz")

    futures_path = destination / "futures.jsonl.gz"
    temporary_futures = destination / ".futures.jsonl.gz.tmp"
    count = write_jsonl_gz(temporary_futures, merged())
    temporary_futures.replace(futures_path)
    if count != expected or completed_records != expected:
        raise RuntimeError(
            f"GARD mirror produced {count:,} records; expected {expected:,}"
        )
    analysis = _analyze(futures_path, protocol["calibration"])
    if int(analysis["record_count"]) != expected:
        raise RuntimeError("GARD mirror streaming analysis count disagrees")
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": "gre-plastic-memory-gard-manifest-v1",
            "record_count": count,
            "expected_record_count": expected,
            "worlds": len(registry["sources"]),
            "elapsed_seconds": prior_elapsed + time.monotonic() - started,
            "protocol_digest": protocol_digest,
            "runtime": runtime_manifest(),
        },
    )
    (destination / "report.md").write_text(
        "# GARD composition-transplant mirror\n\n"
        + ("> Cue calibration only.\n" if protocol["calibration"] else "> Fresh conditional confirmation.\n"),
        encoding="utf-8",
    )
    write_checksums(destination)
    return destination


def run_gard_memory_mirror(
    gard_root: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    sim_path = _resolve_sim_path(gard_root)
    sim = _load_sim(sim_path)
    # Frozen simulator smoke fixture.
    beta = sim.make_beta(np.random.default_rng(1))
    initial = sim.make_initial_state(np.random.default_rng(2))
    fixture = sim.run_fissions(initial, beta, "02", 2, np.random.default_rng(3))
    if fixture["n_done"] != 2:
        raise AssertionError("frozen GARD simulator fixture failed")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_checksums(destination)
        return destination
    provenance = {
        "format": "gre-plastic-memory-gard-provenance-v1",
        "gard_root": str(gard_root.resolve()),
        "sim_path": str(sim_path),
        "sim_sha256": sha256_file(sim_path),
        "source_access": "read-only",
    }
    provenance_path = destination / "provenance.json"
    if provenance_path.is_file() and read_json(provenance_path) != provenance:
        raise ValueError("GARD mirror source provenance changed")
    if not provenance_path.is_file():
        _atomic_json(provenance_path, provenance)

    calibration_registry_path = destination / "calibration-registry.json"
    if calibration_registry_path.is_file():
        calibration_registry = read_json(calibration_registry_path)
    else:
        calibration_registry = _build_registry(sim_path, 32, "calibration", progress)
        _atomic_json(calibration_registry_path, calibration_registry)
    calibration_protocol = {
        "format": "gre-plastic-memory-gard-protocol-v1",
        "seed_label": "calibration",
        "calibration": True,
        "cue_doses": [
            [fraction, dwell]
            for fraction in (0.25, 0.50, 0.75, 1.0)
            for dwell in (1, 4, 16)
        ],
        "carriers": ["state_transplant"],
        "washout_ages": [0],
        "challenges": ["release_only"],
        "futures_per_cell": 16,
        "horizon": 8,
    }
    calibration = _run_stage(
        sim_path,
        destination / "calibration",
        calibration_registry,
        calibration_protocol,
        workers,
        progress,
    )
    selection = read_json(calibration / "analysis.json")["selection"]
    _atomic_json(destination / "cue-selection.json", selection)
    if not all(value["ready"] for value in selection.values()):
        _atomic_json(
            destination / "manifest.json",
            {"completed": True, "stopped_at": "gard-cue-calibration"},
        )
        write_checksums(destination)
        return destination
    confirmation_registry_path = destination / "confirmation-registry.json"
    if confirmation_registry_path.is_file():
        confirmation_registry = read_json(confirmation_registry_path)
    else:
        confirmation_registry = _build_registry(sim_path, 200, "confirmation", progress)
        _atomic_json(confirmation_registry_path, confirmation_registry)
    confirmation_protocol = {
        "format": "gre-plastic-memory-gard-protocol-v1",
        "seed_label": "confirmation",
        "calibration": False,
        "cue_by_candidate": {
            candidate.removeprefix("gard-"): [
                [value["cue"]["fraction"], value["cue"]["dwell"]]
            ]
            for candidate, value in selection.items()
        },
        "conditions": [
            {
                "name": "gard-state-primary",
                "carriers": [
                    "self_continuation",
                    "state_transplant",
                    "reset_both",
                    "destination_matched_donor",
                    "state_pattern_shuffle",
                ],
                "washout_ages": [0],
                "challenges": ["neutral_damage"],
                "futures_per_cell": 128,
            },
            {
                "name": "gard-state-recurrence",
                "carriers": ["state_transplant", "reset_both"],
                "washout_ages": [0],
                "challenges": ["forced_break"],
                "futures_per_cell": 128,
            },
            {
                "name": "gard-state-persistence",
                "carriers": ["state_transplant", "reset_both"],
                "washout_ages": [1, 2, 4, 8],
                "challenges": [
                    "release_only",
                    "neutral_damage",
                    "forced_break",
                ],
                "futures_per_cell": 64,
            },
        ],
        "horizon": 32,
    }
    confirmation = _run_stage(
        sim_path,
        destination / "confirmation",
        confirmation_registry,
        confirmation_protocol,
        workers,
        progress,
    )
    analysis = read_json(confirmation / "analysis.json")
    manifest = {
        "format": "gre-plastic-memory-gard-root-manifest-v1",
        "completed": True,
        "stopped_at": None,
        "candidate_gates": analysis["gates"],
        "general_gard_transfer": all(value["passed"] for value in analysis["gates"].values()),
    }
    _atomic_json(destination / "manifest.json", manifest)
    (destination / "report.md").write_text(
        "# Conditional GARD plastic-memory mirror\n\n"
        f"- Candidate 02 passed: {analysis['gates']['gard-02']['passed']}\n"
        f"- Candidate 03 passed: {analysis['gates']['gard-03']['passed']}\n"
        f"- General GARD transfer: {manifest['general_gard_transfer']}\n",
        encoding="utf-8",
    )
    write_checksums(destination)
    return destination


def replay_gard_memory_future(directory: Path, future_id: str) -> dict[str, Any]:
    """Recompute one archived GARD future from its semantic coordinates."""

    directory = directory.resolve()
    verify_checksums(directory)
    archived = next(
        (
            record
            for record in read_jsonl_gz(directory / "futures.jsonl.gz")
            if record["future_id"] == future_id
        ),
        None,
    )
    if archived is None:
        raise KeyError(f"unknown GARD plastic-memory future: {future_id}")
    registration = read_json(directory / "registration.json")
    protocol = dict(registration["protocol"])
    registry = read_json(directory / "rulebooks.json")
    source = next(
        value
        for value in registry["sources"]
        if value["source_id"] == archived["source_id"]
    )
    provenance = read_json(directory.parent / "provenance.json")
    sim_path = Path(provenance["sim_path"])
    if sha256_file(sim_path) != provenance["sim_sha256"]:
        raise ValueError("frozen GARD simulator hash changed")
    if "conditions" in protocol:
        original = next(
            value
            for value in protocol["conditions"]
            if value["name"] == archived["condition"]
        )
    else:
        original = {
            "name": "legacy-grid",
            "futures_per_cell": protocol["futures_per_cell"],
        }
    candidate = str(archived["candidate"])
    narrowed = {
        **protocol,
        "cue_by_candidate": {
            "02": [],
            "03": [],
            candidate: [
                [archived["cue_fraction"], archived["cue_dwell"]]
            ],
        },
        "conditions": [
            {
                "name": archived["condition"],
                "carriers": [archived["carrier"]],
                "washout_ages": [archived["washout_age"]],
                "challenges": [archived["challenge"]],
                "futures_per_cell": original["futures_per_cell"],
            }
        ],
    }
    replayed = next(
        record
        for record in _simulate_source((source, str(sim_path), narrowed))
        if record["future_id"] == future_id
    )
    fields = (
        "acquired",
        "form_destination",
        "correct_hold_run",
        "wrong_hold_run",
        "generic_hold_run",
        "correct_hold8",
        "returned",
        "died",
        "n_done",
        "trace_digest",
    )
    return {
        "future_id": future_id,
        "matches": all(archived[field] == replayed[field] for field in fields),
        "archived": {field: archived[field] for field in fields},
        "replayed": {field: replayed[field] for field in fields},
    }
