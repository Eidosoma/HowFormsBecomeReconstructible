"""Two own-state continuations under shared fresh disturbance draws."""
import hashlib
import json
import time
import numpy as np
from study import C, P, e, audit, ev, fast_reader, digest, require, ARMS


def environment(stage, key, generation, purpose, regime):
    require(stage in ('pilot', 'benchmark', 'qualification'), 'Undeclared stage')
    require(regime in ('matched', 'independent'), 'Undeclared regime')
    require(purpose in ('writer', 'evaluation'), 'Undeclared purpose')
    def rng(channel):
        encoded = json.dumps([C['future']['namespace'], stage, *key, int(generation), purpose, channel], separators=(',', ':')).encode()
        return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(encoded).digest()[:16], 'little')))
    available = np.flatnonzero(~e.PORTS.any(axis=0).ravel())
    mask = np.zeros((16, 16), bool)
    mask.ravel()[rng('injury').choice(available, 24, replace=False)] = True
    draws = rng('forcing').standard_normal((C['reader']['read_steps'] + 1, 2, 16, 16))
    if regime == 'matched':
        draws[:, 1] = draws[:, 0]
    return mask, C['reader']['birth_sd'] * draws[0], draws[1:]


def batch(rows, initial, audit_key, regime, stage, folder, guard, seal, seal_sha):
    require(seal.exists() and ev.sha(seal) == seal_sha, 'An unchanged complete seal must precede every future')
    require(initial.shape == (len(rows), 2, 2, 16, 16), 'Two initial branches required')
    started, cpu = time.monotonic(), time.process_time()
    incoming = initial.copy()
    audit_indices = [i for i, r in enumerate(rows) if r['key'] == audit_key]
    require(len(audit_indices) == 1, 'Exactly one audit record per batch')
    flat = {i: initial[i].copy() for i in audit_indices}
    data = {n: [] for n in ('incoming', 'mask', 'birth', 'end', 'windows', 'outgoing')}
    forcing, checks = [], []
    for generation in range(15, 34):
        guard.check()
        purpose = 'writer' if generation < 33 else 'evaluation'
        environments = [environment(stage, r['key'], generation, purpose, regime) for r in rows]
        result = fast_reader.read_batch(incoming, environments)
        data['incoming'].append(incoming.copy())
        data['mask'].append(np.stack([a[0] for a in environments]))
        data['birth'].append(np.stack([a[1] for a in environments]))
        for name in ('end', 'windows', 'outgoing'):
            data[name].append(result[name])
        for i, env in enumerate(environments):
            forcing.append(dict(key=rows[i]['key'], generation=generation, purpose=purpose,
                sha256={name: digest(a) for name, a in zip(('mask', 'birth', 'noise'), env, strict=True)}))
        for i in audit_indices:
            reference = audit.read_write(flat[i], *environments[i], P['reader'], P['writer']['beta'])
            for name in ('end', 'windows', 'outgoing'):
                require(result[name][i].shape == reference[name].shape and result[name][i].tobytes() == reference[name].tobytes(), 'Flat paired dynamics mismatch: ' + name)
            if purpose == 'writer':
                flat[i] = reference['outgoing'].copy()
            checks.append(dict(key=rows[i]['key'], generation=generation, arms=list(ARMS), byte_exact=True))
        if purpose == 'writer':
            incoming = result['outgoing'].copy()
    arrays = {n: np.stack(v) for n, v in data.items()}
    aligned = arrays['windows'][-1].mean(axis=1) * np.array([r['rule'] for r in rows])[:, None, None, None] * np.array([[1., -1.], [-1., 1.]])
    minimum = aligned.min(axis=(-1, -2))
    arrays.update(initial_packets=initial, g32_packets=incoming, generations=np.arange(15, 34),
        terminal_aligned=aligned, terminal_margin=minimum, terminal_passed=(minimum > .25).astype(np.uint8))
    raw_sha = ev.save(folder / 'future.npz', arrays)
    receipt = dict(utc=ev.utc(), stage=stage, keys=[r['key'] for r in rows], regime=regime, arms=list(ARMS),
        raw_sha256=raw_sha, seal_sha256=seal_sha, forcing=forcing, audits=checks,
        primary_native_reads=38 * len(rows), flat_native_reads=38,
        wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu)
    outcomes = [dict(key=row['key'], regime=regime, control=int(arrays['terminal_passed'][i, 0]),
        repaired=int(arrays['terminal_passed'][i, 1]), control_margin=float(minimum[i, 0]), repair_margin=float(minimum[i, 1]))
        for i, row in enumerate(rows)]
    ev.write(folder / 'future.json', receipt)
    ev.write(folder / 'OUTCOMES.json', outcomes)
    return receipt, outcomes
