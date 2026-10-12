"""Freeze and technical closeout; never launches or reads E053 scientific data."""
import argparse
import json
import math
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E015_functional_inheritance.audit import verify
from E054_record_interventions.plan import HERE, ROOT
from E054_record_interventions.run import input_paths, design_check


def freeze():
    cap_cpus(1); design_check()
    path = new_run(HERE/'analysis/freeze_v1', input_paths(), dict(experiment='E054', stage='code_freeze', scientific_outcomes_seen=False))
    print('Frozen', len(json.loads((path/'manifest.json').read_text())['inputs_sha256']), 'inputs')


def ready(figures_inspected):
    assert figures_inspected, 'Inspect both technical figures first'
    check_inputs(HERE/'analysis/freeze_v1'); evidence = {}
    for name in ('fixture_v1', 'benchmark_v1'):
        run = HERE/'runs'/name; m = verify(run)
        assert m['inputs_sha256'] == json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256']
        a = json.loads((run/'INDEPENDENT_AUDIT.json').read_text()); s = json.loads((run/'summary.json').read_text())
        assert a['status'] == 'PASS' and a['complete_sha256'] == sha(run/'COMPLETE.json')
        assert a['audit_code_sha256'] == sha(HERE/'audit.py') and a['all_source_interventions_graphs_couplings_trajectories_scores_replayed']
        assert a['summaries_checked'] == len(s['statistics']) and s['controls_pass']
        assert s['status'] == 'TECHNICAL_ONLY' and all(v is None for v in s['primary_classifications'].values())
        job = HERE/'jobs'/name; check_inputs(job)
        status = json.loads((job/'status.json').read_text()); assert status['status'] == 'COMPLETE'
        assert status['complete_sha256'] == sha(run/'COMPLETE.json') and status['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
        fig = HERE/'figures'/name/'provenance.json'; metadata = json.loads(fig.read_text())
        assert metadata['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json') and metadata['summary_sha256'] == sha(run/'summary.json')
        assert metadata['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in metadata['outputs_sha256'].items(): assert sha(fig.parent/rel) == digest
        for p in (run/'COMPLETE.json', run/'INDEPENDENT_AUDIT.json', fig, job/'status.json'):
            evidence[str(p.relative_to(ROOT))] = sha(p)
    log = HERE/'analysis/tests_v1.log'; text = log.read_text()
    assert '\nOK\n' in text and 'Ran 19 tests' in text
    evidence[str(log.relative_to(ROOT))] = sha(log)
    bench = HERE/'runs/benchmark_v1'
    sim = json.loads((bench/'worker_900041.json').read_text())['seconds']
    replay = json.loads((bench/'INDEPENDENT_AUDIT.json').read_text())['worker_seconds'][0]
    size = sum(p.stat().st_size for p in bench.rglob('*') if p.is_file())
    # Benchmark already contains all histories/arms/injuries; scale steps16, R4,
    # four waves of eight blocks. Applying the step factor to I/O/graphs is conservative.
    seconds = 3*(sim+replay)*16*4*4+120
    storage = math.ceil(1.5*size*4*32)+128*1024**2
    forecast = dict(utc=utc(), workers=8, benchmark_simulation_seconds=sim, benchmark_audit_seconds=replay,
        forecast_seconds=seconds, detached_required=seconds > 600, source_records_reused=True,
        benchmark_bytes=size, storage_with_reserve_bytes=storage, free_bytes=shutil.disk_usage(HERE).free,
        basis='3x (simulation+audit) x16 read steps x4 recipients x4 waves, plus120s; includes conservative scaling of graph/I/O time',
        benchmark_complete_sha256=sha(bench/'COMPLETE.json'), benchmark_audit_sha256=sha(bench/'INDEPENDENT_AUDIT.json'))
    assert forecast['free_bytes'] > storage
    dest = HERE/'analysis/forecast_v1.json'; assert not dest.exists(); dump(dest, forecast)
    evidence[str(dest.relative_to(ROOT))] = sha(dest)
    result = dict(status='PASS', utc=utc(), tests=19, figures_inspected=True,
        inputs_sha256=json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256'],
        evidence_sha256=evidence, scientific_run_started=False, automatic_successor_started=False,
        source='E051 audited records; all32 blocks, no success filtering',
        pending='E053 complete+independent audit+closeout and an explicit launch; no polling installed')
    dest = HERE/'analysis/technical_v1.json'; assert not dest.exists(); dump(dest, result)
    print(json.dumps(dict(status='READY_PENDING_E053_CLOSEOUT', forecast_seconds=seconds,
        storage_with_reserve_bytes=storage, tests=19), indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze', action='store_true'); p.add_argument('--ready', action='store_true')
    p.add_argument('--figures-inspected', action='store_true'); a = p.parse_args()
    assert a.freeze != a.ready
    if a.freeze: freeze()
    else: ready(a.figures_inspected)
