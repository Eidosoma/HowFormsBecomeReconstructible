#!/usr/bin/env python3
"""Prospective off-grid evaluation of frozen schedules and deployment rules."""
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
ROOT = MOUNT/'fep-ideas/formal-checks/fep-offgrid-validation-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-joint-deployment-v1/attempt-01'
PREVIOUS_SHA = '4755c7658411aca690ec6967f95ce0258aadb302ea4e95e1affb9b53692ae37e'
REPORT_SHA = 'b698ce95823f6b7607bc9be5030a57b097e2a09635514d178513c04c2f5d1aa1'
HELPER_SHA = 'f33c9685fb466b1707a1548ce3bd4e5ff61560c9be964ebd676346f08a89c499'
BASE,CAP = 6400,64
DEPENDENCE = ('neg075','neg025','zero','pos025','pos075')
T = (F(-3,4),F(-1,4),F(0),F(1,4),F(3,4))

assert sha256((SOURCE/'check_fep_joint_deployment.py').read_bytes()).hexdigest() == HELPER_SHA
spec = importlib.util.spec_from_file_location('frozen_joint',SOURCE/'check_fep_joint_deployment.py')
J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
G,C = J.G,J.C
# Physical integer-unit configuration only. All imported source files remain frozen.
J.BASE = G.BASE = BASE
check,write,identity = C.check,C.write,C.identity


def population():
    panel = {}
    for i,j in product((3,7,11,15,19),repeat=2):
        both = (i*j,3*i*j,4*i*j,3*i*j+40*min(i,j),i*j+120*min(i,j))
        for name,t,q11 in zip(DEPENDENCE,T,both):
            q = (BASE-160*i-160*j+q11,160*j-q11,160*i-q11,q11)
            a,b = F(i,40),F(j,40)
            expected = (1+t)*a*b if t <= 0 else (1-t)*a*b+t*min(a,b)
            check('population','exact feasible new law',min(q) >= 0 and sum(q) == BASE and F(q11,BASE) == expected and
                  F(q[2]+q[3],BASE) == a and F(q[1]+q[3],BASE) == b)
            panel[f'a{25*i:03d}_b{25*j:03d}_{name}'] = dict(q=q,a=a,b=b,t=t,dependence=name,
                role='prospective_validation',weight=F(1,125))
    old = J.decode(json.loads((PREVIOUS/'POPULATION.json').read_text()))
    check('population','inherited denominator',old['denominator'] == 800)
    controls = {label:dict(meta,q=tuple(8*x for x in meta['q']),weight=F(0),role='known_control',
                origin=('previous_panel' if label in old['panel'] else 'earlier_control'))
                for label,meta in dict(old['panel'],**old['controls']).items()}
    newlaws = {x['q'] for x in panel.values()}; oldlaws = {x['q'] for x in controls.values()}
    original_fixtures = {tuple(64*x for x in q) for q in J.REF.TRUTHS.values()}
    original_fixtures |= {(q[0],q[2],q[1],q[3]) for q in original_fixtures}
    check('population','125 distinct new and 135 distinct old laws',len(panel) == len(newlaws) == 125 and len(controls) == len(oldlaws) == 135)
    check('population','new laws unseen in preceding panels and original fixtures',not(newlaws & (oldlaws | original_fixtures)))
    check('population','same independence fraction and equal weighting',sum(x['weight'] for x in panel.values()) == 1 and
          sum(x['weight'] for x in panel.values() if x['t'] == 0) == F(1,5))
    for d in DEPENDENCE:
        check('population','complete slice',sum(x['dependence'] == d for x in panel.values()) == 25)
    return dict(denominator=BASE,panel=panel,controls=controls,control_weight=F(0),
                previous_population_record=identity(PREVIOUS/'POPULATION.json'))


def read_rows():
    rows = J.read_rows()
    with gzip.open(PREVIOUS/'JOINT_DEPLOYMENT.jsonl.gz','rt') as stream:
        for n,c,k,codes in rows:
            check('ledger','frozen joint response aligned',json.loads(next(stream)) == [n,*c,codes[2]])
        check('ledger','joint response ledger complete',next(stream,None) is None)
    return rows


def bridge_case(actual,old):
    for s in J.SCHEDULES:
        for d in J.DEPLOYMENTS:
            row = dict(actual['deployments'][s][d]); G.ratios(row)
            check('bridge','complete rescaled deployment',row == old['deployments'][s][d])
        check('bridge','complete rescaled matched contrasts',actual['contrasts'][s] == old['contrasts'][s])
    check('bridge','complete rescaled informed floor',actual['known_Q_floor'] == old['known_Q_floor'])


def qualify(rows,pop,old,logline):
    start = perf_counter()
    laws = [x['q'] for x in dict(pop['panel'],**pop['controls']).values()]
    laws += [tuple(8*x for x in q) for q in ((800,0,0,0),(0,0,0,800),(200,200,200,200),
               (720,0,0,80),(80,0,0,720),(719,0,0,81),(721,0,0,79))]
    toy = [(n,c,k,(*codes,J.code_for(tuple(2*x+1 for x in c)))) for n,c,k,codes in G.toy_rows()]
    for q in laws:
        costs = []
        for code in G.SYMMETRIC:
            direct = G.direct_score(code,q)
            check('qualification','physical units by independent enumeration',G.score(code,q) == direct)
            costs.append(F(sum(x[0]+x[1] for x in direct),10*BASE))
        check('qualification','informed optimum',min(costs) == G.oracle(q)['task_floor'])
        slow = J.blank(3)
        for errors in product(range(4),repeat=3):
            weight = prod(q[e] for e in errors)
            if not weight:
                continue
            for s in (0,1):
                c = [0]*4; n = 0
                while G.toy_continue(s,c):
                    c[errors[n]] += 1; n += 1
                codes = (G.toy_code(0,c),G.toy_code(1,c),J.code_for(tuple(2*x+1 for x in c)))
                slow[s]['counts'][n] += weight
                for d,code in enumerate(codes):
                    slow[s]['codes'][d][code] += weight
                for d in (0,1):
                    slow[s]['pairs'][d][(codes[d],codes[2])] += weight
        fast = J.integrate(toy,q,3)
        check('qualification','six crossed and paired stopped laws',fast == slow)
        J.finish(fast,q,3)
    check('qualification','rescaled reference tie',G.oracle((5760,0,0,640))['canonical_optimal_actions']['agreement'] == [0,2])
    toy_seconds = perf_counter()-start; replay_start = perf_counter(); known = {}
    for i,(label,meta) in enumerate(pop['controls'].items(),1):
        known[label] = J.finish(J.integrate(rows,meta['q']),meta['q'])
        bridge_case(known[label],old['truths'][label])
        if i % 25 == 0 or i == 135:
            logline(f'Qualified complete rescaled records for {i}/135 known worlds')
    previous_labels = [k for k,v in pop['controls'].items() if v['origin'] == 'previous_panel']
    earlier_labels = [k for k,v in pop['controls'].items() if v['origin'] == 'earlier_control' and k != 'old_shared_diagnostic']
    check('bridge','complete previous 125-world aggregate',J.summary(known,previous_labels) == old['panel'])
    check('bridge','complete previous nine-world aggregate',J.summary(known,earlier_labels) == old['known_panel_control'])
    for d in G.DEPENDENCE:
        labels = [k for k in previous_labels if pop['controls'][k]['dependence'] == d]
        check('bridge','complete previous dependence slice',J.summary(known,labels) == old['dependence_slices'][d])
    replay_seconds = perf_counter()-replay_start; elapsed = perf_counter()-start; bench_start = perf_counter()
    for meta in pop['panel'].values():
        J.integrate(rows[:2048],meta['q'])
    bench = perf_counter()-bench_start; forecast = 120+4*bench*len(rows)/2048
    return dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),qualification_seconds=elapsed,
        toy_seconds=toy_seconds,known_control_replay_seconds=replay_seconds,complete_known_world_bridges=135,
        complete_known_aggregate_bridges=7,laws=len(laws),toy_cap=3,toy_schedules=2,
        benchmark_rows=2048,benchmark_laws=125,benchmark_seconds=bench,forecast_main_seconds=forecast,
        forecast_rule='120 seconds plus four times extrapolated 125-law row benchmark',requires_detached=forecast>600)


def prepare(output,logline):
    check('integrity','previous manifest pinned',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report pinned',identity(SOURCE/'FEP_JOINT_DEPLOYMENT_V1_REPORT.md')['sha256'] == REPORT_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({x['path']:x for group in ('inputs','outputs','preserved') for x in prior[group]}.values())
    preserved.append(identity(PREVIOUS/'MANIFEST.json')); G.verify(preserved)
    (output/'inputs').mkdir(); inputs = []
    files = [(SOURCE/n,n) for n in ('FEP_OFFGRID_VALIDATION_V1.md','check_fep_offgrid_validation.py',
        'check_fep_joint_deployment.py','check_fep_generalization_r2.py','check_fep_stopping_attribution.py',
        'check_fep_factor_revision.py','FEP_JOINT_DEPLOYMENT_V1_REPORT.md')]
    files.append((PREVIOUS/'MANIFEST.json','joint_deployment_MANIFEST.json'))
    for p,name in files:
        inputs.append(identity(p)); shutil.copyfile(p,output/'inputs'/name)
        check('integrity','frozen source snapshot '+name,identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    inputs += [identity(p) for p in (PREVIOUS/'POPULATION.json',PREVIOUS/'RESULTS.json',
                                     PREVIOUS/'JOINT_DEPLOYMENT.jsonl.gz',G.LEDGER)]
    pop = population(); write(output/'POPULATION.json',pop); inputs.append(identity(output/'POPULATION.json'))
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,prospective_validation=True,
        validation_worlds=125,known_control_worlds=135,physical_denominator=BASE,primary_schedule='edit',
        policy_optimizations=0,prior_or_price_tuning=0,new_feedback=0,population_selected_before_outcomes=True))
    logline('FROZEN: source, contract and explicit 125-world population before qualification')
    rows = read_rows(); old = J.decode(json.loads((PREVIOUS/'RESULTS.json').read_text()))
    q = qualify(rows,pop,old,logline); write(output/'QUALIFICATION.json',q)
    logline(f'PREPARED: {q["checks"]} checks; forecast {q["forecast_main_seconds"]:.3f}s; detached={q["requires_detached"]}')


def execute(output,logline):
    prep = json.loads((output/'PREPARATION.json').read_text()); qual = json.loads((output/'QUALIFICATION.json').read_text())
    C.COUNTS.update(qual['groups']); G.verify(prep['inputs']+prep['preserved'])
    check('scope','first execution',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    rows = read_rows(); pop = J.decode(json.loads((output/'POPULATION.json').read_text())); panel = pop['panel']; actual = {}
    for i,(label,meta) in enumerate(panel.items(),1):
        actual[label] = J.finish(J.integrate(rows,meta['q']),meta['q'])
        if i % 25 == 0:
            logline(f'Integrated {i}/125 prospective worlds; six unchanged deployments')
    whole = J.summary(actual,list(panel))
    slices = {d:J.summary(actual,[k for k,v in panel.items() if v['dependence'] == d]) for d in DEPENDENCE}
    for s,d in product(J.SCHEDULES,J.DEPLOYMENTS):
        check('aggregate','five equal slices recover full panel',whole[s]['deployments'][d]['equal_mean']['net_loss'] ==
              sum(slices[t][s]['deployments'][d]['equal_mean']['net_loss'] for t in DEPENDENCE)/5)
    for result in actual.values():
        for methods in result['deployments'].values():
            for row in methods.values():
                G.ratios(row)
    old = json.loads((PREVIOUS/'RESULTS.json').read_text())
    context = dict(previous_125_panel=old['panel'],previous_dependence_slices=old['dependence_slices'],
        earlier_nine_panel=old['known_panel_control'],old_shared_diagnostic=old['truths']['old_shared_diagnostic'],
        all_135_control_records=identity(PREVIOUS/'RESULTS.json'),complete_rescaling_bridges=135,weight_in_validation=0)
    G.verify(prep['inputs']+prep['preserved'])
    info = dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),validation_worlds=125,known_control_worlds=135,
        count_rows=len(rows),stopped_controller_rows=G.STOPPED,primary_schedule='edit',physical_denominator=BASE,
        prospective_validation=True,policy_changes=0,policy_optimizations=0,prior_or_price_tuning=0,new_feedback=0)
    write(output/'RESULTS.json',dict(summary=info,validation_panel=whole,dependence_slices=slices,truths=actual,
        known_control_context=context,no_new_prior_wide_oracle=True,no_optimized_joint_acquisition=True))
    wall = perf_counter()-start; logline(f'COMPLETE: {info["checks"]} cumulative checks; {wall:.3f}s; unchanged policies and frozen new population')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name not in ('LAUNCH.json','PROCESS_STDOUT.log')]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        main_wall_seconds=wall,main_cpu_seconds=process_time()-cpu,processes=1,python=platform.python_version(),
        inputs=prep['inputs'],outputs=outputs,preserved=prep['preserved'],summary=info))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--phase',choices=('prepare','execute','launch'),required=True)
    parser.add_argument('--output',type=Path,required=True); args = parser.parse_args(); output = args.output
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    if args.phase == 'prepare':
        output.mkdir(parents=True,exist_ok=False)
    elif not(output/'QUALIFICATION.json').exists() or (output/'FAILURE.json').exists():
        raise RuntimeError('Qualified unfailed attempt required')
    if args.phase == 'launch':
        q = json.loads((output/'QUALIFICATION.json').read_text())
        if not q['requires_detached'] or (output/'LAUNCH.json').exists() or (output/'EXECUTION_STARTED.json').exists():
            raise RuntimeError('Detached launch requires a qualified unstarted over-ten-minute forecast')
        with (output/'PROCESS_STDOUT.log').open('x') as stream:
            p = subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--phase','execute','--output',str(output)],
                cwd=SOURCE,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        record = dict(launched_utc=datetime.now(timezone.utc).isoformat(),pid=p.pid,processes=1,
            forecast_main_seconds=q['forecast_main_seconds'],automatic_polling=False)
        write(output/'LAUNCH.json',record); print(json.dumps(record),flush=True); return
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; prospective off-grid validation')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc()); write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
