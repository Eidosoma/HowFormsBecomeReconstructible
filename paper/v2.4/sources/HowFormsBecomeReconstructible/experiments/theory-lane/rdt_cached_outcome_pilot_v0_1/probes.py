"""A native writer read followed by paired retained and rewritten fresh reads."""
import hashlib
import json
import resource
import time

import numpy as np

from bridge import PROTOCOL as P, e, audit, ev


def rng(stage, key, probe, purpose, channel):
    if purpose not in ('writer', 'evaluation') or channel not in ('injury', 'forcing'):
        raise ValueError('Declared independent purposes and random channels required')
    payload = json.dumps([P['forcing']['namespace'], stage, *key, int(probe), purpose, channel],
                         separators=(',', ':')).encode()
    seed = int.from_bytes(hashlib.sha256(payload).digest()[:16], 'little')
    return np.random.Generator(np.random.PCG64(seed))


def environment(stage, key, probe, purpose, regime):
    cfg = e.DESIGN['reader']
    available = np.flatnonzero(~e.PORTS.any(axis=0).ravel())
    mask = np.zeros((16, 16), bool)
    mask.ravel()[rng(stage, key, probe, purpose, 'injury').choice(available, 24, replace=False)] = True
    draws = rng(stage, key, probe, purpose, 'forcing').standard_normal((cfg['read_steps']+1, 2, 16, 16))
    if regime == 'matched':
        draws[:, 1] = draws[:, 0]
    elif regime != 'independent':
        raise ValueError('Unknown cue-noise regime')
    return mask, cfg['birth_sd']*draws[0], draws[1:]


def task(windows, rule):
    w = np.asarray(windows)
    if w.ndim != 5 or w.shape[-2:] != (2, 2) or w.shape[1] != e.DESIGN['reader']['observe_steps'] or rule not in (-1, 1):
        raise ValueError('Environments x late frames x branches x cues x ports required')
    if not np.isfinite(w).all():
        raise ValueError('Finite native windows required')
    aligned = w.mean(axis=1)*rule*np.array([[1., -1.], [-1., 1.]])
    margin = aligned.min(axis=(-2, -1))
    return aligned, margin, (margin > .25).astype(np.uint8)


def reduce(passed):
    passed = np.asarray(passed)
    if passed.ndim != 2 or passed.shape[1] != 2 or not np.isin(passed, [0, 1]).all() or not len(passed):
        raise ValueError('Binary retained/rewritten pair outcomes required')
    keep, rewrite = passed[:, 0], passed[:, 1]
    gained = (keep == 0)&(rewrite == 1)
    lost = (keep == 1)&(rewrite == 0)
    q_keep, q_write = float(keep.mean()), float(rewrite.mean())
    gain, loss = float(gained.mean()), float(lost.mean())
    if abs((gain-loss)-(q_write-q_keep)) > 1e-14:
        raise ArithmeticError('Paired contrast does not reconstruct the marginal difference')
    return dict(q_retain=q_keep, q_rewrite=q_write, gain=gain, loss=loss,
                net=gain-loss, pairs=len(passed), gained=int(gained.sum()), lost=int(lost.sum()))


def read_batch(weights, envs):
    """Generalized branch count; archived pointwise reader and writer arithmetic."""
    cfg = e.DESIGN['reader']
    weights = np.asarray(weights)
    if weights.ndim != 5 or weights.shape[2:] != (2, 16, 16) or len(envs) != len(weights):
        raise ValueError('Environments x branches x two-plane native packets required')
    masks, births, noises = [np.stack([v[k] for v in envs]) for k in range(3)]
    count = weights.shape[1]
    effective = weights*e.native.available_edges(masks)[:, None]
    denominator = e.native.incident(abs(effective))
    body = np.repeat(births[:, None], count, axis=1)
    alive = (~masks)[:, None, None]
    cue = np.array([1., -1.])[None, None, :, None]
    body *= alive
    body[..., e.PORTS[0]] = cue
    windows = []
    for t in range(cfg['read_steps']):
        body = e.native.step(body, effective[:, :, None], denominator[:, :, None],
                             noises[:, t, None], cfg, t >= cfg['settling_steps'])
        body *= alive
        body[..., e.PORTS[0]] = cue
        if t >= cfg['read_steps']-cfg['observe_steps']:
            windows.append(e.native.read_ports(body))
    outgoing = []
    for j in range(len(weights)):
        pairs, _ = e.native.writer_components(body[j, :, None, None], masks[j, None, None],
                                            e.DESIGN['writer']['beta'], 1e-4)
        outgoing.append(pairs['exact_rewrite'][:, 0, 0])
    return dict(end=body, windows=np.stack(windows, axis=1), outgoing=np.stack(outgoing))


def compare(primary, checked):
    errors = {}
    for name in ('end', 'windows', 'outgoing'):
        a, b = primary[name], checked[name]
        if a.shape != b.shape or a.tobytes() != b.tobytes():
            raise ArithmeticError('Separate implementation byte mismatch: '+name)
        errors[name] = float(np.max(abs(a-b)))
    return errors


def measure(packet, rule, key, regime, stage, indices, audit_indices, output, deadline, sequential=False):
    wall, cpu = time.monotonic(), time.process_time()
    original = packet.copy()
    names = ('writer_mask', 'writer_birth', 'writer_end', 'writer_windows', 'writer_outgoing',
             'evaluation_mask', 'evaluation_birth', 'evaluation_end', 'evaluation_windows', 'evaluation_outgoing')
    arrays = {name: [] for name in names}
    commitments, audit_errors = [], []
    primary_wall = primary_cpu = audit_wall = audit_cpu = sequential_cpu = 0.
    sequential_wall = evidence_wall = 0.
    indices = list(indices)
    if len(set(indices)) != len(indices) or not indices:
        raise ValueError('Distinct nonempty probe indices required')
    for offset in range(0, len(indices), 4):
        deadline.check()
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > P['resources']['maximum_resident_bytes']:
            raise MemoryError('Declared memory ceiling')
        batch = indices[offset:offset+4]
        start, start_cpu = time.monotonic(), time.process_time()
        writer_envs = [environment(stage, key, j, 'writer', regime) for j in batch]
        evaluation_envs = [environment(stage, key, j, 'evaluation', regime) for j in batch]
        writer_inputs = np.repeat(packet[None, None], len(batch), axis=0)
        first = read_batch(writer_inputs, writer_envs)
        eval_inputs = np.stack([np.stack([packet, w[0]]) for w in first['outgoing']])
        second = read_batch(eval_inputs, evaluation_envs)
        primary_wall += time.monotonic()-start; primary_cpu += time.process_time()-start_cpu
        loop_start = time.monotonic()
        old_audit_wall, old_sequential_wall = audit_wall, sequential_wall
        for j, index in enumerate(batch):
            writer = {name:value[j] for name, value in first.items()}
            evaluation = {name:value[j] for name, value in second.items()}
            if index in audit_indices:
                start, start_cpu = time.monotonic(), time.process_time()
                check_writer = audit.read_write(packet[None], *writer_envs[j], e.DESIGN['reader'], e.DESIGN['writer']['beta'])
                compare(writer, check_writer)
                # The second flat read inherits its own independently written packet.
                flat_inputs = np.stack([packet, check_writer['outgoing'][0]])
                check_evaluation = audit.read_write(flat_inputs, *evaluation_envs[j], e.DESIGN['reader'], e.DESIGN['writer']['beta'])
                compare(evaluation, check_evaluation)
                audit_errors.append(dict(probe=index, writer_max_error=0., evaluation_max_error=0., byte_exact=True))
                audit_wall += time.monotonic()-start; audit_cpu += time.process_time()-start_cpu
            if sequential and index == indices[0]:
                start_cpu = time.process_time(); start = time.monotonic()
                one = e.read_write(packet[None], *writer_envs[j]); compare(writer, one)
                two = e.read_write(np.stack([packet, one['outgoing'][0]]), *evaluation_envs[j]); compare(evaluation, two)
                sequential_cpu += time.process_time()-start_cpu
                sequential_wall += time.monotonic()-start
            record = {}
            for purpose, env, result in [('writer', writer_envs[j], writer), ('evaluation', evaluation_envs[j], evaluation)]:
                mask, birth, noise = env
                record[purpose] = {name:hashlib.sha256(a.tobytes()).hexdigest()
                                   for name,a in [('mask', mask), ('birth', birth), ('noise', noise)]}
                arrays[purpose+'_mask'].append(mask)
                arrays[purpose+'_birth'].append(birth)
                for name in ('end', 'windows', 'outgoing'):
                    arrays[purpose+'_'+name].append(result[name])
            commitments.append(dict(probe=index, purposes=record))
        if not np.array_equal(packet, original):
            raise ArithmeticError('The protected retained packet was changed')
        evidence_wall += time.monotonic()-loop_start-(audit_wall-old_audit_wall)-(sequential_wall-old_sequential_wall)
    persist_start = time.monotonic()
    arrays = {name:np.stack(value) for name,value in arrays.items()}
    arrays['packet'] = packet
    arrays['probes'] = np.array(indices, dtype=np.int64)
    for purpose in ('writer', 'evaluation'):
        aligned, margins, passed = task(arrays[purpose+'_windows'], rule)
        arrays[purpose+'_aligned'] = aligned
        arrays[purpose+'_margins'] = margins
        arrays[purpose+'_passed'] = passed
    digest = ev.save(output.with_suffix('.npz'), arrays)
    persistence_wall = time.monotonic()-persist_start
    report = dict(key=key, rule=rule, regime=regime, stage=stage, probes=indices,
        raw_sha256=digest, forcing=commitments, audit=audit_errors,
        native_reads=3*len(indices), separate_audit_reads=3*len(audit_errors),
        sequential_control_reads=3 if sequential else 0,
        primary_wall_seconds=primary_wall, primary_cpu_seconds=primary_cpu,
        audit_wall_seconds=audit_wall, audit_cpu_seconds=audit_cpu, sequential_cpu_seconds=sequential_cpu,
        sequential_wall_seconds=sequential_wall, per_probe_evidence_wall_seconds=evidence_wall,
        persistence_wall_seconds=persistence_wall,
        elapsed_wall_seconds=time.monotonic()-wall, elapsed_cpu_seconds=time.process_time()-cpu,
        new_long_horizon_outcomes=0)
    ev.write(output.with_suffix('.json'), report)
    return arrays, report
