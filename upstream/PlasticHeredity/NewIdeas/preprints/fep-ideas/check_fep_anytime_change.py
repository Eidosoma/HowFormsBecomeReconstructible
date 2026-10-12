#!/usr/bin/env python3
"""One frozen temporal-support extension; unchanged physical traces and controls."""
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
import shutil
import subprocess
from time import perf_counter, process_time
import traceback

SOURCE = Path(__file__).resolve().parent
EXPECTED = {
    'check_fep_unexpected_change.py': '1fbe502e9a96c75dd14eea06ab9f79cc6c0275476a28855e763f8bcb139fceb8',
    'FEP_UNEXPECTED_CHANGE_V1.md': 'd232ab76a9459e91488037ed62bf0b8fb6fda8804ec3550dcf902aa1869371cf',
    'FEP_UNEXPECTED_CHANGE_V1_REPORT.md': '17561fa4dc87201f403593f28f7caf5101c89da365ae89d100ecd5e5257b3cf4',
    'FEP_UNEXPECTED_CHANGE_V1_CHECKPOINT.md': 'd397f2eeac128c30ce37ce9497f68b730b5299f3c7a851a0c29fbe8a85125880',
    'readback_fep_unexpected_change.py': 'c837c8a700af9f8f90187800be57d2eaf3c3adff5dd5a6ffe7a91b07f1988b69',
}
for _name, _digest in EXPECTED.items():
    assert sha256((SOURCE/_name).read_bytes()).hexdigest() == _digest, _name
import check_fep_unexpected_change as U
import numpy as np
S, M, B, T = U.S, U.M, U.B, U.T
ci, stats_int = S.ci, S.stats_int
CONDITIONS, FAMILIES, UNEXPECTED, WINDOWS = U.CONDITIONS, U.FAMILIES, U.UNEXPECTED, U.WINDOWS
PHASES, SUMS = U.PHASES, U.SUMS
POST_SCALE, POST_DEN = U.POST_SCALE, U.POST_DEN
coefficients, panels = U.coefficients, U.panels
ARMS = (*U.ARMS, 'CT3-anytime')
PRIMARY, PRIMARY_INDEX = ARMS[-1], 9
BOUNDARIES = tuple(range(1, 101))
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-change-v1')
PREVIOUS = U.ROOT/'attempt-01'
PREVIOUS_SHA = 'aa265d528554fab766ca1614ce7629e620522b7cd9fddc6445612b465e45b586'
PREFIX = 'fep-anytime-change-v1'
FIELDS = (*U.FIELDS, 'anytime_alarm', 'anytime_episode_sums')
FALLBACKS = (*U.FALLBACKS, 'anytime_fallback')
CHUNK = 32
CHECKS = {}


def check(group, name, ok):
    if not bool(ok):
        raise AssertionError(group+': '+name)
    CHECKS[group] = CHECKS.get(group, 0)+1


class Filter:
    """Explicit exact mixture: no change, then each supplied time and kind."""
    def __init__(self, counts, boundaries=BOUNDARIES):
        self.boundaries = tuple(boundaries)
        check('model', 'ordered unique times within episode', self.boundaries == tuple(sorted(set(self.boundaries)))
              and self.boundaries and min(self.boundaries) >= 1 and max(self.boundaries) <= 100)
        self.times = np.array([101]+[t for t in self.boundaries for _ in range(3)])
        self.kinds = np.array([0]+[0, 1, 2]*len(self.boundaries))
        self.counts = np.array(counts, dtype=np.int16, copy=True)
        self.n, self.nh = len(counts), len(self.times)
        self.priors = [F(1, 2)]+[F(1, 6*len(self.boundaries))]*(self.nh-1)
        check('model', 'normalized prior', sum(self.priors) == 1)
        self.w = np.broadcast_to(np.array(self.priors, dtype=float), (self.n, self.nh)).copy()
        self.p = np.broadcast_to(M.initial_parameters(counts)[:, None, :], (self.n, self.nh, 6)).copy()
        self.reset = np.broadcast_to(M.PRIOR, (1, self.nh, 6)).copy()
        self.reset[:, self.kinds != 0, 2:4] = (1., 2.)
        self.ys = np.zeros((self.n, 100), dtype=np.int8)
        self.labels = np.full((self.n, 100), -1, dtype=np.int8)
        self.fallback = 0
        self.t = 0

    def active(self, t):
        return np.where(self.times <= t, self.kinds, 0)

    def advance(self, p, t):
        if t in self.boundaries:
            p = p.copy()
            selected = self.times == t
            p[:, selected] = self.reset[:, selected]
        return p

    def before(self, w, p, t, steps, retain=True):
        if steps == 0:
            return np.zeros(len(w))
        p = self.advance(p, t)
        kind = self.active(t)
        value = np.zeros(len(w))
        for parity in (False, True):
            z = np.full(len(w), parity)
            mass, pp = S.observe_warning(w, p, z, kind)
            r, q, _ = self.scores(mass, pp, z, t, steps, retain)
            value += np.minimum(r, q)
        return value

    def scores(self, w, p, z, t, steps=3, retain=True):
        steps = min(steps, 101-t)
        kind = self.active(t)
        one = (w*S.orientation(p, z, kind)).sum(axis=1)
        total = w.sum(axis=1)
        risk = np.minimum(one, total-one)
        if steps == 1:
            return risk, .1*total, np.zeros(len(w))
        v0 = self.before(w, p, t+1, steps-1, retain)
        v1 = np.zeros(len(w)) if retain else v0
        if retain:
            for x in (False, True):
                ww, pp = S.observe_label(w, p, z, x, kind)
                v1 += self.before(ww, pp, t+1, steps-1, retain)
        return risk+v0, .1*total+v1, v0-v1

    def start(self, t):
        self.t = t
        self.p = self.advance(self.p, t)

    def warning(self, y):
        self.ys[:, self.t-1] = y
        self.z = ((y >> 1) ^ (y & 1)).astype(bool)
        self.w, self.p = S.observe_warning(self.w, self.p, self.z, self.active(self.t))
        norm = self.w.sum(axis=1, keepdims=True)
        check('inference', 'positive warning evidence', np.all(norm > 0))
        self.w /= norm
        self.u = (self.w*S.orientation(self.p, self.z, self.active(self.t))).sum(axis=1)
        return self.u.copy()

    def choose(self, steps=3, retain=True):
        r, q, delta = self.scores(self.w, self.p, self.z, self.t, steps, retain)
        y = self.ys[:, self.t-1]
        action = np.where(q <= r, 2, (y >> 1) ^ (self.u > .5)).astype(np.int8)
        myopic = np.where(np.minimum(self.u, 1-self.u) >= .1, 2, (y >> 1) ^ (self.u > .5)).astype(np.int8)
        near = (np.abs(r-q) <= 1e-12) | (np.abs(np.minimum(self.u, 1-self.u)-.1) <= 1e-12)
        if near.any():
            from qualify_fep_anytime_change import rational_state, direct_scores, exact_action
            for row in np.flatnonzero(near):
                hist = [(int(self.ys[row, k]), None if self.labels[row, k] < 0 else int(self.labels[row, k])) for k in range(self.t-1)]
                w, p, reset = rational_state(self.counts[row], hist, int(y[row]), self.boundaries)
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
        self.w, self.p = S.observe_label(self.w, self.p, self.z, x, self.active(self.t), labels >= 0)
        norm = self.w.sum(axis=1, keepdims=True)
        check('inference', 'positive paid-label evidence', np.all(norm > 0))
        self.w /= norm

    def diagnosis(self):
        changed = self.times <= self.t
        return np.stack([self.w[:, ~changed].sum(axis=1)]+[
            self.w[:, changed & (self.kinds == k)].sum(axis=1) for k in range(3)], axis=-1)


def new_batch(meta, indices, prefix, boundaries=BOUNDARIES):
    """Only the new learner; physical labels/laws stay in this evaluator."""
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
        action, delta, gain, extra = f.choose()
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


def run_batch(meta, indices, prefix):
    start, cpu = perf_counter(), process_time()
    old, old_record = U.run_batch(meta, indices, prefix)
    new = new_batch(meta, indices, prefix)
    for key in new:
        old[key] = np.concatenate((old[key], new[key]), axis=2) if key in old else new[key]
    return old, dict(wall_seconds=perf_counter()-start, cpu_seconds=process_time()-cpu,
        old_policy_wall_seconds=old_record['wall_seconds'], cpus=sorted(os.sched_getaffinity(0)), checks=dict(CHECKS))


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


def arm_summary(num, den, offset=0.):
    return dict(arms={arm: stats_int(num[..., i], den, offset) for i, arm in enumerate(ARMS)},
                contrasts={'CT3-anytime_minus_'+arm: stats_int(num[..., 9]-num[..., i], den) for i, arm in enumerate(ARMS) if i != 9},
                CT3_anytime_minus_always=stats_int(num[..., 9], den, offset-.1))


def verdicts(result, schedule='unexpected'):
    post = result['post_change'][schedule+'_core_changed']
    full = result['episode'][schedule+'_core_full']
    return dict(economical_core_recovery=post['CT3_anytime_minus_always']['upper95'] < 0,
                better_than_flat_recovery=post['contrasts']['CT3-anytime_minus_CT3-flat']['upper95'] < 0,
                better_than_flat_full_core=full['contrasts']['CT3-anytime_minus_CT3-flat']['upper95'] < 0)


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
            if ai != 3:
                diagnostics[group]['contrasts']['CT3-anytime_minus_'+arm] = {phase:{name:ci(v[...,3,pi]-v[...,ai,pi]) for name,v in metrics.items()} for pi,phase in enumerate(PHASES)}
            first = rows['first_post_reference'][...,6+ai]
            wait = np.maximum(first-np.array([t for _,t in CONDITIONS])[None,None,:],0)
            diagnostics[group]['query'][arm] = dict(purchase_probability=ci(np.einsum('k,brk->br',co/144,first<101)),
                                                    waiting_tasks=ci(np.einsum('k,brk->br',co/144,wait)))
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
    signs = {}
    for panel, indices in panels().items():
        signs[panel] = {}
        for endpoint,data in (('episode',units),('post_change',post)):
            signs[panel][endpoint] = {}
            for ai,arm in enumerate(ARMS):
                if ai == 9:
                    continue
                tally = dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
                for bi in range(nb):
                    for j in indices:
                        if not j and endpoint == 'post_change':
                            continue
                        d = data[bi,:,j,9]-data[bi,:,j,ai]
                        den = 1000 if endpoint == 'episode' else 10*(101-CONDITIONS[j][1])
                        c = stats_int(d,den)
                        for name,yes in (('point_lower',int(d.sum())<0),('point_equal',int(d.sum())==0),('point_higher',int(d.sum())>0),('upper_below_zero',c['upper95']<0),('lower_above_zero',c['lower95']>0)):
                            tally[name] += int(yes)
                signs[panel][endpoint][arm] = tally
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
        objective='three-decision expected task cost; exact conditional VFE/Bayesian belief inference',
        new_policies=1, tuned_after_outcomes=False, old_cohort_pooled=False),
        episode=episode, post_change=post_change, conditions=conditions, condition_counts=signs,
        diagnostics=diagnostics, planning=planning, posterior=posterior, early_recovery=windows,
        unexpected_minus_supported=sensitivity)
    # Stable costs are separate, including all original controls.
    stable = {}
    for name, data in (('wrong_cost', rows['wrong'][:,:,0]/100),
                       ('purchase_cost', rows['references'][:,:,0]/1000)):
        stable[name] = dict(arms={arm:ci(data[...,ai]) for ai,arm in enumerate(ARMS)},
            contrasts={'CT3-anytime_minus_'+arm:ci(data[...,9]-data[...,ai]) for ai,arm in enumerate(ARMS) if ai != 9})
    stable['total_cost'] = episode['stable']
    aa = rows['anytime_alarm'][:,:,0]
    stable['posterior_false_alarms'] = dict(
        tasks_above_half=ci(aa[...,0]), probability_ever_above_half=ci(aa[...,0]>0),
        first_crossing_censored_at_101=ci(aa[...,1]), mean_change_probability=ci(aa[...,2]/100),
        threshold=.5, update_stage='after available paid label; descriptive, not an action')
    es = rows['anytime_episode_sums'][:,:,0]/100
    stable['CT3_anytime_evaluator'] = {name:ci(es[...,i]) for i,name in enumerate(SUMS)}
    stable['CT3_anytime_evaluator'].update(
        conditional_regret=ci(es[...,2:5].sum(axis=-1)),
        risk_underestimate=ci(es[...,0]-es[...,5]),
        realization_residual=ci((10*rows['wrong'][:,:,0,9]+rows['references'][:,:,0,9])/1000-es[...,0]))
    result['stable_costs'] = stable
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
        for first in range(0,1024,CHUNK):
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
    storage = mount_check(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    (output/'blocks').mkdir()
    M.logline(output, 'PREPARE: new anytime model with unchanged controls and physical population; fresh paired seeds')
    check('integrity', 'completed timing-challenge manifest', M.identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    check('integrity', 'previous study complete', prior['status'] == 'COMPLETE')
    preserved = {r['path']: r for group in ('inputs', 'outputs', 'preserved') for r in prior[group]}
    paths = [PREVIOUS/'MANIFEST.json']+[SOURCE/name for name in EXPECTED]
    paths += sorted((PREVIOUS.parent/'readback-2026-10-10').iterdir())
    paths += [SOURCE/'FEP_ANYTIME_CHANGE_V1_CORRECTION.md', ROOT/'diagnostic-01/NORMALIZATION.json']
    for attempt in sorted(ROOT.glob('attempt-*')):
        if attempt != output:
            paths += sorted(p for p in attempt.rglob('*') if p.is_file())
    for path in paths:
        preserved[str(path)] = M.identity(path)
    M.verify(list(preserved.values()))
    inputs = []
    for name in ('FEP_ANYTIME_CHANGE_V1.md', Path(__file__).name, 'qualify_fep_anytime_change.py'):
        inputs.append(M.identity(SOURCE/name))
        shutil.copyfile(SOURCE/name, output/'inputs'/name)
    pop = S.population()
    previous_population = json.loads((PREVIOUS/'POPULATION.json').read_text())
    check('population', 'base laws unchanged', pop == previous_population['bases'])
    check('population', 'all physical conditions unchanged', [list(x) for x in CONDITIONS] == previous_population['conditions'])
    M.write(output/'POPULATION.json', dict(bases=pop, conditions=CONDITIONS, arms=ARMS,
            coefficients={k: v.tolist() for k, v in coefficients().items()}, coefficient_denominator=144,
            post_scale=POST_SCALE, learner_change_times=BOUNDARIES, old_learner_change_times=M.BOUNDARIES,
            model_prior=dict(no_change='1/2', per_time_kind='1/600', kinds=['G','A','B'],
                             conditional_hazard='1/(201-t)', hypotheses=301), unexpected_physical_times=UNEXPECTED,
            windows=[dict(start=t, tasks=min(25, 101-t)) for t in WINDOWS]))
    seeds = {m['label']: [str(M.seed_for(m['label'], i, PREFIX)) for i in range(1024)] for m in pop}
    flips = {m['label']: [str(M.seed_for(m['label'], i, PREFIX+'-transfer-flips')) for i in range(1024)] for m in pop}
    fresh = {x for values in (seeds, flips) for row in values.values() for x in row}
    check('seeds', 'unique core/flip seeds', len(fresh) == 55296)
    seed_sources = [PREVIOUS/'SEEDS.json', U.PREVIOUS/'SEEDS.json', S.ROOT/'attempt-02/SEEDS.json']+[ROOT.parent/study/'attempt-01/SEEDS.json' for study in
                  ('fep-changing-world-v1', 'fep-future-aware-checking-v1', 'fep-three-decision-checking-v1')]
    for path in seed_sources:
        old = json.loads(path.read_text())
        previous = {x for group in ('blocks', 'flip_blocks') for row in old.get(group, {}).values() for x in row}
        check('seeds', 'separation from '+str(path), not fresh.intersection(previous))
    for study_prefix in (PREFIX, U.PREFIX, 'fep-weak-prior-confirmation-v1', S.PREFIX, S.T.PREFIX, S.B.PREFIX, 'fep-changing-world-v1'):
        for purpose in ('qualification-', 'parallel-', 'benchmark-'):
            prefix = purpose+study_prefix
            synthetic = {str(M.seed_for(S.A.synthetic()['label'], i, p)) for i in range(128)
                         for p in (prefix, prefix+'-transfer-flips')}
            check('seeds', 'synthetic separation '+prefix, not fresh.intersection(synthetic))
    M.write(output/'SEEDS.json', dict(root=20260924, main_prefix=PREFIX, flip_prefix=PREFIX+'-transfer-flips',
            rng='Python random.Random MT19937', python=platform.python_version(), core_draw_order=M.streams.__doc__,
            flip_draw_order='two random() values per task; each flip iff value < 1/4',
            blocks=seeds, flip_blocks=flips, overlap_with_previous=0, selected_after_previous_results=True))
    inputs += [M.identity(output/'POPULATION.json'), M.identity(output/'SEEDS.json')]
    snapshots = [M.identity(p) for p in sorted((output/'inputs').iterdir())]
    check('integrity', 'source snapshot identity', sorted(x['sha256'] for x in inputs[:3]) == sorted(x['sha256'] for x in snapshots))
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources', 'four CPUs available', len(cpus) == 4)
    M.write(output/'PREPARATION.json', dict(started_utc=M.now(), inputs=inputs, source_snapshots=snapshots,
            preserved=list(preserved.values()), storage=storage, cpus=cpus, python=platform.python_version(), numpy=np.__version__,
            imported_policy=M.identity(SOURCE/'check_fep_calibrated_change.py'), source_manifest=M.identity(PREVIOUS/'MANIFEST.json'),
            primary=PRIMARY, new_policy_implementations=1, new_seeds=True, old_cohort_pooled=False))
    M.logline(output, 'FROZEN: design, new model and scalar reference, unchanged 43-condition population, fresh seeds and inherited evidence')
    M.pin_cpus(cpus)
    from qualify_fep_anytime_change import qualify
    qualification = qualify(sys.modules[__name__], cpus)
    M.write(output/'QUALIFICATION.json', qualification)
    M.logline(output, f'QUALIFIED: wrapper {qualification["assertions"]} assertions; {qualification["wall_seconds"]:.3f}s')
    jobs = [(S.extend_meta(S.A.synthetic()), list(range(i*8, (i+1)*8)), 'benchmark-'+PREFIX, None) for i in range(4)]
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        records = list(pool.map(worker, jobs))
    elapsed = perf_counter()-start
    forecast = 120+3*elapsed*27648/32
    M.write(output/'BENCHMARK.json', dict(wall_seconds=elapsed, forecast_seconds=forecast, requires_detached=forecast > 600,
            workers=4, synthetic_blocks=32, conditions_per_block=43, arms=10, records=records,
            rule='120 + 3 * four-worker wall * 27648 / 32; no outcome selection'))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output, f'PREPARED: forecast {forecast:.3f}s; detached={forecast > 600}; main outcomes unread')
    print(json.dumps(dict(qualification_status=qualification['status'], assertions=qualification['assertions'], benchmark_seconds=elapsed, forecast_seconds=forecast,
                         requires_detached=forecast > 600, preserved_identities=len(preserved))))


def execute(output, detached):
    start, cpu = perf_counter(), process_time()
    prep = json.loads((output/'PREPARATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    check('execution', 'not started', not (output/'EXECUTION_STARTED.json').exists())
    check('execution', 'qualified', json.loads((output/'QUALIFICATION.json').read_text())['status'] == 'PASS')
    check('execution', 'prelaunch verified', json.loads((output/'PRELAUNCH.json').read_text())['status'] == 'PASS')
    check('execution', 'detachment rule', detached or not bench['requires_detached'])
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    mount_check(output)
    M.pin_cpus(prep['cpus'])
    M.write(output/'EXECUTION_STARTED.json', dict(started_utc=M.now(), pid=os.getpid(), detached=detached,
            workers=4, cpus=prep['cpus'], benchmark=M.identity(output/'BENCHMARK.json'), primary=PRIMARY))
    M.logline(output, 'MAIN STARTED: 864 fixed chunks, 27648 fresh blocks, 1161 conditions, nine unchanged arms plus CT3-anytime')
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(meta, list(range(i, i+CHUNK)), PREFIX, str(output)) for meta in pop for i in range(0, 1024, CHUNK)]
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
            checks=dict(CHECKS), shared_checks=dict(S.CHECKS), identity_checks=dict(M.CHECKS)))


def launch(output):
    check('launch', 'prepared', (output/'BENCHMARK.json').is_file())
    check('launch', 'not launched', not (output/'EXECUTION_STARTED.json').exists() and not (output/'LAUNCH.json').exists())
    with (output/'DETACHED_STDOUT.log').open('xb') as stream:
        child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), 'execute', '--output', str(output), '--detached'],
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
                cwd=SOURCE, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    receipt = dict(pid=child.pid, launched_utc=M.now(), automatic_polling=False, benchmark=M.identity(output/'BENCHMARK.json'))
    M.write(output/'LAUNCH.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'execute', 'launch'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    check('scope', 'dedicated attempt directory', args.output.parent == ROOT and args.output.name.startswith('attempt-'))
    try:
        {'prepare': lambda: prepare(args.output), 'execute': lambda: execute(args.output, args.detached), 'launch': lambda: launch(args.output)}[args.phase]()
    except Exception:
        if args.output.is_dir():
            path = args.output/f'FAILURE_{args.phase}.json'
            if not path.exists():
                M.write(path, dict(phase=args.phase, utc=M.now(), traceback=traceback.format_exc(), checks=dict(CHECKS)))
            M.logline(args.output, f'FAILED {args.phase}; preserve attempt')
        raise
