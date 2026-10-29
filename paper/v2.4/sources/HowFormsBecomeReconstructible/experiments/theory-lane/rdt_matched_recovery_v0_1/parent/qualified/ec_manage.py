"""Freeze and explicitly launch one bounded benchmark, with no successor."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from ec_common import ROOT, C, ev, read, ledger, require, manifest, environment


def freeze(name, scope='benchmark'):
    require(scope in ('benchmark', 'development'), 'Unknown freeze scope')
    require(name.replace('_', '').isalnum(), 'Simple job name required')
    job = ROOT / 'jobs' / name
    job.mkdir(parents=True, exist_ok=False)
    inputs = job / 'inputs'
    inputs.mkdir()
    for path in ROOT.glob('*.py'):
        shutil.copyfile(path, inputs / path.name)
    for name in ('protocol.json', 'FROZEN_MODELS.json', 'SOURCE_BINDINGS.json', 'NATIVE_PROVENANCE.json'):
        shutil.copyfile(ROOT / name, inputs / name)
    if scope == 'development':
        for name in ('DEVELOPMENT.json', 'DEV_SOURCE.json'):
            shutil.copyfile(ROOT / name, inputs / name)
    for name in ('context', 'native'):
        shutil.copytree(ROOT / name, inputs / name)
    ledger.atomic_json(inputs / 'INPUTS.json', dict(utc=ev.utc(), sha256=manifest(inputs),
        scope='disposable_native_benchmark' if scope == 'benchmark' else 'exposed_equal_read_development', automatic_successor=False))
    return job


def launch(job, name):
    job = Path(job).resolve()
    require(job.is_relative_to(ROOT / 'jobs'), 'Local frozen job required')
    require(name.replace('_', '').isalnum(), 'Simple run name required')
    inputs = job / 'inputs'
    require(manifest(inputs, ('INPUTS.json',)) == read(inputs / 'INPUTS.json')['sha256'], 'Frozen input changed')
    require(read(inputs / 'protocol.json') == C, 'Frozen resource contract differs')
    output = ROOT / 'runs' / name
    require(not output.exists(), 'Never overwrite a run')
    receipt = job / (name + '_LAUNCH.json')
    require(not receipt.exists(), 'No automatic retry')
    command = [sys.executable, str(inputs / 'ec_benchmark.py'), 'run', '--output', str(output)]
    logfile = job / (name + '.log')
    with logfile.open('xb') as stream:
        process = subprocess.Popen(command, cwd=inputs, env=environment(job / (name + '_tmp')),
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    result = dict(utc=ev.utc(), pid=process.pid, run=str(output), log=str(logfile), command=command,
        hard_wall_seconds=C['benchmark']['hard_wall_seconds'], input_manifest_sha256=ev.sha(inputs / 'INPUTS.json'),
        detached=True, automatic_polling=False, automatic_retry=False, automatic_successor=False)
    ledger.atomic_json(receipt, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    a = sub.add_parser('freeze'); a.add_argument('--name', required=True)
    a = sub.add_parser('launch'); a.add_argument('--job', type=Path, required=True); a.add_argument('--name', required=True)
    args = parser.parse_args()
    print(freeze(args.name) if args.mode == 'freeze' else launch(args.job, args.name), flush=True)
