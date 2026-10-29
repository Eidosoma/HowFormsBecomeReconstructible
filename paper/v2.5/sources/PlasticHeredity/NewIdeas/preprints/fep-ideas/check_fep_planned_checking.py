#!/usr/bin/env python3
"""Freeze and verify one finite analytic checking comparison; no sampled cohort."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from time import perf_counter, process_time
import traceback
import numpy as np
import fep_planned_checking as M
import run_fep_paid_checking as OLD

SOURCE = Path(__file__).resolve().parent
ROOT = OLD.ROOT.parent/'fep-planned-checking-v1'
SPEC = SOURCE/'FEP_PLANNED_CHECKING_V1.md'
PREVIOUS = OLD.ROOT/'attempt-01'
CHECKS = {}
write, digest, utc, resources = OLD.write, OLD.digest, OLD.utc, OLD.resources


def check(name, ok):
    if not bool(ok):
        raise AssertionError(name)
    CHECKS[name] = CHECKS.get(name, 0)+1


def close(name, left, right, atol=M.TOL):
    check(name, np.shape(left) == np.shape(right) and np.allclose(left, right, atol=atol, rtol=0))


def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def state_fingerprint(f):
    return OLD.C.M.fingerprint({key: getattr(f, key) for key in ('w', 'p', 'ys', 'labels', 'u', 'z')})


def evaluate(cases):
    f = M.load(cases)
    h, d = cases[0]['horizon'], cases[0]['clock']
    check('one_horizon_clock', all((c['horizon'], c['clock']) == (h, d) for c in cases))
    before = state_fingerprint(f)
    rows = [dict(id=c['id'], t=c['t'], horizon=h, clock=d, u=float(f.u[i]), risk=float(min(f.u[i], 1-f.u[i])),
                 retention={}) for i, c in enumerate(cases)]
    for retain in (True, False):
        planner = M.Vector(f)
        result, clock, information = planner.inspect(h, d, retain)
        check('inference_not_mutated', state_fingerprint(f) == before)
        standard = f.scores(f.w, f.p, f.z, f.t, h, retain)
        close('unchanged_free_answer_score', result['free']['answer'], standard[0], 2e-12)
        close('unchanged_free_purchase_score', result['free']['purchase'], standard[1], 2e-12)
        close('benefit_decomposition', clock+information,
              result['clock']['answer']-result['clock']['purchase']-result['clock']['risk']+.1, 2e-12)
        check('nonnegative_clock_benefit', np.all(clock >= -M.TOL))
        check('nonnegative_information_value', np.all(information >= -M.TOL))
        if not retain:
            close('lesion_zero_information', information, np.zeros(len(cases)), 0)
        for i, row in enumerate(rows):
            modes = {}
            for mode in M.MODES:
                v = result[mode]
                buy = bool(v['buy'][i])
                modes[mode] = dict(cost=float(v['value'][i]), purchases=float(v['purchases'][i]),
                                   answer_score=float(v['answer'][i]), purchase_score=float(v['purchase'][i]),
                                   buy=buy, action=2 if buy else int((cases[i]['y'] >> 1) ^ (f.u[i] > .5)),
                                   near_root=bool(v['near_root'][i]),
                                   near_hypothetical_comparisons=int(planner.near[mode][i]))
            row['retention']['retained' if retain else 'erased'] = dict(
                modes=modes, clock_benefit=float(clock[i]), information_value=float(information[i]),
                total_future_benefit=float(clock[i]+information[i]))
    return rows, before


def verify_rows(rows, cases):
    check('complete_contexts', len(rows) == len(cases) and [r['id'] for r in rows] == [c['id'] for c in cases])
    for row, case in zip(rows, cases):
        h, d = case['horizon'], case['clock']
        check('row_identity', (row['t'], row['horizon'], row['clock']) == (case['t'], h, d))
        check('feasible_prefix', all((target is not None) == (j % 2 == 0)
                                    for j, (_, target) in enumerate(case['history'], 1)))
        check('prefix_clock', d == (case['t']-1) % 2)
        close('saved_risk', row['risk'], min(row['u'], 1-row['u']))
        for retained, result in row['retention'].items():
            modes = result['modes']
            check('complete_modes', set(modes) == set(M.MODES))
            for name, v in modes.items():
                check('finite_values', all(np.isfinite(v[k]) for k in ('cost', 'purchases', 'answer_score', 'purchase_score')))
                close('executed_score', v['cost'], v['purchase_score'] if v['buy'] else v['answer_score'])
                check('cost_nonnegative', v['cost'] >= -M.TOL)
                check('count_bounds', -M.TOL <= v['purchases'] <= h+M.TOL)
                error = v['cost']-.1*v['purchases']
                check('error_cost_bounds', -M.TOL <= error <= .5*(h-v['purchases'])+M.TOL)
                check('action_identity', v['action'] == (2 if v['buy'] else (case['y'] >> 1) ^ (row['u'] > .5)))
                if name != 'free':
                    check('forced_current_purchase', d == 0 or v['buy'])
                    check('minimum_checking_cost', v['purchases'] >= (h+d)//2-M.TOL)
                if name == 'free' or d == 0:
                    decision = modes['free'] if name == 'hybrid' else v
                    check('specified_choice', v['buy'] == (decision['purchase_score'] <= decision['answer_score']))
                    expected_near = abs(decision['purchase_score']-decision['answer_score']) <= M.NEAR
                    check('near_root_label', v['near_root'] == expected_near)
                check('near_count_valid', v['near_hypothetical_comparisons'] >= int(v['near_root']))
            free, hybrid, clock = (modes[k] for k in ('free', 'hybrid', 'clock'))
            check('free_lower_bound', free['cost'] <= clock['cost']+M.TOL)
            check('coherent_dominates_hybrid', clock['cost'] <= hybrid['cost']+M.TOL)
            check('always_buying_upper_bound', clock['cost'] <= .1*h+M.TOL)
            check('benefit_signs', result['clock_benefit'] >= -M.TOL and result['information_value'] >= -M.TOL)
            close('saved_benefit_sum', result['clock_benefit']+result['information_value'], result['total_future_benefit'])
            close('saved_score_decomposition', clock['answer_score']-clock['purchase_score'],
                  row['risk']-.1+result['total_future_benefit'])
            if retained == 'erased':
                close('saved_lesion_zero_information', result['information_value'], 0, 0)
            if h == 1:
                close('terminal_future_benefit', result['total_future_benefit'], 0, 0)
                close('terminal_coherent_equals_hybrid', clock['cost'], hybrid['cost'])
                close('terminal_forced_cost', clock['cost'], .1)
                close('terminal_forced_count', clock['purchases'], 1)


def summarize(rows):
    out = {}
    for retain in ('retained', 'erased'):
        values = [r['retention'][retain] for r in rows]
        differences = [v['modes']['clock']['cost']-v['modes']['hybrid']['cost'] for v in values]
        counts = [v['modes']['clock']['purchases']-v['modes']['hybrid']['purchases'] for v in values]
        out[retain] = dict(
            contexts=len(rows), strict_cost_improvements=sum(v < -M.TOL for v in differences),
            cost_equal_within_tolerance=sum(abs(v) <= M.TOL for v in differences),
            cost_worse=sum(v > M.TOL for v in differences), cost_difference_range=[min(differences), max(differences)],
            fewer_purchases=sum(v < -M.TOL for v in counts), equal_purchases=sum(abs(v) <= M.TOL for v in counts),
            more_purchases=sum(v > M.TOL for v in counts), purchase_difference_range=[min(counts), max(counts)],
            current_action_changes=sum(v['modes']['clock']['action'] != v['modes']['hybrid']['action'] for v in values),
            contexts_with_near_comparisons=sum(any(m['near_hypothetical_comparisons'] for m in v['modes'].values()) for v in values),
            clock_benefit_range=[min(v['clock_benefit'] for v in values), max(v['clock_benefit'] for v in values)],
            information_value_range=[min(v['information_value'] for v in values), max(v['information_value'] for v in values)])
    return out


def worker(job):
    cases, output, name = job
    resources()
    CHECKS.clear()
    tick, cpu = perf_counter(), process_time()
    rows, state = evaluate(cases)
    verify_rows(rows, cases)
    record = dict(name=name, ids=[c['id'] for c in cases], row_count=len(rows), result_fingerprint=fingerprint(rows),
                  state_fingerprint=state, wall_seconds=perf_counter()-tick, cpu_seconds=process_time()-cpu,
                  cpus=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                  threads=len(list(Path('/proc/self/task').iterdir())), checks=dict(CHECKS))
    check('worker_one_thread', record['threads'] == 1)
    if output:
        path = Path(output)/'batches'/(name+'.json')
        write(path, dict(rows=rows, state_fingerprint=state))
        record.update(file='batches/'+name+'.json', sha256=digest(path))
    return record


def synthetic(index, t=97):
    hist = []
    for j in range(1, t):
        y = (j+index) % 4
        hist.append((y, y >> 1 if j % 2 == 0 else None))
    return [dict(id=f'benchmark-{index}-{i}', counts=[41, 7, 11, 5], history=hist,
                 y=i % 4, t=t, horizon=101-t, clock=(t-1) % 2, template='benchmark') for i in range(12)]


def qualify():
    tick = perf_counter()
    CHECKS.clear()
    fixtures = [((20, 4, 8, 32), [(0, None), (3, 0), (1, None)], 0),
                ((58, 3, 3, 0), [(0, 0), (3, None)], 1)]
    exact_records = []
    for counts, hist, y in fixtures:
        case = dict(counts=counts, history=hist, y=y, t=len(hist)+1)
        f = M.load([case], (1, 2, 4))
        ref = M.Reference(counts, (1, 2, 4))
        before = state_fingerprint(f)
        for h in (1, 2, 3, 4):
            for d in (0, 1):
                for retain in (True, False):
                    planner = M.Vector(f)
                    got, clock, information = planner.inspect(h, d, retain)
                    exact, ec, ei = ref.inspect(hist, y, h, d, retain)
                    for mode in M.MODES:
                        for key in ('value', 'purchases', 'answer', 'purchase'):
                            close('independent_rational_'+key, got[mode][key][0], float(exact[mode][key]), 3e-12)
                        if not planner.near[mode][0]:
                            check('independent_rational_choice', bool(got[mode]['buy'][0]) == exact[mode]['buy'])
                    close('rational_clock_benefit', clock[0], float(ec), 3e-12)
                    close('rational_information_value', information[0], float(ei), 3e-12)
                    check('rational_clock_nonnegative', ec >= 0)
                    check('rational_information_nonnegative', ei >= 0)
                    check('exact_cost_order', exact['free']['value'] <= exact['clock']['value'] <= exact['hybrid']['value'])
                    if not retain:
                        check('rational_erasure_zero_information', ei == 0)
                    exact_records.append(dict(counts=counts, history=hist, y=y, horizon=h, clock=d, retained=retain,
                                              costs={m:str(v['value']) for m,v in exact.items()},
                                              counts_expected={m:str(v['purchases']) for m,v in exact.items()},
                                              clock_benefit=str(ec), information_value=str(ei)))
        check('qualification_state_purity', state_fingerprint(f) == before)
    counts, hist, y = (20, 4, 8, 32), [(0, None), (3, 1)], 1
    f = M.load([dict(counts=counts, history=hist, y=y, t=3)])
    ref = M.Reference(counts)
    for retain in (True, False):
        got, clock, information = M.Vector(f).inspect(2, 0, retain)
        exact, ec, ei = ref.inspect(hist, y, 2, 0, retain)
        for mode in M.MODES:
            for key in ('value', 'purchases', 'answer', 'purchase'):
                close('full_support_rational_'+key, got[mode][key][0], float(exact[mode][key]), 3e-12)
        close('full_support_clock', clock[0], float(ec), 3e-12)
        close('full_support_information', information[0], float(ei), 3e-12)
    flipped = [(yy ^ 3, None if target is None else target ^ 1) for yy, target in hist]
    twin = M.load([dict(counts=counts, history=hist, y=y, t=3),
                   dict(counts=counts, history=flipped, y=y ^ 3, t=3)])
    for retain in (True, False):
        result, clock, information = M.Vector(twin).inspect(3, 0, retain)
        for mode in M.MODES:
            for key in ('value', 'purchases', 'answer', 'purchase'):
                close('flip_symmetry_'+key, result[mode][key][0], result[mode][key][1], 0)
        close('flip_clock', clock[0], clock[1], 0)
        close('flip_information', information[0], information[1], 0)
    known = M.known_law()
    for row in known:
        free, hybrid, coherent = (M.F(row[k]) for k in ('free', 'hybrid', 'clock'))
        check('known_law_order', free <= coherent <= hybrid)
        check('known_law_zero_learning', M.F(row['information']) == 0)
        check('known_law_equal_counts', row['hybrid_purchases'] == row['clock_purchases'] == '1')
        if row['law'] == 'varying' and row['warning'] in (1, 2):
            check('known_law_exact_example', (free, hybrid, coherent, M.F(row['clock_benefit'])) ==
                  (M.F(49, 500), M.F(9, 50), M.F(59, 500), M.F(41, 500)))
        if row['law'] == 'constant':
            check('constant_control', (free, hybrid, coherent) == (M.F(1, 50), M.F(11, 100), M.F(11, 100)))
    jobs = [(synthetic(i, 99), None, 'parallel-'+str(i)) for i in range(4)]
    accumulated = dict(CHECKS)
    serial = [worker(j) for j in jobs]
    CHECKS.clear(); CHECKS.update(accumulated)
    with ProcessPoolExecutor(max_workers=4) as pool:
        parallel = list(pool.map(worker, jobs))
    for a, b in zip(serial, parallel):
        check('serial_four_worker_identity', a['result_fingerprint'] == b['result_fingerprint'] and a['state_fingerprint'] == b['state_fingerprint'])
    return dict(passed=True, seconds=perf_counter()-tick, checks=dict(CHECKS), exact_records=exact_records,
                known_law_controls=known, parallel_records=parallel)


def storage(output):
    mounted = json.loads(subprocess.check_output(
        ['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    check('external_mount', mounted == dict(target='/mnt/bioIce1', source='/dev/sdc1', fstype='ext4'))
    check('namespace', output.resolve().parent == ROOT and output.name.startswith('attempt-'))
    stat = os.statvfs('/mnt/bioIce1')
    check('space', stat.f_bavail*stat.f_frsize > 2_000_000_000)
    return mounted


def log(output, message):
    line = utc()+' '+message
    with (output/'RUN_LOG.txt').open('a') as f:
        f.write(line+'\n'); f.flush(); os.fsync(f.fileno())
    print(line, flush=True)


def check_inputs(output):
    frozen = json.loads((output/'FREEZE.json').read_text())
    for p, h in frozen['inputs'].items():
        check('frozen_input', digest(p) == h)
    for name, h in frozen['snapshots'].items():
        check('snapshot', digest(output/'inputs'/name) == h)
    return frozen


def prepare(output):
    mounted = storage(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir(); (output/'batches').mkdir()
    log(output, 'PREPARE: analytic clock-aware design; 144 constructed contexts; no sampled cohort')
    previous = json.loads((PREVIOUS/'FREEZE.json').read_text())
    identities = dict(previous['inputs'])
    for p, h in identities.items():
        check('previous_input', digest(p) == h)
    expected = {
        SOURCE/'fep_structured_reversal.py': '9ae8f36d2730d6885a5558cc0069fe6f2b614e279985831105233ec437a63f3b',
        SOURCE/'FEP_PAID_CHECKING_V1_REPORT.md': 'ef9f1f9718b1736c36b1e0692ec665b0e951cf101700246d6cd60dbd7c1989f7',
        OLD.ROOT/'reporting-2026-10-18/REPORT_PROVENANCE.json': 'bd30372619bd45358dda9efbe8aed45f0b38f71f34270578a99c9b0b43b96df9',
        PREVIOUS/'MANIFEST.json': '7c467271e5f4af6a005f1955c7bbb036f1da6462fb5b71a425da728b3e4b8716',
        PREVIOUS/'READBACK.json': 'ba9ccc2119ee8762beec48f0e36a03a5579dd33e5035bc339d601e692a8a598c',
    }
    for p, h in expected.items():
        check('previous_evidence', digest(p) == h)
        identities[str(p)] = h
    cases = M.contexts()
    check('fixed_context_count', len(cases) == 144 and len({c['id'] for c in cases}) == 144)
    write(output/'CONTEXTS.json', cases)
    identities[str(output/'CONTEXTS.json')] = digest(output/'CONTEXTS.json')
    snapshots = {}
    for path in (SPEC, SOURCE/'fep_planned_checking.py', Path(__file__).resolve()):
        identities[str(path)] = digest(path)
        shutil.copyfile(path, output/'inputs'/path.name)
        snapshots[path.name] = digest(path)
    write(output/'FREEZE.json', dict(created=utc(), inputs=identities, snapshots=snapshots, mount=mounted,
                                     main_contexts=144, numerical_tolerance=M.TOL, near_tolerance=M.NEAR,
                                     cpus=sorted(os.sched_getaffinity(0)), no_main_outcomes_generated=True))
    log(output, 'FROZEN: sources, definitions, costs, terminal windows, both retention modes and conventions')
    q = qualify()
    write(output/'QUALIFICATION.json', q)
    log(output, f'QUALIFIED: {q["seconds"]:.2f}s; independent exact costs/counts, decomposition and controls')
    jobs = [(synthetic(i), None, 'benchmark-'+str(i)) for i in range(4)]
    tick = perf_counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(worker, jobs))
    elapsed = perf_counter()-tick
    forecast = 120+9*elapsed
    write(output/'BENCHMARK.json', dict(seconds=elapsed, forecast_seconds=forecast, records=records,
                                       rule='120 + 9 * benchmark_seconds', within_bound=forecast <= 7200,
                                       requires_detached=forecast > 600))
    check_inputs(output)
    log(output, f'PREPARED: forecast {forecast:.2f}s; feasibility passes={forecast <= 7200}')


def readback(output):
    tick = perf_counter()
    check_inputs(output)
    manifest = json.loads((output/'MANIFEST.json').read_text())
    check('completed', manifest['status'] == 'COMPLETE')
    for name, h in manifest['outputs'].items():
        check('output_hash', digest(output/name) == h)
    started = json.loads((output/'STARTED.json').read_text())
    for key, name in (('freeze_sha256', 'FREEZE.json'),
                      ('qualification_sha256', 'QUALIFICATION.json'),
                      ('benchmark_sha256', 'BENCHMARK.json')):
        check('launch_input_identity', started[key] == digest(output/name))
    qualification = json.loads((output/'QUALIFICATION.json').read_text())
    benchmark = json.loads((output/'BENCHMARK.json').read_text())
    check('qualified_launch', qualification['passed'] and benchmark['within_bound'])
    check('launch_detachment', started['detached'] or not benchmark['requires_detached'])
    check('coordinator_resources', len(started['cpus']) <= 4 and started['nice'] >= 10)
    cases = json.loads((output/'CONTEXTS.json').read_text())
    check('all_definitions', cases == json.loads(json.dumps(M.contexts())))
    records = json.loads((output/'WORKERS.json').read_text())
    check('twelve_batches', len(records) == 12)
    index = {}
    for record in records:
        saved = json.loads((output/record['file']).read_text())
        check('batch_identity', digest(output/record['file']) == record['sha256'] and
              fingerprint(saved['rows']) == record['result_fingerprint'])
        check('batch_state_identity', saved['state_fingerprint'] == record['state_fingerprint'])
        check('worker_resources', len(record['cpus']) <= 4 and record['threads'] == 1 and record['nice'] >= 10)
        for row in saved['rows']:
            check('unique_context_result', row['id'] not in index)
            index[row['id']] = row
    rows = [index[c['id']] for c in cases]
    verify_rows(rows, cases)
    saved = json.loads((output/'RESULTS.json').read_text())
    check('all_saved_rows', saved['rows'] == rows)
    check('no_physical_cohort_claim', saved['sampled_episodes'] == 0 and saved['physical_success_claim'] is False)
    check('known_law_results', saved['known_law_controls'] == M.known_law())
    for retained in ('retained', 'erased'):
        s = saved['summary'][retained]
        vals = [r['retention'][retained] for r in rows]
        dc = [v['modes']['clock']['cost']-v['modes']['hybrid']['cost'] for v in vals]
        dn = [v['modes']['clock']['purchases']-v['modes']['hybrid']['purchases'] for v in vals]
        expected = dict(contexts=144, strict_cost_improvements=len([x for x in dc if x < -M.TOL]),
                        cost_equal_within_tolerance=len([x for x in dc if abs(x) <= M.TOL]),
                        cost_worse=len([x for x in dc if x > M.TOL]), cost_difference_range=[min(dc), max(dc)],
                        fewer_purchases=len([x for x in dn if x < -M.TOL]),
                        equal_purchases=len([x for x in dn if abs(x) <= M.TOL]),
                        more_purchases=len([x for x in dn if x > M.TOL]), purchase_difference_range=[min(dn), max(dn)],
                        current_action_changes=len([v for v in vals if v['modes']['clock']['action'] != v['modes']['hybrid']['action']]),
                        contexts_with_near_comparisons=len([v for v in vals if any(m['near_hypothetical_comparisons'] for m in v['modes'].values())]),
                        clock_benefit_range=[min(v['clock_benefit'] for v in vals), max(v['clock_benefit'] for v in vals)],
                        information_value_range=[min(v['information_value'] for v in vals), max(v['information_value'] for v in vals)])
        check('independent_summary', s == expected)
    write(output/'READBACK.json', dict(passed=True, completed=utc(), seconds=perf_counter()-tick, checks=dict(CHECKS),
                                       total_checks=sum(CHECKS.values()), manifest_sha256=digest(output/'MANIFEST.json'),
                                       source_sha256=digest(Path(__file__).resolve()), policy_evaluations_rerun=0))
    print('Independent saved-result readback passed.', flush=True)


def run(output, detached):
    check_inputs(output); storage(output)
    q = json.loads((output/'QUALIFICATION.json').read_text())
    b = json.loads((output/'BENCHMARK.json').read_text())
    check('qualified_and_feasible', q['passed'] and b['within_bound'])
    check('detachment_rule', detached or not b['requires_detached'])
    check('not_started', not (output/'STARTED.json').exists())
    tick = perf_counter()
    write(output/'STARTED.json', dict(started=utc(), pid=os.getpid(), detached=detached, workers=4,
                                      cpus=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                                      freeze_sha256=digest(output/'FREEZE.json'),
                                      qualification_sha256=digest(output/'QUALIFICATION.json'),
                                      benchmark_sha256=digest(output/'BENCHMARK.json')))
    cases = json.loads((output/'CONTEXTS.json').read_text())
    jobs = [(list(c for c in cases if c['t'] == t and c['template'] == template), str(output), f'{template}-t{t}')
            for t in (97, 98, 99, 100) for template in M.TEMPLATES]
    log(output, 'MAIN STARTED: 12 fixed batches; 144 constructed contexts; both retention modes')
    with ProcessPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(worker, jobs))
    write(output/'WORKERS.json', records)
    index = {}
    for record in records:
        for row in json.loads((output/record['file']).read_text())['rows']:
            index[row['id']] = row
    rows = [index[c['id']] for c in cases]
    verify_rows(rows, cases)
    write(output/'RESULTS.json', dict(rows=rows, summary=summarize(rows), known_law_controls=M.known_law(),
                                      sampled_episodes=0, physical_success_claim=False))
    check_inputs(output)
    log(output, 'MAIN COMPLETE: all finite contexts saved; independent readback follows')
    outputs = {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write(output/'MANIFEST.json', dict(status='COMPLETE', finished=utc(), seconds=perf_counter()-tick,
                                       checks=dict(CHECKS), outputs=outputs))
    with (output/'READBACK_STDOUT.log').open('xb') as f:
        subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), 'readback', '--output', str(output)],
                       stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, check=True, cwd=SOURCE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run', 'readback'))
    parser.add_argument('--output', type=Path, default=ROOT/'attempt-01')
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    resources()
    if args.mode == 'prepare' and args.output.exists():
        raise FileExistsError('Preserve the existing attempt.')
    try:
        if args.mode == 'prepare':
            prepare(args.output)
        elif args.mode == 'run':
            run(args.output, args.detached)
        else:
            readback(args.output)
    except BaseException:
        if args.output.exists():
            path = args.output/('FAILURE-'+args.mode+'.json')
            if not path.exists():
                write(path, dict(utc=utc(), traceback=traceback.format_exc(), checks=dict(CHECKS)))
        raise


if __name__ == '__main__':
    main()
