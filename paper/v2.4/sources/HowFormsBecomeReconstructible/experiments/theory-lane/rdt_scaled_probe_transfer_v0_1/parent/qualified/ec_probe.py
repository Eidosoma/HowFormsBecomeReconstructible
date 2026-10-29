"""Standalone equal-read measurements with exact inherited native dynamics."""
import hashlib
import math
import time

import numpy as np

from ec_common import C, MODELS, P, ev, require, probability_matrix, probability_scalar
import audit
import fast_reader
import probes


def definition(mode):
    require(mode in ('direct8', 'direct64', 'pooled32', 'successor32'), 'Unknown measurement')
    count = 8 if mode == 'direct8' else 64 if mode == 'direct64' else 32
    return count, mode in ('pooled32', 'successor32')


def independent_scores(windows, rule):
    a = np.asarray(windows)
    require(rule in (-1, 1) and a.ndim == 5 and a.shape[1:] == (32, 1, 2, 2), 'Native task evidence shape')
    require(np.isfinite(a).all(), 'Nonfinite native response')
    means = np.array([math.fsum(values) / 32 for values in a.transpose(0, 2, 3, 4, 1).reshape(-1, 32)]).reshape(-1, 1, 2, 2)
    aligned = means * rule * np.array([[1., -1.], [-1., 1.]])
    return aligned, (aligned.min(axis=(-1, -2)) > .25).astype(np.uint8)


def measure(packet, rule, key, regime, mode, boundary, output, guard, stage=None):
    n, paired = definition(mode)
    packet = np.asarray(packet)
    require(packet.shape == (2, 16, 16) and packet.dtype == np.float64 and np.isfinite(packet).all(), 'Native packet required')
    require(regime in ('matched', 'independent') and rule in (-1, 1), 'Declared regime and task required')
    require(len(boundary) == 11, 'Shared boundary information required')
    original = packet.copy()
    wall = time.monotonic()
    cpu = time.process_time()
    branches = (['writer'] if paired else []) + ['successor' if mode == 'successor32' else 'direct']
    names = ('mask', 'birth', 'end', 'windows', 'outgoing')
    data = {branch + '_' + name: [] for branch in branches for name in names}
    forcing, audits = [], []
    primary_wall = primary_cpu = audit_wall = audit_cpu = 0.
    stage = C['benchmark']['stage'] if stage is None else stage
    for begin in range(0, n, 4):
        guard.check()
        indices = list(range(begin, min(begin + 4, n)))
        tick, ticks = time.monotonic(), time.process_time()
        if paired:
            writer_envs = [probes.environment(stage, key, i, 'writer', regime) for i in indices]
            first = fast_reader.read_batch(np.repeat(packet[None, None], len(indices), axis=0), writer_envs)
        eval_envs = [probes.environment(stage, key, i, 'evaluation', regime) for i in indices]
        incoming = first['outgoing'] if mode == 'successor32' else np.repeat(packet[None, None], len(indices), axis=0)
        second = fast_reader.read_batch(incoming, eval_envs)
        primary_wall += time.monotonic() - tick
        primary_cpu += time.process_time() - ticks
        for offset, index in enumerate(indices):
            evaluated = {name: value[offset] for name, value in second.items()}
            sources = [(branches[-1], 'evaluation', eval_envs[offset], evaluated)]
            if paired:
                written = {name: value[offset] for name, value in first.items()}
                sources.insert(0, ('writer', 'writer', writer_envs[offset], written))
            if index in (0, 32):
                tick, ticks = time.monotonic(), time.process_time()
                if paired:
                    flat_writer = audit.read_write(packet[None], *writer_envs[offset], P['reader'], P['writer']['beta'])
                    probes.compare(written, flat_writer)
                flat_input = flat_writer['outgoing'] if mode == 'successor32' else packet[None]
                flat_eval = audit.read_write(flat_input, *eval_envs[offset], P['reader'], P['writer']['beta'])
                probes.compare(evaluated, flat_eval)
                audits.append(dict(probe=index, byte_exact=True, native_reads=2 if paired else 1))
                audit_wall += time.monotonic() - tick
                audit_cpu += time.process_time() - ticks
            for branch, purpose, environment, value in sources:
                for name, array in zip(('mask', 'birth'), environment[:2], strict=True):
                    data[branch + '_' + name].append(array)
                for name in ('end', 'windows', 'outgoing'):
                    data[branch + '_' + name].append(value[name])
                forcing.append(dict(branch=branch, probe=index, purpose=purpose,
                    sha256={name: hashlib.sha256(a.tobytes()).hexdigest() for name, a in
                            zip(('mask', 'birth', 'noise'), environment, strict=True)}))
        require(original.tobytes() == packet.tobytes(), 'Protected original packet mutated')
    arrays = {name: np.stack(values) for name, values in data.items()}
    arrays.update(packet=packet.copy(), probes=np.arange(n, dtype=np.int64), boundary=np.asarray(boundary, dtype=float))
    for branch in branches:
        aligned, _, passed = probes.task(arrays[branch + '_windows'], rule)
        checked, decisions = independent_scores(arrays[branch + '_windows'], rule)
        require(np.max(abs(aligned - checked)) < 1e-12 and np.array_equal(passed, decisions), 'Separate native endpoint arithmetic differs')
        arrays[branch + '_aligned'] = aligned
        arrays[branch + '_passed'] = passed
    if mode == 'pooled32':
        q = (int(arrays['writer_passed'].sum()) + int(arrays['direct_passed'].sum())) / 64
    else:
        q = float(arrays[branches[-1] + '_passed'].mean())
    features = np.array([*boundary, q])
    probability = float(probability_matrix(features[None], MODELS[mode])[0])
    require(abs(probability - probability_scalar(features, MODELS[mode])) < 1e-12, 'Independent prediction differs')
    digest = ev.save(output.with_suffix('.npz'), arrays)
    receipt = dict(mode=mode, key=key, rule=rule, regime=regime, stage=stage, namespace=P['forcing']['namespace'],
        raw_sha256=digest, native_reads=n * (2 if paired else 1), flat_native_reads=sum(a['native_reads'] for a in audits),
        audits=audits, forcing=forcing, q=q, probability=probability, boundary=boundary,
        primary_wall_seconds=primary_wall, primary_cpu_seconds=primary_cpu,
        audit_wall_seconds=audit_wall, audit_cpu_seconds=audit_cpu,
        total_wall_seconds=time.monotonic() - wall, total_cpu_seconds=time.process_time() - cpu,
        shared_boundary_feature_cost_included=False, new_future_outcomes=0, new_fits=0)
    receipt['without_audit_wall_seconds'] = receipt['total_wall_seconds'] - audit_wall
    receipt['without_audit_cpu_seconds'] = receipt['total_cpu_seconds'] - audit_cpu
    ev.write(output.with_suffix('.json'), receipt)
    return arrays, receipt


def verify_case(records):
    """Verify identity and byte-level overlap independently of the measurement loop."""
    require(set(records) == {'direct8', 'direct64', 'pooled32', 'successor32'}, 'All standalone measurements required')
    first = records['direct64'][1]
    for mode, (raw, receipt) in records.items():
        n, paired = definition(mode)
        require(receipt['mode'] == mode and receipt['native_reads'] == n * (2 if paired else 1), 'Wrong native budget')
        require(receipt['flat_native_reads'] == sum(2 if paired else 1 for i in (0, 32) if i < n), 'Wrong flat audit schedule')
        require(raw['probes'].tolist() == list(range(n)), 'Wrong probe indices')
        require(all(receipt[k] == first[k] for k in ('key', 'rule', 'regime', 'stage', 'namespace', 'boundary')), 'Case identities differ')
        require(np.array_equal(raw['packet'], records['direct64'][0]['packet']), 'Case packet differs')
        for branch in (['writer'] if paired else []) + ['successor' if mode == 'successor32' else 'direct']:
            aligned, passed = independent_scores(raw[branch + '_windows'], receipt['rule'])
            require(np.max(abs(aligned - raw[branch + '_aligned'])) < 1e-12 and np.array_equal(passed, raw[branch + '_passed']), 'Changed saved endpoint')
        terminal_branch = 'successor' if mode == 'successor32' else 'direct'
        q = float(raw[terminal_branch + '_passed'].mean()) if mode != 'pooled32' else (
            int(raw['writer_passed'].sum()) + int(raw['direct_passed'].sum())) / 64
        require(q == receipt['q'], 'Changed saved fraction')
        require(abs(probability_scalar([*receipt['boundary'], q], MODELS[mode]) - receipt['probability']) < 1e-12, 'Changed saved probability')
    shared = [('direct8', 'direct', 'direct64', 'direct', 8),
              ('pooled32', 'direct', 'direct64', 'direct', 32),
              ('pooled32', 'writer', 'successor32', 'writer', 32)]
    for left, branch_l, right, branch_r, n in shared:
        for name in ('mask', 'birth', 'end', 'windows', 'outgoing', 'aligned', 'passed'):
            a, b = records[left][0][branch_l + '_' + name], records[right][0][branch_r + '_' + name][:n]
            require(a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes(), 'Shared-read byte mismatch')
        a = [f for f in records[left][1]['forcing'] if f['branch'] == branch_l]
        b = [f for f in records[right][1]['forcing'] if f['branch'] == branch_r][:n]
        require([f['sha256'] for f in a] == [f['sha256'] for f in b], 'Shared forcing mismatch')
    direct_noise = {f['sha256']['noise'] for f in records['direct64'][1]['forcing']}
    writer_noise = {f['sha256']['noise'] for f in records['successor32'][1]['forcing'] if f['branch'] == 'writer'}
    require(len(direct_noise) == 64 and len(writer_noise) == 32 and direct_noise.isdisjoint(writer_noise), 'Reused independent probe draw')
    return dict(status='PASS', standalone_native_reads=200, flat_native_reads=7,
                shared_read_byte_checks=21, distinct_base_environments=96, independent_endpoint_and_probability=True)
