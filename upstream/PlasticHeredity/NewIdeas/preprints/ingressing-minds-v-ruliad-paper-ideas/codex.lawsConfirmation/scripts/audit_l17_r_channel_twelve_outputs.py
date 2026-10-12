"""Independent raw-array rescore; no experiment decoder/metrics are imported."""

import hashlib
import json
from pathlib import Path

import numpy as np

from laws_confirmation.io import atomic_json, external_root, sha256_file, utc_now, write_hash_manifest


RUN_ID = "l17_r_channel_twelve_boundary_v1_attempt1"
SOURCE_ID = "l17_r_channel_one_boundary_v1_attempt1"
AUDIT_ID = RUN_ID + "_independent_rescore_v1"
ARMS = ("fresh_renew", "fresh_reset", "fresh_wrong_seed", "fresh_ancestor_rescue",
        "fresh_reader_off", "fresh_reset_reader_off", "fragment_renew", "fragment_reset", "fragment_ancestor_rescue")
CAL_ARMS = ("injected", "injected_reader_off")
ANCHORS = dict(zip(ARMS, ("copy", "reset", "wrong", "copy", "copy_reader_off", "reset_reader_off", "fragment_copy", "fragment_reset", "fragment_copy")))


def arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {k: data[k].copy() for k in data.files}


def manifest_check(path):
    rows = [line.split("  ", 1) for line in path.read_text().splitlines()]
    assert rows and all(sha256_file(Path(p)) == digest for digest, p in rows), path
    return len(rows)


def probabilities(fields, templates):
    scores = fields.reshape(len(fields), -1) @ templates.reshape(4, -1).T / 256
    ties = np.isclose(scores, scores.max(axis=1)[:, None], atol=1e-12, rtol=0.)
    return scores, ties / ties.sum(axis=1)[:, None]


def positional(field, target):
    if not target.size:
        return None
    signs, desired, active = field > 0, target > 0, abs(field) > .2
    fraction = np.count_nonzero(desired) / target.size
    expected = np.where(signs, fraction, 1 - fraction)
    return {"sign_fidelity": float(np.count_nonzero(signs == desired) / target.size),
            "amplitude_fidelity": float(np.count_nonzero((signs == desired) & active) / target.size),
            "sign_marginal_null": float(expected.sum() / target.size),
            "amplitude_marginal_null": float(expected[active].sum() / target.size)}


def check_metrics(actual, saved):
    assert (actual is None) == (saved is None)
    if actual is not None:
        assert set(actual) == set(saved)
        for key in actual:
            np.testing.assert_allclose(actual[key], saved[key], rtol=0., atol=1e-15)


def digest(array):
    value = np.ascontiguousarray(array)
    return hashlib.sha256(f"{value.dtype}:{value.shape}:".encode() + value.tobytes()).hexdigest()


def check_snapshot(state, rows, summary, templates, ancestor=None, parent=None, growth=None):
    labels, indices = np.repeat(np.arange(4), 8), np.arange(32)
    assert [(r["message"], r["replicate"]) for r in rows] == [(int(m), int(i % 8)) for i, m in enumerate(labels)]
    assert all(np.isfinite(a).all() for a in state.values())
    vs, vp = probabilities(state["V"], templates)
    rs, rp = probabilities(state["R"], templates)
    for name, scores, prob in (("body", vs, vp), ("reference", rs, rp)):
        np.testing.assert_allclose(scores, [r[f"{name}_scores"] for r in rows], atol=1e-12, rtol=0.)
        np.testing.assert_array_equal(prob, [r[f"{name}_probabilities"] for r in rows])
        assert float(prob[indices, labels].mean()) == summary[f"{name}_accuracy"]
    for i, row in enumerate(rows):
        v, reference, message = state["V"][i], state["R"][i], labels[i]
        assert row["body_accuracy"] == vp[i, message] and row["reference_accuracy"] == rp[i, message]
        assert row["wrong_donor_body_accuracy"] == vp[i, (message + 1) % 4]
        assert row["wrong_donor_reference_accuracy"] == rp[i, (message + 1) % 4]
        assert row["body_sha256"] == digest(v) and row["reference_sha256"] == digest(reference)
        np.testing.assert_allclose(row["reference_rms"], np.sqrt((reference**2).mean()), rtol=0., atol=1e-15)
        np.testing.assert_allclose(row["reference_true_margin"], rs[i, message] - np.delete(rs[i], message).max(), rtol=0., atol=1e-12)
        check_metrics(positional(v, templates[message]), row["intended_pattern"])
        for name, target in (("fixed_ancestor", ancestor), ("immediate_parent", parent)):
            if target is None:
                continue
            check_metrics(positional(v, target["V"][i]), row[name])
            if growth is not None:
                for suffix, mask in (("newly_regrown", growth["fresh"][i]), ("regrown1", growth["counts"][i] >= 1), ("regrown2", growth["counts"][i] >= 2)):
                    saved = row[f"{name}_{suffix}"]
                    assert saved["cells"] == int(mask.sum())
                    check_metrics(positional(v[mask], target["V"][i][mask]), saved["metrics"])
        if growth is not None:
            mask = growth["fresh"][i]
            assert row["intended_newly_regrown"]["cells"] == int(mask.sum())
            check_metrics(positional(v[mask], templates[message][mask]), row["intended_newly_regrown"]["metrics"])
    for key in ("reference_rms", "reference_true_margin", "wrong_donor_reference_accuracy", "wrong_donor_body_accuracy", "active_fraction"):
        np.testing.assert_allclose(summary[key], np.mean([r[key] for r in rows]), rtol=0., atol=1e-15)
    for key in ("intended_pattern", "fixed_ancestor", "immediate_parent"):
        if key in rows[0]:
            check_metrics({m: float(np.mean([r[key][m] for r in rows])) for m in rows[0][key]}, summary[key])
    for name in ("fixed_ancestor", "immediate_parent"):
        for suffix in ("newly_regrown", "regrown1", "regrown2"):
            key = f"{name}_{suffix}"
            if key in rows[0]:
                valid = [r[key]["metrics"] for r in rows if r[key]["cells"]]
                assert summary[key]["valid_worlds"] == len(valid)
                check_metrics({m: float(np.mean([v[m] for v in valid])) for m in valid[0]} if valid else None, summary[key]["metrics"])
    return {"body_accuracy": float(vp[indices, labels].mean()), "reference_accuracy": float(rp[indices, labels].mean()),
            "fixed_ancestor_amplitude": summary.get("fixed_ancestor", {}).get("amplitude_fidelity"),
            "immediate_parent_amplitude": summary.get("immediate_parent", {}).get("amplitude_fidelity"),
            "reference_rms": summary["reference_rms"], "reference_true_margin": summary["reference_true_margin"]}


def main():
    root = external_root()
    source, output = root / "outputs" / RUN_ID, root / "outputs" / AUDIT_ID
    if output.exists():
        raise FileExistsError("independent audit is immutable")
    run = root / "runs" / RUN_ID
    status = json.loads((run / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"]
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
    input_count = manifest_check(source / "input_hashes.sha256")
    output_count = manifest_check(source / "output_hashes.sha256")
    study = json.loads((source / "r_channel_twelve.json").read_text())
    assert study["completed_cleanly"] and all(study["completion_gates"].values())
    first = np.broadcast_to(np.where((np.arange(16) // 4) % 2 == 0, 1., -1.), (16, 16))
    templates = np.asarray([np.roll(first, shift, axis=1) for shift in (0, 2, 4, 6)])
    qualified = study["instrument_qualified"]
    stage_rows, final_tissues, positives = [], [], []
    for tissue in range(10000, 10008):
        directory = source / f"tissue_{tissue}"
        original = root / "outputs" / SOURCE_ID / f"tissue_{tissue}"
        raw_ancestor = arrays(original / "parent_states.npz")
        ancestor = {k: raw_ancestor[f"after_render_{k}"] for k in ("V", "ema", "R")}
        parents = {a: ancestor for a in ARMS}
        cumulative = np.zeros((32, 16, 16), dtype=np.int32)
        tissue_final, tissue_positive = {}, []
        for generation in range(1, 13):
            gd = directory / f"g{generation:02d}"
            cal = json.loads((gd / "calibration.json").read_text())
            assert cal["passes"] and all(cal["structural_gates"].values())
            body = arrays(gd / "newborn.npz")
            assert all(np.array_equal(a.reshape(4, 8, 16, 16), np.repeat(a[:8][None], 4, axis=0)) for a in body.values())
            lineage = json.loads((gd / "lineage.json").read_text()) if qualified else None
            growth = arrays(gd / "regrowth.npz") if qualified else None
            if qualified:
                assert lineage["passes"] and all(lineage["structural_gates"].values())
                assert growth["fresh"].dtype == bool and np.all(growth["fresh"].sum(axis=(1, 2)) == 128)
                cumulative += growth["fresh"]
                np.testing.assert_array_equal(cumulative, growth["counts"])
            snapshots = {}
            for arm in (*CAL_ARMS, *(ARMS if qualified else ())):
                raw = arrays(gd / f"{arm}_states.npz")
                snapshots[arm] = raw
                saved = cal if arm in CAL_ARMS else lineage
                if generation == 1:
                    anchor = arrays(original / f"{ANCHORS.get(arm, arm)}_states.npz")
                    for k in raw:
                        np.testing.assert_array_equal(raw[k], anchor[k])
                for sweep in (0, 50, 1000):
                    state = {k: raw[f"s{sweep}_{k}"] for k in ("V", "ema", "R")}
                    rows = [r for r in saved["rows"][arm] if r["sweep"] == sweep]
                    result = check_snapshot(state, rows, saved["summaries"][arm][str(sweep)], templates,
                        ancestor if arm in ARMS else None, parents[arm] if arm in ARMS else None,
                        growth if arm.startswith("fragment") else None)
                    stage_rows.append({"tissue": tissue, "generation": generation, "arm": arm, "sweep": sweep, **result})
                    if arm in ("injected_reader_off", "fresh_reset", "fresh_reader_off", "fresh_reset_reader_off"):
                        assert result["body_accuracy"] == .25
                        v = state["V"].reshape(4, 8, 16, 16)
                        assert all(np.array_equal(v[0], v[m]) for m in range(1, 4))
                    if arm in CAL_ARMS:
                        np.testing.assert_array_equal(state["R"], np.repeat(templates, 8, axis=0) * 3.)
                    if sweep == 0 and arm in (*CAL_ARMS, *ARMS[:6]):
                        for k in ("V", "ema"):
                            np.testing.assert_array_equal(state[k], body[k])
                    if sweep == 1000:
                        if arm == "injected":
                            tissue_positive.append(result["body_accuracy"])
                        if generation == 12 and arm in ARMS:
                            tissue_final[arm] = result
                if arm in ARMS:
                    if "reset" in arm:
                        expected = body["R"]
                    elif arm.endswith("ancestor_rescue"):
                        expected = ancestor["R"]
                    elif arm == "fresh_wrong_seed" and generation == 1:
                        expected = np.concatenate((ancestor["R"][8:], ancestor["R"][:8]))
                    else:
                        expected = parents[arm]["R"]
                    np.testing.assert_array_equal(raw["s0_R"], expected)
                    assert lineage["reference_links"][arm]["birth_sha256"] == digest(expected)
                    assert lineage["reference_links"][arm]["expected_sha256"] == digest(expected)
            if qualified:
                for sweep in (0, 50, 1000):
                    for k in ("V", "ema", "R"):
                        value = snapshots["fresh_renew"][f"s{sweep}_{k}"]
                        np.testing.assert_array_equal(snapshots["fresh_wrong_seed"][f"s{sweep}_{k}"], np.concatenate((value[8:], value[:8])))
                    for k in ("V", "ema"):
                        np.testing.assert_array_equal(snapshots["fresh_reader_off"][f"s{sweep}_{k}"], snapshots["fresh_reset_reader_off"][f"s{sweep}_{k}"])
                if generation == 1:
                    for arm in ARMS[6:]:
                        np.testing.assert_array_equal(snapshots[arm]["s0_V"], snapshots["fragment_renew"]["s0_V"])
                parents = {a: {k: snapshots[a][f"s1000_{k}"] for k in ("V", "ema", "R")} for a in ARMS}
        positives.append(tissue_positive)
        if qualified:
            final_tissues.append({"tissue": tissue, "arms": tissue_final})
    positive_array = np.asarray(positives)
    assert qualified == (bool((positive_array > .25).all()) and bool((positive_array.mean(axis=0) >= .75).all()))
    contrasts = {}
    if qualified:
        for n, kind in enumerate(("body", "reference")):
            differences = np.asarray([r["arms"]["fresh_renew"][f"{kind}_accuracy"] - r["arms"]["fresh_reset"][f"{kind}_accuracy"] for r in final_tissues])
            draws = np.random.default_rng(20260907171201 + n).integers(0, 8, (10000, 8))
            interval = np.quantile(differences[draws].mean(axis=1), [.0125, .9875]).tolist()
            supported = interval[0] > 0 and int((differences > 0).sum()) >= 6
            saved = study["classification"]["co_primary_G12"][kind]
            assert differences.tolist() == saved["tissue_differences"]
            assert float(differences.mean()) == saved["mean"] and interval == saved["paired_tissue_bootstrap_97_5"]
            assert supported == saved["supported"] and int((differences > 0).sum()) == saved["positive_tissues"]
            contrasts[kind] = {"mean": float(differences.mean()), "interval": interval, "supported": supported}
        flags = tuple(contrasts[k]["supported"] for k in ("body", "reference"))
        expected_label = {(True, True): "BODY_AND_REFERENCE_PERSIST_G12", (False, True): "REFERENCE_ONLY_DETECTED_G12",
                          (True, False): "BODY_ONLY_DETECTED_G12", (False, False): "NO_QUALIFIED_G12_MESSAGE_LEAD"}[flags]
    else:
        expected_label = "INSTRUMENT_NOT_QUALIFIED"
    assert expected_label == study["classification"]["label"]
    record = {"run_id": AUDIT_ID, "source_run": RUN_ID, "checked_utc": utc_now(), "passes": True,
              "source_input_hashes_verified": input_count, "source_output_hashes_verified": output_count,
              "raw_state_snapshots_rescored": len(stage_rows), "per_world_rows_rescored": len(stage_rows) * 32,
              "stage_summaries": stage_rows, "G12_tissues": final_tissues, "co_primary_G12": contrasts,
              "classification": expected_label, "new_simulations": 0, "audit_script_sha256": sha256_file(Path(__file__).resolve())}
    output.mkdir(parents=True)
    atomic_json(output / "rescore.json", record, root)
    write_hash_manifest([Path(__file__).resolve(), source / "input_hashes.sha256", source / "output_hashes.sha256", run / "STATUS.json", run / "COMPLETE"], output / "input_hashes.sha256", root)
    write_hash_manifest([output / "rescore.json", output / "input_hashes.sha256"], output / "output_hashes.sha256", root)
    print(json.dumps({k: v for k, v in record.items() if k not in ("stage_summaries", "G12_tissues")}, indent=2))


if __name__ == "__main__":
    main()
