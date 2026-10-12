"""D128: one fixed inverse-address rescue of retained D127 packets.

Fresh readers only; no source dynamics, fitting, offset search or normalization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util

import numpy as np

from . import l20_three_rewrite as parent
from . import l20_source_translation as source_model
from .io import DEFAULT_EXTERNAL_ROOT, canonical_digest, sha256_file

WS, ORIGIN, PACKAGES = parent.WS, parent.ORIGIN, parent.PACKAGES
RUN_ID = 'l20_inverse_address_v1_attempt1'
CONTROL_ID = 'l20_inverse_address_v1_source_bridge_attempt1'
TAG = 'l20-inverse-address-v1'
TISSUES, DISPOSABLE = tuple(range(70000, 70008)), 514228
BASES = ('translated','rescued','aligned','aligned_inverse')
KINDS = BASES + tuple(k+'_shuffle' for k in BASES) + tuple(k+'_sham' for k in BASES) + tuple(k+'_off' for k in BASES) + ('ideal','ideal_shifted','ideal_rescued','zero')
CASES = tuple((r,k) for r in (0,1) for k in KINDS)
METRICS = parent.METRICS
PAIRS = (('rescued','translated'),('aligned_inverse','aligned'),
    ('rescued','aligned'),('translated','aligned'),
    *((k,k+'_shuffle') for k in BASES), *((k,'zero') for k in BASES),
    ('ideal','zero'),('ideal_rescued','ideal_shifted'),('ideal_shifted','zero'))
INTERACTIONS = {
    'specificity_gain': {'rescued':1,'rescued_shuffle':-1,'translated':-1,'translated_shuffle':1},
    'source_interaction': {'rescued':1,'translated':-1,'aligned_inverse':-1,'aligned':1}}
SCIENCE = ('src/laws_confirmation/l20_inverse_address.py',
    'src/laws_confirmation/l20_inverse_address_run.py',
    'scripts/audit_l20_inverse_address_outputs.py', 'tests/test_l20_inverse_address.py',
    'scripts/run_l20_inverse_address.sh', 'protocols/L20_INVERSE_ADDRESS_V1.md')
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
    return 514227 if index == DISPOSABLE else 69000+index-70000


def source_paths(index, root=DEFAULT_EXTERNAL_ROOT):
    si = source_index(index)
    directory = root/('tmp' if index == DISPOSABLE else 'outputs')/(
        source_model.RUN_ID+'_benchmark' if index == DISPOSABLE else source_model.RUN_ID)
    return directory/f'block_{si}.npz', directory/f'block_{si}.json'


def load_source(index, root=DEFAULT_EXTERNAL_ROOT):
    from .l15_repair_speed_run import load_npz, read_json
    paths = source_paths(index, root)
    raw, meta = load_npz(paths[0]), read_json(paths[1])
    assert meta['index'] == source_index(index) and meta['config'] == asdict(source_model.CONFIG)
    assert raw['packets'].shape == (4,28,3,2048) and raw['source_shifts'].shape == (4,3,2)
    assert raw['states'].shape == (4,28,3,4,3,16,16)
    return raw, meta


def rng(index, life, phase):
    key = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(key[:16], 'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d128_checker', WS/SCIENCE[2])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def read_packet(packet, index, life, generation, cfg=CONFIG, enabled=True):
    """Bytes plus public host/life/generation only; no source body/label/RNG."""
    source_index(index)
    if type(life) is not int or not 0 <= life < cfg.lives or type(generation) is not int or generation not in (1, 2, 3):
        raise ValueError('declared life and source-generation stratum required')
    if type(enabled) is not bool: raise ValueError('boolean reading switch required')
    return read_streams(packet,context(index),rng(index,life,f'g{generation}:birth'),
        rng(index,life,f'g{generation}:read'),cfg,enabled)


def read_streams(packet,ctx,birth_random,read_random,cfg,enabled):
    """Shared equations for new readers and the explicitly known-noise bridge."""
    field=decode(packet); applied=field if enabled else np.zeros_like(field)
    v=.2*birth_random.standard_normal((1,16,16))
    birth_rng=canonical_digest(birth_random.bit_generator.state)
    state=(v,v.copy(),v.copy()); saved=[np.stack(state)[:,0]]
    for t in range(1,cfg.steps+1):
        state=ctx['api']['blueprint_step'](*state,applied,ctx['tissue'],ctx['ladder'],
            ctx['bp'],'T',read_random,c_m=0.)
        if t in cfg.times: saved.append(np.stack(state)[:,0])
    return np.stack(saved),dict(birth_rng=birth_rng,read_rng=canonical_digest(read_random.bit_generator.state),
        input_sha256=hashlib.sha256(packet).hexdigest(),packet_bytes=2048,enabled=enabled,
        writing=False,gain=0.,target_labels=False)


def shift_packet(packet,shift,inverse=True):
    """Permutation of saved bytes only, using the declared coordinate shift."""
    if (not isinstance(shift,np.ndarray) or shift.dtype!=np.int64 or shift.shape!=(2,)
            or not np.all((shift>=0)&(shift<16)) or not shift.any() or type(inverse) is not bool):
        raise ValueError('nonzero int64 toroidal shift and boolean direction required')
    field=decode(packet)
    return encode(np.roll(field,tuple((-1 if inverse else 1)*int(x) for x in shift),axis=(0,1)))


def packet_routes(translated_packet,aligned_packet,shift):
    """No source R/body/theta, target label, optimum shift or fitted coefficient."""
    decode(translated_packet);decode(aligned_packet)
    return (translated_packet,shift_packet(translated_packet,shift),
            aligned_packet,shift_packet(aligned_packet,shift))


def simulate_life(index,life,source,cfg=CONFIG,order=CASES):
    source_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or len(order)!=len(CASES) or set(order)!=set(CASES):
        raise ValueError('declared life and complete unique condition order required')
    targets=source['targets'][life].copy();shifts=source['source_shifts'][life].copy()
    source_packets=np.stack([[np.stack([source['packets'][life,source_model.CASES.index((r,k)),gi].copy()
        for k in ('translated','aligned')]) for gi in range(3)] for r in (0,1)])
    fields=np.stack([[np.stack([decode(b) for b in packet_routes(
        source_packets[r,gi,0].tobytes(),source_packets[r,gi,1].tobytes(),shifts[gi])])
        for gi in range(3)] for r in (0,1)])
    if not np.isfinite(fields).all() or not np.all(np.abs(fields.std(axis=(-2,-1))-.3)<1e-14):
        raise ValueError('invalid retained record: fail rather than exclude')
    permutations=np.stack([[rng(index,life,f'g{g}:shuffle:{r}').permutation(256)
        for g in (1,2,3)] for r in (0,1)])
    packets={}
    for r,kind in CASES:
        values=[]
        for gi in range(3):
            if kind in ('ideal','ideal_shifted','ideal_rescued'):
                field=api()['original'].project_theta(np.tanh(1.5*targets[r]),cfg.norm)
                packet=encode(field)
                if kind!='ideal': packet=shift_packet(packet,shifts[gi],False)
                if kind=='ideal_rescued': packet=shift_packet(packet,shifts[gi],True)
            elif kind=='zero': packet=encode(np.zeros((16,16)))
            else:
                base=next(k for k in BASES if kind==k or kind in (k+'_shuffle',k+'_sham',k+'_off'))
                field=fields[r,gi,BASES.index(base)];packet=encode(field)
                if kind.endswith('_shuffle'): packet=encode(field.ravel()[permutations[r,gi]].reshape(16,16))
                elif kind.endswith('_sham'): packet=shift_packet(shift_packet(packet,shifts[gi],False),shifts[gi],True)
            values.append(packet)
        packets[(r,kind)]=values
    paths={c:[read_packet(packets[c][gi],index,life,gi+1,cfg,not c[1].endswith('_off'))
        for gi in range(3)] for c in order}
    states=np.stack([np.stack([x[0] for x in paths[c]]) for c in CASES])
    raw=dict(targets=targets,source_packets=source_packets,source_shifts=shifts,
        prepared_fields=fields,permutations=permutations,
        packets=np.stack([np.stack([np.frombuffer(b,np.uint8) for b in packets[c]]) for c in CASES]),
        states=states,values=parent.observations(states,targets,CASES,cfg))
    ctx=context(index)
    meta=dict(index=index,source_index=source_index(index),life=life,config=asdict(cfg),
        cases=[list(c) for c in CASES],times=list(cfg.times),reader_tag=TAG,source_tag=source_model.TAG,
        source_reused=True,source_checkpoint=1000,source_trajectories_new=False,new_source_writes=0,
        packet_inputs=['saved_packet_bytes','declared_source_shift'],
        record_rule='native bytes or one inverse source shift; no normalization',
        record_reprojected=False,inverse_is_analyst_supplied=True,source_shift_transmitted=False,
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        readers=[[x[1] for x in paths[c]] for c in CASES])
    return raw,meta


def execute_block(index, cfg=CONFIG, root=DEFAULT_EXTERNAL_ROOT):
    source, _ = load_source(index, root); rows, records = [], []; audit = checker()
    for life in range(cfg.lives):
        raw, meta = simulate_life(index, life, source, cfg)
        meta['replay'] = audit.check_life(raw, meta, cfg, source, replay=True)
        rows.append(raw); records.append(meta)
    return {k: np.stack([r[k] for r in rows]) for k in rows[0]}, dict(index=index, config=asdict(cfg),
        source_sha256={str(x): sha256_file(x) for x in source_paths(index, root)}, lives=records)


def source_bridge(root=DEFAULT_EXTERNAL_ROOT):
    """Twenty-four already observed D127 readers, using their original streams."""
    source,_=load_source(DISPOSABLE,root);si=source_index(DISPOSABLE)
    cases=tuple((r,k) for r in (0,1) for k in ('aligned','translated','ideal','zero'))
    indices=[source_model.CASES.index(c) for c in cases]
    packets=source['packets'][0,indices].copy();ctx=context(si)
    paths=[[read_streams(packets[ci,gi].tobytes(),ctx,source_model.rng(si,0,f'g{gi+1}:birth'),
        source_model.rng(si,0,f'g{gi+1}:read'),CONFIG,True) for gi in range(3)]
        for ci in range(len(cases))]
    raw=dict(packets=packets,states=np.stack([np.stack([x[0] for x in row]) for row in paths]),
        targets=source['targets'][0].copy())
    np.testing.assert_array_equal(raw['states'],source['states'][0,indices])
    meta=dict(index=si,life=0,cases=[list(c) for c in cases],times=list(CONFIG.times),
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        readers=[[x[1] for x in row] for row in paths],known_outcomes=True,new_source_writes=0)
    meta['replay']=checker().check_source(raw,meta,source)
    return raw,meta


def summarize(blocks, cfg=CONFIG):
    if len(blocks) != 8: raise ValueError('eight paired source/reader blocks required')
    v = np.stack([b['values'] for b in blocks])
    if v.shape != (8, cfg.lives, 40, 3, len(cfg.times), 12) or not np.isfinite(v).all():
        raise ValueError('complete finite reading panel required')
    draws = rng(0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    for observer, col in (('qualified', 0), ('sign', 2)):
        pref = v[..., -1, col]-v[..., -1, col+1]  # block, life, case, generation
        for stage in ('all', 1, 2, 3):
            obs = pref if stage == 'all' else pref[..., stage-1]
            for name in tuple(a+'_minus_'+b for a, b in PAIRS)+tuple(INTERACTIONS):
                effects = []
                for role in (0, 1):
                    cell = lambda k: obs[:, :, CASES.index((role, k))]
                    if name in INTERACTIONS: effect = sum(w*cell(k) for k,w in INTERACTIONS[name].items())
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
    content={kind:bool(readable and positive(pick(kind+'_minus_'+kind+'_shuffle')) and
        all(positive(pick(kind+'_minus_zero',r)) and pick(kind+'_minus_'+kind+'_shuffle',r)['mean']>0 for r in (0,1)))
        for kind in BASES}
    calibration_gates=[pick('ideal_rescued_minus_ideal_shifted',r) for r in (0,1)]
    calibration=bool(readable and all(positive(x) for x in calibration_gates))
    primary=pick('rescued_minus_translated');directions=[pick('rescued_minus_translated',r) for r in (0,1)]
    gain=positive(primary) and all(x['mean']>0 for x in directions)
    harm=primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions)
    label=('READOUT_NOT_QUALIFIED' if not readable else 'RESCUE_CONTROL_NOT_QUALIFIED' if not calibration else
        'INVERSE_RESCUE_QUALIFIED' if gain and content['rescued'] else
        'INVERSE_GAIN_WITHOUT_CONTENT_QUALIFICATION' if gain else
        'INVERSE_HARM_DETECTED' if harm else 'INVERSE_EFFECT_UNRESOLVED')
    return dict(schema='l20_inverse_address_v1',label=label,primary=primary,directional_primary=directions,
        content_qualified=content,readout_qualified=readable,calibration_qualified=calibration,
        readout_gates=gates,calibration_gates=calibration_gates,contrasts=rows,target_disagreement_cells=disagreement,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(METRICS),
        cell_means=v.mean(axis=(0,1)).tolist(),reader_blocks=list(TISSUES),source_blocks=list(source_model.TISSUES),
        blocks=8,lives_per_block=cfg.lives,generations_reused=3,reader_paths=8*cfg.lives*120,
        packet_bytes=2048,reused_source_histories=True,new_renewal_cohort=False,new_source_writes=0,
        source_checkpoint=1000,packet_inputs=['saved_packet_bytes','declared_source_shift'],
        record_rule='native bytes or one inverse source shift; no normalization',
        record_reprojected=False,inverse_is_analyst_supplied=True,source_shift_transmitted=False,
        absolute_fidelity_gate=None,equivalence_test=False,secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l20_inverse_address_v1',decision='D128',law='L20/L17',run_id=RUN_ID,
        control_id=CONTROL_ID,tag=TAG,config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,
        source_run=source_model.RUN_ID,source_blocks=list(source_model.TISSUES),source_disposable=514227,
        source_checkpoint=1000,source_reused=True,new_source_writes=0,new_source_trajectories=0,
        primary_packets=768,retained_source_packets=384,inverse_packets=384,
        packet_inputs=['saved_packet_bytes','declared_source_shift'],record_reprojected=False,
        inverse_is_analyst_supplied=True,source_shift_transmitted=False,
        record_rule='native bytes or one inverse source shift; no normalization',
        bases=list(BASES),cases=[list(c) for c in CASES],metrics=list(METRICS),times=list(CONFIG.times),
        source_pairs=192,generations_reused=3,reader_paths=3840,packet_bytes=2048,exact_path_aliases=1824,
        primary='all-stratum terminal qualified rescued-minus-translated preference',
        positive='instrument and known-shift calibration and rescued content qualify; primary lower95>0, both direction means>0',
        incomplete_gain='same positive contrast without rescued content qualification is a gain, not qualified rescue',
        negative='instrument and calibration qualify; primary upper95<0 and both directional means<0; report all content flags',
        content='pooled own-shuffle lower95>0 and both directional means>0; both own-zero lower95>0',
        instrument='both ideal-zero directional lower95>0; different targets',
        calibration='both ideal_rescued-ideal_shifted directional lower95>0; ideal_rescued exactly aliases ideal',
        uncertainty='10000 whole-source/reader-block percentile draws; average 3 source strata within 4 paired lives within 8 blocks',
        descriptive_tie_atol=1e-12,no_equivalence=True,shared_shuffle=True,offset_search=False,
        inverse_steps=1,reader_writing=False,reader_gain=0.,reader_sigma=.3,
        state_atol=1e-10,metric_atol=1e-12,automatic_retry=False,automatic_follow_on=False)
