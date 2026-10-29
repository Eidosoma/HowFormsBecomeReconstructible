"""Exact three-decision Bellman and latent-path reference calculations.

Independent numerical routes, not an independently authored validation.
"""
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from itertools import product
from math import exp,log
import random
from time import perf_counter
import numpy as np
import qualify_fep_future_aware_checking as Q2

exact_action = Q2.exact_action


def before(weights,parameters,t,steps,boundaries,retain=True):
    if steps == 0:
        return F(0)
    p = [list(row) for row in parameters]
    if t in boundaries:
        p[boundaries.index(t)+1] = [F(1),F(2),F(1,2),F(1),F(1,2),F(1)]
    total = F(0)
    for y in range(4):
        z = (y >> 1) ^ (y & 1)
        masses = []
        for j in range(4):
            g = p[j][0]/p[j][1]
            masses.append(weights[j]*(g if z else 1-g)/2)
        py = sum(masses)
        if not py:
            continue
        updated = [list(row) for row in p]
        for row in updated:
            row[0] += z
            row[1] += 1
        qr,qq,_,_ = direct_scores([m/py for m in masses],updated,y,t,boundaries,steps=steps,retain=retain)
        total += py*min(qr,qq)
    return total


def direct_scores(weights,parameters,y,t,boundaries=(26,51,76),horizon=100,retain=True,steps=3):
    remaining = min(steps,horizon-t+1)
    if remaining <= 2:
        return Q2.direct_scores(weights,parameters,y,t,boundaries,t+remaining-1,retain)
    assert remaining == 3
    z = (y >> 1) ^ (y & 1)
    u = sum(weights[j]*parameters[j][2+2*z]/parameters[j][3+2*z] for j in range(4))
    v0 = before(weights,parameters,t+1,remaining-1,boundaries,retain)
    if not retain:
        return min(u,1-u)+v0,F(1,10)+v0,F(0),u
    v1 = F(0)
    for target in (0,1):
        x = (y >> 1) ^ target
        p = [list(row) for row in parameters]
        masses = []
        for j in range(4):
            uj = p[j][2+2*z]/p[j][3+2*z]
            masses.append(weights[j]*(uj if x else 1-uj))
            p[j][2+2*z] += x
            p[j][3+2*z] += 1
        probability = sum(masses)
        if probability:
            v1 += probability*before([v/probability for v in masses],p,t+1,remaining-1,boundaries,retain)
    return min(u,1-u)+v0,F(1,10)+v1,v0-v1,u


def latent_scores(initial,history,y,boundaries):
    """Bellman tree from complete latent error-path evidence, without betas."""
    import qualify_fep_changing_world as Q
    configurations = [()]+[(t,) for t in boundaries]
    prior = [F(1,2),F(1,6),F(1,6),F(1,6)]
    def evidence(hist):
        return sum(w*Q.evidence(tuple(initial),tuple(hist),configuration) for w,configuration in zip(prior,configurations))
    current = tuple(history)+((y,None),)
    den = evidence(current)
    def continuation(prefix,remaining):
        if remaining == 0:
            return F(0)
        return sum(min(observed(tuple(prefix)+((yy,None),),remaining)) for yy in range(4))
    def observed(prefix,remaining):
        yy = prefix[-1][0]
        labeled = [prefix[:-1]+((yy,w),) for w in (0,1)]
        mass = evidence(prefix)/den
        report = min(evidence(h)/den for h in labeled)+continuation(prefix,remaining-1)
        reference = mass/10+sum(continuation(h,remaining-1) for h in labeled)
        return report,reference
    return observed(current,3)


def compare_case(S,counts,history,y,boundaries):
    w,p,_,_ = S.M.rational_state(counts,history,'C',boundaries,current=y)
    t = len(history)+1
    qr,qq,delta,u = direct_scores(w,p,y,t,boundaries)
    wf = np.array([[float(x) for x in w]])
    pf = np.array([[[float(x) for x in row] for row in p]])
    original_w,original_p = wf.copy(),pf.copy()
    z = np.array([(y >> 1) ^ (y & 1)],dtype=bool)
    a,b,d = S.scores(wf,pf,z,t,boundaries)
    for name,actual,expected in zip(('report','reference','Delta'),(a[0],b[0],d[0]),(qr,qq,delta)):
        S.check('qualification','rational '+name,abs(actual-float(expected)) < 5e-14)
    S.check('qualification','nonnegative exact value',delta >= 0)
    pw1 = u if (y >> 1) == 0 else 1-u
    continuation = qr-min(u,1-u)
    alternatives = (pw1+continuation,1-pw1+continuation,qq)
    matched = 2 if alternatives[2] <= min(alternatives[:2]) else 0 if alternatives[0] < alternatives[1] else 1
    S.check('qualification','matched Bayesian action',matched == exact_action(qr,qq,u,y))
    if abs(a[0]-b[0]) > 1e-12:
        fast = 2 if b[0] <= a[0] else (y >> 1) ^ int(float(u) > .5)
        S.check('qualification','batched action',fast == matched)
    ar,br,dr = S.scores(wf,pf,z,t,boundaries,retain=False)
    er,eq,ed,eu = direct_scores(w,p,y,t,boundaries,retain=False)
    myopic = 2 if min(u,1-u) >= F(1,10) else (y >> 1) ^ int(u > F(1,2))
    S.check('qualification','retention lesion collapse',dr[0] == 0 and ed == 0 and exact_action(er,eq,eu,y) == myopic
            and abs(ar[0]-float(er)) < 5e-14 and abs(br[0]-float(eq)) < 5e-14)
    if t < 99:
        v = S.future_two(wf,pf,t+1,boundaries)
        scaled = S.future_two(wf*(3/7),pf,t+1,boundaries)
        exact = before(w,p,t+1,2,boundaries)
        S.check('qualification','unnormalized future homogeneity',abs(scaled[0]-v[0]*(3/7)) < 5e-14 and abs(v[0]-float(exact)) < 5e-14)
    S.check('qualification','no hypothetical-state mutation',np.array_equal(wf,original_w) and np.array_equal(pf,original_p))
    if t >= 99:
        er,eq,ed,eu = Q2.direct_scores(w,p,y,t,boundaries)
        S.check('qualification','C2 terminal reduction',qr == er and qq == eq and delta == ed and u == eu)
    return qr,qq


def old_projection(new):
    result = {k:new[k] for k in ('indices','calibration')}
    for k in ('wrong','references','window_wrong','window_references','post_wrong','post_references','first_post_reference'):
        result[k] = new[k][:,:,:6]
    for k in ('extra_references','delta_sum','selected_gain_sum'):
        result[k] = new['c2_'+k]
    result['planner_fallback'] = new['planner_fallbacks'][:1]
    result['control_fallback'] = new['control_fallback']
    result['candidate_inference_fallback'] = new['c2_inference_fallback']
    return result


def qualify(S,cpus):
    start = perf_counter()
    observations = list(product(range(4),(None,0,1)))
    histories = [()]+[(x,) for x in observations]+[(observations[i],observations[(5*i+3)%12]) for i in range(12)]
    counts_set = ((64,0,0,0),(16,16,16,16),(4,0,0,0))
    boundaries = (2,3,4)
    cases,latent = 0,0
    for counts in counts_set:
        for hist in histories:
            for y in range(4):
                qr,qq = compare_case(S,counts,list(hist),y,boundaries)
                if not hist or (hist in (((0,None),),((3,1),)) and y < 2):
                    lr,lq = latent_scores(counts,hist,y,boundaries)
                    S.check('qualification','independent latent-path Bellman recursion',qr == lr and qq == lq)
                    latent += 1
                cases += 1
    rng = random.Random(202609243)
    boundary_cases = 0
    for t in (24,25,26,49,50,51,74,75,76,98,99,100):
        history = [(rng.randrange(4),rng.choice((None,None,0,1))) for _ in range(t-1)]
        for y in range(4):
            compare_case(S,(16,16,16,16),history,y,S.M.BOUNDARIES)
            boundary_cases += 1
    # A known future reset can erase today's label before the first future
    # task, or leave one task to use it before the second future task resets.
    w = [F(0),F(1),F(0),F(0)]
    p = [[F(1),F(2),F(1),F(10),F(1),F(10)] for _ in range(4)]
    for y in range(4):
        qr,qq,d,u = direct_scores(w,p,y,25)
        S.check('qualification','exact tie across first future reset',qr == qq == F(3,10) and d == 0 and exact_action(qr,qq,u,y) == 2)
        r3,q3,_,_ = direct_scores(w,p,y,24)
        r2,q2,_,_ = Q2.direct_scores(w,p,y,24)
        S.check('qualification','second future reset contributes one reference',r3 == r2+F(1,10) and q3 == q2+F(1,10))
        rt,qt,dt,ut = direct_scores(w,p,y,100)
        S.check('qualification','final exact tie',rt == qt == F(1,10) and dt == 0 and exact_action(rt,qt,ut,y) == 2)
    learner = S.M.Filter(np.array([[4,0,0,0]]))
    learner.start(1)
    action,_,_,_ = learner.warning(np.array([0],dtype=np.int8))
    old_scores = S.scores
    def force_near(*args,**kwargs):
        a,b,d = old_scores(*args,**kwargs)
        return b.copy(),b,d
    snapshot = (learner.p.copy(),learner.logw.copy(),learner.labels.copy())
    try:
        S.scores = force_near
        selected,_,_,_,fallback,_,_ = S.choose_three(learner,np.array([0],dtype=np.int8),action[:,2])
    finally:
        S.scores = old_scores
    ew,ep,_,_ = S.M.rational_state([4,0,0,0],[],current=0)
    er,eq,_,eu = direct_scores(ew,ep,0,1)
    S.check('qualification','exact accessible-history fallback',fallback == 1 and selected[0] == exact_action(er,eq,eu,0))
    S.check('qualification','live inference unchanged by planning',all(np.array_equal(a,b) for a,b in zip(snapshot,(learner.p,learner.logw,learner.labels))))
    losses = np.array([0.,.1,1.])
    Z = 1+exp(-.1)+exp(-1)
    preferences = np.exp(-losses)/Z
    mass = np.array([.2,.3,.5])
    S.check('qualification','normalized preference',abs(preferences.sum()-1) < 1e-15)
    for slots in (1,2,3):
        S.check('qualification','preference score equivalence',abs(slots*np.dot(mass,-np.log(preferences))-(slots*np.dot(mass,losses)+slots*log(Z))) < 3e-15)
    # Assert exactly which labels the real evaluator delivers to each learner.
    old_filter,old_three,old_two = S.M.Filter,S.choose_three,S.B.choose_future
    instances,access = [],[0]
    class AccessFilter(old_filter):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.role = len(instances)
            instances.append(self)
        def warning(self,y):
            result = super().warning(y)
            self.last_myopic = result[0].copy()
            return result
        def retain(self,labels):
            permitted = self.last_myopic == 2 if self.role == 0 else np.zeros_like(labels,dtype=bool)
            if self.role:
                permitted[:,2] = self.live_action == 2
            S.check('qualification','paid-only live labels',np.array_equal(labels >= 0,permitted))
            access[0] += 1
            return super().retain(labels)
    def observed_two(f,*args):
        result = old_two(f,*args)
        f.live_action = result[0].copy()
        return result
    def observed_three(f,*args):
        result = old_three(f,*args)
        f.live_action = result[0].copy()
        return result
    try:
        S.M.Filter,S.choose_three,S.B.choose_future = AccessFilter,observed_three,observed_two
        new,_ = S.run_batch(S.A.synthetic(),list(range(4)),'qualification-'+S.PREFIX)
    finally:
        S.M.Filter,S.choose_three,S.B.choose_future = old_filter,old_three,old_two
    original,_ = S.B.run_batch(S.A.synthetic(),list(range(4)),'qualification-'+S.PREFIX)
    projection = old_projection(new)
    S.check('qualification','six controls and all diagnostics unchanged',set(original) == set(projection) and S.M.fingerprint(original) == S.M.fingerprint(projection))
    meta = S.M.population()[0]
    historical,_ = S.run_batch(meta,list(range(128)),S.B.PREFIX)
    path = S.PREVIOUS/'blocks'/f'{meta["label"]}_0000_0127.npz'
    with np.load(path,allow_pickle=False) as data:
        saved = {k:data[k] for k in data.files}
    projection = old_projection(historical)
    for name in saved:
        S.check('qualification','saved C2-study control '+name,np.array_equal(saved[name],projection[name]))
    S.check('qualification','whole historical control fingerprint',S.M.fingerprint(saved) == S.M.fingerprint(projection))
    x = np.arange(1024,dtype=np.int64)[None,:]+np.arange(27,dtype=np.int64)[:,None]
    S.check('qualification','paired stratified uncertainty',S.stats_int((x+2)-x,1)['mc_se'] == 0
            and abs(S.stats_int(x,1)['mc_se']-np.sqrt(np.var(np.arange(1024),ddof=1)/(27*1024))) < 1e-14)
    zero = np.array([1,-1]*512,dtype=np.int64)
    S.check('qualification','integer mean preserves true point ties',S.stats_int(zero,750)['mean'] == 0)
    jobs = [(S.A.synthetic(),list(range(i*2,i*2+2)),'qualification-parallel-'+S.PREFIX,None) for i in range(4)]
    one = [S.worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=4,initializer=S.M.pin_cpus,initargs=(cpus,)) as pool:
        four = list(pool.map(S.worker,jobs))
    for a,b in zip(one,four):
        S.check('qualification','one/four-worker equality',a['fingerprint'] == b['fingerprint'])
    return dict(status='PASS',assertions=sum(S.CHECKS.values()),checks=dict(S.CHECKS),wall_seconds=perf_counter()-start,
        rational_short_history_cases=cases,actual_boundary_terminal_cases=boundary_cases,latent_path_cases=latent,
        paid_label_access_calls=access[0],one_four_worker_chunks=4,unchanged_control_arrays=len(saved),
        historical_control_bridge='first law, C2-study original blocks 0-127; no C3 outcome selection',
        new_main_outcomes_used=False,matched_Bayesian_calculation='exact Bellman recursion over complete warnings, labels and actions')
