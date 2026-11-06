#!/usr/bin/env python3
"""Independent normalized Bayesian and exact transfer audit; no new planner import."""
from datetime import datetime,timezone
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path
import gzip
import json
import math
import sys
import time

import readback_fep_burst_pool_feasibility as certified

previous=certified.previous
load,sha,K=certified.load,certified.sha,certified.K
primitive=previous.previous.primitive
sys.set_int_max_str_digits(0)


def generation(T):
    return {'training_00':[Q(0)]*(T-1),
            'alternating_high':[Q(9,10) if t%2 else Q(0) for t in range(1,T)]}


def heldout():
    return dict(constant_10=[Q(1,10)]*9,constant_70=[Q(7,10)]*9,
        onset_after_3=[Q(0)]*2+[Q(9,10)]*7,offset_after_3=[Q(9,10)]*2+[Q(0)]*7,
        onset_after_7=[Q(0)]*6+[Q(9,10)]*3,offset_after_7=[Q(9,10)]*6+[Q(0)]*3,
        paired_low=list(map(Q,('0','0','9/10','9/10','0','0','9/10','9/10','0'))),
        paired_high=list(map(Q,('9/10','9/10','0','0','9/10','9/10','0','0','9/10'))))


class Bayesian(previous.Bayesian):
    def __init__(self,T):
        self.T,self.D=T,200
        self.states=tuple((e,j,z) for e in (0,1) for j in range(T+1) for z in (0,1))
        self.prior=primitive([Q(1,2)*(Q(1,2) if tau==0 else Q(1,2*T))*(Q(19,20) if z==0 else Q(1,20)) for _,tau,z in self.states])
        self.step=lru_cache(None)(self._step)

    def _step(self,t,w,label,frozen):
        probabilities=[Q(v,sum(w)) if label is None or label==(int(0<j<=t)^z) else Q(0) for v,(_,j,z) in zip(w,self.states)]
        probability=sum(probabilities)
        if frozen:
            onset=[sum(p for p,(_,j,_) in zip(probabilities,self.states) if j==tau) for tau in range(self.T+1)]
            following=[onset[tau]*Q(1,2)*(Q(19,20) if z==0 else Q(1,20)) for _,tau,z in self.states]
        else:
            following=[]
            for i in range(0,len(probabilities),2):
                e=self.states[i][0];a=Q(9,10) if e==1 and t%2 else Q(0)
                zero,one=probabilities[i:i+2]
                error=(zero+one)*Q(1,20)*(1-a)+a*one
                following.extend((zero+one-error,error))
        return primitive(following),probability

    def fields(self,t,w):
        out=super().fields(t,w);out.pop('q_persistent')
        out['q_pattern']=Q(sum(v for v,(e,_,_) in zip(w,self.states) if e==1),sum(w))
        return out


def training(graph,T):
    settings={n:certified.cost_record(graph,p,T) for n,p in generation(T).items()}
    return dict(settings=settings,C=sum(s['summary']['J'] for s in settings.values())/2,
                S=[s['summary']['stable'] for s in settings.values()])


def matrix(records,hybrid,family,expanded):
    names=[f'{family}_mu{m:02d}' for m in (0,1,2,4,8,16)]
    if expanded:names+=['target_'+n for n in names]
    floor=family+'_floor';rows=[('weights:sum',[Q(1)]*len(names)+[Q(0)],Q(1))]
    for label in previous.profiles():
        ps=records[label]
        for criterion,key,limit,d in [('hard_budget','stable',K,Q(0)),('stable','stable',K,Q(1)),
            ('always_recovery','R',Q(1,10),Q(1)),('hybrid_recovery','R',hybrid[label],Q(1))]:
            offset=ps[floor]['summary'][key]
            rows.append((label+':'+criterion,[ps[n]['summary'][key]-offset for n in names]+[d],limit-offset+d))
    return dict(A=[r[1] for r in rows],b=[r[2] for r in rows],c=[Q(0)]*len(names)+[Q(1)],
        row_ids=[r[0] for r in rows],variables=names+['shifted_margin'],floor=floor,profiles=list(previous.profiles()),budget=K)


def same_behavior(a,b):
    seen=set();todo=[(0,0)]
    while todo:
        i,j=todo.pop()
        if (i,j) in seen:continue
        seen.add((i,j));u,v=a[i],b[j]
        if u['t']!=v['t'] or u['action']!=v['action'] or set(u['children'])!=set(v['children']):return False
        if Q(u['q_orientation'])!=Q(v['q_orientation']) or list(map(Q,u['post_orientation']))!=list(map(Q,v['post_orientation'])):return False
        for label,x in u['children'].items():
            y=v['children'][label]
            if x is None or y is None:
                if x!=y:return False
            else:todo.append((x,y))
    return True


def main():
    start=time.monotonic();a=Path(sys.argv[1]);counts={};totals=dict(bellman_states=0,new_graph_states=0,cost_graph_worlds=0,diagnostic_graph_worlds=0,certificates=0)
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
    f,manifest,freeze,started,bundle,mixes,selection,costs,result,modeldata=[load(a/n) for n in
        ('FREEZE.json','MANIFEST.json','CANDIDATE_FREEZE.json','TEST_STARTED.json','GRAPHS.json','MIXTURES.json',
         'SELECTION.json','COSTS.json','RESULTS.json','MODEL.json')]
    check('complete',manifest['status']=='COMPLETE')
    for n,h in f['inputs'].items():check('source_hash',sha(n)==h)
    for n,h in f['snapshots'].items():check('snapshot_hash',sha(a/'inputs'/n)==h)
    for n,h in manifest['outputs'].items():check('output_hash',sha(a/n)==h)
    for n,h in freeze['training_files'].items():check('candidate_freeze_hash',sha(a/n)==h)
    check('freeze_order',f['created']<freeze['created']<started['utc']<=manifest['finished'])
    check('frozen_identities',started['candidate_freeze_sha256']==sha(a/'CANDIDATE_FREEZE.json')
          and freeze['graphs_sha256']==sha(a/'GRAPHS.json') and freeze['mixtures_sha256']==sha(a/'MIXTURES.json'))
    check('holdout_not_in_training_files',all(n not in freeze['training_files'] for n in ('RESULTS.json','TEST_STARTED.json')))
    equal(freeze['heldout_profiles'],list(heldout()),'frozen_holdout_roster')
    equal(modeldata['generation'],generation(10),'generating_laws');equal(modeldata['development'],previous.profiles(),'development_laws')
    equal(modeldata['heldout'],heldout(),'holdout_laws');equal(modeldata['loss_onsets'],list(range(1,11)),'all_onset_loss')
    model=Bayesian(10);equal(modeldata['prior'],model.prior,'prior');equal(modeldata['states'],model.states,'states')
    check('model_dimensions',modeldata['T']==10 and modeldata['D']==200 and len(modeldata['states'])==44 and Q(modeldata['p'])==Q(1,20) and Q(modeldata['rho'])==Q(1,2))
    check('result_dimensions',result['T']==10 and Q(result['rho'])==Q(1,2) and Q(result['budget'])==K)
    exposed={tuple(p) for p in previous.profiles().values()}
    base=Path('/mnt/bioIce1/fep-ideas/formal-checks')
    for folder in ('fep-burst-confidence-v1','fep-burst-learning-v1'):
        exposed.update((Q(alpha),)*9 for alpha in load(base/folder/'attempt-01/RESULTS.json')['cases'])
    check('transfer_profiles_new',len({tuple(p) for p in heldout().values()})==8 and not {tuple(p) for p in heldout().values()}&exposed)
    equal(load(a/'NOVELTY.json'),dict(passed=True,previous_profiles=sorted(exposed),new_profiles=heldout()),'novelty_record')
    check('qualification_passed',load(a/'QUALIFICATION.json')['passed'])
    for fixture in load(a/'LP_FIXTURES.json').values():
        check('qualification_certificate',certified.valid_certificate(fixture['problem'],fixture['certificate']))
    graphs=bundle['graphs'];old=Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-pool-feasibility-v1/attempt-01')
    predecessor=load(old/'READBACK.json');check('predecessor_verified',predecessor['passed'] and predecessor['manifest_sha256']==sha(old/'MANIFEST.json'))
    baseline=load(a/'BASELINES.json')
    legacy=base/'fep-burst-alltiming-v1/attempt-01';legacy_mix=load(legacy/'EVAL_MIXTURES.json')
    expected_baseline=dict(graphs=load(old/'GRAPHS.json')['graphs'],
        mixtures=dict(previous_pool_full=load(old/'MIXTURES.json')['selected_full'],previous_full=legacy_mix['reliability'],
            joint_mixture=legacy_mix['joint_mixture'],fixed_pool=legacy_mix['fixed_pool']),
        direct_controls=['hybrid','always','conservative','fixed_schedule'])
    legacy_graphs=load(legacy/'EVAL_GRAPHS.json')['graphs']
    for n in {c['policy'] for cs in expected_baseline['mixtures'].values() for c in cs}|set(expected_baseline['direct_controls']):
        if n not in expected_baseline['graphs']:expected_baseline['graphs'][n]=legacy_graphs[n]
    equal(baseline,expected_baseline,'baseline_source_identity')
    for n,p in baseline['graphs'].items():equal(graphs[n],p,'frozen_graph_identity')
    for frozen in (False,True):
        family='ablated' if frozen else 'full'
        for mu in (0,1,2,4,8,16):
            name=f'target_{family}_mu{mu:02d}';candidate=load(a/'candidates'/f'{name}.json')
            with gzip.open(a/'bellman'/f'{name}.jsonl.gz','rt',encoding='utf-8') as inp:
                header=json.loads(next(inp));values={(r[0],tuple(r[1])):r[2] for r in map(json.loads,inp)}
            den,coeff=model.coefficients(mu)
            check('bellman_metadata',header['T']==10 and header['D']==200 and header['frozen']==frozen and Q(header['mu'])==mu
                  and header['utility_denominator']==den==candidate['utility_denominator'] and header['states']==len(values)==candidate['bellman_states'])
            def normalized(t,w):return Q(values[t,w],10*den*sum(w)*200**(10-t))
            def scores(t,w):
                total=sum(v*c for v,c in zip(w,coeff[t]));risk=sum(v*c for v,c,(_,tau,z) in zip(w,coeff[t],model.states) if int(0<tau<=t)^z)
                out=dict(B=Q(total,10*den*sum(w)),F=Q(risk,den*sum(w)),R=Q(total-risk,den*sum(w)))
                if t<10:
                    nxt,prob=model.step(t,w,None,frozen);check('unobserved_mass',prob==1)
                    out['F']+=normalized(t+1,nxt);out['R']+=normalized(t+1,nxt);probabilities=[]
                    for d in (0,1):
                        nxt,prob=model.step(t,w,d,frozen);probabilities.append(prob);out['B']+=prob*normalized(t+1,nxt)
                    check('purchased_mass',sum(probabilities)==1)
                return out
            for (t,w),value in values.items():
                check('canonical_state',len(w)==44 and min(w)>0 and math.gcd(*w)==1 and isinstance(value,int))
                check('normalized_bellman',normalized(t,w)==min(scores(t,w).values()));totals['bellman_states']+=1
            equal(candidate['subjective_root'],normalized(1,model.prior),'bayesian_root')
            graph=candidate['graph'];equal(graphs[name],dict(graph=graph,belief='explicit'),'new_graph_identity')
            for node in graph:
                t,w=node['t'],tuple(node['weights']);equal({k:node[k] for k in model.fields(t,w)},model.fields(t,w),'posterior_fields')
                sc=scores(t,w);check('matched_bayesian_action',node['action']==min(('B','F','R'),key=lambda action:sc[action]));totals['new_graph_states']+=1
                for label,child in node['children'].items():
                    if t==10:check('terminal',child is None)
                    else:
                        nxt,_=model.step(t,w,None if label=='N' else int(label),frozen)
                        check('posterior_edge',graph[child]['t']==t+1 and tuple(graph[child]['weights'])==nxt)
            training_record=training(graph,10);equal(candidate['training'],training_record,'generation_costs')
            subjective=(training_record['settings']['training_00']['summary']['J']+mu*training_record['settings']['training_00']['summary']['stable']) if frozen else training_record['C']+mu*sum(training_record['S'])/2
            equal(candidate['subjective_root'],subjective,'objective_identity')
            if frozen:
                oldname=f'ablated_mu{mu:02d}';check('ablated_functional_identity',same_behavior(graph,graphs[oldname]['graph']))
                source=Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-alltiming-v1/attempt-01/candidates')/(oldname+'.json')
                equal(candidate['subjective_root'],Q(load(source)['subjective_root']),'ablated_value_identity')
            print('BELLMAN_READBACK '+name,flush=True)
    records={}
    for label,profile in previous.profiles().items():
        records[label]={n:certified.cost_record(graphs[n]['graph'],profile) for n in costs['records'][label]}
        totals['cost_graph_worlds']+=len(records[label])*11;equal(costs['records'][label],records[label],'independent_costs')
        sealed=load(old/'COSTS.json')['records'][label]
        for n in sealed:equal(sealed[n],records[label][n],'predecessor_cost_reproduction')
    hybrid={n:p['hybrid']['summary']['R'] for n,p in records.items()};expected_mixes={};margins={}
    for kind,expanded in (('original',False),('expanded',True)):
        for family in ('full','ablated'):
            s=selection[kind][family];p=matrix(records,hybrid,family,expanded);equal(s['problem'],p,'constraint_matrix')
            witness=s['certificate'];check('optimality_certificate',certified.valid_certificate(p,witness));totals['certificates']+=1
            x,y=list(map(Q,witness['x'])),list(map(Q,witness['dual']));weights=x[:-1]+[1-sum(x[:-1])]
            check('mixture_weights',min(weights)>=0 and sum(weights)==1)
            components=[dict(policy=n,weight=w) for n,w in zip(p['variables'][:-1]+[p['floor']],weights) if w]
            margin=Q(witness['objective'])-1
            equal(s['components'],components,'selected_components');equal(s['margin'],margin,'margin');equal(s['feasible'],margin>0,'feasibility')
            slacks=[b-sum(u*v for u,v in zip(row,x)) for row,b in zip(p['A'],p['b'])]
            equal(witness['primal_slacks'],slacks,'primal_slacks')
            equal(witness['dual_slacks'],[sum(row[j]*v for row,v in zip(p['A'],y))-c for j,c in enumerate(p['c'])],'dual_slacks')
            equal(s['active'],[n for n,v in zip(p['row_ids'],slacks) if not v],'active_constraints')
            equal(s['dual_support'],[dict(constraint=n,weight=w) for n,w in zip(p['row_ids'],y) if w],'dual_support')
            check('pivot_limit',len(witness['pivots'])<=2000)
            if kind=='original':
                oldsolution=load(old/'SOLUTIONS.json')[family]
                equal(s['components'],[dict(policy=c['policy'],weight=Q(c['weight'])) for c in oldsolution['components']],'old_selection_reproduction')
                equal(s['margin'],Q(oldsolution['margin']),'old_margin_reproduction')
            else:
                expected_mixes['selected_'+family]=components;margins[family]=margin
                check('pool_expansion_monotonicity',margin>=Q(selection['original'][family]['margin']))
                check('hard_budget',all(sum(c['weight']*ps[c['policy']]['summary']['stable'] for c in components)<=K for ps in records.values()))
    check('ablated_pool_unchanged',margins['ablated']==Q(selection['original']['ablated']['margin']))
    expected_mixes['frozen_reliability']=[dict(policy=c['policy'].replace('full_','ablated_',1),weight=c['weight']) for c in expected_mixes['selected_full']]
    expected_mixes['matched_bayesian']=expected_mixes['selected_full']
    expected_mixes.update({n:[dict(policy=c['policy'],weight=Q(c['weight'])) for c in cs] for n,cs in baseline['mixtures'].items()})
    equal(mixes,expected_mixes,'mixture_identities')
    names=sorted({c['policy'] for cs in expected_mixes.values() for c in cs}|set(baseline['direct_controls']))
    equal(freeze['diagnostic_graphs'],names,'diagnostic_roster')
    cases={};profiles={**previous.profiles(),**heldout()};beliefs={n:previous.flow.beliefs(graphs[n]['graph'],graphs[n]['belief']) for n in names}
    comparisons=tuple(baseline['mixtures'])+tuple(baseline['direct_controls'])+('frozen_reliability','selected_ablated','matched_bayesian')
    for label,profile in profiles.items():
        ps={}
        for n in names:
            ws=[previous.forward(graphs[n]['graph'],beliefs[n],10,tau,profile) for tau in [None,*range(1,11)]]
            ps[n]=dict(worlds=ws,summary=previous.summary(ws));totals['diagnostic_graph_worlds']+=11
        for n,cs in expected_mixes.items():ps[n]=certified.blend(ps,cs)
        gs={n:certified.gates(p['summary'],ps['hybrid']['summary']) for n,p in ps.items()}
        cases[label]=dict(profile=profile,held_out_pattern=label in heldout(),policies=ps,gates=gs,
            comparisons={n:certified.difference(ps['selected_full'],ps[n]) for n in comparisons})
        equal(ps['selected_full'],ps['matched_bayesian'],'matched_bayesian_outcomes')
        print('PHYSICAL_READBACK '+label,flush=True)
    for label,case in cases.items():
        case['independence_deltas']={n:{k:None if v is None else v-cases['training_00']['policies'][n]['summary'][k]
            for k,v in case['policies'][n]['summary'].items()} for n in ('selected_full','frozen_reliability','selected_ablated')}
    equal(result['cases'],cases,'all_diagnostic_results');equal(result['profiles'],profiles,'all_physical_profiles')
    equal(result['heldout_profiles'],list(heldout()),'test_roster')
    primary={part:{n:all(all(cases[l]['gates'][n][k] for k in ('stable','always_recovery','hybrid_recovery')) for l in labels)
        for n in ('selected_full','frozen_reliability','selected_ablated')} for part,labels in [('development',previous.profiles()),('transfer',heldout())]}
    equal(result['primary_pass'],primary,'primary_outcomes')
    check('certificate_outcomes',all(primary['development']['selected_'+f]==(margins[f]>0) for f in margins))
    equal(result['deployment_ready'],primary['development']['selected_full'] and primary['transfer']['selected_full'],'deployment_readiness')
    mechanisms={l:{n:dict(lower_R=c['comparisons'][n]['summary']['R']<0,lower_J=c['comparisons'][n]['summary']['J']<0,
        full_stable=c['gates']['selected_full']['stable'],comparator_stable=c['gates'][n]['stable']) for n in ('frozen_reliability','selected_ablated')} for l,c in cases.items()}
    equal(result['mechanisms'],mechanisms,'mechanism_results')
    report=dict(passed=True,completed=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start,total_checks=sum(counts.values()),
        checks=counts,totals=totals,manifest_sha256=sha(a/'MANIFEST.json'),source_sha256=sha(__file__),
        method='Independent time-dependent normalized Bayesian Bellman audit, exact pool primal/dual certificates, frozen ablated equivalence and variable-persistence diagnostic flow; development and transfer separated.')
    with (a/'READBACK.json').open('x') as out:json.dump(report,out,indent=2,sort_keys=True);out.write('\n')
    print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
