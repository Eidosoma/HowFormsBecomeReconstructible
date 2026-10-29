#!/usr/bin/env python3
"""Independent integer-mass replay of time-varying sensor noise."""
from datetime import datetime, timezone
from fractions import Fraction as Q
from pathlib import Path
import hashlib
import json
import math
import sys
import time

sys.set_int_max_str_digits(0)
FIELDS=('cost','errors','purchases','post_cost','post_errors','post_purchases','delay','missing','recovery',
        'orientation_brier','switch_cost','switch_errors','switch_purchases','switch_delay','switch_missing','switch_brier')


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    start,a=time.monotonic(),Path(sys.argv[1]);counts={}
    totals=dict(noise_paths=0,graph_worlds=0,graph_nodes=0,switch_schedules=0,constant_schedules=0)
    def check(name,ok):
        counts[name]=counts.get(name,0)+1
        if not ok:raise AssertionError(name)
    def equal(saved,actual,label):
        check(label+'_fields',set(saved)==set(actual))
        for k,v in actual.items():check(label,saved[k] is None if v is None else Q(saved[k])==v)
    freeze,manifest,g,r=[load(a/n) for n in ('FREEZE.json','MANIFEST.json','GRAPHS.json','RESULTS.json')]
    check('complete',manifest['status']=='COMPLETE')
    for p,h in freeze['inputs'].items():check('input_hash',sha(p)==h)
    for p,h in freeze['snapshots'].items():check('snapshot_hash',sha(a/'inputs'/p)==h)
    for p,h in manifest['outputs'].items():check('output_hash',sha(a/p)==h)
    source=next(Path(p).parent for p in freeze['inputs'] if p.endswith('/RESULTS.json'))
    old,seal,rb=[load(source/n) for n in ('RESULTS.json','MANIFEST.json','READBACK.json')]
    check('inherited_verified',rb['passed'] and rb['manifest_sha256']==sha(source/'MANIFEST.json'))
    check('inherited_result_hash',seal['outputs']['RESULTS.json']==sha(source/'RESULTS.json'))
    check('frozen_graph_bytes',sha(a/'GRAPHS.json')==sha(source/'GRAPHS.json')==seal['outputs']['GRAPHS.json'])
    T,rho,K=10,Q(1,2),Q(19568652557,204800000000)
    check('main_scope',g['T']==r['T']==T and Q(g['rho'])==Q(r['rho'])==rho and Q(g['budget'])==Q(r['budget'])==K)

    def validate(graph,belief,T,rho,erased=False):
        noises=(4,5,6) if belief=='joint_noise' else (5,)
        block=[T*(rho.denominator-rho.numerator)]+[rho.numerator]*T
        div=math.gcd(*block);initial=tuple(w//div for w in block)*len(noises)
        check('initial_belief',tuple(graph[0]['weights'])==initial and graph[0]['t']==1)
        reached={0};probabilities=[]
        for node in graph:
            w=node['weights'];t=node['t']
            probabilities.append(sum(Q(w[e*(T+1)+j],sum(w)) for e in range(len(noises)) for j in range(1,t+1)))
        for i in sorted(range(len(graph)),key=lambda i:graph[i]['t']):
            node=graph[i];w=tuple(node['weights']);t=node['t'];totals['graph_nodes']+=1
            check('observable_interface',set(node) in ({'t','weights','action','children'},{'t','weights','clock','action','children'})
                  and node['action'] in ('B','F','R') and i in reached)
            check('canonical_belief',len(w)==len(initial) and min(w)>0 and math.gcd(*w)==1)
            if erased:check('erased_prior',w==initial)
            children={'N':w}
            if node['action']=='B':
                children={}
                for d in (0,1):
                    raw=[w[e*(T+1)+j]*(100-n if d==int(0<j<=t) else n) for e,n in enumerate(noises) for j in range(T+1)]
                    div=math.gcd(*raw);children[str(d)]=w if erased else tuple(v//div for v in raw)
            check('observation_mask',set(children)==set(node['children']))
            for label,posterior in children.items():
                child=node['children'][label]
                if t==T:check('graph_terminal',child is None)
                else:
                    check('frozen_likelihood_edge',child is not None and graph[child]['t']==t+1 and tuple(graph[child]['weights'])==posterior)
                    reached.add(child)
        check('complete_graph',len(reached)==len(graph))
        return probabilities

    main_probs={n:validate(p['graph'],p['belief'],T,rho) for n,p in g['graphs'].items()}

    def streams(profile,T):
        records=[]
        for bits in range(1<<T):
            mass=1
            for t,n in enumerate(profile['rates']):mass*=n if (bits>>t)&1 else 100-n
            records.append((bits,mass))
        check('unit_noise_mass',sum(mass for _,mass in records)==100**T)
        return records

    def replay(graph,probabilities,T,tau,profile,paths):
        sigma=profile['change_task'];den=100**T
        e=b=pe=pb=delay=missing=se=sb=sd=sm=0;visits=[0]*len(graph)
        for bits,mass in paths:
            i=0;er=bu=per=pbu=ser=sbu=0;first=firstsw=None
            for t in range(1,T+1):
                node=graph[i];check('replay_time',node['t']==t);visits[i]+=mass
                post=tau is not None and t>=tau;sw=sigma is not None and t>=sigma
                d=int(post)^((bits>>(t-1))&1);buy=node['action']=='B'
                error=0 if buy else int(d==1) if node['action']=='F' else int(d==0)
                er+=error;bu+=buy
                if post:
                    per+=error;pbu+=buy
                    if buy and first is None:first=t
                if sw:
                    ser+=error;sbu+=buy
                    if buy and firstsw is None:firstsw=t
                i=node['children'][str(d) if buy else 'N']
            check('replay_terminal',i is None);totals['noise_paths']+=1
            e+=mass*er;b+=mass*bu;pe+=mass*per;pb+=mass*pbu;se+=mass*ser;sb+=mass*sbu
            delay+=mass*(0 if tau is None else T-tau+1 if first is None else first-tau);missing+=mass*int(first is None)
            sd+=mass*(0 if sigma is None else T-sigma+1 if firstsw is None else firstsw-sigma);sm+=mass*int(firstsw is None)
        check('visit_mass',sum(visits)==T*den)
        br=sum(Q(mass,den)*(probabilities[i]-int(tau is not None and node['t']>=tau))**2 for i,(node,mass) in enumerate(zip(graph,visits)))
        sbr=None if sigma is None else sum(Q(mass,den)*(probabilities[i]-int(tau is not None and node['t']>=tau))**2
                                            for i,(node,mass) in enumerate(zip(graph,visits)) if node['t']>=sigma)
        e,b,pe,pb,delay,missing,se,sb,sd,sm=[Q(v,den) for v in (e,b,pe,pb,delay,missing,se,sb,sd,sm)]
        totals['graph_worlds']+=1
        return dict(onset=tau,cost=e+b/10,errors=e,purchases=b,post_cost=pe+pb/10,post_errors=pe,post_purchases=pb,
            delay=delay,missing=missing,recovery=None if tau is None else (pe+pb/10)/(T-tau+1),orientation_brier=br,
            switch_cost=None if sigma is None else se+sb/10,switch_errors=None if sigma is None else se,
            switch_purchases=None if sigma is None else sb,switch_delay=None if sigma is None else sd,
            switch_missing=None if sigma is None else sm,switch_brier=sbr)

    def summary(worlds,T,rho,profile):
        def p(key):
            return None if worlds[0][key] is None else (1-rho)*worlds[0][key]+rho*sum(w[key] for w in worlds[1:])/T
        def divided(v,n):return None if v is None else v/n
        S=worlds[0]['cost']/T;B=p('cost')/T;R=sum(w['recovery'] for w in worlds[1:])/T
        L=1 if profile['change_task'] is None else T-profile['change_task']+1
        return dict(stable=S,B=B,R=R,J=B+R,stable_errors=worlds[0]['errors'],stable_purchases=worlds[0]['purchases'],
            mean_post_errors=sum(w['post_errors'] for w in worlds[1:])/T,mean_post_purchases=sum(w['post_purchases'] for w in worlds[1:])/T,
            capped_first_delay=sum(w['delay'] for w in worlds[1:])/T,no_post_purchase_probability=sum(w['missing'] for w in worlds[1:])/T,
            stable_orientation_brier=divided(worlds[0]['orientation_brier'],T),prior_orientation_brier=divided(p('orientation_brier'),T),
            switch_cost=divided(p('switch_cost'),L),switch_errors=p('switch_errors'),switch_purchases=p('switch_purchases'),
            switch_delay=p('switch_delay'),switch_missing=p('switch_missing'),switch_brier=divided(p('switch_brier'),L))

    def match(saved,worlds,T,rho,profile):
        check('world_count',len(saved['worlds'])==len(worlds)==T+1)
        for u,v in zip(saved['worlds'],worlds):equal(u,v,'world_fields')
        s=summary(worlds,T,rho,profile);equal(saved['summary'],s,'summary_fields')
        return dict(worlds=worlds,summary=s)

    expected_names={f'constant_{n:02d}' for n in (4,5,6)}|{f'{d}_{s:02d}' for d in ('up','down') for s in range(2,11)}
    check('schedule_roster',set(r['cases'])==expected_names)
    expected_switches=[];outcomes={name:[] for name in ('joint_mixture','fixed_pool')}
    for case_name,case in r['cases'].items():
        profile=case['profile'];sigma=profile['change_task']
        if case_name.startswith('constant_'):
            n=int(case_name[-2:]);check('constant_profile',sigma is None and profile['rates']==[n]*T and profile['before']==profile['after']==n)
            totals['constant_schedules']+=1
        else:
            direction,s=case_name.split('_');expected_switches.append(case_name);before,after=(4,6) if direction=='up' else (6,4)
            check('switch_profile',sigma==int(s) and profile['before']==before and profile['after']==after
                  and profile['rates']==[before if t<sigma else after for t in range(1,T+1)])
            totals['switch_schedules']+=1
        paths=streams(profile,T);policies={}
        for name,p in g['graphs'].items():
            worlds=[replay(p['graph'],main_probs[name],T,tau,profile,paths) for tau in [None,*range(1,T+1)]]
            policies[name]=match(case['policies'][name],worlds,T,rho,profile)
        aw=[]
        for tau in [None,*range(1,T+1)]:
            L=0 if tau is None else T-tau+1;N=0 if sigma is None else T-sigma+1
            row=dict(onset=tau,cost=Q(T,10),errors=Q(0),purchases=Q(T),post_cost=Q(L,10),post_errors=Q(0),post_purchases=Q(L),
                delay=Q(0),missing=Q(tau is None),recovery=None if tau is None else Q(1,10),orientation_brier=None,
                switch_cost=None if sigma is None else Q(N,10),switch_errors=None if sigma is None else Q(0),
                switch_purchases=None if sigma is None else Q(N),switch_delay=None if sigma is None else Q(0),
                switch_missing=None if sigma is None else Q(0),switch_brier=None)
            aw.append(row)
        policies['always']=match(case['policies']['always'],aw,T,rho,profile)
        for name,cs in g['mixtures'].items():
            check('fixed_weights',case['policies'][name]['components']==cs and sum(Q(c['weight']) for c in cs)==1
                  and all(Q(c['weight'])>=0 for c in cs))
            worlds=[]
            for i in range(T+1):
                row=dict(onset=None if i==0 else i)
                for key in FIELDS:
                    vals=[(Q(c['weight']),policies[c['policy']]['worlds'][i][key]) for c in cs]
                    row[key]=None if any(v is None for _,v in vals) else sum(w*v for w,v in vals)
                worlds.append(row)
            policies[name]=match(case['policies'][name],worlds,T,rho,profile)
        check('policy_roster',set(case['policies'])==set(policies))
        h=policies['hybrid']['summary']
        for name,p in policies.items():
            s=p['summary'];primary=dict(stable=s['stable']<=K,below_always=s['R']<Q(1,10),below_hybrid=s['R']<h['R'])
            primary['joint']=all(primary.values())
            expected=dict(primary=primary,matched_stable=s['stable']<=h['stable'],full_below_hybrid=s['B']<h['B'],full_below_always=s['B']<Q(1,10))
            check('scientific_gate',case['gates'][name]==expected)
            if sigma is not None and name in outcomes:outcomes[name].append(primary['joint'])
            if sigma is None:
                x=Q(profile['rates'][0],100)
                for row,poly in zip(p['worlds'],old['policies'][name]['worlds']):
                    for key in FIELDS[:9]:
                        check('constant_reproduction',row[key] is None if poly[key] is None else row[key]==sum(Q(c)*x**j for j,c in enumerate(poly[key])))
        for name in outcomes:
            for control in ('hybrid','always',next(n for n in outcomes if n!=name)):
                u,v=policies[name],policies[control];saved=case['comparisons'][name][control]
                delta={k:None if u['summary'][k] is None or v['summary'][k] is None else u['summary'][k]-v['summary'][k] for k in u['summary']}
                equal(saved['summary_deltas'],delta,'signed_summary')
                for item,x,y in zip(saved['worlds'],u['worlds'],v['worlds']):
                    equal(item,dict(onset=x['onset'],full_cost_delta=x['cost']-y['cost'],
                          recovery_delta=None if x['recovery'] is None else x['recovery']-y['recovery']),'signed_world')
    check('switch_case_list',set(r['switch_cases'])==set(expected_switches) and len(r['switch_cases'])==18)
    check('overall_verdicts',r['overall']=={name:all(v) for name,v in outcomes.items()})
    for fixture in load(a/'SHORT_FIXTURES.json'):
        t,prior=fixture['T'],Q(fixture['rho']);profile=fixture['profile']
        probs=validate(fixture['graph'],fixture['belief'],t,prior,fixture['erased']);paths=streams(profile,t)
        worlds=[replay(fixture['graph'],probs,t,tau,profile,paths) for tau in [None,*range(1,t+1)]]
        match(fixture['result'],worlds,t,prior,profile)
    qual,bench,resources=[load(a/n) for n in ('QUALIFICATION.json','BENCHMARK.json','STARTED.json')]
    check('qualification',qual['passed'] and qual['tree_counts']=={'1':3,'2':15,'3':255})
    check('benchmark_scope',bench['T']==7 and Q(bench['rho'])==Q(1,3) and bench['change_task']==4 and bench['directions']==2 and bench['timing_only'])
    check('resource_limits',len(resources['affinity'])==1 and resources['nice']>=10 and all(v=='1' for v in resources['threads'].values()))
    check('execution_rules',bench['forecast_seconds']<=7200 and (bench['forecast_seconds']<=600 or resources['detached']))
    answer=dict(passed=True,completed=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start,
        checks=counts,total_checks=sum(counts.values()),totals=totals,manifest_sha256=sha(a/'MANIFEST.json'),source_sha256=sha(__file__),
        method='Independent integer-probability full-noise replay, graph-visit Brier reconstruction, frozen belief transitions, exact gates and constant-control reproduction.')
    with (a/'READBACK.json').open('x') as out:
        json.dump(answer,out,indent=2,sort_keys=True);out.write('\n')
    print(json.dumps(dict(passed=True,checks=answer['total_checks'],seconds=answer['seconds'],totals=totals)),flush=True)


if __name__=='__main__':main()
