#!/usr/bin/env python3
"""Frozen six-arm comparison of one-step and two-decision evidence use."""
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
from time import perf_counter, process_time
import traceback

SOURCE = Path(__file__).resolve().parent
assert sha256((SOURCE/'check_fep_changing_world.py').read_bytes()).hexdigest() == '1d53b5dd695bf941addf7c03ebb94e6c2a441cd2b84ecbca77c2b4752a691fc1'
assert sha256((SOURCE/'check_fep_recovery_cost_audit.py').read_bytes()).hexdigest() == 'a8bf7e834ee4b66342b11091b8fce6e714d5ce9c33cbe2b750d8470374070ca3'
import check_fep_changing_world as M
import check_fep_recovery_cost_audit as A
import numpy as np

ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-future-aware-checking-v1')
PREVIOUS = ROOT.parent/'fep-recovery-cost-audit-v1/attempt-01'
PREVIOUS_SHA = 'd6e24c5d879b6cb7e2d62d7b24e6b36dae259861dee76c77a307a10ee05e6109'
REPORT_SHA = '5de2d7c4d855aaa40dc64ac12c6bda58898c0b425bbdb6298d58edf8d3814721'
PREFIX = 'fep-future-aware-checking-v1'
ARMS = (*M.ARMS,'C2')
CHECKS = {}


def check(group,name,condition):
    if not bool(condition):
        raise AssertionError(f'{group}: {name}')
    CHECKS[group] = CHECKS.get(group,0)+1


def terminal_value(weights,parameters,next_task,boundaries=M.BOUNDARIES):
    """Expected optimized next-task cost, homogeneous in component masses."""
    p = parameters
    if next_task in boundaries:
        p = p.copy()
        p[:,boundaries.index(next_task)+1] = M.PRIOR
    g = p[...,0]/p[...,1]
    value = np.zeros(len(weights))
    for z in (0,1):
        joint = weights*(g if z else 1-g)
        mass = joint.sum(axis=-1)
        one = (joint*p[...,2+2*z]/p[...,3+2*z]).sum(axis=-1)
        value += np.minimum(.1*mass,np.minimum(one,mass-one))
    return value


def scores(weights,parameters,z,t,boundaries=M.BOUNDARIES,horizon=100,retain=True):
    """Posterior is after today's warning but before a possible paid label."""
    uz = np.where(z[:,None],parameters[...,4]/parameters[...,5],parameters[...,2]/parameters[...,3])
    u = (weights*uz).sum(axis=-1)
    r = np.minimum(u,1-u)
    if t == horizon:
        return r,np.full(len(r),.1),np.zeros(len(r))
    v0 = terminal_value(weights,parameters,t+1,boundaries)
    if not retain:
        return r+v0,.1+v0,np.zeros(len(r))
    v1 = np.zeros(len(r))
    for x in (0,1):
        branch = parameters.copy()
        for parity,offset in ((0,2),(1,4)):
            which = (z == parity)[:,None]
            branch[...,offset] += which*x
            branch[...,offset+1] += which
        mass = weights*(uz if x else 1-uz)
        v1 += terminal_value(mass,branch,t+1,boundaries)
    delta = v0-v1
    check('planning','nonnegative instrumental information value',np.all(delta >= -2e-14))
    return r+v0,.1+v1,delta


def choose_future(learner,y,myopic):
    w = np.exp(learner.logw[:,2,:])
    p = learner.p[:,2,:,:]
    qr,qq,delta = scores(w,p,learner.z,learner.t,learner.boundaries)
    uz = np.where(learner.z[:,None],p[...,4]/p[...,5],p[...,2]/p[...,3])
    u = (w*uz).sum(axis=-1)
    action = np.where(qq <= qr,2,(y >> 1) ^ (u > .5)).astype(np.int8)
    near = np.abs(qr-qq) <= 1e-12
    fallback = 0
    if learner.t == 100:
        # Frozen warning() already resolved the final myopic action exactly.
        action = myopic.copy()
    else:
        from qualify_fep_future_aware_checking import direct_scores,exact_action
        for row in np.flatnonzero(near):
            history = [(int(learner.ys[row,k]),None if learner.labels[row,2,k] < 0 else int(learner.labels[row,2,k]))
                       for k in range(learner.t-1)]
            ew,ep,_,_ = M.rational_state(learner.counts[row],history,'C',learner.boundaries,
                                        learner.priors,int(y[row]))
            er,eq,_,eu = direct_scores(ew,ep,int(y[row]),learner.t,learner.boundaries)
            action[row] = exact_action(er,eq,eu,int(y[row]))
            fallback += 1
    check('planning','never forego an own-history myopic purchase',not np.any((myopic == 2) & (action != 2)))
    extra = (action == 2) & (myopic != 2)
    check('planning','extra-purchase score improvement',np.all((qr-qq)[extra] >= -2e-12))
    return action,delta,np.where(extra,qr-qq,0.),extra,fallback


def run_batch(meta,indices,prefix):
    start,cpu = perf_counter(),process_time()
    b = len(indices)
    calibration,warnings,truth,_ = A.physical_trace(meta,indices,prefix)
    y = warnings.reshape(b*10,100)
    target = truth.reshape(b*10,100)
    counts = np.repeat(calibration,10,axis=0)
    controls,candidate = M.Filter(counts),M.Filter(counts)
    wrong = np.zeros((b*10,6),dtype=np.int16)
    refs = np.zeros_like(wrong)
    window_wrong = np.zeros((b*10,6,3),dtype=np.int16)
    window_refs = np.zeros_like(window_wrong)
    post_wrong = np.zeros_like(wrong)
    post_refs = np.zeros_like(wrong)
    first_post = np.full_like(wrong,101)
    tau = np.tile(np.array([t for _,t in M.CONDITIONS]),b)
    extras = np.zeros((b*10,3),dtype=np.int16)  # all, post-change, after first post-change answer
    delta_sum = np.zeros(b*10)
    selected_gain = np.zeros(b*10)
    planner_fallback = 0
    for t in range(1,101):
        controls.start(t)
        candidate.start(t)
        base,_,_,_ = controls.warning(y[:,t-1])
        own,_,_,_ = candidate.warning(y[:,t-1])
        action,delta,gain,extra,nf = choose_future(candidate,y[:,t-1],own[:,2])
        planner_fallback += nf
        if t == 100:
            check('terminal','own-history myopic collapse',np.array_equal(action,own[:,2]) and np.all(delta == 0))
        actions = np.column_stack((base,action))
        ask = actions == 2
        err = (actions != target[:,t-1,None]) & ~ask
        affected = t >= tau
        extras[:,0] += extra
        extras[:,1] += extra & affected
        extras[:,2] += extra & affected & (first_post[:,5] < t)
        first_post = np.where(ask & affected[:,None] & (first_post == 101),t,first_post)
        wrong += err
        refs += ask
        post_wrong += err & affected[:,None]
        post_refs += ask & affected[:,None]
        if t >= 26:
            wi = (t-26)//25
            window_wrong[:,:,wi] += err
            window_refs[:,:,wi] += ask
        delta_sum += delta
        selected_gain += gain
        # Only purchased labels cross the evaluator/learner boundary.
        controls.retain(np.where(ask[:,:5],target[:,t-1,None],-1).astype(np.int8))
        labels = np.full((b*10,5),-1,dtype=np.int8)
        labels[:,2] = np.where(ask[:,5],target[:,t-1],-1)
        candidate.retain(labels)
    out = dict(indices=np.array(indices,dtype=np.int16),calibration=calibration,
        wrong=wrong.reshape(b,10,6),references=refs.reshape(b,10,6),
        window_wrong=window_wrong.reshape(b,10,6,3),window_references=window_refs.reshape(b,10,6,3),
        post_wrong=post_wrong.reshape(b,10,6),post_references=post_refs.reshape(b,10,6),
        first_post_reference=first_post.reshape(b,10,6),extra_references=extras.reshape(b,10,3),
        delta_sum=delta_sum.reshape(b,10),selected_gain_sum=selected_gain.reshape(b,10),
        planner_fallback=np.array([planner_fallback],dtype=np.int64),
        control_fallback=controls.fallback,candidate_inference_fallback=candidate.fallback)
    check('accounting','total tasks',np.all(wrong+refs <= 100))
    check('accounting','window tasks',np.all(window_wrong+window_refs <= 25))
    check('accounting','extra purchase subset',np.all(extras[:,2] <= extras[:,1]) and np.all(extras[:,1] <= extras[:,0]) and np.all(extras[:,0] <= refs[:,5]))
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


def stats(values):
    return A.ci(values)


def arm_summary(values):
    return dict(arms={arm:stats(values[:,:,j]) for j,arm in enumerate(ARMS)},
        contrasts={f'C2_minus_{arm}':stats(values[:,:,5]-values[:,:,j]) for j,arm in enumerate(ARMS[:5])},
        C2_minus_always=stats(values[:,:,5]-.1))


def aggregate(output,pop):
    fields = ('wrong','references','window_wrong','window_references','post_wrong','post_references',
              'first_post_reference','extra_references','delta_sum','selected_gain_sum')
    rows = {k:[] for k in fields}
    fallbacks = dict(planner=0,control=np.zeros(3,dtype=np.int64),candidate=np.zeros(3,dtype=np.int64))
    for meta in pop:
        parts = []
        for i in range(0,1024,128):
            path = output/'blocks'/f'{meta["label"]}_{i:04d}_{i+127:04d}.npz'
            with np.load(path,allow_pickle=False) as data:
                check('aggregation','complete indices',np.array_equal(data['indices'],np.arange(i,i+128)))
                parts.append({k:data[k] for k in fields})
                fallbacks['planner'] += int(data['planner_fallback'][0])
                fallbacks['control'] += data['control_fallback']
                fallbacks['candidate'] += data['candidate_inference_fallback']
        for k in fields:
            rows[k].append(np.concatenate([d[k] for d in parts],axis=0))
    rows = {k:np.stack(v) for k,v in rows.items()}
    units = 10*rows['wrong']+rows['references']
    cost = (64+100*units.astype(np.int64))/100000
    post_units = 10*rows['post_wrong']+rows['post_references']
    lengths = np.array([max(1,101-t) for _,t in M.CONDITIONS])
    post = post_units/(10*lengths[None,None,:,None])
    gw = dict(zip(M.PROFILE_GROUPS,M.group_weights()))
    episode = {g:arm_summary(np.einsum('k,brka->bra',w,cost)) for g,w in gw.items()}
    post_groups = {g:arm_summary(np.einsum('k,brka->bra',w,post)) for g,w in gw.items() if g not in ('full','stable')}
    criteria = dict(economical_recovery=post_groups['changed']['C2_minus_always']['upper95'] < 0,
        overall_useful_function=episode['full']['C2_minus_always']['upper95'] < 0,
        value_of_future_aware_purchases=post_groups['changed']['contrasts']['C2_minus_C']['upper95'] < 0)
    conditions = {}
    for bi,meta in enumerate(pop):
        for j,(method,tau) in enumerate(M.CONDITIONS):
            arms,contrasts = {},{}
            for ai,arm in enumerate(ARMS):
                arms[arm] = dict(episode=stats(cost[bi,:,j,ai]),
                    post_change=None if method == 'stable' else stats(post[bi,:,j,ai]),
                    mean_wrong=float(rows['wrong'][bi,:,j,ai].mean()),
                    mean_references=float(rows['references'][bi,:,j,ai].mean()),
                    mean_window_cost=((10*rows['window_wrong'][bi,:,j,ai]+rows['window_references'][bi,:,j,ai])/10).mean(axis=0).tolist())
                if arm != 'C2':
                    contrasts['C2_minus_'+arm] = dict(episode=stats((units[bi,:,j,5]-units[bi,:,j,ai])/1000),
                        post_change=None if method == 'stable' else stats(post[bi,:,j,5]-post[bi,:,j,ai]))
            conditions[f'{meta["label"]}__{method}_{tau}'] = dict(arms=arms,contrasts=contrasts,
                extra_references_mean=rows['extra_references'][bi,:,j].mean(axis=0).tolist(),
                delta_sum_mean=float(rows['delta_sum'][bi,:,j].mean()),
                selected_gain_sum_mean=float(rows['selected_gain_sum'][bi,:,j].mean()),
                weight='1/54' if method == 'stable' else '1/486')
    counts = {}
    for endpoint in ('episode','post_change'):
        counts[endpoint] = {}
        for arm in ARMS[:5]:
            ds = [v['contrasts']['C2_minus_'+arm][endpoint] for v in conditions.values()
                  if v['contrasts']['C2_minus_'+arm][endpoint] is not None]
            counts[endpoint][arm] = dict(point_lower=sum(d['mean'] < 0 for d in ds),point_equal=sum(d['mean'] == 0 for d in ds),
                point_higher=sum(d['mean'] > 0 for d in ds),upper_below_zero=sum(d['upper95'] < 0 for d in ds),lower_above_zero=sum(d['lower95'] > 0 for d in ds))
    planning = {}
    for g,w in gw.items():
        extra = np.einsum('k,brkd->brd',w,rows['extra_references'])
        planning[g] = {name:stats(extra[:,:,j]) for j,name in enumerate(('extra_references','post_extra_references','extras_after_first_post_answer'))}
        for field in ('delta_sum','selected_gain_sum'):
            planning[g][field] = stats(np.einsum('k,brk->br',w,rows[field]))
    window = (10*rows['window_wrong']+rows['window_references'])/10
    recovery = {}
    for wi,tau in enumerate(M.BOUNDARIES):
        ix = [j for j,(_,t) in enumerate(M.CONDITIONS) if t == tau]
        changed = np.take(window,ix,axis=2)[...,wi].mean(axis=2)/25
        stable = window[:,:,0,:,wi]/25
        recovery[str(tau)] = dict(changed=arm_summary(changed),stable=arm_summary(stable))
    return dict(summary=dict(independent_blocks=27648,conditions=270,physical_episodes=276480,
        controller_task_steps=165888000,arms=list(ARMS),primary='C2',seed_prefix=PREFIX,
        horizon='receding current plus one next task; terminal is myopic',samples_per_base=1024,
        new_world_types=False,priors_or_prices_tuned=False,optional_stopping=False),
        criteria=criteria,complete_proposed_improvement_supported=all(criteria.values()),
        episode=episode,post_change=post_groups,conditions=conditions,condition_counts=counts,
        planning=planning,first_25_task_mean_cost=recovery,
        fallbacks={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in fallbacks.items()})


def mount_check(output):
    item = json.loads(subprocess.check_output(['findmnt','-J','-T','/mnt/bioIce1','-o','TARGET,SOURCE,FSTYPE'],text=True))['filesystems'][0]
    check('storage','external mount',item['target'] == '/mnt/bioIce1' and item['source'] == '/dev/sdc1' and item['fstype'] == 'ext4' and output.parent == ROOT)
    s = os.statvfs('/mnt/bioIce1')
    free = s.f_bavail*s.f_frsize
    check('storage','free space',free > 2_000_000_000)
    return dict(mount=item,free_bytes=free)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True,exist_ok=False)
    (output/'inputs').mkdir()
    (output/'blocks').mkdir()
    M.logline(output,'PREPARE: six-arm prospective test; one added rule; freeze before qualification or main outcomes')
    check('integrity','previous manifest',M.identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report',M.identity(SOURCE/'FEP_RECOVERY_COST_AUDIT_V1_REPORT.md')['sha256'] == REPORT_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = {r['path']:r for group in ('inputs','outputs','preserved') for r in prior[group]}
    for path in (PREVIOUS/'MANIFEST.json',SOURCE/'FEP_RECOVERY_COST_AUDIT_V1_REPORT.md'):
        preserved[str(path)] = M.identity(path)
    M.verify(list(preserved.values()))
    inputs = []
    for name in ('FEP_FUTURE_AWARE_CHECKING_V1.md','check_fep_future_aware_checking.py','qualify_fep_future_aware_checking.py'):
        inputs.append(M.identity(SOURCE/name))
        shutil.copyfile(SOURCE/name,output/'inputs'/name)
    pop = M.population()
    M.write(output/'POPULATION.json',dict(bases=pop,conditions=M.CONDITIONS,arms=ARMS,primary='C2',
        group_weights=M.group_weights().tolist(),stable_weight='1/2',changed_weight='1/2'))
    seeds = {m['label']:[str(M.seed_for(m['label'],i,PREFIX)) for i in range(1024)] for m in pop}
    old_seeds = json.loads((M.ROOT/'attempt-01/SEEDS.json').read_text())['blocks']
    new = {x for row in seeds.values() for x in row}
    old = {x for row in old_seeds.values() for x in row}
    check('seeds','distinct fresh cohort',len(new) == 27648 and not (new & old))
    M.write(output/'SEEDS.json',dict(root=20260924,main_prefix=PREFIX,rng='Python random.Random MT19937',
        python=platform.python_version(),draw_order=M.streams.__doc__,blocks=seeds,overlap_with_changing_world=0))
    inputs += [M.identity(output/'POPULATION.json'),M.identity(output/'SEEDS.json')]
    snapshots = [M.identity(p) for p in sorted((output/'inputs').iterdir())]
    check('integrity','snapshots',sorted(r['sha256'] for r in inputs[:3]) == sorted(r['sha256'] for r in snapshots))
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources','four CPUs',len(cpus) == 4)
    M.write(output/'PREPARATION.json',dict(started_utc=M.now(),inputs=inputs,source_snapshots=snapshots,
        preserved=list(preserved.values()),storage=storage,cpus=cpus,python=platform.python_version(),numpy=np.__version__))
    M.logline(output,'FROZEN: specification, both sources, population, weights and new seeds; all earlier records preserved')
    M.pin_cpus(cpus)
    import qualify_fep_future_aware_checking as Q
    qualification = Q.qualify(sys.modules[__name__],cpus)
    M.write(output/'QUALIFICATION.json',qualification)
    M.logline(output,f'QUALIFIED: {qualification["assertions"]} assertions; {qualification["wall_seconds"]:.3f}s')
    jobs = [(A.synthetic(),list(range(i*32,(i+1)*32)),'benchmark-'+PREFIX,None) for i in range(4)]
    started = perf_counter()
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(cpus,)) as pool:
        records = list(pool.map(worker,jobs))
    elapsed = perf_counter()-started
    forecast = 120+3*elapsed*(27648/128)
    M.write(output/'BENCHMARK.json',dict(wall_seconds=elapsed,forecast_seconds=forecast,
        requires_detached=forecast > 600,workers=4,synthetic_blocks=128,records=records,
        rule='120 + 3 * four-worker wall * 27648 / 128; no outcome selection'))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output,f'PREPARED: forecast {forecast:.3f}s; detached={forecast>600}; no main performance outcomes')
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
    M.write(output/'EXECUTION_STARTED.json',dict(started_utc=M.now(),pid=os.getpid(),detached=detached,
        cpus=prep['cpus'],workers=4,benchmark=M.identity(output/'BENCHMARK.json')))
    M.logline(output,'MAIN STARTED: 216 fixed chunks, 27648 fresh blocks, all 270 conditions and six arms')
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(m,list(range(i,i+128)),PREFIX,str(output)) for m in pop for i in range(0,1024,128)]
    records = []
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(prep['cpus'],)) as pool:
        for i,record in enumerate(pool.map(worker,jobs),1):
            records.append(record)
            if i % 8 == 0:
                M.logline(output,f'COMPLETED {i}/216 chunks; {record["label"]}; results durable')
    M.write(output/'WORKERS.json',records)
    results = aggregate(output,pop)
    M.write(output/'RESULTS.json',results)
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    M.verify([r['record'] for r in records])
    M.logline(output,f'COMPLETE: {perf_counter()-start:.3f}s; all fixed samples, signed outcomes and criteria retained')
    outputs = [M.identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
    M.write(output/'MANIFEST.json',dict(status='COMPLETE',started_utc=json.loads((output/'EXECUTION_STARTED.json').read_text())['started_utc'],
        finished_utc=M.now(),wall_seconds=perf_counter()-start,parent_cpu_seconds=process_time()-cpu,
        worker_cpu_seconds=sum(r['cpu_seconds'] for r in records),workers=4,cpus=prep['cpus'],
        python=platform.python_version(),numpy=np.__version__,inputs=prep['inputs'],preserved=prep['preserved'],
        outputs=outputs,summary=results['summary'],criteria=results['criteria'],checks=dict(CHECKS),identity_checks=dict(M.CHECKS)))


def launch(output):
    check('launch','prepared', (output/'BENCHMARK.json').is_file())
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
    check('scope','new FEP namespace',args.output.parent == ROOT and args.output.name.startswith('attempt-'))
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
            M.logline(args.output,f'FAILED {args.phase}; preserve attempt; no automatic rerun')
        raise


if __name__ == '__main__':
    main()
