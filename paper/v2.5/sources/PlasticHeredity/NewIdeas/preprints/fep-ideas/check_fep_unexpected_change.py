#!/usr/bin/env python3
"""Unexpected physical timing; fixed policies imported from their previous freeze."""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
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
import statistics
import random
from fractions import Fraction as F
import subprocess
from time import perf_counter, process_time
import traceback

SOURCE = Path(__file__).resolve().parent
EXPECTED = {
    'check_fep_weak_prior_confirmation.py': '695179dab393c7428d04434b57d64ed9ce3c1196eeebc54589f0878f0308b57c',
    'FEP_WEAK_PRIOR_CONFIRMATION_V1.md': '26bdbf79f07405e8a7fbc3fe241bbd48880a6d867ce18352f9a9668da1d74422',
    'FEP_WEAK_PRIOR_CONFIRMATION_V1_REPORT.md': '801ebc5585221000e88d1644f8fa4e8dee27030495743e1eab38165e41af5af3',
    'FEP_WEAK_PRIOR_CONFIRMATION_V1_CHECKPOINT.md': '0af78c380a55a8cf07e08406f69adcc7a962480785bfff4a2213d75d0efa55b0',
    'readback_fep_weak_prior_confirmation.py': 'b2bc0e8e3c1d0780ac67e1c4014a916a219505197563821289064503a5fe2e68',
    'check_fep_calibrated_change.py': 'e35042ba9fecb2dea137d67b1ecca9b97a657ec336fb9a60fc693a10efadb004',
    'qualify_fep_calibrated_change.py': '03e006607dbfe57f8c16185254d57403eda682d79bcf543861d837c13b59470a',
    'FEP_CALIBRATED_CHANGE_V1.md': 'f6d357321240dab27c244d5bcb711a0247398eac6cab8ef624f5dbbaa1691e31',
    'FEP_CALIBRATED_CHANGE_V1_REPORT.md': 'db405bdbdf78f512c34ed6d000cd6b61a0dd7c57a307c3d2d888fdcdcfae8537',
    'FEP_CALIBRATED_CHANGE_V1_CHECKPOINT.md': '5f4e576b0c36d5d16e56be471f9ac1b5c6d86c7e8ea221a22f06c7e5429e9a24',
    'readback_fep_calibrated_change.py': '727c1a3d4323f4cecefcaecac3078a1de030d3f89bea09f68f34b9b22766ab01',
}
for _name, _digest in EXPECTED.items():
    assert sha256((SOURCE/_name).read_bytes()).hexdigest() == _digest, _name
import check_fep_calibrated_change as S
import qualify_fep_calibrated_change as Q
import numpy as np

M, B, T = S.M, S.B, S.T
ARMS, PHASES, SUMS = S.ARMS, S.PHASES, S.SUMS
ci, stats_int = S.ci, S.stats_int
FAMILIES = ('A_loss', 'B_loss', 'reverse', 'A_partial', 'B_partial', 'both_partial')
UNEXPECTED = (13, 38, 63, 88)
CONDITIONS = S.CONDITIONS+[(f, t) for f in FAMILIES for t in UNEXPECTED]
WINDOWS = tuple(sorted((*M.BOUNDARIES, *UNEXPECTED)))
POST_SCALE = 34234200
WEIGHT_DEN = 144
POST_DEN = WEIGHT_DEN*10*POST_SCALE
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-unexpected-change-v1')
PREVIOUS = ROOT.parent/'fep-weak-prior-confirmation-v1/attempt-01'
PREVIOUS_SHA = '88ce572779080f3a0ac29ef4d99b11c445d4b0293b4a8dcaeac3f80c45a1d36a'
PREFIX = 'fep-unexpected-change-v1'
PRIMARY = 'CT3-flat'
PRIMARY_INDEX = S.ARMS.index(PRIMARY)
FIELDS = ('wrong', 'references', 'post_wrong', 'post_references', 'window_wrong', 'window_references',
          'first_post_reference', 'phase_counts', 'phase_sums', 'candidate_extra_references', 'candidate_values', 'diagnosis')
FALLBACKS = ('planner_fallbacks', 'control_fallback', 'c2_inference_fallback', 'c3_inference_fallback', 'candidate_fallback')
CHECKS = {}


def check(group, name, ok):
    if not bool(ok):
        raise AssertionError(group+': '+name)
    CHECKS[group] = CHECKS.get(group, 0)+1


def physical_trace(meta, indices, prefix, legacy=False):
    """Change physical onset only; no timing metadata is passed to a policy."""
    conditions = S.CONDITIONS if legacy else CONDITIONS
    cal, world, error, bit_a, bit_b = M.streams(meta, indices, prefix)
    b, nc = len(indices), len(conditions)
    flips = np.zeros((b, 100, 2), dtype=np.int8)
    for row, block in enumerate(indices):
        rng = random.Random(M.seed_for(meta['label'], block, prefix+'-transfer-flips'))
        for t in range(100):
            flips[row, t] = (rng.random() < .25, rng.random() < .25)
    errors = np.broadcast_to(error[:, None, :], (b, nc, 100)).copy()
    laws = np.broadcast_to(np.array(list(map(float, map(F, meta['laws'][0])))), (nc, 100, 4)).copy()
    for j, (family, tau) in enumerate(conditions[1:], 1):
        if family == 'A_loss':
            changed = (bit_a << 1) | (error & 1)
        elif family == 'B_loss':
            changed = (error & 2) | bit_b
        elif family == 'reverse':
            changed = error ^ 3
        else:
            mask = (2*flips[..., 0] if family != 'B_partial' else 0)+(flips[..., 1] if family != 'A_partial' else 0)
            changed = error ^ mask
        errors[:, j, tau-1:] = changed[:, tau-1:]
        laws[j, tau-1:] = list(map(float, map(F, meta['laws'][1+FAMILIES.index(family)])))
    truth = np.broadcast_to(world[:, None, :], errors.shape).copy()
    return cal, errors ^ (3*truth), truth, laws


def run_batch(meta, indices, prefix, legacy=False):
    start, cpu = perf_counter(), process_time()
    conditions = S.CONDITIONS if legacy else CONDITIONS
    windows = M.BOUNDARIES if legacy else WINDOWS
    lengths = np.array([min(25, 101-t) for t in windows])
    nc, b = len(conditions), len(indices)
    n = b*nc
    cal, warnings, truth, laws = physical_trace(meta, indices, prefix, legacy)
    y, target = warnings.reshape(n, 100), truth.reshape(n, 100)
    counts = np.repeat(cal, nc, axis=0)
    controls, c2, c3 = M.Filter(counts), M.Filter(counts), M.Filter(counts)
    candidate = S.Filter(np.tile(counts, (2,1)), np.repeat([True, False], n))
    wrong = np.zeros((n, 9), dtype=np.int16)
    refs, pw, pr = (np.zeros_like(wrong) for _ in range(3))
    ww, wr = (np.zeros((n, 9, len(windows)), dtype=np.int16) for _ in range(2))
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
        for wi, begin in enumerate(windows):
            if begin <= t < min(begin+25, 101):
                ww[:,:,wi] += error
                wr[:,:,wi] += ask
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
        window_wrong=ww.reshape(b,nc,9,len(windows)), window_references=wr.reshape(b,nc,9,len(windows)),
        post_wrong=pw.reshape(b,nc,9), post_references=pr.reshape(b,nc,9), first_post_reference=first.reshape(b,nc,9),
        extra_references=ex3.reshape(b,nc,3), delta_sum=d3s.reshape(b,nc), selected_gain_sum=g3s.reshape(b,nc),
        own_c2_disagreements=disagreements.reshape(b,nc,2), c2_extra_references=ex2.reshape(b,nc,3),
        c2_delta_sum=d2s.reshape(b,nc), c2_selected_gain_sum=g2s.reshape(b,nc), planner_fallbacks=fallbacks,
        control_fallback=controls.fallback, c2_inference_fallback=c2.fallback, c3_inference_fallback=c3.fallback,
        candidate_fallback=np.array([candidate.fallback],dtype=np.int64),
        candidate_extra_references=candidate_extras.reshape(b,nc,2,3), candidate_values=candidate_values.reshape(b,nc,2,2),
        phase_counts=phase_counts.reshape(b,nc,3,3,3), phase_sums=phase_sums.reshape(b,nc,3,3,6),
        diagnosis=diagnosis.reshape(b,nc,2,4,4))
    check('accounting', 'episode/window counts', np.all(wrong+refs <= 100) and np.all(ww+wr <= lengths))
    check('accounting', 'phase errors', np.array_equal(phase_counts[...,1].sum(axis=-1), pw[:,6:]))
    check('accounting', 'phase references', np.array_equal(phase_counts[...,2].sum(axis=-1), pr[:,6:]))
    check('accounting', 'diagnosis normalized', np.allclose(diagnosis.sum(axis=-1), 1, atol=2e-15, rtol=0))
    for j, (_, t) in enumerate(conditions):
        if t == 101:
            check('accounting', 'no stable post endpoint', not out['post_wrong'][:,j].any() and not out['post_references'][:,j].any())
        else:
            for key, window in (('post_wrong','window_wrong'), ('post_references','window_references')):
                check('accounting', 'post/window identity', np.array_equal(out[key][:,j], np.take(out[window][:,j],
                    [wi for wi, start in enumerate(windows) if start >= t and start in (M.BOUNDARIES if t in M.BOUNDARIES else UNEXPECTED)], axis=-1).sum(axis=-1)))
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


def panels():
    return dict(supported_core=list(range(10)), supported_transfer=list(range(10, 19)),
                unexpected_core=[0]+list(range(19, 31)), unexpected_transfer=list(range(31, 43)),
                all=list(range(43)))


def coefficients():
    out = {'stable': np.array([144]+[0]*42, dtype=np.int64)}
    def add(name, selected):
        assert selected and 144 % len(selected) == 0
        out[name] = np.array([144//len(selected) if j in selected else 0 for j in range(43)], dtype=np.int64)
    for schedule, times in (('supported', M.BOUNDARIES), ('unexpected', UNEXPECTED)):
        for panel, families in (('core', FAMILIES[:3]), ('transfer', FAMILIES[3:])):
            selected = [j for j, (f, t) in enumerate(CONDITIONS) if f in families and t in times]
            name = schedule+'_'+panel
            add(name+'_changed', selected)
            out[name+'_full'] = out[name+'_changed']//2
            out[name+'_full'][0] = 72
            for t in times:
                add(name+'_T'+str(t), [j for j in selected if CONDITIONS[j][1] == t])
        add(schedule+'_core_reliability', [j for j, (f, t) in enumerate(CONDITIONS) if f in FAMILIES[:2] and t in times])
        for family in FAMILIES:
            add(schedule+'_'+family, [j for j, (f, t) in enumerate(CONDITIONS) if f == family and t in times])
    return out


def arm_summary(num, den, offset=0.):
    return dict(arms={arm: stats_int(num[..., i], den, offset) for i, arm in enumerate(ARMS)},
                contrasts={'CT3-flat_minus_'+arm: stats_int(num[..., 8]-num[..., i], den) for i, arm in enumerate(ARMS) if i != 8},
                CT3_flat_minus_always=stats_int(num[..., 8], den, offset-.1))


def verdicts(result, schedule='unexpected'):
    post = result['post_change'][schedule+'_core_changed']
    full = result['episode'][schedule+'_core_full']
    return dict(economical_core_recovery=post['CT3_flat_minus_always']['upper95'] < 0,
                better_than_C3_recovery=post['contrasts']['CT3-flat_minus_C3']['upper95'] < 0,
                better_than_C3_full_core=full['contrasts']['CT3-flat_minus_C3']['upper95'] < 0)


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
            if ai != 2:
                diagnostics[group]['contrasts']['CT3-flat_minus_'+arm] = {phase:{name:ci(v[...,2,pi]-v[...,ai,pi]) for name,v in metrics.items()} for pi,phase in enumerate(PHASES)}
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
                if ai == 8:
                    continue
                tally = dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
                for bi in range(nb):
                    for j in indices:
                        if not j and endpoint == 'post_change':
                            continue
                        d = data[bi,:,j,8]-data[bi,:,j,ai]
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
        learner_change_times=list(M.BOUNDARIES), unexpected_physical_times=list(UNEXPECTED),
        conditional_model='unchanged supplied hypotheses and timing; physical timing challenge only',
        objective='three-decision expected task cost; exact conditional VFE/Bayesian belief inference',
        new_policies=0, tuned_after_outcomes=False, old_cohort_pooled=False),
        episode=episode, post_change=post_change, conditions=conditions, condition_counts=signs,
        diagnostics=diagnostics, planning=planning, posterior=posterior, early_recovery=windows,
        unexpected_minus_supported=sensitivity)
    result['criteria'] = verdicts(result)
    result['supported_control_criteria'] = verdicts(result, 'supported')
    result['core_lead_confirmed'] = all(result['criteria'].values())
    return result


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


def qualify(cpus):
    started = perf_counter()
    inherited = Q.qualify(S, cpus)
    meta = S.extend_meta(S.A.synthetic())
    prefix = 'qualification-'+PREFIX
    old, _ = S.run_batch(meta, [0, 1], prefix)
    legacy, _ = run_batch(meta, [0, 1], prefix, legacy=True)
    check('bridge', 'same legacy fields', old.keys() == legacy.keys())
    for key in old:
        check('bridge', 'legacy array '+key, old[key].dtype == legacy[key].dtype and old[key].shape == legacy[key].shape and old[key].tobytes() == legacy[key].tobytes())
    arrays, _ = run_batch(meta, [0, 1, 2, 3], prefix)
    for key in old:
        if key in FALLBACKS:
            continue  # Global totals include the additional physical conditions.
        new = arrays[key][:2]
        if key not in ('indices', 'calibration'):
            new = new[:, :19]
            if key.startswith('window_'):
                new = np.take(new, [WINDOWS.index(t) for t in M.BOUNDARIES], axis=-1)
        check('bridge', 'original rows preserved '+key, old[key].dtype == new.dtype and old[key].shape == new.shape and old[key].tobytes() == new.tobytes())
    check('schedule', 'legacy learner schedule', M.BOUNDARIES == (26, 51, 76))
    for learner in (M.Filter(arrays['calibration']), S.Filter(arrays['calibration'], np.zeros(4, dtype=bool))):
        check('schedule', 'learner receives supported times only', learner.boundaries == (26, 51, 76))
    for t in UNEXPECTED:
        check('schedule', 'unexpected time is not a model boundary', t not in M.BOUNDARIES)
    cal, warnings, truth, laws = physical_trace(meta, [0, 1], prefix)
    # Separate scalar enumeration, including seed derivation and each RNG draw.
    q = list(map(float, map(F, meta['laws'][0])))
    cumulative = [sum(q[:i+1]) for i in range(4)]
    for block in (0, 1):
        def seeded(p):
            seed = int.from_bytes(sha256(f'{p}|20260924|{meta["label"]}|{block}'.encode('ascii')).digest(), 'big')
            return random.Random(seed)
        rng, flip = seeded(prefix), seeded(prefix+'-transfer-flips')
        counts = [0]*4
        for _ in range(64):
            r = rng.random()
            counts[next(i for i, c in enumerate(cumulative) if r < c)] += 1
        check('physical', 'scalar calibration', counts == cal[block].tolist())
        for t in range(1, 101):
            target = rng.getrandbits(1)
            r = rng.random()
            error = next(i for i, c in enumerate(cumulative) if r < c)
            a, b = rng.getrandbits(1), rng.getrandbits(1)
            fa, fb = flip.random() < .25, flip.random() < .25
            for j, (family, tau) in enumerate(CONDITIONS):
                value, law_index = error, 0
                if t >= tau:
                    law_index = FAMILIES.index(family)+1
                    if family == 'A_loss': value = 2*a+(error % 2)
                    elif family == 'B_loss': value = 2*(error//2)+b
                    elif family == 'reverse': value = 3-error
                    else:
                        if family != 'B_partial' and fa: value ^= 2
                        if family != 'A_partial' and fb: value ^= 1
                check('physical', 'scalar timing/truth/warning', truth[block, j, t-1] == target and warnings[block, j, t-1] == value ^ (3*target))
                check('physical', 'scalar onset law', np.array_equal(laws[j, t-1], list(map(float, map(F, meta['laws'][law_index])))))
    for key in ('wrong', 'references'):
        for j, (_, tau) in enumerate(CONDITIONS[1:], 1):
            schedule = M.BOUNDARIES if tau in M.BOUNDARIES else UNEXPECTED
            indices = [WINDOWS.index(t) for t in schedule if t >= tau]
            check('windows', 'own schedule partitions post-change', np.array_equal(
                arrays['post_'+key][:, j], np.take(arrays['window_'+key][:, j], indices, axis=-1).sum(axis=-1)))
    check('windows', 'late window has thirteen tasks', WINDOWS[-1] == 88 and np.all(
          arrays['window_wrong'][..., -1]+arrays['window_references'][..., -1] <= 13))
    check('arithmetic', 'post denominators exact', all(POST_SCALE % (101-t) == 0 for _, t in CONDITIONS[1:]))
    check('arithmetic', 'int64 cohort bound', 144*10*POST_SCALE*27648 < np.iinfo(np.int64).max)
    weights = coefficients()
    for name, co in weights.items():
        check('weights', 'normalized integer '+name, int(co.sum()) == 144 and np.all(co >= 0))
        if name.endswith('_full'):
            check('weights', 'half stability '+name, co[0] == 72 and np.count_nonzero(co[1:]) == (9 if name.startswith('supported') else 12))
        elif name.endswith('_changed'):
            check('weights', 'equal changed '+name, len(set(co[co > 0])) == 1 and co[0] == 0 and np.count_nonzero(co) == (9 if name.startswith('supported') else 12))
    rows = {k: arrays[k][None, ...] for k in FIELDS}
    result = analyze(rows, [meta])
    def scalar_ci(saved, values):
        mean = statistics.mean(values)
        se = (statistics.variance(values)/len(values))**.5
        actual = [saved[k] for k in ('mean', 'mc_se', 'lower95', 'upper95')]
        check('scalar', 'mean and uncertainty', max(abs(x-y) for x, y in zip(actual, (mean, se, mean-1.96*se, mean+1.96*se))) < 4e-13)
    def compare(saved, values):
        for ai, arm in enumerate(ARMS):
            scalar_ci(saved['arms'][arm], [v[ai] for v in values])
            if ai != 8:
                scalar_ci(saved['contrasts']['CT3-flat_minus_'+arm], [v[8]-v[ai] for v in values])
        scalar_ci(saved['CT3_flat_minus_always'], [v[8]-.1 for v in values])
    scalar_groups = {}
    for group, co in weights.items():
        for endpoint, wk, rk in (('episode', 'wrong', 'references'), ('post_change', 'post_wrong', 'post_references')):
            if endpoint == 'post_change' and (group == 'stable' or group.endswith('_full')): continue
            values = []
            for b in range(4):
                values.append([sum(int(co[j])*(int(arrays[wk][b, j, ai])+int(arrays[rk][b, j, ai])/10)/
                    (100 if endpoint == 'episode' else 101-tau)/144
                    for j, (_, tau) in enumerate(CONDITIONS) if co[j] and (endpoint == 'episode' or tau < 101))+
                    (.00064 if endpoint == 'episode' else 0) for ai in range(9)])
            scalar_groups[(endpoint, group)] = values
            compare(result[endpoint][group], values)
    for panel in ('core', 'transfer'):
        for endpoint, ending in (('episode', '_full'), ('post_change', '_changed')):
            u = scalar_groups[(endpoint, 'unexpected_'+panel+ending)]
            s = scalar_groups[(endpoint, 'supported_'+panel+ending)]
            for ai, arm in enumerate(ARMS):
                scalar_ci(result['unexpected_minus_supported'][panel][endpoint][arm], [u[b][ai]-s[b][ai] for b in range(4)])
    for wi, tau in enumerate(WINDOWS):
        length = min(25, 101-tau)
        for panel, families in (('stable', ()), ('core', FAMILIES[:3]), ('transfer', FAMILIES[3:])):
            chosen = [0] if panel == 'stable' else [j for j, (f, t) in enumerate(CONDITIONS) if f in families and t == tau]
            values = [[sum((int(arrays['window_wrong'][b, j, ai, wi])+int(arrays['window_references'][b, j, ai, wi])/10)/length
                        for j in chosen)/len(chosen) for ai in range(9)] for b in range(4)]
            compare(result['early_recovery'][str(tau)][panel], values)
    for j, (family, tau) in enumerate(CONDITIONS):
        saved = result['conditions'][f'{meta["label"]}__{family}_{tau}']
        for endpoint, wk, rk, den, offset in (('episode', 'wrong', 'references', 100, .00064),
                ('post_change', 'post_wrong', 'post_references', 101-tau, 0)):
            if not j and endpoint == 'post_change':
                check('scalar', 'stable recovery absent', saved[endpoint] is None)
                continue
            compare(saved[endpoint], [[(int(arrays[wk][b,j,ai])+int(arrays[rk][b,j,ai])/10)/den+offset for ai in range(9)] for b in range(4)])
    for panel, indices in panels().items():
        for endpoint, wk, rk in (('episode', 'wrong', 'references'), ('post_change', 'post_wrong', 'post_references')):
            for ai, arm in enumerate(ARMS):
                if ai == 8: continue
                tally = dict(point_lower=0, point_equal=0, point_higher=0, upper_below_zero=0, lower_above_zero=0)
                for j in indices:
                    if not j and endpoint == 'post_change': continue
                    diffs = [10*(int(arrays[wk][b,j,8])-int(arrays[wk][b,j,ai]))+int(arrays[rk][b,j,8])-int(arrays[rk][b,j,ai]) for b in range(4)]
                    den = 1000 if endpoint == 'episode' else 10*(101-CONDITIONS[j][1])
                    mean, se = statistics.mean(diffs)/den, (statistics.variance(diffs)/4)**.5/den
                    for k, yes in (('point_lower', sum(diffs) < 0), ('point_equal', sum(diffs) == 0), ('point_higher', sum(diffs) > 0),
                                   ('upper_below_zero', mean+1.96*se < 0), ('lower_above_zero', mean-1.96*se > 0)):
                        tally[k] += int(yes)
                check('scalar', 'condition signs', tally == result['condition_counts'][panel][endpoint][arm])
    for bad in (None, 0, 1, 2):
        for edge in (0., .01):
            upper = [-.01]*3
            if bad is not None: upper[bad] = edge
            fixture = dict(post_change=dict(unexpected_core_changed=dict(CT3_flat_minus_always=dict(upper95=upper[0]),
                contrasts={'CT3-flat_minus_C3': dict(upper95=upper[1])})),
                episode=dict(unexpected_core_full=dict(contrasts={'CT3-flat_minus_C3': dict(upper95=upper[2])})))
            check('criteria', 'strict rules including equality', list(verdicts(fixture).values()) == [x < 0 for x in upper])
    values = np.array([[0., 2., 4., 6.], [7., 9., 11., 13.]])
    check('scalar', 'stratified paired uncertainty', abs(ci(values)['mc_se']-(sum(statistics.variance(list(row)) for row in values)/16)**.5) < 1e-15)
    # Raw phase observations must reconstruct each post-change loss and task count.
    pc, ps = arrays['phase_counts'], arrays['phase_sums']
    for j, (_, tau) in enumerate(CONDITIONS):
        check('phase', 'exposure closure', np.all(pc[:,j,...,0].sum(axis=-1) == 101-tau))
    check('phase', 'signed decomposition', np.allclose(
        ps[...,0]-.1*pc[...,0], ps[...,2:5].sum(axis=-1)-(.1*pc[...,0]-ps[...,1]), atol=5e-13, rtol=0))
    jobs = [(meta, [i], 'parallel-'+PREFIX, None) for i in range(4)]
    serial = [worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        parallel = list(pool.map(worker, jobs))
    for a, b in zip(serial, parallel):
        check('parallel', 'one/four-worker fingerprint', a['fingerprint'] == b['fingerprint'])
        check('parallel', 'CPU ceiling', b['cpus'] == cpus)
    return dict(status='PASS', wall_seconds=perf_counter()-started, wrapper_assertions=sum(CHECKS.values()),
        wrapper_checks=dict(CHECKS), shared_checks=dict(S.CHECKS), inherited_qualification=inherited,
        inherited_qualification_reexecuted=True, new_policy_implementations=0, legacy_arrays=len(old),
        unchanged_original_rows=True, scalar_physical_blocks=2, scalar_aggregation_blocks=4,
        fresh_one_four_worker_chunks=4, synthetic_only=True, references='separate scalar accounting and inherited rational/path qualification; same author')


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
    M.logline(output, 'PREPARE: unchanged policies under unexpected physical timing; fresh paired seeds')
    check('integrity', 'completed selection-cohort manifest', M.identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    check('integrity', 'previous study complete', prior['status'] == 'COMPLETE')
    preserved = {r['path']: r for group in ('inputs', 'outputs', 'preserved') for r in prior[group]}
    paths = [PREVIOUS/'MANIFEST.json']+[SOURCE/name for name in EXPECTED]
    paths += sorted((PREVIOUS.parent/'readback-2026-10-09').iterdir())
    for attempt in sorted(ROOT.glob('attempt-*')):
        if attempt != output:
            paths += sorted(p for p in attempt.rglob('*') if p.is_file())
    for path in paths:
        preserved[str(path)] = M.identity(path)
    M.verify(list(preserved.values()))
    inputs = []
    for name in ('FEP_UNEXPECTED_CHANGE_V1.md', Path(__file__).name):
        inputs.append(M.identity(SOURCE/name))
        shutil.copyfile(SOURCE/name, output/'inputs'/name)
    pop = S.population()
    previous_population = json.loads((PREVIOUS/'POPULATION.json').read_text())
    check('population', 'base laws unchanged', pop == previous_population['bases'])
    check('population', 'supported conditions unchanged', [list(x) for x in CONDITIONS[:19]] == previous_population['conditions'])
    M.write(output/'POPULATION.json', dict(bases=pop, conditions=CONDITIONS, arms=ARMS,
            coefficients={k: v.tolist() for k, v in coefficients().items()}, coefficient_denominator=144,
            post_scale=POST_SCALE, learner_change_times=M.BOUNDARIES, unexpected_physical_times=UNEXPECTED,
            windows=[dict(start=t, tasks=min(25, 101-t)) for t in WINDOWS]))
    seeds = {m['label']: [str(M.seed_for(m['label'], i, PREFIX)) for i in range(1024)] for m in pop}
    flips = {m['label']: [str(M.seed_for(m['label'], i, PREFIX+'-transfer-flips')) for i in range(1024)] for m in pop}
    fresh = {x for values in (seeds, flips) for row in values.values() for x in row}
    check('seeds', 'unique core/flip seeds', len(fresh) == 55296)
    seed_sources = [PREVIOUS/'SEEDS.json', S.ROOT/'attempt-02/SEEDS.json']+[ROOT.parent/study/'attempt-01/SEEDS.json' for study in
                  ('fep-changing-world-v1', 'fep-future-aware-checking-v1', 'fep-three-decision-checking-v1')]
    for path in seed_sources:
        old = json.loads(path.read_text())
        previous = {x for group in ('blocks', 'flip_blocks') for row in old.get(group, {}).values() for x in row}
        check('seeds', 'separation from '+str(path), not fresh.intersection(previous))
    for study_prefix in (PREFIX, 'fep-weak-prior-confirmation-v1', S.PREFIX, S.T.PREFIX, S.B.PREFIX, 'fep-changing-world-v1'):
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
    check('integrity', 'source snapshot identity', sorted(x['sha256'] for x in inputs[:2]) == sorted(x['sha256'] for x in snapshots))
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources', 'four CPUs available', len(cpus) == 4)
    M.write(output/'PREPARATION.json', dict(started_utc=M.now(), inputs=inputs, source_snapshots=snapshots,
            preserved=list(preserved.values()), storage=storage, cpus=cpus, python=platform.python_version(), numpy=np.__version__,
            imported_policy=M.identity(SOURCE/'check_fep_calibrated_change.py'), source_manifest=M.identity(PREVIOUS/'MANIFEST.json'),
            primary=PRIMARY, new_policy_implementations=0, new_seeds=True, old_cohort_pooled=False))
    M.logline(output, 'FROZEN: design, timing simulator, 43-condition population, both seed sets and all inherited evidence')
    M.pin_cpus(cpus)
    qualification = qualify(cpus)
    M.write(output/'QUALIFICATION.json', qualification)
    M.logline(output, f'QUALIFIED: wrapper {qualification["wrapper_assertions"]} assertions; {qualification["wall_seconds"]:.3f}s')
    jobs = [(S.extend_meta(S.A.synthetic()), list(range(i*32, (i+1)*32)), 'benchmark-'+PREFIX, None) for i in range(4)]
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        records = list(pool.map(worker, jobs))
    elapsed = perf_counter()-start
    forecast = 120+3*elapsed*27648/128
    M.write(output/'BENCHMARK.json', dict(wall_seconds=elapsed, forecast_seconds=forecast, requires_detached=forecast > 600,
            workers=4, synthetic_blocks=128, conditions_per_block=43, arms=9, records=records,
            rule='120 + 3 * four-worker wall * 27648 / 128; no outcome selection'))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output, f'PREPARED: forecast {forecast:.3f}s; detached={forecast > 600}; main outcomes unread')
    print(json.dumps(dict(qualification=qualification, benchmark_seconds=elapsed, forecast_seconds=forecast,
                         requires_detached=forecast > 600, preserved_identities=len(preserved))))


def execute(output, detached):
    start, cpu = perf_counter(), process_time()
    prep = json.loads((output/'PREPARATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    check('execution', 'not started', not (output/'EXECUTION_STARTED.json').exists())
    check('execution', 'qualified', json.loads((output/'QUALIFICATION.json').read_text())['status'] == 'PASS')
    check('execution', 'detachment rule', detached or not bench['requires_detached'])
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    mount_check(output)
    M.pin_cpus(prep['cpus'])
    M.write(output/'EXECUTION_STARTED.json', dict(started_utc=M.now(), pid=os.getpid(), detached=detached,
            workers=4, cpus=prep['cpus'], benchmark=M.identity(output/'BENCHMARK.json'), primary=PRIMARY))
    M.logline(output, 'MAIN STARTED: 216 fixed chunks, 27648 fresh blocks, 1161 conditions, nine unchanged arms')
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(meta, list(range(i, i+128)), PREFIX, str(output)) for meta in pop for i in range(0, 1024, 128)]
    records = []
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(prep['cpus'],)) as pool:
        for i, record in enumerate(pool.map(worker, jobs), 1):
            records.append(record)
            if i % 8 == 0:
                M.logline(output, f'COMPLETED {i}/216 chunks; {record["label"]}')
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
