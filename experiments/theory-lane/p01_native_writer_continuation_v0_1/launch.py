"""Freeze inputs and launch once, detached; never poll the child."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from evidence import ROOT, sha, stamp, verify_sources, write_json


def main():
    cfg = json.loads((ROOT/'config.json').read_text())
    source = verify_sources(cfg)
    benchmark = json.loads((ROOT/'benchmark/COMPLETE.json').read_text())
    assert benchmark['status'] == 'COMPLETE' and benchmark['byte_equal']
    assert benchmark['config_sha256'] == sha(ROOT/'config.json')
    assert benchmark['within_development_cost_ceiling']
    for name, digest in benchmark['code_sha256'].items():
        assert sha(ROOT/name) == digest, name
    assert os.environ.get('OMP_NUM_THREADS') == os.environ.get('OPENBLAS_NUM_THREADS') == os.environ.get('MKL_NUM_THREADS') == '1'
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    folder = ROOT/'runs/pilot_v1'
    folder.mkdir(parents=True, exist_ok=False)
    raw = {}
    for block in cfg['blocks']:
        for generation in range(cfg['branch_generation']-1, cfg['terminal_generation']+1):
            name = f'boundary_{block:06d}_g{generation}.npz'
            raw[name] = sha(source/name)
        for name in (f'assay_{block:06d}_h32.npz', f'cases_{block:06d}.npz'):
            raw[name] = sha(source/name)
    write_json(folder/'raw_inputs.json', dict(source=str(source), status='ALREADY_EXPOSED_DEVELOPMENT_COHORT',
        created_at_utc=stamp(), files=raw))
    # Snapshot code/protocol/config, tests, technical evidence and native sources.
    originals = [p for p in sorted(ROOT.rglob('*')) if p.is_file()
                 and 'runs' not in p.relative_to(ROOT).parts and '__pycache__' not in p.relative_to(ROOT).parts]
    hashes = {}
    for path in originals:
        relative = path.relative_to(ROOT)
        dest = folder/'inputs'/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        hashes[str(relative)] = sha(path)
    manifest = dict(status='READY_TO_LAUNCH', created_at_utc=stamp(), config=cfg,
        protocol_sha256=sha(ROOT/'PROTOCOL.md'), code_sha256=hashes,
        raw_inputs_sha256=sha(folder/'raw_inputs.json'), forecast_seconds=benchmark['forecast_cpu_seconds'],
        process_count=1, numerical_threads=1, polling='NONE_AUTOMATIC',
        endpoint_analysis='Automatic after all eight blocks pass replay; failures stop the worker and retain evidence.',
        executable=sys.executable, source=str(source))
    write_json(folder/'manifest.json', manifest)
    write_json(folder/'START.json', dict(status='RUNNING', launched_at_utc=stamp(), manifest_sha256=sha(folder/'manifest.json')))
    with (folder/'console.log').open('xb') as log:
        child = subprocess.Popen([sys.executable, '-B', str(ROOT/'run.py'), '--run', str(folder)],
            cwd=ROOT, env=os.environ.copy(), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True)
    receipt = dict(status='LAUNCHED', pid=child.pid, launched_at_utc=stamp(), run=str(folder),
        forecast_minutes=benchmark['forecast_cpu_seconds']/60, detached=True, polling=False,
        raw_input_files=len(raw), frozen_source_files=len(hashes),
        completion_report=str(folder/'REPORT.md'), completion_marker=str(folder/'COMPLETE.json'),
        supervisor='A blocking OS wait holds the persistent execution session; no status polling.')
    write_json(folder/'LAUNCH.json', receipt)
    with (folder/'PID').open('x') as f:
        f.write(str(child.pid)+'\n')
    print(json.dumps(receipt, indent=2), flush=True)
    # Some command sandboxes reclaim descendants when their init exits. Keep a
    # quiet supervisor alive in the persistent tool session. This is one blocking
    # wait, not a timer or polling loop; the numerical worker is independently
    # session-detached and writes its own COMPLETE/FAILED markers and report.
    raise SystemExit(child.wait())


if __name__ == '__main__':
    main()
