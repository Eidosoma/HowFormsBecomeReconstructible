"""Three prospective recovery requirements, clustered in whole source blocks."""
import numpy as np
from common import rng
from E068_fresh_recovery_confirmation.plan import SLOTS, PRIMARY, CONFIDENCE, index

SCORES = ('both', 'minimum_margin', 'aligned_transfer')
NATIVE = {slot: (i,) for i, slot in enumerate(SLOTS)}
for h in (0, 1, 3):
    for policy in (('protected',) if h == 0 else ('rewrite', 'copy')):
        for kind in ('native', 'mixture'):
            label = f'h{h}_' + ('' if h == 0 else policy + '_') + kind + '_pooled'
            NATIVE[label] = tuple(index(h, policy, kind + '_' + a) for a in ('sham', 'pulse'))


def effects(x, arm):
    def take(h, policy, kind):
        if kind == 'erased':
            return x[..., index(h, policy, kind)]
        labels = ('sham', 'pulse') if arm == 'pooled' else (arm,)
        return np.stack([x[..., index(h, policy, kind + '_' + a)] for a in labels], axis=-1).mean(axis=-1)
    m0, n0 = take(0, 'protected', 'mixture'), take(0, 'protected', 'native')
    out = dict(native_minus_mixture_h0=n0 - m0)
    for h in (1, 3):
        m, n = take(h, 'rewrite', 'mixture'), take(h, 'rewrite', 'native')
        copied, erased = take(h, 'copy', 'mixture'), take(h, 'rewrite', 'erased')
        out.update({f'absolute_recovery_h{h}': m - m0,
                    f'rewrite_over_erasure_h{h}': m - copied,
                    f'retained_rule_over_erased_h{h}': m - erased,
                    f'native_change_h{h}': n - n0,
                    f'native_minus_mixture_h{h}': n - m,
                    f'mixture_copy_change_h{h}': copied - m0,
                    f'deficit_closure_h{h}': (m - n) - (m0 - n0)})
    return out


def values(cases):
    out = {}
    for metric in cases[0]:
        if metric == 'margin':
            continue
        x = np.stack([c[metric] for c in cases]).mean(axis=(-2, -1))
        for label, slots in NATIVE.items():
            out[f'native/{metric}/{label}'] = x[:, slots].mean(axis=-1)
        if metric in SCORES:
            for arm in ('sham', 'pulse', 'pooled'):
                for name, value in effects(x, arm).items():
                    out[f'effect/{metric}/{arm}/{name}'] = value
    return out


def classification(interval):
    return 'POSITIVE_EFFECT' if interval[0] > 0 else 'NEGATIVE_EFFECT' if interval[1] < 0 else 'UNRESOLVED'


def analyze(cases, controls, mode):
    B = len(cases)
    draws = rng('E068', 'rebuilding', 'bootstrap').integers(0, B, (10000, B))
    primary = {f'effect/both/pooled/{k}' for k in PRIMARY}
    stats = {}
    for key, x in values(cases).items():
        conf = CONFIDENCE if key in primary else .95
        tail = (1 - conf) / 2
        stats[key] = dict(mean=float(x.mean()),
            interval=np.quantile(x[draws].mean(axis=1), [tail, 1 - tail]).tolist(),
            confidence=conf, block_means=x.tolist())
    ok = all(c['pass'] for c in controls)
    enabled = mode == 'scientific' and ok
    labels = {k: classification(stats[f'effect/both/pooled/{k}']['interval']) if enabled else None for k in PRIMARY}
    supported = all(v == 'POSITIVE_EFFECT' for v in labels.values()) if enabled else None
    return dict(status='TECHNICAL_ONLY' if mode != 'scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok
        else 'FRESH_RECOVERY_CONFIRMED' if supported else 'RECOVERY_NOT_CONFIRMED',
        primary_effects=labels, recovery_supported=supported, controls_pass=ok,
        controls_by_block=controls, independent_blocks=B,
        lineages_per_slot=B * cases[0]['both'].shape[-2] * cases[0]['both'].shape[-1],
        primary_arm_weighting='equal_within_block', primary_family_size=3,
        primary_confidence=CONFIDENCE, cohort_reused=False, fresh_sources=mode == 'scientific', old_observations_pooled=False,
        protected_copy_reads_aliased=True, erased_rewrite_assumed_zero=False, statistics=stats)


def audit(cases, controls, summary, mode):
    from E015_functional_inheritance.audit import random
    B = len(cases)
    draws = random('E068', 'rebuilding', 'bootstrap').integers(0, B, size=(10000, B))
    primary = tuple('effect/both/pooled/' + k for k in PRIMARY)
    for key, result in summary['statistics'].items():
        fields = key.split('/')
        metric = fields[1]
        samples = []
        for c in cases:
            x = np.array([np.sum(a) / a.size for a in c[metric]])
            if fields[0] == 'native':
                selected = NATIVE[fields[2]]
                samples.append(sum(x[j] for j in selected) / len(selected))
                continue
            arm, name = fields[2:]
            def average(start):
                return (x[start] + x[start + 1]) / 2 if arm == 'pooled' else x[start + (arm == 'pulse')]
            m0, n0 = average(2), average(0)
            entries = dict(native_minus_mixture_h0=n0 - m0)
            for h, mpos, npos, cpos, epos in ((1, 7, 5, 12, 9), (3, 16, 14, 21, 18)):
                m, n, copied, erased = average(mpos), average(npos), average(cpos), x[epos]
                entries.update({f'absolute_recovery_h{h}': m - m0,
                    f'rewrite_over_erasure_h{h}': m - copied,
                    f'retained_rule_over_erased_h{h}': m - erased,
                    f'native_change_h{h}': n - n0, f'native_minus_mixture_h{h}': n - m,
                    f'mixture_copy_change_h{h}': copied - m0,
                    f'deficit_closure_h{h}': (m - n) - (m0 - n0)})
            samples.append(entries[name])
        samples = np.array(samples)
        conf = 1 - .05 / 3 if key in primary else .95
        np.testing.assert_array_equal(result['block_means'], samples)
        assert result['mean'] == samples.mean() and result['confidence'] == conf
        np.testing.assert_array_equal(result['interval'], np.quantile(samples[draws].mean(axis=1), [(1 - conf) / 2, 1 - (1 - conf) / 2]))
    ok = all(c['pass'] for c in controls)
    labels = {}
    for name in PRIMARY:
        lo, hi = summary['statistics']['effect/both/pooled/' + name]['interval']
        labels[name] = ('POSITIVE_EFFECT' if lo > 0 else 'NEGATIVE_EFFECT' if hi < 0 else 'UNRESOLVED') if mode == 'scientific' and ok else None
    supported = all(v == 'POSITIVE_EFFECT' for v in labels.values()) if mode == 'scientific' and ok else None
    expected = 'TECHNICAL_ONLY' if mode != 'scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else 'FRESH_RECOVERY_CONFIRMED' if supported else 'RECOVERY_NOT_CONFIRMED'
    assert summary['primary_effects'] == labels and summary['recovery_supported'] == supported
    assert summary['status'] == expected and summary['controls_pass'] == ok
    return len(summary['statistics'])


def report(s):
    stats = s['statistics']
    def fmt(key, scale=1):
        v = stats[key]
        return f'{scale*v["mean"]:.4f} [{scale*v["interval"][0]:.4f}, {scale*v["interval"][1]:.4f}]'
    lines = ['# E068 ordinary rebuilding from the mixture', '', s['status'], '',
        ('Fresh source generation and fresh matched readers; no old scientific cases or scores pooled.'
         if s['fresh_sources'] else 'Excluded technical source regeneration and fresh matched readers; no scientific classification.'),
        'Only the current packet is available after the initial mixture construction.', '',
        '| Primary at three rewrites | Points [98.3333%] | Classification |', '| --- | ---: | --- |']
    for name in PRIMARY:
        lines.append(f'| {name} | {fmt("effect/both/pooled/"+name,100)} | {s["primary_effects"][name]} |')
    lines += ['', '| Physical condition | Successes | Success % [95%] | Aligned transfer [95%] |', '| --- | ---: | ---: | ---: |']
    n = s['lineages_per_slot']
    for label in SLOTS:
        key = 'native/both/' + label
        count = round(stats[key]['mean'] * n)
        lines.append(f'| {label} | {count}/{n} | {fmt(key,100)} | {fmt("native/aligned_transfer/"+label)} |')
    lines += ['', '| Pooled mixture | Correct signs but weak % | Wrong sign % | Gains from h0 % | Losses from h0 % |', '| --- | ---: | ---: | ---: | ---: |']
    for label in ('h0_mixture_pooled', 'h1_rewrite_mixture_pooled', 'h3_rewrite_mixture_pooled'):
        entries = [fmt(f'native/{metric}/{label}', 100) for metric in ('correct_signs_below_threshold', 'any_wrong_sign', 'gained_success', 'lost_success')]
        lines.append('| ' + ' | '.join([label] + entries) + ' |')
    lines += ['', 'All uncertainty resamples whole independent blocks. Native tables and secondary contrasts use pointwise 95% intervals.',
        'A narrowing native/mixture gap is not recovery unless the mixture improves absolutely.',
        'Erased-start rewriting can produce nonzero records; its success is measured.',
        'Protected copies and erased copies alias initial reads; rewritten erased controls do not.',
        'No complete-repair, fine founder-specificity, changed-apparatus robustness or biological ageing claim.',
        'Interpret only after independent replay, figure inspection and closeout.', '']
    return '\n'.join(lines)
