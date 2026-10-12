"""Re-encode coherent hidden patterns; test a single common replacement."""
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from h003 import experiment as e
from h005.engine import signals, success, encode, decode

DOSES = (1, 2, 4, 8)
VARIANTS = ('unchanged', 'hidden_swap')
ARMS = ('renewal', 'restored', 'foreign', 'protected_copy',
        'damaged_copy', 'read_off', 'write_off')
TRIALS = 8
SCREEN_PROBES = 8
VALIDATION_PROBES = 64


def read(packets, base, seed, *key):
    return e.read_one(packets, base, seed, ('h007', *key), 4., e.INPUTS)


def construct(seed, source):
    original = source['records']
    bodies = source['source_bodies']
    feasible = np.all(bodies[..., 1, :] == -bodies[..., 0, :], axis=-1)
    feasible &= np.all(signals(bodies) == 1, axis=-1)
    permutations = np.broadcast_to(np.arange(64), (len(DOSES), 4, 4, 64)).copy()
    for f in range(4):
        for r in range(4):
            pools = [24+np.flatnonzero(bodies[f, r, 0, 24:] == sign) for sign in (1, -1)]
            if not feasible[f, r] or min(map(len, pools)) < max(DOSES):
                feasible[f, r] = False
                continue
            pools = [e.m.rng(seed, 'h007', 'hidden_swap', f, r, sign).permutation(pool)
                     for sign, pool in zip((1, -1), pools)]
            for d, k in enumerate(DOSES):
                permutation = permutations[d, f, r]
                a, b = pools[0][:k], pools[1][:k]
                permutation[a], permutation[b] = b, a
    changed_bodies = np.take_along_axis(
        np.broadcast_to(bodies, (len(DOSES), *bodies.shape)), permutations[..., None, :], axis=-1)
    changed = e.m.write_body(changed_bodies)
    packets = np.stack([np.broadcast_to(original, changed.shape), changed], axis=1)
    return dict(packets=packets, changed_bodies=changed_bodies.astype(np.int8),
                permutations=permutations, feasible=feasible)


def matched(observed, feasible):
    # probe, dose, variant, founder, replica, four output means
    passing = np.all(observed > .5, axis=(0, 2, 5))
    equal = np.all(observed == observed[:, :, :1], axis=(0, 2, 5))
    return passing & equal & feasible[None]


def measure(seed, source):
    construction = construct(seed, source)
    packets = construction.pop('packets')
    screen = np.stack([read(packets, source['base'], seed, 'current', 'screen', p)
                       for p in range(SCREEN_PROBES)]).astype(np.int8)
    validation = np.stack([read(packets, source['base'], seed, 'current', 'validation', p)
                           for p in range(VALIDATION_PROBES)]).astype(np.int8)
    observed = signals(screen)
    gained = e.effective_weights(source['base'], packets, 4., e.INPUTS)
    return dict(**construction, packet_codes=encode(packets), doses=np.array(DOSES),
                screen_states=screen, screen_signals=observed, validation_states=validation,
                validation_signals=signals(validation), validation_success=success(validation),
                eligible=matched(observed, construction['feasible']),
                record_norm=np.linalg.norm(packets, axis=(-2, -1)),
                effective_total_norm=np.linalg.norm(gained, axis=(-2, -1)))


def initial_records(packets):
    records = np.broadcast_to(packets[:, :, None], (len(DOSES), 2, len(ARMS), 4, 4, 64, 64)).copy()
    records[:, :, ARMS.index('restored')] = packets[:, :1]
    records[:, :, ARMS.index('foreign')] = packets[:, :, [2, 3, 0, 1]]
    return records


def metrics(outgoing, packets, bodies, readers):
    own_retained = np.all(outgoing == packets[:, :, None], axis=(-2, -1))
    distinct = np.any(outgoing[:, 0] != outgoing[:, 1], axis=(-2, -1))
    body_success, reader_success = success(bodies), success(readers)
    joint = (np.all(own_retained & body_success & reader_success, axis=1) & distinct)
    return dict(own_retained=own_retained, distinct=distinct, body_success=body_success,
                reader_success=reader_success, joint_functional_retention=joint)


def one_step(seed, source, packets, trial):
    incoming = initial_records(packets)
    mask = e.m.mask_edges(e.m.rng(seed, 'h007', 'replacement', trial, 'damage'), (4, 4, 64, 64), .5)
    available = incoming * mask
    protected = ARMS.index('protected_copy')
    available[:, :, protected] = incoming[:, :, protected]
    reading = available.copy()
    reading[:, :, ARMS.index('read_off')] = 0
    body = read(reading, source['base'], seed, 'replacement', trial, 'body')
    outgoing = e.m.write_body(body)
    outgoing[:, :, protected] = incoming[:, :, protected]
    outgoing[:, :, ARMS.index('damaged_copy')] = available[:, :, ARMS.index('damaged_copy')]
    outgoing[:, :, ARMS.index('write_off')] = 0
    reader = read(outgoing, source['base'], seed, 'replacement', trial, 'assay')
    return dict(record_codes=encode(np.stack([incoming, outgoing])), damage=mask,
                bodies=body.astype(np.int8), reader_states=reader.astype(np.int8),
                **metrics(outgoing, packets, body, reader), seed=np.array(seed), trial=np.array(trial),
                doses=np.array(DOSES), variants=np.array(VARIANTS), arms=np.array(ARMS))
