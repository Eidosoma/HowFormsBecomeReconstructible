#!/usr/bin/env python3
"""Independent physical recursions and primal/dual feasibility certificates."""
from datetime import datetime, timezone
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path
import itertools
import json
import sys
import time

import readback_fep_burst_alltiming as previous

sys.set_int_max_str_digits(0)
K = Q(19568652557, 204800000000)
load, sha = previous.load, previous.sha


def physical(graph, profile, T, tau):
    @lru_cache(None)
    def future(i, error_state):
        if i is None:
            return (Q(0),)*4
        n = graph[i]
        post = tau is not None and n['t'] >= tau
        bought = n['action'] == 'B'
        label = int(post)^error_state
        child = n['children'][str(label) if bought else 'N']
        persistence = profile[n['t']-1] if n['t'] < T else Q(0)
        p = (1-persistence)*Q(1,20) + persistence*error_state
        later = [(1-p)*x+p*y for x,y in zip(future(child,0),future(child,1))]
        error = int(not bought and label != int(n['action']=='R'))
        return tuple(v+r for v,r in zip(later,(error,int(bought),error if post else 0,int(bought and post))))
    e,b,pe,pb = [(19*x+y)/20 for x,y in zip(future(0,0),future(0,1))]
    return dict(onset=tau,errors=e,purchases=b,post_errors=pe,post_purchases=pb,
                cost=e+b/10,post_cost=pe+pb/10,recovery=None if tau is None else (pe+pb/10)/(T-tau+1))


def cost_record(graph, profile, T=10):
    ws = [physical(graph,profile,T,tau) for tau in [None,*range(1,T+1)]]
    s = ws[0]['cost']/T
    b = (ws[0]['cost']/2+sum(w['cost'] for w in ws[1:])/(2*T))/T
    r = sum(w['recovery'] for w in ws[1:])/T
    return dict(worlds=ws,summary=dict(stable=s,B=b,R=r,J=b+r))


def matrix(records, hybrid, family, budget=K, order=None):
    order = list(previous.profiles()) if order is None else list(order)
    names = [f'{family}_mu{mu:02d}' for mu in (0,1,2,4,8,16)]
    floor = family+'_floor'
    rows = [('weights:sum',[Q(1)]*6+[Q(0)],Q(1))]
    for name in order:
        ps = records[name]
        fs,fr = [ps[floor]['summary'][k] for k in ('stable','R')]
        for criterion,key,limit,coefficient in [('hard_budget','stable',budget,Q(0)),
            ('stable','stable',budget,Q(1)),('always_recovery','R',Q(1,10),Q(1)),
            ('hybrid_recovery','R',hybrid[name],Q(1))]:
            offset = fs if key=='stable' else fr
            vector = [ps[n]['summary'][key]-offset for n in names]+[coefficient]
            rows.append((name+':'+criterion,vector,limit-offset+coefficient))
    return dict(A=[r[1] for r in rows],b=[r[2] for r in rows],c=[Q(0)]*6+[Q(1)],
        row_ids=[r[0] for r in rows],variables=names+['shifted_margin'],floor=floor,
        profiles=order,budget=budget)


def valid_certificate(p, s):
    A,b,c = [[list(map(Q,row)) for row in p['A']],list(map(Q,p['b'])),list(map(Q,p['c']))]
    x,y = list(map(Q,s['x'])),list(map(Q,s['dual']))
    if len(x)!=len(c) or len(y)!=len(b) or min(x+y)<0:
        return False
    if any(sum(u*v for u,v in zip(row,x))>bound for row,bound in zip(A,b)):
        return False
    if any(sum(row[j]*weight for row,weight in zip(A,y))<value for j,value in enumerate(c)):
        return False
    return sum(u*v for u,v in zip(c,x))==sum(u*v for u,v in zip(b,y))==Q(s['objective'])


def linear_solve(A,b):
    rows = [[Q(x) for x in row]+[Q(rhs)] for row,rhs in zip(A,b)]
    n = len(b)
    for col in range(n):
        pivot = next((j for j in range(col,n) if rows[j][col]),None)
        if pivot is None:
            return None
        rows[col],rows[pivot]=rows[pivot],rows[col]
        value=rows[col][col]
        rows[col]=[x/value for x in rows[col]]
        for j in range(n):
            if j!=col:
                v=rows[j][col]
                rows[j]=[x-v*y for x,y in zip(rows[j],rows[col])]
    return [row[-1] for row in rows]


def vertex_optimum(A,b,c):
    n=len(c)
    constraints=[(list(map(Q,row)),Q(rhs)) for row,rhs in zip(A,b)]
    constraints += [([Q(-int(i==j)) for i in range(n)],Q(0)) for j in range(n)]
    values=[]
    for chosen in itertools.combinations(constraints,n):
        x=linear_solve([v[0] for v in chosen],[v[1] for v in chosen])
        if x is not None and all(sum(u*v for u,v in zip(row,x))<=rhs for row,rhs in constraints):
            values.append(sum(Q(u)*v for u,v in zip(c,x)))
    assert values
    return max(values)


def converted(record):
    out=dict(worlds=[{k:v if k=='onset' or v is None else Q(v) for k,v in w.items()} for w in record['worlds']],
             summary={k:None if v is None else Q(v) for k,v in record['summary'].items()})
    if 'components' in record:
        out['components']=[dict(policy=c['policy'],weight=Q(c['weight'])) for c in record['components']]
    return out


def blend(records, components):
    worlds=[]
    for j,tau in enumerate([None,*range(1,11)]):
        row=dict(onset=tau)
        for key in records[components[0]['policy']]['worlds'][j]:
            if key=='onset':
                continue
            values=[(Q(c['weight']),records[c['policy']]['worlds'][j][key]) for c in components]
            row[key]=None if any(v is None for _,v in values) else sum(w*v for w,v in values)
        worlds.append(row)
    return dict(components=components,worlds=worlds,summary=previous.summary(worlds))


def gates(s,h):
    return dict(stable=s['stable']<=K,always_recovery=s['R']<Q(1,10),hybrid_recovery=s['R']<h['R'],
        matched_stable=s['stable']<=h['stable'],hybrid_full=s['B']<h['B'],always_full=s['B']<Q(1,10))


def difference(a,b):
    return dict(summary={k:None if v is None or b['summary'][k] is None else v-b['summary'][k] for k,v in a['summary'].items()},
        worlds=[dict(onset=u['onset'],full=(u['cost']-v['cost'])/10,
                     recovery=None if u['recovery'] is None else u['recovery']-v['recovery']) for u,v in zip(a['worlds'],b['worlds'])])


def main():
    start=time.monotonic();a=Path(sys.argv[1]);counts={}
    totals=dict(cost_graph_worlds=0,diagnostic_graph_worlds=0,pool_certificates=0,fixture_certificates=0)
    def check(k,ok):
        counts[k]=counts.get(k,0)+1
        if not ok:raise AssertionError(k)
    def equal(u,v,k):
        if isinstance(v,dict):
            check(k+':keys',set(u)==set(v))
            for key,x in v.items():equal(u[key],x,k)
        elif isinstance(v,(list,tuple)):
            check(k+':length',len(u)==len(v))
            for x,y in zip(u,v):equal(x,y,k)
        elif isinstance(v,Q):check(k,Q(u)==v)
        else:check(k,u==v)
    f,manifest,freeze,started,bundle,mixes,solutions,saved_costs,result=[load(a/n) for n in
        ('FREEZE.json','MANIFEST.json','SELECTION_FREEZE.json','CHECKS_STARTED.json','GRAPHS.json',
         'MIXTURES.json','SOLUTIONS.json','COSTS.json','RESULTS.json')]
    check('complete',manifest['status']=='COMPLETE')
    for n,h in f['inputs'].items():check('source_hash',sha(n)==h)
    for n,h in f['snapshots'].items():check('snapshot_hash',sha(a/'inputs'/n)==h)
    for n,h in manifest['outputs'].items():check('output_hash',sha(a/n)==h)
    for n,h in freeze['selection_files'].items():check('selection_hash',sha(a/n)==h)
    check('freeze_order',f['created']<freeze['created']<started['utc']<=manifest['finished'])
    check('frozen_selection_identity',started['selection_freeze_sha256']==sha(a/'SELECTION_FREEZE.json')
          and freeze['mixtures_sha256']==sha(a/'MIXTURES.json'))
    check('selection_precedes_diagnostics',all(n not in freeze['selection_files'] for n in ('RESULTS.json','CHECKS_STARTED.json')))
    check('development_only',f['development_only'] and freeze['development_only'] and result['development_only'])
    check('model_scope',bundle['T']==result['T']==10 and Q(bundle['rho'])==Q(result['rho'])==Q(1,2)
          and Q(f['budget'])==Q(result['budget'])==K)
    profiles=previous.profiles()
    for obj in (f,saved_costs,result):equal(obj['profiles'],profiles,'physical_profiles')
    pools={family:[f'{family}_mu{mu:02d}' for mu in (0,1,2,4,8,16)]+[family+'_floor'] for family in ('full','ablated')}
    equal(bundle['pools'],pools,'pool_roster')
    graphs=bundle['graphs'];check('graph_roster',set(graphs)==set(sum(pools.values(),[]))|{'hybrid'})
    source=Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-alltiming-v1/attempt-01')
    old_manifest=load(source/'MANIFEST.json');old_audit=load(source/'READBACK.json');old_result=load(source/'RESULTS.json')
    check('predecessor_verified',old_audit['passed'] and old_audit['manifest_sha256']==sha(source/'MANIFEST.json'))
    check('matched_bayesian_inherited',old_audit['totals']['bellman_states']==354288
          and old_audit['checks']['matched_bayesian_action']==3535
          and old_audit['source_sha256']==sha(Path(previous.__file__)))
    candidates={}
    for name in sum(pools.values(),[]):
        path=source/'candidates'/f'{name}.json';candidate=load(path);candidates[name]=candidate
        check('candidate_manifest_hash',sha(path)==old_manifest['outputs'][str(path.relative_to(source))]==f['inputs'][str(path)])
        equal(graphs[name],{k:candidate[k] for k in ('graph','belief')},'candidate_identity')
    for name in ('RESULTS.json','EVAL_GRAPHS.json','EVAL_MIXTURES.json'):
        check('control_manifest_hash',sha(source/name)==old_manifest['outputs'][name]==f['inputs'][str(source/name)])
    equal(graphs['hybrid'],load(source/'EVAL_GRAPHS.json')['graphs']['hybrid'],'hybrid_identity')
    records={};reproduction=0
    for label,profile in profiles.items():
        records[label]={name:cost_record(p['graph'],profile) for name,p in graphs.items()}
        totals['cost_graph_worlds']+=11*len(graphs)
        equal(saved_costs['records'][label],records[label],'backward_costs')
        for name,record in records[label].items():
            known=old_result['cases'][label]['policies'].get(name)
            if known is not None:
                for u,v in zip(record['worlds'],known['worlds']):
                    equal({k:v[k] for k in u},u,'previous_cost_reproduction');reproduction+=len(u)
                equal({k:known['summary'][k] for k in record['summary']},record['summary'],'previous_summary_reproduction')
                reproduction+=len(record['summary'])
        for family in pools:
            floor=records[label][family+'_floor']['summary']
            check('strict_floor_budget',floor['stable']==Q(1,20)<K and floor['R']==Q(19,20))
        print('COST_READBACK '+label,flush=True)
    for name,candidate in candidates.items():
        for label,alpha in (('training_00','0'),('training_75','3/4')):
            old=candidate['training']['settings'][alpha];current=records[label][name]
            for u,v in zip(current['worlds'],old['worlds']):
                equal({k:v[k] for k in u},u,'training_cost_reproduction');reproduction+=len(u)
            equal({k:old[k] for k in ('stable','B','R')},{k:current['summary'][k] for k in ('stable','B','R')},'training_summary_reproduction')
            reproduction+=3
    equal(load(a/'REPRODUCTION.json'),dict(passed=True,checks=reproduction),'reproduction_count')
    hybrid={label:ps['hybrid']['summary']['R'] for label,ps in records.items()}
    components={};margins={}
    for family in pools:
        saved=solutions[family];p=matrix(records,hybrid,family);equal(saved['problem'],p,'constraint_matrix')
        s=saved['certificate'];check('optimality_certificate',valid_certificate(p,s));totals['pool_certificates']+=1
        x,y=list(map(Q,s['x'])),list(map(Q,s['dual']));objective=Q(s['objective']);margin=objective-1;margins[family]=margin
        slacks=[b-sum(u*v for u,v in zip(row,x)) for row,b in zip(p['A'],p['b'])]
        reduced=[sum(row[j]*v for row,v in zip(p['A'],y))-c for j,c in enumerate(p['c'])]
        equal(s['primal_slacks'],slacks,'primal_slacks');equal(s['dual_slacks'],reduced,'dual_slacks')
        check('complementarity',all(u*v==0 for u,v in zip(slacks,y)) and all(u*v==0 for u,v in zip(reduced,x)))
        basis=list(range(7,48));last=Q(0)
        for pivot in s['pivots']:
            row=pivot['row'];enter=pivot['enter']
            check('pivot_trace',0<=row<41 and 0<=enter<48 and enter not in basis and pivot['leave']==basis[row]
                  and Q(pivot['ratio'])>=0 and Q(pivot['objective'])>=last)
            basis[row]=enter;last=Q(pivot['objective'])
        check('basis_trace',basis==s['basis'] and len(set(basis))==41 and len(s['pivots'])<=2000 and last==objective)
        check('nonbasic_zero',all(v==0 for j,v in enumerate(x+slacks) if j not in basis))
        weights=x[:6]+[1-sum(x[:6])]
        check('global_mixture',min(weights)>=0 and sum(weights)==1)
        components[family]=[dict(policy=n,weight=w) for n,w in zip(pools[family],weights) if w]
        equal(saved['components'],components[family],'selected_weights');equal(saved['margin'],margin,'optimal_margin')
        equal(saved['feasible'],margin>0,'pool_feasibility')
        equal(saved['active'],[n for n,v in zip(p['row_ids'],slacks) if not v],'active_constraints')
        equal(saved['dual_support'],[dict(constraint=n,weight=v) for n,v in zip(p['row_ids'],y) if v],'dual_support')
        physical_margins=[]
        for label,ps in records.items():
            S,R=[sum(c['weight']*ps[c['policy']]['summary'][key] for c in components[family]) for key in ('stable','R')]
            check('hard_budget',S<=K);physical_margins.extend((K-S,Q(1,10)-R,hybrid[label]-R))
        check('physical_margin',min(physical_margins)==margin)
    equal(freeze['feasibility'],{f:margins[f]>0 for f in pools},'frozen_feasibility')
    fixtures=load(a/'FIXTURES.json');qualification=load(a/'QUALIFICATION.json')
    check('qualified',qualification['passed'] and qualification['linear_programs']==5 and qualification['margin_fixtures']==4)
    for fixture in fixtures['linear_programs']:
        p,s=fixture['problem'],fixture['certificate'];check('fixture_certificate',valid_certificate(p,s))
        check('fixture_vertex_optimum',Q(s['objective'])==vertex_optimum(p['A'],p['b'],list(map(Q,p['c']))));totals['fixture_certificates']+=1
        for key in ('x','dual'):
            corrupted=dict(s);corrupted[key]=list(s[key]);corrupted[key][0]=-1
            check('reject_corrupted_witness',not valid_certificate(p,corrupted))
    for fixture,sign in zip(fixtures['margin_fixtures'],(1,0,-1,-1)):
        rec={label:{n:dict(summary={k:Q(v) for k,v in d['summary'].items()}) for n,d in ps.items()} for label,ps in fixture['records'].items()}
        p=matrix(rec,{k:Q(v) for k,v in fixture['hybrid'].items()},'full',order=['fixture']);s=fixture['solution']
        equal(s['problem'],p,'fixture_matrix');check('fixture_certificate',valid_certificate(p,s['certificate']));totals['fixture_certificates']+=1
        check('fixture_aggregation',all(all(v==row[0] for v in row[:6]) for row in p['A']))
        optimum=vertex_optimum([[row[0],row[-1]] for row in p['A']],p['b'],[Q(0),Q(1)])
        check('fixture_margin',Q(s['margin'])==optimum-1 and (optimum>1)-(optimum<1)==sign)
    expected_mixes=dict(selected_full=components['full'],selected_ablated=components['ablated'],matched_bayesian=components['full'],
        frozen_reliability=[dict(policy=c['policy'].replace('full_','ablated_',1),weight=c['weight']) for c in components['full']])
    equal(mixes,expected_mixes,'all_mixture_identities')
    diagnostic_names=sorted({c['policy'] for cs in expected_mixes.values() for c in cs})
    equal(freeze['diagnostic_components'],diagnostic_names,'diagnostic_roster')
    controls=dict(previous_full='reliability',previous_ablation='frozen_reliability',joint_mixture='joint_mixture',
        fixed_pool='fixed_pool',hybrid='hybrid',always='always',conservative='conservative',fixed_schedule='fixed_schedule')
    beliefs={n:previous.flow.beliefs(graphs[n]['graph'],graphs[n]['belief']) for n in diagnostic_names};cases={}
    for label,profile in profiles.items():
        ps={}
        for n in diagnostic_names:
            ws=[previous.forward(graphs[n]['graph'],beliefs[n],10,tau,profile) for tau in [None,*range(1,11)]]
            ps[n]=dict(worlds=ws,summary=previous.summary(ws));totals['diagnostic_graph_worlds']+=11
            equal({k:ps[n]['summary'][k] for k in ('stable','B','R','J')},records[label][n]['summary'],'diagnostic_cost_identity')
        for n,cs in expected_mixes.items():ps[n]=blend(ps,cs)
        for n,source_name in controls.items():ps[n]=converted(old_result['cases'][label]['policies'][source_name])
        gs={n:gates(p['summary'],ps['hybrid']['summary']) for n,p in ps.items()}
        comparisons={n:difference(ps['selected_full'],ps[n]) for n in (*controls,'frozen_reliability','selected_ablated','matched_bayesian')}
        cases[label]=dict(profile=profile,policies=ps,gates=gs,comparisons=comparisons)
        equal(ps['matched_bayesian'],ps['selected_full'],'matched_bayesian_outcomes')
        print('DIAGNOSTIC_READBACK '+label,flush=True)
    targets=('selected_full','frozen_reliability','selected_ablated')
    for label,case in cases.items():
        case['independence_deltas']={n:{k:None if v is None else v-cases['training_00']['policies'][n]['summary'][k]
            for k,v in case['policies'][n]['summary'].items()} for n in targets}
        delta=case['independence_deltas']['selected_full']
        case['false_confidence_pattern']={k:delta[k]>0 for k in ('stable_confidence','stable_wrong95','stable_brier','stable','prior_wrong95_errors')}
    equal(result['cases'],cases,'all_results')
    primary={n:all(all(case['gates'][n][k] for k in ('stable','always_recovery','hybrid_recovery')) for case in cases.values()) for n in targets}
    equal(result['primary_pass'],primary,'primary_outcomes')
    check('outcome_certificate_consistency',all(primary[n]==(margins[f]>0) for n,f in [('selected_full','full'),('selected_ablated','ablated')]))
    mechanisms={label:{n:dict(lower_R=case['comparisons'][n]['summary']['R']<0,lower_J=case['comparisons'][n]['summary']['J']<0,
        full_stable=case['gates']['selected_full']['stable'],comparator_stable=case['gates'][n]['stable'])
        for n in ('frozen_reliability','selected_ablated')} for label,case in cases.items()}
    equal(result['mechanisms'],mechanisms,'mechanism_outcomes')
    equal(result['pool_margin_difference'],margins['full']-margins['ablated'],'pool_margin_comparison')
    report=dict(passed=True,completed=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start,
        total_checks=sum(counts.values()),checks=counts,totals=totals,manifest_sha256=sha(a/'MANIFEST.json'),source_sha256=sha(__file__),
        method='Independent rational backward physical costs, primal/dual optimality certificates, short-fixture vertex enumeration, '
               'frozen predecessor Bayesian identities, augmented-state diagnostic flow and paired/optimized mixture checks; exposed development profiles only.')
    with (a/'READBACK.json').open('x') as out:json.dump(report,out,indent=2,sort_keys=True);out.write('\n')
    print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
