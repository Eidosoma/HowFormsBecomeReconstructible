"""Post hoc all-case saved-record diagnosis, append-only outputs and verification."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, finish, new_run, rng, sha, utc
from E015_functional_inheritance.audit import verify
from E032_renewal_failure_diagnosis import metrics as m, audit
import numpy as np


def inputs():
    return [ROOT/'common.py', ROOT/'run_python.sh', ROOT/'E015_functional_inheritance/audit.py']+[HERE/p for p in (
        'metrics.py', 'run.py', 'audit.py', 'tests.py', 'plot.py', 'PROTOCOL.md', 'SOURCE_DATA.json')]


def source_check():
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest, rel
    for key in ('source_run', 'fixture_run'): verify(ROOT/index[key])
    assert json.loads((ROOT/'E031_renewal_durability/analysis/closeout_v1.json').read_text())['status'] == 'PASS'
    return index


def statistics(numerator, denominator, draws):
    n, d = np.asarray(numerator, float), np.asarray(denominator, float)
    bn, bd = n[draws].sum(axis=1), d[draws].sum(axis=1)
    valid = bd > 0
    return dict(mean=float(n.sum()/d.sum()) if d.sum() else None,
        ci95=np.quantile(bn[valid]/bd[valid], [.025, .975]).tolist() if valid.any() else None,
        block_numerators=n.tolist(), block_denominators=d.tolist(), valid_bootstrap_draws=int(valid.sum()))


def summarize(data, ids):
    draws = rng('E032', 'bootstrap', 'diagnosis').integers(0, len(ids), (10000, len(ids)))
    series = {}
    definitions = {}
    def add(kind, g, c, k, injury=None, subset=None):
        conditions = [m.CONDITIONS[i] for i in (m.ACTIVE if kind in ('body', 'transitions') else m.GRAPH_CONDITIONS if kind == 'graph' else range(10))]
        fields = dict(packet=m.PACKET_FIELDS, body=m.OUTPUT_FIELDS, terminal=m.OUTPUT_FIELDS, graph=m.GRAPH_FIELDS, transitions=m.TRANSITION_FIELDS)[kind]
        generation = m.HORIZONS[g] if kind == 'terminal' else g+1 if kind in ('body', 'transitions') else g
        key = f'{kind}.g{generation}.{conditions[c]}.'+(m.DAMAGE[injury]+'.' if injury is not None else '')+fields[k]
        x = data[kind][:, g, c, :, :, injury, k] if injury is not None else data[kind][:, g, c, :, :, k]
        selected = np.ones(x.shape, bool)
        if subset:
            s, n, success = subset['stage'], subset['condition'], subset['success']
            y = data['body'][:, s, n, :, :, 0] if subset['kind'] == 'body' else data['terminal'][:, s, n, :, :, 0, 0]
            selected = y.astype(bool) == success
            key += f"|{subset['kind']}_{'success' if success else 'failure'}"
        n = (x*selected).sum(axis=(1, 2)); d = selected.sum(axis=(1, 2))
        assert key not in series
        series[key] = statistics(n, d, draws)
        definitions[key] = dict(kind=kind, stage=g, condition=c, feature=k, injury=injury, subset=subset)
    for kind in ('packet', 'graph', 'body', 'terminal', 'transitions'):
        arr = data[kind]
        for g in range(arr.shape[1]):
            for c in range(arr.shape[2]):
                for k in range(arr.shape[-1]):
                    for d in (range(3) if kind == 'terminal' else (None,)): add(kind, g, c, k, d)
    conditional_fields = (1, 5, 8, 10, 13)
    for g in range(1, 17):
        for a, c in enumerate(m.ACTIVE):
            for success in (True, False):
                subset = dict(kind='body', stage=g-1, condition=a, success=success)
                for k in conditional_fields: add('packet', g, c, k, subset=subset)
                if c in m.GRAPH_CONDITIONS:
                    for k in (0, 1): add('graph', g, m.GRAPH_CONDITIONS.index(c), k, subset=subset)
    for i, g in enumerate(m.HORIZONS[1:], 1):
        for c in range(10):
            for success in (True, False):
                subset = dict(kind='terminal', stage=i, condition=c, success=success)
                for k in conditional_fields: add('packet', g, c, k, subset=subset)
                if c in m.GRAPH_CONDITIONS:
                    for k in (0, 1): add('graph', g, m.GRAPH_CONDITIONS.index(c), k, subset=subset)
    return series, definitions


def report(output, s):
    def f(key):
        x = s['series'][key]
        return 'n/a' if x['mean'] is None else f"{x['mean']:.6g} [{x['ci95'][0]:.6g}, {x['ci95'][1]:.6g}]"
    lines = ['# E032 saved-record failure diagnosis', '',
        '**'+s['status']+'**', '',
        f"{len(s['blocks'])} blocks, {s['lineages']} lineages. Same E031 histories; no new dynamics or causal intervention.", '',
        'All intervals below are pointwise whole-block 95% intervals. Sign changes refer to the acquired record and need not be functionally wrong.', '',
        '## Per-generation packet structure', '',
        '| Generation | Policy | Strong edges | Strong lost to injury | Weak promoted | Newly strong, changed sign | Strong outputs reachable fraction |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for g in range(17):
        for c in ('maturing', 'strength_compensated'):
            keys = [f'packet.g{g}.{c}.{k}' for k in ('strong', 'physical_strong_lost', 'weak_promoted', 'new_strong_changed_sign')]
            keys.append(f'graph.g{g}.{c}.output_reachable_fraction')
            lines.append(f'| {g} | {c} | '+' | '.join(f(k) for k in keys)+' |')
    lines += ['', '## Current body failure classes', '',
        '| Generation | Policy | Both correct | Both reversed | At least one locked output | Other failure | Never failed yet | Recovery |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for g in range(1, 17):
        for c in ('maturing', 'strength_compensated'):
            keys = [f'body.g{g}.{c}.{k}' for k in m.OUTPUT_FIELDS[:4]]
            keys += [f'transitions.g{g}.{c}.{k}' for k in ('never_failed_yet', 'recovery')]
            lines.append(f'| {g} | {c} | '+' | '.join(f(k) for k in keys)+' |')
    lines += ['', '## Terminal failure classes', '',
        '| Horizon | Policy | Injury | Both correct | Both reversed | Locked output | Other |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for g in m.HORIZONS:
        for c in ('maturing', 'strength_compensated'):
            for d in m.DAMAGE:
                lines.append(f'| {g} | {c} | {d} | '+' | '.join(f(f'terminal.g{g}.{c}.{d}.{k}') for k in m.OUTPUT_FIELDS[:4])+' |')
    lines += ['', '## Interpretation limits', '',
        'Strong-edge reachability omits weak edges and signs; it is a diagnostic graph, not the actual reader. Output locking describes measured ports and does not prove an attractor or a causal role. Conditional successful/failed groups are selected after outcomes; their associations cannot establish a repair mechanism. Successive body challenges differ, so recovery and first-failure curves do not measure irreversible survival. All ten policies, per-block numerators/denominators and all conditional measurements are retained in summary.json. A subsequent intervention requires a separate frozen design.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')


def execute(mode):
    started = time.monotonic(); cap_cpus(8)
    index = source_check()
    technical = mode == 'benchmark'
    source = ROOT/index['fixture_run' if technical else 'source_run']
    ids = [900031] if technical else index['source_blocks']
    name = 'benchmark_v1' if technical else 'diagnosis_v1'
    output = HERE/'runs'/name; job = HERE/'jobs'/name
    if job.exists(): raise FileExistsError(job)
    new_run(job, inputs(), dict(mode=mode, no_dynamics=True, pid=os.getpid()))
    output = new_run(output, inputs(), dict(experiment='E032', mode=mode, blocks=ids,
        source=str(source.relative_to(ROOT)), cpu_affinity=cap_cpus(8), numerical_threads=1))
    dump(job/'status.json', dict(status='RUNNING', stage='extraction', utc=utc(), pid=os.getpid()))
    try:
        t = time.monotonic(); collected = []
        for block in ids:
            values = m.extract(source, block)
            np.savez_compressed(output/f'measurements_{block:06d}.npz', **values)
            collected.append(values)
        extraction_seconds = time.monotonic()-t
        dump(job/'status.json', dict(status='RUNNING', stage='independent_measurement_verification', utc=utc(), pid=os.getpid()))
        t = time.monotonic()
        for block, values in zip(ids, collected): assert audit.inspect(source, block, values)
        audit_seconds = time.monotonic()-t
        all_data = {k:np.stack([a[k] for a in collected]) for k in collected[0]}
        series, definitions = summarize(all_data, ids)
        summary = dict(experiment='E032', status='TECHNICAL_ONLY' if technical else 'EXPLORATORY_DIAGNOSIS_COMPLETE',
            blocks=ids, lineages=len(ids)*4*all_data['packet'].shape[4], source=str(source.relative_to(ROOT)),
            no_new_trajectories=True, prior_cases_reused=True, causal_claim_established=False,
            conditions=m.CONDITIONS, active=m.ACTIVE, graph_conditions=m.GRAPH_CONDITIONS, horizons=m.HORIZONS,
            fields=dict(packet=m.PACKET_FIELDS, body=m.OUTPUT_FIELDS, terminal=m.OUTPUT_FIELDS, graph=m.GRAPH_FIELDS, transitions=m.TRANSITION_FIELDS),
            series=series, definitions=definitions, interval_scope='Exploratory pointwise whole-block bootstrap',
            extraction_seconds=extraction_seconds, independent_measurement_seconds=audit_seconds)
        audit.check_aggregates(summary, all_data)
        audit.check_statistics(summary)
        # Reproduce the already audited E031 body/terminal means under the declared axes.
        original = json.loads((source/'summary.json').read_text())
        for g in range(1, 17):
            for c in [m.CONDITIONS[i] for i in m.ACTIVE]:
                assert series[f'body.g{g}.{c}.both_correct']['mean'] == original['body_reading'][str(g)][c]['both_cues']['mean']
        for g in m.HORIZONS:
            for c in m.CONDITIONS:
                for d in m.DAMAGE:
                    expected = original['groups'][str(g)]['local_strength']['initial' if g == 0 else c]['both_cues'][d]['own']['mean']
                    assert series[f'terminal.g{g}.{c}.{d}.both_correct']['mean'] == expected
        dump(output/'summary.json', summary); report(output, summary)
        finish(output, started, dict(experiment='E032', blocks_completed=len(ids)))
        dump(output/'INDEPENDENT_AUDIT.json', dict(status='PASS', utc=utc(), measurement_seconds=audit_seconds,
            scalar_packet_metrics_verified=True, graph_union_find_verified=True, all_output_classes_verified=True,
            first_failure_and_recovery_verified=True, all_aggregates_and_intervals_verified=True,
            source_scores_reproduced=True, no_new_trajectories=True, complete_sha256=sha(output/'COMPLETE.json'), audit_code_sha256=sha(HERE/'audit.py')))
        subprocess.run([sys.executable, '-B', str(HERE/'plot.py'), str(output)], check=True)
        check_inputs(job); check_inputs(output)
        elapsed = time.monotonic()-started
        if technical:
            predicted = 1.5*(extraction_seconds+audit_seconds)*32*2+60
            forecast = dict(utc=utc(), forecast_seconds=predicted,
                benchmark_workflow_seconds=elapsed, extraction_seconds=extraction_seconds,
                independent_measurement_seconds=audit_seconds, formula='1.5*(extraction_seconds+independent_measurement_seconds)*32*2+60',
                detached_required=predicted > 600, benchmark_complete_sha256=sha(output/'COMPLETE.json'),
                benchmark_audit_sha256=sha(output/'INDEPENDENT_AUDIT.json'), inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs()})
            path = HERE/'analysis/forecast_v1.json'; assert not path.exists(); dump(path, forecast)
        dump(job/'status.json', dict(status='COMPLETE', utc=utc(), seconds=elapsed,
            complete_sha256=sha(output/'COMPLETE.json'), audit_sha256=sha(output/'INDEPENDENT_AUDIT.json'),
            figure_provenance_sha256=sha(HERE/'figures'/name/'provenance.json'), automatic_successor_started=False))
        print(json.dumps(dict(status='COMPLETE', mode=mode, seconds=elapsed, extraction_seconds=extraction_seconds,
            independent_measurement_seconds=audit_seconds, output=str(output)), indent=2), flush=True)
    except BaseException:
        dump(job/'status.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc()))
        dump(output/'FAILED.json', dict(status='FAILED', traceback=traceback.format_exc()))
        raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--mode', choices=('benchmark', 'scientific'), required=True)
    parser.add_argument('--detach', action='store_true'); parser.add_argument('--child', action='store_true')
    args = parser.parse_args(); cap_cpus(8)
    if args.mode == 'scientific':
        f = json.loads((HERE/'analysis/forecast_v1.json').read_text())
        for rel, digest in f['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
        if f['detached_required'] and not (args.detach or args.child): raise ValueError('Forecast >600s; detach required')
    if args.detach:
        assert not args.child
        name = 'benchmark_v1' if args.mode == 'benchmark' else 'diagnosis_v1'
        logpath = HERE/'analysis'/f'{name}_launcher.log'
        with logpath.open('x') as log:
            cmd = [sys.executable, '-B', str(Path(__file__).resolve()), '--mode', args.mode, '--child']
            p = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        dump(HERE/'analysis'/f'{name}_launch.json', dict(utc=utc(), pid=p.pid, command=cmd))
        print('Detached PID', p.pid, flush=True)
    else: execute(args.mode)


if __name__ == '__main__': main()
