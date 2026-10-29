"""Independent full-dynamics, boundary, common-input and content checks."""
from __future__ import annotations

import numpy as np
import model as m
from h035 import design as d
from h035.audit import reference_relax, reference_write, reference_score
from h038 import experiment as e


def reference_read(record, base, birth, orders, cues, gain):
    w = base+record
    w[..., :4, 4:] *= gain
    w[..., 4:, :4] *= gain
    x = np.broadcast_to(birth, (*record.shape[:-2], 4, 64))
    return reference_relax(w[..., None, :, :], x, orders, np.arange(4), cues)


def bit_score(states, rules=d.RULES):
    target = (np.asarray(rules)[:, :, None]*np.array([-1, 1])).reshape(4, 1, 4)
    pos = (states[..., 8:16] == target[..., None]).sum(-1) >= 7
    neg = (states[..., 16:24] == -target[..., None]).sum(-1) >= 7
    trial = pos & neg
    rule = trial.reshape(*trial.shape[:-1], 2, 2).all(-1)
    return rule, rule.all(-1)


def audit(source, raw, cohort, block):
    checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
        if not value:
            raise AssertionError(name)
    rec, body, states = [raw[k] for k in ('records', 'bodies', 'states')]
    G, P, J = body.shape[1], states.shape[5], len(source['checkpoints'])
    tape = d.inputs(cohort, block, G)
    for k, v in tape.items():
        check('archived input independently reproduced '+k, np.array_equal(source[k], v))
    check('record dimensions', rec.shape == (2, G+1, 3, 11, 4, 2, 64, 64))
    check('body dimensions', body.shape == (2, G, 3, 11, 4, 2, 4, 64))
    check('assay dimensions', states.shape == (J, 2, 2, 3, 11, P, 4, 2, 4, 64))
    check('finite data', all(np.isfinite(a).all() for a in raw.values()))
    check('binary bodies', np.isin(body, [-1, 1]).all())
    check('binary assay states', np.isin(states, [-1, 1]).all())
    check('symmetric records', np.array_equal(rec, rec.swapaxes(-1, -2)))
    check('zero record diagonal', not np.diagonal(rec, axis1=-2, axis2=-1).any())
    check('cue clamp in assays', np.all(states[..., :4] == d.CUES))
    for l, schedule in enumerate(d.SCHEDULES):
        check('cue clamp in bodies '+str(l), np.all(body[:, :, l, ..., :4] == d.CUES[schedule]))
    teaching = np.empty((4, 4, 24))
    teaching[..., :8] = np.tile(d.CUES, (1, 2))
    teaching[..., 8:16] = d.TARGETS[..., None]
    teaching[..., 16:24] = -d.TARGETS[..., None]
    founder = reference_relax(source['base'], np.broadcast_to(source['founder_birth'], (4, 4, 64)),
        source['formation_orders'], np.arange(24), teaching)
    check('independent founder replay', np.array_equal(founder, source['founder']))
    initial = np.stack([reference_write(founder[:, schedule]) for schedule in d.SCHEDULES])
    check('independent initial acquisition', np.array_equal(initial, source['initial']))
    for a, arm in enumerate(d.ARMS):
        expected = initial
        if arm in d.DONORS:
            expected = initial[:, d.DONORS[arm]]
        elif arm == 'scrambled':
            p = source['permutation']; expected = initial[..., p, :][..., :, p]
        elif arm == 'erased':
            expected = np.zeros_like(initial)
        check('initial record '+arm, np.array_equal(rec[:, 0, :, a],
            np.broadcast_to(expected[None, :, :, None], rec[:, 0, :, a].shape)))
    check('all baseline records exactly replay H035', np.array_equal(rec[0], source['records']))
    check('all baseline bodies exactly replay H035', np.array_equal(body[0], source['bodies']))
    check('all legacy baseline assays exactly replay H035', np.array_equal(states[:, 0, 0, :, :, 0], source['reader_states']))
    for name, gain in [('ordinary', 4), ('strong', 8)]:
        w = e.weights(source['base'], rec[:, 0], gain)
        plain = source['base']+rec[:, 0]
        check('symmetric weights '+name, np.array_equal(w, w.swapaxes(-1, -2)))
        check('cue-incident weights '+name, np.array_equal(w[..., :4, 4:], gain*plain[..., :4, 4:]))
        check('other weights unchanged '+name, np.array_equal(w[..., 4:, 4:], plain[..., 4:, 4:]) and
            np.array_equal(w[..., :4, :4], plain[..., :4, :4]))
    for j, g in enumerate(source['checkpoints']):
        check('legacy probe birth '+str(g), np.array_equal(raw['probe_birth'][j, 0], source['assay_birth'][j]))
        check('legacy probe orders '+str(g), np.array_equal(raw['probe_orders'][j, 0], source['assay_orders'][j]))
        for p in range(1, P):
            key = ('H038', 'probe', cohort, int(block), int(g), p-1)
            birth = m.rng(38038, *key, 'birth').choice([-1., 1.], size=(2, 4, 64))
            r = m.rng(38038, *key, 'order')
            order = np.array([r.permutation(64) for _ in range(8)])
            check(f'fresh probe birth {g}/{p}', np.array_equal(raw['probe_birth'][j, p], birth))
            check(f'fresh probe orders {g}/{p}', np.array_equal(raw['probe_orders'][j, p], order))
        for r, gain in enumerate(e.GAINS):
            for p in range(P):
                expected = reference_read(rec[:, g], source['base'], raw['probe_birth'][j, p],
                    raw['probe_orders'][j, p], d.CUES, gain)
                check(f'independent assay replay {g}/{gain}/{p}', np.array_equal(expected, states[j, :, r, :, :, p]))
    protected, damaged, read_off, write_off, scrambled = [d.ARMS.index(a) for a in
        ('protected_copy', 'damaged_copy', 'read_off', 'write_off', 'writer_scrambled')]
    for b, gain in enumerate(e.GAINS):
        for g in range(G):
            for l, schedule in enumerate(d.SCHEDULES):
                incoming = rec[b, g, l]*source['damage'][g]
                incoming[protected] = rec[b, g, l, protected]
                incoming[read_off] = 0
                expected = reference_read(incoming, source['base'], source['body_birth'][g][:, schedule],
                    source['body_orders'][g], d.CUES[schedule], gain)
                check(f'independent body replay {gain}/{g+1}/{l}', np.array_equal(expected, body[b, g, l]))
            outgoing = reference_write(body[b, g])
            for a, arm in enumerate(d.ARMS):
                expected = outgoing[:, a]
                if a == protected:
                    expected = rec[b, g, :, a]
                elif a == damaged:
                    expected = rec[b, g, :, a]*source['damage'][g]
                elif a == write_off:
                    expected = np.zeros_like(expected)
                elif a == scrambled:
                    p = source['permutation']; expected = expected[..., p, :][..., :, p]
                check(f'body-only rewrite or declared bypass {gain}/{g+1}/{arm}',
                    np.array_equal(expected, rec[b, g+1, :, a]))
    for arm in ('protected_copy', 'damaged_copy'):
        a = d.ARMS.index(arm)
        check('record invariant to reconstruction gain '+arm, np.array_equal(rec[0, :, :, a], rec[1, :, :, a]))
        check('assay invariant to reconstruction gain '+arm, np.array_equal(states[:, 0, :, :, a], states[:, 1, :, :, a]))
    for arm in ('erased', 'read_off', 'write_off'):
        a = d.ARMS.index(arm)
        first = 0 if arm == 'erased' else 1
        x = rec[:, first:, :, a]
        check('history-independent record '+arm, np.array_equal(x, np.broadcast_to(x[..., :1, :, :, :], x.shape)))
        start = 0 if arm == 'erased' else 1
        x = states[start:, :, :, :, a]
        check('history-independent assays '+arm, np.array_equal(x, np.broadcast_to(x[..., :1, :, :, :], x.shape)))
        _, joint = bit_score(x)
        check('balanced-history joint ceiling '+arm, np.all(joint.mean(axis=-2) <= .25))
    for arm, donor in d.DONORS.items():
        a = d.ARMS.index(arm)
        check('donor lineage exactly permutes own '+arm, np.array_equal(rec[:, :, :, a], np.take(rec[:, :, :, 0], donor, axis=-4)))
        check('donor assays exactly permute own '+arm, np.array_equal(states[:, :, :, :, a], np.take(states[:, :, :, :, 0], donor, axis=-4)))
    for load, irrelevant in ((0, 'foreign_b'), (1, 'foreign_a')):
        a = d.ARMS.index(irrelevant)
        check('untrained history swap inert '+str(load), np.array_equal(rec[:, :, load, 0], rec[:, :, load, a]))
    for label, rules in [('own', d.RULES), *[(a, d.RULES[x]) for a, x in d.DONORS.items()]]:
        actual = e.score(states, 2, rules)
        reference = reference_score(states, rules)
        bits = bit_score(states, rules)
        for name, x, y, z in zip(('rule', 'joint'), actual[1:], reference[1:], bits):
            check(f'independent endpoint {label}/{name}', np.array_equal(x, y) and np.array_equal(y, z))
    for l in range(3):
        observed = bit_score(body[:, :, l])[0]
        expected = observed.all(-1) if l == 2 else observed[..., l]
        check('independent body observer '+str(l), np.array_equal(e.body_success(body[:, :, l], l), expected))
    return dict(passed=True, checks_count=len(checks), checks=checks,
        body_replays=2*G*3, assay_replays=J*2*P, legacy_probes_excluded_from_primary=True)
