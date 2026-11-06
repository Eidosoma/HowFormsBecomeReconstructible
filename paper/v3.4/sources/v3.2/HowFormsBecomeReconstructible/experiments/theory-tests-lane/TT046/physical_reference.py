"""Independent AF01 reference. No imports from production or its checkers.

Structural tissue parameters and NumPy/PCG64 are shared dependencies. Physical
updates use explicit periodic neighbor indices, preserving floating operation
order so exact replay can be required. Only the online averaging comparator and
scalar reductions have the protocol's explicit absolute tolerances.
"""
import hashlib
import json
import math

import numpy as np

KEYS = ('V', 'ema', 'R', 'theta')
SOURCE_TAG = 'l22-source-recovery-v1'
REPAIR_TAG = 'l22-active-form-boundary-v1'
READ_TAG = 'l22-fixed-record-readout-v1'
CELLS = np.arange(256).reshape(16, 16)
NEIGHBORS = tuple(x.reshape(-1) for x in (
    CELLS[(np.arange(16)-1) % 16, :], CELLS[(np.arange(16)+1) % 16, :],
    CELLS[:, (np.arange(16)-1) % 16], CELLS[:, (np.arange(16)+1) % 16]))


def generator(tag, tissue, phase):
    seed = int.from_bytes(hashlib.sha256(f'{tag}:{tissue}:{phase}'.encode()).digest()[:16], 'little')
    return np.random.default_rng(seed)


class Coupled:
    def __init__(self, tag, tissue, phase, replicates):
        self.generator = generator(tag, tissue, phase)
        self.replicates = replicates

    def standard_normal(self, shape):
        assert shape[0] == 4*self.replicates
        draw = self.generator.standard_normal((self.replicates, *shape[1:]))
        return np.concatenate([draw]*4, axis=0)

    def integers(self, low, high, size):
        assert size == 4*self.replicates
        draw = self.generator.integers(low, high, self.replicates)
        return np.concatenate([draw]*4)

    def digest(self):
        data = json.dumps(self.generator.bit_generator.state, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data.encode()).hexdigest()


def exact(observed, expected, label='array'):
    assert observed.dtype == expected.dtype and observed.shape == expected.shape, label
    assert observed.tobytes() == expected.tobytes(), f'{label}: byte discrepancy'


def project(theta, norm):
    center = theta - np.mean(theta, axis=(-2, -1), keepdims=True)
    scale = np.std(center, axis=(-2, -1), keepdims=True)
    return center * (norm / np.maximum(scale, 1e-9))


def physical(v, ema, memory, applied, tissue, ema_rate, rho, gain, rng):
    """Only rung A sheet plus rung T memory; no observer/labels/parent access."""
    flat = v.reshape(len(v), 256)
    up, down, left, right = [np.take(flat, indices, axis=1).reshape(v.shape) for indices in NEIGHBORS]
    neighbor = (up + down + left + right) / 4.0
    force = v - v**3 + tissue.well_asym + applied + tissue.coupling*(neighbor-v) + 0.0
    force = force - np.mean(force, axis=(-2, -1), keepdims=True)
    noise = tissue.sigma*rng.standard_normal(v.shape)
    noise = noise - np.mean(noise, axis=(-2, -1), keepdims=True)
    next_v = np.clip(v + tissue.dt*force + noise, -2.0, 2.0)
    # Native ema observes the sheet before the memory-feedback substep.
    next_ema = (1.0-ema_rate)*ema + ema_rate*next_v
    if gain > 0:
        feedback = gain*(memory-next_v)
        feedback = feedback - np.mean(feedback, axis=(-2, -1), keepdims=True)
        next_v = np.clip(next_v + tissue.dt*feedback, -2.0, 2.0)
    next_memory = memory + rho*(next_v-memory)
    return next_v, next_ema, next_memory


def advance(state, applied, tissue, ladder, bp, cfg, rng, write=True, reference_write=True):
    v, e, r = physical(state['V'], state['ema'], state['R'], applied, tissue,
                       ladder.ema_rate, bp.rho if reference_write else 0., bp.c_m, rng)
    theta = project((1-cfg.lam)*state['theta'] + cfg.lam*np.tanh(r), cfg.norm) if write else state['theta'].copy()
    return dict(zip(KEYS, (v, e, r, theta)))


def parent(ctx, before, acquired):
    cfg, tissue = ctx['config'], ctx['tissue']
    # Independent construction of the native vertical/horizontal half planes.
    vertical = np.where(np.indices((16, 16))[1] < 8, 1., -1.)
    horizontal = np.where(np.indices((16, 16))[0] < 8, 1., -1.)
    codes = np.stack([horizontal, -horizontal, vertical, -vertical])
    exact(ctx['codes'], codes, 'teaching codebook')
    # Native threshold seed has two components, with no trailing phase colon.
    seed = int.from_bytes(hashlib.sha256(f'{tissue.tissue_tag}:{tissue.tissue_index}'.encode()).digest()[:16], 'little')
    thresholds = tissue.threshold_spread*np.random.default_rng(seed).standard_normal((16,16))
    native = project(np.broadcast_to(thresholds, (4*cfg.replicates,16,16)).copy(), cfg.norm)
    exact(ctx['native'], native, 'initial threshold field')
    rng = Coupled(SOURCE_TAG, ctx['index'], 'parent', cfg.replicates)
    v = np.broadcast_to(vertical, native.shape).copy()
    v += tissue.copy_jitter*rng.standard_normal(v.shape)
    state = dict(V=v, ema=v.copy(), R=v.copy(), theta=native.copy())
    for _ in range(cfg.settle):
        state = advance(state, state['theta'], tissue, ctx['ladder'], ctx['bp'], cfg, rng)
    for key in KEYS:
        exact(before[key], state[key], 'before teaching '+key)
    for _ in range(cfg.imprint):
        state['V'] = 1.2*np.repeat(codes, cfg.replicates, axis=0)
        state = advance(state, state['theta'], tissue, ctx['ladder'], ctx['bp'], cfg, rng)
    for key in KEYS:
        exact(acquired[key], state[key], 'parent '+key)
    return {'parent_checkpoints': 8, 'max_absolute_difference': 0.}


def source_boundary(ctx, parent, original):
    cfg, tissue = ctx['config'], ctx['tissue']
    rng = Coupled(SOURCE_TAG, ctx['index'], 'fission', cfg.replicates)
    n = len(parent['V'])
    axis, side = rng.integers(0,2,n), rng.integers(0,2,n)
    grid = np.indices((16,16))
    keep = np.stack([(grid[a]//8) == s for a, s in zip(axis, side)])
    v = np.where(keep, parent['V'], tissue.resting)
    v = v + tissue.copy_jitter*rng.standard_normal(v.shape)
    expected = dict(kept_V=v, kept_ema=v.copy(), kept_R=parent['R'], kept_theta=parent['theta'], fresh=~keep)
    scramble = v.copy()
    srng = generator(SOURCE_TAG, ctx['index'], 'shuffle')
    permutations = [srng.permutation(128) for _ in range(cfg.replicates)]
    for i in range(n):
        scramble[i][keep[i]] = v[i][keep[i]][permutations[i % cfg.replicates]]
    expected['scrambled_V'] = scramble
    # Residual damage is independently seeded per original world, not coupled
    # across messages. It is an informative comparator, not the common boundary.
    drng = generator(SOURCE_TAG, ctx['index'], 'damage')
    damage = np.empty_like(parent['theta'])
    for i, old in enumerate(parent['theta']):
        t = old-old.mean()
        unit = t/max(np.linalg.norm(t), 1e-12)
        noise = drng.standard_normal((16,16)); noise -= noise.mean()
        noise -= (noise*unit).sum()*unit
        noise /= max(np.linalg.norm(noise), 1e-12)
        damage[i] = (cfg.damage*unit + np.sqrt(max(0.,1-cfg.damage**2))*noise)*np.linalg.norm(t)
    expected['damaged_theta'] = project(damage, cfg.norm)
    for key, array in expected.items():
        exact(original[key], array, 'source boundary '+key)
    return {'source_boundary_arrays': len(expected), 'max_absolute_difference': 0.}


def repairs(physical_context, initial, tissue_index, spec, raw, metadata):
    assert set(physical_context) == {'config','tissue','ladder','bp'}
    ctx, cfg = physical_context, physical_context['config']
    assert set(initial) == set(KEYS)
    exact(initial['R'], np.zeros_like(initial['V']), 'zero repair memory')
    exact(initial['ema'], initial['V'] if spec.reset == 'native' else np.zeros_like(initial['V']), 'repair ema')
    rng = Coupled(SOURCE_TAG if spec.reset == 'native' else REPAIR_TAG, tissue_index,
                  'recovery' if spec.reset == 'native' else 'repair', cfg.replicates)
    state = {k:v.copy() for k,v in initial.items()}
    average_on = spec.reader == 'fixed' and spec.write and spec.reset == 'zero'
    running = np.zeros_like(state['V']); averaged = state['theta'].copy()
    max_average_error, checked = 0., 0
    expected_keys = {f's{s}_{k}' for s in cfg.times for k in KEYS}
    if average_on:
        expected_keys |= {f'a{s}_{k}' for s in cfg.times for k in ('mean','theta')}
    assert set(raw) == expected_keys
    for step in range(cfg.sweeps+1):
        if step:
            applied = state['theta'] if spec.reader == 'live' else initial['theta']
            state = advance(state, applied, ctx['tissue'], ctx['ladder'], ctx['bp'], cfg, rng,
                            spec.write, spec.reference_write)
            if average_on:
                running += (state['V']-running)/step
                averaged = project((1-cfg.lam)*averaged + cfg.lam*np.tanh(running), cfg.norm)
        if step in cfg.times:
            for key in KEYS:
                exact(raw[f's{step}_{key}'], state[key], f'repair s{step} {key}')
                checked += 1
            if average_on:
                for key, array in (('mean',running), ('theta',averaged)):
                    observed = raw[f'a{step}_{key}']
                    assert observed.dtype == array.dtype and observed.shape == array.shape
                    error = float(np.max(np.abs(observed-array)))
                    assert error <= 2e-12, f'averaging s{step} {key}: {error}'
                    max_average_error = max(max_average_error, error)
    assert metadata['rng_final'] == rng.digest()
    return dict(native_arrays=checked, max_native_error=0., max_average_error=max_average_error,
                rng_match=True)


def fresh_read(physical_context, packet, tissue_index, cfg, off, raw, metadata):
    assert set(physical_context) == {'config','tissue','ladder','bp'}
    assert type(packet) is bytes and len(packet) == 4*cfg.parents*2048
    theta = np.frombuffer(packet, dtype=np.float64).reshape(4*cfg.parents,16,16)
    assert np.isfinite(theta).all()
    theta = np.repeat(theta, cfg.draws, axis=0).copy()
    assert set(raw) == {f's{s}_{k}' for s in cfg.times for k in KEYS} | {'scores','probabilities','correctness','margins'}
    assert metadata['expanded_sha256'] == hashlib.sha256(theta.tobytes()).hexdigest()
    assert metadata['theta_unchanged'] is True and metadata['R_zero_every_step'] is True
    birth = Coupled(READ_TAG, tissue_index, 'assay_birth', cfg.parents*cfg.draws)
    rng = Coupled(READ_TAG, tissue_index, 'assay', cfg.parents*cfg.draws)
    v = .2*birth.standard_normal(theta.shape); v -= v.mean(axis=(-2,-1),keepdims=True)
    e, r = v.copy(), np.zeros_like(v)
    applied = np.zeros_like(theta) if off else theta
    checked = 0
    for step in range(cfg.sweeps+1):
        if step:
            v,e,r = physical(v,e,r,applied,physical_context['tissue'],
                              physical_context['ladder'].ema_rate,0.,0.,rng)
        if step in cfg.times:
            for key, value in zip(KEYS,(v,e,r,theta)):
                exact(raw[f's{step}_{key}'], value, f'fresh reader s{step} {key}')
                checked += 1
    assert metadata['rng_final'] == rng.digest()
    assert metadata['birth_rng_final'] == birth.digest()
    assert metadata['packet_sha256'] == hashlib.sha256(packet).hexdigest()
    return dict(native_arrays=checked,max_native_error=0.,rng_match=True,carrier_bytes_per_record=2048)


def scores(codes, raw, cfg):
    v = raw[f's{cfg.sweeps}_V']
    calculated = np.asarray([[math.fsum(float(a)*float(b) for a,b in zip(row.flat,code.flat))/256
                              for code in codes] for row in v])
    assert np.max(np.abs(calculated-raw['scores'])) <= 2e-13
    winners = np.abs(calculated-calculated.max(axis=1,keepdims=True)) <= 1e-12
    probability = winners/winners.sum(axis=1,keepdims=True)
    exact(raw['probabilities'],probability,'recognition/ties')
    labels = np.repeat(np.arange(4),cfg.parents*cfg.draws)
    correct = probability[np.arange(len(v)),labels].reshape(4*cfg.parents,cfg.draws)
    exact(raw['correctness'],correct,'saved correctness flags')
    margins = np.asarray([row[m]-max(row[k] for k in range(4) if k!=m)
                          for row,m in zip(calculated,labels)]).reshape(correct.shape)
    assert raw['margins'].shape == margins.shape
    assert np.max(np.abs(raw['margins']-margins)) <= 2e-13
    return probability, calculated


def record_scores(theta, parent, codes, raw, cfg, observed):
    probs, projected = scores(codes,raw,cfg)
    rows=[]
    for i,t in enumerate(theta):
        own = i//cfg.parents; partner=(own+2)%4
        j=partner*cfg.parents+i%cfg.parents
        sl=slice(i*cfg.draws,(i+1)*cfg.draws)
        def mean(vals): return math.fsum(float(x) for x in vals)/cfg.draws
        def corr(other):
            a=t.reshape(-1);b=other.reshape(-1)
            a=a-math.fsum(a)/256;b=b-math.fsum(b)/256
            den=math.sqrt(math.fsum(a*a)*math.fsum(b*b))
            return math.fsum(a*b)/den if den else 0.
        row=dict(world=i,message=own,replicate=i%cfg.parents,
            accuracy=mean(probs[sl,own]),partner_accuracy=mean(probs[sl,partner]),
            preference=mean(probs[sl,own]-probs[sl,partner]),
            projection_gap=mean(projected[sl,own]-projected[sl,partner]),
            sign_fidelity=float(np.mean((raw[f's{cfg.sweeps}_V'][sl]>0)==(codes[own]>0))),
            theta_corr_parent=corr(parent['theta'][i]),theta_corr_partner=corr(parent['theta'][j]))
        assert set(observed[i]) == set(row)
        for key,value in row.items():
            if key in ('accuracy','partner_accuracy','preference','world','message','replicate','sign_fidelity'):
                assert observed[i][key] == value, (i,key)
            else:
                assert abs(observed[i][key]-value) <= 2e-12, (i,key)
        rows.append(row)
    assert len(observed) == len(rows)
    return rows
