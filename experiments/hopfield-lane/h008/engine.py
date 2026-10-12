"""Fixed H007 packets under independently sampled sixteen-replacement futures."""
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from h003 import experiment as model
from h005.engine import signals, success, encode, decode
from h007 import engine as selected

DOSE = 8
VARIANTS = selected.VARIANTS
ARMS = selected.ARMS
FORKS = 8
GENERATIONS = 16
CHECKPOINTS = (1, 4, 8, 16)
VALIDATION_PROBES = 64


def load_candidate(out, seed):
    with np.load(Path(out)/f'inputs/candidate_{seed}.npz') as raw:
        return {key: raw[key] for key in raw.files}


def read(records, base, seed, *key):
    return model.read_one(records, base, seed, ('h008', *key), 4., model.INPUTS)


def measure(seed, source, candidate):
    packets = decode(candidate['packet_codes'])
    states = np.stack([read(packets, source['base'], seed, 'current', 'validation', p)
                       for p in range(VALIDATION_PROBES)]).astype(np.int8)
    return dict(validation_states=states, validation_signals=signals(states),
                validation_success=success(states), eligible=candidate['eligible'].copy(),
                record_norm=np.linalg.norm(packets, axis=(-2, -1)),
                effective_total_norm=np.linalg.norm(model.effective_weights(source['base'], packets, 4., model.INPUTS), axis=(-2, -1)))


def initial_records(packets):
    records = np.broadcast_to(packets[:, None], (2, len(ARMS), 4, 4, 64, 64)).copy()
    records[:, ARMS.index('restored')] = packets[0]
    records[:, ARMS.index('foreign')] = packets[:, [2, 3, 0, 1]]
    return records


def rollout(seed, source, candidate, fork):
    packets = decode(candidate['packet_codes'])
    records = initial_records(packets)
    codes = [encode(records)]
    bodies, masks, readers = [], [], []
    for g in range(1, GENERATIONS+1):
        mask = model.m.mask_edges(model.m.rng(seed, 'h008', 'future', fork, 'damage', g), (4, 4, 64, 64), .5)
        available = records*mask
        protected = ARMS.index('protected_copy')
        available[:, protected] = records[:, protected]
        reading = available.copy()
        reading[:, ARMS.index('read_off')] = 0
        body = read(reading, source['base'], seed, 'future', fork, 'body', g)
        outgoing = model.m.write_body(body)
        outgoing[:, protected] = records[:, protected]
        outgoing[:, ARMS.index('damaged_copy')] = available[:, ARMS.index('damaged_copy')]
        outgoing[:, ARMS.index('write_off')] = 0
        records = outgoing
        codes.append(encode(records))
        bodies.append(body.astype(np.int8))
        masks.append(mask)
        if g in CHECKPOINTS:
            readers.append(read(records, source['base'], seed, 'future', fork, 'assay', g).astype(np.int8))
    codes = np.stack(codes)
    bodies, readers = np.stack(bodies), np.stack(readers)
    body_success, reader_success = success(bodies), success(readers)
    # Comparing exact integer codes avoids allocating a second full float archive.
    original_codes = candidate['packet_codes'][:, None]
    own = np.all(codes == original_codes, axis=(-2, -1))
    distinct = np.any(codes[:, 0] != codes[:, 1], axis=(-2, -1))
    at = np.array(CHECKPOINTS)
    joint = np.all(own[at] & body_success[at-1] & reader_success, axis=1) & distinct[at]
    return dict(record_codes=codes, bodies=bodies, damage=np.stack(masks), reader_states=readers,
                success=reader_success, body_success=body_success,
                uninterrupted=np.all(body_success, axis=0) & reader_success[-1],
                own_retained=own, distinct=distinct, joint_functional_retention=joint,
                checkpoints=np.array(CHECKPOINTS), variants=np.array(VARIANTS), arms=np.array(ARMS),
                seed=np.array(seed), fork=np.array(fork))
