"""Post hoc, saved-data-only check of interference between teaching episodes.

All 64 founders are retained. Associations use the 16 independent block means;
these exploratory descriptors do not establish causation or change E015 gates.
"""
import csv
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, sha
import numpy as np


def crossing(mask):
    return np.stack((mask ^ np.roll(mask, -1, -1),
                     mask ^ np.roll(mask, -1, -2)))


def main():
    cap_cpus()
    started = time.monotonic()
    source = HERE / "runs/feasibility_v1"
    complete = json.loads((source / "COMPLETE.json").read_text())
    audit = json.loads((source / "INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS"
    assert audit["complete_sha256"] == sha(source / "COMPLETE.json")
    assert sha(source / "summary.json") == complete["outputs_sha256"]["summary.json"]
    summary = json.loads((source / "summary.json").read_text())
    assert summary["selected_gain"] is None
    out = new_run(HERE / "analysis/writer_interference_v1",
        [Path(__file__), ROOT / "common.py", ROOT / "run_python.sh"],
        dict(experiment="E015", mode="post_hoc_saved_data_description", new_simulations=0,
             source_complete_sha256=sha(source / "COMPLETE.json"),
             source_audit_sha256=sha(source / "INDEPENDENT_AUDIT.json"),
             source_blocks=summary["blocks"], criterion_changed=False,
             scope="Per-episode edge cancellation, teaching polarity, boundary strength, and fixed-gain existing performance",
             interpretation="Exploratory associations on 16 independent block means; no causal or confirmatory inference"))
    rows = []
    raw_hashes = {}
    reconstruction_error = 0.
    gain_index = summary["gains"].index(2.)
    own_index = summary["arms"].index("own")
    for block_index, block in enumerate(summary["blocks"]):
        for kind in ("source", "task"):
            name = f"{kind}_{block:06d}.npz"
            digest = sha(source / name)
            assert digest == complete["outputs_sha256"][name]
            raw_hashes[name] = digest
        with np.load(source / f"source_{block:06d}.npz", allow_pickle=False) as raw:
            states = raw["capture_states"]
            weights = raw["weights"]
            ports = raw["ports"]
            rules = raw["rules"]
            cues = raw["cues"]
        # Independent reconstruction of exactly the original local writer.
        activity = np.tanh(summary["cfg"]["writer_beta"] * states)
        edges = np.stack((activity * np.roll(activity, -1, -1),
                          activity * np.roll(activity, -1, -2)), axis=-3)
        episode_weights = edges.mean(axis=1)
        reconstructed = episode_weights.mean(axis=0)
        error = float(np.max(abs(reconstructed - weights)))
        reconstruction_error = max(reconstruction_error, error)
        np.testing.assert_allclose(reconstructed, weights, rtol=0, atol=3e-15)
        separate_strength = abs(episode_weights).mean(axis=(0, 2, 3, 4))
        combined_strength = abs(weights).mean(axis=(1, 2, 3))
        cancellation = 1. - combined_strength / separate_strength
        disagreement = (episode_weights[0] * episode_weights[1] < 0).mean(axis=(1, 2, 3))
        fields = states.mean(axis=1)
        flips = (fields[0] * fields[1] < 0)[:, ~ports.any(axis=0)].mean(axis=1)
        input_edges = crossing(ports[0])
        output_edges = crossing(ports[1]) | crossing(ports[2])
        input_strength = abs(weights[:, input_edges]).mean(axis=1)
        output_strength = abs(weights[:, output_edges]).mean(axis=1)
        with np.load(source / f"task_{block:06d}.npz", allow_pickle=False) as raw:
            trace = raw["port_trace"]
        values = trace[-summary["cfg"]["observe_steps"]:].mean(axis=0)
        desired = rules[None, :, None, None, None, None] * cues[None, None, None, :, None, None]
        strict = ((desired * values[..., 0] > summary["cfg"]["margin"]) &
                  (-desired * values[..., 1] > summary["cfg"]["margin"]))
        for g, gain in enumerate(summary["gains"]):
            np.testing.assert_array_equal(strict[g].mean(axis=(0, 1, 2)),
                summary["groups"][str(gain)]["block_accuracy"][block_index])
        own = strict[gain_index, ..., own_index]  # F,R,C,D
        accuracy = own.mean(axis=(1, 2))
        both = own.all(axis=2).mean(axis=1)
        for f in range(len(rules)):
            row = dict(block=block, founder=f, rule=int(rules[f]),
                       edge_sign_disagreement=float(disagreement[f]),
                       lost_absolute_edge_strength_fraction=float(cancellation[f]),
                       teaching_bulk_sign_flip_fraction=float(flips[f]),
                       separate_mean_absolute_edge=float(separate_strength[f]),
                       combined_mean_absolute_edge=float(combined_strength[f]),
                       input_boundary_mean_absolute_edge=float(input_strength[f]),
                       output_boundary_mean_absolute_edge=float(output_strength[f]))
            for d, damage in enumerate(summary["damage"]):
                row[f"gain2_strict_{damage}"] = float(accuracy[f, d])
                row[f"gain2_both_cues_{damage}"] = float(both[f, d])
            rows.append(row)
    assert len(rows) == summary["founders"] == 64
    with (out / "founders.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metrics = list(rows[0])[3:]
    blocks = {key: [float(np.mean([row[key] for row in rows if row["block"] == block]))
                    for block in summary["blocks"]] for key in metrics}
    associations = []
    for x, y in (
        ("lost_absolute_edge_strength_fraction", "gain2_strict_intact"),
        ("lost_absolute_edge_strength_fraction", "gain2_both_cues_intact"),
        ("teaching_bulk_sign_flip_fraction", "gain2_both_cues_intact"),
        ("input_boundary_mean_absolute_edge", "gain2_both_cues_intact"),
    ):
        value = float(np.corrcoef(blocks[x], blocks[y])[0, 1])
        associations.append(dict(x=x, y=y, pearson_r=value, independent_units=16))
    descriptors = {key: dict(mean=float(np.mean(blocks[key])),
                             block_min=float(min(blocks[key])), block_max=float(max(blocks[key])))
                   for key in metrics}
    dump(out / "summary.json", dict(status="EXPLORATORY_ONLY", blocks=summary["blocks"],
        founders=64, source_files_sha256=raw_hashes, max_writer_reconstruction_error=reconstruction_error,
        descriptors=descriptors, block_means=blocks, associations=associations,
        new_simulations=0, feasibility_result="FAIL; unchanged"))
    labels = (
        ("edge_sign_disagreement", "Edges whose signs disagree across teaching episodes", True),
        ("lost_absolute_edge_strength_fraction", "Absolute edge strength lost when episodes are averaged", True),
        ("teaching_bulk_sign_flip_fraction", "Non-port cells reversing teaching polarity with the cue", True),
        ("separate_mean_absolute_edge", "Mean absolute edge before combining episodes", False),
        ("combined_mean_absolute_edge", "Mean absolute stored edge", False),
        ("input_boundary_mean_absolute_edge", "Mean absolute edge crossing the input boundary", False),
        ("output_boundary_mean_absolute_edge", "Mean absolute edge crossing an output boundary", False),
    )
    lines = ["# E015 saved-data check of teaching-episode interference", "",
        "Post hoc and exploratory. All 64 founders in all 16 independent blocks are retained. No new simulation, gain, threshold, or renewal run. The failed feasibility result is unchanged.", "",
        "The local writer averages neighboring-cell correlations from two separately initialized teaching episodes. This diagnostic reconstructs each episode's contribution and measures what their average cancels. It then relates these descriptors to already recorded performance at gain 2.", "",
        "| Descriptor | Cohort mean | Range of block means |",
        "| --- | --- | --- |"]
    for key, label, percent in labels:
        v = descriptors[key]
        scale, unit = (100, "%") if percent else (1, "")
        lines.append(f"| {label} | {scale*v['mean']:.3f}{unit} | {scale*v['block_min']:.3f}–{scale*v['block_max']:.3f}{unit} |")
    lines += ["", "| Association across 16 block means | Pearson r |", "| --- | --- |"]
    for item in associations:
        lines.append(f"| {item['x']} vs {item['y']} | {item['pearson_r']:.3f} |")
    lines += ["", "These are descriptive associations in a previously inspected development cohort, with no confirmatory p values. They cannot distinguish cancellation causing failure from another feature of teaching causing both. Total absolute strength is not a measure of task information: a small set of weakened edges could matter disproportionately. A teaching field need not reverse everywhere to implement the output rule.", "",
        f"The reconstructed combined writer agrees with saved records to maximum absolute error {reconstruction_error:.3g}. Original task scores match the audited block scores exactly. Every raw file was verified against the original COMPLETE hashes. Per-founder values and all block means are retained."]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    finish(out, started, dict(experiment="E015", new_simulations=0, founders=64, independent_blocks=16))
    print((out / "REPORT.md").read_text(), flush=True)


if __name__ == "__main__":
    main()
