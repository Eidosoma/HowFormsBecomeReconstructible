#!/usr/bin/env python3
"""Revision two: correct the archived headroom field; unchanged evaluation."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
import importlib.util
from itertools import product
import json
from math import prod
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from time import perf_counter, process_time
import traceback

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-generalization-v1'
FAILED = ROOT/'attempt-01'
FIRST_CHECKER_SHA = '0bb15729648438af336b897d355e0ef03aef47e72e505a17db391c475fde8123'
FAILURE_SHA = '0bf5826ec51b2ceef2d01a4ef7d727c01a500a60c2bfd46b5df68bb3bc85b43e'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-task-regret-v1/attempt-01'
LEDGER = MOUNT/'fep-ideas/formal-checks/fep-reference-feedback-v1/attempt-01/POSTERIOR_TABLES.jsonl.gz'
PREVIOUS_SHA = 'bed6cf623ad0003e3dda91ed53e1e716d848a9b41c44ad84b32857ab7abb14a5'
REPORT_SHA = 'aa56d084a13cfc006ec1dd5bc9eb70ee8848b41346bc32f171ee379f8fdb41d5'
LEDGER_SHA = '1b558ab92ca4fc2b8e12b3c3d14b575e9b880fd09c9954e15272af6679de7671'
HELPER_SHA = '18f0f15f1f89bfd2c98f8aa8601f52264ef4eeb17f9c19e01733aa90aedb96bd'
CAP, BASE, ROWS, STOPPED = 64,800,136499,259142
NAMES = ('edit','average')
METRICS = ('wrong_loss','reference_expense','excess_checking','unsafe_reporting','wrong_direction')
WARNINGS = ('agreement','disagreement')
DEPENDENCE = ('neg1','neg05','zero','pos05','pos1')

assert sha256((SOURCE/'check_fep_stopping_attribution.py').read_bytes()).hexdigest() == HELPER_SHA
spec = importlib.util.spec_from_file_location('frozen_bookkeeping',SOURCE/'check_fep_stopping_attribution.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
check, write, identity = C.check,C.write,C.identity
SYMMETRIC = tuple(code for code,d in enumerate(C.ACTS) if all(d[3-y] == (1,0,2)[d[y]] for y in (0,1)))


def population():
    panel = {}
    for i,j in product((1,3,5,7,9),repeat=2):
        both = (0,i*j,2*i*j,i*j+20*min(i,j),40*min(i,j))
        for d,name in enumerate(DEPENDENCE):
            q11 = both[d]
            q = (BASE-40*i-40*j+q11,40*j-q11,40*i-q11,q11)
            panel[f'a{5*i:02d}_b{5*j:02d}_{name}'] = dict(q=q,a=F(i,20),b=F(j,20),
                dependence=name,t=F(d-2,2),role='new_panel',weight=F(1,125))
    old = {'a05_rho0':(342,38,18,2),'a05_rho5':(351,29,9,11),'a05_rho1':(360,20,0,20),
        'a15_rho0':(238,102,42,18),'a15_rho5':(259,81,21,39),'a15_rho1':(280,60,0,60),
        'a25_rho0':(150,150,50,50),'a25_rho5':(175,125,25,75),'a25_rho1':(200,100,0,100),
        'old_shared_diagnostic':(320,40,0,40)}
    controls = {name:dict(q=tuple(2*x for x in q),role='known_control',weight=F(0)) for name,q in old.items()}
    check('population','125 distinct new laws',len(panel) == len({v['q'] for v in panel.values()}) == 125)
    check('population','new laws distinct from controls',not({v['q'] for v in panel.values()} & {v['q'] for v in controls.values()}))
    for x in panel.values():
        q = x['q']
        check('population','valid marginals and law',min(q) >= 0 and sum(q) == BASE and
            F(q[2]+q[3],BASE) == x['a'] and F(q[1]+q[3],BASE) == x['b'])
        lo,hi = max(F(0),x['a']+x['b']-1),min(x['a'],x['b'])
        ab,t = x['a']*x['b'],x['t']
        expected = (1+t)*ab-t*lo if t <= 0 else (1-t)*ab+t*hi
        check('population','declared interpolation',F(q[3],BASE) == expected)
    return panel,controls


def verify(entries):
    for x in entries:
        actual = identity(Path(x['path']))
        check('integrity','unchanged '+x['path'],actual == x)


def read_rows():
    rows,seen,stopped = [],set(),0
    with gzip.open(LEDGER,'rt') as stream:
        for line in stream:
            raw = json.loads(line)
            n,c,k,codes = raw[0],tuple(raw[1:5]),tuple(map(int,raw[5])),tuple(raw[6])
            check('ledger','unique valid stopped history',c not in seen and len(c) == 4 and
                min(c) >= 0 and sum(c) == n and 0 <= n <= CAP)
            check('ledger','valid multiplicities and saved tables',len(k) == len(codes) == 2 and
                min(k) >= 0 and any(k) and all(code in SYMMETRIC for code in codes))
            seen.add(c); stopped += sum(x > 0 for x in k)
            rows.append((n,c,k,codes))
    check('ledger','all original rows and controllers',len(rows) == ROWS and stopped == STOPPED)
    return rows


def score(code,q):
    out = []
    for g in (0,1):
        a = C.ACTS[code][g]
        mass,better = q[g]+q[3-g],10*min(q[g],q[3-g])
        floor = min(mass,better)
        risk = 10*q[3-g if a == 0 else g]
        row = (0,mass,mass-floor,0,0) if a == 2 else (risk,0,0,better-floor,risk-better)
        check('regret','nonnegative action decomposition',min(row) >= 0 and row[0]+row[1] == floor+sum(row[2:]))
        out.append(row)
    return tuple(out)


def oracle(q):
    by_warning,optimal = {},{}
    for g,name in enumerate(WARNINGS):
        losses = (10*q[3-g],10*q[g],q[g]+q[3-g])
        by_warning[name] = F(min(losses),10*BASE)
        optimal[name] = [a for a,v in enumerate(losses) if v == min(losses)]
    actions = []
    for y in range(4):
        loss = (10*q[3-y],10*q[y],q[y]+q[3-y])
        actions.append(2 if loss[2] == min(loss) else min(range(2),key=lambda a:loss[a]))
    return dict(task_floor=sum(by_warning.values()),by_warning=by_warning,
                canonical_optimal_actions=optimal,representative_actions=actions)


def integrate(rows,q,cap=CAP):
    powers = [[x**n for n in range(cap+1)] for x in q]
    tails = [BASE**n for n in range(cap+1)]
    stats = [dict(codes=[0]*81,counts=[0]*(cap+1)) for _ in NAMES]
    for n,c,k,codes in rows:
        w = prod(powers[e][c[e]] for e in range(4))*tails[cap-n]
        if not w:
            continue
        for s in (0,1):
            if k[s]:
                mass = k[s]*w
                stats[s]['codes'][codes[s]] += mass
                stats[s]['counts'][n] += mass
    return stats


def finish(stats,q,cap=CAP):
    den = BASE**cap; o = oracle(q)
    scores = {code:score(code,q) for code in SYMMETRIC}
    results = {}
    for name,stat in zip(NAMES,stats):
        check('mass','normalized code and count stopped laws',sum(stat['codes']) == sum(stat['counts']) == den)
        n = F(sum(i*m for i,m in enumerate(stat['counts'])),den)
        by_warning = {}
        for g,w in enumerate(WARNINGS):
            metrics = {key:F(sum(stat['codes'][code]*scores[code][g][j] for code in SYMMETRIC),10*BASE*den)
                       for j,key in enumerate(METRICS)}
            metrics['raw_loss'] = metrics['wrong_loss']+metrics['reference_expense']
            metrics['task_floor'] = o['by_warning'][w]
            metrics['decision_regret'] = sum(metrics[k] for k in METRICS[2:])
            check('regret','warning partition',metrics['raw_loss'] == metrics['task_floor']+metrics['decision_regret'])
            by_warning[w] = metrics
        totals = {key:sum(v[key] for v in by_warning.values()) for key in by_warning['agreement']}
        calibration = n/100000; net = totals['raw_loss']+calibration
        components = dict(calibration=calibration,**{k:totals[k] for k in METRICS[2:]})
        check('regret','full known-Q cost identity',net-o['task_floor'] == sum(components.values()) and min(components.values()) >= 0)
        row = dict(expected_calibrations=n,calibration_expense=calibration,net_loss=net,
            raw_task_loss=totals['raw_loss'],wrong_loss=totals['wrong_loss'],reference_expense=totals['reference_expense'],
            episode_expected_wrong_reports=100*totals['wrong_loss'],episode_expected_references=1000*totals['reference_expense'],
            task_floor=o['task_floor'],task_headroom=F(1,10)-o['task_floor'],gap_to_known_Q=net-o['task_floor'],
            net_advantage_over_always_reference=F(1,10)-net,components=components,by_warning=by_warning,
            early_probability=F(sum(stat['counts'][:-1]),den),cap_probability=F(stat['counts'][-1],den),
            stop_distribution=[F(m,den) for m in stat['counts']],
            response_table_probabilities={str(code):F(stat['codes'][code],den) for code in SYMMETRIC})
        check('mass','mean calibration from stop distribution',n == sum(i*p for i,p in enumerate(row['stop_distribution'])))
        results[name] = row
    return results


def average(rows):
    if isinstance(rows[0],dict):
        return {k:average([x[k] for x in rows]) for k in rows[0]}
    if isinstance(rows[0],list):
        return [average([x[i] for x in rows]) for i in range(len(rows[0]))]
    return sum(rows,F(0))/len(rows)


def ratios(row):
    h,gap = row['task_headroom'],row['gap_to_known_Q']
    row['captured_headroom_fraction'] = row['net_advantage_over_always_reference']/h if h else None
    row['gap_component_fractions'] = {k:v/gap if gap else None for k,v in row['components'].items()}
    check('bound','headroom fraction bounded above',h >= 0 and (not h or row['captured_headroom_fraction'] <= 1))


def population_summary(actual,labels,with_gates=True):
    summary = {}
    for name in NAMES:
        rows = [actual[label][name] for label in labels]
        mean = average(rows); ratios(mean)
        eligible = [label for label in labels if actual[label][name]['task_headroom'] > 0]
        failures = [label for label in eligible if actual[label][name]['net_loss'] >= F(1,10)]
        worst = max(row['net_loss'] for row in rows)
        summary[name] = dict(equal_mean=mean,environments=len(labels),
            positive_headroom_environments=len(eligible),zero_headroom_environments=len(labels)-len(eligible),
            coverage_beneficial=len(eligible)-len(failures),coverage_failures=failures,
            below_always_reference=sum(row['net_loss'] < F(1,10) for row in rows),
            tied_always_reference=sum(row['net_loss'] == F(1,10) for row in rows),
            above_always_reference=sum(row['net_loss'] > F(1,10) for row in rows),
            worst_net_loss=worst,worst_excess_over_always_reference=worst-F(1,10),
            worst_cases=[label for label in labels if actual[label][name]['net_loss'] == worst])
        if with_gates:
            summary[name]['gates'] = dict(population_benefit=mean['net_loss'] < F(1,10),functional_coverage=not failures)
        check('aggregate','complete coverage accounting',len(eligible)-len(failures) == summary[name]['below_always_reference'])
    return summary


def direct_score(code,q):
    weights = [[F(0),F(0)] for _ in range(4)]
    out = [[F(0)]*5 for _ in WARNINGS]
    for w,e in product((0,1),range(4)):
        y = e if w == 0 else 3-e
        weights[y][w] += F(q[e],2*BASE)
        a = C.ACTS[code][y]; g = min(y,3-y)
        out[g][0] += F(q[e],2*BASE)*int(a != 2 and a != w)
        out[g][1] += F(q[e],20*BASE)*int(a == 2)
    for y,(p0,p1) in enumerate(weights):
        p = p0+p1
        if not p:
            continue
        risks = (p1/p,p0/p); m = min(risks); b = min(m,F(1,10))
        a = C.ACTS[code][y]; g = min(y,3-y)
        if a == 2:
            out[g][2] += p*(F(1,10)-b)
        else:
            out[g][3] += p*(m-b)
            out[g][4] += p*(risks[a]-m)
    return tuple(tuple(v*10*BASE for v in row) for row in out)


def toy_continue(s,c):
    n = sum(c)
    return n == 0 or (n == 1 and c[s] == 0) or (n == 2 and c[3-s] == 0)


def toy_code(s,c):
    return SYMMETRIC[(s+sum((e+1)*x for e,x in enumerate(c))) % len(SYMMETRIC)]


def toy_rows():
    stops = {}
    for s in (0,1):
        current = {(0,0,0,0):1}
        for n in range(4):
            future = {}
            for c,k in current.items():
                if toy_continue(s,c):
                    for e in range(4):
                        child = tuple(x+int(i == e) for i,x in enumerate(c))
                        future[child] = future.get(child,0)+k
                else:
                    stops.setdefault(c,[0,0])[s] = k
            current = future
    return [(sum(c),c,tuple(k),tuple(toy_code(s,c) for s in (0,1))) for c,k in stops.items()]


def qualify(rows,pop):
    begin = perf_counter()
    controls = [(800,0,0,0),(0,0,0,800),(200,200,200,200),
                (720,0,0,80),(80,0,0,720),(719,0,0,81),(721,0,0,79)]
    laws = [x['q'] for x in pop.values()]+controls
    toy = toy_rows()
    for q in laws:
        direct = {}
        for code in SYMMETRIC:
            direct[code] = direct_score(code,q)
            check('qualification','independent target/error decomposition',score(code,q) == direct[code])
        o = oracle(q); code = sum(a*3**y for y,a in enumerate(o['representative_actions']))
        check('qualification','exhaustive informed optimum',o['task_floor'] == min(F(sum(x[0]+x[1] for x in v),10*BASE) for v in direct.values()))
        check('qualification','informed choice has zero regret',all(sum(v[2:]) == 0 for v in direct[code]))
        slow = [dict(codes=[0]*81,counts=[0]*4) for _ in NAMES]
        for errors in product(range(4),repeat=3):
            weight = prod(q[e] for e in errors)
            for s in (0,1):
                c = [0]*4; used = 0
                while toy_continue(s,c):
                    c[errors[used]] += 1; used += 1
                slow[s]['codes'][toy_code(s,c)] += weight
                slow[s]['counts'][used] += weight
        fast = integrate(toy,q,3)
        check('qualification','ordered histories recover first-stop laws',fast == slow)
        result = finish(fast,q,3)
        for s,name in enumerate(NAMES):
            for j,key in enumerate(METRICS):
                actual = sum(slow[s]['codes'][code]*sum(g[j] for g in direct[code]) for code in SYMMETRIC)/F(10*BASE**4)
                displayed = result[name].get(key,result[name]['components'].get(key))
                check('qualification','ordered-history physical costs '+key,actual == displayed)
    check('qualification','reference tie retains both optimal actions',oracle((720,0,0,80))['canonical_optimal_actions']['agreement'] == [0,2])
    known = {label:finish(integrate(rows,v['q']),v['q']) for label,v in pop.items() if v['role'] == 'known_control'}
    bridge(known,json.loads((PREVIOUS/'RESULTS.json').read_text()))
    duration = perf_counter()-begin
    begin = perf_counter()
    for v in pop.values():
        integrate(rows[:2048],v['q'])
    benchmark = perf_counter()-begin; forecast = 90+4*benchmark*ROWS/2048
    return dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),qualification_seconds=duration,
        laws=len(laws),symmetric_tables=len(SYMMETRIC),toy_cap=3,toy_schedules=2,complete_known_control_bridges=10,
        benchmark_rows=2048,benchmark_laws=len(pop),benchmark_seconds=benchmark,
        forecast_main_seconds=forecast,forecast_rule='90 seconds plus four times extrapolated full-population row benchmark',
        requires_detached=forecast > 600)


def prepare(output,logline):
    check('integrity','preserved failed checker',identity(SOURCE/'check_fep_generalization.py')['sha256'] == FIRST_CHECKER_SHA)
    check('integrity','preserved first failure',identity(FAILED/'FAILURE.json')['sha256'] == FAILURE_SHA)
    check('integrity','previous manifest pinned',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report pinned',identity(SOURCE/'FEP_TASK_REGRET_V1_REPORT.md')['sha256'] == REPORT_SHA)
    check('integrity','saved original policies pinned',identity(LEDGER)['sha256'] == LEDGER_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({x['path']:x for group in ('inputs','outputs','preserved') for x in old[group]}.values())
    preserved += [identity(p) for p in sorted(FAILED.rglob('*')) if p.is_file()]
    verify(preserved); (output/'inputs').mkdir()
    files = [(SOURCE/name,name) for name in ('FEP_GENERALIZATION_V1.md','check_fep_generalization.py',
        'check_fep_generalization_r2.py','FEP_GENERALIZATION_V1_CORRECTION.md',
        'FEP_TASK_REGRET_V1_REPORT.md','check_fep_stopping_attribution.py')]
    files += [(PREVIOUS/'MANIFEST.json','task_regret_MANIFEST.json'),(PREVIOUS/'RESULTS.json','task_regret_RESULTS.json')]
    inputs = []
    for p,name in files:
        inputs.append(identity(p)); shutil.copyfile(p,output/'inputs'/name)
        check('integrity','source snapshot '+name,identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    inputs.append(identity(LEDGER))
    panel,controls = population(); pop = dict(panel,**controls)
    write(output/'POPULATION.json',dict(denominator=BASE,panel=panel,controls=controls,
        response_tables={str(code):C.ACTS[code] for code in SYMMETRIC}))
    inputs.append(identity(output/'POPULATION.json'))
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,new_environments=125,
        known_controls=10,primary='edit',policy_changes=0,prior_or_price_tuning=0,policy_optimizations=0,
        new_feedback=0,prior_wide_oracle_evaluation=False,large_ledger_read_in_place=True,
        source_revision=2,prior_failed_attempts=1,correction='Archived task_headroom is controller-level; no policy/population/cost change.'))
    rows = read_rows(); q = qualify(rows,pop); write(output/'QUALIFICATION.json',q)
    logline(f'PREPARED: {q["checks"]} checks; qualification {q["qualification_seconds"]:.3f}s; forecast {q["forecast_main_seconds"]:.3f}s; detached={q["requires_detached"]}')


def bridge(actual,old):
    for label,methods in actual.items():
        for name,row in methods.items():
            prior = old['truths'][label][name]; arm = prior['arms']['no_update']
            check('bridge','same expected calibrations',row['expected_calibrations'] == F(prior['expected_calibrations']['exact']))
            for key in ('net_loss','raw_task_loss','wrong_loss','reference_expense','calibration_expense',
                        'episode_expected_wrong_reports','episode_expected_references','task_floor','gap_to_known_Q'):
                check('bridge','old no-update '+key,row[key] == F(arm[key]['exact']))
            check('bridge','old controller task_headroom',row['task_headroom'] == F(prior['task_headroom']['exact']))
            for key in row['components']:
                check('bridge','old regret '+key,row['components'][key] == F(arm['components'][key]['exact']))
            for warning in WARNINGS:
                for key in row['by_warning'][warning]:
                    check('bridge','old warning '+key,row['by_warning'][warning][key] == F(arm['by_warning'][warning][key]['exact']))


def execute(output,logline):
    prep = json.loads((output/'PREPARATION.json').read_text()); qual = json.loads((output/'QUALIFICATION.json').read_text())
    C.COUNTS.update(qual['groups']); verify(prep['inputs']+prep['preserved'])
    check('scope','first execution only',not (output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    rows = read_rows(); panel,controls = population(); actual = {}
    for i,(label,meta) in enumerate(dict(panel,**controls).items(),1):
        actual[label] = finish(integrate(rows,meta['q']),meta['q'])
        if i % 25 == 0 or i == 135:
            logline(f'Integrated {i}/135 fixed environments')
    old = json.loads((PREVIOUS/'RESULTS.json').read_text()); known = {k:actual[k] for k in controls}
    bridge(known,old)
    new = population_summary(actual,list(panel))
    slices = {d:population_summary(actual,[k for k,v in panel.items() if v['dependence'] == d],False) for d in DEPENDENCE}
    for name in NAMES:
        check('aggregate','five equal slices recover primary population',new[name]['equal_mean']['net_loss'] == sum(slices[d][name]['equal_mean']['net_loss'] for d in DEPENDENCE)/5)
    old_panel = population_summary(actual,[k for k in controls if k != 'old_shared_diagnostic'])
    for name in NAMES:
        check('bridge','known nine-case panel cost',old_panel[name]['equal_mean']['net_loss'] == F(old['equal_panel_aggregate'][name]['arms']['no_update']['net_loss']['exact']))
    for methods in actual.values():
        for row in methods.values():
            ratios(row)
    verify(prep['inputs']+prep['preserved'])
    summary = dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),new_environments=125,known_controls=10,
        count_rows=len(rows),stopped_controller_rows=STOPPED,policy_changes=0,policy_optimizations=0,
        prior_or_price_tuning=0,new_feedback=0,primary='edit',symmetric_tables=len(SYMMETRIC),
        source_revision=2,prior_failed_attempts=1,main_attempt=2)
    write(output/'RESULTS.json',dict(summary=summary,new_panel=new,dependence_slices=slices,
        known_panel_control=old_panel,truths=actual,known_Q_floors={k:oracle(v['q']) for k,v in dict(panel,**controls).items()},
        prior_context='Earlier own-prior controls are preserved, with no new prior-wide oracle calculation.'))
    wall = perf_counter()-start
    logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s; fixed-policy evaluation only')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        main_wall_seconds=wall,main_cpu_seconds=process_time()-cpu,python=platform.python_version(),processes=1,
        inputs=prep['inputs'],outputs=outputs,preserved=prep['preserved'],summary=summary))


def launch(output):
    qual = json.loads((output/'QUALIFICATION.json').read_text())
    if not qual['requires_detached'] or (output/'LAUNCH.json').exists() or (output/'EXECUTION_STARTED.json').exists():
        raise RuntimeError('Detached launch requires a qualified, unstarted, over-ten-minute forecast')
    with (output/'PROCESS_STDOUT.log').open('x') as stream:
        process = subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--phase','execute','--output',str(output)],
            cwd=SOURCE,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    record = dict(launched_utc=datetime.now(timezone.utc).isoformat(),pid=process.pid,processes=1,
        forecast_main_seconds=qual['forecast_main_seconds'],automatic_polling=False)
    write(output/'LAUNCH.json',record)
    print(json.dumps(record),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('prepare','execute','launch'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); output = args.output
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    if args.phase == 'prepare':
        output.mkdir(parents=True,exist_ok=False)
    elif not (output/'QUALIFICATION.json').exists() or (output/'FAILURE.json').exists():
        raise RuntimeError('Qualified unfailed attempt required')
    if args.phase == 'launch':
        launch(output); return
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; 125 new worlds plus 10 known controls')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
