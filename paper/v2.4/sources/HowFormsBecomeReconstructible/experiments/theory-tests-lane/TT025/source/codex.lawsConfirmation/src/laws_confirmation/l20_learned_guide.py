"""D131: one supervised mean guide, frozen before fresh-founder test outcomes."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import importlib.util
import numpy as np
from . import l20_blind_alignment as previous
from . import l20_acquisition as acquisition
from .io import DEFAULT_EXTERNAL_ROOT, canonical_digest

WS,ORIGIN,PACKAGES=previous.WS,previous.ORIGIN,previous.PACKAGES
api,context,encode,decode=previous.api,previous.context,previous.encode,previous.decode
RUN_ID='l20_learned_guide_v1_attempt1'
CONTROL_ID='l20_learned_guide_v1_source_bridge_attempt1'
TRAIN_ID='l20_learned_guide_v1_training_attempt1'
TAG='l20-learned-guide-v1'
TISSUES,TRAINING,DISPOSABLE=tuple(range(72000,72008)),(72500,72501),514231
MODES=('translated','aligned')
BASES=('native','learned','supplied','known','aligned','aligned_learned')
KINDS=BASES+tuple(k+'_shuffle' for k in BASES)+(
    'shuffle_learned','shuffle_supplied','aligned_shuffle_learned','wrong_guide','learned_sham',
    'learned_off','supplied_off','ideal','ideal_shifted','ideal_learned','ideal_supplied','zero')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
GUIDES=('learned','supplied','wrong')
SELECTOR_INPUTS=('native','aligned','native_shuffle','aligned_shuffle','ideal_shifted','zero')
METRICS=previous.METRICS
RULE='family tie: identity abstention; otherwise lexicographically first maximizing shift, then inverse'
FIT_RULE='arithmetic mean of all eight canonically aligned training packets per supplied family'
PAIRS=(('learned','native'),('supplied','native'),('learned','supplied'),('known','native'),
    ('learned','known'),('learned','aligned'),('aligned_learned','aligned'),('learned','wrong_guide'),
    *((k,k+'_shuffle') for k in BASES),
    ('learned','shuffle_learned'),('supplied','shuffle_supplied'),('aligned_learned','aligned_shuffle_learned'),
    *((k,'zero') for k in BASES),('ideal','zero'),('ideal_supplied','ideal_shifted'),
    ('ideal_learned','ideal_shifted'),('ideal_learned','ideal'),
    ('shuffle_learned','native_shuffle'),('shuffle_supplied','native_shuffle'))
INTERACTIONS={
    'specificity_gain':{'learned':1,'learned_shuffle':-1,'native':-1,'native_shuffle':1},
    'matched_specificity_gain':{'learned':1,'shuffle_learned':-1,'native':-1,'native_shuffle':1},
    'source_interaction':{'learned':1,'native':-1,'aligned_learned':-1,'aligned':1}}
SCIENCE=('src/laws_confirmation/l20_learned_guide.py','src/laws_confirmation/l20_learned_guide_run.py',
    'scripts/audit_l20_learned_guide_outputs.py','tests/test_l20_learned_guide.py',
    'scripts/run_l20_learned_guide.sh','protocols/L20_LEARNED_GUIDE_V1.md')


@dataclass(frozen=True)
class Config:
    lives:int=4
    settle:int=120
    teaching:int=1000
    steps:int=300
    source_steps:int=1000
    norm:float=.3
    lam:float=.001
    hold:float=1.2
    amp_threshold:float=.2

    def __post_init__(self):
        if type(self.lives) is not int or not 1<=self.lives<=4:
            raise ValueError('one to four paired lives required')
        if any(type(n) is not int or n<2 for n in (self.settle,self.teaching,self.steps,self.source_steps)):
            raise ValueError('integer phase lengths >=2 required')
        if (self.norm,self.lam,self.hold,self.amp_threshold)!=(.3,.001,1.2,.2):
            raise ValueError('fixed strength, rate, instruction and observer required')

    @property
    def times(self):return tuple(sorted({0,1,min(100,self.steps),self.steps}))
    @property
    def parent_times(self):return tuple(sorted({0,1,min(20,self.teaching),min(80,self.teaching),min(300,self.teaching),self.teaching}))
    @property
    def source_times(self):return tuple(sorted({0,1,min(300,self.source_steps),self.source_steps}))


CONFIG=Config()


def validate_index(index,training=False):
    if type(training) is not bool or type(index) is not int or index not in ((TRAINING if training else TISSUES)+(DISPOSABLE,)):
        raise ValueError('declared, split-isolated identity required')


def rng(index,life,phase):
    key=hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(key[:16],'little')))


def checker():
    spec=importlib.util.spec_from_file_location('d131_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def guide_bytes(guide):
    if not isinstance(guide,np.ndarray) or guide.shape!=(2,16,16) or guide.dtype!=np.float64 or not np.isfinite(guide).all():
        raise ValueError('finite two-pattern float64 guide required')
    if np.any(guide.std(axis=(-2,-1))<=1e-9):raise ValueError('numerically degenerate guide: fail, never refit')
    return guide.astype('<f8').tobytes()


def fit_guide(packets,labels):
    """Pixels come only from examples; family membership/alignment are supplied."""
    if (not isinstance(packets,np.ndarray) or packets.dtype!=np.uint8 or packets.ndim!=2 or packets.shape[1]!=2048
            or not isinstance(labels,np.ndarray) or labels.dtype!=np.int64 or labels.shape!=(len(packets),)
            or not np.all(np.isin(labels,(0,1))) or any(not np.any(labels==r) for r in (0,1))):
        raise ValueError('byte records and both declared family groups required')
    fields=np.stack([decode(b.tobytes()) for b in packets])
    result=np.stack([fields[labels==r].mean(axis=0) for r in (0,1)])
    guide_bytes(result)
    return result


def guide_bank(serialized):
    if type(serialized) is not bytes or len(serialized)!=4096:raise ValueError('4096 guide bytes required')
    return _guide_bank(serialized)


@lru_cache(maxsize=8)
def _guide_bank(serialized):
    guide=np.frombuffer(serialized,'<f8').reshape(2,16,16).copy();guide_bytes(guide)
    centered=guide-guide.mean(axis=(-2,-1),keepdims=True)
    normalized=centered/centered.std(axis=(-2,-1),keepdims=True)
    bank=np.stack([[np.roll(t,divmod(n,16),(0,1)) for n in range(256)] for t in normalized]).reshape(2,16,16,16,16)
    bank.setflags(write=False);return bank


def select_packet(packet,guide):
    """No labels, canonical pixels, index, source shift, source state or outcome."""
    serialized=guide_bytes(guide);bank=guide_bank(serialized)
    field=decode(packet);centered=field-field.mean();scale=float(centered.std())
    scores=np.einsum('rabij,ij->rab',bank,centered,optimize=False)/(256*scale) if scale else np.zeros((2,16,16))
    if not np.isfinite(scores).all():raise ValueError('finite correlations required')
    maxima=scores.max(axis=(1,2));tie=bool(abs(maxima[0]-maxima[1])<=1e-12)
    family=-1 if tie else int(np.argmax(maxima));mask=abs(scores-scores.max())<=1e-12
    shift=np.zeros(2,dtype=np.int64)
    if not tie:
        mask=np.zeros_like(scores,dtype=bool);mask[family]=abs(scores[family]-maxima[family])<=1e-12
        shift=np.argwhere(mask[family])[0].astype(np.int64)
    output=previous.shift_packet(packet,shift)
    return output,scores,dict(input_sha256=hashlib.sha256(packet).hexdigest(),
        output_sha256=hashlib.sha256(output).hexdigest(),guide_sha256=hashlib.sha256(serialized).hexdigest(),
        inferred_family=family,chosen_forward_shift=shift.tolist(),family_maxima=maxima.tolist(),
        family_tie=tie,candidate_count=int(mask.sum()),candidate_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
        rule=RULE,tie_atol=1e-12,inputs=['packet_bytes','frozen_guide_bytes'],
        target_label_access=False,historical_shift_access=False,source_state_access=False,
        outcome_access=False,record_reprojected=False)


def guide_variants(learned):
    guide_bytes(learned)
    return np.stack((learned.copy(),previous.template_prior().targets(),
        np.roll(learned,(3,5),(-2,-1))))


def common_parent_streams(ctx,birth_random,settle_random,cfg=CONFIG):
    a=ctx['api'];t=ctx['tissue'];native=a['original'].make_thresholds(t)
    theta=a['original'].project_theta(native,cfg.norm)
    v=a['launch_pattern'](0,t)[None]+t.copy_jitter*birth_random.standard_normal((1,16,16))
    state=(v,v.copy(),v.copy());birth=np.stack(state)[:,0]
    for _ in range(cfg.settle):
        state=a['blueprint_step'](*state,theta,t,ctx['ladder'],ctx['bp'],'T',settle_random)
    return native,theta,birth,np.stack(state)[:,0],dict(parent_birth_rng=canonical_digest(birth_random.bit_generator.state),
        parent_settle_rng=canonical_digest(settle_random.bit_generator.state))


def acquire_streams(settled,theta0,target,ctx,random,cfg=CONFIG):
    state=tuple(x[None].copy() for x in settled);theta=theta0[None].copy()
    saved=[np.stack((*state,theta))[:,0]]
    for t in range(1,cfg.teaching+1):
        state=(np.full_like(state[0],cfg.hold)*target[None],state[1],state[2])
        result=ctx['api']['original'].cascade_step(*state,theta,ctx['tissue'],ctx['ladder'],ctx['bp'],
            random,cfg.lam,cfg.norm)
        state,theta=result[:3],result[3]
        if t in cfg.parent_times:saved.append(np.stack((*state,theta))[:,0])
    return np.stack(saved),canonical_digest(random.bit_generator.state)


read_streams=previous.read_streams
source_path_write=previous.source_path_write


def generate_sources(index,life,cfg=CONFIG,training=False):
    validate_index(index,training)
    if type(life) is not int or not 0<=life<cfg.lives:raise ValueError('declared life required')
    ctx=context(index);targets=acquisition.capacity.target_fields(ctx)
    native,theta,birth,settled,seeds=common_parent_streams(ctx,rng(index,life,'parent_birth'),rng(index,life,'parent_settle'),cfg)
    acquired=[acquire_streams(settled,theta,targets[r],ctx,rng(index,life,'teaching'),cfg) for r in (0,1)]
    founders=np.stack([x[0] for x in acquired]);incoming=[encode(founders[r,-1,3]) for r in (0,1)]
    before=[read_streams(incoming[r],ctx,rng(index,life,'source_birth'),rng(index,life,'source_read'),cfg,True) for r in (0,1)]
    pre_states=np.stack([x[0] for x in before]);starts=pre_states[:,-1]
    code=int(rng(index,life,'source_shift').integers(1,256));shift=np.asarray(divmod(code,16),dtype=np.int64)
    modes=('aligned',) if training else MODES
    writes=[[source_path_write(starts[r],ctx,rng(index,life,'source_write'),mode,shift,cfg)
        for mode in modes] for r in (0,1)]
    paths=np.stack([np.stack([x[0] for x in row]) for row in writes])
    ref=paths[:,:,-1,2]
    if np.any(np.tanh(ref).std(axis=(-2,-1))<=1e-9):raise ValueError('degenerate record: fail rather than exclude')
    fields=np.stack([np.stack([previous.write_record(v) for v in row]) for row in ref])
    raw=dict(native_theta=native,theta0=theta,parent_birth=birth,settled=settled,targets=targets,
        founder_states=founders,founder_packets=np.stack([np.frombuffer(b,np.uint8) for b in incoming]),
        pre_states=pre_states,source_starts=starts.copy(),source_shift=shift,source_states=paths,written_fields=fields)
    meta=dict(index=index,life=life,config=asdict(cfg),training=training,tag=TAG,modes=list(modes),
        parent_times=list(cfg.parent_times),times=list(cfg.times),source_times=list(cfg.source_times),
        fresh_founders=True,reused_source_starts=False,source_theta_erased=True,source_shift_transmitted=False,
        source_gain=.2,source_rho=.002,source_lambda=.001,writer_rule='project(tanh(R_final), .3)',
        instructed_founders=True,unseen_pattern_families=False,**seeds,teaching_rng=[x[1] for x in acquired],
        pre_readers=[x[1] for x in before],writers=[[x[1] for x in row] for row in writes],
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']))
    return raw,meta


def training_block(index,cfg=CONFIG):
    validate_index(index,True);rows=[];records=[];audit=checker()
    for life in range(cfg.lives):
        raw,meta=generate_sources(index,life,cfg,True)
        meta['replay']=audit.check_sources(raw,meta,cfg,True)
        rows.append(raw);records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),training=True,lives=records)


def prepare_packets(native,aligned,shift,perm,ideal,learned):
    shuffle=lambda b:encode(decode(b).ravel()[perm].reshape(16,16))
    zero=encode(np.zeros((16,16)));inputs=(native,aligned,shuffle(native),shuffle(aligned),
        previous.shift_packet(ideal,shift,False),zero)
    variants=guide_variants(learned);selections=[[select_packet(b,guide) for b in inputs] for guide in variants]
    bases=dict(native=native,learned=selections[0][0][0],supplied=selections[1][0][0],
        known=previous.shift_packet(native,shift),aligned=aligned,aligned_learned=selections[0][1][0])
    packets=bases|{k+'_shuffle':shuffle(b) for k,b in bases.items()}
    packets.update(shuffle_learned=selections[0][2][0],shuffle_supplied=selections[1][2][0],
        aligned_shuffle_learned=selections[0][3][0],wrong_guide=selections[2][0][0],
        learned_sham=previous.shift_packet(previous.shift_packet(bases['learned'],np.ones(2,dtype=np.int64),False),np.ones(2,dtype=np.int64)),
        learned_off=bases['learned'],supplied_off=bases['supplied'],ideal=ideal,ideal_shifted=inputs[4],
        ideal_learned=selections[0][4][0],ideal_supplied=selections[1][4][0],zero=zero)
    return packets,inputs,selections


def read_packet(packet,index,life,cfg=CONFIG,enabled=True):
    validate_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or type(enabled) is not bool:raise ValueError('declared reader required')
    return read_streams(packet,context(index),rng(index,life,'birth'),rng(index,life,'read'),cfg,enabled)


def simulate_life(index,life,guide,cfg=CONFIG,order=CASES):
    if len(order)!=len(CASES) or set(order)!=set(CASES):raise ValueError('complete unique condition order required')
    raw,meta=generate_sources(index,life,cfg,False)
    perms=np.stack([rng(index,life,f'shuffle:{r}').permutation(256) for r in (0,1)])
    prepared=[prepare_packets(encode(raw['written_fields'][r,0]),encode(raw['written_fields'][r,1]),
        raw['source_shift'],perms[r],encode(api()['original'].project_theta(np.tanh(1.5*raw['targets'][r]),.3)),guide) for r in (0,1)]
    packets={(r,k):prepared[r][0][k] for r,k in CASES}
    paths={c:read_packet(packets[c],index,life,cfg,not c[1].endswith('_off')) for c in order}
    states=np.stack([paths[c][0] for c in CASES])
    raw.update(guide=guide.copy(),guide_variants=guide_variants(guide),permutations=perms,
        selector_inputs=np.stack([np.stack([np.frombuffer(b,np.uint8) for b in row[1]]) for row in prepared]),
        selector_outputs=np.stack([np.stack([np.stack([np.frombuffer(x[0],np.uint8) for x in g]) for g in row[2]]) for row in prepared]),
        selector_scores=np.stack([np.stack([np.stack([x[1] for x in g]) for g in row[2]]) for row in prepared]),
        prepared_fields=np.stack([np.stack([decode(row[0][k]) for k in BASES]) for row in prepared]),
        packets=np.stack([np.frombuffer(packets[c],np.uint8) for c in CASES]),states=states,
        values=previous.parent.observations(states,raw['targets'],CASES,cfg))
    meta.update(cases=[list(c) for c in CASES],guide_sha256=hashlib.sha256(guide_bytes(guide)).hexdigest(),
        guide_fitted_on_test=False,guide_host_prior_bytes=4096,ordinary_packet_bytes=2048,
        guide_variants=list(GUIDES),selector_inputs=list(SELECTOR_INPUTS),selector_rule=RULE,
        selectors=[[[x[2] for x in g] for g in row[2]] for row in prepared],
        readers=[paths[c][1] for c in CASES])
    return raw,meta


def load_guide(root=DEFAULT_EXTERNAL_ROOT):
    from .l15_repair_speed_run import load_npz
    raw=load_npz(root/'outputs'/TRAIN_ID/'guide.npz')
    guide=raw['guide'].copy();guide_bytes(guide);return guide


def execute_block(index,cfg=CONFIG,root=DEFAULT_EXTERNAL_ROOT,guide=None):
    guide=load_guide(root) if guide is None else guide
    rows=[];records=[];audit=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,guide,cfg)
        meta['replay']=audit.check_life(raw,meta,cfg,guide,True)
        rows.append(raw);records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),
        guide_sha256=hashlib.sha256(guide_bytes(guide)).hexdigest(),lives=records)

def bridge_inputs(root=DEFAULT_EXTERNAL_ROOT):
    from .l15_repair_speed_run import load_npz
    founder=previous.load_source(previous.DISPOSABLE,root)[0]
    known=load_npz(root/'tmp'/(previous.RUN_ID+'_benchmark')/f'block_{previous.DISPOSABLE}.npz')
    return founder,known


def source_bridge(root=DEFAULT_EXTERNAL_ROOT):
    founder,known=bridge_inputs(root);ctx=context(514217)
    native,theta,birth,settled,seeds=common_parent_streams(ctx,
        acquisition.rng(514217,0,'parent_birth'),acquisition.rng(514217,0,'parent_settle'))
    taught=[acquire_streams(settled,theta,founder['targets'][0,r],ctx,acquisition.rng(514217,0,'teaching')) for r in (0,1)]
    np.testing.assert_array_equal(np.stack([x[0] for x in taught]),founder['founder_states'][0])
    incoming=[encode(taught[r][0][-1,3]) for r in (0,1)]
    before=[read_streams(incoming[r],ctx,previous.parent.rng(514217,0,'g1:birth'),
        previous.parent.rng(514217,0,'g1:read'),CONFIG,True) for r in (0,1)]
    shift=known['source_shifts'][0,0]
    writes=[[source_path_write(before[r][0][-1],ctx,previous.rng(514230,0,'g1:source'),mode,shift)
        for mode in MODES] for r in (0,1)]
    source_states=np.stack([np.stack([x[0] for x in row]) for row in writes])
    np.testing.assert_array_equal(source_states,known['source_states'][0,:,0])
    cases=tuple((r,k) for r in (0,1) for k in ('native','blind','aligned','ideal','zero'))
    indices=[previous.CASES.index(c) for c in cases]
    packets=known['packets'][0,indices,0].copy();host=context(514230)
    reads=[read_streams(b.tobytes(),host,previous.rng(514230,0,'g1:birth'),
        previous.rng(514230,0,'g1:read'),CONFIG,True) for b in packets]
    states=np.stack([x[0] for x in reads])
    np.testing.assert_array_equal(states,known['states'][0,indices,0])
    raw=dict(native_theta=native,theta0=theta,parent_birth=birth,settled=settled,targets=founder['targets'][0].copy(),
        founder_states=np.stack([x[0] for x in taught]),founder_packets=np.stack([np.frombuffer(b,np.uint8) for b in incoming]),
        pre_states=np.stack([x[0] for x in before]),source_shift=shift.copy(),source_states=source_states,
        packets=packets,states=states)
    meta=dict(index=514217,life=0,config=asdict(CONFIG),known_outcomes=True,qualification_pool=False,
        new_futures=0,**seeds,teaching_rng=[x[1] for x in taught],pre_readers=[x[1] for x in before],
        writers=[[x[1] for x in row] for row in writes],readers=[x[1] for x in reads],cases=[list(c) for c in cases],
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        host=dict(index=514230,tissue=asdict(host['tissue']),ladder=asdict(host['ladder']),blueprint=asdict(host['bp'])))
    meta['replay']=checker().check_bridge(raw,meta,founder,known)
    return raw,meta

def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8:raise ValueError('eight held-out blocks required')
    values=np.stack([b['values'] for b in blocks])
    if values.shape!=(8,cfg.lives,48,len(cfg.times),12) or not np.isfinite(values).all():raise ValueError('complete finite panel required')
    draws=rng(0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        prefs=values[:,:,:,-1,col]-values[:,:,:,-1,col+1]
        for name in tuple(a+'_minus_'+b for a,b in PAIRS)+tuple(INTERACTIONS):
            effects=[]
            for role in (0,1):
                cell=lambda k:prefs[:,:,CASES.index((role,k))]
                if name in INTERACTIONS:effect=sum(w*cell(k) for k,w in INTERACTIONS[name].items())
                else:
                    left,right=name.split('_minus_');effect=cell(left)-cell(right)
                effects.append(effect)
            for role,effect in ((0,effects[0]),(1,effects[1]),('both',sum(effects)/2)):
                rows.append(dict(name=name,role=role,observer=observer,
                    **acquisition.capacity.native.contrast_stats(effect,draws)))
    get=lambda name,role='both':next(r for r in rows if (r['name'],r['role'],r['observer'])==(name,role,'qualified'))
    positive=lambda r:r['pointwise_block_bootstrap_95'][0]>0
    gates=[get('ideal_minus_zero',r) for r in (0,1)]
    disagreement=[[int(np.count_nonzero(b['targets'][l,0]!=b['targets'][l,1])) for l in range(cfg.lives)] for b in blocks]
    readable=bool(all(positive(r) for r in gates) and np.all(np.asarray(disagreement)>0))
    content={k:bool(readable and positive(get(k+'_minus_'+k+'_shuffle')) and
        all(get(k+'_minus_'+k+'_shuffle',r)['mean']>0 and positive(get(k+'_minus_zero',r)) for r in (0,1))) for k in BASES}
    matched={k:bool(readable and positive(get(k+'_minus_'+other)) and
        all(get(k+'_minus_'+other,r)['mean']>0 for r in (0,1))) for k,other in (
        ('learned','shuffle_learned'),('supplied','shuffle_supplied'),('aligned_learned','aligned_shuffle_learned'))}
    calibrations={k:bool(readable and all(positive(get('ideal_'+k+'_minus_ideal_shifted',r)) for r in (0,1))) for k in ('learned','supplied')}
    guide_control=bool(readable and positive(get('learned_minus_wrong_guide')) and all(get('learned_minus_wrong_guide',r)['mean']>0 for r in (0,1)))
    supplied=bool(content['supplied'] and matched['supplied'] and calibrations['supplied'])
    qualified=bool(content['learned'] and matched['learned'] and calibrations['learned'] and guide_control)
    primary=get('learned_minus_native');directions=[get('learned_minus_native',r) for r in (0,1)]
    gain=positive(primary) and all(r['mean']>0 for r in directions)
    harm=primary['pointwise_block_bootstrap_95'][1]<0 and all(r['mean']<0 for r in directions)
    label=('READOUT_NOT_QUALIFIED' if not readable else 'SUPPLIED_CONTROL_NOT_QUALIFIED' if not supplied else
        'LEARNED_GUIDE_QUALIFIED' if gain and qualified else 'LEARNED_GAIN_WITHOUT_CONTROL_QUALIFICATION' if gain else
        'LEARNED_HARM_DETECTED' if harm else 'LEARNED_EFFECT_UNRESOLVED')
    return dict(schema='l20_learned_guide_v1',label=label,primary=primary,directional_primary=directions,
        content_qualified=content,matched_control_qualified=matched,calibration_qualified=calibrations,
        guide_control_qualified=guide_control,supplied_control_qualified=supplied,readout_qualified=readable,
        readout_gates=gates,contrasts=rows,target_disagreement_cells=disagreement,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(METRICS),cell_means=values.mean(axis=(0,1)).tolist(),
        test_blocks=list(TISSUES),training_blocks=list(TRAINING),blocks=8,lives_per_block=cfg.lives,
        reader_paths=8*cfg.lives*48,source_writers=8*cfg.lives*4,founder_acquisitions=8*cfg.lives*2,
        pre_readers=8*cfg.lives*2,training_records=16,guide_bytes=4096,packet_bytes=2048,
        conditional_on_one_fitted_guide=True,fit_rule=FIT_RULE,guide_labels_and_alignment_supplied=True,
        perfect_template_pixels_in_fit=False,fresh_founders=True,reused_source_starts=False,
        unseen_pattern_families=False,new_three_generation_chain=False,learned_ontology=False,
        absolute_fidelity_gate=None,equivalence_test=False,secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l20_learned_guide_v1',decision='D131',law='L20/L17',run_id=RUN_ID,
        control_id=CONTROL_ID,training_id=TRAIN_ID,tag=TAG,config=asdict(CONFIG),
        tissues=list(TISSUES),training=list(TRAINING),disposable=DISPOSABLE,
        fit_rule=FIT_RULE,training_records=16,records_per_family=8,training_guide_fits=1,
        guide_labels_and_alignment_supplied=True,perfect_template_pixels_in_fit=False,
        conditional_on_one_fitted_guide=True,guide_bytes=4096,packet_bytes=2048,
        wrong_guide_shift=[3,5],selector_rule=RULE,selector_tie_atol=1e-12,
        guide_inputs=['training_packet_bytes','supplied_family_groups'],
        selector_inputs=['packet_bytes','frozen_guide_bytes'],
        main_cases=[list(c) for c in CASES],bases=list(BASES),modes=list(MODES),guides=list(GUIDES),
        selector_input_kinds=list(SELECTOR_INPUTS),metrics=list(METRICS),
        times=list(CONFIG.times),parent_times=list(CONFIG.parent_times),source_times=list(CONFIG.source_times),
        training_parent_acquisitions=16,training_pre_readers=16,training_source_writers=16,
        main_parent_acquisitions=64,main_pre_readers=64,main_source_writers=128,main_reader_paths=1536,
        selector_decisions=1152,selector_scores=589824,primary_packets=384,exact_path_aliases=288,
        fresh_founders=True,reused_source_starts=False,unseen_pattern_families=False,new_three_generation_chain=False,
        learned_ontology=False,learner_target_pixel_access=False,record_reprojected=False,source_shift_transmitted=False,
        source_rho=.002,source_gain=.2,source_lambda=.001,reader_writing=False,reader_gain=0.,reader_sigma=.3,
        primary='terminal qualified learned-minus-native preference, both roles within life, four lives within eight blocks',
        positive='instrument and supplied control qualify; primary lower95>0, both directional means>0; learned content, pre-shuffle matched, ideal calibration and wrong-guide control qualify',
        negative='instrument and supplied control qualify; primary upper95<0 and both directional means<0',
        content='pooled own-postshuffle lower95>0, both directional means>0; both own-zero directional lower95>0',
        matched='pooled learned-preshuffle_learned lower95>0 and both directional means>0; analogous supplied/aligned_learned',
        guide_control='pooled learned-wrong_guide lower95>0 and both directional means>0',
        instrument='both ideal-zero directional lower95>0 and distinct targets',
        calibration='both ideal_corrected-ideal_shifted directional lower95>0; supplied ideal must byte/path-alias ideal, learned need not',
        supplied_control='supplied content, matched pre-shuffle and supplied ideal calibration qualify',
        uncertainty='10000 whole-test-block percentile draws; conditional on one shared fitted guide; training uncertainty not estimated',
        contrasts=192,primary_rows=1,secondary_rows=191,secondary_intervals_multiplicity_adjusted=False,
        noninferiority_margin=None,equivalence_test=False,absolute_fidelity_gate=None,
        state_atol=1e-10,metric_atol=1e-12,automatic_retry=False,automatic_follow_on=False)
