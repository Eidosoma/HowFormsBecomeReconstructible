#!/usr/bin/env python3
"""Matched learned-joint deployment on sealed stopping laws; no optimizer."""
import argparse
from collections import defaultdict
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
ROOT = MOUNT/'fep-ideas/formal-checks/fep-joint-deployment-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-generalization-attribution-v1/attempt-01'
GENERAL = MOUNT/'fep-ideas/formal-checks/fep-generalization-v1/attempt-02'
PREVIOUS_SHA = '0d2ec5f0d05682a12e1cbacaebda267a37034b4aba45cd9269dfc5f24a1d0660'
REPORT_SHA = 'b24aedae8c4659f2e61f545db16c3ecd4e38fc2c8ca3a295c2556df97ace7ac6'
GENERAL_SHA = 'b0c6520e63b60f709674b6de9ba9c17fda7fcea47c04fd71b4667b8c21641f63'
FACTOR_SHA = '208835070d8032dfceb6fa05bde2d63c36b95013eb165531387e91aa5384d880'
CAP,BASE = 64,800
SCHEDULES = ('edit','average')
DEPLOYMENTS = ('edit','average','joint')


def module(name,path,digest):
    assert sha256(path.read_bytes()).hexdigest() == digest
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


G = module('frozen_generalization',SOURCE/'check_fep_generalization_r2.py',GENERAL_SHA)
REF = module('frozen_factor',SOURCE/'check_fep_factor_revision.py',FACTOR_SHA)
C = G.C
check,write,identity = C.check,C.write,C.identity


def decode(x):
    if isinstance(x,dict):
        return F(x['exact']) if 'exact' in x and 'value' in x else {k:decode(v) for k,v in x.items()}
    if isinstance(x,list):
        return [decode(v) for v in x]
    return x


def code_for(v):
    return sum(a*3**y for y,a in enumerate(REF.policy(v)))


def read_rows():
    out = []
    for n,c,k,codes in G.read_rows():
        fit = REF.fit(c); vectors = fit['vectors']
        check('posterior','original deployment codes',codes == (code_for(vectors[1]),code_for(vectors[3])))
        joint = code_for(tuple(2*x+1 for x in c))
        check('posterior','joint component and symmetry',joint == code_for(vectors[2]) and joint in G.SYMMETRIC)
        mix = vectors[3]
        check('posterior','averaging optimal under full mixture',
              sum(v*u for v,u in zip(mix,C.UNITS[codes[1]])) <= sum(v*u for v,u in zip(mix,C.UNITS[joint])))
        out.append((n,c,k,(*codes,joint)))
    return out


def blank(cap):
    return [dict(codes=[[0]*81 for _ in DEPLOYMENTS],counts=[0]*(cap+1),
                 pairs=[defaultdict(int) for _ in SCHEDULES]) for _ in SCHEDULES]


def integrate(rows,q,cap=CAP):
    powers = [[v**n for n in range(cap+1)] for v in q]
    tails = [BASE**n for n in range(cap+1)]; stats = blank(cap)
    for n,c,k,codes in rows:
        w = prod(powers[e][c[e]] for e in range(4))*tails[cap-n]
        if not w:
            continue
        for s in (0,1):
            if not k[s]:
                continue
            mass = w*k[s]; stat = stats[s]; stat['counts'][n] += mass
            for d,code in enumerate(codes):
                stat['codes'][d][code] += mass
            for d in (0,1):
                stat['pairs'][d][(codes[d],codes[2])] += mass
    return stats


def finish(stats,q,cap=CAP):
    den = BASE**cap; deployed = {s:{} for s in SCHEDULES}; contrasts = {s:{} for s in SCHEDULES}
    for d,name in enumerate(DEPLOYMENTS):
        rows = G.finish([dict(codes=x['codes'][d],counts=x['counts']) for x in stats],q,cap)
        for s in SCHEDULES:
            deployed[s][name] = rows[s]
    risks = {code:sum(x[0]+x[1] for x in G.score(code,q)) for code in G.SYMMETRIC}
    for s,sname in enumerate(SCHEDULES):
        joint = deployed[sname]['joint']
        for d,dname in enumerate(SCHEDULES):
            original = deployed[sname][dname]; pairs = stats[s]['pairs'][d]
            check('mass','matched pair normalization',sum(pairs.values()) == den)
            check('matched','same calibration and stopped law',joint['stop_distribution'] == original['stop_distribution'] and
                  joint['calibration_expense'] == original['calibration_expense'])
            for code in G.SYMMETRIC:
                check('matched','paired marginal original',sum(m for (b,j),m in pairs.items() if b == code) == stats[s]['codes'][d][code])
                check('matched','paired marginal joint',sum(m for (b,j),m in pairs.items() if j == code) == stats[s]['codes'][2][code])
            delta = {k:joint[k]-original[k] for k in ('net_loss','raw_task_loss','wrong_loss','reference_expense','calibration_expense')}
            components = {k:joint['components'][k]-original['components'][k] for k in joint['components']}
            gross_negative = F(sum(m*min(0,risks[j]-risks[b]) for (b,j),m in pairs.items()),10*BASE*den)
            gross_positive = F(sum(m*max(0,risks[j]-risks[b]) for (b,j),m in pairs.items()),10*BASE*den)
            probability = {sign:F(sum(m for (b,j),m in pairs.items() if
                ((risks[j] > risks[b])-(risks[j] < risks[b])) == value),den)
                for sign,value in (('lower',-1),('equal',0),('higher',1))}
            check('matched','signed contrast identities',delta['net_loss'] == delta['raw_task_loss'] ==
                delta['wrong_loss']+delta['reference_expense'] == sum(components.values()) == gross_negative+gross_positive)
            check('matched','conditional probabilities normalize',sum(probability.values()) == 1)
            contrasts[sname]['joint_minus_'+dname] = dict(delta=delta,components=components,
                gross_negative_delta=gross_negative,gross_positive_delta=gross_positive,
                conditional_cost_probability=probability,
                changed_table_probability=F(sum(m for (b,j),m in pairs.items() if b != j),den),
                paired_response_probabilities={str(b)+':'+str(j):F(m,den) for (b,j),m in sorted(pairs.items())})
    return dict(deployments=deployed,contrasts=contrasts,known_Q_floor=G.oracle(q))


def bridge(actual,old,attribution=None):
    for label,result in actual.items():
        for s in SCHEDULES:
            row = dict(result['deployments'][s][s]); G.ratios(row)
            prior = old['truths'][label][s]
            check('bridge','same complete archived fields',set(row) == set(prior))
            for key,value in row.items():
                check('bridge','original diagonal '+key,value == prior[key])
        if attribution is not None and label in attribution['focus']:
            for s,d in product(SCHEDULES,repeat=2):
                row = result['deployments'][s][d]; prior = attribution['focus'][label]['crossed'][s][d]
                for key,oldkey in (('net_loss','net_loss'),('raw_task_loss','raw_loss'),
                                   ('expected_calibrations','expected_calibrations'),('calibration_expense','calibration_expense')):
                    check('bridge','previous crossed '+key,row[key] == prior[oldkey])


def summary(actual,labels):
    out = {}
    for s in SCHEDULES:
        methods,contrasts = {},{}
        for d in DEPLOYMENTS:
            rows = [actual[k]['deployments'][s][d] for k in labels]
            mean = G.average(rows); G.ratios(mean)
            eligible = [k for k in labels if actual[k]['deployments'][s][d]['task_headroom'] > 0]
            failures = [k for k in eligible if actual[k]['deployments'][s][d]['net_loss'] >= F(1,10)]
            worst = max(x['net_loss'] for x in rows)
            methods[d] = dict(equal_mean=mean,environments=len(labels),positive_headroom_environments=len(eligible),
                zero_headroom_environments=len(labels)-len(eligible),coverage_beneficial=len(eligible)-len(failures),
                coverage_failures=failures,below_always_reference=sum(x['net_loss'] < F(1,10) for x in rows),
                tied_always_reference=sum(x['net_loss'] == F(1,10) for x in rows),
                above_always_reference=sum(x['net_loss'] > F(1,10) for x in rows),
                worst_net_loss=worst,worst_cases=[k for k in labels if actual[k]['deployments'][s][d]['net_loss'] == worst])
        for d in SCHEDULES:
            key = 'joint_minus_'+d
            rows = [{k:v for k,v in actual[label]['contrasts'][s][key].items() if k != 'paired_response_probabilities'} for label in labels]
            mean = G.average(rows)
            signs = {name:[label for label in labels if
                     ((actual[label]['contrasts'][s][key]['delta']['net_loss'] > 0)-
                      (actual[label]['contrasts'][s][key]['delta']['net_loss'] < 0)) == value]
                     for name,value in (('improved',-1),('tied',0),('worsened',1))}
            check('aggregate','matched mean contrast',mean['delta']['net_loss'] ==
                  methods['joint']['equal_mean']['net_loss']-methods[d]['equal_mean']['net_loss'])
            check('aggregate','all comparison signs retained',sum(map(len,signs.values())) == len(labels))
            contrasts[key] = dict(equal_mean=mean,case_counts={k:len(v) for k,v in signs.items()},cases=signs)
        j = methods['joint']
        out[s] = dict(deployments=methods,contrasts=contrasts,criteria=dict(
            mean_joint_below_matched_MAP=contrasts['joint_minus_edit']['equal_mean']['delta']['net_loss'] < 0,
            mean_joint_below_matched_average=contrasts['joint_minus_average']['equal_mean']['delta']['net_loss'] < 0,
            mean_joint_below_always_reference=j['equal_mean']['net_loss'] < F(1,10),
            joint_full_positive_headroom_coverage=not j['coverage_failures']))
    return out


def qualify(rows,pop,old):
    start = perf_counter(); ties = 0
    for n in range(7):
        for c in C.counts(n):
            v = tuple(2*x+1 for x in c); joint = code_for(v); evidence = REF.evidence(c)[1]
            for e in range(4):
                child = tuple(x+int(i == e) for i,x in enumerate(c))
                check('qualification','joint predictive evidence ratio',REF.evidence(child)[1]/evidence == F(v[e],2*(n+2)))
            check('qualification','normalized joint predictive',sum(v) == 2*(n+2))
            risks = []
            for actions in C.ACTS:
                risk = sum(v[e]*(1 if actions[e if w == 0 else 3-e] == 2 else
                    10*int(actions[e if w == 0 else 3-e] != w)) for w,e in product((0,1),range(4)))
                risks.append(risk)
            check('qualification','joint optimum over all response tables',risks[joint] == min(risks))
            for y in range(4):
                if 10*min(v[y],v[3-y]) == v[y]+v[3-y]:
                    check('qualification','joint reference at exact tie',C.ACTS[joint][y] == 2); ties += 1
    check('qualification','ties exercised',ties > 0)
    toy = [(n,c,k,(*codes,code_for(tuple(2*x+1 for x in c)))) for n,c,k,codes in G.toy_rows()]
    laws = [x['q'] for x in pop.values()]+[(800,0,0,0),(0,0,0,800),(200,200,200,200),
                                          (720,0,0,80),(80,0,0,720),(719,0,0,81),(721,0,0,79)]
    for q in laws:
        for code in G.SYMMETRIC:
            check('qualification','independent physical task accounting',G.score(code,q) == G.direct_score(code,q))
        slow = blank(3)
        for errors in product(range(4),repeat=3):
            weight = prod(q[e] for e in errors)
            if not weight:
                continue
            for s in (0,1):
                c = [0]*4; n = 0
                while G.toy_continue(s,c):
                    c[errors[n]] += 1; n += 1
                codes = (G.toy_code(0,c),G.toy_code(1,c),code_for(tuple(2*x+1 for x in c)))
                slow[s]['counts'][n] += weight
                for d,code in enumerate(codes):
                    slow[s]['codes'][d][code] += weight
                for d in (0,1):
                    slow[s]['pairs'][d][(codes[d],codes[2])] += weight
        fast = integrate(toy,q,3)
        check('qualification','all six crossed and paired first-stop laws',fast == slow)
        finish(fast,q,3)
    known = {label:finish(integrate(rows,meta['q']),meta['q']) for label,meta in pop.items() if meta['role'] == 'known_control'}
    bridge(known,old)
    elapsed = perf_counter()-start; start = perf_counter()
    for meta in pop.values():
        integrate(rows[:2048],meta['q'])
    bench = perf_counter()-start; forecast = 120+4*bench*len(rows)/2048
    return dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),qualification_seconds=elapsed,
        laws=len(laws),toy_cap=3,toy_schedules=2,complete_known_control_bridges=len(known),
        benchmark_rows=2048,benchmark_laws=len(pop),benchmark_seconds=bench,forecast_main_seconds=forecast,
        forecast_rule='120 seconds plus four times extrapolated full-population row benchmark',requires_detached=forecast>600)


def prepare(output,logline):
    check('integrity','previous manifest pinned',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report pinned',identity(SOURCE/'FEP_GENERALIZATION_ATTRIBUTION_V1_REPORT.md')['sha256'] == REPORT_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({x['path']:x for group in ('inputs','outputs','preserved') for x in prior[group]}.values())
    preserved.append(identity(PREVIOUS/'MANIFEST.json')); G.verify(preserved)
    (output/'inputs').mkdir(); inputs = []
    files = [(SOURCE/n,n) for n in ('FEP_JOINT_DEPLOYMENT_V1.md','check_fep_joint_deployment.py',
        'check_fep_generalization_r2.py','check_fep_stopping_attribution.py','check_fep_factor_revision.py',
        'FEP_GENERALIZATION_ATTRIBUTION_V1_REPORT.md')]
    files += [(PREVIOUS/'MANIFEST.json','attribution_MANIFEST.json'),(GENERAL/'MANIFEST.json','generalization_MANIFEST.json')]
    for p,name in files:
        inputs.append(identity(p)); shutil.copyfile(p,output/'inputs'/name)
        check('integrity','source snapshot '+name,identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    inputs += [identity(p) for p in (G.LEDGER,GENERAL/'POPULATION.json',GENERAL/'RESULTS.json',PREVIOUS/'RESULTS.json')]
    shutil.copyfile(GENERAL/'POPULATION.json',output/'POPULATION.json')
    check('integrity','unchanged population copy',identity(output/'POPULATION.json')['sha256'] == identity(GENERAL/'POPULATION.json')['sha256'])
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,post_result_comparison=True,
        primary_schedule='edit',schedules=SCHEDULES,deployments=DEPLOYMENTS,panel_worlds=125,known_controls=10,
        policy_optimizations=0,prior_or_price_tuning=0,new_feedback=0,joint_component_conditioning=True))
    rows = read_rows()
    with gzip.open(output/'JOINT_DEPLOYMENT.jsonl.gz','wt') as stream:
        for n,c,k,codes in rows:
            stream.write(json.dumps([n,*c,codes[2]],separators=(',',':'))+'\n')
    pop = json.loads((GENERAL/'POPULATION.json').read_text()); pop = dict(pop['panel'],**pop['controls'])
    qual = qualify(rows,pop,decode(json.loads((GENERAL/'RESULTS.json').read_text())))
    qual['joint_ledger'] = identity(output/'JOINT_DEPLOYMENT.jsonl.gz'); write(output/'QUALIFICATION.json',qual)
    logline(f'PREPARED: {qual["checks"]} checks; forecast {qual["forecast_main_seconds"]:.3f}s; detached={qual["requires_detached"]}')


def execute(output,logline):
    prep = json.loads((output/'PREPARATION.json').read_text()); qual = json.loads((output/'QUALIFICATION.json').read_text())
    C.COUNTS.update(qual['groups']); G.verify(prep['inputs']+prep['preserved']+[qual['joint_ledger']])
    check('scope','first execution',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    rows = read_rows()
    with gzip.open(output/'JOINT_DEPLOYMENT.jsonl.gz','rt') as stream:
        for n,c,k,codes in rows:
            check('ledger','frozen joint code aligned',json.loads(next(stream)) == [n,*c,codes[2]])
        check('ledger','joint ledger complete',next(stream,None) is None)
    pop = json.loads((GENERAL/'POPULATION.json').read_text()); panel,controls = pop['panel'],pop['controls']; actual = {}
    for i,(label,meta) in enumerate(dict(panel,**controls).items(),1):
        actual[label] = finish(integrate(rows,meta['q']),meta['q'])
        if i % 25 == 0 or i == 135:
            logline(f'Integrated {i}/135 worlds; all six matched deployments')
    oldraw = json.loads((GENERAL/'RESULTS.json').read_text()); old = decode(oldraw)
    bridge(actual,old,decode(json.loads((PREVIOUS/'RESULTS.json').read_text())))
    whole = summary(actual,list(panel))
    slices = {d:summary(actual,[k for k,v in panel.items() if v['dependence'] == d]) for d in G.DEPENDENCE}
    for s,d in product(SCHEDULES,DEPLOYMENTS):
        check('aggregate','equal slices recover full population',whole[s]['deployments'][d]['equal_mean']['net_loss'] ==
              sum(slices[t][s]['deployments'][d]['equal_mean']['net_loss'] for t in G.DEPENDENCE)/5)
    for s in SCHEDULES:
        check('bridge','complete original aggregate',whole[s]['deployments'][s]['equal_mean'] == old['new_panel'][s]['equal_mean'])
    known = summary(actual,[k for k in controls if k != 'old_shared_diagnostic'])
    for result in actual.values():
        for methods in result['deployments'].values():
            for row in methods.values():
                G.ratios(row)
    G.verify(prep['inputs']+prep['preserved']+[qual['joint_ledger']])
    info = dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),panel_worlds=125,known_controls=10,
        count_rows=len(rows),stopped_controller_rows=G.STOPPED,primary_schedule='edit',policy_optimizations=0,
        prior_or_price_tuning=0,new_feedback=0,post_result_comparison=True)
    write(output/'RESULTS.json',dict(summary=info,panel=whole,dependence_slices=slices,known_panel_control=known,
        truths=actual,original_generalization_context=oldraw['new_panel'],
        no_new_prior_wide_oracle=True,no_optimized_joint_acquisition=True))
    wall = perf_counter()-start; logline(f'COMPLETE: {info["checks"]} cumulative checks; {wall:.3f}s; no optimization or tuning')
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
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; learned joint on saved schedules')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc()); write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
