#!/usr/bin/env python3
"""Exact development-pool feasibility followed by both requested FEP checks."""
from fractions import Fraction as F
from pathlib import Path
import argparse
import copy
import os
import platform
import subprocess
import sys
import time

import check_fep_noise_interval as io
import fep_burst_pool_core as core

ROOT = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
STORE = BASE/'fep-burst-pool-feasibility-v1'
SOURCE = BASE/'fep-burst-alltiming-v1/attempt-01'
SOURCES = ('FEP_BURST_POOL_FEASIBILITY_V1.md','fep_burst_pool_core.py',
           'check_fep_burst_pool_feasibility.py','readback_fep_burst_pool_feasibility.py')
REFERENCES = ('FEP_BURST_ALLTIMING_V1.md','FEP_BURST_ALLTIMING_V1_REPORT.md',
    'fep_burst_alltiming_core.py','fep_burst_learning_core.py','check_fep_burst_learning.py',
    'check_fep_burst_confidence.py','readback_fep_burst_alltiming.py','readback_fep_burst_learning.py',
    'readback_fep_burst_confidence.py','check_fep_noise_interval.py','check_fep_noise_switch.py')
CONTROLS = dict(previous_full='reliability',previous_ablation='frozen_reliability',
    joint_mixture='joint_mixture',fixed_pool='fixed_pool',hybrid='hybrid',always='always',
    conservative='conservative',fixed_schedule='fixed_schedule')
save,read,sha,utc,log,check_freeze = io.save,io.read,io.sha,io.utc,io.log,io.check_freeze


def convert(record):
    result = dict(worlds=[{k:v if k=='onset' or v is None else F(v) for k,v in row.items()} for row in record['worlds']],
                  summary={k:None if v is None else F(v) for k,v in record['summary'].items()})
    if 'components' in record:
        result['components']=[dict(policy=c['policy'],weight=F(c['weight'])) for c in record['components']]
    return result


def compare(a,b):
    return dict(summary={k:None if value is None or b['summary'][k] is None else value-b['summary'][k]
        for k,value in a['summary'].items()},worlds=[dict(onset=x['onset'],full=(x['cost']-y['cost'])/10,
        recovery=None if x['recovery'] is None else x['recovery']-y['recovery']) for x,y in zip(a['worlds'],b['worlds'])])


def select(a):
    graphs=read(a/'GRAPHS.json')['graphs'];prior=read(SOURCE/'RESULTS.json');records={};checks=0
    for label,profile in core.PROFILES.items():
        ps={name:core.cost_record(p['graph'],profile) for name,p in graphs.items()}
        records[label]=ps
        for name,p in ps.items():
            known=prior['cases'][label]['policies'].get(name)
            if known is not None:
                for actual,expected in zip(p['worlds'],known['worlds']):
                    for key,value in actual.items():
                        assert value==expected[key] if key=='onset' or value is None else value==F(expected[key])
                        checks+=1
                for key,value in p['summary'].items():
                    assert value==F(known['summary'][key]);checks+=1
        log(a,'COST_PROFILE_COMPLETE '+label)
    for family in core.FAMILIES:
        for name in core.names(family):
            source=read(SOURCE/'candidates'/f'{name}.json')
            for label,alpha in [('training_00','0'),('training_75','3/4')]:
                old=source['training']['settings'][alpha]
                for actual,expected in zip(records[label][name]['worlds'],old['worlds']):
                    for key,value in actual.items():
                        assert value==expected[key] if key=='onset' or value is None else value==F(expected[key]);checks+=1
                for key in ('stable','B','R'):
                    assert records[label][name]['summary'][key]==F(old[key]);checks+=1
    save(a/'COSTS.json',dict(profiles=core.PROFILES,records=records))
    save(a/'REPRODUCTION.json',dict(passed=True,checks=checks))
    hybrid={label:ps['hybrid']['summary']['R'] for label,ps in records.items()}
    solutions={family:core.solve(core.problem(records,hybrid,family)) for family in core.FAMILIES}
    save(a/'SOLUTIONS.json',solutions)
    mixes=dict(selected_full=solutions['full']['components'],selected_ablated=solutions['ablated']['components'])
    mixes['frozen_reliability']=[dict(policy=c['policy'].replace('full_','ablated_',1),weight=c['weight']) for c in mixes['selected_full']]
    mixes['matched_bayesian']=mixes['selected_full']
    save(a/'MIXTURES.json',mixes)
    diag_names=sorted({c['policy'] for cs in mixes.values() for c in cs})
    check_freeze(a)
    files=[p for p in sorted(a.rglob('*')) if p.is_file() and p.name!='RUN_LOG.txt']
    save(a/'SELECTION_FREEZE.json',dict(created=utc(),development_only=True,diagnostic_components=diag_names,
        feasibility={k:v['feasible'] for k,v in solutions.items()},mixtures_sha256=sha(a/'MIXTURES.json'),
        selection_files={str(p.relative_to(a)):sha(p) for p in files}))
    log(a,'SELECTION_FROZEN')


def diagnostics(a):
    frozen=read(a/'SELECTION_FREEZE.json')
    for name,digest in frozen['selection_files'].items():
        assert sha(a/name)==digest,name
    save(a/'CHECKS_STARTED.json',dict(utc=utc(),selection_freeze_sha256=sha(a/'SELECTION_FREEZE.json')))
    graphs=read(a/'GRAPHS.json')['graphs'];mixes=read(a/'MIXTURES.json');solutions=read(a/'SOLUTIONS.json')
    names=frozen['diagnostic_components'];physical=core.previous.physical
    traces={n:[physical.trace(graphs[n]['graph'],physical.info(graphs[n]['graph'],graphs[n]['belief']),10,tau)
               for tau in [None,*range(1,11)]] for n in names}
    prior=read(SOURCE/'RESULTS.json');cases={}
    for label,profile in core.PROFILES.items():
        ps={n:core.previous.record(graphs[n]['graph'],graphs[n]['belief'],profile,traces[n]) for n in names}
        for name,components in mixes.items():
            ps[name]=core.previous.mix(ps,components)
        for name,source_name in CONTROLS.items():
            ps[name]=convert(prior['cases'][label]['policies'][source_name])
        gates={n:physical.gates(p['summary'],ps['hybrid']['summary']) for n,p in ps.items()}
        comparisons={n:compare(ps['selected_full'],ps[n]) for n in (*CONTROLS,'frozen_reliability','selected_ablated','matched_bayesian')}
        assert all(v is None or v==0 for v in comparisons['matched_bayesian']['summary'].values())
        assert gates['selected_full']['stable'] and gates['selected_ablated']['stable']
        cases[label]=dict(profile=profile,policies=ps,gates=gates,comparisons=comparisons)
        log(a,'FEP_CHECKS_PROFILE_COMPLETE '+label)
    targets=('selected_full','frozen_reliability','selected_ablated')
    for label,case in cases.items():
        case['independence_deltas']={n:{k:None if v is None else v-cases['training_00']['policies'][n]['summary'][k]
            for k,v in case['policies'][n]['summary'].items()} for n in targets}
        delta=case['independence_deltas']['selected_full']
        case['false_confidence_pattern']={k:delta[k]>0 for k in
            ('stable_confidence','stable_wrong95','stable_brier','stable','prior_wrong95_errors')}
    primary={n:all(all(c['gates'][n][k] for k in ('stable','always_recovery','hybrid_recovery')) for c in cases.values())
             for n in targets}
    assert primary['selected_full']==solutions['full']['feasible']
    assert primary['selected_ablated']==solutions['ablated']['feasible']
    mechanisms={label:{n:dict(lower_R=c['comparisons'][n]['summary']['R']<0,
        lower_J=c['comparisons'][n]['summary']['J']<0,full_stable=c['gates']['selected_full']['stable'],
        comparator_stable=c['gates'][n]['stable']) for n in ('frozen_reliability','selected_ablated')} for label,c in cases.items()}
    save(a/'RESULTS.json',dict(T=10,rho='1/2',budget=core.K,development_only=True,profiles=core.PROFILES,
        primary_pass=primary,pool_margin_difference=F(solutions['full']['margin'])-F(solutions['ablated']['margin']),
        cases=cases,mechanisms=mechanisms))
    for name,digest in frozen['selection_files'].items():
        assert sha(a/name)==digest,name


def qualify():
    import readback_fep_burst_pool_feasibility as audit
    checks=0;fixtures=[]
    examples=[([[1]],[2],[1]),([[1,1],[1,0],[0,1]],[1,1,1],[1,1]),
        ([[1,-1],[-1,1],[1,0],[0,1]],[0,0,2,2],[2,1]),
        ([[F(1,2),F(-11,2),F(-5,2),9],[F(1,2),F(-3,2),F(-1,2),1],[1,0,0,0]],
         [0,0,1],[10,-57,-9,-24]),
        ([[2,1],[1,3],[1,0],[0,1]],[3,4,2,2],[3,2])]
    for A,b,c in examples:
        A=[[F(v) for v in row] for row in A];b=list(map(F,b));c=list(map(F,c))
        p=dict(A=A,b=b,c=c);s=core.simplex(A,b,c)
        assert s['objective']==audit.vertex_optimum(A,b,c) and audit.valid_certificate(p,s);checks+=1
        for key in ('x','dual'):
            broken=copy.deepcopy(s);broken[key][0]=F(-1)
            assert not audit.valid_certificate(p,broken);checks+=1
        fixtures.append(dict(problem=p,certificate=s))
    margin_fixtures=[]
    for stable,recovery,expected_sign in [(F(9,100),F(8,100),1),(F(5,100),F(95,1000),0),
            (F(5,100),F(11,100),-1),(F(2,10),F(2,100),-1)]:
        records={'fixture':{n:dict(summary=dict(stable=stable,R=recovery)) for n in core.names('full')}}
        records['fixture']['full_floor']=dict(summary=dict(stable=F(1,20),R=F(19,20)))
        p=core.problem(records,{'fixture':F(95,1000)},'full',profile_order=['fixture'])
        solution=core.solve(p);certificate=solution['certificate']
        assert audit.valid_certificate(p,certificate)
        # The six non-floor columns are identical, so aggregating them gives
        # an equivalent two-variable problem with an independently enumerated optimum.
        assert all(all(v==row[0] for v in row[:6]) for row in p['A'])
        reduced=[[row[0],row[-1]] for row in p['A']]
        assert certificate['objective']==audit.vertex_optimum(reduced,p['b'],[F(0),F(1)])
        assert (solution['margin']>0)-(solution['margin']<0)==expected_sign
        assert sum(c['weight']*records['fixture'][c['policy']]['summary']['stable'] for c in solution['components'])<=core.K
        checks+=4;margin_fixtures.append(dict(records=records,hybrid={'fixture':F(95,1000)},solution=solution))
    worlds=trees=0
    for T in (1,2,3):
        profiles=sorted({(F(0),)*(T-1),(F(3,4),)*(T-1),tuple([F(1,4),F(3,4)][:T-1]),tuple([F(3,4),F(1,4)][:T-1])})
        for tree in io.trees(T):
            graph=io.graph_from_tree(tree);trees+=1
            for profile in profiles:
                for tau in [None,*range(1,T+1)]:
                    assert core.costs(graph,profile,T,tau)==audit.physical(graph,profile,T,tau);checks+=1;worlds+=1
    return dict(passed=True,checks=checks,linear_programs=len(fixtures),margin_fixtures=len(margin_fixtures),
                short_trees=trees,physical_worlds=worlds),dict(linear_programs=fixtures,margin_fixtures=margin_fixtures)


def benchmark(a):
    import readback_fep_burst_pool_feasibility as audit
    graphs=read(a/'GRAPHS.json')['graphs'];names=[n for f in core.FAMILIES for n in core.names(f)]
    profile=core.PROFILES['training_00'];physical=core.previous.physical
    start=time.monotonic()
    for n in names:core.cost_record(graphs[n]['graph'],profile)
    costs=time.monotonic()-start;start=time.monotonic()
    traces={n:[physical.trace(graphs[n]['graph'],physical.info(graphs[n]['graph'],graphs[n]['belief']),10,tau)
        for tau in [None,*range(1,11)]] for n in names}
    tracing=time.monotonic()-start;start=time.monotonic()
    for n in names:core.previous.record(graphs[n]['graph'],graphs[n]['belief'],profile,traces[n])
    diagnostics=time.monotonic()-start;start=time.monotonic()
    for n in names:
        g=graphs[n]['graph'];qs=audit.previous.flow.beliefs(g,graphs[n]['belief'])
        for tau in [None,*range(1,11)]:audit.previous.forward(g,qs,10,tau,profile)
    auditing=time.monotonic()-start
    forecast=60+2*tracing+20*(costs+diagnostics+auditing)
    return dict(T=10,graphs=14,worlds_per_graph=11,profile='training_00',cost_seconds=costs,
        trace_seconds=tracing,diagnostic_seconds=diagnostics,audit_seconds=auditing,
        forecast_seconds=forecast,timing_only=True)


def run(a,detached):
    check_freeze(a);forecast=read(a/'BENCHMARK.json')['forecast_seconds']
    assert forecast<=7200 and (forecast<=600 or detached)
    save(a/'STARTED.json',dict(utc=utc(),pid=os.getpid(),sid=os.getsid(0),nice=os.getpriority(os.PRIO_PROCESS,0),
        affinity=sorted(os.sched_getaffinity(0)),detached=detached))
    start=time.monotonic();log(a,'FEASIBILITY_START');select(a);log(a,'FEP_CHECKS_START');diagnostics(a)
    check_freeze(a);log(a,'MAIN_COMPLETE')
    save(a/'MANIFEST.json',dict(status='COMPLETE',finished=utc(),wall_seconds=time.monotonic()-start,
        outputs={str(p.relative_to(a)):sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable,'-B',str(ROOT/'readback_fep_burst_pool_feasibility.py'),str(a)],stdout=out,stderr=subprocess.STDOUT,check=True)
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
            paths=[ROOT/n for n in SOURCES+REFERENCES]+[SOURCE/n for n in ('EVAL_GRAPHS.json','EVAL_MIXTURES.json','RESULTS.json','MANIFEST.json','READBACK.json')]
            predecessor=read(SOURCE/'MANIFEST.json');audit=read(SOURCE/'READBACK.json')
            assert audit['passed'] and audit['manifest_sha256']==sha(SOURCE/'MANIFEST.json')
            graphs={}
            for family in core.FAMILIES:
                for n in core.names(family):
                    path=SOURCE/'candidates'/f'{n}.json';paths.append(path)
                    assert sha(path)==predecessor['outputs'][str(path.relative_to(SOURCE))]
                    d=read(path);graphs[n]={k:d[k] for k in ('graph','belief')}
            graphs['hybrid']=read(SOURCE/'EVAL_GRAPHS.json')['graphs']['hybrid']
            for n in ('EVAL_GRAPHS.json','EVAL_MIXTURES.json','RESULTS.json'):
                assert sha(SOURCE/n)==predecessor['outputs'][n]
            save(a/'FREEZE.json',dict(created=utc(),inputs={str(p):sha(p) for p in paths},snapshots={n:sha(a/'inputs'/n) for n in SOURCES},
                python=platform.python_version(),profiles=core.PROFILES,development_only=True,budget=core.K))
            save(a/'GRAPHS.json',dict(T=10,rho='1/2',graphs=graphs,pools={f:core.names(f) for f in core.FAMILIES}))
            log(a,'QUALIFICATION_START');start=time.monotonic();q,fixtures=qualify();q['seconds']=time.monotonic()-start
            save(a/'QUALIFICATION.json',q);save(a/'FIXTURES.json',fixtures);log(a,'QUALIFICATION_PASS')
            b=benchmark(a);save(a/'BENCHMARK.json',b);log(a,'BENCHMARK_COMPLETE')
            if b['forecast_seconds']>7200:log(a,'FEASIBILITY_CEILING_EXCEEDED');return
            if b['forecast_seconds']>600:print('DETACHED_MAIN_REQUIRED',flush=True);return
        run(a,args.detached)
    except Exception as error:
        name='READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/name).exists():save(a/name,dict(utc=utc(),error=repr(error)))
        raise


if __name__=='__main__':main()
