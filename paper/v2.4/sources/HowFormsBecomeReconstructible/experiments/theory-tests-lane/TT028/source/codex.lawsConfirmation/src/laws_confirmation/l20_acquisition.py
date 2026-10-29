"""D116: instructed acquisition, then a theta-only fresh-recipient interface."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util

import numpy as np

from . import l16_theta_content as capacity
from .io import canonical_digest

WS, ORIGIN = capacity.WS, capacity.ORIGIN
RUN_ID = 'l20_acquisition_only_v1_attempt1'
CONTROL_ID = 'l20_acquisition_only_v1_source_bridge_attempt1'
TAG = 'l20-acquisition-only-v1'
TISSUES, DISPOSABLE = tuple(range(59000, 59008)), 514216
PACKAGES = capacity.PACKAGES + ('assimilation', 'two_headed_final')
KINDS = ('written', 'shuffled', 'sham', 'held', 'wrong', 'off', 'ideal')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
PARENTS = tuple((r, writing) for r in (0, 1) for writing in (True, False))
METRICS = capacity.METRICS
SCIENCE = ('src/laws_confirmation/l20_acquisition.py',
    'src/laws_confirmation/l20_acquisition_run.py',
    'scripts/audit_l20_acquisition_outputs.py', 'tests/test_l20_acquisition.py',
    'scripts/run_l20_acquisition.sh', 'protocols/L20_ACQUISITION_ONLY_V1.md')


@dataclass(frozen=True)
class Config:
    lives: int = 4
    settle: int = 120
    teaching: int = 1000
    parent_times: tuple = (0, 1, 20, 80, 300, 1000)
    steps: int = 300
    times: tuple = (0, 1, 20, 80, 300)
    norm: float = .3
    lam: float = .001
    hold: float = 1.2
    amp_threshold: float = .2

    def __post_init__(self):
        if any(type(x) is not int or x <= 0 for x in (self.lives, self.settle, self.teaching, self.steps)):
            raise ValueError('positive integer counts required')
        for times, last in ((self.parent_times, self.teaching), (self.times, self.steps)):
            if (not isinstance(times, tuple) or len(times) < 2 or
                any(type(t) is not int for t in times) or times != tuple(sorted(set(times))) or
                times[:2] != (0, 1) or times[-1] != last):
                raise ValueError('ordered birth/step1/endpoint times required')
        if (self.norm, self.lam, self.hold, self.amp_threshold) != (.3, .001, 1.2, .2):
            raise ValueError('fixed strength, rate, teaching and observer required')


CONFIG = Config()
api = capacity.api
context = capacity.context


def rng(index, life, phase):
    seed = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(seed[:16], 'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d116_checker', WS/SCIENCE[2])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def encode(theta):
    if theta.shape != (16, 16) or theta.dtype != np.float64 or not np.isfinite(theta).all():
        raise ValueError('finite float64 sheet required')
    return theta.astype('<f8', copy=False).tobytes(order='C')


def decode(packet):
    if type(packet) is not bytes or len(packet) != 2048:
        raise ValueError('only a 2048-byte theta packet is accepted')
    field = np.frombuffer(packet, dtype='<f8').reshape(16, 16).copy()
    if not np.isfinite(field).all(): raise ValueError('finite theta required')
    return field


def common_parent(index, life, cfg=CONFIG):
    ctx = context(index); a = ctx['api']; t = ctx['tissue']
    native = a['original'].make_thresholds(t)
    theta = a['original'].project_theta(native, cfg.norm)
    random = rng(index, life, 'parent_birth')
    v = a['launch_pattern'](0, t)[None] + t.copy_jitter*random.standard_normal((1, 16, 16))
    state = (v, v.copy(), v.copy())
    birth = np.stack([x[0] for x in state])
    birth_digest = canonical_digest(random.bit_generator.state)
    random = rng(index, life, 'parent_settle')
    for _ in range(cfg.settle):
        state = a['blueprint_step'](*state, theta, t, ctx['ladder'], ctx['bp'], 'T', random)
    return native, theta, birth, np.stack([x[0] for x in state]), dict(
        parent_birth_rng=birth_digest, parent_settle_rng=canonical_digest(random.bit_generator.state))


def acquire(settled, theta0, target, index, life, writing, cfg=CONFIG):
    ctx = context(index); state = tuple(x[None].copy() for x in settled)
    theta = theta0[None].copy(); random = rng(index, life, 'teaching')
    saved = [np.concatenate((settled, theta), axis=0)]
    for t in range(1, cfg.teaching+1):
        state = (np.full_like(state[0], cfg.hold)*target[None], state[1], state[2])
        result = ctx['api']['original'].cascade_step(*state, theta, ctx['tissue'], ctx['ladder'],
            ctx['bp'], random, cfg.lam if writing else 0., cfg.norm)
        state, theta = result[:3], result[3]
        if t in cfg.parent_times:
            saved.append(np.stack([x[0] for x in (*state, theta)]))
    return np.stack(saved), canonical_digest(random.bit_generator.state)


def read_packet(packet, index, life, cfg=CONFIG, enabled=True):
    """The only state supplied by a parent is bytes; targets are not inputs."""
    if type(enabled) is not bool: raise ValueError('declared reader switch required')
    theta = decode(packet); ctx = context(index)
    applied = theta if enabled else np.zeros_like(theta)
    birth_rng = rng(index, life, 'child_birth')
    v = .2*birth_rng.standard_normal((1, 16, 16))
    birth_digest = canonical_digest(birth_rng.bit_generator.state)
    state = (v, v.copy(), v.copy()); saved = [np.stack([x[0] for x in state])]
    random = rng(index, life, 'child_noise')
    for t in range(1, cfg.steps+1):
        state = ctx['api']['blueprint_step'](*state, applied, ctx['tissue'], ctx['ladder'],
            ctx['bp'], 'T', random, c_m=0.)
        if t in cfg.times: saved.append(np.stack([x[0] for x in state]))
    return np.stack(saved), dict(birth_rng=birth_digest,
        noise_rng=canonical_digest(random.bit_generator.state), packet_sha256=hashlib.sha256(packet).hexdigest())


def measure(states, targets, cfg=CONFIG):
    if states.shape != (14, len(cfg.times), 3, 16, 16) or not np.isfinite(states).all():
        raise ValueError('complete finite descendant states required')
    mean = lambda x: x.mean(axis=(-2, -1))
    rows = []
    for (role, _), trace in zip(CASES, states):
        v, ref = trace[:, 0], trace[:, 2]; amp = abs(v) > cfg.amp_threshold
        own, other = (v > 0) == (targets[role] > 0), (v > 0) == (targets[1-role] > 0)
        rough = (abs(v-np.roll(v, 1, -1))+abs(v-np.roll(v, 1, -2)))/2
        rows.append(np.stack((mean(own & amp), mean(other & amp), mean(own), mean(other),
            mean(amp), mean(v), np.sqrt(mean(v*v)), mean(abs(v) == 2.), mean(rough),
            mean(ref), np.sqrt(mean(ref*ref)), mean(abs(v-ref))), axis=-1))
    return np.stack(rows)


def simulate_life(index, life, cfg=CONFIG, order=CASES):
    if type(life) is not int or not 0 <= life < cfg.lives or len(order) != 14 or set(order) != set(CASES):
        raise ValueError('valid life and complete unique conditions required')
    ctx = context(index); targets = capacity.target_fields(ctx)
    native, theta0, birth, settled, seeds = common_parent(index, life, cfg)
    acquisitions = [acquire(settled, theta0, targets[r], index, life, writing, cfg) for r, writing in PARENTS]
    parent_states = np.stack([x[0] for x in acquisitions])
    permutations = np.stack([rng(index, life, f'shuffle:{r}').permutation(256) for r in (0, 1)])
    fields = []
    for role, kind in CASES:
        field = parent_states[PARENTS.index((role, True)), -1, 3].copy()
        perm = permutations[role]
        if kind == 'shuffled': field = field.ravel()[perm].reshape(16, 16)
        elif kind == 'sham': field = field.ravel()[perm][np.argsort(perm)].reshape(16, 16)
        elif kind == 'held': field = parent_states[PARENTS.index((role, False)), -1, 3].copy()
        elif kind == 'wrong': field = parent_states[PARENTS.index((1-role, True)), -1, 3].copy()
        elif kind == 'ideal': field = ctx['api']['original'].project_theta(np.tanh(1.5*targets[role]), cfg.norm)
        fields.append(field)
    theta = np.stack(fields); packets = [encode(field) for field in theta]
    outcomes = {case: read_packet(packets[CASES.index(case)], index, life, cfg,
                                 enabled=case[1] != 'off') for case in order}
    states = np.stack([outcomes[c][0] for c in CASES])
    raw = dict(native_theta=native, theta0=theta0, parent_birth=birth, settled=settled,
        targets=targets, parent_states=parent_states, permutations=permutations, theta=theta,
        packets=np.stack([np.frombuffer(x, dtype=np.uint8) for x in packets]),
        states=states, values=measure(states, targets, cfg))
    meta = dict(index=index, life=life, config=asdict(cfg), cases=[list(c) for c in CASES],
        parents=[list(c) for c in PARENTS], tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']),
        blueprint=asdict(ctx['bp']), **seeds, teaching_rng=[x[1] for x in acquisitions],
        recipients=[outcomes[c][1] for c in CASES], child_gain=0., child_writing=False,
        packet_bytes=2048, transmitted_fields=['theta'], parent_settle_writing=False)
    return raw, meta


def execute_block(index, cfg=CONFIG):
    rows, records = [], []; audit = checker()
    for life in range(cfg.lives):
        raw, meta = simulate_life(index, life, cfg)
        meta['replay'] = audit.check_life(raw, meta, cfg, replay=True)
        rows.append(raw); records.append(meta)
    return {k: np.stack([r[k] for r in rows]) for k in rows[0]}, dict(index=index, config=asdict(cfg), lives=records)


def summarize(blocks, cfg=CONFIG):
    if len(blocks) != 8: raise ValueError('eight equally weighted blocks required')
    values = np.stack([b['values'] for b in blocks])
    if values.shape != (8, cfg.lives, 14, len(cfg.times), 12) or not np.isfinite(values).all():
        raise ValueError('complete finite measurement panel required')
    draws = rng(0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    for observer, offset in (('qualified', 0), ('sign', 2)):
        pref = values[..., offset]-values[..., offset+1]
        for ti, t in enumerate(cfg.times):
            for left, right in (('written', 'held'), ('written', 'shuffled'),
                ('written', 'wrong'), ('written', 'off'), ('ideal', 'off')):
                effects = [pref[:, :, CASES.index((r, left)), ti]-pref[:, :, CASES.index((r, right)), ti] for r in (0, 1)]
                for role, effect in ((0, effects[0]), (1, effects[1]), ('both', sum(effects)/2)):
                    rows.append(dict(name=left+'_minus_'+right, role=role, time=t, observer=observer,
                        **capacity.native.contrast_stats(effect, draws)))
    pick = lambda name, role='both': next(r for r in rows if r['name'] == name and r['role'] == role
        and r['time'] == cfg.steps and r['observer'] == 'qualified')
    primary = pick('written_minus_held'); specificity = pick('written_minus_shuffled')
    directions = [pick('written_minus_held', r) for r in (0, 1)]
    gates = [pick('ideal_minus_off', r) for r in (0, 1)]
    disagreement = [[int(np.count_nonzero(b['targets'][l, 0] != b['targets'][l, 1])) for l in range(cfg.lives)] for b in blocks]
    readable = bool(np.all(np.asarray(disagreement) > 0) and all(x['pointwise_block_bootstrap_95'][0] > 0 for x in gates))
    positive = bool(primary['pointwise_block_bootstrap_95'][0] > 0 and
        specificity['pointwise_block_bootstrap_95'][0] > 0 and all(x['mean'] > 0 for x in directions))
    return dict(schema='l20_acquisition_only_v1', tissues=list(TISSUES),
        label='READOUT_NOT_QUALIFIED' if not readable else 'QUALIFIED_ACQUIRED_CONTENT' if positive else 'ACQUISITION_UNRESOLVED',
        primary=primary, specificity=specificity, directional_primary=directions, readout_gates=gates,
        readout_qualified=readable, target_disagreement_cells=disagreement, contrasts=rows,
        cases=[list(c) for c in CASES], times=list(cfg.times), metrics=list(METRICS),
        cell_means=values.mean(axis=(0, 1)).tolist(), blocks=8, lives_per_block=cfg.lives,
        packet_bytes=2048, boundaries=1, descendant_renewal=False, absolute_fidelity_gate=None,
        secondary_intervals_multiplicity_adjusted=False, independent_confirmation=False,
        independent_unit='random-stream/native-field block; fixed effective physics and targets')


def source_bridge(config=None):
    """Observe original full writer and transplant without writing source files."""
    a = api(); original = a['original']; config = config or a['LandlordConfig']()
    # This dependency is imported lazily by the source lineage.
    import sys
    for package in PACKAGES:
        path = str(ORIGIN/package/'src')
        if path not in sys.path: sys.path.insert(0, path)
    cascade, step = original.cascade_step, original.blueprint_step
    count = 0; prefix = []; endings = []; prefix_end = config.settle_sweeps+config.imprint_sweeps
    times = sorted({0, 1, config.settle_sweeps, config.settle_sweeps+1, prefix_end})
    def observed(*args, **kwargs):
        nonlocal count
        if count == 0: prefix.append(np.stack([x.copy() for x in args[:4]]))
        result = cascade(*args, **kwargs); count += 1
        if count in times: prefix.append(np.stack(result))
        if count == prefix_end: endings.append(canonical_digest(args[7].bit_generator.state))
        return result
    try:
        original.cascade_step = observed
        lineage = original.landlord_lineage(config, 0, 'writable_fast', .3, .2)
    finally:
        original.cascade_step = cascade
    probe_count = 0; traces = []; probe_rng = []
    def observed_probe(*args, **kwargs):
        nonlocal probe_count
        local = probe_count % config.consensus_settle
        if local == 0: traces.append([np.stack([x.copy() for x in args[:3]])])
        result = step(*args, **kwargs); probe_count += 1
        if local+1 in (1, config.consensus_settle): traces[-1].append(np.stack(result))
        if local+1 == config.consensus_settle: probe_rng.append(canonical_digest(args[8].bit_generator.state))
        return result
    try:
        original.blueprint_step = observed_probe
        probe = original.transplant_probe(config, lineage, .3)
    finally:
        original.blueprint_step = step
    ctx = context(0)
    raw = dict(prefix=np.stack(prefix), theta_final=lineage['theta_final'], targets=lineage['targets'],
               transplant_states=np.stack([np.stack(x) for x in traces]))
    meta = dict(index=0, config=asdict(config), prefix_times=times, prefix_rng=endings,
        transplant_rng=probe_rng, result=probe, fidelity=lineage['fidelity'], freedom=lineage['freedom'],
        tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']),
        full_source_executed=True, original_lineage_updates=count,
        new_verification_not_historical_raw=True, whole_primary_reconstructed=False)
    meta['replay'] = checker().check_source(raw, meta)
    return raw, meta


def contract():
    return dict(schema='l20_acquisition_only_v1', decision='D116', law='L20', run_id=RUN_ID,
        control_id=CONTROL_ID, tag=TAG, config=asdict(CONFIG), tissues=list(TISSUES), disposable=DISPOSABLE,
        cases=[list(c) for c in CASES], parents=[list(c) for c in PARENTS], metrics=list(METRICS),
        parent_paths=128, main_paths=448, full_life_replays=32, exact_aliases=192,
        primary='qualified own-minus-other preference: written-minus-held at300',
        specificity='written-minus-shuffled lower95>0, conjunctive',
        readout='both role ideal-minus-off lower95>0 and target disagreement',
        positive='readout, primary lower95>0, both direction means>0, specificity lower95>0',
        transmitted_fields=['theta'], packet_bytes=2048, packet_dtype='<f8', coordinate_address='fixed 16x16 row-major',
        parent_teaching='1000 V overwrites at +/-1.2; source lambda .001',
        parent_settle='120 common writing-off steps; equally projected theta from birth',
        child='fresh V=EMA=R; paired new noise; reference gain0; no theta writing',
        independent_unit='eight random-stream/native-field blocks, not distinct physics families',
        uncertainty='10000 whole-block percentile pointwise95', state_atol=1e-10, metric_atol=1e-12,
        full_source_lineage_independently_replayed=False, source_prefix_and_transplant_replayed=True,
        whole_historical_primary_reconstructed=False, boundaries=1, renewal=False,
        automatic_retry=False, automatic_follow_on=False)
