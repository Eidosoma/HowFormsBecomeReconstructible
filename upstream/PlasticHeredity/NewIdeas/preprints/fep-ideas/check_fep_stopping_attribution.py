#!/usr/bin/env python3
"""Saved-policy completion and crossed deployment audit; no optimizer."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
import importlib.util
from itertools import product
import json
from math import comb, factorial
from pathlib import Path
import platform
import shutil
from time import perf_counter, process_time
import traceback

MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-stopping-attribution-v1'
ADAPT = MOUNT/'fep-ideas/formal-checks/fep-adaptive-calibration-v1/attempt-01'
FIXED = MOUNT/'fep-ideas/formal-checks/fep-factor-revision-v1/attempt-01'
ADAPT_SHA = '166d3532b5e77f0c618ad23092ceb0cef8d1886950a3e5a4f69c76a5168afb9f'
FIXED_SHA = '1666bab83fe475199da13b7e7c254fd230a583c7558cc4af989d747e868421a4'
FACTOR_CODE_SHA = '208835070d8032dfceb6fa05bde2d63c36b95013eb165531387e91aa5384d880'
ADAPT_REPORT_SHA = 'f17b05236f77d11423bcccd9295735096b0a741ff3fab7a1d47da8af7250f8b4'
CAP, H = 64,100
Q, Q10 = (80,10,0,10),(8,1,0,1)
FACT = [factorial(n) for n in range(2*CAP+3)]
BIN3 = [comb(n,3) if n >= 3 else 0 for n in range(CAP+5)]
ACTS = tuple(tuple(code//3**y % 3 for y in range(4)) for code in range(81))
UNITS = tuple(tuple(sum(1 if d[e if w == 0 else 3-e] == 2 else
                       10*int(d[e if w == 0 else 3-e] != w) for w in (0,1))
                    for e in range(4)) for d in ACTS)
NAMES, OLD_NAMES = ('edit','average'),('adaptive_edit','adaptive_average')
COUNTS, MAX_ERROR, TOL = Counter(),0.0,1e-10


def check(group,label,condition):
    if not condition:
        raise AssertionError((group,label))
    COUNTS[group] += 1


def close(group,label,x,y):
    global MAX_ERROR
    error = abs(float(x)-float(y))
    MAX_ERROR = max(MAX_ERROR,error)
    check(group,label,error <= TOL)


def encode(x):
    if isinstance(x,F):
        return dict(exact=str(x),value=float(x))
    if isinstance(x,dict):
        return {str(k):encode(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):
        return [encode(v) for v in x]
    return x


def write(path,data):
    path.write_text(json.dumps(encode(data),indent=2,sort_keys=True)+'\n')


def identity(path):
    digest = sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            size += len(block)
            digest.update(block)
    return dict(path=str(path.resolve()),bytes=size,sha256=digest.hexdigest())


def counts(n):
    for a in range(n+1):
        for b in range(n-a+1):
            for c in range(n-a-b+1):
                yield (a,b,c,n-a-b-c)


def ix(n,a,b,c):
    return BIN3[n+3]-BIN3[n-a+3]+b*(n-a+1)-b*(b-1)//2+c


def children(n,c):
    a,b,d,_ = c
    return (ix(n+1,a+1,b,d),ix(n+1,a,b+1,d),ix(n+1,a,b,d+1),ix(n+1,a,b,d))


def weights(c,scale):
    n,a,b = sum(c),c[2]+c[3],c[1]+c[3]
    num0,den0 = scale*FACT[a]*FACT[n-a]*FACT[b]*FACT[n-b],FACT[n+1]**2
    num1,den1 = scale,4**n*FACT[n+1]
    for k in c:
        num1 *= FACT[2*k]
        den1 *= FACT[k]
    w0,r0 = divmod(num0,den0)
    w1,r1 = divmod(num1,den1)
    check('likelihood','integer conjugate integrals',r0 == r1 == 0)
    return w0,w1


def mixed(c,scale):
    w0,w1 = weights(c,scale)
    return 9*w0+w1


def physical(code):
    wrong,ask = 0,0
    for w in (0,1):
        for e,p in enumerate(Q):
            act = ACTS[code][e if w == 0 else 3-e]
            wrong += p*int(act != 2 and act != w)
            ask += p*int(act == 2)
    return wrong,ask


PHYS = tuple(physical(code) for code in range(81))
RISK = tuple(10*wrong+ask for wrong,ask in PHYS)


def code_at(codes,c,d):
    n = sum(c)
    return codes[n][2*ix(n,*c[:3])+d]


def load_saved():
    stops = [{},{}]
    raw_rows = 0
    with gzip.open(ADAPT/'STOPPED.jsonl.gz','rt',encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            raw_rows += 1
            if row[0] != 'shared' or row[1] not in (0,1):
                continue
            s,n,c = row[1],row[2],tuple(row[3:7])
            mass,remainder = divmod(int(row[7]),10**CAP)
            check('saved stops','supported and exactly rescaled',c[2] == 0 and sum(c) == n and remainder == 0 and mass > 0)
            check('saved stops','unique stopped count',c not in stops[s])
            stops[s][c] = (mass,row[8])
    for s in (0,1):
        check('saved stops','normalized conditional-path mass',sum(m for m,_ in stops[s].values()) == 10**CAP)
    targets = set(stops[0]) | set(stops[1])
    codes = [bytearray(2*comb(n+3,3)) for n in range(CAP+1)]
    records,seen = {},Counter()
    with gzip.open(ADAPT/'BELLMAN.jsonl.gz','rt',encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            n,c,mask = row[0],tuple(row[1:5]),row[5]
            index = ix(n,*c[:3])
            check('saved policies','complete ordered count indexing',sum(c) == n and index == seen[n])
            seen[n] += 1
            for d in (0,1):
                codes[n][2*index+d] = row[7][d]
            if c in targets:
                records[c] = dict(mask=mask,stop_display=row[8][:2])
                for s in (0,1):
                    if c in stops[s]:
                        check('saved policies','actual stop and terminal code',not(mask & (1 << s)) and row[7][s] == stops[s][c][1])
    check('saved policies','full lattice and all targets',sum(seen.values()) == comb(CAP+4,4) and set(records) == targets)
    for n in range(CAP+1):
        check('saved policies','each layer complete',seen[n] == comb(n+3,3))
    return stops,codes,records,raw_rows


def prior_completion(codes,targets,cap,records=None,logline=lambda s:None):
    scale = 4**(cap+1)*FACT[cap+2]**2
    boundary = [mixed(c,scale) for c in counts(cap+1)]
    next_z = None
    extracted,states = {},0
    for n in range(cap,-1,-1):
        current = [[0]*comb(n+3,3) for _ in (0,1)]
        for i,c in enumerate(counts(n)):
            child = children(n,c)
            programs = (codes[n][2*i],codes[n][2*i+1])
            if n == cap:
                pred = tuple(boundary[k] for k in child)
                scores = tuple(5000*sum(p*u for p,u in zip(pred,UNITS[code])) for code in programs)
                for d in (0,1):
                    current[d][i] = scores[d]
            else:
                for d in (0,1):
                    current[d][i] = sum(next_z[d][k] for k in child)
            if c in targets:
                w0,w1 = weights(c,scale)
                w = 9*w0+w1
                if n < cap:
                    pred = tuple(mixed(tuple(x+int(e == t) for t,x in enumerate(c)),scale) for e in range(4))
                    scores = tuple(5000*sum(p*u for p,u in zip(pred,UNITS[code])) for code in programs)
                check('prior prediction','conditional likelihoods normalize',sum(pred) == w)
                benefits = tuple(F(scores[d]-current[d][i]-(cap-n)*w,100000*w) for d in (0,1))
                extracted[c] = dict(prior_benefit=benefits,posterior_joint=F(w1,w),
                                    prior_current_loss=tuple(F(v,100000*w) for v in scores),
                                    prior_completion_loss=tuple(F(current[d][i],100000*w) for d in (0,1)))
                if records is not None:
                    check('prior prediction','saved structural choice',bool(records[c]['mask'] & 16) == (w1 > 9*w0))
                    for d in (0,1):
                        close('saved display','current task cost',F(scores[d],1000*w),records[c]['stop_display'][d])
            states += 1
        next_z = current
        if n == cap or n % 16 == 0:
            logline(f'Evaluated fixed completion under prior through n={n}; {states} states; no minimization')
    root_w = 10*scale
    roots = tuple(F(next_z[d][0],100000*root_w) for d in (0,1))
    check('scope','prior completion full lattice',states == comb(cap+4,4))
    return extracted,roots,states


def si(n,a,b):
    return a*(n+1)-a*(a-1)//2+b


def truth_completion(codes,targets,cap):
    next_v,extracted,states = None,{},0
    for n in range(cap,-1,-1):
        current = [[0]*comb(n+2,2) for _ in (0,1)]
        for a in range(n+1):
            for b in range(n-a+1):
                c,index = (a,b,0,n-a-b),si(n,a,b)
                for d in (0,1):
                    if n == cap:
                        value = RISK[code_at(codes,c,d)]
                    else:
                        value = 8*next_v[d][si(n+1,a+1,b)]+next_v[d][si(n+1,a,b+1)]+next_v[d][si(n+1,a,b)]
                    current[d][index] = value
                if c in targets:
                    extracted[c] = tuple(F(current[d][index],2000*10**(cap-n)) for d in (0,1))
                states += 1
        next_v = current
    check('scope','supported truth lattice',states == comb(cap+3,3))
    return extracted,tuple(F(next_v[d][0],2000*10**cap) for d in (0,1)),states


def toy_codes(reference,cap):
    result = [bytearray(2*comb(n+3,3)) for n in range(cap+1)]
    for n in range(cap+1):
        for i,c in enumerate(counts(n)):
            old = reference.fit(c)['vectors']
            for d,v in enumerate((old[1],old[3])):
                acts = reference.policy(v)
                result[n][2*i+d] = sum(a*3**y for y,a in enumerate(acts))
    return result


def qualify(reference):
    start = perf_counter()
    cap,scale = 3,4**4*FACT[5]**2
    codes = toy_codes(reference,cap)
    targets = {c for n in range(cap+1) for c in counts(n)}
    pred,prior_roots,_ = prior_completion(codes,targets,cap)
    actual,true_roots,_ = truth_completion(codes,targets,cap)
    for code in range(81):
        check('qualification','physical loss units',F(RISK[code],2000) == sum(F(q,100)*F(u,20) for q,u in zip(Q,UNITS[code])))
    def mixture_evidence(c):
        ev = reference.evidence(c)
        return (9*ev[0]+ev[1])/10
    for c in targets:
        check('qualification','integer evidence equals frozen integral',tuple(F(w,scale) for w in weights(c,scale)) == reference.evidence(c))
        n,den = sum(c),mixture_evidence(c)
        prior_values,true_values = [F(0),F(0)],[F(0),F(0)]
        for seq in product(range(4),repeat=cap-n):
            terminal = tuple(x+seq.count(e) for e,x in enumerate(c))
            p_prior = mixture_evidence(terminal)/den
            p_true = F(1)
            for e in seq:
                p_true *= F(Q10[e],10)
            p = reference.fit(terminal)['vectors'][3]
            for d in (0,1):
                code = code_at(codes,terminal,d)
                prior_risk = sum(F(v,sum(p))*F(u,20) for v,u in zip(p,UNITS[code]))
                prior_values[d] += p_prior*prior_risk
                true_values[d] += p_true*F(RISK[code],2000)
        for d in (0,1):
            check('qualification','ordered/prior completion',prior_values[d] == pred[c]['prior_completion_loss'][d])
            if c[2] == 0:
                check('qualification','ordered/true completion',true_values[d] == actual[c][d])
            if n == cap:
                check('qualification','no completion at cap',pred[c]['prior_benefit'][d] == 0)
    # Stop after the first 00, otherwise after two draws: retain path ordering.
    stop_mass = defaultdict(F)
    for e in range(4):
        p = F(Q10[e],10)
        if e == 0:
            stop_mass[(1,0,0,0)] += p
        else:
            for f in range(4):
                c = tuple(int(t == e)+int(t == f) for t in range(4))
                stop_mass[c] += p*F(Q10[f],10)
    stop_mass = {c:p for c,p in stop_mass.items() if p}
    check('qualification','toy stopping mass and count',sum(stop_mass.values()) == 1 and sum(sum(c)*p for c,p in stop_mass.items()) == F(6,5))
    for d in (0,1):
        completed = sum(p*actual[c][d] for c,p in stop_mass.items())
        raw = sum(p*F(RISK[code_at(codes,c,d)],2000) for c,p in stop_mass.items())
        paid = sum(p*F(sum(c),100000) for c,p in stop_mass.items())
        benefits = sum(p*(F(RISK[code_at(codes,c,d)],2000)-actual[c][d]-F(cap-sum(c),100000)) for c,p in stop_mass.items())
        check('qualification','stopping partition recovers completion law',completed == true_roots[d])
        check('qualification','local/global net attribution',benefits == raw+paid-true_roots[d]-F(cap,100000))
    return dict(checks=sum(COUNTS.values()),groups=dict(COUNTS),wall_seconds=perf_counter()-start,
                direct_ordered_cap=cap,numeric_contract='exact rational checks; no policy optimization')


def aggregate(stops,codes,records,pred,actual,reference,output):
    rows,groups,examples = {},{},{}
    with gzip.open(output/'STOP_AUDIT.jsonl.gz','wt',encoding='utf-8') as stream:
        for s in (0,1):
            for d in (0,1):
                key = NAMES[s]+'_stop__'+NAMES[d]+'_deploy'
                totals = defaultdict(F)
                bins = {axis:defaultdict(lambda:defaultdict(F)) for axis in ('count','MAP_structure','response_table','benefit_sign')}
                prior_min,prior_max = None,None
                local_examples = []
                for c,(mass,_) in sorted(stops[s].items()):
                    n,p = sum(c),F(mass,10**CAP)
                    code = code_at(codes,c,d)
                    wrong,ask = PHYS[code]
                    raw,paid = F(RISK[code],2000),F(n,100000)
                    completion,saved = actual[c][d],F(CAP-n,100000)
                    benefit = raw-completion-saved
                    predicted = pred[c]['prior_benefit'][d]
                    joined = bool(records[c]['mask'] & 16)
                    old = reference.fit(c)
                    v = old['vectors'][1 if d == 0 else 3]
                    check('saved policy','audited deployment matches posterior rule',ACTS[code] == reference.policy(v))
                    if s == d:
                        check('prior choice','declined feasible completion under own belief',predicted <= 0)
                    if n == CAP:
                        check('boundary','cap benefits zero',benefit == predicted == 0)
                    prior_min = predicted if prior_min is None else min(prior_min,predicted)
                    prior_max = predicted if prior_max is None else max(prior_max,predicted)
                    vals = dict(mass=F(1),expected_calibrations=F(n),raw_loss=raw,net_loss=raw+paid,
                                wrong_probability=F(wrong,200),ask_probability=F(ask,200),
                                completion_raw_loss=completion,raw_completion_gain=raw-completion,
                                saved_calibration_cost=saved,net_completion_gain=benefit,
                                positive_gain=max(benefit,F(0)),negative_gain=min(benefit,F(0)),
                                early_probability=F(n<CAP),positive_probability=F(benefit>0),
                                negative_probability=F(benefit<0),MAP_join_probability=F(joined),
                                forecast_sign_disagreement_probability=F(benefit>0 and predicted<=0),
                                differing_deployment_probability=F(code_at(codes,c,0)!=code_at(codes,c,1)))
                    for name,value in vals.items():
                        totals[name] += p*value
                    sign = 'cap' if n == CAP else ('positive' if benefit>0 else ('negative' if benefit<0 else 'zero'))
                    if s == d:
                        for axis,label in (('count',n),('MAP_structure','joint' if joined else 'independent'),('response_table',code),('benefit_sign',sign)):
                            for name,value in vals.items():
                                bins[axis][label][name] += p*value
                    local = dict(stopping_rule=NAMES[s],deployment=NAMES[d],counts=c,n=n,
                        probability=p,MAP_structure='joint' if joined else 'independent',response=ACTS[code],
                        response_code=code,posterior_joint=pred[c]['posterior_joint'],raw_loss=raw,
                        true_completion_loss=completion,saved_calibration_cost=saved,
                        true_net_completion_gain=benefit,prior_net_completion_gain=predicted,
                        weighted_true_gain=p*benefit,prior_current_loss=pred[c]['prior_current_loss'][d],
                        prior_completion_loss=pred[c]['prior_completion_loss'][d])
                    stream.write(json.dumps(encode(local),separators=(',',':'))+'\n')
                    if s == d:
                        local_examples.append(local)
                check('aggregation','row normalized',totals['mass'] == 1)
                check('aggregation','raw/cost split',totals['net_completion_gain'] == totals['raw_completion_gain']-totals['saved_calibration_cost'])
                check('aggregation','positive/negative partition',totals['net_completion_gain'] == totals['positive_gain']+totals['negative_gain'])
                rows[key] = dict(totals,prior_benefit_range=(prior_min,prior_max),stopped_count_states=len(stops[s]))
                if s == d:
                    for axis,parts in bins.items():
                        check('aggregation',axis+' complete',sum(v['mass'] for v in parts.values()) == 1 and sum(v['net_completion_gain'] for v in parts.values()) == totals['net_completion_gain'])
                    groups[key] = bins
                    positive = sorted((v for v in local_examples if v['weighted_true_gain']>0),key=lambda v:v['weighted_true_gain'],reverse=True)[:3]
                    negative = sorted((v for v in local_examples if v['weighted_true_gain']<0),key=lambda v:v['weighted_true_gain'])[:1]
                    examples[key] = dict(selection='three largest positive and one largest negative weighted contributions',positive=positive,negative=negative)
    write(output/'STRATA.json',groups)
    write(output/'EXAMPLES.json',examples)
    return rows


def run(output):
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Mounted external FEP namespace required')
    output.mkdir(parents=True,exist_ok=False)
    (output/'inputs').mkdir()
    started,start,cpu = datetime.now(timezone.utc).isoformat(),perf_counter(),process_time()
    inputs,preserved = [],[]
    source = Path(__file__).resolve().parent
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline('Started '+started+'; one process; fixed-policy attribution, no optimizer')
        for path,digest in ((ADAPT/'MANIFEST.json',ADAPT_SHA),(FIXED/'MANIFEST.json',FIXED_SHA),
                            (source/'check_fep_factor_revision.py',FACTOR_CODE_SHA),
                            (source/'FEP_ADAPTIVE_CALIBRATION_V1_REPORT.md',ADAPT_REPORT_SHA)):
            check('integrity','pinned '+str(path),identity(path)['sha256'] == digest)
        old_manifest = json.loads((ADAPT/'MANIFEST.json').read_text())
        unique = {e['path']:e for group in ('inputs','outputs','preserved') for e in old_manifest[group]}
        for e in unique.values():
            check('integrity','preserved '+e['path'],identity(Path(e['path'])) == e)
            preserved.append(e)
        small = [(source/name,name) for name in ('FEP_STOPPING_ATTRIBUTION_V1.md','check_fep_stopping_attribution.py',
                 'FEP_ADAPTIVE_CALIBRATION_V1.md','FEP_ADAPTIVE_CALIBRATION_V1_REPORT.md','check_fep_adaptive_calibration.py',
                 'FEP_FACTOR_REVISION_V1.md','check_fep_factor_revision.py')]
        small += [(ADAPT/'MANIFEST.json','adaptive_MANIFEST.json'),(ADAPT/'RESULTS.json','adaptive_RESULTS.json'),
                  (FIXED/'MANIFEST.json','fixed_MANIFEST.json'),(FIXED/'RESULTS.json','fixed_RESULTS.json')]
        for path,name in small:
            entry = identity(path)
            inputs.append(entry)
            shutil.copyfile(path,output/'inputs'/name)
            check('integrity','snapshot '+name,identity(output/'inputs'/name)['sha256'] == entry['sha256'])
        inputs += [identity(ADAPT/name) for name in ('BELLMAN.jsonl.gz','STOPPED.jsonl.gz')]
        write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,scope='post-result attribution under shared truth only',
              cap=CAP,H=H,truth=Q,pair_cost=F(1,1000),large_inputs_referenced_in_place=True,
              policy_optimization=False,successor_controller=False,display_tolerance=TOL,
              subjective_benefits='exact per history and exact range; no need to average heterogeneous-denominator fractions'))
        spec = importlib.util.spec_from_file_location('frozen_factor_reference',source/'check_fep_factor_revision.py')
        reference = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reference)
        qualification = qualify(reference)
        write(output/'QUALIFICATION.json',qualification)
        logline(f'Qualification passed: {qualification["checks"]} cumulative checks; {qualification["wall_seconds"]:.3f}s')
        stops,codes,records,raw_rows = load_saved()
        logline(f'Loaded sealed policies and shared stopped states: {len(stops[0])} edit, {len(stops[1])} average')
        targets = set(records)
        pred,prior_roots,prior_states = prior_completion(codes,targets,CAP,records,logline)
        actual,true_roots,true_states = truth_completion(codes,targets,CAP)
        check('scope','all true conditional completions extracted',set(actual) == targets)
        rows = aggregate(stops,codes,records,pred,actual,reference,output)
        adaptive = json.loads((output/'inputs/adaptive_RESULTS.json').read_text())
        fixed = json.loads((output/'inputs/fixed_RESULTS.json').read_text())['budgets']['64']['shared']['methods']
        fixed_rows = {}
        for d,name in enumerate(('edit','model_average')):
            old = fixed[name]
            check('saved totals','fixed raw completion',true_roots[d] == F(old['raw_loss']['exact']))
            check('saved totals','prior fixed completion',H*(prior_roots[d]+F(CAP,100000)) == F(adaptive['root_prior_predictions'][OLD_NAMES[d]]['fixed_cap_prior_value']['exact']))
            fixed_rows[NAMES[d]] = dict(raw_loss=true_roots[d],net_loss=true_roots[d]+F(CAP,100000),expected_calibrations=F(CAP))
        for s in (0,1):
            for d in (0,1):
                key = NAMES[s]+'_stop__'+NAMES[d]+'_deploy'
                row = rows[key]
                check('coupling','complete stopped stream recovers fixed law',row['completion_raw_loss'] == true_roots[d])
                check('coupling','net completion gap matches fixed comparison',row['net_completion_gain'] == row['net_loss']-fixed_rows[NAMES[d]]['net_loss'])
                if s == d:
                    old = adaptive['truths']['shared']['methods'][OLD_NAMES[s]]
                    for key_old,key_new in (('expected_calibrations','expected_calibrations'),('raw_loss','raw_loss'),
                                            ('net_loss','net_loss'),('wrong_probability','wrong_probability'),('ask_probability','ask_probability')):
                        check('saved totals','diagonal '+key_old,row[key_new] == F(old[key_old]['exact']))
                    if s == 0:
                        check('saved totals','join frequency',row['MAP_join_probability'] == F(old['terminal_MAP_join_probability']['exact']))
        ee,ea,ae,aa = (rows[key]['net_loss'] for key in ('edit_stop__edit_deploy','edit_stop__average_deploy','average_stop__edit_deploy','average_stop__average_deploy'))
        fe,fa = fixed_rows['edit']['net_loss'],fixed_rows['average']['net_loss']
        attribution = dict(primary_gap=ee-fe,matched_average_gap=ea-fa,
                           commitment_at_edit_stop=ee-ea,commitment_at_fixed=fe-fa,
                           commitment_interaction=(ee-ea)-(fe-fa),
                           diagonal_difference=ee-aa,
                           deployment_first=(ee-ea,ea-aa),stopping_first=(ee-ae,ae-aa),
                           matched_average_penalty_nonpositive=(ea-fa <= 0),
                           matched_averaging_penalty_persists=(ea-fa > 0))
        check('attribution','matched stopping and interaction identity',attribution['primary_gap'] == attribution['matched_average_gap']+attribution['commitment_interaction'])
        check('attribution','both substitution orders',sum(attribution['deployment_first']) == ee-aa == sum(attribution['stopping_first']))
        for entry in inputs+preserved:
            check('integrity','unchanged '+entry['path'],identity(Path(entry['path'])) == entry)
        summary = dict(checks=sum(COUNTS.values()),groups=dict(COUNTS),max_display_residual=MAX_ERROR,
                       prior_completion_states=prior_states,shared_completion_states=true_states,
                       source_stopped_rows=raw_rows,shared_stopped_states=dict(zip(NAMES,map(len,stops))),
                       audited_history_rows=2*sum(map(len,stops)),policy_optimizations=0,
                       sampled_trajectories=0,post_result_attribution=True,new_success_gate=False)
        write(output/'RESULTS.json',dict(summary=summary,crossed=rows,fixed_64=fixed_rows,
              attribution=attribution,prior_fixed_raw_loss=dict(zip(NAMES,prior_roots))))
        finished,wall,cpu_seconds = datetime.now(timezone.utc).isoformat(),perf_counter()-start,process_time()-cpu
        logline(f'COMPLETE: {summary["checks"]} checks; exact crossed/conditional identities; {wall:.3f}s wall')
        outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
        write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=finished,
              wall_seconds=wall,cpu_seconds=cpu_seconds,python=platform.python_version(),processes=1,
              inputs=inputs,outputs=outputs,preserved=preserved,summary=summary))
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(status='failed',inputs=inputs,preserved=preserved,
              checks=sum(COUNTS.values()),groups=dict(COUNTS),wall_seconds=perf_counter()-start))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
