"""Paired serial reconstruction gains, crossed with independent assay gains."""
from __future__ import annotations

import numpy as np
import model as m
from h035 import design as d, experiment as old

ROOT_SEED = 38038
GAINS = (4, 8)
PROBES = 8
EFFECTS = {
    'serial_benefit_at_gain8': ((1, 1), (0, 1)),
    'serial_benefit_at_gain4': ((1, 0), (0, 0)),
    'final_only_access': ((0, 1), (0, 0)),
    'access_after_strong_reconstruction': ((1, 1), (1, 0)),
    'combined_benefit': ((1, 1), (0, 0)),
}


def settings():
    return dict(root_seed=ROOT_SEED, reconstruction_gains=GAINS, assay_gains=GAINS,
        fresh_probes=PROBES, legacy_probe_index=0, primary_probe_indices=list(range(1, PROBES+1)),
        generations=d.GENERATIONS, checkpoints=d.CHECKPOINTS, loads=d.LOADS, arms=d.ARMS,
        sweeps=d.SWEEPS, damage=d.DAMAGE, independent_networks=8,
        pilot_blocks=list(range(8)), benchmark_blocks=list(range(4)),
        effects=EFFECTS, primary='G16 both renewal: reconstruction 8 vs 4, assay 8',
        classification='EXPOSED_COHORT_SERIAL_GUIDANCE_DIAGNOSIS', confirmation=False,
        writer_changes=False, predictor_fits=0)


def load_archive(path):
    with np.load(path) as a:
        return {key: a[key] for key in a.files}


def probes(source, cohort, block, count=PROBES):
    if cohort not in ('engineering', 'pilot', 'fixture'):
        raise ValueError('Unknown source cohort')
    births, orders = [], []
    for j, g in enumerate(source['checkpoints']):
        b, o = [source['assay_birth'][j]], [source['assay_orders'][j]]
        for p in range(count):
            key = ('H038', 'probe', cohort, int(block), int(g), p)
            b.append(m.rng(ROOT_SEED, *key, 'birth').choice([-1., 1.], size=(2, 4, 64)))
            r = m.rng(ROOT_SEED, *key, 'order')
            o.append(np.stack([r.permutation(64) for _ in range(d.SWEEPS)]))
        births.append(b); orders.append(o)
    return np.asarray(births), np.asarray(orders)


def weights(base, record, gain):
    cue = np.arange(64) < 4
    return (base+record)*np.where(cue[:, None] ^ cue[None, :], gain, 1.)


def read(record, base, birth, order, cues, gain):
    shape = (*record.shape[:-2], len(cues), 64)
    return m.relax(weights(base, record, gain)[..., None, :, :],
                   np.broadcast_to(birth, shape), order, d.INPUTS, cues)


def generate(source, cohort, block, count=PROBES):
    generations = len(source['body_birth'])
    record = np.stack([source['records'][0].copy() for _ in GAINS])
    records, bodies = [record.copy()], []
    protected, damaged, read_off, write_off, scrambled = [d.ARMS.index(a) for a in
        ('protected_copy', 'damaged_copy', 'read_off', 'write_off', 'writer_scrambled')]
    for g in range(generations):
        surviving = record*source['damage'][g]
        surviving[:, :, protected] = record[:, :, protected]
        incoming = surviving.copy(); incoming[:, :, read_off] = 0
        body = np.stack([np.stack([read(incoming[b, l], source['base'],
            source['body_birth'][g][:, schedule], source['body_orders'][g],
            d.CUES[schedule], gain) for l, schedule in enumerate(d.SCHEDULES)])
            for b, gain in enumerate(GAINS)])
        outgoing = m.write_body(body)
        outgoing[:, :, write_off] = 0
        outgoing[:, :, protected] = record[:, :, protected]
        outgoing[:, :, damaged] = surviving[:, :, damaged]
        outgoing[:, :, scrambled] = m.permute_record(outgoing[:, :, scrambled], source['permutation'])
        record = outgoing
        records.append(record.copy()); bodies.append(body.astype(np.int8))
    rec = np.stack(records, axis=1)
    body = np.stack(bodies, axis=1)
    birth, orders = probes(source, cohort, block, count)
    states = np.empty((len(birth), 2, 2, 3, 11, count+1, 4, 2, 4, 64), np.int8)
    for j, g in enumerate(source['checkpoints']):
        for r, gain in enumerate(GAINS):
            for p in range(count+1):
                states[j, :, r, :, :, p] = read(rec[:, g], source['base'],
                    birth[j, p], orders[j, p], d.CUES, gain)
    return dict(records=rec, bodies=body, states=states, probe_birth=birth, probe_orders=orders)


def score(states, load, rules=d.RULES):
    _, rule, joint = old.score(states, rules)
    return (joint if load == 2 else rule[..., load]), rule, joint


def body_success(states, load, rules=d.RULES):
    # A-only has A polarities in slots 0/1; B-only has B polarities in slots
    # 2/3. Duplicate exposures never count as two independently learned rules.
    return score(states, load, rules)[0]
