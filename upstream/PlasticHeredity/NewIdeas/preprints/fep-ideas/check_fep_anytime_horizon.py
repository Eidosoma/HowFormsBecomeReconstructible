#!/usr/bin/env python3
"""Frozen horizon comparison using the unchanged anytime filter and controls."""
import os
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_name]='1'
import sys
sys.dont_write_bytecode=True
import argparse
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import subprocess
from time import perf_counter,process_time
import traceback

SOURCE=Path(__file__).resolve().parent
EXPECTED={
    'check_fep_anytime_change.py':'a6997b617a4f100f73cdedc45ebd2eecf4471d809e878a445793e8049ac70708',
    'qualify_fep_anytime_change.py':'31cbcfa97e43d7ef50ddfd0c52d6a3217606871d5a8c37b2dfd28c41a74e102a',
    'FEP_ANYTIME_CHANGE_V1.md':'aae315188798d6e34f153e73b411cced5646f40609dda8b29b1c67edea4e7f18',
    'FEP_ANYTIME_CHANGE_V1_REPORT.md':'c83592ed731b91ca1bda3c0ff1df2faa6f235bbc2cf3675736158c2eab5afa9e',
    'FEP_ANYTIME_CHANGE_V1_CHECKPOINT.md':'73edc4bd13c94a1f2528a68bf34385d30eca695b380baadbe606789adeefc9a6',
    'readback_fep_anytime_change.py':'ddbe3db3c6c4b75bb28207edc45f36473d03e326317d2e18bf08202a0f42221d',
    'FEP_ANYTIME_CHANGE_V1_CORRECTION.md':'06cefa23c52fa55086c0cd5074009122fbe9728fbe2ff9bc8284981e0d631446',
    'verify_fep_anytime_launch.py':'066f4953d8a86e217391dc31657c14d0483b7a5daa7486e15d8acee627f66803',
}
for _name,_digest in EXPECTED.items():
    assert sha256((SOURCE/_name).read_bytes()).hexdigest()==_digest,_name
import check_fep_anytime_change as A
import numpy as np
U,S,M,B,T=A.U,A.S,A.M,A.B,A.T
Filter=A.Filter
ci,stats_int=A.ci,A.stats_int
CONDITIONS,FAMILIES,UNEXPECTED,WINDOWS=A.CONDITIONS,A.FAMILIES,A.UNEXPECTED,A.WINDOWS
PHASES,SUMS=A.PHASES,A.SUMS
POST_SCALE,POST_DEN=A.POST_SCALE,A.POST_DEN
coefficients,panels=A.coefficients,A.panels
BOUNDARIES=A.BOUNDARIES
ARMS=(*A.ARMS,'CT1-anytime','CT4-anytime')
HORIZONS={'CT1-anytime':1,'CT3-anytime':3,'CT4-anytime':4}
PRIMARY,PRIMARY_INDEX='CT4-anytime',11
CONTRASTS=[(PRIMARY,arm) for arm in ARMS if arm!=PRIMARY]+[('CT3-anytime','CT1-anytime')]
ROOT=Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-horizon-v1')
PREVIOUS=A.ROOT/'attempt-02'
PREVIOUS_SHA='ffef707794cc6f4f4149de2f09d11f368b23d4d48ae52ce4fe3468966b1b2573'
PREFIX='fep-anytime-horizon-v1'
FIELDS=(*A.FIELDS,'horizon_alarm','horizon_episode_sums')
FALLBACKS=(*A.FALLBACKS,'horizon_fallback')
BLOCKS=256
TOTAL_BLOCKS=27*BLOCKS
CHUNK=8
MAX_FORECAST=14*86400
CHECKS={}

def check(group,name,ok):
    if not bool(ok):raise AssertionError(group+': '+name)
    CHECKS[group]=CHECKS.get(group,0)+1

def new_batch(meta, indices, prefix, horizon, boundaries=BOUNDARIES):
    """Only the new learner; physical labels/laws stay in this evaluator."""
    check('horizon', 'predeclared depth', horizon in (1,3,4))
    b, nc = len(indices), len(CONDITIONS)
    n = b*nc
    cal, warnings, truth, laws = U.physical_trace(meta, indices, prefix)
    y, target = warnings.reshape(n, 100), truth.reshape(n, 100)
    f = Filter(np.repeat(cal, nc, axis=0), boundaries)
    wrong = np.zeros(n, dtype=np.int16)
    refs, pw, pr = (np.zeros_like(wrong) for _ in range(3))
    ww, wr = (np.zeros((n, len(WINDOWS)), dtype=np.int16) for _ in range(2))
    first = np.full(n, 101, dtype=np.int16)
    tau = np.tile([t for _, t in CONDITIONS], b)
    extras = np.zeros((n, 3), dtype=np.int16)
    values = np.zeros((n, 2))
    pc = np.zeros((n, 3, 3), dtype=np.int16)
    ps = np.zeros((n, 3, 6))
    diagnosis = np.zeros((n, 4, 4))
    alarm = np.zeros((n, 3))  # count above half, first crossing, summed mass
    alarm[:, 1] = 101
    episode_sums = np.zeros((n, 6))
    for t in range(1, 101):
        f.start(t)
        yy = y[:, t-1]
        u = f.warning(yy)
        action, delta, gain, extra = f.choose(steps=horizon)
        ask = action == 2
        error = (action != target[:, t-1]) & ~ask
        affected = t >= tau
        extras[:, 0] += extra
        extras[:, 1] += extra & affected
        extras[:, 2] += extra & affected & (first < t)
        values += np.column_stack((delta, gain))
        first = np.where(ask & affected & (first == 101), t, first)
        wrong += error; refs += ask
        pw += error & affected; pr += ask & affected
        for wi, begin in enumerate(WINDOWS):
            if begin <= t < min(begin+25, 101):
                ww[:, wi] += error; wr[:, wi] += ask
        q = np.tile(laws[:, t-1], (b, 1))
        p1 = q[np.arange(n), yy ^ 3]/(q[np.arange(n), yy]+q[np.arange(n), yy ^ 3])
        risk = np.where(action == 0, p1, 1-p1)
        best = np.minimum(p1, 1-p1)
        subjective_p1 = np.where(yy >> 1, 1-u, u)
        sums = np.stack((np.where(ask, .1, risk), np.minimum(best, .1),
            np.where(ask, 0, np.maximum(best-.1, 0)), np.where(ask, 0, risk-best),
            np.where(ask, np.maximum(.1-best, 0), 0),
            np.where(ask, .1, np.where(action == 0, subjective_p1, 1-subjective_p1))), axis=-1)
        check('accounting', 'new task regret closure', np.allclose(sums[:,0]-sums[:,1], sums[:,2:5].sum(axis=-1), atol=2e-15, rtol=0))
        episode_sums += sums
        phase = np.where(first < t, 2, np.where(first == t, 1, 0))
        c = np.column_stack((np.ones(n, dtype=np.int16), error, ask))
        for j in range(3):
            selected = affected & (phase == j)
            pc[:, j] += c*selected[:, None]
            ps[:, j] += sums*selected[:, None]
        f.retain(np.where(ask, target[:, t-1], -1))
        d = f.diagnosis()
        changed = d[:, 1:].sum(axis=1)
        alarm[:, 0] += changed > .5
        alarm[:, 1] = np.where((changed > .5) & (alarm[:, 1] == 101), t, alarm[:, 1])
        alarm[:, 2] += changed
        if t in (25, 50, 75, 100):
            diagnosis[:, t//25-1] = d
        if t == 100:
            check('terminal', 'new final information value zero', np.all(delta == 0))
    out = dict(wrong=wrong, references=refs, post_wrong=pw, post_references=pr,
        window_wrong=ww, window_references=wr, first_post_reference=first,
        candidate_extra_references=extras, candidate_values=values,
        phase_counts=pc, phase_sums=ps, diagnosis=diagnosis)
    out = {k: v.reshape((b, nc, 1)+v.shape[1:]) for k, v in out.items()}
    out.update(anytime_alarm=alarm.reshape(b, nc, 3), anytime_episode_sums=episode_sums.reshape(b, nc, 6),
               anytime_fallback=np.array([f.fallback], dtype=np.int64))
    check('accounting', 'new phase errors', np.array_equal(pc[...,1].sum(axis=-1), pw))
    check('accounting', 'new phase references', np.array_equal(pc[...,2].sum(axis=-1), pr))
    check('accounting', 'new phase exposure', np.array_equal(pc[...,0].sum(axis=-1), 101-tau))
    check('accounting', 'new diagnosis normalized', np.allclose(diagnosis.sum(axis=-1), 1, atol=2*f.nh*np.finfo(float).eps, rtol=0))
    check('accounting', 'new window bounds', np.all(ww+wr <= [min(25,101-t) for t in WINDOWS]))
    check('accounting', 'new total bounds', np.all(wrong+refs <= 100))
    for j, (_, t) in enumerate(CONDITIONS[1:], 1):
        indices_ = [wi for wi, start in enumerate(WINDOWS) if start >= t and start in (M.BOUNDARIES if t in M.BOUNDARIES else UNEXPECTED)]
        for k, window in (('post_wrong','window_wrong'), ('post_references','window_references')):
            check('accounting', 'new post/window closure', np.array_equal(out[k][:,j], np.take(out[window][:,j], indices_, axis=-1).sum(axis=-1)))
    return out


def run_batch(meta,indices,prefix):
    start,cpu=perf_counter(),process_time()
    arrays,old_record=A.run_batch(meta,indices,prefix)
    added=[new_batch(meta,indices,prefix,h) for h in (1,4)]
    for key in U.FIELDS:
        arrays[key]=np.concatenate([arrays[key]]+[x[key] for x in added],axis=2)
    arrays['horizon_alarm']=np.stack([x['anytime_alarm'] for x in added],axis=2)
    arrays['horizon_episode_sums']=np.stack([x['anytime_episode_sums'] for x in added],axis=2)
    arrays['horizon_fallback']=np.concatenate([x['anytime_fallback'] for x in added])
    return arrays,dict(wall_seconds=perf_counter()-start,cpu_seconds=process_time()-cpu,
        old_policy_wall_seconds=old_record['wall_seconds'],cpus=sorted(os.sched_getaffinity(0)),checks=dict(CHECKS))

def worker(job):
    meta, indices, prefix, output = job
    arrays, record = run_batch(meta, indices, prefix)
    record.update(label=meta['label'], first=indices[0], last=indices[-1], fingerprint=M.fingerprint(arrays))
    if output:
        path = Path(output)/'blocks'/f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        record['record'] = M.identity(path)
    return record


def arm_summary(num,den,offset=0.):
    return dict(arms={arm:stats_int(num[...,i],den,offset) for i,arm in enumerate(ARMS)},
        contrasts={a+'_minus_'+b:stats_int(num[...,ARMS.index(a)]-num[...,ARMS.index(b)],den) for a,b in CONTRASTS},
        against_always={a:stats_int(num[...,ARMS.index(a)],den,offset-.1) for a in HORIZONS})

def verdicts(result,schedule='unexpected'):
    post=result['post_change'][schedule+'_core_changed']
    full=result['episode'][schedule+'_core_full']
    key=PRIMARY+'_minus_CT3-anytime'
    return dict(economical_core_recovery=post['against_always'][PRIMARY]['upper95']<0,
        better_than_three_recovery=post['contrasts'][key]['upper95']<0,
        better_than_three_full_core=full['contrasts'][key]['upper95']<0)

def condition_signs(data,indices,left,right,endpoint):
    tally=dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
    for bi in range(data.shape[0]):
        for j in indices:
            if not j and endpoint=='post_change':continue
            d=data[bi,:,j,left]-data[bi,:,j,right]
            den=1000 if endpoint=='episode' else 10*(101-CONDITIONS[j][1])
            c=stats_int(d,den)
            for name,yes in [('point_lower',int(d.sum())<0),('point_equal',int(d.sum())==0),('point_higher',int(d.sum())>0),('upper_below_zero',c['upper95']<0),('lower_above_zero',c['lower95']>0)]:
                tally[name]+=int(yes)
    return tally

def paired_metrics(by_arm):
    names=set(next(iter(by_arm.values())))
    check('aggregation','matched diagnostic fields',all(set(v)==names for v in by_arm.values()))
    return dict(arms={a:{k:ci(x) for k,x in d.items()} for a,d in by_arm.items()},
        contrasts={a+'_minus_'+b:{k:ci(by_arm[a][k]-by_arm[b][k]) for k in sorted(names)}
            for a,b in CONTRASTS if a in by_arm and b in by_arm})

def analyze(rows, pop):
    nb, n = rows['wrong'].shape[:2]
    units = 10*rows['wrong'].astype(np.int64)+rows['references']
    post = 10*rows['post_wrong'].astype(np.int64)+rows['post_references']
    mult = np.array([0]+[POST_SCALE//(101-t) for _,t in CONDITIONS[1:]])
    episode, post_change, diagnostics, planning, posterior = {}, {}, {}, {}, {}
    pc = rows['phase_counts'].astype(np.int64)
    ps = rows['phase_sums']
    check('aggregation', 'saved phase errors', np.array_equal(pc[...,1].sum(axis=-1), rows['post_wrong'][...,6:]))
    check('aggregation', 'saved phase references', np.array_equal(pc[...,2].sum(axis=-1), rows['post_references'][...,6:]))
    check('aggregation', 'saved regret closure', np.allclose(ps[...,0]-ps[...,1], ps[...,2:5].sum(axis=-1), atol=5e-13, rtol=0))
    pc = np.concatenate((pc, pc.sum(axis=-2,keepdims=True)),axis=-2)
    ps = np.concatenate((ps, ps.sum(axis=-2,keepdims=True)),axis=-2)
    for group, co in coefficients().items():
        episode[group] = arm_summary(np.einsum('k,brka->bra',co,units),144000,.00064)
        posterior[group] = {}
        for ai, arm in enumerate(ARMS[7:]):
            weighted = np.einsum('k,brkts->brts',co/144,rows['diagnosis'][...,ai,:,:])
            posterior[group][arm] = {str(t): {name:ci(weighted[...,ti,j]) for j,name in enumerate(('no_change_yet','G','A','B'))} for ti,t in enumerate((25,50,75,100))}
        planning[group] = {}
        for ai, arm in enumerate(ARMS[7:]):
            ex = np.einsum('k,brkd->brd',co,rows['candidate_extra_references'][...,ai,:].astype(np.int64))
            val = np.einsum('k,brkd->brd',co/144,rows['candidate_values'][...,ai,:])
            planning[group][arm] = {name:stats_int(ex[...,j],144) for j,name in enumerate(('extra_checks','post_extra_checks','extras_after_first_answer'))}
            planning[group][arm].update({name:ci(val[...,j]) for j,name in enumerate(('information_value_sum','selected_gain_sum'))})
        if group == 'stable' or group.endswith('_full'):
            continue
        post_change[group] = arm_summary(np.einsum('k,brka->bra',co*mult,post),POST_DEN)
        c = np.einsum('k,brkapm->brapm',co*mult/(144*POST_SCALE),pc)
        s = np.einsum('k,brkapm->brapm',co*mult/(144*POST_SCALE),ps)
        exposure, wrong, reference = (c[...,j] for j in range(3))
        cost = wrong+.1*reference
        metrics = dict(exposure=exposure, wrong_cost=wrong, reference_cost=.1*reference,
                       cost=cost, excess_always=cost-.1*exposure)
        metrics.update({name:s[...,j] for j,name in enumerate(SUMS)})
        metrics.update(conditional_regret=s[...,2:5].sum(axis=-1), realization_residual=cost-s[...,0],
                       risk_underestimate=s[...,0]-s[...,5], available_headroom=.1*exposure-s[...,1])
        diagnostics[group] = dict(arms={}, contrasts={}, query={})
        for ai, arm in enumerate(ARMS[6:]):
            diagnostics[group]['arms'][arm] = {phase:{name:ci(v[...,ai,pi]) for name,v in metrics.items()} for pi,phase in enumerate(PHASES)}
            check('aggregation','diagnostic cost endpoint', abs(diagnostics[group]['arms'][arm]['total']['cost']['mean']-post_change[group]['arms'][arm]['mean']) < 3e-13)
            if 6+ai != PRIMARY_INDEX:
                diagnostics[group]['contrasts'][PRIMARY+'_minus_'+arm] = {phase:{name:ci(v[...,PRIMARY_INDEX-6,pi]-v[...,ai,pi]) for name,v in metrics.items()} for pi,phase in enumerate(PHASES)}
            first = rows['first_post_reference'][...,6+ai]
            wait = np.maximum(first-np.array([t for _,t in CONDITIONS])[None,None,:],0)
            diagnostics[group]['query'][arm] = dict(purchase_probability=ci(np.einsum('k,brk->br',co/144,first<101)),
                                                    waiting_tasks=ci(np.einsum('k,brk->br',co/144,wait)))
        diagnostics[group]['contrasts']['CT3-anytime_minus_CT1-anytime'] = {phase:{name:ci(v[...,3,pi]-v[...,4,pi]) for name,v in metrics.items()} for pi,phase in enumerate(PHASES)}
    conditions = {}
    for bi, meta in enumerate(pop):
        for j,(family,tau) in enumerate(CONDITIONS):
            key = f'{meta["label"]}__{family}_{tau}'
            endpoint = None if not j else arm_summary(post[bi:bi+1,:,j],10*(101-tau))
            law = meta['laws'][('stable','A_loss','B_loss','reverse','A_partial','B_partial','both_partial').index(family)]
            floor = M.floor(law)
            conditions[key] = dict(episode=arm_summary(units[bi:bi+1,:,j],1000,.00064), post_change=endpoint,
                mean_wrong=rows['wrong'][bi,:,j].mean(axis=0).tolist(), mean_references=rows['references'][bi,:,j].mean(axis=0).tolist(),
                known_Q_floor=dict(rational=str(floor),mean=float(floor),headroom=float(F(1,10)-floor)),
                panel='stable' if not j else ('core' if family in FAMILIES[:3] else 'transfer'),
                schedule='stable' if not j else ('supported' if tau in M.BOUNDARIES else 'unexpected'))
    signs={panel:{e:{arm:condition_signs(data,indices,PRIMARY_INDEX,ai,e) for ai,arm in enumerate(ARMS) if ai!=PRIMARY_INDEX}
        for e,data in (('episode',units),('post_change',post))} for panel,indices in panels().items()}
    matched_signs={panel:{e:condition_signs(data,indices,9,10,e) for e,data in (('episode',units),('post_change',post))}
        for panel,indices in panels().items()}
    windows = {}
    wunits = 10*rows['window_wrong'].astype(np.int64)+rows['window_references']
    for wi, tau in enumerate(WINDOWS):
        length = min(25, 101-tau)
        windows[str(tau)] = dict(task_count=length, stable=arm_summary(wunits[:, :, 0, :, wi], 10*length))
        for panel, families in (('core', FAMILIES[:3]), ('transfer', FAMILIES[3:])):
            chosen = [j for j, (f, t) in enumerate(CONDITIONS) if f in families and t == tau]
            windows[str(tau)][panel] = arm_summary(np.take(wunits, chosen, axis=2)[..., wi].sum(axis=2), 10*length*len(chosen))
    sensitivity = {}
    weights = coefficients()
    for panel in ('core', 'transfer'):
        sensitivity[panel] = {}
        for endpoint, data, den, ending in (('episode', units, 144000, '_full'), ('post_change', post, POST_DEN, '_changed')):
            co = weights['unexpected_'+panel+ending]-weights['supported_'+panel+ending]
            if endpoint == 'post_change':
                co = co*mult
            num = np.einsum('k,brka->bra', co, data)
            sensitivity[panel][endpoint] = {arm: stats_int(num[..., ai], den) for ai, arm in enumerate(ARMS)}
    result = dict(summary=dict(independent_blocks=nb*n, bases=nb, blocks_per_base=n, physical_conditions=nb*43,
        physical_episodes=nb*n*43, arms=list(ARMS), primary=PRIMARY, seed_prefix=PREFIX,
        learner_change_times=list(BOUNDARIES), old_learner_change_times=list(M.BOUNDARIES), unexpected_physical_times=list(UNEXPECTED),
        conditional_model='one change uniformly at tasks 1 through 100, total probability one half; weak new-rate priors',
        objective='matched one/three/four-decision task-cost planning; unchanged exact conditional VFE/Bayesian inference',
        horizons=HORIZONS, new_policies=2, tuned_after_outcomes=False, old_cohort_pooled=False),
        episode=episode, post_change=post_change, conditions=conditions, condition_counts=signs, matched_planning_condition_counts=matched_signs,
        diagnostics=diagnostics, planning=planning, posterior=posterior, early_recovery=windows,
        unexpected_minus_supported=sensitivity)
    stable={}
    for name,data in (('wrong_cost',rows['wrong'][:,:,0]/100),('purchase_cost',rows['references'][:,:,0]/1000)):
        stable[name]=dict(arms={a:ci(data[...,i]) for i,a in enumerate(ARMS)},
            contrasts={a+'_minus_'+b:ci(data[...,ARMS.index(a)]-data[...,ARMS.index(b)]) for a,b in CONTRASTS})
    stable['total_cost']=episode['stable']
    alarms={'CT3-anytime':rows['anytime_alarm'][:,:,0],
        'CT1-anytime':rows['horizon_alarm'][:,:,0,0], 'CT4-anytime':rows['horizon_alarm'][:,:,0,1]}
    stable['posterior_false_alarms']=paired_metrics({a:dict(tasks_above_half=x[...,0],
        probability_ever_above_half=(x[...,0]>0).astype(float),first_crossing_censored_at_101=x[...,1],
        mean_change_probability=x[...,2]/100) for a,x in alarms.items()})
    stable['posterior_false_alarms'].update(threshold=.5,update_stage='after available paid label; descriptive, not an action')
    episode_sums={'CT3-anytime':rows['anytime_episode_sums'][:,:,0]/100,
        'CT1-anytime':rows['horizon_episode_sums'][:,:,0,0]/100,'CT4-anytime':rows['horizon_episode_sums'][:,:,0,1]/100}
    metrics={}
    for a,x in episode_sums.items():
        ai=ARMS.index(a)
        d={name:x[...,i] for i,name in enumerate(SUMS)}
        d.update(conditional_regret=x[...,2:5].sum(axis=-1),risk_underestimate=x[...,0]-x[...,5],
            realization_residual=(10*rows['wrong'][:,:,0,ai]+rows['references'][:,:,0,ai])/1000-x[...,0])
        metrics[a]=d
    stable['anytime_evaluator']=paired_metrics(metrics)
    result['stable_costs']=stable
    result['criteria'] = verdicts(result)
    result['supported_control_criteria'] = verdicts(result, 'supported')
    result['core_lead_confirmed'] = all(result['criteria'].values())
    return result

def aggregate(output,pop):
    fields = FIELDS
    rows = {k:[] for k in fields}
    fallback_names = FALLBACKS
    fallbacks = {k:0 for k in fallback_names}
    for meta in pop:
        parts = {k:[] for k in fields}
        for first in range(0,BLOCKS,CHUNK):
            with np.load(output/'blocks'/f'{meta["label"]}_{first:04d}_{first+CHUNK-1:04d}.npz',allow_pickle=False) as saved:
                check('aggregation','chunk indices',np.array_equal(saved['indices'],np.arange(first,first+CHUNK)))
                for key in fields:
                    parts[key].append(saved[key])
                for key in fallback_names:
                    fallbacks[key] += saved[key]
        for key in fields:
            rows[key].append(np.concatenate(parts[key],axis=0))
    result = analyze({k:np.stack(v) for k,v in rows.items()},pop)
    result['fallbacks'] = {k:v.tolist() for k,v in fallbacks.items()}
    return result

def mount_check(output):
    mount = json.loads(subprocess.check_output(['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    check('storage', 'verified FEP destination', mount == dict(target='/mnt/bioIce1', source='/dev/sdc1', fstype='ext4') and output.parent == ROOT)
    stat = os.statvfs('/mnt/bioIce1')
    free = stat.f_bavail*stat.f_frsize
    check('storage', 'space available', free > 2_000_000_000)
    return dict(mount=mount, free_bytes=free)


def prepare(output):
    storage=mount_check(output)
    output.mkdir(parents=True,exist_ok=False)
    (output/'inputs').mkdir(); (output/'blocks').mkdir()
    M.logline(output,'PREPARE: fixed horizons 1/3/4, unchanged anytime model and ten controls, fresh paired seeds')
    check('integrity','completed anytime manifest',M.identity(PREVIOUS/'MANIFEST.json')['sha256']==PREVIOUS_SHA)
    prior=json.loads((PREVIOUS/'MANIFEST.json').read_text())
    check('integrity','previous study complete',prior['status']=='COMPLETE')
    preserved={r['path']:r for group in ('inputs','outputs','preserved') for r in prior[group]}
    paths=[PREVIOUS/'MANIFEST.json']+[SOURCE/name for name in EXPECTED]
    paths+=sorted((A.ROOT/'readback-2026-10-11').iterdir())
    for folder in ('attempt-01','diagnostic-01','status-checks'):
        paths+=sorted(p for p in (A.ROOT/folder).rglob('*') if p.is_file())
    for attempt in sorted(ROOT.glob('attempt-*')):
        if attempt!=output:paths+=sorted(p for p in attempt.rglob('*') if p.is_file())
    for path in paths:preserved[str(path)]=M.identity(path)
    M.verify(list(preserved.values()))
    names=('FEP_ANYTIME_HORIZON_V1.md',Path(__file__).name,'qualify_fep_anytime_horizon.py','verify_fep_anytime_horizon_launch.py')
    inputs=[]
    for name in names:
        inputs.append(M.identity(SOURCE/name)); shutil.copyfile(SOURCE/name,output/'inputs'/name)
    previous_population=json.loads((PREVIOUS/'POPULATION.json').read_text())
    pop=S.population()
    check('population','unchanged base laws',pop==previous_population['bases'])
    check('population','unchanged physical conditions',[list(x) for x in CONDITIONS]==previous_population['conditions'])
    population=dict(previous_population)
    population.update(arms=ARMS,horizons=HORIZONS,blocks_per_base=BLOCKS,primary=PRIMARY)
    M.write(output/'POPULATION.json',population)
    seeds={m['label']:[str(M.seed_for(m['label'],i,PREFIX)) for i in range(BLOCKS)] for m in pop}
    flips={m['label']:[str(M.seed_for(m['label'],i,PREFIX+'-transfer-flips')) for i in range(BLOCKS)] for m in pop}
    fresh={x for values in (seeds,flips) for row in values.values() for x in row}
    check('seeds','unique main and flip seeds',len(fresh)==2*TOTAL_BLOCKS)
    seed_sources=[PREVIOUS/'SEEDS.json',A.PREVIOUS/'SEEDS.json',U.PREVIOUS/'SEEDS.json',S.ROOT/'attempt-02/SEEDS.json']+[ROOT.parent/study/'attempt-01/SEEDS.json' for study in
        ('fep-changing-world-v1','fep-future-aware-checking-v1','fep-three-decision-checking-v1')]
    for path in seed_sources:
        old=json.loads(path.read_text())
        previous={x for group in ('blocks','flip_blocks') for row in old.get(group,{}).values() for x in row}
        check('seeds','prior separation '+str(path),not fresh.intersection(previous))
    for study_prefix in (PREFIX,A.PREFIX,U.PREFIX,'fep-weak-prior-confirmation-v1',S.PREFIX,S.T.PREFIX,S.B.PREFIX,'fep-changing-world-v1'):
        for purpose in ('qualification-','parallel-','benchmark-'):
            prefix=purpose+study_prefix
            synthetic={str(M.seed_for(S.A.synthetic()['label'],i,p)) for i in range(128) for p in (prefix,prefix+'-transfer-flips')}
            check('seeds','synthetic separation '+prefix,not fresh.intersection(synthetic))
    M.write(output/'SEEDS.json',dict(root=20260924,main_prefix=PREFIX,flip_prefix=PREFIX+'-transfer-flips',
        rng='Python random.Random MT19937',python=platform.python_version(),core_draw_order=M.streams.__doc__,
        flip_draw_order='two random() values per task; each flip iff value < 1/4',blocks=seeds,flip_blocks=flips,
        overlap_with_previous=0,selected_after_previous_results=True))
    inputs+=[M.identity(output/'POPULATION.json'),M.identity(output/'SEEDS.json')]
    snapshots=[M.identity(p) for p in sorted((output/'inputs').iterdir())]
    check('integrity','source snapshots',sorted(x['sha256'] for x in inputs[:4])==sorted(x['sha256'] for x in snapshots))
    cpus=sorted(os.sched_getaffinity(0))[:4]
    check('resources','four CPUs available',len(cpus)==4)
    M.pin_cpus(cpus)
    M.write(output/'PREPARATION.json',dict(started_utc=M.now(),inputs=inputs,source_snapshots=snapshots,
        preserved=list(preserved.values()),storage=storage,cpus=cpus,python=platform.python_version(),numpy=np.__version__,
        source_manifest=M.identity(PREVIOUS/'MANIFEST.json'),primary=PRIMARY,new_policy_implementations=2,
        horizons=HORIZONS,blocks_per_base=BLOCKS,new_seeds=True,old_cohort_pooled=False))
    M.logline(output,'FROZEN: horizons, design, sources, unchanged population, fixed sample and fresh seeds')
    from qualify_fep_anytime_horizon import qualify
    qualification=qualify(sys.modules[__name__],cpus,output)
    M.write(output/'QUALIFICATION.json',qualification)
    M.logline(output,f'QUALIFIED: {qualification["assertions"]} wrapper checks; {qualification["wall_seconds"]:.3f}s')
    M.logline(output,'BENCHMARK: four workers, eight synthetic blocks each, all twelve policies')
    jobs=[(S.extend_meta(S.A.synthetic()),list(range(i*8,(i+1)*8)),'benchmark-'+PREFIX,None) for i in range(4)]
    start=perf_counter()
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(cpus,)) as pool:
        records=list(pool.map(worker,jobs))
    elapsed=perf_counter()-start
    forecast=120+3*elapsed*TOTAL_BLOCKS/32
    M.write(output/'BENCHMARK.json',dict(wall_seconds=elapsed,forecast_seconds=forecast,requires_detached=forecast>600,
        workers=4,synthetic_blocks=32,conditions_per_block=43,arms=len(ARMS),records=records,
        rule='120 + 3 * four-worker wall * 6912 / 32; no outcome selection',maximum_forecast_seconds=MAX_FORECAST,
        within_compute_bound=forecast<=MAX_FORECAST))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output,f'PREPARED: forecast {forecast:.3f}s; bound passes={forecast<=MAX_FORECAST}; no main outcomes')

def execute(output, detached):
    start, cpu = perf_counter(), process_time()
    prep = json.loads((output/'PREPARATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    check('execution', 'frozen compute bound', bench['forecast_seconds'] <= MAX_FORECAST)
    check('execution', 'not started', not (output/'EXECUTION_STARTED.json').exists())
    check('execution', 'qualified', json.loads((output/'QUALIFICATION.json').read_text())['status'] == 'PASS')
    check('execution', 'prelaunch verified', json.loads((output/'PRELAUNCH.json').read_text())['status'] == 'PASS')
    prelaunch = json.loads((output/'PRELAUNCH.json').read_text())
    M.verify([prelaunch[k] for k in ('source','snapshot','preparation','qualification','benchmark')])
    check('execution', 'detachment rule', detached or not bench['requires_detached'])
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    mount_check(output)
    M.pin_cpus(prep['cpus'])
    M.write(output/'EXECUTION_STARTED.json', dict(started_utc=M.now(), pid=os.getpid(), detached=detached,
            workers=4, cpus=prep['cpus'], benchmark=M.identity(output/'BENCHMARK.json'), primary=PRIMARY))
    M.logline(output, 'MAIN STARTED: 864 fixed chunks, 6912 fresh blocks, 1161 conditions, ten unchanged arms plus CT1/CT4-anytime')
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(meta, list(range(i, i+CHUNK)), PREFIX, str(output)) for meta in pop for i in range(0, BLOCKS, CHUNK)]
    records = []
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(prep['cpus'],)) as pool:
        for i, record in enumerate(pool.map(worker, jobs), 1):
            records.append(record)
            if i % 32 == 0:
                M.logline(output, f'COMPLETED {i}/864 chunks; {record["label"]}')
    M.write(output/'WORKERS.json', records)
    results = aggregate(output, pop)
    M.write(output/'RESULTS.json', results)
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved']+[r['record'] for r in records])
    M.logline(output, f'COMPLETE: {perf_counter()-start:.3f}s; three frozen criteria and all signed results retained')
    outputs = [M.identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
    M.write(output/'MANIFEST.json', dict(status='COMPLETE', started_utc=json.loads((output/'EXECUTION_STARTED.json').read_text())['started_utc'],
            finished_utc=M.now(), wall_seconds=perf_counter()-start, parent_cpu_seconds=process_time()-cpu,
            worker_cpu_seconds=sum(r['cpu_seconds'] for r in records), workers=4, cpus=prep['cpus'],
            python=platform.python_version(), numpy=np.__version__, inputs=prep['inputs'], preserved=prep['preserved'], outputs=outputs,
            summary=results['summary'], criteria=results['criteria'], core_lead_confirmed=results['core_lead_confirmed'],
            checks=dict(CHECKS), shared_checks=dict(A.CHECKS), identity_checks=dict(M.CHECKS)))


def campaign(output):
    prepare(output)
    bench=json.loads((output/'BENCHMARK.json').read_text())
    if not bench['within_compute_bound']:
        M.write(output/'FEASIBILITY_STOP.json',dict(status='STOPPED_BEFORE_MAIN',utc=M.now(),
            forecast_seconds=bench['forecast_seconds'],maximum_forecast_seconds=MAX_FORECAST,
            reason='predeclared conservative runtime cap exceeded; no tuning or sample change'))
        M.logline(output,'STOPPED BEFORE MAIN: conservative forecast exceeds frozen compute bound')
        return
    with (output/'PRELAUNCH_STDOUT.log').open('xb') as log:
        subprocess.run([sys.executable,'-B',str(SOURCE/'verify_fep_anytime_horizon_launch.py'),'--output',str(output)],
            cwd=SOURCE,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    execute(output,True)

def launch_campaign(output):
    mount_check(output)
    check('launch','new attempt',not output.exists())
    ROOT.mkdir(parents=True,exist_ok=True)
    receipt_path=ROOT/(output.name+'-campaign-launch.json')
    log_path=ROOT/(output.name+'-campaign-stdout.log')
    check('launch','new campaign receipt',not receipt_path.exists() and not log_path.exists())
    cpus=sorted(os.sched_getaffinity(0))[:4]
    check('launch','four CPUs available',len(cpus)==4)
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'campaign','--output',str(output),'--detached']
    with log_path.open('xb') as log:
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True,cwd=SOURCE,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            preexec_fn=lambda:os.sched_setaffinity(0,set(cpus)))
    receipt=dict(pid=child.pid,launched_utc=M.now(),cpus=cpus,automatic_polling=False,
        stage='detached preparation; main conditional on qualification, benchmark cap and prelaunch checks',
        command=command,output=str(output),stdout=str(log_path),source=M.identity(Path(__file__).resolve()),
        design=M.identity(SOURCE/'FEP_ANYTIME_HORIZON_V1.md'),maximum_forecast_seconds=MAX_FORECAST)
    M.write(receipt_path,receipt)
    print(json.dumps(receipt))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('prepare','execute','campaign','launch-campaign'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--detached',action='store_true')
    args=parser.parse_args()
    check('scope','dedicated attempt',args.output.parent==ROOT and args.output.name.startswith('attempt-'))
    try:
        if args.phase=='campaign':check('scope','campaign detached',args.detached)
        {'prepare':lambda:prepare(args.output),'execute':lambda:execute(args.output,args.detached),
            'campaign':lambda:campaign(args.output),'launch-campaign':lambda:launch_campaign(args.output)}[args.phase]()
    except Exception:
        if args.output.is_dir():
            path=args.output/f'FAILURE_{args.phase}.json'
            if not path.exists():M.write(path,dict(phase=args.phase,utc=M.now(),traceback=traceback.format_exc(),checks=dict(CHECKS)))
            M.logline(args.output,f'FAILED {args.phase}; preserve attempt; no automatic retry')
        raise
