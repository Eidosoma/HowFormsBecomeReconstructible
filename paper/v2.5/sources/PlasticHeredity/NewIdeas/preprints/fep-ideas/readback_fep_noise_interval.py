#!/usr/bin/env python3
"""Independent full-noise-path polynomial reconstruction and interval proof audit."""
from datetime import datetime, timezone
from fractions import Fraction as Q
from pathlib import Path
import hashlib
import itertools
import json
import math
import sys
import time

sys.set_int_max_str_digits(0)
FIELDS=('cost','errors','purchases','post_cost','post_errors','post_purchases','delay','missing','recovery')


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def clean(p):
    p=list(map(Q,p))
    while len(p)>1 and p[-1]==0:p.pop()
    return p


def plus(a,b):
    out=[Q(0)]*max(len(a),len(b))
    for i,v in enumerate(a):out[i]+=v
    for i,v in enumerate(b):out[i]+=v
    return clean(out)


def times(p,factor):return clean(v*factor for v in p)
def minus(a,b):return plus(a,times(b,-1))
def at(p,x):return sum(v*x**i for i,v in enumerate(p))
def diff(p):return clean([i*v for i,v in enumerate(p)][1:] or [0])


def main():
    start,a=time.monotonic(),Path(sys.argv[1])
    counts={};totals=dict(graphs=0,worlds=0,noise_paths=0,certificates=0,leaves=0,identity_points=0,
                          main_graph_nodes=0,max_subdivision_depth=0,max_certificate_nodes=0)
    def check(name,ok):
        counts[name]=counts.get(name,0)+1
        if not ok:raise AssertionError(name)
    def equal_poly(saved,actual,label):
        check(label, saved is None if actual is None else list(map(Q,saved))==actual)
    def equal_record(saved,actual):
        check('world_count',len(saved['worlds'])==len(actual['worlds']))
        for x,y in zip(saved['worlds'],actual['worlds']):
            check('onset_identity',x['onset']==y['onset'])
            check('world_fields',set(x)==set(y))
            for k in FIELDS:equal_poly(x[k],y[k],'world_polynomial')
        check('summary_fields',set(saved['summary'])==set(actual['summary']))
        for k,v in actual['summary'].items():equal_poly(saved['summary'][k],v,'summary_polynomial')

    freeze,manifest,graphs,result=[load(a/n) for n in ('FREEZE.json','MANIFEST.json','GRAPHS.json','RESULTS.json')]
    check('complete',manifest['status']=='COMPLETE')
    for p,h in manifest['outputs'].items():check('output_hash',sha(a/p)==h)
    for p,h in freeze['inputs'].items():check('input_hash',sha(p)==h)
    for p,h in freeze['snapshots'].items():check('snapshot_hash',sha(a/'inputs'/p)==h)
    paths=list(freeze['inputs'])
    joint_path=next(Path(p) for p in paths if 'fep-noise-uncertainty-v1/' in p and p.endswith('/RESULTS.json'))
    mismatch_path=next(Path(p) for p in paths if 'fep-noise-mismatch-v1/' in p and p.endswith('/RESULTS.json'))
    joint,mismatch=load(joint_path),load(mismatch_path)
    old_graphs=load(mismatch_path.parent/'GRAPHS.json')
    for path in (joint_path,mismatch_path):
        m,r=load(path.parent/'MANIFEST.json'),load(path.parent/'READBACK.json')
        check('inherited_verified',r['passed'] and r['manifest_sha256']==sha(path.parent/'MANIFEST.json'))
        check('inherited_result_hash',m['outputs']['RESULTS.json']==sha(path))
        if path==mismatch_path:check('inherited_graph_hash',m['outputs']['GRAPHS.json']==sha(path.parent/'GRAPHS.json'))
    T,rho,K=10,Q(1,2),Q(19568652557,204800000000)
    domain=[Q(1,25),Q(3,50)]
    check('scope',graphs['T']==result['T']==T and Q(graphs['rho'])==Q(result['rho'])==rho
          and Q(graphs['budget'])==Q(result['budget'])==K
          and list(map(Q,graphs['domain']))==list(map(Q,result['domain']))==domain)
    expected_graphs,expected_mixtures={},{}
    for c in joint['problems']['retained']['solution']['components']:
        name='joint_'+c['policy']
        expected_graphs[name]=dict(graph=joint['problems']['retained']['policies'][c['policy']]['graph'],
                                  belief='joint_noise',source=c['policy'])
    expected_mixtures['joint_mixture']=[dict(policy='joint_'+c['policy'],weight=c['weight'])
                                      for c in joint['problems']['retained']['solution']['components']]
    for c in joint['controls']['fixed_pool']['components']:
        name='fixed_'+c['policy']
        expected_graphs[name]=dict(graph=old_graphs['policies'][c['policy']]['graph'],belief='nominal_5_percent',source=c['policy'])
    expected_mixtures['fixed_pool']=[dict(policy='fixed_'+c['policy'],weight=c['weight'])
                                   for c in joint['controls']['fixed_pool']['components']]
    expected_graphs['hybrid']=dict(graph=old_graphs['policies']['hybrid']['graph'],belief='nominal_5_percent',source='hybrid')
    check('frozen_graph_identity',graphs['graphs']==expected_graphs)
    check('frozen_mixture_identity',graphs['mixtures']==expected_mixtures)

    def replay(graph,T,tau):
        histogram=[[0]*6 for _ in range(T+1)]
        for bits in itertools.product((0,1),repeat=T):
            k=sum(bits);i=0;errors=buys=post_errors=post_buys=0;first=None
            for t,flip in enumerate(bits,1):
                node=graph[i];check('path_time',node['t']==t)
                post=tau is not None and t>=tau
                d=int(post)^flip
                buy=node['action']=='B'
                error=0 if buy else int(d==1) if node['action']=='F' else int(d==0)
                errors+=error;buys+=buy
                if post:
                    post_errors+=error;post_buys+=buy
                    if buy and first is None:first=t
                i=node['children'][str(d) if buy else 'N']
            check('path_terminal',i is None)
            delay=0 if tau is None else T-tau+1 if first is None else first-tau
            for j,v in enumerate((errors,buys,post_errors,post_buys,delay,int(first is None))):histogram[k][j]+=v
            totals['noise_paths']+=1
        polys=[]
        # Each bit string with k flips has probability x^k (1-x)^(T-k).
        # Expanding that expression uses counts, independently of graph recursion.
        for metric in range(6):
            polys.append(clean([sum(histogram[k][metric]*(-1)**(j-k)*math.comb(T-k,j-k)
                                    for k in range(j+1)) for j in range(T+1)]))
        er,bu,pe,pb,de,mi=polys
        cost,post=plus(er,times(bu,Q(1,10))),plus(pe,times(pb,Q(1,10)))
        totals['worlds']+=1
        return dict(onset=tau,cost=cost,errors=er,purchases=bu,post_cost=post,post_errors=pe,
                    post_purchases=pb,delay=de,missing=mi,recovery=None if tau is None else times(post,Q(1,T-tau+1)))

    def summarize(worlds,T,rho):
        stable=times(worlds[0]['cost'],Q(1,T));b=times(stable,1-rho);r=[Q(0)]
        for w in worlds[1:]:
            b=plus(b,times(w['cost'],rho/(T*T)))
            r=plus(r,times(w['recovery'],Q(1,T)))
        return dict(stable=stable,B=b,R=r,J=plus(b,r))

    def rebuild(graph,T,rho):
        totals['graphs']+=1
        rows=[replay(graph,T,tau) for tau in [None,*range(1,T+1)]]
        return dict(worlds=rows,summary=summarize(rows,T,rho))

    def rebuild_mixture(policies,components):
        weights=[(v['policy'],Q(v['weight'])) for v in components]
        check('mixture_probabilities',sum(w for _,w in weights)==1 and all(w>=0 for _,w in weights))
        worlds=[]
        for i in range(T+1):
            row=dict(onset=None if i==0 else i)
            for field in FIELDS:
                if field=='recovery' and i==0:row[field]=None;continue
                p=[Q(0)]
                for name,w in weights:p=plus(p,times(policies[name]['worlds'][i][field],w))
                row[field]=p
            worlds.append(row)
        return dict(worlds=worlds,summary=summarize(worlds,T,rho))

    policies={}
    for name,g in graphs['graphs'].items():
        graph=g['graph'];reachable={0};totals['main_graph_nodes']+=len(graph)
        for i in sorted(range(len(graph)),key=lambda i:graph[i]['t']):
            node=graph[i]
            check('graph_reachable',i in reachable)
            allowed={'t','weights','action','children'}|({'clock'} if g['belief']=='nominal_5_percent' else set())
            check('action_interface',set(node)==allowed and node['action'] in ('F','R','B'))
            check('observation_mask',set(node['children'])==({'0','1'} if node['action']=='B' else {'N'}))
            check('belief_size',len(node['weights'])==(33 if g['belief']=='joint_noise' else 11))
            for child in node['children'].values():
                if node['t']==T:check('graph_terminal',child is None)
                else:
                    check('graph_edge_time',child is not None and graph[child]['t']==node['t']+1)
                    reachable.add(child)
        policies[name]=rebuild(graph,T,rho)
    for name,cs in graphs['mixtures'].items():
        check('saved_mixture_identity',result['policies'][name]['components']==cs)
        policies[name]=rebuild_mixture(policies,cs)
    always=[dict(t=t,action='B',children={str(d):t if t<T else None for d in (0,1)}) for t in range(1,T+1)]
    policies['always']=rebuild(always,T,rho)
    check('policy_roster',set(policies)==set(result['policies']))
    for name,p in policies.items():equal_record(result['policies'][name],p)
    for key in ('stable','B','R'):check('analytic_always',policies['always']['summary'][key]==[Q(1,10)])

    for name,p in policies.items():
        if name=='always':continue
        for e,rate in enumerate(('0.04','0.05','0.06')):
            if name=='joint_mixture':expected=joint['problems']['retained']['solution']['worlds'][e*11:(e+1)*11]
            elif name=='fixed_pool':expected=joint['controls']['fixed_pool']['worlds'][e*11:(e+1)*11]
            elif name.startswith('joint_'):
                expected=joint['problems']['retained']['policies'][graphs['graphs'][name]['source']]['worlds'][e*11:(e+1)*11]
            else:expected=mismatch['conditions'][rate]['policies'][graphs['graphs'][name]['source']]['worlds']
            for actual,old in zip(p['worlds'],expected):
                check('reference_onset',actual['onset']==old['onset'])
                for key in FIELDS:check('nominal_reproduction',old[key] is None if actual[key] is None else at(actual[key],Q(rate))==Q(old[key]))

    def verify_certificate(p,c):
        totals['certificates']+=1
        lo,hi=map(Q,c['domain']);check('certificate_domain',lo<hi)
        check('certificate_limits',1<=c['nodes']<=c['max_nodes']<=4095 and 0<=c['max_depth']<=16)
        totals['max_certificate_nodes']=max(totals['max_certificate_nodes'],c['nodes'])
        if c['verdict']=='FAIL':
            x,y=Q(c['witness']['x']),Q(c['witness']['value'])
            check('exact_counterexample',lo<=x<=hi and at(p,x)==y and (y<0 or (c['strict'] and y==0)))
            check('failure_has_no_global_bounds',not c['leaves'] and c['lower_bound'] is None and c['upper_bound'] is None)
            return
        check('nonfailure_verdict',c['verdict'] in ('PASS','INCONCLUSIVE') and c['witness'] is None)
        leaves=sorted(c['leaves'],key=lambda v:Q(v['lo']))
        check('complete_binary_tree',c['nodes']==2*len(leaves)-1)
        previous=lo;all_coeff=[];unresolved=0
        for leaf in leaves:
            left,right,depth=Q(leaf['lo']),Q(leaf['hi']),leaf['depth']
            coeff=list(map(Q,leaf['coefficients']));degree=len(p)-1
            check('leaf_partition',left==previous and left<right<=hi)
            check('dyadic_leaf',0<=depth<=c['max_depth'] and right-left==(hi-lo)/2**depth
                  and ((left-lo)/(hi-lo)*2**depth).denominator==1)
            check('bernstein_degree',len(coeff)==len(p))
            for j in range(degree+1):
                u=Q(j,degree) if degree else Q(0)
                represented=sum(coeff[i]*math.comb(degree,i)*u**i*(1-u)**(degree-i) for i in range(degree+1))
                check('bernstein_polynomial_identity',at(p,left+(right-left)*u)==represented)
                totals['identity_points']+=1
            meets=min(coeff)>0 if c['strict'] else min(coeff)>=0
            check('leaf_status',leaf['kind']==('proved' if meets else 'unresolved'))
            unresolved+=not meets
            totals['leaves']+=1;totals['max_subdivision_depth']=max(totals['max_subdivision_depth'],depth)
            all_coeff.extend(coeff);previous=right
        check('closed_interval_covered',previous==hi and bool(leaves))
        check('convex_hull_bounds',Q(c['lower_bound'])==min(all_coeff) and Q(c['upper_bound'])==max(all_coeff))
        check('certificate_verdict',c['verdict']==('INCONCLUSIVE' if unresolved else 'PASS'))

    def verify_sign(p,s):
        for key,poly in [('nonnegative',p),('nonpositive',times(p,-1))]:
            check('sign_scope',not s[key]['strict'] and list(map(Q,s[key]['domain']))==domain)
            verify_certificate(poly,s[key])
        a,b=s['nonnegative']['verdict'],s['nonpositive']['verdict']
        expected='zero' if a==b=='PASS' else 'nonnegative' if a=='PASS' else 'nonpositive' if b=='PASS' else 'mixed' if a==b=='FAIL' else 'unresolved'
        check('two_sided_sign',s['sign']==expected)

    def verify_check(saved,p,strict):
        equal_poly(saved['polynomial'],p,'criterion_polynomial')
        c=saved['certificate']
        check('criterion_scope',c['strict']==strict and list(map(Q,c['domain']))==domain and c['max_depth']==16 and c['max_nodes']==4095)
        verify_certificate(p,c)

    h=policies['hybrid']['summary'];expected_keys=[]
    for name in graphs['mixtures']:
        s=policies[name]['summary']
        definitions=[('stable',minus([K],s['stable']),False),('always_recovery',minus([Q(1,10)],s['R']),True),
                     ('hybrid_recovery',minus(h['R'],s['R']),True)]
        keys=[]
        for key,p,strict in definitions:
            full=name+':'+key;keys.append(full);saved=result['checks'][full]
            verify_check(saved,p,strict);verify_sign(diff(p),saved['derivative'])
        expected_keys+=keys;check('primary_roster',result['primary'][name]==keys)
        statuses=[result['checks'][key]['certificate']['verdict'] for key in keys]
        verdict='PASS' if all(s=='PASS' for s in statuses) else 'FAIL' if 'FAIL' in statuses else 'INCONCLUSIVE'
        check('primary_verdict',result['verdicts'][name]==verdict)
        for key,p,strict in [('matched_stable',minus(h['stable'],s['stable']),False),
                             ('hybrid_full',minus(h['B'],s['B']),True),('always_full',minus([Q(1,10)],s['B']),True)]:
            verify_check(result['secondary'][name][key],p,strict)
        for saved,u,v in zip(result['onsets'][name],policies[name]['worlds'],policies['hybrid']['worlds']):
            check('onset_diagnostic_identity',saved['onset']==u['onset']==v['onset'])
            full=times(minus(v['cost'],u['cost']),Q(1,T));equal_poly(saved['full'],full,'onset_full_difference')
            verify_sign(full,saved['full_sign'])
            if u['recovery'] is None:check('no_stable_recovery',saved['recovery'] is None and saved['recovery_sign'] is None)
            else:
                recovery=minus(v['recovery'],u['recovery']);equal_poly(saved['recovery'],recovery,'onset_recovery_difference')
                verify_sign(recovery,saved['recovery_sign'])
    check('all_primary_keys',set(result['checks'])==set(expected_keys) and set(result['primary'])==set(graphs['mixtures']))
    comparison=minus(policies['fixed_pool']['summary']['J'],policies['joint_mixture']['summary']['J'])
    verify_check(result['secondary']['joint_J_vs_pool'],comparison,True)
    verify_sign(comparison,result['secondary']['joint_J_vs_pool']['sign'])
    for name in [*graphs['mixtures'],'hybrid']:
        for field in ('stable','B','R'):verify_sign(diff(policies[name]['summary'][field]),result['trends'][name][field])

    # The predecessor's three-point objective and lower bound are unchanged.
    old=joint['problems']['retained'];cert=old['certificate'];mu=Q(cert['mu'])
    C=sum(at(policies['joint_mixture']['summary']['J'],x) for x in (Q(1,25),Q(1,20),Q(3,50)))/3
    bound=Q(old['policies'][cert['oracle']]['root'])-mu*K
    check('inherited_objective_bound',C==Q(old['solution']['summary']['C'])==bound==Q(cert['lower_bound'])
          and Q(cert['duality_gap'])==0 and mu>=0)

    fixtures=load(a/'SHORT_FIXTURES.json')
    for fixture in fixtures['graphs']:
        actual=rebuild(fixture['graph'],fixture['T'],Q(fixture['rho']))
        equal_record(fixture['record'],actual)
    for fixture in fixtures['certificates']:
        p=clean(fixture['polynomial']);c=fixture['certificate']
        verify_certificate(p,c);check('certificate_fixture_verdict',c['verdict']==fixture['expected'])
    qual,bench,resources=[load(a/n) for n in ('QUALIFICATION.json','BENCHMARK.json','STARTED.json')]
    check('qualification_scope',qual['passed'] and qual['cases']==273 and qual['tree_counts']=={'1':3,'2':15,'3':255})
    check('resource_limits',len(resources['affinity'])==1 and resources['nice']>=10 and all(v=='1' for v in resources['threads'].values()))
    check('benchmark_scope',bench['T']==7 and Q(bench['rho'])==Q(1,3) and bench['timing_only'] and bench['graphs']==5)
    check('execution_rules',bench['forecast_seconds']<=7200 and (bench['forecast_seconds']<=600 or resources['detached']))
    answer=dict(passed=True,completed=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start,
                checks=counts,total_checks=sum(counts.values()),totals=totals,manifest_sha256=sha(a/'MANIFEST.json'),
                source_sha256=sha(__file__),method='Complete-noise integer histograms reconstruct every cost polynomial; exact degree+1 evaluations verify Bernstein identities and interval coverage.')
    with (a/'READBACK.json').open('x') as out:
        json.dump(answer,out,indent=2,sort_keys=True);out.write('\n')
    print(json.dumps(dict(passed=True,checks=answer['total_checks'],seconds=answer['seconds'],totals=totals)),flush=True)


if __name__=='__main__':main()
