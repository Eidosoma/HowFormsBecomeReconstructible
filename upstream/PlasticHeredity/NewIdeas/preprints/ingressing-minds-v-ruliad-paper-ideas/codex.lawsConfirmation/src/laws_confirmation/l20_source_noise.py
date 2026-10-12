"""D123: source noise on/off by body/history record, matched fresh readers.

Known D117 starting states and incoming theta; new source-read and recipient futures.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import importlib.util

import numpy as np

from . import l20_three_rewrite as parent
from .io import DEFAULT_EXTERNAL_ROOT, canonical_digest, sha256_file

WS, ORIGIN, PACKAGES = parent.WS, parent.ORIGIN, parent.PACKAGES
RUN_ID = 'l20_source_noise_v1_attempt1'
CONTROL_ID = 'l20_source_noise_v1_source_bridge_attempt1'
TAG = 'l20-source-noise-v1'
TISSUES, DISPOSABLE = tuple(range(65000, 65008)), 514223
MODES = ('noisy', 'quiet')
SIGMAS = (.3, 0.)
SOURCE_STEPS, SOURCE_TIMES, SOURCE_RHO = 300, (0, 1, 100, 300), .002
BIRTH_COEFFICIENT = .998**300
BASES = ('noisy_body', 'noisy_history', 'quiet_body', 'quiet_history')
KINDS = BASES + tuple(k+'_shuffle' for k in BASES) + (
    'noisy_sham', 'quiet_sham', 'noisy_off', 'quiet_off', 'ideal', 'zero')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
METRICS = parent.METRICS
PAIRS = (('noisy_history', 'noisy_body'), ('quiet_history', 'quiet_body'),
    ('noisy_history', 'quiet_history'), ('noisy_body', 'quiet_body'), ('ideal', 'zero')) + tuple(
        pair for k in BASES for pair in ((k, k+'_shuffle'), (k, 'zero')))
SPECIAL = {
    'noisy_specificity_gain': {'noisy_history': 1, 'noisy_history_shuffle': -1,
        'noisy_body': -1, 'noisy_body_shuffle': 1},
    'quiet_specificity_gain': {'quiet_history': 1, 'quiet_history_shuffle': -1,
        'quiet_body': -1, 'quiet_body_shuffle': 1},
    'noise_interaction': {'noisy_history': 1, 'noisy_body': -1,
        'quiet_history': -1, 'quiet_body': 1},
    'specificity_interaction': {'noisy_history': 1, 'noisy_history_shuffle': -1,
        'noisy_body': -1, 'noisy_body_shuffle': 1, 'quiet_history': -1,
        'quiet_history_shuffle': 1, 'quiet_body': 1, 'quiet_body_shuffle': -1}}
SCIENCE = ('src/laws_confirmation/l20_source_noise.py',
    'src/laws_confirmation/l20_source_noise_run.py',
    'scripts/audit_l20_source_noise_outputs.py', 'tests/test_l20_source_noise.py',
    'scripts/run_l20_source_noise.sh', 'protocols/L20_SOURCE_NOISE_V1.md')
api, context, encode, decode = parent.api, parent.context, parent.encode, parent.decode


@dataclass(frozen=True)
class Config:
    lives: int = 4
    steps: int = 300
    norm: float = .3
    amp_threshold: float = .2

    def __post_init__(self):
        if type(self.lives) is not int or not 1 <= self.lives <= 4:
            raise ValueError('one to four retained lives required')
        if type(self.steps) is not int or self.steps <= 1:
            raise ValueError('at least two reader steps required')
        if (self.norm, self.amp_threshold) != (.3, .2):
            raise ValueError('fixed strength and observer required')

    @property
    def times(self): return tuple(sorted({0, 1, min(100, self.steps), self.steps}))


CONFIG = Config()


def source_index(index):
    if type(index) is not int or index not in (*TISSUES, DISPOSABLE):
        raise ValueError('declared reader block required')
    return 514217 if index == DISPOSABLE else 60000+index-65000


def source_paths(index, root=DEFAULT_EXTERNAL_ROOT):
    si = source_index(index)
    directory = root/('tmp' if index == DISPOSABLE else 'outputs')/(
        parent.RUN_ID+'_benchmark' if index == DISPOSABLE else parent.RUN_ID)
    return directory/f'block_{si}.npz', directory/f'block_{si}.json'


def load_source(index, root=DEFAULT_EXTERNAL_ROOT):
    from .l15_repair_speed_run import load_npz, read_json
    paths = source_paths(index, root)
    raw, meta = load_npz(paths[0]), read_json(paths[1])
    assert meta['index'] == source_index(index) and meta['config'] == asdict(parent.CONFIG)
    assert raw['generation_states'].shape == (4, 16, 3, 8, 4, 16, 16)
    return raw, meta


def rng(index, life, phase):
    key = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(key[:16], 'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d123_checker', WS/SCIENCE[2])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def read_packet(packet, index, life, generation, cfg=CONFIG, enabled=True):
    """Bytes plus public host/life/generation only; no source body/label/RNG."""
    source_index(index)
    if type(life) is not int or not 0 <= life < cfg.lives or type(generation) is not int or generation not in (1, 2, 3):
        raise ValueError('declared life and source-generation stratum required')
    if type(enabled) is not bool: raise ValueError('boolean reading switch required')
    field = decode(packet); applied = field if enabled else np.zeros_like(field)
    ctx = context(index); random = rng(index, life, f'g{generation}:birth')
    v = .2*random.standard_normal((1, 16, 16))
    birth_rng = canonical_digest(random.bit_generator.state)
    state = (v, v.copy(), v.copy()); saved = [np.stack(state)[:, 0]]
    random = rng(index, life, f'g{generation}:read')
    for t in range(1, cfg.steps+1):
        state = ctx['api']['blueprint_step'](*state, applied, ctx['tissue'], ctx['ladder'],
            ctx['bp'], 'T', random, c_m=0.)
        if t in cfg.times: saved.append(np.stack(state)[:, 0])
    return np.stack(saved), dict(birth_rng=birth_rng, read_rng=canonical_digest(random.bit_generator.state),
        input_sha256=hashlib.sha256(packet).hexdigest(), packet_bytes=2048, enabled=enabled,
        writing=False, gain=0., target_labels=False)


def validate_snapshot(snapshot):
    if not isinstance(snapshot, np.ndarray) or snapshot.shape != (16, 16) or snapshot.dtype != np.float64 or not np.isfinite(snapshot).all():
        raise ValueError('finite float64 16x16 snapshot required')


def write_record(snapshot):
    """One input; no target, incoming theta, source state or noise selector."""
    validate_snapshot(snapshot)
    return api()['original'].project_theta(snapshot, .3)


def source_path_read(start, packet, ctx, random):
    """Fixed 300-step gain-off read, no source writing or new birth draw."""
    if not isinstance(start, np.ndarray) or start.shape != (3, 16, 16) or start.dtype != np.float64 or not np.isfinite(start).all():
        raise ValueError('finite V/EMA/R birth state required')
    theta = decode(packet)
    state = tuple(x[None].copy() for x in start); saved = [start.copy()]
    for t in range(1, SOURCE_STEPS+1):
        state = ctx['api']['blueprint_step'](*state, theta, ctx['tissue'], ctx['ladder'],
            ctx['bp'], 'T', random, c_m=0.)
        if t in SOURCE_TIMES: saved.append(np.stack(state)[:, 0])
    return np.stack(saved), dict(noise_rng=canonical_digest(random.bit_generator.state),
        input_sha256=hashlib.sha256(packet).hexdigest(), packet_bytes=2048,
        sigma=ctx['tissue'].sigma, writing=False, gain=0., target_labels=False)


def source_read(start, packet, index, life, generation, mode):
    """Same saved birth/incoming packet; only ongoing source sigma changes."""
    si = source_index(index)
    if type(life) is not int or not 0 <= life < 4 or type(generation) is not int or generation not in (1, 2, 3) or mode not in MODES:
        raise ValueError('declared source life/generation/noise condition required')
    ctx = context(si)
    assert ctx['tissue'].sigma == .3 and ctx['bp'].rho == .002
    ctx['tissue'] = replace(ctx['tissue'], sigma=SIGMAS[MODES.index(mode)])
    return source_path_read(start, packet, ctx, rng(index, life, f'g{generation}:source'))


def simulate_life(index, life, source, cfg=CONFIG, order=CASES):
    if type(life) is not int or not 0 <= life < cfg.lives or len(order) != len(CASES) or set(order) != set(CASES):
        raise ValueError('declared life and complete unique condition order required')
    targets = source['targets'][life].copy()
    starts = np.stack([[source['generation_states'][life, 8*r, g, 0, :3].copy()
                        for g in range(3)] for r in (0, 1)])
    incoming = np.stack([[source['incoming'][life, 8*r, g].copy()
                          for g in range(3)] for r in (0, 1)])
    source_runs = [[[source_read(starts[r, g], incoming[r, g].tobytes(), index, life, g+1, mode)
                     for mode in MODES] for g in range(3)] for r in (0, 1)]
    source_states = np.stack([[np.stack([x[0] for x in source_runs[r][g]]) for g in range(3)] for r in (0, 1)])
    histories = source_states[:, :, :, -1, 2] - BIRTH_COEFFICIENT*starts[:, :, None, 2]
    candidates = np.stack((source_states[:, :, :, -1, 0], histories), axis=3)
    if np.any(candidates.std(axis=(-2, -1)) <= 1e-9):
        raise ValueError('degenerate source: fail rather than exclude')
    fields = np.stack([[np.stack([np.stack([write_record(x) for x in candidates[r, g, m]])
                                  for m in range(2)]) for g in range(3)] for r in (0, 1)])
    permutations = np.stack([[rng(index, life, f'g{g}:shuffle:{r}').permutation(256)
                              for g in (1, 2, 3)] for r in (0, 1)])
    packets = {}
    for r, kind in CASES:
        values = []
        for gi in range(3):
            perm = permutations[r, gi]
            if kind == 'ideal': field = api()['original'].project_theta(np.tanh(1.5*targets[r]), cfg.norm)
            elif kind == 'zero': field = np.zeros((16, 16))
            else:
                mode, handling = kind.split('_', 1)
                body, history = fields[r, gi, MODES.index(mode)]
                if handling == 'body': field = body
                elif handling in ('history', 'sham', 'off'): field = history
                elif handling == 'body_shuffle': field = body.ravel()[perm].reshape(16, 16)
                elif handling == 'history_shuffle': field = history.ravel()[perm].reshape(16, 16)
                else: raise AssertionError('undeclared condition')
                if handling == 'sham': field = history.ravel()[perm][np.argsort(perm)].reshape(16, 16)
            values.append(encode(field))
        packets[(r, kind)] = values
    paths = {c: [read_packet(packets[c][gi], index, life, gi+1, cfg, not c[1].endswith('_off'))
                 for gi in range(3)] for c in order}
    states = np.stack([np.stack([x[0] for x in paths[c]]) for c in CASES])
    raw = dict(targets=targets, source_births=starts, source_packets=incoming,
        source_states=source_states, history_fields=histories, written_fields=fields, permutations=permutations,
        packets=np.stack([np.stack([np.frombuffer(b, np.uint8) for b in packets[c]]) for c in CASES]),
        states=states, values=parent.observations(states, targets, CASES, cfg))
    ctx, sctx = context(index), context(source_index(index))
    meta = dict(index=index, source_index=source_index(index), life=life, config=asdict(cfg),
        cases=[list(c) for c in CASES], times=list(cfg.times), reader_tag=TAG, source_tag=TAG,
        origin_tag=parent.TAG, source_birth_checkpoint=0, source_steps=SOURCE_STEPS, source_times=list(SOURCE_TIMES),
        source_start_reused=True, source_noise_reused=False, source_trajectories_new=True,
        modes=list(MODES), sigmas=list(SIGMAS), birth_coefficient=BIRTH_COEFFICIENT,
        writer_inputs=['V300', 'R300-.998**300*R0'], writer_rule='project(snapshot, .3)',
        source_rho=SOURCE_RHO, incoming_theta_used_for_source=True, incoming_theta_used_by_writer=False,
        birth_direct_term_only=True, source_birth_shared_between_roles=True,
        source_context=dict(index=source_index(index), tissue=asdict(sctx['tissue']),
            ladder=asdict(sctx['ladder']), blueprint=asdict(sctx['bp'])),
        source_paths=[[[x[1] for x in source_runs[r][g]] for g in range(3)] for r in (0, 1)],
        tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']),
        readers=[[x[1] for x in paths[c]] for c in CASES])
    return raw, meta


def execute_block(index, cfg=CONFIG, root=DEFAULT_EXTERNAL_ROOT):
    source, _ = load_source(index, root); rows, records = [], []; audit = checker()
    for life in range(cfg.lives):
        raw, meta = simulate_life(index, life, source, cfg)
        meta['replay'] = audit.check_life(raw, meta, cfg, source, replay=True)
        rows.append(raw); records.append(meta)
    return {k: np.stack([r[k] for r in rows]) for k in rows[0]}, dict(index=index, config=asdict(cfg),
        source_sha256={str(x): sha256_file(x) for x in source_paths(index, root)}, lives=records)


def source_bridge(root=DEFAULT_EXTERNAL_ROOT):
    """Six known terminal readers plus six known source-read paths, no writers."""
    source, _ = load_source(DISPOSABLE, root); si = source_index(DISPOSABLE)
    cases = tuple((r, k) for r in (0, 1) for k in ('rewrite', 'ideal', 'zero'))
    indices = [parent.PROBES.index(c) for c in cases]
    packets = source['probe_packets'][0, indices].copy()
    paths = [parent.probe(packet.tobytes(), si, 0) for packet in packets]
    raw = dict(packets=packets, states=np.stack([x[0] for x in paths]), targets=source['targets'][0].copy())
    np.testing.assert_array_equal(raw['states'], source['probe_states'][0, indices])
    ctx = context(si)
    meta = dict(index=si, life=0, cases=[list(c) for c in cases], times=list(parent.CONFIG.probe_times),
        tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']),
        readers=[x[1] for x in paths], known_outcomes=True, new_source_writes=0)
    starts = np.stack([[source['generation_states'][0, 8*r, g, 0, :3] for g in range(3)] for r in (0, 1)])
    incoming = np.stack([[source['incoming'][0, 8*r, g] for g in range(3)] for r in (0, 1)])
    paths = [[source_path_read(starts[r, g], incoming[r, g].tobytes(), ctx,
        parent.rng(si, 0, f'g{g+1}:read')) for g in range(3)] for r in (0, 1)]
    raw.update(source_births=starts, source_packets=incoming,
        source_states=np.stack([[x[0] for x in row] for row in paths]))
    expected = np.stack([[source['generation_states'][0, 8*r, g, [0, 1, 2, 4], :3]
                          for g in range(3)] for r in (0, 1)])
    np.testing.assert_array_equal(raw['source_states'], expected)
    meta['source_paths'] = [[x[1] for x in row] for row in paths]
    meta['replay'] = checker().check_source(raw, meta, source)
    return raw, meta


def summarize(blocks, cfg=CONFIG):
    if len(blocks) != 8: raise ValueError('eight paired source/reader blocks required')
    v = np.stack([b['values'] for b in blocks])
    if v.shape != (8, cfg.lives, 28, 3, len(cfg.times), 12) or not np.isfinite(v).all():
        raise ValueError('complete finite reading panel required')
    draws = rng(0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    contrasts = {a+'_minus_'+b: {a: 1, b: -1} for a, b in PAIRS} | SPECIAL
    for observer, col in (('qualified', 0), ('sign', 2)):
        pref = v[..., -1, col]-v[..., -1, col+1]
        for stage in ('all', 1, 2, 3):
            obs = pref if stage == 'all' else pref[..., stage-1]
            for name, weights in contrasts.items():
                effects = []
                for role in (0, 1):
                    effect = sum(w*obs[:, :, CASES.index((role, k))] for k, w in weights.items())
                    effects.append(effect.mean(axis=-1) if stage == 'all' else effect)
                for role, effect in ((0, effects[0]), (1, effects[1]), ('both', sum(effects)/2)):
                    rows.append(dict(name=name, stage=stage, role=role, observer=observer,
                        **parent.parent.capacity.native.contrast_stats(effect, draws)))
    pick = lambda name, role='both': next(x for x in rows if (x['name'], x['stage'], x['role'], x['observer']) == (name, 'all', role, 'qualified'))
    positive = lambda x: x['pointwise_block_bootstrap_95'][0] > 0
    gates = [pick('ideal_minus_zero', r) for r in (0, 1)]
    disagreement = [[int(np.count_nonzero(b['targets'][l, 0] != b['targets'][l, 1])) for l in range(cfg.lives)] for b in blocks]
    readable = bool(all(positive(x) for x in gates) and np.all(np.asarray(disagreement) > 0))
    content = {kind: bool(readable and positive(pick(kind+'_minus_'+kind+'_shuffle')) and
        all(positive(pick(kind+'_minus_zero', r)) and pick(kind+'_minus_'+kind+'_shuffle', r)['mean'] > 0 for r in (0, 1)))
        for kind in BASES}
    primary = pick('noise_interaction')
    directions = [pick('noise_interaction', r) for r in (0, 1)]
    ready = all(content.values())
    label = 'READOUT_NOT_QUALIFIED' if not readable else 'INTERACTION_CONTENT_NOT_QUALIFIED' if not ready else 'SOURCE_NOISE_INTERACTION_UNRESOLVED'
    if ready:
        if positive(primary) and all(x['mean'] > 0 for x in directions): label = 'SOURCE_NOISE_INCREASES_HISTORY_GAP'
        elif primary['pointwise_block_bootstrap_95'][1] < 0 and all(x['mean'] < 0 for x in directions): label = 'SOURCE_NOISE_DECREASES_HISTORY_GAP'
    gaps, gap_directions, gap_labels = {}, {}, {}
    for mode in MODES:
        gap = pick(mode+'_history_minus_'+mode+'_body')
        ds = [pick(mode+'_history_minus_'+mode+'_body', r) for r in (0, 1)]
        glabel = 'HISTORY_EFFECT_UNRESOLVED' if content[mode+'_history'] and content[mode+'_body'] else 'CONTENT_NOT_QUALIFIED'
        if glabel != 'CONTENT_NOT_QUALIFIED':
            if positive(gap) and all(x['mean'] > 0 for x in ds): glabel = 'HISTORY_ADVANTAGE_QUALIFIED'
            elif gap['pointwise_block_bootstrap_95'][1] < 0 and all(x['mean'] < 0 for x in ds): glabel = 'BODY_ADVANTAGE_QUALIFIED'
        gaps[mode], gap_directions[mode], gap_labels[mode] = gap, ds, glabel
    return dict(schema='l20_source_noise_v1', label=label, primary=primary, directional_primary=directions,
        content_readable=content, readout_qualified=readable, readout_gates=gates,
        history_gaps=gaps, directional_history_gaps=gap_directions, history_gap_labels=gap_labels,
        history_gaps_are_secondary=True, contrasts=rows, target_disagreement_cells=disagreement,
        cases=[list(c) for c in CASES], times=list(cfg.times), metrics=list(METRICS),
        cell_means=v.mean(axis=(0, 1)).tolist(), reader_blocks=list(TISSUES), source_blocks=list(parent.TISSUES),
        blocks=8, lives_per_block=cfg.lives, source_generation_strata=3, reader_paths=8*cfg.lives*84,
        packet_bytes=2048, source_starts_reused=True, new_source_paths=8*cfg.lives*12,
        source_noise_reused=False, new_renewal_cohort=False,
        source_steps=SOURCE_STEPS, source_times=list(SOURCE_TIMES), source_rho=SOURCE_RHO,
        birth_coefficient=BIRTH_COEFFICIENT, modes=list(MODES), sigmas=list(SIGMAS), reader_sigma=.3,
        writer_inputs=['V300', 'R300-.998**300*R0'], writer_rule='project(snapshot, .3)', birth_direct_term_only=True,
        absolute_fidelity_gate=None, equivalence_test=False, secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l20_source_noise_v1', decision='D123', law='L20', run_id=RUN_ID,
        control_id=CONTROL_ID, tag=TAG, config=asdict(CONFIG), tissues=list(TISSUES), disposable=DISPOSABLE,
        source_run=parent.RUN_ID, source_blocks=list(parent.TISSUES), source_disposable=514217,
        source_birth_checkpoint=0, source_start_reused=True, source_noise_reused=False,
        source_steps=SOURCE_STEPS, source_times=list(SOURCE_TIMES), source_rho=SOURCE_RHO,
        new_source_writes=0, new_source_paths=384, constructed_primary_packets=768,
        modes=list(MODES), sigmas=list(SIGMAS), reader_sigma=.3, source_context='original D117 block',
        source_pairing='identical saved V/EMA/R and incoming theta, new common source RNG per life/generation',
        birth_coefficient=BIRTH_COEFFICIENT, decomposition='H=R300-.998**300*R0',
        birth_direct_term_only=True, writer_inputs=['V300', 'R300-.998**300*R0'],
        incoming_theta_used_for_source=True, incoming_theta_used_by_writer=False,
        writer_rule='project(snapshot, .3)', normalization_retained=True,
        source_writing=False, source_reference_gain=0., source_target_labels=False,
        cases=[list(c) for c in CASES], metrics=list(METRICS), times=list(CONFIG.times),
        source_starts=192, source_generation_strata=3, reader_paths=2688, exact_path_aliases=864, packet_bytes=2048,
        primary='(noisy H-body)-(quiet H-body), terminal qualified preference, averaged source strata',
        positive='all four content routes qualified, interaction lower95>0 and both direction means>0',
        negative='all four content routes qualified, interaction upper95<0 and both direction means<0',
        content='each route: pooled intact-minus-shuffle lower95>0 and both directional means>0; both intact-minus-zero lower95>0',
        instrument='both ideal-minus-zero directional lower95>0; different target fields',
        secondary='each H-body gap, source-noise effects on H/body, specificity interaction, sign observer and strata',
        secondary_intervals_multiplicity_adjusted=False,
        uncertainty='10000 whole-block percentile draws; average 3 source strata within 4 paired lives within 8 blocks',
        descriptive_tie_atol=1e-12, no_equivalence=True, shared_shuffle=True,
        noisy_means_ongoing_source_noise_only=True, cleaner_cascade_identified=False, new_renewal_cohort=False,
        reader_writing=False, reader_gain=0., state_atol=1e-10, metric_atol=1e-12,
        automatic_retry=False, automatic_follow_on=False)

