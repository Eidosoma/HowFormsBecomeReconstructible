"""Bounded fresh-cohort timing experiment; immutable runs and complete reporting."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, rng, sha, utc
from E017_reader_timing import model
import numpy as np

BLOCKS = tuple(range(15000, 15032))
BENCHMARK = 900017
CSV_FIELDS = ("block", "condition", "regime", "founder", "rule", "recipient", "cue", "damage", "arm", "success", "margin", "output_A", "output_B")
CONTRASTS = (("extended_minus_baseline", 1, 0), ("staged_minus_extended", 2, 1), ("staged_minus_baseline", 2, 0))


def input_paths():
    paths = [ROOT/x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json", "SOURCE_LICENSE.txt",
        "E015_functional_inheritance/model.py", "E015_functional_inheritance/audit.py", "E016_teaching_consistency/model.py")]
    return paths + [HERE/x for x in ("model.py", "run.py", "audit.py", "tests.py", "plot.py", "workflow.py", "PROTOCOL.md")]


def save_block(output, block, cfg=model.CFG, timing=model.TIMING):
    started = time.monotonic()
    cap_cpus()
    source = model.acquisition.teach(block, cfg)
    path = output/f"source_{block:06d}.npz"
    np.savez_compressed(path, **source)
    packets, permutations = model.initial_packets(source, block, cfg)
    raw = model.read(packets, block, cfg, timing)
    raw["permutations"] = permutations
    np.savez_compressed(output/f"task_{block:06d}.npz", **raw)
    dump(output/f"worker_{block}.json", dict(block=block, seconds=time.monotonic()-started,
        source_file=str(path.relative_to(ROOT)), source_sha256=sha(path)))


def statistics(values):
    x = np.asarray(values, dtype=float)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    draws = rng("E017", "bootstrap", "timing").integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def analyze(output, ids, technical, cfg=model.CFG, timing=model.TIMING):
    collected = {key: [] for key in ("accuracy", "both_cues", "margin", "rules")}
    with (output/"observations.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for block in ids:
            with np.load(output/f"task_{block:06d}.npz", allow_pickle=False) as raw:
                success, margin, values = model.score(raw["port_trace"], cfg, timing)
            collected["accuracy"].append(success.mean(axis=(2, 3, 4)))
            collected["both_cues"].append(success.all(axis=4).mean(axis=(2, 3)))
            collected["margin"].append(margin.mean(axis=(2, 3, 4)))
            collected["rules"].append(np.stack([success[:, :, [r, r+2]][..., 0].mean(axis=(2, 3, 4)) for r in range(2)], axis=2))
            for k, condition in enumerate(model.CONDITIONS):
                for m, regime in enumerate(model.REGIMES):
                    for f in range(4):
                        for r in range(cfg.recipients):
                            for c, cue in enumerate(model.CUES):
                                for d, damage in enumerate(model.DAMAGE):
                                    for a, arm in enumerate(model.ARMS):
                                        index = (k, m, f, r, c, d, a)
                                        writer.writerow(dict(block=block, condition=condition, regime=regime, founder=f,
                                            rule=int(model.RULES[f]), recipient=r, cue=int(cue), damage=damage, arm=arm,
                                            success=int(success[index]), margin=float(margin[index]),
                                            output_A=float(values[index+(0,)]), output_B=float(values[index+(1,)])))
    arrays = {key: np.asarray(value) for key, value in collected.items()}
    groups, contrasts = {}, {}
    for m, regime in enumerate(model.REGIMES):
        groups[regime] = {}
        for k, condition in enumerate(model.CONDITIONS):
            group = {key: {damage: {arm: statistics(arrays[key][:, k, m, d, a]) for a, arm in enumerate(model.ARMS)}
                     for d, damage in enumerate(model.DAMAGE)} for key in ("accuracy", "both_cues", "margin")}
            group["own_accuracy_by_rule"] = {str(rule): {damage: statistics(arrays["rules"][:, k, m, r, d])
                for d, damage in enumerate(model.DAMAGE)} for r, rule in enumerate((1, -1))}
            group["own_minus_control"] = {damage: {arm: statistics(arrays["accuracy"][:, k, m, d, 0]-arrays["accuracy"][:, k, m, d, a])
                for a, arm in enumerate(model.ARMS) if a} for d, damage in enumerate(model.DAMAGE)}
            gates = {f"accuracy_rule_{rule}_{damage}": group["own_accuracy_by_rule"][str(rule)][damage]["ci95"][0] > .75
                     for rule in (1, -1) for damage in model.DAMAGE}
            gates.update({f"advantage_{damage}_{arm}": group["own_minus_control"][damage][arm]["ci95"][0] > .10
                          for damage in model.DAMAGE for arm in model.ARMS[1:]})
            group.update(gates=gates, all_original_feasibility_gates_pass=all(gates.values()))
            groups[regime][condition] = group
        contrasts[regime] = {name: {key: {damage: statistics(arrays[key][:, hi, m, d, 0]-arrays[key][:, lo, m, d, 0])
            for d, damage in enumerate(model.DAMAGE)} for key in ("accuracy", "both_cues", "margin")}
            for name, hi, lo in CONTRASTS}
    primary = contrasts["consistent"]["staged_minus_extended"]["both_cues"]["intact"]
    supported = primary["ci95"][0] > 0
    summary = dict(experiment="E017", blocks=list(ids), founders=4*len(ids), conditions=model.CONDITIONS,
        regimes=model.REGIMES, arms=model.ARMS, damage=model.DAMAGE, cfg=asdict(cfg), timing=asdict(timing), gain=2.,
        packet_bytes=4096, status="TECHNICAL_ONLY" if technical else "PRIMARY_TIMING_BENEFIT_SUPPORTED" if supported else "PRIMARY_TIMING_BENEFIT_NOT_ESTABLISHED",
        evidence_status="technical" if technical else "prospective_diagnostic", groups=groups, contrasts=contrasts,
        primary=dict(endpoint="consistent learned record; staged minus extended intact both-cue strict success",
                     statistics=primary, lower_bound_above_zero=None if technical else supported),
        interval_scope="Single prespecified primary; secondary intervals and readiness gates pointwise",
        renewal_started=False, setting_selected=None)
    dump(output/"summary.json", summary)
    report(output, summary)
    return summary


def report(output, summary):
    def fmt(st): return f"{100*st['mean']:.1f} [{100*st['ci95'][0]:.1f}, {100*st['ci95'][1]:.1f}]"
    lines = ["# E017 reader timing", "", f"**{summary['status']}**", "",
        f"{len(summary['blocks'])} fresh blocks, {summary['founders']} founders; all cases retained. No renewal.", "",
        "Primary staged-minus-extended intact both-cue effect with learned records, percentage points [95%]: **" + fmt(summary["primary"]["statistics"]) + "**."]
    for metric, label in (("accuracy", "Individual-cue strict success"), ("both_cues", "Both opposing cues strictly correct")):
        lines += ["", f"## {label}", "", "| Record | Reader | Intact % [95%] | Scattered loss | Square lesion | Original gates passed |", "| --- | --- | --- | --- | --- | --- |"]
        for regime in summary["regimes"]:
            for condition in summary["conditions"]:
                group = summary["groups"][regime][condition]
                lines.append(f"| {regime} | {condition} | " + " | ".join(fmt(group[metric][d]["own"]) for d in summary["damage"]) + f" | {sum(group['gates'].values())}/24 |")
    for regime in summary["regimes"]:
        for condition in summary["conditions"]:
            group = summary["groups"][regime][condition]
            lines += ["", f"## {regime} / {condition}: individual-cue controls", "", "| Arm | Intact % [95%] | Scattered loss | Square lesion |", "| --- | --- | --- | --- |"]
            for arm in summary["arms"]:
                lines.append("| " + arm + " | " + " | ".join(fmt(group["accuracy"][d][arm]) for d in summary["damage"]) + " |")
            for rule in (1, -1):
                lines += ["", f"Rule {rule}, own: " + "; ".join(f"{d}: {fmt(group['own_accuracy_by_rule'][str(rule)][d])}%" for d in summary["damage"]) + "."]
            failed = [key for key, passed in group["gates"].items() if not passed]
            lines += ["", "Failed original gates: " + (", ".join(failed) if failed else "none") + "."]
    lines += ["", "## Scope", "",
        "Baseline is the 512-step prefix of the ordinary 2048-step trajectory. Staged reading removes only positive linear self-amplification for the first 256 of 2048 steps. Noise, coupling, input, records and damage are paired. The single primary comparison uses learned records and equal total time. Staging also changes total amplification exposure and early state distributions; benefit would not uniquely establish premature commitment.", "",
        "Teaching coordination, the public timing schedule, ports and engineered record are supplied apparatus. Engineered success is capacity, not learned competence. Secondary intervals and readiness gates are pointwise. No automatic parameter search, active repair, autonomous goals, independent pattern agency or competence inheritance is established. The independent audit is a separate receipt."]
    (output/"REPORT.md").write_text("\n".join(lines)+"\n")


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
    if not output.is_relative_to(HERE/"runs"): raise ValueError("Local E017 run required")
    if args.worker is not None:
        if args.worker not in (*BLOCKS, BENCHMARK): raise ValueError("Undeclared block")
        save_block(output, args.worker)
        return
    ids = [BENCHMARK] if args.benchmark else list(BLOCKS)
    started = time.monotonic()
    output = new_run(output, input_paths(), dict(experiment="E017", blocks=ids, gain=2., regimes=model.REGIMES,
        conditions=model.CONDITIONS, config=asdict(model.CFG), timing=asdict(model.TIMING), workers=args.workers,
        mode="technical" if args.benchmark else "prospective_diagnostic"))
    def launch(block):
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable, "-B", str(HERE/"run.py"), "--output", str(output), "--worker", str(block)],
                stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1800)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for future in as_completed([pool.submit(launch, block) for block in ids]):
                print("Completed block", future.result(), flush=True)
        analyze(output, ids, args.benchmark)
        finish(output, started, dict(experiment="E017", blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output/"FAILED.json", dict(time=utc(), traceback=traceback.format_exc()))
        raise


if __name__ == "__main__": main()
