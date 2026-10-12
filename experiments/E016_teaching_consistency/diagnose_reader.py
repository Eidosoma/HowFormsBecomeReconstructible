"""Post hoc saved-trace description; no additional simulation or outcome tuning."""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, sha
import numpy as np

CHECKPOINTS = (64, 128, 256, 512)
DRIFT_TOLERANCE = .05
SIGN_WINDOW = 128


def main():
    cap_cpus()
    started = time.monotonic()
    source = HERE / "runs/comparison_v1"
    complete = json.loads((source / "COMPLETE.json").read_text())
    audit = json.loads((source / "INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(source / "COMPLETE.json")
    assert sha(source / "summary.json") == complete["outputs_sha256"]["summary.json"]
    summary = json.loads((source / "summary.json").read_text())
    cfg = summary["cfg"]
    assert cfg["read_steps"] == CHECKPOINTS[-1] and cfg["observe_steps"] == 32
    output = new_run(HERE / "analysis/saved_dynamics_v1",
        [Path(__file__), ROOT / "common.py", ROOT / "run_python.sh"],
        dict(experiment="E016", mode="post_hoc_saved_trace_description", new_simulations=0,
             source_complete_sha256=sha(source / "COMPLETE.json"), source_audit_sha256=sha(source / "INDEPENDENT_AUDIT.json"),
             source_blocks=summary["blocks"], checkpoints=CHECKPOINTS, output_window=32,
             late_drift_definition="Maximum across two ports of difference between final and preceding 32-step means",
             quiet_wrong_definition="Final signed margin below -0.25; late drift below 0.05; neither port changes sign in final 128 steps",
             no_gate_change=True, no_new_primary_test=True))
    result = {key: [] for key in ("checkpoint_accuracy", "checkpoint_both_cues", "failed", "wrong_signs",
              "strongly_wrong", "quiet_strongly_wrong", "same_strong_output_signs_across_cues", "late_drift")}
    hashes = {}
    target = np.array([1., -1., 1., -1.]).reshape(1, 4, 1, 1, 1, 1) * np.array([1., -1.]).reshape(1, 1, 1, 2, 1, 1)
    for b, block in enumerate(summary["blocks"]):
        name = f"task_{block:06d}.npz"
        hashes[name] = sha(source / name)
        assert hashes[name] == complete["outputs_sha256"][name]
        with np.load(source / name, allow_pickle=False) as raw:
            trace = raw["port_trace"]
        at_time, both_time = [], []
        for stop in CHECKPOINTS:
            values = trace[stop-32:stop].mean(axis=0)
            signed_a = target*values[..., 0]
            signed_b = -target*values[..., 1]
            strict = (signed_a > cfg["margin"]) & (signed_b > cfg["margin"])
            at_time.append(strict.mean(axis=(1, 2, 3)))
            both_time.append(strict.all(axis=3).mean(axis=(1, 2)))
        # Last iteration retains exactly the original final scoring window.
        for m, regime in enumerate(summary["regimes"]):
            for d, damage in enumerate(summary["damage"]):
                for a, arm in enumerate(summary["arms"]):
                    assert at_time[-1][m, d, a] == summary["groups"][regime]["accuracy"][damage][arm]["block_means"][b]
                    assert both_time[-1][m, d, a] == summary["groups"][regime]["both_cues"][damage][arm]["block_means"][b]
        failed = ~strict
        wrong = (signed_a <= 0) | (signed_b <= 0)
        strong_wrong = np.minimum(signed_a, signed_b) < -cfg["margin"]
        drift = abs(values - trace[-64:-32].mean(axis=0)).max(axis=-1)
        sign_changed = (np.sign(trace[-SIGN_WINDOW:]) != np.sign(trace[-SIGN_WINDOW])).any(axis=(0, -1))
        quiet_wrong = strong_wrong & (drift < DRIFT_TOLERANCE) & ~sign_changed
        assert not (quiet_wrong & ~failed).any()
        same = ((np.sign(values[:, :, :, 0]) == np.sign(values[:, :, :, 1])).all(axis=-1)
                & (abs(values[:, :, :, 0]) > cfg["margin"]).all(axis=-1)
                & (abs(values[:, :, :, 1]) > cfg["margin"]).all(axis=-1))
        result["checkpoint_accuracy"].append(np.array(at_time))
        result["checkpoint_both_cues"].append(np.array(both_time))
        for key, values_array in (("failed", failed), ("wrong_signs", wrong), ("strongly_wrong", strong_wrong),
                                  ("quiet_strongly_wrong", quiet_wrong), ("late_drift", drift)):
            result[key].append(values_array.mean(axis=(1, 2, 3)))
        result["same_strong_output_signs_across_cues"].append(same.mean(axis=(1, 2)))
    arrays = {key: np.array(values) for key, values in result.items()}
    means = {key: array.mean(axis=0) for key, array in arrays.items()}
    assert len(summary["blocks"]) == 32 and summary["founders"] == 128
    dump(output / "summary.json", dict(status="DESCRIPTIVE_ONLY", blocks=summary["blocks"], founders=128,
        regimes=summary["regimes"], damage=summary["damage"], arms=summary["arms"], checkpoints=CHECKPOINTS,
        source_files_sha256=hashes, block_metrics={key: value.tolist() for key, value in arrays.items()},
        means={key: value.tolist() for key, value in means.items()}, new_simulations=0,
        inference="No equilibrium or premature-commitment mechanism inferred from finite-time port traces."))
    lines = ["# E016 saved response dynamics", "",
        "Post hoc, descriptive only. All 32 blocks and 128 founders retained; all regimes, controls and damage conditions are included in summary.json. No simulation, candidate, criterion or primary test was added.", "",
        "Each checkpoint uses the preceding 32-step output mean and the original strict margin. Later observations are descriptive, not a longer-horizon test.", "",
        "| Own-record regime | Damage | Accuracy at step 64 | Step 128 | Step 256 | Step 512 |",
        "| --- | --- | --- | --- | --- | --- |"]
    for m, regime in enumerate(summary["regimes"]):
        for d, damage in enumerate(summary["damage"]):
            values = means["checkpoint_accuracy"][:, m, d, 0]
            lines.append(f"| {regime} | {damage} | " + " | ".join(f"{100*v:.2f}%" for v in values) + " |")
    lines += ["", "| Own-record regime | Damage | Final failures | Failures with a wrong sign | Failures strongly wrong and quiet late | Same strong output signs for both opposing cues |", "| --- | --- | --- | --- | --- | --- |"]
    for m, regime in enumerate(summary["regimes"]):
        for d, damage in enumerate(summary["damage"]):
            failed = means["failed"][m, d, 0]
            wrong = means["wrong_signs"][m, d, 0]/failed if failed else 0.
            quiet = means["quiet_strongly_wrong"][m, d, 0]/failed if failed else 0.
            same = means["same_strong_output_signs_across_cues"][m, d, 0]
            lines.append(f"| {regime} | {damage} | {100*failed:.2f}% | {100*wrong:.2f}% | {100*quiet:.2f}% | {100*same:.2f}% |")
    lines += ["", "The two failure-subtype columns use all final failures as their denominator. The last column instead uses all matched founder/recipient pairs. A strongly wrong response has at least one requested signed output below -0.25. 'Quiet late' additionally requires less than 0.05 change between the final two 32-step means at both ports, and no output sign change in the last 128 steps. These descriptive cutoffs were chosen after the main outcome was known, before this trace analysis.", "",
        "Quiet wrong outputs during this finite window do not prove a stable whole-body attractor or show when/why commitment occurred. A longer run or a change in the timing of amplification would be a new experiment. Equal output signs do not imply exactly equal amplitudes or no causal input effect. All final scores reproduce the independently audited original block scores exactly; raw file hashes match the scientific COMPLETE receipt."]
    (output / "REPORT.md").write_text("\n".join(lines)+"\n")
    finish(output, started, dict(experiment="E016", new_simulations=0, founders=128, independent_blocks=32))
    print((output / "REPORT.md").read_text(), flush=True)


if __name__ == "__main__":
    main()
