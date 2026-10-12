"""Post hoc description of saved failures; no new simulation or criterion change."""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, sha
import numpy as np


def main():
    cap_cpus(); started = time.monotonic()
    source = HERE / "runs/feasibility_v1"
    complete = json.loads((source / "COMPLETE.json").read_text())
    audit = json.loads((source / "INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(source / "COMPLETE.json")
    summary = json.loads((source / "summary.json").read_text())
    assert sha(source / "summary.json") == complete["outputs_sha256"]["summary.json"]
    assert summary["selected_gain"] is None
    output = new_run(HERE / "analysis/saved_output_diagnostic_v1",
        [Path(__file__), ROOT / "common.py", ROOT / "run_python.sh"],
        dict(experiment="E015", mode="post_hoc_saved_output_description", new_simulations=0,
             source_complete_sha256=sha(source / "COMPLETE.json"), source_blocks=summary["blocks"],
             criterion_changed=False, no_selection_or_followup_run=True))
    result = {key: [] for key in ("strict", "correct_signs", "weak_but_correct_signs", "wrong_signs",
                                 "both_cues_strict", "mean_absolute_cue_effect")}
    rules = np.array([1., -1., 1., -1.]).reshape(1, 4, 1, 1, 1, 1)
    cues = np.array([1., -1.]).reshape(1, 1, 1, 2, 1, 1)
    target = rules * cues
    for block in summary["blocks"]:
        name = f"task_{block:06d}.npz"
        assert sha(source / name) == complete["outputs_sha256"][name]
        with np.load(source / name, allow_pickle=False) as raw:
            values = raw["port_trace"][-summary["cfg"]["observe_steps"]:].mean(axis=0)
        a = target * values[..., 0]; b = -target * values[..., 1]
        strict = (a > summary["cfg"]["margin"]) & (b > summary["cfg"]["margin"])
        signs = (a > 0) & (b > 0)
        weak = signs & ~strict
        wrong = ~signs
        assert np.all(strict.astype(int) + weak + wrong == 1)
        for key, metric in (("strict", strict), ("correct_signs", signs),
                            ("weak_but_correct_signs", weak), ("wrong_signs", wrong)):
            result[key].append(metric.mean(axis=(1, 2, 3)))
        result["both_cues_strict"].append(strict.all(axis=3).mean(axis=(1, 2)))
        effect = abs(values[:, :, :, 0] - values[:, :, :, 1]).mean(axis=-1)
        result["mean_absolute_cue_effect"].append(effect.mean(axis=(1, 2)))
    arrays = {key: np.array(value) for key, value in result.items()}
    for g, gain in enumerate(summary["gains"]):
        np.testing.assert_array_equal(arrays["strict"][:, g], summary["groups"][str(gain)]["block_accuracy"])
    for arm in ("communication_off", "source_cut"):
        assert not arrays["mean_absolute_cue_effect"][..., summary["arms"].index(arm)].any()
        assert not arrays["both_cues_strict"][..., summary["arms"].index(arm)].any()
    dump(output / "summary.json", dict(status="DESCRIPTIVE_ONLY", gains=summary["gains"], damage=summary["damage"],
        arms=summary["arms"], blocks=summary["blocks"], block_metrics={k: v.tolist() for k, v in arrays.items()},
        means={k: v.mean(axis=0).tolist() for k, v in arrays.items()},
        interpretation="Relaxed sign-only scores describe errors; they do not replace the frozen margin criterion."))
    lines = ["# E015 saved-output failure description", "",
        "Post hoc, descriptive only. No new bodies, candidate settings or simulations; the feasibility failure remains unchanged.", "",
        "| Gain | Damage | Original strict success | Correct signs, margin ignored | Correct signs but too weak | Wrong sign(s) | Both cues strictly correct for same founder/trial |",
        "| --- | --- | --- | --- | --- | --- | --- |"]
    for g, gain in enumerate(summary["gains"]):
        for d, damage in enumerate(summary["damage"]):
            values = [arrays[key].mean(axis=0)[g, d, 0] for key in
                      ("strict", "correct_signs", "weak_but_correct_signs", "wrong_signs", "both_cues_strict")]
            lines.append(f"| {gain:g} | {damage} | " + " | ".join(f"{100*v:.2f}%" for v in values) + " |")
    lines += ["", "The final column requires the same founder and recipient trial to answer both opposing cues correctly. Input-isolated and communication-off controls have exactly zero cue effect and zero both-cue successes. Single-cue successes in the isolated control therefore do not demonstrate cue-sensitive routing. No new success threshold or mechanism claim is inferred from this diagnostic."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")
    finish(output, started, dict(experiment="E015", new_simulations=0))
    print((output / "REPORT.md").read_text(), flush=True)


if __name__ == "__main__": main()
