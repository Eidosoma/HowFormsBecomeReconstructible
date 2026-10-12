"""Strength-preserving record interventions and a shared Hopfield future."""
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from h003 import experiment as e
from h005.engine import signals, success, encode, decode

DOSES = (4, 8, 16, 24, 32)
VARIANTS = ('unchanged', 'output_flips', 'hidden_flips')
ARMS = ('renewal', 'restored', 'foreign', 'protected_copy',
        'damaged_copy', 'read_off', 'write_off')
CHECKPOINTS = (1, 4, 8, 16)
FORKS = 8
SCREEN_PROBES = 8
VALIDATION_PROBES = 64


def read(records, base, seed, *key):
    return e.read_one(records, base, seed, ('h006', *key), 4., e.INPUTS)


def cue_link(records):
    return ((records[..., :4, 8:16].mean(axis=(-2, -1)) -
             records[..., :4, 16:24].mean(axis=(-2, -1))) *
            32 * e.h001.RULES[:, None])


def interventions(seed, source, doses=DOSES):
    """Nested balanced sign flips; no observation or outcome enters this map."""
    own = source['records']
    codes = encode(own)
    variants = np.broadcast_to(own, (len(doses), 3, *own.shape)).copy()
    masks = np.zeros(variants.shape, dtype=bool)
    feasible = np.ones((4, 4), dtype=bool)
    for f in range(4):
        for r in range(4):
            packet = codes[f, r]
            ideal = np.r_[np.full(8, e.h001.RULES[f]),
                          np.full(8, -e.h001.RULES[f])]
            if not np.all(packet[:4, 8:24] == ideal):
                feasible[f, r] = False
                continue
            pools = {}
            for location, sites in [('output', np.arange(8, 24)),
                                    ('hidden', np.arange(24, 64))]:
                for cue in range(4):
                    for sign in (1, -1):
                        pool = sites[packet[cue, sites] == sign]
                        if len(pool) < 4:
                            feasible[f, r] = False
                        pools[location, cue, sign] = e.m.rng(
                            seed, 'h006', 'mutation', f, r, location, cue, sign
                        ).permutation(pool)
            if not feasible[f, r]:
                continue
            cue_order = e.m.rng(seed, 'h006', 'mutation', f, r, 'cue_order').permutation(4)
            for v, location in enumerate(('output', 'hidden'), 1):
                edges = [(int(cue), int(pools[location, cue, sign][round_]))
                         for round_ in range(4) for cue in cue_order for sign in (1, -1)]
                for d, dose in enumerate(doses):
                    if dose not in DOSES:
                        raise ValueError('Unregistered dose')
                    for i, j in edges[:dose]:
                        variants[d, v, f, r, i, j] *= -1
                        variants[d, v, f, r, j, i] *= -1
                        masks[d, v, f, r, i, j] = masks[d, v, f, r, j, i] = True
    return dict(packets=variants, flip_masks=masks, feasible=feasible, doses=np.array(doses))


def matched(screen_signals, feasible):
    # Shape: probe, dose, variant, founder, replica, four output signals.
    passing = np.all(screen_signals > .5, axis=(0, 2, 5))
    equal = np.all(screen_signals == screen_signals[:, :, :1], axis=(0, 2, 5))
    return passing & equal & feasible[None]


def measure(seed, source, doses, stage):
    intervention = interventions(seed, source, doses)
    packets = intervention.pop('packets')
    screen = np.stack([read(packets, source['base'], seed, stage, 'screen', p)
                       for p in range(SCREEN_PROBES)]).astype(np.int8)
    validation = np.stack([read(packets, source['base'], seed, stage, 'validation', p)
                           for p in range(VALIDATION_PROBES)]).astype(np.int8)
    observed = signals(screen)
    base_weights = e.effective_weights(source['base'], packets, 4., e.INPUTS)
    return dict(**intervention, packet_codes=encode(packets), screen_states=screen,
                validation_states=validation, screen_signals=observed,
                validation_signals=signals(validation), validation_success=success(validation),
                eligible=matched(observed, intervention['feasible']),
                cue_link=cue_link(packets), record_norm=np.linalg.norm(packets, axis=(-2, -1)),
                effective_total_norm=np.linalg.norm(base_weights, axis=(-2, -1)))


def initial_records(packets):
    records = np.broadcast_to(packets[:, None], (3, len(ARMS), 4, 4, 64, 64)).copy()
    records[:, ARMS.index('restored')] = packets[0]
    records[:, ARMS.index('foreign')] = packets[:, [2, 3, 0, 1]]
    return records


def rollout(seed, source, packets, fork):
    records = initial_records(packets)
    codes = [encode(records)]
    bodies, masks, readers, endpoints = [], [], [], []
    for g in range(1, 17):
        mask = e.m.mask_edges(e.m.rng(seed, 'h006', 'future', fork, 'damage', g),
                             (4, 4, 64, 64), .5)
        available = records * mask
        protected = ARMS.index('protected_copy')
        available[:, protected] = records[:, protected]
        reading = available.copy()
        reading[:, ARMS.index('read_off')] = 0
        state = read(reading, source['base'], seed, 'future', fork, 'body', g)
        outgoing = e.m.write_body(state)
        outgoing[:, protected] = records[:, protected]
        outgoing[:, ARMS.index('damaged_copy')] = available[:, ARMS.index('damaged_copy')]
        outgoing[:, ARMS.index('write_off')] = 0
        records = outgoing
        bodies.append(state.astype(np.int8))
        masks.append(mask)
        codes.append(encode(records))
        if g in CHECKPOINTS:
            reader = read(records, source['base'], seed, 'future', fork, 'assay', g)
            readers.append(reader.astype(np.int8))
            endpoints.append(success(reader))
    bodies = np.stack(bodies)
    body_success = success(bodies)
    endpoints = np.stack(endpoints)
    return dict(record_codes=np.stack(codes), bodies=bodies, damage=np.stack(masks),
                reader_states=np.stack(readers), success=endpoints, body_success=body_success,
                uninterrupted=np.all(body_success, axis=0) & endpoints[-1],
                checkpoints=np.array(CHECKPOINTS), arms=np.array(ARMS), variants=np.array(VARIANTS),
                seed=np.array(seed), fork=np.array(fork))
