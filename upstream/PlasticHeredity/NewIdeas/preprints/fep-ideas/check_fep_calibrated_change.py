#!/usr/bin/env python3
"""Fixed calibration-transfer change model with matched three-decision control."""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
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
import random
import shutil
import subprocess
from time import perf_counter, process_time
import traceback

SOURCE = Path(__file__).resolve().parent
assert sha256((SOURCE/'check_fep_three_decision_checking.py').read_bytes()).hexdigest() == '6198011cb6fe32d2a2c1acc0bc977300e6c8b2281c58e706e2da98b9ed231349'
import check_fep_three_decision_checking as T
import numpy as np
M, A, B = T.M, T.A, T.B
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-calibrated-change-v1')
PREVIOUS = ROOT.parent/'fep-c3-recovery-audit-v1/attempt-01'
PREVIOUS_SHA = '2cdfd9861d8b868a89f00b27b7357d2ef19295b5bd93979a37f522aa911f341a'
PREFIX = 'fep-calibrated-change-v1'
ARMS = (*T.ARMS, 'CT3', 'CT3-flat')
CONDITIONS = M.CONDITIONS+[(f, t) for f in ('A_partial', 'B_partial', 'both_partial') for t in M.BOUNDARIES]
KINDS = np.array([0]+[0, 1, 2]*3)
TIMES = np.array([101]+[t for t in M.BOUNDARIES for _ in range(3)])
PHASES = ('before', 'first_answer', 'after', 'total')
SUMS = ('conditional_cost', 'known_Q_floor', 'insufficient_checking', 'wrong_direction', 'excess_checking', 'subjective_cost')
CHECKS = {}


def check(group, name, ok):
    if not bool(ok):
        raise AssertionError(group+': '+name)
    CHECKS[group] = CHECKS.get(group, 0)+1


def active(t, boundaries=M.BOUNDARIES):
    times = np.array([101]+[b for b in boundaries for _ in range(3)])
    return np.where(times <= t, KINDS, 0)


def reset_parameters(counts, transfer):
    n = len(counts)
    reset = np.broadcast_to(M.PRIOR, (n, 10, 6)).copy()
    for j in range(1, 10):
        if KINDS[j]:
            errors = counts[:, 1]+counts[:, 3] if KINDS[j] == 1 else counts[:, 2]+counts[:, 3]
            reset[:, j, 2] = np.where(transfer, errors+1, 1)
            reset[:, j, 3] = np.where(transfer, counts.sum(axis=1)+2, 2)
    return reset


def advance(p, reset, t, boundaries=M.BOUNDARIES):
    if t in boundaries:
        p = p.copy()
        j = 1+3*boundaries.index(t)
        p[:, j:j+3] = reset[:, j:j+3]
    return p


def observe_warning(w, p, z, kind):
    general = kind == 0
    g = np.where(general[None, :], p[..., 0]/p[..., 1], .5)
    mass = w*np.where(z[:, None], g, 1-g)
    out = p.copy()
    out[..., 0] += z[:, None]*general[None, :]
    out[..., 1] += general[None, :]
    return mass, out


def orientation(p, z, kind):
    u = np.where(z[:, None], p[..., 4]/p[..., 5], p[..., 2]/p[..., 3])
    rate = p[..., 2]/p[..., 3]
    return np.where(kind[None, :] == 1, np.where(z[:, None], 1-rate, rate),
                    np.where(kind[None, :] == 2, rate, u))


def observe_label(w, p, z, x, kind, observed=None):
    x = np.broadcast_to(x, z.shape).astype(bool)
    if observed is None:
        observed = np.ones(len(z), dtype=bool)
    u = orientation(p, z, kind)
    mass = w*np.where(observed[:, None], np.where(x[:, None], u, 1-u), 1.)
    out = p.copy()
    for parity, offset in ((False, 2), (True, 4)):
        use = observed[:, None] & (z[:, None] == parity) & (kind[None, :] == 0)
        out[..., offset] += use*x[:, None]
        out[..., offset+1] += use
    use = observed[:, None] & (kind[None, :] != 0)
    error = np.where(kind[None, :] == 1, (x ^ z)[:, None], x[:, None])
    out[..., 2] += use*error
    out[..., 3] += use
    return mass, out


def before(w, p, reset, t, steps, boundaries=M.BOUNDARIES, retain=True):
    if steps == 0:
        return np.zeros(len(w))
    p = advance(p, reset, t, boundaries)
    kind = active(t, boundaries)
    value = np.zeros(len(w))
    for parity in (False, True):
        z = np.full(len(w), parity)
        mass, pp = observe_warning(w, p, z, kind)
        r, q, _ = scores(mass, pp, reset, z, t, steps, boundaries, retain)
        value += np.minimum(r, q)
    return value


def scores(w, p, reset, z, t, steps=3, boundaries=M.BOUNDARIES, retain=True):
    steps = min(steps, 101-t)
    kind = active(t, boundaries)
    one = (w*orientation(p, z, kind)).sum(axis=1)
    total = w.sum(axis=1)
    risk = np.minimum(one, total-one)
    if steps == 1:
        return risk, .1*total, np.zeros(len(w))
    v0 = before(w, p, reset, t+1, steps-1, boundaries, retain)
    v1 = np.zeros(len(w)) if retain else v0
    if retain:
        for x in (False, True):
            ww, pp = observe_label(w, p, z, x, kind)
            v1 += before(ww, pp, reset, t+1, steps-1, boundaries, retain)
    return risk+v0, .1*total+v1, v0-v1


class Filter:
    """Exact posterior for the declared model conditional on calibration."""
    def __init__(self, counts, transfer=True, boundaries=M.BOUNDARIES, kinds_prior=(F(1,3),)*3):
        self.counts = np.array(counts, dtype=np.int16, copy=True)
        self.n = len(counts)
        self.transfer = np.broadcast_to(transfer, (self.n,)).copy()
        self.boundaries = tuple(boundaries)
        self.kinds_prior = tuple(kinds_prior)
        priors = [F(1,2)]+[F(1,6)*v for _ in boundaries for v in kinds_prior]
        check('inference', 'normalized model prior', sum(priors) == 1 and len(priors) == 10)
        self.w = np.broadcast_to(list(map(float, priors)), (self.n, 10)).copy()
        self.p = np.broadcast_to(M.initial_parameters(counts)[:, None, :], (self.n, 10, 6)).copy()
        self.reset = reset_parameters(self.counts, self.transfer)
        self.ys = np.zeros((self.n, 100), dtype=np.int8)
        self.labels = np.full((self.n, 100), -1, dtype=np.int8)
        self.fallback = 0
        self.t = 0

    def start(self, t):
        self.t = t
        self.p = advance(self.p, self.reset, t, self.boundaries)

    def warning(self, y):
        self.ys[:, self.t-1] = y
        self.z = ((y >> 1) ^ (y & 1)).astype(bool)
        self.w, self.p = observe_warning(self.w, self.p, self.z, active(self.t, self.boundaries))
        norm = self.w.sum(axis=1, keepdims=True)
        check('inference', 'positive warning evidence', np.all(norm > 0))
        self.w /= norm
        self.u = (self.w*orientation(self.p, self.z, active(self.t, self.boundaries))).sum(axis=1)
        return self.u.copy()

    def choose(self, steps=3, retain=True):
        r, q, delta = scores(self.w, self.p, self.reset, self.z, self.t, steps, self.boundaries, retain)
        y = self.ys[:, self.t-1]
        action = np.where(q <= r, 2, (y >> 1) ^ (self.u > .5)).astype(np.int8)
        myopic = np.where(np.minimum(self.u, 1-self.u) >= .1, 2, (y >> 1) ^ (self.u > .5)).astype(np.int8)
        near = (np.abs(r-q) <= 1e-12) | (np.abs(np.minimum(self.u, 1-self.u)-.1) <= 1e-12)
        if near.any():
            from qualify_fep_calibrated_change import rational_state, direct_scores, exact_action
            for row in np.flatnonzero(near):
                hist = [(int(self.ys[row,k]), None if self.labels[row,k] < 0 else int(self.labels[row,k])) for k in range(self.t-1)]
                w, p, reset = rational_state(self.counts[row], hist, int(y[row]), bool(self.transfer[row]), self.boundaries, self.kinds_prior)
                er, eq, _, u = direct_scores(w, p, reset, int(y[row]), self.t, steps, self.boundaries, retain)
                action[row] = exact_action(er, eq, u, int(y[row]))
                myopic[row] = exact_action(min(u, 1-u), F(1,10), u, int(y[row]))
                self.fallback += 1
        check('planning', 'nonnegative information value', np.all(delta >= -2e-12))
        check('planning', 'myopic purchases retained', not np.any((myopic == 2) & (action != 2)))
        extra = (action == 2) & (myopic != 2)
        return action, delta, np.where(extra, r-q, 0.), extra

    def retain(self, labels):
        labels = np.asarray(labels, dtype=np.int8)
        self.labels[:, self.t-1] = labels
        x = (self.ys[:, self.t-1] >> 1) ^ np.maximum(labels, 0)
        self.w, self.p = observe_label(self.w, self.p, self.z, x, active(self.t, self.boundaries), labels >= 0)
        norm = self.w.sum(axis=1, keepdims=True)
        check('inference', 'positive paid-label evidence', np.all(norm > 0))
        self.w /= norm

    def diagnosis(self):
        times = np.array([101]+[t for t in self.boundaries for _ in range(3)])
        changed = times <= self.t
        return np.stack([self.w[:, ~changed].sum(axis=1)]+[
            self.w[:, changed & (KINDS == k)].sum(axis=1) for k in range(3)], axis=-1)


def extend_meta(meta):
    q = list(map(F, meta['laws'][0]))
    qa = [(3*q[i]+q[i ^ 2])/4 for i in range(4)]
    qb = [(3*q[i]+q[i ^ 1])/4 for i in range(4)]
    qab = [(3*qa[i]+qa[i ^ 1])/4 for i in range(4)]
    return dict(meta, laws=meta['laws']+[[str(x) for x in law] for law in (qa, qb, qab)])


def population():
    return [extend_meta(m) for m in M.population()]


def physical_trace(meta, indices, prefix, core_only=False):
    cal, warnings, truth, q = A.physical_trace(meta, indices, prefix)
    if core_only:
        return cal, warnings, truth, q
    b = len(indices)
    _, w, e, _, _ = M.streams(meta, indices, prefix)
    flips = np.zeros((b, 100, 2), dtype=np.int8)
    for row, block in enumerate(indices):
        rng = random.Random(M.seed_for(meta['label'], block, prefix+'-transfer-flips'))
        for t in range(100):
            flips[row, t] = (rng.random() < .25, rng.random() < .25)
    extension = np.broadcast_to(e[:, None, :], (b, 9, 100)).copy()
    laws = np.broadcast_to(np.array(list(map(float, map(F, meta['laws'][0])))), (9, 100, 4)).copy()
    for j, (family, tau) in enumerate(CONDITIONS[10:]):
        mask = (2*flips[..., 0] if family != 'B_partial' else 0)+(flips[..., 1] if family != 'A_partial' else 0)
        extension[:, j, tau-1:] ^= mask[:, tau-1:]
        law_index = {'A_partial': 4, 'B_partial': 5, 'both_partial': 6}[family]
        laws[j, tau-1:] = list(map(float, map(F, meta['laws'][law_index])))
    return cal, np.concatenate((warnings, extension ^ (3*w[:, None, :])), axis=1), np.broadcast_to(w[:, None, :], (b, 19, 100)).copy(), np.concatenate((q, laws))


def run_batch(meta, indices, prefix, core_only=False):
    start, cpu = perf_counter(), process_time()
    conditions = CONDITIONS[:10] if core_only else CONDITIONS
    nc, b = len(conditions), len(indices)
    n = b*nc
    cal, warnings, truth, laws = physical_trace(meta, indices, prefix, core_only)
    y, target = warnings.reshape(n, 100), truth.reshape(n, 100)
    counts = np.repeat(cal, nc, axis=0)
    controls, c2, c3 = M.Filter(counts), M.Filter(counts), M.Filter(counts)
    candidate = Filter(np.tile(counts, (2,1)), np.repeat([True, False], n))
    wrong = np.zeros((n, 9), dtype=np.int16)
    refs, pw, pr = (np.zeros_like(wrong) for _ in range(3))
    ww, wr = (np.zeros((n, 9, 3), dtype=np.int16) for _ in range(2))
    first = np.full_like(wrong, 101)
    tau = np.tile([t for _, t in conditions], b)
    ex2, ex3 = (np.zeros((n, 3), dtype=np.int16) for _ in range(2))
    d2s, d3s, g2s, g3s = (np.zeros(n) for _ in range(4))
    disagreements = np.zeros((n, 2), dtype=np.int16)
    fallbacks = np.zeros(3, dtype=np.int64)
    candidate_extras = np.zeros((n, 2, 3), dtype=np.int16)
    candidate_values = np.zeros((n, 2, 2))
    phase_counts = np.zeros((n, 3, 3, 3), dtype=np.int16)
    phase_sums = np.zeros((n, 3, 3, 6))
    diagnosis = np.zeros((n, 2, 4, 4))
    for t in range(1, 101):
        for f in (controls, c2, c3, candidate):
            f.start(t)
        base, _, _, _ = controls.warning(y[:, t-1])
        my2, _, _, _ = c2.warning(y[:, t-1])
        my3, _, _, u3 = c3.warning(y[:, t-1])
        a2, d2, g2, e2, n2 = B.choose_future(c2, y[:, t-1], my2[:,2])
        a3, d3, g3, e3, n3, own2, nd = T.choose_three(c3, y[:,t-1], my3[:,2])
        uc = candidate.warning(np.tile(y[:, t-1], 2))
        ac, dc, gc, ec = candidate.choose()
        acts = ac.reshape(2, n).T
        actions = np.column_stack((base, a2, a3, acts))
        ask = actions == 2
        error = (actions != target[:, t-1, None]) & ~ask
        affected = t >= tau
        fallbacks += (n2, n3, nd)
        for extra, event, ai in ((ex2, e2, 5), (ex3, e3, 6)):
            extra[:,0] += event
            extra[:,1] += event & affected
            extra[:,2] += event & affected & (first[:,ai] < t)
        for ci in (0,1):
            event = ec.reshape(2,n)[ci]
            candidate_extras[:,ci,0] += event
            candidate_extras[:,ci,1] += event & affected
            candidate_extras[:,ci,2] += event & affected & (first[:,7+ci] < t)
        candidate_values += np.stack((dc.reshape(2,n).T, gc.reshape(2,n).T), axis=-1)
        disagreements[:,0] += (a3 == 2) & (own2 != 2)
        disagreements[:,1] += (a3 != 2) & (own2 == 2)
        first = np.where(ask & affected[:,None] & (first == 101), t, first)
        wrong += error; refs += ask
        pw += error & affected[:,None]; pr += ask & affected[:,None]
        if t >= 26:
            wi = (t-26)//25
            ww[:,:,wi] += error; wr[:,:,wi] += ask
        d2s += d2; d3s += d3; g2s += g2; g3s += g3
        # Evaluator-only risk attribution; these arrays never enter a learner.
        q = np.tile(laws[:, t-1, :], (b, 1))
        yy = y[:, t-1]
        p1 = q[np.arange(n), yy ^ 3]/(q[np.arange(n), yy]+q[np.arange(n), yy ^ 3])
        aa, ar = actions[:,6:], ask[:,6:]
        risk = np.where(aa == 0, p1[:,None], 1-p1[:,None])
        best = np.minimum(p1, 1-p1)[:,None]
        physical = np.where(ar, .1, risk)
        u = np.column_stack((u3[:,2], uc.reshape(2,n).T))
        subjective_p1 = np.where((yy >> 1)[:,None], 1-u, u)
        subjective = np.where(ar, .1, np.where(aa == 0, subjective_p1, 1-subjective_p1))
        floor = np.broadcast_to(np.minimum(best, .1), physical.shape)
        sums = np.stack((physical, floor, np.where(ar, 0, np.maximum(best-.1,0)),
                         np.where(ar, 0, risk-best), np.where(ar, np.maximum(.1-best,0), 0), subjective), axis=-1)
        check('accounting', 'task regret identity', np.allclose(sums[...,0]-sums[...,1], sums[...,2:5].sum(axis=-1), atol=2e-15, rtol=0))
        phase = np.where(first[:,6:] < t, 2, np.where(first[:,6:] == t, 1, 0))
        c = np.stack((np.ones_like(ar), error[:,6:], ar), axis=-1)
        for j in range(3):
            selected = affected[:,None] & (phase == j)
            phase_counts[:,:,j] += c*selected[...,None]
            phase_sums[:,:,j] += sums*selected[...,None]
        controls.retain(np.where(ask[:,:5], target[:,t-1,None], -1).astype(np.int8))
        for f, ai in ((c2,5), (c3,6)):
            labels = np.full((n,5), -1, dtype=np.int8)
            labels[:,2] = np.where(ask[:,ai], target[:,t-1], -1)
            f.retain(labels)
        candidate.retain(np.where(ask[:,7:].T.reshape(2*n), np.tile(target[:,t-1],2), -1))
        if t in (25,50,75,100):
            diagnosis[:,:,(t//25)-1] = candidate.diagnosis().reshape(2,n,4).transpose(1,0,2)
        if t >= 99:
            check('terminal', 'old C3 collapse', np.array_equal(a3, own2))
        if t == 100:
            check('terminal', 'no future information value', np.all(dc == 0) and np.all(d3 == 0))
    out = dict(indices=np.array(indices,dtype=np.int16), calibration=cal,
        wrong=wrong.reshape(b,nc,9), references=refs.reshape(b,nc,9),
        window_wrong=ww.reshape(b,nc,9,3), window_references=wr.reshape(b,nc,9,3),
        post_wrong=pw.reshape(b,nc,9), post_references=pr.reshape(b,nc,9), first_post_reference=first.reshape(b,nc,9),
        extra_references=ex3.reshape(b,nc,3), delta_sum=d3s.reshape(b,nc), selected_gain_sum=g3s.reshape(b,nc),
        own_c2_disagreements=disagreements.reshape(b,nc,2), c2_extra_references=ex2.reshape(b,nc,3),
        c2_delta_sum=d2s.reshape(b,nc), c2_selected_gain_sum=g2s.reshape(b,nc), planner_fallbacks=fallbacks,
        control_fallback=controls.fallback, c2_inference_fallback=c2.fallback, c3_inference_fallback=c3.fallback,
        candidate_fallback=np.array([candidate.fallback],dtype=np.int64),
        candidate_extra_references=candidate_extras.reshape(b,nc,2,3), candidate_values=candidate_values.reshape(b,nc,2,2),
        phase_counts=phase_counts.reshape(b,nc,3,3,3), phase_sums=phase_sums.reshape(b,nc,3,3,6),
        diagnosis=diagnosis.reshape(b,nc,2,4,4))
    check('accounting', 'episode/window counts', np.all(wrong+refs <= 100) and np.all(ww+wr <= 25))
    check('accounting', 'phase errors', np.array_equal(phase_counts[...,1].sum(axis=-1), pw[:,6:]))
    check('accounting', 'phase references', np.array_equal(phase_counts[...,2].sum(axis=-1), pr[:,6:]))
    check('accounting', 'diagnosis normalized', np.allclose(diagnosis.sum(axis=-1), 1, atol=2e-15, rtol=0))
    for j, (_, t) in enumerate(conditions):
        if t == 101:
            check('accounting', 'no stable post endpoint', not out['post_wrong'][:,j].any() and not out['post_references'][:,j].any())
        else:
            for key, window in (('post_wrong','window_wrong'), ('post_references','window_references')):
                check('accounting', 'post/window identity', np.array_equal(out[key][:,j], out[window][:,j,:,(t-26)//25:].sum(axis=-1)))
    return out, dict(wall_seconds=perf_counter()-start, cpu_seconds=process_time()-cpu, cpus=sorted(os.sched_getaffinity(0)), checks=dict(CHECKS))


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


def coefficients():
    out = {'core_full': [9]+[1]*9+[0]*9, 'stable': [18]+[0]*18,
           'core_changed': [0]+[2]*9+[0]*9,
           'core_reliability': [0]+[3]*6+[0]*12,
           'transfer': [0]*10+[2]*9, 'transfer_full': [9]+[0]*9+[1]*9}
    for family in ('A_loss', 'B_loss', 'reverse', 'A_partial', 'B_partial', 'both_partial'):
        out[family] = [6 if f == family else 0 for f, t in CONDITIONS]
    for panel, indices in (('core', range(1,10)), ('transfer', range(10,19))):
        for tau in M.BOUNDARIES:
            out[f'{panel}_T{tau}'] = [6 if i in indices and t == tau else 0 for i, (f,t) in enumerate(CONDITIONS)]
    return {k: np.array(v, dtype=np.int64) for k,v in out.items()}


def ci(values):
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        values = values[None, :]
    nb, n = values.shape
    check('aggregation', 'independent block matrix', n > 1)
    mean = float(values.mean())
    se = float(np.sqrt(values.var(axis=1, ddof=1).sum()/(nb*nb*n)))
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def stats_int(num, den, offset=0.):
    result = ci(num/den)
    mean = int(num.sum())/(num.size*den)+offset
    return dict(result, mean=mean, lower95=mean-1.96*result['mc_se'], upper95=mean+1.96*result['mc_se'])


def arm_summary(num, den, offset=0.):
    return dict(arms={arm: stats_int(num[...,i],den,offset) for i,arm in enumerate(ARMS)},
        contrasts={'CT3_minus_'+arm: stats_int(num[...,7]-num[...,i],den) for i,arm in enumerate(ARMS) if i != 7},
        CT3_minus_always=stats_int(num[...,7],den,offset-.1))


def analyze(rows, pop):
    nb, n = rows['wrong'].shape[:2]
    units = 10*rows['wrong'].astype(np.int64)+rows['references']
    post = 10*rows['post_wrong'].astype(np.int64)+rows['post_references']
    mult = np.array([0]+[150//(101-t) for _,t in CONDITIONS[1:]])
    episode, post_change, diagnostics, planning, posterior = {}, {}, {}, {}, {}
    pc = rows['phase_counts'].astype(np.int64)
    ps = rows['phase_sums']
    check('aggregation', 'saved phase errors', np.array_equal(pc[...,1].sum(axis=-1), rows['post_wrong'][...,6:]))
    check('aggregation', 'saved phase references', np.array_equal(pc[...,2].sum(axis=-1), rows['post_references'][...,6:]))
    check('aggregation', 'saved regret closure', np.allclose(ps[...,0]-ps[...,1], ps[...,2:5].sum(axis=-1), atol=5e-13, rtol=0))
    pc = np.concatenate((pc, pc.sum(axis=-2,keepdims=True)),axis=-2)
    ps = np.concatenate((ps, ps.sum(axis=-2,keepdims=True)),axis=-2)
    for group, co in coefficients().items():
        episode[group] = arm_summary(np.einsum('k,brka->bra',co,units),18000,.00064)
        posterior[group] = {}
        for ai, arm in enumerate(ARMS[7:]):
            weighted = np.einsum('k,brkts->brts',co/18,rows['diagnosis'][...,ai,:,:])
            posterior[group][arm] = {str(t): {name:ci(weighted[...,ti,j]) for j,name in enumerate(('no_change_yet','G','A','B'))} for ti,t in enumerate((25,50,75,100))}
        planning[group] = {}
        for ai, arm in enumerate(ARMS[7:]):
            ex = np.einsum('k,brkd->brd',co,rows['candidate_extra_references'][...,ai,:].astype(np.int64))
            val = np.einsum('k,brkd->brd',co/18,rows['candidate_values'][...,ai,:])
            planning[group][arm] = {name:stats_int(ex[...,j],18) for j,name in enumerate(('extra_checks','post_extra_checks','extras_after_first_answer'))}
            planning[group][arm].update({name:ci(val[...,j]) for j,name in enumerate(('information_value_sum','selected_gain_sum'))})
        if group == 'stable' or group.endswith('_full'):
            continue
        post_change[group] = arm_summary(np.einsum('k,brka->bra',co*mult,post),27000)
        c = np.einsum('k,brkapm->brapm',co*mult/2700,pc)
        s = np.einsum('k,brkapm->brapm',co*mult/2700,ps)
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
            if ai != 1:
                diagnostics[group]['contrasts']['CT3_minus_'+arm] = {phase:{name:ci(v[...,1,pi]-v[...,ai,pi]) for name,v in metrics.items()} for pi,phase in enumerate(PHASES)}
            first = rows['first_post_reference'][...,6+ai]
            wait = np.maximum(first-np.array([t for _,t in CONDITIONS])[None,None,:],0)
            diagnostics[group]['query'][arm] = dict(purchase_probability=ci(np.einsum('k,brk->br',co/18,first<101)),
                                                    waiting_tasks=ci(np.einsum('k,brk->br',co/18,wait)))
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
                panel='core' if j < 10 else 'transfer')
    signs = {}
    for panel, indices in (('core',range(10)),('transfer',range(10,19)),('all',range(19))):
        signs[panel] = {}
        for endpoint,data in (('episode',units),('post_change',post)):
            signs[panel][endpoint] = {}
            for ai,arm in enumerate(ARMS):
                if ai == 7:
                    continue
                tally = dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
                for bi in range(nb):
                    for j in indices:
                        if not j and endpoint == 'post_change':
                            continue
                        d = data[bi,:,j,7]-data[bi,:,j,ai]
                        den = 1000 if endpoint == 'episode' else 10*(101-CONDITIONS[j][1])
                        c = stats_int(d,den)
                        for name,yes in (('point_lower',int(d.sum())<0),('point_equal',int(d.sum())==0),('point_higher',int(d.sum())>0),('upper_below_zero',c['upper95']<0),('lower_above_zero',c['lower95']>0)):
                            tally[name] += int(yes)
                signs[panel][endpoint][arm] = tally
    windows = {}
    wunits = 10*rows['window_wrong'].astype(np.int64)+rows['window_references']
    for wi,tau in enumerate(M.BOUNDARIES):
        windows[str(tau)] = {'stable':arm_summary(wunits[:,:,0,:,wi],250)}
        for panel,indices in (('core',range(1,10)),('transfer',range(10,19))):
            selected = [j for j in indices if CONDITIONS[j][1] == tau]
            windows[str(tau)][panel] = arm_summary(np.take(wunits,selected,axis=2)[...,wi].sum(axis=2),750)
    criteria = dict(overall_useful_function=episode['core_full']['CT3_minus_always']['upper95']<0,
        economical_core_recovery=post_change['core_changed']['CT3_minus_always']['upper95']<0,
        reliability_recovery_gain=post_change['core_reliability']['contrasts']['CT3_minus_C3']['upper95']<0,
        calibration_transfer_value=post_change['core_reliability']['contrasts']['CT3_minus_CT3-flat']['upper95']<0,
        transfer_gain=post_change['transfer']['contrasts']['CT3_minus_C3']['upper95']<0)
    return dict(summary=dict(independent_blocks=nb*n,bases=nb,blocks_per_base=n,physical_conditions=nb*19,
        physical_episodes=nb*n*19,arms=list(ARMS),primary='CT3',seed_prefix=PREFIX,
        conditional_model='calibration-informed independent new-phase marginal; no exact old/new latent tying',
        objective='three-decision expected task cost; exact conditional VFE/Bayesian belief inference',
        new_policies=2,tuned_after_outcomes=False),criteria=criteria,complete_proposed_claim=all(criteria.values()),
        episode=episode,post_change=post_change,conditions=conditions,condition_counts=signs,
        diagnostics=diagnostics,planning=planning,posterior=posterior,first_25_task_mean_cost=windows)


def aggregate(output,pop):
    fields = ('wrong','references','post_wrong','post_references','window_wrong','window_references',
              'first_post_reference','phase_counts','phase_sums','candidate_extra_references','candidate_values','diagnosis')
    rows = {k:[] for k in fields}
    fallback_names = ('planner_fallbacks','control_fallback','c2_inference_fallback','c3_inference_fallback','candidate_fallback')
    fallbacks = {k:0 for k in fallback_names}
    for meta in pop:
        parts = {k:[] for k in fields}
        for first in range(0,1024,128):
            with np.load(output/'blocks'/f'{meta["label"]}_{first:04d}_{first+127:04d}.npz',allow_pickle=False) as saved:
                check('aggregation','chunk indices',np.array_equal(saved['indices'],np.arange(first,first+128)))
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
    mount = json.loads(subprocess.check_output(['findmnt','-J','-T','/mnt/bioIce1','-o','TARGET,SOURCE,FSTYPE'],text=True))['filesystems'][0]
    check('storage','verified FEP mount',mount == dict(target='/mnt/bioIce1',source='/dev/sdc1',fstype='ext4') and output.parent == ROOT)
    stat = os.statvfs('/mnt/bioIce1')
    free = stat.f_bavail*stat.f_frsize
    check('storage','space available',free > 2_000_000_000)
    return dict(mount=mount,free_bytes=free)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True,exist_ok=False)
    (output/'inputs').mkdir(); (output/'blocks').mkdir()
    M.logline(output,'PREPARE: one fixed calibration-transfer model comparison; freeze before qualification')
    check('integrity','completed audit manifest',M.identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = {r['path']:r for group in ('inputs','outputs','preserved') for r in prior[group]}
    paths = [PREVIOUS/'MANIFEST.json', SOURCE/'FEP_C3_RECOVERY_AUDIT_V1_REPORT.md', SOURCE/'FEP_C3_RECOVERY_AUDIT_V1_CHECKPOINT.md', SOURCE/'readback_fep_c3_recovery_audit.py']
    paths += sorted((PREVIOUS.parent/'readback-2026-10-08').iterdir())
    for attempt in sorted(ROOT.glob('attempt-*')):
        if attempt != output:
            paths += sorted(p for p in attempt.rglob('*') if p.is_file())
    for path in paths:
        preserved[str(path)] = M.identity(path)
    M.verify(list(preserved.values()))
    inputs = []
    source_names = ('FEP_CALIBRATED_CHANGE_V1.md','check_fep_calibrated_change.py','qualify_fep_calibrated_change.py','FEP_CALIBRATED_CHANGE_V1_CORRECTION.md')
    for name in source_names:
        inputs.append(M.identity(SOURCE/name))
        shutil.copyfile(SOURCE/name,output/'inputs'/name)
    pop = population()
    M.write(output/'POPULATION.json',dict(bases=pop,conditions=CONDITIONS,arms=ARMS,coefficients={g:v.tolist() for g,v in coefficients().items()},coefficient_denominator=18))
    seeds = {m['label']:[str(M.seed_for(m['label'],i,PREFIX)) for i in range(1024)] for m in pop}
    flips = {m['label']:[str(M.seed_for(m['label'],i,PREFIX+'-transfer-flips')) for i in range(1024)] for m in pop}
    new = {x for d in (seeds,flips) for row in d.values() for x in row}
    check('seeds','distinct main and flip seeds',len(new) == 55296)
    for study in ('fep-changing-world-v1','fep-future-aware-checking-v1','fep-three-decision-checking-v1'):
        old = json.loads((ROOT.parent/study/'attempt-01/SEEDS.json').read_text())['blocks']
        check('seeds','separate from '+study,not new.intersection(x for row in old.values() for x in row))
    for prefix in ('qualification-'+PREFIX,'parallel-'+PREFIX,'benchmark-'+PREFIX):
        synthetic_seeds = {str(M.seed_for(A.synthetic()['label'],i,p)) for i in range(128) for p in (prefix,prefix+'-transfer-flips')}
        check('seeds','synthetic separation '+prefix,not new.intersection(synthetic_seeds))
    M.write(output/'SEEDS.json',dict(root=20260924,main_prefix=PREFIX,flip_prefix=PREFIX+'-transfer-flips',
        rng='Python random.Random MT19937',python=platform.python_version(),core_draw_order=M.streams.__doc__,
        flip_draw_order='two random() values per task; each flip iff value < 1/4',blocks=seeds,flip_blocks=flips,overlap_with_previous=0))
    inputs += [M.identity(output/'POPULATION.json'),M.identity(output/'SEEDS.json')]
    snapshots = [M.identity(p) for p in sorted((output/'inputs').iterdir())]
    check('integrity','source snapshots',sorted(x['sha256'] for x in inputs[:len(source_names)]) == sorted(x['sha256'] for x in snapshots))
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources','four CPUs available',len(cpus)==4)
    M.write(output/'PREPARATION.json',dict(started_utc=M.now(),inputs=inputs,source_snapshots=snapshots,preserved=list(preserved.values()),
        storage=storage,cpus=cpus,python=platform.python_version(),numpy=np.__version__))
    M.pin_cpus(cpus)
    import qualify_fep_calibrated_change as Q
    qualification = Q.qualify(sys.modules[__name__],cpus)
    M.write(output/'QUALIFICATION.json',qualification)
    M.logline(output,f'QUALIFIED: {qualification["assertions"]} assertions; {qualification["wall_seconds"]:.3f}s')
    jobs = [(extend_meta(A.synthetic()),list(range(i*32,(i+1)*32)),'benchmark-'+PREFIX,None) for i in range(4)]
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(cpus,)) as pool:
        records = list(pool.map(worker,jobs))
    elapsed = perf_counter()-start
    forecast = 120+3*elapsed*27648/128
    M.write(output/'BENCHMARK.json',dict(wall_seconds=elapsed,forecast_seconds=forecast,requires_detached=forecast>600,
        workers=4,synthetic_blocks=128,conditions_per_block=19,arms=9,records=records,
        rule='120 + 3 * four-worker wall * 27648 / 128; no outcome selection'))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output,f'PREPARED: forecast {forecast:.3f}s; detached={forecast>600}; main outcomes unread')
    print(json.dumps(dict(qualification=qualification,forecast_seconds=forecast,requires_detached=forecast>600,preserved_identities=len(preserved))))


def execute(output,detached):
    start,cpu = perf_counter(),process_time()
    prep = json.loads((output/'PREPARATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    check('execution','not started',not (output/'EXECUTION_STARTED.json').exists())
    check('execution','qualified',json.loads((output/'QUALIFICATION.json').read_text())['status']=='PASS')
    check('execution','detachment rule',detached or not bench['requires_detached'])
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    mount_check(output); M.pin_cpus(prep['cpus'])
    M.write(output/'EXECUTION_STARTED.json',dict(started_utc=M.now(),pid=os.getpid(),detached=detached,workers=4,cpus=prep['cpus'],benchmark=M.identity(output/'BENCHMARK.json')))
    M.logline(output,'MAIN STARTED: 216 fixed chunks, 27648 fresh blocks, 513 conditions, nine arms')
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(m,list(range(i,i+128)),PREFIX,str(output)) for m in pop for i in range(0,1024,128)]
    records = []
    with ProcessPoolExecutor(max_workers=4,initializer=M.pin_cpus,initargs=(prep['cpus'],)) as pool:
        for i,record in enumerate(pool.map(worker,jobs),1):
            records.append(record)
            if i % 8 == 0:
                M.logline(output,f'COMPLETED {i}/216 chunks; {record["label"]}')
    M.write(output/'WORKERS.json',records)
    results = aggregate(output,pop)
    M.write(output/'RESULTS.json',results)
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved']+[r['record'] for r in records])
    M.logline(output,f'COMPLETE: {perf_counter()-start:.3f}s; all five criteria and signed outcomes retained')
    outputs = [M.identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
    M.write(output/'MANIFEST.json',dict(status='COMPLETE',started_utc=json.loads((output/'EXECUTION_STARTED.json').read_text())['started_utc'],finished_utc=M.now(),
        wall_seconds=perf_counter()-start,parent_cpu_seconds=process_time()-cpu,worker_cpu_seconds=sum(r['cpu_seconds'] for r in records),workers=4,cpus=prep['cpus'],
        python=platform.python_version(),numpy=np.__version__,inputs=prep['inputs'],preserved=prep['preserved'],outputs=outputs,
        summary=results['summary'],criteria=results['criteria'],checks=dict(CHECKS),identity_checks=dict(M.CHECKS)))


def launch(output):
    check('launch','prepared',(output/'BENCHMARK.json').is_file())
    check('launch','not launched',not (output/'EXECUTION_STARTED.json').exists() and not (output/'LAUNCH.json').exists())
    with (output/'DETACHED_STDOUT.log').open('xb') as stream:
        child = subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'execute','--output',str(output),'--detached'],
            stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,cwd=SOURCE,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    receipt = dict(pid=child.pid,launched_utc=M.now(),automatic_polling=False,benchmark=M.identity(output/'BENCHMARK.json'))
    M.write(output/'LAUNCH.json',receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase',choices=('prepare','execute','launch'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--detached',action='store_true')
    args = parser.parse_args()
    check('scope','new study namespace',args.output.parent == ROOT and args.output.name.startswith('attempt-'))
    try:
        {'prepare':lambda:prepare(args.output),'execute':lambda:execute(args.output,args.detached),'launch':lambda:launch(args.output)}[args.phase]()
    except Exception:
        if args.output.is_dir():
            path = args.output/f'FAILURE_{args.phase}.json'
            if not path.exists():
                M.write(path,dict(phase=args.phase,utc=M.now(),traceback=traceback.format_exc(),checks=dict(CHECKS)))
            M.logline(args.output,f'FAILED {args.phase}; preserve attempt')
        raise
