"""Replay every pilot event using auditor primitives, never production dynamics."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import support as s

BASE = s.reference('E015_functional_inheritance.audit')
RENEWAL = s.reference('E022_reader_compensation.audit')


def equal(actual, expected, name):
    a, b = np.asarray(actual), np.asarray(expected)
    if a.shape != b.shape or a.dtype != b.dtype or a.tobytes() != b.tobytes():
        raise ValueError('Replay differs: '+name)


def geometry(mask):
    active = ~mask
    edges = np.empty((len(mask), 2, 16, 16), bool)
    for y in range(16):
        for x in range(16):
            edges[:, 0, y, x] = active[:, y, x] & active[:, y, (x+1) % 16]
            edges[:, 1, y, x] = active[:, y, x] & active[:, (y+1) % 16, x]
    return edges


def capture(body, edges, beta):
    x = np.tanh(beta*body)
    computed = np.zeros(edges.shape, dtype=float)
    for r, direction, y, col in np.ndindex(edges.shape):
        if not edges[r, direction, y, col]: continue
        yy, xx = (y, (col+1) % 16) if direction == 0 else ((y+1) % 16, col)
        a, b = x[r, :, y, col], x[r, :, yy, xx]
        q = ((a[0]-a[1])/2)*((b[0]-b[1])/2)
        ordinary = np.float64(0.); ordinary += a[0]*b[0]; ordinary += a[1]*b[1]; ordinary /= 2
        computed[r, direction, y, col] = q if q != 0 else ordinary
    return computed


def replay_event(path, expected_input, key, cfg, *, renewal=False, disabled=False):
    with np.load(path, allow_pickle=False) as z: raw = {k: z[k] for k in z.files}
    fields = {'incoming', 'physical', 'denominator', 'available', 'read_end', 'late_ports', 'mean_ports', 'masks', 'birth'}
    if renewal: fields |= {'outgoing', 'holding_end', 'holding_hashes'}
    if set(raw) != fields or not all(np.isfinite(x).all() for x in raw.values()):
        raise ValueError('Unexpected evidence schema or nonfinite value')
    equal(raw['incoming'], expected_input, 'incoming boundary state')
    n, p = len(expected_input), BASE.ports()
    mask = np.zeros((n, 16, 16), bool); birth = []
    permitted = np.flatnonzero(~p.any(axis=0).ravel())
    streams = []
    for i in range(n):
        mask[i].ravel()[BASE.random(*key, 'path', i, 'damage').choice(permitted, cfg['damage_cells'], replace=False)] = True
        birth.append(cfg['birth_sd']*BASE.random(*key, 'path', i, 'birth').standard_normal((16, 16)))
        streams.append(BASE.random(*key, 'path', i, 'noise'))
    birth = np.stack(birth); edges = geometry(mask)
    equal(raw['masks'], mask, 'damage'); equal(raw['birth'], birth, 'birth'); equal(raw['available'], edges, 'edges')
    physical = expected_input*edges
    if disabled: physical.fill(0.)
    denom = np.empty((n, 16, 16))
    w = abs(physical)
    for y in range(16):
        for x in range(16):
            denom[:, y, x] = w[:, 0, y, x]+w[:, 0, y, (x-1) % 16]+w[:, 1, y, x]+w[:, 1, (y-1) % 16, x]
    equal(raw['physical'], physical, 'physical packet'); equal(raw['denominator'], denom, 'normalizer')
    v = np.stack((birth, birth), axis=1)
    active = (~mask)[:, None]; cue = np.array([1., -1.])[None, :, None]
    v *= active; v[..., p[0]] = cue
    late = []
    for t in range(cfg['read_steps']):
        noise = np.stack([r.standard_normal((16, 16)) for r in streams])
        v = RENEWAL.advance_compensated(v, physical[:, None], denom[:, None], noise[:, None], cfg,
                                      t >= cfg['settling_steps'])
        v *= active; v[..., p[0]] = cue
        if t >= cfg['read_steps']-cfg['observe_steps']:
            late.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    equal(raw['read_end'], v, 'read end'); equal(raw['late_ports'], np.stack(late), 'late readouts')
    equal(raw['mean_ports'], np.stack(late).mean(axis=0), 'mean ports')
    if renewal:
        computed = capture(v, edges, cfg['writer_beta'])
        equal(raw['outgoing'], computed, 'activity capture before holding')
        streams = [BASE.random(*key, 'path', i, 'holding_noise') for i in range(n)]
        hashes = []
        for _ in range(cfg['write_steps']):
            noise = np.stack([r.standard_normal((16, 16)) for r in streams])
            v = BASE.advance(v, edges[:, None].astype(float), 2., noise[:, None], cfg)
            v *= active; v[..., p[0]] = cue
            hashes.append(np.frombuffer(hashlib.sha256(np.ascontiguousarray(v, dtype='<f8').tobytes()).digest(), np.uint8))
        equal(raw['holding_end'], v, 'holding end'); equal(raw['holding_hashes'], np.stack(hashes), 'holding trajectory')
        return computed
    return None


def audit(output):
    output = Path(output); started = time.monotonic()
    index = json.loads((output/'EVENTS.json').read_text())
    mode = index['mode']; cfg = s.config(mode)
    if index['cfg'] != cfg: raise ValueError('Configuration mismatch')
    records, weights = s.cases(mode)
    if records != index['records']: raise ValueError('Source cohort changed')
    lookup = {(r['block'], r['source_depth'], r['founder']): i for i, r in enumerate(records)}
    entries = {(x['case_id'], x['event']): x for x in index['events']}
    if len(entries) != 14*len(records) or len(entries) != len(index['events']): raise ValueError('Missing or duplicated events')
    checked = set()
    for i, record in enumerate(records):
        initial = np.repeat(weights[i][None], cfg['paths'], axis=0)
        def check(name, incoming, role, depth, repeat=0, disabled=False):
            item = entries[record['id'], name]
            key = [*s.PLAN['random_namespace'], record['block'], record['source_depth'],
                   record['founder']//2, role, depth, repeat]
            if (item['key'], item['role'], item['depth'], item['repeat'], item['disabled']) != (key, role, depth, repeat, disabled):
                raise ValueError('Event contract changed')
            if item['incoming_sha256'] != s.array_sha(incoming): raise ValueError('Record boundary mismatch')
            path = output/item['path']
            if s.sha(path) != item['sha256']: raise ValueError('Evidence hash mismatch')
            result = replay_event(path, incoming, key, cfg, renewal=role == 'renewal', disabled=disabled)
            checked.add((record['id'], name))
            return result
        check('a0', initial, 'assay', 0); check('a0_repeat', initial, 'assay', 0, 1)
        check('copy1', initial, 'assay', 1); check('copy2', initial, 'assay', 2)
        foreign = weights[lookup[record['block'], record['source_depth'], record['founder'] ^ 1]]
        random_packet = BASE.random(*s.PLAN['random_namespace'], record['block'], record['source_depth'],
            record['founder']//2, 'random_control').uniform(-1, 1, (2, 16, 16))
        check('erased', np.zeros_like(initial), 'assay', 0)
        check('random', np.repeat(random_packet[None], cfg['paths'], axis=0), 'assay', 0)
        check('foreign', np.repeat(foreign[None], cfg['paths'], axis=0), 'assay', 0)
        check('reader_disabled', initial, 'assay', 0, disabled=True)
        current = initial.copy()
        for depth in (1, 2):
            current = check(f'renew{depth}', current, 'renewal', depth)
            check(f'a{depth}', current, 'assay', depth)
            check(f'a{depth}_repeat', current, 'assay', depth, 1)
    if checked != set(entries): raise ValueError('Audit coverage mismatch')
    report = dict(status='PASS', utc=s.utc(), seconds=time.monotonic()-started,
        events_replayed=len(checked), paired_cue_assays=index['paired_cue_assays'], renewal_bodies=index['renewal_bodies'],
        scope='Separate native auditor primitives, scalar writer and boundary replay; shared NumPy runtime and declared seed contract.')
    s.dump(output/'DYNAMICS_AUDIT.json', report)
    return report
