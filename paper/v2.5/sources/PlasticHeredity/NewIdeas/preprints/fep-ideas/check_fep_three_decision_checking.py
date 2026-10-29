#!/usr/bin/env python3
"""Frozen seven-arm test of a three-decision contingent checking horizon."""
import os
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_name] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import subprocess
from time import perf_counter,process_time
import traceback

SOURCE = Path(__file__).resolve().parent
assert sha256((SOURCE/'check_fep_future_aware_checking.py').read_bytes()).hexdigest() == 'f9fc4ffa70ea3f2f14a4ef3a1cab282819b228008aefd5c01428058494ba7988'
assert sha256((SOURCE/'qualify_fep_future_aware_checking.py').read_bytes()).hexdigest() == '795cadf35b58ddfb25d9bfd2c06a08ae212152bea172ea29c6727b470a7452a3'
import check_fep_future_aware_checking as B
import numpy as np
M,A = B.M,B.A

ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-three-decision-checking-v1')
PREVIOUS = B.ROOT/'attempt-01'
PREVIOUS_SHA = 'ed960bb62e8db392c88fde7f6d1574b14386b8f77bc4c88ca5293cb1a4923fbf'
REPORT_SHA = '5577bb9be0fbdecb8088e53b93b20bc97f9bc8577a68b85a95afcfe4269afa00'
PREFIX = 'fep-three-decision-checking-v1'
ARMS = (*B.ARMS,'C3')
CHECKS = {}


def check(group,name,condition):
    if not bool(condition):
        raise AssertionError(f'{group}: {name}')
    CHECKS[group] = CHECKS.get(group,0)+1


def future_two(weights,parameters,next_task,boundaries=M.BOUNDARIES,retain=True):
    """Two contingent future tasks, before either warning; unnormalized mass."""
    p = parameters
    if next_task in boundaries:
        p = p.copy()
        p[:,boundaries.index(next_task)+1] = M.PRIOR
    g = p[...,0]/p[...,1]
    value = np.zeros(len(weights))
    for z in (0,1):
        mass = weights*(g if z else 1-g)
        after = p.copy()
        after[...,0] += z
        after[...,1] += 1
        u = after[...,2+2*z]/after[...,3+2*z]
        total = mass.sum(axis=-1)
        one = (mass*u).sum(axis=-1)
        v0 = B.terminal_value(mass,after,next_task+1,boundaries)
        if retain:
            v1 = np.zeros(len(weights))
            for x in (0,1):
                branch = after.copy()
                branch[...,2+2*z] += x
                branch[...,3+2*z] += 1
                v1 += B.terminal_value(mass*(u if x else 1-u),branch,next_task+1,boundaries)
        else:
            v1 = v0
        report = np.minimum(one,total-one)+v0
        reference = .1*total+v1
        value += np.minimum(report,reference)
    return value


def scores(weights,parameters,z,t,boundaries=M.BOUNDARIES,horizon=100,retain=True,steps=3):
    remaining = min(steps,horizon-t+1)
    if remaining <= 2:
        return B.scores(weights,parameters,z,t,boundaries,t+remaining-1,retain)
    check('planning','fixed three-decision horizon',remaining == 3)
    uz = np.where(z[:,None],parameters[...,4]/parameters[...,5],parameters[...,2]/parameters[...,3])
    u = (weights*uz).sum(axis=-1)
    risk = np.minimum(u,1-u)
    v0 = future_two(weights,parameters,t+1,boundaries,retain)
    if not retain:
        return risk+v0,.1+v0,np.zeros(len(weights))
    v1 = np.zeros(len(weights))
    for x in (0,1):
        branch = parameters.copy()
        for parity,offset in ((0,2),(1,4)):
            which = (z == parity)[:,None]
            branch[...,offset] += which*x
            branch[...,offset+1] += which
        v1 += future_two(weights*(uz if x else 1-uz),branch,t+1,boundaries,retain)
    delta = v0-v1
    check('planning','nonnegative instrumental information value',np.all(delta >= -4e-14))
    return risk+v0,.1+v1,delta


def choose_three(learner,y,myopic):
    own2 = B.choose_future(learner,y,myopic)
    if learner.t >= 99:
        # Exact frozen C2 collapse, including its own rational tie handling.
        action,delta,gain,extra,nf = own2
        return action,delta,gain,extra,nf,action.copy(),0
    w,p = np.exp(learner.logw[:,2,:]),learner.p[:,2,:,:]
    qr,qq,delta = scores(w,p,learner.z,learner.t,learner.boundaries)
    u = (w*np.where(learner.z[:,None],p[...,4]/p[...,5],p[...,2]/p[...,3])).sum(axis=-1)
    action = np.where(qq <= qr,2,(y >> 1) ^ (u > .5)).astype(np.int8)
    near = np.abs(qr-qq) <= 1e-12
    fallback = 0
    if near.any():
        from qualify_fep_three_decision_checking import direct_scores,exact_action
        for row in np.flatnonzero(near):
            hist = [(int(learner.ys[row,k]),None if learner.labels[row,2,k] < 0 else int(learner.labels[row,2,k]))
                    for k in range(learner.t-1)]
            ew,ep,_,_ = M.rational_state(learner.counts[row],hist,'C',learner.boundaries,
                                       learner.priors,int(y[row]))
            er,eq,_,eu = direct_scores(ew,ep,int(y[row]),learner.t,learner.boundaries)
            action[row] = exact_action(er,eq,eu,int(y[row]))
            fallback += 1
    check('planning','never forego own-history myopic purchase',not np.any((myopic == 2) & (action != 2)))
    extra = (action == 2) & (myopic != 2)
    check('planning','selected extra score gain',np.all((qr-qq)[extra] >= -2e-12))
    return action,delta,np.where(extra,qr-qq,0.),extra,fallback,own2[0],own2[4]


def run_batch(meta,indices,prefix):
    start,cpu = perf_counter(),process_time()
    b,n = len(indices),len(indices)*10
    cal,warnings,truth,_ = A.physical_trace(meta,indices,prefix)
    y,target = warnings.reshape(n,100),truth.reshape(n,100)
    counts = np.repeat(cal,10,axis=0)
    controls,c2,c3 = M.Filter(counts),M.Filter(counts),M.Filter(counts)
    wrong = np.zeros((n,7),dtype=np.int16)
    refs = np.zeros_like(wrong)
    ww = np.zeros((n,7,3),dtype=np.int16)
    wr = np.zeros_like(ww)
    pw,pr = np.zeros_like(wrong),np.zeros_like(wrong)
    first = np.full_like(wrong,101)
    tau = np.tile(np.array([t for _,t in M.CONDITIONS]),b)
    extra2,extra3 = np.zeros((n,3),dtype=np.int16),np.zeros((n,3),dtype=np.int16)
    delta2,delta3,gain2,gain3 = (np.zeros(n) for _ in range(4))
    disagreements = np.zeros((n,2),dtype=np.int16)
    fallbacks = np.zeros(3,dtype=np.int64)  # C2, C3, own-C2 diagnostic on C3 history
    for t in range(1,101):
        for f in (controls,c2,c3):
            f.start(t)
        base,_,_,_ = controls.warning(y[:,t-1])
        my2,_,_,_ = c2.warning(y[:,t-1])
        my3,_,_,_ = c3.warning(y[:,t-1])
        a2,d2,g2,e2,n2 = B.choose_future(c2,y[:,t-1],my2[:,2])
        a3,d3,g3,e3,n3,own2,nd = choose_three(c3,y[:,t-1],my3[:,2])
        fallbacks += (n2,n3,nd)
        if t >= 99:
            check('terminal','C3-to-C2 collapse',np.array_equal(a3,own2))
        if t == 100:
            check('terminal','final myopic collapse',np.array_equal(a3,my3[:,2]) and np.all(d3 == 0))
        actions = np.column_stack((base,a2,a3))
        ask = actions == 2
        error = (actions != target[:,t-1,None]) & ~ask
        affected = t >= tau
        for extra,event,ai in ((extra2,e2,5),(extra3,e3,6)):
            extra[:,0] += event
            extra[:,1] += event & affected
            extra[:,2] += event & affected & (first[:,ai] < t)
        disagreements[:,0] += (a3 == 2) & (own2 != 2)
        disagreements[:,1] += (a3 != 2) & (own2 == 2)
        first = np.where(ask & affected[:,None] & (first == 101),t,first)
        wrong += error
        refs += ask
        pw += error & affected[:,None]
        pr += ask & affected[:,None]
        if t >= 26:
            wi = (t-26)//25
            ww[:,:,wi] += error
            wr[:,:,wi] += ask
        delta2 += d2
        delta3 += d3
        gain2 += g2
        gain3 += g3
        controls.retain(np.where(ask[:,:5],target[:,t-1,None],-1).astype(np.int8))
        for f,ai in ((c2,5),(c3,6)):
            labels = np.full((n,5),-1,dtype=np.int8)
            labels[:,2] = np.where(ask[:,ai],target[:,t-1],-1)
            f.retain(labels)
    out = dict(indices=np.array(indices,dtype=np.int16),calibration=cal,
        wrong=wrong.reshape(b,10,7),references=refs.reshape(b,10,7),
        window_wrong=ww.reshape(b,10,7,3),window_references=wr.reshape(b,10,7,3),
        post_wrong=pw.reshape(b,10,7),post_references=pr.reshape(b,10,7),first_post_reference=first.reshape(b,10,7),
        extra_references=extra3.reshape(b,10,3),delta_sum=delta3.reshape(b,10),selected_gain_sum=gain3.reshape(b,10),
        own_c2_disagreements=disagreements.reshape(b,10,2),
        c2_extra_references=extra2.reshape(b,10,3),c2_delta_sum=delta2.reshape(b,10),c2_selected_gain_sum=gain2.reshape(b,10),
        planner_fallbacks=fallbacks,control_fallback=controls.fallback,
        c2_inference_fallback=c2.fallback,c3_inference_fallback=c3.fallback)
    check('accounting','task counts',np.all(wrong+refs <= 100) and np.all(ww+wr <= 25))
    for ex,ai in ((extra2,5),(extra3,6)):
        check('accounting','extra purchase subset',np.all(ex[:,2] <= ex[:,1]) and np.all(ex[:,1] <= ex[:,0]) and np.all(ex[:,0] <= refs[:,ai]))
    for j,(_,when) in enumerate(M.CONDITIONS):
        if when == 101:
            check('accounting','stable post endpoint absent',np.all(out['post_wrong'][:,j] == 0) and np.all(out['post_references'][:,j] == 0) and np.all(out['first_post_reference'][:,j] == 101))
        else:
            wi = M.BOUNDARIES.index(when)
            for key,wkey in (('post_wrong','window_wrong'),('post_references','window_references')):
                check('accounting','post/window '+key,np.array_equal(out[key][:,j],out[wkey][:,j,:,wi:].sum(axis=-1)))
    return out,dict(wall_seconds=perf_counter()-start,cpu_seconds=process_time()-cpu,
                    checks=dict(CHECKS),cpus=sorted(os.sched_getaffinity(0)))


def worker(job):
    meta,indices,prefix,output = job
    arrays,record = run_batch(meta,indices,prefix)
    record.update(label=meta['label'],first=indices[0],last=indices[-1],fingerprint=M.fingerprint(arrays))
    if output:
        path = Path(output)/'blocks'/f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        with path.open('xb') as stream:
            np.savez_compressed(stream,**arrays)
        record['record'] = M.identity(path)
    return record


def stats_int(numerator,denominator,offset=0.):
    values = numerator/denominator+offset
    result = B.stats(values)
    mean = int(numerator.sum())/(numerator.size*denominator)+offset
    result.update(mean=mean,lower95=mean-1.96*result['mc_se'],upper95=mean+1.96*result['mc_se'])
    return result


def arm_summary(numerator,denominator,offset=0.):
    return dict(arms={arm:stats_int(numerator[:,:,j],denominator,offset) for j,arm in enumerate(ARMS)},
        contrasts={f'C3_minus_{arm}':stats_int(numerator[:,:,6]-numerator[:,:,j],denominator) for j,arm in enumerate(ARMS[:6])},
        C3_minus_always=stats_int(numerator[:,:,6],denominator,offset-.1))


def aggregate(output,pop):
    fields = ('wrong','references','window_wrong','window_references','post_wrong','post_references',
        'first_post_reference','extra_references','delta_sum','selected_gain_sum','own_c2_disagreements',
        'c2_extra_references','c2_delta_sum','c2_selected_gain_sum')
    rows = {k:[] for k in fields}
    fallbacks = {k:np.zeros(3,dtype=np.int64) for k in ('planner_fallbacks','control_fallback','c2_inference_fallback','c3_inference_fallback')}
    for meta in pop:
        parts = []
        for i in range(0,1024,128):
            with np.load(output/'blocks'/f'{meta["label"]}_{i:04d}_{i+127:04d}.npz',allow_pickle=False) as data:
                check('aggregation','complete block indices',np.array_equal(data['indices'],np.arange(i,i+128)))
                parts.append({k:data[k] for k in fields})
                for k in fallbacks:
                    fallbacks[k] += data[k]
        for k in fields:
            rows[k].append(np.concatenate([part[k] for part in parts],axis=0))
    rows = {k:np.stack(v) for k,v in rows.items()}
    units = 10*rows['wrong'].astype(np.int64)+rows['references']
    post_units = 10*rows['post_wrong'].astype(np.int64)+rows['post_references']
    coefficients = np.rint(18*M.group_weights()).astype(np.int64)
    post_multiplier = np.array([0]+[2,3,6]*3)
    episode,post_groups = {},{}
    for g,co in zip(M.PROFILE_GROUPS,coefficients):
        num = np.einsum('k,brka->bra',co,units)
        episode[g] = arm_summary(num,18000,.00064)
        if g not in ('full','stable'):
            num = np.einsum('k,brka->bra',co*post_multiplier,post_units)
            post_groups[g] = arm_summary(num,27000)
    criteria = dict(economical_recovery=post_groups['changed']['C3_minus_always']['upper95'] < 0,
        overall_useful_function=episode['full']['C3_minus_always']['upper95'] < 0,
        value_of_longer_horizon=post_groups['changed']['contrasts']['C3_minus_C2']['upper95'] < 0)
    conditions = {}
    for bi,meta in enumerate(pop):
        for j,(method,tau) in enumerate(M.CONDITIONS):
            arms,contrasts = {},{}
            den = 10*max(1,101-tau)
            for ai,arm in enumerate(ARMS):
                arms[arm] = dict(episode=stats_int(units[bi,:,j,ai],1000,.00064),
                    post_change=None if method == 'stable' else stats_int(post_units[bi,:,j,ai],den),
                    mean_wrong=float(rows['wrong'][bi,:,j,ai].mean()),mean_references=float(rows['references'][bi,:,j,ai].mean()),
                    mean_window_cost=((10*rows['window_wrong'][bi,:,j,ai]+rows['window_references'][bi,:,j,ai])/10).mean(axis=0).tolist())
                if arm != 'C3':
                    contrasts['C3_minus_'+arm] = dict(episode=stats_int(units[bi,:,j,6]-units[bi,:,j,ai],1000),
                        post_change=None if method == 'stable' else stats_int(post_units[bi,:,j,6]-post_units[bi,:,j,ai],den))
            conditions[f'{meta["label"]}__{method}_{tau}'] = dict(arms=arms,contrasts=contrasts,
                extra_references_mean=rows['extra_references'][bi,:,j].mean(axis=0).tolist(),
                own_c2_disagreements_mean=rows['own_c2_disagreements'][bi,:,j].mean(axis=0).tolist(),
                delta_sum_mean=float(rows['delta_sum'][bi,:,j].mean()),selected_gain_sum_mean=float(rows['selected_gain_sum'][bi,:,j].mean()),
                weight='1/54' if method == 'stable' else '1/486')
    counts = {}
    for endpoint in ('episode','post_change'):
        counts[endpoint] = {}
        for arm in ARMS[:6]:
            ds = [v['contrasts']['C3_minus_'+arm][endpoint] for v in conditions.values() if v['contrasts']['C3_minus_'+arm][endpoint] is not None]
            counts[endpoint][arm] = dict(point_lower=sum(d['mean'] < 0 for d in ds),point_equal=sum(d['mean'] == 0 for d in ds),
                point_higher=sum(d['mean'] > 0 for d in ds),upper_below_zero=sum(d['upper95'] < 0 for d in ds),lower_above_zero=sum(d['lower95'] > 0 for d in ds))
    planning = {}
    for g,co in zip(M.PROFILE_GROUPS,coefficients):
        extra = np.einsum('k,brkd->brd',co,rows['extra_references'].astype(np.int64))
        disagree = np.einsum('k,brkd->brd',co,rows['own_c2_disagreements'].astype(np.int64))
        planning[g] = {name:stats_int(extra[:,:,i],18) for i,name in enumerate(('extra_references','post_extra_references','extras_after_first_post_answer'))}
        for i,name in enumerate(('C3_buys_own_C2_reports','C3_reports_own_C2_buys')):
            planning[g][name] = stats_int(disagree[:,:,i],18)
        for field in ('delta_sum','selected_gain_sum'):
            planning[g][field] = B.stats(np.einsum('k,brk->br',co/18,rows[field]))
    window = 10*rows['window_wrong'].astype(np.int64)+rows['window_references']
    recovery = {}
    for wi,tau in enumerate(M.BOUNDARIES):
        ix = [j for j,(_,t) in enumerate(M.CONDITIONS) if t == tau]
        recovery[str(tau)] = dict(changed=arm_summary(np.take(window,ix,axis=2)[...,wi].sum(axis=2),750),
                                 stable=arm_summary(window[:,:,0,:,wi],250))
    return dict(summary=dict(independent_blocks=27648,conditions=270,physical_episodes=276480,controller_task_steps=193536000,
        arms=list(ARMS),primary='C3',seed_prefix=PREFIX,horizon='receding current plus two future tasks; C2 at 99 and myopic at 100',
        samples_per_base=1024,new_world_types=False,priors_or_prices_tuned=False,optional_stopping=False),
        criteria=criteria,complete_proposed_improvement_supported=all(criteria.values()),episode=episode,post_change=post_groups,
        conditions=conditions,condition_counts=counts,planning=planning,first_25_task_mean_cost=recovery,
        fallbacks={k:v.tolist() for k,v in fallbacks.items()})


def mount_check(output):
    item = json.loads(subprocess.check_output(['findmnt','-J','-T','/mnt/bioIce1','-o','TARGET,SOURCE,FSTYPE'],text=True))['filesystems'][0]
    check('storage','external FEP mount',item['target'] == '/mnt/bioIce1' and item['source'] == '/dev/sdc1' and item['fstype'] == 'ext4' and output.parent == ROOT)
    s = os.statvfs('/mnt/bioIce1')
    free = s.f_bavail*s.f_frsize
    check('storage','adequate space',free > 2_000_000_000)
    return dict(mount=item,free_bytes=free)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True,exist_ok=False)
    (output/'inputs').mkdir()
    (output/'blocks').mkdir()
    M.logline(output,'PREPARE: one fixed three-decision comparison; freeze before qualification and main outcomes')
    check('integrity','previous manifest',M.identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report',M.identity(SOURCE/'FEP_FUTURE_AWARE_CHECKING_V1_REPORT.md')['sha256'] == REPORT_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = {r['path']:r for group in ('inputs','outputs','preserved') for r in prior[group]}
    for path in (PREVIOUS/'MANIFEST.json',SOURCE/'FEP_FUTURE_AWARE_CHECKING_V1_REPORT.md'):
        preserved[str(path)] = M.identity(path)
    M.verify(list(preserved.values()))
    inputs = []
    for name in ('FEP_THREE_DECISION_CHECKING_V1.md','check_fep_three_decision_checking.py','qualify_fep_three_decision_checking.py'):
        inputs.append(M.identity(SOURCE/name))
        shutil.copyfile(SOURCE/name,output/'inputs'/name)
    pop = M.population()
    M.write(output/'POPULATION.json',dict(bases=pop,conditions=M.CONDITIONS,arms=ARMS,primary='C3',group_weights=M.group_weights().tolist(),stable_weight='1/2',changed_weight='1/2'))
    seeds = {m['label']:[str(M.seed_for(m['label'],i,PREFIX)) for i in range(1024)] for m in pop}
    new = {x for row in seeds.values() for x in row}
    check('seeds','all new seeds distinct',len(new) == 27648)
    for path in (M.ROOT/'attempt-01/SEEDS.json',PREVIOUS/'SEEDS.json'):
        old = json.loads(path.read_text())['blocks']
        check('seeds','no overlap '+str(path),not(new & {x for row in old.values() for x in row}))
    M.write(output/'SEEDS.json',dict(root=20260924,main_prefix=PREFIX,rng='Python random.Random MT19937',python=platform.python_version(),
        draw_order=M.streams.__doc__,blocks=seeds,overlap_with_changing_world=0,overlap_with_C2_study=0))
    inputs += [M.identity(output/'POPULATION.json'),M.identity(output/'SEEDS.json')]
    snapshots = [M.identity(p) for p in sorted((output/'inputs').iterdir())]
    check('integrity','source snapshots',sorted(r['sha256'] for r in inputs[:3]) == sorted(r['sha256'] for r in snapshots))
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources','four available CPUs',len(cpus) == 4)
    M.write(output/'PREPARATION.json',dict(started_utc=M.now(),inputs=inputs,source_snapshots=snapshots,preserved=list(preserved.values()),
        storage=storage,cpus=cpus,python=platform.python_version(),numpy=np.__version__))
    M.logline(output,'FROZEN: design, both sources, population, weights and fresh seeds; inherited identities verified')
    M.pin_cpus(cpus)
    import qualify_fep_three_decision_checking as Q
    qualification = Q.qualify(sys.modules[__name__],cpus)
    M.write(output/'QUALIFICATION.json',qualification)
    M.logline(output,f'QUALIFIED: {qualification["assertions"]} assertions; {qualification["wall_seconds"]:.3f}s')
    jobs = [(A.synthetic(),list(range(i*32,(i+1)*32)),'benchmark-'+PREFIX,None) for i in range(4)]
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(cpus,)) as pool:
        records = list(pool.map(worker,jobs))
    elapsed = perf_counter()-start
    forecast = 120+3*elapsed*(27648/128)
    M.write(output/'BENCHMARK.json',dict(wall_seconds=elapsed,forecast_seconds=forecast,requires_detached=forecast > 600,
        workers=4,synthetic_blocks=128,records=records,rule='120 + 3 * four-worker wall * 27648 / 128; no outcome selection'))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output,f'PREPARED: forecast {forecast:.3f}s; detached={forecast>600}; no main outcomes')
    print(json.dumps(dict(qualification=qualification['assertions'],forecast_seconds=forecast,requires_detached=forecast>600)))


def execute(output,detached):
    start,cpu = perf_counter(),process_time()
    prep = json.loads((output/'PREPARATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    check('execution','qualified',json.loads((output/'QUALIFICATION.json').read_text())['status'] == 'PASS')
    check('execution','detachment rule',detached or not bench['requires_detached'])
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    mount_check(output)
    M.pin_cpus(prep['cpus'])
    M.write(output/'EXECUTION_STARTED.json',dict(started_utc=M.now(),pid=os.getpid(),detached=detached,cpus=prep['cpus'],workers=4,
        benchmark=M.identity(output/'BENCHMARK.json')))
    M.logline(output,'MAIN STARTED: 216 fixed chunks, 27648 fresh blocks, 270 conditions, seven arms; no adaptation')
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(m,list(range(i,i+128)),PREFIX,str(output)) for m in pop for i in range(0,1024,128)]
    records = []
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(prep['cpus'],)) as pool:
        for i,record in enumerate(pool.map(worker,jobs),1):
            records.append(record)
            if i % 8 == 0:
                M.logline(output,f'COMPLETED {i}/216 chunks; {record["label"]}; durable outputs')
    M.write(output/'WORKERS.json',records)
    results = aggregate(output,pop)
    M.write(output/'RESULTS.json',results)
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    M.verify([r['record'] for r in records])
    M.logline(output,f'COMPLETE: {perf_counter()-start:.3f}s; all criteria and signed outcomes retained')
    outputs = [M.identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
    M.write(output/'MANIFEST.json',dict(status='COMPLETE',started_utc=json.loads((output/'EXECUTION_STARTED.json').read_text())['started_utc'],
        finished_utc=M.now(),wall_seconds=perf_counter()-start,parent_cpu_seconds=process_time()-cpu,worker_cpu_seconds=sum(r['cpu_seconds'] for r in records),
        workers=4,cpus=prep['cpus'],python=platform.python_version(),numpy=np.__version__,inputs=prep['inputs'],preserved=prep['preserved'],
        outputs=outputs,summary=results['summary'],criteria=results['criteria'],checks=dict(CHECKS),identity_checks=dict(M.CHECKS)))


def launch(output):
    check('launch','prepared',(output/'BENCHMARK.json').is_file())
    check('launch','not started',not (output/'EXECUTION_STARTED.json').exists() and not (output/'LAUNCH.json').exists())
    with (output/'DETACHED_STDOUT.log').open('xb') as stream:
        child = subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'execute','--output',str(output),'--detached'],
            stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,cwd=SOURCE,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    record = dict(pid=child.pid,launched_utc=M.now(),automatic_polling=False,benchmark=M.identity(output/'BENCHMARK.json'))
    M.write(output/'LAUNCH.json',record)
    print(json.dumps(record))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('phase',choices=('prepare','execute','launch'))
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--detached',action='store_true')
    args = ap.parse_args()
    check('scope','new FEP attempt namespace',args.output.parent == ROOT and args.output.name.startswith('attempt-'))
    try:
        if args.phase == 'prepare':
            prepare(args.output)
        elif args.phase == 'execute':
            execute(args.output,args.detached)
        else:
            launch(args.output)
    except Exception:
        if args.output.is_dir():
            failure = args.output/f'FAILURE_{args.phase}.json'
            if not failure.exists():
                M.write(failure,dict(phase=args.phase,utc=M.now(),traceback=traceback.format_exc(),checks=dict(CHECKS)))
            M.logline(args.output,f'FAILED {args.phase}; attempt retained; no automatic rerun')
        raise


if __name__ == '__main__':
    main()
