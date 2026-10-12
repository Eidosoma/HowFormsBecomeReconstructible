"""Frozen fresh-cohort comparison; no setting search or automatic renewal."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, rng, sha, utc
from E016_teaching_consistency import model
import numpy as np

BLOCKS = tuple(range(14000, 14032))
BENCHMARK = 900016
CSV_FIELDS = ("block", "regime", "founder", "rule", "recipient", "cue", "damage", "arm",
              "success", "margin", "output_A", "output_B")


def input_paths():
    paths = [ROOT / x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json", "SOURCE_LICENSE.txt",
             "E015_functional_inheritance/model.py", "E015_functional_inheritance/audit.py")]
    return paths + [HERE / x for x in ("model.py", "run.py", "audit.py", "tests.py", "plot.py", "workflow.py", "PROTOCOL.md")]


def save_block(output, block, cfg=model.CFG):
    started = time.monotonic()
    cap_cpus()
    source = model.teach(block, cfg)
    source_path = output / f"source_{block:06d}.npz"
    np.savez_compressed(source_path, **source)
    packets, permutations = model.initial_packets(source["acquired"], block, cfg)
    raw = model.read(packets, block, cfg)
    raw["permutations"] = permutations
    np.savez_compressed(output / f"task_{block:06d}.npz", **raw)
    dump(output / f"worker_{block}.json", dict(block=block, seconds=time.monotonic()-started,
        source_file=str(source_path.relative_to(ROOT)), source_sha256=sha(source_path)))


def statistics(values):
    x = np.asarray(values, dtype=float)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    draws = rng("E016", "bootstrap", "comparison").integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws].mean(axis=1), [.025, .975]).tolist(),
                block_means=x.tolist())


def analyze(output, ids, technical, cfg=model.CFG):
    accuracy, both_cues, by_rule, margins, cancellations = [], [], [], [], []
    with (output / "observations.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for block in ids:
            with np.load(output / f"task_{block:06d}.npz", allow_pickle=False) as raw:
                success, margin, values = model.score(raw["port_trace"], cfg)
            accuracy.append(success.mean(axis=(1, 2, 3)))
            both_cues.append(success.all(axis=3).mean(axis=(1, 2)))
            margins.append(margin.mean(axis=(1, 2, 3)))
            by_rule.append(np.stack([success[:, [r, r+2]][..., 0].mean(axis=(1, 2, 3)) for r in range(2)], axis=1))
            with np.load(output / f"source_{block:06d}.npz", allow_pickle=False) as raw:
                separate = abs(raw["episode_weights"]).mean(axis=(1, 3, 4, 5))
                combined = abs(raw["weights"][:2]).mean(axis=(2, 3, 4))
                cancellations.append((1. - combined / separate).mean(axis=1))
            for m, regime in enumerate(model.REGIMES):
                for f in range(4):
                    for r in range(cfg.recipients):
                        for c, cue in enumerate(model.CUES):
                            for d, damage in enumerate(model.DAMAGE):
                                for a, arm in enumerate(model.ARMS):
                                    index = (m, f, r, c, d, a)
                                    writer.writerow(dict(block=block, regime=regime, founder=f, rule=int(model.RULES[f]),
                                        recipient=r, cue=int(cue), damage=damage, arm=arm, success=int(success[index]),
                                        margin=float(margin[index]), output_A=float(values[index+(0,)]),
                                        output_B=float(values[index+(1,)])))
    arrays = {"accuracy": np.array(accuracy), "both_cues": np.array(both_cues),
              "margin": np.array(margins)}
    rules = np.array(by_rule)
    groups = {}
    for m, regime in enumerate(model.REGIMES):
        group = {key: {damage: {arm: statistics(arr[:, m, d, a]) for a, arm in enumerate(model.ARMS)}
                       for d, damage in enumerate(model.DAMAGE)} for key, arr in arrays.items()}
        group["own_accuracy_by_rule"] = {str(rule): {damage: statistics(rules[:, m, r, d])
            for d, damage in enumerate(model.DAMAGE)} for r, rule in enumerate((1, -1))}
        group["own_minus_control"] = {damage: {arm: statistics(arrays["accuracy"][:, m, d, 0] - arrays["accuracy"][:, m, d, a])
            for a, arm in enumerate(model.ARMS) if a} for d, damage in enumerate(model.DAMAGE)}
        gates = {f"accuracy_rule_{rule}_{damage}": group["own_accuracy_by_rule"][str(rule)][damage]["ci95"][0] > .75
                 for rule in (1, -1) for damage in model.DAMAGE}
        gates.update({f"advantage_{damage}_{arm}": group["own_minus_control"][damage][arm]["ci95"][0] > .10
                      for damage in model.DAMAGE for arm in model.ARMS[1:]})
        group.update(gates=gates, all_original_feasibility_gates_pass=all(gates.values()))
        groups[regime] = group
    contrasts = {regime: {key: {damage: statistics(arr[:, m, d, 0] - arr[:, 0, d, 0])
                 for d, damage in enumerate(model.DAMAGE)} for key, arr in arrays.items()}
                 for m, regime in enumerate(model.REGIMES) if m}
    primary = contrasts["consistent"]["both_cues"]["intact"]
    supported = primary["ci95"][0] > 0
    summary = dict(experiment="E016", blocks=list(ids), founders=4*len(ids),
        status="TECHNICAL_ONLY" if technical else "PRIMARY_IMPROVEMENT_SUPPORTED" if supported else "PRIMARY_IMPROVEMENT_NOT_ESTABLISHED",
        evidence_status="technical" if technical else "prospective_diagnostic", gain=model.GAIN,
        regimes=model.REGIMES, arms=model.ARMS, damage=model.DAMAGE, cfg=asdict(cfg), packet_bytes=4096,
        groups=groups, own_contrasts_against_ordinary=contrasts,
        primary=dict(endpoint="consistent minus ordinary; intact both-cue strict success", statistics=primary,
                     lower_bound_above_zero=None if technical else supported),
        cancellation={regime: statistics(np.array(cancellations)[:, m]) for m, regime in enumerate(model.REGIMES[:2])},
        renewal_started=False, setting_selected=None,
        interval_scope="Single prespecified primary endpoint; secondary intervals and feasibility gates are pointwise")
    dump(output / "summary.json", summary)
    report(output, summary)
    return summary


def report(output, summary):
    def fmt(st):
        return f"{100*st['mean']:.1f} [{100*st['ci95'][0]:.1f}, {100*st['ci95'][1]:.1f}]"
    lines = ["# E016 teaching consistency and routing capacity", "", f"**{summary['status']}**", "",
        f"{len(summary['blocks'])} fresh blocks, {summary['founders']} founders; all cases retained. Reader gain fixed at 2. No renewal.", "",
        "Primary effect (consistent minus ordinary, both opposing cues correct, intact), percentage points [95% whole-block interval]: **" +
        fmt(summary["primary"]["statistics"]) + "**.", "",
        "| Record regime | Intact individual-cue success % [95%] | Scattered loss | Square lesion | Original feasibility gates passed |",
        "| --- | --- | --- | --- | --- |"]
    for regime in summary["regimes"]:
        group = summary["groups"][regime]
        lines.append("| " + regime + " | " + " | ".join(fmt(group["accuracy"][d]["own"]) for d in model.DAMAGE) +
                     f" | {sum(group['gates'].values())}/24 |")
    lines += ["", "| Record regime | Intact both-cue success % [95%] | Scattered loss | Square lesion |", "| --- | --- | --- | --- |"]
    for regime in summary["regimes"]:
        group = summary["groups"][regime]
        lines.append("| " + regime + " | " + " | ".join(fmt(group["both_cues"][d]["own"]) for d in model.DAMAGE) + " |")
    for regime in summary["regimes"]:
        group = summary["groups"][regime]
        lines += ["", f"## {regime}: individual-cue accuracy", "", "| Control | Intact % [95%] | Scattered loss | Square lesion |", "| --- | --- | --- | --- |"]
        for arm in model.ARMS:
            lines.append("| " + arm + " | " + " | ".join(fmt(group["accuracy"][d][arm]) for d in model.DAMAGE) + " |")
        for rule in (1, -1):
            lines += ["", f"Rule {rule}, own record: " + "; ".join(f"{d}: {fmt(group['own_accuracy_by_rule'][str(rule)][d])}%" for d in model.DAMAGE) + "."]
        failed = [name for name, passed in group["gates"].items() if not passed]
        lines += ["", "Failed original feasibility gates: " + (", ".join(failed) if failed else "none") + "."]
    lines += ["", "## Scope", "",
        "Consistent teaching coordinates initial fluctuations and noise across lessons; it changes their joint history while preserving each episode's marginal law. Its effect does not isolate scalar cancellation from all other changes to the acquired record. The engineered condition supplies a globally constructed, unit-strength sign-consistent record: success there establishes supplied capacity, not learning. Failure there would not exclude all possible records.", "",
        "The reader, local writer, task margin and damage distributions are unchanged from E015. All regimes have a 4096-byte record and shared external machinery. Goals and teaching coordination are supplied. Primary inference concerns the fixed intact both-cue contrast; other intervals and readiness gates are pointwise. No repeated record replacement, autonomous goal formation, active compensation, or independent agency of patterns is established.", "",
        "Mean fraction of absolute edge strength lost by averaging lessons: " + "; ".join(f"{r}: {fmt(st)}%" for r, st in summary["cancellation"].items()) + ". Full statistics and individual observations are retained; independent audit is a separate receipt."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--worker", type=int)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    cap_cpus()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    output = args.output.resolve()
    if not output.is_relative_to(HERE / "runs"): raise ValueError("Local E016 run required")
    if args.worker is not None:
        if args.worker not in (*BLOCKS, BENCHMARK): raise ValueError("Undeclared block")
        save_block(output, args.worker)
        return
    ids = [BENCHMARK] if args.benchmark else list(BLOCKS)
    started = time.monotonic()
    output = new_run(output, input_paths(), dict(experiment="E016", blocks=ids, gain=model.GAIN,
        regimes=model.REGIMES, config=asdict(model.CFG), workers=args.workers,
        mode="technical" if args.benchmark else "prospective_diagnostic"))
    def launch(block):
        with (output / f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable, "-B", str(HERE / "run.py"), "--output", str(output), "--worker", str(block)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for future in as_completed([pool.submit(launch, block) for block in ids]):
                print("Completed block", future.result(), flush=True)
        analyze(output, ids, args.benchmark)
        finish(output, started, dict(experiment="E016", blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output / "FAILED.json", dict(time=utc(), traceback=traceback.format_exc()))
        raise


if __name__ == "__main__":
    main()
