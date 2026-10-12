"""Freeze authorized inputs and launch once, detached, with no status polling."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from evidence import ROOT, sha, stamp, verify_sources, verified_prior, write_json
from schedules import validate


def main():
    cfg = json.loads((ROOT/'config.json').read_text())
    validate(cfg)
    source = verify_sources(cfg)
    native_complete = json.loads((source/'COMPLETE.json').read_text())['outputs_sha256']
    prior, prior_complete = verified_prior(cfg)
    benchmark = json.loads((ROOT/'benchmark/COMPLETE.json').read_text())
    assert benchmark['status'] == 'COMPLETE' and benchmark['byte_equal']
    assert benchmark['config_sha256'] == sha(ROOT/'config.json')
    assert benchmark['within_development_cost_ceiling']
    for name, digest in benchmark['code_sha256'].items():
        assert sha(ROOT/name) == digest, name
    validation = json.loads((ROOT/'VALIDATION.json').read_text())
    assert validation['status'] == 'PASS' and validation['tests_passed'] == 8
    for name, digest in validation['files_sha256'].items():
        assert sha(ROOT/name) == digest, name
    assert os.environ.get('OMP_NUM_THREADS') == os.environ.get('OPENBLAS_NUM_THREADS') == os.environ.get('MKL_NUM_THREADS') == '1'
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    assert shutil.disk_usage(ROOT).free > 1024**3, 'Less than 1 GiB free for retained pilot evidence'
    diagnostic_source = (ROOT/cfg['diagnostic_source']).resolve()
    assert sha(diagnostic_source) == cfg['diagnostic_source_sha256']
    folder = ROOT/'runs/pilot_v1'
    folder.mkdir(parents=True, exist_ok=False)
    native_files, prior_files = {}, {}
    for block in cfg['blocks']:
        for generation in range(2, 33):
            name = f'boundary_{block:06d}_g{generation}.npz'
            digest = sha(source/name)
            assert digest == native_complete[name], name
            native_files[name] = digest
        for name in (f'assay_{block:06d}_h32.npz', f'cases_{block:06d}.npz'):
            digest = sha(source/name)
            assert digest == native_complete[name], name
            native_files[name] = digest
        for name in [f'cases_{block:06d}.npz']+[f'boundary_{block:06d}_g{g}.npz' for g in range(3, 10)]:
            digest = sha(prior/name)
            assert digest == prior_complete[name], name
            prior_files[name] = digest
    write_json(folder/'raw_inputs.json', dict(source=str(source), prior_source=str(prior), created_at_utc=stamp(),
        status='EXPOSED_DEVELOPMENT_COHORT_NEW_SCHEDULES_UNSEEN', native_files=native_files, prior_files=prior_files,
        prior_complete_sha256=cfg['prior_complete_sha256'], native_complete_sha256=cfg['native_complete_sha256'],
        diagnostic_source=str(diagnostic_source), diagnostic_source_sha256=cfg['diagnostic_source_sha256']))
    for original, name in ((prior/'COMPLETE.json', 'prior_COMPLETE.json'),
                           (source/'COMPLETE.json', 'native_COMPLETE.json'),
                           (diagnostic_source, 'reference_diagnostics.csv')):
        with (folder/name).open('xb') as f:
            f.write(original.read_bytes())
    originals = [p for p in sorted(ROOT.rglob('*')) if p.is_file() and
        'runs' not in p.relative_to(ROOT).parts and '__pycache__' not in p.relative_to(ROOT).parts]
    hashes = {}
    for path in originals:
        relative = path.relative_to(ROOT)
        destination = folder/'inputs'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        hashes[str(relative)] = sha(path)
    manifest = dict(status='READY_TO_LAUNCH', created_at_utc=stamp(), config=cfg,
        protocol_sha256=sha(ROOT/'PROTOCOL.md'), code_sha256=hashes,
        raw_inputs_sha256=sha(folder/'raw_inputs.json'), forecast_seconds=benchmark['forecast_cpu_seconds'],
        process_count=1, numerical_threads=1, polling='NONE_AUTOMATIC', executable=sys.executable,
        source=str(source), prior_source=str(prior),
        endpoint_analysis='Automatic report, plots and independent table/transfer verification after every block passes its checks.',
        simulated_policy_count=3, analyzed_policy_count=5)
    write_json(folder/'manifest.json', manifest)
    write_json(folder/'START.json', dict(status='RUNNING', launched_at_utc=stamp(), manifest_sha256=sha(folder/'manifest.json')))
    with (folder/'console.log').open('xb') as log:
        child = subprocess.Popen([sys.executable, '-B', str(ROOT/'run.py'), '--run', str(folder)],
            cwd=ROOT, env=os.environ.copy(), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True)
    receipt = dict(status='LAUNCHED', pid=child.pid, launched_at_utc=stamp(), run=str(folder),
        forecast_minutes=benchmark['forecast_cpu_seconds']/60, detached=True, polling=False,
        native_input_files=len(native_files), reused_input_files=len(prior_files), frozen_source_files=len(hashes),
        completion_report=str(folder/'REPORT.md'), completion_marker=str(folder/'COMPLETE.json'),
        supervisor='One blocking OS wait preserves the persistent execution session; no status polling.')
    write_json(folder/'LAUNCH.json', receipt)
    with (folder/'PID').open('x') as f:
        f.write(str(child.pid)+'\n')
    print(json.dumps(receipt, indent=2), flush=True)
    raise SystemExit(child.wait())


if __name__ == '__main__':
    main()
