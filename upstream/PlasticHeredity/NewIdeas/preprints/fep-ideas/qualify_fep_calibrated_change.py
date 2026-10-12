"""Independent scalar and latent-path references for the conditional model."""
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


def reset_rows(counts,transfer):
    c = list(map(int,counts))
    reset = []
    for j in range(10):
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


def rational_state(counts,history,current,transfer=True,boundaries=(26,51,76),kinds_prior=(F(1,3),)*3):
    w = [F(1,2)]+[F(1,6)*x for _ in boundaries for x in kinds_prior]
    p = [initial(counts) for _ in w]
    reset = reset_rows(counts,transfer)
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


def latent_evidence(counts,history,transfer,boundaries):
    """Integrate complete error paths with Dirichlet/Beta moments, no filter."""
    c = list(map(int,counts))
    evidence = [F(0) for _ in range(10)]
    unknown = [i for i,(_,target) in enumerate(history) if target is None]
    for values in product((0,1),repeat=len(unknown)):
        targets = [target for _,target in history]
        for i,value in zip(unknown,values):
            targets[i] = value
        errors = [y ^ (3*target) for (y,_),target in zip(history,targets)]
        for j in range(10):
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
    return [v*(F(1,2) if j == 0 else F(1,18)) for j,v in enumerate(evidence)]


def compare(S,counts,hist,y,transfer,boundaries=(2,3,4),steps=3):
    f = S.Filter(np.array([counts]),transfer,boundaries)
    for t,(yy,target) in enumerate(hist,1):
        f.start(t); f.warning(np.array([yy],dtype=np.int8))
        f.retain(np.array([-1 if target is None else target]))
    f.start(len(hist)+1); f.warning(np.array([y],dtype=np.int8))
    w,p,reset = rational_state(counts,hist,y,transfer,boundaries)
    S.check('qualification','rational mixture posterior',np.allclose(f.w[0],list(map(float,w)),atol=3e-14,rtol=0))
    S.check('qualification','rational conjugate state',np.array_equal(f.p[0],np.array(p,dtype=float)))
    r,q,d,u = direct_scores(w,p,reset,y,len(hist)+1,steps,boundaries)
    oldw,oldp,oldreset = f.w.copy(),f.p.copy(),f.reset.copy()
    actual = S.scores(f.w,f.p,f.reset,f.z,f.t,steps,boundaries)
    for name,a,e in zip(('report','reference','information value'),actual,(r,q,d)):
        S.check('qualification','rational '+name,abs(a[0]-float(e)) < 8e-14)
    S.check('qualification','nonnegative exact information value',d >= 0)
    actions,_,_,_ = f.choose(steps)
    S.check('qualification','exact chosen action',actions[0] == exact_action(r,q,u,y))
    S.check('qualification','planning leaves live state unchanged',np.array_equal(f.w,oldw) and np.array_equal(f.p,oldp) and np.array_equal(f.reset,oldreset))
    rr,qq,dd,_ = direct_scores(w,p,reset,y,f.t,steps,boundaries,False)
    ar,aq,ad = S.scores(f.w,f.p,f.reset,f.z,f.t,steps,boundaries,False)
    S.check('qualification','retention lesion',dd == 0 and ad[0] == 0 and abs(ar[0]-float(rr)) < 8e-14 and abs(aq[0]-float(qq)) < 8e-14)
    if len(hist) <= 2:
        ev = latent_evidence(counts,list(hist)+[(y,None)],transfer,boundaries)
        S.check('qualification','independent latent-path posterior',w == [x/sum(ev) for x in ev])
        optimum = -log(float(sum(ev)))
        wf,mass = np.array(w,dtype=float),np.array(ev,dtype=float)
        free = float(np.sum(wf*(np.log(wf)-np.log(mass))))
        perturbed = .9*wf+.1/10
        excess = float(np.sum(perturbed*(np.log(perturbed)-np.log(mass))))-optimum
        kl = float(np.sum(perturbed*(np.log(perturbed)-np.log(wf))))
        S.check('qualification','collapsed conditional VFE identity',abs(free-optimum)<5e-14 and abs(excess-kl)<5e-14 and excess>=-5e-14)


def old_projection(arrays):
    keys = ('indices','calibration','wrong','references','window_wrong','window_references','post_wrong','post_references','first_post_reference',
            'extra_references','delta_sum','selected_gain_sum','own_c2_disagreements','c2_extra_references','c2_delta_sum','c2_selected_gain_sum',
            'planner_fallbacks','control_fallback','c2_inference_fallback','c3_inference_fallback')
    fields = {'wrong','references','window_wrong','window_references','post_wrong','post_references','first_post_reference'}
    return {k:arrays[k][:,:,:7] if k in fields else arrays[k] for k in keys}


def qualify(S,cpus):
    started = perf_counter()
    histories = [(),((0,None),),((1,0),),((2,1),(3,None))]
    cases = 0
    for counts in ((0,0,0,0),(4,0,0,0),(16,16,16,16),(20,4,8,32)):
        for hist in histories:
            for y in range(4):
                for transfer in (False,True):
                    compare(S,counts,hist,y,transfer)
                    cases += 1
    rng = random.Random(20261008)
    for t in (24,25,26,49,50,51,74,75,76,98,99,100):
        hist = [(rng.randrange(4),rng.choice((None,None,0,1))) for _ in range(t-1)]
        for transfer in (False,True):
            compare(S,(20,4,8,32),hist,t%4,transfer,S.M.BOUNDARIES)
            cases += 1
        # General-only mixture must recover the frozen C3 values.
        y = t%4
        w,p,reset = rational_state((20,4,8,32),hist,y,True,S.M.BOUNDARIES,(F(1),F(0),F(0)))
        ow,op,_,_ = S.M.rational_state((20,4,8,32),hist,'C',current=y)
        selected = (0,1,4,7)
        S.check('qualification','general-only C3 posterior',[w[j] for j in selected] == ow and [p[j] for j in selected] == op)
        z = np.array([(y>>1)^(y&1)],dtype=bool)
        a = S.scores(np.array([w],dtype=float),np.array([p],dtype=float),np.array([reset],dtype=float),z,t)
        b = S.T.scores(np.array([ow],dtype=float),np.array([op],dtype=float),z,t)
        S.check('qualification','general-only C3 objective',np.allclose(a,b,atol=8e-14,rtol=0))
    # Shared blank calibration makes the two new prior settings identical.
    S.check('qualification','empty-calibration lesion collapse',reset_rows((0,0,0,0),True) == reset_rows((0,0,0,0),False))
    # Query at exact final threshold; rational tie rule must purchase.
    f = S.Filter(np.array([[9,0,0,1]]),False)
    f.start(100)
    f.w[:] = 0; f.w[:,0] = 1
    f.p[:,0] = [F(1),F(2),F(1),F(10),F(1),F(10)]
    r,q,d = S.scores(f.w,f.p,f.reset,np.array([False]),100)
    S.check('qualification','final exact cost tie',abs(r[0]-.1)<1e-15 and q[0]==.1 and d[0]==0 and exact_action(F(1,10),F(1,10),F(1,10),0)==2)
    meta = S.extend_meta(S.A.synthetic())
    for law in meta['laws']:
        S.check('qualification','physical probability law',sum(map(F,law)) == 1 and all(F(x)>0 for x in law))
    q = list(map(F,meta['laws'][0]))
    for index,mask in ((4,2),(5,1),(6,3)):
        enumerated = [F(0)]*4
        for e in range(4):
            for fa,fb in product((0,1),repeat=2):
                weight = (F(1,4) if fa else F(3,4))*(F(1,4) if fb else F(3,4))
                altered = e ^ ((2*fa+fb)&mask)
                enumerated[altered] += q[e]*weight
        S.check('qualification','independent partial-flip enumeration',enumerated == list(map(F,meta['laws'][index])))
    prefix = 'qualification-'+S.PREFIX
    new,_ = S.run_batch(meta,[0,1],prefix,core_only=True)
    old,_ = S.T.run_batch(meta,[0,1],prefix)
    projected = old_projection(new)
    S.check('qualification','old output fields',projected.keys() == old.keys())
    for key in old:
        S.check('qualification','exact old array '+key,projected[key].dtype == old[key].dtype and np.array_equal(projected[key],old[key]))
    S.check('qualification','old byte fingerprint',S.M.fingerprint(projected) == S.M.fingerprint(old))
    all_arrays,_ = S.run_batch(meta,[0,1],prefix)
    for key in ('wrong','references','window_wrong','window_references','post_wrong','post_references','first_post_reference'):
        S.check('qualification','core unaffected by transfer rows '+key,np.array_equal(all_arrays[key][:,:10],new[key]))
    for key in ('calibration','indices'):
        S.check('qualification','core input identity',np.array_equal(all_arrays[key],new[key]))
    # Saved-array aggregation and a separate scalar accounting route.
    fields = ('wrong','references','post_wrong','post_references','window_wrong','window_references','first_post_reference',
              'phase_counts','phase_sums','candidate_extra_references','candidate_values','diagnosis')
    rows = {k:all_arrays[k][None,...] for k in fields}
    result = S.analyze(rows,[meta])
    for ai,arm in enumerate(S.ARMS):
        for name,indices in (('core_changed',list(range(1,10))),('transfer',list(range(10,19))),('core_reliability',list(range(1,7)))):
            block_values = []
            for bi in range(2):
                values = [(int(all_arrays['post_wrong'][bi,j,ai])+int(all_arrays['post_references'][bi,j,ai])/10)/(101-S.CONDITIONS[j][1]) for j in indices]
                block_values.append(sum(values)/len(values))
            saved = result['post_change'][name]['arms'][arm]
            S.check('qualification','scalar endpoint',abs(saved['mean']-sum(block_values)/2)<2e-14)
            S.check('qualification','paired-block SE',abs(saved['mc_se']-abs(block_values[0]-block_values[1])/2)<2e-14)
    for group,co in S.coefficients().items():
        S.check('qualification','weights normalized',co.sum()==18 and np.all(co>=0))
    for wi,tau in enumerate(S.M.BOUNDARIES):
        for panel,indices in (('core',range(1,10)),('transfer',range(10,19))):
            selected = [j for j in indices if S.CONDITIONS[j][1] == tau]
            for ai,arm in enumerate(S.ARMS):
                block_values = [sum((int(all_arrays['window_wrong'][bi,j,ai,wi])+int(all_arrays['window_references'][bi,j,ai,wi])/10)/25 for j in selected)/3 for bi in range(2)]
                saved = result['first_25_task_mean_cost'][str(tau)][panel]['arms'][arm]
                S.check('qualification','scalar recovery-window mean',abs(saved['mean']-sum(block_values)/2)<2e-14)
                S.check('qualification','scalar recovery-window SE',abs(saved['mc_se']-abs(block_values[0]-block_values[1])/2)<2e-14)
    fixture = np.array([[0.,2.,4.,6.],[10.,12.,14.,16.]])
    se = np.sqrt((20/3+20/3)/(4*4))
    S.check('qualification','stratified uncertainty',abs(S.ci(fixture)['mc_se']-se)<1e-15)
    jobs = [(meta,[i],'parallel-'+S.PREFIX,None) for i in range(4)]
    serial = [S.worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=4,initializer=S.M.pin_cpus,initargs=(cpus,)) as pool:
        parallel = list(pool.map(S.worker,jobs))
    for a,b in zip(serial,parallel):
        S.check('qualification','one/four worker byte identity',a['fingerprint'] == b['fingerprint'])
        S.check('qualification','worker CPU limit',b['cpus'] == cpus)
    return dict(status='PASS',wall_seconds=perf_counter()-started,assertions=sum(S.CHECKS.values()),checks=dict(S.CHECKS),
        rational_cases=cases,old_arrays=20,one_four_worker_chunks=4,synthetic_only=True,
        references='independent scalar four-warning recursion and complete latent-path evidence; same author',
        inherited_policy_qualification='existing C3 policy checks inherited; original arrays and general-only bridge tested here')
