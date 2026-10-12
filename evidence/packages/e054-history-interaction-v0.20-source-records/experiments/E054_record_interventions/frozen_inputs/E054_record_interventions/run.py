"""Immutable block evidence and simulation driver; workflow owns launch policy."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import cap_cpus, check_inputs, dump, finish, new_run, sha, utc
from E054_record_interventions import model, data, inference
from E054_record_interventions.plan import HERE, ROOT, NAMES, settings


def input_paths():
    external = ('common.py', 'run_python.sh', 'RUN_POLICY.md',
        'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py',
        'E017_reader_timing/audit.py', 'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py')
    local = ('PROTOCOL.md', 'SOURCE_DATA.json', 'plan.py', 'model.py', 'data.py', 'inference.py',
             'audit_model.py', 'audit.py', 'run.py', 'workflow.py', 'tests.py', 'plot.py',
             'analysis/design_v1/manifest.json', 'analysis/prepare.py')
    return [ROOT/p for p in external]+[HERE/p for p in local]


def design_check():
    frozen = json.loads((HERE/'analysis/design_v1/manifest.json').read_text())
    for name, digest in frozen['sha256'].items():
        assert sha(HERE/name) == digest == sha(HERE/'analysis/design_v1'/name)


def block(output, b, cfg):
    started = time.monotonic()
    original = data.source(cfg['mode'], b)
    assert original['records'].shape[2] == cfg['recipients']
    inter = model.intervene(original['records'], original['repair'], b)
    raw = model.assay(inter, b, cfg)
    measures, controls = inference.diagnostics(inter, raw)
    cases = dict(**model.scores(raw), **measures, exposure=inter['exposure'],
                 graph_before=inter['graph_before'], graph_after=raw['graph_after'])
    for kind, values in (('source', original), ('interventions', inter), ('assay', raw), ('cases', cases)):
        data.save(output/f'{kind}_{b:06d}.npz', values)
    dump(output/f'worker_{b}.json', dict(block=b, seconds=time.monotonic()-started,
         controls=controls, records=5*4*cfg['recipients'], terminal_cue_observations=55*4*cfg['recipients']*2*3))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', required=True, choices=NAMES)
    p.add_argument('--worker', type=int); p.add_argument('--workers', type=int, default=1)
    a = p.parse_args(); assert 1 <= a.workers <= 8; cap_cpus(a.workers)
    run = HERE/'runs'/NAMES[a.mode]; cfg = settings(a.mode)
    if a.worker is not None:
        check_inputs(run); assert a.worker in cfg['blocks']; block(run, a.worker, cfg); return
    job = HERE/'jobs'/NAMES[a.mode]; check_inputs(job)
    assert json.loads((job/'status.json').read_text())['stage'] == 'simulation'
    started = time.monotonic(); design_check(); check_inputs(HERE/'analysis/freeze_v1')
    new_run(run, input_paths(), dict(experiment='E054', **cfg, workers=a.workers,
        cohort_reused=True, predecessor_evidence=json.loads((job/'manifest.json').read_text())['contract']['predecessor_evidence']))
    def launch(b):
        with (run/f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'run.py'), '--mode', a.mode, '--worker', str(b),
                            '--workers', str(a.workers)], cwd=ROOT, stdin=subprocess.DEVNULL,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        return b
    try:
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for b in pool.map(launch, cfg['blocks']): print('Completed simulation block', b, flush=True)
        cases = [data.load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']]
        controls = [json.loads((run/f'worker_{b}.json').read_text())['controls'] for b in cfg['blocks']]
        summary = inference.analyze(cases, controls, a.mode)
        dump(run/'summary.json', summary); (run/'REPORT.md').write_text(inference.report(summary))
        finish(run, started, dict(experiment='E054', blocks_completed=len(cfg['blocks'])))
    except BaseException:
        dump(run/'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__': main()
