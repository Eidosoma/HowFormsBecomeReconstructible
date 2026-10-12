#!/usr/bin/env python3
"""Saved-history attribution; fixed continuations, no policy optimization."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
import importlib.util
from itertools import product
import json
from math import comb, prod
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
ROOT = MOUNT/'fep-ideas/formal-checks/fep-generalization-attribution-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-generalization-v1/attempt-02'
BELLMAN = MOUNT/'fep-ideas/formal-checks/fep-adaptive-calibration-v1/attempt-01/BELLMAN.jsonl.gz'
FORECASTS = MOUNT/'fep-ideas/formal-checks/fep-forecast-validation-v1/attempt-01/STOPPED_FORECASTS.jsonl.gz'
PREVIOUS_SHA = '05a124a7408b5d37a9f275e085dce9f31d53f5eea2aed666260b29808393911b'
REPORT_SHA = 'e7af00681e055bed8f0d4fe6e382657456813bdfa6f16a96bee4de2d83c74453'
GENERAL_SHA = 'b0c6520e63b60f709674b6de9ba9c17fda7fcea47c04fd71b4667b8c21641f63'
FACTOR_SHA = '208835070d8032dfceb6fa05bde2d63c36b95013eb165531387e91aa5384d880'
BELLMAN_SHA = '97bd9ac3e39e631fb3cbda9d4c76e42d93938ca5f3ec3219e125610972b55022'
FORECAST_SHA = '35154325d6adc3101598f1fdc33f14d7fc87b48bf2b9abf6603c181491dd7100'
FOCUS = ('a15_b15_pos05','a15_b45_neg05','a45_b15_neg05','a15_b35_pos05','a35_b15_pos05')
CAP,BASE,GRID = 64,800,2**40
BIN_KEYS = ('event_probability','original_regret','structure_weight_remainder','parameter_contribution',
    'positive_parameter_contribution','negative_parameter_contribution','excess_checking','unsafe_reporting',
    'wrong_direction','raw_loss','parameter_substituted_raw_loss')


def module(name,path,digest):
    assert sha256(path.read_bytes()).hexdigest() == digest
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


G = module('frozen_generalization',SOURCE/'check_fep_generalization_r2.py',GENERAL_SHA)
C = G.C
REF = module('frozen_factor',SOURCE/'check_fep_factor_revision.py',FACTOR_SHA)
check,write,identity = C.check,C.write,C.identity
NAMES = G.NAMES


def program(v):
    return sum(
        ((0 if v[y] > v[3-y] else 1) if 10*min(v[y],v[3-y]) < v[y]+v[3-y] else 2)*3**y for y in range(4))


def belief(c):
    n,a,b = sum(c),c[2]+c[3],c[1]+c[3]
    num = C.FACT[n+1]*prod(C.FACT[2*x] for x in c)
    den = 4**n*C.FACT[a]*C.FACT[n-a]*C.FACT[b]*C.FACT[n-b]*prod(C.FACT[x] for x in c)
    v0 = ((n-a+1)*(n-b+1),(n-a+1)*(b+1),(a+1)*(n-b+1),(a+1)*(b+1))
    v1 = tuple(2*x+1 for x in c)
    mix = tuple(18*den*x+num*y*(n+2) for x,y in zip(v0,v1))
    joined = int(num > 9*den)
    return dict(c=c,n=n,num=num,den=den,joined=joined,vectors=(v0,v1,mix),
                codes=(program(v1 if joined else v0),program(mix)))


def projected(row,q):
    a,b = q[2]+q[3],q[1]+q[3]
    independent = ((BASE-a)*(BASE-b),(BASE-a)*b,a*(BASE-b),a*b)
    joint = tuple(BASE*x for x in q)
    mixed = tuple(9*row['den']*x+row['num']*y for x,y in zip(independent,joint))
    return program(joint if row['joined'] else independent),program(mixed)


def load_saved():
    levels = [{} for _ in range(CAP+1)]; rows = []
    with gzip.open(G.LEDGER,'rt') as stream, gzip.open(FORECASTS,'rt') as forecasts:
        for line in stream:
            raw = json.loads(line); c = tuple(raw[1:5]); n = raw[0]; k = tuple(map(int,raw[5]))
            row = belief(c); codes = tuple(raw[6]); i = C.ix(n,*c[:3])
            check('ledger','unique valid posterior state',n == sum(c) and min(c) >= 0 and n <= CAP and i not in levels[n])
            check('posterior','sealed model choice and actions',row['codes'] == codes and row['joined'] == raw[7])
            check('ledger','valid multiplicities',len(k) == 2 and min(k) >= 0 and any(k))
            bounds = [None,None]
            mix = row['vectors'][2]
            for s in (0,1):
                if not k[s]:
                    continue
                f = json.loads(next(forecasts))
                check('ledger','complete forecast alignment',(f[0],f[1],tuple(f[2:6]),int(f[6]),f[7]) == (s,n,c,k[s],codes[s]))
                rlo,rhi,blo,bhi = f[8:12]
                check('forecast','saved nonpositive completion bounds',0 <= rlo <= rhi <= GRID and rhi-rlo <= 1 and blo <= bhi <= 0 and bhi-blo <= 1)
                numerator = sum(x*u for x,u in zip(mix,C.UNITS[codes[s]])); denominator = 20*sum(mix)
                check('posterior','full-belief risk within saved bounds',rlo*denominator <= numerator*GRID <= rhi*denominator)
                bounds[s] = (rlo,rhi,blo,bhi)
            row.pop('vectors'); row.update(k=k,bounds=tuple(bounds))
            levels[n][i] = row; rows.append((n,c,k,codes))
        check('ledger','no remaining forecast rows',next(forecasts,None) is None)
    check('ledger','complete stopped census',len(rows) == G.ROWS and sum(sum(x>0 for x in r[2]) for r in rows) == G.STOPPED)
    codes = [bytearray(2*comb(n+3,3)) for n in range(CAP+1)]; seen = Counter()
    with gzip.open(BELLMAN,'rt') as stream:
        for line in stream:
            raw = json.loads(line); n,c = raw[0],tuple(raw[1:5]); i = C.ix(n,*c[:3])
            check('ledger','complete response lattice indexing',sum(c) == n and i == seen[n])
            seen[n] += 1; codes[n][2*i:2*i+2] = bytes(raw[7][:2])
            if i in levels[n]:
                row = levels[n][i]
                check('ledger','same saved deployment tables',tuple(raw[7][:2]) == row['codes'])
                check('ledger','actual stopping mask',all(not(raw[5] & (1<<s)) for s in (0,1) if row['k'][s]))
    check('ledger','full lattice layers',all(seen[n] == comb(n+3,3) for n in range(CAP+1)))
    return codes,levels,rows


def fresh():
    return dict(mass=0,count=0,raw=0,completion=0,gain=0,positive_gain=0,negative_gain=0,
        positive_mass=0,negative_mass=0,early=0,joint=0,rlo=0,rhi=0,blo=0,bhi=0)


def choose(best,key,value,c,g,row,extra=None):
    if value <= 0:
        return
    old = best[key]
    if old is None or value > old['weight'] or (value == old['weight'] and (c,g) < (old['counts'],old['warning_index'])):
        best[key] = dict(weight=value,counts=c,warning_index=g,row=row,extra=extra)


def physical(q,codes,levels,cap=CAP,max_layers=None):
    powers = [[x**n for n in range(cap+1)] for x in q]; tails = [BASE**n for n in range(cap+1)]
    scores = {code:G.score(code,q) for code in G.SYMMETRIC}
    risk = {code:sum(x[0]+x[1] for x in scores[code]) for code in scores}
    floors = [min(10*q[3-g],10*q[g],q[g]+q[3-g]) for g in (0,1)]
    stats = [[fresh() for _ in (0,1)] for _ in (0,1)]
    bins = [[[[0]*len(BIN_KEYS) for _ in range(2)] for _ in range(2)] for _ in range(2*(cap+1))]
    best = [dict(excess_checking=None,unsafe_reporting=None,positive_completion=None) for _ in (0,1)]
    next_z,states,conditional = None,0,{}
    for step,n in enumerate(range(cap,-1,-1)):
        if max_layers is not None and step == max_layers:
            break
        current = [[0]*comb(n+3,3) for _ in (0,1)]; rem = tails[cap-n]
        for i,c in enumerate(C.counts(n)):
            child = C.children(n,c) if n < cap else None
            current_codes = (codes[n][2*i],codes[n][2*i+1])
            for d in (0,1):
                current[d][i] = risk[current_codes[d]] if n == cap else sum(x*next_z[d][t] for x,t in zip(q,child))
            row = levels[n].get(i)
            states += 1
            if row is None:
                continue
            if cap <= 3:
                conditional[c] = tuple(current[d][i] for d in (0,1))
            likelihood = prod(powers[e][c[e]] for e in range(4))
            if not likelihood:
                continue
            substituted = projected(row,q)
            for s in (0,1):
                if not row['k'][s]:
                    continue
                kl = row['k'][s]*likelihood; mass = kl*rem
                for d in (0,1):
                    st = stats[s][d]; z = current[d][i]; r = risk[current_codes[d]]
                    gain = 25*(r*rem-z)-2*(cap-n)*rem
                    st['mass'] += mass; st['count'] += n*mass; st['raw'] += mass*r
                    st['completion'] += kl*z; st['gain'] += kl*gain
                    st['early'] += mass*int(n < cap); st['joint'] += mass*row['joined']
                    st['positive_gain'] += kl*max(gain,0); st['negative_gain'] += kl*min(gain,0)
                    st['positive_mass'] += mass*int(gain > 0); st['negative_mass'] += mass*int(gain < 0)
                    if n == cap:
                        check('completion','zero cap benefit',gain == 0)
                    if s == d and row['bounds'][s] is not None:
                        for key,value in zip(('rlo','rhi','blo','bhi'),row['bounds'][s]):
                            st[key] += mass*value
                    if s == d:
                        choose(best[s],'positive_completion',kl*gain,c,0,row,
                               dict(mass=mass,completion_numerator=z,remaining_scale=rem,gain_numerator=gain))
                for g in (0,1):
                    old,new = scores[current_codes[s]][g],scores[substituted[s]][g]
                    raw,newraw = old[0]+old[1],new[0]+new[1]
                    parameter,structure = raw-newraw,newraw-floors[g]
                    check('attribution','fixed-order telescope',structure >= 0 and sum(old[2:]) == structure+parameter)
                    vals = (10*(q[g]+q[3-g]),sum(old[2:]),structure,parameter,max(parameter,0),min(parameter,0),*old[2:],raw,newraw)
                    bucket = bins[2*n+s][row['joined']][g]
                    for j,value in enumerate(vals):
                        bucket[j] += mass*value
                    for key,j in (('excess_checking',2),('unsafe_reporting',3)):
                        choose(best[s],key,mass*old[j],c,g,row,dict(mass=mass,projected_code=substituted[s]))
        next_z = current
    if max_layers is not None:
        return dict(states=states)
    check('completion','full response lattice',states == comb(cap+4,4))
    return dict(stats=stats,bins=bins,best=best,roots=[z[0] for z in next_z],states=states,conditional=conditional)


def example(item,q,s,kind,cap):
    if item is None:
        return None
    c,g,row = item['counts'],item['warning_index'],item['row']; b = belief(c); den = BASE**cap
    v = b['vectors'][b['joined']] if s == 0 else b['vectors'][2]
    full = b['vectors'][2]; mass = item['extra']['mass']; p = projected(row,q)
    def best_risk(vec):
        return F(min(vec[g],vec[3-g]),vec[g]+vec[3-g]) if vec[g]+vec[3-g] else None
    out = dict(counts=c,n=sum(c),history_probability=F(mass,den),MAP_model='joint' if row['joined'] else 'independent',
        posterior_joint_weight=F(row['num'],row['num']+9*row['den']),bayes_factor=F(row['num'],row['den']),
        saved_actions=C.ACTS[row['codes'][s]],parameter_substituted_actions=C.ACTS[p[s]],
        known_Q_actions=G.oracle(q)['representative_actions'])
    if kind == 'positive_completion':
        x = item['extra']; out.update(weighted_gain=F(item['weight'],200000*den),
            conditional_net_gain=F(x['gain_numerator'],200000*x['remaining_scale']),
            conditional_completion_raw_loss=F(x['completion_numerator'],8000*x['remaining_scale']))
    else:
        out.update(warning=G.WARNINGS[g],weighted_regret=F(item['weight'],8000*den),
            selected_belief_best_report_risk=best_risk(v),full_belief_best_report_risk=best_risk(full),
            physical_best_report_risk=best_risk(q),conditional_warning_probability=F(q[g]+q[3-g],BASE))
    out['saved_forecast_bounds'] = [F(x,GRID) for x in row['bounds'][s]] if row['bounds'][s] is not None else None
    return out


def summarize(result,q,cap=CAP,subjective=True):
    den = BASE**cap; roots = result['roots']; crossed = {}; diagonal = {}
    for s,sname in enumerate(NAMES):
        crossed[sname] = {}
        for d,dname in enumerate(NAMES):
            st = result['stats'][s][d]
            check('mass','normalized stopped law',st['mass'] == den)
            check('completion','stops partition fixed completion',st['completion'] == roots[d])
            check('completion','gain sign partition',st['gain'] == st['positive_gain']+st['negative_gain'])
            check('completion','gain signs occur only before cap',st['positive_mass']+st['negative_mass'] <= st['early'])
            raw = F(st['raw'],8000*den); charge = F(st['count'],100000*den)
            fixed = F(roots[d],8000*den)+F(cap,100000); gain = F(st['gain'],200000*den)
            check('completion','exact full-cost bridge',raw+charge-fixed == gain)
            crossed[sname][dname] = dict(raw_loss=raw,calibration_expense=charge,net_loss=raw+charge,
                expected_calibrations=F(st['count'],den),early_probability=F(st['early'],den),cap_probability=1-F(st['early'],den),
                MAP_joint_probability=F(st['joint'],den),fixed64_raw_loss=F(roots[d],8000*den),fixed64_net_loss=fixed,
                completion_benefit=gain,positive_gain=F(st['positive_gain'],200000*den),negative_gain=F(st['negative_gain'],200000*den),
                positive_probability=F(st['positive_mass'],den),negative_probability=F(st['negative_mass'],den),
                zero_probability=1-F(st['positive_mass']+st['negative_mass'],den),
                positive_fraction_of_early_stops=F(st['positive_mass'],st['early']) if st['early'] else None)
        st = result['stats'][s][s]
        records = []
        for n,j,g in product(range(cap+1),range(2),range(2)):
            row = {key:F(value,8000*den) for key,value in zip(BIN_KEYS,result['bins'][2*n+s][j][g])}
            check('attribution','bin identities',row['original_regret'] == row['structure_weight_remainder']+row['parameter_contribution'] and
                row['parameter_contribution'] == row['positive_parameter_contribution']+row['negative_parameter_contribution'])
            records.append(dict(n=n,MAP_structure=('independent','joint')[j],warning=G.WARNINGS[g],values=row))
        def total(subset):
            return {key:sum(x['values'][key] for x in subset) for key in BIN_KEYS}
        totals = total(records)
        check('attribution','event mass and full gap',totals['event_probability'] == 1 and
            totals['original_regret']+G.oracle(q)['task_floor'] == crossed[sname][sname]['raw_loss'])
        diag = dict(totals=totals,by_structure={name:total([x for x in records if x['MAP_structure'] == name]) for name in ('independent','joint')},
            by_warning={name:total([x for x in records if x['warning'] == name]) for name in G.WARNINGS},joint_bins=records,
            examples={key:example(v,q,s,key,cap) for key,v in result['best'][s].items()})
        if subjective:
            intervals = {key:[F(st[lo],GRID*den),F(st[hi],GRID*den)] for key,lo,hi in
                         (('current_risk','rlo','rhi'),('completion_benefit','blo','bhi'))}
            for pair in intervals.values():
                check('forecast','weighted bound width',F(0) <= pair[1]-pair[0] <= F(1,GRID))
            check('forecast','subjective completion nonpositive',intervals['completion_benefit'][1] <= 0)
            diag['subjective_forecast_intervals'] = intervals
        diagonal[sname] = diag
    ee,ea,ae,aa = (crossed[s][d]['net_loss'] for s,d in (('edit','edit'),('edit','average'),('average','edit'),('average','average')))
    contrasts = dict(diagonal_difference=ee-aa,deployment_at_edit_stops=ee-ea,schedule_with_average_deployment=ea-aa,
        schedule_with_edit_deployment=ee-ae,deployment_at_average_stops=ae-aa)
    check('crossing','both substitution orders',ee-aa == (ee-ea)+(ea-aa) == (ee-ae)+(ae-aa))
    return dict(Q=[F(x,BASE) for x in q],crossed=crossed,diagonal=diagonal,contrasts=contrasts,known_Q_floor=G.oracle(q))


def bridge(summary,old):
    for s,name in enumerate(NAMES):
        x = summary['crossed'][name][name]; prior = old[name]; d = summary['diagonal'][name]
        for key,source in (('net_loss','net_loss'),('raw_loss','raw_task_loss'),('calibration_expense','calibration_expense'),
                           ('expected_calibrations','expected_calibrations'),('early_probability','early_probability'),('cap_probability','cap_probability')):
            check('bridge','sealed diagonal '+key,x[key] == F(prior[source]['exact']))
        for key in ('excess_checking','unsafe_reporting','wrong_direction'):
            check('bridge','sealed original regret '+key,d['totals'][key] == F(prior['components'][key]['exact']))
        for w in G.WARNINGS:
            check('bridge','sealed warning regret',d['by_warning'][w]['original_regret'] == F(prior['by_warning'][w]['decision_regret']['exact']))


def toy():
    cap=3; codes=[bytearray(2*comb(n+3,3)) for n in range(cap+1)]; levels=[{} for _ in range(cap+1)]
    for n in range(cap+1):
        for i,c in enumerate(C.counts(n)):
            row=belief(c); row.pop('vectors'); row.update(k=[0,0],bounds=(None,None))
            codes[n][2*i:2*i+2]=bytes(row['codes']); levels[n][i]=row
    for s in (0,1):
        current={(0,0,0,0):1}
        for n in range(cap+1):
            future={}
            for c,k in current.items():
                if G.toy_continue(s,c):
                    for e in range(4):
                        child=tuple(v+int(e==i) for i,v in enumerate(c));future[child]=future.get(child,0)+k
                else:
                    levels[n][C.ix(n,*c[:3])]['k'][s]=k
            current=future
    levels=[{i:r for i,r in layer.items() if any(r['k'])} for layer in levels]
    return codes,levels


def qualify(codes,levels,rows,pop,old):
    begin=perf_counter(); tc,tl=toy(); laws=[tuple(v) for v in pop.values()]+[(800,0,0,0),(0,0,0,800),(720,0,0,80),(200,200,200,200)]
    for n in range(5):
        for c in C.counts(n):
            b=belief(c); ref=REF.fit(c); ev=REF.evidence(c)
            check('qualification','conjugate odds',F(b['num'],b['den']) == ev[1]/ev[0])
            check('qualification','independent frozen action reference',b['codes'] == tuple(sum(a*3**y for y,a in enumerate(REF.policy(ref['vectors'][j]))) for j in (1,3)))
            for q in laws:
                sub=projected(b,q)
                for code in (*b['codes'],*sub):
                    score=G.score(code,q)
                    direct=G.direct_score(code,q)
                    check('qualification','independent physical regret',score == direct)
    for q in laws:
        calc=physical(q,tc,tl,3); out=summarize(calc,q,3,False)
        for n,layer in enumerate(tl):
            for row in layer.values():
                c=row['c']; future=[F(0),F(0)]
                for seq in product(range(4),repeat=3-n):
                    terminal=tuple(c[e]+seq.count(e) for e in range(4)); code=tc[3][2*C.ix(3,*terminal[:3]):2*C.ix(3,*terminal[:3])+2]
                    probability=F(prod(q[e] for e in seq),BASE**len(seq))
                    for d in (0,1):
                        loss=sum(F(q[e],2*BASE)*(F(1,10) if C.ACTS[code[d]][e if w==0 else 3-e]==2 else
                            int(C.ACTS[code[d]][e if w==0 else 3-e]!=w)) for w,e in product((0,1),range(4)))
                        future[d]+=probability*loss
                for d in (0,1):
                    check('qualification','direct future sequences',future[d] == F(calc['conditional'][c][d],8000*BASE**(3-n)))
        direct=[[dict(net=F(0),completion=F(0)) for _ in (0,1)] for _ in (0,1)]
        for seq in product(range(4),repeat=3):
            probability=F(prod(q[e] for e in seq),BASE**3)
            end=tuple(seq.count(e) for e in range(4))
            for s in (0,1):
                c=[0]*4;used=0
                while G.toy_continue(s,c):
                    c[seq[used]]+=1;used+=1
                for d in (0,1):
                    code=tc[used][2*C.ix(used,*c[:3])+d];last=tc[3][2*C.ix(3,*end[:3])+d]
                    raw=F(sum(x[0]+x[1] for x in G.score(code,q)),8000)
                    complete=F(sum(x[0]+x[1] for x in G.score(last,q)),8000)
                    direct[s][d]['net']+=probability*(raw+F(used,100000))
                    direct[s][d]['completion']+=probability*complete
        for s,d in product(range(2),repeat=2):
            x=out['crossed'][NAMES[s]][NAMES[d]]
            check('qualification','ordered stopping/global coupling',x['net_loss'] == direct[s][d]['net'] and x['fixed64_raw_loss'] == direct[s][d]['completion'])
    # Exercise the archived schema with known diagonal costs before execution.
    for label,q in pop.items():
        reproduced=G.finish(G.integrate(rows,q),q)
        for name in NAMES:
            for key in ('net_loss','raw_task_loss','expected_calibrations','calibration_expense','early_probability','cap_probability'):
                check('qualification','archived diagonal schema '+key,reproduced[name][key] == F(old['truths'][label][name][key]['exact']))
            for key in ('excess_checking','unsafe_reporting','wrong_direction'):
                check('qualification','archived component schema '+key,reproduced[name]['components'][key] == F(old['truths'][label][name]['components'][key]['exact']))
            for w in G.WARNINGS:
                check('qualification','archived warning schema',reproduced[name]['by_warning'][w]['decision_regret'] == F(old['truths'][label][name]['by_warning'][w]['decision_regret']['exact']))
    elapsed=perf_counter()-begin;begin=perf_counter();states=0
    for q in pop.values():
        states+=physical(q,codes,levels,max_layers=2)['states']
    bench=perf_counter()-begin;forecast=120+4*bench*(5*comb(CAP+4,4))/states
    return dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),qualification_seconds=elapsed,laws=len(laws),
        benchmark_seconds=bench,benchmark_states=states,forecast_main_seconds=forecast,requires_detached=forecast>600,
        forecast_rule='120 seconds plus four times full-five-case lattice extrapolation',toy_cap=3,policy_optimizations=0)


def prepare(output,logline):
    for path,digest in ((PREVIOUS/'MANIFEST.json',PREVIOUS_SHA),(SOURCE/'FEP_GENERALIZATION_V1_REPORT.md',REPORT_SHA),
                        (BELLMAN,BELLMAN_SHA),(FORECASTS,FORECAST_SHA)):
        check('integrity','pinned '+path.name,identity(path)['sha256'] == digest)
    prior=json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved=list({x['path']:x for group in ('inputs','outputs','preserved') for x in prior[group]}.values())
    G.verify(preserved);(output/'inputs').mkdir()
    files=[(SOURCE/n,n) for n in ('FEP_GENERALIZATION_ATTRIBUTION_V1.md','check_fep_generalization_attribution.py',
        'FEP_GENERALIZATION_V1_REPORT.md','check_fep_generalization_r2.py','check_fep_stopping_attribution.py','check_fep_factor_revision.py')]
    files += [(PREVIOUS/'MANIFEST.json','generalization_MANIFEST.json'),(PREVIOUS/'POPULATION.json','generalization_POPULATION.json')]
    inputs=[]
    for p,name in files:
        inputs.append(identity(p));shutil.copyfile(p,output/'inputs'/name)
        check('integrity','source snapshot '+name,identity(output/'inputs'/name)['sha256']==inputs[-1]['sha256'])
    inputs += [identity(p) for p in (BELLMAN,FORECASTS,G.LEDGER,PREVIOUS/'RESULTS.json')]
    population=json.loads((PREVIOUS/'POPULATION.json').read_text())
    pop={label:tuple(population['panel'][label]['q']) for label in FOCUS}
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,focus=pop,post_result_analysis=True,
        context_worlds=125,new_controllers=0,new_gates=0,prior_or_price_tuning=0,policy_optimizations=0))
    codes,levels,rows=load_saved();old=json.loads((PREVIOUS/'RESULTS.json').read_text())
    q=qualify(codes,levels,rows,pop,old);write(output/'QUALIFICATION.json',q)
    logline(f'PREPARED: {q["checks"]} checks; qualification {q["qualification_seconds"]:.3f}s; forecast {q["forecast_main_seconds"]:.3f}s; detached={q["requires_detached"]}')


def execute(output,logline):
    prep=json.loads((output/'PREPARATION.json').read_text());qual=json.loads((output/'QUALIFICATION.json').read_text())
    C.COUNTS.update(qual['groups']);G.verify(prep['inputs']+prep['preserved'])
    check('scope','first execution',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started=perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    codes,levels,rows=load_saved();old=json.loads((PREVIOUS/'RESULTS.json').read_text());actual={}
    for label in FOCUS:
        q=tuple(prep['focus'][label]);raw=physical(q,codes,levels);result=summarize(raw,q)
        bridge(result,old['truths'][label]);actual[label]=result
        write(output/(label+'.json'),result);logline('Completed fixed attribution for '+label)
    G.verify(prep['inputs']+prep['preserved'])
    summary=dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),focus_worlds=5,context_worlds=125,
        count_rows=len(rows),stopped_controller_rows=G.STOPPED,lattice_states_per_world=comb(CAP+4,4),
        policy_optimizations=0,new_controllers=0,new_gates=0,post_result_analysis=True,prior_or_price_tuning=0)
    write(output/'RESULTS.json',dict(summary=summary,focus=actual,generalization_context=old['new_panel'],
        complete_context_record=identity(PREVIOUS/'RESULTS.json'),no_new_prior_wide_oracle=True))
    wall=perf_counter()-start;logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s; no changed policy or new gate')
    outputs=[identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        main_wall_seconds=wall,main_cpu_seconds=process_time()-cpu,processes=1,python=platform.python_version(),
        inputs=prep['inputs'],outputs=outputs,preserved=prep['preserved'],summary=summary))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('prepare','execute','launch'),required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();output=args.output
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    if args.phase=='prepare':
        output.mkdir(parents=True,exist_ok=False)
    elif not(output/'QUALIFICATION.json').exists() or (output/'FAILURE.json').exists():
        raise RuntimeError('Qualified, unfailed attempt required')
    if args.phase=='launch':
        qual=json.loads((output/'QUALIFICATION.json').read_text())
        if not qual['requires_detached'] or (output/'LAUNCH.json').exists() or (output/'EXECUTION_STARTED.json').exists():
            raise RuntimeError('Detached launch requires qualified unstarted over-ten-minute forecast')
        with (output/'PROCESS_STDOUT.log').open('x') as stream:
            process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--phase','execute','--output',str(output)],
                cwd=SOURCE,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        record=dict(launched_utc=datetime.now(timezone.utc).isoformat(),pid=process.pid,processes=1,
                    forecast_main_seconds=qual['forecast_main_seconds'],automatic_polling=False)
        write(output/'LAUNCH.json',record);print(json.dumps(record),flush=True);return
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; saved-history attribution')
        (prepare if args.phase=='prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc());write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS)))
        raise


if __name__=='__main__':
    main()
