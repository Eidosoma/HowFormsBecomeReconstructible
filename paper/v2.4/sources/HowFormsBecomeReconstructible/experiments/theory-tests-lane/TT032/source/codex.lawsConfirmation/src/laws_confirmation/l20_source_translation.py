"""D127: aligned versus geometry-preserving translated source feedback, with zero baseline.

Fixed input strength; audit realized same-state, same-noise feedback increments.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util

import numpy as np

from . import l20_three_rewrite as parent
from .io import DEFAULT_EXTERNAL_ROOT, canonical_digest, sha256_file

WS, ORIGIN, PACKAGES = parent.WS, parent.ORIGIN, parent.PACKAGES
RUN_ID = 'l20_source_translation_v1_attempt1'
CONTROL_ID = 'l20_source_translation_v1_source_bridge_attempt1'
TAG = 'l20-source-translation-v1'
TISSUES, DISPOSABLE = tuple(range(69000, 69008)), 514227
MODES = ('aligned', 'translated', 'no_feedback')
FORCE_METRICS = ('applied_mean', 'applied_std', 'input_rms', 'effective_rms',
    'effective_dot_v', 'effective_dot_reference_gap', 'output_clip_fraction', 'reference_gap_rms')
SOURCE_STEPS, SOURCE_TIMES = 1000, (0, 1, 300, 1000)
SOURCE_RHO, SOURCE_LAMBDA, SOURCE_GAIN = .002, .001, .2
KINDS = ('aligned', 'translated', 'no_feedback',
         'aligned_shuffle', 'translated_shuffle', 'no_feedback_shuffle',
         'aligned_sham', 'translated_sham', 'no_feedback_sham',
         'aligned_off', 'translated_off', 'no_feedback_off', 'ideal', 'zero')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
METRICS = parent.METRICS
PAIRS = (('aligned', 'translated'), ('aligned', 'no_feedback'), ('translated', 'no_feedback'),
         ('aligned', 'aligned_shuffle'), ('translated', 'translated_shuffle'), ('no_feedback', 'no_feedback_shuffle'),
         ('ideal', 'zero'), ('aligned', 'zero'), ('translated', 'zero'), ('no_feedback', 'zero'))
SCIENCE = ('src/laws_confirmation/l20_source_translation.py',
    'src/laws_confirmation/l20_source_translation_run.py',
    'scripts/audit_l20_source_translation_outputs.py', 'tests/test_l20_source_translation.py',
    'scripts/run_l20_source_translation.sh', 'protocols/L20_SOURCE_TRANSLATION_V1.md')
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
    return 514217 if index == DISPOSABLE else 60000+index-69000


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
    spec = importlib.util.spec_from_file_location('d127_checker', WS/SCIENCE[2])
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


def write_record(snapshot):
    """Instantaneous constructor; only the final R sheet is an input."""
    if not isinstance(snapshot, np.ndarray) or snapshot.shape != (16, 16) or snapshot.dtype != np.float64 or not np.isfinite(snapshot).all():
        raise ValueError('finite float64 16x16 snapshot required')
    return api()['original'].project_theta(np.tanh(snapshot), .3)



def source_shift(index, life, generation):
    """Uniform coordinate shift, never selected using targets or outcomes."""
    source_index(index)
    if type(life) is not int or not 0 <= life < 4 or type(generation) is not int or generation not in (1,2,3):
        raise ValueError('declared source life/generation required')
    code = int(rng(index, life, f'g{generation}:source_shift').integers(1,256))
    return np.asarray(divmod(code,16), dtype=np.int64)


def source_permutation(index, life, generation):
    shift = source_shift(index,life,generation)
    return np.roll(np.arange(256,dtype=np.int64).reshape(16,16),
        tuple(int(x) for x in shift), axis=(0,1)).reshape(256)


def translation_shift(permutation):
    """Accept only toroidal translations; preserve both oriented neighbors."""
    if (not isinstance(permutation, np.ndarray) or permutation.dtype != np.int64
            or permutation.shape != (256,) or not np.all((permutation>=0)&(permutation<256))):
        raise ValueError('fixed toroidal translation required')
    origin_y, origin_x = divmod(int(permutation[0]),16)
    shift = ((-origin_y)%16,(-origin_x)%16)
    expected = np.roll(np.arange(256,dtype=np.int64).reshape(16,16),shift,axis=(0,1)).reshape(256)
    if not np.array_equal(permutation,expected):
        raise ValueError('cell scrambling or reflection is not a rigid translation')
    return shift


def applied_field(theta, mode, permutation):
    if mode not in MODES or type(mode) is not str:
        raise ValueError('declared source address mode required')
    shift = translation_shift(permutation)
    if mode == 'translated' and shift == (0,0):
        raise ValueError('translated source requires a nonzero coordinate shift')
    if mode == 'aligned': return theta.copy()
    if mode == 'translated': return theta.reshape(-1)[permutation].reshape(theta.shape)
    return np.zeros_like(theta)


def force_measurements(v, ref, applied, actual, without, dt):
    """Diagnostic only: two next-V values share the same old state and noise."""
    force = dt*(applied-applied.mean(axis=(-2,-1), keepdims=True))
    delta, gap = actual-without, ref-v
    return np.asarray([applied.mean(), applied.std(), np.sqrt(np.mean(force*force)),
        np.sqrt(np.mean(delta*delta)), np.mean(delta*v), np.mean(delta*gap),
        np.mean(np.abs(actual) == 2.), np.sqrt(np.mean(gap*gap))], dtype=np.float64)


def source_path_write(start, ctx, random, mode, permutation):
    """Keep writing in all arms; rigidly translate only the applied feedback."""
    if not isinstance(start, np.ndarray) or start.shape != (3, 16, 16) or start.dtype != np.float64 or not np.isfinite(start).all():
        raise ValueError('finite float64 V/EMA/R pre-writing state required')
    applied_field(np.zeros((1,16,16)), mode, permutation)
    assert ctx['tissue'].sigma == .3 and ctx['bp'].rho == .002 and ctx['bp'].c_m == .2
    state = tuple(x[None].copy() for x in start); theta = np.zeros((1,16,16))
    zero = np.zeros_like(theta); saved = [np.stack((*state,theta))[:,0]]; forces = []
    # The auxiliary evaluation never feeds forward or advances the real RNG.
    counter_random = np.random.Generator(np.random.PCG64(0))
    for t in range(1, SOURCE_STEPS+1):
        applied = applied_field(theta, mode, permutation)
        counter_random.bit_generator.state = random.bit_generator.state
        without = ctx['api']['blueprint_step'](*state, zero, ctx['tissue'], ctx['ladder'],
            ctx['bp'], 'T', counter_random, c_m=SOURCE_GAIN)
        advanced = ctx['api']['blueprint_step'](*state, applied, ctx['tissue'], ctx['ladder'],
            ctx['bp'], 'T', random, c_m=SOURCE_GAIN)
        assert counter_random.bit_generator.state == random.bit_generator.state
        forces.append(force_measurements(state[0], state[2], applied, advanced[0], without[0], ctx['tissue'].dt))
        state = advanced
        theta = ctx['api']['original'].project_theta(
            (1.-SOURCE_LAMBDA)*theta+SOURCE_LAMBDA*np.tanh(state[2]), .3)
        if t in SOURCE_TIMES: saved.append(np.stack((*state,theta))[:,0])
    return np.stack(saved), np.stack(forces), dict(noise_rng=canonical_digest(random.bit_generator.state),
        source_mode=mode, theta_to_body=mode != 'no_feedback', writing=True, gain=SOURCE_GAIN,
        rho=SOURCE_RHO, lam=SOURCE_LAMBDA, sigma=.3, theta_start_zero=True, target_labels=False,
        source_permutation_sha256=hashlib.sha256(permutation.astype('<i8').tobytes()).hexdigest(),
        source_shift=list(translation_shift(permutation)), geometry_preserved=True,
        force_counterfactual='same-old-state/same-noise zero-theta next-V; diagnostic only')


def source_write(start, index, life, generation, mode):
    si = source_index(index)
    if type(life) is not int or not 0 <= life < 4 or type(generation) is not int or generation not in (1,2,3) or mode not in MODES:
        raise ValueError('declared source life/generation/address mode required')
    return source_path_write(start, context(si), rng(index, life, f'g{generation}:source'),
        mode, source_permutation(index,life,generation))


def simulate_life(index, life, source, cfg=CONFIG, order=CASES):
    if type(life) is not int or not 0 <= life < cfg.lives or len(order) != len(CASES) or set(order) != set(CASES):
        raise ValueError('declared life and complete unique condition order required')
    targets = source['targets'][life].copy()
    # Known state AFTER read300, but erase theta exactly as D117 rewrite did.
    starts = np.stack([[source['generation_states'][life,8*r,g,4,:3].copy()
                        for g in range(3)] for r in (0,1)])
    source_runs = [[[source_write(starts[r,g], index, life, g+1, mode)
                     for mode in MODES] for g in range(3)] for r in (0,1)]
    source_states = np.stack([[np.stack([x[0] for x in source_runs[r][g]])
                               for g in range(3)] for r in (0,1)])
    source_forces = np.stack([[np.stack([x[1] for x in source_runs[r][g]])
                               for g in range(3)] for r in (0,1)])
    source_permutations = np.stack([source_permutation(index,life,g) for g in (1,2,3)])
    source_shifts = np.stack([source_shift(index,life,g) for g in (1,2,3)])
    refs = source_states[:,:,:,-1,2]
    if np.any(np.tanh(refs).std(axis=(-2,-1)) <= 1e-9):
        raise ValueError('degenerate source: fail rather than exclude')
    fields = np.stack([[np.stack([write_record(x) for x in refs[r,g]])
                        for g in range(3)] for r in (0,1)])
    permutations = np.stack([[rng(index, life, f'g{g}:shuffle:{r}').permutation(256)
                              for g in (1, 2, 3)] for r in (0, 1)])
    packets = {}
    for r, kind in CASES:
        values = []
        for gi in range(3):
            perm = permutations[r,gi]
            base = next((k for k in MODES if kind == k or kind.startswith(k+'_')), None)
            if base is not None: field = fields[r,gi,MODES.index(base)]
            elif kind == 'ideal': field = api()['original'].project_theta(np.tanh(1.5*targets[r]), cfg.norm)
            else: field = np.zeros((16,16))
            if kind.endswith('_shuffle'): field = field.ravel()[perm].reshape(16, 16)
            elif kind.endswith('_sham'): field = field.ravel()[perm][np.argsort(perm)].reshape(16, 16)
            values.append(encode(field))
        packets[(r, kind)] = values
    paths = {c: [read_packet(packets[c][gi], index, life, gi+1, cfg, not c[1].endswith('_off'))
                 for gi in range(3)] for c in order}
    states = np.stack([np.stack([x[0] for x in paths[c]]) for c in CASES])
    raw = dict(targets=targets, source_starts=starts, source_states=source_states,
        written_fields=fields, permutations=permutations, source_permutations=source_permutations,
        source_forces=source_forces, source_shifts=source_shifts,
        packets=np.stack([np.stack([np.frombuffer(b, np.uint8) for b in packets[c]]) for c in CASES]),
        states=states, values=parent.observations(states, targets, CASES, cfg))
    ctx, sctx = context(index), context(source_index(index))
    meta = dict(index=index, source_index=source_index(index), life=life, config=asdict(cfg),
        cases=[list(c) for c in CASES], times=list(cfg.times), reader_tag=TAG, source_tag=TAG,
        origin_tag=parent.TAG, source_start_checkpoint=300, source_start_reused=True,
        source_noise_reused=False, source_trajectories_new=True, source_steps=SOURCE_STEPS,
        source_times=list(SOURCE_TIMES), modes=list(MODES), theta_start_zero=True,
        geometry_preserved=True,
        force_metrics=list(FORCE_METRICS), source_address_rule='one uniform nonzero toroidal shift per life/stratum; fixed and shared across roles',
        source_rho=SOURCE_RHO, source_gain=SOURCE_GAIN, source_lambda=SOURCE_LAMBDA,
        writer_inputs=['R_final'], writer_rule='project(tanh(R_final), .3)',
        latent_theta_transmitted=False, source_target_labels=False,
        source_context=dict(index=source_index(index), tissue=asdict(sctx['tissue']),
            ladder=asdict(sctx['ladder']), blueprint=asdict(sctx['bp'])),
        source_paths=[[[x[2] for x in source_runs[r][g]] for g in range(3)] for r in (0,1)],
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
    """Six known source writers and six terminal readers, no new source futures."""
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
        readers=[x[1] for x in paths], known_outcomes=True, new_source_writer_paths=0)
    starts = np.stack([[source['generation_states'][0,8*r,g,4,:3] for g in range(3)] for r in (0,1)])
    writes = [[source_path_write(starts[r,g], ctx, parent.rng(si,0,f'g{g+1}:write'), 'aligned', np.arange(256,dtype=np.int64))
               for g in range(3)] for r in (0,1)]
    raw.update(source_starts=starts, source_states=np.stack([[x[0] for x in row] for row in writes]))
    expected = np.stack([[source['generation_states'][0,8*r,g,5:8] for g in range(3)] for r in (0,1)])
    np.testing.assert_array_equal(raw['source_states'][:,:,1:], expected)
    raw['source_forces'] = np.stack([[x[1] for x in row] for row in writes])
    meta['force_metrics'] = list(FORCE_METRICS)
    meta['source_paths'] = [[x[2] for x in row] for row in writes]
    meta['replay'] = checker().check_source(raw, meta, source)
    return raw, meta


def force_summary(blocks, cfg=CONFIG):
    values = np.stack([b['source_forces'] for b in blocks])
    if values.shape != (8,cfg.lives,2,3,3,1000,len(FORCE_METRICS)) or not np.isfinite(values).all():
        raise ValueError('complete finite per-step force diagnostics required')
    draws = rng(0,0,'bootstrap').integers(0,8,(10000,8)); rows = []
    # First average time; preserve the same paired life/block uncertainty units.
    gap = (values[:,:,:,:,0]-values[:,:,:,:,1]).mean(axis=-2)
    for metric, name in enumerate(FORCE_METRICS):
        for stage in ('all',1,2,3):
            panel = gap[...,metric].mean(axis=-1) if stage == 'all' else gap[...,stage-1,metric]
            for role, effect in ((0,panel[:,:,0]),(1,panel[:,:,1]),('both',panel.mean(axis=-1))):
                rows.append(dict(metric=name,stage=stage,role=role,
                    **parent.parent.capacity.native.contrast_stats(effect,draws)))
    return dict(metrics=list(FORCE_METRICS),modes=list(MODES),steps=list(range(1,1001)),
        mode_means=values.mean(axis=(0,1,2,3,5)).tolist(),aligned_minus_translated=rows,
        input_strength_matched=True,effective_force_matched=False,
        inferential_gate=False,secondary_intervals_multiplicity_adjusted=False)


def summarize(blocks, cfg=CONFIG):
    if len(blocks) != 8: raise ValueError('eight paired source/reader blocks required')
    v = np.stack([b['values'] for b in blocks])
    if v.shape != (8, cfg.lives, 28, 3, len(cfg.times), 12) or not np.isfinite(v).all():
        raise ValueError('complete finite reading panel required')
    draws = rng(0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    for observer, col in (('qualified', 0), ('sign', 2)):
        pref = v[..., -1, col]-v[..., -1, col+1]  # block, life, case, generation
        for stage in ('all', 1, 2, 3):
            obs = pref if stage == 'all' else pref[..., stage-1]
            for name in tuple(a+'_minus_'+b for a, b in PAIRS)+('specificity_gain',):
                effects = []
                for role in (0, 1):
                    cell = lambda k: obs[:, :, CASES.index((role, k))]
                    if name == 'specificity_gain': effect = cell('aligned')-cell('aligned_shuffle')-cell('translated')+cell('translated_shuffle')
                    else:
                        a, b = name.split('_minus_'); effect = cell(a)-cell(b)
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
        for kind in MODES}
    primary = pick('aligned_minus_translated'); directions = [pick('aligned_minus_translated', r) for r in (0, 1)]
    gain = content['aligned'] and positive(primary) and all(x['mean'] > 0 for x in directions)
    loss = content['translated'] and primary['pointwise_block_bootstrap_95'][1] < 0 and all(x['mean'] < 0 for x in directions)
    label = 'READOUT_NOT_QUALIFIED' if not readable else 'ALIGNED_ADVANTAGE_QUALIFIED' if gain else 'TRANSLATED_ADVANTAGE_QUALIFIED' if loss else 'ADDRESS_EFFECT_UNRESOLVED'
    return dict(schema='l20_source_translation_v1', label=label, primary=primary, directional_primary=directions,
        source_force_audit=force_summary(blocks,cfg),
        translated_readable=content['translated'], aligned_readable=content['aligned'],
        no_feedback_readable=content['no_feedback'], readout_qualified=readable,
        readout_gates=gates, contrasts=rows, target_disagreement_cells=disagreement,
        cases=[list(c) for c in CASES], times=list(cfg.times), metrics=list(METRICS),
        cell_means=v.mean(axis=(0, 1)).tolist(), reader_blocks=list(TISSUES), source_blocks=list(parent.TISSUES),
        blocks=8, lives_per_block=cfg.lives, generations_reused=3, reader_paths=8*cfg.lives*84,
        packet_bytes=2048, new_renewal_cohort=False, source_geometry_preserved=True,
        source_start_checkpoint=300, source_steps=SOURCE_STEPS, source_times=list(SOURCE_TIMES),
        source_rho=SOURCE_RHO, source_lambda=SOURCE_LAMBDA, source_gain=SOURCE_GAIN,
        source_starts_reused=True, source_noise_reused=False, new_source_writer_paths=8*cfg.lives*18,
        modes=list(MODES), latent_theta_transmitted=False, writer_inputs=['R_final'],
        record_rule='project(tanh(R_final), .3)', theta_start_zero=True,
        absolute_fidelity_gate=None, equivalence_test=False, secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l20_source_translation_v1', decision='D127', law='L20/L17', run_id=RUN_ID,
        control_id=CONTROL_ID, tag=TAG, config=asdict(CONFIG), tissues=list(TISSUES), disposable=DISPOSABLE,
        source_run=parent.RUN_ID, source_blocks=list(parent.TISSUES), source_disposable=514217,
        source_start_checkpoint=300, source_starts_reused=True, source_noise_reused=False,
        source_steps=SOURCE_STEPS, source_times=list(SOURCE_TIMES), modes=list(MODES),
        source_rho=SOURCE_RHO, source_lambda=SOURCE_LAMBDA, source_gain=SOURCE_GAIN, source_sigma=.3,
        new_source_writer_paths=576, source_writer_updates=576000,
        diagnostic_zero_theta_steps=576000, source_address_rule='one uniform nonzero toroidal shift per life/stratum; fixed and shared across roles',
        force_metrics=list(FORCE_METRICS), input_strength_matched=True, effective_force_matched=False, theta_start_zero=True,
        latent_theta_written_all_arms=True, latent_theta_transmitted=False,
        writer_inputs=['R_final'], writer_rule='project(tanh(R_final), .3)',
        constructed_primary_packets=576, source_pairs=192, generations_reused=3,
        cases=[list(c) for c in CASES], metrics=list(METRICS), times=list(CONFIG.times),
        reader_paths=2688, packet_bytes=2048,
        primary='all-generation terminal qualified aligned-minus-translated preference',
        positive='instrument and aligned content qualify, primary lower95>0, both direction means>0',
        negative='instrument and translated content qualify, primary upper95<0, both direction means<0',
        losing_arm_content_required=False,
        content='pooled intact-minus-shuffle lower95>0 and both directional means>0; both intact-minus-zero lower95>0',
        instrument='both ideal-minus-zero directional lower95>0; different target fields',
        uncertainty='10000 whole-source/reader-block percentile draws; average 3 source strata within 4 paired lives within 8 blocks',
        descriptive_tie_atol=1e-12, no_equivalence=True, shared_shuffle=True, source_shifting_target_blind=True,
        source_shift_distribution='uniform integer 1..255 -> divmod(code,16); np.roll(y,x)',
        source_geometry_preserved=True, nonzero_shift_may_preserve_symmetric_content=True,
        force_counterfactual='same-old-state/same-noise zero-theta next-V; diagnostic only', new_renewal_cohort=False,
        reader_writing=False, reader_gain=0., reader_sigma=.3, state_atol=1e-10, metric_atol=1e-12,
        automatic_retry=False, automatic_follow_on=False)
