#!/usr/bin/env python3
"""Independent augmented-state forward audit for correlated-error studies."""
from collections import defaultdict
from datetime import datetime,timezone
from fractions import Fraction as Q
from pathlib import Path
import hashlib
import json
import sys
import time

sys.set_int_max_str_digits(0)
RAW=('errors','purchases','post_errors','post_purchases','delay','missing','wrong95','any_wrong95',
     'wrong95_errors','adoption_delay','adoption_missing','false_adoption','repeat_events','repeat_increases')
BELIEF=('wrong95','any_wrong95','wrong95_errors','adoption_delay','adoption_missing','false_adoption',
        'repeat_increases','brier','confidence','repeat_gain')


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def beliefs(graph,kind):
    if kind=='none':return [None]*len(graph)
    if kind=='explicit':return [dict(q=Q(n['q_orientation']),post=list(map(Q,n['post_orientation']))) for n in graph]
    result=[];noises=[Q(4,100),Q(5,100),Q(6,100)] if kind=='joint_noise' else [Q(1,20)]
    for node in graph:
        weights=node['weights'];width=len(weights)//len(noises);cut=node['t']
        probabilities=[Q(x,sum(weights)) for x in weights]
        orientation=[int(0<j%width<=cut) for j in range(len(weights))]
        q=sum(p*y for p,y in zip(probabilities,orientation));posterior=[]
        for label in (0,1):
            joint=[p*(1-noises[j//width] if y==label else noises[j//width]) for j,(p,y) in enumerate(zip(probabilities,orientation))]
            posterior.append(sum(p*y for p,y in zip(joint,orientation))/sum(joint))
        result.append(dict(q=q,post=posterior))
    return result


def forward(graph,qs,T,tau,alpha):
    num,den=alpha.numerator,alpha.denominator;scale=20*den;normalizer=20*scale**(T-1)
    trans=((19*den+num,den-num),(19*(den-num),den+19*num))
    # State: node, current error, last purchased report, last report wrong,
    # ever wrongly confident, orientation adoption, acquired after reversal.
    states={(0,0,-1,False,False,False,False):19,(0,1,-1,False,False,False,False):1}
    totals={k:0 for k in RAW};visits=[0]*len(graph);repeats=[0]*len(graph);terminal=0
    for t in range(1,T+1):
        next_states=defaultdict(int);lift=scale**(T-t);truth=int(tau is not None and t>=tau)
        for (i,z,last,last_bad,seen,adopted,acquired),mass in states.items():
            if not mass:continue
            node=graph[i];assert node['t']==t
            buy=node['action']=='B';label=z^truth;error=int(not buy and label!=int(node['action']=='R'))
            v=qs[i];wrong=False if v is None else (v['q'] if not truth else 1-v['q'])>=Q(19,20)
            adopt=adopted or (truth and v is not None and v['q']>=Q(9,10))
            acquired2=acquired or (truth and buy);seen2=seen or wrong;weight=mass*lift
            visits[i]+=weight;totals['errors']+=weight*error;totals['purchases']+=weight*buy
            totals['wrong95']+=weight*wrong;totals['wrong95_errors']+=weight*wrong*error
            totals['false_adoption']+=weight*int(not truth and v is not None and v['q']>=Q(9,10))
            if truth:
                totals['post_errors']+=weight*error;totals['post_purchases']+=weight*buy
                totals['delay']+=weight*int(not acquired2);totals['adoption_delay']+=weight*int(not adopt)
            if buy and last_bad and z and last==label:
                totals['repeat_events']+=weight;repeats[i]+=weight
                if v is not None:
                    change=(v['post'][label]-v['q'])*(1 if truth==0 else -1)
                    totals['repeat_increases']+=weight*int(change>0)
            child=node['children'][str(label) if buy else 'N']
            if t==T:
                assert child is None;terminal+=mass
                totals['missing']+=mass*int(not acquired2);totals['any_wrong95']+=mass*int(seen2)
                totals['adoption_missing']+=mass*int(not adopt)
            else:
                for zz,prob in enumerate(trans[z]):
                    if prob:next_states[(child,zz,label if buy else last,bool(z) if buy else last_bad,seen2,adopt,acquired2)]+=mass*prob
        states=next_states
    assert terminal==normalizer
    result=dict(onset=tau,**{k:Q(v,normalizer) for k,v in totals.items()})
    if qs[0] is None:result.update({k:None for k in BELIEF})
    else:
        scores=[];conf=[];gain=[]
        for i,node in enumerate(graph):
            actual=int(tau is not None and node['t']>=tau);q=qs[i]['q']
            scores.append(Q(visits[i],normalizer)*(q-actual)**2)
            conf.append(Q(visits[i],normalizer)*(Q(1,2)+abs(q-Q(1,2))))
            gain.append(Q(repeats[i],normalizer)*(qs[i]['post'][1-actual]-q)*(1-2*actual))
        result.update(brier=sum(scores),confidence=sum(conf),repeat_gain=sum(gain))
    result['cost']=result['errors']+result['purchases']/10
    result['post_cost']=result['post_errors']+result['post_purchases']/10
    result['recovery']=None if tau is None else result['post_cost']/(T-tau+1)
    return result


def summarize(ws,T,rho):
    def prior(k):return None if ws[0][k] is None else sum(w[k]*(1-rho if j==0 else rho/T) for j,w in enumerate(ws))
    def divided(x,n):return None if x is None else x/n
    full=prior('cost')/T;rec=sum(ws[j]['post_cost']/(T-j+1) for j in range(1,T+1))/T
    out=dict(stable=ws[0]['cost']/T,B=full,R=rec,J=full+rec,stable_errors=ws[0]['errors'],stable_purchases=ws[0]['purchases'],
        mean_post_errors=sum(w['post_errors'] for w in ws[1:])/T,mean_post_purchases=sum(w['post_purchases'] for w in ws[1:])/T,
        mean_pre_purchases=sum(w['purchases']-w['post_purchases'] for w in ws[1:])/T,
        capped_first_delay=sum(w['delay'] for w in ws[1:])/T,no_post_purchase_probability=sum(w['missing'] for w in ws[1:])/T)
    for k in ('brier','confidence','wrong95','wrong95_errors','false_adoption'):
        out['stable_'+k]=divided(ws[0][k],T);out['prior_'+k]=divided(prior(k),T)
    for k in ('any_wrong95','repeat_events','repeat_increases','repeat_gain'):
        out['stable_'+k]=ws[0][k];out['prior_'+k]=prior(k)
    out['mean_adoption_delay']=None if ws[0]['adoption_delay'] is None else sum(w['adoption_delay'] for w in ws[1:])/T
    out['no_adoption_probability']=None if ws[0]['adoption_missing'] is None else sum(w['adoption_missing'] for w in ws[1:])/T
    return out


def main():
    start=time.monotonic();a=Path(sys.argv[1]);checks={};worlds=0
    def check(k,ok):
        checks[k]=checks.get(k,0)+1
        if not ok:raise AssertionError(k)
    def equal(u,v,k):
        if isinstance(v,dict):
            check(k+':fields',set(u)==set(v))
            for key,x in v.items():equal(u[key],x,k)
        elif isinstance(v,(list,tuple)):
            check(k+':length',len(u)==len(v))
            for x,y in zip(u,v):equal(x,y,k)
        elif isinstance(v,Q):check(k,Q(u)==v)
        else:check(k,u==v)
    f,m,g,mixes,r,fixtures=[load(a/n) for n in ('FREEZE.json','MANIFEST.json','GRAPHS.json','MIXTURES.json','RESULTS.json','FIXTURES.json')]
    check('complete',m['status']=='COMPLETE')
    for p,h in f['inputs'].items():check('input_hash',sha(p)==h)
    for p,h in f['snapshots'].items():check('snapshot_hash',sha(a/'inputs'/p)==h)
    for p,h in m['outputs'].items():check('output_hash',sha(a/p)==h)
    source=next(Path(p).parent for p in f['inputs'] if p.endswith('/DIAGNOSTICS.json'))
    inherited=load(source/'MANIFEST.json');rv=load(source/'READBACK.json')
    check('inherited_verified',rv['passed'] and rv['manifest_sha256']==sha(source/'MANIFEST.json'))
    for n in ('GRAPHS.json','MIXTURES.json'):
        check('frozen_identity',sha(a/n)==sha(source/n)==inherited['outputs'][n])
    T=10;rho=Q(1,2);budget=Q(19568652557,204800000000)
    check('scope',r['T']==g['T']==T and Q(r['rho'])==rho and Q(r['budget'])==budget)
    check('correlation_roster',list(map(Q,r['alphas']))==[Q(0),Q(1,4),Q(1,2),Q(3,4),Q(9,10),Q(1)])
    graphs=dict(g['graphs']);graphs['always']=dict(belief='none',graph=[dict(t=t,action='B',children={str(z):t if t<T else None for z in (0,1)}) for t in range(1,T+1)])
    rebuilt={}
    for alpha in map(Q,r['alphas']):
        case=r['cases'][str(alpha)];ps={}
        # Marginal invariance follows by explicit matrix propagation.
        distribution=[Q(19,20),Q(1,20)];matrix=[[1-Q(1,20)*(1-alpha),Q(1,20)*(1-alpha)],
            [Q(19,20)*(1-alpha),Q(1,20)+Q(19,20)*alpha]]
        for _ in range(T):
            check('stationary_marginal',distribution==[Q(19,20),Q(1,20)])
            distribution=[sum(distribution[i]*matrix[i][j] for i in (0,1)) for j in (0,1)]
        for name,p in graphs.items():
            qs=beliefs(p['graph'],p['belief']);rows=[]
            for tau in [None,*range(1,T+1)]:rows.append(forward(p['graph'],qs,T,tau,alpha));worlds+=1
            ps[name]=dict(worlds=rows,summary=summarize(rows,T,rho))
        for name,cs in mixes.items():
            check('weights',sum(Q(c['weight']) for c in cs)==1 and all(Q(c['weight'])>=0 for c in cs))
            rows=[]
            for j,tau in enumerate([None,*range(1,T+1)]):
                row=dict(onset=tau)
                for k in ps[cs[0]['policy']]['worlds'][j]:
                    if k=='onset':continue
                    vals=[(Q(c['weight']),ps[c['policy']]['worlds'][j][k]) for c in cs]
                    row[k]=None if any(x is None for _,x in vals) else sum(w*x for w,x in vals)
                rows.append(row)
            ps[name]=dict(components=cs,worlds=rows,summary=summarize(rows,T,rho))
        equal(case['policies'],ps,'worlds_and_summaries');rebuilt[str(alpha)]=ps
        h=ps['hybrid']['summary'];gs={}
        for name in mixes:
            s=ps[name]['summary'];gs[name]=dict(stable=s['stable']<=budget,always_recovery=s['R']<Q(1,10),hybrid_recovery=s['R']<h['R'],
                matched_stable=s['stable']<=h['stable'],hybrid_full=s['B']<h['B'],always_full=s['B']<Q(1,10))
        equal(case['gates'],gs,'gates')
        check('mean_run',case['mean_error_run'] is None if alpha==1 else Q(case['mean_error_run'])==1/(Q(19,20)*(1-alpha)))
        for name in ('joint_mixture','fixed_pool'):
            for control in ('hybrid','always','old_'+name):
                s,p=ps[name],ps[control]
                expected=dict(summary={k:None if p['summary'][k] is None else v-p['summary'][k] for k,v in s['summary'].items()},
                    worlds=[dict(onset=u['onset'],full=(u['cost']-v['cost'])/T,recovery=None if u['recovery'] is None else u['recovery']-v['recovery']) for u,v in zip(s['worlds'],p['worlds'])])
                equal(case['comparisons'][name][control],expected,'comparisons')
    for key,ps in rebuilt.items():
        expected={n:{k:None if v is None else v-rebuilt['0'][n]['summary'][k] for k,v in ps[n]['summary'].items()}
                  for n in ('joint_mixture','fixed_pool')}
        equal(r['cases'][key]['independence_deltas'],expected,'independence_comparison')
    equal(r['overall'],{n:all(all(c['gates'][n][k] for k in ('stable','always_recovery','hybrid_recovery')) for c in r['cases'].values()) for n in ('joint_mixture','fixed_pool')},'overall')
    old=load(source/'DIAGNOSTICS.json')['constant_05']['policies'];count=0
    for name,p in rebuilt['0'].items():
        for u,v in zip(p['worlds'],old[name]['worlds']):
            for k in ('cost','errors','purchases','post_cost','post_errors','post_purchases','delay','missing','recovery'):
                equal(v[k],u[k],'independent_reproduction');count+=1
            equal(v['orientation_brier'],u['brier'],'brier_reproduction');count+=1
    check('reproduction_count',load(a/'REPRODUCTION.json')==dict(passed=True,checks=count))
    # Short readback exercises changed horizon and explicit known repeated paths.
    for fixture in fixtures:
        t=fixture['T'];graph=fixture['graph'];qs=beliefs(graph,fixture['belief'])
        for tau in [None,*range(1,t+1)]:
            w=forward(graph,qs,t,tau,Q(1));worlds+=1
            check('short_nonnegative',all(v is None or v>=0 for k,v in w.items() if k!='onset'))
    result=dict(passed=True,completed=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start,
        total_checks=sum(checks.values()),checks=checks,graph_worlds=worlds,manifest_sha256=sha(a/'MANIFEST.json'),source_sha256=sha(__file__),
        method='Independent augmented-state Markov forward flow, separate likelihood calculations, marginal propagation, mixture/gate arithmetic and exact independent-5%-noise reproduction.')
    with (a/'READBACK.json').open('x') as out:json.dump(result,out,indent=2,sort_keys=True);out.write('\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
