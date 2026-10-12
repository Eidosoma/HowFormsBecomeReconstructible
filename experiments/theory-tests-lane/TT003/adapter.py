"""Fresh read-only assays and stationary full-rewrite packet renewal."""
from pathlib import Path
from types import SimpleNamespace
import json
import time

import numpy as np
import support as s

BASE = s.reference('E015_functional_inheritance.model')
RENEWAL = s.reference('E022_reader_compensation.model')


def read_body(weights, masks, birth, noise, cfg, disabled=False):
    weights = np.array(weights, dtype=float, copy=True)
    if weights.shape != (len(birth), 2, 16, 16) or not np.isfinite(weights).all():
        raise ValueError('Invalid weights')
    p = s.ports()
    if masks.shape != birth.shape or masks.shape[1:] != (16, 16) or (masks & p.any(axis=0)).any():
        raise ValueError('Invalid damage or port deletion')
    available = RENEWAL.surviving_edges(masks)
    physical = weights*available
    if disabled: physical.fill(0.)
    denominator = RENEWAL.incident_sum(abs(physical))
    active = (~masks)[:, None]
    v = np.repeat(np.asarray(birth)[:, None], 2, axis=1)
    cue = np.array([1., -1.])[None, :, None]
    v *= active; v[..., p[0]] = cue
    late = []; namespace = SimpleNamespace(**cfg)
    count = 0
    for t, draw in enumerate(noise):
        if t >= cfg['read_steps']: raise ValueError('Extra noise frame')
        v = RENEWAL.compensated_step(v, physical[:, None], denominator[:, None],
            draw[:, None], namespace, amplification=t >= cfg['settling_steps'])
        v *= active; v[..., p[0]] = cue
        if t >= cfg['read_steps']-cfg['observe_steps']:
            late.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
        count += 1
    if count != cfg['read_steps'] or not np.isfinite(v).all(): raise ValueError('Invalid read duration or state')
    late = np.stack(late)
    return dict(physical=physical, denominator=denominator, available=available,
                read_end=v, late_ports=late, mean_ports=late.mean(axis=0))


def capture(body, available, beta=3.):
    transformed = np.tanh(beta*body)
    difference = (transformed[:, 0]-transformed[:, 1])/2
    contrast = np.stack((difference*np.roll(difference, -1, -1),
                         difference*np.roll(difference, -1, -2)), axis=-3)
    ordinary = BASE.correlations(body, beta).mean(axis=1)
    computed = np.where(contrast != 0, contrast, ordinary)
    if (computed*~available).any(): raise ValueError('Capture crossed a deleted edge')
    return np.where(available, computed, 0.)


def hold(body, masks, available, noise, cfg):
    v = body.copy(); p = s.ports(); namespace = SimpleNamespace(**cfg)
    hashes = []; count = 0
    for draw in noise:
        v = BASE.step(v, available[:, None].astype(float), 2., draw[:, None], namespace)
        v *= (~masks)[:, None]; v[..., p[0]] = np.array([1., -1.])[None, :, None]
        hashes.append(np.frombuffer(bytes.fromhex(s.array_sha(v)), dtype=np.uint8)); count += 1
    if count != cfg['write_steps'] or not np.isfinite(v).all(): raise ValueError('Invalid holding duration or state')
    return dict(holding_end=v, holding_hashes=np.stack(hashes))


def simulate(weights, key, cfg, renewal=False, disabled=False):
    saved = np.array(weights, copy=True)
    masks, birth, noise = s.draws(key, len(weights), cfg)
    result = read_body(weights, masks, birth, noise, cfg, disabled)
    result.update(incoming=saved, masks=masks, birth=birth)
    if renewal:
        outgoing = capture(result['read_end'], result['available'], cfg['writer_beta'])
        result.update(hold(result['read_end'], masks, result['available'],
                           s.holding_noise(key, len(weights), cfg['write_steps']), cfg))
        result['outgoing'] = outgoing
    if not np.array_equal(saved.view(np.uint8), np.asarray(weights).view(np.uint8)):
        raise ValueError('Assay modified the input record')
    return result


def run_events(output, mode, progress=None):
    output = Path(output); folder = output/'events'; folder.mkdir(exist_ok=False)
    cfg = s.config(mode); records, weights = s.cases(mode); entries = []
    lookup = {(r['block'], r['source_depth'], r['founder']): i for i, r in enumerate(records)}
    started = time.monotonic()
    for i, record in enumerate(records):
        initial = np.repeat(weights[i][None], cfg['paths'], axis=0)
        def event(name, incoming, role, depth, repeat=0, disabled=False):
            key = s.event_key(record, role, depth, repeat)
            result = simulate(incoming, key, cfg, renewal=role == 'renewal', disabled=disabled)
            path = folder/f"{record['id']}__{name}.npz"
            with path.open('xb') as f: np.savez_compressed(f, **result)
            entry = dict(case_id=record['id'], event=name, path=str(path.relative_to(output)),
                role=role, depth=depth, repeat=repeat, key=key, disabled=disabled,
                incoming_sha256=s.array_sha(incoming), sha256=s.sha(path))
            entries.append(entry)
            # A crash retains every completed event, even before the final index.
            with (output/'events.jsonl').open('a') as f:f.write(json.dumps(entry, sort_keys=True)+'\n')
            return result
        event('a0', initial, 'assay', 0)
        event('a0_repeat', initial, 'assay', 0, 1)
        event('copy1', initial, 'assay', 1)
        event('copy2', initial, 'assay', 2)
        foreign = weights[lookup[record['block'], record['source_depth'], record['founder'] ^ 1]]
        controls = dict(erased=np.zeros_like(initial), random=np.repeat(s.random_control(record)[None], cfg['paths'], axis=0),
            foreign=np.repeat(foreign[None], cfg['paths'], axis=0), reader_disabled=initial)
        for name in s.PLAN['controls']:
            event(name, controls[name], 'assay', 0, disabled=name == 'reader_disabled')
        current = initial.copy()
        for depth in (1, 2):
            result = event(f'renew{depth}', current, 'renewal', depth)
            current = result['outgoing'].copy()
            event(f'a{depth}', current, 'assay', depth)
            event(f'a{depth}_repeat', current, 'assay', depth, 1)
        if progress: progress(record['id'])
    s.dump(output/'EVENTS.json', dict(mode=mode, cfg=cfg, records=records, events=entries,
        paired_cue_assays=len(records)*12*cfg['paths'], renewal_bodies=len(records)*2*cfg['paths'],
        simulation_seconds=time.monotonic()-started))
    return time.monotonic()-started
