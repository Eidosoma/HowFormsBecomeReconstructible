"""D111: bounded qualification of bulk-matched body-context steering.

Native E53 dynamics, a declared centred injury, no donor reference transfer.
Source outcomes are known; only the eight frozen qualification tissues are new.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import sys

import numpy as np

from . import l15_repair_speed as native
from .io import canonical_digest

WS, ORIGIN = native.WS, native.ORIGIN
RUN_ID = 'l16_body_content_qualification_v1_attempt1'
CONTROL_ID = 'l16_body_content_v1_source_controls_attempt1'
TAG = 'l16-body-content-v1'
TISSUES = tuple(range(56000, 56008))
DISPOSABLE = 514211
PACKAGES = native.PACKAGES + ('hidden_genome',)
KINDS = ('intact', 'shuffled', 'alternative', 'sham', 'full_own', 'full_alternative')
GAINS = (.2, 0.)
CASES = tuple((role, gain, kind) for role in (0, 1) for gain in GAINS for kind in KINDS)
FIELDS = ('V', 'ema', 'R')
METRICS = ('own_fidelity', 'alternative_fidelity', 'amp_fraction', 'body_mean',
           'body_rms', 'reference_mean', 'reference_rms', 'vr_mae', 'roughness')
SCIENCE = ('src/laws_confirmation/l16_body_content.py',
           'src/laws_confirmation/l16_body_content_run.py',
           'scripts/audit_l16_body_content_outputs.py',
           'tests/test_l16_body_content.py', 'scripts/run_l16_body_content.sh',
           'protocols/L16_BODY_CONTENT_V1.md')


@dataclass(frozen=True)
class Config:
    lives: int = 2
    settle: int = 120
    recovery: int = 240
    times: tuple = (0, 1, 20, 80, 240)
    amp_threshold: float = .2

    def __post_init__(self):
        if any(type(x) is not int or x <= 0 for x in (self.lives, self.settle, self.recovery)):
            raise ValueError('positive integer clocks/lives required')
        if (not isinstance(self.times, tuple) or len(self.times) < 2
                or any(type(t) is not int for t in self.times)
                or self.times != tuple(sorted(set(self.times)))
                or self.times[:2] != (0, 1) or self.times[-1] != self.recovery):
            raise ValueError('ordered checkpoints including birth, step1 and endpoint required')
        if not np.isfinite(self.amp_threshold) or not 0 < self.amp_threshold < 2:
            raise ValueError('finite positive amplitude threshold required')


CONFIG = Config()


def api():
    a = native.api()
    path = str(ORIGIN / 'hidden_genome/src')
    if path not in sys.path:
        sys.path.insert(0, path)
    from hidden_genome import knives, pipeline
    from hidden_genome.config import KnifeConfig
    from contract_bridge.artifacts import seed_rng
    return a | dict(knives=knives, original=pipeline, KnifeConfig=KnifeConfig, seed_rng=seed_rng)


def context(index):
    c = native.context(index)
    c['api'] = api()
    return c


def rng(index, life, phase):
    payload = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(payload[:16], 'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d111_independent_checker', WS / SCIENCE[2])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def injury_mask():
    mask = np.zeros((16, 16), dtype=bool)
    mask[4:12, 4:12] = True
    return mask


def rank_match(values, guide):
    """Preserve the exact multiset; guide supplies only a stable spatial rank."""
    if (values.shape != guide.shape or values.ndim != 1 or not values.size
            or values.dtype != np.float64 or guide.dtype != np.float64
            or not np.isfinite(values).all() or not np.isfinite(guide).all()):
        raise ValueError('matching finite nonempty float64 vectors required')
    output = np.empty_like(values)
    output[np.argsort(guide, kind='stable')] = np.sort(values, kind='stable')
    return output


def birth(sources, role, kind, permutation, resting):
    if (sources.shape != (2, 3, 16, 16) or sources.dtype != np.float64
            or not np.isfinite(sources).all() or type(role) is not int or role not in (0, 1)
            or kind not in KINDS or not np.isfinite(resting)):
        raise ValueError('declared finite source pair/role/kind required')
    if (permutation.shape != (192,) or permutation.dtype != np.int64
            or not np.array_equal(np.sort(permutation), np.arange(192))):
        raise ValueError('bijection on the surviving 192 sites required')
    mask = injury_mask()
    v = sources[role, 0].copy()
    alt = sources[1-role, 0]
    if kind == 'full_alternative':
        v = rank_match(v.ravel(), alt.ravel()).reshape(16, 16)
    elif kind != 'full_own':
        v[mask] = resting
        if kind == 'shuffled':
            v[~mask] = v[~mask][permutation]
        elif kind == 'alternative':
            v[~mask] = rank_match(v[~mask], alt[~mask])
        elif kind == 'sham':
            v[~mask] = rank_match(v[~mask], sources[role, 0][~mask])
    # E53 resets EMA to manipulated V; recipient R persists, no donor R/EMA.
    return np.stack((v, v.copy(), sources[role, 2].copy()))


def evolve(initial, theta, ctx, random, gain, cfg):
    if gain not in GAINS:
        raise ValueError('declared gain required')
    v, ema, ref = (a[None].copy() for a in initial)
    saved = [initial.copy()]
    for t in range(1, cfg.recovery+1):
        v, ema, ref = ctx['api']['blueprint_step'](v, ema, ref, theta,
            ctx['tissue'], ctx['ladder'], ctx['bp'], 'T', random, c_m=gain)
        if t in cfg.times:
            saved.append(np.stack((v[0], ema[0], ref[0])))
    return np.stack(saved), canonical_digest(random.bit_generator.state)


def measurements(states, sources, cfg=CONFIG):
    if (states.shape != (24, len(cfg.times), 3, 16, 16)
            or sources.shape != (2, 3, 16, 16) or not np.isfinite(states).all()
            or not np.isfinite(sources).all()):
        raise ValueError('complete finite states and source pair required')
    mask = injury_mask()
    result = []
    for (role, _, _), trace in zip(CASES, states):
        v, ref = trace[:, 0], trace[:, 2]
        amp = np.abs(v) > cfg.amp_threshold
        score = lambda target: (((v > 0) == (target > 0)) & amp)[:, mask].mean(axis=-1)
        means = lambda x: x.mean(axis=(-2, -1))
        rough = (abs(v-np.roll(v, 1, -1)) + abs(v-np.roll(v, 1, -2))) / 2
        result.append(np.stack((score(sources[role, 0]), score(sources[1-role, 0]),
            means(amp), means(v), np.sqrt(means(v*v)), means(ref),
            np.sqrt(means(ref*ref)), means(abs(v-ref)), means(rough)), axis=-1))
    return np.stack(result)


def simulate_life(index, life, cfg=CONFIG, order=CASES):
    if type(life) is not int or not 0 <= life < cfg.lives or set(order) != set(CASES) or len(order) != 24:
        raise ValueError('complete unique conditions and declared life required')
    ctx = context(index); a = ctx['api']; theta = a['knives'].tissue_theta(ctx['tissue'])
    theta.setflags(write=False)
    sources, source_rng = [], []
    for seed_index in (0, 1):
        random = rng(index, life, 'settle')  # source launches share jitter/noise
        v, ema, ref, _ = a['knives'].settle_T(ctx['tissue'], ctx['bp'], theta,
            random, 1, cfg.settle, seed_index)
        sources.append(np.stack((v[0], ema[0], ref[0])))
        source_rng.append(canonical_digest(random.bit_generator.state))
    sources = np.stack(sources)
    permutations = np.stack([rng(index, life, f'shuffle:{role}').permutation(192) for role in (0, 1)])
    records = {}
    for role, gain, kind in order:
        initial = birth(sources, role, kind, permutations[role], ctx['tissue'].resting)
        records[(role, gain, kind)] = evolve(initial, theta, ctx,
            rng(index, life, 'regrow'), gain, cfg)
    states = np.stack([records[c][0] for c in CASES])
    raw = dict(theta=theta.copy(), sources=sources, permutations=permutations,
               states=states, values=measurements(states, sources, cfg))
    meta = dict(index=index, life=life, config=asdict(cfg), cases=[list(c) for c in CASES],
        tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']),
        source_rng=source_rng, branch_rng=[records[c][1] for c in CASES],
        theta_writable=False, donor_reference_transferred=False, ema_reset_to_birth_v=True)
    return raw, meta


def execute_block(index, cfg=CONFIG):
    raw_rows, meta_rows = [], []
    audit = checker()
    for life in range(cfg.lives):
        raw, meta = simulate_life(index, life, cfg)
        meta['replay'] = audit.check_life(raw, meta, cfg, replay=True)
        raw_rows.append(raw); meta_rows.append(meta)
    return {k: np.stack([r[k] for r in raw_rows]) for k in raw_rows[0]}, dict(
        index=index, config=asdict(cfg), lives=meta_rows)


def summarize(blocks, cfg=CONFIG):
    if len(blocks) != 8:
        raise ValueError('eight tissue blocks required')
    v = np.stack([b['values'] for b in blocks])
    if v.shape != (8, cfg.lives, 24, len(cfg.times), 9) or not np.isfinite(v).all():
        raise ValueError('complete finite measurements required')
    samples = rng(0, 0, 'bootstrap').integers(0, 8, size=(10000, 8))
    stats = lambda x: native.contrast_stats(x, samples)
    preference = v[..., 1]-v[..., 0]
    ix = lambda role, gain, kind: CASES.index((role, gain, kind))
    contrasts = []
    for ti, t in enumerate(cfg.times):
        for gain in GAINS:
            for name, left, right in (
                    ('alternative_minus_shuffled_preference', 'alternative', 'shuffled'),
                    ('alternative_minus_intact_preference', 'alternative', 'intact'),
                    ('full_alternative_minus_full_own_preference', 'full_alternative', 'full_own')):
                effects = [preference[:, :, ix(r, gain, left), ti]-preference[:, :, ix(r, gain, right), ti]
                           for r in (0, 1)]
                for role, effect in [(0, effects[0]), (1, effects[1]), ('both', sum(effects)/2)]:
                    contrasts.append(dict(name=name, gain=gain, time=t, role=role, **stats(effect)))
            effects = [v[:, :, ix(r, gain, 'intact'), ti, 0]-v[:, :, ix(r, gain, 'shuffled'), ti, 0]
                       for r in (0, 1)]
            contrasts.append(dict(name='intact_minus_shuffled_own_fidelity', gain=gain,
                time=t, role='both', **stats(sum(effects)/2)))
    select = lambda name, gain, role='both': next(c for c in contrasts
        if c['name'] == name and c['gain'] == gain and c['role'] == role and c['time'] == cfg.recovery)
    primary = select('alternative_minus_shuffled_preference', 0.)
    gates = [select('full_alternative_minus_full_own_preference', 0., role) for role in (0, 1)]
    disagreements = [[int(np.count_nonzero(((b['sources'][life, 0, 0] > 0) !=
        (b['sources'][life, 1, 0] > 0)) & injury_mask())) for life in range(cfg.lives)] for b in blocks]
    readable = bool(np.all(np.asarray(disagreements) > 0) and
                    all(g['pointwise_block_bootstrap_95'][0] > 0 for g in gates))
    directional = [select('alternative_minus_shuffled_preference', 0., role) for role in (0, 1)]
    positive = bool(primary['pointwise_block_bootstrap_95'][0] > 0 and
                    all(c['mean'] > 0 for c in directional))
    label = ('READOUT_NOT_QUALIFIED' if not readable else 'QUALIFIED_CONTEXT_STEERING'
             if positive else 'CONTEXT_STEERING_UNRESOLVED')
    return dict(schema='l16_body_content_qualification_v1', tissues=list(TISSUES),
        primary=primary, readout_gates=gates, directional_primary=directional,
        readout_qualified=readable, label=label, target_disagreement_cells=disagreements,
        contrasts=contrasts, cell_means=v.mean(axis=(0, 1)).tolist(), cases=[list(c) for c in CASES],
        times=list(cfg.times), metrics=list(METRICS), blocks=8, lives_per_block=cfg.lives,
        independent_main_confirmation_run=False, secondary_intervals_multiplicity_adjusted=False,
        absolute_fidelity_gate=None)


def source_control(index):
    """Replay all 20 E53 arms; save source pair and final V without monkeypatches."""
    if type(index) is not int or index not in range(6):
        raise ValueError('known E53 tissue 0..5 only')
    ctx = context(index); a = ctx['api']; cfg = a['KnifeConfig'](); k = a['knives']
    theta = k.tissue_theta(ctx['tissue']); region = k.quarter_mask(ctx['tissue'])
    starts = []
    for phase, seed in (('settle', 0), ('alt', 1)):
        v, ema, ref, _ = k.settle_T(ctx['tissue'], ctx['bp'], theta,
            a['seed_rng'](cfg.trajectory_seed_tag, phase, index), 8, 120, seed)
        starts.append(np.stack((v, ema, ref)))
    sources = np.stack(starts)
    krng = a['seed_rng'](cfg.trajectory_seed_tag, 'knife', index)
    variants = {kind: k.theta_knife(theta, region, kind, krng) for kind in ('intact', 'scrambled', 'zeroed')}
    entry = dict(tissue=index, fidelity={}, fidelity_vs_alt={}, floor={})
    finals = []
    for label, gain in (('R_on', None), ('R_off', 0.)):
        cases = [('floor', 'intact')] + [(c, th) for c in ('intact', 'reset', 'transplant')
                                        for th in ('intact', 'scrambled', 'zeroed')]
        for c, th in cases:
            v0 = sources[0, 0].copy() if c == 'floor' else np.where(region[None], ctx['tissue'].resting, sources[0, 0])
            if c != 'floor':
                v0 = k.context_knife(v0, region, c, ctx['tissue'].resting, sources[1, 0])
            v = a['original']._regrow(v0, sources[0, 2].copy(), variants[th], ctx['tissue'],
                ctx['ladder'], ctx['bp'], a['seed_rng'](cfg.trajectory_seed_tag, 'regrow', index), 240, gain)
            finals.append(v)
            score = k.region_fidelity(v, sources[0, 0], region, .2)
            if c == 'floor':
                entry['floor'][label] = score
            else:
                key = f'{label}|{c}|{th}'
                entry['fidelity'][key] = score
                entry['fidelity_vs_alt'][key] = k.region_fidelity(v, sources[1, 0], region, .2)
    raw = dict(theta=theta, sources=sources, finals=np.stack(finals))
    meta = dict(index=index, config=asdict(cfg), result=entry, tissue=asdict(ctx['tissue']),
        ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']))
    meta['replay'] = checker().check_source(raw, meta)
    return raw, meta


def contract():
    return dict(schema='l16_body_content_qualification_v1', decision='D111', law='L16',
        run_id=RUN_ID, control_id=CONTROL_ID, config=asdict(CONFIG), seed_tag=TAG,
        tissues=list(TISSUES), disposable=DISPOSABLE, cases=[list(c) for c in CASES],
        fields=list(FIELDS), metrics=list(METRICS), injury='fixed centred rows/columns4:12,64cells',
        matched='exact surviving V multiset within role; alternative spatial ranks, no donor R/EMA',
        primary='off-reader alternative-minus-shuffled donor preference at240; equal direction/life/tissue means',
        gates='nonempty target disagreement in every life; each direction full-body flip lower95>0',
        positive='primary lower95>0 and each direction point estimate>0; otherwise unresolved',
        independent_unit='eight tissue blocks, two lives; directions averaged within life',
        bootstrap_resamples=10000, qualification_only=True, main_confirmation=False,
        branch_paths=384, independent_life_replays=16, exact_sham_aliases=64,
        source_jobs=6, source_branches=120, source_futures_per_branch=8,
        state_atol=1e-10, metric_atol=1e-12, exact_signs=True,
        reader='native rho=.002, c_m=.2/on or0/off; R keeps updating in both',
        scope='one-life repair; not heredity, exclusive information attribution or biology')
