#!/usr/bin/env python3
"""Reconstruct unchanged changing-world policies; attribute recovery costs."""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_name] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import subprocess
from time import perf_counter, process_time
import traceback

SOURCE = Path(__file__).resolve().parent
OLD_SHA = '1d53b5dd695bf941addf7c03ebb94e6c2a441cd2b84ecbca77c2b4752a691fc1'
assert sha256((SOURCE/'check_fep_changing_world.py').read_bytes()).hexdigest() == OLD_SHA
import check_fep_changing_world as M
import numpy as np

ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-recovery-cost-audit-v1')
PREVIOUS = ROOT.parent/'fep-changing-world-v1/attempt-01'
PREVIOUS_SHA = '2c7d6b493e9a042cbc56f2260739fb1bd18aa9177e01f18672e795878bd2b73c'
REPORT_SHA = '5bcaeda9c378c25a72cc925d260d9648807034807cf561fca09a8136ecc187b2'
ANCHORS = [(0, t) for t in M.BOUNDARIES]+[(i, t) for i, (_, t) in enumerate(M.CONDITIONS) if i]
ANCHOR_NAMES = [f'{M.CONDITIONS[i][0]}_{t}' for i, t in ANCHORS]
PHASES = ('before', 'first_answer', 'after', 'total')
COUNTS = ('tasks', 'wrong', 'references')
SUMS = ('conditional_cost', 'known_Q_floor', 'insufficient_checking',
        'wrong_direction', 'excess_checking', 'subjective_cost')
METRICS = ('exposure', 'wrong_cost', 'reference_cost', 'cost', 'excess_always',
           'conditional_cost', 'known_Q_floor', 'insufficient_checking',
           'wrong_direction', 'excess_checking', 'subjective_cost',
           'conditional_regret', 'realization_residual', 'risk_underestimate')
BASE_FILTER = M.Filter
CHECKS = {}


def check(group, name, condition):
    if not bool(condition):
        raise AssertionError(f'{group}: {name}')
    CHECKS[group] = CHECKS.get(group, 0)+1


class TracedFilter(BASE_FILTER):
    last = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audit_actions = np.empty((self.n, 5, 100), dtype=np.int8)
        self.audit_u = np.empty((self.n, 5, 100))
        TracedFilter.last = self

    def warning(self, y):
        result = super().warning(y)
        self.audit_actions[:, :, self.t-1] = result[0]
        self.audit_u[:, :, self.t-1] = result[3]
        return result


def phase_masks(actions, tau):
    """Actions have an arbitrary leading shape, followed by the task axis."""
    times = np.arange(1, actions.shape[-1]+1)
    end = actions.shape[-1]+1
    k = np.where((actions == 2) & (times >= tau), times, end).min(axis=-1)
    active = times >= tau
    masks = np.stack((active & (times < k[..., None]),
                      active & (times == k[..., None]),
                      active & (times > k[..., None])), axis=-2)
    check('partition', 'disjoint and exhaustive', np.array_equal(masks.sum(axis=-2),
          np.broadcast_to(active, actions.shape)))
    return k, masks


def physical_probabilities(q, warnings):
    expanded = np.broadcast_to(q, (*warnings.shape, 4))
    qy = np.take_along_axis(expanded, warnings[..., None], axis=-1)[..., 0]
    qr = np.take_along_axis(expanded, (warnings ^ 3)[..., None], axis=-1)[..., 0]
    check('physical', 'positive warning probabilities', np.all(qy+qr > 0))
    return qr/(qy+qr)


def task_terms(actions, u, warnings, truth, q):
    """Truth and Q are external scores only; nothing here calls a learner."""
    p = physical_probabilities(q, warnings)[..., None, :]
    ask = actions == 2
    r = np.where(actions == 0, p, 1-p)
    best = np.minimum(p, 1-p)
    floor = np.broadcast_to(np.minimum(best, .1), actions.shape)
    physical = np.where(ask, .1, r)
    posterior = np.where((warnings[..., None, :] & 2) != 0, 1-u, u)
    subjective = np.where(ask, .1, np.where(actions == 0, posterior, 1-posterior))
    insufficient = np.where(ask, 0., np.maximum(best-.1, 0.))
    direction = np.where(ask, 0., r-best)
    excess = np.where(ask, np.maximum(.1-best, 0.), 0.)
    wrong = (actions != truth[..., None, :]) & ~ask
    counts = np.stack((np.ones_like(ask), wrong, ask), axis=-1).astype(np.int16)
    sums = np.stack((physical, floor, insufficient, direction, excess, subjective), axis=-1)
    check('risk', 'regret decomposition', np.allclose(physical-floor, insufficient+direction+excess, atol=2e-15, rtol=0))
    check('risk', 'nonnegative physical components', np.all(sums[..., 2:5] >= -2e-15))
    check('risk', 'finite traces and scores', np.isfinite(sums).all() and np.all((u >= -1e-12) & (u <= 1+1e-12)))
    return counts, sums


def physical_trace(meta, indices, prefix):
    c, w, e, bit_a, bit_b = M.streams(meta, indices, prefix)
    b = len(indices)
    errors = np.broadcast_to(e[:, None, :], (b, 10, 100)).copy()
    q = np.broadcast_to(np.array([float(F(x)) for x in meta['laws'][0]]), (10, 100, 4)).copy()
    for j, (method, tau) in enumerate(M.CONDITIONS[1:], 1):
        new = (bit_a << 1) | (e & 1) if method == 'A_loss' else (e & 2) | bit_b if method == 'B_loss' else e ^ 3
        errors[:, j, tau-1:] = new[:, tau-1:]
        q[j, tau-1:] = np.array([float(F(x)) for x in meta['laws'][{'A_loss':1, 'B_loss':2, 'reverse':3}[method]]])
    truth = np.broadcast_to(w[:, None, :], errors.shape)
    return c, errors ^ (3*truth), truth, q


def replay(meta, indices, prefix, bridge):
    start, cpu = perf_counter(), process_time()
    check('trace', 'original class before trace', M.Filter is BASE_FILTER)
    try:
        M.Filter = TracedFilter
        original, _ = M.run_batch(meta, indices, prefix)
        traced = TracedFilter.last
    finally:
        M.Filter = BASE_FILTER
        TracedFilter.last = None
    original_fingerprint = M.fingerprint(original)
    if bridge:
        path = PREVIOUS/'blocks'/f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        with np.load(path, allow_pickle=False) as saved:
            check('bridge', 'same output fields', set(saved.files) == set(original))
            for name, array in original.items():
                check('bridge', name, array.dtype == saved[name].dtype and np.array_equal(array, saved[name]))
            check('bridge', 'entire byte fingerprint', M.fingerprint({k:saved[k] for k in saved.files}) == original_fingerprint)
    b = len(indices)
    c, warnings, truth, q = physical_trace(meta, indices, prefix)
    check('trace', 'calibration exactly reconstructed', np.array_equal(c, original['calibration']))
    actions = traced.audit_actions.reshape(b, 10, 5, 100)
    u = traced.audit_u.reshape(b, 10, 5, 100)
    counts, sums = task_terms(actions, u, warnings, truth, q)
    check('trace', 'all wrong and reference counts', np.array_equal(counts[..., 1].sum(axis=-1), original['wrong'])
          and np.array_equal(counts[..., 2].sum(axis=-1), original['references']))
    pc = np.empty((b, 12, 5, 3, 3), dtype=np.int16)
    ps = np.empty((b, 12, 5, 3, 6))
    first = np.empty((b, 12, 5), dtype=np.int16)
    for j, (condition, tau) in enumerate(ANCHORS):
        first[:, j], masks = phase_masks(actions[:, condition], tau)
        pc[:, j] = np.einsum('bapt,batm->bapm', masks.astype(np.int16), counts[:, condition])
        ps[:, j] = np.einsum('bapt,batm->bapm', masks.astype(float), sums[:, condition])
        check('partition', 'integer sums across all phases', np.array_equal(pc[:, j].sum(axis=-2), counts[:, condition, :, tau-1:].sum(axis=-2)))
        check('partition', 'fixed exposure', np.all(pc[:, j, :, :, 0].sum(axis=-1) == 101-tau))
        check('partition', 'first-answer cost and timing', np.all(pc[:, j, :, 1, 1] == 0)
              and np.array_equal(pc[:, j, :, 1, 0], pc[:, j, :, 1, 2])
              and np.array_equal(pc[:, j, :, 0, 0], first[:, j]-tau))
        window_index = M.BOUNDARIES.index(tau)
        phase_loss = (10*pc[:, j, :, :, 1]+pc[:, j, :, :, 2]).sum(axis=-1)/10
        check('bridge', 'post-anchor window cost', np.allclose(phase_loss, original['window_loss'][:, condition, :, window_index:].sum(axis=-1), atol=2e-13, rtol=0))
    result = dict(indices=np.array(indices, dtype=np.int16), first_query=first,
                  phase_counts=pc, phase_sums=ps,
                  whole_units=(10*original['wrong']+original['references']).astype(np.int16))
    check('partition', 'phase regret closure', np.allclose(ps[..., 0]-ps[..., 1], ps[..., 2:5].sum(axis=-1), atol=5e-13, rtol=0))
    return result, dict(original_fingerprint=original_fingerprint, original_arrays=len(original),
        wall_seconds=perf_counter()-start, cpu_seconds=process_time()-cpu,
        checks=dict(CHECKS), cpus=sorted(os.sched_getaffinity(0)))


def worker(job):
    meta, indices, prefix, output, bridge = job
    arrays, record = replay(meta, indices, prefix, bridge)
    record.update(label=meta['label'], first=indices[0], last=indices[-1], fingerprint=M.fingerprint(arrays))
    if output:
        path = Path(output)/'blocks'/f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        record['record'] = M.identity(path)
    return record


def synthetic():
    q = tuple(F(x, 400) for x in (221, 119, 39, 21))
    a, b = q[2]+q[3], q[1]+q[3]
    laws = [q, ((1-b)/2,b/2,(1-b)/2,b/2), ((1-a)/2,(1-a)/2,a/2,a/2), tuple(reversed(q))]
    return dict(label='synthetic_audit', laws=[[str(x) for x in law] for law in laws])


def ci(values):
    values = np.asarray(values)
    n = values.shape[-1]
    if values.ndim == 1:
        mean, se = float(values.mean()), float(np.sqrt(values.var(ddof=1)/n))
    else:
        check('aggregation', 'stratified independent blocks', values.shape == (27, 1024))
        mean = float(values.mean(axis=1).mean())
        se = float(np.sqrt(values.var(axis=1, ddof=1).sum()/(27**2*n)))
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def weights():
    stable = np.array([1/3]*3+[0.]*9)
    changed = np.array([0.]*3+[1/9]*9)
    out = dict(full_anchored=(stable+changed)/2, stable=stable, changed=changed)
    for method in ('A_loss','B_loss','reverse'):
        out[method] = np.array([1/3 if M.CONDITIONS[c][0] == method else 0. for c,t in ANCHORS])
    for tau in M.BOUNDARIES:
        out[f'T{tau}'] = np.array([1/3 if c and t == tau else 0. for c,t in ANCHORS])
        out[f'stable_T{tau}'] = np.array([1. if not c and t == tau else 0. for c,t in ANCHORS])
    for name, row in out.items():
        check('aggregation', 'normalized '+name, abs(row.sum()-1) < 2e-15)
    return out


def qualify(cpus):
    start = perf_counter()
    # Independent scalar event assignment, including a purchase on the anchor,
    # before it, at the last task, multiple purchases and no purchase.
    for tau in (1,2,4):
        for pattern in range(16):
            a = np.array([2 if pattern & (1 << t) else 0 for t in range(4)])
            k, mask = phase_masks(a, tau)
            expected_k = next((t for t in range(tau,5) if a[t-1] == 2),5)
            expected = np.zeros((3,4), dtype=bool)
            for t in range(tau,5):
                expected[0 if t < expected_k else 1 if t == expected_k else 2,t-1] = True
            check('qualification', 'scalar event partition', k == expected_k and np.array_equal(mask, expected))
    # Exact rational known-law probabilities and action regret, independently
    # enumerated over target/error pairs for all warnings and all actions.
    for q in (tuple(F(x,20) for x in (14,2,1,3)), (F(1,4),)*4,
              (F(1,20),F(1,20),F(1,20),F(17,20)),
              (F(9,20),F(9,20),F(1,20),F(1,20))):
        for y in range(4):
            den = sum(q[e]/2 for w in (0,1) for e in range(4) if (e ^ (3*w)) == y)
            p = sum(q[e]/2 for e in range(4) if (e ^ 3) == y)/den
            for action in range(3):
                for target in (0,1):
                    a = np.array([[[action]]])
                    c,s = task_terms(a, np.array([[[.3]]]), np.array([[y]]),
                                     np.array([[target]]), np.array([[[float(x) for x in q]]]))
                    r = F(1,10) if action == 2 else p if action == 0 else 1-p
                    f = min(p,1-p,F(1,10))
                    check('qualification', 'rational physical cost and floor', abs(s[0,0,0,0]-float(r)) < 2e-15 and abs(s[0,0,0,1]-float(f)) < 2e-15)
                    check('qualification', 'rational regret and signed residual', abs(s[0,0,0,2:5].sum()-float(r-f)) < 2e-15
                          and c[0,0,0,1] == (action != 2 and action != target))
    # Exact ties, reports, labels and filtering were qualified in the source.
    # Here prove that the instrumentation leaves every output unchanged.
    meta, indices, prefix = synthetic(), list(range(8)), 'qualification-fep-recovery-cost-audit-v1'
    original, _ = M.run_batch(meta, indices, prefix)
    arrays, record = replay(meta, indices, prefix, False)
    check('qualification', 'instrumented versus original byte equality', M.fingerprint(original) == record['original_fingerprint'])
    check('qualification', 'trace cleaned up', M.Filter is BASE_FILTER and TracedFilter.last is None)
    # Coupled-arm uncertainty must be computed on differences, not independent
    # arms. A constant difference has zero SE despite varying arm outcomes.
    x = np.arange(1024, dtype=float)[None,:]+np.arange(27)[:,None]
    check('qualification', 'paired uncertainty', ci((x+2)-x)['mc_se'] == 0 and ci((x+2)-x)['mean'] == 2)
    check('qualification', 'stratified uncertainty formula', abs(ci(x)['mc_se']-np.sqrt(np.var(np.arange(1024),ddof=1)/(27*1024))) < 1e-14)
    jobs = [(meta, list(range(i*2,i*2+2)), prefix, None, False) for i in range(4)]
    one = [worker(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        four = list(pool.map(worker,jobs))
    for a,b in zip(one,four):
        check('qualification', 'one/four worker equality', a['fingerprint'] == b['fingerprint'] and a['original_fingerprint'] == b['original_fingerprint'])
    weights()
    return dict(status='PASS', checks=dict(CHECKS), assertions=sum(CHECKS.values()),
                wall_seconds=perf_counter()-start, synthetic_only=True,
                policy_qualification='unchanged source, retained 81005-assertion record',
                original_arrays=len(original), one_four_worker_chunks=4)


def metric_arrays(counts, sums):
    # Inputs have (..., phase, metric) with raw phase sums. Include the sum
    # across phases as an additional endpoint before fixed-length division.
    c = np.concatenate((counts, counts.sum(axis=-2,keepdims=True)),axis=-2)
    s = np.concatenate((sums, sums.sum(axis=-2,keepdims=True)),axis=-2)
    length = np.array([101-t for _,t in ANCHORS])[None,None,:,None,None]
    exposure, wrong, references = (c[...,i]/length for i in range(3))
    yield 'exposure', exposure
    yield 'wrong_cost', wrong
    yield 'reference_cost', references/10
    cost = wrong+references/10
    yield 'cost', cost
    yield 'excess_always', cost-.1*exposure
    for i,name in enumerate(SUMS):
        yield name, s[...,i]/length
    yield 'conditional_regret', s[...,2:5].sum(axis=-1)/length
    yield 'realization_residual', cost-s[...,0]/length
    yield 'risk_underestimate', (s[...,0]-s[...,5])/length


def aggregate(output, pop):
    fields = ('phase_counts','phase_sums','first_query','whole_units')
    rows = {k:[] for k in fields}
    for meta in pop:
        chunks = []
        for i in range(0,1024,128):
            path = output/'blocks'/f'{meta["label"]}_{i:04d}_{i+127:04d}.npz'
            with np.load(path,allow_pickle=False) as d:
                check('aggregation','complete indices',np.array_equal(d['indices'],np.arange(i,i+128)))
                chunks.append({k:d[k] for k in fields})
        for k in fields:
            rows[k].append(np.concatenate([c[k] for c in chunks],axis=0))
    rows = {k:np.stack(v) for k,v in rows.items()}
    c,s = rows['phase_counts'], rows['phase_sums']
    groups = {g:dict(arms={a:{p:{} for p in PHASES} for a in M.ARMS},
                         contrasts={f'C_minus_{a}':{p:{} for p in PHASES} for a in ('F','S','R','C-Y')},
                         query={a:{} for a in M.ARMS}) for g in weights()}
    condition_rows = {f'{meta["label"]}__{anchor}':dict(base=meta['label'],anchor=anchor,
        original_condition=M.CONDITIONS[ANCHORS[j][0]],analysis_tau=ANCHORS[j][1],
        arms={a:{p:{} for p in PHASES} for a in M.ARMS},query={a:{} for a in M.ARMS})
        for meta in pop for j,anchor in enumerate(ANCHOR_NAMES)}
    for metric, values in metric_arrays(c,s):
        for g,w in weights().items():
            v = np.einsum('k,brkap->brap',w,values)
            for a,arm in enumerate(M.ARMS):
                for p,phase in enumerate(PHASES):
                    groups[g]['arms'][arm][phase][metric] = ci(v[:,:,a,p])
                    if arm != 'C':
                        groups[g]['contrasts']['C_minus_'+arm][phase][metric] = ci(v[:,:,2,p]-v[:,:,a,p])
        for bi,meta in enumerate(pop):
            for j,anchor in enumerate(ANCHOR_NAMES):
                row = condition_rows[f'{meta["label"]}__{anchor}']
                for a,arm in enumerate(M.ARMS):
                    for p,phase in enumerate(PHASES):
                        row['arms'][arm][phase][metric] = ci(values[bi,:,j,a,p])
    query_values = dict(purchase_probability=(rows['first_query'] < 101).astype(float),
                        waiting_tasks=c[:,:,:,:,0,0].astype(float))
    for name,values in query_values.items():
        for g,w in weights().items():
            v = np.einsum('k,brka->bra',w,values)
            for a,arm in enumerate(M.ARMS):
                groups[g]['query'][arm][name] = ci(v[:,:,a])
        for bi,meta in enumerate(pop):
            for j,anchor in enumerate(ANCHOR_NAMES):
                for a,arm in enumerate(M.ARMS):
                    condition_rows[f'{meta["label"]}__{anchor}']['query'][arm][name] = ci(values[bi,:,j,a])
    prior = json.loads((PREVIOUS/'RESULTS.json').read_text())
    whole = (64+100*rows['whole_units'].astype(np.int64))/100000
    old_means = {}
    for g,w in zip(M.PROFILE_GROUPS,M.group_weights()):
        v = np.einsum('k,brka->bra',w,whole)
        old_means[g] = {a:ci(v[:,:,j]) for j,a in enumerate(M.ARMS)}
        for arm in M.ARMS:
            for field in ('mean','mc_se','lower95','upper95'):
                check('bridge','original endpoint '+g+' '+arm+' '+field,
                      abs(old_means[g][arm][field]-prior['means'][g][arm][field]) < 2e-14)
    check('bridge','post-change cost unchanged',abs(groups['changed']['arms']['C']['total']['cost']['mean']-.11319731652949247) < 2e-14)
    check('bridge','post-change SE unchanged',abs(groups['changed']['arms']['C']['total']['cost']['mc_se']-(.11350840839818403-.11288622466080091)/3.92) < 2e-14)
    changed = np.einsum('k,brka->bra',M.group_weights()[2],whole)
    full = np.einsum('k,brka->bra',M.group_weights()[0],whole)
    criteria = dict(changed_C_below_F=ci(changed[:,:,2]-changed[:,:,0])['upper95'] < 0,
                    full_C_below_always_reference=ci(full[:,:,2]-.1)['upper95'] < 0)
    check('bridge','original criteria unchanged',criteria == prior['criteria'])
    return dict(summary=dict(independent_blocks=27648,original_physical_conditions=270,
        analysis_rows=324,original_arms=list(M.ARMS),new_samples=0,new_policies=0,
        interpretation='retrospective explanatory replay; endogenous query times; no causal forced-query contrast',
        fixed_denominator='101 minus anchor; stable anchors averaged within block',
        phases=list(PHASES),count_fields=list(COUNTS),sum_fields=list(SUMS)),
        original_criteria=criteria,original_means=old_means,groups=groups,conditions=condition_rows)


def mount_check(output):
    item = json.loads(subprocess.check_output(['findmnt','-J','-T','/mnt/bioIce1','-o','TARGET,SOURCE,FSTYPE'],text=True))['filesystems'][0]
    check('storage','external FEP namespace',item['target'] == '/mnt/bioIce1' and item['source'] == '/dev/sdc1'
          and item['fstype'] == 'ext4' and output.parent == ROOT)
    stat = os.statvfs('/mnt/bioIce1')
    free = stat.f_bavail*stat.f_frsize
    check('storage','adequate free space',free > 2_000_000_000)
    return dict(mount=item,free_bytes=free)


def prepare(output):
    start = perf_counter()
    storage = mount_check(output)
    output.mkdir(parents=True,exist_ok=False)
    (output/'inputs').mkdir()
    (output/'blocks').mkdir()
    M.logline(output,'PREPARE: explanatory replay; no new policy, sample or attribution outcomes')
    check('integrity','original manifest',M.identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','original report',M.identity(SOURCE/'FEP_CHANGING_WORLD_V1_REPORT.md')['sha256'] == REPORT_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = {r['path']:r for group in ('inputs','outputs','preserved') for r in old[group]}
    for path in (PREVIOUS/'MANIFEST.json',SOURCE/'FEP_CHANGING_WORLD_V1_REPORT.md'):
        preserved[str(path)] = M.identity(path)
    M.verify(list(preserved.values()))
    inputs = [M.identity(SOURCE/name) for name in ('FEP_RECOVERY_COST_AUDIT_V1.md','check_fep_recovery_cost_audit.py')]
    for record in inputs:
        shutil.copyfile(record['path'],output/'inputs'/Path(record['path']).name)
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources','four available CPUs',len(cpus) == 4)
    snapshots = [M.identity(p) for p in sorted((output/'inputs').iterdir())]
    check('integrity','source snapshots',sorted(r['sha256'] for r in inputs) == sorted(r['sha256'] for r in snapshots))
    M.write(output/'PREPARATION.json',dict(started_utc=M.now(),inputs=inputs,preserved=list(preserved.values()),
        source_snapshots=snapshots,cpus=cpus,storage=storage,python=platform.python_version(),numpy=np.__version__,
        source_manifest=M.identity(PREVIOUS/'MANIFEST.json'),source_seeds=M.identity(PREVIOUS/'SEEDS.json'),
        source_population=M.identity(PREVIOUS/'POPULATION.json'),new_seeds=False,source_prefix='fep-changing-world-v1',
        anchors=ANCHORS,anchor_names=ANCHOR_NAMES,phases=PHASES,counts=COUNTS,sums=SUMS))
    M.logline(output,'FROZEN: audit design, wrapper, original source/seed/population identities and inherited records')
    M.pin_cpus(cpus)
    qualification = qualify(cpus)
    M.write(output/'QUALIFICATION.json',qualification)
    M.logline(output,f'QUALIFIED: {qualification["assertions"]} assertions; {qualification["wall_seconds"]:.3f}s')
    jobs = [(synthetic(),list(range(i*32,(i+1)*32)),'benchmark-fep-recovery-cost-audit-v1',None,False) for i in range(4)]
    clock = perf_counter()
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(cpus,)) as pool:
        records = list(pool.map(worker,jobs))
    elapsed = perf_counter()-clock
    forecast = 120+3*elapsed*(27648/128)
    M.write(output/'BENCHMARK.json',dict(wall_seconds=elapsed,forecast_seconds=forecast,
        requires_detached=forecast>600,workers=4,synthetic_blocks=128,records=records,
        rule='120 + 3 * four-worker wall * 27648 / 128; no outcome selection'))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output,f'PREPARED: forecast {forecast:.3f}s; detached={forecast>600}; wall {perf_counter()-start:.3f}s')
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
    M.logline(output,'AUDIT STARTED: 216 unchanged original chunks, four CPUs; each original array must match')
    pop = json.loads((PREVIOUS/'POPULATION.json').read_text())['bases']
    jobs = [(m,list(range(i,i+128)),'fep-changing-world-v1',str(output),True) for m in pop for i in range(0,1024,128)]
    records = []
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(prep['cpus'],)) as pool:
        for i,record in enumerate(pool.map(worker,jobs),1):
            records.append(record)
            if i % 8 == 0:
                M.logline(output,f'REPLAYED AND BRIDGED {i}/216 chunks; {record["label"]}')
    M.write(output/'WORKERS.json',records)
    M.logline(output,'REPLAY COMPLETE: original arrays identical; aggregate all conditions, controls and signed outcomes')
    results = aggregate(output,pop)
    M.write(output/'RESULTS.json',results)
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    M.verify([r['record'] for r in records])
    M.logline(output,f'COMPLETE: {perf_counter()-start:.3f}s; all original endpoints preserved; no new samples')
    outputs = [M.identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
    M.write(output/'MANIFEST.json',dict(status='COMPLETE',started_utc=json.loads((output/'EXECUTION_STARTED.json').read_text())['started_utc'],
        finished_utc=M.now(),wall_seconds=perf_counter()-start,parent_cpu_seconds=process_time()-cpu,
        worker_cpu_seconds=sum(r['cpu_seconds'] for r in records),workers=4,cpus=prep['cpus'],
        python=platform.python_version(),numpy=np.__version__,inputs=prep['inputs'],preserved=prep['preserved'],
        outputs=outputs,summary=results['summary'],checks=dict(CHECKS),identity_checks=dict(M.CHECKS)))


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
    check('scope','new audit namespace',args.output.parent == ROOT and args.output.name.startswith('attempt-'))
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
            M.logline(args.output,f'FAILED {args.phase}; retain attempt; no automatic rerun')
        raise


if __name__ == '__main__':
    main()
