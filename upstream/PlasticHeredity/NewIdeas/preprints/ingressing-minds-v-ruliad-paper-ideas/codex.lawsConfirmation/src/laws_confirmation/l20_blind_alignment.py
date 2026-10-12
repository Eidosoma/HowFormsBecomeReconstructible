"""D130: supplied-template, shift-blind alignment on fresh continuations.

Only record bytes enter the selector. The template prior is explicitly supplied.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util
from functools import lru_cache

import numpy as np

from . import l20_three_rewrite as parent
from . import l20_source_translation as source_model
from . import l20_inverse_address as known_reader
from .io import DEFAULT_EXTERNAL_ROOT, canonical_digest, sha256_file

WS, ORIGIN, PACKAGES = parent.WS, parent.ORIGIN, parent.PACKAGES
RUN_ID = 'l20_blind_alignment_v1_attempt1'
CONTROL_ID = 'l20_blind_alignment_v1_source_bridge_attempt1'
TAG = 'l20-blind-alignment-v1'
TISSUES, DISPOSABLE = tuple(range(71000, 71008)), 514230
MODES = ('translated', 'aligned')
BASES = ('native','blind','known','aligned','aligned_blind')
SELECTOR_INPUTS = ('native','aligned','native_shuffle','aligned_shuffle','ideal_shifted','zero')
KINDS = BASES + tuple(k+'_shuffle' for k in BASES) + (
    'shuffle_blind','aligned_shuffle_blind','blind_sham','blind_off',
    'aligned_blind_off','native_off','known_off','ideal','ideal_shifted','ideal_blind','zero')
CASES = tuple((r,k) for r in (0,1) for k in KINDS)
METRICS = parent.METRICS
PAIRS = (('blind','native'),('known','native'),('blind','known'),
    ('aligned_blind','aligned'),('blind','aligned'),('native','aligned'),
    *((k,k+'_shuffle') for k in BASES),
    ('blind','shuffle_blind'),('aligned_blind','aligned_shuffle_blind'),
    *((k,'zero') for k in BASES),('ideal','zero'),('ideal_blind','ideal_shifted'),
    ('ideal_shifted','zero'),('shuffle_blind','native_shuffle'),
    ('aligned_shuffle_blind','aligned_shuffle'))
INTERACTIONS = {
    'specificity_gain': {'blind':1,'blind_shuffle':-1,'native':-1,'native_shuffle':1},
    'matched_specificity_gain': {'blind':1,'shuffle_blind':-1,'native':-1,'native_shuffle':1},
    'source_interaction': {'blind':1,'native':-1,'aligned_blind':-1,'aligned':1}}
ATOL = 1e-12
SELECTOR_RULE = 'family tie: identity abstention; otherwise lexicographically first maximizing shift, then inverse'
RECORD_RULE = 'project(tanh(R_final), .3); selector only permutes original packet values'

SCIENCE = ('src/laws_confirmation/l20_blind_alignment.py',
    'src/laws_confirmation/l20_blind_alignment_run.py',
    'scripts/audit_l20_blind_alignment_outputs.py', 'tests/test_l20_blind_alignment.py',
    'scripts/run_l20_blind_alignment.sh', 'protocols/L20_BLIND_ALIGNMENT_V1.md')
api, context, encode, decode = parent.api, parent.context, parent.encode, parent.decode


@dataclass(frozen=True)
class Config:
    lives: int = 4
    steps: int = 300
    source_steps: int = 1000
    norm: float = .3
    amp_threshold: float = .2

    def __post_init__(self):
        if type(self.lives) is not int or not 1 <= self.lives <= 4:
            raise ValueError('one to four retained lives required')
        if any(type(x) is not int or x <= 1 for x in (self.steps,self.source_steps)):
            raise ValueError('at least two reader steps required')
        if (self.norm, self.amp_threshold) != (.3, .2):
            raise ValueError('fixed strength and observer required')

    @property
    def times(self): return tuple(sorted({0, 1, min(100, self.steps), self.steps}))


    @property
    def source_times(self): return tuple(sorted({0, 1, min(300, self.source_steps), self.source_steps}))


CONFIG = Config()


def source_index(index):
    if type(index) is not int or index not in (*TISSUES, DISPOSABLE):
        raise ValueError('declared fresh block required')
    return 514217 if index == DISPOSABLE else 60000+index-71000


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
    assert raw['generation_states'].shape == (4,16,3,8,4,16,16)
    return raw, meta

def rng(index, life, phase):
    key = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(key[:16], 'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d130_checker', WS/SCIENCE[2])
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
    """Rigid permutation, including identity; never changes any saved value."""
    if (not isinstance(shift,np.ndarray) or shift.dtype!=np.int64 or shift.shape!=(2,)
            or not np.all((shift>=0)&(shift<16)) or type(inverse) is not bool):
        raise ValueError('int64 toroidal shift and boolean direction required')
    return encode(np.roll(decode(packet),tuple((-1 if inverse else 1)*int(x) for x in shift),(0,1)))


@lru_cache(maxsize=1)
def template_prior():
    spec=importlib.util.spec_from_file_location('d130_fixed_prior',WS/'scripts/audit_l20_address_ambiguity.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def blind_packet(packet):
    """Only bytes plus the frozen public template library. No historical shift."""
    prior=template_prior();library=prior.bank();scores=prior.correlations(packet,library)
    maxima=scores.max(axis=(1,2));family_tie=bool(abs(maxima[0]-maxima[1])<=ATOL)
    family=-1 if family_tie else int(np.argmax(maxima))
    candidates=abs(scores-scores.max())<=ATOL
    if family_tie: shift=np.zeros(2,dtype=np.int64)
    else:
        mask=abs(scores[family]-maxima[family])<=ATOL
        shift=np.argwhere(mask)[0].astype(np.int64)
        candidates=np.zeros_like(scores,dtype=bool);candidates[family]=mask
    output=shift_packet(packet,shift)
    return output,scores,dict(input_sha256=hashlib.sha256(packet).hexdigest(),
        output_sha256=hashlib.sha256(output).hexdigest(),inferred_family=family,
        chosen_forward_shift=shift.tolist(),family_maxima=maxima.tolist(),family_tie=family_tie,
        candidate_count=int(candidates.sum()),candidate_mask_sha256=hashlib.sha256(candidates.tobytes()).hexdigest(),
        template_sha256=hashlib.sha256(library.astype('<f8').tobytes()).hexdigest(),
        rule=SELECTOR_RULE,tie_atol=ATOL,inputs=['packet_bytes','fixed_public_templates'],
        target_label_access=False,historical_shift_access=False,source_state_access=False,
        reader_outcome_access=False,record_reprojected=False)


def source_shift(index,life,generation):
    source_index(index)
    if type(life) is not int or not 0<=life<4 or type(generation) is not int or generation not in (1,2,3):
        raise ValueError('declared source life and stratum required')
    code=int(rng(index,life,f'g{generation}:source_shift').integers(1,256))
    return np.asarray(divmod(code,16),dtype=np.int64)


def source_path_write(start,ctx,random,mode,shift,cfg=CONFIG):
    """Fresh writing with a fixed feedback address; no auxiliary force probes."""
    if not isinstance(start,np.ndarray) or start.shape!=(3,16,16) or start.dtype!=np.float64 or not np.isfinite(start).all():
        raise ValueError('finite float64 V/EMA/R start required')
    shift_packet(encode(np.zeros((16,16))),shift)
    if mode not in MODES or not shift.any(): raise ValueError('declared mode and nonzero source shift required')
    assert (ctx['tissue'].sigma,ctx['bp'].rho,ctx['bp'].c_m)==(.3,.002,.2)
    state=tuple(x[None].copy() for x in start);theta=np.zeros((1,16,16))
    saved=[np.stack((*state,theta))[:,0]]
    for t in range(1,cfg.source_steps+1):
        applied=theta if mode=='aligned' else np.roll(theta,tuple(int(x) for x in shift),(-2,-1))
        state=ctx['api']['blueprint_step'](*state,applied,ctx['tissue'],ctx['ladder'],
            ctx['bp'],'T',random,c_m=.2)
        theta=ctx['api']['original'].project_theta(.999*theta+.001*np.tanh(state[2]),.3)
        if t in cfg.source_times: saved.append(np.stack((*state,theta))[:,0])
    return np.stack(saved),dict(noise_rng=canonical_digest(random.bit_generator.state),source_mode=mode,
        source_shift=shift.tolist(),writing=True,gain=.2,rho=.002,lam=.001,sigma=.3,
        theta_start_zero=True,target_labels=False,force_probes=False)


def write_record(snapshot):
    return source_model.write_record(snapshot)


def prepare_packets(native,aligned,shift,permutation,ideal):
    """Orchestrator: known-shift comparator is separate from blind_packet."""
    shuffle=lambda b:encode(decode(b).ravel()[permutation].reshape(16,16))
    zero=encode(np.zeros((16,16)))
    inputs=(native,aligned,shuffle(native),shuffle(aligned),shift_packet(ideal,shift,False),zero)
    selected=[blind_packet(b) for b in inputs]
    base=dict(native=native,blind=selected[0][0],known=shift_packet(native,shift),
        aligned=aligned,aligned_blind=selected[1][0])
    packets=base | {k+'_shuffle':shuffle(b) for k,b in base.items()}
    packets.update(shuffle_blind=selected[2][0],aligned_shuffle_blind=selected[3][0],
        blind_sham=shift_packet(shift_packet(base['blind'],np.ones(2,dtype=np.int64),False),
            np.ones(2,dtype=np.int64)),
        ideal=ideal,ideal_shifted=inputs[4],ideal_blind=selected[4][0],zero=zero)
    for k in ('blind','aligned_blind','native','known'): packets[k+'_off']=base[k]
    return packets,inputs,selected

def simulate_life(index,life,source,cfg=CONFIG,order=CASES):
    source_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or len(order)!=len(CASES) or set(order)!=set(CASES):
        raise ValueError('declared life and complete unique condition order required')
    targets=source['targets'][life].copy()
    starts=np.stack([[source['generation_states'][life,8*r,g,4,:3].copy() for g in range(3)] for r in (0,1)])
    shifts=np.stack([source_shift(index,life,g) for g in (1,2,3)])
    ctx=context(source_index(index))
    writes=[[[source_path_write(starts[r,g],ctx,rng(index,life,f'g{g+1}:source'),mode,shifts[g],cfg)
        for mode in MODES] for g in range(3)] for r in (0,1)]
    source_states=np.stack([[np.stack([x[0] for x in writes[r][g]]) for g in range(3)] for r in (0,1)])
    refs=source_states[:,:,:,-1,2]
    if not np.isfinite(refs).all() or np.any(np.tanh(refs).std(axis=(-2,-1))<=1e-9):
        raise ValueError('degenerate source: fail rather than exclude')
    written=np.stack([[np.stack([write_record(x) for x in refs[r,g]]) for g in range(3)] for r in (0,1)])
    permutations=np.stack([[rng(index,life,f'g{g}:shuffle:{r}').permutation(256) for g in (1,2,3)] for r in (0,1)])
    prepared=[[prepare_packets(encode(written[r,g,0]),encode(written[r,g,1]),shifts[g],permutations[r,g],
        encode(api()['original'].project_theta(np.tanh(1.5*targets[r]),cfg.norm))) for g in range(3)] for r in (0,1)]
    packets={(r,k):[prepared[r][g][0][k] for g in range(3)] for r,k in CASES}
    paths={c:[read_packet(packets[c][g],index,life,g+1,cfg,not c[1].endswith('_off')) for g in range(3)] for c in order}
    states=np.stack([np.stack([x[0] for x in paths[c]]) for c in CASES])
    raw=dict(targets=targets,source_starts=starts,source_shifts=shifts,source_states=source_states,
        written_fields=written,permutations=permutations,
        selector_inputs=np.stack([[np.stack([np.frombuffer(b,np.uint8) for b in prepared[r][g][1]])
            for g in range(3)] for r in (0,1)]),
        selector_outputs=np.stack([[np.stack([np.frombuffer(x[0],np.uint8) for x in prepared[r][g][2]])
            for g in range(3)] for r in (0,1)]),
        selector_scores=np.stack([[np.stack([x[1] for x in prepared[r][g][2]]) for g in range(3)] for r in (0,1)]),
        prepared_fields=np.stack([[np.stack([decode(prepared[r][g][0][k]) for k in BASES]) for g in range(3)] for r in (0,1)]),
        packets=np.stack([np.stack([np.frombuffer(b,np.uint8) for b in packets[c]]) for c in CASES]),
        states=states,values=parent.observations(states,targets,CASES,cfg))
    host=context(index)
    meta=dict(index=index,source_index=source_index(index),life=life,config=asdict(cfg),
        cases=[list(c) for c in CASES],times=list(cfg.times),source_times=list(cfg.source_times),
        tag=TAG,origin_tag=parent.TAG,source_start_checkpoint=300,source_start_reused=True,
        source_noise_reused=False,source_trajectories_new=True,theta_start_zero=True,
        latent_theta_transmitted=False,source_shift_transmitted=False,
        record_rule=RECORD_RULE,selector_rule=SELECTOR_RULE,selector_inputs=list(SELECTOR_INPUTS),
        template_prior_supplied=True,learned_ontology=False,source_modes=list(MODES),
        source_context=dict(index=source_index(index),tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp'])),
        source_paths=[[[x[1] for x in writes[r][g]] for g in range(3)] for r in (0,1)],
        selectors=[[[x[2] for x in prepared[r][g][2]] for g in range(3)] for r in (0,1)],
        tissue=asdict(host['tissue']),ladder=asdict(host['ladder']),blueprint=asdict(host['bp']),
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


def bridge_source(root=DEFAULT_EXTERNAL_ROOT):
    return known_reader.load_source(known_reader.DISPOSABLE,root)[0]


def source_bridge(root=DEFAULT_EXTERNAL_ROOT):
    """Twelve already observed D127 writers plus its 24 known reader paths."""
    source=bridge_source(root);ctx=context(514217)
    writes=[[[source_path_write(source['source_starts'][0,r,g],ctx,
        source_model.rng(514227,0,f'g{g+1}:source'),mode,source['source_shifts'][0,g],CONFIG)
        for mode in MODES] for g in range(3)] for r in (0,1)]
    states=np.stack([[np.stack([x[0] for x in writes[r][g]]) for g in range(3)] for r in (0,1)])
    np.testing.assert_array_equal(states,source['source_states'][0][:,:,[1,0]])
    cases=tuple((r,k) for r in (0,1) for k in ('aligned','translated','ideal','zero'))
    indices=[source_model.CASES.index(c) for c in cases]
    packets=source['packets'][0,indices].copy();host=context(514227)
    paths=[[read_streams(packets[ci,g].tobytes(),host,source_model.rng(514227,0,f'g{g+1}:birth'),
        source_model.rng(514227,0,f'g{g+1}:read'),CONFIG,True) for g in range(3)] for ci in range(8)]
    raw=dict(packets=packets,states=np.stack([np.stack([x[0] for x in row]) for row in paths]),
        targets=source['targets'][0].copy())
    np.testing.assert_array_equal(raw['states'],source['states'][0,indices])
    meta=dict(index=514227,life=0,cases=[list(c) for c in cases],times=list(CONFIG.times),
        tissue=asdict(host['tissue']),ladder=asdict(host['ladder']),blueprint=asdict(host['bp']),
        readers=[[x[1] for x in row] for row in paths],known_outcomes=True,new_source_writes=0)
    raw.update(source_starts=source['source_starts'][0].copy(),source_shifts=source['source_shifts'][0].copy(),
        source_states=states,written_fields=np.stack([[np.stack([write_record(x) for x in states[r,g,:,-1,2]])
            for g in range(3)] for r in (0,1)]))
    meta.update(source_paths=[[[x[1] for x in writes[r][g]] for g in range(3)] for r in (0,1)],
        source_context=dict(index=514217,tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp'])))
    meta['replay']=checker().check_source(raw,meta,source)
    return raw,meta

def summarize(blocks, cfg=CONFIG):
    if len(blocks) != 8: raise ValueError('eight paired source/reader blocks required')
    v = np.stack([b['values'] for b in blocks])
    if v.shape != (8, cfg.lives, 42, 3, len(cfg.times), 12) or not np.isfinite(v).all():
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
    matched={k:bool(readable and positive(pick(k+'_minus_'+other)) and
        all(pick(k+'_minus_'+other,r)['mean']>0 for r in (0,1)))
        for k,other in (('blind','shuffle_blind'),('aligned_blind','aligned_shuffle_blind'))}
    calibration_gates=[pick('ideal_blind_minus_ideal_shifted',r) for r in (0,1)]
    calibration=bool(readable and all(positive(x) for x in calibration_gates))
    primary=pick('blind_minus_native');directions=[pick('blind_minus_native',r) for r in (0,1)]
    gain=positive(primary) and all(x['mean']>0 for x in directions)
    harm=primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions)
    label=('READOUT_NOT_QUALIFIED' if not readable else 'ALIGNMENT_CONTROL_NOT_QUALIFIED' if not calibration else
        'BLIND_ALIGNMENT_QUALIFIED' if gain and content['blind'] and matched['blind'] else
        'BLIND_GAIN_WITHOUT_CONTENT_QUALIFICATION' if gain else
        'BLIND_HARM_DETECTED' if harm else 'BLIND_EFFECT_UNRESOLVED')
    return dict(schema='l20_blind_alignment_v1',label=label,primary=primary,directional_primary=directions,
        content_qualified=content,matched_control_qualified=matched,readout_qualified=readable,calibration_qualified=calibration,
        readout_gates=gates,calibration_gates=calibration_gates,contrasts=rows,target_disagreement_cells=disagreement,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(METRICS),
        cell_means=v.mean(axis=(0,1)).tolist(),reader_blocks=list(TISSUES),source_blocks=list(parent.TISSUES),
        blocks=8,lives_per_block=cfg.lives,generations_reused=3,reader_paths=8*cfg.lives*126,
        packet_bytes=2048,reused_source_starts=True,new_renewal_cohort=False,new_source_writes=8*cfg.lives*12,
        source_start_checkpoint=300,source_steps=cfg.source_steps,source_times=list(cfg.source_times),
        source_noise_reused=False,template_prior_supplied=True,learned_ontology=False,
        record_rule=RECORD_RULE,selector_rule=SELECTOR_RULE,record_reprojected=False,source_shift_transmitted=False,
        known_shift_is_upper_bound=False,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l20_blind_alignment_v1',decision='D130',law='L20/L17',run_id=RUN_ID,
        control_id=CONTROL_ID,tag=TAG,config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,
        source_run=parent.RUN_ID,source_blocks=list(parent.TISSUES),source_disposable=514217,
        source_start_checkpoint=300,source_start_reused=True,source_noise_reused=False,
        new_source_writes=384,new_source_trajectories=384,new_founders=0,new_serial_boundaries=0,
        primary_packets=960,source_pairs=192,selector_decisions=1152,selector_scores=589824,
        selector_inputs=list(SELECTOR_INPUTS),record_rule=RECORD_RULE,selector_rule=SELECTOR_RULE,
        selector_tie_atol=ATOL,template_prior_supplied=True,learned_ontology=False,
        selector_access=['packet_bytes','fixed_public_templates'],record_reprojected=False,
        historical_shift_access=False,source_shift_transmitted=False,known_shift_is_upper_bound=False,
        bases=list(BASES),modes=list(MODES),cases=[list(c) for c in CASES],metrics=list(METRICS),
        times=list(CONFIG.times),source_times=list(CONFIG.source_times),source_rho=.002,source_gain=.2,source_lambda=.001,
        generations_reused=3,reader_paths=4032,packet_bytes=2048,exact_path_aliases=1248,
        primary='all-stratum terminal qualified blind-minus-native preference',
        positive='instrument, ideal calibration, blind content and pre-shuffle matched control qualify; primary lower95>0 and both directional means>0',
        negative='instrument and calibration qualify; primary upper95<0 and both directional means<0; report content flags',
        content='pooled own-postshuffle lower95>0 and both directional means>0; both own-zero lower95>0',
        matched='pooled blind-preshuffle_blind lower95>0 and both directional means>0',
        instrument='both ideal-zero directional lower95>0; different targets',
        calibration='both ideal_blind-ideal_shifted directional lower95>0; ideal_blind exactly aliases ideal',
        uncertainty='10000 whole-block percentile draws; average 3 source strata within 4 paired lives within 8 blocks',
        contrast_rows=624,primary_rows=1,secondary_rows=623,secondary_intervals_multiplicity_adjusted=False,
        no_equivalence=True,shared_shuffle=True,offset_search='all 256 per supplied family, frozen rule, no outcome access',
        reader_writing=False,reader_gain=0.,reader_sigma=.3,
        state_atol=1e-10,metric_atol=1e-12,automatic_retry=False,automatic_follow_on=False)
