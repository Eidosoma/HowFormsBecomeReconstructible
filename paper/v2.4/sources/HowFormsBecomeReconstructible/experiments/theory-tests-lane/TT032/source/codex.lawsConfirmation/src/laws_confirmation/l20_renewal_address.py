"""D134: matched writer-only addressing from retained D132 renewal states."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import numpy as np
from . import l20_guide_renewal as old
from .l20_three_rewrite import observations
from .io import DEFAULT_EXTERNAL_ROOT, sha256_file

WS=old.WS
RUN_ID='l20_renewal_address_v1_attempt1'
TAG='l20-renewal-address-v1'
TISSUES=tuple(range(74000,74008)); DISPOSABLE=514234
MODES=('translated','aligned')
KINDS=MODES+tuple(m+'_'+k for k in ('pre_shuffle','post_shuffle','off','wrong') for m in MODES)+('ideal','zero')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
PAIRS=(('aligned','translated'),)+tuple((m,m+'_'+k) for m in MODES for k in ('pre_shuffle','post_shuffle','off','wrong'))+tuple((m,'zero') for m in MODES)+(('ideal','zero'),)
METRICS=old.METRICS
SCIENCE=('src/laws_confirmation/l20_renewal_address.py','src/laws_confirmation/l20_renewal_address_run.py',
    'scripts/audit_l20_renewal_address_outputs.py','tests/test_l20_renewal_address.py',
    'scripts/run_l20_renewal_address.sh','protocols/L20_RENEWAL_ADDRESS_V1.md')
SOURCE_KEYS=('targets','guide','generation_shifts','generation_read_states','generation_write_states','outgoing')

@dataclass(frozen=True)
class Config:
    lives:int=4
    steps:int=300
    norm:float=.3
    amp_threshold:float=.2
    def __post_init__(self):
        if type(self.lives) is not int or not 1<=self.lives<=4 or type(self.steps) is not int or self.steps<2:
            raise ValueError('declared lives and reader steps required')
        if (self.norm,self.amp_threshold)!=(.3,.2):raise ValueError('fixed writer norm/observer required')
    @property
    def times(self):return tuple(sorted({0,1,min(100,self.steps),self.steps}))

CONFIG=Config()
api,context,encode,decode=old.api,old.context,old.encode,old.decode

def source_index(index):
    if type(index) is not int or index not in TISSUES+(DISPOSABLE,):raise ValueError('declared main/disposable index required')
    return 514232 if index==DISPOSABLE else index-1000

def source_paths(index,root=DEFAULT_EXTERNAL_ROOT):
    si=source_index(index);d=root/('tmp' if index==DISPOSABLE else 'outputs')/(old.RUN_ID+'_benchmark' if index==DISPOSABLE else old.RUN_ID)
    return d/f'block_{si}.npz',d/f'block_{si}.json'

def load_source(index,root=DEFAULT_EXTERNAL_ROOT):
    from .l15_repair_speed_run import read_json
    a,b=source_paths(index,root)
    with np.load(a,allow_pickle=False) as z:raw={k:z[k] for k in SOURCE_KEYS}
    meta=read_json(b);assert meta['index']==source_index(index) and len(meta['lives'])==4
    assert raw['generation_read_states'].shape==(4,22,3,5,3,16,16)
    assert raw['generation_write_states'].shape==(4,22,3,4,4,16,16)
    assert raw['generation_shifts'].shape==(4,3,2) and raw['generation_shifts'].dtype==np.int64
    assert raw['outgoing'].shape==(4,22,3,2048) and raw['outgoing'].dtype==np.uint8
    assert raw['targets'].shape==raw['guide'].shape==(4,2,16,16)
    assert all(np.isfinite(x).all() for x in raw.values())
    for g in raw['guide']:assert hashlib.sha256(g.astype('<f8').tobytes()).hexdigest()==old.GUIDE_SHA256
    return raw,meta

def rng(index,life,phase):return old.generator(TAG,index,life,phase)

def checker():
    spec=importlib.util.spec_from_file_location('d134_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def write(start,index,life,generation,mode,shift):
    si=source_index(index)
    if type(life) is not int or not 0<=life<4 or type(generation) is not int or generation not in (1,2,3) or mode not in MODES:
        raise ValueError('declared life/stage/writer mode required')
    if not isinstance(start,np.ndarray) or start.shape!=(3,16,16) or start.dtype!=np.float64 or not np.isfinite(start).all():
        raise ValueError('finite V/EMA/R start required')
    if not isinstance(shift,np.ndarray) or shift.shape!=(2,) or shift.dtype!=np.int64 or not np.all((shift>=0)&(shift<16)) or not shift.any():
        raise ValueError('original nonzero toroidal shift required')
    return old.write_streams(start,context(si),old.rng(si,life,f'g{generation}:source_write'),mode,shift)

def read_packet(packet,index,life,generation,cfg=CONFIG,enabled=True):
    source_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or type(generation) is not int or generation not in (1,2,3):
        raise ValueError('declared reader life/stage required')
    return old.read_selected(packet,context(index),rng(index,life,f'g{generation}:birth'),
        rng(index,life,f'g{generation}:read'),cfg,enabled,times=cfg.times)

def simulate_life(index,life,source,cfg=CONFIG,order=CASES):
    source_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or len(order)!=len(CASES) or set(order)!=set(CASES):
        raise ValueError('complete unique condition panel required')
    targets=source['targets'][life].copy();guide=source['guide'][life].copy()
    ci=[old.CASES.index((r,'learned')) for r in (0,1)]
    starts=source['generation_read_states'][life,ci,:,-1].copy()
    shifts=source['generation_shifts'][life].copy()
    writes=[[[write(starts[r,g],index,life,g+1,m,shifts[g]) for m in MODES] for g in range(3)] for r in (0,1)]
    paths=np.stack([[np.stack([x[0] for x in row]) for row in role] for role in writes])
    np.testing.assert_array_equal(paths[:,:,0],source['generation_write_states'][life,ci])
    fields=np.stack([[np.stack([old.record(ref) for ref in row]) for row in role] for role in paths[:,:,:,-1,2]])
    for r in (0,1):
        for g in range(3):assert encode(fields[r,g,0])==source['outgoing'][life,ci[r],g].tobytes()
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
    raw=dict(targets=targets,guide=guide,source_starts=starts,source_shifts=shifts,source_states=paths,
        written_fields=fields,permutations=perms,inputs=np.stack([inputs[c] for c in CASES]),
        packets=np.stack([[np.frombuffer(b,np.uint8) for b in packets[c]] for c in CASES]),
        scores=np.stack([scores[c] for c in CASES]),states=states,
        values=observations(states,targets,CASES,cfg))
    ctx=context(index);sctx=context(source_index(index))
    meta=dict(index=index,source_index=source_index(index),life=life,config=asdict(cfg),tag=TAG,
        cases=[list(c) for c in CASES],modes=list(MODES),times=list(cfg.times),source_times=[0,1,300,1000],
        source_context=dict(index=source_index(index),tissue=asdict(sctx['tissue']),ladder=asdict(sctx['ladder']),blueprint=asdict(sctx['bp'])),
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        writers=[[[x[1] for x in row] for row in role] for role in writes],
        selectors=[selections[c] for c in CASES],readers=[[x[1] for x in reads[c]] for c in CASES],
        source_noise_reused=True,source_starts_reused=True,translated_exact_replay=True,
        fresh_founders=False,new_renewal_cohort=False,guide_refitted=False,latent_theta_transmitted=False,
        guide_sha256=old.GUIDE_SHA256,public_guide_bytes=4096,packet_bytes=2048,
        writer_rule='project(tanh(R_final), .3)',writer_inputs=['R_final'],target_labels_in_writer=False)
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
    if v.shape!=(8,cfg.lives,24,3,len(cfg.times),12) or not np.isfinite(v).all():raise ValueError('complete finite panel required')
    draws=rng(0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        pref=v[...,-1,col]-v[...,-1,col+1]
        for stage in ('all',1,2,3):
            for a,b in PAIRS:
                e=[pref[:,:,CASES.index((r,a))]-pref[:,:,CASES.index((r,b))] for r in (0,1)]
                e=[x.mean(axis=-1) if stage=='all' else x[...,stage-1] for x in e]
                for role,x in ((0,e[0]),(1,e[1]),('both',sum(e)/2)):
                    rows.append(dict(name=a+'_minus_'+b,stage=stage,role=role,observer=observer,
                        **old.previous.acquisition.capacity.native.contrast_stats(x,draws)))
    pick=lambda n,r='both':next(x for x in rows if (x['name'],x['stage'],x['role'],x['observer'])==(n,'all',r,'qualified'))
    good=lambda n,r='both':pick(n,r)['pointwise_block_bootstrap_95'][0]>0
    supported=lambda n:good(n) and all(pick(n,r)['mean']>0 for r in (0,1))
    disagreement=[[int(np.count_nonzero(b['targets'][l,0]!=b['targets'][l,1])) for l in range(cfg.lives)] for b in blocks]
    instrument=bool(all(good('ideal_minus_zero',r) for r in (0,1)) and np.all(np.asarray(disagreement)>0))
    content={m:bool(instrument and all(good(m+'_minus_zero',r) for r in (0,1)) and
        all(supported(m+'_minus_'+m+'_'+k) for k in ('pre_shuffle','post_shuffle'))) for m in MODES}
    primary=pick('aligned_minus_translated');directions=[pick('aligned_minus_translated',r) for r in (0,1)]
    gain=content['aligned'] and supported('aligned_minus_translated')
    harm=content['translated'] and primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions)
    label='READOUT_NOT_QUALIFIED' if not instrument else 'ALIGNED_RENEWAL_WRITER_ADVANTAGE' if gain else 'TRANSLATED_RENEWAL_WRITER_ADVANTAGE' if harm else 'RENEWAL_ADDRESS_EFFECT_UNRESOLVED'
    return dict(schema='l20_renewal_address_v1',label=label,primary=primary,directional_primary=directions,
        readout_qualified=instrument,content_qualified=content,contrasts=rows,target_disagreement_cells=disagreement,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(METRICS),cell_means=v.mean(axis=(0,1)).tolist(),
        test_blocks=list(TISSUES),source_blocks=list(range(73000,73008)),blocks=8,lives_per_block=cfg.lives,
        stage_count=3,source_pairs=8*cfg.lives*6,known_source_writers=8*cfg.lives*6,new_aligned_writers=8*cfg.lives*6,
        reader_paths=8*cfg.lives*72,selector_decisions=8*cfg.lives*60,packet_bytes=2048,public_guide_bytes=4096,
        guide_sha256=old.GUIDE_SHA256,new_guide_fits=0,source_noise_reused=True,source_starts_reused=True,
        new_renewal_cohort=False,fresh_founders=False,conditional_on_one_fitted_guide=True,
        supplied_groups_and_frame=True,learned_ontology=False,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False,automatic_successor=False)

def contract():
    return dict(schema='l20_renewal_address_v1',decision='D134',run_id=RUN_ID,tag=TAG,config=asdict(CONFIG),
        test_blocks=list(TISSUES),disposable=DISPOSABLE,source_run=old.RUN_ID,source_blocks=list(range(73000,73008)),
        source_disposable=514232,modes=list(MODES),cases=[list(c) for c in CASES],pairs=[list(p) for p in PAIRS],
        source_checkpoint='learned read300',source_steps=1000,source_times=[0,1,300,1000],
        source_pairs=192,known_source_writers=192,new_aligned_writers=192,reader_paths=2304,selector_decisions=1920,
        source_noise_reused=True,source_starts_reused=True,new_renewal_cohort=False,
        source_gain=.2,source_rho=.002,source_lambda=.001,source_sigma=.3,writer_theta_erased=True,
        writer_rule='project(tanh(R_final), .3)',packet_bytes=2048,public_guide_bytes=4096,
        guide_sha256=old.GUIDE_SHA256,new_guide_fits=0,reader_steps=300,reader_gain=0.,reader_writing=False,
        primary='all-stage terminal qualified aligned-minus-translated preference',
        positive='instrument and aligned content, primary lower95>0, both directional means>0',
        negative='instrument and translated content, primary upper95<0, both directional means<0',
        content='both intact-zero directional lower95>0; pre/post shuffle pooled lower95>0 and both means>0',
        uncertainty='10000 whole-block percentile draws; average stages and roles within lives then blocks',
        absolute_fidelity_gate=None,equivalence_test=False,automatic_retry=False,automatic_successor=False)
