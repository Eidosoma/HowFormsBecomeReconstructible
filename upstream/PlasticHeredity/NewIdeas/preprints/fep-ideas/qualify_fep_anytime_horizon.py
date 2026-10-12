"""Independent scalar accounting and inherited rational recursion for fixed horizons."""
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
import random
import statistics
from time import perf_counter
import numpy as np
import qualify_fep_anytime_change as Q

def old_projection(arrays):
    sizes=dict(wrong=10,references=10,post_wrong=10,post_references=10,
        window_wrong=10,window_references=10,first_post_reference=10,
        candidate_extra_references=3,candidate_values=3,diagnosis=3,phase_counts=4,phase_sums=4)
    return {k:(v[:,:,:sizes[k]] if k in sizes else v) for k,v in arrays.items()
        if k not in ('horizon_alarm','horizon_episode_sums','horizon_fallback')}

def qualify(X,cpus,output=None):
    def log(message):
        if output is not None:X.M.logline(output,'QUALIFICATION: '+message)
    started=perf_counter(); cases=0
    rng=random.Random(20261011)
    log('rational small-support horizons one and four')
    for boundaries,history in [((1,2,4),()),((2,3,4),((2,1),(3,None))),
            ((26,51,76),((0,None),)),((1,3,4),((1,0),))]:
        for h in (1,4):
            Q.compare(X,(20,4,8,32),history,3,boundaries,steps=h,paths=True)
            cases+=1
    for t,h in ((1,4),(13,4),(38,1),(88,1),(98,4),(99,4),(100,4)):
        log(f'full 301-component rational reference at task {t}, horizon {h}')
        hist=[(rng.randrange(4),rng.choice((None,None,0,1))) for _ in range(t-1)]
        Q.compare(X,(20,4,8,32),hist,t%4,X.BOUNDARIES,steps=h,paths=t==1)
        cases+=1
    X.check('scope','same imported filter',X.Filter is X.A.Filter)
    f=X.Filter(np.array([[20,4,8,32]]))
    X.check('prior','unchanged 301 components',f.nh==301 and f.priors[0]==F(1,2) and set(f.priors[1:])=={F(1,600)})
    # Shared history, all depths: planning must leave exact conditional beliefs unchanged.
    for t in range(1,101):
        yy=np.array([rng.randrange(4)],dtype=np.int8)
        f.start(t); f.warning(yy)
        if t in (1,13,26,38,51,63,76,88,98,99,100):
            w,par=f.w.copy(),f.p.copy()
            for h in (1,3,4):
                actions,delta,gain,extra=f.choose(steps=h)
                X.check('filter','planning leaves belief unchanged',np.array_equal(w,f.w) and np.array_equal(par,f.p))
                if h==1:X.check('myopic','zero prospective information value',np.all(delta==0) and np.all(gain==0) and not extra.any())
                if t==100:X.check('terminal','one-step truncation',np.array_equal(actions,f.choose(steps=1)[0]) and np.all(delta==0))
        f.retain(np.array([rng.choice((-1,-1,0,1))],dtype=np.int8))
    f=X.Filter(np.array([[9,0,0,1]])); f.w[:]=0; f.w[:,0]=1
    f.p[:,0]=[1,2,1,10,1,10]
    for h in (1,3,4):
        a,b,d=f.scores(f.w,f.p,np.array([False]),100,h)
        X.check('ties','terminal equality buys',abs(a[0]-.1)<1e-15 and b[0]==.1 and d[0]==0 and Q.exact_action(F(1,10),F(1,10),F(1,10),0)==2)
    log('complete synthetic batches and byte-identical inherited-policy bridge')
    meta=X.S.extend_meta(X.S.A.synthetic()); prefix='qualification-'+X.PREFIX
    arrays,_=X.run_batch(meta,[0,1],prefix)
    old_arrays,_=X.A.run_batch(meta,[0,1],prefix)
    projected=old_projection(arrays)
    X.check('bridge','all old fields preserved',projected.keys()==old_arrays.keys())
    for k in old_arrays:
        X.check('bridge','old bytes '+k,projected[k].shape==old_arrays[k].shape and projected[k].dtype==old_arrays[k].dtype and projected[k].tobytes()==old_arrays[k].tobytes())
    X.check('bridge','complete old fingerprint',X.M.fingerprint(projected)==X.M.fingerprint(old_arrays))
    same=X.new_batch(meta,[0,1],prefix,3)
    inherited=X.A.new_batch(meta,[0,1],prefix)
    X.check('bridge','three-step evaluator fields',same.keys()==inherited.keys())
    for k in same:X.check('bridge','same evaluator bytes '+k,same[k].dtype==inherited[k].dtype and same[k].shape==inherited[k].shape and same[k].tobytes()==inherited[k].tobytes())
    X.check('myopic','all one-step episode information values zero',np.all(arrays['candidate_values'][:,:,3]==0) and np.all(arrays['candidate_extra_references'][:,:,3]==0))
    log('independent scalar aggregation, uncertainty and signs')
    rows = {k:arrays[k][None,...] for k in X.FIELDS}
    result = X.analyze(rows,[meta])
    def scalar_ci(saved,values):
        mean=statistics.mean(values); se=(statistics.variance(values)/len(values))**.5
        X.check('scalar','mean and paired uncertainty',max(abs(saved[k]-v) for k,v in zip(
            ('mean','mc_se','lower95','upper95'),(mean,se,mean-1.96*se,mean+1.96*se)))<4e-13)
    def compare_summary(saved,values):
        for ai,arm in enumerate(X.ARMS):scalar_ci(saved['arms'][arm],[v[ai] for v in values])
        for left,right in X.CONTRASTS:
            li,ri=X.ARMS.index(left),X.ARMS.index(right)
            scalar_ci(saved['contrasts'][left+'_minus_'+right],[v[li]-v[ri] for v in values])
        for arm in X.HORIZONS:scalar_ci(saved['against_always'][arm],[v[X.ARMS.index(arm)]-.1 for v in values])
    scalar_groups={}
    for group,co in X.coefficients().items():
        X.check('weights','normalized unchanged weights',int(co.sum())==144)
        for endpoint,wk,rk in (('episode','wrong','references'),('post_change','post_wrong','post_references')):
            if endpoint=='post_change' and (group=='stable' or group.endswith('_full')): continue
            values=[[(sum(int(co[j])*(int(arrays[wk][b,j,ai])+int(arrays[rk][b,j,ai])/10)/
                     (100 if endpoint=='episode' else 101-tau)/144 for j,(_,tau) in enumerate(X.CONDITIONS)
                     if co[j] and (endpoint=='episode' or tau<101))+(.00064 if endpoint=='episode' else 0))
                     for ai in range(len(X.ARMS))] for b in range(2)]
            scalar_groups[endpoint,group]=values
            compare_summary(result[endpoint][group],values)
    for panel in ('core','transfer'):
        for endpoint,ending in (('episode','_full'),('post_change','_changed')):
            a=scalar_groups[endpoint,'unexpected_'+panel+ending]; b=scalar_groups[endpoint,'supported_'+panel+ending]
            for ai,arm in enumerate(X.ARMS): scalar_ci(result['unexpected_minus_supported'][panel][endpoint][arm],[a[i][ai]-b[i][ai] for i in range(2)])
    for wi,tau in enumerate(X.WINDOWS):
        length=min(25,101-tau)
        for panel,families in (('stable',()),('core',X.FAMILIES[:3]),('transfer',X.FAMILIES[3:])):
            chosen=[0] if panel=='stable' else [j for j,(f,t) in enumerate(X.CONDITIONS) if f in families and t==tau]
            values=[[sum((int(arrays['window_wrong'][b,j,ai,wi])+int(arrays['window_references'][b,j,ai,wi])/10)/length
                     for j in chosen)/len(chosen) for ai in range(len(X.ARMS))] for b in range(2)]
            compare_summary(result['early_recovery'][str(tau)][panel],values)
    for j,(family,tau) in enumerate(X.CONDITIONS):
        saved=result['conditions'][f'{meta["label"]}__{family}_{tau}']
        for endpoint,wk,rk,den,offset in (('episode','wrong','references',100,.00064),('post_change','post_wrong','post_references',101-tau,0)):
            if not j and endpoint=='post_change':
                X.check('scalar','stable recovery absent',saved[endpoint] is None); continue
            compare_summary(saved[endpoint],[[(int(arrays[wk][b,j,ai])+int(arrays[rk][b,j,ai])/10)/den+offset for ai in range(len(X.ARMS))] for b in range(2)])
    for panel,indices in X.panels().items():
        for endpoint,wk,rk in (('episode','wrong','references'),('post_change','post_wrong','post_references')):
            for ai,arm in enumerate(X.ARMS[:-1]):
                tally=dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
                for j in indices:
                    if not j and endpoint=='post_change': continue
                    diffs=[10*(int(arrays[wk][b,j,X.PRIMARY_INDEX])-int(arrays[wk][b,j,ai]))+int(arrays[rk][b,j,X.PRIMARY_INDEX])-int(arrays[rk][b,j,ai]) for b in range(2)]
                    den=1000 if endpoint=='episode' else 10*(101-X.CONDITIONS[j][1])
                    mean,se=statistics.mean(diffs)/den,(statistics.variance(diffs)/2)**.5/den
                    for k,yes in (('point_lower',sum(diffs)<0),('point_equal',sum(diffs)==0),('point_higher',sum(diffs)>0),('upper_below_zero',mean+1.96*se<0),('lower_above_zero',mean-1.96*se>0)): tally[k]+=int(yes)
                X.check('scalar','condition signs',tally==result['condition_counts'][panel][endpoint][arm])
    for panel,indices in X.panels().items():
        for endpoint,wk,rk in [('episode','wrong','references'),('post_change','post_wrong','post_references')]:
            tally=dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
            for j in indices:
                if not j and endpoint=='post_change':continue
                diffs=[10*(int(arrays[wk][b,j,9])-int(arrays[wk][b,j,10]))+int(arrays[rk][b,j,9])-int(arrays[rk][b,j,10]) for b in range(2)]
                den=1000 if endpoint=='episode' else 10*(101-X.CONDITIONS[j][1])
                mean=statistics.mean(diffs)/den;se=(statistics.variance(diffs)/2)**.5/den
                for k,yes in [('point_lower',sum(diffs)<0),('point_equal',sum(diffs)==0),('point_higher',sum(diffs)>0),('upper_below_zero',mean+1.96*se<0),('lower_above_zero',mean-1.96*se>0)]:tally[k]+=int(yes)
            X.check('scalar','matched one/three signs',tally==result['matched_planning_condition_counts'][panel][endpoint])
    for bad in (None,0,1,2):
        for edge in (0.,.01):
            upper=[-.01]*3
            if bad is not None:upper[bad]=edge
            key=X.PRIMARY+'_minus_CT3-anytime'
            fixture=dict(post_change=dict(unexpected_core_changed=dict(against_always={X.PRIMARY:dict(upper95=upper[0])},contrasts={key:dict(upper95=upper[1])})),
                episode=dict(unexpected_core_full=dict(contrasts={key:dict(upper95=upper[2])})))
            X.check('criteria','strict zero and failure rules',list(X.verdicts(fixture).values())==[v<0 for v in upper])
    # Independent scalar exposure/cost aggregation catches the expanded arm offsets.
    for group,co in X.coefficients().items():
        if group=='stable' or group.endswith('_full'):continue
        for ai,arm in enumerate(X.ARMS[6:]):
            for pi,phase in enumerate(X.PHASES):
                for name,metric in [('exposure',0),('wrong_cost',1),('reference_cost',2)]:
                    values=[]
                    for block in range(2):
                        value=0.
                        for j,(_,tau) in enumerate(X.CONDITIONS):
                            if not co[j]:continue
                            c=arrays['phase_counts'][block,j,ai,:,metric]
                            v=int(c.sum()) if phase=='total' else int(c[pi])
                            value+=int(co[j])*v/(101-tau)/144/(10 if metric==2 else 1)
                        values.append(value)
                    scalar_ci(result['diagnostics'][group]['arms'][arm][phase][name],values)
    # Scalar task replay verifies new false-alarm and evaluator measurements.
    log('scalar trajectory and stable-counter replay')
    cal,ys,truth,laws=X.U.physical_trace(meta,[0],prefix)
    for hi,h in enumerate((1,4)):
        for j in (0,27):
            f=X.Filter(cal);raw=[];masses=[]
            for t in range(1,101):
                y=int(ys[0,j,t-1]);target=int(truth[0,j,t-1])
                f.start(t);u=float(f.warning(np.array([y]))[0]);action=int(f.choose(steps=h)[0][0])
                law=laws[j,t-1];p1=law[y^3]/(law[y]+law[y^3]);best=min(p1,1-p1)
                risk=p1 if action==0 else 1-p1;subjective_p1=1-u if y>>1 else u
                raw.append((.1 if action==2 else risk,min(best,.1),0 if action==2 else max(best-.1,0),
                    0 if action==2 else risk-best,max(.1-best,0) if action==2 else 0,
                    .1 if action==2 else subjective_p1 if action==0 else 1-subjective_p1))
                f.retain(np.array([target if action==2 else -1]))
                masses.append(float(sum(f.w[0,k] for k,tau in enumerate(f.times) if tau<=t)))
            crossings=[t for t,v in enumerate(masses,1) if v>.5]
            expected=[len(crossings),crossings[0] if crossings else 101,sum(masses)]
            X.check('scalar','new stable counters',np.allclose(arrays['horizon_alarm'][0,j,hi],expected,atol=1e-12,rtol=0))
            X.check('scalar','new evaluator sums',np.allclose(arrays['horizon_episode_sums'][0,j,hi],np.sum(raw,axis=0),atol=1e-12,rtol=0))
    for name,field,den in [('wrong_cost','wrong',100),('purchase_cost','references',1000)]:
        for ai,arm in enumerate(X.ARMS):scalar_ci(result['stable_costs'][name]['arms'][arm],[int(arrays[field][b,0,ai])/den for b in range(2)])
        for left,right in X.CONTRASTS:
            li,ri=X.ARMS.index(left),X.ARMS.index(right)
            scalar_ci(result['stable_costs'][name]['contrasts'][left+'_minus_'+right],[(int(arrays[field][b,0,li])-int(arrays[field][b,0,ri]))/den for b in range(2)])
    scalar_alarms={};scalar_evaluator={}
    for arm,hi in [('CT3-anytime',None),('CT1-anytime',0),('CT4-anytime',1)]:
        a=arrays['anytime_alarm'][:,0] if hi is None else arrays['horizon_alarm'][:,0,hi]
        s=(arrays['anytime_episode_sums'][:,0] if hi is None else arrays['horizon_episode_sums'][:,0,hi])/100
        scalar_alarms[arm]=dict(tasks_above_half=list(a[:,0]),probability_ever_above_half=list(map(float,a[:,0]>0)),
            first_crossing_censored_at_101=list(a[:,1]),mean_change_probability=list(a[:,2]/100))
        d={name:list(s[:,i]) for i,name in enumerate(X.SUMS)};ai=X.ARMS.index(arm)
        d.update(conditional_regret=list(s[:,2:5].sum(axis=1)),risk_underestimate=list(s[:,0]-s[:,5]),
            realization_residual=[(10*int(arrays['wrong'][b,0,ai])+int(arrays['references'][b,0,ai]))/1000-s[b,0] for b in range(2)])
        scalar_evaluator[arm]=d
    for name,values in [('posterior_false_alarms',scalar_alarms),('anytime_evaluator',scalar_evaluator)]:
        saved=result['stable_costs'][name]
        for arm,d in values.items():
            for k,v in d.items():scalar_ci(saved['arms'][arm][k],v)
        for left,right in X.CONTRASTS:
            if left not in values or right not in values:continue
            for k in values[left]:scalar_ci(saved['contrasts'][left+'_minus_'+right][k],[a-b for a,b in zip(values[left][k],values[right][k])])
    fixture=np.array([[0.,2.,4.,6.],[7.,9.,11.,13.]])
    X.check('scalar','stratified standard error',abs(X.ci(fixture)['mc_se']-(sum(statistics.variance(list(row)) for row in fixture)/16)**.5)<1e-15)
    X.check('arithmetic','int64 main bound',144*10*X.POST_SCALE*X.TOTAL_BLOCKS<np.iinfo(np.int64).max)
    log('serial/four-worker fingerprint comparison')
    jobs=[(meta,[i],'parallel-'+X.PREFIX,None) for i in range(4)]
    serial=[X.worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=4,initializer=X.M.pin_cpus,initargs=(cpus,)) as pool:
        parallel=list(pool.map(X.worker,jobs))
    for a,b in zip(serial,parallel):
        X.check('parallel','one/four worker identity',a['fingerprint']==b['fingerprint'])
        X.check('parallel','four CPU limit',b['cpus']==cpus)
    return dict(status='PASS',wall_seconds=perf_counter()-started,assertions=sum(X.CHECKS.values()),
        checks=dict(X.CHECKS),rational_cases=cases,old_arrays=len(old_arrays),same_three_evaluator_fields=len(same),
        inherited_filter=True,three_step_bridge=True,new_policy_implementations=2,horizons=X.HORIZONS,
        fresh_one_four_worker_chunks=4,scalar_aggregation_blocks=2,synthetic_only=True,
        reference='unchanged rational four-warning recursion, latent-path VFE check and independent scalar aggregation; same author')
