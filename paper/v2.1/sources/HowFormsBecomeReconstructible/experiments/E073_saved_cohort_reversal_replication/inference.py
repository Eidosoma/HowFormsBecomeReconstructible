"""Paired block inference for the immediate and one-rewrite pruning benefits."""
import numpy as np
from common import rng
from E073_saved_cohort_reversal_replication.plan import SLOTS, PRIMARY, CONFIDENCE

SCORES = ('both', 'minimum_margin', 'aligned_transfer')
NATIVE = {s: (i,) for i, s in enumerate(SLOTS)}
for h in (0, 1):
    for p, policy in enumerate(('intact', 'pruned')):
        for offset, kind in ((0, 'native'), (2, 'mixture')):
            start = 9*h+4*p+offset
            NATIVE[f'h{h}_{policy}_{kind}_pooled'] = (start, start+1)


def effects(x, history):
    def take(h, p, kind):
        start = 9*h+4*p+(2 if kind == 'mixture' else 0)
        return (x[..., start]+x[..., start+1])/2 if history == 'pooled' else x[..., start+(history == 'pulse')]
    n0, m0, p0, q0, n1, m1, p1, q1 = [take(h, p, k) for h in (0, 1) for p in (0, 1) for k in ('native', 'mixture')]
    return dict(mixture_gain_h0=q0-m0, mixture_gain_h1=q1-m1,
        native_gain_h0=p0-n0, native_gain_h1=p1-n1,
        mixture_benefit_change=(q1-m1)-(q0-m0), native_benefit_change=(p1-n1)-(p0-n0),
        intact_mixture_change=m1-m0, pruned_mixture_change=q1-q0,
        intact_native_change=n1-n0, pruned_native_change=p1-p0,
        intact_mixture_over_erased_h0=m0-x[..., 8], pruned_mixture_over_erased_h0=q0-x[..., 8],
        intact_mixture_over_erased_h1=m1-x[..., 17], pruned_mixture_over_erased_h1=q1-x[..., 17],
        intact_native_minus_mixture_h1=n1-m1, pruned_native_minus_mixture_h1=p1-q1)


def values(cases):
    out = {}
    for metric in cases[0]:
        if metric == 'margin': continue
        x = np.stack([c[metric] for c in cases]).mean(axis=(-2, -1))
        for label, slots in NATIVE.items():
            out[f'native/{metric}/{label}'] = x[:, slots].mean(axis=-1)
        if metric in SCORES:
            for history in ('pooled', 'sham', 'pulse'):
                for name, value in effects(x, history).items():
                    out[f'effect/{metric}/{history}/{name}'] = value
    return out


def classification(interval):
    return 'POSITIVE_EFFECT' if interval[0] > 0 else 'NEGATIVE_EFFECT' if interval[1] < 0 else 'UNRESOLVED'


def status(mode, ok, labels):
    if mode != 'scientific': return 'TECHNICAL_ONLY'
    if not ok: return 'NUMERICAL_CONTROL_FAILURE'
    before, after = [labels[n] for n in PRIMARY]
    if before == after == 'POSITIVE_EFFECT': return 'PERSISTENCE_SUPPORTED'
    if before == 'POSITIVE_EFFECT':
        return 'BENEFIT_REVERSED' if after == 'NEGATIVE_EFFECT' else 'POST_REWRITE_BENEFIT_UNRESOLVED'
    if after == 'POSITIVE_EFFECT': return 'POST_REWRITE_GAIN_WITHOUT_IMMEDIATE_CONFIRMATION'
    return 'PERSISTENCE_NOT_ESTABLISHED'


def analyze(cases, controls, mode):
    B = len(cases)
    draws = rng('E073', 'single_pruning', 'bootstrap').integers(0, B, (10000, B))
    primary_keys = {f'effect/both/pooled/{n}' for n in PRIMARY}
    stats = {}
    for key, x in values(cases).items():
        confidence = CONFIDENCE if key in primary_keys else .95
        a = (1-confidence)/2
        stats[key] = dict(mean=float(x.mean()), confidence=confidence, block_means=x.tolist(),
            interval=np.quantile(x[draws].mean(axis=1), [a, 1-a]).tolist())
    ok = all(c['pass'] for c in controls)
    enabled = mode == 'scientific' and ok
    labels = {n: classification(stats[f'effect/both/pooled/{n}']['interval']) if enabled else None for n in PRIMARY}
    return dict(status=status(mode, ok, labels), primary_effects=labels,
        persistence_supported=all(v == 'POSITIVE_EFFECT' for v in labels.values()) if enabled else None,
        reversal_replicated=(labels['mixture_gain_h0'] == 'POSITIVE_EFFECT' and labels['mixture_gain_h1'] == 'NEGATIVE_EFFECT') if enabled else None,
        controls_pass=ok, controls_by_block=controls, independent_blocks=B,
        lineages_per_slot=B*cases[0]['both'].shape[-2]*cases[0]['both'].shape[-1],
        primary_family_size=2, primary_confidence=CONFIDENCE, primary_arm_weighting='equal_within_block',
        source_boundary=1, additional_rewrites=1, repeated_pruning=False,
        cohort_reused=True, prior_diagnostic_exposure_declared=True,
        old_observations_pooled=False, statistics=stats)


def audit(cases, controls, summary, mode):
    from E015_functional_inheritance.audit import random
    B = len(cases)
    draws = random('E073', 'single_pruning', 'bootstrap').integers(0, B, size=(10000, B))
    labels = list(SLOTS)
    pools = {}
    for h, base in ((0, 0), (1, 9)):
        for policy, offset in (('intact', 0), ('pruned', 4)):
            pools[f'h{h}_{policy}_native_pooled'] = (base+offset, base+offset+1)
            pools[f'h{h}_{policy}_mixture_pooled'] = (base+offset+2, base+offset+3)
    expected = {}
    def append(key, value): expected.setdefault(key, []).append(value)
    for case in cases:
        for metric, arrays in case.items():
            if metric == 'margin': continue
            x = np.array([np.sum(a)/a.size for a in arrays])
            for i, label in enumerate(labels): append(f'native/{metric}/{label}', x[i])
            for label, (a, b) in pools.items(): append(f'native/{metric}/{label}', (x[a]+x[b])/2)
            if metric not in ('both', 'minimum_margin', 'aligned_transfer'): continue
            for history in ('pooled', 'sham', 'pulse'):
                if history == 'pooled':
                    ni0, mi0, np0, mp0, ni1, mi1, np1, mp1 = [(x[i]+x[i+1])/2 for i in (0, 2, 4, 6, 9, 11, 13, 15)]
                else:
                    off = int(history == 'pulse')
                    ni0, mi0, np0, mp0, ni1, mi1, np1, mp1 = [x[i+off] for i in (0, 2, 4, 6, 9, 11, 13, 15)]
                contrasts = dict(mixture_gain_h0=mp0-mi0, mixture_gain_h1=mp1-mi1,
                    native_gain_h0=np0-ni0, native_gain_h1=np1-ni1,
                    mixture_benefit_change=(mp1-mi1)-(mp0-mi0), native_benefit_change=(np1-ni1)-(np0-ni0),
                    intact_mixture_change=mi1-mi0, pruned_mixture_change=mp1-mp0,
                    intact_native_change=ni1-ni0, pruned_native_change=np1-np0,
                    intact_mixture_over_erased_h0=mi0-x[8], pruned_mixture_over_erased_h0=mp0-x[8],
                    intact_mixture_over_erased_h1=mi1-x[17], pruned_mixture_over_erased_h1=mp1-x[17],
                    intact_native_minus_mixture_h1=ni1-mi1, pruned_native_minus_mixture_h1=np1-mp1)
                for name, value in contrasts.items(): append(f'effect/{metric}/{history}/{name}', value)
    assert set(expected) == set(summary['statistics'])
    for key, samples in expected.items():
        x = np.array(samples)
        result = summary['statistics'][key]
        confidence = .975 if key in ('effect/both/pooled/mixture_gain_h0', 'effect/both/pooled/mixture_gain_h1') else .95
        a = (1-confidence)/2
        np.testing.assert_array_equal(result['block_means'], x)
        assert result['mean'] == x.mean() and result['confidence'] == confidence
        np.testing.assert_array_equal(result['interval'], np.quantile(x[draws].mean(axis=1), [a, 1-a]))
    ok = all(c['pass'] for c in controls)
    enabled = ok and mode == 'scientific'
    observed = {}
    for name in ('mixture_gain_h0', 'mixture_gain_h1'):
        lo, hi = summary['statistics'][f'effect/both/pooled/{name}']['interval']
        observed[name] = ('POSITIVE_EFFECT' if lo > 0 else 'NEGATIVE_EFFECT' if hi < 0 else 'UNRESOLVED') if enabled else None
    before, after = observed.values()
    expected_status = 'TECHNICAL_ONLY' if mode != 'scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else (
        'PERSISTENCE_SUPPORTED' if before == after == 'POSITIVE_EFFECT' else
        'BENEFIT_REVERSED' if before == 'POSITIVE_EFFECT' and after == 'NEGATIVE_EFFECT' else
        'POST_REWRITE_BENEFIT_UNRESOLVED' if before == 'POSITIVE_EFFECT' else
        'POST_REWRITE_GAIN_WITHOUT_IMMEDIATE_CONFIRMATION' if after == 'POSITIVE_EFFECT' else
        'PERSISTENCE_NOT_ESTABLISHED')
    assert summary['status'] == expected_status and summary['controls_pass'] == ok
    assert summary['primary_effects'] == observed and summary['primary_family_size'] == 2
    assert summary['primary_confidence'] == .975
    assert summary['persistence_supported'] == (before == after == 'POSITIVE_EFFECT' if enabled else None)
    assert summary['reversal_replicated'] == (before == 'POSITIVE_EFFECT' and after == 'NEGATIVE_EFFECT' if enabled else None)
    assert summary['additional_rewrites'] == 1 and summary['repeated_pruning'] is False
    return len(expected)


def report(s):
    stats = s['statistics']
    def fmt(key, scale=1):
        r = stats[key]
        return f'{scale*r["mean"]:.4f} [{scale*r["interval"][0]:.4f}, {scale*r["interval"][1]:.4f}]'
    lines = ['# E073 saved-cohort reversal replication', '', s['status'], '',
        'All E068 sources retained; one additional ordinary rewrite; no repeated pruning.',
        'Fresh matched readers before/after, independent of writer streams. Prior exposure declared.', '',
        'Reversal replicated: '+str(s['reversal_replicated'])+'. Both original signed contrasts and intervals retained.', '',
        '| Primary mixture gain: pruned minus intact | Points [97.5%] | Classification |', '| --- | ---: | --- |']
    for name in PRIMARY:
        lines.append('| '+name+' | '+fmt('effect/both/pooled/'+name, 100)+' | '+str(s['primary_effects'][name])+' |')
    lines += ['', '| Condition | Successes | Success % [95%] | Aligned transfer [95%] |', '| --- | ---: | ---: | ---: |']
    n = s['lineages_per_slot']
    for label in SLOTS:
        lines.append(f'| {label} | {round(stats["native/both/"+label]["mean"]*n)}/{n} | {fmt("native/both/"+label,100)} | {fmt("native/aligned_transfer/"+label)} |')
    lines += ['', '| Secondary pooled success effect | Points [95%] |', '| --- | ---: |']
    for name in ('mixture_benefit_change', 'native_gain_h0', 'native_gain_h1',
                 'intact_mixture_change', 'pruned_mixture_change', 'pruned_mixture_over_erased_h1'):
        lines.append('| '+name+' | '+fmt('effect/both/pooled/'+name,100)+' |')
    lines += ['', '| Mixture record | Selected edges present % [95%] | Postinjury coupling share % [95%] |', '| --- | ---: | ---: |']
    for h in (0, 1):
        for policy in ('intact', 'pruned'):
            label = f'h{h}_{policy}_mixture_pooled'
            lines.append('| '+label+' | '+fmt('native/selected_present_fraction/'+label,100)+' | '+fmt('native/postinjury_selected_coupling_share/'+label,100)+' |')
    lines += ['', 'Whole source blocks are the independent units; two primaries have a nominal approximate 95% family target.',
        'Other intervals are pointwise 95%. Reappearance is descriptive, not a causal explanation of performance.',
        'Unresolved is not equivalence. No indefinite-persistence or autonomous-pruning claim.',
        'Interpret after independent replay, figure inspection and artifact closeout.', '']
    return '\n'.join(lines)
