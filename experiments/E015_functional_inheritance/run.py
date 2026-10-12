"""Bounded two-gain functional feasibility study; no outcome-driven extensions."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, rng, sha, utc
from E015_functional_inheritance import model as tissue
import numpy as np

BLOCKS = tuple(range(13000, 13016))
BENCHMARK = 900015
CSV_FIELDS = ("block", "gain", "founder", "rule", "recipient", "cue", "damage", "arm",
              "success", "margin", "output_A", "output_B")


def input_paths():
    return [ROOT / x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json", "SOURCE_LICENSE.txt")] + [
        HERE / x for x in ("model.py", "run.py", "audit.py", "tests.py", "plot.py", "PROTOCOL.md")]


def save_block(output, block, cfg=tissue.CFG):
    started = time.monotonic(); cap_cpus()
    source = tissue.teach(block, cfg)
    source_path = output / f"source_{block:06d}.npz"
    np.savez_compressed(source_path, **source)
    packets, permutations = tissue.initial_packets(source["acquired"], block, cfg)
    raw = tissue.read(packets, block, "feasibility", cfg=cfg)
    raw["permutations"] = permutations
    np.savez_compressed(output / f"task_{block:06d}.npz", **raw)
    dump(output / f"worker_{block}.json", dict(block=block, seconds=time.monotonic() - started,
        source_file=str(source_path.relative_to(ROOT)), source_sha256=sha(source_path)))


def statistics(values):
    x = np.asarray(values, dtype=float)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    draws = rng("E015", "bootstrap", "feasibility").integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws].mean(axis=1), [.025, .975]).tolist(),
                block_means=x.tolist())


def analyze(output, ids, technical, cfg=tissue.CFG):
    block_accuracy, rule_accuracy, block_margin = [], [], []
    with (output / "observations.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS); writer.writeheader()
        for block in ids:
            with np.load(output / f"task_{block:06d}.npz", allow_pickle=False) as raw:
                success, margin, values = tissue.score(raw["port_trace"], cfg)
            block_accuracy.append(success.mean(axis=(1, 2, 3)))
            rule_accuracy.append(np.stack([success[:, [r, r+2]].mean(axis=(1, 2, 3)) for r in range(2)], axis=1))
            block_margin.append(margin.mean(axis=(1, 2, 3)))
            for g, gain in enumerate(tissue.GAINS):
                for f in range(4):
                    for r in range(cfg.recipients):
                        for c, cue in enumerate(tissue.CUES):
                            for d, damage in enumerate(tissue.DAMAGE):
                                for a, arm in enumerate(tissue.ARMS):
                                    writer.writerow(dict(block=block, gain=gain, founder=f, rule=int(tissue.RULES[f]),
                                        recipient=r, cue=int(cue), damage=damage, arm=arm,
                                        success=int(success[g, f, r, c, d, a]), margin=float(margin[g, f, r, c, d, a]),
                                        output_A=float(values[g, f, r, c, d, a, 0]), output_B=float(values[g, f, r, c, d, a, 1])))
    x = np.asarray(block_accuracy); by_rule = np.asarray(rule_accuracy); margins = np.asarray(block_margin)
    groups = {}
    for g, gain in enumerate(tissue.GAINS):
        accuracy = {damage: {arm: statistics(x[:, g, d, a]) for a, arm in enumerate(tissue.ARMS)}
                    for d, damage in enumerate(tissue.DAMAGE)}
        contrasts = {damage: {arm: statistics(x[:, g, d, 0] - x[:, g, d, a])
                    for a, arm in enumerate(tissue.ARMS) if a} for d, damage in enumerate(tissue.DAMAGE)}
        rules = {str(int(rule)): {damage: statistics(by_rule[:, g, r, d, 0]) for d, damage in enumerate(tissue.DAMAGE)}
                 for r, rule in enumerate((1, -1))}
        gates = {f"accuracy_rule_{rule}_{damage}": rules[str(rule)][damage]["ci95"][0] > .75
                 for rule in (1, -1) for damage in tissue.DAMAGE}
        gates.update({f"advantage_{damage}_{arm}": contrasts[damage][arm]["ci95"][0] > .10
                      for damage in tissue.DAMAGE for arm in tissue.ARMS[1:]})
        groups[str(gain)] = dict(gain=gain, block_accuracy=x[:, g].tolist(), block_rule_accuracy=by_rule[:, g].tolist(),
            block_margin=margins[:, g].tolist(), accuracy=accuracy, contrasts=contrasts, own_accuracy_by_rule=rules,
            gates=gates, all_gates_pass=all(gates.values()))
    eligible = [gain for gain in tissue.GAINS if groups[str(gain)]["all_gates_pass"]]
    selected = None if technical or not eligible else eligible[0]
    summary = dict(experiment="E015", stage="feasibility", blocks=list(ids), founders=len(ids) * 4,
        status="TECHNICAL_ONLY" if technical else "FUNCTIONAL_FEASIBILITY_PASSED" if eligible else "FUNCTIONAL_FEASIBILITY_NOT_ESTABLISHED",
        evidence_status="technical" if technical else "bounded_development", selected_gain=selected,
        gains=tissue.GAINS, arms=tissue.ARMS, damage=tissue.DAMAGE, groups=groups,
        packet_bytes=4096, trained_rules=[1, -1], cfg=asdict(cfg),
        interval_scope="Pointwise whole-block development intervals; no confirmatory claim")
    dump(output / "summary.json", summary)
    report(output, summary)
    return summary


def report(output, summary):
    fmt = lambda st: f"{100*st['mean']:.1f} [{100*st['ci95'][0]:.1f}, {100*st['ci95'][1]:.1f}]"
    lines = ["# E015 functional feasibility", "", f"**{summary['status']}**", "",
        f"{len(summary['blocks'])} blocks, {summary['founders']} founders; all cases retained. "
        f"Selected reader gain: `{summary['selected_gain']}`. Development only.", "",
        "Success requires correct opposing output polarities beyond ±0.25. Both cues are tested in fresh bodies; output teachers are absent."]
    for gain in summary["gains"]:
        group = summary["groups"][str(gain)]
        lines += ["", f"## Reader gain {gain}", "", f"All criteria passed: `{group['all_gates_pass']}`.", "",
            "| Record/control | Intact accuracy %, [95%] | Scattered damage | Square damage |",
            "| --- | --- | --- | --- |"]
        for arm in summary["arms"]:
            lines.append("| " + arm + " | " + " | ".join(fmt(group["accuracy"][d][arm]) for d in summary["damage"]) + " |")
        lines += ["", "Own-record performance by taught rule:", ""]
        for rule, values in group["own_accuracy_by_rule"].items():
            lines.append(f"- Rule {rule}: " + "; ".join(f"{d}: {fmt(values[d])}%" for d in summary["damage"]) + ".")
        failed = [name for name, passed in group["gates"].items() if not passed]
        lines += ["", "Failed criteria: " + (", ".join(failed) if failed else "none") + "."]
    lines += ["", "## Scope", "",
        "This is a new local tissue variant with supplied ports, teaching targets, signed connections and an activity-product writer. It differs from E014's scalar-field and globally centered dynamics. Records contain 4096 bytes; geometry and machinery are shared. Protected ports and held-out interior deletions define a limited elementary relay task. Robustness does not distinguish active compensation from redundant paths. These are developmental results; inherited competence through replacement requires the separate renewal phase. All controls, individual scores and failures are retained; audit is a separate receipt."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--benchmark", action="store_true"); parser.add_argument("--worker", type=int)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args(); cap_cpus()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    output = args.output.resolve()
    if not output.is_relative_to(HERE / "runs"): raise ValueError("Local E015 run required")
    if args.worker is not None:
        if args.worker not in (*BLOCKS, BENCHMARK): raise ValueError("Undeclared block")
        save_block(output, args.worker); return
    ids = [BENCHMARK] if args.benchmark else list(BLOCKS)
    started = time.monotonic()
    output = new_run(output, input_paths(), dict(experiment="E015", stage="feasibility", blocks=ids,
        gains=tissue.GAINS, config=asdict(tissue.CFG), workers=args.workers,
        mode="technical" if args.benchmark else "bounded_development"))
    def launch(block):
        with (output / f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable, "-B", str(HERE / "run.py"), "--output", str(output), "--worker", str(block)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for result in as_completed([pool.submit(launch, b) for b in ids]): print("Completed block", result.result(), flush=True)
        analyze(output, ids, args.benchmark)
        finish(output, started, dict(experiment="E015", stage="feasibility", blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output / "FAILED.json", dict(time=utc(), traceback=traceback.format_exc())); raise


if __name__ == "__main__": main()
