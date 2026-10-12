"""Immutable E055 block evidence; the workflow manages launch and stages."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import cap_cpus, check_inputs, dump, finish, new_run
from E055_stress_capture_recovery import data, model, inference
from E055_stress_capture_recovery.plan import HERE, ROOT, NAMES, settings


def input_paths():
    external = ('common.py', 'run_python.sh', 'RUN_POLICY.md',
        'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py',
        'E017_reader_timing/audit.py', 'E022_reader_compensation/model.py',
        'E022_reader_compensation/audit.py', 'E054_record_interventions/model.py',
        'E054_record_interventions/audit_model.py', 'E054_record_interventions/plan.py')
    local = ('PROTOCOL.md', 'SOURCE_DATA.json', 'plan.py', 'data.py', 'model.py',
        'audit_model.py', 'inference.py', 'run.py', 'audit.py', 'workflow.py',
        'tests.py', 'plot.py', 'analysis/prepare.py')
    return [ROOT/p for p in external] + [HERE/p for p in local]


def block(run, b, cfg):
    start = time.monotonic()
    source = data.source(cfg['mode'], b)
    assert source['records'].shape == (3, 4, cfg['recipients'], 2, 16, 16)
    body = model.develop(source['records'], b, cfg)
    outgoing = model.transmit(body, cfg)
    fresh = model.assay(outgoing['packets'], b, cfg)
    cases, controls = model.diagnostics(body, outgoing, fresh, cfg)
    for name, arrays in (('source', source), ('body', body), ('outgoing', outgoing), ('assay', fresh), ('cases', cases)):
        data.save(run/f'{name}_{b:06d}.npz', arrays)
    dump(run/f'worker_{b}.json', dict(block=b, seconds=time.monotonic()-start, controls=controls,
        terminal_cue_observations=21*4*cfg['recipients']*2*3,
        body_boundary_cue_observations=3*2*4*cfg['recipients']*2*3))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', required=True, choices=NAMES)
    p.add_argument('--workers', type=int, default=1); p.add_argument('--worker', type=int)
    a = p.parse_args(); assert 1 <= a.workers <= 8; cap_cpus(a.workers)
    run = HERE/'runs'/NAMES[a.mode]; cfg = settings(a.mode)
    if a.worker is not None:
        check_inputs(run); assert a.worker in cfg['blocks']; block(run, a.worker, cfg); return
    job = HERE/'jobs'/NAMES[a.mode]; check_inputs(job)
    assert json.loads((job/'status.json').read_text())['stage'] == 'simulation'
    check_inputs(HERE/'analysis/freeze_v1')
    started = time.monotonic()
    new_run(run, input_paths(), dict(experiment='E055', **cfg, workers=a.workers,
        cohort_reused=True, predecessor_evidence=json.loads((job/'manifest.json').read_text())['contract']['predecessor_evidence']))
    def launch(b):
        with (run/f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'run.py'), '--mode', a.mode,
                '--workers', str(a.workers), '--worker', str(b)], cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, check=True)
        return b
    try:
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for b in pool.map(launch, cfg['blocks']): print('Completed simulation block', b, flush=True)
        cases = [data.load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']]
        controls = [json.loads((run/f'worker_{b}.json').read_text())['controls'] for b in cfg['blocks']]
        summary = inference.analyze(cases, controls, a.mode)
        dump(run/'summary.json', summary)
        (run/'REPORT.md').write_text(inference.report(summary))
        finish(run, started, dict(experiment='E055', blocks_completed=len(cfg['blocks'])))
    except BaseException:
        dump(run/'FAILED.json', dict(traceback=traceback.format_exc())); raise


if __name__ == '__main__': main()
