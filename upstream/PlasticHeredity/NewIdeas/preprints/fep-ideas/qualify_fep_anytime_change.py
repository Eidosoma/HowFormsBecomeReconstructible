"""Scalar four-warning recursion and complete latent-path reference for anytime change."""
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from itertools import product
from math import log
import random
from time import perf_counter
import numpy as np


def kind_at(j,t,boundaries):
    return 0 if j == 0 or t < boundaries[(j-1)//3] else (j-1)%3


def initial(counts):
    c = list(map(int,counts))
    return [F(c[1]+c[2]+1), F(sum(c)+2), F(2*c[3]+1,2), F(c[0]+c[3]+1), F(2*c[2]+1,2), F(c[1]+c[2]+1)]


def reset_rows(counts,transfer,boundaries):
    c = list(map(int,counts))
    reset = []
    for j in range(1+3*len(boundaries)):
        row = [F(1),F(2),F(1,2),F(1),F(1,2),F(1)]
        kind = 0 if not j else (j-1)%3
        if kind:
            row[2] = F(1+((c[1]+c[3] if kind == 1 else c[2]+c[3]) if transfer else 0))
            row[3] = F(2+(sum(c) if transfer else 0))
        reset.append(row)
    return reset


def advance(p,reset,t,boundaries):
    out = [row[:] for row in p]
    if t in boundaries:
        for j in range(1+3*boundaries.index(t),4+3*boundaries.index(t)):
            out[j] = reset[j][:]
    return out


def law(row,kind):
    if kind:
        rate = row[2]/row[3]
        return ((1-rate)/2,rate/2,(1-rate)/2,rate/2) if kind == 1 else ((1-rate)/2,(1-rate)/2,rate/2,rate/2)
    g,u0,u1 = row[0]/row[1],row[2]/row[3],row[4]/row[5]
    return ((1-g)*(1-u0),g*(1-u1),g*u1,(1-g)*u0)


def warning(w,p,y,t,boundaries):
    mass, out = [], [row[:] for row in p]
    z = (y >> 1) ^ (y & 1)
    for j,row in enumerate(p):
        kind = kind_at(j,t,boundaries)
        q = law(row,kind)
        mass.append(w[j]*(q[y]+q[y ^ 3])/2)
        if kind == 0:
            out[j][0] += z
            out[j][1] += 1
    total = sum(mass)
    return [v/total for v in mass],out,total


def label(w,p,y,target,t,boundaries):
    mass,out = [],[row[:] for row in p]
    e = y ^ (3*target)
    for j,row in enumerate(p):
        kind = kind_at(j,t,boundaries)
        q = law(row,kind)
        mass.append(w[j]*q[e]/(q[y]+q[y ^ 3]))
        if kind == 0:
            z = (y >> 1) ^ (y & 1)
            out[j][2+2*z] += e >> 1
            out[j][3+2*z] += 1
        else:
            out[j][2] += (e & 1) if kind == 1 else (e >> 1)
            out[j][3] += 1
    total = sum(mass)
    return [v/total for v in mass],out,total


def rational_state(counts,history,current,boundaries=tuple(range(1,101))):
    w = [F(1,2)]+[F(1,6*len(boundaries))]*(3*len(boundaries))
    p = [initial(counts) for _ in w]
    reset = reset_rows(counts,False,boundaries)
    for t,(y,target) in enumerate(history,1):
        p = advance(p,reset,t,boundaries)
        w,p,_ = warning(w,p,y,t,boundaries)
        if target is not None:
            w,p,_ = label(w,p,y,target,t,boundaries)
    t = len(history)+1
    p = advance(p,reset,t,boundaries)
    w,p,_ = warning(w,p,current,t,boundaries)
    return w,p,reset


def before(w,p,reset,t,steps,boundaries,retain):
    if not steps:
        return F(0)
    p = advance(p,reset,t,boundaries)
    total = F(0)
    for y in range(4):
        ww,pp,probability = warning(w,p,y,t,boundaries)
        r,q,_,_ = direct_scores(ww,pp,reset,y,t,steps,boundaries,retain)
        total += probability*min(r,q)
    return total


def direct_scores(w,p,reset,y,t,steps=3,boundaries=(26,51,76),retain=True):
    steps = min(steps,101-t)
    labeled = [label(w,p,y,target,t,boundaries) for target in (0,1)]
    pw1 = labeled[1][2]
    v0 = before(w,p,reset,t+1,steps-1,boundaries,retain)
    v1 = sum(probability*before(ww,pp,reset,t+1,steps-1,boundaries,retain) for ww,pp,probability in labeled) if retain else v0
    u = 1-pw1 if y >> 1 else pw1
    return min(pw1,1-pw1)+v0,F(1,10)+v1,v0-v1,u


def exact_action(r,q,u,y):
    return 2 if q <= r else (y >> 1) ^ int(u > F(1,2))


def moment(alpha,counts):
    result = F(1)
    for a,n in zip(alpha,counts):
        for i in range(n):
            result *= a+i
    for i in range(sum(counts)):
        result /= sum(alpha)+i
    return result


def latent_evidence(counts,history,boundaries):
    transfer = False
    """Integrate complete error paths with Dirichlet/Beta moments, no filter."""
    c = list(map(int,counts))
    evidence = [F(0) for _ in range(1+3*len(boundaries))]
    unknown = [i for i,(_,target) in enumerate(history) if target is None]
    for values in product((0,1),repeat=len(unknown)):
        targets = [target for _,target in history]
        for i,value in zip(unknown,values):
            targets[i] = value
        errors = [y ^ (3*target) for (y,_),target in zip(history,targets)]
        for j in range(1+3*len(boundaries)):
            tau = 101 if j == 0 else boundaries[(j-1)//3]
            kind = 0 if j == 0 else (j-1)%3
            old = [sum(e == k and t < tau for t,e in enumerate(errors,1)) for k in range(4)]
            new = [sum(e == k and t >= tau for t,e in enumerate(errors,1)) for k in range(4)]
            prob = moment([F(2*x+1,2) for x in c],old)
            if kind == 0:
                prob *= moment([F(1,2)]*4,new)
            else:
                ones = new[1]+new[3] if kind == 1 else new[2]+new[3]
                cal_ones = c[1]+c[3] if kind == 1 else c[2]+c[3]
                alpha = [F(1+(sum(c)-cal_ones if transfer else 0)),F(1+(cal_ones if transfer else 0))]
                prob *= moment(alpha,[sum(new)-ones,ones])/2**sum(new)
            evidence[j] += prob/2**len(history)
    return [v*(F(1,2) if j == 0 else F(1,6*len(boundaries))) for j,v in enumerate(evidence)]


def compare(X, counts, hist, y, boundaries, steps=3, paths=False):
    f = X.Filter(np.array([counts]), boundaries)
    for t, (yy, target) in enumerate(hist, 1):
        f.start(t); f.warning(np.array([yy], dtype=np.int8))
        f.retain(np.array([-1 if target is None else target]))
    f.start(len(hist)+1); f.warning(np.array([y], dtype=np.int8))
    w, p, reset = rational_state(counts, hist, y, boundaries)
    X.check('rational', 'mixture posterior', np.allclose(f.w[0], np.array(w,dtype=float), atol=4e-14, rtol=0))
    X.check('rational', 'conjugate states', np.array_equal(f.p[0], np.array(p,dtype=float)))
    er, eq, ed, eu = direct_scores(w, p, reset, y, f.t, steps, boundaries)
    oldw, oldp = f.w.copy(), f.p.copy()
    actual = f.scores(f.w, f.p, f.z, f.t, steps)
    for a, e in zip(actual, (er, eq, ed)):
        X.check('rational', 'direct contingent score', abs(a[0]-float(e)) < 8e-14)
    action, _, _, _ = f.choose(steps)
    X.check('rational', 'exact action', action[0] == exact_action(er, eq, eu, y))
    X.check('rational', 'nonnegative information value', ed >= 0)
    X.check('rational', 'planner leaves belief unchanged', np.array_equal(f.w,oldw) and np.array_equal(f.p,oldp))
    rr, rq, rd, _ = direct_scores(w,p,reset,y,f.t,steps,boundaries,False)
    ar, aq, ad = f.scores(f.w,f.p,f.z,f.t,steps,False)
    X.check('rational', 'no-retention lesion', rd == 0 and ad[0] == 0 and abs(ar[0]-float(rr)) < 8e-14 and abs(aq[0]-float(rq)) < 8e-14)
    if paths:
        ev = latent_evidence(counts, list(hist)+[(y,None)], boundaries)
        X.check('latent', 'integrated complete error paths', w == [e/sum(ev) for e in ev])
        wf, mass = np.array(w,dtype=float), np.array(ev,dtype=float)
        optimum = -log(float(sum(ev)))
        free = float(np.sum(wf*(np.log(wf)-np.log(mass))))
        perturb = .9*wf+.1/len(wf)
        excess = float(np.sum(perturb*(np.log(perturb)-np.log(mass))))-optimum
        kl = float(np.sum(perturb*(np.log(perturb)-np.log(wf))))
        X.check('latent', 'collapsed conditional VFE identity', abs(free-optimum)<8e-14 and abs(excess-kl)<8e-14 and excess>=-8e-14)


def old_projection(X, arrays):
    dimensions = dict(wrong=9,references=9,post_wrong=9,post_references=9,
        window_wrong=9,window_references=9,first_post_reference=9,
        candidate_extra_references=2,candidate_values=2,diagnosis=2,phase_counts=3,phase_sums=3)
    return {k:(v[:,:,:dimensions[k]] if k in dimensions else v) for k,v in arrays.items()
            if k not in ('anytime_alarm','anytime_episode_sums','anytime_fallback')}


def qualify(X, cpus):
    import statistics
    started = perf_counter()
    cases = 0
    # Interior resets and consecutive supported times; different paid histories.
    for boundaries in ((1,2,4), (2,3,4), (26,51,76)):
        for counts in ((0,0,0,0), (20,4,8,32)):
            for hist in ((), ((0,None),), ((2,1),(3,None))):
                for y in (0,3):
                    compare(X,counts,hist,y,boundaries,paths=True)
                    cases += 1
    rng = random.Random(20261010)
    # Full 301-component model: pre-26 learning and terminal truncation.
    for t in (1,13,38,88,99,100):
        hist = [(rng.randrange(4),rng.choice((None,None,0,1))) for _ in range(t-1)]
        compare(X,(20,4,8,32),hist,t%4,X.BOUNDARIES,paths=t==1)
        cases += 1
    f = X.Filter(np.array([[20,4,8,32]]))
    X.check('prior','301 components and fixed masses', f.nh == 301 and f.priors[0] == F(1,2)
            and set(f.priors[1:]) == {F(1,600)})
    for t in range(1,101):
        past = sum(v for v,tau in zip(f.priors,f.times) if tau < t)
        onset = sum(v for v,tau in zip(f.priors,f.times) if tau == t)
        X.check('prior','declared conditional hazard', onset/(1-past) == F(1,201-t))
    X.check('prior','no-change mass at end without evidence', sum(v for v,tau in zip(f.priors,f.times) if tau > 100) == F(1,2))
    # Same support reproduces the sealed CT3-flat implementation.
    counts = np.array([[20,4,8,32],[64,0,0,0]])
    new, old = X.Filter(counts,X.M.BOUNDARIES), X.S.Filter(counts,False)
    for t in range(1,101):
        y = np.array([rng.randrange(4), rng.randrange(4)],dtype=np.int8)
        for learner in (new,old): learner.start(t); learner.warning(y)
        X.check('bridge','same-schedule mixture', np.array_equal(new.w,old.w) and np.array_equal(new.p,old.p))
        if t in (1,13,25,26,38,50,51,63,75,76,88,98,99,100):
            a,b = new.choose(), old.choose()
            for av,bv in zip(a,b): X.check('bridge','same-schedule action and values',np.array_equal(av,bv))
        labels = np.array([rng.choice((-1,-1,0,1)),rng.choice((-1,0,1))],dtype=np.int8)
        for learner in (new,old): learner.retain(labels)
    # Exact final cost threshold; both rational and vector scores purchase at equality.
    f = X.Filter(np.array([[9,0,0,1]]))
    f.w[:] = 0; f.w[:,0] = 1
    f.p[:,0] = [1,2,1,10,1,10]
    r,q,d = f.scores(f.w,f.p,np.array([False]),100)
    X.check('ties','final equality', abs(r[0]-.1)<1e-15 and q[0]==.1 and d[0]==0 and exact_action(F(1,10),F(1,10),F(1,10),0)==2)
    meta = X.S.extend_meta(X.S.A.synthetic())
    prefix = 'qualification-'+X.PREFIX
    arrays, _ = X.run_batch(meta,[0,1],prefix)
    old_arrays, _ = X.U.run_batch(meta,[0,1],prefix)
    projected = old_projection(X,arrays)
    X.check('bridge','all old fields', projected.keys() == old_arrays.keys())
    for k in old_arrays:
        X.check('bridge','old bytes '+k, projected[k].shape == old_arrays[k].shape and projected[k].dtype == old_arrays[k].dtype and projected[k].tobytes() == old_arrays[k].tobytes())
    X.check('bridge','old complete fingerprint',X.M.fingerprint(projected)==X.M.fingerprint(old_arrays))
    # Old schedule in new evaluator reproduces CT3-flat counts and diagnostics.
    limited = X.new_batch(meta,[0,1],prefix,X.M.BOUNDARIES)
    for k in X.U.FIELDS:
        if k in ('phase_counts','phase_sums'): idx=2
        elif k in ('candidate_extra_references','candidate_values','diagnosis'): idx=1
        else: idx=8
        a,b = limited[k][:,:,0],old_arrays[k][:,:,idx]
        if np.issubdtype(a.dtype,np.integer):
            X.check('bridge','limited evaluator integer '+k,np.array_equal(a,b))
        else:
            X.check('bridge','limited evaluator values '+k,np.allclose(a,b,atol=8e-13,rtol=0))
    rows = {k:arrays[k][None,...] for k in X.FIELDS}
    result = X.analyze(rows,[meta])
    def scalar_ci(saved,values):
        mean=statistics.mean(values); se=(statistics.variance(values)/len(values))**.5
        X.check('scalar','mean and paired uncertainty',max(abs(saved[k]-v) for k,v in zip(
            ('mean','mc_se','lower95','upper95'),(mean,se,mean-1.96*se,mean+1.96*se)))<4e-13)
    def compare_summary(saved,values):
        for ai,arm in enumerate(X.ARMS):
            scalar_ci(saved['arms'][arm],[v[ai] for v in values])
            if ai != 9:
                scalar_ci(saved['contrasts']['CT3-anytime_minus_'+arm],[v[9]-v[ai] for v in values])
        scalar_ci(saved['CT3_anytime_minus_always'],[v[9]-.1 for v in values])
    scalar_groups={}
    for group,co in X.coefficients().items():
        X.check('weights','normalized unchanged weights',int(co.sum())==144)
        for endpoint,wk,rk in (('episode','wrong','references'),('post_change','post_wrong','post_references')):
            if endpoint=='post_change' and (group=='stable' or group.endswith('_full')): continue
            values=[[(sum(int(co[j])*(int(arrays[wk][b,j,ai])+int(arrays[rk][b,j,ai])/10)/
                     (100 if endpoint=='episode' else 101-tau)/144 for j,(_,tau) in enumerate(X.CONDITIONS)
                     if co[j] and (endpoint=='episode' or tau<101))+(.00064 if endpoint=='episode' else 0))
                     for ai in range(10)] for b in range(2)]
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
                     for j in chosen)/len(chosen) for ai in range(10)] for b in range(2)]
            compare_summary(result['early_recovery'][str(tau)][panel],values)
    for j,(family,tau) in enumerate(X.CONDITIONS):
        saved=result['conditions'][f'{meta["label"]}__{family}_{tau}']
        for endpoint,wk,rk,den,offset in (('episode','wrong','references',100,.00064),('post_change','post_wrong','post_references',101-tau,0)):
            if not j and endpoint=='post_change':
                X.check('scalar','stable recovery absent',saved[endpoint] is None); continue
            compare_summary(saved[endpoint],[[(int(arrays[wk][b,j,ai])+int(arrays[rk][b,j,ai])/10)/den+offset for ai in range(10)] for b in range(2)])
    for panel,indices in X.panels().items():
        for endpoint,wk,rk in (('episode','wrong','references'),('post_change','post_wrong','post_references')):
            for ai,arm in enumerate(X.ARMS[:-1]):
                tally=dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
                for j in indices:
                    if not j and endpoint=='post_change': continue
                    diffs=[10*(int(arrays[wk][b,j,9])-int(arrays[wk][b,j,ai]))+int(arrays[rk][b,j,9])-int(arrays[rk][b,j,ai]) for b in range(2)]
                    den=1000 if endpoint=='episode' else 10*(101-X.CONDITIONS[j][1])
                    mean,se=statistics.mean(diffs)/den,(statistics.variance(diffs)/2)**.5/den
                    for k,yes in (('point_lower',sum(diffs)<0),('point_equal',sum(diffs)==0),('point_higher',sum(diffs)>0),('upper_below_zero',mean+1.96*se<0),('lower_above_zero',mean-1.96*se>0)): tally[k]+=int(yes)
                X.check('scalar','condition signs',tally==result['condition_counts'][panel][endpoint][arm])
    for bad in (None,0,1,2):
        for edge in (0.,.01):
            upper=[-.01]*3
            if bad is not None: upper[bad]=edge
            fixture=dict(post_change=dict(unexpected_core_changed=dict(CT3_anytime_minus_always=dict(upper95=upper[0]),
                contrasts={'CT3-anytime_minus_CT3-flat':dict(upper95=upper[1])})),
                episode=dict(unexpected_core_full=dict(contrasts={'CT3-anytime_minus_CT3-flat':dict(upper95=upper[2])})))
            X.check('criteria','strict zero and failure rules',list(X.verdicts(fixture).values())==[v<0 for v in upper])
    # Separate scalar replay of one complete learner trajectory validates new counters.
    cal,ys,truth,laws=X.U.physical_trace(meta,[0],prefix)
    for j in (0,19,27,30):
        f=X.Filter(cal)
        raw=[]; exposure=[]
        for t in range(1,101):
            y=int(ys[0,j,t-1]); target=int(truth[0,j,t-1])
            f.start(t); u=float(f.warning(np.array([y]))[0]); action=int(f.choose()[0][0])
            q=laws[j,t-1]; p1=q[y^3]/(q[y]+q[y^3]); best=min(p1,1-p1)
            risk=p1 if action==0 else 1-p1
            subjective_p1=1-u if y>>1 else u
            raw.append((.1 if action==2 else risk,min(best,.1),0 if action==2 else max(best-.1,0),
                0 if action==2 else risk-best,max(.1-best,0) if action==2 else 0,
                .1 if action==2 else subjective_p1 if action==0 else 1-subjective_p1))
            f.retain(np.array([target if action==2 else -1]))
            exposure.append(float(sum(f.w[0,k] for k,tau in enumerate(f.times) if tau<=t)))
        alarms=[t for t,mass in enumerate(exposure,1) if mass>.5]
        expected=[len(alarms),alarms[0] if alarms else 101,sum(exposure)]
        X.check('scalar','posterior false alarms',np.allclose(arrays['anytime_alarm'][0,j],expected,atol=1e-12,rtol=0))
        X.check('scalar','whole episode evaluator sums',np.allclose(arrays['anytime_episode_sums'][0,j],np.sum(raw,axis=0),atol=1e-12,rtol=0))
    for name,field,den in (('wrong_cost','wrong',100),('purchase_cost','references',1000)):
        for ai,arm in enumerate(X.ARMS):
            scalar_ci(result['stable_costs'][name]['arms'][arm],[int(arrays[field][b,0,ai])/den for b in range(2)])
            if ai!=9: scalar_ci(result['stable_costs'][name]['contrasts']['CT3-anytime_minus_'+arm],[(int(arrays[field][b,0,9])-int(arrays[field][b,0,ai]))/den for b in range(2)])
    fixture=np.array([[0.,2.,4.,6.],[7.,9.,11.,13.]])
    X.check('scalar','stratified SE',abs(X.ci(fixture)['mc_se']-(sum(statistics.variance(list(row)) for row in fixture)/16)**.5)<1e-15)
    X.check('arithmetic','int64 cohort bound',144*10*X.POST_SCALE*27648 < np.iinfo(np.int64).max)
    jobs=[(meta,[i],'parallel-'+X.PREFIX,None) for i in range(4)]
    serial=[X.worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=4,initializer=X.M.pin_cpus,initargs=(cpus,)) as pool:
        parallel=list(pool.map(X.worker,jobs))
    for a,b in zip(serial,parallel):
        X.check('parallel','one/four-worker fingerprint',a['fingerprint']==b['fingerprint'])
        X.check('parallel','CPU ceiling',b['cpus']==cpus)
    return dict(status='PASS',wall_seconds=perf_counter()-started,assertions=sum(X.CHECKS.values()),
        checks=dict(X.CHECKS),rational_cases=cases,old_arrays=len(old_arrays),same_support_bridge=True,
        fresh_one_four_worker_chunks=4,scalar_aggregation_blocks=2,new_policy_implementations=1,
        synthetic_only=True,inherited_qualification='unchanged imported code and preserved qualification; legacy arrays reexecuted',
        references='rational four-warning recursion, complete latent error paths, scalar saved accounting; same author')


