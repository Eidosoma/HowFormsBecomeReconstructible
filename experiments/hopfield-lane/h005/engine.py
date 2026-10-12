"""Paired packet transplantation under a common Hopfield future apparatus."""
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from h003 import experiment as e

HISTORIES = ('gain1_history', 'gain4_history')
ARMS = ('renewal', 'equalized', 'foreign', 'protected_copy', 'damaged_copy',
        'read_off', 'write_off')
CHECKPOINTS = (1, 4, 8, 16)
FORKS = 8


def signals(states):
    a = states[..., 8:16].mean(axis=-1)
    b = states[..., 16:24].mean(axis=-1)
    target = e.h001.RULES[:, None, None] * np.array([-1., 1.])
    return np.stack([target * a, -target * b], axis=-1).reshape(*a.shape[:-1], 4)


def success(states):
    return np.all(signals(states) > .5, axis=-1)


def match(screen_signals):
    passing = np.all(screen_signals > .5, axis=(0, 1, 4))
    exact = np.all(screen_signals[:, 0] == screen_signals[:, 1], axis=(0, 3))
    return passing & exact


def read(records, base, seed, *key):
    return e.read_one(records, base, seed, ('h005', *key), 4., e.INPUTS)


def encode(records):
    scaled = records * 64
    if not np.isin(scaled, [-1., 0., 1.]).all():
        raise AssertionError('Record is outside the exact ternary codebook')
    return scaled.astype(np.int8)


def decode(codes):
    return codes.astype(np.float64) / 64


def measure(seed, source):
    records, base = source['records'], source['base']
    screen = np.stack([read(records, base, seed, 'screen', p) for p in range(4)]).astype(np.int8)
    validation = np.stack([read(records, base, seed, 'validation', p) for p in range(16)]).astype(np.int8)
    screen_signals = signals(screen)
    cue_link = (records[..., :4, 8:16].mean(axis=(-2, -1)) -
                records[..., :4, 16:24].mean(axis=(-2, -1))) * 32 * e.h001.RULES[:, None]
    return dict(screen_states=screen, screen_signals=screen_signals,
                validation_states=validation, validation_signals=signals(validation),
                validation_success=success(validation), eligible=match(screen_signals),
                record_norm=np.linalg.norm(records, axis=(-2, -1)), cue_link=cue_link,
                identical_packets=np.all(records[0] == records[1], axis=(-2, -1)))


def initial_records(source):
    own = source['records']
    records = np.broadcast_to(own[:, None], (2, len(ARMS), 4, 4, 64, 64)).copy()
    records[:, ARMS.index('equalized')] = own[1]
    records[:, ARMS.index('foreign')] = own[:, [2, 3, 0, 1]]
    return records


def rollout(seed, source, fork):
    records = initial_records(source)
    codes = [encode(records)]
    bodies, masks, readers, endpoints = [], [], [], []
    for g in range(1, 17):
        mask = e.m.mask_edges(e.m.rng(seed, 'h005', 'future', fork, 'damage', g), (4, 4, 64, 64), .5)
        available = records * mask
        protected = ARMS.index('protected_copy')
        available[:, protected] = records[:, protected]
        reading = available.copy()
        reading[:, ARMS.index('read_off')] = 0
        state = read(reading, source['base'], seed, 'future', fork, 'body', g)
        outgoing = e.m.write_body(state)
        outgoing[:, protected] = records[:, protected]
        damaged = ARMS.index('damaged_copy')
        outgoing[:, damaged] = available[:, damaged]
        outgoing[:, ARMS.index('write_off')] = 0
        records = outgoing
        bodies.append(state.astype(np.int8)); masks.append(mask); codes.append(encode(records))
        if g in CHECKPOINTS:
            reader = read(records, source['base'], seed, 'future', fork, 'assay', g)
            readers.append(reader.astype(np.int8)); endpoints.append(success(reader))
    bodies = np.stack(bodies)
    body_success = success(bodies)
    endpoints = np.stack(endpoints)
    return dict(record_codes=np.stack(codes), bodies=bodies, damage=np.stack(masks),
                reader_states=np.stack(readers), success=endpoints, body_success=body_success,
                uninterrupted=np.all(body_success, axis=0) & endpoints[-1],
                checkpoints=np.array(CHECKPOINTS), arms=np.array(ARMS), histories=np.array(HISTORIES),
                seed=np.array(seed), fork=np.array(fork))
