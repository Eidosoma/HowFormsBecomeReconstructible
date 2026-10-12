"""Independent common-birth audit using the frozen independent array scorer.

No experiment dynamics, decoder, metric or bootstrap function is imported.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np

from laws_confirmation.io import atomic_json, external_root, sha256_file, utc_now, write_hash_manifest


_spec = importlib.util.spec_from_file_location("frozen_independent_twelve", Path(__file__).with_name("audit_l17_r_channel_twelve_outputs.py"))
independent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(independent)

RUN_ID = "l17_common_birth_factorial_v1_attempt1"
SOURCE_ID = "l17_r_channel_twelve_boundary_v1_attempt1"
PARENT_ID = "l17_r_channel_one_boundary_v1_attempt1"
AUDIT_ID = RUN_ID + "_independent_rescore_v1"
ARMS = tuple(f"{b}_{r}_{w}" for b in ("native", "centered") for r in ("current", "ancestor") for w in ("live", "held")) + (
    "centered_wrong_held", "centered_ancestor_off", "centered_current_off")


def templates():
    first = np.broadcast_to(np.where((np.arange(16) // 4) % 2 == 0, 1., -1.), (16, 16))
    return np.stack([np.roll(first, shift, axis=1) for shift in (0, 2, 4, 6)])


def check_cell(common, saved, maps, codes):
    initial, ancestor, parent = ({k: common[f"{name}_{k}"] for k in ("V", "ema", "R")} for name in ("initial", "ancestor", "parent"))
    growth = {k: common[k] for k in ("fresh", "counts")}
    assert set(maps) == set(ARMS)
    centered = initial["V"] - initial["V"].reshape(32, 256).mean(axis=1)[:, None, None]
    stages = []
    for arm, raw in maps.items():
        body, reference, writer = arm.split("_")
        expected_v = initial["V"] if body == "native" else centered
        expected_r = (initial["R"] if reference == "current" else ancestor["R"] if reference == "ancestor"
                      else np.concatenate((ancestor["R"][8:], ancestor["R"][:8])))
        np.testing.assert_array_equal(raw["s0_V"], expected_v)
        np.testing.assert_array_equal(raw["s0_ema"], expected_v)
        np.testing.assert_array_equal(raw["s0_R"], expected_r)
        if body == "centered":
            assert abs(raw["s0_V"].mean(axis=(1, 2))).max() < 1e-14
            np.testing.assert_allclose(raw["s0_V"] - raw["s0_V"].mean(axis=(1, 2))[:, None, None], centered, rtol=0., atol=1e-14)
        first_expected = expected_r + (.002 if writer == "live" else 0.) * (raw["s1_V"] - expected_r)
        np.testing.assert_array_equal(raw["s1_R"], first_expected)
        times = sorted({r["sweep"] for r in saved["rows"][arm]})
        for sweep in times:
            state = {k: raw[f"s{sweep}_{k}"] for k in ("V", "ema", "R")}
            rows = [r for r in saved["rows"][arm] if r["sweep"] == sweep]
            summary = saved["summaries"][arm][str(sweep)]
            stage = independent.check_snapshot(state, rows, summary, codes, ancestor, parent, growth)
            for i, row in enumerate(rows):
                v, r = state["V"][i], state["R"][i]
                actual = {"body_mean": float(v.mean()), "body_rms": float(np.sqrt((v*v).mean())), "body_min": float(v.min()),
                          "body_max": float(v.max()), "positive_fraction": float((v>0).mean()), "reference_mean": float(r.mean())}
                for k, value in actual.items():
                    np.testing.assert_allclose(row[k], value, rtol=0., atol=1e-15)
            for k in ("body_mean", "body_rms", "body_min", "body_max", "positive_fraction", "reference_mean"):
                np.testing.assert_allclose(summary[k], np.mean([r[k] for r in rows]), rtol=0., atol=1e-15)
            if writer != "live":
                np.testing.assert_array_equal(state["R"], expected_r)
            if writer == "off":
                for k in ("V", "ema"):
                    np.testing.assert_array_equal(state[k], maps["centered_current_off"][f"s{sweep}_{k}"])
            stages.append({"arm": arm, "sweep": sweep, **stage, "body_mean": summary["body_mean"], "positive_fraction": summary["positive_fraction"]})
    return stages


def main():
    root = external_root()
    source, output = root / "outputs" / RUN_ID, root / "outputs" / AUDIT_ID
    if output.exists():
        raise FileExistsError("immutable audit already exists")
    run = root / "runs" / RUN_ID
    status = json.loads((run / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"]
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
    input_count = independent.manifest_check(source / "input_hashes.sha256")
    output_count = independent.manifest_check(source / "output_hashes.sha256")
    study = json.loads((source / "common_birth.json").read_text())
    assert study["completed_cleanly"] and all(study["completion_gates"].values())
    codes = templates()
    stages, endpoints = [], []
    for tissue in range(10000, 10008):
        for generation in (2, 12):
            directory = source / f"tissue_{tissue}" / f"g{generation:02d}"
            previous = root / "outputs" / SOURCE_ID / f"tissue_{tissue}"
            common = independent.arrays(directory / "common.npz")
            saved = json.loads((directory / "branches.json").read_text())
            assert saved["passes"] and all(saved["structural_gates"].values())
            prior = independent.arrays(previous / f"g{generation-1:02d}" / "fragment_renew_states.npz")
            native = independent.arrays(previous / f"g{generation:02d}" / "fragment_renew_states.npz")
            growth = independent.arrays(previous / f"g{generation:02d}" / "regrowth.npz")
            original = independent.arrays(root / "outputs" / PARENT_ID / f"tissue_{tissue}" / "parent_states.npz")
            for key in ("V", "ema", "R"):
                np.testing.assert_array_equal(common[f"initial_{key}"], native[f"s0_{key}"])
                np.testing.assert_array_equal(common[f"parent_{key}"], prior[f"s1000_{key}"])
                np.testing.assert_array_equal(common[f"ancestor_{key}"], original[f"after_render_{key}"])
            for key in ("fresh", "counts"):
                np.testing.assert_array_equal(common[key], growth[key])
            np.testing.assert_array_equal(common["codes"], codes)
            maps = {arm: independent.arrays(directory / f"{arm}_states.npz") for arm in ARMS}
            for key in native:
                np.testing.assert_array_equal(maps["native_current_live"][key], native[key])
            cell_stages = check_cell(common, saved, maps, codes)
            stages.extend({"tissue": tissue, "generation": generation, **r} for r in cell_stages)
            if generation == 12:
                endpoints.append({"tissue": tissue, "arms": {r["arm"]: r["body_accuracy"] for r in cell_stages if r["sweep"] == 1000}})
    contrasts = {}
    for n, (name, left, right) in enumerate((("body_compatibility", "centered_ancestor_held", "native_ancestor_held"),
                                            ("reference_quality", "centered_ancestor_held", "centered_current_held"))):
        values = np.asarray([r["arms"][left] - r["arms"][right] for r in endpoints])
        draws = np.random.default_rng(20260907170301 + n).integers(0, 8, (10000, 8))
        interval = np.quantile(values[draws].mean(axis=1), [.0125, .9875]).tolist()
        supported = interval[0] > 0 and int((values > 0).sum()) >= 6
        saved = study["classification"]["co_primary_G12"][name]
        assert values.tolist() == saved["tissue_differences"] and float(values.mean()) == saved["mean"]
        assert interval == saved["paired_tissue_bootstrap_97_5"] and supported == saved["supported"]
        contrasts[name] = {"mean": float(values.mean()), "interval": interval, "supported": supported}
    flags = tuple(contrasts[k]["supported"] for k in ("body_compatibility", "reference_quality"))
    label = {(True, True): "BODY_AND_REFERENCE_LIMITATIONS", (True, False): "BODY_LIMITATION_ONLY",
             (False, True): "REFERENCE_LIMITATION_ONLY", (False, False): "NO_QUALIFIED_COMMON_BIRTH_LEAD"}[flags]
    assert label == study["classification"]["label"]
    diagnostic = json.loads((source / "retained_diagnostics.json").read_text())
    labels = np.repeat(np.arange(4), 8)
    indices = np.arange(32)
    alpha = .998**1000
    for row in diagnostic["rows"]:
        data = independent.arrays(root / "outputs" / SOURCE_ID / f"tissue_{row['tissue']}" / f"g{row['generation']:02d}" / f"{row['arm']}_states.npz")
        grouped = data["s1000_R"].reshape(4, 8, 16, 16)
        residual = (grouped - grouped.mean(axis=0)[None]).reshape(32, 16, 16)
        scores, decoded = independent.probabilities(data["s1000_R"], codes)
        birth_scores, _ = independent.probabilities(data["s0_R"], codes)
        _, centered = independent.probabilities(residual, codes)
        actual = {"birth_body_mean": data["s0_V"].mean(), "final_body_mean": data["s1000_V"].mean(),
                  "final_positive_fraction": (data["s1000_V"] > 0).mean(), "raw_reference_accuracy": decoded[indices, labels].mean(),
                  "oracle_centered_reference_accuracy": centered[indices, labels].mean(), "oracle_residual_rms": np.sqrt((residual**2).mean()),
                  "reference_rms": np.sqrt((data["s1000_R"]**2).mean()), "birth_true_projection": birth_scores[indices, labels].mean(),
                  "final_true_projection": scores[indices, labels].mean(), "direct_carry_projection": alpha * birth_scores[indices, labels].mean(),
                  "implied_body_history_projection": ((scores-alpha*birth_scores)/(1-alpha))[indices, labels].mean()}
        for key, value in actual.items():
            np.testing.assert_allclose(row[key], value, rtol=0., atol=1e-12)
    record = {"run_id": AUDIT_ID, "source_run": RUN_ID, "checked_utc": utc_now(), "passes": True,
              "source_input_hashes_verified": input_count, "source_output_hashes_verified": output_count,
              "raw_snapshots_rescored": len(stages), "world_rows_rescored": len(stages)*32,
              "retrospective_rows_rescored": len(diagnostic["rows"]), "co_primary_G12": contrasts,
              "classification": label, "stages": stages, "G12_tissues": endpoints, "new_simulations": 0}
    output.mkdir(parents=True)
    atomic_json(output / "rescore.json", record, root)
    write_hash_manifest([Path(__file__).resolve(), Path(independent.__file__).resolve(), source / "input_hashes.sha256", source / "output_hashes.sha256", run / "STATUS.json", run / "COMPLETE"], output / "input_hashes.sha256", root)
    write_hash_manifest([output / "rescore.json", output / "input_hashes.sha256"], output / "output_hashes.sha256", root)
    print(json.dumps({k: v for k, v in record.items() if k not in ("stages", "G12_tissues")}, indent=2))


if __name__ == "__main__":
    main()
