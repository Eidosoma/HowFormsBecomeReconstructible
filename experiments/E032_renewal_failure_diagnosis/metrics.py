"""Descriptive saved-packet measurements; no dynamics or interventions."""
from collections import deque
import hashlib
import json
from pathlib import Path
import numpy as np

CONDITIONS = ('maturing', 'maturing_read_blocked', 'strength_compensated', 'intact_renewed',
              'protected_copy', 'masked_copy', 'read_blocked', 'write_blocked', 'selective', 'maturing_refresh_blocked')
ACTIVE = (0, 1, 2, 3, 6, 7, 8, 9)
GRAPH_CONDITIONS = (0, 2)
HORIZONS = (0, 1, 3, 8, 16)
DAMAGE = ('intact', 'scattered', 'square')
RULES = np.array([1., -1., 1., -1.])
PACKET_FIELDS = ('nonzero', 'strong', 'weak_nonzero', 'absolute_mass', 'mean_absolute_change',
    'changed_sign_nonzero', 'original_strong_same_strong', 'original_strong_opposite_strong',
    'physical_strong_lost', 'available_strong_before', 'weak_promoted', 'strong_weakened', 'strong_sign_flips',
    'new_strong_changed_sign', 'surviving_strong_changed_sign', 'available_weak_before', 'exact_strong_copies')
OUTPUT_FIELDS = ('both_correct', 'both_reversed', 'locked_output_failure', 'other_failure',
    'individual_cue_accuracy', 'worst_margin', 'cue_amplitude_A', 'cue_amplitude_B', 'absolute_bias_A', 'absolute_bias_B')
GRAPH_FIELDS = ('output_reachable_fraction', 'all_outputs_reachable')
TRANSITION_FIELDS = ('first_failure', 'never_failed_yet', 'new_failure', 'recovery')


def decode(packet):
    assert packet.dtype == np.uint8 and packet.shape[-1] == 4096
    return np.frombuffer(packet.tobytes(), dtype='<f8').reshape(*packet.shape[:-1], 2, 16, 16).copy()


def arrays(path, compact=False):
    with np.load(path, allow_pickle=False) as handle:
        result = {k:handle[k] for k in handle.files}
    if compact:
        index = json.loads(result.pop('__index__').tobytes())
        assert index['format'] == 'E031_compact_v1' and set(result) == set(index['retained'])
        for key, value in result.items():
            assert index['arrays'][key] == dict(shape=list(value.shape), dtype=value.dtype.str,
                sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest()), (path, key)
    for value in result.values(): assert np.isfinite(value).all()
    return result


def available(mask):
    alive = ~mask
    return np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)


def packet_features(old, new, original, live, initial=False):
    strong, before = abs(new) > .5, abs(old) > .5
    nonzero = new != 0
    opposed = (new != 0) & (original != 0) & (np.sign(new) != np.sign(original))
    promoted = live & ~before & strong
    survived = live & before & strong
    original_strong = abs(original) > .5
    total = lambda x: x.sum(axis=(-3, -2, -1))
    f = [total(nonzero), total(strong), total(nonzero & ~strong), total(abs(new)),
         abs(new-original).mean(axis=(-3, -2, -1)), total(opposed),
         total(original_strong & strong & (np.sign(new) == np.sign(original))), total(original_strong & strong & opposed),
         total(before & ~live), total(before & live), total(promoted), total(before & live & ~strong),
         total(survived & (np.sign(new) != np.sign(old))), total(promoted & opposed), total(survived & opposed),
         total(live & ~before), total(survived & (old == new))]
    values = np.stack(f, axis=-1).astype(float)
    if initial: values[..., 8:] = 0.
    else:
        np.testing.assert_array_equal(total(strong)-total(before), values[..., 10]-values[..., 8]-values[..., 11])
    return values


def output_features(value, rule):
    assert value.shape[-2:] == (2, 2)
    signed = value*rule[..., None, None]*np.array([1., -1.])[:, None]*np.array([1., -1.])[None, :]
    correct = (signed > .25).all(axis=(-2, -1))
    reversed_rule = (signed < -.25).all(axis=(-2, -1))
    locked = ((abs(value) > .25).all(axis=-2) & (value[..., 0, :]*value[..., 1, :] > 0)).any(axis=-1)
    assert not (correct & (reversed_rule | locked)).any() and not (reversed_rule & locked).any()
    remaining = ~(correct | reversed_rule | locked)
    amplitude = abs(value[..., 0, :]-value[..., 1, :])/2
    bias = abs(value[..., 0, :]+value[..., 1, :])/2
    return np.stack((correct, reversed_rule, locked, remaining, (signed > .25).all(axis=-1).mean(axis=-1),
        signed.min(axis=(-2, -1)), amplitude[..., 0], amplitude[..., 1], bias[..., 0], bias[..., 1]), axis=-1)


def graph_features(weights):
    result = np.empty((*weights.shape[:-3], 2))
    sources = [7*16+1, 7*16+2, 8*16+1, 8*16+2]
    outputs = [y*16+x for y in (3, 4, 11, 12) for x in (10, 11)]
    for index in np.ndindex(weights.shape[:-3]):
        adjacency = [[] for _ in range(256)]
        for axis, y, x in np.argwhere(abs(weights[index]) > .5):
            a = int(y*16+x)
            b = int(y*16+(x+1)%16 if axis == 0 else ((y+1)%16)*16+x)
            adjacency[a].append(b); adjacency[b].append(a)
        seen, queue = set(sources), deque(sources)
        while queue:
            for target in adjacency[queue.popleft()]:
                if target not in seen: seen.add(target); queue.append(target)
        reached = sum(node in seen for node in outputs)
        result[index] = (reached/8, reached == 8)
    return result


def transitions(correct):
    correct = correct.astype(bool)
    previous = np.concatenate((correct[:1], correct[:-1]))
    seen_failure = np.maximum.accumulate(~correct, axis=0)
    earlier_failure = np.concatenate((np.zeros_like(correct[:1]), seen_failure[:-1]))
    first = ~correct & ~earlier_failure
    new, recovery = previous & ~correct, ~previous & correct
    new[0] = False; recovery[0] = False
    return np.stack((first, ~seen_failure, new, recovery), axis=-1).astype(float)


def extract(source, block):
    original_packet = arrays(source/f'source_{block:06d}.npz')['acquired'][1]
    first = arrays(source/f'boundary_{block:06d}_g1.npz', True)
    R = first['outgoing'].shape[2]
    original = np.repeat(decode(original_packet)[:, None], R, axis=1)
    current = np.repeat(original[None], 10, axis=0)
    records = [packet_features(current, current, original, np.ones_like(current, bool), True)]
    graph = [graph_features(current[list(GRAPH_CONDITIONS)])]
    bodies = []
    for generation in range(1, 17):
        raw = first if generation == 1 else arrays(source/f'boundary_{block:06d}_g{generation}.npz', True)
        new = decode(raw['outgoing'])
        physical = available(raw['renewal_mask'])
        live = np.broadcast_to(physical, new.shape).copy(); live[[3, 4]] = True
        values = packet_features(current, new, original, live)
        np.testing.assert_array_equal(raw['retained_edges'][0], live[0] & (abs(current[0]) > .5))
        np.testing.assert_array_equal(raw['eligible_edges'][0], live[0] & (abs(current[0]) <= .5))
        assert not values[0, ..., [11, 12]].any()
        np.testing.assert_array_equal(values[0, ..., 9], values[0, ..., 16])
        records.append(values); graph.append(graph_features(new[list(GRAPH_CONDITIONS)]))
        bodies.append(output_features(raw['developed_mean_ports'], RULES[None, :, None]))
        current = new
    terminal = []
    for horizon in HORIZONS:
        raw = arrays(source/f'assay_{block:06d}_h{horizon}.npz', True)
        n = 1 if horizon == 0 else 10
        ports = raw['mean_ports'][n:, :, :, :, :, 0, :].transpose(0, 1, 2, 4, 3, 5)
        if n == 1: ports = np.repeat(ports, 10, axis=0)
        terminal.append(output_features(ports, RULES[None, :, None, None]))
    body = np.stack(bodies)
    return dict(packet=np.stack(records), graph=np.stack(graph), body=body,
                terminal=np.stack(terminal), transitions=transitions(body[..., 0]))
