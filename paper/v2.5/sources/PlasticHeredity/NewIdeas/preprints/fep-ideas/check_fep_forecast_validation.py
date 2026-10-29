#!/usr/bin/env python3
"""Frozen-policy forecast validation: exact laws and bounded subjective means."""
import argparse
from array import array
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
import importlib.util
from itertools import product
import json
from math import comb, prod
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter, process_time
import traceback

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-forecast-validation-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-stopping-attribution-v1/attempt-01'
ADAPT = MOUNT/'fep-ideas/formal-checks/fep-adaptive-calibration-v1/attempt-01'
PREVIOUS_SHA = 'ab66ca8a2866f8777e57c074e41e8ff566f5fae3c5eff83775c8c2174f5478b6'
HELPER_SHA = '18f0f15f1f89bfd2c98f8aa8601f52264ef4eeb17f9c19e01733aa90aedb96bd'
REPORT_SHA = 'e5c57656a68a0d262afb050c86c88570aa542f19edf4dbd57178f13fc44deae0'
FACTOR_SHA = '208835070d8032dfceb6fa05bde2d63c36b95013eb165531387e91aa5384d880'
CAP, BASE, GRID = 64, 400, 2**40
NAMES = ('edit', 'average')
CUTS = (F(1,40), F(1,20), F(3,40), F(1,10), F(1,8))
BIN_LABELS = ('[0,.025)', '[.025,.05)', '[.05,.075)', '[.075,.1)', '[.1,.125)', '[.125,1]')
PANEL = {
    'a05_rho0': (342,38,18,2), 'a05_rho5': (351,29,9,11), 'a05_rho1': (360,20,0,20),
    'a15_rho0': (238,102,42,18), 'a15_rho5': (259,81,21,39), 'a15_rho1': (280,60,0,60),
    'a25_rho0': (150,150,50,50), 'a25_rho5': (175,125,25,75), 'a25_rho1': (200,100,0,100)}
OLD_Q = (320,40,0,40)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


# Pure finite-model helpers; this module contains no policy optimizer.
from hashlib import sha256
assert sha256((SOURCE/'check_fep_stopping_attribution.py').read_bytes()).hexdigest() == HELPER_SHA
C = module('frozen_attribution_helpers', SOURCE/'check_fep_stopping_attribution.py')
check, close, write, identity = C.check, C.close, C.write, C.identity


def risk_bin(num, den):
    for i, cut in enumerate(CUTS):
        if num*cut.denominator < den*cut.numerator:
            return i
    return len(CUTS)


def bound(num, den):
    low, rem = divmod(num*GRID, den)
    return low, int(rem != 0)


def load_policy():
    masks = [bytearray(comb(n+3,3)) for n in range(CAP+1)]
    codes = [bytearray(2*comb(n+3,3)) for n in range(CAP+1)]
    displays = [array('d', [0.0])*(2*comb(n+3,3)) for n in range(CAP+1)]
    seen = Counter()
    with gzip.open(ADAPT/'BELLMAN.jsonl.gz', 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            n, c, mask = row[0], tuple(row[1:5]), row[5]
            i = C.ix(n, *c[:3])
            check('saved policy', 'complete count indexing', sum(c) == n and i == seen[n])
            seen[n] += 1
            masks[n][i] = mask
            for s in (0,1):
                codes[n][2*i+s] = row[7][s]
                displays[n][2*i+s] = row[8][s]/100
            if n == CAP:
                check('saved policy', 'cap stops', mask & 3 == 0)
    check('saved policy', 'all layers', all(seen[n] == comb(n+3,3) for n in range(CAP+1)))
    return dict(cap=CAP, masks=masks, codes=codes, displays=displays)


def paths(policy):
    cap = policy['cap']
    reach = [[[0]*comb(n+3,3) for n in range(cap+1)] for _ in (0,1)]
    for s in (0,1):
        reach[s][0][0] = 1
    for n in range(cap):
        for i,c in enumerate(C.counts(n)):
            child = None
            for s in (0,1):
                k = reach[s][n][i]
                if k and policy['masks'][n][i] & (1 << s):
                    if child is None:
                        child = C.children(n,c)
                    for t in child:
                        reach[s][n+1][t] += k
    return reach


def quant_arrays(cap):
    return {key:[array('q', [0])*(2*comb(n+3,3)) for n in range(cap+1)]
            for key in ('risk','benefit')} | {
        key:[bytearray(2*comb(n+3,3)) for n in range(cap+1)] for key in ('widths','bins')}


def prior_evaluate(policy, reach, ledger=None, strict=False, logline=lambda s:None):
    cap, scale = policy['cap'], 4**(policy['cap']+1)*C.FACT[policy['cap']+2]**2
    denominator = 10*scale
    next_w = [C.mixed(c,scale) for c in C.counts(cap+1)]
    next_z, quant = None, quant_arrays(cap)
    stats = [dict(mass=0,reads=0,count=0,risk=0,completion=0,benefit=0,early=0,
                  counts=[0]*(cap+1),bins=[[0,0] for _ in BIN_LABELS]) for _ in (0,1)]
    states, rows = 0, 0
    for n in range(cap,-1,-1):
        length = comb(n+3,3)
        current_w, current_z = [0]*length, [[0]*length for _ in (0,1)]
        for i,c in enumerate(C.counts(n)):
            child = C.children(n,c)
            pred = tuple(next_w[t] for t in child)
            w = sum(pred)
            current_w[i] = w
            scores = [5000*sum(p*u for p,u in zip(pred,C.UNITS[policy['codes'][n][2*i+s]])) for s in (0,1)]
            for s in (0,1):
                z = scores[s] if n == cap else sum(next_z[s][t] for t in child)
                current_z[s][i] = z
                k = reach[s][n][i]
                if not k:
                    continue
                stat, mass = stats[s], k*w
                if policy['masks'][n][i] & (1 << s):
                    check('paths', 'no calibration after cap', n < cap)
                    stat['reads'] += mass
                    continue
                score, benefit = scores[s], scores[s]-z-(cap-n)*w
                if strict:
                    check('prior stopping', 'completion forecast nonpositive', benefit <= 0)
                if 'displays' in policy:
                    close('saved display', 'task forecast', F(score,100000*w), policy['displays'][n][2*i+s])
                rlo,rwidth = bound(score,100000*w)
                blo,bwidth = bound(benefit,100000*w)
                b = risk_bin(score,100000*w)
                at = 2*i+s
                quant['risk'][n][at], quant['benefit'][n][at] = rlo,blo
                quant['widths'][n][at], quant['bins'][n][at] = rwidth+2*bwidth,b
                stat['mass'] += mass
                stat['count'] += n*mass
                stat['counts'][n] += mass
                stat['risk'] += k*score
                stat['completion'] += k*z
                stat['benefit'] += k*benefit
                stat['early'] += mass*int(n < cap)
                stat['bins'][b][0] += mass
                stat['bins'][b][1] += k*score
                if ledger is not None:
                    ledger.write(json.dumps([s,n,*c,str(k),policy['codes'][n][at],rlo,rlo+rwidth,blo,blo+bwidth,b],separators=(',',':'))+'\n')
                rows += 1
            states += 1
        next_w,next_z = current_w,current_z
        if n == cap or n % 16 == 0:
            logline(f'Prior completion through n={n}; {states} states')
    check('prior law', 'root evidence', next_w == [denominator])
    result = {}
    for s,name in enumerate(NAMES):
        stat = stats[s]
        check('prior law', 'stop probability and acquisition accounting', stat['mass'] == denominator and stat['reads'] == stat['count'])
        check('prior law', 'completion coupling', stat['completion'] == next_z[s][0])
        raw = F(stat['risk'],100000*denominator)
        net = F(stat['risk']+stat['reads'],100000*denominator)
        fixed_raw = F(next_z[s][0],100000*denominator)
        fixed_net = fixed_raw+F(cap,100000)
        benefit = F(stat['benefit'],100000*denominator)
        check('prior law', 'benefit identity', benefit == net-fixed_net)
        result[name] = dict(expected_calibrations=F(stat['count'],denominator),
            early_probability=F(stat['early'],denominator),cap_probability=F(stat['counts'][-1],denominator),
            raw_loss=raw,predicted_raw_loss=raw,forecast_bias=F(0),net_loss=net,
            fixed_raw_loss=fixed_raw,fixed_net_loss=fixed_net,completion_benefit=benefit,
            stop_distribution=[F(x,denominator) for x in stat['counts']],
            calibration_bins=[dict(label=label,probability=F(m,denominator),
                actual_risk=F(r,100000*m) if m else None,predicted_risk=F(r,100000*m) if m else None)
                for label,(m,r) in zip(BIN_LABELS,stat['bins'])])
    return quant,result,dict(states=states,stopped_forecast_rows=rows)


def interval(low, high, denominator):
    result = (F(low,denominator*GRID),F(high,denominator*GRID))
    check('bounds', 'mean quantization width', F(0) <= result[1]-result[0] <= F(1,GRID))
    return result


def truth_evaluate(policy, reach, quant, q):
    cap, denominator = policy['cap'], BASE**policy['cap']
    check('population', 'rational Q', sum(q) == BASE and min(q) >= 0)
    powers = [[x**n for n in range(cap+1)] for x in q]
    scale = [BASE**n for n in range(cap+1)]
    risk = [sum(x*u for x,u in zip(q,units)) for units in C.UNITS]
    stats = [dict(mass=0,reads=0,count=0,risk=0,completion=0,gain=0,positive=0,negative=0,
        positive_mass=0,negative_mass=0,early=0,forecast_rlo=0,forecast_rhi=0,forecast_blo=0,forecast_bhi=0,
        counts=[[0,0,0] for _ in range(cap+1)],bins=[[0,0,0,0] for _ in BIN_LABELS]) for _ in (0,1)]
    next_z, states = None,0
    for n in range(cap,-1,-1):
        current = [[0]*comb(n+3,3) for _ in (0,1)]
        rem_scale = scale[cap-n]
        for i,c in enumerate(C.counts(n)):
            child = C.children(n,c) if n < cap else None
            likelihood = None
            for s in (0,1):
                code = policy['codes'][n][2*i+s]
                z = risk[code] if n == cap else sum(x*next_z[s][t] for x,t in zip(q,child))
                current[s][i] = z
                k = reach[s][n][i]
                if not k:
                    continue
                if likelihood is None:
                    likelihood = prod(powers[e][c[e]] for e in range(4))
                if not likelihood:
                    continue
                stat, kl = stats[s],k*likelihood
                mass = kl*rem_scale
                if policy['masks'][n][i] & (1 << s):
                    stat['reads'] += mass
                    continue
                # Raw denominator is 20*400=8000; common cost denominator 200000.
                gain = 25*(risk[code]*rem_scale-z)-2*(cap-n)*rem_scale
                weighted_gain = kl*gain
                stat['mass'] += mass
                stat['count'] += n*mass
                stat['risk'] += mass*risk[code]
                stat['completion'] += kl*z
                stat['gain'] += weighted_gain
                stat['early'] += mass*int(n < cap)
                if gain > 0:
                    stat['positive'] += weighted_gain
                    stat['positive_mass'] += mass
                elif gain < 0:
                    stat['negative'] += weighted_gain
                    stat['negative_mass'] += mass
                at = 2*i+s
                rlo,blo = quant['risk'][n][at],quant['benefit'][n][at]
                widths,b = quant['widths'][n][at],quant['bins'][n][at]
                rhi,bhi = rlo+(widths & 1),blo+((widths >> 1) & 1)
                stat['forecast_rlo'] += mass*rlo
                stat['forecast_rhi'] += mass*rhi
                stat['forecast_blo'] += mass*blo
                stat['forecast_bhi'] += mass*bhi
                bucket = stat['bins'][b]
                bucket[0] += mass
                bucket[1] += mass*risk[code]
                bucket[2] += mass*rlo
                bucket[3] += mass*rhi
                bucket = stat['counts'][n]
                bucket[0] += mass
                bucket[1] += weighted_gain
                bucket[2] += mass*int(gain > 0)
            states += 1
        next_z = current
    result = {}
    for s,name in enumerate(NAMES):
        stat = stats[s]
        check('true law', 'stop probability and acquisition accounting', stat['mass'] == denominator and stat['reads'] == stat['count'])
        check('true law', 'completion coupling', stat['completion'] == next_z[s][0])
        check('true law', 'signed gain partition', stat['positive']+stat['negative'] == stat['gain'])
        raw = F(stat['risk'],8000*denominator)
        net = raw+F(stat['reads'],100000*denominator)
        fixed_raw = F(next_z[s][0],8000*denominator)
        fixed_net = fixed_raw+F(cap,100000)
        gain = F(stat['gain'],200000*denominator)
        check('true law', 'net benefit identity', gain == net-fixed_net)
        check('true law', 'known-Q response bound', raw >= F(min(risk),8000))
        r_interval = interval(stat['forecast_rlo'],stat['forecast_rhi'],denominator)
        b_interval = interval(stat['forecast_blo'],stat['forecast_bhi'],denominator)
        bins = []
        for label,(mass,r,rlo,rhi) in zip(BIN_LABELS,stat['bins']):
            predicted = interval(rlo,rhi,mass) if mass else None
            actual = F(r,8000*mass) if mass else None
            bins.append(dict(label=label,probability=F(mass,denominator),actual_risk=actual,
                predicted_risk_bounds=predicted,
                actual_minus_predicted_bounds=(actual-predicted[1],actual-predicted[0]) if mass else None))
        result[name] = dict(expected_calibrations=F(stat['count'],denominator),
            early_probability=F(stat['early'],denominator),cap_probability=F(stat['counts'][-1][0],denominator),
            raw_loss=raw,net_loss=net,fixed_raw_loss=fixed_raw,fixed_net_loss=fixed_net,
            known_Q_best_response_loss=F(min(risk),8000),completion_benefit=gain,
            positive_gain=F(stat['positive'],200000*denominator),negative_gain=F(stat['negative'],200000*denominator),
            positive_probability=F(stat['positive_mass'],denominator),negative_probability=F(stat['negative_mass'],denominator),
            positive_given_early=F(stat['positive_mass'],stat['early']) if stat['early'] else None,
            predicted_raw_loss_bounds=r_interval,predicted_completion_benefit_bounds=b_interval,
            actual_minus_predicted_risk_bounds=(raw-r_interval[1],raw-r_interval[0]),
            actual_minus_predicted_benefit_bounds=(gain-b_interval[1],gain-b_interval[0]),
            calibration_bins=bins,
            stopping_counts=[dict(n=n,probability=F(m,denominator),
                weighted_gain=F(g,200000*denominator),positive_probability=F(p,denominator))
                for n,(m,g,p) in enumerate(stat['counts'])])
    return result,states


def toy_policy(reference, cap=3, all_to_cap=False):
    masks,codes = [],[]
    for n in range(cap+1):
        masks.append(bytearray(comb(n+3,3)))
        codes.append(bytearray(2*comb(n+3,3)))
        for i,c in enumerate(C.counts(n)):
            if all_to_cap:
                mask = 3 if n < cap else 0
                code = (51,51)
            else:
                go0 = n < cap and (n == 0 or (n == 1 and c[0] == 0) or (n == 2 and c[3] > 0))
                go1 = n < cap and (n == 0 or (n == 1 and c[3] == 0))
                mask = int(go0)+2*int(go1)
                vectors = reference.fit(c)['vectors']
                code = tuple(sum(a*3**y for y,a in enumerate(reference.policy(vectors[j]))) for j in (1,3))
            masks[n][i] = mask
            for s in (0,1):
                codes[n][2*i+s] = code[s]
    return dict(cap=cap,masks=masks,codes=codes)


def qualify(reference):
    started = perf_counter()
    policy = toy_policy(reference)
    reach = paths(policy)
    quant,prior,_ = prior_evaluate(policy,reach)
    def evidence(c):
        e = reference.evidence(c)
        return (9*e[0]+e[1])/10
    def pred_risk(c,s):
        v = reference.fit(c)['vectors'][3]
        code = policy['codes'][sum(c)][2*C.ix(sum(c),*c[:3])+s]
        return sum(F(x,sum(v))*F(u,20) for x,u in zip(v,C.UNITS[code]))
    def prior_completion(c,s):
        return sum(evidence(tuple(x+seq.count(e) for e,x in enumerate(c)))/evidence(c)*
            pred_risk(tuple(x+seq.count(e) for e,x in enumerate(c)),s)
            for seq in product(range(4),repeat=3-sum(c)))
    expected_panel = {}
    for a,rlabel in ((F(1,20),'05'),(F(3,20),'15'),(F(1,4),'25')):
        for rho,label in ((F(0),'0'),(F(1,2),'5'),(F(1),'1')):
            t = (1-rho)*a*(2*a)+rho*a
            expected_panel['a'+rlabel+'_rho'+label] = tuple(int(BASE*x) for x in (1-3*a+t,2*a-t,a-t,t))
    check('qualification','panel formula',expected_panel == PANEL)
    previous_truths = {(288,72,32,8),(320,40,0,40),(304,56,16,24),(280,80,40,0),(224,56,96,24)}
    check('qualification','panel excludes old truths',not(set(PANEL.values()) & previous_truths))
    for value in (F(-1,3),F(0),F(1,40),F(1,10),F(1,8),F(1)):
        lo,width = bound(value.numerator,value.denominator)
        check('qualification','signed quantization',F(lo,GRID) <= value <= F(lo+width,GRID))
    check('qualification','bin ties', [risk_bin(x.numerator,x.denominator) for x in CUTS] == [1,2,3,4,5])
    cases = dict(PANEL,old_shared=OLD_Q,own_prior=None)
    for label,q in cases.items():
        actual = prior if q is None else truth_evaluate(policy,reach,quant,q)[0]
        for s,name in enumerate(NAMES):
            stopped = Counter()
            def walk(c,p):
                n,i = sum(c),C.ix(sum(c),*c[:3])
                if policy['masks'][n][i] & (1 << s):
                    for e in range(4):
                        nxt = tuple(x+int(e == t) for t,x in enumerate(c))
                        probability = evidence(nxt)/evidence(c) if q is None else F(q[e],BASE)
                        walk(nxt,p*probability)
                else:
                    stopped[c] += p
            walk((0,0,0,0),F(1))
            nmean,raw,benefit,rpred,bpred = F(0),F(0),F(0),F(0),F(0)
            for c,p in stopped.items():
                n,i = sum(c),C.ix(sum(c),*c[:3])
                factor = evidence(c) if q is None else prod(F(q[e],BASE)**c[e] for e in range(4))
                check('qualification','ordered stopping path weights',p == reach[s][n][i]*factor)
                prior_r = pred_risk(c,s)
                prior_b = prior_r-prior_completion(c,s)-F(3-n,100000)
                at = 2*i+s
                for key,number,shift in (('risk',prior_r,0),('benefit',prior_b,1)):
                    low = quant[key][n][at]
                    width = (quant['widths'][n][at] >> shift) & 1
                    check('qualification','forecast bound contains exact',F(low,GRID) <= number <= F(low+width,GRID))
                check('qualification','exact risk bin',quant['bins'][n][at] == risk_bin(prior_r.numerator,prior_r.denominator))
                nmean += p*n
                rpred += p*prior_r
                bpred += p*prior_b
                if q is None:
                    raw += p*prior_r
                    benefit += p*prior_b
                else:
                    code = policy['codes'][n][at]
                    r = sum(F(x,BASE)*F(u,20) for x,u in zip(q,C.UNITS[code]))
                    complete = F(0)
                    for seq in product(range(4),repeat=3-n):
                        terminal = tuple(x+seq.count(e) for e,x in enumerate(c))
                        tcode = policy['codes'][3][2*C.ix(3,*terminal[:3])+s]
                        complete += prod(F(q[e],BASE) for e in seq)*sum(F(x,BASE)*F(u,20) for x,u in zip(q,C.UNITS[tcode]))
                    raw += p*r
                    benefit += p*(r-complete-F(3-n,100000))
            row = actual[name]
            check('qualification','ordered law totals',sum(stopped.values()) == 1 and nmean == row['expected_calibrations'] and raw == row['raw_loss'] and benefit == row['completion_benefit'])
            if q is not None:
                for key,val in (('predicted_raw_loss_bounds',rpred),('predicted_completion_benefit_bounds',bpred)):
                    check('qualification','weighted quantization contains exact',row[key][0] <= val <= row[key][1])
    # Time the same kernels at cap 12; no optimizer and no main panel outcomes.
    bench_policy = toy_policy(reference,cap=12,all_to_cap=True)
    bench_reach = paths(bench_policy)
    t = perf_counter()
    bench_quant,_,scope = prior_evaluate(bench_policy,bench_reach)
    prior_seconds = perf_counter()-t
    t = perf_counter()
    truth_evaluate(bench_policy,bench_reach,bench_quant,(100,100,100,100))
    truth_seconds = perf_counter()-t
    forecast = 90+6*(prior_seconds+10*truth_seconds)*comb(CAP+4,4)/scope['states']
    return dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),wall_seconds=perf_counter()-started,
        direct_ordered_cap=3,benchmark_cap=12,benchmark_prior_seconds=prior_seconds,
        benchmark_truth_seconds=truth_seconds,forecast_main_seconds=forecast,
        forecast_rule='90 seconds I/O plus six times cap-12 per-state cost for one prior and ten truth integrations',
        requires_detached=forecast > 600,quantization_step=F(1,GRID))


def verify(entries, label):
    for entry in entries:
        check('integrity',label+' '+entry['path'],identity(Path(entry['path'])) == entry)


def prepare(output,logline):
    check('integrity','prior manifest',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','prior report',identity(SOURCE/'FEP_STOPPING_ATTRIBUTION_V1_REPORT.md')['sha256'] == REPORT_SHA)
    check('integrity','factor source',identity(SOURCE/'check_fep_factor_revision.py')['sha256'] == FACTOR_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    unique = {e['path']:e for group in ('inputs','outputs','preserved') for e in old[group]}
    preserved = list(unique.values())
    verify(preserved,'preserved before')
    originals = [(SOURCE/name,name) for name in ('FEP_FORECAST_VALIDATION_V1.md','check_fep_forecast_validation.py',
        'FEP_STOPPING_ATTRIBUTION_V1.md','FEP_STOPPING_ATTRIBUTION_V1_REPORT.md','check_fep_stopping_attribution.py',
        'FEP_ADAPTIVE_CALIBRATION_V1.md','FEP_ADAPTIVE_CALIBRATION_V1_REPORT.md','check_fep_factor_revision.py')]
    originals += [(PREVIOUS/'MANIFEST.json','attribution_MANIFEST.json'),
        (PREVIOUS/'RESULTS.json','attribution_RESULTS.json'),(ADAPT/'RESULTS.json','adaptive_RESULTS.json')]
    (output/'inputs').mkdir()
    inputs = []
    for path,name in originals:
        entry = identity(path)
        inputs.append(entry)
        shutil.copyfile(path,output/'inputs'/name)
        check('integrity','snapshot '+name,identity(output/'inputs'/name)['sha256'] == entry['sha256'])
    inputs.append(identity(ADAPT/'BELLMAN.jsonl.gz'))
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,panel=PANEL,Q_denominator=BASE,
        cap=CAP,task_horizon=100,pair_cost=F(1,1000),forecast_grid_step=F(1,GRID),
        bins=BIN_LABELS,methods=NAMES,large_inputs_read_in_place=True,policy_optimizations=0,
        forecast_ledger_columns=['method','n','c00','c01','c10','c11','ordered stopped path count','terminal code',
            'risk grid lower','risk grid upper','benefit grid lower','benefit grid upper','risk bin'],
        declaration='fixed policies; prior identity control; new panel equal weights; old shared truth is integrity replay only'))
    reference = module('frozen_factor_reference',SOURCE/'check_fep_factor_revision.py')
    qualification = qualify(reference)
    write(output/'QUALIFICATION.json',qualification)
    logline(f'PREPARED: {qualification["checks"]} checks; qualification {qualification["wall_seconds"]:.3f}s; main forecast {qualification["forecast_main_seconds"]:.1f}s; detached={qualification["requires_detached"]}')


def execute(output,logline):
    prepared = json.loads((output/'PREPARATION.json').read_text())
    qualification = json.loads((output/'QUALIFICATION.json').read_text())
    for key,value in qualification['groups'].items():
        C.COUNTS[key] += value
    verify(prepared['inputs']+prepared['preserved'],'unchanged before main')
    check('scope','main not already started',not(output/'EXECUTION_STARTED.json').exists())
    started,cpu,start = datetime.now(timezone.utc).isoformat(),process_time(),perf_counter()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qualification['forecast_main_seconds']))
    policy = load_policy()
    reach = paths(policy)
    logline('Loaded frozen policies and stopping-conditioned ordered path counts')
    with gzip.open(output/'STOPPED_FORECASTS.jsonl.gz','wt',encoding='utf-8',compresslevel=6) as ledger:
        quant,prior,scope = prior_evaluate(policy,reach,ledger,True,logline)
    saved = json.loads((ADAPT/'RESULTS.json').read_text())
    for name in NAMES:
        root = saved['root_prior_predictions']['adaptive_'+name]
        check('prior control','sealed optimal root',prior[name]['net_loss'] == F(root['value']['exact'])/100)
        check('prior control','sealed fixed root',prior[name]['fixed_net_loss'] == F(root['fixed_cap_prior_value']['exact'])/100)
        check('prior control','nonpositive completion gain',prior[name]['completion_benefit'] <= 0)
    write(output/'PRIOR_CONTROL.json',prior)
    rows,total_truth_states = {},0
    for label,q in dict(PANEL,old_shared_integrity_replay=OLD_Q).items():
        row,states = truth_evaluate(policy,reach,quant,q)
        total_truth_states += states
        write(output/(label+'.json'),dict(Q=[F(x,BASE) for x in q],methods=row))
        if label in PANEL:
            rows[label] = row
        else:
            attribution = json.loads((PREVIOUS/'RESULTS.json').read_text())
            for name in NAMES:
                old_row = saved['truths']['shared']['methods']['adaptive_'+name]
                for key in ('expected_calibrations','raw_loss','net_loss'):
                    check('integrity replay','known shared '+key,row[name][key] == F(old_row[key]['exact']))
                old_cross = attribution['crossed'][name+'_stop__'+name+'_deploy']
                for key,old_key in (('completion_benefit','net_completion_gain'),('positive_probability','positive_probability'),('negative_gain','negative_gain')):
                    check('integrity replay','known attribution '+key,row[name][key] == F(old_cross[old_key]['exact']))
        logline(f'Integrated {label}; edit net {float(row["edit"]["net_loss"]):.12f}; stopping gap {float(row["edit"]["completion_benefit"]):+.12f}')
    aggregates = {}
    for name in NAMES:
        values = [row[name] for row in rows.values()]
        keys = ('expected_calibrations','early_probability','raw_loss','net_loss','fixed_net_loss',
                'completion_benefit','positive_probability','positive_gain','negative_gain')
        avg = {key:sum(v[key] for v in values)/len(values) for key in keys}
        for key in ('predicted_raw_loss_bounds','predicted_completion_benefit_bounds','actual_minus_predicted_risk_bounds'):
            avg[key] = tuple(sum(v[key][j] for v in values)/len(values) for j in (0,1))
        avg['positive_given_early'] = avg['positive_probability']/avg['early_probability'] if avg['early_probability'] else None
        avg['gates'] = dict(learning_pays_on_equal_panel=avg['net_loss'] < F(1,10),
            stopping_no_worse_on_equal_panel=avg['completion_benefit'] <= 0,
            stopping_no_worse_in_every_environment=all(v['completion_benefit'] <= 0 for v in values))
        avg['individual_learning_pays'] = sum(v['net_loss'] < F(1,10) for v in values)
        avg['individual_stopping_no_worse'] = sum(v['completion_benefit'] <= 0 for v in values)
        avg['maximum_stopping_penalty'] = max(v['completion_benefit'] for v in values)
        aggregates[name] = avg
    verify(prepared['inputs']+prepared['preserved'],'unchanged after main')
    summary = dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),max_display_residual=C.MAX_ERROR,
        prior_states=scope['states'],stopped_forecast_rows=scope['stopped_forecast_rows'],truth_states=total_truth_states,
        new_environments=9,known_integrity_replays=1,policy_optimizations=0,sampled_trajectories=0,
        forecast_interval_width_bound=F(1,GRID),functional_gates=aggregates['edit']['gates'])
    write(output/'RESULTS.json',dict(summary=summary,own_prior=prior,equal_panel_aggregate=aggregates,
        panel={label:{name:{k:v for k,v in row[name].items() if k not in ('calibration_bins','stopping_counts')}
                     for name in NAMES} for label,row in rows.items()}))
    wall = perf_counter()-start
    logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s main wall; primary gates {summary["functional_gates"]}')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,
        finished_utc=datetime.now(timezone.utc).isoformat(),main_wall_seconds=wall,
        main_cpu_seconds=process_time()-cpu,preparation_qualification_seconds=qualification['wall_seconds'],
        python=platform.python_version(),processes=1,inputs=prepared['inputs'],outputs=outputs,
        preserved=prepared['preserved'],summary=summary))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',choices=('prepare','execute'),required=True)
    args = parser.parse_args()
    output = args.output
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    if args.phase == 'prepare':
        output.mkdir(parents=True,exist_ok=False)
    else:
        if not (output/'QUALIFICATION.json').exists() or (output/'FAILURE.json').exists():
            raise RuntimeError('Qualified, unfailed prepared record required')
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; no optimizer')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
