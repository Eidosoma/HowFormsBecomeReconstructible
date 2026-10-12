"""Independent raw-array audit, with no experiment dynamics/metrics imported.

Fission is reconstructed from the frozen seed contract and explicit half-cut
formula. The previously frozen independent scorer checks every world's maps.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import numpy as np

from laws_confirmation.io import (atomic_json, canonical_digest, external_root,
                                 utc_now, write_hash_manifest)


_spec = importlib.util.spec_from_file_location("frozen_independent_twelve", Path(__file__).with_name("audit_l17_r_channel_twelve_outputs.py"))
independent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(independent)

RUN_ID = "l17_centered_renewal_v1_attempt1"
SOURCE_ID = "l17_r_channel_twelve_boundary_v1_attempt1"
PARENT_ID = "l17_r_channel_one_boundary_v1_attempt1"
AUDIT_ID = RUN_ID + "_independent_rescore_v1"
ARMS = tuple(f"{b}_{r}_{w}" for b in ("native", "centered") for r in ("copy", "reset") for w in ("live", "held")) + (
    "centered_copy_off", "centered_reset_off")
ANCHORS = {"native_copy_live": "fragment_renew", "native_reset_live": "fragment_reset"}


def templates():
    stripe = np.broadcast_to(np.where((np.arange(16) // 4) % 2 == 0, 1., -1.), (16, 16))
    return np.stack([np.roll(stripe, shift, axis=1) for shift in (0, 2, 4, 6)])


def state_hash(state):
    return canonical_digest({k: independent.digest(v) for k, v in state.items()})


def native_birth(tissue, generation, parent_v):
    """Independent reconstruction, not a call to the simulation's fission."""
    event = "fragment_boundary" if generation == 1 else f"twelve_boundary_v1:g{generation:02d}:fragment_boundary"
    seed = int.from_bytes(hashlib.sha256(f"l17-r-channel-one-boundary-v1:{tissue}:{event}".encode()).digest()[:16], "little")
    rng = np.random.default_rng(seed)
    replicates = len(parent_v) // 4
    axes = np.tile(rng.integers(0, 2, replicates), 4)
    sides = np.tile(rng.integers(0, 2, replicates), 4)
    fresh = np.ones_like(parent_v, dtype=bool)
    for world, (axis, side) in enumerate(zip(axes, sides)):
        kept = slice(0, 8) if side == 0 else slice(8, 16)
        if axis == 0:
            fresh[world, kept, :] = False
        else:
            fresh[world, :, kept] = False
    raw = np.where(fresh, -1., parent_v)
    raw += .05 * np.tile(rng.standard_normal((replicates, 16, 16)), (4, 1, 1))
    return raw, fresh


def check_generation(tissue, generation, g0, parents, previous_counts, saved, maps, births, reset, times=(0, 50, 1000)):
    assert set(maps) == set(ARMS) and saved["generation"] == generation
    assert saved["passes"] and all(saved["structural_gates"].values())
    assert births["fresh"].dtype == bool and births["counts"].dtype == np.int32
    np.testing.assert_array_equal(births["counts"], previous_counts + births["fresh"])
    np.testing.assert_array_equal(births["reset_R"], reset)
    grouped = reset.reshape(4, 8, 16, 16)
    assert all(np.array_equal(grouped[0], grouped[m]) for m in range(1, 4))
    assert saved["reset_reference_sha256"] == independent.digest(reset)
    codes, stages = templates(), []
    for arm, raw in maps.items():
        body, reference, writer = arm.split("_")
        assert set(raw) == {f"s{t}_{k}" for t in times for k in ("V", "ema", "R")}
        raw_v, fresh = native_birth(tissue, generation, parents[arm]["V"])
        np.testing.assert_array_equal(births[f"raw_{arm}"], raw_v)
        np.testing.assert_array_equal(fresh, births["fresh"])
        mean = raw_v.reshape(32, 256).mean(axis=1)[:, None, None]
        expected_v = raw_v - mean if body == "centered" else raw_v
        expected_r = parents[arm]["R"] if reference == "copy" else reset
        np.testing.assert_array_equal(raw["s0_V"], expected_v)
        np.testing.assert_array_equal(raw["s0_ema"], expected_v)
        np.testing.assert_array_equal(raw["s0_R"], expected_r)
        if body == "centered":
            assert abs(expected_v.mean(axis=(1, 2))).max() < 1e-14
        if generation == 1:
            np.testing.assert_array_equal(raw["s0_V"], maps[f"{body}_copy_live"]["s0_V"])
        assert saved["parent_state_sha256"][arm] == state_hash(parents[arm])
        assert saved["birth_state_sha256"][arm] == state_hash({k: raw[f"s0_{k}"] for k in ("V", "ema", "R")})
        assert saved["final_state_sha256"][arm] == state_hash({k: raw[f"s{times[-1]}_{k}"] for k in ("V", "ema", "R")})
        assert saved["reference_links"][arm] == {
            "source": "immediate_parent" if reference == "copy" else "naive_reset",
            "expected_sha256": independent.digest(expected_r), "birth_sha256": independent.digest(expected_r)}
        corrected_shape = expected_v - expected_v.mean(axis=(1, 2))[:, None, None]
        shape_error = float(np.max(abs(corrected_shape - (raw_v - mean))))
        assert shape_error < 1e-14
        correction = saved["birth_corrections"][arm]
        for key, value in (("raw_means", mean[:, 0, 0]), ("raw_mins", raw_v.min(axis=(1, 2))),
                           ("raw_maxs", raw_v.max(axis=(1, 2))), ("birth_means", expected_v.mean(axis=(1, 2))),
                           ("centered_shape_max_error", shape_error)):
            np.testing.assert_allclose(correction[key], value, rtol=0., atol=1e-15)
        changed = not np.array_equal(raw["s0_R"], raw[f"s{times[-1]}_R"])
        assert saved["reference_changed_in_life"][arm] == changed
        assert changed == (writer != "held")
        for sweep in times:
            state = {k: raw[f"s{sweep}_{k}"] for k in ("V", "ema", "R")}
            rows = [r for r in saved["rows"][arm] if r["sweep"] == sweep]
            summary = saved["summaries"][arm][str(sweep)]
            stage = independent.check_snapshot(state, rows, summary, codes, g0, parents[arm], births)
            for i, row in enumerate(rows):
                v, r = state["V"][i], state["R"][i]
                actual = {"body_mean": float(v.mean()), "body_rms": float(np.sqrt((v*v).mean())),
                          "body_min": float(v.min()), "body_max": float(v.max()), "positive_fraction": float((v > 0).mean()),
                          "active_fraction": float((abs(v) > .2).mean()), "reference_mean": float(r.mean()),
                          "reference_l2_norm": float(np.linalg.norm(r))}
                for key, value in actual.items():
                    np.testing.assert_allclose(row[key], value, rtol=0., atol=1e-14)
            for key in ("body_mean", "body_rms", "body_min", "body_max", "positive_fraction", "reference_mean"):
                np.testing.assert_allclose(summary[key], np.mean([r[key] for r in rows]), rtol=0., atol=1e-15)
            if writer == "held":
                np.testing.assert_array_equal(state["R"], expected_r)
                if reference == "copy":
                    np.testing.assert_array_equal(state["R"], g0["R"])
            if writer == "off":
                for key in ("V", "ema"):
                    np.testing.assert_array_equal(state[key], maps["centered_reset_off"][f"s{sweep}_{key}"])
            stages.append({"generation": generation, "arm": arm, "sweep": sweep, **stage,
                           "body_mean": summary["body_mean"], "positive_fraction": summary["positive_fraction"]})
    return stages


def adjudicate(endpoints, protected, saved):
    assert [e["tissue"] for e in endpoints] == list(range(10000, 10008))
    matrix = np.asarray(protected)
    assert matrix.shape == (8, 12)
    qualified = bool((matrix > .25).all() and (matrix.mean(axis=0) >= .75).all())
    assert saved["protected_reference_control_qualified"] == qualified
    assert saved["protected_body_accuracy_tissue_by_generation"] == matrix.tolist()
    contrasts = {}
    for i, (name, metric, other) in enumerate((("body_vs_reset", "body_accuracy", "centered_reset_live"),
            ("body_vs_reader_off", "body_accuracy", "centered_copy_off"),
            ("reference_vs_reset", "reference_accuracy", "centered_reset_live"))):
        values = np.array([e["arms"]["centered_copy_live"][metric] - e["arms"][other][metric] for e in endpoints])
        seed = 20260907170401 + i
        draws = np.random.default_rng(seed).integers(0, 8, (10000, 8))
        interval = np.quantile(values[draws].mean(axis=1), [1 / 120, 119 / 120]).tolist()
        positive = int((values > 0).sum())
        contrast = {"tissue_differences": values.tolist(), "mean": float(values.mean()), "positive_tissues": positive,
                    "paired_tissue_interval": interval, "quantiles": [1 / 120, 119 / 120], "resamples": 10000,
                    "seed": seed, "supported": interval[0] > 0 and positive >= 6}
        assert contrast == saved["co_primary_G12"][name]
        contrasts[name] = contrast
    label = ("PROTECTED_REFERENCE_CONTROL_NOT_QUALIFIED" if not qualified else
             "CENTERED_NATIVE_RENEWAL_WITH_R_CONTRIBUTION" if all(c["supported"] for c in contrasts.values()) else
             "NO_QUALIFIED_CENTERED_RENEWAL_LEAD")
    assert saved["label"] == label
    return {"label": label, "protected_reference_control_qualified": qualified, "co_primary_G12": contrasts}


def main():
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    assert all(os.environ.get(k) == "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"))
    root = external_root()
    source, output, run = root / "outputs" / RUN_ID, root / "outputs" / AUDIT_ID, root / "runs" / RUN_ID
    if output.exists():
        raise FileExistsError("immutable independent audit already exists")
    status = json.loads((run / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"]
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
    input_count = independent.manifest_check(source / "input_hashes.sha256")
    output_count = independent.manifest_check(source / "output_hashes.sha256")
    study = json.loads((source / "centered_renewal.json").read_text())
    assert study["completed_cleanly"] and all(study["completion_gates"].values())
    assert study["config"]["generations"] == 12 and study["config"]["child_sweeps"] == 1000
    assert [r["tissue"] for r in study["results"]] == list(range(10000, 10008))
    stages, endpoints, protected = [], [], []
    for tissue in range(10000, 10008):
        directory = source / f"tissue_{tissue}"
        lineage = json.loads((directory / "lineage.json").read_text())
        assert lineage == study["results"][tissue - 10000]
        assert [g["generation"] for g in lineage["generations"]] == list(range(1, 13))
        ancestor = independent.arrays(root / "outputs" / PARENT_ID / f"tissue_{tissue}" / "parent_states.npz")
        g0 = {k: ancestor[f"after_render_{k}"] for k in ("V", "ema", "R")}
        assert lineage["g0_sha256"] == state_hash(g0)
        parents, counts = {a: g0 for a in ARMS}, np.zeros((32, 16, 16), dtype=np.int32)
        tissue_protected, streams = [], []
        for generation in range(1, 13):
            gd = directory / f"g{generation:02d}"
            previous = root / "outputs" / SOURCE_ID / f"tissue_{tissue}" / f"g{generation:02d}"
            reset = independent.arrays(previous / "newborn.npz")["R"]
            births = independent.arrays(gd / "births.npz")
            saved = json.loads((gd / "generation.json").read_text())
            assert {k: v for k, v in saved.items() if k != "rows"} == lineage["generations"][generation - 1]
            maps = {a: independent.arrays(gd / f"{a}_states.npz") for a in ARMS}
            for arm, old_arm in ANCHORS.items():
                anchor = independent.arrays(previous / f"{old_arm}_states.npz")
                assert set(anchor) == set(maps[arm])
                for key, value in anchor.items():
                    np.testing.assert_array_equal(maps[arm][key], value)
            growth = independent.arrays(previous / "regrowth.npz")
            for key in ("fresh", "counts"):
                np.testing.assert_array_equal(births[key], growth[key])
            checked = check_generation(tissue, generation, g0, parents, counts, saved, maps, births, reset)
            stages.extend({"tissue": tissue, **r} for r in checked)
            end = {r["arm"]: r for r in checked if r["sweep"] == 1000}
            tissue_protected.append(end["centered_copy_held"]["body_accuracy"])
            if generation == 12:
                endpoints.append({"tissue": tissue, "arms": end})
            counts = births["counts"]
            parents = {a: {k: maps[a][f"s1000_{k}"] for k in ("V", "ema", "R")} for a in ARMS}
            streams.append(saved["rng_initial_sha256"])
        assert len(set(streams)) == 12
        protected.append(tissue_protected)
        print(f"independent centered-renewal audit: tissue {tissue} verified", flush=True)
    classification = adjudicate(endpoints, protected, study["classification"])
    assert len(stages) == 2880
    assert independent.manifest_check(source / "input_hashes.sha256") == input_count
    assert independent.manifest_check(source / "output_hashes.sha256") == output_count
    record = {"run_id": AUDIT_ID, "source_run": RUN_ID, "checked_utc": utc_now(), "passes": True,
              "source_input_hashes_verified": input_count, "source_output_hashes_verified": output_count,
              "raw_snapshots_rescored": len(stages), "world_rows_rescored": len(stages) * 32,
              "fission_births_reconstructed": 8 * 12 * 10, "classification": classification,
              "stages": stages, "G12_tissues": endpoints, "protected_reference_tissue_by_generation": protected,
              "new_simulations": 0}
    output.mkdir(parents=True)
    atomic_json(output / "rescore.json", record, root)
    write_hash_manifest([Path(__file__).resolve(), Path(independent.__file__).resolve(), source / "input_hashes.sha256",
                         source / "output_hashes.sha256", run / "STATUS.json", run / "COMPLETE"], output / "input_hashes.sha256", root)
    write_hash_manifest([output / "rescore.json", output / "input_hashes.sha256"], output / "output_hashes.sha256", root)
    print(json.dumps({k: v for k, v in record.items() if k not in ("stages", "G12_tissues", "protected_reference_tissue_by_generation")}, indent=2))


if __name__ == "__main__":
    main()
