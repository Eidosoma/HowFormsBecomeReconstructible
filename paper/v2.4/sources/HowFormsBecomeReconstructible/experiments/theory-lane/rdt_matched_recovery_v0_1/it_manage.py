"""Exclusive freezing and explicit detached launch; no automatic polling."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from it_common import ROOT, C, ev, read, ledger, require, manifest, environment


def freeze(name):
    require(name.replace("_", "").isalnum(), "Simple job name required")
    job = ROOT / "jobs" / name
    inputs = job / "inputs"
    inputs.mkdir(parents=True, exist_ok=False)
    for path in sorted(ROOT.glob("*.py")):
        shutil.copyfile(path, inputs / path.name)
    for name in ("protocol.json", "SOURCE_BINDINGS.json", "FROZEN_CANDIDATES.json", "FROZEN_CALIBRATION.json", "EXPOSURE_AND_DECISIONS.json"):
        shutil.copyfile(ROOT / name, inputs / name)
    for name in ("parent", "context"):
        shutil.copytree(ROOT / name, inputs / name)
    ledger.atomic_json(inputs / "INPUTS.json", dict(utc=ev.utc(), sha256=manifest(inputs)))
    ledger.atomic_json(job / "FROZEN.json", dict(
        utc=ev.utc(), input_manifest_sha256=ev.sha(inputs / "INPUTS.json"), automatic_launch=False))
    return job


def launch(job, scope, name, qualification=None):
    job = Path(job).resolve()
    inputs = job / "inputs"
    require(inputs.is_relative_to(ROOT / "jobs"), "Use a local frozen snapshot")
    require(scope in ("qualification", "development"), "Unknown launch scope")
    require(name.replace("_", "").isalnum(), "Simple run name required")
    output = ROOT / "runs" / name
    receipt = job / (name + "_LAUNCH.json")
    require(not output.exists() and not receipt.exists(), "Never overwrite or retry a run")
    require(manifest(inputs, ("INPUTS.json",)) == read(inputs / "INPUTS.json")["sha256"], "Snapshot differs")
    if scope == "development":
        require(qualification is not None, "Explicit matching qualification required")
    command = [sys.executable, str(inputs / "it_run.py"), "--scope", scope, "--output", str(output)]
    if qualification is not None:
        command += ["--qualification", str(Path(qualification).resolve())]
    logpath = job / (name + ".log")
    with logpath.open("xb") as log:
        process = subprocess.Popen(
            command, cwd=inputs, env=environment(job / (name + "_tmp")), stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    value = dict(
        utc=ev.utc(), pid=process.pid, command=command, scope=scope, run=str(output), log=str(logpath),
        detached=True, input_manifest_sha256=ev.sha(inputs / "INPUTS.json"),
        hard_wall_seconds=C["resources"]["qualification_hard_seconds"] if scope == "qualification"
        else C["resources"]["hard_wall_seconds"],
        automatic_polling=False, automatic_retry=False, automatic_successor=False,
    )
    ledger.atomic_json(receipt, value)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--name", required=True)
    l = sub.add_parser("launch")
    l.add_argument("--job", type=Path, required=True)
    l.add_argument("--scope", choices=("qualification", "development"), required=True)
    l.add_argument("--name", required=True)
    l.add_argument("--qualification", type=Path)
    args = parser.parse_args()
    print(freeze(args.name) if args.mode == "freeze" else launch(
        args.job, args.scope, args.name, args.qualification), flush=True)
