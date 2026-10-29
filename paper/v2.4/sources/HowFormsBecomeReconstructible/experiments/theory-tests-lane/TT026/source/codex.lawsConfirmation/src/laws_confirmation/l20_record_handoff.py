"""D139: record-stage by reference-correction interaction, saved writers/new readers."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import numpy as np
from . import l20_guide_renewal as old
from . import l20_reference_handoff as source_model
from .l20_three_rewrite import observations
from .io import DEFAULT_EXTERNAL_ROOT, sha256_file

WS=old.WS
RUN_ID='l20_record_handoff_v1_attempt1'
TAG='l20-record-handoff-v1'
TISSUES=tuple(range(77000,77008)); DISPOSABLE=514239
CELLS=(('instant','reference'),('instant','matched'),('theta','reference'),('theta','matched'))
MODES=tuple(a+'_'+b for a,b in CELLS)
KINDS=MODES+tuple(m+'_'+k for k in ('pre_shuffle','post_shuffle','off','wrong') for m in MODES)+('ideal','zero')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
PAIRS=(('theta_matched','theta_reference'),('instant_matched','instant_reference'),
    ('theta_matched','instant_matched'),('theta_reference','instant_reference'))+tuple(
    (m,m+'_'+k) for m in MODES for k in ('pre_shuffle','post_shuffle','off','wrong'))+tuple((m,'zero') for m in MODES)+(('ideal','zero'),)
INTERACTION={'theta_matched':1,'theta_reference':-1,'instant_matched':-1,'instant_reference':1}
SPECIAL={'record_correction_interaction':INTERACTION,
    'pooled_theta_minus_instant':{'theta_matched':.5,'theta_reference':.5,'instant_matched':-.5,'instant_reference':-.5}}
for kind in ('pre_shuffle','post_shuffle'):
    SPECIAL[kind+'_specificity_interaction']=INTERACTION|{k+'_'+kind:-v for k,v in INTERACTION.items()}
CONTRASTS={a+'_minus_'+b:{a:1,b:-1} for a,b in PAIRS}|SPECIAL
METRICS=old.METRICS
SCIENCE=('src/laws_confirmation/l20_record_handoff.py','src/laws_confirmation/l20_record_handoff_run.py',
    'scripts/audit_l20_record_handoff_outputs.py','tests/test_l20_record_handoff.py',
    'scripts/run_l20_record_handoff.sh','protocols/L20_RECORD_HANDOFF_V1.md')
SOURCE_KEYS=('targets','guide','source_states','written_fields')

@dataclass(frozen=True)
class Config:
    lives:int=4
    steps:int=300
    norm:float=.3
    amp_threshold:float=.2
    def __post_init__(self):
        if type(self.lives) is not int or not 1<=self.lives<=4 or type(self.steps) is not int or self.steps<2:
            raise ValueError('declared lives and reader steps required')
        if (self.norm,self.amp_threshold)!=(.3,.2):raise ValueError('fixed record norm/observer required')
    @property
    def times(self):return tuple(sorted({0,1,min(100,self.steps),self.steps}))

CONFIG=Config()
api,context,encode,decode=old.api,old.context,old.encode,old.decode

def source_index(index):
    if type(index) is not int or index not in TISSUES+(DISPOSABLE,):raise ValueError('declared main/disposable index required')
    return 514237 if index==DISPOSABLE else index-1000

def source_paths(index,root=DEFAULT_EXTERNAL_ROOT):
    si=source_index(index)
    directory=root/('tmp' if index==DISPOSABLE else 'outputs')/(source_model.RUN_ID+'_benchmark' if index==DISPOSABLE else source_model.RUN_ID)
    return directory/f'block_{si}.npz',directory/f'block_{si}.json'

def load_source(index,root=DEFAULT_EXTERNAL_ROOT):
    from .l15_repair_speed_run import read_json
    a,b=source_paths(index,root)
    with np.load(a,allow_pickle=False) as z:raw={k:z[k] for k in SOURCE_KEYS}
    meta=read_json(b);assert meta['index']==source_index(index) and meta['config']==asdict(source_model.CONFIG) and len(meta['lives'])==4
    assert raw['source_states'].shape==(4,2,3,4,4,4,16,16)
    assert raw['written_fields'].shape==(4,2,3,4,16,16)
    assert raw['targets'].shape==raw['guide'].shape==(4,2,16,16)
    assert all(x.dtype==np.float64 and np.isfinite(x).all() for x in raw.values())
    for g in raw['guide']:assert hashlib.sha256(g.astype('<f8').tobytes()).hexdigest()==old.GUIDE_SHA256
    return raw,meta

def rng(index,life,phase):return old.generator(TAG,index,life,phase)

def checker():
    spec=importlib.util.spec_from_file_location('d139_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def record(field,stage):
    """Only one endpoint field and a declared record rule, never source labels/body."""
    if stage not in ('theta','instant'):raise ValueError('declared record stage required')
    if not isinstance(field,np.ndarray) or field.shape!=(16,16) or field.dtype!=np.float64 or not np.isfinite(field).all():
        raise ValueError('finite float64 endpoint required')
    if stage=='theta':
        if abs(float(field.mean()))>1e-14 or abs(float(field.std())-.3)>1e-14:
            raise ValueError('saved theta must already have declared mean/std; no reprojecting')
        return field.copy()
    if np.tanh(field).std()<=1e-9:raise ValueError('degenerate R record; fail rather than exclude')
    return old.record(field)

def read_packet(packet,index,life,generation,cfg=CONFIG,enabled=True):
    source_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or type(generation) is not int or generation not in (1,2,3):
        raise ValueError('declared reader life/stage required')
    if type(enabled) is not bool:raise ValueError('boolean read switch required')
    return old.read_selected(packet,context(index),rng(index,life,f'g{generation}:birth'),
        rng(index,life,f'g{generation}:read'),cfg,enabled,times=cfg.times)

def simulate_life(index,life,source,cfg=CONFIG,order=CASES):
    source_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or len(order)!=len(CASES) or set(order)!=set(CASES):
        raise ValueError('complete unique condition panel required')
    targets=source['targets'][life].copy();guide=source['guide'][life].copy()
    endpoints=source['source_states'][life,:,:,:2,-1].copy()
    fields=np.stack([[np.stack([record(endpoints[r,g,('reference','matched').index(h),3 if stage=='theta' else 2],stage)
        for stage,h in CELLS]) for g in range(3)] for r in (0,1)])
    for r in (0,1):
        for g in range(3):
            for hi in (0,1):assert encode(fields[r,g,hi])==encode(source['written_fields'][life,r,g,hi])
    perms=np.stack([[rng(index,life,f'g{g}:shuffle:{r}').permutation(256) for g in (1,2,3)] for r in (0,1)])
    inputs={};packets={};scores={};selections={}
    for r,k in CASES:
        ins=[];bs=[];ss=[];ms=[]
        for g in range(3):
            if k in ('ideal','zero'):
                field=old.record(1.5*targets[r]) if k=='ideal' else np.zeros((16,16))
                incoming=encode(field);b=incoming;score=np.zeros((2,16,16));selection=None
            else:
                mode=next(m for m in MODES if k==m or k.startswith(m+'_'))
                role=1-r if k.endswith('_wrong') else r
                incoming=encode(fields[role,g,MODES.index(mode)])
                shuffle=lambda b:encode(decode(b).ravel()[perms[r,g]].reshape(16,16))
                if k.endswith('_pre_shuffle'):incoming=shuffle(incoming)
                b,score,selection=old.route(incoming,'learned',guide)
                if k.endswith('_post_shuffle'):b=shuffle(b)
            ins.append(np.frombuffer(incoming,np.uint8));bs.append(b);ss.append(score);ms.append(selection)
        inputs[r,k]=np.stack(ins);packets[r,k]=bs;scores[r,k]=np.stack(ss);selections[r,k]=ms
    reads={c:[read_packet(packets[c][g],index,life,g+1,cfg,not c[1].endswith('_off')) for g in range(3)] for c in order}
    states=np.stack([np.stack([x[0] for x in reads[c]]) for c in CASES])
    raw=dict(targets=targets,guide=guide,source_endpoints=endpoints,written_fields=fields,
        permutations=perms,inputs=np.stack([inputs[c] for c in CASES]),
        packets=np.stack([[np.frombuffer(b,np.uint8) for b in packets[c]] for c in CASES]),
        scores=np.stack([scores[c] for c in CASES]),states=states,
        values=observations(states,targets,CASES,cfg))
    ctx=context(index)
    meta=dict(index=index,source_index=source_index(index),life=life,config=asdict(cfg),tag=TAG,source_tag=source_model.TAG,
        cases=[list(c) for c in CASES],modes=list(MODES),cells=[list(c) for c in CELLS],times=list(cfg.times),
        source_checkpoint=1000,source_mode_indices=[0,1],source_endpoints_reused=True,new_source_writes=0,
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        selectors=[selections[c] for c in CASES],readers=[[x[1] for x in reads[c]] for c in CASES],
        fresh_founders=False,new_renewal_cohort=False,guide_refitted=False,latent_theta_transmitted=True,
        theta_reprojected=False,source_theta_feedback=True,fresh_reader_streams=True,
        guide_sha256=old.GUIDE_SHA256,public_guide_bytes=4096,packet_bytes=2048,
        record_rule='theta: saved bytes; instant: project(tanh(R_final), .3)',record_inputs=['theta_final','R_final'],
        target_labels_in_record=False,source_correction_uses_archived_birth=True)
    return raw,meta

def execute_block(index,cfg=CONFIG,root=DEFAULT_EXTERNAL_ROOT):
    source,_=load_source(index,root);rows=[];records=[];audit=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,source,cfg)
        meta['replay']=audit.check_life(raw,meta,cfg,source,replay=True)
        rows.append(raw);records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),
        source_sha256={str(x):sha256_file(x) for x in source_paths(index,root)},lives=records)

def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8:raise ValueError('eight complete blocks required')
    v=np.stack([b['values'] for b in blocks])
    if v.shape!=(8,cfg.lives,44,3,len(cfg.times),12) or not np.isfinite(v).all():raise ValueError('complete finite panel required')
    draws=rng(0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        pref=v[...,-1,col]-v[...,-1,col+1]
        for stage in ('all',1,2,3):
            for name,weights in CONTRASTS.items():
                e=[sum(w*pref[:,:,CASES.index((r,k))] for k,w in weights.items()) for r in (0,1)]
                e=[x.mean(axis=-1) if stage=='all' else x[...,stage-1] for x in e]
                for role,x in ((0,e[0]),(1,e[1]),('both',sum(e)/2)):
                    rows.append(dict(name=name,stage=stage,role=role,observer=observer,
                        **old.previous.acquisition.capacity.native.contrast_stats(x,draws)))
    pick=lambda n,r='both':next(x for x in rows if (x['name'],x['stage'],x['role'],x['observer'])==(n,'all',r,'qualified'))
    good=lambda n,r='both':pick(n,r)['pointwise_block_bootstrap_95'][0]>0
    supported=lambda n:good(n) and all(pick(n,r)['mean']>0 for r in (0,1))
    disagreement=[[int(np.count_nonzero(b['targets'][l,0]!=b['targets'][l,1])) for l in range(cfg.lives)] for b in blocks]
    instrument=bool(all(good('ideal_minus_zero',r) for r in (0,1)) and np.all(np.asarray(disagreement)>0))
    content={m:bool(instrument and all(good(m+'_minus_zero',r) for r in (0,1)) and
        all(supported(m+'_minus_'+m+'_'+k) for k in ('pre_shuffle','post_shuffle'))) for m in MODES}
    primary=pick('record_correction_interaction');directions=[pick('record_correction_interaction',r) for r in (0,1)]
    gain=all(content.values()) and supported('record_correction_interaction')
    harm=all(content.values()) and primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions)
    label='READOUT_NOT_QUALIFIED' if not instrument else 'THETA_CORRECTION_INTERACTION_POSITIVE' if gain else 'THETA_CORRECTION_INTERACTION_NEGATIVE' if harm else 'RECORD_CORRECTION_INTERACTION_UNRESOLVED'
    cleanup={s:bool(content[s+'_matched'] and content[s+'_reference'] and supported(s+'_matched_minus_'+s+'_reference')) for s in ('instant','theta')}
    record_gain={h:bool(content['theta_'+h] and content['instant_'+h] and supported('theta_'+h+'_minus_instant_'+h)) for h in ('reference','matched')}
    return dict(schema='l20_record_handoff_v1',label=label,primary=primary,directional_primary=directions,
        readout_qualified=instrument,content_qualified=content,cleanup_benefit_qualified=cleanup,theta_record_benefit_qualified=record_gain,
        contrasts=rows,target_disagreement_cells=disagreement,cases=[list(c) for c in CASES],times=list(cfg.times),
        metrics=list(METRICS),cell_means=v.mean(axis=(0,1)).tolist(),
        test_blocks=list(TISSUES),source_blocks=list(range(76000,76008)),blocks=8,lives_per_block=cfg.lives,
        stage_count=3,source_pairs=8*cfg.lives*6,reused_writer_endpoints=8*cfg.lives*12,new_source_writes=0,
        primary_packets=8*cfg.lives*24,reader_paths=8*cfg.lives*132,selector_decisions=8*cfg.lives*120,
        packet_bytes=2048,public_guide_bytes=4096,guide_sha256=old.GUIDE_SHA256,new_guide_fits=0,
        new_renewal_cohort=False,fresh_founders=False,conditional_on_one_fitted_guide=True,
        supplied_groups_and_frame=True,learned_ontology=False,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False,automatic_successor=False,
        source_checkpoint=1000,theta_reprojected=False,source_theta_feedback=True,
        source_correction_uses_archived_birth=True,interaction_alone_is_not_positive_cleanup_or_theta_advantage=True)

def contract():
    return dict(schema='l20_record_handoff_v1',decision='D139',run_id=RUN_ID,tag=TAG,config=asdict(CONFIG),
        test_blocks=list(TISSUES),disposable=DISPOSABLE,source_run=source_model.RUN_ID,source_blocks=list(range(76000,76008)),
        source_disposable=514237,modes=list(MODES),cells=[list(c) for c in CELLS],cases=[list(c) for c in CASES],
        pairs=[list(p) for p in PAIRS],special_contrasts=SPECIAL,source_checkpoint=1000,source_mode_indices=[0,1],
        source_pairs=192,reused_writer_endpoints=384,primary_packets=768,new_source_writes=0,reader_paths=4224,selector_decisions=3840,
        new_renewal_cohort=False,fresh_founders=False,theta_reprojected=False,source_theta_feedback=True,
        record_rule='theta: saved bytes; instant: project(tanh(R_final), .3)',packet_bytes=2048,public_guide_bytes=4096,
        guide_sha256=old.GUIDE_SHA256,new_guide_fits=0,reader_steps=300,reader_gain=0.,reader_writing=False,
        primary='all-stage terminal qualified (theta_matched-theta_reference)-(instant_matched-instant_reference) preference',
        positive='instrument and all four contents, primary lower95>0, both directional means>0',
        negative='instrument and all four contents, primary upper95<0, both directional means<0',
        content='both intact-zero directional lower95>0; pre/post shuffle pooled lower95>0 and both means>0',
        uncertainty='10000 whole-block percentile draws; average stages and roles within lives then blocks',
        absolute_fidelity_gate=None,equivalence_test=False,automatic_retry=False,automatic_successor=False,
        source_correction_uses_archived_birth=True,known_D124_theta_disadvantage=True,
        interaction_alone_is_not_positive_cleanup_or_theta_advantage=True)
