"""Body-only rewriting with independent histories and matched common tapes."""
from __future__ import annotations

import numpy as np
import model as m
from h035 import design as d


def effective_weights(base, record):
    selected = np.zeros(d.N, bool)
    selected[d.INPUTS] = True
    incident = selected[:, None] ^ selected[None, :]
    return (base + record) * np.where(incident, d.GAIN, 1.)


def read(record, base, birth, order, cues):
    """Recipient interface contains no teacher, desired answer or prior body."""
    shape = (*record.shape[:-2], len(cues), d.N)
    return m.relax(effective_weights(base, record)[..., None, :, :],
                   np.broadcast_to(birth, shape), order, d.INPUTS, cues)


def acquire(tape):
    values = np.empty((d.HISTORIES, 4, 24))
    values[..., :4] = d.CUES
    values[..., 4:8] = d.CUES
    values[..., 8:16] = d.TARGETS[..., None]
    values[..., 16:24] = -d.TARGETS[..., None]
    founder = m.relax(tape['base'],
        np.broadcast_to(tape['founder_birth'], (d.HISTORIES, 4, d.N)),
        tape['formation_orders'], d.TEACHING_SITES, values)
    initial = np.stack([m.write_body(founder[:, schedule]) for schedule in d.SCHEDULES])
    return founder, initial


def start_records(initial, permutation):
    records = np.broadcast_to(initial[:, None, :, None],
        (len(d.LOADS), len(d.ARMS), d.HISTORIES, d.REPLICATES, d.N, d.N)).copy()
    for arm, donor in d.DONORS.items():
        records[:, d.ARMS.index(arm)] = initial[:, donor, None]
    records[:, d.ARMS.index('scrambled')] = m.permute_record(initial, permutation)[:, :, None]
    records[:, d.ARMS.index('erased')] = 0
    return records


def lineage(cohort, block, generations=d.GENERATIONS):
    tape = d.inputs(cohort, block, generations)
    founder, initial = acquire(tape)
    record = start_records(initial, tape['permutation'])
    protected, damaged = [d.ARMS.index(a) for a in ('protected_copy', 'damaged_copy')]
    records, bodies, readers = [record.copy()], [], []
    for g in range(generations+1):
        if g in tape['checkpoints']:
            j = list(tape['checkpoints']).index(g)
            readers.append(read(record, tape['base'], tape['assay_birth'][j],
                                tape['assay_orders'][j], d.CUES).astype(np.int8))
        if g == generations:
            break
        surviving = record * tape['damage'][g]
        surviving[:, protected] = record[:, protected]
        incoming = surviving.copy()
        incoming[:, d.ARMS.index('read_off')] = 0
        body = np.stack([read(incoming[l], tape['base'],
            tape['body_birth'][g][:, schedule], tape['body_orders'][g], d.CUES[schedule])
            for l, schedule in enumerate(d.SCHEDULES)])
        # Complete writer gets only current body activity. Its mean coactivity
        # is explicitly bypassed in the two designated copying controls.
        outgoing = m.write_body(body)
        outgoing[:, d.ARMS.index('write_off')] = 0
        outgoing[:, protected] = record[:, protected]
        outgoing[:, damaged] = surviving[:, damaged]
        a = d.ARMS.index('writer_scrambled')
        outgoing[:, a] = m.permute_record(outgoing[:, a], tape['permutation'])
        record = outgoing
        records.append(record.copy())
        bodies.append(body.astype(np.int8))
    return dict(**tape, founder=founder.astype(np.int8), initial=initial,
        records=np.stack(records), bodies=np.stack(bodies), reader_states=np.stack(readers),
        loads=np.array(d.LOADS), arms=np.array(d.ARMS), rules=d.RULES,
        cues=d.CUES, schedules=d.SCHEDULES)


def score(states, rules=d.RULES):
    """Separate two rules, each requiring both polarities and both patches."""
    a = states[..., 8:16].mean(axis=-1)
    b = states[..., 16:24].mean(axis=-1)
    target = (np.asarray(rules)[:, :, None] * d.POLARITIES).reshape(d.HISTORIES, 1, 4)
    trial_margin = np.minimum(a*target, -b*target)
    margin = trial_margin.reshape(*trial_margin.shape[:-1], 2, 2).min(axis=-1)
    success = margin > .5
    return margin, success, success.all(axis=-1)
