"""D114: fixed-strength, supplied theta content; no writer or heredity claim."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import sys

import numpy as np

from . import l15_repair_speed as native
from .io import canonical_digest

WS, ORIGIN = native.WS, native.ORIGIN
RUN_ID = 'l16_theta_content_qualification_v1_attempt1'
CONTROL_ID = 'l16_theta_content_v1_source_bridge_attempt1'
TAG = 'l16-theta-content-v1'
TISSUES = tuple(range(58000, 58008))
DISPOSABLE = 514214
PACKAGES = native.PACKAGES + ('writable_landlord',)
KINDS = ('aligned', 'shuffled', 'sham', 'off', 'body_own', 'body_alternative')
CASES = tuple((role, kind) for role in (0, 1) for kind in KINDS)
METRICS = ('own_qualified', 'alternative_qualified', 'own_sign', 'alternative_sign',
           'amp_fraction', 'body_mean', 'body_rms', 'clip_fraction', 'roughness',
           'reference_mean', 'reference_rms', 'vr_mae')
SCIENCE = ('src/laws_confirmation/l16_theta_content.py',
    'src/laws_confirmation/l16_theta_content_run.py',
    'scripts/audit_l16_theta_content_outputs.py', 'tests/test_l16_theta_content.py',
    'scripts/run_l16_theta_content.sh', 'protocols/L16_THETA_CONTENT_V1.md')


@dataclass(frozen=True)
class Config:
    lives: int = 4
    steps: int = 300
    times: tuple = (0, 1, 20, 80, 300)
    norm: float = .3
    amp_threshold: float = .2

    def __post_init__(self):
        if any(type(x) is not int or x <= 0 for x in (self.lives, self.steps)):
            raise ValueError('positive integer lives/steps required')
        if (not isinstance(self.times, tuple) or len(self.times) < 2
                or any(type(t) is not int for t in self.times)
                or self.times != tuple(sorted(set(self.times)))
                or self.times[:2] != (0, 1) or self.times[-1] != self.steps):
            raise ValueError('birth, step1 and endpoint checkpoints required')
        if self.norm != .3 or self.amp_threshold != .2:
            raise ValueError('single fixed norm and observer required')


CONFIG = Config()


def api():
    a = native.api()
    path = str(ORIGIN/'writable_landlord/src')
    if path not in sys.path:
        sys.path.insert(0, path)
    from writable_landlord import pipeline as original
    from writable_landlord.config import LandlordConfig
    from voltage_web.engine import launch_pattern
    from contract_bridge.artifacts import seed_rng
    return a | dict(original=original, LandlordConfig=LandlordConfig,
                    launch_pattern=launch_pattern, seed_rng=seed_rng)


def context(index):
    c = native.context(index)
    c['api'] = api()
    return c


def rng(index, life, phase):
    payload = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(payload[:16], 'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d114_checker', WS/SCIENCE[2])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def target_fields(ctx):
    return np.stack([ctx['api']['launch_pattern'](i, ctx['tissue']) for i in (1, 3)])


def theta_fields(targets, permutations, cfg=CONFIG):
    if (targets.shape != (2, 16, 16) or targets.dtype != np.float64
            or not np.all(np.isin(targets, [-1., 1.]))
            or permutations.shape != (2, 256) or permutations.dtype != np.int64
            or not all(np.array_equal(np.sort(x), np.arange(256)) for x in permutations)):
        raise ValueError('declared binary targets and permutation bijections required')
    aligned = api()['original'].project_theta(np.tanh(1.5*targets), cfg.norm)
    if not np.array_equal(np.sort(aligned[0].ravel()), np.sort(aligned[1].ravel())):
        raise ValueError('target field value multisets must match exactly')
    fields = []
    for role, kind in CASES:
        flat, perm = aligned[role].ravel(), permutations[role]
        if kind == 'shuffled': field = flat[perm].reshape(16, 16)
        elif kind == 'sham': field = flat[perm][np.argsort(perm)].reshape(16, 16)
        elif kind == 'aligned': field = aligned[role].copy()
        else: field = np.zeros((16, 16), dtype=np.float64)
        fields.append(field)
    return np.stack(fields)


def initial(common, targets, role, kind):
    if (common.shape != (16, 16) or common.dtype != np.float64
            or not np.isfinite(common).all() or role not in (0, 1) or kind not in KINDS):
        raise ValueError('finite common birth and declared condition required')
    v = targets[role] if kind == 'body_own' else targets[1-role] if kind == 'body_alternative' else common
    return np.stack((v.copy(), v.copy(), common.copy()))


def evolve(start, theta, ctx, random, cfg=CONFIG):
    state = tuple(x[None].copy() for x in start)
    saved = [start.copy()]
    for t in range(1, cfg.steps+1):
        state = ctx['api']['blueprint_step'](*state, theta, ctx['tissue'], ctx['ladder'],
                                            ctx['bp'], 'T', random, c_m=0.)
        if t in cfg.times:
            saved.append(np.stack([x[0] for x in state]))
    return np.stack(saved), canonical_digest(random.bit_generator.state)


def measurements(states, targets, cfg=CONFIG):
    if (states.shape != (12, len(cfg.times), 3, 16, 16) or targets.shape != (2, 16, 16)
            or not np.isfinite(states).all() or not np.isfinite(targets).all()):
        raise ValueError('complete finite states and targets required')
    rows = []
    mean = lambda x: x.mean(axis=(-2, -1))
    for (role, _), trace in zip(CASES, states):
        v, ref = trace[:, 0], trace[:, 2]
        amp = abs(v) > cfg.amp_threshold
        own, other = (v > 0) == (targets[role] > 0), (v > 0) == (targets[1-role] > 0)
        rough = (abs(v-np.roll(v, 1, -1))+abs(v-np.roll(v, 1, -2)))/2
        rows.append(np.stack((mean(own & amp), mean(other & amp), mean(own), mean(other),
            mean(amp), mean(v), np.sqrt(mean(v*v)), mean(abs(v) == 2.), mean(rough),
            mean(ref), np.sqrt(mean(ref*ref)), mean(abs(v-ref))), axis=-1))
    return np.stack(rows)


def simulate_life(index, life, cfg=CONFIG, order=CASES):
    if (type(life) is not int or not 0 <= life < cfg.lives
            or len(order) != len(CASES) or set(order) != set(CASES)):
        raise ValueError('complete unique conditions and valid life required')
    ctx = context(index); targets = target_fields(ctx)
    random = rng(index, life, 'birth')
    common = .2*random.standard_normal((16, 16))
    birth_digest = canonical_digest(random.bit_generator.state)
    permutations = np.stack([rng(index, life, f'shuffle:{r}').permutation(256) for r in (0, 1)])
    theta = theta_fields(targets, permutations, cfg); theta.setflags(write=False)
    runs = {case: evolve(initial(common, targets, *case), theta[CASES.index(case)], ctx,
                         rng(index, life, 'noise'), cfg) for case in order}
    states = np.stack([runs[c][0] for c in CASES])
    raw = dict(targets=targets, common=common, permutations=permutations, theta=theta.copy(),
               states=states, values=measurements(states, targets, cfg))
    meta = dict(index=index, life=life, config=asdict(cfg), cases=[list(c) for c in CASES],
        tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']),
        birth_rng=birth_digest, branch_rng=[runs[c][1] for c in CASES], gain=0.,
        theta_writable=False, target_reference_supplied=False, primary_births_identical=True)
    return raw, meta


def execute_block(index, cfg=CONFIG):
    rows, records = [], []
    audit = checker()
    for life in range(cfg.lives):
        raw, meta = simulate_life(index, life, cfg)
        meta['replay'] = audit.check_life(raw, meta, cfg, replay=True)
        rows.append(raw); records.append(meta)
    return {k: np.stack([r[k] for r in rows]) for k in rows[0]}, dict(
        index=index, config=asdict(cfg), lives=records)


def summarize(blocks, cfg=CONFIG):
    if len(blocks) != 8:
        raise ValueError('eight equal random-stream blocks required')
    values = np.stack([b['values'] for b in blocks])
    if values.shape != (8, cfg.lives, 12, len(cfg.times), 12) or not np.isfinite(values).all():
        raise ValueError('complete finite measurements required')
    samples = rng(0, 0, 'bootstrap').integers(0, 8, (10000, 8))
    contrasts = []
    ix = lambda role, kind: CASES.index((role, kind))
    for observer, offset in (('qualified', 0), ('sign', 2)):
        pref = values[..., offset]-values[..., offset+1]
        for ti, t in enumerate(cfg.times):
            for name, left, right in (
                ('aligned_minus_shuffled', 'aligned', 'shuffled'),
                ('aligned_minus_off', 'aligned', 'off'),
                ('aligned_minus_wrong_field', 'aligned', 'wrong'),
                ('body_own_minus_alternative', 'body_own', 'body_alternative')):
                effects = []
                for role in (0, 1):
                    lhs = pref[:, :, ix(role, left), ti]
                    rhs = (-pref[:, :, ix(1-role, 'aligned'), ti] if right == 'wrong'
                           else pref[:, :, ix(role, right), ti])
                    effects.append(lhs-rhs)
                for role, effect in ((0, effects[0]), (1, effects[1]), ('both', sum(effects)/2)):
                    contrasts.append(dict(name=name, time=t, role=role, observer=observer,
                        **native.contrast_stats(effect, samples)))
    pick = lambda name, role='both': next(c for c in contrasts if c['name'] == name
        and c['role'] == role and c['time'] == cfg.steps and c['observer'] == 'qualified')
    primary = pick('aligned_minus_shuffled')
    directional = [pick('aligned_minus_shuffled', r) for r in (0, 1)]
    gates = [pick('body_own_minus_alternative', r) for r in (0, 1)]
    disagreement = [[int(np.count_nonzero((b['targets'][life, 0] > 0) !=
        (b['targets'][life, 1] > 0))) for life in range(cfg.lives)] for b in blocks]
    readable = bool(np.all(np.asarray(disagreement) > 0) and
                    all(g['pointwise_block_bootstrap_95'][0] > 0 for g in gates))
    positive = bool(primary['pointwise_block_bootstrap_95'][0] > 0 and
                    all(d['mean'] > 0 for d in directional))
    label = ('READOUT_NOT_QUALIFIED' if not readable else 'QUALIFIED_THETA_CONTENT'
             if positive else 'THETA_CONTENT_UNRESOLVED')
    return dict(schema='l16_theta_content_qualification_v1', tissues=list(TISSUES), label=label,
        primary=primary, directional_primary=directional, readout_gates=gates,
        readout_qualified=readable, target_disagreement_cells=disagreement, contrasts=contrasts,
        cases=[list(c) for c in CASES], times=list(cfg.times), metrics=list(METRICS),
        cell_means=values.mean(axis=(0, 1)).tolist(), blocks=8, lives_per_block=cfg.lives,
        absolute_fidelity_gate=None, secondary_intervals_multiplicity_adjusted=False,
        biological_or_learned_or_heredity_claim=False, independent_confirmation=False,
        independent_unit='random-stream block; fixed target pair and effective physics')


def source_bridge():
    """Observe the unaltered historical gate; restore instrumentation in finally."""
    a = api(); original = a['original']; config = a['LandlordConfig']()
    original_step = original.blueprint_step
    starts, fields, traces, endings = [], [], [], []
    count = 0

    def observed(*args, **kwargs):
        nonlocal count
        local = count % config.capacity_settle
        if local == 0:
            starts.append(np.stack([x.copy() for x in args[:3]]))
            fields.append(args[3].copy()); traces.append([starts[-1]])
        result = original_step(*args, **kwargs); count += 1
        if local+1 in CONFIG.times:
            traces[-1].append(np.stack(result))
        if local+1 == config.capacity_settle:
            endings.append(canonical_digest(args[8].bit_generator.state))
        return result

    try:
        original.blueprint_step = observed
        result = original.capacity_gate(config)
    finally:
        original.blueprint_step = original_step
    assert count == 900
    ctx = context(0)
    raw = dict(theta=np.stack(fields), states=np.stack([np.stack(t) for t in traces]),
               target=a['launch_pattern'](1, ctx['tissue']))
    meta = dict(index=0, config=asdict(config), result=result, end_rng=endings,
        tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']),
        known_outcomes=True, new_verification_not_historical_raw=True)
    meta['replay'] = checker().check_source(raw, meta)
    return raw, meta


def contract():
    return dict(schema='l16_theta_content_v1', decision='D114', law='L16', run_id=RUN_ID,
        control_id=CONTROL_ID, tag=TAG, config=asdict(CONFIG), tissues=list(TISSUES),
        disposable=DISPOSABLE, cases=[list(c) for c in CASES], metrics=list(METRICS),
        source_norms_known=[.3, .4, .5], main_norm=.3, targets=[1, 3], gain=0.,
        main_paths=384, full_life_replays=32, exact_aliases=160,
        primary='qualified own-minus-other preference: aligned-minus-shuffled at300',
        unit='eight equal random-stream blocks, four lives averaged; fixed effective physics',
        uncertainty='10000 whole-block bootstrap percentile pointwise95',
        theta='supplied fixed field replacing native theta; exact value-multiset controls',
        readout='both reciprocal final zero-theta body controls lower95>0; no absolute gate',
        positive='qualified readout and primary lower95>0 and both directional means>0',
        state_axes='life,case,time,field,row,column', state_atol=1e-10,
        metric_atol=1e-12, exact_signs=True, source_outcomes_known=True,
        learned_or_renewable_heredity=False, automatic_retry=False, automatic_follow_on=False)
