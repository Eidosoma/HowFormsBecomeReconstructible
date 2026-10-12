"""D141 held-out physics, adapted literally from the frozen D140 implementation.

Founder acquisition is separate from descendant generation. The executor supplies
retained founders only after sealing all forecasts. No development code is edited.
"""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation.l20_three_rewrite import observations

TAG='l20-extension1-heldout-v1'
TISSUES=tuple(range(90000,90016));DISPOSABLE=514240
KINDS=('translated','aligned','copy','aligned_read_off','aligned_write_off','aligned_wrong','aligned_lesion','aligned_rescue')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
EXTRAS=('aligned_post_shuffle','aligned_pre_shuffle','ideal','zero')
PROBES=tuple((r,k) for r in (0,1) for k in KINDS+EXTRAS)
PAIRS=(('aligned','translated'),('aligned','copy'),('aligned','aligned_read_off'),('aligned','aligned_write_off'),
    ('aligned','aligned_wrong'),('aligned','aligned_lesion'),('aligned_rescue','aligned_lesion'),('translated','copy'))
TERMINAL_PAIRS=(('aligned','aligned_post_shuffle'),('aligned','aligned_pre_shuffle'),('ideal','zero'),
    ('copy','zero'),('aligned','zero'),('translated','zero'))
FOUNDER_KEYS=('native_theta','theta0','parent_birth','settled','targets','founder_states',
    'founder_packets','pre_states','source_starts','source_shift','source_states','written_fields')
Config=old.Config;CONFIG=old.CONFIG;METRICS=old.METRICS
api,context,encode,decode=old.api,old.context,old.encode,old.decode
load_guide=old.load_guide

def validate_index(index):
    if type(index) is not int or index not in TISSUES+(DISPOSABLE,):raise ValueError('declared fresh main/disposable index required')
    return index

def rng(index,life,phase):return old.generator(TAG,index,life,phase)

def generate_founders(index,life,cfg=CONFIG):
    validate_index(index)
    if type(life) is not int or not 0<=life<cfg.lives:raise ValueError('declared life required')
    random=lambda phase:rng(index,life,phase)
    ctx=context(index);targets=old.previous.acquisition.capacity.target_fields(ctx)
    native,theta,birth,settled,seeds=old.previous.common_parent_streams(ctx,random('parent_birth'),random('parent_settle'),cfg)
    acquired=[old.previous.acquire_streams(settled,theta,targets[r],ctx,random('teaching'),cfg) for r in (0,1)]
    founders=np.stack([x[0] for x in acquired]);incoming=[encode(founders[r,-1,3]) for r in (0,1)]
    before=[old.previous.read_streams(b,ctx,random('source_birth'),random('source_read'),cfg,True) for b in incoming]
    pre=np.stack([x[0] for x in before]);starts=pre[:,-1]
    shift=np.asarray(divmod(int(random('source_shift').integers(1,256)),16),dtype=np.int64)
    writes=[[old.previous.source_path_write(starts[r],ctx,random('source_write'),mode,shift,cfg)
        for mode in ('translated','aligned')] for r in (0,1)]
    paths=np.stack([np.stack([x[0] for x in row]) for row in writes])
    fields=np.stack([np.stack([old.record(ref) for ref in row]) for row in paths[:,:,-1,2]])
    raw=dict(native_theta=native,theta0=theta,parent_birth=birth,settled=settled,targets=targets,
        founder_states=founders,founder_packets=np.stack([np.frombuffer(b,np.uint8) for b in incoming]),
        pre_states=pre,source_starts=starts.copy(),source_shift=shift,source_states=paths,written_fields=fields)
    meta=dict(index=index,life=life,config=asdict(cfg),tag=TAG,**seeds,teaching_rng=[x[1] for x in acquired],
        pre_readers=[x[1] for x in before],writers=[[x[1] for x in row] for row in writes],
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']))
    return raw,meta


def descendant(packet,index,life,generation,kind,guide,cfg=CONFIG,*,rescue_packet=None):
    validate_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or type(generation) is not int or generation not in (1,2,3) or kind not in KINDS:
        raise ValueError('declared descendant life/stage/condition required')
    needs_backup=kind=='aligned_rescue' and generation==1
    if needs_backup!=(rescue_packet is not None):raise ValueError('backup only in declared G1 rescue')
    b,scores,selection=old.route(packet,'learned',guide)
    if needs_backup:backup,bscores,bselection=old.route(rescue_packet,'learned',guide)
    else:backup,bscores,bselection=None,np.zeros((2,16,16)),None
    random=lambda phase:rng(index,life,f'g{generation}:'+phase)
    ctx=context(index);read,rm=old.read_selected(b,ctx,random('birth'),random('read'),cfg,kind!='aligned_read_off',backup)
    shift=np.asarray(divmod(int(random('source_shift').integers(1,256)),16),np.int64)
    mode='translated' if kind in ('translated','copy') else 'aligned'
    enabled=kind not in ('copy','aligned_write_off')
    write,wm=old.write_streams(read[-1],ctx,random('source_write'),mode,shift,cfg,enabled)
    output=packet if kind=='copy' else bytes(2048) if kind=='aligned_write_off' else encode(old.record(write[-1,2]))
    raw=dict(read_states=read,write_states=write,routed=np.frombuffer(b,np.uint8),
        backup_routed=np.frombuffer(backup if needs_backup else bytes(2048),np.uint8),
        outgoing=np.frombuffer(output,np.uint8),scores=np.stack((scores,bscores)),shift=shift)
    meta=dict(generation=generation,kind=kind,input_sha256=hashlib.sha256(packet).hexdigest(),
        output_sha256=hashlib.sha256(output).hexdigest(),rescue_input_sha256=hashlib.sha256(rescue_packet).hexdigest() if needs_backup else None,
        selector=selection,backup_selector=bselection,reader=rm,writer=wm,ordinary_packet_bytes=2048,
        extra_backup_bytes=2048 if needs_backup else 0,erased_before_writing=True,record_enabled=enabled,
        copied_input=kind=='copy',host_guide_bytes=4096,guide_inherited=False)
    return raw,meta

def simulate_life(index,life,guide,source,founder_meta,cfg=CONFIG,order=CASES):
    validate_index(index)
    if type(life) is not int or not 0<=life<cfg.lives or len(order)!=len(CASES) or set(order)!=set(CASES):
        raise ValueError('complete unique life/condition panel required')
    guide=guide.copy()
    if hashlib.sha256(old.previous.guide_bytes(guide)).hexdigest()!=old.GUIDE_SHA256:raise ValueError('frozen guide required')
    assert founder_meta['index']==index and founder_meta['life']==life and founder_meta['tag']==TAG
    targets=source['targets'].copy();ctx=context(index)
    founders=[encode(source['written_fields'][r,0]) for r in (0,1)]
    lesions=np.stack([rng(index,life,f'lesion:{r}').permutation(256) for r in (0,1)])
    perms=np.stack([rng(index,life,f'terminal_shuffle:{r}').permutation(256) for r in (0,1)])
    paths={};records={}
    for r,k in order:
        b=founders[1-r] if k=='aligned_wrong' else founders[r]
        if k in ('aligned_lesion','aligned_rescue'):b=encode(decode(b).ravel()[lesions[r]].reshape(16,16))
        rows=[];entries=[];incoming=[]
        for g in (1,2,3):
            incoming.append(np.frombuffer(b,np.uint8))
            row,entry=descendant(b,index,life,g,k,guide,cfg,rescue_packet=founders[r] if k=='aligned_rescue' and g==1 else None)
            rows.append(row);entries.append(entry);b=row['outgoing'].tobytes()
        paths[r,k]={key:np.stack([x[key] for x in rows]) for key in rows[0]}|dict(incoming=np.stack(incoming))
        records[r,k]=entries
    last={c:paths[c]['outgoing'][-1].tobytes() for c in CASES}
    terminal_inputs=last.copy();prepared={c:old.route(b,'learned',guide) for c,b in last.items()}
    for r in (0,1):
        shuffle=lambda b:encode(decode(b).ravel()[perms[r]].reshape(16,16))
        for k,b in dict(aligned_post_shuffle=shuffle(prepared[r,'aligned'][0]),aligned_pre_shuffle=shuffle(last[r,'aligned']),
            ideal=encode(old.record(1.5*targets[r])),zero=bytes(2048)).items():
            terminal_inputs[r,k]=b
            prepared[r,k]=old.route(b,'learned',guide) if k=='aligned_pre_shuffle' else (b,np.zeros((2,16,16)),None)
    terminal={c:old.read_selected(prepared[c][0],ctx,rng(index,life,'terminal:birth'),rng(index,life,'terminal:read'),
        cfg,True,times=cfg.times) for c in PROBES}
    reads=np.stack([paths[c]['read_states'] for c in CASES]);ends=np.stack([terminal[c][0] for c in PROBES])
    raw=dict(targets=targets,guide=guide,founder_packets=np.stack([np.frombuffer(b,np.uint8) for b in founders]),
        lesion_permutations=lesions,terminal_permutations=perms,generation_shifts=paths[CASES[0]]['shift'].copy(),
        incoming=np.stack([paths[c]['incoming'] for c in CASES]),routed=np.stack([paths[c]['routed'] for c in CASES]),
        backup_routed=np.stack([paths[c]['backup_routed'] for c in CASES]),outgoing=np.stack([paths[c]['outgoing'] for c in CASES]),
        generation_read_states=reads,generation_write_states=np.stack([paths[c]['write_states'] for c in CASES]),
        generation_scores=np.stack([paths[c]['scores'] for c in CASES]),terminal_inputs=np.stack([np.frombuffer(terminal_inputs[c],np.uint8) for c in PROBES]),
        terminal_packets=np.stack([np.frombuffer(prepared[c][0],np.uint8) for c in PROBES]),
        terminal_scores=np.stack([prepared[c][1] for c in PROBES]),terminal_states=ends,
        values=observations(reads,targets,CASES,cfg),terminal_values=observations(ends,targets,PROBES,cfg))
    raw.update({'f_'+key:source[key].copy() for key in FOUNDER_KEYS})
    meta=dict(index=index,life=life,config=asdict(cfg),tag=TAG,stream_tag=TAG,founder=founder_meta,
        cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],times=list(cfg.times),read_times=list(cfg.read_times),
        source_times=list(cfg.source_times),generations=[records[c] for c in CASES],
        terminal=[dict(selector=prepared[c][2],reader=terminal[c][1]) for c in PROBES],
        host=dict(index=index,tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp'])),
        guide_sha256=old.GUIDE_SHA256,host_guide_bytes=4096,ordinary_packet_bytes=2048,rescue_g1_extra_bytes=2048,
        fresh_founders=True,reused_founder_packets=False,reused_noise_streams=False,reused_later_states=False,
        reused_source_starts=False,fresh_noise_streams=True,
        guide_refitted=False,guide_inherited=False,target_labels_in_descendants=False,renewal_generations=3)
    return raw,meta

def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=16:raise ValueError('sixteen full fresh-founder blocks required')
    v=np.stack([b['values'] for b in blocks]);q=np.stack([b['terminal_values'] for b in blocks])
    if v.shape!=(16,cfg.lives,16,3,len(cfg.read_times),12) or q.shape!=(16,cfg.lives,24,len(cfg.times),12):
        raise ValueError('complete serial observation panel required')
    if not np.isfinite(v).all() or not np.isfinite(q).all():raise ValueError('finite panel required')
    draws=np.random.default_rng(14120260917).integers(0,16,(10000,16));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        for stage in (1,2,3,4):
            a=v[:,:,:,stage-1,-1] if stage<4 else q[:,:,:,-1];cases=CASES if stage<4 else PROBES
            pref=a[...,col]-a[...,col+1]
            for left,right in PAIRS+(TERMINAL_PAIRS if stage==4 else ()):
                effects=[pref[:,:,cases.index((r,left))]-pref[:,:,cases.index((r,right))] for r in (0,1)]
                for role,e in ((0,effects[0]),(1,effects[1]),('both',sum(effects)/2)):
                    rows.append(dict(name=left+'_minus_'+right,stage=stage,role=role,observer=observer,
                        **old.previous.acquisition.capacity.native.contrast_stats(e,draws)))
    get=lambda n,s=4,r='both':next(x for x in rows if (x['name'],x['stage'],x['role'],x['observer'])==(n,s,r,'qualified'))
    good=lambda n,s=4,r='both':get(n,s,r)['pointwise_block_bootstrap_95'][0]>0
    supported=lambda n,s=4:good(n,s) and all(get(n,s,r)['mean']>0 for r in (0,1))
    dis=[[int(np.count_nonzero(b['targets'][l,0]!=b['targets'][l,1])) for l in range(cfg.lives)] for b in blocks]
    instrument=bool(all(good(n,r=r) for n in ('ideal_minus_zero','copy_minus_zero') for r in (0,1)) and np.all(np.asarray(dis)>0))
    content=bool(instrument and all(good('aligned_minus_zero',r=r) for r in (0,1)) and
        all(supported('aligned_minus_aligned_'+k) for k in ('pre_shuffle','post_shuffle')))
    continuity={k:bool(instrument and all(supported('aligned_minus_aligned_'+k,s) for s in (2,3,4))) for k in ('read_off','write_off')}
    interventions={n:bool(instrument and supported(n)) for n in ('aligned_minus_aligned_wrong','aligned_minus_aligned_lesion','aligned_rescue_minus_aligned_lesion')}
    primary=get('aligned_minus_translated');directions=[get('aligned_minus_translated',r=r) for r in (0,1)]
    gain=supported('aligned_minus_translated');harm=primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions)
    renewal=bool(content and all(continuity.values()) and all(interventions.values()))
    label='READOUT_NOT_QUALIFIED' if not instrument else 'ALIGNED_SERIAL_RENEWAL_ADVANTAGE' if gain and renewal else 'ALIGNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION' if gain else 'ALIGNED_SERIAL_HARM_DETECTED' if harm else 'SERIAL_ADDRESS_EFFECT_UNRESOLVED'
    return dict(schema='l20_extension1_heldout_controls_v1',label=label,primary=primary,directional_primary=directions,
        readout_qualified=instrument,content_qualified=content,continuity_qualified=continuity,interventions_qualified=interventions,
        renewal_controls_qualified=renewal,contrasts=rows,target_disagreement_cells=dis,cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],
        read_times=list(cfg.read_times),times=list(cfg.times),metrics=list(METRICS),generation_cell_means=v.mean(axis=(0,1)).tolist(),
        terminal_cell_means=q.mean(axis=(0,1)).tolist(),test_blocks=list(TISSUES),founder_blocks=list(TISSUES),
        blocks=16,lives_per_block=cfg.lives,renewal_generations=3,generation_paths=16*cfg.lives*48,enabled_rewrites=16*cfg.lives*36,
        terminal_paths=16*cfg.lives*24,selector_decisions=16*cfg.lives*68,packet_bytes=2048,public_guide_bytes=4096,rescue_g1_extra_bytes=2048,
        guide_sha256=old.GUIDE_SHA256,new_guide_fits=0,fresh_founders=True,reused_founder_packets=False,reused_noise_streams=False,
        reused_later_states=False,reused_source_starts=False,fresh_noise_streams=True,
        founder_acquisitions=16*cfg.lives*2,founder_pre_readers=16*cfg.lives*2,founder_source_writers=16*cfg.lives*4,
        identical_initial_records=True,counterfactual_outputs_propagated=True,
        conditional_on_one_fitted_guide=True,supplied_groups_and_frame=True,learned_ontology=False,
        absolute_fidelity_gate=None,equivalence_test=False,secondary_intervals_multiplicity_adjusted=False,automatic_successor=False)
