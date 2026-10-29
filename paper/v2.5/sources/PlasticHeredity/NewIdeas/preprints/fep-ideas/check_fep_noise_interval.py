#!/usr/bin/env python3
"""Exact physical cost polynomials and bounded Bernstein interval certificates."""
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import os
import platform
import subprocess
import sys
import time

sys.set_int_max_str_digits(0)
ROOT = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
STORE = BASE/'fep-noise-interval-v1'
JOINT = BASE/'fep-noise-uncertainty-v1/attempt-01'
MISMATCH = BASE/'fep-noise-mismatch-v1/attempt-01'
SOURCES = ('FEP_NOISE_INTERVAL_V1.md', 'check_fep_noise_interval.py', 'readback_fep_noise_interval.py')
REFERENCES = ('FEP_NOISE_UNCERTAINTY_V1.md', 'FEP_NOISE_UNCERTAINTY_V1_REPORT.md',
              'FEP_NOISE_MISMATCH_V1.md', 'FEP_NOISE_MISMATCH_V1_REPORT.md')
A, B, K = F(1, 25), F(3, 50), F(19568652557, 204800000000)
MAX_DEPTH, MAX_NODES = 16, 4095
ZERO, ONE, X = (F(0),), (F(1),), (F(0), F(1))
FIELDS = ('cost','errors','purchases','post_cost','post_errors','post_purchases','delay','missing','recovery')


def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())


def save(p, value):
    with Path(p).open('x') as out:
        json.dump(value, out, default=lambda v: str(v) if isinstance(v, F) else v, indent=2, sort_keys=True)
        out.write('\n')


def trim(p):
    p = list(p)
    while len(p) > 1 and p[-1] == 0: p.pop()
    return tuple(p)


def add(*polys):
    result = [F(0)]*max((len(p) for p in polys), default=1)
    for p in polys:
        for i, v in enumerate(p): result[i] += v
    return trim(result)


def scale(p, c): return trim(v*c for v in p)


def multiply(p, q):
    result = [F(0)]*(len(p)+len(q)-1)
    for i, u in enumerate(p):
        for j, v in enumerate(q): result[i+j] += u*v
    return trim(result)


def value(p, x):
    result = F(0)
    for v in reversed(p): result = result*x+v
    return result


def derivative(p): return trim([i*v for i, v in enumerate(p)][1:] or [F(0)])


def bernstein(p, lo, hi):
    n = len(p)-1
    local = [sum(p[j]*math.comb(j, k)*lo**(j-k)*(hi-lo)**k for j in range(k, n+1)) for k in range(n+1)]
    return tuple(sum(local[k]*F(math.comb(i, k), math.comb(n, k)) for k in range(i+1)) for i in range(n+1))


def certify(p, strict=False, lo=A, hi=B, max_depth=MAX_DEPTH, max_nodes=MAX_NODES):
    p = trim(p)
    assert lo < hi and max_nodes >= 1
    stack, leaves, nodes = [(lo, hi, 0)], [], 0
    while stack:
        left, right, depth = stack.pop(); nodes += 1
        for x in (left, (left+right)/2, right):
            y = value(p, x)
            if y < 0 or (strict and y == 0):
                return dict(verdict='FAIL', strict=strict, domain=[lo, hi], nodes=nodes,
                    max_depth=max_depth, max_nodes=max_nodes, leaves=[],
                    witness=dict(x=x, value=y), lower_bound=None, upper_bound=None)
        coeff = bernstein(p, left, right)
        proved = min(coeff) > 0 if strict else min(coeff) >= 0
        if proved or depth >= max_depth or nodes+len(stack)+2 > max_nodes:
            leaves.append(dict(lo=left, hi=right, depth=depth, coefficients=coeff,
                               kind='proved' if proved else 'unresolved'))
        else:
            middle = (left+right)/2
            stack.extend([(middle, right, depth+1), (left, middle, depth+1)])
    return dict(verdict='PASS' if all(v['kind'] == 'proved' for v in leaves) else 'INCONCLUSIVE',
        strict=strict, domain=[lo, hi], nodes=nodes, max_depth=max_depth, max_nodes=max_nodes,
        leaves=leaves, witness=None, lower_bound=min(min(v['coefficients']) for v in leaves),
        upper_bound=max(max(v['coefficients']) for v in leaves))


def sign(p):
    positive, negative = certify(p), certify(scale(p, -1))
    a, b = positive['verdict'], negative['verdict']
    verdict = ('zero' if a == b == 'PASS' else 'nonnegative' if a == 'PASS' else
               'nonpositive' if b == 'PASS' else 'mixed' if a == b == 'FAIL' else 'unresolved')
    return dict(sign=verdict, nonnegative=positive, nonpositive=negative)


def world_polynomials(graph, T, tau):
    @lru_cache(None)
    def walk(i):
        if i is None: return (ZERO,)*5+(ONE,)
        node = graph[i]
        t, buy = node['t'], node['action'] == 'B'
        post = tau is not None and t >= tau
        risk = (F(1), F(-1)) if post else X
        if buy:
            left, right = walk(node['children']['0']), walk(node['children']['1'])
            future = [add(u, multiply(risk, add(v, scale(u,-1)))) for u,v in zip(left,right)]
        else: future = list(walk(node['children']['N']))
        error = ZERO if buy else risk if node['action'] == 'F' else add(ONE,scale(risk,-1))
        future[0] = add(future[0], error)
        future[1] = add(future[1], ONE if buy else ZERO)
        if post:
            future[2] = add(future[2], error)
            future[3] = add(future[3], ONE if buy else ZERO)
            if buy: future[4], future[5] = ZERO, ZERO
            else: future[4] = add(future[4], ONE)
        return tuple(future)
    e,b,pe,pb,d,m = walk(0)
    cost, post = add(e,scale(b,F(1,10))), add(pe,scale(pb,F(1,10)))
    row = dict(onset=tau,cost=cost,errors=e,purchases=b,post_cost=post,post_errors=pe,
               post_purchases=pb,delay=d,missing=m,recovery=None if tau is None else scale(post,F(1,T-tau+1)))
    assert all(v is None or k == 'onset' or len(v) <= T+1 for k,v in row.items())
    return row


def summary(worlds, T, rho):
    S = scale(worlds[0]['cost'],F(1,T))
    B = add(scale(S,1-rho),scale(add(*(w['cost'] for w in worlds[1:])),rho/(T*T)))
    R = scale(add(*(w['recovery'] for w in worlds[1:])),F(1,T))
    return dict(stable=S,B=B,R=R,J=add(B,R))


def record(graph, T, rho):
    worlds = [world_polynomials(graph,T,tau) for tau in [None,*range(1,T+1)]]
    return dict(worlds=worlds,summary=summary(worlds,T,rho))


def mixture(policies, components, T, rho):
    assert sum(F(c['weight']) for c in components) == 1
    assert all(F(c['weight']) >= 0 for c in components)
    worlds = []
    for i in range(T+1):
        row = dict(onset=None if i == 0 else i)
        for key in FIELDS:
            row[key] = None if key == 'recovery' and i == 0 else add(*(
                scale(policies[c['policy']]['worlds'][i][key],F(c['weight'])) for c in components))
        worlds.append(row)
    return dict(components=components,worlds=worlds,summary=summary(worlds,T,rho))


def roster():
    joint, mismatch = read(JOINT/'RESULTS.json'), read(MISMATCH/'GRAPHS.json')
    problem = joint['problems']['retained']
    graphs, mixtures = {}, {}
    components = []
    for c in problem['solution']['components']:
        name = 'joint_'+c['policy']
        graphs[name] = dict(graph=problem['policies'][c['policy']]['graph'],belief='joint_noise',source=c['policy'])
        components.append(dict(policy=name,weight=c['weight']))
    mixtures['joint_mixture'] = components
    components = []
    for c in joint['controls']['fixed_pool']['components']:
        name = 'fixed_'+c['policy']
        graphs[name] = dict(graph=mismatch['policies'][c['policy']]['graph'],belief='nominal_5_percent',source=c['policy'])
        components.append(dict(policy=name,weight=c['weight']))
    mixtures['fixed_pool'] = components
    graphs['hybrid'] = dict(graph=mismatch['policies']['hybrid']['graph'],belief='nominal_5_percent',source='hybrid')
    assert joint['T'] == mismatch['T'] == 10 and F(joint['budget']) == F(mismatch['budget']) == K
    return dict(T=10,rho=F(1,2),budget=K,domain=[A,B],graphs=graphs,mixtures=mixtures)


def calculate(roster):
    T, rho, budget = roster['T'],F(roster['rho']),F(roster['budget'])
    policies = {name:record(p['graph'],T,rho) for name,p in roster['graphs'].items()}
    for name,components in roster['mixtures'].items(): policies[name] = mixture(policies,components,T,rho)
    always = [dict(t=t,action='B',children={str(d):t if t<T else None for d in (0,1)}) for t in range(1,T+1)]
    policies['always'] = record(always,T,rho)
    assert all(policies['always']['summary'][k] == (F(1,10),) for k in ('stable','B','R'))
    checks, primary, secondary, trends, onsets = {}, {}, {}, {}, {}
    h = policies['hybrid']['summary']
    for name in roster['mixtures']:
        s = policies[name]['summary']
        margins = dict(stable=(add((budget,),scale(s['stable'],-1)),False),
                       always_recovery=(add((F(1,10),),scale(s['R'],-1)),True),
                       hybrid_recovery=(add(h['R'],scale(s['R'],-1)),True))
        primary[name] = []
        for criterion,(poly,strict) in margins.items():
            key=name+':'+criterion
            checks[key] = dict(polynomial=poly,certificate=certify(poly,strict),derivative=sign(derivative(poly)))
            primary[name].append(key)
        secondary[name] = {}
        for criterion,poly,strict in [('matched_stable',add(h['stable'],scale(s['stable'],-1)),False),
                                      ('hybrid_full',add(h['B'],scale(s['B'],-1)),True),
                                      ('always_full',add((F(1,10),),scale(s['B'],-1)),True)]:
            secondary[name][criterion] = dict(polynomial=poly,certificate=certify(poly,strict))
        onsets[name] = []
        for u,v in zip(policies[name]['worlds'],policies['hybrid']['worlds']):
            full = scale(add(v['cost'],scale(u['cost'],-1)),F(1,T))
            recovery = None if u['recovery'] is None else add(v['recovery'],scale(u['recovery'],-1))
            onsets[name].append(dict(onset=u['onset'],full=full,full_sign=sign(full),recovery=recovery,
                                    recovery_sign=None if recovery is None else sign(recovery)))
    comparison = add(policies['fixed_pool']['summary']['J'],scale(policies['joint_mixture']['summary']['J'],-1))
    secondary['joint_J_vs_pool'] = dict(polynomial=comparison,certificate=certify(comparison,True),sign=sign(comparison))
    for name in [*roster['mixtures'],'hybrid']:
        trends[name] = {field:sign(derivative(policies[name]['summary'][field])) for field in ('stable','B','R')}
    verdicts = {}
    for name,keys in primary.items():
        v = [checks[k]['certificate']['verdict'] for k in keys]
        verdicts[name] = 'PASS' if all(x=='PASS' for x in v) else 'FAIL' if 'FAIL' in v else 'INCONCLUSIVE'
    return dict(T=T,rho=rho,budget=budget,domain=[A,B],policies=policies,checks=checks,primary=primary,
                secondary=secondary,onsets=onsets,trends=trends,verdicts=verdicts)


@lru_cache(None)
def trees(T):
    if not T: return (None,)
    sub=trees(T-1)
    return tuple([(a,x) for a in ('F','R') for x in sub]+[('B',x,y) for x in sub for y in sub])


def graph_from_tree(tree):
    graph=[]
    def visit(tree,t):
        if tree is None: return None
        i=len(graph);graph.append(None)
        children = {str(d):visit(tree[d+1],t+1) for d in (0,1)} if tree[0]=='B' else {'N':visit(tree[1],t+1)}
        graph[i]=dict(t=t,action=tree[0],children=children)
        return i
    visit(tree,1)
    return graph


def brute(graph,T,tau,x):
    totals=[F(0)]*6
    for bits in itertools.product((0,1),repeat=T):
        k=sum(bits);prob=x**k*(1-x)**(T-k)
        i=0;e=b=pe=pb=0;first=None
        for t,noise in enumerate(bits,1):
            node=graph[i];post=tau is not None and t>=tau
            label=int(post)^noise;buy=node['action']=='B'
            error=int(not buy and ((node['action']=='R') != bool(label)))
            e+=error;b+=buy;pe+=error*post;pb+=buy*post
            if post and buy and first is None:first=t
            i=node['children'][str(label) if buy else 'N']
        assert i is None
        delay=0 if tau is None else T-tau+1 if first is None else first-tau
        vals=(e,b,pe,pb,delay,int(first is None))
        totals=[a+prob*v for a,v in zip(totals,vals)]
    e,b,pe,pb,d,m=totals
    return dict(onset=tau,cost=e+b/10,errors=e,purchases=b,post_cost=pe+pb/10,post_errors=pe,
                post_purchases=pb,delay=d,missing=m,recovery=None if tau is None else (pe+pb/10)/(T-tau+1))


def qualify():
    checks=cases=0
    fixtures=[]
    for T in (1,2,3):
        for tree in trees(T):
            graph=graph_from_tree(tree)
            p=record(graph,T,F(1,2))
            for row in p['worlds']:
                for x in (F(0),A,F(1,20),B,F(1,2),F(1)):
                    exact=brute(graph,T,row['onset'],x)
                    for k in FIELDS:
                        assert exact[k] is None if row[k] is None else value(row[k],x)==exact[k]
                        checks+=1
            cases+=1
        fixtures.append(dict(T=T,rho='1/2',graph=graph_from_tree(trees(T)[-1]),record=record(graph_from_tree(trees(T)[-1]),T,F(1,2))))
    q = multiply((F(-1,2),F(1)),(F(-1,2),F(1)))
    well = add(multiply((F(-47,1000),F(1)),(F(-47,1000),F(1))),(F(-1,100000000),))
    examples = [(ONE,True,A,B,16,'PASS'),((-F(1),),False,A,B,16,'FAIL'),
                (ZERO,False,A,B,16,'PASS'),(ZERO,True,A,B,16,'FAIL'),
                ((B,F(-1)),False,A,B,16,'PASS'),((B,F(-1)),True,A,B,16,'FAIL'),
                ((-A,F(1)),False,A,B,16,'PASS'),
                (add(q,(F(1,100),)),True,F(0),F(1),16,'PASS'),
                (q,False,F(0),F(1),16,'PASS'),(q,True,F(0),F(1),16,'FAIL'),
                (well,False,A,B,16,'FAIL'),
                (multiply((F(-1,3),F(1)),(F(-1,3),F(1))),False,F(0),F(1),0,'INCONCLUSIVE')]
    certs=[]
    for p,strict,lo,hi,depth,expected in examples:
        c=certify(p,strict,lo,hi,depth)
        assert c['verdict']==expected;checks+=1
        certs.append(dict(polynomial=p,certificate=c,expected=expected))
    # A purchase-only erased sequence and a fixed mixture remain exact at
    # extra off-grid qualification rates; no optimization is performed.
    graph=[dict(t=t,action='B',children={str(d):t if t<3 else None for d in (0,1)}) for t in range(1,4)]
    p=record(graph,3,F(1,3));fixtures.append(dict(T=3,rho='1/3',graph=graph,record=p))
    a=record(graph_from_tree(trees(3)[0]),3,F(1,3))
    mixed=mixture({'a':a,'b':p},[dict(policy='a',weight=F(2,7)),dict(policy='b',weight=F(5,7))],3,F(1,3))
    for i,row in enumerate(mixed['worlds']):
        for x in (F(9,200),F(11,200)):
            for k in FIELDS:
                if row[k] is None:continue
                assert value(row[k],x)==F(2,7)*value(a['worlds'][i][k],x)+F(5,7)*value(p['worlds'][i][k],x)
                checks+=1
    return dict(passed=True,checks=checks,cases=cases,tree_counts={str(t):len(trees(t)) for t in (1,2,3)}),dict(graphs=fixtures,certificates=certs)


def truncate(roster,T):
    result=dict(roster,T=T,rho='1/3',graphs={})
    for name,p in roster['graphs'].items():
        kept=[i for i,n in enumerate(p['graph']) if n['t']<=T];mapping={old:new for new,old in enumerate(kept)}
        graph=[]
        for i in kept:
            node=p['graph'][i]
            graph.append(dict(node,children={k:None if node['t']==T else mapping[v] for k,v in node['children'].items()}))
        result['graphs'][name]=dict(p,graph=graph)
    return result


def check_freeze(a):
    f=read(a/'FREEZE.json')
    for n,h in f['inputs'].items():assert sha(n)==h,n
    for n,h in f['snapshots'].items():assert sha(a/'inputs'/n)==h,n


def log(a,message):
    line=utc()+' '+message
    with (a/'RUN_LOG.txt').open('a') as out:out.write(line+'\n')
    print(line,flush=True)


def run_main(a,detached):
    check_freeze(a);forecast=read(a/'BENCHMARK.json')['forecast_seconds']
    assert forecast<=7200 and (forecast<=600 or detached)
    save(a/'STARTED.json',dict(utc=utc(),pid=os.getpid(),sid=os.getsid(0),affinity=sorted(os.sched_getaffinity(0)),
        nice=os.getpriority(os.PRIO_PROCESS,0),detached=detached,
        threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}))
    start=time.monotonic();log(a,'MAIN_START')
    result=calculate(read(a/'GRAPHS.json'));save(a/'RESULTS.json',result)
    check_freeze(a);log(a,'MAIN_COMPLETE')
    save(a/'MANIFEST.json',dict(status='COMPLETE',finished=utc(),wall_seconds=time.monotonic()-start,
        outputs={str(p.relative_to(a)):sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable,'-B',str(ROOT/'readback_fep_noise_interval.py'),str(a)],stdout=out,stderr=subprocess.STDOUT,check=True)
    print('READBACK_COMPLETE '+str(a),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',default='attempt-01')
    parser.add_argument('--main-only',action='store_true');parser.add_argument('--detached',action='store_true');args=parser.parse_args()
    assert args.attempt.startswith('attempt-') and '/' not in args.attempt
    assert Path('/mnt/bioIce1').is_mount()
    disk=os.statvfs('/mnt/bioIce1');assert disk.f_bavail*disk.f_frsize>300_000_000
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    if os.getpriority(os.PRIO_PROCESS,0)<10:os.nice(10-os.getpriority(os.PRIO_PROCESS,0))
    a=STORE/args.attempt
    if args.main_only:assert a.is_dir() and not (a/'STARTED.json').exists()
    else:a.mkdir(parents=True,exist_ok=False)
    try:
        if not args.main_only:
            (a/'inputs').mkdir()
            for n in SOURCES:(a/'inputs'/n).write_bytes((ROOT/n).read_bytes())
            paths=[ROOT/n for n in SOURCES+REFERENCES]
            paths += [JOINT/n for n in ('RESULTS.json','MANIFEST.json','READBACK.json')]
            paths += [MISMATCH/n for n in ('RESULTS.json','GRAPHS.json','MANIFEST.json','READBACK.json')]
            save(a/'FREEZE.json',dict(created=utc(),inputs={str(p):sha(p) for p in paths},
                snapshots={n:sha(a/'inputs'/n) for n in SOURCES},python=platform.python_version(),
                T=10,rho='1/2',domain=[A,B],budget=K,max_depth=MAX_DEPTH,max_nodes=MAX_NODES))
            graphs=roster();save(a/'GRAPHS.json',graphs)
            log(a,'QUALIFICATION_START');start=time.monotonic()
            q,fixtures=qualify();q['seconds']=time.monotonic()-start
            save(a/'QUALIFICATION.json',q);save(a/'SHORT_FIXTURES.json',fixtures);log(a,'QUALIFICATION_PASS')
            start=time.monotonic();short=truncate(graphs,7);benchmark=calculate(short)
            for p in short['graphs'].values():
                for tau in [None,*range(1,8)]:brute(p['graph'],7,tau,F(1,20))
            seconds=time.monotonic()-start;forecast=120+6*2**3*seconds
            save(a/'BENCHMARK.json',dict(T=7,rho='1/3',timing_only=True,graphs=len(short['graphs']),
                seconds=seconds,forecast_seconds=forecast))
            log(a,'BENCHMARK_COMPLETE')
            if forecast>7200:log(a,'FEASIBILITY_CEILING_EXCEEDED');return
            if forecast>600:print('DETACHED_MAIN_REQUIRED',flush=True);return
        run_main(a,args.detached)
    except Exception as error:
        n='READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/n).exists():save(a/n,dict(utc=utc(),error=repr(error)))
        raise


if __name__=='__main__':main()
