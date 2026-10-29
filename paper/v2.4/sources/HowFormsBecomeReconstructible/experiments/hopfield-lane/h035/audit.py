"""Independent retained-data equations and full sequential-dynamics replay."""
from __future__ import annotations

import numpy as np
from h035 import design as d, experiment as e


def reference_relax(weights, birth, orders, indices, values):
    state = np.array(birth, dtype=float, copy=True)
    state[..., indices] = values
    clamped = set(int(i) for i in indices)
    for order in orders:
        for i in order:
            if int(i) in clamped:
                continue
            field = np.sum(weights[..., i, :] * state, axis=-1)
            state[..., i] = np.where(field > 0, 1., np.where(field < 0, -1., state[..., i]))
    return state


def reference_read(record, base, birth, orders, cues):
    weights = base + record
    weights[..., :4, 4:] *= 4.
    weights[..., 4:, :4] *= 4.
    state = np.broadcast_to(birth, (*record.shape[:-2], 4, 64))
    return reference_relax(weights[..., None, :, :], state, orders, np.arange(4), cues)


def reference_write(state):
    result = np.zeros((*state.shape[:-2], 64, 64), float)
    for trial in range(4):
        x = state[..., trial, :].astype(float)
        result += x[..., :, None] * x[..., None, :]
    result /= 256.
    result[..., np.arange(64), np.arange(64)] = 0.
    return result


def reference_score(states, rules=d.RULES):
    margins = np.empty((*states.shape[:-2], 2))
    for h in range(4):
        for task in range(2):
            values = []
            for polarity, cue in ((-1, 2*task), (1, 2*task+1)):
                state = states[..., h, :, cue, :]
                target = polarity*rules[h, task]
                values += [target*state[..., 8:16].sum(axis=-1)/8,
                           -target*state[..., 16:24].sum(axis=-1)/8]
            margins[..., h, :, task] = np.minimum.reduce(values)
    return margins, margins > .5, (margins > .5).all(axis=-1)


def audit(raw, cohort, block):
    checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
        if not value:
            raise AssertionError(name)
    records, bodies = raw['records'], raw['bodies']
    generations = len(bodies)
    tape = d.inputs(cohort, block, generations)
    for name, value in tape.items():
        check('reproduced input '+name, np.array_equal(value, raw[name]))
    check('record dimensions', records.shape == (generations+1, 3, 11, 4, 2, 64, 64))
    check('all data finite', all(np.isfinite(a).all() for a in raw.values() if a.dtype.kind in 'fi'))
    for name in ('founder', 'bodies', 'reader_states'):
        check('binary '+name, np.isin(raw[name], [-1, 1]).all())
    check('all records symmetric', np.array_equal(records, records.swapaxes(-1, -2)))
    check('all record diagonals zero', not np.diagonal(records, axis1=-2, axis2=-1).any())
    check('symmetric damage', np.array_equal(raw['damage'], raw['damage'].swapaxes(-1, -2)))
    check('damage diagonal zero', not np.diagonal(raw['damage'], axis1=-2, axis2=-1).any())
    check('permutation fixes cue address', np.array_equal(raw['permutation'][:8], np.arange(8)))
    check('declared metadata', all(np.array_equal(raw[k], v) for k, v in
        [('loads', d.LOADS), ('arms', d.ARMS), ('rules', d.RULES), ('cues', d.CUES), ('schedules', d.SCHEDULES)]))
    for name in ('formation_orders', 'body_orders', 'assay_orders'):
        check('valid update permutations '+name, np.all(np.sort(raw[name], axis=-1) == np.arange(64)))
    teaching = np.empty((4, 4, 24))
    teaching[..., :8] = np.tile(d.CUES, (1, 2))
    teaching[..., 8:16] = d.TARGETS[..., None]
    teaching[..., 16:24] = -d.TARGETS[..., None]
    founder = reference_relax(raw['base'], np.broadcast_to(raw['founder_birth'], (4, 4, 64)),
        raw['formation_orders'], np.arange(24), teaching)
    check('independent founder replay', np.array_equal(founder, raw['founder']))
    initial = np.stack([reference_write(founder[:, s]) for s in d.SCHEDULES])
    check('independent acquisition coactivity', np.array_equal(initial, raw['initial']))
    for l in range(3):
        for a, arm in enumerate(d.ARMS):
            expected = initial[l]
            if arm in d.DONORS:
                expected = expected[d.DONORS[arm]]
            elif arm == 'scrambled':
                p = raw['permutation']; expected = expected[..., p, :][..., :, p]
            elif arm == 'erased':
                expected = np.zeros_like(expected)
            check(f'initial {l}/{arm}', np.array_equal(records[0, l, a],
                np.broadcast_to(expected[:, None], records[0, l, a].shape)))
    for g in range(generations):
        for l, schedule in enumerate(d.SCHEDULES):
            incoming = records[g, l] * raw['damage'][g]
            p = d.ARMS.index('protected_copy'); incoming[p] = records[g, l, p]
            incoming[d.ARMS.index('read_off')] = 0
            expected = reference_read(incoming, raw['base'], raw['body_birth'][g][:, schedule],
                raw['body_orders'][g], d.CUES[schedule])
            check(f'fresh-body independent replay {g+1}/{l}', np.array_equal(expected, bodies[g, l]))
            check(f'only input cues fixed {g+1}/{l}', np.all(bodies[g, l, ..., :4] == d.CUES[schedule]))
        outgoing = reference_write(bodies[g])
        for a, arm in enumerate(d.ARMS):
            expected = outgoing[:, a]
            if arm == 'protected_copy':
                expected = records[g, :, a]
            elif arm == 'damaged_copy':
                expected = records[g, :, a] * raw['damage'][g]
            elif arm == 'write_off':
                expected = np.zeros_like(expected)
            elif arm == 'writer_scrambled':
                p = raw['permutation']; expected = expected[..., p, :][..., :, p]
            check(f'body-only boundary or declared copy {g+1}/{arm}',
                np.array_equal(expected, records[g+1, :, a]))
        for arm in ('erased', 'read_off'):
            # Identical births/base/cues and absent acquired information cannot
            # reconstruct a different answer for an invisible history label.
            values = records[g+1, :, d.ARMS.index(arm)]
            check(f'no history-label leakage {g+1}/{arm}',
                np.array_equal(values, np.broadcast_to(values[:, :1], values.shape)))
    own = d.ARMS.index('renewal')
    check('untrained B swap exactly inert for A-only throughout',
        np.array_equal(records[:, 0, own], records[:, 0, d.ARMS.index('foreign_b')] ))
    check('untrained A swap exactly inert for B-only throughout',
        np.array_equal(records[:, 1, own], records[:, 1, d.ARMS.index('foreign_a')] ))
    for j, g in enumerate(raw['checkpoints']):
        expected = reference_read(records[g], raw['base'], raw['assay_birth'][j], raw['assay_orders'][j], d.CUES)
        check(f'independent fresh reader {g}', np.array_equal(expected, raw['reader_states'][j]))
    for label, rules in [('own', d.RULES), *[(a, d.RULES[x]) for a, x in d.DONORS.items()]]:
        for name, actual, expected in zip(('margin', 'rule', 'joint'),
                e.score(raw['reader_states'], rules), reference_score(raw['reader_states'], rules)):
            check(f'independent endpoint {label}/{name}', np.array_equal(actual, expected))
    return dict(passed=True, checks_count=len(checks), checks=checks,
                independent_body_replays=3*generations, independent_assay_replays=len(raw['checkpoints']))
