"""D132: fixed D131 guide, fresh founders, three reset/renewal lives and a probe."""
from __future__ import annotations
from dataclasses import asdict,dataclass
import hashlib
import importlib.util
import numpy as np
from . import l20_learned_guide as previous
from .io import DEFAULT_EXTERNAL_ROOT,canonical_digest

WS,ORIGIN,PACKAGES=previous.WS,previous.ORIGIN,previous.PACKAGES
api,context,encode,decode=previous.api,previous.context,previous.encode,previous.decode
RUN_ID='l20_guide_renewal_v1_attempt1'
CONTROL_ID='l20_guide_renewal_v1_source_bridge_attempt1'
TAG='l20-guide-renewal-v1'
TISSUES,DISPOSABLE=tuple(range(73000,73008)),514232
GUIDE_SHA256='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
KINDS=('learned','native','supplied','aligned','copy','read_off','write_off','wrong','lesion','rescue','wrong_guide')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
EXTRAS=('learned_shuffle','shuffle_learned','ideal','ideal_shifted','ideal_learned','zero')
PROBES=tuple((r,k) for r in (0,1) for k in KINDS+EXTRAS)
PAIRS=(('learned','native'),('learned','supplied'),('learned','aligned'),('learned','copy'),
    ('learned','read_off'),('learned','write_off'),('learned','wrong'),('learned','lesion'),
    ('rescue','lesion'),('learned','wrong_guide'))
TERMINAL_PAIRS=(('learned','learned_shuffle'),('learned','shuffle_learned'),('ideal','zero'),('copy','zero'),
    ('ideal_learned','ideal_shifted'),('ideal_learned','ideal'),('learned','zero'),('aligned','zero'),('supplied','zero'))
METRICS=previous.METRICS
SCIENCE=('src/laws_confirmation/l20_guide_renewal.py','src/laws_confirmation/l20_guide_renewal_run.py',
    'scripts/audit_l20_guide_renewal_outputs.py','tests/test_l20_guide_renewal.py',
    'scripts/run_l20_guide_renewal.sh','protocols/L20_GUIDE_RENEWAL_V1.md')


@dataclass(frozen=True)
class Config(previous.Config):
    generations:int=3
    rescue_after:int=100

    def __post_init__(self):
        super().__post_init__()
        if type(self.generations) is not int or self.generations!=3 or type(self.rescue_after) is not int or not 1<=self.rescue_after<self.steps:
            raise ValueError('three renewals and an internal rescue time required')

    @property
    def read_times(self):return tuple(sorted({0,1,self.rescue_after,self.rescue_after+1,self.steps}))


CONFIG=Config()


def validate_index(index):
    if type(index) is not int or index not in TISSUES+(DISPOSABLE,):raise ValueError('declared new cohort or disposable required')


def generator(tag,index,life,phase):
    seed=hashlib.sha256(f'{tag}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(seed[:16],'little')))


def rng(index,life,phase):return generator(TAG,index,life,phase)


def checker():
    spec=importlib.util.spec_from_file_location('d132_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def load_guide(root=DEFAULT_EXTERNAL_ROOT):
    guide=previous.load_guide(root)
    if hashlib.sha256(previous.guide_bytes(guide)).hexdigest()!=GUIDE_SHA256:raise ValueError('original one-fit D131 guide required')
    return guide


def generate_founders(index,life,cfg=CONFIG,tag=TAG):
    if tag==TAG:validate_index(index)
    elif not (tag==previous.TAG and index==previous.DISPOSABLE and life==0 and cfg==previous.CONFIG):
        raise ValueError('only the declared already-observed bridge may use an old stream')
    if type(life) is not int or not 0<=life<cfg.lives:raise ValueError('declared life required')
    random=lambda phase:generator(tag,index,life,phase)
    ctx=context(index);targets=previous.acquisition.capacity.target_fields(ctx)
    native,theta,birth,settled,seeds=previous.common_parent_streams(ctx,random('parent_birth'),random('parent_settle'),cfg)
    acquired=[previous.acquire_streams(settled,theta,targets[r],ctx,random('teaching'),cfg) for r in (0,1)]
    founders=np.stack([x[0] for x in acquired]);incoming=[encode(founders[r,-1,3]) for r in (0,1)]
    before=[previous.read_streams(b,ctx,random('source_birth'),random('source_read'),cfg,True) for b in incoming]
    pre=np.stack([x[0] for x in before]);starts=pre[:,-1]
    shift=np.asarray(divmod(int(random('source_shift').integers(1,256)),16),dtype=np.int64)
    writes=[[previous.source_path_write(starts[r],ctx,random('source_write'),mode,shift,cfg)
        for mode in ('translated','aligned')] for r in (0,1)]
    paths=np.stack([np.stack([x[0] for x in row]) for row in writes])
    fields=np.stack([np.stack([record(ref) for ref in row]) for row in paths[:,:,-1,2]])
    raw=dict(native_theta=native,theta0=theta,parent_birth=birth,settled=settled,targets=targets,
        founder_states=founders,founder_packets=np.stack([np.frombuffer(b,np.uint8) for b in incoming]),
        pre_states=pre,source_starts=starts.copy(),source_shift=shift,source_states=paths,written_fields=fields)
    meta=dict(index=index,life=life,config=asdict(cfg),tag=tag,**seeds,teaching_rng=[x[1] for x in acquired],
        pre_readers=[x[1] for x in before],writers=[[x[1] for x in row] for row in writes],
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']))
    return raw,meta


def record(ref):
    if ref.shape!=(16,16) or not np.isfinite(ref).all() or np.tanh(ref).std()<=1e-9:
        raise ValueError('nondegenerate finite record required; never exclude or refit')
    return previous.previous.write_record(ref)


def route(packet,kind,guide):
    decode(packet);previous.guide_bytes(guide)
    if kind in ('native','aligned','ideal','ideal_shifted','zero','learned_shuffle'):
        return packet,np.zeros((2,16,16)),None
    if kind=='supplied':prior=previous.previous.template_prior().targets()
    elif kind=='wrong_guide':prior=np.roll(guide,(3,5),(-2,-1))
    elif kind in KINDS+('shuffle_learned','ideal_learned'):prior=guide
    else:raise ValueError('declared packet route required')
    return previous.select_packet(packet,prior)


def read_selected(packet,ctx,birth_random,read_random,cfg=CONFIG,enabled=True,backup=None,times=None):
    field=decode(packet);backup_field=decode(backup) if backup is not None else None
    if type(enabled) is not bool:raise ValueError('boolean reader switch required')
    times=cfg.read_times if times is None else times
    v=.2*birth_random.standard_normal((1,16,16));state=(v,v.copy(),v.copy());saved=[np.stack(state)[:,0]]
    birth=canonical_digest(birth_random.bit_generator.state)
    for t in range(1,cfg.steps+1):
        if backup is not None and t==cfg.rescue_after+1:field=backup_field.copy()
        applied=field if enabled else np.zeros((16,16))
        state=ctx['api']['blueprint_step'](*state,applied,ctx['tissue'],ctx['ladder'],ctx['bp'],'T',read_random,c_m=0.)
        if t in times:saved.append(np.stack(state)[:,0])
    return np.stack(saved),dict(birth_rng=birth,read_rng=canonical_digest(read_random.bit_generator.state),
        input_sha256=hashlib.sha256(packet).hexdigest(),backup_sha256=hashlib.sha256(backup).hexdigest() if backup is not None else None,
        rescue_after=cfg.rescue_after if backup is not None else None,packet_bytes=2048,extra_backup_bytes=2048 if backup is not None else 0,
        enabled=enabled,writing=False,gain=0.,target_labels=False)


def write_streams(start,ctx,random,mode,shift,cfg=CONFIG,enabled=True):
    if mode not in ('translated','aligned') or type(enabled) is not bool:raise ValueError('declared writer required')
    state=tuple(x[None].copy() for x in start);theta=np.zeros((1,16,16))
    saved=[np.stack((*state,theta))[:,0]]
    for t in range(1,cfg.source_steps+1):
        applied=theta if mode=='aligned' else np.roll(theta,tuple(int(x) for x in shift),(-2,-1))
        state=ctx['api']['blueprint_step'](*state,applied,ctx['tissue'],ctx['ladder'],ctx['bp'],'T',random)
        if enabled:theta=ctx['api']['original'].project_theta((1-cfg.lam)*theta+cfg.lam*np.tanh(state[2]),cfg.norm)
        if t in cfg.source_times:saved.append(np.stack((*state,theta))[:,0])
    return np.stack(saved),dict(noise_rng=canonical_digest(random.bit_generator.state),mode=mode,shift=shift.tolist(),
        theta_start_zero=True,theta_writing=enabled,gain=.2,rho=.002,lam=.001 if enabled else 0.,sigma=.3,
        incoming_packet_access=False,guide_access=False,target_labels=False)


def descendant(packet,index,life,generation,kind,guide,cfg=CONFIG,*,rescue_packet=None):
    validate_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or type(generation) is not int or not 1<=generation<=3 or kind not in KINDS:
        raise ValueError('declared descendant required')
    needs_backup=kind=='rescue' and generation==1
    if needs_backup!=(rescue_packet is not None):raise ValueError('backup only at declared first-generation rescue')
    selected,score,selection=route(packet,kind,guide)
    if needs_backup:backup,backup_score,backup_selection=route(rescue_packet,'learned',guide)
    else:backup,backup_score,backup_selection=None,np.zeros((2,16,16)),None
    ctx=context(index);read,rm=read_selected(selected,ctx,rng(index,life,f'g{generation}:birth'),
        rng(index,life,f'g{generation}:read'),cfg,kind!='read_off',backup)
    shift=np.asarray(divmod(int(rng(index,life,f'g{generation}:source_shift').integers(1,256)),16),dtype=np.int64)
    write,wm=write_streams(read[-1],ctx,rng(index,life,f'g{generation}:source_write'),
        'aligned' if kind=='aligned' else 'translated',shift,cfg,kind not in ('copy','write_off'))
    output=packet if kind=='copy' else encode(np.zeros((16,16))) if kind=='write_off' else encode(record(write[-1,2]))
    raw=dict(read_states=read,write_states=write,routed=np.frombuffer(selected,np.uint8),
        backup_routed=np.frombuffer(backup if needs_backup else bytes(2048),np.uint8),
        scores=np.stack((score,backup_score)),outgoing=np.frombuffer(output,np.uint8),shift=shift)
    meta=dict(generation=generation,kind=kind,input_sha256=hashlib.sha256(packet).hexdigest(),
        output_sha256=hashlib.sha256(output).hexdigest(),rescue_input_sha256=hashlib.sha256(rescue_packet).hexdigest() if needs_backup else None,
        selector=selection,backup_selector=backup_selection,reader=rm,writer=wm,ordinary_packet_bytes=2048,
        extra_backup_bytes=2048 if needs_backup else 0,erased_before_writing=True,record_enabled=kind not in ('copy','write_off'),
        copied_input=kind=='copy',host_guide_bytes=4096,guide_inherited=False)
    return raw,meta


def simulate_life(index,life,guide,cfg=CONFIG,order=CASES):
    if len(order)!=len(CASES) or set(order)!=set(CASES):raise ValueError('complete unique condition order required')
    previous.guide_bytes(guide)
    raw,meta=generate_founders(index,life,cfg);ctx=context(index)
    founders=[[encode(raw['written_fields'][r,mi]) for mi in (0,1)] for r in (0,1)]
    lesions=np.stack([rng(index,life,f'lesion:{r}').permutation(256) for r in (0,1)])
    permutations=np.stack([rng(index,life,f'terminal_shuffle:{r}').permutation(256) for r in (0,1)])
    initial={}
    for r,k in CASES:
        b=founders[1-r][0] if k=='wrong' else founders[r][1] if k=='aligned' else founders[r][0]
        if k in ('lesion','rescue'):b=encode(decode(b).ravel()[lesions[r]].reshape(16,16))
        initial[r,k]=b
    paths={};records={}
    for r,k in order:
        packet=initial[r,k];rows=[];entries=[];incoming=[]
        for g in range(1,4):
            incoming.append(np.frombuffer(packet,np.uint8))
            row,entry=descendant(packet,index,life,g,k,guide,cfg,
                rescue_packet=founders[r][0] if k=='rescue' and g==1 else None)
            rows.append(row);entries.append(entry);packet=row['outgoing'].tobytes()
        paths[r,k]={key:np.stack([x[key] for x in rows]) for key in rows[0]}|dict(incoming=np.stack(incoming))
        records[r,k]=entries
    last={c:paths[c]['outgoing'][-1].tobytes() for c in CASES}
    terminal_shift=np.asarray(divmod(int(rng(index,life,'terminal:shift').integers(1,256)),16),dtype=np.int64)
    prepared={c:route(b,c[1],guide) for c,b in last.items()};terminal_inputs=last.copy()
    for r in (0,1):
        shuffle=lambda b:encode(decode(b).ravel()[permutations[r]].reshape(16,16))
        ideal=encode(ctx['api']['original'].project_theta(np.tanh(1.5*raw['targets'][r]),cfg.norm))
        shifted=previous.previous.shift_packet(ideal,terminal_shift,False)
        extra=dict(learned_shuffle=shuffle(prepared[r,'learned'][0]),shuffle_learned=shuffle(last[r,'learned']),
            ideal=ideal,ideal_shifted=shifted,ideal_learned=shifted,zero=encode(np.zeros((16,16))))
        for k,b in extra.items():terminal_inputs[r,k]=b;prepared[r,k]=route(b,k,guide)
    terminal={c:read_selected(prepared[c][0],ctx,rng(index,life,'terminal:birth'),
        rng(index,life,'terminal:read'),cfg,True,times=cfg.times) for c in PROBES}
    read_states=np.stack([paths[c]['read_states'] for c in CASES]);probe_states=np.stack([terminal[c][0] for c in PROBES])
    raw.update(guide=guide.copy(),lesion_permutations=lesions,terminal_permutations=permutations,
        incoming=np.stack([paths[c]['incoming'] for c in CASES]),routed=np.stack([paths[c]['routed'] for c in CASES]),
        backup_routed=np.stack([paths[c]['backup_routed'] for c in CASES]),outgoing=np.stack([paths[c]['outgoing'] for c in CASES]),
        generation_shifts=paths[CASES[0]]['shift'].copy(),generation_read_states=read_states,
        generation_write_states=np.stack([paths[c]['write_states'] for c in CASES]),
        generation_scores=np.stack([paths[c]['scores'] for c in CASES]),terminal_shift=terminal_shift,
        terminal_inputs=np.stack([np.frombuffer(terminal_inputs[c],np.uint8) for c in PROBES]),
        terminal_packets=np.stack([np.frombuffer(prepared[c][0],np.uint8) for c in PROBES]),
        terminal_scores=np.stack([prepared[c][1] for c in PROBES]),terminal_states=probe_states,
        values=previous.previous.parent.observations(read_states,raw['targets'],CASES,cfg),
        terminal_values=previous.previous.parent.observations(probe_states,raw['targets'],PROBES,cfg))
    meta.update(cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],
        times=list(cfg.times),read_times=list(cfg.read_times),source_times=list(cfg.source_times),parent_times=list(cfg.parent_times),
        generations=[records[c] for c in CASES],terminal=[dict(selector=prepared[c][2],reader=terminal[c][1]) for c in PROBES],
        guide_sha256=hashlib.sha256(previous.guide_bytes(guide)).hexdigest(),host_guide_bytes=4096,ordinary_packet_bytes=2048,
        rescue_g1_extra_bytes=2048,fresh_founders=True,reused_source_starts=False,guide_refitted=False,
        guide_inherited=False,target_labels_in_descendants=False,renewal_generations=3,transfer_interfaces_including_probe=4)
    return raw,meta


def execute_block(index,cfg=CONFIG,root=DEFAULT_EXTERNAL_ROOT,guide=None):
    validate_index(index);guide=load_guide(root) if guide is None else guide
    rows=[];records=[];audit=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,guide,cfg)
        meta['replay']=audit.check_life(raw,meta,cfg,guide,True)
        rows.append(raw);records.append(meta)
    return {k:np.stack([x[k] for x in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),
        guide_sha256=hashlib.sha256(previous.guide_bytes(guide)).hexdigest(),lives=records)


def bridge_source(root=DEFAULT_EXTERNAL_ROOT):
    from .l15_repair_speed_run import load_npz
    return load_npz(root/'tmp'/(previous.RUN_ID+'_benchmark')/f'block_{previous.DISPOSABLE}.npz')


def source_bridge(root=DEFAULT_EXTERNAL_ROOT):
    known=bridge_source(root);cfg=previous.CONFIG;index=previous.DISPOSABLE;guide=load_guide(root)
    raw,meta=generate_founders(index,0,cfg,previous.TAG);ctx=context(index)
    for key in raw:np.testing.assert_array_equal(raw[key],known[key][0])
    writes=[[write_streams(raw['source_starts'][r],ctx,previous.rng(index,0,'source_write'),mode,raw['source_shift'],cfg)
        for mode in ('translated','aligned')] for r in (0,1)]
    paths=np.stack([np.stack([x[0] for x in row]) for row in writes])
    np.testing.assert_array_equal(paths,known['source_states'][0])
    cases=tuple((r,k) for r in (0,1) for k in ('native','learned','supplied','aligned','wrong_guide','ideal','zero'))
    supplied=[known['packets'][0,previous.CASES.index(c)].tobytes() for c in cases]
    reads=[read_selected(b,ctx,previous.rng(index,0,'birth'),previous.rng(index,0,'read'),cfg,True,times=cfg.times) for b in supplied]
    states=np.stack([x[0] for x in reads]);np.testing.assert_array_equal(states,known['states'][0,[previous.CASES.index(c) for c in cases]])
    raw.update(bridge_write_states=paths,bridge_packets=np.stack([np.frombuffer(b,np.uint8) for b in supplied]),bridge_states=states)
    meta.update(bridge_cases=[list(c) for c in cases],bridge_writers=[[x[1] for x in row] for row in writes],
        bridge_readers=[x[1] for x in reads],known_outcomes=True,new_futures=0,qualification_pool=False,
        guide_sha256=hashlib.sha256(previous.guide_bytes(guide)).hexdigest())
    meta['replay']=checker().check_bridge(raw,meta,known)
    return raw,meta


def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8:raise ValueError('eight equal test blocks required')
    v=np.stack([b['values'] for b in blocks]);q=np.stack([b['terminal_values'] for b in blocks])
    if v.shape!=(8,cfg.lives,22,3,len(cfg.read_times),12) or q.shape!=(8,cfg.lives,34,len(cfg.times),12):
        raise ValueError('complete serial observation panel required')
    if not np.isfinite(v).all() or not np.isfinite(q).all():raise ValueError('finite panel required')
    draws=rng(0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        for stage in (1,2,3,4):
            obs=v[:,:,:,stage-1,-1] if stage<4 else q[:,:,:,-1]
            cases=CASES if stage<4 else PROBES;pref=obs[...,col]-obs[...,col+1]
            for left,right in PAIRS+(TERMINAL_PAIRS if stage==4 else ()):
                effects=[pref[:,:,cases.index((r,left))]-pref[:,:,cases.index((r,right))] for r in (0,1)]
                for role,e in ((0,effects[0]),(1,effects[1]),('both',sum(effects)/2)):
                    rows.append(dict(name=left+'_minus_'+right,stage=stage,role=role,observer=observer,
                        **previous.acquisition.capacity.native.contrast_stats(e,draws)))
    get=lambda name,stage=4,role='both':next(x for x in rows if (x['name'],x['stage'],x['role'],x['observer'])==(name,stage,role,'qualified'))
    positive=lambda row:row['pointwise_block_bootstrap_95'][0]>0
    directional=lambda name,stage=4:all(get(name,stage,r)['mean']>0 for r in (0,1))
    supported=lambda name,stage=4:positive(get(name,stage)) and directional(name,stage)
    disagreement=[[int(np.count_nonzero(b['targets'][l,0]!=b['targets'][l,1])) for l in range(cfg.lives)] for b in blocks]
    gates=[get(name,role=r) for name in ('ideal_minus_zero','copy_minus_zero') for r in (0,1)]
    readable=bool(all(positive(x) for x in gates) and np.all(np.asarray(disagreement)>0))
    calibration=bool(readable and all(positive(get('ideal_learned_minus_ideal_shifted',role=r)) for r in (0,1)))
    continuity={name:bool(readable and all(supported('learned_minus_'+name,s) for s in (2,3,4))) for name in ('read_off','write_off')}
    content=bool(readable and all(positive(get('learned_minus_zero',role=r)) for r in (0,1))
        and supported('learned_minus_learned_shuffle') and supported('learned_minus_shuffle_learned'))
    interventions={name:bool(readable and supported(name)) for name in ('learned_minus_wrong','learned_minus_lesion','rescue_minus_lesion','learned_minus_wrong_guide')}
    primary=get('learned_minus_native');directions=[get('learned_minus_native',role=r) for r in (0,1)]
    gain=supported('learned_minus_native');harm=primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions)
    renewal=bool(all(continuity.values()) and content and all(interventions.values()))
    label=('READOUT_NOT_QUALIFIED' if not readable else 'GUIDE_CALIBRATION_NOT_QUALIFIED' if not calibration else
        'LEARNED_SERIAL_RENEWAL_QUALIFIED' if gain and renewal else 'LEARNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION' if gain else
        'LEARNED_HARM_DETECTED' if harm else 'SERIAL_EFFECT_UNRESOLVED')
    return dict(schema='l20_guide_renewal_v1',label=label,primary=primary,directional_primary=directions,
        readout_qualified=readable,readout_gates=gates,calibration_qualified=calibration,continuity_qualified=continuity,
        content_qualified=content,interventions_qualified=interventions,renewal_controls_qualified=renewal,
        contrasts=rows,target_disagreement_cells=disagreement,cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],
        read_times=list(cfg.read_times),times=list(cfg.times),metrics=list(METRICS),
        generation_cell_means=v.mean(axis=(0,1)).tolist(),terminal_cell_means=q.mean(axis=(0,1)).tolist(),
        test_blocks=list(TISSUES),training_blocks=list(previous.TRAINING),blocks=8,lives_per_block=cfg.lives,
        renewal_generations=3,transfer_interfaces_including_probe=4,generation_paths=8*cfg.lives*66,
        terminal_paths=8*cfg.lives*34,packet_bytes=2048,public_guide_bytes=4096,rescue_g1_extra_bytes=2048,
        guide_sha256=GUIDE_SHA256,new_guide_fits=0,fresh_founders=True,reused_source_starts=False,
        conditional_on_one_fitted_guide=True,supplied_groups_and_frame=True,unseen_pattern_families=False,
        learned_ontology=False,native_renewal_necessity=False,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l20_guide_renewal_v1',decision='D132',law='L20/L17',run_id=RUN_ID,control_id=CONTROL_ID,
        tag=TAG,config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,
        guide_source_run=previous.RUN_ID,guide_source_training=previous.TRAIN_ID,guide_sha256=GUIDE_SHA256,
        cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],metrics=list(METRICS),
        times=list(CONFIG.times),read_times=list(CONFIG.read_times),source_times=list(CONFIG.source_times),parent_times=list(CONFIG.parent_times),
        main_parent_acquisitions=64,main_pre_readers=64,main_founder_source_writers=128,
        main_generation_paths=2112,main_generation_writer_phases=2112,main_enabled_generation_rewrites=1728,
        main_terminal_paths=1088,selector_decisions=2496,selector_scores=1277952,
        generation_path_aliases=352,read_only_aliases=128,rescue_prefix_aliases=64,terminal_aliases=192,exact_alias_checks=736,
        new_guide_fits=0,packet_bytes=2048,public_guide_bytes=4096,guide_inherited=False,rescue_g1_extra_bytes=2048,
        fresh_founders=True,reused_source_starts=False,renewal_generations=3,transfer_interfaces_including_probe=4,
        conditional_on_one_fitted_guide=True,supplied_groups_and_frame=True,unseen_pattern_families=False,learned_ontology=False,
        ordinary_incoming_erased_before_writing=True,writer_packet_access=False,writer_guide_access=False,
        record_rule='project(tanh(R_final), .3)',writer_off='theta adaptation disabled and output exact zero',
        copy='theta adaptation disabled; original incoming bytes explicitly retained and copied',
        primary='terminal qualified learned-minus-native preference; two roles within life, four lives within eight blocks',
        positive='readout/calibration; primary lower95>0 and both direction means>0; all continuity, content and intervention controls',
        continuity='learned-read_off and learned-write_off at G2,G3,terminal: pooled lower95>0 and both means>0',
        content='both terminal learned-zero directional lower95>0; learned-postshuffle and learned-preshuffle correction pooled lower95>0 and both means>0',
        interventions='terminal learned-wrong,learned-lesion,rescue-lesion,learned-wrong_guide: pooled lower95>0 and both means>0',
        readout='both terminal ideal-zero and copy-zero directional lower95>0; distinct targets',
        calibration='both terminal ideal_learned-ideal_shifted directional lower95>0',
        uncertainty='10000 whole-test-block pointwise percentile95; conditional on the fixed D131 guide',
        contrasts=294,primary_rows=1,secondary_rows=293,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False,state_atol=1e-10,metric_atol=1e-12,
        automatic_retry=False,automatic_follow_on=False)
