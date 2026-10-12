"""Independent rescoring of the frozen L17 one-boundary raw arrays.

Does not import the experiment's decoder, metric, summary, or bootstrap code.
Writes a separate immutable audit directory; never edits the scientific run.
"""

import json
from pathlib import Path

import numpy as np

from laws_confirmation.io import atomic_json, external_root, sha256_file, utc_now, write_hash_manifest


RUN_ID = "l17_r_channel_one_boundary_v1_attempt1"
AUDIT_ID = RUN_ID + "_independent_rescore_v1"
ARMS = ("copy", "reset", "wrong", "shuffle", "copy_reader_off", "reset_reader_off", "fragment_copy", "fragment_reset")


def manifest_check(path):
    rows = [line.split("  ", 1) for line in path.read_text().splitlines()]
    assert rows and all(sha256_file(Path(p)) == digest for digest, p in rows), path
    return len(rows)


def probabilities(fields, templates):
    scores = fields.reshape(len(fields), -1) @ templates.reshape(4, -1).T / 256
    ties = np.isclose(scores, scores.max(axis=1)[:, None], atol=1e-12, rtol=0.)
    return scores, ties / ties.sum(axis=1)[:, None]


def check_positional(field, target, saved):
    signs = field > 0
    target_positive = target > 0
    active = abs(field) > .2
    p = np.count_nonzero(target_positive) / target.size
    expected_matches = np.where(signs, p, 1 - p)
    calculations = {
        "sign_fidelity": np.count_nonzero(signs == target_positive) / target.size,
        "amplitude_fidelity": np.count_nonzero((signs == target_positive) & active) / target.size,
        "sign_marginal_null": expected_matches.sum() / target.size,
        "amplitude_marginal_null": expected_matches[active].sum() / target.size,
    }
    assert calculations == saved, (calculations, saved)


def main():
    root = external_root()
    source = root / "outputs" / RUN_ID
    output = root / "outputs" / AUDIT_ID
    if output.exists():
        raise FileExistsError("independent audit is immutable")
    status = json.loads((root / "runs" / RUN_ID / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"]
    assert (root / "runs" / RUN_ID / "COMPLETE").is_file()
    assert not (root / "runs" / RUN_ID / "FAILED").exists()
    input_count = manifest_check(source / "input_hashes.sha256")
    output_count = manifest_check(source / "output_hashes.sha256")
    study = json.loads((source / "r_channel.json").read_text())
    first = np.broadcast_to(np.where((np.arange(16) // 4) % 2 == 0, 1., -1.), (16, 16))
    templates = np.asarray([np.roll(first, shift, axis=1) for shift in (0, 2, 4, 6)])
    message = np.repeat(np.arange(4), 8)
    index = np.arange(32)
    row_count, snapshots, tissue_rows, stage_totals = 0, 0, [], []
    for tissue in range(10000, 10008):
        directory = source / f"tissue_{tissue}"
        acquired = json.loads((directory / "acquired.json").read_text())
        calibration = json.loads((directory / "calibration.json").read_text())
        with np.load(directory / "parent_states.npz", allow_pickle=False) as loaded:
            parent = {k: loaded[k].copy() for k in loaded.files}
        with np.load(directory / "newborn.npz", allow_pickle=False) as loaded:
            newborn = {k: loaded[k].copy() for k in loaded.files}
        with np.load(directory / "fragment_regrown_mask.npz", allow_pickle=False) as loaded:
            fresh = loaded["fresh"].copy()
        final = {}
        for arm in (*ARMS, "injected", "injected_reader_off"):
            saved = acquired if arm in ARMS else calibration
            with np.load(directory / f"{arm}_states.npz", allow_pickle=False) as states:
                for timepoint in (0, 50, 250, 500, 1000):
                    body, reference = states[f"s{timepoint}_V"], states[f"s{timepoint}_R"]
                    scores, decoded = probabilities(body, templates)
                    r_scores, r_decoded = probabilities(reference, templates)
                    rows = [r for r in saved["rows"][arm] if r["sweep"] == timepoint]
                    assert [(r["message"], r["replicate"]) for r in rows] == [(int(m), int(i % 8)) for i, m in enumerate(message)]
                    np.testing.assert_allclose(scores, [r["body_scores"] for r in rows], atol=1e-12, rtol=0.)
                    np.testing.assert_allclose(r_scores, [r["reference_scores"] for r in rows], atol=1e-12, rtol=0.)
                    np.testing.assert_array_equal(decoded, [r["body_probabilities"] for r in rows])
                    np.testing.assert_array_equal(r_decoded, [r["reference_probabilities"] for r in rows])
                    for i, row in enumerate(rows):
                        check_positional(body[i], templates[message[i]], row["intended_pattern"])
                        if arm in ARMS:
                            check_positional(body[i], parent["after_render_V"][i], row["rendered_parent"])
                        if arm.startswith("fragment"):
                            check_positional(body[i][fresh[i]], templates[message[i]][fresh[i]], row["regrown_intended_pattern"])
                            check_positional(body[i][fresh[i]], parent["after_render_V"][i][fresh[i]], row["regrown_rendered_parent"])
                    accuracy = decoded[index, message].mean()
                    assert accuracy == saved["summaries"][arm][str(timepoint)]["body_accuracy"]
                    row_count += len(rows)
                    snapshots += 1
                    stage_totals.append({"tissue": tissue, "arm": arm, "sweep": timepoint,
                                         "body_accuracy": float(accuracy),
                                         "reference_accuracy": float(r_decoded[index, message].mean()),
                                         "mean_intended_sign_fidelity": float(np.mean([r["intended_pattern"]["sign_fidelity"] for r in rows])),
                                         "mean_ancestor_amplitude_fidelity": float(np.mean([r["rendered_parent"]["amplitude_fidelity"] for r in rows])) if arm in ARMS else None})
                    if timepoint == 0 and arm in ARMS[:6]:
                        np.testing.assert_array_equal(body, newborn["newborn_V"])
                        np.testing.assert_array_equal(states["s0_ema"], newborn["newborn_ema"])
                    if timepoint == 1000:
                        final[arm] = float(accuracy)
                        if arm == "wrong":
                            final["wrong_donor"] = float(decoded[index, (message + 1) % 4].mean())
        assert final["reset"] == final["copy_reader_off"] == final["reset_reader_off"] == final["injected_reader_off"] == .25
        assert final["wrong_donor"] == final["copy"]
        _, parent_decoded = probabilities(parent["after_render_R"], templates)
        tissue_rows.append({"tissue": tissue, **final, "parent_reference_accuracy": float(parent_decoded[index, message].mean())})
    contrasts = {}
    for number, (name, left, right) in enumerate((
        ("primary_copy_minus_reset", "copy", "reset"),
        ("specificity_copy_minus_wrong", "copy", "wrong"),
        ("wrong_donor_following", "wrong_donor", "wrong"),
    )):
        differences = np.asarray([r[left] - r[right] for r in tissue_rows])
        draws = np.random.default_rng(202609071701 + number).integers(0, 8, (10000, 8))
        interval = np.quantile(differences[draws].mean(axis=1), [.025, .975]).tolist()
        assert float(differences.mean()) == study["classification"][name]["mean"]
        assert interval == study["classification"][name]["paired_tissue_bootstrap_95"]
        contrasts[name] = {"mean": float(differences.mean()), "interval": interval}
    record = {"run_id": AUDIT_ID, "source_run": RUN_ID, "checked_utc": utc_now(), "passes": True,
              "source_input_hashes_verified": input_count, "source_output_hashes_verified": output_count,
              "raw_state_snapshots_rescored": snapshots, "per_world_rows_rescored": row_count,
              "tissues": tissue_rows, "stage_summaries": stage_totals, "contrasts": contrasts,
              "classification": study["classification"]["label"], "new_simulations": 0,
              "audit_script_sha256": sha256_file(Path(__file__))}
    output.mkdir(parents=True)
    atomic_json(output / "rescore.json", record, root)
    write_hash_manifest([Path(__file__).resolve(), source / "input_hashes.sha256", source / "output_hashes.sha256"], output / "input_hashes.sha256", root)
    write_hash_manifest([output / "rescore.json", output / "input_hashes.sha256"], output / "output_hashes.sha256", root)
    print(json.dumps({k: v for k, v in record.items() if k not in ("stage_summaries", "tissues")}, indent=2))


if __name__ == "__main__":
    main()
