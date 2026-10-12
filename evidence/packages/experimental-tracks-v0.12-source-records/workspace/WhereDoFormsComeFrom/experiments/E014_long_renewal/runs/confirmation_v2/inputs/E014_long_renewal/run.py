"""Longitudinal extension of the immutable E006 lifecycle; offline checkpoints."""
from __future__ import annotations

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
from E006_compact_renewal import run as compact
from E001_unprescribed_capture.analyze import formation_metrics
import numpy as np

tissue = compact.tissue
CFG = replace(tissue.CFG, generations=16)
FACTORS = (1, 4)
CHECKPOINTS = (1, 3, 8, 16)
BLOCKS = tuple(range(12000, 12064))
BENCHMARK = 900014
ARMS = tissue.ARMS
STAGES = tuple(f"G{g}" for g in range(1, 17)) + tuple(f"after_{g}" for g in CHECKPOINTS)
CSV_FIELDS = ("block", "factor", "stage", "founder", "recipient", "arm",
              "qualified_own", "preference", "target_0", "target_1", "target_2", "target_3")


def input_paths():
    return [ROOT / x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json",
            "E001_unprescribed_capture/model.py", "E001_unprescribed_capture/analyze.py",
            "E006_compact_renewal/run.py")] + [HERE / x for x in
            ("run.py", "audit.py", "tests.py", "plot.py", "workflow.py", "PROTOCOL.md")]


def simulate(source, block, factor, cfg=CFG, checkpoints=CHECKPOINTS):
    assert checkpoints and tuple(sorted(set(checkpoints))) == tuple(checkpoints)
    assert checkpoints[-1] == cfg.generations
    stream = block + 1000000
    packets, permutations = compact.initial(source, stream, factor)
    raw = {key: source[key].copy() for key in ("prototype", "prototype_halves", "acquired", "background")}
    raw["permutations"] = permutations
    incoming, outgoing, histories, probes, probe_packets, births, masks = [], [], [], [], [], [], []
    for g in range(1, cfg.generations + 1):
        incoming.append(packets.copy())
        packets, state = compact.generation(packets, stream, g, factor, cfg)
        outgoing.append(packets.copy())
        histories.append(state)
        if g in checkpoints:
            probe_packets.append(packets.copy())
            probe, birth, mask = tissue.read_packets(packets, stream, "terminal", factor=factor, cfg=cfg)
            probes.append(probe); births.append(birth); masks.append(mask)
    raw.update(incoming=np.stack(incoming), outgoing=np.stack(outgoing),
               checkpoint_numbers=np.array(checkpoints), checkpoint_packets=np.stack(probe_packets),
               checkpoint_read=np.stack(probes), checkpoint_birth=np.stack(births),
               checkpoint_mask=np.stack(masks))
    for key in histories[0]:
        raw["generation_" + key] = np.stack([h[key] for h in histories])
    raw.update(terminal=probes[-1], terminal_birth=births[-1], terminal_mask=masks[-1])
    tissue.checks(raw)
    np.testing.assert_array_equal(raw["checkpoint_packets"], raw["outgoing"][np.array(checkpoints) - 1])
    for probe in probes[1:]:
        np.testing.assert_array_equal(probe[:, :, ARMS.index("copy")], probes[0][:, :, ARMS.index("copy")])
    return raw


def worker(block, output):
    cap_cpus(); started = time.monotonic()
    source = tissue.formation(block, "heterogeneous", CFG)
    acquired, end, first = tissue.capture(source["founder_state"], block, CFG)
    source.update(acquired=acquired, capture_end=end, capture_first=first)
    source_path = output / f"source_{block:06d}.npz"
    np.savez_compressed(source_path, **source)
    for factor in FACTORS:
        raw = simulate(source, block, factor)
        np.savez_compressed(output / f"block_{block:06d}_factor_{factor}.npz", **raw)
        dump(output / f"block_{block:06d}_factor_{factor}.json",
             dict(block=block, factor=factor, source_file=str(source_path.relative_to(ROOT)),
                  source_sha256=sha(source_path), audit=tissue.checks(raw)))
    dump(output / f"worker_{block}.json", dict(seconds=time.monotonic() - started))


def statistics(values):
    x = np.asarray(values, dtype=float)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    draws = rng("E014", "bootstrap").integers(0, len(x), (10000, len(x)))
    samples = x[draws].mean(axis=1)
    return dict(mean=float(x.mean()), ci95=np.quantile(samples, [.025, .975]).tolist(),
                ci975=np.quantile(samples, [.0125, .9875]).tolist(),
                block_means=x.tolist(), positive_blocks=int((x > 0).sum()))


def analyze(output, ids, technical):
    formations = []
    for block in ids:
        with np.load(output / f"source_{block:06d}.npz", allow_pickle=False) as raw:
            formations.append(dict(block=block, **formation_metrics(raw)))
    nqualified = sum(sum(x["qualified"]) for x in formations)
    diversity = float(np.mean([d for x in formations for d in x["pairwise_disagreement"]]))
    formation_pass = nqualified / (4 * len(ids)) >= .75 and diversity > .10
    groups = {}
    with (output / "observations.csv").open("x", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=CSV_FIELDS); writer.writeheader()
        for factor in FACTORS:
            scores, preferences, field_sds = [], [], []
            for block in ids:
                with np.load(output / f"block_{block:06d}_factor_{factor}.npz", allow_pickle=False) as raw:
                    v = np.concatenate((raw["generation_read"][:, :, :, :, 0], raw["checkpoint_read"][:, :, :, :, 0]))
                    q = compact.score(v, raw["prototype"])
                    own = compact.own_scores(q)
                    preference = own - (q.sum(axis=-1) - own) / 3
                    scores.append(own.mean(axis=(1, 2)))
                    preferences.append(preference.mean(axis=(1, 2)))
                    fields = tissue.unpack(np.concatenate((raw["incoming"], raw["checkpoint_packets"])), factor)
                    field_sds.append(fields.std(axis=(-2, -1)).mean(axis=(1, 2)))
                    for s, stage in enumerate(STAGES):
                        for f in range(4):
                            for r in range(2):
                                for a, arm in enumerate(ARMS):
                                    writer.writerow(dict(block=block, factor=factor, stage=stage, founder=f,
                                        recipient=r, arm=arm, qualified_own=float(own[s, f, r, a]),
                                        preference=float(preference[s, f, r, a]),
                                        **{f"target_{t}": float(q[s, f, r, a, t]) for t in range(4)}))
            x = np.asarray(scores)
            contrasts = {stage: {left + "_minus_" + right:
                         statistics(x[:, s, ARMS.index(left)] - x[:, s, ARMS.index(right)])
                         for left, right in compact.CONTRASTS} for s, stage in enumerate(STAGES)}
            pos = lambda stage, name: contrasts[stage][name]["ci95"][0] > 0
            gates = dict(formation=formation_pass, acquisition_readable=pos("G1", "copy_minus_erased"),
                         early_specificity=all(pos(f"G{g}", "rewrite_minus_foreign") for g in (1, 2, 3)),
                         checkpoint_specificity=all(pos(f"after_{g}", "rewrite_minus_foreign") for g in CHECKPOINTS),
                         terminal_read_required=pos("after_16", "rewrite_minus_read_off"),
                         terminal_write_required=pos("after_16", "rewrite_minus_write_off"))
            i, j = STAGES.index("after_3"), STAGES.index("after_16")
            own_i, own_j = x[:, i, 0], x[:, j, 0]
            spec_i, spec_j = own_i - x[:, i, 1], own_j - x[:, j, 1]
            groups[str(factor)] = dict(packet_bytes=2048 // factor**2, gates=gates,
                contrasts=contrasts, block_own=x.tolist(), own_means=x.mean(axis=0).tolist(),
                own_statistics={stage: {arm: statistics(x[:, s, a]) for a, arm in enumerate(ARMS)}
                                for s, stage in enumerate(STAGES)},
                block_preference=np.asarray(preferences).tolist(),
                preference_means=np.asarray(preferences).mean(axis=0).tolist(),
                block_field_sd=np.asarray(field_sds).tolist(),
                decoded_field_sd_means=np.asarray(field_sds).mean(axis=0).tolist(),
                after_16_minus_after_3=dict(own=statistics(own_j - own_i), specificity=statistics(spec_j - spec_i)))
    reference = all(groups["1"]["gates"].values())
    for factor in FACTORS:
        g = groups[str(factor)]
        g["checkpoint_minus_full_field"] = {str(c): statistics(
            np.asarray(g["block_own"])[:, STAGES.index(f"after_{c}"), 0] -
            np.asarray(groups["1"]["block_own"])[:, STAGES.index(f"after_{c}"), 0]) for c in CHECKPOINTS}
        g["complete_sequence_confirmed"] = not technical and all(g["gates"].values()) and reference
    confirmed = not technical and reference and all(groups["4"]["gates"].values())
    primary = groups["4"]["contrasts"]["after_16"]["rewrite_minus_foreign"]
    summary = dict(experiment="E014", status="TECHNICAL_ONLY" if technical else
        "LONG_RENEWAL_CONFIRMED" if confirmed else "LONG_RENEWAL_NOT_CONFIRMED",
        evidence_status="technical" if technical else "fresh_long_horizon_test",
        source_blocks=list(ids), founders=4 * len(ids), arms=ARMS, stages=STAGES,
        checkpoint_numbers=CHECKPOINTS, renewal_generations=16, formation=formations,
        formation_qualified=nqualified, formation_diversity=diversity, groups=groups,
        reference_qualified=reference, complete_sequence_confirmed=confirmed,
        primary=primary, primary_specificity_confirmed=not technical and primary["ci95"][0] > 0,
        pooled_with_earlier_experiments=False,
        interval_scope="One 128-byte after-16 primary; secondary intervals pointwise; full criterion all-required")
    dump(output / "summary.json", summary)
    report(output, summary)
    return summary


def report(output, summary):
    fmt = lambda st: f"{100*st['mean']:+.3f} [{100*st['ci95'][0]:+.3f}, {100*st['ci95'][1]:+.3f}]"
    lines = ["# E014 — sixteen rewrites", "", f"**{summary['status']}**", "",
        f"All {summary['founders']} founders retained. Formation qualified {summary['formation_qualified']}/{summary['founders']}; "
        f"mean within-block sign disagreement {100*summary['formation_diversity']:.2f}%.", "",
        f"Primary 128-byte after-16 own-minus-foreign-record effect: **{fmt(summary['primary'])} percentage points** (95% block bootstrap).",
        f"Primary specificity confirmed: `{summary['primary_specificity_confirmed']}`. Full conjunction confirmed: `{summary['complete_sequence_confirmed']}`.", "",
        "Checkpoint probes follow the indicated number of completed replacements and never feed back. Their births/noise are paired across horizons, so protected-copy outcomes are exactly constant.", "",
        "| Bytes | Completed rewrites | Own agreement | Own minus foreign record, pp [95%] | Renewal minus protected copy, pp [95%] |",
        "| --- | --- | --- | --- | --- |"]
    for factor in FACTORS:
        group = summary["groups"][str(factor)]
        for checkpoint in CHECKPOINTS:
            stage = f"after_{checkpoint}"; s = STAGES.index(stage); c = group["contrasts"][stage]
            lines.append(f"| {group['packet_bytes']} | {checkpoint} | {100*group['own_means'][s][0]:.2f}% | "
                         f"{fmt(c['rewrite_minus_foreign'])} | {fmt(c['rewrite_minus_copy'])} |")
    for factor in FACTORS:
        group = summary["groups"][str(factor)]
        lines += ["", f"## {group['packet_bytes']} bytes", "", f"Gates: `{json.dumps(group['gates'], sort_keys=True)}`.",
            f"After-16 minus after-3 own agreement: {fmt(group['after_16_minus_after_3']['own'])} pp.",
            f"After-16 minus after-3 specificity: {fmt(group['after_16_minus_after_3']['specificity'])} pp.",
            f"After-16 own agreement minus full field: {fmt(group['checkpoint_minus_full_field']['16'])} pp."]
    lines += ["", "## Interpretation limits", "",
        "The primary contrast compares descendants given their own versus a different founder's initial record, scored against the same own founder. All-target observer preferences are separate secondary outcomes. read_off suppresses reading during maintenance; checkpoint readers are enabled for every arm. A failed gate or interval spanning zero does not prove complete loss of information.", "",
        "This is a fresh-cohort duration extension within the supplied reader/writer and shared coordinates. Compression changes resolution and amplitude together. It does not measure inherited task competence, transfer to unrelated dynamics, or independent agency of patterns. Secondary intervals are pointwise; all individual outcomes, failures and controls are retained. The independent audit is a separate receipt."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--worker", type=int)
    args = parser.parse_args(); cap_cpus()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    output = args.output.resolve()
    if not output.is_relative_to(HERE / "runs"): raise ValueError("Local E014 runs required")
    if args.worker is not None:
        if args.worker not in (*BLOCKS, BENCHMARK): raise ValueError("Undeclared block")
        worker(args.worker, output); return
    ids = [BENCHMARK] if args.benchmark else list(BLOCKS)
    started = time.monotonic()
    output = new_run(output, input_paths(), dict(experiment="E014", blocks=ids, factors=FACTORS,
        config=asdict(CFG), checkpoints=CHECKPOINTS, workers=args.workers,
        mode="technical" if args.benchmark else "fresh_long_horizon_test"))
    def launch(block):
        with (output / f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable, "-B", str(HERE / "run.py"), "--output", str(output), "--worker", str(block)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for task in as_completed([pool.submit(launch, b) for b in ids]):
                print("Completed block", task.result(), flush=True)
        analyze(output, ids, args.benchmark)
        finish(output, started, dict(experiment="E014", blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output / "FAILED.json", dict(time=utc(), traceback=traceback.format_exc())); raise


if __name__ == "__main__":
    main()
