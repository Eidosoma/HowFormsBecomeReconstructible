#!/usr/bin/env python3
"""Frozen policies under one hidden change of sensor reliability."""
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse
import itertools
import math
import os
import platform
import subprocess
import sys
import time

import check_fep_noise_interval as old

ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/bioIce1/fep-ideas/formal-checks')
STORE=BASE/'fep-noise-switch-v1'
REFERENCE=BASE/'fep-noise-interval-v1/attempt-01'
SOURCES=('FEP_NOISE_SWITCH_V1.md','check_fep_noise_switch.py','readback_fep_noise_switch.py')
REFERENCES=('FEP_NOISE_INTERVAL_V1.md','FEP_NOISE_INTERVAL_V1_REPORT.md','check_fep_noise_interval.py')
SHARED=('cost','errors','purchases','post_cost','post_errors','post_purchases','delay','missing','recovery')
FIELDS=SHARED+('orientation_brier','switch_cost','switch_errors','switch_purchases','switch_delay','switch_missing','switch_brier')
TARGETS=('joint_mixture','fixed_pool')
K=F(19568652557,204800000000)
save,read,sha,utc,log,check_freeze=old.save,old.read,old.sha,old.utc,old.log,old.check_freeze


def schedule(T,before,after,sigma):
    return dict(before=before,after=after,change_task=sigma,
                rates=[before if sigma is None or t<sigma else after for t in range(1,T+1)])


def schedules(T):
    result={f'constant_{n:02d}':schedule(T,n,n,None) for n in (4,5,6)}
    for name,before,after in [('up',4,6),('down',6,4)]:
        for sigma in range(2,T+1):result[f'{name}_{sigma:02d}']=schedule(T,before,after,sigma)
    return result


def probabilities(graph,belief):
    result=[]
    for node in graph:
        w=node['weights'];width=len(w)//3 if belief=='joint_noise' else len(w)
        result.append(F(sum(w[base+j] for base in range(0,len(w),width)
                            for j in range(1,node['t']+1)),sum(w)))
    return result


def world(graph,probs,T,tau,profile):
    sigma=profile['change_task']
    @lru_cache(None)
    def walk(i):
        if i is None:return (F(0),)*5+(F(1),)+(F(0),)*4+(F(1),F(0))
        node=graph[i];t=node['t'];buy=node['action']=='B'
        post=tau is not None and t>=tau;sw=sigma is not None and t>=sigma
        eps=F(profile['rates'][t-1],100);risk=1-eps if post else eps
        branches=[('0',1-risk),('1',risk)] if buy else [('N',F(1))]
        result=[sum(p*walk(node['children'][label])[k] for label,p in branches) for k in range(12)]
        error=F(0) if buy else risk if node['action']=='F' else 1-risk
        brier=(probs[i]-int(post))**2
        result[0]+=error;result[1]+=buy;result[6]+=brier
        if post:
            result[2]+=error;result[3]+=buy
            if buy:result[4]=result[5]=F(0)
            else:result[4]+=1
        if sw:
            result[7]+=error;result[8]+=buy;result[11]+=brier
            if buy:result[9]=result[10]=F(0)
            else:result[9]+=1
        return tuple(result)
    e,b,pe,pb,d,m,br,se,sb,sd,sm,sbr=walk(0)
    return dict(onset=tau,cost=e+b/10,errors=e,purchases=b,post_cost=pe+pb/10,post_errors=pe,
        post_purchases=pb,delay=d,missing=m,recovery=None if tau is None else (pe+pb/10)/(T-tau+1),
        orientation_brier=br,switch_cost=None if sigma is None else se+sb/10,
        **{key:None if sigma is None else val for key,val in
           [('switch_errors',se),('switch_purchases',sb),('switch_delay',sd),('switch_missing',sm),('switch_brier',sbr)]})


def summarize(worlds,T,rho,profile):
    def prior(key):
        return None if worlds[0][key] is None else (1-rho)*worlds[0][key]+rho*sum(w[key] for w in worlds[1:])/T
    def divided(x,n):return None if x is None or n==0 else x/n
    S=worlds[0]['cost']/T;B=prior('cost')/T;R=sum(w['recovery'] for w in worlds[1:])/T
    L=1 if profile['change_task'] is None else T-profile['change_task']+1
    return dict(stable=S,B=B,R=R,J=B+R,stable_errors=worlds[0]['errors'],stable_purchases=worlds[0]['purchases'],
        mean_post_errors=sum(w['post_errors'] for w in worlds[1:])/T,
        mean_post_purchases=sum(w['post_purchases'] for w in worlds[1:])/T,
        capped_first_delay=sum(w['delay'] for w in worlds[1:])/T,
        no_post_purchase_probability=sum(w['missing'] for w in worlds[1:])/T,
        stable_orientation_brier=divided(worlds[0]['orientation_brier'],T),prior_orientation_brier=divided(prior('orientation_brier'),T),
        switch_cost=divided(prior('switch_cost'),L),switch_errors=prior('switch_errors'),switch_purchases=prior('switch_purchases'),
        switch_delay=prior('switch_delay'),switch_missing=prior('switch_missing'),switch_brier=divided(prior('switch_brier'),L))


def record(graph,belief,T,rho,profile):
    probs=probabilities(graph,belief)
    worlds=[world(graph,probs,T,tau,profile) for tau in [None,*range(1,T+1)]]
    return dict(worlds=worlds,summary=summarize(worlds,T,rho,profile))


def always(T,rho,profile):
    worlds=[];sigma=profile['change_task']
    for tau in [None,*range(1,T+1)]:
        L=0 if tau is None else T-tau+1;N=0 if sigma is None else T-sigma+1
        worlds.append(dict(onset=tau,cost=F(T,10),errors=F(0),purchases=F(T),post_cost=F(L,10),post_errors=F(0),
            post_purchases=F(L),delay=F(0),missing=F(tau is None),recovery=None if tau is None else F(1,10),
            orientation_brier=None,switch_cost=None if sigma is None else F(N,10),
            switch_errors=None if sigma is None else F(0),switch_purchases=None if sigma is None else F(N),
            switch_delay=None if sigma is None else F(0),switch_missing=None if sigma is None else F(0),switch_brier=None))
    return dict(worlds=worlds,summary=summarize(worlds,T,rho,profile))


def mixture(policies,components,T,rho,profile):
    assert sum(F(c['weight']) for c in components)==1 and all(F(c['weight'])>=0 for c in components)
    worlds=[]
    for i in range(T+1):
        row=dict(onset=None if i==0 else i)
        for k in FIELDS:
            vals=[(F(c['weight']),policies[c['policy']]['worlds'][i][k]) for c in components]
            row[k]=None if any(v is None for _,v in vals) else sum(p*v for p,v in vals)
        worlds.append(row)
    return dict(components=components,worlds=worlds,summary=summarize(worlds,T,rho,profile))


def gates(s,h,budget):
    p=dict(stable=s['stable']<=budget,below_always=s['R']<F(1,10),below_hybrid=s['R']<h['R'])
    p['joint']=all(p.values())
    return dict(primary=p,matched_stable=s['stable']<=h['stable'],full_below_hybrid=s['B']<h['B'],full_below_always=s['B']<F(1,10))


def calculate(graphs,profile):
    T,rho=graphs['T'],F(graphs['rho'])
    policies={n:record(p['graph'],p['belief'],T,rho,profile) for n,p in graphs['graphs'].items()}
    policies['always']=always(T,rho,profile)
    for name,cs in graphs['mixtures'].items():policies[name]=mixture(policies,cs,T,rho,profile)
    g={n:gates(p['summary'],policies['hybrid']['summary'],F(graphs['budget'])) for n,p in policies.items()}
    comparisons={}
    for name in TARGETS:
        comparisons[name]={}
        for control in ('hybrid','always',next(n for n in TARGETS if n!=name)):
            p,q=policies[name],policies[control]
            summaries={k:None if p['summary'][k] is None or q['summary'][k] is None else p['summary'][k]-q['summary'][k] for k in p['summary']}
            rows=[dict(onset=u['onset'],full_cost_delta=u['cost']-v['cost'],
                       recovery_delta=None if u['recovery'] is None else u['recovery']-v['recovery']) for u,v in zip(p['worlds'],q['worlds'])]
            comparisons[name][control]=dict(summary_deltas=summaries,worlds=rows)
    return dict(profile=profile,policies=policies,gates=g,comparisons=comparisons)


def graph_from_tree(tree,T,rho,belief,erased=False):
    noises=(4,5,6) if belief=='joint_noise' else (5,)
    initial=(T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
    g=math.gcd(*initial);initial=tuple(w//g for w in initial)*len(noises)
    graph=[]
    def visit(tree,t,w):
        if tree is None:return None
        i=len(graph);graph.append(None)
        if tree[0]=='B':
            children={}
            for d in (0,1):
                raw=[v*(100-noises[e] if d==int(0<j<=t) else noises[e])
                     for e in range(len(noises)) for j,v in enumerate(w[e*(T+1):(e+1)*(T+1)])]
                common=math.gcd(*raw);new=tuple(v//common for v in raw)
                children[str(d)]=visit(tree[d+1],t+1,w if erased else new)
        else:children={'N':visit(tree[1],t+1,w)}
        graph[i]=dict(t=t,weights=w,action=tree[0],children=children)
        return i
    visit(tree,1,initial)
    return graph


def brute(graph,belief,T,tau,profile):
    probs=probabilities(graph,belief);totals=[F(0)]*12;sigma=profile['change_task']
    for bits in itertools.product((0,1),repeat=T):
        mass=math.prod(n if bit else 100-n for bit,n in zip(bits,profile['rates']))
        vals=[F(0)]*12;first=firstsw=None;i=0
        for t,bit in enumerate(bits,1):
            node=graph[i];post=tau is not None and t>=tau;sw=sigma is not None and t>=sigma
            d=int(post)^bit;buy=node['action']=='B';error=int(not buy and (node['action']=='R')!=bool(d))
            br=(probs[i]-int(post))**2
            vals[0]+=error;vals[1]+=buy;vals[6]+=br
            if post:
                vals[2]+=error;vals[3]+=buy
                if buy and first is None:first=t
            if sw:
                vals[7]+=error;vals[8]+=buy;vals[11]+=br
                if buy and firstsw is None:firstsw=t
            i=node['children'][str(d) if buy else 'N']
        assert i is None
        vals[4]=0 if tau is None else T-tau+1 if first is None else first-tau
        vals[5]=int(first is None);vals[9]=0 if sigma is None else T-sigma+1 if firstsw is None else firstsw-sigma;vals[10]=int(firstsw is None)
        totals=[a+mass*b for a,b in zip(totals,vals)]
    e,b,pe,pb,d,m,br,se,sb,sd,sm,sbr=[v/100**T for v in totals]
    return dict(onset=tau,cost=e+b/10,errors=e,purchases=b,post_cost=pe+pb/10,post_errors=pe,post_purchases=pb,
        delay=d,missing=m,recovery=None if tau is None else (pe+pb/10)/(T-tau+1),orientation_brier=br,
        switch_cost=None if sigma is None else se+sb/10,
        **{k:None if sigma is None else v for k,v in [('switch_errors',se),('switch_purchases',sb),('switch_delay',sd),('switch_missing',sm),('switch_brier',sbr)]})


def qualify():
    checks=cases=0;fixtures=[]
    for T in (1,2,3):
        for tree in old.trees(T):
            graph=graph_from_tree(tree,T,F(1,2),'joint_noise')
            for profile in schedules(T).values():
                p=record(graph,'joint_noise',T,F(1,2),profile)
                for row in p['worlds']:
                    assert row==brute(graph,'joint_noise',T,row['onset'],profile);checks+=1
                cases+=1
    for belief,erased,rho in [('joint_noise',False,F(1,3)),('nominal_5_percent',False,F(1,3)),('nominal_5_percent',True,F(1,2))]:
        tree=old.trees(3)[-1] if erased else old.trees(3)[87]
        graph=graph_from_tree(tree,3,rho,belief,erased)
        for profile in [schedule(3,4,6,2),schedule(3,6,4,3)]:
            p=record(graph,belief,3,rho,profile)
            for row in p['worlds']:
                assert row==brute(graph,belief,3,row['onset'],profile);checks+=1
                if row['onset']==profile['change_task']:
                    assert row['delay']==row['switch_delay'] and row['missing']==row['switch_missing'];checks+=1
            fixtures.append(dict(T=3,rho=rho,belief=belief,erased=erased,graph=graph,profile=profile,result=p))
        for before,after in [(4,6),(6,4)]:
            for sigma,n in [(1,after),(4,before)]:
                a=record(graph,belief,3,rho,schedule(3,before,after,sigma))
                b=record(graph,belief,3,rho,schedule(3,n,n,None))
                for x,y in zip(a['worlds'],b['worlds']):
                    assert all(x[k]==y[k] for k in SHARED+('orientation_brier',));checks+=1
    a,b=fixtures[0]['result'],fixtures[2]['result']
    cs=[dict(policy='a',weight=F(2,7)),dict(policy='b',weight=F(5,7))]
    m=mixture({'a':a,'b':b},cs,3,F(1,3),fixtures[0]['profile'])
    for i,row in enumerate(m['worlds']):
        for k in FIELDS:
            if row[k] is not None:assert row[k]==F(2,7)*a['worlds'][i][k]+F(5,7)*b['worlds'][i][k];checks+=1
    return dict(passed=True,checks=checks,cases=cases,tree_counts={str(t):len(old.trees(t)) for t in (1,2,3)}),fixtures


def run_main(a,detached):
    check_freeze(a);forecast=read(a/'BENCHMARK.json')['forecast_seconds']
    assert forecast<=7200 and (forecast<=600 or detached)
    save(a/'STARTED.json',dict(utc=utc(),pid=os.getpid(),sid=os.getsid(0),affinity=sorted(os.sched_getaffinity(0)),
        nice=os.getpriority(os.PRIO_PROCESS,0),detached=detached,
        threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}))
    start=time.monotonic();log(a,'MAIN_START');graphs=read(a/'GRAPHS.json')
    cases={}
    for name,profile in schedules(graphs['T']).items():
        cases[name]=calculate(graphs,profile);log(a,'SCHEDULE_COMPLETE '+name)
    old_result=read(REFERENCE/'RESULTS.json')
    for n in (4,5,6):
        for name,p in cases[f'constant_{n:02d}']['policies'].items():
            for u,v in zip(p['worlds'],old_result['policies'][name]['worlds']):
                for k in SHARED:assert u[k] is None if v[k] is None else u[k]==sum(F(c)*F(n,100)**j for j,c in enumerate(v[k]))
    switches=[name for name,p in cases.items() if p['profile']['change_task'] is not None]
    result=dict(T=10,rho='1/2',budget=K,cases=cases,switch_cases=switches,
                overall={name:all(cases[s]['gates'][name]['primary']['joint'] for s in switches) for name in TARGETS})
    save(a/'RESULTS.json',result);check_freeze(a);log(a,'MAIN_COMPLETE')
    save(a/'MANIFEST.json',dict(status='COMPLETE',finished=utc(),wall_seconds=time.monotonic()-start,
        outputs={str(p.relative_to(a)):sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable,'-B',str(ROOT/'readback_fep_noise_switch.py'),str(a)],stdout=out,stderr=subprocess.STDOUT,check=True)
    print('READBACK_COMPLETE '+str(a),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',default='attempt-01')
    parser.add_argument('--main-only',action='store_true');parser.add_argument('--detached',action='store_true');args=parser.parse_args()
    assert args.attempt.startswith('attempt-') and '/' not in args.attempt and Path('/mnt/bioIce1').is_mount()
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
            paths=[ROOT/n for n in SOURCES+REFERENCES]+[REFERENCE/n for n in ('GRAPHS.json','RESULTS.json','MANIFEST.json','READBACK.json')]
            save(a/'FREEZE.json',dict(created=utc(),inputs={str(p):sha(p) for p in paths},snapshots={n:sha(a/'inputs'/n) for n in SOURCES},
                python=platform.python_version(),T=10,rho='1/2',budget=K,noise_endpoints=[4,6],switch_tasks=list(range(2,11))))
            (a/'GRAPHS.json').write_bytes((REFERENCE/'GRAPHS.json').read_bytes())
            log(a,'QUALIFICATION_START');start=time.monotonic();q,fixtures=qualify();q['seconds']=time.monotonic()-start
            save(a/'QUALIFICATION.json',q);save(a/'SHORT_FIXTURES.json',fixtures);log(a,'QUALIFICATION_PASS')
            short=old.truncate(read(a/'GRAPHS.json'),7);start=time.monotonic()
            for profile in [schedule(7,4,6,4),schedule(7,6,4,4)]:calculate(short,profile)
            seconds=time.monotonic()-start;forecast=120+6*(21/2)*2**3*seconds
            save(a/'BENCHMARK.json',dict(T=7,rho='1/3',timing_only=True,change_task=4,directions=2,seconds=seconds,forecast_seconds=forecast))
            log(a,'BENCHMARK_COMPLETE')
            if forecast>7200:log(a,'FEASIBILITY_CEILING_EXCEEDED');return
            if forecast>600:print('DETACHED_MAIN_REQUIRED',flush=True);return
        run_main(a,args.detached)
    except Exception as error:
        name='READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/name).exists():save(a/name,dict(utc=utc(),error=repr(error)))
        raise


if __name__=='__main__':main()
