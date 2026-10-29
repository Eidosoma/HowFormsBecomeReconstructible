"""Positive-control-first, one-boundary R transmission in the original sheet.

Historical dynamics are imported read-only. Only experiment orchestration,
paired randomness, boundary controls and measurements are new.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import numpy as np

from .io import (
    atomic_json, atomic_text, canonical_digest, environment_manifest, external_root,
    git_head, require_beneath, sha256_file, utc_now, write_hash_manifest,
)


RUN_ID = "l17_r_channel_one_boundary_v1_attempt1"
SEED_TAG = "l17-r-channel-one-boundary-v1"
TISSUES = tuple(range(10000, 10008))
WORKERS = 4
MESSAGES = 4
ARMS = ("copy", "reset", "wrong", "shuffle", "copy_reader_off", "reset_reader_off", "fragment_copy", "fragment_reset")
PACKAGES = ("blueprint_web", "ladder_web", "voltage_web", "growing_web", "setpoint_rewrite", "contract_bridge", "glider_test", "xeno_bridge", "error_threshold")


@dataclass(frozen=True)
class ExperimentConfig:
    replicates: int = 8
    settle_sweeps: int = 120
    imprint_sweeps: int = 1000
    render_sweeps: int = 500
    child_sweeps: int = 1000
    sample_times: tuple[int, ...] = (0, 50, 250, 500, 1000)


CONFIG = ExperimentConfig()
REGISTERED_CHILD_LIVES = len(TISSUES) * CONFIG.replicates * MESSAGES * (len(ARMS) + 2)


def sources_root() -> Path:
    return Path(__file__).resolve().parents[3]


def source_api() -> dict:
    for package in PACKAGES:
        directory = str(sources_root() / package / "src")
        if directory not in sys.path:
            sys.path.insert(0, directory)
    from blueprint_web.config import BlueprintConfig
    from blueprint_web.engine import blueprint_step
    from error_threshold.config import EigenConfig
    from ladder_web.config import LadderConfig
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import tissue_config
    from voltage_web.engine import fission, launch_pattern, make_thresholds
    return locals()


def array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    h = hashlib.sha256(f"{array.dtype}:{array.shape}:".encode())
    h.update(array.tobytes())
    return h.hexdigest()


def state_digest(state: dict[str, np.ndarray]) -> str:
    return canonical_digest({k: array_digest(v) for k, v in state.items()})


def state_copy(state: dict) -> dict:
    return {k: v.copy() for k, v in state.items()}


def seed(tissue: int, phase: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{SEED_TAG}:{tissue}:{phase}".encode()).digest()[:16], "little")


class MessageCoupledRNG:
    """Eight marginal replicate streams, shared across all message labels.

    This adapter only exposes draws used by the frozen sheet and its fission.
    An arm/message label cannot enter its seed; phase/tissue identify events.
    """

    def __init__(self, tissue: int, phase: str, replicates: int):
        self.generator = np.random.default_rng(seed(tissue, phase))
        self.replicates = replicates

    def standard_normal(self, shape):
        shape = tuple(shape)
        if shape[0] != MESSAGES * self.replicates:
            raise ValueError("unexpected message-coupled batch shape")
        base = self.generator.standard_normal((self.replicates, *shape[1:]))
        return np.tile(base, (MESSAGES, *([1] * (base.ndim - 1))))

    def integers(self, low, high, size):
        if size != MESSAGES * self.replicates:
            raise ValueError("unexpected message-coupled integer shape")
        return np.tile(self.generator.integers(low, high, self.replicates), MESSAGES)

    def digest(self):
        return canonical_digest(self.generator.bit_generator.state)


def codebook(height=16, width=16) -> np.ndarray:
    if width != 16 or height != 16:
        raise ValueError("registered codebook requires the native 16x16 sheet")
    base = np.tile(np.where((np.arange(width) * 4 // width) % 2 == 0, 1., -1.), (height, 1))
    return np.stack([np.roll(base, shift, axis=1) for shift in (0, 2, 4, 6)])


def labels(replicates: int) -> np.ndarray:
    return np.repeat(np.arange(MESSAGES), replicates)


def decode(fields: np.ndarray, codes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scores = np.einsum("bhw,mhw->bm", fields, codes) / codes[0].size
    winners = np.abs(scores - scores.max(axis=1, keepdims=True)) <= 1e-12
    probabilities = winners / winners.sum(axis=1, keepdims=True)
    return scores, probabilities


def message_independent(fields: np.ndarray, replicates: int) -> bool:
    grouped = fields.reshape(MESSAGES, replicates, *fields.shape[1:])
    return all(np.array_equal(grouped[0], grouped[m]) for m in range(1, MESSAGES))


def measure_field(field: np.ndarray, target: np.ndarray) -> dict:
    positive, desired, active = field > 0, target > 0, np.abs(field) > .2
    p_target = float(desired.mean())
    expected = np.where(positive, p_target, 1. - p_target)
    return {
        "sign_fidelity": float((positive == desired).mean()),
        "amplitude_fidelity": float(((positive == desired) & active).mean()),
        "sign_marginal_null": float(expected.mean()),
        "amplitude_marginal_null": float((expected * active).mean()),
    }


def measure_state(state: dict, codes: np.ndarray, replicates: int, timepoint: int,
                  ancestor: np.ndarray | None = None, fresh: np.ndarray | None = None) -> list[dict]:
    true_labels = labels(replicates)
    scores_v, probabilities_v = decode(state["V"], codes)
    scores_r, probabilities_r = decode(state["R"], codes)
    rows = []
    for index, (message, v, reference) in enumerate(zip(true_labels, state["V"], state["R"])):
        row = {
            "message": int(message), "replicate": index % replicates, "sweep": timepoint,
            "body_scores": scores_v[index].tolist(), "body_probabilities": probabilities_v[index].tolist(),
            "reference_scores": scores_r[index].tolist(), "reference_probabilities": probabilities_r[index].tolist(),
            "body_accuracy": float(probabilities_v[index, message]),
            "reference_accuracy": float(probabilities_r[index, message]),
            "wrong_donor_body_accuracy": float(probabilities_v[index, (message + 1) % MESSAGES]),
            "intended_pattern": measure_field(v, codes[message]),
            "positive_fraction": float((v > 0).mean()), "active_fraction": float((np.abs(v) > .2).mean()),
            "body_mean": float(v.mean()), "body_rms": float(np.sqrt(np.mean(v * v))),
            "reference_mean": float(reference.mean()), "reference_rms": float(np.sqrt(np.mean(reference * reference))),
            "reference_l2_norm": float(np.linalg.norm(reference)),
            "body_sha256": array_digest(v), "reference_sha256": array_digest(reference),
        }
        if ancestor is not None:
            row["rendered_parent"] = measure_field(v, ancestor[index])
        if fresh is not None:
            mask = fresh[index]
            row["regrown_cells"] = int(mask.sum())
            row["regrown_intended_pattern"] = measure_field(v[mask], codes[message][mask])
            if ancestor is not None:
                row["regrown_rendered_parent"] = measure_field(v[mask], ancestor[index][mask])
        rows.append(row)
    return rows


def make_context(tissue_index: int, config: ExperimentConfig) -> dict:
    api = source_api()
    rewrite = api["RewriteConfig"]()
    tissue = api["tissue_config"](tissue_index, rewrite.coupling_band, rewrite)
    return {"index": tissue_index, "config": config, "tissue": tissue,
            "theta": api["make_thresholds"](tissue), "bp": api["BlueprintConfig"](),
            "ladder": api["LadderConfig"](), "codes": codebook(tissue.height, tissue.width), "api": api}


def simulate(context: dict, initial: dict, phase: str, sweeps: int, *,
             sample_times: tuple = (), c_m: float | None = None, rho: float | None = None,
             instruction: np.ndarray | None = None) -> dict:
    config = context["config"]
    rng = MessageCoupledRNG(context["index"], phase, config.replicates)
    state = state_copy(initial)
    input_digest = state_digest(initial)
    rng_initial = rng.digest()
    bp = context["bp"] if rho is None else replace(context["bp"], rho=rho)
    snapshots = {0: state_copy(state)} if 0 in sample_times else {}
    for step in range(1, sweeps + 1):
        v = state["V"] if instruction is None else instruction.copy()
        v, ema, reference = context["api"]["blueprint_step"](
            v, state["ema"], state["R"], context["theta"], context["tissue"],
            context["ladder"], bp, "T", rng, c_m=c_m,
        )
        state = {"V": v, "ema": ema, "R": reference}
        if step in sample_times:
            snapshots[step] = state_copy(state)
    gates = {"inputs_unchanged": input_digest == state_digest(initial),
             "finite_final_state": all(np.isfinite(v).all() for v in state.values()),
             "finite_snapshots": all(np.isfinite(v).all() for s in snapshots.values() for v in s.values())}
    if not all(gates.values()):
        raise RuntimeError(f"simulation structural failure: {gates}")
    return {"final": state, "snapshots": snapshots, "initial_sha256": input_digest,
            "final_sha256": state_digest(state), "rng_initial_sha256": rng_initial,
            "rng_final_sha256": rng.digest(), "gates": gates}


def trajectory_digest(trajectory: dict) -> str:
    return canonical_digest({"snapshots": {str(t): state_digest(s) for t, s in trajectory["snapshots"].items()},
                             **{k: v for k, v in trajectory.items() if k not in ("snapshots", "final")}})


def naive_body(context: dict, phase: str) -> dict:
    config, tissue = context["config"], context["tissue"]
    rng = MessageCoupledRNG(context["index"], phase + "_jitter", config.replicates)
    v = np.tile(context["api"]["launch_pattern"](0, tissue), (MESSAGES * config.replicates, 1, 1))
    v += tissue.copy_jitter * rng.standard_normal(v.shape)
    initial = {"V": v, "ema": v.copy(), "R": v.copy()}
    result = simulate(context, initial, phase + "_settle", config.settle_sweeps)["final"]
    if not all(message_independent(a, config.replicates) for a in result.values()):
        raise RuntimeError("naive body contains message identity")
    return result


def teach_parent(context: dict) -> dict:
    before = naive_body(context, "parent_birth")
    config = context["config"]
    instruction = np.repeat(context["codes"], config.replicates, axis=0) * 1.2
    imprinted = simulate(context, before, "parent_imprint", config.imprint_sweeps, instruction=instruction)["final"]
    rendered = simulate(context, imprinted, "parent_render", config.render_sweeps)["final"]
    return {"before_instruction": before, "after_instruction": imprinted, "after_render": rendered}


def fragment_boundary(context: dict, parent: dict) -> tuple[np.ndarray, np.ndarray]:
    rng = MessageCoupledRNG(context["index"], "fragment_boundary", context["config"].replicates)
    preview = deepcopy(rng)
    v, tissue = parent["V"], context["tissue"]
    axes, sides = preview.integers(0, 2, len(v)), preview.integers(0, 2, len(v))
    fresh = np.ones(v.shape, dtype=bool)
    for b, (axis, side) in enumerate(zip(axes, sides)):
        if axis == 0:
            rows = slice(0, tissue.height // 2) if side == 0 else slice(tissue.height // 2, None)
            fresh[b, rows, :] = False
        else:
            cols = slice(0, tissue.width // 2) if side == 0 else slice(tissue.width // 2, None)
            fresh[b, :, cols] = False
    # Source fission, not a reimplementation; preview only identifies the mask.
    offspring = context["api"]["fission"](v.copy(), tissue, rng)
    return offspring, fresh


def boundary_states(context: dict, parent: dict, newborn: dict) -> tuple[dict, np.ndarray]:
    config = context["config"]
    reference = parent["R"]
    wrong = np.roll(reference.reshape(MESSAGES, config.replicates, 16, 16), -1, axis=0).reshape(reference.shape).copy()
    shuffled = np.empty_like(reference)
    shuffle_rng = np.random.default_rng(seed(context["index"], "reference_shuffle"))
    for replicate in range(config.replicates):
        permutation = shuffle_rng.permutation(16 * 16)
        for message in range(MESSAGES):
            i = message * config.replicates + replicate
            shuffled[i] = reference[i].ravel()[permutation].reshape(16, 16)
    fragment, fresh = fragment_boundary(context, parent)
    states = {}
    for arm in ARMS:
        state = state_copy(newborn)
        if arm.startswith("fragment"):
            state["V"], state["ema"] = fragment.copy(), fragment.copy()
        if arm in ("copy", "copy_reader_off", "fragment_copy"):
            state["R"] = reference.copy()
        elif arm == "wrong":
            state["R"] = wrong.copy()
        elif arm == "shuffle":
            state["R"] = shuffled.copy()
        states[arm] = state
    if not all(np.array_equal(np.sort(shuffled[i].ravel()), np.sort(reference[i].ravel())) for i in range(len(reference))):
        raise RuntimeError("shuffle changed reference content histogram")
    return states, fresh


def trajectory_rows(context: dict, trajectory: dict, ancestor=None, fresh=None) -> list[dict]:
    return [row for t, state in trajectory["snapshots"].items()
            for row in measure_state(state, context["codes"], context["config"].replicates, t, ancestor, fresh)]


def summarize_rows(rows: list[dict]) -> dict:
    summary = {}
    for t in sorted({r["sweep"] for r in rows}):
        selected = [r for r in rows if r["sweep"] == t]
        confusion = np.zeros((MESSAGES, MESSAGES))
        for message in range(MESSAGES):
            confusion[message] = np.mean([r["body_probabilities"] for r in selected if r["message"] == message], axis=0)
        summary[str(t)] = {"observations": len(selected),
                           **{k: float(np.mean([r[k] for r in selected])) for k in ("body_accuracy", "reference_accuracy", "wrong_donor_body_accuracy", "active_fraction")},
                           "body_confusion_probabilities": confusion.tolist()}
    return summary


def atomic_npz(path: Path, arrays: dict, root: Path) -> None:
    path = require_beneath(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            np.savez_compressed(handle, **arrays)
        os.replace(temporary, path)
    except Exception:
        os.unlink(temporary)
        raise


def trajectory_arrays(trajectory: dict) -> dict:
    return {f"s{t}_{name}": array for t, state in trajectory["snapshots"].items() for name, array in state.items()}


def calibration(context: dict) -> tuple[dict, dict, dict]:
    body = naive_body(context, "fresh_body_birth")
    body_digest = state_digest(body)
    initial = state_copy(body)
    initial["R"] = np.repeat(context["codes"], context["config"].replicates, axis=0) * 3.
    settings = {"sample_times": context["config"].sample_times, "rho": 0.}
    positive = simulate(context, initial, "child_development", context["config"].child_sweeps, **settings)
    disabled = simulate(context, initial, "child_development", context["config"].child_sweeps, c_m=0., **settings)
    replay = simulate(context, initial, "child_development", context["config"].child_sweeps, **settings)
    summaries = {arm: summarize_rows(trajectory_rows(context, trajectory)) for arm, trajectory in (("injected", positive), ("injected_reader_off", disabled))}
    final = str(context["config"].child_sweeps)
    gates = {
        "positive_exact_replay": trajectory_digest(positive) == trajectory_digest(replay),
        "newborn_unchanged": body_digest == state_digest(body),
        "reader_off_message_independent": all(message_independent(s["V"], context["config"].replicates) for s in disabled["snapshots"].values()),
        "reader_off_exact_chance": all(s["body_accuracy"] == .25 for s in summaries["injected_reader_off"].values()),
        "streams_match": positive["rng_final_sha256"] == disabled["rng_final_sha256"],
        "injected_reference_held_exactly": all(np.array_equal(s["R"], initial["R"]) for s in positive["snapshots"].values()),
    }
    result = {"tissue": context["index"], "summaries": summaries, "structural_gates": gates,
              "passes": all(gates.values()), "positive_accuracy": summaries["injected"][final]["body_accuracy"],
              "newborn_sha256": body_digest,
              "trajectory_sha256": {"injected": trajectory_digest(positive), "injected_reader_off": trajectory_digest(disabled)}}
    return result, body, {"injected": positive, "injected_reader_off": disabled}


def calibration_qualified(results: list[dict]) -> bool:
    return (len(results) == len(TISSUES) and sorted(r["tissue"] for r in results) == list(TISSUES)
            and all(r["passes"] and r["positive_accuracy"] > .25 for r in results)
            and float(np.mean([r["positive_accuracy"] for r in results])) >= .75)


def acquired_experiment(context: dict, newborn: dict) -> tuple[dict, dict, dict, np.ndarray]:
    parents = teach_parent(context)
    source_digest = canonical_digest({k: state_digest(v) for k, v in parents.items()})
    newborn_digest = state_digest(newborn)
    states, fresh = boundary_states(context, parents["after_render"], newborn)
    initial_hashes = {a: state_digest(s) for a, s in states.items()}
    config = context["config"]
    trajectories = {}
    for arm in ARMS:
        trajectories[arm] = simulate(context, states[arm], "child_development", config.child_sweeps,
                                     sample_times=config.sample_times, c_m=0. if arm.endswith("reader_off") else None)
    replay = simulate(context, states["copy"], "child_development", config.child_sweeps, sample_times=config.sample_times)
    rows = {a: trajectory_rows(context, tr, parents["after_render"]["V"], fresh if a.startswith("fragment") else None)
            for a, tr in trajectories.items()}
    summaries = {a: summarize_rows(r) for a, r in rows.items()}
    gates = {
        "copy_exact_replay": trajectory_digest(trajectories["copy"]) == trajectory_digest(replay),
        "parents_unchanged": source_digest == canonical_digest({k: state_digest(v) for k, v in parents.items()}),
        "newborn_unchanged": newborn_digest == state_digest(newborn),
        "birth_states_unchanged": initial_hashes == {a: state_digest(s) for a, s in states.items()},
        "fresh_bodies_exactly_matched": all(np.array_equal(states[a][k], newborn[k]) for a in ARMS[:6] for k in ("V", "ema")),
        "fragment_bodies_exactly_matched": all(np.array_equal(states["fragment_copy"][k], states["fragment_reset"][k]) for k in ("V", "ema")),
        "all_development_streams_exact": len({t["rng_final_sha256"] for t in trajectories.values()}) == 1,
        "reader_off_body_alias": all(np.array_equal(trajectories["copy_reader_off"]["snapshots"][t][k], trajectories["reset_reader_off"]["snapshots"][t][k])
                                     for t in config.sample_times for k in ("V", "ema")),
        "null_message_independence": all(message_independent(trajectories[a]["snapshots"][t]["V"], config.replicates)
                                         for a in ("reset", "copy_reader_off", "reset_reader_off") for t in config.sample_times),
        "null_exact_chance": all(summaries[a][str(t)]["body_accuracy"] == .25
                                for a in ("reset", "copy_reader_off", "reset_reader_off") for t in config.sample_times),
        "wrong_donor_bijection": np.array_equal(np.sort(states["wrong"]["R"].ravel()), np.sort(parents["after_render"]["R"].ravel())),
        "wrong_donor_trajectory_exact_permutation": all(
            np.array_equal(trajectories["wrong"]["snapshots"][t][k],
                           np.roll(trajectories["copy"]["snapshots"][t][k].reshape(MESSAGES, config.replicates, 16, 16), -1, axis=0).reshape(-1, 16, 16))
            for t in config.sample_times for k in ("V", "ema", "R")),
    }
    result = {"tissue": context["index"], "structural_gates": gates, "passes": all(gates.values()),
              "initial_state_sha256": initial_hashes, "newborn_sha256": newborn_digest,
              "parent_sha256": source_digest, "summaries": summaries, "rows": rows,
              "parent_measurements": {k: measure_state(s, context["codes"], config.replicates, 0) for k, s in parents.items()},
              "trajectory_sha256": {a: trajectory_digest(tr) for a, tr in trajectories.items()},
              "development_rng_initial_sha256": trajectories["copy"]["rng_initial_sha256"],
              "development_rng_final_sha256": trajectories["copy"]["rng_final_sha256"]}
    return result, parents, trajectories, fresh


def bootstrap(values: list[float], seed_value: int) -> dict:
    data = np.asarray(values)
    indices = np.random.default_rng(seed_value).integers(0, len(data), (10000, len(data)))
    return {"tissue_differences": data.tolist(), "mean": float(data.mean()), "positive_tissues": int((data > 0).sum()),
            "paired_tissue_bootstrap_95": np.quantile(data[indices].mean(axis=1), [.025, .975]).tolist(),
            "seed": seed_value, "resamples": 10000}


def classify(results: list[dict], calibrated: bool, structural: bool = True) -> dict:
    if not structural:
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    if not calibrated:
        return {"label": "INSTRUMENT_NOT_QUALIFIED"}
    if sorted(r["tissue"] for r in results) != list(TISSUES) or not all(r["passes"] for r in results):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    final = [r["summaries"] for r in sorted(results, key=lambda r: r["tissue"])]
    endpoint = lambda s, arm, key="body_accuracy": s[arm][str(CONFIG.child_sweeps)][key]
    primary = bootstrap([endpoint(s, "copy") - endpoint(s, "reset") for s in final], 202609071701)
    specificity = bootstrap([endpoint(s, "copy") - endpoint(s, "wrong") for s in final], 202609071702)
    donor_following = bootstrap([endpoint(s, "wrong", "wrong_donor_body_accuracy") - endpoint(s, "wrong") for s in final], 202609071703)
    qualified = primary["positive_tissues"] >= 6 and all(c["paired_tissue_bootstrap_95"][0] > 0 for c in (primary, specificity, donor_following))
    return {"label": "CONTENT_SPECIFIC_R_TRANSMISSION" if qualified else "NO_QUALIFIED_R_TRANSMISSION_IN_THIS_ASSAY",
            "primary_copy_minus_reset": primary, "specificity_copy_minus_wrong": specificity, "wrong_donor_following": donor_following}


def runtime() -> dict:
    cpus = sorted(os.sched_getaffinity(0))[:WORKERS]
    os.sched_setaffinity(0, cpus)
    api = source_api()
    gates = {"at_most_four_cpus": 0 < len(cpus) <= WORKERS,
             "numerical_threads_one": all(os.environ.get(k) == "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")),
             "pinned_python_numpy": platform.python_version_tuple()[:2] == ("3", "13") and np.__version__ == "2.5.2",
             "native_E55_config": api["EigenConfig"]().digest() == "26e403f2e841da5a1fd5d2cb15fedf678174644be094e14a5c1a54de38a57f54",
             "native_reference_parameters": api["BlueprintConfig"]().rho == .002 and api["BlueprintConfig"]().c_m == .2}
    return {"cpu_affinity": cpus, "workers": WORKERS, "threads_per_worker": 1, "gates": gates, "passes": all(gates.values())}


def disk_preflight(root: Path) -> dict:
    free = shutil.disk_usage(root).free
    return {"free_bytes": free, "estimated_output_bytes": 512 * 1024**2, "safety_margin_bytes": 1024**3,
            "passes": free >= 512 * 1024**2 + 1024**3}


def input_paths() -> list[Path]:
    workspace = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), workspace / "src/laws_confirmation/io.py", workspace / "src/laws_confirmation/__init__.py",
             workspace / "tests/test_l17_r_channel.py", workspace / "scripts/run_l17_r_channel.sh",
             workspace / "protocols/L17_R_CHANNEL_ONE_BOUNDARY_V1.md", workspace / "reviews/L17_DEVELOPMENT_HEREDITY_AUDIT_2026-09-03.md",
             sources_root() / "LAWS.md", sources_root() / "error_threshold/EXPECTATIONS.md"]
    for package in PACKAGES:
        package_root = sources_root() / package
        paths.extend(package_root.joinpath("src").rglob("*.py"))
        paths.extend(package_root.joinpath("tests").rglob("*.py"))
        paths.append(package_root / "pyproject.toml")
    return sorted(set(paths))


def verify_hashes(hashes: dict) -> bool:
    return bool(hashes) and all(Path(p).is_file() and sha256_file(Path(p)) == expected for p, expected in hashes.items())


def benchmark_path(root: Path) -> Path:
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root: Path) -> dict:
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("benchmark cannot change prepared inputs")
    qualification = runtime()
    if not qualification["passes"] or not disk_preflight(root)["passes"]:
        raise RuntimeError("benchmark runtime/storage qualification failed")
    cfg = ExperimentConfig(replicates=2, settle_sweeps=32, imprint_sweeps=32, render_sweeps=32, child_sweeps=32, sample_times=(0, 8, 16, 32))
    ctx = make_context(20000, cfg)
    started = time.monotonic()
    control, body, _ = calibration(ctx)
    calibration_seconds = time.monotonic() - started
    started = time.monotonic()
    result, _, _, _ = acquired_experiment(ctx, body)
    acquired_seconds = time.monotonic() - started
    if not control["passes"] or not result["passes"]:
        raise RuntimeError("benchmark structural gate failed")
    cal_scale = (CONFIG.replicates / cfg.replicates) * (CONFIG.settle_sweeps + 3 * CONFIG.child_sweeps) / (cfg.settle_sweeps + 3 * cfg.child_sweeps)
    acquired_scale = (CONFIG.replicates / cfg.replicates) * (CONFIG.settle_sweeps + CONFIG.imprint_sweeps + CONFIG.render_sweeps + 9 * CONFIG.child_sweeps) / (cfg.settle_sweeps + cfg.imprint_sweeps + cfg.render_sweeps + 9 * cfg.child_sweeps)
    projection = math.ceil(len(TISSUES) / WORKERS) * (calibration_seconds * cal_scale + acquired_seconds * acquired_scale) * 1.75 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "effect_sizes_not_reported": True,
              "disposable_tissue": 20000, "runtime": qualification, "config": asdict(cfg),
              "calibration_seconds": calibration_seconds, "acquired_seconds": acquired_seconds,
              "projected_seconds_four_workers": projection, "safety_multiplier": 1.75, "must_detach": projection > 600,
              "all_structural_gates_pass": True, "input_sha256": {str(p): sha256_file(p) for p in input_paths()}}
    atomic_json(benchmark_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root: Path) -> dict:
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("refusing existing immutable scientific target")
    timing = json.loads(benchmark_path(root).read_text())
    qualification, disk = runtime(), disk_preflight(root)
    hashes = {str(p): sha256_file(p) for p in input_paths()}
    if not (timing["all_structural_gates_pass"] and timing["input_sha256"] == hashes and qualification["passes"] and disk["passes"]):
        raise RuntimeError("source/benchmark/runtime/storage preflight failed")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    manifest = {"run_id": RUN_ID, "prepared_utc": utc_now(), "config": asdict(CONFIG), "tissues": list(TISSUES),
                "arms": list(ARMS), "workers": WORKERS, "registered_child_lives": REGISTERED_CHILD_LIVES,
                "input_sha256": hashes, "contract_digest": canonical_digest(hashes), "benchmark": timing,
                "runtime": qualification, "disk_preflight": disk, "environment": environment_manifest(),
                "repository_head": git_head(Path(__file__).resolve().parents[2]), "law_verdict_changes": 0}
    atomic_json(run / "MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], output / "input_hashes.sha256", root)
    atomic_json(run / "STATUS.json", {"status": "PREPARED", "run_id": RUN_ID, "updated_utc": utc_now()}, root)
    return manifest


def verify_prepared(root: Path) -> dict:
    run = root / "runs" / RUN_ID
    manifest = json.loads((run / "MANIFEST.json").read_text())
    status = json.loads((run / "STATUS.json").read_text())
    if (status["status"] != "PREPARED" or manifest["run_id"] != RUN_ID
            or not verify_hashes(manifest["input_sha256"])
            or manifest["contract_digest"] != canonical_digest(manifest["input_sha256"])
            or set(manifest["input_sha256"]) != {str(p) for p in input_paths() + [benchmark_path(root)]}
            or canonical_digest(manifest["config"]) != canonical_digest(asdict(CONFIG))
            or manifest["tissues"] != list(TISSUES) or manifest["arms"] != list(ARMS) or manifest["workers"] != WORKERS
            or (run / "COMPLETE").exists() or (run / "FAILED").exists()):
        raise RuntimeError("not uniquely PREPARED or contract changed")
    return manifest


def launch_detached(root: Path) -> dict:
    if not (root / "runs" / RUN_ID).exists():
        prepare(root)
    manifest = verify_prepared(root)
    run = root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{suffix}.log" for suffix in ("stdout", "stderr")]
    command = [sys.executable, "-m", "laws_confirmation.l17_r_channel", "--external-root", str(root), "--run"]
    with stdout.open("xb") as out_handle, stderr.open("xb") as err_handle:
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                                   stdout=out_handle, stderr=err_handle, start_new_session=True)
    launch = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(), "command": command,
              "stdout_log": str(stdout), "stderr_log": str(stderr), "status": str(run / "STATUS.json"),
              "complete": str(run / "COMPLETE"), "failed": str(run / "FAILED"),
              "estimated_seconds": manifest["benchmark"]["projected_seconds_four_workers"], "polling_owner": "user"}
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    atomic_json(run / "LAUNCH.json", launch, root)
    print(json.dumps(launch, indent=2), flush=True)
    # Deliberately no wait/poll/status inspection after detachment.
    return launch


def worker(tissue_index: int, phase: str, root_text: str) -> dict:
    root = external_root(root_text)
    if not runtime()["passes"]:
        raise RuntimeError("worker runtime gate failed")
    output = root / "outputs" / RUN_ID / f"tissue_{tissue_index}"
    context = make_context(tissue_index, CONFIG)
    if phase == "calibration":
        result, newborn, trajectories = calibration(context)
        arrays = {**{f"newborn_{k}": v for k, v in newborn.items()}, "theta": context["theta"], "codes": context["codes"]}
        atomic_npz(output / "newborn.npz", arrays, root)
        result["newborn_file_sha256"] = sha256_file(output / "newborn.npz")
        result["configs"] = {"tissue": asdict(context["tissue"]), "blueprint": asdict(context["bp"]), "ladder": asdict(context["ladder"])}
        for arm, trajectory in trajectories.items():
            atomic_npz(output / f"{arm}_states.npz", trajectory_arrays(trajectory), root)
        result["rows"] = {arm: trajectory_rows(context, tr) for arm, tr in trajectories.items()}
    elif phase == "acquired":
        control = json.loads((output / "calibration.json").read_text())
        if sha256_file(output / "newborn.npz") != control["newborn_file_sha256"]:
            raise RuntimeError("newborn artifact changed")
        with np.load(output / "newborn.npz", allow_pickle=False) as loaded:
            newborn = {k: loaded[f"newborn_{k}"].copy() for k in ("V", "ema", "R")}
            if not np.array_equal(loaded["theta"], context["theta"]) or not np.array_equal(loaded["codes"], context["codes"]):
                raise RuntimeError("newborn rulebook changed")
        if state_digest(newborn) != control["newborn_sha256"]:
            raise RuntimeError("newborn reconstruction failed")
        result, parents, trajectories, fresh = acquired_experiment(context, newborn)
        atomic_npz(output / "parent_states.npz", {f"{stage}_{k}": v for stage, state in parents.items() for k, v in state.items()}, root)
        atomic_npz(output / "fragment_regrown_mask.npz", {"fresh": fresh}, root)
        for arm, trajectory in trajectories.items():
            atomic_npz(output / f"{arm}_states.npz", trajectory_arrays(trajectory), root)
    else:
        raise ValueError("unregistered worker phase")
    if not result["passes"]:
        raise RuntimeError(f"{phase} tissue {tissue_index} structural failure: {result['structural_gates']}")
    atomic_json(output / f"{phase}.json", result, root)
    print(f"{phase}: tissue {tissue_index} complete", flush=True)
    return {k: v for k, v in result.items() if k not in ("rows", "parent_measurements")} | {"path": str(output / f"{phase}.json")}


def markdown_report(study: dict) -> str:
    lines = ["# L17 original-sheet one-boundary R-channel assay", "", f"Run: `{RUN_ID}`.",
             f"Structural completion: `{study['completed_cleanly']}`.", f"Result: `{study['classification']['label']}`.", "",
             "One boundary, native dynamics, four equal-area translated messages; not a twelve-generation or zero-capacity test.",
             f"Positive-control instrument qualified: `{study['instrument_qualified']}`.", ""]
    if study["acquired_results"]:
        lines += ["| Tissue | Correct | Reset | Wrong (receiver) | Wrong (donor) | Shuffled | Fragment + R | Fragment, reset R |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for result in study["acquired_results"]:
            final = {a: s["1000"] for a, s in result["summaries"].items()}
            values = [final[a]["body_accuracy"] for a in ("copy", "reset", "wrong")]
            values += [final["wrong"]["wrong_donor_body_accuracy"]]
            values += [final[a]["body_accuracy"] for a in ("shuffle", "fragment_copy", "fragment_reset")]
            lines.append(f"| {result['tissue']} | " + " | ".join(f"{v:.6f}" for v in values) + " |")
        for name in ("primary_copy_minus_reset", "specificity_copy_minus_wrong", "wrong_donor_following"):
            contrast = study["classification"].get(name)
            if contrast:
                lines += ["", f"{name}: mean {contrast['mean']:+.6f}, 95% paired tissue interval {contrast['paired_tissue_bootstrap_95']}."]
    else:
        lines += ["Acquired-parent phase was not run because the positive-control instrument did not qualify."]
    lines += ["", "No numbered-law verdict is changed automatically. All outcomes, including negative and unqualified measurements, are retained.", ""]
    return "\n".join(lines)


def run_study(root: Path) -> int:
    manifest = verify_prepared(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    (run / "EXECUTION.lock").mkdir()
    started = time.monotonic()
    try:
        qualification = runtime()
        if not qualification["passes"]:
            raise RuntimeError("runtime gate failed")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        collected = {"calibration": [], "acquired": []}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as executor:
            for phase in ("calibration", "acquired"):
                if phase == "acquired" and not calibration_qualified(collected["calibration"]):
                    break
                atomic_json(run / "STATUS.json", {"status": "RUNNING", "run_id": RUN_ID, "phase": phase, "completed_tissues_in_phase": 0, "updated_utc": utc_now()}, root)
                futures = [executor.submit(worker, tissue, phase, str(root)) for tissue in TISSUES]
                for future in as_completed(futures):
                    collected[phase].append(future.result())
                    atomic_json(run / "STATUS.json", {"status": "RUNNING", "run_id": RUN_ID, "phase": phase,
                                                     "completed_tissues_in_phase": len(collected[phase]), "updated_utc": utc_now()}, root)
        for result_list in collected.values():
            result_list.sort(key=lambda r: r["tissue"])
        calibrated = calibration_qualified(collected["calibration"])
        gates = {"runtime": qualification["passes"], "all_calibrations_structural": len(collected["calibration"]) == len(TISSUES) and all(r["passes"] for r in collected["calibration"]),
                 "acquired_phase_correctly_gated": (len(collected["acquired"]) == len(TISSUES) if calibrated else not collected["acquired"]),
                 "all_acquired_structural": all(r["passes"] for r in collected["acquired"]), "input_hashes_unchanged": verify_hashes(manifest["input_sha256"])}
        classification = classify(collected["acquired"], calibrated, all(gates.values()))
        study = {"run_id": RUN_ID, "generated_utc": utc_now(), "runtime": qualification, "config": asdict(CONFIG),
                 "instrument_qualified": calibrated, "calibration_results": collected["calibration"], "acquired_results": collected["acquired"],
                 "classification": classification, "completion_gates": gates, "completed_cleanly": all(gates.values()),
                 "registered_child_lives_if_calibrated": REGISTERED_CHILD_LIVES,
                 "child_lives_run_excluding_replays": len(TISSUES) * MESSAGES * CONFIG.replicates * (2 + (len(ARMS) if calibrated else 0)),
                 "elapsed_seconds": time.monotonic() - started, "numbered_law_verdict_changes": 0}
        atomic_json(output / "r_channel.json", study, root)
        atomic_text(output / "audit.md", markdown_report(study), root)
        paths = sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256")
        write_hash_manifest(paths, output / "output_hashes.sha256", root)
        outputs_valid = all(sha256_file(Path(p)) == h for h, p in (line.split("  ", 1) for line in (output / "output_hashes.sha256").read_text().splitlines()))
        success = study["completed_cleanly"] and outputs_valid
        status = {"run_id": RUN_ID, "status": "COMPLETE" if success else "FAILED_GATES", "completed_cleanly": success,
                  "classification": classification["label"], "completed_utc": utc_now(), "elapsed_seconds": time.monotonic() - started,
                  "instrument_qualified": calibrated, "child_lives_run_excluding_replays": study["child_lives_run_excluding_replays"],
                  "workers": WORKERS, "cpu_affinity": qualification["cpu_affinity"], "output_manifest_self_verifies": outputs_valid}
        atomic_json(run / "STATUS.json", status, root)
        atomic_text(run / ("COMPLETE" if success else "FAILED"), status["completed_utc"] + "\n", root)
        print(json.dumps(status, indent=2), flush=True)
        return 0 if success else 1
    except Exception as error:
        failure = {"status": "FAILED", "run_id": RUN_ID, "failed_utc": utc_now(), "error": str(error), "traceback": traceback.format_exc()}
        atomic_json(run / "STATUS.json", failure, root)
        atomic_text(run / "FAILED", failure["failed_utc"] + "\n", root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for option in ("benchmark", "prepare", "detach", "run"):
        group.add_argument(f"--{option}", action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        manifest = prepare(root)
        print(json.dumps({"status": "PREPARED", "input_files": len(manifest["input_sha256"]), "estimated_seconds": manifest["benchmark"]["projected_seconds_four_workers"]}, indent=2))
    elif args.detach:
        launch_detached(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
