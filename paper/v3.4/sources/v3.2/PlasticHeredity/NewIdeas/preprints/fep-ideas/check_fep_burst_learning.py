#!/usr/bin/env python3
"""Frozen selection/test workflow for the authorised reliability-learning study."""
from fractions import Fraction as F
from pathlib import Path
import argparse
import gzip
import itertools
import json
import os
import platform
import subprocess
import sys
import time

import check_fep_noise_interval as io
import check_fep_burst_confidence as physical
import fep_burst_learning_core as core

ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/bioIce1/fep-ideas/formal-checks')
STORE=BASE/'fep-burst-learning-v1'
PREVIOUS=BASE/'fep-noise-sequence-v1/attempt-01'
BURST=BASE/'fep-burst-confidence-v1/attempt-01'
SOURCES=('FEP_BURST_LEARNING_V1.md','fep_burst_learning_core.py','check_fep_burst_learning.py','readback_fep_burst_learning.py')
REFERENCES=('FEP_BURST_CONFIDENCE_V1.md','FEP_BURST_CONFIDENCE_V1_REPORT.md','check_fep_burst_confidence.py',
            'readback_fep_burst_confidence.py','check_fep_noise_interval.py','check_fep_noise_switch.py')
TEST=(F(1,8),F(3,8),F(5,8),F(7,8),F(19,20))
TRAIN=(F(0),F(3,4))
EXTRA=('inverse_delay','inverse_missing','pre_inverse')
save,read,sha,utc,log,check_freeze=io.save,io.read,io.sha,io.utc,io.log,io.check_freeze


def dump_bellman(path,oracle):
    with gzip.open(path,'xt',encoding='utf-8') as out:
        out.write(json.dumps(dict(T=oracle.m.T,mu=str(oracle.mu),frozen=oracle.frozen,D=oracle.m.D,
                                  utility_denominator=oracle.den,states=len(oracle.cache)),sort_keys=True)+'\n')
        for (t,w),value in sorted(oracle.cache.items()):out.write(json.dumps([t,w,value],separators=(',',':'))+'\n')


def select_schedules(model,logger=None):
    records=[];best=None;graph=None
    for mask in range(1<<model.T):
        g=core.graph_for_schedule(model,mask);cost=core.training(g,model.T)
        records.append(dict(mask=mask,training=cost))
        if all(s<=core.K for s in cost['S']):
            key=cost['C'],mask
            if best is None or key<(best['training']['C'],best['mask']):best=records[-1];graph=g
        if logger and mask%128==127:logger('SCHEDULES '+str(mask+1))
    assert best is not None
    return dict(selected=best,records=records),graph


def train(a):
    m=core.Model(10);candidates={};scores={};(a/'candidates').mkdir();(a/'bellman').mkdir()
    for frozen in (False,True):
        prefix='ablated' if frozen else 'full'
        for mu in core.MUS:
            name=f'{prefix}_mu{mu:02d}';start=time.monotonic();oracle=core.Oracle(m,mu,frozen)
            root=oracle.root();graph=oracle.graph();cost=core.training(graph,10)
            subjective=(cost['settings']['0']['C']+mu*cost['settings']['0']['stable']) if frozen else cost['C']+mu*sum(cost['S'])/2
            assert root==subjective,(name,root,subjective)
            item=dict(graph=graph,belief='explicit',mu=mu,frozen=frozen,training=cost,subjective_root=root,
                      utility_denominator=oracle.den,bellman_states=len(oracle.cache))
            save(a/'candidates'/f'{name}.json',item);dump_bellman(a/'bellman'/f'{name}.jsonl.gz',oracle)
            candidates[name]=item
            if not frozen:scores[name]=cost
            log(a,f'ORACLE_COMPLETE {name} states={len(oracle.cache)} seconds={time.monotonic()-start:.3f}')
    floor=core.floor_graph(m);floor_cost=core.training(floor,10)
    for prefix in ('full','ablated'):
        name=prefix+'_floor';item=dict(graph=floor,belief='explicit',mu=None,frozen=prefix=='ablated',training=floor_cost)
        candidates[name]=item;save(a/'candidates'/f'{name}.json',item)
    scores['full_floor']=floor_cost
    selection=core.select_pool(scores);save(a/'SELECTION.json',selection);log(a,'POOL_SELECTED')
    schedules,schedule_graph=select_schedules(m,lambda s:log(a,s));save(a/'SCHEDULES.json',schedules)
    g=read(PREVIOUS/'GRAPHS.json');graphs=dict(g['graphs'])
    for c in selection['selected']['components']:
        for name in (c['policy'],c['policy'].replace('full_','ablated_',1)):
            graphs[name]={k:candidates[name][k] for k in ('graph','belief')}
    graphs['fixed_schedule']=dict(graph=schedule_graph,belief='explicit')
    graphs['conservative']=dict(graph=core.conservative(10),belief='none')
    graphs['always']=dict(graph=[dict(t=t,action='B',children={str(d):t if t<10 else None for d in (0,1)}) for t in range(1,11)],belief='none')
    mixtures=read(PREVIOUS/'MIXTURES.json');mixtures['reliability']=selection['selected']['components']
    mixtures['frozen_reliability']=[dict(policy=c['policy'].replace('full_','ablated_',1),weight=c['weight']) for c in mixtures['reliability']]
    mixtures['matched_bayesian']=mixtures['reliability']
    save(a/'EVAL_GRAPHS.json',dict(T=10,rho='1/2',budget=core.K,graphs=graphs));save(a/'EVAL_MIXTURES.json',mixtures)
    save(a/'MODEL.json',dict(T=10,rho='1/2',p='1/20',alphas=TRAIN,prior=m.prior,states=m.states,D=m.D,
        training_onsets=list(range(1,11,2)),timing_holdout=list(range(2,11,2)),test_alphas=TEST,mus=core.MUS))
    check_freeze(a)
    # The append-only stage log continues after this freeze; freeze immutable
    # training artifacts here and seal the complete log in the final manifest.
    files=[p for p in sorted(a.rglob('*')) if p.is_file() and p.name!='RUN_LOG.txt']
    save(a/'CANDIDATE_FREEZE.json',dict(created=utc(),selected=selection['selected'],fixed_schedule=schedules['selected']['mask'],
        training_files={str(p.relative_to(a)):sha(p) for p in files},
        evaluation_graphs_sha256=sha(a/'EVAL_GRAPHS.json'),evaluation_mixtures_sha256=sha(a/'EVAL_MIXTURES.json'),test_alphas=TEST,
        note='No held-out costs computed before this candidate freeze. Original even-onset support is retained, but its losses are absent from selection.'))
    log(a,'CANDIDATES_FROZEN');m.step.cache_clear()


def extra_worlds(graph,traces,T,tau,alpha):
    masses,den=physical.markov(T,alpha);delay=missing=pre=0
    for mass,(_,visits,_) in zip(masses,traces):
        times=[graph[i]['t'] for i in visits if graph[i]['action']=='R']
        before=[t for t in times if tau is None or t<tau];after=[] if tau is None else [t for t in times if t>=tau]
        pre+=mass*len(before);missing+=mass*int(not after)
        delay+=mass*(0 if tau is None else (after[0]-tau if after else T-tau+1))
    return dict(inverse_delay=F(delay,den),inverse_missing=F(missing,den),pre_inverse=F(pre,den))


def summary(ws,T=10,rho=F(1,2)):
    out=physical.summarize(ws,T,rho)
    out.update(stable_inverse=ws[0]['pre_inverse']/T,mean_inverse_delay=sum(w['inverse_delay'] for w in ws[1:])/T,
               no_inverse_probability=sum(w['inverse_missing'] for w in ws[1:])/T)
    for name,ids in [('odd',list(range(1,T+1,2))),('even',list(range(2,T+1,2)))]:
        out[name+'_B']=(1-rho)*out['stable']+rho*sum(ws[j]['cost'] for j in ids)/(len(ids)*T)
        out[name+'_R']=sum(ws[j]['recovery'] for j in ids)/len(ids)
    return out


def test(a):
    freeze=read(a/'CANDIDATE_FREEZE.json')
    for n,h in freeze['training_files'].items():assert sha(a/n)==h,n
    save(a/'TEST_STARTED.json',dict(utc=utc(),candidate_freeze_sha256=sha(a/'CANDIDATE_FREEZE.json')))
    g=read(a/'EVAL_GRAPHS.json');mixtures=read(a/'EVAL_MIXTURES.json');T=10;rho=F(1,2)
    traces={name:[physical.trace(p['graph'],physical.info(p['graph'],p['belief']),T,tau) for tau in [None,*range(1,11)]] for name,p in g['graphs'].items()}
    cases={}
    for alpha in (*TRAIN,*TEST):
        ps={}
        for name,p in g['graphs'].items():
            record=physical.record(p['graph'],p['belief'],T,rho,alpha,traces[name])
            for j,row in enumerate(record['worlds']):row.update(extra_worlds(p['graph'],traces[name][j],T,row['onset'],alpha))
            record['summary']=summary(record['worlds']);ps[name]=record
        for name,cs in mixtures.items():
            record=physical.mix(ps,cs,T,rho)
            for j,row in enumerate(record['worlds']):
                row.update({k:sum(F(c['weight'])*ps[c['policy']]['worlds'][j][k] for c in cs) for k in EXTRA})
            record['summary']=summary(record['worlds']);ps[name]=record
        gates={name:physical.gates(p['summary'],ps['hybrid']['summary']) for name,p in ps.items()}
        controls=('joint_mixture','fixed_pool','hybrid','always','conservative','fixed_schedule','frozen_reliability','matched_bayesian')
        comparisons={}
        s=ps['reliability']
        for name in controls:
            control=ps[name]
            comparisons[name]=dict(summary={k:None if control['summary'][k] is None else v-control['summary'][k] for k,v in s['summary'].items()},
                worlds=[dict(onset=u['onset'],full=(u['cost']-v['cost'])/10,recovery=None if u['recovery'] is None else u['recovery']-v['recovery']) for u,v in zip(s['worlds'],control['worlds'])])
        assert all(v is None or v==0 for v in comparisons['matched_bayesian']['summary'].values())
        cases[str(alpha)]=dict(alpha=alpha,held_out_duration=alpha in TEST,policies=ps,gates=gates,comparisons=comparisons)
        log(a,'TEST_SETTING_COMPLETE '+str(alpha))
    overall=all(all(cases[str(alpha)]['gates']['reliability'][k] for k in ('stable','always_recovery','hybrid_recovery')) for alpha in TEST)
    result=dict(T=T,rho=rho,budget=core.K,training_alphas=TRAIN,test_alphas=TEST,cases=cases,primary_pass=overall,
        mechanism={str(alpha):dict(lower_R=cases[str(alpha)]['comparisons']['frozen_reliability']['summary']['R']<0,
            lower_J=cases[str(alpha)]['comparisons']['frozen_reliability']['summary']['J']<0,
            full_stable=cases[str(alpha)]['gates']['reliability']['stable'],ablated_stable=cases[str(alpha)]['gates']['frozen_reliability']['stable']) for alpha in TEST})
    save(a/'RESULTS.json',result)
    for n,h in freeze['training_files'].items():assert sha(a/n)==h,n
    return result


def exhaustive(m,mu,frozen):
    values=[]
    for tree in io.trees(m.T):
        graph=io.graph_from_tree(tree);cost=core.training(graph,m.T)
        values.append(cost['settings']['0']['C']+mu*cost['settings']['0']['stable'] if frozen else cost['C']+mu*sum(cost['S'])/2)
    return min(values)


def qualify():
    checks=0;fixtures=[]
    for T in (1,2,3):
        m=core.Model(T)
        for frozen in (False,True):
            for mu in (0,4):
                p=core.Oracle(m,mu,frozen);assert p.root()==exhaustive(m,mu,frozen);checks+=1
                fixtures.append(dict(T=T,mu=mu,frozen=frozen,root=p.root(),graph=p.graph()))
        for d in (0,1,None):
            new,_=m.step(1,m.prior,d,True)
            selected=[v if d is None or d==(int(0<tau<=1)^z) else 0 for v,(_,tau,z) in zip(m.prior,m.states)]
            # Projection leaves every onset with the same class/error conditional.
            for tau in range(T+1):
                cells=[v for v,(_,j,_) in zip(new,m.states) if j==tau]
                assert cells[0]==cells[2]==19*cells[1]==19*cells[3];checks+=1
                before=sum(v for v,(_,j,_) in zip(selected,m.states) if j==tau)
                assert F(sum(cells),sum(new))==F(before,sum(selected));checks+=1
        assert m.step(1,m.prior,None,False)[0]==m.prior;checks+=1
        zero=core.Model(T,(F(0),));w=zero.prior
        for t in range(1,T):
            for label in (None,0,1):
                nextw,_=zero.step(t,w,label,False)
                assert all(nextw[j]==19*nextw[j+1] for j in range(0,len(nextw),2));checks+=1
            w=zero.step(t,w,1,False)[0]
        schedules,_=select_schedules(m)
        assert len(schedules['records'])==2**T and all(x<=core.K for x in schedules['selected']['training']['S']);checks+=1
    synthetic={'a':dict(C=F(2),S=[F(0),F(0)]),'b':dict(C=F(0),S=[F(2),F(0)]),'c':dict(C=F(0),S=[F(0),F(2)])}
    selection=core.select_pool(synthetic,F(1,2));assert selection['selected']['C']==1 and len(selection['selected']['components'])==3;checks+=1
    return dict(passed=True,checks=checks,exhaustive_oracles=12),fixtures


def run(a,detached):
    check_freeze(a);forecast=read(a/'BENCHMARK.json')['forecast_seconds'];assert forecast<=7200 and (forecast<=600 or detached)
    save(a/'STARTED.json',dict(utc=utc(),pid=os.getpid(),sid=os.getsid(0),nice=os.getpriority(os.PRIO_PROCESS,0),
        affinity=sorted(os.sched_getaffinity(0)),detached=detached))
    start=time.monotonic();log(a,'TRAINING_START');train(a);log(a,'TEST_START');test(a);check_freeze(a);log(a,'MAIN_COMPLETE')
    save(a/'MANIFEST.json',dict(status='COMPLETE',finished=utc(),wall_seconds=time.monotonic()-start,
        outputs={str(p.relative_to(a)):sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable,'-B',str(ROOT/'readback_fep_burst_learning.py'),str(a)],stdout=out,stderr=subprocess.STDOUT,check=True)
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
            paths=[ROOT/n for n in SOURCES+REFERENCES]+[PREVIOUS/n for n in ('GRAPHS.json','MIXTURES.json','MANIFEST.json','READBACK.json')]+[BURST/n for n in ('MANIFEST.json','READBACK.json')]
            for d in (PREVIOUS,BURST):
                v=read(d/'READBACK.json');assert v['passed'] and v['manifest_sha256']==sha(d/'MANIFEST.json')
            save(a/'FREEZE.json',dict(created=utc(),inputs={str(p):sha(p) for p in paths},snapshots={n:sha(a/'inputs'/n) for n in SOURCES},
                python=platform.python_version(),training_alphas=TRAIN,test_alphas=TEST,mus=core.MUS,budget=core.K))
            log(a,'QUALIFICATION_START');start=time.monotonic();q,fixtures=qualify();q['seconds']=time.monotonic()-start
            save(a/'QUALIFICATION.json',q);save(a/'FIXTURES.json',fixtures);log(a,'QUALIFICATION_PASS')
            start=time.monotonic();model=core.Model(7)
            for frozen in (False,True):p=core.Oracle(model,4,frozen);p.root();p.graph()
            oracle_seconds=time.monotonic()-start;model.step.cache_clear()
            start=time.monotonic();model=core.Model(5);select_schedules(model);schedule_seconds=time.monotonic()-start;model.step.cache_clear()
            forecast=180+4*6*3**3*(11/8)*oracle_seconds+4*(1024/32)*(11/6)*schedule_seconds
            save(a/'BENCHMARK.json',dict(oracle_T=7,oracle_mu=4,oracle_seconds=oracle_seconds,schedule_T=5,schedule_count=32,
                schedule_seconds=schedule_seconds,forecast_seconds=forecast,timing_only=True));log(a,'BENCHMARK_COMPLETE')
            if forecast>7200:log(a,'FEASIBILITY_CEILING_EXCEEDED');return
            if forecast>600:print('DETACHED_MAIN_REQUIRED',flush=True);return
        run(a,args.detached)
    except Exception as e:
        name='READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/name).exists():save(a/name,dict(utc=utc(),error=repr(e)))
        raise


if __name__=='__main__':main()
