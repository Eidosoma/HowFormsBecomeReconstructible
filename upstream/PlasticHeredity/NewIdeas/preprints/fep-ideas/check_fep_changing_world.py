#!/usr/bin/env python3
"""Frozen changing-world v1: batched filtering and paired physical evaluation.

No external state enters the filter beyond calibration, task time, warnings
and labels explicitly delivered by the evaluator after reference purchases.
"""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_name] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
import json
from math import log, sqrt
from pathlib import Path
import platform
import random
import shutil
import subprocess
from time import perf_counter, process_time
import traceback
import numpy as np

SOURCE = Path(__file__).resolve().parent
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-changing-world-v1')
PREVIOUS = ROOT.parent/'fep-offgrid-validation-v1/attempt-01'
PREVIOUS_SHA = 'de050f89a6438dddbfbf93bb13cbac15b3e71e5aac9407790643f814c93fa124'
DESIGN_SHA = 'c5c07184dc65b47d60ddcafe12449aa6c546428358b754ce4dc4c278180dd7e0'
ARMS = ('F', 'S', 'C', 'R', 'C-Y')
BOUNDARIES = (26, 51, 76)
CONDITIONS = [('stable', 101)] + [(m, t) for m in ('A_loss', 'B_loss', 'reverse') for t in BOUNDARIES]
BLOCKS, CHUNK, HORIZON, ROOT_SEED = 1024, 128, 100, 20260924
PRIOR = np.array([1., 2., .5, 1., .5, 1.])
WEIGHTS = np.array([.5] + [1/18]*9)
PROFILE_GROUPS = ('full', 'stable', 'changed', 'A_loss', 'B_loss', 'reverse', 'T26', 'T51', 'T76')
CHECKS = {}


def check(group, name, condition):
    if not bool(condition):
        raise AssertionError(f'{group}: {name}')
    CHECKS[group] = CHECKS.get(group, 0)+1


def now():
    return datetime.now(timezone.utc).isoformat()


def identity(path):
    path = Path(path)
    h = sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1 << 20), b''):
            h.update(data)
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=h.hexdigest())


def verify(records):
    for rec in records:
        check('integrity', rec['path'], identity(rec['path']) == rec)


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def logline(output, message):
    with (output/'RUN_LOG.txt').open('a') as stream:
        stream.write(f'{now()} {message}\n')
        stream.flush()


def mount_check(output):
    mount = Path('/mnt/bioIce1')
    info = subprocess.check_output(['findmnt', '-J', '-T', str(mount), '-o', 'TARGET,SOURCE,FSTYPE'], text=True)
    item = json.loads(info)['filesystems'][0]
    check('storage', 'external FEP mount', item['target'] == str(mount) and item['source'] == '/dev/sdc1'
          and item['fstype'] == 'ext4' and output.parent == ROOT)
    stat = os.statvfs(mount)
    free = stat.f_bavail*stat.f_frsize
    check('storage', 'space before new output', free > 2_000_000_000)
    return dict(mount=item, free_bytes=free)


def pin_cpus(cpus):
    os.sched_setaffinity(0, set(cpus))


def population():
    out = []
    for ai, bi, di in product((3, 11, 19), (3, 11, 19), (-1, 0, 1)):
        a, b, d = F(ai, 40), F(bi, 40), F(di, 2)
        q11 = (1+d)*a*b if d <= 0 else (1-d)*a*b+d*min(a, b)
        q = (1-a-b+q11, b-q11, a-q11, q11)
        label = f'a{25*ai:03d}_b{25*bi:03d}_'+{-1:'neg050', 0:'zero', 1:'pos050'}[di]
        laws = [q, ((1-b)/2, b/2, (1-b)/2, b/2),
                ((1-a)/2, (1-a)/2, a/2, a/2), tuple(reversed(q))]
        out.append(dict(label=label, a=str(a), b=str(b), d=str(d),
                        laws=[[str(v) for v in x] for x in laws]))
    return out


def floor(q):
    q = tuple(map(F, q))
    return sum(min(q[i], q[3-i], (q[i]+q[3-i])/10) for i in (0, 1))


def seed_for(label, block, prefix='fep-changing-world-v1'):
    token = f'{prefix}|{ROOT_SEED}|{label}|{block}'.encode('ascii')
    return int.from_bytes(sha256(token).digest(), 'big')


def streams(meta, indices, prefix):
    """Python 3.10 random.Random MT19937, fixed draw order independent of policy.

    Per block: 64 random() categorical calibration draws; then 100 tuples
    (getrandbits(1) target, random() categorical error, getrandbits(1) A,
    getrandbits(1) B). Categorical cells have ascending 00/01/10/11 order.
    """
    q = list(map(float, map(F, meta['laws'][0])))
    cumulative = np.cumsum(q)
    n = len(indices)
    counts = np.zeros((n, 4), dtype=np.int16)
    worlds = np.empty((n, HORIZON), dtype=np.int8)
    errors = np.empty_like(worlds)
    bit_a = np.empty_like(worlds)
    bit_b = np.empty_like(worlds)
    def draw(rng):
        u = rng.random()
        return 0 if u < cumulative[0] else 1 if u < cumulative[1] else 2 if u < cumulative[2] else 3
    for row, block in enumerate(indices):
        rng = random.Random(seed_for(meta['label'], block, prefix))
        for _ in range(64):
            counts[row, draw(rng)] += 1
        for t in range(HORIZON):
            worlds[row, t] = rng.getrandbits(1)
            errors[row, t] = draw(rng)
            bit_a[row, t] = rng.getrandbits(1)
            bit_b[row, t] = rng.getrandbits(1)
    return counts, worlds, errors, bit_a, bit_b


def initial_parameters(counts):
    c = np.asarray(counts)
    return np.stack([c[:, 1]+c[:, 2]+1, c.sum(axis=1)+2,
                     c[:, 3]+.5, c[:, 0]+c[:, 3]+1,
                     c[:, 2]+.5, c[:, 1]+c[:, 2]+1], axis=-1)


def rational_state(counts, observations, arm='C', boundaries=BOUNDARIES, priors=None, current=None):
    """Independent rational sequential replay of accessible observations only.

    observations are (warning, retained target or None), completed tasks.
    current, if supplied, is the next warning without a label.
    """
    c = list(map(int, counts))
    init = [F(c[1]+c[2]+1), F(sum(c)+2), F(2*c[3]+1, 2), F(c[0]+c[3]+1),
            F(2*c[2]+1, 2), F(c[1]+c[2]+1)]
    fresh = [F(1), F(2), F(1, 2), F(1), F(1, 2), F(1)]
    params = [list(init) for _ in range(4)]
    weights = list(priors or (F(1, 2), F(1, 6), F(1, 6), F(1, 6))) if arm in ('C', 'C-Y') else [F(1), F(0), F(0), F(0)]
    evidence = F(1)
    seq = list(observations)+([] if current is None else [(int(current), None)])
    orientation = None
    for t, (y, w) in enumerate(seq, 1):
        if t in boundaries:
            if arm in ('C', 'C-Y'):
                params[boundaries.index(t)+1] = list(fresh)
            elif arm == 'R':
                params = [list(fresh) for _ in range(4)]
        z = (y >> 1) ^ (y & 1)
        likelihoods = [(p[0]/p[1] if z else 1-p[0]/p[1])/2 for p in params]
        normalizer = sum(a*b for a, b in zip(weights, likelihoods))
        evidence *= normalizer
        weights = [a*b/normalizer for a, b in zip(weights, likelihoods)]
        orientation = sum(weights[j]*params[j][2+2*z]/params[j][3+2*z] for j in range(4))
        if arm != 'F':
            for p in params:
                p[0] += z
                p[1] += 1
        if w is not None and arm not in ('F', 'C-Y'):
            x = (y >> 1) ^ w
            likelihoods = [p[2+2*z]/p[3+2*z] if x else 1-p[2+2*z]/p[3+2*z] for p in params]
            normalizer = sum(a*b for a, b in zip(weights, likelihoods))
            evidence *= normalizer
            weights = [a*b/normalizer for a, b in zip(weights, likelihoods)]
            for p in params:
                p[2+2*z] += x
                p[3+2*z] += 1
    return weights, params, orientation, evidence


class Filter:
    """Five policies batched over observable rows; no world/Q/change inputs."""
    def __init__(self, counts, boundaries=BOUNDARIES, priors=None):
        self.counts = np.asarray(counts, dtype=np.int16).copy()
        self.n = len(counts)
        self.boundaries = tuple(boundaries)
        self.priors = tuple(priors or (F(1, 2), F(1, 6), F(1, 6), F(1, 6)))
        self.p = np.broadcast_to(initial_parameters(counts)[:, None, None, :], (self.n, 5, 4, 6)).copy()
        self.logw = np.full((self.n, 5, 4), -np.inf)
        self.logw[:, :, 0] = 0
        for a in (2, 4):
            self.logw[:, a] = np.array([log(float(v)) if v else -np.inf for v in self.priors])
        self.ys = np.zeros((self.n, HORIZON), dtype=np.int8)
        self.labels = np.full((self.n, 5, HORIZON), -1, dtype=np.int8)
        self.t = 0
        self.fallback = np.zeros(3, dtype=np.int64)  # common action / action replay / diagnostic replay
        self.above_half = np.zeros((self.n, 2), dtype=bool)

    def start(self, t):
        self.t = t
        if t in self.boundaries:
            j = self.boundaries.index(t)+1
            self.p[:, 2, j] = PRIOR
            self.p[:, 4, j] = PRIOR
            self.p[:, 3] = PRIOR

    def probability_changed(self, retained=False):
        mask = np.array([False]+[t <= self.t for t in self.boundaries])
        probability = np.exp(self.logw[:, (2, 4), :])[..., mask].sum(axis=-1)
        self.above_half = probability > .5
        for row, j in np.argwhere(np.abs(probability-.5) <= 1e-12):
            arm = (2, 4)[j]
            end = self.t if retained else self.t-1
            hist = [(int(self.ys[row, k]), None if self.labels[row, arm, k] < 0 else int(self.labels[row, arm, k]))
                    for k in range(end)]
            w = rational_state(self.counts[row], hist, ARMS[arm], self.boundaries, self.priors,
                               None if retained else int(self.ys[row, self.t-1]))[0]
            exact = sum(v for v, present in zip(w, mask) if present)
            probability[row, j] = float(exact)
            self.above_half[row, j] = exact > F(1, 2)
            self.fallback[2] += 1
        return probability

    def warning(self, y):
        y = np.asarray(y, dtype=np.int8)
        self.ys[:, self.t-1] = y
        self.z = ((y >> 1) ^ (y & 1)).astype(bool)
        g = self.p[..., 0]/self.p[..., 1]
        probability = np.where(self.z[:, None, None], g, 1-g)
        unnormalized = self.logw+np.log(probability)
        peak = unnormalized.max(axis=-1, keepdims=True)
        norm = peak+np.log(np.exp(unnormalized-peak).sum(axis=-1, keepdims=True))
        nll = log(2)-norm[..., 0]
        self.logw = unnormalized-norm
        u_num = np.where(self.z[:, None, None], self.p[..., 4], self.p[..., 2])
        u_den = np.where(self.z[:, None, None], self.p[..., 5], self.p[..., 3])
        u = (np.exp(self.logw)*(u_num/u_den)).sum(axis=-1)
        risk = np.minimum(u, 1-u)
        actions = np.where(risk < .1, (y[:, None] >> 1) ^ (u > .5), 2).astype(np.int8)
        near = np.abs(risk-.1) <= 1e-12
        for row, arm in np.argwhere(near):
            # A common orientation across components makes the weights irrelevant.
            nums, dens = u_num[row, arm], u_den[row, arm]
            same = np.all(nums*dens[0] == nums[0]*dens)
            if arm in (0, 1, 3) or same:
                exact_u = F(int(2*nums[0]), int(2*dens[0]))
                self.fallback[0] += 1
            else:
                hist = [(int(self.ys[row, k]), None if self.labels[row, arm, k] < 0 else int(self.labels[row, arm, k]))
                        for k in range(self.t-1)]
                exact_u = rational_state(self.counts[row], hist, ARMS[arm], self.boundaries,
                                         self.priors, int(y[row]))[2]
                self.fallback[1] += 1
            actions[row, arm] = 2 if min(exact_u, 1-exact_u) >= F(1, 10) else (int(y[row]) >> 1) ^ int(exact_u > F(1, 2))
        self.p[:, 1:, :, 0] += self.z[:, None, None]
        self.p[:, 1:, :, 1] += 1
        return actions, nll, self.probability_changed(), u

    def retain(self, labels):
        labels = np.asarray(labels, dtype=np.int8).copy()
        labels[:, (0, 4)] = -1
        self.labels[:, :, self.t-1] = labels
        observed = labels >= 0
        x = (self.ys[:, self.t-1, None] >> 1) ^ np.maximum(labels, 0)
        u_num = np.where(self.z[:, None, None], self.p[..., 4], self.p[..., 2])
        u_den = np.where(self.z[:, None, None], self.p[..., 5], self.p[..., 3])
        u = u_num/u_den
        likelihood = np.where(x[..., None].astype(bool), u, 1-u)
        likelihood = np.where(observed[..., None], likelihood, 1.)
        unnormalized = self.logw+np.log(likelihood)
        peak = unnormalized.max(axis=-1, keepdims=True)
        norm = peak+np.log(np.exp(unnormalized-peak).sum(axis=-1, keepdims=True))
        self.logw = unnormalized-norm
        for z, offset in ((False, 2), (True, 4)):
            which = observed & (self.z[:, None] == z)
            self.p[..., offset] += (which*x)[..., None]
            self.p[..., offset+1] += which[..., None]
        return self.probability_changed(retained=True)


def group_weights():
    rows = [WEIGHTS, np.array([1.]+[0.]*9), np.array([0.]+[1/9]*9)]
    for m in ('A_loss', 'B_loss', 'reverse'):
        rows.append(np.array([1/3 if c[0] == m else 0 for c in CONDITIONS]))
    for t in BOUNDARIES:
        rows.append(np.array([1/3 if c[1] == t else 0 for c in CONDITIONS]))
    return np.stack(rows)


def run_batch(meta, indices, prefix):
    start, cpu = perf_counter(), process_time()
    c, w, e, bit_a, bit_b = streams(meta, indices, prefix)
    b = len(indices)
    physical = np.broadcast_to(e[:, None, :], (b, 10, HORIZON)).copy()
    for j, (method, tau) in enumerate(CONDITIONS[1:], 1):
        new = (bit_a << 1) | (e & 1) if method == 'A_loss' else (e & 2) | bit_b if method == 'B_loss' else e ^ 3
        physical[:, j, tau-1:] = new[:, tau-1:]
    truth = np.broadcast_to(w[:, None, :], physical.shape).reshape(-1, HORIZON)
    warnings = physical.reshape(-1, HORIZON) ^ (3*truth)
    learner = Filter(np.repeat(c, 10, axis=0))
    shape = (b*10, 5, HORIZON)
    losses = np.empty(shape)
    refs = np.empty(shape, dtype=bool)
    wrong = np.empty(shape, dtype=bool)
    nlls = np.empty(shape)
    beliefs = np.empty((b*10, 2, 2, HORIZON))  # arm C/C-Y, before/after
    tau = np.tile(np.array([x[1] for x in CONDITIONS]), b)
    first_reference = np.full((b*10, 5), 101, dtype=np.int16)
    first_alarm = np.full((b*10, 2), 101, dtype=np.int16)
    first_after = np.full_like(first_alarm, 101)
    early_alarm = np.zeros_like(first_alarm, dtype=bool)
    wrong_before_reference = np.zeros((b*10, 5), dtype=np.int16)
    for t in range(1, HORIZON+1):
        learner.start(t)
        actions, nll, before, _ = learner.warning(warnings[:, t-1])
        ask = actions == 2
        err = (actions != truth[:, t-1, None]) & ~ask
        labels = np.where(ask, truth[:, t-1, None], -1).astype(np.int8)
        after = learner.retain(labels)
        losses[:, :, t-1] = err+.1*ask
        refs[:, :, t-1], wrong[:, :, t-1], nlls[:, :, t-1] = ask, err, nll
        beliefs[:, :, 0, t-1], beliefs[:, :, 1, t-1] = before, after
        first_reference = np.where(ask & (first_reference == 101), t, first_reference)
        wrong_before_reference += err & (first_reference == 101)
        alarm = learner.above_half
        first_alarm = np.where(alarm & (first_alarm == 101), t, first_alarm)
        first_after = np.where(alarm & (t >= tau[:, None]) & (first_after == 101), t, first_after)
        early_alarm |= alarm & (t < tau[:, None])
    loss = losses.reshape(b, 10, 5, 100)
    beliefs = beliefs.reshape(b, 10, 2, 2, 100)
    event = np.arange(1, 101)[None, :] >= np.array([x[1] for x in CONDITIONS])[:, None]
    brier = (beliefs-event[None, :, None, None, :])**2
    gw = group_weights()
    # Mean profiles, and paired-contrast moments, preserve within-block coupling.
    grouped = np.einsum('gk,bkat->bgat', gw, loss)
    differences = grouped[:, :, 2:3]-grouped[:, :, (0, 1, 3, 4)]
    result = dict(indices=np.array(indices, dtype=np.int16), calibration=c,
        wrong=wrong.sum(axis=-1).reshape(b, 10, 5), references=refs.sum(axis=-1).reshape(b, 10, 5),
        window_loss=np.stack([(.1*(10*wrong[:, :, i:i+25].sum(axis=-1)+refs[:, :, i:i+25].sum(axis=-1))).reshape(b, 10, 5)
                              for i in (25, 50, 75)], axis=-1),
        wrong_before_reference=wrong_before_reference.reshape(b, 10, 5),
        first_reference=first_reference.reshape(b, 10, 5),
        first_alarm=first_alarm.reshape(b, 10, 2), first_after=first_after.reshape(b, 10, 2),
        early_alarm=early_alarm.reshape(b, 10, 2),
        belief_mean=beliefs.mean(axis=-1), brier_mean=brier.mean(axis=-1),
        warning_nll=nlls.mean(axis=-1).reshape(b, 10, 5),
        condition_loss_sum=loss.sum(axis=0), condition_loss_square_sum=(loss**2).sum(axis=0),
        profile_sum=grouped.sum(axis=0), profile_square_sum=(grouped**2).sum(axis=0),
        contrast_profile_sum=differences.sum(axis=0), contrast_profile_square_sum=(differences**2).sum(axis=0),
        reference_profile_sum=refs.reshape(b, 10, 5, 100).sum(axis=0),
        wrong_profile_sum=wrong.reshape(b, 10, 5, 100).sum(axis=0),
        belief_profile_sum=beliefs.sum(axis=0), brier_profile_sum=brier.sum(axis=0),
        warning_nll_profile_sum=nlls.reshape(b, 10, 5, 100).sum(axis=0), fallback=learner.fallback)
    check('accounting', 'all task and window costs', np.allclose(loss.sum(axis=-1), result['wrong']+.1*result['references'], atol=1e-12, rtol=0)
          and np.all(result['wrong']+result['references'] <= 100))
    check('beliefs', 'finite positive predictions', np.isfinite(nlls).all() and np.all((beliefs >= 0) & (beliefs <= 1+1e-12)))
    return result, dict(wall_seconds=perf_counter()-start, cpu_seconds=process_time()-cpu,
                        checks=dict(CHECKS), cpus=sorted(os.sched_getaffinity(0)))


def fingerprint(arrays):
    h = sha256()
    for k, v in sorted(arrays.items()):
        h.update(k.encode('ascii'))
        h.update(str(v.shape).encode('ascii'))
        h.update(v.dtype.str.encode('ascii'))
        h.update(v.tobytes())
    return h.hexdigest()


def worker(job):
    meta, indices, prefix, output = job
    arrays, timing = run_batch(meta, indices, prefix)
    if output:
        target = Path(output)/'blocks'/f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        with target.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        return dict(label=meta['label'], first=indices[0], last=indices[-1], record=identity(target),
                    fingerprint=fingerprint(arrays), **timing)
    return dict(fingerprint=fingerprint(arrays), **timing)


def interval(values):
    """One within-block outcome, stratified by equally weighted base law."""
    values = np.asarray(values)
    check('aggregation', 'independent-block axes', values.shape == (27, 1024))
    mean = float(values.mean(axis=1).mean())
    se = float(np.sqrt(values.var(axis=1, ddof=1).sum()/(27**2*1024)))
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def aggregate(output, pop):
    all_fields = ('wrong', 'references', 'window_loss', 'wrong_before_reference', 'first_reference',
                  'first_alarm', 'first_after', 'early_alarm', 'belief_mean', 'brier_mean', 'warning_nll')
    store = {k:[] for k in all_fields}
    profiles = {}
    fallback = np.zeros(3, dtype=np.int64)
    for meta in pop:
        chunks = []
        for i in range(0, BLOCKS, CHUNK):
            path = output/'blocks'/f'{meta["label"]}_{i:04d}_{i+CHUNK-1:04d}.npz'
            with np.load(path, allow_pickle=False) as data:
                check('aggregation', 'complete block indices', np.array_equal(data['indices'], np.arange(i, i+CHUNK)))
                chunks.append({k:data[k] for k in all_fields})
                fallback += data['fallback']
                for k in data.files:
                    if k.endswith('_sum'):
                        profiles[k] = profiles.get(k, 0)+data[k]
        for k in all_fields:
            store[k].append(np.concatenate([c[k] for c in chunks], axis=0))
    store = {k:np.stack(v) for k, v in store.items()}
    units = 10*store['wrong']+store['references']
    costs = (64+100*units)/100000
    coefficients = np.rint(18*group_weights()).astype(np.int64)
    grouped_units = np.einsum('gk,brka->brga', coefficients, units)
    grouped = grouped_units/18000+.00064
    means, contrasts = {}, {}
    for i, group in enumerate(PROFILE_GROUPS):
        means[group] = {arm:interval(grouped[:, :, i, j]) for j, arm in enumerate(ARMS)}
        contrasts[group] = {f'C_minus_{arm}':interval((grouped_units[:, :, i, 2]-grouped_units[:, :, i, j])/18000)
                            for j, arm in enumerate(ARMS) if j != 2}
        contrasts[group]['C_minus_always_reference'] = interval(grouped[:, :, i, 2]-.1)
    criteria = dict(changed_C_below_F=contrasts['changed']['C_minus_F']['upper95'] < 0,
                    full_C_below_always_reference=contrasts['full']['C_minus_always_reference']['upper95'] < 0)
    conditions = {}
    for b, meta in enumerate(pop):
        for k, (method, tau) in enumerate(CONDITIONS):
            records = {}
            for j, arm in enumerate(ARMS):
                vals = costs[b, :, k, j]
                mu, se = float(vals.mean()), float(vals.std(ddof=1)/sqrt(BLOCKS))
                records[arm] = dict(mean_cost=mu, mc_se=se, lower95=mu-1.96*se, upper95=mu+1.96*se,
                    mean_wrong=float(store['wrong'][b, :, k, j].mean()),
                    mean_references=float(store['references'][b, :, k, j].mean()),
                    mean_wrong_before_first_reference=float(store['wrong_before_reference'][b, :, k, j].mean()),
                    mean_window_loss=store['window_loss'][b, :, k, j].mean(axis=0).tolist())
            paired = {}
            for j in (0, 1, 3, 4):
                delta_units = units[b, :, k, 2]-units[b, :, k, j]
                vals = delta_units/1000
                mu, se = int(delta_units.sum())/(1000*BLOCKS), float(vals.std(ddof=1)/sqrt(BLOCKS))
                paired['C_minus_'+ARMS[j]] = dict(mean=mu, mc_se=se, lower95=mu-1.96*se, upper95=mu+1.96*se)
            qindex = {'stable':0, 'A_loss':1, 'B_loss':2, 'reverse':3}[method]
            old_floor, new_floor = floor(meta['laws'][0]), floor(meta['laws'][qindex])
            episode_floor = (min(tau-1, 100)*old_floor+max(0, 101-tau)*new_floor)/100
            diag = {}
            for j, arm in enumerate(('C', 'C-Y')):
                after = store['first_after'][b, :, k, j]
                found = after <= 100
                diag[arm] = dict(first_alarm_probability=float((store['first_alarm'][b, :, k, j] <= 100).mean()),
                    early_or_stable_alarm_probability=float(store['early_alarm'][b, :, k, j].mean()),
                    post_change_above_half_probability=None if method == 'stable' else float(found.mean()),
                    conditional_delay=None if method == 'stable' or not found.any() else float((after[found]-tau).mean()),
                    posterior_before_after_mean=store['belief_mean'][b, :, k, j].mean(axis=0).tolist(),
                    brier_before_after_mean=store['brier_mean'][b, :, k, j].mean(axis=0).tolist())
            conditions[f'{meta["label"]}__{method}_{tau}'] = dict(arms=records, contrasts=paired, diagnostics=diag,
                old_floor=str(old_floor), new_floor=str(new_floor), episode_floor=str(episode_floor),
                weight='1/54' if method == 'stable' else '1/486')
    counts = {}
    for comp in ('F', 'S', 'R', 'C-Y'):
        ds = [v['contrasts']['C_minus_'+comp] for v in conditions.values()]
        counts[comp] = dict(point_lower=sum(x['mean'] < 0 for x in ds), point_equal=sum(x['mean'] == 0 for x in ds),
                           point_higher=sum(x['mean'] > 0 for x in ds), upper_below_zero=sum(x['upper95'] < 0 for x in ds),
                           lower_above_zero=sum(x['lower95'] > 0 for x in ds))
    profiles['known_Q_floor'] = np.array([[float(floor(meta['laws'][0 if t < tau else {'stable':0,'A_loss':1,'B_loss':2,'reverse':3}[method]]))
                      for t in range(1, 101)] for meta in pop for method, tau in CONDITIONS]).reshape(27, 10, 100)
    with (output/'TIME_PROFILES.npz').open('xb') as stream:
        np.savez_compressed(stream, **profiles)
    # First 25 affected tasks, and matched stable windows, retain block pairing.
    window = store['window_loss']
    recovery = {}
    for ti, tau in enumerate(BOUNDARIES):
        changed_indices = [i for i, (_, t) in enumerate(CONDITIONS) if t == tau]
        x = np.take(window, changed_indices, axis=2)[..., ti].mean(axis=2)
        stable = window[:, :, 0, :, ti]
        changed_floor = np.array([float(sum(floor(m['laws'][k]) for k in (1, 2, 3))/3)*25 for m in pop])[:, None]
        stable_floor = np.array([float(floor(m['laws'][0]))*25 for m in pop])[:, None]
        recovery[str(tau)] = dict(changed={a:interval(x[:, :, j]) for j, a in enumerate(ARMS)},
            stable={a:interval(stable[:, :, j]) for j, a in enumerate(ARMS)},
            changed_excess_above_known_Q={a:interval(x[:, :, j]-changed_floor) for j, a in enumerate(ARMS)},
            stable_excess_above_known_Q={a:interval(stable[:, :, j]-stable_floor) for j, a in enumerate(ARMS)},
            changed_contrasts={f'C_minus_{ARMS[j]}':interval(x[:, :, 2]-x[:, :, j]) for j in (0, 1, 3, 4)},
            stable_contrasts={f'C_minus_{ARMS[j]}':interval(stable[:, :, 2]-stable[:, :, j]) for j in (0, 1, 3, 4)})
    return dict(summary=dict(conditions=270, independent_blocks=27648, physical_episodes=276480,
        controller_task_steps=138240000, simulation='paired stratified Monte Carlo', blocks_per_base=BLOCKS,
        priors_or_prices_tuned=False, optional_stopping=False, policy='myopic', primary_arm='C',
        fallback_common_orientation=int(fallback[0]), fallback_full_rational_replays=int(fallback[1]),
        fallback_diagnostic_rational_replays=int(fallback[2])),
        means=means, contrasts=contrasts, criteria=criteria, functional_recovery_pass=all(criteria.values()),
        condition_counts=counts, conditions=conditions, first_25_affected_and_stable_window_costs=recovery)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    (output/'blocks').mkdir()
    logline(output, 'PREPARE; freeze before qualification and performance evaluation')
    check('integrity', 'prospective design', identity(SOURCE/'FEP_CHANGING_WORLD_V1.md')['sha256'] == DESIGN_SHA)
    check('integrity', 'previous manifest', identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = {x['path']:x for g in ('inputs', 'outputs', 'preserved') for x in prior[g]}
    for path in (PREVIOUS/'MANIFEST.json', SOURCE/'FEP_OFFGRID_VALIDATION_V1_REPORT.md'):
        preserved[str(path)] = identity(path)
    verify(list(preserved.values()))
    inputs = []
    for name in ('FEP_CHANGING_WORLD_V1.md', 'check_fep_changing_world.py', 'qualify_fep_changing_world.py'):
        inputs.append(identity(SOURCE/name))
        shutil.copyfile(SOURCE/name, output/'inputs'/name)
        check('integrity', 'source snapshot matches '+name, identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    pop = population()
    write(output/'POPULATION.json', dict(bases=pop, conditions=CONDITIONS, arms=ARMS,
         group_weights=group_weights().tolist(), stable_weight='1/2', changed_weight='1/2', primary='C'))
    write(output/'SEEDS.json', dict(root=ROOT_SEED, rng='Python random.Random MT19937', python=platform.python_version(),
        draw_order=streams.__doc__, main_prefix='fep-changing-world-v1', blocks={x['label']:[str(seed_for(x['label'], i)) for i in range(BLOCKS)] for x in pop}))
    inputs += [identity(output/'POPULATION.json'), identity(output/'SEEDS.json')]
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources', 'four available CPUs', len(cpus) == 4)
    write(output/'PREPARATION.json', dict(inputs=inputs, preserved=list(preserved.values()),
        started_utc=now(), python=platform.python_version(), numpy=np.__version__, cpus=cpus,
        storage=storage, chunks=216, block_chunk=CHUNK, sample_size=BLOCKS,
        source_snapshots=[identity(p) for p in sorted((output/'inputs').iterdir())]))
    logline(output, 'FROZEN: design, both sources, population, weights, seeds and prior records')
    pin_cpus(cpus)
    import qualify_fep_changing_world as Q
    # Running this script as __main__ must not create a second tested module.
    qualification = Q.qualify(sys.modules[__name__], cpus)
    write(output/'QUALIFICATION.json', qualification)
    logline(output, f'QUALIFIED: {qualification["checks"]} assertions; {qualification["wall_seconds"]:.3f}s')
    synthetic = dict(label='synthetic_benchmark', laws=[[str(F(x, 400)) for x in (221, 119, 39, 21)]])
    jobs = [(synthetic, list(range(i*32, (i+1)*32)), 'benchmark-fep-changing-world-v1', None) for i in range(4)]
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=4, initializer=pin_cpus, initargs=(cpus,)) as pool:
        bench = list(pool.map(worker, jobs))
    elapsed = perf_counter()-start
    forecast = 120+3*elapsed*(27648/128)
    record = dict(workers=4, total_benchmark_blocks=128, wall_seconds=elapsed,
        forecast_seconds=forecast, requires_detached=forecast > 600,
        rule='120 seconds plus 3 times four-worker wall extrapolation from 128 benchmark blocks to 27648 main blocks',
        runs=bench, no_benchmark_costs_used_for_selection=True)
    write(output/'BENCHMARK.json', record)
    verify(inputs+list(preserved.values()))
    logline(output, f'PREPARED: forecast {forecast:.3f}s; detached={forecast > 600}; no main outcomes')
    print(json.dumps(dict(qualification=qualification['checks'], benchmark_seconds=elapsed,
                         forecast_seconds=forecast, requires_detached=forecast > 600)))


def execute(output, detached):
    start, cpu = perf_counter(), process_time()
    prep = json.loads((output/'PREPARATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    verify(prep['inputs']+prep['preserved']+prep['source_snapshots'])
    check('execution', 'qualified before execution', json.loads((output/'QUALIFICATION.json').read_text())['status'] == 'PASS')
    check('execution', 'detachment threshold', detached or not bench['requires_detached'])
    mount_check(output)
    pin_cpus(prep['cpus'])
    write(output/'EXECUTION_STARTED.json', dict(started_utc=now(), pid=os.getpid(), detached=detached,
        cpu_affinity=prep['cpus'], workers=4, benchmark=identity(output/'BENCHMARK.json')))
    logline(output, 'MAIN STARTED; 216 fixed chunks; four workers; no sample-size adaptation')
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(m, list(range(i, i+CHUNK)), 'fep-changing-world-v1', str(output)) for m in pop for i in range(0, BLOCKS, CHUNK)]
    records = []
    with ProcessPoolExecutor(max_workers=4, initializer=pin_cpus, initargs=(prep['cpus'],)) as pool:
        for i, record in enumerate(pool.map(worker, jobs), 1):
            records.append(record)
            if i % 8 == 0:
                logline(output, f'COMPLETED {i}/216 chunks; latest base {record["label"]}; data durable')
    write(output/'WORKERS.json', records)
    results = aggregate(output, pop)
    write(output/'RESULTS.json', results)
    verify(prep['inputs']+prep['preserved']+prep['source_snapshots'])
    verify([r['record'] for r in records])
    end = now()
    logline(output, f'COMPLETE; main wall {perf_counter()-start:.3f}s; all fixed blocks retained; readback passed')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
    write(output/'MANIFEST.json', dict(status='COMPLETE', finished_utc=end,
        started_utc=json.loads((output/'EXECUTION_STARTED.json').read_text())['started_utc'],
        main_wall_seconds=perf_counter()-start, parent_cpu_seconds=process_time()-cpu,
        worker_cpu_seconds=sum(r['cpu_seconds'] for r in records), workers=4,
        python=platform.python_version(), numpy=np.__version__, inputs=prep['inputs'],
        preserved=prep['preserved'], outputs=outputs, summary=results['summary'], verification_checks=dict(CHECKS)))


def launch(output):
    check('launch', 'qualified forecast exists', (output/'BENCHMARK.json').is_file())
    check('launch', 'not started', not (output/'EXECUTION_STARTED.json').exists() and not (output/'LAUNCH.json').exists())
    with (output/'DETACHED_STDOUT.log').open('xb') as stream:
        child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), 'execute', '--output', str(output), '--detached'],
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
            cwd=SOURCE, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    rec = dict(pid=child.pid, launched_utc=now(), command='execute --detached', automatic_polling=False,
               qualified_benchmark=identity(output/'BENCHMARK.json'))
    write(output/'LAUNCH.json', rec)
    print(json.dumps(rec))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=('prepare', 'execute', 'launch'))
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--detached', action='store_true')
    args = ap.parse_args()
    check('scope', 'fresh FEP attempt namespace', args.output.parent == ROOT and args.output.name.startswith('attempt-'))
    try:
        if args.phase == 'prepare':
            prepare(args.output)
        elif args.phase == 'execute':
            execute(args.output, args.detached)
        else:
            launch(args.output)
    except Exception:
        if args.output.is_dir():
            failure = args.output/f'FAILURE_{args.phase}.json'
            if not failure.exists():
                write(failure, dict(phase=args.phase, utc=now(), traceback=traceback.format_exc(), checks=dict(CHECKS)))
            logline(args.output, f'FAILED {args.phase}; attempt preserved; no automatic rerun')
        raise


if __name__ == '__main__':
    main()
