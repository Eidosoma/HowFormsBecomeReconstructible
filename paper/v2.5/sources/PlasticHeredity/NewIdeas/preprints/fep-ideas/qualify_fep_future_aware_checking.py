"""Independent rational enumeration for the two-decision task planner.

This is an independent calculation route, not an independently authored study.
No physical evaluation law or hidden event flag is accepted by the planner.
"""
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from itertools import product
from math import exp,log
import random
from time import perf_counter
import numpy as np


def terminal(weights,parameters,next_task,boundaries):
    p = [list(x) for x in parameters]
    if next_task in boundaries:
        p[boundaries.index(next_task)+1] = [F(1),F(2),F(1,2),F(1),F(1,2),F(1)]
    laws = []
    for v in p:
        g,u0,u1 = v[0]/v[1],v[2]/v[3],v[4]/v[5]
        laws.append(((1-g)*(1-u0),g*(1-u1),g*u1,(1-g)*u0))
    total = F(0)
    for y in range(4):
        masses = [sum(weights[j]*laws[j][y ^ (3*w)]/2 for j in range(4)) for w in (0,1)]
        total += min(masses[1],masses[0],sum(masses)/10)
    return total


def direct_scores(weights,parameters,y,t,boundaries=(26,51,76),horizon=100,retain=True):
    z = (y >> 1) ^ (y & 1)
    u = sum(weights[j]*parameters[j][2+2*z]/parameters[j][3+2*z] for j in range(4))
    r = min(u,1-u)
    if t == horizon:
        return r,F(1,10),F(0),u
    v0 = terminal(weights,parameters,t+1,boundaries)
    if not retain:
        return r+v0,F(1,10)+v0,F(0),u
    future = F(0)
    for target in (0,1):
        x = (y >> 1) ^ target
        p = [list(row) for row in parameters]
        masses = []
        for j in range(4):
            orientation = p[j][2+2*z]/p[j][3+2*z]
            masses.append(weights[j]*(orientation if x else 1-orientation))
            p[j][2+2*z] += x
            p[j][3+2*z] += 1
        probability = sum(masses)
        if probability:
            future += probability*terminal([w/probability for w in masses],p,t+1,boundaries)
    return r+v0,F(1,10)+future,v0-future,u


def exact_action(qr,qq,u,y):
    return 2 if qq <= qr else (y >> 1) ^ int(u > F(1,2))


def latent_scores(initial,history,y,boundaries):
    """Integrate complete error paths with Dirichlet moments, not beta factors."""
    import qualify_fep_changing_world as Q
    configurations = [()]+[(t,) for t in boundaries]
    prior = [F(1,2),F(1,6),F(1,6),F(1,6)]
    def evidence(hist):
        return sum(w*Q.evidence(tuple(initial),tuple(hist),conf) for w,conf in zip(prior,configurations))
    current = tuple(history)+((y,None),)
    den = evidence(current)
    def continuation(prefix):
        value = F(0)
        for yy in range(4):
            mass = [evidence(tuple(prefix)+((yy,w),))/den for w in (0,1)]
            value += min(mass[1],mass[0],sum(mass)/10)
        return value
    labeled = [tuple(history)+((y,w),) for w in (0,1)]
    immediate = min(evidence(h)/den for h in labeled)
    return immediate+continuation(current),F(1,10)+sum(continuation(h) for h in labeled)


def compare_case(S,counts,history,y,boundaries,horizon=100):
    w,p,_,_ = S.M.rational_state(counts,history,'C',boundaries,current=y)
    t = len(history)+1
    qr,qq,delta,u = direct_scores(w,p,y,t,boundaries,horizon)
    wr = np.array([[float(x) for x in w]])
    pr = np.array([[[float(x) for x in v] for v in p]])
    z = np.array([(y >> 1) ^ (y & 1)],dtype=bool)
    a,b,c = S.scores(wr,pr,z,t,boundaries,horizon)
    for name,actual,expected in zip(('report','reference','Delta'),(a[0],b[0],c[0]),(qr,qq,delta)):
        S.check('qualification','rational '+name,abs(actual-float(expected)) < 2e-14)
    S.check('qualification','rational nonnegative value',delta >= 0)
    # Directly enumerate each candidate report's current loss as well as the
    # purchase. This is the matched Bayesian expected-cost action calculation.
    pw1 = u if (y >> 1) == 0 else 1-u
    continuation = qr-min(u,1-u)
    costs = (pw1+continuation,1-pw1+continuation,qq)
    matched = 2 if costs[2] <= min(costs[:2]) else 0 if costs[0] < costs[1] else 1
    S.check('qualification','matched Bayesian action',matched == exact_action(qr,qq,u,y))
    if abs(a[0]-b[0]) > 1e-12:
        fast = 2 if b[0] <= a[0] else (y >> 1) ^ int(float(u) > .5)
        S.check('qualification','batched action',fast == matched)
    # A retention lesion removes future value for this fresh-target task.
    ar,br,dr = S.scores(wr,pr,z,t,boundaries,horizon,retain=False)
    er,eq,ed,eu = direct_scores(w,p,y,t,boundaries,horizon,retain=False)
    myopic = 2 if min(u,1-u) >= F(1,10) else (y >> 1) ^ int(u > F(1,2))
    S.check('qualification','label-ignorance collapse',dr[0] == 0 and ed == 0 and exact_action(er,eq,eu,y) == myopic
            and abs(ar[0]-float(er)) < 2e-14 and abs(br[0]-float(eq)) < 2e-14)
    return qr,qq


def qualify(S,cpus):
    start = perf_counter()
    initial = ((64,0,0,0),(16,16,16,16),(4,0,0,0))
    observations = list(product(range(4),(None,0,1)))
    histories = [()]+[(x,) for x in observations]+list(product(observations,repeat=2))
    boundaries = (2,3,4)
    cases = 0
    for counts in initial:
        for hist in histories:
            for y in range(4):
                qr,qq = compare_case(S,counts,list(hist),y,boundaries)
                if len(hist) <= 1:
                    lr,lq = latent_scores(counts,hist,y,boundaries)
                    S.check('qualification','independent latent-error path enumeration',lr == qr and lq == qq)
                cases += 1
    rng = random.Random(2026092417)
    boundary_cases = 0
    for t in (25,26,50,51,75,76,99,100):
        hist = [(rng.randrange(4),rng.choice((None,None,0,1))) for _ in range(t-1)]
        for y in range(4):
            compare_case(S,(16,16,16,16),hist,y,S.M.BOUNDARIES)
            boundary_cases += 1
    # Exact synthetic tie at a reset of the sole supported component: the
    # bought answer has no future value after that component is reset.
    w = [F(0),F(1),F(0),F(0)]
    p = [[F(1),F(2),F(1),F(10),F(1),F(10)] for _ in range(4)]
    qr,qq,d,u = direct_scores(w,p,0,25)
    S.check('qualification','exact nonterminal tie and reset',qr == qq == F(1,5) and d == 0 and exact_action(qr,qq,u,0) == 2)
    for y in range(4):
        qr,qq,d,u = direct_scores(w,p,y,100)
        S.check('qualification','exact terminal tie',qr == qq == F(1,10) and d == 0 and exact_action(qr,qq,u,y) == 2)
    # Exercise the runtime rational replay path by forcing only the numerical
    # near-tie detector on a valid accessible history, restoring it afterward.
    learner = S.M.Filter(np.array([[4,0,0,0]]))
    learner.start(1)
    action,_,_,_ = learner.warning(np.array([0],dtype=np.int8))
    original_scores = S.scores
    def force_near(*args,**kwargs):
        a,b,d = original_scores(*args,**kwargs)
        return b.copy(),b,d
    try:
        S.scores = force_near
        selected,_,_,_,fallback = S.choose_future(learner,np.array([0],dtype=np.int8),action[:,2])
    finally:
        S.scores = original_scores
    w,p,_,_ = S.M.rational_state([4,0,0,0],[],current=0)
    qr,qq,_,u = direct_scores(w,p,0,1)
    S.check('qualification','accessible-history rational fallback',fallback == 1 and selected[0] == exact_action(qr,qq,u,0))
    # Preference normalization and expected surprisal, without adding a label.
    losses = np.array([0.,.1,1.])
    Z = 1+exp(-.1)+exp(-1.)
    pref = np.exp(-losses)/Z
    mass = np.array([.2,.3,.5])
    S.check('qualification','normalized preferences',abs(pref.sum()-1) < 1e-15)
    S.check('qualification','two-slot preference cost',abs(2*np.dot(mass,-np.log(pref))-(2*np.dot(mass,losses)+2*log(Z))) < 2e-15)
    S.check('qualification','final preference cost',abs(np.dot(mass,-np.log(pref))-(np.dot(mass,losses)+log(Z))) < 2e-15)
    # Observe the evaluator/filter boundary on a synthetic six-arm trajectory.
    original_filter,original_choose = S.M.Filter,S.choose_future
    instances = []
    access_checks = [0]
    class AccessFilter(original_filter):
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
            if self.role == 1:
                permitted[:,2] = self.future_action == 2
            S.check('qualification','paid-only labels supplied',np.array_equal(labels >= 0,permitted))
            access_checks[0] += 1
            return super().retain(labels)
    def observed_choose(learner,*args):
        result = original_choose(learner,*args)
        learner.future_action = result[0].copy()
        return result
    try:
        S.M.Filter,S.choose_future = AccessFilter,observed_choose
        arrays,_ = S.run_batch(S.A.synthetic(),list(range(4)),'qualification-'+S.PREFIX)
    finally:
        S.M.Filter,S.choose_future = original_filter,original_choose
    original,_ = S.M.run_batch(S.A.synthetic(),list(range(4)),'qualification-'+S.PREFIX)
    for key in ('wrong','references'):
        S.check('qualification','unchanged controls '+key,np.array_equal(arrays[key][:,:,:5],original[key]))
    window = (10*arrays['window_wrong']+arrays['window_references'])/10
    S.check('qualification','unchanged control windows',np.allclose(window[:,:,:5],original['window_loss'],atol=2e-14,rtol=0))
    S.check('qualification','unchanged control fallback counts',np.array_equal(arrays['control_fallback'],original['fallback']))
    # Fixed historical control bridge, not a development cohort for C2.
    meta = S.M.population()[0]
    historical,_ = S.run_batch(meta,list(range(128)),'fep-changing-world-v1')
    path = S.M.ROOT/'attempt-01/blocks'/f'{meta["label"]}_0000_0127.npz'
    with np.load(path,allow_pickle=False) as saved:
        for name in ('wrong','references'):
            S.check('qualification','saved original control '+name,np.array_equal(historical[name][:,:,:5],saved[name]))
        S.check('qualification','saved original calibration',np.array_equal(historical['calibration'],saved['calibration']))
        window = (10*historical['window_wrong']+historical['window_references'])/10
        S.check('qualification','saved original windows',np.allclose(window[:,:,:5],saved['window_loss'],atol=2e-14,rtol=0))
        S.check('qualification','saved original fallback',np.array_equal(historical['control_fallback'],saved['fallback']))
    x = np.arange(1024,dtype=float)[None,:]+np.arange(27)[:,None]
    S.check('qualification','paired independent-block uncertainty',S.stats((x+2)-x)['mc_se'] == 0
        and abs(S.stats(x)['mc_se']-np.sqrt(np.var(np.arange(1024),ddof=1)/(27*1024))) < 1e-14)
    jobs = [(S.A.synthetic(),list(range(i*2,i*2+2)),'qualification-parallel-'+S.PREFIX,None) for i in range(4)]
    one = [S.worker(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=4,initializer=S.M.pin_cpus,initargs=(cpus,)) as pool:
        four = list(pool.map(S.worker,jobs))
    for a,b in zip(one,four):
        S.check('qualification','one/four-worker equality',a['fingerprint'] == b['fingerprint'])
    return dict(status='PASS',checks=dict(S.CHECKS),assertions=sum(S.CHECKS.values()),
        wall_seconds=perf_counter()-start,rational_short_history_cases=cases,
        actual_boundary_and_terminal_cases=boundary_cases,latent_error_cases=156,
        paid_label_access_calls=access_checks[0],one_four_worker_chunks=4,
        historical_control_bridge='first initial law, original blocks 0-127; no C2 performance selection',
        new_main_outcomes_used=False,matched_Bayesian_calculation='exact rational next-warning/label/action enumeration')
