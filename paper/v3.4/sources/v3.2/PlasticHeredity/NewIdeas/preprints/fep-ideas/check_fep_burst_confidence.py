#!/usr/bin/env python3
"""Exact stationary Markov error bursts on frozen observable policy graphs."""
from fractions import Fraction as F
from pathlib import Path
import argparse
import os
import platform
import subprocess
import sys
import time

import check_fep_noise_interval as old
import check_fep_noise_switch as history

ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/bioIce1/fep-ideas/formal-checks')
STORE=BASE/'fep-burst-confidence-v1'
SOURCE=BASE/'fep-noise-sequence-v1/attempt-01'
RESERVE=BASE/'fep-mixture-reserve-v1/attempt-01'
SOURCES=('FEP_BURST_CONFIDENCE_V1.md','check_fep_burst_confidence.py','readback_fep_burst_confidence.py')
REFERENCES=('FEP_BURST_SIDEQUESTS_2026-10-30.md','FEP_NOISE_SEQUENCE_V1_REPORT.md',
            'check_fep_noise_interval.py','check_fep_noise_switch.py')
ALPHAS=(F(0),F(1,4),F(1,2),F(3,4),F(9,10),F(1))
TARGETS=('joint_mixture','fixed_pool')
RAW=('errors','purchases','post_errors','post_purchases','delay','missing','wrong95','any_wrong95',
     'wrong95_errors','adoption_delay','adoption_missing','false_adoption','repeat_events','repeat_increases')
BELIEF=('wrong95','any_wrong95','wrong95_errors','adoption_delay','adoption_missing','false_adoption',
        'repeat_increases','brier','confidence','repeat_gain')
FIELDS=RAW+('brier','confidence','repeat_gain','cost','post_cost','recovery')
K=F(19568652557,204800000000)
save,read,sha,utc,log,check_freeze=old.save,old.read,old.sha,old.utc,old.log,old.check_freeze


def info(graph,belief):
    if belief=='none':return [None]*len(graph)
    if belief=='explicit':return [dict(q=F(n['q_orientation']),post=tuple(map(F,n['post_orientation']))) for n in graph]
    result=[];noises=(4,5,6) if belief=='joint_noise' else (5,)
    for n in graph:
        w=n['weights'];width=len(w)//len(noises);t=n['t']
        states=[(e,j) for e in range(len(noises)) for j in range(width)]
        q=F(sum(v for v,(_,j) in zip(w,states) if 0<j<=t),sum(w))
        post=[]
        for label in (0,1):
            raw=[v*(100-noises[e] if label==int(0<j<=t) else noises[e]) for v,(e,j) in zip(w,states)]
            post.append(F(sum(v for v,(_,j) in zip(raw,states) if 0<j<=t),sum(raw)))
        result.append(dict(q=q,post=tuple(post)))
    return result


def markov(T,alpha):
    a,b=alpha.numerator,alpha.denominator;D=20*b
    transition=((19*b+a,b-a),(19*(b-a),b+19*a));den=20*D**(T-1)
    masses=[]
    for bits in range(1<<T):
        previous=bits&1;mass=1 if previous else 19
        for t in range(1,T):
            current=(bits>>t)&1;mass*=transition[previous][current];previous=current
        masses.append(mass)
    assert sum(masses)==den
    assert all(sum(m for bits,m in enumerate(masses) if bits>>t&1)*20==den for t in range(T))
    return masses,den


def trace(graph,beliefs,T,tau):
    result=[]
    for bits in range(1<<T):
        row=[0]*len(RAW);i=0;visits=[];repeat_visits=[];last=None;last_wrong=False
        first=None;adopt=None;seen=False
        for t in range(1,T+1):
            n=graph[i];z=(bits>>(t-1))&1;orient=int(tau is not None and t>=tau);d=orient^z
            buy=n['action']=='B';err=int(not buy and d!=int(n['action']=='R'));v=beliefs[i]
            visits.append(i);wrong=False
            if v is not None:
                wrong=(v['q'] if not orient else 1-v['q'])>=F(19,20)
                row[6]+=wrong;seen=seen or wrong;row[8]+=wrong and err
                row[11]+=not orient and v['q']>=F(9,10)
                if orient and adopt is None and v['q']>=F(9,10):adopt=t
            row[0]+=err;row[1]+=buy
            if orient:
                row[2]+=err;row[3]+=buy
                if buy and first is None:first=t
            if buy:
                if last_wrong and z and last==d:
                    row[12]+=1;repeat_visits.append(i)
                    if v is not None:
                        gain=(v['post'][d]-v['q'])*(1 if not orient else -1)
                        row[13]+=gain>0
                last,last_wrong=d,bool(z)
            i=n['children'][str(d) if buy else 'N']
        assert i is None
        length=0 if tau is None else T-tau+1
        row[4]=length if first is None else first-tau;row[5]=int(first is None);row[7]=int(seen)
        row[9]=length if adopt is None else adopt-tau;row[10]=int(adopt is None)
        result.append((row,visits,repeat_visits))
    return result


def evaluate(graph,beliefs,T,tau,alpha,traces=None):
    masses,den=markov(T,alpha);traces=trace(graph,beliefs,T,tau) if traces is None else traces
    totals=[0]*len(RAW);visits=[0]*len(graph);repeats=[0]*len(graph)
    for mass,(row,seen,rep) in zip(masses,traces):
        if not mass:continue
        for j,x in enumerate(row):totals[j]+=mass*x
        for i in seen:visits[i]+=mass
        for i in rep:repeats[i]+=mass
    out=dict(onset=tau,**{k:F(v,den) for k,v in zip(RAW,totals)})
    if beliefs[0] is None:
        out.update({k:None for k in BELIEF})
    else:
        brier=confidence=gain=F(0)
        for i,n in enumerate(graph):
            truth=int(tau is not None and n['t']>=tau);v=beliefs[i];q=v['q']
            brier+=visits[i]*(q-truth)**2;confidence+=visits[i]*max(q,1-q)
            gain+=repeats[i]*(v['post'][1-truth]-q)*(1 if not truth else -1)
        out.update(brier=brier/den,confidence=confidence/den,repeat_gain=gain/den)
    out['cost']=out['errors']+out['purchases']/10;out['post_cost']=out['post_errors']+out['post_purchases']/10
    out['recovery']=None if tau is None else out['post_cost']/(T-tau+1)
    return out


def summarize(ws,T,rho):
    def prior_(k):return None if ws[0][k] is None else (1-rho)*ws[0][k]+rho*sum(w[k] for w in ws[1:])/T
    def div(v,n):return None if v is None else v/n
    s=ws[0]['cost']/T;b=prior_('cost')/T;r=sum(w['recovery'] for w in ws[1:])/T
    out=dict(stable=s,B=b,R=r,J=b+r,stable_errors=ws[0]['errors'],stable_purchases=ws[0]['purchases'],
        mean_post_errors=sum(w['post_errors'] for w in ws[1:])/T,mean_post_purchases=sum(w['post_purchases'] for w in ws[1:])/T,
        mean_pre_purchases=sum(w['purchases']-w['post_purchases'] for w in ws[1:])/T,
        capped_first_delay=sum(w['delay'] for w in ws[1:])/T,no_post_purchase_probability=sum(w['missing'] for w in ws[1:])/T)
    for k in ('brier','confidence','wrong95','wrong95_errors','false_adoption'):
        out['stable_'+k]=div(ws[0][k],T);out['prior_'+k]=div(prior_(k),T)
    for k in ('any_wrong95','repeat_events','repeat_increases','repeat_gain'):
        out['stable_'+k]=ws[0][k];out['prior_'+k]=prior_(k)
    out['mean_adoption_delay']=None if ws[0]['adoption_delay'] is None else sum(w['adoption_delay'] for w in ws[1:])/T
    out['no_adoption_probability']=None if ws[0]['adoption_missing'] is None else sum(w['adoption_missing'] for w in ws[1:])/T
    return out


def record(graph,belief,T,rho,alpha,traces=None):
    beliefs=info(graph,belief)
    ws=[evaluate(graph,beliefs,T,tau,alpha,None if traces is None else traces[j]) for j,tau in enumerate([None,*range(1,T+1)])]
    return dict(worlds=ws,summary=summarize(ws,T,rho))


def mix(ps,cs,T,rho):
    assert sum(F(c['weight']) for c in cs)==1
    ws=[]
    for j,tau in enumerate([None,*range(1,T+1)]):
        row=dict(onset=tau)
        for k in FIELDS:
            vals=[(F(c['weight']),ps[c['policy']]['worlds'][j][k]) for c in cs]
            row[k]=None if any(v is None for _,v in vals) else sum(w*v for w,v in vals)
        ws.append(row)
    return dict(components=cs,worlds=ws,summary=summarize(ws,T,rho))


def gates(s,h):return dict(stable=s['stable']<=K,always_recovery=s['R']<F(1,10),hybrid_recovery=s['R']<h['R'],
    matched_stable=s['stable']<=h['stable'],hybrid_full=s['B']<h['B'],always_full=s['B']<F(1,10))


def calculate(g,mixtures,alphas=ALPHAS):
    T=g['T'];rho=F(g['rho']);graphs=dict(g['graphs'])
    graphs['always']=dict(belief='none',graph=[dict(t=t,action='B',children={str(d):t if t<T else None for d in (0,1)}) for t in range(1,T+1)])
    traces={n:[trace(p['graph'],info(p['graph'],p['belief']),T,tau) for tau in [None,*range(1,T+1)]] for n,p in graphs.items()}
    cases={}
    for alpha in alphas:
        ps={n:record(p['graph'],p['belief'],T,rho,alpha,traces[n]) for n,p in graphs.items()}
        for n,cs in mixtures.items():ps[n]=mix(ps,cs,T,rho)
        gate={n:gates(ps[n]['summary'],ps['hybrid']['summary']) for n in mixtures}
        comparisons={}
        for n in TARGETS:
            comparisons[n]={}
            for c in ('hybrid','always','old_'+n):
                comparisons[n][c]=dict(summary={k:None if ps[c]['summary'][k] is None else ps[n]['summary'][k]-ps[c]['summary'][k] for k in ps[n]['summary']},
                    worlds=[dict(onset=u['onset'],full=(u['cost']-v['cost'])/T,recovery=None if u['recovery'] is None else u['recovery']-v['recovery'])
                            for u,v in zip(ps[n]['worlds'],ps[c]['worlds'])])
        cases[str(alpha)]=dict(alpha=alpha,marginal=F(1,20),mean_error_run=None if alpha==1 else 1/(F(19,20)*(1-alpha)),
                               policies=ps,gates=gate,comparisons=comparisons)
    if '0' in cases:
        for case in cases.values():
            case['independence_deltas']={n:{k:None if v is None else v-cases['0']['policies'][n]['summary'][k]
                for k,v in case['policies'][n]['summary'].items()} for n in TARGETS}
    return dict(T=T,rho=rho,budget=K,alphas=alphas,cases=cases,
        overall={n:all(all(c['gates'][n][k] for k in ('stable','always_recovery','hybrid_recovery')) for c in cases.values()) for n in TARGETS})


def qualify():
    import readback_fep_burst_confidence as audit
    checks=0;fixtures=[]
    for T in (1,2,3):
        for j,tree in enumerate(old.trees(T)):
            graph=history.graph_from_tree(tree,T,F(1,2),'nominal_5_percent')
            for tau in [None,*range(1,T+1)]:
                qs=info(graph,'nominal_5_percent');tr=trace(graph,qs,T,tau)
                for alpha in ALPHAS:
                    x=evaluate(graph,qs,T,tau,alpha,tr);y=audit.forward(graph,audit.beliefs(graph,'nominal_5_percent'),T,tau,alpha)
                    assert x==y;(checks:=checks+1)
            if j in (0,len(old.trees(T))//2,len(old.trees(T))-1):fixtures.append(dict(T=T,graph=graph,belief='nominal_5_percent'))
    for T in (1,3,10):
        for alpha in ALPHAS:
            masses,den=markov(T,alpha)
            assert sum(masses)==den;checks+=1
            for lag in range(1,T):
                joint=F(sum(m for bits,m in enumerate(masses) if bits&1 and bits>>lag&1),den)
                assert joint==F(1,400)+F(19,400)*alpha**lag;checks+=1
    # Equality belongs to the wrong-confidence/adoption thresholds.
    graph=[dict(t=1,action='F',children={'N':None},q_orientation='1/20',post_orientation=['1/20','1/20'])]
    x=evaluate(graph,info(graph,'explicit'),1,1,F(0));assert x['wrong95']==1 and x['wrong95_errors']==F(19,20);checks+=1
    graph=[dict(t=1,action='F',children={'N':None},q_orientation='9/10',post_orientation=['9/10','9/10'])]
    x=evaluate(graph,info(graph,'explicit'),1,1,F(0));assert x['adoption_delay']==0 and x['adoption_missing']==0;checks+=1
    graph=history.graph_from_tree(old.trees(3)[-1],3,F(1,3),'nominal_5_percent')
    x=evaluate(graph,info(graph,'nominal_5_percent'),3,None,F(1))
    assert x['repeat_events']==x['repeat_increases']==F(1,10) and x['errors']==0 and x['repeat_gain']>0;checks+=1
    p=record(graph,'nominal_5_percent',3,F(1,3),F(1,2))
    qgraph=history.graph_from_tree(old.trees(3)[0],3,F(1,3),'nominal_5_percent')
    q=record(qgraph,'nominal_5_percent',3,F(1,3),F(1,2))
    mixed=mix({'p':p,'q':q},[dict(policy='p',weight=F(2,7)),dict(policy='q',weight=F(5,7))],3,F(1,3))
    for k,v in mixed['summary'].items():
        assert v==F(2,7)*p['summary'][k]+F(5,7)*q['summary'][k];checks+=1
    return dict(passed=True,checks=checks,trees=273,world_settings=1071*6),fixtures


def main_run(a,detached):
    check_freeze(a);forecast=read(a/'BENCHMARK.json')['forecast_seconds']
    assert forecast<=7200 and (forecast<=600 or detached)
    save(a/'STARTED.json',dict(utc=utc(),pid=os.getpid(),sid=os.getsid(0),nice=os.getpriority(os.PRIO_PROCESS,0),
        affinity=sorted(os.sched_getaffinity(0)),detached=detached))
    start=time.monotonic();log(a,'MAIN_START');g=read(a/'GRAPHS.json');mixes=read(a/'MIXTURES.json')
    result=calculate(g,mixes);save(a/'RESULTS.json',result)
    previous=read(SOURCE/'DIAGNOSTICS.json')['constant_05']['policies'];checks=0
    for name,p in result['cases']['0']['policies'].items():
        for u,v in zip(p['worlds'],previous[name]['worlds']):
            for k in ('cost','errors','purchases','post_cost','post_errors','post_purchases','delay','missing','recovery'):
                assert u[k] is None if v[k] is None else u[k]==F(v[k]);checks+=1
            assert u['brier'] is None if v['orientation_brier'] is None else u['brier']==F(v['orientation_brier']);checks+=1
    save(a/'REPRODUCTION.json',dict(passed=True,checks=checks));check_freeze(a);log(a,'MAIN_COMPLETE')
    save(a/'MANIFEST.json',dict(status='COMPLETE',finished=utc(),wall_seconds=time.monotonic()-start,
        outputs={str(p.relative_to(a)):sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable,'-B',str(ROOT/'readback_fep_burst_confidence.py'),str(a)],stdout=out,stderr=subprocess.STDOUT,check=True)
    print('READBACK_COMPLETE '+str(a),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--attempt',default='attempt-01');p.add_argument('--main-only',action='store_true');p.add_argument('--detached',action='store_true');args=p.parse_args()
    assert args.attempt.startswith('attempt-') and '/' not in args.attempt and Path('/mnt/bioIce1').is_mount()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    if os.getpriority(os.PRIO_PROCESS,0)<10:os.nice(10-os.getpriority(os.PRIO_PROCESS,0))
    a=STORE/args.attempt
    if args.main_only:assert a.is_dir() and not (a/'STARTED.json').exists()
    else:a.mkdir(parents=True,exist_ok=False)
    try:
        if not args.main_only:
            (a/'inputs').mkdir()
            for n in SOURCES:(a/'inputs'/n).write_bytes((ROOT/n).read_bytes())
            paths=[ROOT/n for n in SOURCES+REFERENCES]+[SOURCE/n for n in ('GRAPHS.json','MIXTURES.json','DIAGNOSTICS.json','MANIFEST.json','READBACK.json')]
            v=read(SOURCE/'READBACK.json');m=read(SOURCE/'MANIFEST.json')
            assert v['passed'] and v['manifest_sha256']==sha(SOURCE/'MANIFEST.json')
            for n in ('GRAPHS.json','MIXTURES.json','DIAGNOSTICS.json'):assert m['outputs'][n]==sha(SOURCE/n)
            save(a/'FREEZE.json',dict(created=utc(),inputs={str(p):sha(p) for p in paths},snapshots={n:sha(a/'inputs'/n) for n in SOURCES},
                python=platform.python_version(),T=10,rho='1/2',marginal='1/20',alphas=ALPHAS,budget=K))
            for n in ('GRAPHS.json','MIXTURES.json'):(a/n).write_bytes((SOURCE/n).read_bytes())
            log(a,'QUALIFICATION_START');start=time.monotonic();q,fixtures=qualify();q['seconds']=time.monotonic()-start
            save(a/'QUALIFICATION.json',q);save(a/'FIXTURES.json',fixtures);log(a,'QUALIFICATION_PASS')
            short=old.truncate(read(a/'GRAPHS.json'),7);start=time.monotonic()
            for item in short['graphs'].values():record(item['graph'],item['belief'],7,F(1,3),F(1,2))
            seconds=time.monotonic()-start;forecast=120+4*6*(11/8)*2**3*seconds
            save(a/'BENCHMARK.json',dict(T=7,graphs=5,worlds=8,alpha='1/2',seconds=seconds,forecast_seconds=forecast,timing_only=True));log(a,'BENCHMARK_COMPLETE')
            if forecast>7200:log(a,'FEASIBILITY_CEILING_EXCEEDED');return
            if forecast>600:print('DETACHED_MAIN_REQUIRED',flush=True);return
        main_run(a,args.detached)
    except Exception as e:
        name='READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/name).exists():save(a/name,dict(utc=utc(),error=repr(e)))
        raise


if __name__=='__main__':main()
