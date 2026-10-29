"""D121: linear-input versus tanh V/R writers, paired fresh readers.

Known D117 sources; four matched-strength packets without new source dynamics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util

import numpy as np

from . import l20_three_rewrite as parent
from .io import DEFAULT_EXTERNAL_ROOT, canonical_digest, sha256_file

WS, ORIGIN, PACKAGES = parent.WS, parent.ORIGIN, parent.PACKAGES
RUN_ID = 'l20_linear_writer_v1_attempt1'
CONTROL_ID = 'l20_linear_writer_v1_source_bridge_attempt1'
TAG = 'l20-linear-writer-v1'
TISSUES, DISPOSABLE = tuple(range(63000, 63008)), 514221
WRITERS = ('linear', 'tanh')
BASES = ('linear_body', 'linear_reference', 'tanh_body', 'tanh_reference')
KINDS = BASES + tuple(k+'_shuffle' for k in BASES) + (
    'linear_sham', 'tanh_sham', 'linear_off', 'tanh_off', 'ideal', 'zero')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
METRICS = parent.METRICS
PAIRS = (('linear_reference', 'linear_body'), ('tanh_reference', 'tanh_body'),
    ('tanh_reference', 'linear_reference'), ('tanh_body', 'linear_body'), ('ideal', 'zero')) + tuple(
        pair for k in BASES for pair in ((k, k+'_shuffle'), (k, 'zero')))
SPECIAL = {
    'linear_specificity_gain': {'linear_reference': 1, 'linear_reference_shuffle': -1,
        'linear_body': -1, 'linear_body_shuffle': 1},
    'tanh_specificity_gain': {'tanh_reference': 1, 'tanh_reference_shuffle': -1,
        'tanh_body': -1, 'tanh_body_shuffle': 1},
    'writer_interaction': {'tanh_reference': 1, 'tanh_body': -1,
        'linear_reference': -1, 'linear_body': 1},
    'specificity_interaction': {'tanh_reference': 1, 'tanh_reference_shuffle': -1,
        'tanh_body': -1, 'tanh_body_shuffle': 1, 'linear_reference': -1,
        'linear_reference_shuffle': 1, 'linear_body': 1, 'linear_body_shuffle': -1}}
SCIENCE = ('src/laws_confirmation/l20_linear_writer.py',
    'src/laws_confirmation/l20_linear_writer_run.py',
    'scripts/audit_l20_linear_writer_outputs.py', 'tests/test_l20_linear_writer.py',
    'scripts/run_l20_linear_writer.sh', 'protocols/L20_LINEAR_WRITER_V1.md')
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
    return 514217 if index == DISPOSABLE else 60000+index-63000


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
    spec = importlib.util.spec_from_file_location('d121_checker', WS/SCIENCE[2])
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


def write_record(snapshot, writer):
    """Only the selected snapshot and a public, fixed transform selector."""
    if writer not in WRITERS: raise ValueError('linear or tanh writer required')
    if not isinstance(snapshot, np.ndarray) or snapshot.shape != (16, 16) or snapshot.dtype != np.float64 or not np.isfinite(snapshot).all():
        raise ValueError('finite float64 16x16 snapshot required')
    candidate = snapshot if writer == 'linear' else np.tanh(snapshot)
    return api()['original'].project_theta(candidate, .3)


def simulate_life(index, life, source, cfg=CONFIG, order=CASES):
    if len(order) != len(CASES) or set(order) != set(CASES): raise ValueError('complete unique condition order required')
    targets = source['targets'][life].copy()
    source_fields = np.stack([[np.stack([source['generation_states'][life, parent.CASES.index((r, 'rewrite')), g, 4, f]
                                        for f in (0, 2)]) for g in range(3)] for r in (0, 1)])
    # role, generation, writer(linear/tanh), source(V/R), row, column.
    fields = np.stack([[np.stack([np.stack([write_record(x, writer) for x in source_fields[r, g]])
                        for writer in WRITERS]) for g in range(3)] for r in (0, 1)])
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
                writer, handling = kind.split('_', 1)
                body, reference = fields[r, gi, WRITERS.index(writer)]
                if handling in ('body', 'sham'): field = body
                elif handling in ('reference', 'off'): field = reference
                elif handling == 'body_shuffle': field = body.ravel()[perm].reshape(16, 16)
                elif handling == 'reference_shuffle': field = reference.ravel()[perm].reshape(16, 16)
                else: raise AssertionError('undeclared condition')
                if handling == 'sham': field = body.ravel()[perm][np.argsort(perm)].reshape(16, 16)
            values.append(encode(field))
        packets[(r, kind)] = values
    paths = {c: [read_packet(packets[c][gi], index, life, gi+1, cfg, not c[1].endswith('_off'))
                 for gi in range(3)] for c in order}
    states = np.stack([np.stack([x[0] for x in paths[c]]) for c in CASES])
    raw = dict(targets=targets, source_fields=source_fields, written_fields=fields, permutations=permutations,
        packets=np.stack([np.stack([np.frombuffer(b, np.uint8) for b in packets[c]]) for c in CASES]),
        states=states, values=parent.observations(states, targets, CASES, cfg))
    ctx = context(index)
    meta = dict(index=index, source_index=source_index(index), life=life, config=asdict(cfg),
        cases=[list(c) for c in CASES], times=list(cfg.times), reader_tag=TAG, source_tag=parent.TAG,
        source_reused=True, source_checkpoint=300, writer_inputs=['V', 'R'], writers=list(WRITERS),
        writer_rules=['project(snapshot, .3)', 'project(tanh(snapshot), .3)'],
        incoming_theta_used=False, tissue=asdict(ctx['tissue']),
        ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']),
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
    """Six already observed D117 disposable terminal readers, no writers."""
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
    primary = pick('linear_reference_minus_linear_body')
    directions = [pick('linear_reference_minus_linear_body', r) for r in (0, 1)]
    gain = content['linear_reference'] and positive(primary) and all(x['mean'] > 0 for x in directions)
    loss = content['linear_body'] and primary['pointwise_block_bootstrap_95'][1] < 0 and all(x['mean'] < 0 for x in directions)
    label = 'READOUT_NOT_QUALIFIED' if not readable else 'LINEAR_REFERENCE_ADVANTAGE_QUALIFIED' if gain else 'LINEAR_BODY_ADVANTAGE_QUALIFIED' if loss else 'LINEAR_REFERENCE_EFFECT_UNRESOLVED'
    interaction = pick('writer_interaction')
    idir = [pick('writer_interaction', r) for r in (0, 1)]
    ilabel = 'INTERACTION_CONTENT_NOT_QUALIFIED' if not all(content.values()) else 'INTERACTION_UNRESOLVED'
    if all(content.values()):
        if positive(interaction) and all(x['mean'] > 0 for x in idir): ilabel = 'TANH_INCREASES_REFERENCE_GAP'
        elif interaction['pointwise_block_bootstrap_95'][1] < 0 and all(x['mean'] < 0 for x in idir): ilabel = 'TANH_DECREASES_REFERENCE_GAP'
    return dict(schema='l20_linear_writer_v1', label=label, primary=primary, directional_primary=directions,
        content_readable=content, readout_qualified=readable, readout_gates=gates,
        interaction=interaction, directional_interaction=idir, interaction_label=ilabel,
        interaction_is_secondary=True, contrasts=rows, target_disagreement_cells=disagreement,
        cases=[list(c) for c in CASES], times=list(cfg.times), metrics=list(METRICS),
        cell_means=v.mean(axis=(0, 1)).tolist(), reader_blocks=list(TISSUES), source_blocks=list(parent.TISSUES),
        blocks=8, lives_per_block=cfg.lives, generations_reused=3, reader_paths=8*cfg.lives*84,
        packet_bytes=2048, reused_source_histories=True, new_renewal_cohort=False,
        source_checkpoint=300, writer_inputs=['V', 'R'], writers=list(WRITERS),
        writer_rules=['project(snapshot, .3)', 'project(tanh(snapshot), .3)'],
        absolute_fidelity_gate=None, equivalence_test=False, secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l20_linear_writer_v1', decision='D121', law='L20', run_id=RUN_ID,
        control_id=CONTROL_ID, tag=TAG, config=asdict(CONFIG), tissues=list(TISSUES), disposable=DISPOSABLE,
        source_run=parent.RUN_ID, source_blocks=list(parent.TISSUES), source_disposable=514217,
        source_checkpoint=300, source_reused=True, new_source_writes=0, new_source_trajectories=0,
        constructed_primary_packets=768, writer_inputs=['V', 'R'], incoming_theta_used=False,
        writers=list(WRITERS), writer_rules=['project(snapshot, .3)', 'project(tanh(snapshot), .3)'],
        source_reference_gain_during_read=0., normalization_retained=True,
        cases=[list(c) for c in CASES], metrics=list(METRICS), times=list(CONFIG.times),
        source_pairs=192, generations_reused=3, reader_paths=2688, exact_path_aliases=864, packet_bytes=2048,
        primary='all-generation terminal qualified linear-reference-minus-linear-body preference',
        positive='ideal/linear-reference content qualified, primary lower95>0, both direction means>0',
        content='pooled intact-minus-shuffle lower95>0 and both directional means>0; both intact-minus-zero lower95>0',
        instrument='both ideal-minus-zero directional lower95>0; different target fields',
        negative='ideal/linear-body content qualified, primary upper95<0, both direction means<0',
        key_secondary='(tanh reference-body)-(linear reference-body), paired within the same readers',
        interaction_label='all four content routes qualified; interval excludes zero and both direction means have same sign',
        interaction_is_secondary=True, secondary_intervals_multiplicity_adjusted=False,
        uncertainty='10000 whole-source/reader-block percentile draws; average 3 generations within 4 paired lives within 8 blocks',
        descriptive_tie_atol=1e-12, no_equivalence=True, shared_shuffle=True, history_mechanism_identified=False,
        reader_writing=False, reader_gain=0., state_atol=1e-10, metric_atol=1e-12,
        automatic_retry=False, automatic_follow_on=False)
