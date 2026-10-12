#!/usr/bin/env python3
"""One matched deployment-feedback opportunity; exact finite integration."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
import importlib.util
from itertools import product
import json
from math import comb, factorial, fsum, log, prod
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter, process_time
import traceback

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-reference-feedback-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-forecast-validation-v1/attempt-01'
ATTRIBUTION = MOUNT/'fep-ideas/formal-checks/fep-stopping-attribution-v1/attempt-01'
PREVIOUS_SHA = '88410f24829e4230253d1f245f56d3bbf7638592d9c47fe36d57860186b159ee'
REPORT_SHA = '34bc28f453c83601563714f0bec2e6e80a8c6a21768e3b9199489a9bc02cbca7'
HELPER_SHA = '18f0f15f1f89bfd2c98f8aa8601f52264ef4eeb17f9c19e01733aa90aedb96bd'
FACTOR_SHA = '208835070d8032dfceb6fa05bde2d63c36b95013eb165531387e91aa5384d880'
CAP, BASE, H = 64,400,100
NAMES, ARMS = ('edit','average'),('none','warnings','full')
PANEL = {'a05_rho0':(342,38,18,2),'a05_rho5':(351,29,9,11),'a05_rho1':(360,20,0,20),
         'a15_rho0':(238,102,42,18),'a15_rho5':(259,81,21,39),'a15_rho1':(280,60,0,60),
         'a25_rho0':(150,150,50,50),'a25_rho5':(175,125,25,75),'a25_rho1':(200,100,0,100)}
TRUTHS = dict(PANEL,old_shared_diagnostic=(320,40,0,40))
FACT = [factorial(n) for n in range(2*(CAP+2)+1)]
BIN3 = [comb(n,3) if n >= 3 else 0 for n in range(CAP+7)]


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


assert sha256((SOURCE/'check_fep_stopping_attribution.py').read_bytes()).hexdigest() == HELPER_SHA
C = module('frozen_finite_helpers',SOURCE/'check_fep_stopping_attribution.py')
check,close,identity,write = C.check,C.close,C.identity,C.write


def counts(n):
    for a in range(n+1):
        for b in range(n-a+1):
            for c in range(n-a-b+1):
                yield (a,b,c,n-a-b-c)


def ix(n,a,b,c):
    return BIN3[n+3]-BIN3[n-a+3]+b*(n-a+1)-b*(b-1)//2+c


def add(c,e):
    return tuple(x+int(e == t) for t,x in enumerate(c))


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
    check('likelihood','common denominator exact',r0 == r1 == 0)
    return w0,w1


def program(v):
    return sum(((0 if v[y] > v[3-y] else 1)
        if 10*min(v[y],v[3-y]) < v[y]+v[3-y] else 2)*3**y for y in range(4))


def tables(v0,v1,w0,w1):
    joined = w1 > 9*w0
    return (program(v1 if joined else v0),program(tuple(9*x+y for x,y in zip(v0,v1)))),int(joined)


def empty_stops(cap):
    return [[[0]*comb(n+3,3) for n in range(cap+1)] for _ in (0,1)]


def load_stops():
    stops = empty_stops(CAP)
    saved = [bytearray([255])*(2*comb(n+3,3)) for n in range(CAP+1)]
    rows = 0
    with gzip.open(PREVIOUS/'STOPPED_FORECASTS.jsonl.gz','rt') as stream:
        for line in stream:
            row = json.loads(line)
            s,n,c,k,code = row[0],row[1],tuple(row[2:6]),int(row[6]),row[7]
            i = ix(n,*c[:3])
            check('saved stops','valid unique path multiplicity',s in (0,1) and 0 <= n <= CAP and sum(c) == n and k > 0 and stops[s][n][i] == 0)
            stops[s][n][i],saved[n][2*i+s] = k,code
            rows += 1
    check('saved stops','complete stopped ledger',rows == 259142)
    return stops,saved


def features(initial,joined,warnings,warning_joins,labels,label_joins,first,joint):
    result = dict(first=0,wrong=0,ask=0,pairs=[0]*4,revealed=[0]*4,
        future=[0]*3,changed=[0]*3,switched=[0]*3,label_changed=0)
    cache = {}
    for e in range(4):
        for w in (0,1):
            y = e if w == 0 else 3-e
            g,act = min(y,3-y),C.ACTS[initial][y]
            bought = act == 2
            outcome_codes = (initial,warnings[g],labels[e] if bought else warnings[g])
            outcome_joins = (joined,warning_joins[g],label_joins[e] if bought else warning_joins[g])
            result['pairs'][e] += first[e]
            result['wrong'] += first[e]*int(not bought and act != w)
            result['ask'] += first[e]*int(bought)
            result['revealed'][e] += first[e]*int(bought)
            result['label_changed'] += first[e]*int(bought and labels[e] != warnings[g])
            for a,code in enumerate(outcome_codes):
                key = (e,code)
                if key not in cache:
                    cache[key] = sum(p*u for p,u in zip(joint[e],C.UNITS[code]))
                result['future'][a] += cache[key]
                result['changed'][a] += first[e]*int(code != initial)
                result['switched'][a] += first[e]*int(outcome_joins[a] != joined)
            if not bought:
                check('retention','unpurchased label not used',outcome_codes[2] == outcome_codes[1])
    result['first'] = 10*result['wrong']+result['ask']
    return result


def fresh_stats():
    return dict(mass=0,count=0,first=0,wrong=0,ask=0,pairs=[0]*4,revealed=[0]*4,
        future=[0]*3,changed=[0]*3,switched=[0]*3,label_changed=0,
        conditional_worse_counts=[0,0],conditional_worse_mass=[0,0])


def accumulate(stat,feat,weight,mass,n,prior=False):
    stat['mass'] += mass
    stat['count'] += n*mass
    for key in ('first','wrong','ask','label_changed'):
        stat[key] += weight*feat[key]
    for key in ('pairs','revealed','future','changed','switched'):
        for i,x in enumerate(feat[key]):
            stat[key][i] += weight*x
    if prior:
        for i,other in enumerate((0,1)):
            if feat['future'][2] > feat['future'][other]:
                stat['conditional_worse_counts'][i] += 1
                stat['conditional_worse_mass'][i] += mass


class Collector:
    def __init__(self,cap,truths,ledger=None):
        self.cap,self.truths,self.ledger = cap,truths,ledger
        self.scale = 4**(cap+2)*FACT[cap+3]**2
        self.prior = [fresh_stats(),fresh_stats()]
        self.actual = {label:[fresh_stats(),fresh_stats()] for label in truths}
        self.powers = {label:[[x**n for n in range(cap+1)] for x in q] for label,q in truths.items()}
        self.tail = [BASE**n for n in range(cap+1)]
        self.caches = {label:{} for label in truths}
        self.rows,self.stopped_rows = 0,0

    def collect(self,c,kernel,k,pred0,pred1,grand0,grand1):
        n = sum(c)
        initial,joined,warnings,warning_joins,labels,label_joins = kernel
        mix = tuple(9*x+y for x,y in zip(pred0,pred1))
        w = sum(mix)
        joint = tuple(tuple(9*x+y for x,y in zip(row0,row1)) for row0,row1 in zip(grand0,grand1))
        for e in range(4):
            check('posterior','two-step marginal evidence',sum(joint[e]) == mix[e])
        if self.ledger is not None:
            self.ledger.write(json.dumps([n,*c,[str(x) for x in k],initial,joined,warnings,warning_joins,labels,label_joins],separators=(',',':'))+'\n')
        for s in (0,1):
            if not k[s]:
                continue
            args = (initial[s],joined,tuple(x[s] for x in warnings),warning_joins,
                    tuple(x[s] for x in labels),label_joins)
            feat = features(*args,mix,joint)
            check('prior law','no-update future risk',feat['future'][0] == 2*feat['first'])
            if s == 1:
                check('prior dominance','Bayes averaged information refinement',feat['future'][2] <= feat['future'][1] <= feat['future'][0])
            accumulate(self.prior[s],feat,k[s],k[s]*w,n,True)
            for label,q in self.truths.items():
                p = self.powers[label]
                mass = k[s]*prod(p[e][c[e]] for e in range(4))*self.tail[self.cap-n]
                if not mass:
                    continue
                cache = self.caches[label]
                if args not in cache:
                    cache[args] = features(*args,q,tuple(tuple(x*y for y in q) for x in q))
                    check('true law','no-update future risk',cache[args]['future'][0] == 2*BASE*cache[args]['first'])
                accumulate(self.actual[label][s],cache[args],mass,mass,n)
            self.stopped_rows += 1
        self.rows += 1

    def finish(self):
        prior_den = 10*self.scale
        prior = {name:summarize(self.prior[s],prior_den,20*prior_den,40*prior_den,2*prior_den,
                              (F(1,4),)*4,True) for s,name in enumerate(NAMES)}
        actual = {}
        d = BASE**self.cap
        for label,q in self.truths.items():
            actual[label] = {name:summarize(self.actual[label][s],d,20*BASE*d,40*BASE**2*d,2*BASE*d,
                                           tuple(F(x,BASE) for x in q),False) for s,name in enumerate(NAMES)}
        return prior,actual


def summarize(stat,den,first_den,future_den,event_den,q,prior):
    check('mass','stopped law normalized',stat['mass'] == den)
    pairs = [F(x,event_den) for x in stat['pairs']]
    check('mass','first error law preserved',tuple(pairs) == q)
    check('cost','first-task physical accounting',stat['first'] == 10*stat['wrong']+stat['ask'] and sum(stat['revealed']) == stat['ask'])
    first = F(stat['first'],first_den)
    charge = F(stat['count'],100000*den)
    arms = {}
    for a,name in enumerate(ARMS):
        future = F(stat['future'][a],future_den)
        arms[name] = dict(future_raw_risk=future,net_loss=(first+99*future)/100+charge,
            response_table_change_probability=F(stat['changed'][a],event_den),
            diagnostic_MAP_structure_switch_probability=F(stat['switched'][a],event_den))
    check('cost','no-update bridge',arms['none']['net_loss'] == first+charge)
    return dict(expected_calibrations=F(stat['count'],den),calibration_cost_per_task=charge,
        first_raw_risk=first,first_wrong_probability=F(stat['wrong'],event_den),
        first_reference_probability=F(stat['ask'],event_den),first_error_probabilities=pairs,
        revealed_error_probabilities=[F(x,event_den) for x in stat['revealed']],
        common_error_reference_fraction=F(stat['revealed'][3],stat['pairs'][3]) if stat['pairs'][3] else None,
        additional_label_changes_table_probability=F(stat['label_changed'],event_den),arms=arms,
        full_minus_none=arms['full']['net_loss']-arms['none']['net_loss'],
        full_minus_warnings=arms['full']['net_loss']-arms['warnings']['net_loss'],
        warnings_minus_none=arms['warnings']['net_loss']-arms['none']['net_loss'],
        conditional_full_worse_counts=stat['conditional_worse_counts'] if prior else None,
        conditional_full_worse_prior_mass=[F(x,den) for x in stat['conditional_worse_mass']] if prior else None)


def build(stops,cap,collector,saved=None,logline=lambda s:None,extra=None):
    scale = collector.scale
    top = [weights(c,scale) for c in counts(cap+2)]
    next0,next1 = [x[0] for x in top],[x[1] for x in top]
    grand0,grand1,next_codes,next_joins = None,None,None,None
    states = 0
    for n in range(cap+1,-1,-1):
        length = comb(n+3,3)
        current0,current1 = [0]*length,[0]*length
        codes,joins = bytearray(2*length),bytearray(length)
        for i,c in enumerate(counts(n)):
            child = children(n,c)
            pred0,pred1 = tuple(next0[t] for t in child),tuple(next1[t] for t in child)
            w0,w1 = sum(pred0),sum(pred1)
            current0[i],current1[i] = w0,w1
            initial,joined = tables(pred0,pred1,w0,w1)
            codes[2*i],codes[2*i+1],joins[i] = initial[0],initial[1],joined
            k = (stops[0][n][i],stops[1][n][i]) if n <= cap else (0,0)
            if any(k):
                indices = [children(n+1,add(c,e)) for e in range(4)]
                matrix0 = tuple(tuple(grand0[t] for t in row) for row in indices)
                matrix1 = tuple(tuple(grand1[t] for t in row) for row in indices)
                warnings,warning_joins = [],[]
                for g in (0,1):
                    v0 = tuple(x+y for x,y in zip(matrix0[g],matrix0[3-g]))
                    v1 = tuple(x+y for x,y in zip(matrix1[g],matrix1[3-g]))
                    check('posterior','coarsened likelihood normalizes',sum(v0) == pred0[g]+pred0[3-g] and sum(v1) == pred1[g]+pred1[3-g])
                    code,join = tables(v0,v1,pred0[g]+pred0[3-g],pred1[g]+pred1[3-g])
                    warnings.append(code)
                    warning_joins.append(join)
                labels = tuple((next_codes[2*t],next_codes[2*t+1]) for t in child)
                label_joins = tuple(next_joins[t] for t in child)
                kernel = (initial,joined,tuple(warnings),tuple(warning_joins),labels,label_joins)
                if saved is not None:
                    for s in (0,1):
                        if k[s]:
                            check('saved stops','same initial deployment',initial[s] == saved[n][2*i+s])
                collector.collect(c,kernel,k,pred0,pred1,matrix0,matrix1)
                if extra is not None:
                    extra(c,kernel,k,pred0,pred1,matrix0,matrix1,scale)
            states += 1
        grand0,grand1 = next0,next1
        next0,next1,next_codes,next_joins = current0,current1,codes,joins
        if n == cap+1 or n % 16 == 0:
            logline(f'Exact posterior tables through n={n}; {states} count states')
    check('scope','all inference states',states == comb(cap+5,4))
    return states


def toy_stops(reference,cap,full=False):
    stops,reach = empty_stops(cap),empty_stops(cap)
    for s in (0,1):
        reach[s][0][0] = 1
    for n in range(cap+1):
        for i,c in enumerate(counts(n)):
            for s in (0,1):
                go = n < cap and (full or n == 0 or
                    (s == 0 and n == 1 and c[0] == 0) or
                    (s == 0 and n == 2 and c[3] > 0) or
                    (s == 1 and n == 1 and c[3] == 0))
                if go:
                    for t in children(n,c):
                        reach[s][n+1][t] += reach[s][n][i]
                else:
                    stops[s][n][i] = reach[s][n][i]
    return stops


def qualify(reference):
    start = perf_counter()
    cap = 3
    stops = toy_stops(reference,cap)
    coll = Collector(cap,TRUTHS)
    direct = {label:[[F(0)]*3 for _ in (0,1)] for label in ('prior',*TRUTHS)}
    def ev(c):
        x = reference.evidence(c)
        return (9*x[0]+x[1])/10
    def direct_codes(v0,v1,m0,m1):
        joined = m1 > 9*m0
        vm = tuple(9*x+y for x,y in zip(v0,v1))
        return tuple(sum(a*3**y for y,a in enumerate(reference.policy(v))) for v in (v1 if joined else v0,vm)),int(joined)
    def extra(c,kernel,k,p0,p1,g0,g1,scale):
        initial,joined,warn,wjoin,labels,ljoin = kernel
        n = sum(c)
        before = reference.fit(c)
        for s,j in enumerate((1,3)):
            check('qualification','initial frozen predictions',C.ACTS[initial[s]] == reference.policy(before['vectors'][j]))
        old = reference.evidence(c)
        for e in range(4):
            after = reference.fit(add(c,e))
            for s,j in enumerate((1,3)):
                check('qualification','labeled frozen predictions',C.ACTS[labels[e][s]] == reference.policy(after['vectors'][j]))
            for i in (0,1):
                check('qualification','direct evidence',F((p0,p1)[i][e],scale) == reference.evidence(add(c,e))[i])
        for g in (0,1):
            m = tuple(sum(reference.evidence(add(c,e))[i] for e in (g,3-g)) for i in (0,1))
            v = []
            for i,j in ((0,0),(1,2)):
                v.append(tuple(sum(reference.evidence(add(c,e))[i]*F(reference.fit(add(c,e))['vectors'][j][f],sum(reference.fit(add(c,e))['vectors'][j])) for e in (g,3-g)) for f in range(4)))
            expected,j = direct_codes(v[0],v[1],m[0],m[1])
            check('qualification','exact coarsened mixture',expected == warn[g] and j == wjoin[g])
            for e in (g,3-g):
                # Update model weights on Y, then on purchased W; selection is fixed by Y.
                obs_mass = (9*m[0]+m[1])/2
                post_warn = (9*m[0]/(2*obs_mass),m[1]/(2*obs_mass))
                ev_label = reference.evidence(add(c,e))
                likelihood = (ev_label[0]/m[0],ev_label[1]/m[1])
                un = tuple(x*y for x,y in zip(post_warn,likelihood))
                expected_post = (9*ev_label[0]/(9*ev_label[0]+ev_label[1]),ev_label[1]/(9*ev_label[0]+ev_label[1]))
                check('qualification','sequential equals joint conditioning',tuple(x/sum(un) for x in un) == expected_post)
            prior_weights = (F(9,10),F(1,10))
            norm = sum(x*y/2 for x,y in zip(prior_weights,m))
            post = tuple(x*y/(2*norm) for x,y in zip(prior_weights,m))
            free = fsum(float(x)*log(float(x/(pr*lik/2))) for x,pr,lik in zip(post,prior_weights,m))
            close('VFE','partial-observation structural evidence',free,-log(float(norm)))
        for label,q in dict(prior=None,**TRUTHS).items():
            seq_mass = ev(c) if q is None else prod(F(q[e],BASE)**c[e] for e in range(4))
            for s in (0,1):
                if not k[s]:
                    continue
                losses = [F(0)]*3
                first_only = [F(0)]*3
                for w,e,z,f in product((0,1),range(4),(0,1),range(4)):
                    y = e if w == 0 else 3-e
                    later_y = f if z == 0 else 3-f
                    act = C.ACTS[initial[s]][y]
                    branch = (initial[s],warn[min(y,3-y)][s],labels[e][s] if act == 2 else warn[min(y,3-y)][s])
                    probability = ev(add(add(c,e),f))/(4*ev(c)) if q is None else F(q[e]*q[f],4*BASE**2)
                    loss0 = F(1,10) if act == 2 else int(act != w)
                    for a,code in enumerate(branch):
                        action = C.ACTS[code][later_y]
                        loss1 = F(1,10) if action == 2 else int(action != z)
                        losses[a] += probability*(loss0+99*loss1)/100
                        first_only[a] += probability*loss0
                check('qualification','no future tasks means no benefit',len(set(first_only)) == 1)
                for a in range(3):
                    direct[label][s][a] += k[s]*seq_mass*(losses[a]+F(n,100000))
    build(stops,cap,coll,extra=extra)
    prior,actual = coll.finish()
    for label in direct:
        rows = prior if label == 'prior' else actual[label]
        for s,name in enumerate(NAMES):
            for a,arm in enumerate(ARMS):
                check('qualification','direct two-task physical integration',direct[label][s][a] == rows[name]['arms'][arm]['net_loss'])
    # Ordered prefix walks independently verify outcome-dependent stopping counts.
    for s in (0,1):
        reached = Counter()
        def walk(c):
            n,i = sum(c),ix(sum(c),*c[:3])
            if stops[s][n][i]:
                reached[c] += 1
            else:
                check('qualification','toy stops by cap',n < cap)
                for e in range(4):
                    walk(add(c,e))
        walk((0,0,0,0))
        for n in range(cap+1):
            for i,c in enumerate(counts(n)):
                check('qualification','ordered stopping multiplicity',reached[c] == stops[s][n][i])
    # Without a purchased label, full retention is literally the warnings arm.
    dummy = features(36,0,(51,80),(0,1),(51,80,36,65),(0,1,0,1),
                     (100,100,100,100),tuple((10000,)*4 for _ in range(4)))
    check('qualification','no-reference control',dummy['future'][2] == dummy['future'][1] and dummy['label_changed'] == 0)
    c = (0,0,0,0)
    p = tuple(sum(reference.evidence(add(add(c,e),f))[0] for e in (0,3)) /
              sum(reference.evidence(add(c,e))[0] for e in (0,3)) for f in range(4))
    check('qualification','M0 coarsening couples parameter uncertainty',p == tuple(F(x,18) for x in (5,4,4,5)) and p[0] != (p[0]+p[1])*(p[0]+p[2]))
    # All-correct labeled counts ensure a real unchecked-report branch is exercised.
    full_stops = toy_stops(reference,3,True)
    control = Collector(3,{'uniform':(100,100,100,100)})
    build(full_stops,3,control,extra=None)
    control.finish()
    check('qualification','unchecked branch present',C.ACTS[program(reference.fit((3,0,0,0))['vectors'][1])] != (2,2,2,2))
    t = perf_counter()
    bench = Collector(12,TRUTHS)
    bench_states = build(toy_stops(reference,12,True),12,bench)
    bench.finish()
    bench_seconds = perf_counter()-t
    forecast = 90+6*bench_seconds*comb(CAP+5,4)/bench_states
    return dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),wall_seconds=perf_counter()-start,
        direct_ordered_cap=3,benchmark_cap=12,benchmark_states=bench_states,benchmark_seconds=bench_seconds,
        forecast_main_seconds=forecast,requires_detached=forecast > 600,
        forecast_rule='90s I/O plus six times cap-12 full-panel per-state time',max_residual=C.MAX_ERROR)


def verify(entries,label):
    for entry in entries:
        check('integrity',label+' '+entry['path'],identity(Path(entry['path'])) == entry)


def prepare(output,logline):
    check('integrity','prior manifest',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','prior report',identity(SOURCE/'FEP_FORECAST_VALIDATION_V1_REPORT.md')['sha256'] == REPORT_SHA)
    check('integrity','factor checker',identity(SOURCE/'check_fep_factor_revision.py')['sha256'] == FACTOR_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({x['path']:x for group in ('inputs','outputs','preserved') for x in old[group]}.values())
    verify(preserved,'preserved before')
    (output/'inputs').mkdir()
    originals = [(SOURCE/name,name) for name in ('FEP_REFERENCE_FEEDBACK_V1.md','check_fep_reference_feedback.py',
        'FEP_FORECAST_VALIDATION_V1.md','FEP_FORECAST_VALIDATION_V1_REPORT.md','check_fep_forecast_validation.py',
        'check_fep_factor_revision.py','check_fep_stopping_attribution.py')]
    originals += [(PREVIOUS/'MANIFEST.json','validation_MANIFEST.json'),(PREVIOUS/'RESULTS.json','validation_RESULTS.json'),
                  (ATTRIBUTION/'RESULTS.json','attribution_RESULTS.json')]
    inputs = []
    for path,name in originals:
        entry = identity(path)
        inputs.append(entry)
        shutil.copyfile(path,output/'inputs'/name)
        check('integrity','snapshot '+name,identity(output/'inputs'/name)['sha256'] == entry['sha256'])
    inputs.append(identity(PREVIOUS/'STOPPED_FORECASTS.jsonl.gz'))
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,cap=CAP,H=H,methods=NAMES,retention_arms=ARMS,
        truths=TRUTHS,Q_denominator=BASE,panel_equal_weights=True,feedback_opportunities=1,model_prior=[F(9,10),F(1,10)],
        posterior_ledger_columns=['n','c00','c01','c10','c11','two exact stopped-path counts',
            'two initial codes','initial MAP join','two warning/two-method codes','two warning MAP joins',
            'four label/two-method codes','four label MAP joins'],
        large_inputs_read_in_place=True,policy_optimizations=0,known_challenge_panel=True,
        declaration='initial policies and costs matched; no unpurchased labels; one observation-retention opportunity'))
    reference = module('frozen_factor_reference',SOURCE/'check_fep_factor_revision.py')
    qualification = qualify(reference)
    write(output/'QUALIFICATION.json',qualification)
    logline(f'PREPARED: {qualification["checks"]} checks; {qualification["wall_seconds"]:.3f}s; main forecast {qualification["forecast_main_seconds"]:.1f}s; detached={qualification["requires_detached"]}')


def execute(output,logline):
    prepared = json.loads((output/'PREPARATION.json').read_text())
    qualification = json.loads((output/'QUALIFICATION.json').read_text())
    for key,value in qualification['groups'].items():
        C.COUNTS[key] += value
    C.MAX_ERROR = qualification['max_residual']
    verify(prepared['inputs']+prepared['preserved'],'unchanged before main')
    check('scope','not already started',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qualification['forecast_main_seconds']))
    stops,saved = load_stops()
    with gzip.open(output/'POSTERIOR_TABLES.jsonl.gz','wt',encoding='utf-8',compresslevel=6) as ledger:
        coll = Collector(CAP,TRUTHS,ledger)
        states = build(stops,CAP,coll,saved,logline)
    prior,actual = coll.finish()
    old = json.loads((PREVIOUS/'RESULTS.json').read_text())
    old_shared = json.loads((PREVIOUS/'old_shared_integrity_replay.json').read_text())['methods']
    for name in NAMES:
        check('bridge','same own-prior no-update value',prior[name]['arms']['none']['net_loss'] == F(old['own_prior'][name]['net_loss']['exact']))
        for label,rows in actual.items():
            former = old['panel'][label][name] if label in PANEL else old_shared[name]
            check('bridge','same no-update task loss',rows[name]['arms']['none']['net_loss'] == F(former['net_loss']['exact']))
            check('bridge','same calibration count',rows[name]['expected_calibrations'] == F(former['expected_calibrations']['exact']))
    write(output/'PRIOR_CONTROL.json',prior)
    for label,rows in actual.items():
        write(output/(label+'.json'),dict(Q=[F(x,BASE) for x in TRUTHS[label]],methods=rows))
    aggregate = {}
    for name in NAMES:
        rows = [actual[label][name] for label in PANEL]
        avg = {key:sum(row[key] for row in rows)/9 for key in ('expected_calibrations','first_reference_probability',
            'first_wrong_probability','additional_label_changes_table_probability','full_minus_none','full_minus_warnings','warnings_minus_none')}
        avg['arms'] = {arm:{key:sum(row['arms'][arm][key] for row in rows)/9 for key in rows[0]['arms'][arm]} for arm in ARMS}
        avg['gates'] = dict(full_feedback_improves_average=avg['full_minus_none'] < 0,
            purchased_labels_improve_average=avg['full_minus_warnings'] < 0,
            full_feedback_no_worse_in_every_environment=all(row['full_minus_none'] <= 0 for row in rows))
        avg['no_worse_environment_count'] = sum(row['full_minus_none'] <= 0 for row in rows)
        avg['below_always_reference_counts'] = {arm:sum(row['arms'][arm]['net_loss'] < F(1,10) for row in rows) for arm in ARMS}
        aggregate[name] = avg
    verify(prepared['inputs']+prepared['preserved'],'unchanged after main')
    summary = dict(checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS),max_float_identity_residual=C.MAX_ERROR,
        inference_states=states,boundary_likelihood_states=comb(CAP+5,3),posterior_table_rows=coll.rows,
        stopped_controller_rows=coll.stopped_rows,known_panel_environments=9,secondary_shared_cases=1,
        sampled_trajectories=0,policy_optimizations=0,feedback_opportunities=1,primary_gates=aggregate['edit']['gates'])
    write(output/'RESULTS.json',dict(summary=summary,prior=prior,equal_panel_aggregate=aggregate,truths=actual))
    wall = perf_counter()-start
    logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s; primary gates {summary["primary_gates"]}')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        main_wall_seconds=wall,main_cpu_seconds=process_time()-cpu,qualification_seconds=qualification['wall_seconds'],
        python=platform.python_version(),processes=1,inputs=prepared['inputs'],outputs=outputs,
        preserved=prepared['preserved'],summary=summary))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('prepare','execute'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output
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
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; no optimizer')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(C.COUNTS.values()),groups=dict(C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
