"""Scalar raw-window scoring and independent whole-block endpoint analysis."""
import math
import numpy as np
import support as s

METRICS=('uninterrupted','terminal','ever_recovered','terminal_after_failure',
         'mean_cycle_success','initial_success_run','ever_opposite','terminal_opposite')

def raw_scores(d):
    G,B,C=d['both_pass'].shape;s.require(G==18 and C==16 and B in (4,6),'Full source scoring panel')
    s.require(d['port_windows'].shape==(G,32,B,C,2,2),'All 32 observations')
    means=np.empty((G,B,C,2,2))
    for g,v,case,cue,port in np.ndindex(means.shape):
        means[g,v,case,cue,port]=math.fsum(map(float,d['port_windows'][g,:,v,case,cue,port]))/32
    error=s.close(means,d['mean_ports'],1e-12,'Independent scalar windows')
    margin=np.empty((G,B,C));opposite=np.empty_like(margin)
    for g,v,case in np.ndindex(margin.shape):
        rule=1 if (case//4)%2==0 else -1;p=means[g,v,case]
        values=[rule*p[0,0],-rule*p[0,1],-rule*p[1,0],rule*p[1,1]]
        margin[g,v,case]=min(values);opposite[g,v,case]=-max(values)
    for key,value in [('min_margin',margin),('opposite_margin',opposite)]:s.close(value,d[key],1e-12,'Scalar '+key)
    good=margin>.25;other=opposite>.25
    s.equal(good,d['both_pass'],'Every intended flag');s.equal(other,d['opposite_pass'],'Every opposite flag')
    s.require(not (good&other).any(),'Exclusive tasks')
    return good,other,dict(max_window_error=error,nearest_threshold=float(min(abs(margin-.25).min(),abs(opposite-.25).min())))

def endpoints(good,other):
    G,B,C=good.shape;result={k:np.zeros((B,C),float) for k in METRICS}
    for v,case in np.ndindex(B,C):
        flags=[bool(x) for x in good[:,v,case]];opposite=[bool(x) for x in other[:,v,case]]
        first=next((i for i,x in enumerate(flags) if not x),G)
        result['uninterrupted'][v,case]=all(flags);result['terminal'][v,case]=flags[-1]
        result['ever_recovered'][v,case]=any(flags[j] and any(not k for k in flags[:j]) for j in range(1,G))
        result['terminal_after_failure'][v,case]=flags[-1] and not all(flags[:-1])
        result['mean_cycle_success'][v,case]=sum(flags)/G;result['initial_success_run'][v,case]=first
        result['ever_opposite'][v,case]=any(opposite);result['terminal_opposite'][v,case]=opposite[-1]
    return result

class Summaries:
    def __init__(self,cfg):
        self.cfg=cfg;rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
        self.counts=np.zeros((20000,16),np.int64)
        for h in range(4):
            ids=[i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h]
            s.require(len(ids)==4,'Four independent blocks per history')
            draws=rng.integers(0,4,size=(20000,4))
            for j,i in enumerate(ids):self.counts[:,i]=(draws==j).sum(axis=1)
        s.require((self.counts.sum(axis=1)==16).all(),'Complete block resampling')
    def __call__(self,values):
        values=list(map(float,values));s.require(len(values)==16,'Sixteen block effects')
        samples=sorted(map(float,(self.counts@np.asarray(values))/16))
        def q(p):
            where=p*19999;low=math.floor(where);f=where-low
            return samples[low]*(1-f)+samples[low+1]*f
        return dict(mean=math.fsum(values)/16,by_block=dict(zip(map(str,self.cfg['blocks']),values)),
                    descriptive_stratified_block_bootstrap_95=[q(.025),q(.975)],
                    positive_blocks=sum(v>0 for v in values),tied_blocks=sum(v==0 for v in values),negative_blocks=sum(v<0 for v in values))

def same_tree(actual,expected,label,tol=1e-14):
    if isinstance(expected,dict):
        s.require(isinstance(actual,dict) and set(actual)==set(expected),'Summary schema '+label)
        for k,v in expected.items():same_tree(actual[k],v,label+'/'+k,tol)
    elif isinstance(expected,(list,tuple)):
        s.require(len(actual)==len(expected),'Summary length '+label)
        for i,v in enumerate(expected):same_tree(actual[i],v,label+'/'+str(i),tol)
    elif isinstance(expected,(str,bool)) or expected is None:s.require(actual==expected,'Summary value '+label)
    else:s.close(actual,expected,tol,'Summary numeric '+label)

def paired(x,y):
    x=np.asarray(x,bool);y=np.asarray(y,bool)
    return dict(repeated_only=int((x&~y).sum()),baseline_only=int((y&~x).sum()),
                both=int((x&y).sum()),neither=int((~(x|y)).sum()),lineages=256)

def classification(effect):
    if effect['mean']<=0:return 'DIRECTIONAL_FORECAST_FAILED'
    if effect['descriptive_stratified_block_bootstrap_95'][0]<=0:return 'POSITIVE_UNRESOLVED'
    return 'POSITIVE_DEVELOPMENT_EVIDENCE'

def table_check(path,rows,tol=1e-12):
    actual=s.table(path);s.require(len(actual)==len(rows),'Complete table rows '+str(path))
    for i,(a,b) in enumerate(zip(actual,rows)):
        s.require(set(a)==set(b),'Table columns')
        for k,v in b.items():
            if isinstance(v,str):s.require(a[k]==v,'Table label')
            else:s.close(float(a[k]),v,tol,'Table value '+str(i)+'/'+k)
    return len(rows)

def analyze(panel,cfg,label):
    s.require(set(panel)==set(cfg['blocks']),'All source blocks')
    ep={};errors=[];rows=[];resources_rows=[];block_rows=[]
    for b in cfg['blocks']:
        d=panel[b];good,opposite,check=raw_scores(d);errors.append(check);ep[b]=endpoints(good,opposite)
        for vi,name in enumerate(cfg['variants']):
            block_rows.append(dict(block=b,history=cfg['history_by_block'][str(b)],variant=name,
                                   **{k:math.fsum(ep[b][k][vi])/16 for k in METRICS}))
        for gi,g in enumerate(cfg['generations']):
            for vi,name in enumerate(cfg['variants']):
                for case in range(16):
                    ids=dict(block=b,generation=g,variant=name,case=case)
                    rows.append(dict(**ids,intended=int(good[gi,vi,case]),opposite=int(opposite[gi,vi,case]),
                        min_margin=float(d['min_margin'][gi,vi,case]),opposite_margin=float(d['opposite_margin'][gi,vi,case]),
                        uninterrupted_so_far=int(all(good[:gi+1,vi,case]))))
                    resources_rows.append(dict(**ids,repair_call=int(d['applied'][gi,vi,case]),missing_edges=int(d['missing_edges'][gi,vi,case]),
                        added_edges=int(d['added_edges'][gi,vi,case]),added_abs_weight=float(d['added_abs_weight'][gi,vi,case]),
                        imputed_magnitude=float(d['magnitude'][gi,vi,case]),repair_cpu_seconds=float(d['repair_cpu_seconds'][gi,vi,case]),
                        audit_cpu_seconds=float(d['audit_cpu_seconds'][gi,vi,case]),record_bytes=4096))
    summary=Summaries(cfg)
    rates={name:{k:summary([math.fsum(ep[b][k][vi])/16 for b in cfg['blocks']]) for k in METRICS}
           for vi,name in enumerate(cfg['variants'])}
    coefficients=cfg.get('contrasts',dict(repeated_minus_baseline=[-1,0,1,0],one_time_minus_baseline=[-1,1,0,0],
                                        repeated_minus_one_time=[0,-1,1,0],repeated_minus_shuffled=[0,0,1,-1]))
    contrasts={name:{k:summary([math.fsum(coef*math.fsum(ep[b][k][vi])/16 for vi,coef in enumerate(coefs))
                              for b in cfg['blocks']]) for k in ('uninterrupted','terminal')} for name,coefs in coefficients.items()}
    def pairs(left,right):
        return {k:paired([ep[b][k][left] for b in cfg['blocks']],[ep[b][k][right] for b in cfg['blocks']]) for k in ('uninterrupted','terminal')}
    pair_counts=pairs(2,0) if label=='serial' else {n:pairs(2*i+1,2*i) for i,n in enumerate(cfg['noise_regimes'])}
    curves={name:[dict(generation=g,success=sum(int(panel[b]['both_pass'][gi,vi].sum()) for b in cfg['blocks'])/256,
                       uninterrupted=sum(sum(all(panel[b]['both_pass'][:gi+1,vi,j]) for j in range(16)) for b in cfg['blocks'])/256,
                       opposite=sum(int(panel[b]['opposite_pass'][gi,vi].sum()) for b in cfg['blocks'])/256)
                  for gi,g in enumerate(cfg['generations'])] for vi,name in enumerate(cfg['variants'])}
    histories={name:{v:{k:math.fsum(math.fsum(ep[b][k][vi])/16 for b in cfg['blocks'] if cfg['history_by_block'][str(b)]==h)/4
                        for k in ('uninterrupted','terminal')} for vi,v in enumerate(cfg['variants'])} for h,name in enumerate(cfg['histories'])}
    resources={}
    for vi,name in enumerate(cfg['variants']):
        fields={k:float(sum(d[k][:,vi].sum() for d in panel.values())) for k in ('added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds')}
        resources[name]=dict(repair_calls=sum(int(d['applied'][:,vi].sum()) for d in panel.values()),**fields,
             added_edges_per_lineage=fields['added_edges']/256,record_bytes_per_boundary=4096,read_updates_per_lineage=18*2048,
             optimizer_starts_per_call=16,maximum_sweeps_per_call=64)
    primary_name=cfg.get('primary_contrast','repeated_minus_baseline')
    result=dict(blocks=16,records=256,read_contexts=len(rows),rates=rates,contrasts=contrasts,paired_counts=pair_counts,
                curves=curves,history_summaries=histories,resources=resources,renewal_cpu_seconds=float(sum(d['renewal_cpu_seconds'].sum() for d in panel.values())),
                primary_direction_observed=contrasts[primary_name]['uninterrupted']['mean']>0,fitted_parameters=0)
    if label=='noise':
        result['mechanism']={}
        for vi,name in enumerate(cfg['variants']):
            counts={k:sum(int(d[k][:,vi].sum()) for d in panel.values()) for k in ('available_edges','fallback_edges','returning_edges','returning_fallback_edges')}
            result['mechanism'][name]=dict(**counts,fallback_fraction=counts['fallback_edges']/counts['available_edges'] if counts['available_edges'] else None,
                returning_fallback_fraction=counts['returning_fallback_edges']/counts['returning_edges'] if counts['returning_edges'] else None)
        totals=np.array([[math.fsum(float(panel[b]['noise_moments'][g,i,j]) for b in cfg['blocks'] for g in range(18)) for j in range(6)] for i in range(3)])
        result['noise_diagnostics']={}
        for i,name in enumerate(cfg['noise_regimes']):
            p,m,pp,mm,pm,n=totals[i];mp=p/n;mn=m/n;vp=pp/n-mp*mp;vn=mm/n-mn*mn
            result['noise_diagnostics'][name]=dict(draws=int(n),mean_plus=mp,mean_minus=mn,variance_plus=vp,variance_minus=vn,
                correlation=(pm/n-mp*mn)/math.sqrt(vp*vn),target_correlation=cfg['correlations'][i])
    source=s.HERE/'source'/label/'run';published=s.read(source/'analysis.json')
    for key,value in result.items():same_tree(published[key],value,label+'/'+key,1e-12 if key=='noise_diagnostics' else 1e-14)
    tables=dict(reads=rows,resources=resources_rows,block_summaries=block_rows)
    counts={name:table_check(source/(name+'.csv'),r) for name,r in tables.items()}
    result.update(primary_name=primary_name,scientific_verdict=classification(contrasts[primary_name]['uninterrupted']),
                  source_agreement=True,new_scientific_cohort=False)
    receipt=dict(status='PASS',raw_endpoints=len(rows),dual_task_flags=2*len(rows),table_rows=counts,
                 scalar_window_max_error=max(x['max_window_error'] for x in errors),nearest_threshold=min(x['nearest_threshold'] for x in errors),
                 descriptive_whole_block_inference=True,independent_bootstrap_multiplicity_check=True)
    return result,receipt
