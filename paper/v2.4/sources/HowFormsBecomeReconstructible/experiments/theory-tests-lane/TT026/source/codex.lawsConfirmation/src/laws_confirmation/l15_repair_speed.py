"""D097: matched recovery-only rho intervention; native fixed theta, fixed gain."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np

from .io import canonical_digest

WS = Path(__file__).resolve().parents[2]
ORIGIN = WS.parent
RUN_ID = 'l15_repair_speed_v1_attempt1'
CONTROL_ID = 'l15_repair_speed_v1_source_controls_attempt1'
TAG = 'l15-repair-speed-v1'
TISSUES = tuple(range(43000, 43008))
DISPOSABLE = 514197
RATES = (.002, .01, .05)
GAINS = (.2, 0.)
CASES = tuple((rho, cm, injury) for rho in RATES for cm in GAINS for injury in (True, False))
FIELDS = ('V', 'ema', 'R')
METRICS = ('body_profile_error', 'body_sign_agreement', 'body_cell_mae',
           'reference_profile_error', 'reference_sign_agreement',
           'reference_from_birth_mae', 'vr_mae', 'body_mean', 'reference_mean',
           'clip_fraction')
PACKAGES = ('blueprint_web', 'ladder_web', 'voltage_web', 'growing_web',
            'setpoint_rewrite', 'contract_bridge', 'glider_test', 'xeno_bridge',
            'error_threshold', 'persuadability', 'triangle_final')
SCIENCE = ('src/laws_confirmation/l15_repair_speed.py',
           'src/laws_confirmation/l15_repair_speed_run.py',
           'scripts/audit_l15_repair_speed_outputs.py',
           'tests/test_l15_repair_speed.py', 'scripts/run_l15_repair_speed.sh',
           'protocols/L15_REPAIR_SPEED_V1.md')
SOURCE_DIGEST = 'e5ecf2e981b236b1c2d9e0becc709013cba7da0d866d30298079bab4daffbd84'


@dataclass(frozen=True)
class Config:
    lives: int = 2
    settle: int = 120
    recovery: int = 500
    times: tuple = (0, 1, 20, 80, 200, 500)
    primary_time: int = 80
    distance: int = 8
    strip_width: int = 3
    magnitude: float = .8

    def __post_init__(self):
        if any(type(x) is not int or x <= 0 for x in
               (self.lives, self.settle, self.recovery, self.distance, self.strip_width)):
            raise ValueError('positive integer dimensions required')
        if (not isinstance(self.times, tuple) or len(self.times) < 2
                or type(self.primary_time) is not int or any(type(t) is not int for t in self.times)
                or tuple(sorted(set(self.times))) != self.times or self.times[:2] != (0, 1)
                or self.times[-1] != self.recovery or self.primary_time not in self.times
                or self.primary_time <= 0):
            raise ValueError('ordered checkpoints must include 0, 1, primary and endpoint')
        if not (self.strip_width <= self.distance and 2+self.distance+self.strip_width <= 16
                and np.isfinite(self.magnitude) and 0 < self.magnitude < 2):
            raise ValueError('nonoverlapping in-bounds strips and finite positive insult required')


CONFIG = Config()


def api():
    # Install the complete native dependency path before any native import.
    for package in PACKAGES:
        directory = str(ORIGIN/package/'src')
        if directory not in sys.path:
            sys.path.insert(0, directory)
    from blueprint_web.config import BlueprintConfig
    from blueprint_web.engine import blueprint_step, settle_with_blueprint
    from ladder_web.config import LadderConfig
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import tissue_config
    from triangle_final.config import TriangleConfig
    from triangle_final import pipeline as original
    return locals()


def context(index):
    if type(index) is not int or index < 0:
        raise ValueError('nonnegative integer tissue identity required')
    a = api(); rc = a['RewriteConfig']()
    return dict(index=index, api=a, tissue=a['tissue_config'](index, rc.coupling_band, rc),
                ladder=a['LadderConfig'](), bp=a['BlueprintConfig']())


def rng(index, life, phase):
    seed = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(seed[:16], 'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d097_independent_checker', WS/SCIENCE[2])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def displaced(v, cfg=CONFIG):
    result = v.copy()
    result[..., 2:2+cfg.strip_width] -= cfg.magnitude
    result[..., 2+cfg.distance:2+cfg.distance+cfg.strip_width] += cfg.magnitude
    return result


def recover(ctx, settled, theta, life, case, cfg=CONFIG):
    if case not in CASES or type(life) is not int or life < 0:
        raise ValueError('declared condition and nonnegative life required')
    rho, cm, injury = case
    v, _, ref = (field[None].copy() for field in settled)
    if injury:
        v = displaced(v, cfg)
    ema = v.copy()  # both sham and insult receive the same EMA-reset operation
    bp = replace(ctx['bp'], rho=rho, c_m=cm)
    random = rng(ctx['index'], life, 'recover')
    saved = [np.stack((v[0], ema[0], ref[0]))]
    for t in range(1, cfg.recovery+1):
        v, ema, ref = ctx['api']['blueprint_step'](
            v, ema, ref, theta, ctx['tissue'], ctx['ladder'], bp, 'T', random)
        if t in cfg.times:
            saved.append(np.stack((v[0], ema[0], ref[0])))
    return np.stack(saved), canonical_digest(random.bit_generator.state)


def measure(states, settled):
    # condition,time,field,row,column -> condition,time,metric
    v, ref = states[:, :, 0], states[:, :, 2]
    old, ref0 = settled[0], settled[2]
    profile = old.mean(axis=-2)
    return np.stack((np.abs(v.mean(axis=-2)-profile).mean(axis=-1),
        ((v > 0) == (old > 0)).mean(axis=(-2,-1)), np.abs(v-old).mean(axis=(-2,-1)),
        np.abs(ref.mean(axis=-2)-profile).mean(axis=-1),
        ((ref > 0) == (old > 0)).mean(axis=(-2,-1)), np.abs(ref-ref0).mean(axis=(-2,-1)),
        np.abs(v-ref).mean(axis=(-2,-1)), v.mean(axis=(-2,-1)),
        ref.mean(axis=(-2,-1)), (abs(v) == 2).mean(axis=(-2,-1))), axis=-1)


def simulate_life(index, life, cfg=CONFIG, cases=CASES):
    ctx = context(index); a = ctx['api']
    random = rng(index, life, 'settle')
    v, ema, ref, theta, _ = a['settle_with_blueprint'](
        ctx['tissue'], ctx['bp'], 'T', random, None, 1, cfg.settle)
    theta.setflags(write=False)
    settled = np.stack((v[0], ema[0], ref[0]))
    outcomes = [recover(ctx, settled, theta, life, case, cfg) for case in cases]
    states = np.stack([row[0] for row in outcomes])
    d0 = float(np.abs(displaced(v, cfg).mean(axis=-2)-v.mean(axis=-2)).mean())
    if not np.isfinite(d0) or d0 <= 0:
        raise ValueError('undefined injury normalization; no denominator flooring')
    raw = dict(theta=theta, settled=settled, states=states, values=measure(states, settled),
               initial_error=np.array(d0))
    meta = dict(index=index, life=life, config=asdict(cfg), cases=[list(c) for c in cases],
        tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']),
        settle_rng=canonical_digest(random.bit_generator.state),
        recovery_rng=[row[1] for row in outcomes], theta_writable=theta.flags.writeable)
    return raw, meta


def execute_block(index, cfg=CONFIG):
    rows, records = [], []
    check = checker()
    for life in range(cfg.lives):
        raw, meta = simulate_life(index, life, cfg)
        meta['replay'] = check.check_life(raw, meta, cfg)
        # Duplicate intact future, then reverse primary injured/sham order.
        ctx = context(index)
        for case_id in (0, 1, 0):
            alias, digest = recover(ctx, raw['settled'], raw['theta'], life, CASES[case_id], cfg)
            np.testing.assert_array_equal(alias, raw['states'][case_id])
            assert digest == meta['recovery_rng'][case_id]
        meta['exact_alias_futures'] = 3
        rows.append(raw); records.append(meta)
    payload = {key: np.stack([row[key] for row in rows]) for key in rows[0]}
    return payload, dict(index=index, config=asdict(cfg), lives=records)


def contrast_stats(life_values, resamples):
    blocks = life_values.mean(axis=1)
    result = dict(mean=float(blocks.mean()), block_means=blocks.tolist(), life_values=life_values.tolist(),
        pointwise_block_bootstrap_95=np.quantile(blocks[resamples].mean(axis=1), (.025,.975)).tolist())
    for prefix, values in (('block_', blocks), ('life_', life_values)):
        for name, mask in (('positive', values > 1e-12), ('negative', values < -1e-12),
                           ('tied', abs(values) <= 1e-12)):
            result[prefix+name] = int(mask.sum())
    return result


def summarize(blocks, cfg=CONFIG):
    if len(blocks) != len(TISSUES):
        raise ValueError('all eight equally weighted tissue blocks required')
    values = np.stack([b['values'] for b in blocks])
    denom = np.stack([b['initial_error'] for b in blocks])
    if (values.shape != (8, cfg.lives, 12, len(cfg.times), len(METRICS))
            or denom.shape != (8, cfg.lives) or not np.isfinite(values).all()
            or not np.isfinite(denom).all() or np.any(denom <= 0)):
        raise ValueError('complete finite paired table with positive denominators required')
    errors = values[..., 0]
    q = 1-(errors[:, :, 0::2]-errors[:, :, 1::2])/denom[:, :, None, None]
    resamples = rng(0, 0, 'bootstrap').integers(0, 8, (10000, 8))
    contrasts = []
    for ti, t in enumerate(cfg.times):
        for gi, cm in enumerate(GAINS):
            for ri in (1, 2):
                contrast = q[:, :, gi, ti]-q[:, :, 2*ri+gi, ti]
                contrasts.append(dict(kind='slow_minus_faster', time=t, gain=cm,
                    faster_rho=RATES[ri], **contrast_stats(contrast, resamples)))
        for ri, rho in enumerate(RATES):
            contrasts.append(dict(kind='comparator_on_minus_off', time=t, rho=rho,
                **contrast_stats(q[:, :, 2*ri, ti]-q[:, :, 2*ri+1, ti], resamples)))
    primary = next(row for row in contrasts if row['kind'] == 'slow_minus_faster'
                   and row['time'] == cfg.primary_time and row['gain'] == .2 and row['faster_rho'] == .05)
    return dict(schema='l15_repair_speed_summary_v1', tissues=list(TISSUES), times=list(cfg.times),
        cases=[list(c) for c in CASES], metrics=list(METRICS), values_axes='case,time,metric',
        cell_means=values.mean(axis=(0,1)).tolist(),
        score_cases=[[rho, cm] for rho in RATES for cm in GAINS],
        adjusted_repair_means=q.mean(axis=(0,1)).tolist(),
        unadjusted_injury_repair_means=(1-errors[:, :, 0::2]/denom[:, :, None, None]).mean(axis=(0,1)).tolist(),
        primary=primary, contrasts=contrasts, blocks=8, lives_per_block=cfg.lives,
        main_futures=8*cfg.lives*len(CASES), secondary_intervals_multiplicity_adjusted=False)


def source_control(arm, index, config=None):
    a = api(); original = a['original']; config = config or a['TriangleConfig']()
    saved, ends, end_rng = {}, [], []
    settle_fn, step_fn = original.settle_with_blueprint, original.blueprint_step

    def observed_settle(*args, **kwargs):
        v, ema, ref, theta, ladder = settle_fn(*args, **kwargs)
        saved.update(theta=theta.copy(), settled=np.stack((v, ema, np.zeros_like(v) if ref is None else ref)),
                     has_reference=ref is not None,
                     settle_rng=canonical_digest(args[3].bit_generator.state))
        return v, ema, ref, theta, ladder

    count = 0

    def observed_step(*args, **kwargs):
        nonlocal count
        result = step_fn(*args, **kwargs); count += 1
        if count % config.recovery_sweeps == 0:
            v, ema, ref = result
            ends.append(np.stack((v, ema, np.zeros_like(v) if ref is None else ref)))
            end_rng.append(canonical_digest(args[8].bit_generator.state))
        return result

    try:
        original.settle_with_blueprint, original.blueprint_step = observed_settle, observed_step
        result = original.transport(config, arm, index)
    finally:
        original.settle_with_blueprint, original.blueprint_step = settle_fn, step_fn
    assert count == len(config.displacement_ladder)*config.recovery_sweeps
    raw = dict(theta=saved['theta'], settled=saved['settled'], ends=np.stack(ends))
    ctx = context(index)
    meta = dict(arm=arm, index=index, config=asdict(config), result=result,
        has_reference=saved['has_reference'], settle_rng=saved['settle_rng'], end_rng=end_rng,
        tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']))
    meta['replay'] = checker().check_source(raw, meta)
    return raw, meta


def contract():
    return dict(schema='l15_repair_speed_v1', decision='D097', law='L15', run_id=RUN_ID,
        control_id=CONTROL_ID, seed_tag=TAG, config=asdict(CONFIG), tissues=list(TISSUES),
        disposable=DISPOSABLE, cases=[list(c) for c in CASES], fields=list(FIELDS), metrics=list(METRICS),
        main_futures=192, technical_alias_futures=48, source_jobs=36,
        source_futures=36*16*3, primary='Q(.002,.2)-Q(.05,.2) at 80',
        uncertainty='10000 equal-whole-block bootstrap percentile pointwise 95',
        theta='native fixed unprojected', rho_intervention='recovery_only',
        future_noise='paired PCG64; no condition label in random address',
        saved_state_axes='life,case,time,field,row,column', full_independent_replay=True,
        state_atol=1e-10, metrics_atol=1e-12, exact_signs=True,
        biological_or_adoption_or_heredity_claim=False, automatic_follow_on=False,
        automatic_retry=False, source_outcomes_known=True)
