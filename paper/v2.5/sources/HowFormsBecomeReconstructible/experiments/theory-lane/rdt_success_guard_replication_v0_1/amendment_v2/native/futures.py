"""Eighteen inherited exact rewrites, then a fresh terminal recipient."""
import hashlib
import json
import time

import numpy as np

from bridge import P, e, audit, ev
import fast_reader
import probes


def environment(stage, key, generation, purpose, regime):
    if purpose not in ('writer', 'evaluation') or regime not in ('matched', 'independent'):
        raise ValueError('Declared future purpose and regime required')
    def random(channel):
        payload = [P['forcing']['future_namespace'], stage, *key, int(generation), purpose, channel]
        seed = int.from_bytes(hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).digest()[:16], 'little')
        return np.random.Generator(np.random.PCG64(seed))
    available = np.flatnonzero(~e.PORTS.any(axis=0).ravel())
    mask = np.zeros((16, 16), bool)
    mask.ravel()[random('injury').choice(available, 24, replace=False)] = True
    draws = random('forcing').standard_normal((P['reader']['read_steps']+1, 2, 16, 16))
    if regime == 'matched':
        draws[:, 1] = draws[:, 0]
    return mask, P['reader']['birth_sd']*draws[0], draws[1:]


def terminal_scores(windows, rows):
    aligned, margins, passed = [], [], []
    for j, row in enumerate(rows):
        a, m, y = probes.task(windows[j:j+1], row['rule'])
        aligned.append(a[0, 0]); margins.append(m[0, 0]); passed.append(y[0, 0])
    return dict(terminal_aligned=np.stack(aligned), terminal_margin=np.array(margins),
                terminal_passed=np.array(passed, np.uint8))


def batch(rows, packets, audit_key, regime, stage, output, guard, seal_path, seal_sha256):
    if not seal_path.exists() or ev.sha(seal_path) != seal_sha256:
        raise ValueError('An unchanged cohort-wide forecast seal is required before a future read')
    start, cpu = time.monotonic(), time.process_time()
    initial = np.stack(packets)
    incoming = initial[:, None].copy()
    audit_indices = [j for j, row in enumerate(rows) if row['key'] == audit_key]
    flat = {j: initial[j:j+1].copy() for j in audit_indices}
    data = {name: [] for name in ('incoming', 'mask', 'birth', 'end', 'windows', 'outgoing')}
    forcing = []; checks = []
    generations = [(g, 'writer') for g in range(15, 33)] + [(33, 'evaluation')]
    for generation, purpose in generations:
        guard.check()
        environments = [environment(stage, row['key'], generation, purpose, regime) for row in rows]
        readout = fast_reader.read_batch(incoming, environments)
        data['incoming'].append(incoming.copy())
        data['mask'].append(np.stack([v[0] for v in environments]))
        data['birth'].append(np.stack([v[1] for v in environments]))
        for name in ('end', 'windows', 'outgoing'):
            data[name].append(readout[name])
        for j, env in enumerate(environments):
            forcing.append(dict(key=rows[j]['key'], generation=generation, purpose=purpose,
                sha256={n: hashlib.sha256(a.tobytes()).hexdigest() for n, a in zip(('mask', 'birth', 'noise'), env)}))
        for j in audit_indices:
            independent = audit.read_write(flat[j], *environments[j], P['reader'], P['writer']['beta'])
            probes.compare({name: value[j] for name, value in readout.items()}, independent)
            if purpose == 'writer':
                flat[j] = independent['outgoing'].copy()
            checks.append(dict(key=rows[j]['key'], generation=generation, byte_exact=True))
        if purpose == 'writer':
            incoming = readout['outgoing'].copy()
    arrays = {name: np.stack(value) for name, value in data.items()}
    arrays.update(initial_packets=initial, g32_packets=incoming,
                  generations=np.array([g for g, _ in generations], np.int64),
                  rules=np.array([row['rule'] for row in rows], np.int8))
    arrays.update(terminal_scores(arrays['windows'][-1], rows))
    if not np.array_equal(arrays['incoming'][1:], arrays['outgoing'][:-1]):
        raise ArithmeticError('Broken inherited rewrite chain')
    if not np.array_equal(arrays['g32_packets'], arrays['outgoing'][-2]):
        raise ArithmeticError('Terminal writer output incorrectly inherited')
    digest = ev.save(output.with_suffix('.npz'), arrays)
    receipt = dict(utc=ev.utc(), stage=stage, keys=[r['key'] for r in rows], regime=regime,
        raw_sha256=digest, forecast_seal_sha256=seal_sha256, forcing=forcing, audits=checks,
        native_reads=19*len(rows), flat_native_reads=19*len(audit_indices),
        wall_seconds=time.monotonic()-start, cpu_seconds=time.process_time()-cpu)
    ev.write(output.with_suffix('.json'), receipt)
    outcomes = [dict(key=row['key'], regime=regime, passed=int(arrays['terminal_passed'][j]),
                     margin=float(arrays['terminal_margin'][j])) for j, row in enumerate(rows)]
    return receipt, outcomes
