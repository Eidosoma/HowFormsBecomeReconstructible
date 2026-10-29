#!/usr/bin/env python3
"""Supervised bounded study runner. Main study requires an explicit frozen package."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np
from fep_structured_inference import (
    Budget, Inference, ResourceStop, WORK_LEVELS, decode, enumerate_exact,
    exact_elimination, model, rss_bytes,
)

HERE = Path(__file__).resolve().parent
DEST = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-structured-inference-v1')
SOURCE_NAMES = ['FEP_STRUCTURED_INFERENCE_TEST_DESIGN_V1.md',
                'FEP_STRUCTURED_INFERENCE_V1.md', 'fep_structured_inference.py',
                'run_fep_structured_inference.py', 'check_fep_structured_inference.py']
THREAD_ENV = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')


def identity(path):
    p = Path(path).resolve()
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def json_default(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    raise TypeError(type(x).__name__)


def save(path, obj):
    p = Path(path)
    temp = p.with_name(p.name+'.tmp')
    temp.write_text(json.dumps(obj, default=json_default, indent=2, allow_nan=False)+'\n')
    temp.replace(p)


def validate_destination(output):
    output = Path(output).resolve()
    if output.parent != DEST or not os.path.ismount('/mnt/bioIce1'):
        raise ValueError('require the mounted external FEP attempt namespace')
    return output


def verify_freeze(freeze):
    if freeze['status'] != 'qualified_frozen':
        raise ValueError('unqualified package')
    for entry in freeze['inputs']:
        if identity(entry['path']) != entry:
            raise ValueError('frozen package mismatch')
    return freeze['inputs']


def prepare(output, inputs, purpose):
    output = validate_destination(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'sources').mkdir()
    for index, entry in enumerate(inputs):
        if identity(entry['path']) != entry:
            raise ValueError('input changed before preparation')
        shutil.copyfile(entry['path'], output/'sources'/f"{index:02d}-{Path(entry['path']).name}")
    manifest = {'status': 'prepared', 'purpose': purpose,
                'started_utc': datetime.now(timezone.utc).isoformat(), 'inputs': inputs}
    save(output/'MANIFEST.json', manifest)
    return manifest


def seal(output, manifest, status):
    for entry in manifest['inputs']:
        if identity(entry['path']) != entry:
            raise ValueError('source changed during execution')
    files = sorted(p for p in output.rglob('*') if p.is_file() and p != output/'MANIFEST.json')
    manifest.update(status=status, outputs=[identity(p) for p in files])
    save(output/'MANIFEST.json', manifest)


def proc_usage(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        cpu = (int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
        rss = int(Path(f'/proc/{pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
        return cpu, rss
    except (FileNotFoundError, ProcessLookupError):
        return 0., 0


def supervise(command, directory, cpu=300., memory=512*1024**2):
    """Local runner supervision, not interactive agent polling; preserves killed jobs."""
    directory.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env.update({k: '1' for k in THREAD_ENV})
    start = time.monotonic()
    peak_cpu, peak_rss, reason = 0., 0, None
    with (directory/'PROCESS_LOG.txt').open('w') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   env=env, cwd=HERE, start_new_session=True)
        while process.poll() is None:
            used, rss = proc_usage(process.pid)
            peak_cpu, peak_rss = max(peak_cpu, used), max(peak_rss, rss)
            if used >= cpu or rss > memory:
                reason = 'cpu_limit' if used >= cpu else 'memory_limit'
                process.kill()
                break
            time.sleep(.02)
        rc = process.wait()
    status = 'censored' if reason else ('completed' if rc == 0 else 'failed')
    record = {'status': status, 'reason': reason, 'returncode': rc,
              'observed_cpu_seconds': peak_cpu, 'observed_peak_rss_bytes': peak_rss,
              'elapsed_seconds': time.monotonic()-start,
              'cpu_limit': cpu, 'memory_limit': memory, 'sample_period_seconds': .02}
    save(directory/'SUPERVISION.json', record)
    return record


def worker(job_path, output):
    job = json.loads(Path(job_path).read_text())
    startup_cpu = time.process_time()
    limit = Budget()
    try:
        begin = time.process_time()
        m = model(job['rows'], job['cols'], job['h'], job['record'], main=job['main'])
        preparation = time.process_time()-begin
        if job['kind'] == 'exact':
            reference = exact_elimination(m, limit)
            begin = time.process_time()
            reference['decisions'] = decode(m, reference['nodes'], reference['pairs'])
            decoding = time.process_time()-begin
            validation_cpu = 0.
            if m.main and m.n == 16:
                begin = time.process_time()
                independent = enumerate_exact(m)
                for key in ('nodes', 'pairs'):
                    if np.max(np.abs(independent[key]-reference[key])) > 1e-10:
                        raise ArithmeticError('L=4 independent reference mismatch')
                if abs(independent['log_z']-reference['log_z']) > 1e-9:
                    raise ArithmeticError('L=4 independent evidence mismatch')
                validation_cpu = time.process_time()-begin
            result = {'status': 'completed', 'job': job, 'reference': reference,
                      'timing': {'preparation_cpu': preparation, 'startup_cpu': startup_cpu,
                                 'inference_cpu': reference['metadata']['cpu_seconds'],
                                 'decoding_cpu': decoding, 'validation_cpu': validation_cpu}}
        else:
            inf = Inference(m, job['kind'], job['order'], limit)
            save(output/'INITIAL.json', inf.initial)
            snapshots = []
            for level in WORK_LEVELS:
                s = inf.advance(level*len(m.edges))
                snapshots.append(s)
                save(output/f'CHECKPOINT_{level}.json', s)
            result = {'status': 'completed', 'job': job, 'model': m.description(),
                      'initial_work': inf.initial_work, 'snapshots': snapshots,
                      'sweeps': inf.sweeps, 'offending_updates': inf.offending_updates,
                      'preparation_cpu': preparation, 'startup_cpu': startup_cpu}
        limit.check()
        result.update(process_cpu_seconds=time.process_time(), rss_bytes=rss_bytes(),
                      sampled_peak_rss_bytes=limit.peak, python=platform.python_version(),
                      peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      numpy=np.__version__)
        save(output/'RESULTS.json', result)
    except ResourceStop as exc:
        save(output/'RESULTS.json', {'status': 'censored', 'job': job, 'reason': str(exc)})
    except Exception:
        save(output/'RESULTS.json', {'status': 'failed', 'job': job,
                                   'traceback': traceback.format_exc()})
        raise


def execute_job(job, directory):
    config = directory.parent/(directory.name+'_job.json')
    save(config, job)
    supervision = supervise([sys.executable, '-B', str(Path(__file__).resolve()),
                             '--worker', str(config), '--worker-output', str(directory)], directory)
    if supervision['status'] != 'completed' or not (directory/'RESULTS.json').exists():
        return {'status': supervision['status'], 'job': job, 'supervision': supervision}
    result = json.loads((directory/'RESULTS.json').read_text())
    result['supervision'] = supervision
    return result


def evaluate(m, snap, ref):
    nodes, pairs = np.asarray(snap['nodes']), np.asarray(snap['pairs'])
    reference = {'pairs': np.asarray(ref['pairs'])}
    original = decode(m, nodes, pairs, reference, snap['owner'])
    product = decode(m, nodes, np.asarray(snap['product_pairs']), reference, snap['owner'])
    internal = [i for i, r in enumerate(original) if r['internal']]
    return {'queries': original, 'product_queries': product,
            'mean_action_error': float(np.mean([abs(r['action_error']) for r in original])),
            'max_risk_excess': max(r['risk_excess'] for r in original),
            'nondegenerate_fraction': float(np.mean([
                .01 < r['exact']['r'] < r['exact']['r_free']-.01 for r in original])),
            'internal_risk_error': None if not internal else float(np.mean([
                abs(original[i]['risk_errors'][1]) for i in internal])),
            'internal_product_error': None if not internal else float(np.mean([
                abs(product[i]['risk_errors'][1]) for i in internal])),
            'node_errors': nodes-np.asarray(ref['nodes']),
            'max_node_error': float(np.max(np.abs(nodes-np.asarray(ref['nodes'])))),
            'F': snap['F'], 'exact_KL': snap['F']+ref['log_z']}


def gate(rows, expected_fixtures):
    """All final rows must exist; no selected-size or selected-order aggregation."""
    complete = len(rows) == expected_fixtures*4 and all(r['status'] == 'completed' for r in rows)
    if not complete:
        return {'passed': False, 'reason': 'incomplete_references_or_trajectories'}
    keys = [(r['fixture'], r['kind'], r['order']) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('duplicate gate rows')
    by_kind = {kind: [r for r in rows if r['kind'] == kind] for kind in ('mf', 'block')}
    if any(len(v) != expected_fixtures*2 for v in by_kind.values()):
        raise ValueError('unbalanced gate rows')
    a = {k: float(np.mean([r['metrics']['mean_action_error'] for r in v])) for k, v in by_kind.items()}
    v = {k: max(r['metrics']['max_risk_excess'] for r in val) for k, val in by_kind.items()}
    strata = {}
    for h in sorted({r['h'] for r in rows}):
        strata[h] = {k: float(np.mean([r['metrics']['mean_action_error'] for r in val if r['h'] == h]))
                     for k, val in by_kind.items()}
        # Count actual directed queries, not duplicated orders or inference families.
        base = [r for r in by_kind['mf'] if r['h'] == h and r['order'] == 'forward']
        total = sum(r['query_count'] for r in base)
        strata[h]['nondegenerate_fraction'] = sum(
            r['query_count']*r['metrics']['nondegenerate_fraction'] for r in base)/total
    block = by_kind['block']
    correlation_gain = float(np.mean([r['metrics']['internal_product_error']-
                                      r['metrics']['internal_risk_error'] for r in block]))
    informative = all(s['nondegenerate_fraction'] >= .25 for s in strata.values())
    decision_ok = (a['block'] <= .9*a['mf'] and a['mf']-a['block'] >= .001 and
                   v['block'] <= v['mf']+1e-6 and
                   all(s['block'] <= s['mf']+1e-8 for s in strata.values()))
    return {'passed': bool(informative and decision_ok and correlation_gain >= 1e-5),
            'complete': True, 'informative': informative, 'decision_pass': bool(decision_ok),
            'correlation_pass': bool(correlation_gain >= 1e-5),
            'mean_action_errors': a, 'max_risk_excesses': v, 'strata': strata,
            'correlation_gain': correlation_gain}


def phase(output, sides, workers):
    configs = []
    for side in sides:
        for h in (1e-6, .01):
            for record in ('fail', 'mixed'):
                fixture = f'L{side}_h{h:g}_{record}'
                common = {'rows': side, 'cols': side, 'h': h, 'record': record,
                          'main': True, 'fixture': fixture}
                configs.append(dict(common, kind='exact', order='none'))
                for kind in ('mf', 'block'):
                    for order in ('forward', 'reverse'):
                        configs.append(dict(common, kind=kind, order=order))
    def one(job):
        name = f"{job['fixture']}_{job['kind']}_{job['order']}"
        return execute_job(job, output/name)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, configs))
    if any(r['status'] == 'failed' for r in results):
        save(output/f'PHASE_{sides[0]}_FAILED.json',
             [{'job': r['job'], 'status': r['status']} for r in results])
        raise ArithmeticError('main worker failed; no scientific gate verdict')
    references = {r['job']['fixture']: r for r in results if r['job']['kind'] == 'exact'}
    rows = []
    for result in results:
        job = result['job']
        if job['kind'] == 'exact':
            continue
        ref = references[job['fixture']]
        row = {k: job[k] for k in ('fixture', 'kind', 'order', 'h', 'rows')}
        row['status'] = 'unavailable'
        if result['status'] == ref['status'] == 'completed':
            m = model(job['rows'], job['cols'], job['h'], job['record'], main=True)
            evaluations = [evaluate(m, s, ref['reference']) for s in result['snapshots']]
            save(output/f"{job['fixture']}_{job['kind']}_{job['order']}_evaluation.json", evaluations)
            row.update(status='completed', metrics={k: v for k, v in evaluations[-1].items()
                        if k not in ('queries', 'product_queries', 'node_errors')}, query_count=2*len(m.edges))
            timing = result['snapshots'][-1]['timing']
            approximation_cpu = (result['startup_cpu']+result['preparation_cpu']+
                                 sum(timing[k] for k in ('initialization_cpu', 'inference_cpu', 'decoding_cpu')))
            exact_cpu = sum(ref['timing'][k] for k in (
                'startup_cpu', 'preparation_cpu', 'inference_cpu', 'decoding_cpu'))
            row['cost'] = {'approximation_cpu': approximation_cpu, 'exact_cpu': exact_cpu,
                           'approximation_peak_rss': result['peak_rss_bytes'],
                           'exact_peak_rss': ref['peak_rss_bytes'],
                           'faster_and_no_more_memory': approximation_cpu < exact_cpu and
                               result['peak_rss_bytes'] <= ref['peak_rss_bytes']}
        rows.append(row)
    return rows, [{'job': r['job'], 'status': r['status']} for r in results]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--worker-output', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--freeze', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.worker_output)
        return
    if args.output is None or args.freeze is None or not 1 <= args.workers <= 4:
        parser.error('explicit output, frozen package and one to four workers required')
    freeze = json.loads(args.freeze.read_text())
    verify_freeze(freeze)
    output = validate_destination(args.output)
    inputs = freeze['inputs']+[identity(args.freeze)]
    manifest = prepare(output, inputs, 'main_core_and_conditional_scale')
    try:
        core, statuses = phase(output, (4, 8), args.workers)
        verdict = gate(core, 8)
        save(output/'CORE.json', {'rows': core, 'statuses': statuses, 'gate': verdict})
        scales = {}
        if verdict['passed']:
            for side in (16, 24):
                rows, statuses = phase(output, (side,), args.workers)
                scales[side] = {'rows': rows, 'statuses': statuses, 'gate': gate(rows, 4)}
                save(output/f'SCALE_{side}.json', scales[side])
        save(output/'RESULTS.json', {'status': 'completed', 'core_gate': verdict,
                                   'scale_executed': bool(verdict['passed']), 'scales': scales})
        seal(output, manifest, 'completed')
    except Exception:
        (output/'FAILURE.txt').write_text(traceback.format_exc())
        seal(output, manifest, 'failed')
        raise


if __name__ == '__main__':
    main()
