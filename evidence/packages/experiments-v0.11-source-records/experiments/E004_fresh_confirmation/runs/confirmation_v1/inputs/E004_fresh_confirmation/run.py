"""New cohort only: the E001 simulator and scorer remain unchanged."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE = ROOT / "E001_unprescribed_capture"
sys.path[:0] = [str(ROOT), str(BASE)]
from common import cap_cpus, dump, finish, new_run, sha, utc
from model import ARMS, CFG, checks, simulate
from analyze import analyze
import numpy as np


def worker(block, output):
    cap_cpus()
    started = time.monotonic()
    raw = simulate(block, "heterogeneous")
    audit = checks(raw)
    np.savez_compressed(output / f"block_{block:06d}_heterogeneous.npz", **raw)
    dump(output / f"block_{block:06d}_heterogeneous.json", dict(block=block, background="heterogeneous",
         seconds=time.monotonic()-started, audit=audit, config=asdict(CFG)))


def adjudicate(output, technical):
    summary = json.loads((output / "summary.json").read_text())
    g = summary["groups"]["heterogeneous"]
    primary = g["contrasts"]["terminal"]["rewrite_minus_foreign"]
    full = all(g["gates"].values())
    status = "TECHNICAL_ONLY" if technical else "CONFIRMED_COMPLETE_SEQUENCE" if full else "COMPLETE_SEQUENCE_NOT_CONFIRMED"
    result = dict(experiment="E004", status=status, blocks=len(summary["blocks"]),
                  founders=g["founder_count"], formation_qualified=g["formation_qualified_count"],
                  primary=primary, specificity_confirmed=not technical and primary["ci95"][0]>0,
                  complete_sequence_confirmed=not technical and full, gates=g["gates"],
                  independent_code=False, pooled_with_pilot=False)
    # The original scorer's numerical output is retained verbatim. This separate
    # adjudication identifies this new cohort correctly without editing it.
    dump(output / "confirmation.json", result)
    original = output / "REPORT.md"
    original.rename(output / "E001_SCORER_REPORT.md")
    p = lambda s: f"{100*s['mean']:+.2f} [{100*s['ci95'][0]:+.2f}, {100*s['ci95'][1]:+.2f}]"
    lines = ["# E004 fresh-cohort confirmation", "", f"**{status}**", "",
             f"{len(summary['blocks'])} fresh blocks; all {g['founder_count']} founders retained. Formation qualified {g['formation_qualified_count']}/{g['founder_count']}.",
             f"Terminal own-minus-foreign effect: **{p(primary)} percentage points**, 95% whole-block interval.", "",
             "| Reading | Own minus foreign, points [95%] |", "| --- | --- |"]
    for stage in g["stages"]:
        lines.append(f"| {stage} | {p(g['contrasts'][stage]['rewrite_minus_foreign'])} |")
    lines += ["", "Terminal controls:", ""]
    for name, stats in g["contrasts"]["terminal"].items():
        if name != "rewrite_minus_foreign": lines.append(f"- {name}: {p(stats)} points.")
    lines += ["", "Complete-sequence gates: `"+json.dumps(g["gates"],sort_keys=True)+"`.", "",
              "The unchanged E001 scorer's full tables are in E001_SCORER_REPORT.md and summary.json; their legacy 'pilot' labels describe the reused scorer, not a pooled cohort. This confirmation uses the same engineered model and codebase, with new random streams and backgrounds. It does not establish autonomous writer origin, biological heredity, or perfect reconstruction."]
    (output / "REPORT.md").write_text("\n".join(lines)+"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--worker", type=int)
    args = parser.parse_args()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    if not args.output.resolve().is_relative_to(HERE): raise ValueError("E004 output must be local")
    if args.worker is not None:
        worker(args.worker,args.output.resolve()); return
    cap_cpus()
    ids = [900002] if args.benchmark else list(range(1000,1032))
    source_manifest = json.loads((BASE / "runs/pilot_v1/manifest.json").read_text())
    for file in ("model.py", "analyze.py"):
        assert sha(BASE / file) == source_manifest["inputs_sha256"][str((BASE/file).relative_to(ROOT))]
    inputs = [ROOT/x for x in ("common.py","run_python.sh","SOURCE_SNAPSHOT.json")]
    inputs += [BASE/x for x in ("model.py","analyze.py","tests.py","PROTOCOL.md")]
    inputs += [HERE/x for x in ("run.py","audit.py","PROTOCOL.md")]
    started = time.monotonic()
    output = new_run(args.output,inputs,dict(experiment="E004",blocks=ids,background="heterogeneous",
         mode="technical" if args.benchmark else "fresh_confirmation",workers=args.workers,config=asdict(CFG),
         original_pilot_complete_sha256=sha(BASE/"runs/pilot_v1/COMPLETE.json")))
    def launch(block):
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable,"-B",str(HERE/"run.py"),"--output",str(output),"--worker",str(block)],
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for task in as_completed([pool.submit(launch,b) for b in ids]):
                print(f"Completed fresh block {task.result()}",flush=True)
        analyze(output,ids,["heterogeneous"],technical=args.benchmark)
        adjudicate(output,args.benchmark)
        finish(output,started,dict(experiment="E004",blocks_completed=len(ids)))
        print(f"Complete: {output}",flush=True)
    except BaseException:
        dump(output/"FAILED.json",dict(time=utc(),traceback=traceback.format_exc()));raise


if __name__ == "__main__": main()
