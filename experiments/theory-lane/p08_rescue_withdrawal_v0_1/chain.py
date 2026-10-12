"""Own-writer successors under no rescue, one rescue, and continual repair."""
import numpy as np
import audit_optimizer
import audit_reader
import audit_serial
import lineage_dynamics as dynamics
import writer_audit
from common import equal
from read_case import replay
from repair import recipient_repair

DIAGNOSTICS = ('signs', 'candidate_costs', 'flips', 'final_improvable_nodes', 'cost',
               'initial_cost', 'winner', 'sweeps', 'selected_improvable_nodes')
BRANCHES = ['no_rescue', 'rescue_then_withdraw', 'continued_repair']


def score(means, case, margin=.25):
    target = (1. if (case // 4) % 2 == 0 else -1.) * np.array([[1., -1.], [-1., 1.]])
    aligned = means * target
    minimum, opposite = aligned.min(axis=(-2, -1)), -aligned.max(axis=(-2, -1))
    return dict(min_margin=minimum, both_pass=minimum > margin,
                opposite_margin=opposite, opposite_pass=opposite > margin)


def capture(body, mask, cfg):
    assert body.shape == (3, 2, 16, 16) and mask.shape == (16, 16)
    packet, _ = dynamics.capture(body.reshape(3, 1, 1, 2, 16, 16), mask[None, None],
        ['exact_rewrite'] * 3, cfg['development_config'], cfg['tolerance'])
    packet = packet.reshape(3, 4096)
    separate = writer_audit.writer_pair(body, writer_audit.available_edges(mask),
        cfg['development_config']['writer_beta'], cfg['tolerance'])
    flat_packet = np.ascontiguousarray(separate['exact'], dtype='<f8').view(np.uint8).reshape(3, 4096)
    equal(packet, flat_packet, 'independent native writer')
    return packet


def prepare(incoming, cfg):
    assert incoming.shape == (3, 4096)
    prepared = incoming.copy()
    w = dynamics.decode(incoming[2])
    repaired, solution, magnitude = recipient_repair(w, cfg['optimizer'])
    other = audit_optimizer.solve(audit_optimizer.independent_coupling(w),
        np.flatnonzero(dynamics.PORTS[0].ravel()), cfg['optimizer'])
    for key in DIAGNOSTICS:
        if isinstance(solution[key], np.ndarray):
            equal(solution[key], other[key], 'independent optimizer ' + key)
        else:
            assert solution[key] == other[key], key
    expected = w.copy()
    absolute = sorted(abs(float(x)) for x in w[w != 0])
    n = len(absolute)
    median = (absolute[n // 2] if n % 2 else (absolute[n // 2 - 1] + absolute[n // 2]) / 2) if n else 0.
    assert magnitude == median
    signs = solution['signs']
    if magnitude > 0:
        for plane in range(2):
            for y in range(16):
                for x in range(16):
                    if w[plane, y, x] == 0:
                        yy, xx = (y, (x + 1) % 16) if plane == 0 else ((y + 1) % 16, x)
                        expected[plane, y, x] = magnitude * int(signs[y, x]) * int(signs[yy, xx])
    equal(repaired, expected, 'independent repair construction')
    equal(repaired[w != 0], w[w != 0], 'observed weights preserved')
    prepared[2] = dynamics.encode(repaired)
    equal(prepared[:2], incoming[:2], 'withdrawal has no repair')
    fields = dict(magnitude=np.asarray(magnitude), added_edges=np.asarray(np.count_nonzero((w == 0) & (repaired != 0))),
                  **{'optimizer_' + key: np.asarray(solution[key]) for key in DIAGNOSTICS})
    return prepared, fields


def transition(incoming, event, generation, cfg):
    identity = cfg['continuation_namespace'] + ':' + str(event['block'])
    case = event['case']
    mask = dynamics.damage_masks(identity, f'E022_renewal_g{generation}', 4)[:, :, 1].reshape(16, 16, 16)[case]
    equal(mask, audit_serial.masks(identity, generation)[case], 'independent injury')
    prepared, details = prepare(incoming, cfg)
    raw = replay(prepared, mask, case, identity, generation, cfg)
    flat = audit_reader.replay(prepared, mask, case // 4, case % 4, identity, 0,
        cfg, original=True, generation=generation, rhos=[0., 0., 0.])
    equal(raw['birth'], flat['birth'], 'independent fresh reset')
    for key in ('end', 'mean_ports', 'port_windows'):
        equal(raw[key], flat[key][0], 'independent flat dynamics ' + key)
    return dict(generation=np.asarray(generation), incoming=incoming.copy(), prepared=prepared,
        outgoing=capture(raw['end'], mask, cfg), mask=mask, **raw, **score(raw['mean_ports'], case),
        applied=np.array([False, False, True]), **details)


def boundary(saved, event, cfg):
    choices = [0, 1, 1]
    data = dict(generation=np.asarray(event['generation']),
        incoming=np.repeat(saved['incoming'][None], 3, axis=0), prepared=saved['packets'][choices],
        mask=saved['mask'], birth=saved['birth'], end=saved['end'][choices],
        port_windows=saved['port_windows'][:, choices], mean_ports=saved['mean_ports'][choices],
        applied=np.array([False, True, True]))
    data.update(score(data['mean_ports'], event['case']))
    equal(data['min_margin'], saved['min_margin'][choices], 'saved boundary margins')
    assert data['both_pass'].tolist() == [False, True, True]
    data['outgoing'] = capture(data['end'], data['mask'], cfg)
    equal(data['outgoing'][0], saved['source_factual_outgoing'], 'saved factual writer')
    equal(data['outgoing'][1], data['outgoing'][2], 'identical rescued start')
    return data


def follow(initial, event, horizon, step):
    """No endpoint-dependent stopping; only each branch's written packet survives."""
    values = []
    incoming = initial.copy()
    for offset in range(1, horizon + 1):
        data = step(incoming, event, event['generation'] + offset)
        equal(data['incoming'], incoming, 'own successor input')
        values.append(data)
        incoming = data['outgoing'].copy()
    return {key: np.stack([row[key] for row in values]) for key in values[0]}


def endpoints(good):
    assert good.ndim == 2 and good.shape[1] == 3 and good.dtype == np.bool_
    uninterrupted = np.logical_and.accumulate(good, axis=0)
    first_failure = [int(np.flatnonzero(~good[:, i])[0] + 1) if (~good[:, i]).any() else None for i in range(3)]
    return dict(first_successor=good[0].tolist(), uninterrupted=uninterrupted[-1].tolist(),
        terminal=good[-1].tolist(), first_failure_offset=first_failure,
        uninterrupted_by_offset=uninterrupted.tolist())
