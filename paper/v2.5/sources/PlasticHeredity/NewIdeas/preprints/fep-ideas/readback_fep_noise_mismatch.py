#!/usr/bin/env python3
"""Independent complete-noise replay of immutable policies and calibration."""
from datetime import datetime, timezone
from fractions import Fraction as Q
from pathlib import Path
import hashlib
import json
import math
import sys
import time


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    start = time.monotonic()
    a = Path(sys.argv[1])
    checks, totals = {}, dict(noise_paths=0, graph_worlds=0, graph_states_checked=0, calibration_states=0)
    def check(name, value):
        checks[name] = checks.get(name, 0)+1
        if not value: raise AssertionError(name)
    def load(name): return json.loads((a/name).read_text())
    def equal(saved, actual, label):
        check(label+'_keys', set(saved) == set(actual))
        for key, value in actual.items():
            check(label+'_'+key, saved[key] is None if value is None else Q(saved[key]) == value)

    freeze, manifest, graphs, results = load('FREEZE.json'), load('MANIFEST.json'), load('GRAPHS.json'), load('RESULTS.json')
    check('complete', manifest['status'] == 'COMPLETE')
    for name, identity in freeze['inputs'].items(): check('input_hash', digest(name) == identity)
    for name, identity in freeze['snapshots'].items(): check('snapshot_hash', digest(a/'inputs'/name) == identity)
    for name, identity in manifest['outputs'].items(): check('output_hash', digest(a/name) == identity)
    source_paths = [Path(p) for p in freeze['inputs'] if p.endswith('/RESULTS.json')]
    sources = {}
    for path in source_paths:
        rb = json.loads((path.parent/'READBACK.json').read_text())
        mf = json.loads((path.parent/'MANIFEST.json').read_text())
        check('source_readback', rb['passed'] and rb['manifest_sha256'] == digest(path.parent/'MANIFEST.json'))
        check('source_result', mf['outputs']['RESULTS.json'] == digest(path))
        if 'fep-deterministic-recovery-v1' in str(path): name = 'deterministic'
        elif 'fep-stable-constraint-v1' in str(path): name = 'constraint'
        else: name = 'noisy'
        sources[name] = json.loads(path.read_text())
    d = sources['deterministic']
    p = sources['constraint']['conditions']['1']['problems']['retained_primary']
    n = sources['noisy']['conditions']['1']['policies']
    budget = Q(19568652557, 204800000000)
    check('declared_parameters', graphs['T'] == 10 and Q(graphs['rho']) == Q(1, 2)
          and Q(graphs['price']) == Q(1, 10) and Q(graphs['assumed_epsilon']) == Q(1, 20)
          and Q(graphs['budget']) == budget and Q(results['fixed_budget']) == budget
          and Q(results['assumed_epsilon']) == Q(1, 20))
    check('fixed_selected_policy', d['selected']['primary'] == 37)
    high = d['anchor_reference']
    low = next(c['policy'] for c in p['solution']['components'] if c['policy'] != high)
    mapping = {high:'anchor', low:'low_component'}
    source_policies = {name:n[name] for name in ('hybrid', 'ordinary', 'recovery', 'erased')}
    source_policies.update(deterministic=d['selected_policies']['37'], anchor=p['policies'][high], low_component=p['policies'][low])
    check('fixed_policy_names', set(graphs['policies']) == set(source_policies))
    for name, policy in source_policies.items():
        copied = graphs['policies'][name]
        check('graph_identity', copied['graph'] == policy['graph'])
        check('nominal_source_identity', copied['nominal_worlds'] == policy['worlds'] and copied['nominal_summary'] == policy['summary'])
        check('erasure_flag', copied['erased'] == (name == 'erased'))
    check('fixed_mixture', graphs['mixture'] == [dict(policy=mapping[c['policy']], weight=c['weight']) for c in p['solution']['components']])
    check('nominal_mixture_source', graphs['nominal_mixture'] == p['solution'])
    target = d['nodes'][d['candidates'][37]['override']['state']]
    for name, policy in graphs['policies'].items():
        if name in ('deterministic', 'anchor'):
            matches = [i for i, node in enumerate(policy['graph']) if node['t'] == target['t'] and node['weights'] == target['weights']]
            check('fixed_guard', len(matches) == 1 and policy['guard_node'] == matches[0])
        else: check('unused_guard', policy['guard_node'] is None)

    def validate_graph(graph, T, rho, erased, hybrid=False):
        initial = (T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
        check('initial_state', graph[0]['t'] == 1 and tuple(graph[0]['weights']) == initial and graph[0]['clock'] == 0)
        seen = {0}
        for i in sorted(range(len(graph)), key=lambda j:graph[j]['t']):
            node = graph[i]; t = node['t']; w = tuple(node['weights'])
            totals['graph_states_checked'] += 1
            check('observable_interface', set(node) == {'t','weights','clock','action','children'} and node['action'] in ('B','F','R'))
            check('reachable_state', i in seen)
            check('positive_beliefs', len(w) == T+1 and min(w) > 0 and math.gcd(*w) == 1)
            if erased: check('erased_prior', w == initial)
            branches = {'N':w}
            if node['action'] == 'B':
                branches = {}
                for label in (0,1):
                    raw = [mass*(19 if label == int(0<j<=t) else 1) for j,mass in enumerate(w)]
                    common = math.gcd(*raw)
                    branches[str(label)] = w if erased else tuple(mass//common for mass in raw)
            check('observation_mask', set(branches) == set(node['children']))
            for label, updated in branches.items():
                child = node['children'][label]
                if t == T: check('terminal_edge', child is None)
                else:
                    clock = int(hybrid and node['action'] != 'B')
                    check('assumed_likelihood_edge', child is not None and graph[child]['t'] == t+1
                          and tuple(graph[child]['weights']) == updated and graph[child]['clock'] == clock)
                    seen.add(child)
        check('complete_graph', len(seen) == len(graph))

    def summarize(T,rho,worlds):
        S = worlds[0]['cost']/T
        B = (1-rho)*S+rho*sum(w['cost'] for w in worlds[1:])/(T*T)
        R = sum(w['recovery'] for w in worlds[1:])/T
        return dict(stable=S,B=B,R=R,J=B+R,stable_errors=worlds[0]['errors'],stable_purchases=worlds[0]['purchases'],
                    mean_changed_errors=sum(w['errors'] for w in worlds[1:])/T,
                    mean_changed_purchases=sum(w['purchases'] for w in worlds[1:])/T,
                    mean_post_errors=sum(w['post_errors'] for w in worlds[1:])/T,
                    mean_post_purchases=sum(w['post_purchases'] for w in worlds[1:])/T,
                    capped_first_delay=sum(w['delay'] for w in worlds[1:])/T,
                    no_post_purchase_probability=sum(w['missing'] for w in worlds[1:])/T,
                    stable_orientation_brier=worlds[0]['brier']/T,
                    prior_orientation_brier=((1-rho)*worlds[0]['brier']+rho*sum(w['brier'] for w in worlds[1:])/T)/T)

    def replay(graph,T,rho,eps,guard,saved):
        denom = 100**T
        number = int(eps*100)
        check('rational_noise', Q(number,100) == eps)
        streams=[]
        for bits in range(1<<T):
            ones=bits.bit_count(); mass=number**ones*(100-number)**(T-ones)
            if mass: streams.append((bits,mass))
        check('noise_probability',sum(m for _,m in streams)==denom)
        probabilities=[Q(sum(node['weights'][1:node['t']+1]),sum(node['weights'])) for node in graph]
        all_visits=[]; worlds=[]
        for j,tau in enumerate([None,*range(1,T+1)]):
            totals['graph_worlds']+=1
            e=b=pe=pb=delay=missing=0
            visits=[0]*len(graph)
            for bits,mass in streams:
                i=0; errors=buys=post_errors=post_buys=0; first=None
                for t in range(1,T+1):
                    node=graph[i]; visits[i]+=mass
                    changed=tau is not None and t>=tau
                    label=int(changed)^((bits>>(t-1))&1)
                    buy=int(node['action']=='B')
                    error=int(not buy and (node['action']=='R')!=bool(label))
                    errors+=error; buys+=buy
                    if changed:
                        post_errors+=error; post_buys+=buy
                        if buy and first is None: first=t
                    i=node['children'][str(label) if buy else 'N']
                check('noise_path_terminal',i is None); totals['noise_paths']+=1
                e+=mass*errors; b+=mass*buys; pe+=mass*post_errors; pb+=mass*post_buys
                if first is None: missing+=mass
                if tau is not None: delay+=mass*(T-tau+1 if first is None else first-tau)
            brier=sum(Q(v,denom)*(probabilities[i]-int(tau is not None and graph[i]['t']>=tau))**2 for i,v in enumerate(visits))
            row=dict(onset=tau,cost=Q(10*e+b,10*denom),errors=Q(e,denom),purchases=Q(b,denom),
                     post_cost=Q(10*pe+pb,10*denom),post_errors=Q(pe,denom),post_purchases=Q(pb,denom),
                     delay=Q(delay,denom),missing=Q(missing,denom),brier=brier,
                     recovery=None if tau is None else Q(10*pe+pb,10*denom*(T-tau+1)),
                     guard_probability=None if guard is None else Q(visits[guard],denom))
            equal(saved['worlds'][j],row,'world')
            check('known_orientation_floor',row['cost']/T>=min(eps,Q(1,10)))
            worlds.append(row); all_visits.append(visits)
        s=summarize(T,rho,worlds); equal(saved['summary'],s,'summary')
        prior=(T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
        prior_total=sum(prior)
        variance=excess=Q(0); expected_nodes=[]; total_visit=Q(0)
        for i,node in enumerate(graph):
            joint=sum(w*visits[i] for w,visits in zip(prior,all_visits))
            if not joint: continue
            mass=Q(joint,prior_total*denom)
            true_p=Q(sum(prior[j]*all_visits[j][i] for j in range(1,node['t']+1)),joint)
            delta=mass*(probabilities[i]-true_p)**2/T
            variance+=mass*true_p*(1-true_p)/T; excess+=delta; total_visit+=mass
            expected_nodes.append(dict(node=i,visit_mass=mass,assumed_probability=probabilities[i],
                                       true_state_conditional_probability=true_p,excess_brier=delta))
        check('calibration_mass',total_visit==T)
        check('calibration_identity',s['prior_orientation_brier']==variance+excess)
        check('nonnegative_discrepancy',excess>=0)
        check('calibration_node_count',len(saved['calibration']['nodes'])==len(expected_nodes))
        for actual,stored in zip(expected_nodes,saved['calibration']['nodes']):
            equal(stored,actual,'calibration_node'); totals['calibration_states']+=1
        cal=dict(discrepancy=excess,conditional_variance=variance,brier=s['prior_orientation_brier'])
        equal({k:v for k,v in saved['calibration'].items() if k!='nodes'},cal,'calibration')
        if eps==Q(1,20): check('nominal_calibration',excess==0)
        return dict(worlds=worlds,summary=s,calibration=cal)

    T,rho=graphs['T'],Q(graphs['rho'])
    for name,p in graphs['policies'].items(): validate_graph(p['graph'],T,rho,p['erased'],name=='hybrid')
    check('declared_conditions',set(results['conditions'])=={'0.04','0.05','0.06'})
    primary=[]; matched=[]
    for rate,case in results['conditions'].items():
        eps=Q(rate); check('true_rate',Q(case['true_epsilon'])==eps)
        check('result_policy_names',set(case['policies'])==set(graphs['policies'])|{'mixture'})
        rebuilt={}
        for name,p in graphs['policies'].items():
            rebuilt[name]=replay(p['graph'],T,rho,eps,p['guard_node'],case['policies'][name])
        worlds=[]
        for j in range(T+1):
            row={'onset':None if j==0 else j}
            for key in rebuilt['anchor']['worlds'][j]:
                if key=='onset': continue
                parts=[(Q(c['weight']),rebuilt[c['policy']]['worlds'][j][key]) for c in graphs['mixture']]
                row[key]=None if any(v is None for _,v in parts) else sum(w*v for w,v in parts)
            equal(case['policies']['mixture']['worlds'][j],row,'mixture_world'); worlds.append(row)
        summary=summarize(T,rho,worlds)
        equal(case['policies']['mixture']['summary'],summary,'mixture_summary')
        cal={key:sum(Q(c['weight'])*rebuilt[c['policy']]['calibration'][key] for c in graphs['mixture'])
             for key in ('discrepancy','conditional_variance','brier')}
        equal(case['policies']['mixture']['calibration'],cal,'mixture_calibration')
        check('mixture_identity',cal['brier']==cal['conditional_variance']+cal['discrepancy']==summary['prior_orientation_brier'])
        rebuilt['mixture']=dict(worlds=worlds,summary=summary,calibration=cal)
        if eps==Q(1,20):
            for name,p in rebuilt.items():
                source=graphs['nominal_mixture'] if name=='mixture' else source_policies[name]
                for x,y in zip(p['worlds'],source['worlds']):
                    for key in ('onset','cost','errors','purchases','post_cost','post_errors','post_purchases','delay','missing','recovery'):
                        check('nominal_world_reproduction',y[key] is None if x[key] is None else Q(y[key])==x[key])
                    if 'brier' in y: check('nominal_brier',Q(y['brier'])==x['brier'])
                for key,v in p['summary'].items():
                    if key in source['summary'] and key!='J': check('nominal_summary',Q(source['summary'][key])==v)
        s,h=rebuilt['deterministic']['summary'],rebuilt['hybrid']['summary']
        common=dict(below_always=s['R']<Q(1,10),below_hybrid=s['R']<h['R'])
        f=dict(common,stable_within_fixed_budget=s['stable']<=budget)
        m=dict(common,stable_not_above_matched_hybrid=s['stable']<=h['stable'])
        f['joint']=all(f.values()); m['joint']=all(m.values())
        check('fixed_budget_gate',case['gate']['fixed_budget']==f)
        check('matched_gate',case['gate']['matched_hybrid']==m)
        primary.append(f['joint']); matched.append(m['joint'])
        check('always_buy',all(Q(v)==Q(1,10) for v in case['always'].values()))
        check('erased_physical_costs',all(rebuilt['erased']['summary'][k]==Q(1,10) for k in ('stable','R','B')))
        check('erased_calibration',rebuilt['erased']['calibration']['discrepancy']==0)
    check('primary_robustness',results['primary_robustness']==all(primary))
    check('matched_robustness',results['matched_robustness']==all(matched))
    for fixture in load('SHORT_FIXTURES.json'):
        T,rho=fixture['T'],Q(fixture['rho'])
        validate_graph(fixture['graph'],T,rho,fixture['erased'])
        replay(fixture['graph'],T,rho,Q(fixture['true_epsilon']),None,fixture['result'])
    start_record,bench=load('STARTED.json'),load('BENCHMARK.json')
    check('resources',len(start_record['affinity'])==1 and start_record['nice']>=10)
    check('detachment',bench['forecast_seconds']<=600 or start_record['detached'])
    output=dict(passed=True,completed=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start,
                checks=checks,total_checks=sum(checks.values()),totals=totals,
                manifest_sha256=digest(a/'MANIFEST.json'),source_sha256=digest(__file__),
                method='Independent complete-noise integer replay, retained-state calibration and frozen nominal reproduction.')
    with (a/'READBACK.json').open('x') as out: json.dump(output,out,indent=2,sort_keys=True); out.write('\n')
    print(json.dumps({k:output[k] for k in ('passed','seconds','total_checks','totals')},sort_keys=True))


if __name__=='__main__': main()
