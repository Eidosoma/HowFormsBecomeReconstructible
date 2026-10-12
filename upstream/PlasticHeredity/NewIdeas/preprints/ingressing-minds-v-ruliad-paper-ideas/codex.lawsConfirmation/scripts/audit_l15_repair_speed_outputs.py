"""Independent D097 equations, endpoints and paired-block pooling.

Does not call production simulation, displacement, measurement or summary.
Source parameter dataclasses are shared; threshold/random generation, updates,
intervention and measurement are restated. This is not a clean-room replica.
"""
from dataclasses import asdict, replace
import hashlib

import numpy as np

from laws_confirmation.io import canonical_digest

TAG = 'l15-repair-speed-v1'
RATES = (.002, .01, .05)
GAINS = (.2, 0.)
CASES = tuple((r, c, injury) for r in RATES for c in GAINS for injury in (True, False))
METRICS = ('body_profile_error', 'body_sign_agreement', 'body_cell_mae',
           'reference_profile_error', 'reference_sign_agreement',
           'reference_from_birth_mae', 'vr_mae', 'body_mean', 'reference_mean', 'clip_fraction')


def generator(tag, *parts):
    key = (tag+':'+':'.join(map(str, parts))).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:16], 'little')
    return np.random.Generator(np.random.PCG64(seed))


def nested(actual, expected):
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), 'dictionary schema drift'
        for key in expected:
            nested(actual[key], expected[key])
    elif isinstance(expected, (list, tuple)):
        assert isinstance(actual, (list, tuple)) and len(actual) == len(expected), 'sequence drift'
        for x, y in zip(actual, expected):
            nested(x, y)
    elif isinstance(expected, float):
        assert type(actual) in (float, int) and np.isfinite(actual)
        assert abs(actual-expected) <= 1e-12, (actual, expected)
    else:
        assert type(actual) is type(expected) and actual == expected, (actual, expected)


def compare(actual, expected):
    assert isinstance(actual, np.ndarray) and actual.dtype == np.float64
    assert actual.shape == expected.shape and np.isfinite(actual).all()
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-10)
    np.testing.assert_array_equal(np.sign(actual), np.sign(expected))
    return float(np.max(abs(actual-expected))) if actual.size else 0.


def parameters(meta):
    from voltage_web.config import VoltageConfig
    from setpoint_rewrite.config import RewriteConfig
    from ladder_web.config import LadderConfig
    from blueprint_web.config import BlueprintConfig
    index = meta['index']; assert type(index) is int and index >= 0
    rewrite = RewriteConfig()
    random = generator(rewrite.tissue_param_tag, index)
    tissue = replace(VoltageConfig(), tissue_index=index, coupling=rewrite.coupling_band,
                     well_asym=float(random.uniform(-.05,.05)),
                     threshold_spread=float(random.uniform(.15,.30)))
    ladder, bp = LadderConfig(), BlueprintConfig()
    nested(meta['tissue'], asdict(tissue)); nested(meta['ladder'], asdict(ladder))
    nested(meta['blueprint'], asdict(bp))
    assert (tissue.height, tissue.width) == (16,16)
    assert bp.rho == .002 and bp.c_m == .2 and tissue.dt == .2 and tissue.coupling == 1.
    return tissue, ladder, bp


def step(v, ema, ref, theta, tissue, ladder, gain, rho, noise):
    neighbors = (np.roll(v,1,-2)+np.roll(v,-1,-2)+np.roll(v,1,-1)+np.roll(v,-1,-1))/4.
    drift = v-v**3+tissue.well_asym+theta+tissue.coupling*(neighbors-v)
    drift = drift-drift.mean(axis=(-2,-1), keepdims=True)
    noise = tissue.sigma*noise
    noise = noise-noise.mean(axis=(-2,-1), keepdims=True)
    v = np.clip(v+tissue.dt*drift+noise, -2., 2.)
    ema = (1-ladder.ema_rate)*ema+ladder.ema_rate*v
    if gain > 0:
        pull = gain*(ref-v)
        pull = pull-pull.mean(axis=(-2,-1), keepdims=True)
        v = np.clip(v+tissue.dt*pull, -2., 2.)
    ref = ref+rho*(v-ref)
    return v, ema, ref


def settle(tissue, ladder, random, futures, steps, gain=.2, rho=.002, has_ref=True):
    theta = tissue.threshold_spread*generator(tissue.tissue_tag, tissue.tissue_index).standard_normal((16,16))
    start = np.full((16,16), -1.); start[:, :8] = 1.
    v = np.tile(start, (futures,1,1))
    v = v+tissue.copy_jitter*random.standard_normal(v.shape)
    ema = v.copy(); ref = v.copy() if has_ref else np.zeros_like(v)
    for _ in range(steps):
        v, ema, ref = step(v, ema, ref, theta, tissue, ladder, gain, rho,
                           random.standard_normal(v.shape))
    return np.stack((v,ema,ref)), theta


def metrics(states, settled):
    rows = []
    old, r0 = settled[0], settled[2]
    old_profile = np.mean(old, axis=0)
    for condition in states:
        times = []
        for v, _, ref in condition:
            times.append([float(abs(np.mean(v,axis=0)-old_profile).mean()),
                float(np.count_nonzero((v > 0) == (old > 0))/256), float(abs(v-old).sum()/256),
                float(abs(np.mean(ref,axis=0)-old_profile).mean()),
                float(np.count_nonzero((ref > 0) == (old > 0))/256), float(abs(ref-r0).sum()/256),
                float(abs(v-ref).sum()/256), float(v.sum()/256), float(ref.sum()/256),
                float(np.count_nonzero(abs(v) == 2)/256)])
        rows.append(times)
    return np.asarray(rows)


def check_metrics(raw):
    expected = metrics(raw['states'], raw['settled'])
    assert raw['values'].shape == expected.shape and raw['values'].dtype == np.float64
    np.testing.assert_allclose(raw['values'], expected, rtol=0, atol=1e-12)
    assert np.isfinite(raw['values']).all()
    return True


def check_life(raw, meta, cfg):
    assert set(raw) == {'theta','settled','states','values','initial_error'}
    nested(meta['config'], asdict(cfg)); nested(meta['cases'], [list(c) for c in CASES])
    index, life = meta['index'], meta['life']
    assert type(life) is int and 0 <= life < cfg.lives and meta['theta_writable'] is False
    assert raw['states'].shape == (12, len(cfg.times), 3, 16,16)
    assert raw['initial_error'].shape == () and raw['initial_error'].dtype == np.float64
    tissue, ladder, bp = parameters(meta)
    random = generator(TAG, index, life, 'settle')
    settled, theta = settle(tissue, ladder, random, 1, cfg.settle)
    error = max(compare(raw['theta'], theta), compare(raw['settled'], settled[:,0]))
    assert canonical_digest(random.bit_generator.state) == meta['settle_rng']
    birth_v = settled[0].copy()
    birth_v[:,:,2:2+cfg.strip_width] -= cfg.magnitude
    birth_v[:,:,2+cfg.distance:2+cfg.distance+cfg.strip_width] += cfg.magnitude
    d0 = float(abs(birth_v.mean(axis=1)-settled[0].mean(axis=1)).mean())
    assert d0 > 0 and np.isfinite(d0) and float(raw['initial_error']) == d0
    for ci, (rho, cm, injured) in enumerate(CASES):
        random = generator(TAG, index, life, 'recover')
        v = birth_v.copy() if injured else settled[0].copy()
        ema, ref = v.copy(), settled[2].copy()
        observed = [np.stack((v[0],ema[0],ref[0]))]
        for t in range(1,cfg.recovery+1):
            v, ema, ref = step(v, ema, ref, theta, tissue, ladder, cm, rho,
                               random.standard_normal(v.shape))
            if t in cfg.times:
                observed.append(np.stack((v[0],ema[0],ref[0])))
        error = max(error, compare(raw['states'][ci], np.stack(observed)))
        assert canonical_digest(random.bit_generator.state) == meta['recovery_rng'][ci]
    assert len(set(meta['recovery_rng'])) == 1, 'noise streams not paired'
    # The body does not read rho directly, including at the first update.
    for gain_id in range(2):
        for injury_id in range(2):
            base = 2*gain_id+injury_id
            for offset in (4,8):
                np.testing.assert_array_equal(raw['states'][base, :2, :2],
                                              raw['states'][base+offset, :2, :2])
                if gain_id == 1:
                    np.testing.assert_array_equal(raw['states'][base, :, :2],
                                                  raw['states'][base+offset, :, :2])
    check_metrics(raw)
    return dict(max_abs=error, exact_signs=True, complete_life_replay=True,
                paired_streams=True, off_gain_body_aliases=True, metrics_pass=True)


def check_source(raw, meta):
    assert set(raw) == {'theta','settled','ends'}
    arm = meta['arm']; assert arm in ('D','T','T_lesion')
    config = meta['config']; tissue, ladder, bp = parameters(meta)
    has_ref = arm != 'D'; gain = .2 if arm == 'T' else 0.; rho = .002 if has_ref else 0.
    assert meta['has_reference'] is has_ref
    random = generator(config['trajectory_seed_tag']+'-transport', arm, meta['index'])
    settled, theta = settle(tissue, ladder, random, config['futures'], config['settle_sweeps'], gain, rho, has_ref)
    error = max(compare(raw['theta'], theta), compare(raw['settled'], settled))
    assert canonical_digest(random.bit_generator.state) == meta['settle_rng']
    assert len(raw['ends']) == len(config['displacement_ladder']) == len(meta['end_rng'])
    results = {}; old = settled[0]; old_profile = old.mean(axis=1)
    for j, distance in enumerate(config['displacement_ladder']):
        v = old.copy(); width = config['strip_width']
        v[:,:,2:2+width] -= config['displacement_magnitude']
        v[:,:,2+distance:2+distance+width] += config['displacement_magnitude']
        ema, ref = v.copy(), settled[2].copy()
        d0 = abs(v.mean(axis=1)-old_profile).mean()
        for _ in range(config['recovery_sweeps']):
            v, ema, ref = step(v,ema,ref,theta,tissue,ladder,gain,rho,random.standard_normal(v.shape))
        error = max(error, compare(raw['ends'][j], np.stack((v,ema,ref))))
        assert canonical_digest(random.bit_generator.state) == meta['end_rng'][j]
        results[str(distance)] = dict(profile_recovery=float(1-abs(v.mean(axis=1)-old_profile).mean()/max(d0,1e-9)),
            sign_recovery=float(((v > 0) == (old > 0)).mean()))
    cone = 0
    for distance in config['displacement_ladder']:
        if results[str(distance)]['profile_recovery'] >= .5:
            cone = distance
    nested(meta['result'], dict(arm=arm, tissue=meta['index'], by_distance=results, spatial_cone=cone))
    return dict(max_abs=error, exact_signs=True, full_source_replay=True,
                continuing_distance_stream=True, source_metrics_pass=True)


def check_block(raw, meta, cfg, replay=True):
    assert set(raw) == {'theta','settled','states','values','initial_error'}
    nested(meta['config'], asdict(cfg))
    assert len(meta['lives']) == cfg.lives
    shapes = dict(theta=(cfg.lives,16,16), settled=(cfg.lives,3,16,16),
        states=(cfg.lives,12,len(cfg.times),3,16,16),
        values=(cfg.lives,12,len(cfg.times),10), initial_error=(cfg.lives,))
    for key, shape in shapes.items():
        assert raw[key].shape == shape and raw[key].dtype == np.float64 and np.isfinite(raw[key]).all()
    assert np.all(raw['initial_error'] > 0)
    for life, record in enumerate(meta['lives']):
        assert record['index'] == meta['index'] and type(record['life']) is int and record['life'] == life
        assert record['exact_alias_futures'] == 3
        piece = {key: value[life] for key, value in raw.items()}
        # Indexing scalar ndarray columns yields a numpy scalar; canonicalize its shape/type.
        piece['initial_error'] = np.asarray(piece['initial_error'])
        if replay:
            nested(record['replay'], check_life(piece, record, cfg))
        else:
            check_metrics(piece)
            assert record['replay']['complete_life_replay'] is True
            assert 0 <= record['replay']['max_abs'] <= 1e-10
    return True


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8 and all(b['values'].shape == (cfg.lives,12,len(cfg.times),10) for b in blocks)
    values = np.asarray([[metrics(b['states'][life], b['settled'][life])
                          for life in range(cfg.lives)] for b in blocks])
    q = np.empty((8,cfg.lives,6,len(cfg.times)))
    raw_repair = np.empty_like(q)
    for b in range(8):
        for life in range(cfg.lives):
            d0 = float(blocks[b]['initial_error'][life]); assert np.isfinite(d0) and d0 > 0
            for pair in range(6):
                injured, sham = values[b,life,2*pair,:,0], values[b,life,2*pair+1,:,0]
                q[b,life,pair] = 1-(injured-sham)/d0
                raw_repair[b,life,pair] = 1-injured/d0
    resamples = generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8))

    def stats(lives):
        b = np.array([row.mean() for row in lives])
        output = dict(mean=float(b.mean()), block_means=b.tolist(), life_values=lives.tolist(),
            pointwise_block_bootstrap_95=np.quantile(b[resamples].mean(axis=1),[.025,.975]).tolist())
        for prefix, x in (('block_',b), ('life_',lives)):
            output[prefix+'positive'] = int(np.count_nonzero(x > 1e-12))
            output[prefix+'negative'] = int(np.count_nonzero(x < -1e-12))
            output[prefix+'tied'] = int(np.count_nonzero(abs(x) <= 1e-12))
        return output

    contrasts = []
    for ti, t in enumerate(cfg.times):
        for gain in GAINS:
            slow = [(r,c) for r in RATES for c in GAINS].index((.002,gain))
            for rate in RATES[1:]:
                faster = [(r,c) for r in RATES for c in GAINS].index((rate,gain))
                contrasts.append(dict(kind='slow_minus_faster', time=t, gain=gain, faster_rho=rate,
                    **stats(q[:,:,slow,ti]-q[:,:,faster,ti])))
        for j, rate in enumerate(RATES):
            contrasts.append(dict(kind='comparator_on_minus_off', time=t, rho=rate,
                **stats(q[:,:,2*j,ti]-q[:,:,2*j+1,ti])))
    primary = [c for c in contrasts if c['kind']=='slow_minus_faster' and c['time']==cfg.primary_time
               and c['gain']==.2 and c['faster_rho']==.05][0]
    expected = dict(schema='l15_repair_speed_summary_v1', tissues=list(range(43000,43008)),
        times=list(cfg.times), cases=[list(c) for c in CASES], metrics=list(METRICS),
        values_axes='case,time,metric', cell_means=values.mean(axis=(0,1)).tolist(),
        score_cases=[[r,c] for r in RATES for c in GAINS], adjusted_repair_means=q.mean(axis=(0,1)).tolist(),
        unadjusted_injury_repair_means=raw_repair.mean(axis=(0,1)).tolist(), primary=primary,
        contrasts=contrasts, blocks=8, lives_per_block=cfg.lives, main_futures=8*cfg.lives*12,
        secondary_intervals_multiplicity_adjusted=False)
    nested(summary, expected)
    return True


if __name__ == '__main__':
    from laws_confirmation.l15_repair_speed_run import main
    main(default_command='audit')
