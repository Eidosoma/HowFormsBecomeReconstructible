"""Fresh founders, unchanged E001 formation and E006 compact lifecycle."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import csv
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import bootstrap, cap_cpus, dump, finish, new_run, sha, utc
from E006_compact_renewal import run as compact
from E001_unprescribed_capture.analyze import formation_metrics
import numpy as np

tissue = compact.tissue
FACTORS = (1, 4)


def worker(block, output):
    cap_cpus(); started = time.monotonic()
    source = tissue.formation(block, "heterogeneous")
    acquired, end, first = tissue.capture(source["founder_state"], block)
    source.update(acquired=acquired, capture_end=end, capture_first=first)
    source_path = output / f"source_{block:06d}.npz"
    np.savez_compressed(source_path, **source)
    for factor in FACTORS:
        raw = compact.simulate(source, block, factor)
        np.savez_compressed(output / f"block_{block:06d}_factor_{factor}.npz", **raw)
        dump(output / f"block_{block:06d}_factor_{factor}.json",
             dict(block=block, factor=factor, source_file=str(source_path.relative_to(ROOT)),
                  source_sha256=sha(source_path), audit=tissue.checks(raw)))
    dump(output / f"worker_{block}.json", dict(seconds=time.monotonic()-started))


def statistics(values):
    result = bootstrap(values, "E007")
    # Same deterministic whole-block draws, with a wider descriptive interval.
    from common import rng
    x = np.asarray(values)
    draws = rng("E007", "bootstrap").integers(0, len(x), (10000, len(x)))
    result["ci975"] = np.quantile(x[draws].mean(axis=1), [.0125, .9875]).tolist()
    return result


def analyze(output, ids, technical):
    formations = []
    for block in ids:
        with np.load(output / f"source_{block:06d}.npz", allow_pickle=False) as raw:
            formations.append(dict(block=block, **formation_metrics(raw)))
    nqualified = sum(sum(x["qualified"]) for x in formations)
    diversity = float(np.mean([d for x in formations for d in x["pairwise_disagreement"]]))
    formation_pass = nqualified/(4*len(ids)) >= .75 and diversity > .10
    groups = {}; observations = []
    for factor in FACTORS:
        scores = []
        for block in ids:
            with np.load(output / f"block_{block:06d}_factor_{factor}.npz", allow_pickle=False) as raw:
                v = np.concatenate((raw["generation_read"][:, :, :, :, 0], raw["terminal"][None, :, :, :, 0]))
                q = compact.score(v, raw["prototype"])
                own = compact.own_scores(q)
                scores.append(own.mean(axis=(1, 2)))
                for s, stage in enumerate(compact.STAGES):
                    for f in range(4):
                        for r in range(2):
                            for a, arm in enumerate(tissue.ARMS):
                                observations.append(dict(block=block, factor=factor, stage=stage,
                                    founder=f, recipient=r, arm=arm, qualified_own=float(own[s, f, r, a])))
        x = np.asarray(scores)
        contrasts = {stage: {left+"_minus_"+right: statistics(x[:, s, tissue.ARMS.index(left)]-x[:, s, tissue.ARMS.index(right)])
                     for left, right in compact.CONTRASTS} for s, stage in enumerate(compact.STAGES)}
        positive = lambda stage, name: contrasts[stage][name]["ci95"][0] > 0
        gates = dict(formation=formation_pass, acquisition_readable=positive("G1", "copy_minus_erased"),
                     early_specificity=all(positive(s, "rewrite_minus_foreign") for s in compact.STAGES[:3]),
                     terminal_specificity=positive("terminal", "rewrite_minus_foreign"),
                     terminal_read_required=positive("terminal", "rewrite_minus_read_off"),
                     terminal_write_required=positive("terminal", "rewrite_minus_write_off"))
        groups[str(factor)] = dict(packet_bytes=2048//factor**2, block_own=x.tolist(),
                                   own_means=x.mean(axis=0).tolist(), contrasts=contrasts, gates=gates)
    reference = all(groups["1"]["gates"].values())
    for factor in FACTORS:
        g = groups[str(factor)]
        g["terminal_minus_full_field"] = statistics(np.array(g["block_own"])[:, 3, 0]-np.array(groups["1"]["block_own"])[:, 3, 0])
        g["complete_sequence_confirmed"] = not technical and reference and all(g["gates"].values())
    confirmed = groups["4"]["complete_sequence_confirmed"]
    status = "TECHNICAL_ONLY" if technical else "COMPACT_RENEWAL_CONFIRMED" if confirmed else "COMPACT_RENEWAL_NOT_CONFIRMED"
    summary = dict(experiment="E007", status=status, source_blocks=ids, founders=4*len(ids),
                   formation=formations, formation_qualified=nqualified, formation_diversity=diversity,
                   groups=groups, arms=tissue.ARMS, stages=compact.STAGES, reference_qualified=reference,
                   complete_sequence_confirmed=confirmed, independent_formation_cohort=True,
                   specificity_confirmed=not technical and groups["4"]["gates"]["terminal_specificity"],
                   primary_interval="95%; one prespecified compressed size", pooled_with_development=False)
    dump(output / "summary.json", summary)
    with (output / "observations.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(observations[0])); writer.writeheader(); writer.writerows(observations)
    fmt = lambda st: f"{100*st['mean']:+.2f} [{100*st['ci95'][0]:+.2f}, {100*st['ci95'][1]:+.2f}]"
    lines = ["# E007 fresh compact-renewal confirmation", "", f"**{status}**", "",
             f"All {4*len(ids)} founders retained; formation qualified {nqualified}/{4*len(ids)}. Mean within-block disagreement {100*diversity:.2f}%.", "",
             "| Bytes at every boundary | Terminal own minus foreign, points [95%] | Own agreement | Renewal minus same-budget copy, points [95%] |",
             "| --- | --- | --- | --- |"]
    for factor in FACTORS:
        g = groups[str(factor)]
        lines.append(f"| {g['packet_bytes']} | {fmt(g['contrasts']['terminal']['rewrite_minus_foreign'])} | {100*g['own_means'][3][0]:.2f}% | {fmt(g['contrasts']['terminal']['rewrite_minus_copy'])} |")
        lines += []
    for factor in FACTORS:
        g = groups[str(factor)]
        lines += ["", f"## {g['packet_bytes']} bytes", "", f"Gates: `{json.dumps(g['gates'], sort_keys=True)}`.", ""]
        for stage in compact.STAGES:
            lines.append(f"- {stage} own minus foreign: {fmt(g['contrasts'][stage]['rewrite_minus_foreign'])} points.")
        lines += [f"- Terminal renewal minus full-field renewal: {fmt(g['terminal_minus_full_field'])} points."]
    lines += ["", "This is a fresh-cohort confirmation in the same codebase. Three body-written replacements precede a fresh terminal reader. General writing/reading machinery and coordinates are supplied. Compression changes field amplitude and resolution together; the packet budget excludes shared machinery. The wider 97.5% intervals and all controls are retained in summary.json."]
    (output / "REPORT.md").write_text("\n".join(lines)+"\n")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12); parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--worker", type=int)
    args = parser.parse_args(); cap_cpus()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    if not args.output.resolve().is_relative_to(HERE): raise ValueError("Local E007 output required")
    if args.worker is not None: worker(args.worker, args.output.resolve()); return
    ids = [900007] if args.benchmark else list(range(2000, 2032))
    inputs = [ROOT/x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json",
              "E001_unprescribed_capture/model.py", "E001_unprescribed_capture/analyze.py", "E006_compact_renewal/run.py")]
    inputs += [HERE/x for x in ("run.py", "audit.py", "tests.py", "PROTOCOL.md")]
    started = time.monotonic()
    output = new_run(args.output, inputs, dict(experiment="E007", blocks=ids, factors=FACTORS,
                     config=asdict(tissue.CFG), workers=args.workers, mode="technical" if args.benchmark else "fresh_confirmation"))
    def launch(block):
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable, "-B", str(HERE/"run.py"), "--output", str(output), "--worker", str(block)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for task in as_completed([pool.submit(launch, b) for b in ids]): print("Completed block", task.result(), flush=True)
        analyze(output, ids, args.benchmark)
        finish(output, started, dict(experiment="E007", blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output/"FAILED.json", dict(time=utc(), traceback=traceback.format_exc())); raise


if __name__ == "__main__": main()
