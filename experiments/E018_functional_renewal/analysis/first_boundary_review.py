"""Descriptive review of saved E018 data; no simulation or parameter selection.

All percentages describe the retained cohort. Writing-step output margins are
diagnostics, not new functional assays or replacements for the frozen endpoint.
"""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE.parent / "runs" / "renewal_v1"
DEST = HERE / "first_boundary_review_v1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ports(v):
    return np.stack((v[..., 3:5, 10:12].mean(axis=(-2, -1)),
                     v[..., 11:13, 10:12].mean(axis=(-2, -1))), axis=-1)


def margins(values):
    # Values end in founder, lineage, cue, output; any leading time axis stays.
    desired = np.array([1., -1., 1., -1.])[:, None, None] * np.array([1., -1.])[None, None, :]
    return np.minimum(desired * values[..., 0], -desired * values[..., 1])


def decode(packet):
    return np.frombuffer(packet.tobytes(), dtype="<f8").reshape(*packet.shape[:-1], 2, 16, 16)


def main():
    if DEST.exists():
        raise FileExistsError(DEST)
    complete = json.loads((RUN / "COMPLETE.json").read_text())
    audit = json.loads((RUN / "INDEPENDENT_AUDIT.json").read_text())
    job = json.loads((HERE.parent / "jobs" / "renewal_v1" / "status.json").read_text())
    assert digest(RUN / "COMPLETE.json") == audit["complete_sha256"] == job["scientific_complete_sha256"]
    assert digest(RUN / "INDEPENDENT_AUDIT.json") == job["audit_sha256"]
    assert audit["status"] == "PASS" and job["status"] == "COMPLETE"
    manifest = json.loads((RUN / "manifest.json").read_text())
    for name, expected in manifest["inputs_sha256"].items():
        assert digest(ROOT / name) == expected, name
    checked = {}

    def verify(name):
        value = digest(RUN / name)
        assert value == complete["outputs_sha256"][name], name
        checked[name] = value

    verify("summary.json")
    verify("observations.csv")
    summary = json.loads((RUN / "summary.json").read_text())
    blocks = summary["blocks"]
    threshold = summary["cfg"]["margin"]
    assert len(blocks) == 32 and threshold == .25
    assert summary["cfg"]["recipients"] == 4
    steps = (0, 1, 4, 8, 16, 32, 64, 128)
    rowsets, read_successes, write_successes = [], [], []
    negative_fractions, sign_changes, byte_replays = [], [], 0
    for block in blocks:
        name = f"boundary_{block:06d}_g1.npz"
        verify(name)
        with np.load(RUN / name, allow_pickle=False) as z:
            developed = z["developed_end"][0]
            states = z["write_states"][:, 0]
            reading = z["developed_late_ports"][:, 0].mean(axis=0)
            assert states.shape == (128, 4, 4, 2, 16, 16)
            values = ports(states)
            before = margins(ports(developed))
            during = margins(values)
            initial_ok = (margins(reading) > threshold).all(axis=-1)
            final_ok = (margins(values[-32:].mean(axis=0)) > threshold).all(axis=-1)
            read_successes.extend(initial_ok.ravel().tolist())
            write_successes.extend(final_ok.ravel().tolist())
            records = {}
            for step in steps:
                m = before if step == 0 else during[step-1]
                records[str(step)] = {
                    "both_cue_output_successes": int((m > threshold).all(axis=-1).sum()),
                    "mean_signed_margin": float(m.mean()),
                }
            old, new = decode(z["incoming"][0]), decode(z["outgoing"][0])
            negative_fractions.append([float((old < 0).mean()), float((new < 0).mean())])
            sign_changes.append(float(((old < 0) != (new < 0)).mean()))
            # Reconstruct the stored writer accumulation in its original order.
            total = np.zeros((4, 4, 2, 2, 16, 16))
            for v in states:
                x = np.tanh(3. * v)
                total += np.stack((x * np.roll(x, -1, -1), x * np.roll(x, -1, -2)), axis=-3)
            rebuilt = total.mean(axis=2) / 128
            assert np.array_equal(rebuilt, new), block
            byte_replays += 1
            rowsets.append({"block": block, "steps": records,
                            "reading_both_cue_successes": int(initial_ok.sum()),
                            "last32_writing_both_cue_output_successes": int(final_ok.sum())})

    assays = {}
    with (RUN / "observations.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["damage"] != "intact" or row["arm"] != "own":
                continue
            key = (int(row["horizon"]), row["condition"])
            sample = tuple(int(row[k]) for k in ("block", "founder", "lineage"))
            assays.setdefault(key, {}).setdefault(sample, []).append(bool(int(row["success"])))
    assert all(len(v) == 2 for panel in assays.values() for v in panel.values())
    assert all(len(panel) == 512 for panel in assays.values())
    sample_order = sorted(assays[(1, "renewed")])
    h1 = np.array([all(assays[(1, "renewed")][k]) for k in sample_order])
    h3 = np.array([all(assays[(3, "renewed")][k]) for k in sample_order])
    read_ok, write_ok = np.array(read_successes), np.array(write_successes)
    assert len(read_ok) == len(write_ok) == len(h1) == 512
    assert float(h3.mean()) == summary["primary"]["statistics"]["mean"]
    checkpoints = {}
    for step in steps:
        count = sum(r["steps"][str(step)]["both_cue_output_successes"] for r in rowsets)
        checkpoints[str(step)] = {"successes": count, "total": 512,
                                  "percent": 100 * count / 512,
                                  "mean_signed_margin": float(np.mean([r["steps"][str(step)]["mean_signed_margin"] for r in rowsets]))}
    result = {
        "status": "DESCRIPTIVE_SAVED_DATA_REVIEW",
        "utc": datetime.now(timezone.utc).isoformat(),
        "scope": "All first-boundary renewed trajectories and existing intact own-record assays; no new dynamics or assays.",
        "units": {"blocks": 32, "founders": 128, "lineages": 512},
        "reading_last32_both_cue_successes": int(read_ok.sum()),
        "writing_last32_both_cue_output_successes": int(write_ok.sum()),
        "writing_checkpoints": checkpoints,
        "first_boundary_assay_successes": int(h1.sum()),
        "reading_success_then_assay_failure": int((read_ok & ~h1).sum()),
        "writing_success_then_assay_failure": int((write_ok & ~h1).sum()),
        "writing_failure_then_assay_success": int((~write_ok & h1).sum()),
        "h1_h3_transition_counts": {
            "success_success": int((h1 & h3).sum()),
            "success_failure": int((h1 & ~h3).sum()),
            "failure_success": int((~h1 & h3).sum()),
            "failure_failure": int((~h1 & ~h3).sum()),
        },
        "mean_negative_weight_fraction_incoming_outgoing": np.mean(negative_fractions, axis=0).tolist(),
        "mean_weight_sign_change_fraction": float(np.mean(sign_changes)),
        "writer_records_reconstructed_exactly_from_saved_states": byte_replays,
        "limits": ["Post-hoc development diagnosis, not prospective confirmation.",
                   "Writing outputs are directly observed margins under the current cues, not fresh-body functional capacity.",
                   "No intervention separates scaffold effects, capture timing, record representation and subsequent reading.",
                   "Same G1/G3 endpoint labels do not establish continuous or indefinite stability."],
        "block_results": rowsets,
        "provenance": {"script_sha256": digest(Path(__file__)),
                       "complete_sha256": digest(RUN / "COMPLETE.json"),
                       "audit_sha256": digest(RUN / "INDEPENDENT_AUDIT.json"),
                       "checked_outputs": checked,
                       "frozen_input_hashes_verified": len(manifest["inputs_sha256"])},
    }
    with DEST.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("block_results", "provenance")}, indent=2))


if __name__ == "__main__":
    main()
