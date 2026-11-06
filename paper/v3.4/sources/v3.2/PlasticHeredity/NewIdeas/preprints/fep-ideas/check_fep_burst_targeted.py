#!/usr/bin/env python3
"""Generate targeted policies, certify development selection, freeze and test."""
from fractions import Fraction as F
from pathlib import Path
import argparse
import os
import platform
import subprocess
import sys
import time

import check_fep_noise_interval as io
import check_fep_burst_learning as history
import check_fep_burst_pool_feasibility as predecessor
import fep_burst_targeted_core as core

ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/bioIce1/fep-ideas/formal-checks')
STORE=BASE/'fep-burst-targeted-v1'
SOURCE=BASE/'fep-burst-pool-feasibility-v1/attempt-01'
ALLTIMING=BASE/'fep-burst-alltiming-v1/attempt-01'
SOURCES=('FEP_BURST_TARGETED_V1.md','fep_burst_targeted_core.py','check_fep_burst_targeted.py','readback_fep_burst_targeted.py')
REFERENCES=('FEP_BURST_POOL_FEASIBILITY_V1.md','FEP_BURST_POOL_FEASIBILITY_V1_REPORT.md',
    'FEP_BURST_ALLTIMING_V1.md','fep_burst_alltiming_core.py','fep_burst_learning_core.py','fep_burst_pool_core.py',
    'check_fep_burst_learning.py','check_fep_burst_confidence.py','check_fep_burst_pool_feasibility.py',
    'readback_fep_burst_alltiming.py','readback_fep_burst_learning.py','readback_fep_burst_confidence.py',
    'readback_fep_burst_pool_feasibility.py','check_fep_noise_interval.py','check_fep_noise_switch.py')
save,read,sha,utc,log,check_freeze=io.save,io.read,io.sha,io.utc,io.log,io.check_freeze


def baselines():
    graphs=read(SOURCE/'GRAPHS.json')['graphs'];previous=read(ALLTIMING/'EVAL_GRAPHS.json')['graphs']
    oldmix=read(ALLTIMING/'EVAL_MIXTURES.json')
    mixes=dict(previous_pool_full=read(SOURCE/'MIXTURES.json')['selected_full'],previous_full=oldmix['reliability'],
        joint_mixture=oldmix['joint_mixture'],fixed_pool=oldmix['fixed_pool'])
    direct=('hybrid','always','conservative','fixed_schedule')
    for n in {c['policy'] for cs in mixes.values() for c in cs}|set(direct):
        if n not in graphs:graphs[n]=previous[n]
    return dict(graphs=graphs,mixtures=mixes,direct_controls=direct)


def novelty():
    exposed={tuple(p) for p in core.DEVELOPMENT.values()}
    for folder in ('fep-burst-confidence-v1','fep-burst-learning-v1'):
        record=read(BASE/folder/'attempt-01/RESULTS.json')
        exposed.update((F(a),)*9 for a in record['cases'])
    assert len(set(core.HOLDOUT.values()))==8 and not set(core.HOLDOUT.values())&exposed
    return dict(passed=True,previous_profiles=sorted(exposed),new_profiles=core.HOLDOUT)


def qualify():
    import readback_fep_burst_targeted as audit
    checks=trees=states=0
    for T in (1,2,3):
        physical=[]
        for tree in io.trees(T):
            graph=io.graph_from_tree(tree);cost=core.training(graph,T)
            independent=audit.training(graph,T)
            assert cost==independent;checks+=1;trees+=1;physical.append(cost)
        for frozen in (False,True):
            for mu in (0,4):
                model=core.Model(T);oracle=core.Oracle(model,mu,frozen);bayes=audit.Bayesian(T)
                best=min(c['settings']['training_00']['summary']['J']+mu*c['settings']['training_00']['summary']['stable']
                    if frozen else c['C']+mu*sum(c['S'])/2 for c in physical)
                assert oracle.root()==best;checks+=1
                den,coeff=bayes.coefficients(mu);assert den==oracle.den and all(tuple(coeff[t])==oracle.coeff[t] for t in coeff);checks+=1
                graph=oracle.graph()
                for node in graph:
                    expected=bayes.fields(node['t'],tuple(node['weights']))
                    assert all(node[k]==v for k,v in expected.items());checks+=1
                for (t,w) in list(oracle.cache):
                    states+=1
                    if t==T:continue
                    for label in (None,0,1):
                        nw,g=model.step(t,w,label,frozen);expected,prob=bayes.step(t,w,label,frozen)
                        assert nw==expected and F(g*sum(nw),model.D*sum(w))==prob;checks+=1
                        if frozen:
                            assert bayes.fields(t+1,nw)['q_pattern']==F(1,2) and bayes.fields(t+1,nw)['q_error']==F(1,20);checks+=1
                model.step.cache_clear();bayes.step.cache_clear()
    for profile in core.generation(10).values():
        p=F(1,20)
        for alpha in profile:
            p=(1-p)*F(1,20)*(1-alpha)+p*(F(1,20)*(1-alpha)+alpha)
            assert p==F(1,20);checks+=1
    old=read(SOURCE/'COSTS.json')['records']
    records={label:{n:dict(summary={k:F(v) for k,v in p['summary'].items()}) for n,p in ps.items()} for label,ps in old.items()}
    for ps in records.values():
        for family in ('full','ablated'):
            for n in core.pool.names(family)[:-1]:ps['target_'+n]=ps[n]
    hybrid={l:ps['hybrid']['summary']['R'] for l,ps in records.items()};fixtures={}
    for family in ('full','ablated'):
        for expanded in (False,True):
            p=core.problem(records,hybrid,family,expanded);assert p==audit.matrix(records,hybrid,family,expanded);checks+=1
            s=core.pool.solve(p);assert audit.certified.valid_certificate(p,s['certificate']);checks+=1
            assert s['margin']==F(read(SOURCE/'SOLUTIONS.json')[family]['margin']);checks+=1
            fixtures[f'{family}_{expanded}']=s
    return dict(passed=True,checks=checks,short_trees=trees,bellman_states=states),fixtures


def benchmark():
    import readback_fep_burst_targeted as audit
    seconds=0;graphs=[]
    for frozen in (False,True):
        model=core.Model(7);oracle=core.Oracle(model,4,frozen);start=time.monotonic()
        oracle.root();graphs.append(oracle.graph());seconds+=time.monotonic()-start
        model.step.cache_clear()
    start=time.monotonic()
    for graph in graphs:
        beliefs=audit.previous.flow.beliefs(graph,'explicit')
        for profile in core.generation(7).values():
            for tau in [None,*range(1,8)]:audit.previous.forward(graph,beliefs,7,tau,profile)
    diagnostics=(time.monotonic()-start)/4
    forecast=480+4*6*3**3*F(11,8)*seconds+4*18*34*F(11,8)*2**3*diagnostics
    return dict(T=7,oracle_seconds=seconds,diagnostic_seconds_per_graph_profile=diagnostics,
        forecast_seconds=float(forecast),timing_only=True)


def train(a):
    baseline=read(a/'BASELINES.json');graphs=dict(baseline['graphs']);model=core.Model(10)
    (a/'candidates').mkdir();(a/'bellman').mkdir()
    for frozen in (False,True):
        family='ablated' if frozen else 'full'
        for mu in core.MUS:
            name=f'target_{family}_mu{mu:02d}';start=time.monotonic();oracle=core.Oracle(model,mu,frozen)
            value,graph=oracle.root(),oracle.graph();cost=core.training(graph,10)
            expected=cost['settings']['training_00']['summary']['J']+mu*cost['settings']['training_00']['summary']['stable'] if frozen else cost['C']+mu*sum(cost['S'])/2
            assert value==expected
            if frozen:
                old=read(ALLTIMING/'candidates'/f'ablated_mu{mu:02d}.json')
                assert core.same_behavior(graph,old['graph']) and value==F(old['subjective_root'])
            save(a/'candidates'/f'{name}.json',dict(graph=graph,belief='explicit',mu=mu,frozen=frozen,
                training=cost,subjective_root=value,utility_denominator=oracle.den,bellman_states=len(oracle.cache)))
            history.dump_bellman(a/'bellman'/f'{name}.jsonl.gz',oracle)
            graphs[name]=dict(graph=graph,belief='explicit')
            log(a,f'ORACLE_COMPLETE {name} states={len(oracle.cache)} seconds={time.monotonic()-start:.3f}')
    model.step.cache_clear()
    records={};names=set(core.names('full'))|set(core.names('ablated'))|{'hybrid'}
    for label,profile in core.DEVELOPMENT.items():
        records[label]={n:core.pool.cost_record(graphs[n]['graph'],profile) for n in sorted(names)}
        previous_costs=read(SOURCE/'COSTS.json')['records'][label]
        for n,p in previous_costs.items():
            for actual,expected in zip(records[label][n]['worlds'],p['worlds']):
                for k,v in actual.items():assert v==expected[k] if k=='onset' or v is None else v==F(expected[k])
            for k,v in records[label][n]['summary'].items():assert v==F(p['summary'][k])
        log(a,'DEVELOPMENT_COSTS_COMPLETE '+label)
    save(a/'COSTS.json',dict(profiles=core.DEVELOPMENT,records=records))
    hybrid={l:ps['hybrid']['summary']['R'] for l,ps in records.items()};solutions={}
    for kind,expanded in (('original',False),('expanded',True)):
        solutions[kind]={family:core.pool.solve(core.problem(records,hybrid,family,expanded)) for family in ('full','ablated')}
    old=read(SOURCE/'SOLUTIONS.json')
    for family in ('full','ablated'):
        assert solutions['original'][family]['margin']==F(old[family]['margin'])
        assert solutions['expanded'][family]['margin']>=solutions['original'][family]['margin']
    assert solutions['expanded']['ablated']['margin']==solutions['original']['ablated']['margin']
    save(a/'SELECTION.json',solutions)
    mixes=dict(baseline['mixtures']);mixes.update({f'selected_{f}':solutions['expanded'][f]['components'] for f in ('full','ablated')})
    mixes['frozen_reliability']=[dict(policy=c['policy'].replace('full_','ablated_',1),weight=c['weight']) for c in mixes['selected_full']]
    mixes['matched_bayesian']=mixes['selected_full']
    save(a/'MIXTURES.json',mixes);save(a/'GRAPHS.json',dict(T=10,rho='1/2',graphs=graphs))
    diagnostic_names=sorted({c['policy'] for cs in mixes.values() for c in cs}|set(baseline['direct_controls']))
    check_freeze(a)
    save(a/'CANDIDATE_FREEZE.json',dict(created=utc(),diagnostic_graphs=diagnostic_names,heldout_profiles=list(core.HOLDOUT),
        graphs_sha256=sha(a/'GRAPHS.json'),mixtures_sha256=sha(a/'MIXTURES.json'),
        training_files={str(p.relative_to(a)):sha(p) for p in sorted(a.rglob('*')) if p.is_file() and p.name!='RUN_LOG.txt'}))
    log(a,'CANDIDATES_FROZEN')


def test(a):
    frozen=read(a/'CANDIDATE_FREEZE.json')
    for n,h in frozen['training_files'].items():assert sha(a/n)==h,n
    save(a/'TEST_STARTED.json',dict(utc=utc(),candidate_freeze_sha256=sha(a/'CANDIDATE_FREEZE.json')))
    graphs=read(a/'GRAPHS.json')['graphs'];mixes=read(a/'MIXTURES.json');baseline=read(a/'BASELINES.json')
    physical=core.old.physical;names=frozen['diagnostic_graphs']
    traces={n:[physical.trace(graphs[n]['graph'],physical.info(graphs[n]['graph'],graphs[n]['belief']),10,tau) for tau in [None,*range(1,11)]] for n in names}
    controls=tuple(baseline['mixtures'])+tuple(baseline['direct_controls'])+('frozen_reliability','selected_ablated','matched_bayesian')
    cases={};profiles={**core.DEVELOPMENT,**core.HOLDOUT}
    for label,profile in profiles.items():
        ps={n:core.old.record(graphs[n]['graph'],graphs[n]['belief'],profile,traces[n]) for n in names}
        for n,components in mixes.items():ps[n]=core.old.mix(ps,components)
        gs={n:physical.gates(p['summary'],ps['hybrid']['summary']) for n,p in ps.items()}
        comparisons={n:predecessor.compare(ps['selected_full'],ps[n]) for n in controls}
        assert all(v is None or v==0 for v in comparisons['matched_bayesian']['summary'].values())
        cases[label]=dict(profile=profile,held_out_pattern=label in core.HOLDOUT,policies=ps,gates=gs,comparisons=comparisons)
        log(a,'TEST_PROFILE_COMPLETE '+label)
    for case in cases.values():
        case['independence_deltas']={n:{k:None if v is None else v-cases['training_00']['policies'][n]['summary'][k]
            for k,v in case['policies'][n]['summary'].items()} for n in ('selected_full','frozen_reliability','selected_ablated')}
    primary={part:{n:all(all(cases[l]['gates'][n][k] for k in ('stable','always_recovery','hybrid_recovery')) for l in labels)
        for n in ('selected_full','frozen_reliability','selected_ablated')} for part,labels in [('development',core.DEVELOPMENT),('transfer',core.HOLDOUT)]}
    mechanisms={l:{n:dict(lower_R=c['comparisons'][n]['summary']['R']<0,lower_J=c['comparisons'][n]['summary']['J']<0,
        full_stable=c['gates']['selected_full']['stable'],comparator_stable=c['gates'][n]['stable']) for n in ('frozen_reliability','selected_ablated')} for l,c in cases.items()}
    save(a/'RESULTS.json',dict(T=10,rho='1/2',budget=core.K,profiles=profiles,heldout_profiles=list(core.HOLDOUT),
        primary_pass=primary,deployment_ready=primary['development']['selected_full'] and primary['transfer']['selected_full'],cases=cases,mechanisms=mechanisms))
    for n,h in frozen['training_files'].items():assert sha(a/n)==h,n


def run(a,detached):
    check_freeze(a);forecast=read(a/'BENCHMARK.json')['forecast_seconds']
    assert forecast<=7200 and (forecast<=600 or detached)
    save(a/'STARTED.json',dict(utc=utc(),pid=os.getpid(),sid=os.getsid(0),nice=os.getpriority(os.PRIO_PROCESS,0),
        affinity=sorted(os.sched_getaffinity(0)),detached=detached))
    start=time.monotonic();log(a,'GENERATION_START');train(a);log(a,'TRANSFER_START');test(a);check_freeze(a);log(a,'MAIN_COMPLETE')
    save(a/'MANIFEST.json',dict(status='COMPLETE',finished=utc(),wall_seconds=time.monotonic()-start,
        outputs={str(p.relative_to(a)):sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable,'-B',str(ROOT/'readback_fep_burst_targeted.py'),str(a)],stdout=out,stderr=subprocess.STDOUT,check=True)
    print('READBACK_COMPLETE '+str(a),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',default='attempt-01');parser.add_argument('--main-only',action='store_true');parser.add_argument('--detached',action='store_true');args=parser.parse_args()
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
            paths=[ROOT/n for n in SOURCES+REFERENCES]
            for directory,files in [(SOURCE,('GRAPHS.json','MIXTURES.json','COSTS.json','SOLUTIONS.json')),
                    (ALLTIMING,('EVAL_GRAPHS.json','EVAL_MIXTURES.json')),
                    (BASE/'fep-burst-confidence-v1/attempt-01',('RESULTS.json',)),
                    (BASE/'fep-burst-learning-v1/attempt-01',('RESULTS.json',))]:
                manifest=read(directory/'MANIFEST.json');audit=read(directory/'READBACK.json')
                assert audit['passed'] and audit['manifest_sha256']==sha(directory/'MANIFEST.json')
                paths.extend(directory/n for n in ('MANIFEST.json','READBACK.json',*files))
                for n in files:assert sha(directory/n)==manifest['outputs'][n]
            oldmanifest=read(ALLTIMING/'MANIFEST.json')
            for mu in core.MUS:
                path=ALLTIMING/'candidates'/f'ablated_mu{mu:02d}.json';paths.append(path)
                assert sha(path)==oldmanifest['outputs'][str(path.relative_to(ALLTIMING))]
            save(a/'FREEZE.json',dict(created=utc(),inputs={str(p):sha(p) for p in paths},snapshots={n:sha(a/'inputs'/n) for n in SOURCES},python=platform.python_version()))
            save(a/'BASELINES.json',baselines());model=core.Model(10)
            save(a/'MODEL.json',dict(T=10,D=model.D,p='1/20',rho='1/2',prior=model.prior,states=model.states,
                generation=core.generation(10),development=core.DEVELOPMENT,heldout=core.HOLDOUT,loss_onsets=list(range(1,11))))
            save(a/'NOVELTY.json',novelty());log(a,'QUALIFICATION_START');start=time.monotonic();qualification,fixtures=qualify()
            qualification['seconds']=time.monotonic()-start;save(a/'QUALIFICATION.json',qualification);save(a/'LP_FIXTURES.json',fixtures);log(a,'QUALIFICATION_PASS')
            b=benchmark();save(a/'BENCHMARK.json',b);log(a,'BENCHMARK_COMPLETE')
            if b['forecast_seconds']>7200:log(a,'FEASIBILITY_CEILING_EXCEEDED');return
            if b['forecast_seconds']>600:print('DETACHED_MAIN_REQUIRED',flush=True);return
        run(a,args.detached)
    except Exception as error:
        n='READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/n).exists():save(a/n,dict(utc=utc(),error=repr(error)))
        raise


if __name__=='__main__':main()
