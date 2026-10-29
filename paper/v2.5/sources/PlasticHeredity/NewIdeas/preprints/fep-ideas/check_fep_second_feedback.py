#!/usr/bin/env python3
"""Exact second-task retention with first acquisition and second action fixed."""
import argparse
from collections import namedtuple
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
import gzip
from hashlib import sha256
import importlib.util
from itertools import islice, product
import json
from math import prod
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter, process_time
import traceback

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-second-feedback-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-checking-attribution-v1/attempt-01'
ACTIVE = MOUNT/'fep-ideas/formal-checks/fep-active-verification-v1/attempt-01'
PREVIOUS_SHA = '657feb75ecca2ebf17b68ff58544247ec2071ff0649e8c165346289cd48cbd99'
REPORT_SHA = 'baf6af451a642a76412d9764aa8714fd5799aea47d4fab4237e3120073cdbaaa'
HELPER_SHA = '692e1cf60e6fd1709ab85f300250b47bdef796f6ba063198bd89c973e4b3a821'
ARMS = ('frozen','warnings','full')
COMPARISONS = ('full_minus_frozen','full_minus_warnings','warnings_minus_frozen')
PAIRS = ((2,0),(2,1),(1,0))
Program = namedtuple('Program','initial asks first_codes first_joins passive_codes scopes warning_codes warning_joins full_codes full_joins')
T,BASE,CAP = 98,400,64


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


assert sha256((SOURCE/'check_fep_active_verification.py').read_bytes()).hexdigest() == HELPER_SHA
A = module('frozen_active_verification',SOURCE/'check_fep_active_verification.py')
V,R = A.V,A.R
check,write,identity = A.check,A.write,A.identity
MULT = 4*68**2
SCALE,DEN = V.SCALE*MULT,V.DEN*MULT
BAD = tuple(tuple(int(a == 1) for a in d) for d in R.C.ACTS)
ASK = tuple(tuple(int(a == 2) for a in d) for d in R.C.ACTS)
UNITS = tuple(tuple(10*x+y for x,y in zip(b,a)) for b,a in zip(BAD,ASK))
SYMMETRIC = frozenset(code for code,d in enumerate(R.C.ACTS) if all(
    (d[g] == d[3-g] == 2) or (d[g] < 2 and d[3-g] == 1-d[g]) for g in (0,1)))


def third_kernel(z):
    tables = [[[None]*4 for _ in range(4)] for _ in (0,1)]
    for e in range(4):
        for f in range(e,4):
            check('likelihood','exchangeable second moment',all(z['g'][i][e][f] == z['g'][i][f][e] for i in (0,1)))
            vals = V.predict(R.add(R.add(z['c'],e),f),z['g'][0][e][f]*MULT,z['g'][1][e][f]*MULT)
            for i in (0,1):
                tables[i][e][f] = tables[i][f][e] = vals[i]
    return tuple(tuple(tuple(row) for row in table) for table in tables)


def make_planner(z,third):
    cache = {}
    def plan(s,decisions,force=None):
        asks = tuple(bool(decisions[g][2]) if force is None else bool(decisions[g][0] == 2 or force) for g in (0,1))
        first,joins,passive,scopes,wcodes,wjoins,fcodes,fjoins = [],[],[],[],[],[],[],[]
        def infer(one,two):
            key = (one,two)
            if key not in cache:
                vectors,weights = [],[]
                for i in (0,1):
                    vector = tuple(sum(third[i][e][f][h] for e in one for f in two) for h in range(4))
                    weight = MULT*sum(z['g'][i][e][f] for e in one for f in two)
                    check('posterior','two observations normalize',sum(vector) == weight)
                    vectors.append(vector)
                    weights.append(weight)
                codes,join = R.tables(*vectors,*weights)
                check('symmetry','second-feedback response symmetry',all(code in SYMMETRIC for code in codes))
                cache[key] = codes,join
            codes,join = cache[key]
            return codes[s],join
        for e in range(4):
            g = min(e,3-e)
            one = (e,) if asks[g] else (g,3-g)
            code = z['labels'][e][s] if asks[g] else z['warnings'][g][s]
            join = z['ljoins'][e] if asks[g] else z['wjoins'][g]
            first.append(code); joins.append(join); passive.append(z['warnings'][g][s]); scopes.append(one)
            for f in range(4):
                h = min(f,3-f)
                wc,wj = infer(one,(h,3-h))
                fc,fj = infer(one,(f,)) if ASK[code][f] else (wc,wj)
                check('retention','no unpurchased second label',ASK[code][f] or (fc == wc and fj == wj))
                wcodes.append(wc); wjoins.append(wj); fcodes.append(fc); fjoins.append(fj)
        return Program(z['initial'][s],asks,tuple(first),tuple(joins),tuple(passive),tuple(scopes),
                       tuple(wcodes),tuple(wjoins),tuple(fcodes),tuple(fjoins))
    return plan


def codes_at(program,e,f):
    j = 4*e+f
    return program.first_codes[e],program.warning_codes[j],program.full_codes[j]


def risk_parts(code,vector):
    return tuple(sum(x*y for x,y in zip(vector,units[code])) for units in (BAD,ASK))


def features(program,first,joint,third=None,physical_risks=None):
    out = dict(first=[0,0],second=[0,0],future=[[0,0] for _ in ARMS],
               changed=[0]*3,switched=[0]*3,label_changed=0)
    conditional = {scope:[0,0,0] for scope in program.scopes}
    for e in range(4):
        bought = program.asks[min(e,3-e)]
        out['first'][0] += first[e]*int(not bought and R.C.ACTS[program.initial][e] == 1)
        out['first'][1] += first[e]*int(bought)
        old = program.first_codes[e]
        for f in range(4):
            j,mass = 4*e+f,joint[e][f]
            out['second'][0] += mass*BAD[old][f]
            out['second'][1] += mass*ASK[old][f]
            codes = codes_at(program,e,f)
            joins = program.first_joins[e],program.warning_joins[j],program.full_joins[j]
            cache = {}
            for a,code in enumerate(codes):
                if code not in cache:
                    cache[code] = risk_parts(code,third[e][f]) if third is not None else tuple(mass*x for x in physical_risks[code])
                wrong,ask = cache[code]
                out['future'][a][0] += wrong
                out['future'][a][1] += ask
                out['changed'][a] += mass*int(code != old)
                out['switched'][a] += mass*int(joins[a] != joins[0])
                conditional[program.scopes[e]][a] += 10*wrong+ask
            out['label_changed'] += mass*int(codes[2] != codes[1])
    return out,conditional


def persistence(program,q):
    result = [0]*6  # base, still references, original report, flipped report, wrong change, reference change
    for e in range(4):
        if not program.asks[min(e,3-e)] or R.C.ACTS[program.initial][e] == 2:
            continue
        old,once = program.passive_codes[e],program.first_codes[e]
        eligible = []
        for t in range(4):
            h = min(t,3-t)
            act = R.C.ACTS[old][h]
            err = q[3-h] if act == 0 else q[h]
            if ASK[once][t] and R.C.ACTS[old][t] != 2 and 10*err < q[h]+q[3-h]:
                eligible.append(t)
        for f in range(4):
            new = program.full_codes[4*e+f]
            for t in eligible:
                mass = q[e]*q[f]*q[t]
                result[0] += mass
                act = R.C.ACTS[new][t]
                category = 1 if act == 2 else 2 if act == R.C.ACTS[old][t] else 3
                result[category] += mass
                result[4] += mass*BAD[new][t]
                result[5] += mass*(ASK[new][t]-1)
    check('persistence','reference persistence partition',result[0] == sum(result[1:4]))
    check('persistence','removed references match reports',result[5] == -sum(result[2:4]))
    return result


PHYSICAL_RISKS = {label:tuple(risk_parts(code,q) for code in range(81)) for label,q in R.TRUTHS.items()}


@lru_cache(maxsize=2048)
def physical_features(program):
    result = {}
    for label,q in R.TRUTHS.items():
        joint = tuple(tuple(x*y for y in q) for x in q)
        feat,_ = features(program,q,joint,physical_risks=PHYSICAL_RISKS[label])
        result[label] = feat,persistence(program,q)
    return result


def fresh():
    return dict(mass=0,count=0,first=[0,0],second=[0,0],future=[[0,0] for _ in ARMS],
                changed=[0]*3,switched=[0]*3,label_changed=0,persistence=[0]*6)


def accumulate(stat,feat,weight,mass,n,diagnostic=None):
    stat['mass'] += mass
    stat['count'] += n*mass
    stat['label_changed'] += weight*feat['label_changed']
    for key in ('first','second','changed','switched'):
        for j,x in enumerate(feat[key]):
            stat[key][j] += weight*x
    for a in range(3):
        for j in range(2):
            stat['future'][a][j] += weight*feat['future'][a][j]
    if diagnostic is not None:
        for j,x in enumerate(diagnostic):
            stat['persistence'][j] += weight*x


def summarize(stat,mass_den,first_den,second_den,future_den):
    check('mass','stopping distribution normalized',stat['mass'] == mass_den)
    n = F(stat['count'],mass_den)
    first = tuple(F(x,first_den) for x in stat['first'])
    second = tuple(F(x,second_den) for x in stat['second'])
    out = dict(expected_calibrations=n,calibration_cost_per_task=n/100000,
        first_wrong_probability=first[0],first_reference_probability=first[1],
        second_wrong_probability=second[0],second_reference_probability=second[1],
        first_raw_risk=first[0]+first[1]/10,second_raw_risk=second[0]+second[1]/10,
        second_label_changes_warnings_table_probability=F(stat['label_changed'],second_den),arms={})
    for a,name in enumerate(ARMS):
        wrong,ask = (F(x,future_den) for x in stat['future'][a])
        check('probability','valid later event probabilities',0 <= wrong+ask <= 1)
        raw = wrong+ask/10
        out['arms'][name] = dict(later_wrong_probability=wrong,later_reference_probability=ask,later_raw_risk=raw,
            episode_expected_wrong_reports=first[0]+second[0]+T*wrong,
            episode_expected_references=first[1]+second[1]+T*ask,
            response_table_change_probability=F(stat['changed'][a],second_den),
            diagnostic_MAP_switch_probability=F(stat['switched'][a],second_den),
            net_loss=(out['first_raw_risk']+out['second_raw_risk']+T*raw)/100+n/100000)
    check('bridge','frozen task two equals later risk',out['arms']['frozen']['later_raw_risk'] == out['second_raw_risk'])
    out['contrasts'],out['decompositions'] = {},{}
    for name,(a,b) in zip(COMPARISONS,PAIRS):
        new,old = out['arms'][ARMS[a]],out['arms'][ARMS[b]]
        delta = new['net_loss']-old['net_loss']
        parts = dict(later_wrong_loss=T*(new['later_wrong_probability']-old['later_wrong_probability'])/100,
                     later_reference_expense=T*(new['later_reference_probability']-old['later_reference_probability'])/1000)
        check('cost','first two tasks cancel',sum(parts.values()) == delta)
        out['contrasts'][name],out['decompositions'][name] = delta,parts
    d = [F(x,future_den) for x in stat['persistence']]
    out['costly_caution'] = dict(original_probability=d[0],still_reference_probability=d[1],
        original_report_probability=d[2],flipped_report_probability=d[3],wrong_probability_change=d[4],reference_probability_change=d[5],
        later_wrong_loss=T*d[4]/100,later_reference_expense=T*d[5]/1000,later_net_change=T*(10*d[4]+d[5])/1000)
    return out


class Collector:
    def __init__(self,ledger=None):
        self.prior = [fresh(),fresh()]
        self.actual = {label:[fresh(),fresh()] for label in R.TRUTHS}
        self.powers = {label:[[x**n for n in range(65)] for x in q] for label,q in R.TRUTHS.items()}
        self.tail = [BASE**n for n in range(65)]
        self.controls = [dict(first_observation_branches=0,violations=[0]*3,masses=[0]*3) for _ in (0,1)]
        self.rows,self.stopped,self.ledger = 0,0,ledger

    def row(self,z,k,decisions):
        n,c = sum(z['c']),z['c']
        third = third_kernel(z)
        mix3 = tuple(tuple(tuple(9*x+y for x,y in zip(a,b)) for a,b in zip(row0,row1))
                     for row0,row1 in zip(*third))
        first = tuple(x*MULT for x in z['mix'])
        joint = tuple(tuple(x*MULT for x in row) for row in z['joint'])
        planner = make_planner(z,third)
        programs = []
        for s in (0,1):
            if not k[s]:
                programs.append(None)
                continue
            program = planner(s,decisions[s]); programs.append(program)
            feat,conditional = features(program,first,joint,mix3)
            for scope,costs in conditional.items():
                self.controls[s]['first_observation_branches'] += 1
                mass = k[s]*sum(first[e] for e in scope)
                for j,(a,b) in enumerate(PAIRS):
                    if s == 1:
                        check('prior control','averaged conditional refinement',costs[a] <= costs[b])
                    if costs[a] > costs[b]:
                        self.controls[s]['violations'][j] += 1
                        self.controls[s]['masses'][j] += mass
            accumulate(self.prior[s],feat,k[s],k[s]*sum(first),n)
            physical = physical_features(program)
            for label,q in R.TRUTHS.items():
                mass = k[s]*prod(self.powers[label][e][c[e]] for e in range(4))*self.tail[64-n]
                if mass:
                    feat,diag = physical[label]
                    accumulate(self.actual[label][s],feat,mass,mass,n,diag)
            self.stopped += 1
        if self.ledger is not None:
            self.ledger.write(json.dumps([n,*c,[str(x) for x in k],programs],separators=(',',':'))+'\n')
        self.rows += 1

    def finish(self):
        prior = {name:summarize(self.prior[s],DEN,DEN,DEN,DEN) for s,name in enumerate(V.NAMES)}
        d = BASE**CAP
        actual = {label:{name:summarize(stats[s],d,d*BASE,d*BASE**2,d*BASE**3) for s,name in enumerate(V.NAMES)}
                  for label,stats in self.actual.items()}
        controls = {name:dict(first_observation_branches=self.controls[s]['first_observation_branches'],
            comparisons={key:dict(worse_branches=self.controls[s]['violations'][j],
                worse_prior_probability=F(self.controls[s]['masses'][j],DEN)) for j,key in enumerate(COMPARISONS)})
            for s,name in enumerate(V.NAMES)}
        return prior,actual,controls


def direct(program,first,joint,third):
    a,b,c = [0,0],[0,0],[[0,0] for _ in ARMS]
    for w,e in product((0,1),range(4)):
        y = e if w == 0 else 3-e
        bought = program.asks[min(y,3-y)]
        a[0] += first[e]*int(not bought and R.C.ACTS[program.initial][y] != w)
        a[1] += first[e]*int(bought)
        for v,f in product((0,1),range(4)):
            obs = f if v == 0 else 3-f
            act = R.C.ACTS[program.first_codes[e]][obs]
            b[0] += joint[e][f]*int(act != 2 and act != v)
            b[1] += joint[e][f]*int(act == 2)
            for u,h in product((0,1),range(4)):
                obs3 = h if u == 0 else 3-h
                for arm,code in enumerate(codes_at(program,e,f)):
                    action = R.C.ACTS[code][obs3]
                    c[arm][0] += third[e][f][h]*int(action != 2 and action != u)
                    c[arm][1] += third[e][f][h]*int(action == 2)
    return a,b,c


def qualify():
    started = perf_counter()
    ref = module('independent_factor_reference',SOURCE/'check_fep_factor_revision.py')
    states,partial,unchecked = 0,0,0
    for n in range(5):
        for c in ref.histograms(n):
            z = V.kernel(c); third = third_kernel(z)
            evidence = {}
            def ev(e,f,h=None):
                counts = R.add(R.add(c,e),f)
                if h is not None:
                    counts = R.add(counts,h)
                if counts not in evidence:
                    evidence[counts] = ref.evidence(counts)
                return evidence[counts]
            for e,f,h in product(range(4),repeat=3):
                for i in (0,1):
                    check('qualification','independent third evidence moment',F(third[i][e][f][h],SCALE) == ev(e,f,h)[i])
            p = tuple(x*MULT for x in z['mix'])
            j = tuple(tuple(x*MULT for x in row) for row in z['joint'])
            t = tuple(tuple(tuple(9*x+y for x,y in zip(a,b)) for a,b in zip(r0,r1)) for r0,r1 in zip(*third))
            planner = make_planner(z,third)
            for s in (0,1):
                ds = [[V.branch(z,s,g)['b'],0,int(V.branch(z,s,g)['future']),0] for g in (0,1)]
                for force in (None,False,True):
                    program = planner(s,ds,force)
                    for e,f in product(range(4),repeat=2):
                        one = program.scopes[e]; g = min(f,3-f)
                        for a in (1,2):
                            two = (f,) if a == 2 and ASK[program.first_codes[e]][f] else (g,3-g)
                            partial += int(len(one) == len(two) == 2)
                            weights = [sum(ev(e0,f0)[i] for e0 in one for f0 in two) for i in (0,1)]
                            vec = [tuple(sum(ev(e0,f0,h)[i] for e0 in one for f0 in two) for h in range(4)) for i in (0,1)]
                            joint_model = int(weights[1] > 9*weights[0])
                            pred = vec[joint_model] if s == 0 else tuple(9*x+y for x,y in zip(*vec))
                            expected = ref.policy(pred)
                            code = codes_at(program,e,f)[a]
                            check('qualification','independent two-observation inference',R.C.ACTS[code] == expected)
                        if not ASK[program.first_codes[e]][f]:
                            unchecked += 1
                            check('qualification','no second label no full/warnings difference',program.full_codes[4*e+f] == program.warning_codes[4*e+f])
                    feat,conditional = features(program,p,j,t)
                    if s == 1:
                        check('qualification','conditional Bayes refinement',all(row[2] <= row[1] <= row[0] for row in conditional.values()))
                    laws = [(p,j,t,None)] + [(q,tuple(tuple(x*y for y in q) for x in q),
                        tuple(tuple(tuple(x*y*z for z in q) for y in q) for x in q),PHYSICAL_RISKS[label]) for label,q in R.TRUTHS.items()]
                    for first,joint,triple,risks in laws:
                        feat,_ = features(program,first,joint,triple if risks is None else None,risks)
                        da,db,dc = direct(program,first,joint,triple)
                        check('qualification','three fair targets enumerated independently',da == [2*x for x in feat['first']] and db == [4*x for x in feat['second']] and dc == [[8*x for x in row] for row in feat['future']])
            states += 1
    check('qualification','two partial observations exercised',partial > 0)
    check('qualification','unchecked second answers exercised',unchecked > 0)
    for v,want in (((10,1,1,1),0),((9,1,1,1),2),((8,1,1,1),2)):
        check('qualification','original reference threshold including tie',R.C.ACTS[R.program(v)][0] == want)
    check('qualification','MAP structural tie selects independence',R.tables((10,1,1,1),(9,9,9,90),13,117)[1] == 0)
    elapsed = perf_counter()-started
    physical_features.cache_clear()
    begin = perf_counter(); collector = Collector()
    for z,k,ds in islice(A.read_rows(),512):
        collector.row(z,k,ds)
    bench = perf_counter()-begin
    forecast = 90+4*bench*136499/512
    return dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),small_count_states=states,
        two_partial_observation_cases=partial,unchecked_second_cases=unchecked,qualification_seconds=elapsed,
        benchmark_rows=512,benchmark_seconds=bench,forecast_main_seconds=forecast,requires_detached=forecast > 600,
        forecast_rule='90 seconds I/O plus four times full-workload 512-row rate')


def bridge(row,old):
    for key in ('expected_calibrations','calibration_cost_per_task'):
        check('bridge','unchanged '+key,row[key] == F(old[key]['exact']))
    for key in ('first_wrong_probability','first_reference_probability','first_raw_risk'):
        check('bridge','same first action cost '+key,row[key] == F(old['arms']['future'][key]['exact']))
    for event in ('wrong','reference'):
        expected = F(old['arms']['future']['future_'+event+'_probability']['exact'])
        check('bridge','same second '+event,row['second_'+event+'_probability'] == expected)
        check('bridge','same frozen later '+event,row['arms']['frozen']['later_'+event+'_probability'] == expected)
    for key in ('net_loss','episode_expected_wrong_reports','episode_expected_references'):
        check('bridge','same frozen full cost '+key,row['arms']['frozen'][key] == F(old['arms']['future'][key]['exact']))
    row['no_update_net_loss'] = F(old['no_update_net_loss']['exact'])
    row['always_reference_net_loss'] = F(1,10)
    row['contrasts']['full_minus_no_update'] = row['arms']['full']['net_loss']-row['no_update_net_loss']


def persistence_fraction(row):
    d = row['costly_caution']; den = d['original_probability']
    d['released_fraction'] = (d['original_report_probability']+d['flipped_report_probability'])/den if den else None


def prepare(output,logline):
    check('integrity','previous manifest',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report',identity(SOURCE/'FEP_CHECKING_ATTRIBUTION_V1_REPORT.md')['sha256'] == REPORT_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({x['path']:x for group in ('inputs','outputs','preserved') for x in old[group]}.values())
    V.verify(preserved)
    (output/'inputs').mkdir()
    files = [(SOURCE/name,name) for name in ('FEP_SECOND_FEEDBACK_V1.md','check_fep_second_feedback.py',
        'FEP_CHECKING_ATTRIBUTION_V1.md','FEP_CHECKING_ATTRIBUTION_V1_REPORT.md','check_fep_checking_attribution.py',
        'check_fep_active_verification.py','check_fep_verification_value.py','check_fep_reference_feedback.py',
        'check_fep_stopping_attribution.py','check_fep_factor_revision.py')]
    files += [(PREVIOUS/'MANIFEST.json','attribution_MANIFEST.json'),(ACTIVE/'RESULTS.json','active_RESULTS.json')]
    inputs = []
    for p,name in files:
        inputs.append(identity(p)); shutil.copyfile(p,output/'inputs'/name)
        check('integrity','snapshot '+name,identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    inputs += [identity(V.LEDGER),identity(A.DECISIONS),identity(PREVIOUS/'RESULTS.json')]
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,arms=ARMS,controllers=V.NAMES,
        total_tasks=100,retention_tasks=[1,2],fixed_later_tasks=T,truths=R.TRUTHS,truth_denominator=BASE,
        known_panel=True,old_shared_excluded=True,program_fields=Program._fields,
        ledger_fields=['n','c00','c01','c10','c11','stopped_multiplicities','programs_edit_average'],
        primary_criteria=['full mean < frozen mean','full mean < warnings mean','full mean < original no-update mean'],
        acquisition_reoptimizations=0,prior_or_price_tuning=0,large_inputs_read_in_place=True))
    q = qualify(); write(output/'QUALIFICATION.json',q)
    logline(f'PREPARED: {q["checks"]} checks; qualification {q["qualification_seconds"]:.3f}s; main forecast {q["forecast_main_seconds"]:.1f}s; detached={q["requires_detached"]}')


def execute(output,logline):
    prep = json.loads((output/'PREPARATION.json').read_text())
    qual = json.loads((output/'QUALIFICATION.json').read_text())
    for key,n in qual['groups'].items():
        R.C.COUNTS[key] += n
    V.verify(prep['inputs']+prep['preserved'])
    check('scope','first execution',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    with gzip.open(output/'SECOND_TASK_TABLES.jsonl.gz','wt') as ledger:
        collector = Collector(ledger)
        for z,k,ds in A.read_rows():
            collector.row(z,k,ds)
            if collector.rows % 40000 == 0:
                logline(f'Integrated {collector.rows} frozen count rows with second feedback')
    check('scope','all stopped rows',collector.rows == 136499 and collector.stopped == 259142)
    prior,actual,controls = collector.finish()
    old = json.loads((ACTIVE/'RESULTS.json').read_text())
    attr = json.loads((PREVIOUS/'RESULTS.json').read_text())
    aggregate = {}
    for name in V.NAMES:
        bridge(prior[name],old['prior'][name])
        for label in R.TRUTHS:
            row = actual[label][name]; bridge(row,old['truths'][label][name])
            check('bridge','same physically costly caution events',row['costly_caution']['original_probability'] == F(attr['truths'][label][name]['future_total']['costly_reference_entry_probability']['exact']))
        rows = [actual[label][name] for label in R.PANEL]
        avg = A.average(rows)
        avg['gates'] = {f'improves_{other}':avg['contrasts']['full_minus_'+other] < 0 for other in ('frozen','warnings','no_update')}
        avg['improved_counts'] = {other:sum(row['contrasts']['full_minus_'+other] < 0 for row in rows) for other in ('frozen','warnings','no_update')}
        avg['uniform_no_worse_than_frozen'] = all(row['contrasts']['full_minus_frozen'] <= 0 for row in rows)
        avg['below_always_reference_counts'] = {arm:sum(row['arms'][arm]['net_loss'] < F(1,10) for row in rows) for arm in ARMS}
        avg['below_always_reference_counts']['no_update'] = sum(row['no_update_net_loss'] < F(1,10) for row in rows)
        persistence_fraction(avg); aggregate[name] = avg
        for label in R.TRUTHS:
            persistence_fraction(actual[label][name])
    check('prior control','averaged integrated refinement',prior['average']['arms']['full']['net_loss'] <= prior['average']['arms']['warnings']['net_loss'] <= prior['average']['arms']['frozen']['net_loss'])
    write(output/'PRIOR_CONTROL.json',dict(outcomes=prior,conditional=controls))
    for label,rows in actual.items():
        write(output/(label+'.json'),dict(Q=[F(x,BASE) for x in R.TRUTHS[label]],methods=rows))
    V.verify(prep['inputs']+prep['preserved'])
    summary = dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),count_rows=collector.rows,
        stopped_controller_rows=collector.stopped,panel_environments=9,excluded_shared_diagnostics=1,
        feedback_opportunities=2,acquisition_reoptimizations=0,prices_or_priors_tuned=0,sampled_trajectories=0,
        primary_gates=aggregate['edit']['gates'],physical_program_cache=physical_features.cache_info()._asdict())
    write(output/'RESULTS.json',dict(summary=summary,prior=prior,conditional_controls=controls,truths=actual,equal_panel_aggregate=aggregate))
    wall = perf_counter()-start
    logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s; primary gates {summary["primary_gates"]}')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        main_wall_seconds=wall,main_cpu_seconds=process_time()-cpu,python=platform.python_version(),processes=1,
        inputs=prep['inputs'],outputs=outputs,preserved=prep['preserved'],summary=summary))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('prepare','execute'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); output = args.output
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    if args.phase == 'prepare':
        output.mkdir(parents=True,exist_ok=False)
    elif not (output/'QUALIFICATION.json').exists() or (output/'FAILURE.json').exists():
        raise RuntimeError('Qualified, unfailed record required')
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; second-task retention')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
