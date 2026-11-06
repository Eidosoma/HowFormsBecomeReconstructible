#!/usr/bin/env python3
"""Independent normalized Bayesian planning and held-out physical audit."""
from collections import defaultdict
from datetime import datetime,timezone
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path
import gzip
import hashlib
import itertools
import json
import math
import sys
import time

import readback_fep_burst_confidence as flow

sys.set_int_max_str_digits(0)
K=Q(19568652557,204800000000)


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def primitive(probabilities):
    denominator=math.lcm(*(p.denominator for p in probabilities));counts=[int(p*denominator) for p in probabilities]
    common=math.gcd(*counts);return tuple(v//common for v in counts)


class Bayesian:
    def __init__(self,T):
        self.T=T;self.states=tuple((a,j,z) for a in (Q(0),Q(3,4)) for j in range(T+1) for z in (0,1));self.D=80
        self.prior=primitive([Q(1,2)*(Q(1,2) if tau==0 else Q(1,2*T))*(Q(19,20) if z==0 else Q(1,20)) for _,tau,z in self.states])
        self.step=lru_cache(None)(self._step)

    def _step(self,t,w,label,frozen):
        probabilities=[Q(v,sum(w)) if label is None or label==(int(0<tau<=t)^z) else Q(0) for v,(_,tau,z) in zip(w,self.states)]
        probability=sum(probabilities)
        if frozen:
            onset=[sum(p for p,(_,j,_) in zip(probabilities,self.states) if j==tau) for tau in range(self.T+1)]
            next_=[onset[tau]*Q(1,2)*(Q(19,20) if z==0 else Q(1,20)) for _,tau,z in self.states]
        else:
            next_=[]
            for i in range(0,len(probabilities),2):
                a=self.states[i][0];zero,one=probabilities[i:i+2]
                flip=zero*Q(1,20)*(1-a)+one*(Q(1,20)+Q(19,20)*a)
                next_.extend([zero+one-flip,flip])
        return primitive(next_),probability

    def coefficients(self,mu):
        odd=list(range(1,self.T+1,2));n=len(odd)
        weights={t:[(Q(1,self.T) if j==0 else Q(1,n) if j in odd else Q(0))+
                    (Q(2*self.T,n*(self.T-j+1)) if j in odd and j<=t else 0)+
                    (Q(2*mu,self.T) if j==0 else 0) for _,j,_ in self.states] for t in range(1,self.T+1)}
        denominator=math.lcm(*(p.denominator for row in weights.values() for p in row))
        return denominator,{t:[int(p*denominator) for p in row] for t,row in weights.items()}

    def fields(self,t,w):
        qs=Q(sum(v for v,(_,j,_) in zip(w,self.states) if 0<j<=t),sum(w));posts=[]
        for d in (0,1):
            subset=[(v,j) for v,(_,j,z) in zip(w,self.states) if d==(int(0<j<=t)^z)]
            posts.append(Q(sum(v for v,j in subset if 0<j<=t),sum(v for v,_ in subset)))
        return dict(q_orientation=qs,post_orientation=posts,q_error=Q(sum(v for v,(_,_,z) in zip(w,self.states) if z),sum(w)),
            q_persistent=Q(sum(v for v,(a,_,_) in zip(w,self.states) if a==Q(3,4)),sum(w)))


def physical(graph,T,tau,alpha):
    @lru_cache(None)
    def future(i,z):
        if i is None:return (Q(0),)*4
        node=graph[i];post=tau is not None and node['t']>=tau;buy=node['action']=='B';label=int(post)^z
        child=node['children'][str(label) if buy else 'N']
        probability=Q(1,20)+(Q(19,20)*alpha if z else -Q(1,20)*alpha)
        next_=[(1-probability)*a+probability*b for a,b in zip(future(child,0),future(child,1))]
        error=int(not buy and label!=int(node['action']=='R'))
        return tuple(v+reward for v,reward in zip(next_,(error,int(buy),error if post else 0,int(buy and post))))
    e,b,pe,pb=[Q(19,20)*x+Q(1,20)*y for x,y in zip(future(0,0),future(0,1))]
    return dict(onset=tau,cost=e+b/10,errors=e,purchases=b,post_cost=pe+pb/10,post_errors=pe,post_purchases=pb,
                recovery=None if tau is None else (pe+pb/10)/(T-tau+1))


def training(graph,T):
    onsets=list(range(1,T+1,2));settings={}
    for alpha in (Q(0),Q(3,4)):
        rows=[physical(graph,T,tau,alpha) for tau in [None,*onsets]]
        s=rows[0]['cost']/T;b=(s+sum(w['cost'] for w in rows[1:])/(len(onsets)*T))/2
        r=sum(w['recovery'] for w in rows[1:])/len(onsets)
        settings[str(alpha)]=dict(worlds=rows,stable=s,B_odd=b,R_odd=r,C=b+r)
    return dict(settings=settings,C=sum(v['C'] for v in settings.values())/2,S=[settings[k]['stable'] for k in ('0','3/4')])


def schedule_graph(m,mask):
    nodes=[];indices={}
    def node(t,w):
        if t>m.T:return None
        key=t,w
        if key in indices:return indices[key]
        i=len(nodes);indices[key]=i;nodes.append(None)
        error_probability=Q(sum(v for v,(_,j,z) in zip(w,m.states) if int(0<j<=t)^z),sum(w))
        action='B' if (mask//2**(t-1))%2 else 'R' if error_probability>Q(1,2) else 'F'
        children={}
        for label in ((0,1) if action=='B' else (None,)):
            child=None if t==m.T else node(t+1,m.step(t,w,label,False)[0]);children[str(label) if label is not None else 'N']=child
        nodes[i]=dict(t=t,weights=w,action=action,children=children,**m.fields(t,w))
        return i
    node(1,m.prior);return nodes


def determinant(matrix):
    if len(matrix)==1:return matrix[0][0]
    return sum((-1)**j*matrix[0][j]*determinant([row[:j]+row[j+1:] for row in matrix[1:]]) for j in range(len(matrix)))


def pool_vertices(records,budget):
    result={};names=sorted(records)
    for size in (1,2,3):
        for support in itertools.combinations(names,size):
            for constraints in itertools.combinations((0,1),size-1):
                matrix=[[Q(1)]*size]+[[records[n]['S'][j] for n in support] for j in constraints]
                rhs=[Q(1)]+[budget]*(size-1);det=determinant(matrix)
                if not det:continue
                weights=[]
                for col in range(size):
                    replaced=[[rhs[i] if j==col else x for j,x in enumerate(row)] for i,row in enumerate(matrix)]
                    weights.append(determinant(replaced)/det)
                if min(weights)<0:continue
                cs=tuple((n,w) for n,w in zip(support,weights) if w)
                stable=[sum(w*records[n]['S'][j] for n,w in cs) for j in (0,1)]
                if max(stable)>budget:continue
                result[cs]=dict(components=[dict(policy=n,weight=w) for n,w in cs],C=sum(w*records[n]['C'] for n,w in cs),S=stable)
    return list(result.values())


def inverse(graph,T,tau,alpha):
    @lru_cache(None)
    def future(i,z,seen):
        if i is None:return Q(0),Q(not seen),Q(0)
        n=graph[i];post=tau is not None and n['t']>=tau;action=n['action'];now=seen or (post and action=='R')
        d=int(post)^z;child=n['children'][str(d) if action=='B' else 'N']
        p=Q(1,20)*(1-alpha)+alpha*z
        following=tuple((1-p)*a+p*b for a,b in zip(future(child,0,now),future(child,1,now)))
        return following[0]+int(post and not now),following[1],following[2]+int(not post and action=='R')
    vals=[Q(19,20)*a+Q(1,20)*b for a,b in zip(future(0,0,False),future(0,1,False))]
    return dict(zip(('inverse_delay','inverse_missing','pre_inverse'),vals))


def summary(ws):
    out=flow.summarize(ws,10,Q(1,2));out.update(stable_inverse=ws[0]['pre_inverse']/10,
        mean_inverse_delay=sum(w['inverse_delay'] for w in ws[1:])/10,no_inverse_probability=sum(w['inverse_missing'] for w in ws[1:])/10)
    for name,ids in [('odd',range(1,11,2)),('even',range(2,11,2))]:
        out[name+'_B']=out['stable']/2+sum(ws[j]['cost'] for j in ids)/100
        out[name+'_R']=sum(ws[j]['recovery'] for j in ids)/5
    return out


def main():
    start=time.monotonic();a=Path(sys.argv[1]);counts={};totals=dict(bellman_states=0,candidate_graph_states=0,fixed_schedules=0,physical_graph_worlds=0)
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
    f,manifest,freeze,started,graphs,mixes,selection,schedules,result=[load(a/n) for n in ('FREEZE.json','MANIFEST.json','CANDIDATE_FREEZE.json',
        'TEST_STARTED.json','EVAL_GRAPHS.json','EVAL_MIXTURES.json','SELECTION.json','SCHEDULES.json','RESULTS.json')]
    check('complete',manifest['status']=='COMPLETE')
    for n,h in f['inputs'].items():check('source_hash',sha(n)==h)
    for n,h in f['snapshots'].items():check('snapshot_hash',sha(a/'inputs'/n)==h)
    for n,h in manifest['outputs'].items():check('output_hash',sha(a/n)==h)
    for n,h in freeze['training_files'].items():check('candidate_freeze_hash',sha(a/n)==h)
    check('freeze_order',freeze['created']<started['utc']<=manifest['finished'] and started['candidate_freeze_sha256']==sha(a/'CANDIDATE_FREEZE.json'))
    check('freeze_precedes_test',all(n not in freeze['training_files'] for n in ('RESULTS.json','TEST_STARTED.json')))
    check('frozen_eval_identity',freeze['evaluation_graphs_sha256']==sha(a/'EVAL_GRAPHS.json') and freeze['evaluation_mixtures_sha256']==sha(a/'EVAL_MIXTURES.json'))
    model=Bayesian(10);candidates={};costs={};mus=(0,1,2,4,8,16)

    for frozen in (False,True):
        for mu in mus:
            name=f'{"ablated" if frozen else "full"}_mu{mu:02d}';p=load(a/'candidates'/f'{name}.json');candidates[name]=p
            with gzip.open(a/'bellman'/f'{name}.jsonl.gz','rt',encoding='utf-8') as inp:
                header=json.loads(next(inp));values={(row[0],tuple(row[1])):row[2] for row in map(json.loads,inp)}
            den,coeff=model.coefficients(mu)
            check('bellman_metadata',header['T']==10 and header['D']==80 and header['frozen']==frozen and Q(header['mu'])==mu
                  and header['utility_denominator']==p['utility_denominator']==den and header['states']==len(values)==p['bellman_states'])
            def normalized(t,w):return Q(values[t,w],10*den*sum(w)*80**(10-t))
            def scores(t,w):
                total=sum(v*c for v,c in zip(w,coeff[t]));risk=sum(v*c for v,c,(_,j,z) in zip(w,coeff[t],model.states) if int(0<j<=t)^z)
                out=dict(F=Q(risk,den*sum(w)),R=Q(total-risk,den*sum(w)),B=Q(total,10*den*sum(w)))
                if t<10:
                    nxt,prob=model.step(t,w,None,frozen);check('unobserved_mass',prob==1)
                    out['F']+=normalized(t+1,nxt);out['R']+=normalized(t+1,nxt)
                    probs=[]
                    for d in (0,1):
                        nxt,prob=model.step(t,w,d,frozen);probs.append(prob);out['B']+=prob*normalized(t+1,nxt)
                    check('purchased_mass',sum(probs)==1)
                return out
            for (t,w),value in values.items():
                check('canonical_weights',len(w)==44 and min(w)>0 and math.gcd(*w)==1 and isinstance(value,int))
                check('normalized_bellman',normalized(t,w)==min(scores(t,w).values()));totals['bellman_states']+=1
            equal(p['subjective_root'],normalized(1,model.prior),'bayesian_root')
            graph=p['graph'];check('graph_root',tuple(graph[0]['weights'])==model.prior)
            for n in graph:
                t=n['t'];w=tuple(n['weights']);sc=scores(t,w);best=min(('B','F','R'),key=lambda c:sc[c])
                check('matched_bayesian_action',n['action']==best);totals['candidate_graph_states']+=1
                equal({k:n[k] for k in model.fields(t,w)},model.fields(t,w),'graph_beliefs')
                for label,child in n['children'].items():
                    if t==10:check('terminal_child',child is None)
                    else:
                        nw,_=model.step(t,w,None if label=='N' else int(label),frozen)
                        check('posterior_edge',graph[child]['t']==t+1 and tuple(graph[child]['weights'])==nw)
            c=training(graph,10);equal(p['training'],c,'candidate_training');costs[name]=c
            check('subjective_cost_identity',Q(p['subjective_root'])==(c['settings']['0']['C']+mu*c['settings']['0']['stable'] if frozen else c['C']+mu*sum(c['S'])/2))
    for prefix in ('full','ablated'):
        name=prefix+'_floor';p=load(a/'candidates'/f'{name}.json');candidates[name]=p
        check('floor_rule',all(n['action']=='F' and tuple(n['weights'])==model.prior for n in p['graph']))
        costs[name]=training(p['graph'],10);equal(p['training'],costs[name],'floor_training')
    vertices=pool_vertices({n:v for n,v in costs.items() if n.startswith('full_')},K)
    key=lambda r:(r['C'],len(r['components']),tuple(c['policy'] for c in r['components']),tuple(c['weight'] for c in r['components']))
    expected=min(vertices,key=key);equal(selection['selected'],expected,'finite_pool_optimum')
    canon=lambda r:tuple((c['policy'],Q(c['weight'])) for c in r['components'])
    expected_vertices={canon(p):p for p in vertices};actual_vertices={canon(p):p for p in selection['vertices']}
    check('vertex_set',set(expected_vertices)==set(actual_vertices))
    for k,v in expected_vertices.items():equal(actual_vertices[k],v,'feasible_vertex')
    equal(freeze['selected'],expected,'frozen_selection')

    best=None;best_graph=None
    for row in schedules['records']:
        mask=row['mask'];graph=schedule_graph(model,mask);cost=training(graph,10)
        equal(row['training'],cost,'all_fixed_schedules');totals['fixed_schedules']+=1
        if max(cost['S'])<=K and (best is None or (cost['C'],mask)<(best['training']['C'],best['mask'])):
            best=dict(mask=mask,training=cost);best_graph=graph
    check('all_masks',sorted(row['mask'] for row in schedules['records'])==list(range(1024)))
    equal(schedules['selected'],best,'best_fixed_schedule');equal(graphs['graphs']['fixed_schedule']['graph'],best_graph,'fixed_schedule_identity')
    check('frozen_schedule',freeze['fixed_schedule']==best['mask'])
    # Clear the large normalized filter cache before the physical held-out audit.
    model.step.cache_clear()
    previous=next(Path(n).parent for n in f['inputs'] if 'fep-noise-sequence-v1/' in n and n.endswith('/GRAPHS.json'))
    original=load(previous/'GRAPHS.json');original_mix=load(previous/'MIXTURES.json')
    for name,p in original['graphs'].items():equal(graphs['graphs'][name],p,'original_graph_identity')
    for name,cs in original_mix.items():equal(mixes[name],cs,'original_mixture_identity')
    equal(mixes['reliability'],expected['components'],'selected_weights')
    equal(mixes['matched_bayesian'],expected['components'],'matched_bayesian_weights')
    equal(mixes['frozen_reliability'],[dict(policy=c['policy'].replace('full_','ablated_',1),weight=c['weight']) for c in expected['components']],'ablated_weights')
    for name,p in graphs['graphs'].items():
        if name in candidates:equal(p,{k:candidates[name][k] for k in ('graph','belief')},'candidate_graph_identity')
    for n in graphs['graphs']['conservative']['graph']:
        t=n['t'];direction=n['direction'];count=n['opposite_count'];action='B' if t%2==0 else 'R' if direction else 'F'
        check('conservative_rule',n['action']==action)
        for label,child in n['children'].items():
            if t==10:check('conservative_terminal',child is None);continue
            direction2,count2=direction,count
            if label!='N':
                d=int(label)
                if d==direction:count2=0
                elif count:direction2,count2=d,0
                else:count2=1
            nn=graphs['graphs']['conservative']['graph'][child]
            check('conservative_transition',(nn['t'],nn['direction'],nn['opposite_count'])==(t+1,direction2,count2))
    heldout=[Q(1,8),Q(3,8),Q(5,8),Q(7,8),Q(19,20)]
    equal(result['test_alphas'],heldout,'heldout_roster');equal(result['training_alphas'],[Q(0),Q(3,4)],'training_roster')
    reconstructed={}
    for alpha in [Q(0),Q(3,4),*heldout]:
        saved=result['cases'][str(alpha)];ps={}
        for name,p in graphs['graphs'].items():
            qs=flow.beliefs(p['graph'],p['belief']);ws=[]
            for tau in [None,*range(1,11)]:
                row=flow.forward(p['graph'],qs,10,tau,alpha);row.update(inverse(p['graph'],10,tau,alpha));ws.append(row);totals['physical_graph_worlds']+=1
            ps[name]=dict(worlds=ws,summary=summary(ws))
        for name,cs in mixes.items():
            ws=[]
            for j,tau in enumerate([None,*range(1,11)]):
                row=dict(onset=tau)
                for k in ps[cs[0]['policy']]['worlds'][j]:
                    if k=='onset':continue
                    values=[(Q(c['weight']),ps[c['policy']]['worlds'][j][k]) for c in cs]
                    row[k]=None if any(v is None for _,v in values) else sum(w*v for w,v in values)
                ws.append(row)
            ps[name]=dict(components=cs,worlds=ws,summary=summary(ws))
        equal(saved['policies'],ps,'heldout_metrics');check('heldout_label',saved['held_out_duration']==(alpha in heldout));reconstructed[str(alpha)]=ps
        h=ps['hybrid']['summary'];gs={}
        for name,p in ps.items():
            s=p['summary'];gs[name]=dict(stable=s['stable']<=K,always_recovery=s['R']<Q(1,10),hybrid_recovery=s['R']<h['R'],
                matched_stable=s['stable']<=h['stable'],hybrid_full=s['B']<h['B'],always_full=s['B']<Q(1,10))
        equal(saved['gates'],gs,'heldout_gates')
        s=ps['reliability']
        for name in saved['comparisons']:
            control=ps[name]
            expected_comp=dict(summary={k:None if control['summary'][k] is None else v-control['summary'][k] for k,v in s['summary'].items()},
                worlds=[dict(onset=u['onset'],full=(u['cost']-v['cost'])/10,recovery=None if u['recovery'] is None else u['recovery']-v['recovery']) for u,v in zip(s['worlds'],control['worlds'])])
            equal(saved['comparisons'][name],expected_comp,'heldout_comparison')
        equal(ps['matched_bayesian']['worlds'],ps['reliability']['worlds'],'matched_planner_function')
    equal(result['primary_pass'],all(all(result['cases'][str(alpha)]['gates']['reliability'][k] for k in ('stable','always_recovery','hybrid_recovery')) for alpha in heldout),'primary_outcome')
    mechanism={}
    for alpha in heldout:
        ps=reconstructed[str(alpha)];full=ps['reliability']['summary'];abl=ps['frozen_reliability']['summary']
        mechanism[str(alpha)]=dict(lower_R=full['R']<abl['R'],lower_J=full['J']<abl['J'],full_stable=full['stable']<=K,ablated_stable=abl['stable']<=K)
    equal(result['mechanism'],mechanism,'mechanism_outcomes')
    report=dict(passed=True,completed=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start,total_checks=sum(counts.values()),checks=counts,totals=totals,
        manifest_sha256=sha(a/'MANIFEST.json'),source_sha256=sha(__file__),
        method='Independent normalized Bayesian Bellman equations, Cramer-rule finite-pool vertices, all 1024 fixed schedules, candidate freeze chronology and augmented-state Markov physical/diagnostic verification.')
    with (a/'READBACK.json').open('x') as out:json.dump(report,out,indent=2,sort_keys=True);out.write('\n')
    print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
