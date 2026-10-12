"""Frozen functional renewal cohort, append-only evidence and complete reporting."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from dataclasses import asdict, replace
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
from E022_reader_compensation import model
import numpy as np

BLOCKS = tuple(range(20000, 20032))
BENCHMARK = 900022
BENCHMARK_CFG = replace(model.CFG, recipients=1)
CSV_FIELDS = ("block", "horizon", "condition", "founder", "rule", "lineage", "cue", "damage", "arm", "success", "margin", "output_A", "output_B")


def input_paths():
    paths = [ROOT/x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json", "SOURCE_LICENSE.txt",
        "E015_functional_inheritance/model.py", "E015_functional_inheritance/audit.py",
        "E016_teaching_consistency/model.py", "E017_reader_timing/model.py", "E017_reader_timing/audit.py",
        "E021_damaged_renewal/model.py")]
    return paths+[HERE/x for x in ("model.py", "run.py", "audit.py", "tests.py", "plot.py", "workflow.py", "PROTOCOL.md")]


def save_block(output, block, cfg=model.CFG, cycle=model.CYCLE):
    started = time.monotonic()
    cap_cpus()
    source = model.acquisition.teach(block, cfg)
    path = output/f"source_{block:06d}.npz"
    np.savez_compressed(path, **source)
    records = np.repeat(source["acquired"][1, :, None], cfg.recipients, axis=1)
    initial = model.assay(records[None], block, 0, cfg, cycle)
    np.savez_compressed(output/f"assay_{block:06d}_h0.npz", **initial)
    del initial
    incoming = np.repeat(records[None], len(model.CONDITIONS), axis=0)
    for generation in range(1, cycle.generations+1):
        boundary = model.replace_record(incoming, block, generation, cfg, cycle)
        np.savez_compressed(output/f"boundary_{block:06d}_g{generation}.npz", **boundary)
        incoming = boundary["outgoing"].copy()
        del boundary
        if generation == 1:
            result = model.assay(incoming, block, generation, cfg, cycle)
            np.savez_compressed(output/f"assay_{block:06d}_h{generation}.npz", **result)
            del result
    dump(output/f"worker_{block}.json", dict(block=block, seconds=time.monotonic()-started,
        source_file=str(path.relative_to(ROOT)), source_sha256=sha(path)))


def statistics(x):
    x = np.asarray(x, dtype=float)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    draws = rng("E022", "bootstrap", "compensation").integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def body_summary(output, ids, cfg):
    collected = {name: [] for name in ("accuracy", "both_cues", "margin")}
    fields = ("block", "condition", "founder", "rule", "lineage", "cue", "success", "margin", "output_A", "output_B")
    with (output/"body_observations.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for block in ids:
            with np.load(output/f"boundary_{block:06d}_g1.npz", allow_pickle=False) as raw:
                values = raw["developed_late_ports"].mean(axis=0)
            desired = model.RULES[None, :, None, None]*model.CUES[None, None, None, :]
            margin = np.minimum(desired*values[..., 0], -desired*values[..., 1])
            correct = margin > cfg.margin
            collected["accuracy"].append(correct.mean(axis=(1, 2, 3)))
            collected["both_cues"].append(correct.all(axis=3).mean(axis=(1, 2)))
            collected["margin"].append(margin.mean(axis=(1, 2, 3)))
            for a, condition in enumerate(model.ACTIVE):
                for f in range(4):
                    for r in range(cfg.recipients):
                        for c, cue in enumerate(model.CUES):
                            index = (a, f, r, c)
                            writer.writerow(dict(block=block, condition=model.CONDITIONS[condition], founder=f,
                                rule=int(model.RULES[f]), lineage=r, cue=int(cue), success=int(correct[index]),
                                margin=float(margin[index]), output_A=float(values[index+(0,)]), output_B=float(values[index+(1,)])))
    return {model.CONDITIONS[n]: {metric: statistics(np.asarray(value)[:, a]) for metric, value in collected.items()}
            for a, n in enumerate(model.ACTIVE)}


def analyze(output, ids, technical, cfg=model.CFG, cycle=model.CYCLE):
    collected = {key: [] for key in ("accuracy", "both_cues", "margin", "rules")}
    with (output/"observations.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for block in ids:
            scores, margins, values = [], [], []
            for h in (0, 1):
                with np.load(output/f"assay_{block:06d}_h{h}.npz", allow_pickle=False) as raw:
                    correct, margin, ports = model.score(raw["late_ports"], cfg)
                scores.append(correct); margins.append(margin); values.append(ports)
            success, margin, ports = [np.concatenate(x) for x in (scores, margins, values)]
            collected["accuracy"].append(success.mean(axis=(1, 2, 3)))
            collected["both_cues"].append(success.all(axis=3).mean(axis=(1, 2)))
            collected["margin"].append(margin.mean(axis=(1, 2, 3)))
            collected["rules"].append(np.stack([success[:, [r, r+2]][..., 0].mean(axis=(1, 2, 3)) for r in range(2)], axis=1))
            for k, (horizon, condition) in enumerate(model.PANELS):
                for f in range(4):
                    for r in range(cfg.recipients):
                        for c, cue in enumerate(model.CUES):
                            for d, damage in enumerate(model.DAMAGE):
                                for a, arm in enumerate(model.ARMS):
                                    index = (k, f, r, c, d, a)
                                    writer.writerow(dict(block=block, horizon=horizon, condition=condition, founder=f,
                                        rule=int(model.RULES[f]), lineage=r, cue=int(cue), damage=damage, arm=arm,
                                        success=int(success[index]), margin=float(margin[index]),
                                        output_A=float(ports[index+(0,)]), output_B=float(ports[index+(1,)])))
    arrays = {key: np.asarray(value) for key, value in collected.items()}
    groups, contrasts = {}, {}
    for k, (h, condition) in enumerate(model.PANELS):
        group = {metric: {damage: {arm: statistics(arrays[metric][:, k, d, a]) for a, arm in enumerate(model.ARMS)}
                 for d, damage in enumerate(model.DAMAGE)} for metric in ("accuracy", "both_cues", "margin")}
        group["own_accuracy_by_rule"] = {str(rule): {damage: statistics(arrays["rules"][:, k, r, d])
            for d, damage in enumerate(model.DAMAGE)} for r, rule in enumerate((1, -1))}
        group["own_minus_control"] = {damage: {arm: statistics(arrays["accuracy"][:, k, d, 0]-arrays["accuracy"][:, k, d, a])
            for a, arm in enumerate(model.ARMS) if a} for d, damage in enumerate(model.DAMAGE)}
        gates = {f"accuracy_rule_{rule}_{damage}": group["own_accuracy_by_rule"][str(rule)][damage]["ci95"][0] > .75
                 for rule in (1, -1) for damage in model.DAMAGE}
        gates.update({f"advantage_{damage}_{arm}": group["own_minus_control"][damage][arm]["ci95"][0] > .10
                      for damage in model.DAMAGE for arm in model.ARMS[1:]})
        group.update(gates=gates, all_original_gates_pass=all(gates.values()))
        groups.setdefault(str(h), {})[condition] = group
    boundary_gates = {}
    for h in (1,):
        hi = model.PANELS.index((h, "strength_compensated"))
        contrasts[str(h)] = {}
        for condition in model.CONDITIONS:
            if condition == "strength_compensated": continue
            lo = model.PANELS.index((h, condition))
            result = {metric: {damage: statistics(arrays[metric][:, hi, d, 0]-arrays[metric][:, lo, d, 0])
                      for d, damage in enumerate(model.DAMAGE)} for metric in ("accuracy", "both_cues", "margin")}
            contrasts[str(h)][f"strength_compensated_minus_{condition}"] = result
            if condition in ("read_blocked", "write_blocked"):
                boundary_gates.update({f"h{h}_{condition}_{damage}": result["accuracy"][damage]["ci95"][0] > .10 for damage in model.DAMAGE})
    degree, baseline = (model.PANELS.index((1, condition)) for condition in ("degree_compensated", "baseline"))
    contrasts["1"]["degree_compensated_minus_baseline"] = {
        metric: {damage: statistics(arrays[metric][:, degree, d, 0]-arrays[metric][:, baseline, d, 0])
                 for d, damage in enumerate(model.DAMAGE)} for metric in ("accuracy", "both_cues", "margin")}
    primary = contrasts["1"]["strength_compensated_minus_baseline"]["both_cues"]["intact"]
    primary_pass = primary["ci95"][0] > .10
    qualification = dict(
        candidate_intact_both_cue_lower_above_075=groups["1"]["strength_compensated"]["both_cues"]["intact"]["own"]["ci95"][0] > .75,
        candidate_original_24_gates=groups["1"]["strength_compensated"]["all_original_gates_pass"],
        intact_reference_original_24_gates=groups["1"]["intact_renewed"]["all_original_gates_pass"],
        reading_writing_6_gates=all(boundary_gates.values()))
    full = primary_pass and all(qualification.values())
    bodies = body_summary(output, ids, cfg)
    summary = dict(experiment="E022", blocks=list(ids), founders=4*len(ids), lineages=4*cfg.recipients*len(ids),
        panels=model.PANELS, conditions=model.CONDITIONS, arms=model.ARMS, damage=model.DAMAGE, cfg=asdict(cfg), cycle=asdict(cycle),
        packet_bytes=4096, gain=2., groups=groups, contrasts=contrasts, boundary_gates=boundary_gates,
        qualification_gates=qualification, body_reading=bodies, reader_modes=model.READER_MODES,
        primary=dict(endpoint="strength-compensated minus unchanged reading: intact-assay both-cue success after one damaged replacement", statistics=primary,
                     lower_bound_above_010=None if technical else primary_pass),
        full_compensation_qualified=None if technical else full,
        status="TECHNICAL_ONLY" if technical else "READER_COMPENSATION_QUALIFIED" if full else "READER_COMPENSATION_NOT_ESTABLISHED",
        evidence_status="technical" if technical else "prospective_reader_compensation_test",
        interval_scope="Single primary; all secondary intervals and qualification gates pointwise",
        individual_observations=len(ids)*len(model.PANELS)*4*cfg.recipients*2*3*7,
        body_individual_observations=len(ids)*len(model.ACTIVE)*4*cfg.recipients*2,
        damage_during_renewal=True, renewal_damage=dict(kind="scattered", cells=24, applied_at_birth=True, generations=1),
        setting_selected=None)
    dump(output/"summary.json", summary)
    report(output, summary)
    return summary


def report(output, summary):
    def fmt(st): return f"{100*st['mean']:.1f} [{100*st['ci95'][0]:.1f}, {100*st['ci95'][1]:.1f}]"
    lines = ["# E022 local compensation during damaged renewal", "", f"**{summary['status']}**", "",
        f"{len(summary['blocks'])} blocks; {summary['founders']} founders; {summary['lineages']} lineages; all cases retained.", "",
        "Primary: strength-compensated minus baseline intact-assay both-cue success after one replacement, percentage points [95%]: **"+fmt(summary["primary"]["statistics"])+"**.", "",
        f"Primary lower bound >10 points: {summary['primary']['lower_bound_above_010']}; full qualification: {summary['full_compensation_qualified']}."]
    for name, passed in summary["qualification_gates"].items(): lines += ["", f"{name}: {passed}."]
    lines += ["", "One renewal body lacks 24 scattered non-port cells from birth. Baseline divides incoming drive by four; degree compensation divides by physical degree; strength compensation divides by total absolute incident weight. Zero denominator gives zero incoming drive. Only renewal reading changes; the immediate writer and every terminal assay retain their original rules. Table damage columns describe independent terminal injury. Copying bypasses bodies; masked copying applies the same edge erasures."]
    for metric, label in (("both_cues", "Both opposing inputs correct"), ("accuracy", "Individual-cue strict success")):
        lines += ["", f"## {label}", "", "| Replacements | Condition | Intact % [95%] | Scattered loss | Square lesion | Original gates |", "| --- | --- | --- | --- | --- | --- |"]
        for h, condition in summary["panels"]:
            group = summary["groups"][str(h)][condition]
            lines.append(f"| {h} | {condition} | "+" | ".join(fmt(group[metric][d]["own"]) for d in summary["damage"])+f" | {sum(group['gates'].values())}/24 |")
    for h in (1,):
        lines += ["", f"## Renewal contrasts after {h} replacements", "", "Paired both-cue effects, percentage points [95%].", "",
                  "| Contrast | Intact | Scattered loss | Square lesion |", "| --- | --- | --- | --- |"]
        for name, result in summary["contrasts"][str(h)].items():
            lines.append("| "+name+" | "+" | ".join(fmt(result["both_cues"][d]) for d in summary["damage"])+" |")
    lines += ["", "## Body outputs before capture", "", "These are renewal-body measurements, not fresh-body function or qualification gates.", "",
              "| Condition | Individual-cue % [95%] | Both cues % [95%] |", "| --- | --- | --- |"]
    for name, result in summary["body_reading"].items():
        lines.append(f"| {name} | {fmt(result['accuracy'])} | {fmt(result['both_cues'])} |")
    for h, condition in summary["panels"]:
        group = summary["groups"][str(h)][condition]
        lines += ["", f"## {h} replacements / {condition}: individual-cue controls", "",
            "| Arm | Intact % [95%] | Scattered loss | Square lesion |", "| --- | --- | --- | --- |"]
        for arm in summary["arms"]:
            lines.append("| "+arm+" | "+" | ".join(fmt(group["accuracy"][d][arm]) for d in summary["damage"])+" |")
        for rule in (1, -1):
            lines += ["", f"Rule {rule}, own: "+"; ".join(f"{d}: {fmt(group['own_accuracy_by_rule'][str(rule)][d])}%" for d in summary["damage"])+"."]
        failed = [key for key, passed in group["gates"].items() if not passed]
        lines += ["", "Failed original gates: "+(", ".join(failed) if failed else "none")+"."]
    failed = [key for key, passed in summary["boundary_gates"].items() if not passed]
    lines += ["", "Failed reading/writing-dependence gates: "+(", ".join(failed) if failed else "none")+".", "", "## Scope", "",
        "Incoming record weights are erased before unchanged immediate capture from activity. The new 4096-byte packet is protected through 128 holding updates with no feedback. Denominators remain local to renewal reading and never enter the writer or terminal reader. No output reteaching, successful-case filtering or assay feedback occurs.", "",
        "This tests one damaged-development boundary. Local compensation is supplied machinery and changes effective coupling symmetry despite reciprocal stored edges. It does not establish acute repair, regrowth, autonomous compensation, three-boundary reliability or a unique microscopic mechanism. Strength compensation is the fixed candidate; the degree control is secondary and never selected by its outcome. Whole-block intervals; all secondary comparisons/gates are pointwise. No equivalence or superiority over copying is prespecified. No tuning, exclusions, severity adjustment or automatic successor follows. Independent audit is a separate receipt."]
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
    if not output.is_relative_to(HERE/"runs"): raise ValueError("Local E022 run required")
    if args.worker is not None:
        contract = json.loads((output/"manifest.json").read_text())["contract"]
        if args.worker not in contract["blocks"]: raise ValueError("Undeclared block")
        save_block(output, args.worker, model.base.Config(**contract["config"]), model.Cycle(**contract["cycle"]))
        return
    ids = [BENCHMARK] if args.benchmark else list(BLOCKS)
    cfg = BENCHMARK_CFG if args.benchmark else model.CFG
    started = time.monotonic()
    output = new_run(output, input_paths(), dict(experiment="E022", blocks=ids, gain=2., panels=model.PANELS,
        conditions=model.CONDITIONS, config=asdict(cfg), cycle=asdict(model.CYCLE), workers=args.workers,
        mode="technical" if args.benchmark else "prospective_reader_compensation_test"))
    def launch(block):
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable, "-B", str(HERE/"run.py"), "--output", str(output), "--worker", str(block)],
                stdout=log, stderr=subprocess.STDOUT, check=True, timeout=7200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for future in as_completed([pool.submit(launch, block) for block in ids]):
                print("Completed block", future.result(), flush=True)
        analyze(output, ids, args.benchmark, cfg)
        finish(output, started, dict(experiment="E022", blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output/"FAILED.json", dict(time=utc(), traceback=traceback.format_exc()))
        raise


if __name__ == "__main__": main()
