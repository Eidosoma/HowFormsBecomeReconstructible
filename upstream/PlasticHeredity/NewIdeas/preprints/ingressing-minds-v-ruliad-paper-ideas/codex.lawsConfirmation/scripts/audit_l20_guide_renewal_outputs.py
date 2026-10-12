"""D132 independently replayed reset bodies, address selection, bytes and inference."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_learned_guide as old
from laws_confirmation.io import canonical_digest

prior=old.checker();physics=prior.physics
compare,nested,generator=physics.compare,physics.nested,physics.generator
project,observe,stats,packet,unpack,sha=prior.project,prior.observe,prior.stats,prior.packet,prior.unpack,prior.sha
TAG='l20-guide-renewal-v1'
GUIDE_SHA256='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
KINDS=('learned','native','supplied','aligned','copy','read_off','write_off','wrong','lesion','rescue','wrong_guide')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
EXTRAS=('learned_shuffle','shuffle_learned','ideal','ideal_shifted','ideal_learned','zero')
PROBES=tuple((r,k) for r in (0,1) for k in KINDS+EXTRAS)
SOURCE_KEYS=prior.SOURCE_KEYS
BASE_META={'index','life','config','tag','parent_birth_rng','parent_settle_rng','teaching_rng','pre_readers','writers','tissue','ladder','blueprint'}
METRICS=prior.METRICS


def selected(b,kind,guide):
    if kind in ('native','aligned','ideal','ideal_shifted','zero','learned_shuffle'):return b,np.zeros((2,16,16)),None
    if kind=='supplied':g=prior.targets()
    elif kind=='wrong_guide':g=np.stack([prior.move(x,(3,5),False) for x in guide])
    else:
        assert kind in KINDS+('shuffle_learned','ideal_learned');g=guide
    return prior.select(b,g)


def read_trace(b,tissue,ladder,bp,birth_random,read_random,cfg,enabled=True,backup=None,times=None,replay=True):
    times=cfg.read_times if times is None else times
    v=.2*birth_random.standard_normal((1,16,16));state=(v,v.copy(),v.copy());saved=[np.stack(state)[:,0]]
    birth=canonical_digest(birth_random.bit_generator.state);field=unpack(b)
    for t in range(1,cfg.steps+1):
        if backup is not None and t==cfg.rescue_after+1:field=unpack(backup)
        noise=read_random.standard_normal((1,16,16))
        if replay:
            state=physics.step(*state,field if enabled else np.zeros((16,16)),tissue,ladder,0.,bp.rho,noise)
            if t in times:saved.append(np.stack(state)[:,0])
    return np.stack(saved),dict(birth_rng=birth,read_rng=canonical_digest(read_random.bit_generator.state),
        input_sha256=sha(b),backup_sha256=sha(backup) if backup is not None else None,
        rescue_after=cfg.rescue_after if backup is not None else None,packet_bytes=2048,
        extra_backup_bytes=2048 if backup is not None else 0,enabled=enabled,writing=False,gain=0.,target_labels=False)


def write_trace(start,tissue,ladder,random,mode,shift,cfg,enabled=True,replay=True):
    state=tuple(x[None].copy() for x in start);theta=np.zeros((1,16,16));saved=[np.stack((*state,theta))[:,0]]
    for t in range(1,cfg.source_steps+1):
        noise=random.standard_normal((1,16,16))
        if replay:
            applied=theta if mode=='aligned' else prior.move(theta[0],shift,False)[None]
            state=physics.step(*state,applied,tissue,ladder,.2,.002,noise)
            if enabled:theta=project(.999*theta+.001*np.tanh(state[2]))
            if t in cfg.source_times:saved.append(np.stack((*state,theta))[:,0])
    return np.stack(saved),dict(noise_rng=canonical_digest(random.bit_generator.state),mode=mode,shift=shift.tolist(),
        theta_start_zero=True,theta_writing=enabled,gain=.2,rho=.002,lam=.001 if enabled else 0.,sigma=.3,
        incoming_packet_access=False,guide_access=False,target_labels=False)


def check_founders(raw,meta,cfg,replay=True,tag=TAG):
    assert set(raw)==SOURCE_KEYS and set(meta)==BASE_META
    index,life=meta['index'],meta['life'];assert meta['tag']==tag
    nested(meta['config'],asdict(cfg))
    shapes=dict(native_theta=(16,16),theta0=(16,16),parent_birth=(3,16,16),settled=(3,16,16),targets=(2,16,16),
        founder_states=(2,len(cfg.parent_times),4,16,16),founder_packets=(2,2048),pre_states=(2,len(cfg.times),3,16,16),
        source_starts=(2,3,16,16),source_shift=(2,),source_states=(2,2,len(cfg.source_times),4,16,16),written_fields=(2,2,16,16))
    for k,shape in shapes.items():
        dtype=np.uint8 if k=='founder_packets' else np.int64 if k=='source_shift' else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all()
    np.testing.assert_array_equal(raw['targets'],prior.targets());tissue,ladder,bp=physics.parameters(meta)
    assert (tissue.sigma,bp.rho,bp.c_m)==(.3,.002,.2)
    fmax=prior.founder_check(raw,meta,cfg,replay,tag,index);pmax=smax=0.;readers=[];writers=[]
    shift=np.asarray(divmod(int(generator(tag,index,life,'source_shift').integers(1,256)),16),dtype=np.int64)
    np.testing.assert_array_equal(raw['source_shift'],shift)
    for r in (0,1):
        path,entry=prior.reader_trace(raw['founder_packets'][r].tobytes(),tissue,ladder,bp,
            generator(tag,index,life,'source_birth'),generator(tag,index,life,'source_read'),cfg,replay=replay)
        np.testing.assert_array_equal(raw['pre_states'][r,0],path[0])
        if replay:pmax=max(pmax,compare(raw['pre_states'][r],path))
        np.testing.assert_array_equal(raw['source_starts'][r],raw['pre_states'][r,-1]);readers.append(entry);records=[]
        for mi,mode in enumerate(('translated','aligned')):
            start=raw['source_starts'][r];np.testing.assert_array_equal(raw['source_states'][r,mi,0],np.concatenate((start,np.zeros((1,16,16)))))
            random=generator(tag,index,life,'source_write')
            if replay:
                path,entry=prior.previous.replay_source(start,tissue,ladder,random,mode,shift,cfg)
                smax=max(smax,compare(raw['source_states'][r,mi],path))
            else:
                for _ in range(cfg.source_steps):random.standard_normal((1,16,16))
                entry=prior.previous.source_metadata(random,mode,shift)
            ref=raw['source_states'][r,mi,-1,2];assert np.tanh(ref).std()>1e-9
            np.testing.assert_array_equal(raw['written_fields'][r,mi],project(np.tanh(ref)));records.append(entry)
        writers.append(records)
    nested(meta['pre_readers'],readers);nested(meta['writers'],writers)
    return dict(founder_max_abs=fmax,pre_reader_max_abs=pmax,founder_source_max_abs=smax)


def check_life(raw,meta,cfg,guide,replay=True):
    extra={'cases','probes','times','read_times','source_times','parent_times','generations','terminal','guide_sha256',
        'host_guide_bytes','ordinary_packet_bytes','rescue_g1_extra_bytes','fresh_founders','reused_source_starts',
        'guide_refitted','guide_inherited','target_labels_in_descendants','renewal_generations','transfer_interfaces_including_probe'}
    assert set(meta) in (BASE_META|extra,BASE_META|extra|{'replay'})
    index,life=meta['index'],meta['life'];assert type(index) is int and index in (*range(73000,73008),514232)
    assert type(life) is int and 0<=life<cfg.lives
    nested(meta['cases'],[list(c) for c in CASES]);nested(meta['probes'],[list(c) for c in PROBES])
    for k in ('times','read_times','source_times','parent_times'):nested(meta[k],list(getattr(cfg,k)))
    assert meta['guide_sha256']==sha(guide.astype('<f8').tobytes())
    assert (meta['host_guide_bytes'],meta['ordinary_packet_bytes'],meta['rescue_g1_extra_bytes'])==(4096,2048,2048)
    assert meta['fresh_founders'] is True
    for k in ('reused_source_starts','guide_refitted','guide_inherited','target_labels_in_descendants'):assert meta[k] is False
    assert type(meta['renewal_generations']) is int and meta['renewal_generations']==3
    assert meta['transfer_interfaces_including_probe']==4
    source=check_founders({k:raw[k] for k in SOURCE_KEYS},{k:meta[k] for k in BASE_META},cfg,replay)
    shapes=dict(guide=(2,16,16),lesion_permutations=(2,256),terminal_permutations=(2,256),incoming=(22,3,2048),
        routed=(22,3,2048),backup_routed=(22,3,2048),outgoing=(22,3,2048),generation_shifts=(3,2),
        generation_read_states=(22,3,len(cfg.read_times),3,16,16),generation_write_states=(22,3,len(cfg.source_times),4,16,16),
        generation_scores=(22,3,2,2,16,16),terminal_shift=(2,),terminal_inputs=(34,2048),terminal_packets=(34,2048),
        terminal_scores=(34,2,16,16),terminal_states=(34,len(cfg.times),3,16,16),
        values=(22,3,len(cfg.read_times),12),terminal_values=(34,len(cfg.times),12))
    assert set(raw)==SOURCE_KEYS|set(shapes)
    bytekeys={'incoming','routed','backup_routed','outgoing','terminal_inputs','terminal_packets'}
    intkeys={'lesion_permutations','terminal_permutations','generation_shifts','terminal_shift'}
    for k,shape in shapes.items():
        dtype=np.uint8 if k in bytekeys else np.int64 if k in intkeys else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all()
    np.testing.assert_array_equal(raw['guide'],guide)
    tissue,ladder,bp=physics.parameters(meta);rmax=wmax=tmax=scoremax=0.;selections=0
    founders=[[packet(raw['written_fields'][r,mi]) for mi in (0,1)] for r in (0,1)]
    lesions=np.stack([generator(TAG,index,life,f'lesion:{r}').permutation(256) for r in (0,1)])
    perms=np.stack([generator(TAG,index,life,f'terminal_shuffle:{r}').permutation(256) for r in (0,1)])
    np.testing.assert_array_equal(raw['lesion_permutations'],lesions);np.testing.assert_array_equal(raw['terminal_permutations'],perms)
    all_entries=[];last={}
    for ci,(r,k) in enumerate(CASES):
        incoming=founders[1-r][0] if k=='wrong' else founders[r][1] if k=='aligned' else founders[r][0]
        if k in ('lesion','rescue'):incoming=packet(unpack(incoming).ravel()[lesions[r]].reshape(16,16))
        entries=[]
        for gi in range(3):
            g=gi+1;assert raw['incoming'][ci,gi].tobytes()==incoming
            routed,scores,selection=selected(incoming,k,guide)
            assert raw['routed'][ci,gi].tobytes()==routed
            np.testing.assert_allclose(raw['generation_scores'][ci,gi,0],scores,atol=1e-12,rtol=0)
            scoremax=max(scoremax,float(abs(raw['generation_scores'][ci,gi,0]-scores).max()));selections+=int(selection is not None)
            rescue=founders[r][0] if k=='rescue' and g==1 else None
            if rescue is None:backup,bscores,bselection=None,np.zeros((2,16,16)),None
            else:backup,bscores,bselection=selected(rescue,'learned',guide);selections+=1
            assert raw['backup_routed'][ci,gi].tobytes()==(bytes(2048) if backup is None else backup)
            np.testing.assert_allclose(raw['generation_scores'][ci,gi,1],bscores,atol=1e-12,rtol=0)
            scoremax=max(scoremax,float(abs(raw['generation_scores'][ci,gi,1]-bscores).max()))
            path,rm=read_trace(routed,tissue,ladder,bp,generator(TAG,index,life,f'g{g}:birth'),generator(TAG,index,life,f'g{g}:read'),
                cfg,k!='read_off',backup,replay=replay)
            np.testing.assert_array_equal(raw['generation_read_states'][ci,gi,0],path[0])
            if replay:rmax=max(rmax,compare(raw['generation_read_states'][ci,gi],path))
            shift=np.asarray(divmod(int(generator(TAG,index,life,f'g{g}:source_shift').integers(1,256)),16),dtype=np.int64)
            np.testing.assert_array_equal(raw['generation_shifts'][gi],shift)
            start=raw['generation_read_states'][ci,gi,-1]
            path,wm=write_trace(start,tissue,ladder,generator(TAG,index,life,f'g{g}:source_write'),
                'aligned' if k=='aligned' else 'translated',shift,cfg,k not in ('copy','write_off'),replay)
            np.testing.assert_array_equal(raw['generation_write_states'][ci,gi,0],path[0])
            if replay:wmax=max(wmax,compare(raw['generation_write_states'][ci,gi],path))
            if k=='copy':outgoing=incoming
            elif k=='write_off':outgoing=packet(np.zeros((16,16)))
            else:
                ref=raw['generation_write_states'][ci,gi,-1,2];assert np.tanh(ref).std()>1e-9
                outgoing=packet(project(np.tanh(ref)))
            assert raw['outgoing'][ci,gi].tobytes()==outgoing
            entries.append(dict(generation=g,kind=k,input_sha256=sha(incoming),output_sha256=sha(outgoing),
                rescue_input_sha256=sha(rescue) if rescue is not None else None,selector=selection,backup_selector=bselection,
                reader=rm,writer=wm,ordinary_packet_bytes=2048,extra_backup_bytes=2048 if rescue is not None else 0,
                erased_before_writing=True,record_enabled=k not in ('copy','write_off'),copied_input=k=='copy',
                host_guide_bytes=4096,guide_inherited=False))
            incoming=outgoing
        last[r,k]=incoming;all_entries.append(entries)
    nested(meta['generations'],all_entries)
    terminal_shift=np.asarray(divmod(int(generator(TAG,index,life,'terminal:shift').integers(1,256)),16),dtype=np.int64)
    np.testing.assert_array_equal(raw['terminal_shift'],terminal_shift)
    prepared={c:selected(b,c[1],guide) for c,b in last.items()};inputs=last.copy()
    for r in (0,1):
        shuffle=lambda b:packet(unpack(b).ravel()[perms[r]].reshape(16,16))
        ideal=packet(project(np.tanh(1.5*prior.targets()[r])));shifted=packet(prior.move(unpack(ideal),terminal_shift,False))
        extras=dict(learned_shuffle=shuffle(prepared[r,'learned'][0]),shuffle_learned=shuffle(last[r,'learned']),
            ideal=ideal,ideal_shifted=shifted,ideal_learned=shifted,zero=packet(np.zeros((16,16))))
        for k,b in extras.items():inputs[r,k]=b;prepared[r,k]=selected(b,k,guide)
    entries=[]
    for ci,c in enumerate(PROBES):
        b,scores,selection=prepared[c];assert raw['terminal_inputs'][ci].tobytes()==inputs[c]
        assert raw['terminal_packets'][ci].tobytes()==b
        np.testing.assert_allclose(raw['terminal_scores'][ci],scores,atol=1e-12,rtol=0)
        scoremax=max(scoremax,float(abs(raw['terminal_scores'][ci]-scores).max()));selections+=int(selection is not None)
        path,rm=read_trace(b,tissue,ladder,bp,generator(TAG,index,life,'terminal:birth'),
            generator(TAG,index,life,'terminal:read'),cfg,True,times=cfg.times,replay=replay)
        np.testing.assert_array_equal(raw['terminal_states'][ci,0],path[0])
        if replay:tmax=max(tmax,compare(raw['terminal_states'][ci],path))
        entries.append(dict(selector=selection,reader=rm))
    nested(meta['terminal'],entries);assert selections==78
    pairs=[((r,'wrong'),(1-r,'learned'),g) for r in (0,1) for g in range(3)]
    pairs += [((0,'read_off'),(1,'read_off'),g) for g in range(3)]
    pairs += [((0,'write_off'),(1,'write_off'),g) for g in (1,2)]
    for a,b,g in pairs:
        for key in ('generation_read_states','generation_write_states'):
            np.testing.assert_array_equal(raw[key][CASES.index(a),g],raw[key][CASES.index(b),g])
    for r in (0,1):
        for k in ('copy','write_off'):
            np.testing.assert_array_equal(raw['generation_read_states'][CASES.index((r,k)),0],raw['generation_read_states'][CASES.index((r,'learned')),0])
        prefix=[i for i,t in enumerate(cfg.read_times) if t<=cfg.rescue_after]
        np.testing.assert_array_equal(raw['generation_read_states'][CASES.index((r,'rescue')),0,prefix],
            raw['generation_read_states'][CASES.index((r,'lesion')),0,prefix])
    tpairs=[((r,'wrong'),(1-r,'learned')) for r in (0,1)]+[((r,'write_off'),(r,'zero')) for r in (0,1)]
    tpairs += [((0,'read_off'),(1,'read_off')),((0,'zero'),(1,'zero'))]
    for a,b in tpairs:np.testing.assert_array_equal(raw['terminal_states'][PROBES.index(a)],raw['terminal_states'][PROBES.index(b)])
    metricmax=0.
    for key,states,cases in (('values','generation_read_states',CASES),('terminal_values','terminal_states',PROBES)):
        values=observe(raw[states],raw['targets'],cases,cfg)
        np.testing.assert_allclose(raw[key],values,atol=1e-12,rtol=0)
        metricmax=max(metricmax,float(abs(raw[key]-values).max()))
    return dict(full_life_replay=replay,**source,generation_read_max_abs=rmax,generation_write_max_abs=wmax,
        terminal_max_abs=tmax,metric_max_abs=metricmax,selector_max_abs=scoremax,parent_acquisitions=2,
        pre_readers=2,founder_source_writers=4,generation_paths=66,generation_writer_phases=66,
        enabled_generation_rewrites=54,terminal_paths=34,selector_decisions=78,
        generation_path_aliases=11,read_only_aliases=4,rescue_prefix_aliases=2,terminal_aliases=6,exact_alias_checks=23,
        packet_lineage_checked=True,fresh_reset=True,exact_signs=True)


def check_block(raw,meta,cfg,guide,replay=True):
    assert set(meta)=={'index','config','guide_sha256','lives'}
    nested(meta['config'],asdict(cfg));assert meta['guide_sha256']==sha(guide.astype('<f8').tobytes())
    assert len(meta['lives'])==cfg.lives and all(x.shape[0]==cfg.lives for x in raw.values())
    for life,row in enumerate(meta['lives']):
        assert row['index']==meta['index'] and row['life']==life
        current=check_life({k:x[life] for k,x in raw.items()},row,cfg,guide,replay)
        proof=row['replay'];expected=current|dict(full_life_replay=True)
        for key in (k for k in current if k.endswith('_max_abs')):
            assert 0<=proof[key]<=(1e-12 if key in ('metric_max_abs','selector_max_abs') else 1e-10)
            if not replay:expected[key]=proof[key]
        nested(proof,expected)
    return True


def check_bridge(raw,meta,known):
    cfg=old.CONFIG;index=old.DISPOSABLE;assert meta['index']==514231 and meta['life']==0
    extras={'bridge_cases','bridge_writers','bridge_readers','known_outcomes','new_futures','qualification_pool','guide_sha256'}
    assert set(meta) in (BASE_META|extras,BASE_META|extras|{'replay'})
    assert set(raw)==SOURCE_KEYS|{'bridge_write_states','bridge_packets','bridge_states'}
    assert meta['known_outcomes'] is True and meta['new_futures']==0 and meta['qualification_pool'] is False
    assert meta['guide_sha256']==GUIDE_SHA256
    for key in SOURCE_KEYS:np.testing.assert_array_equal(raw[key],known[key][0])
    source=check_founders({k:raw[k] for k in SOURCE_KEYS},{k:meta[k] for k in BASE_META},cfg,True,old.TAG)
    tissue,ladder,bp=physics.parameters(meta);maximum=max(source.values());writers=[]
    for r in (0,1):
        entries=[]
        for mi,mode in enumerate(('translated','aligned')):
            path,entry=write_trace(raw['source_starts'][r],tissue,ladder,generator(old.TAG,index,0,'source_write'),mode,raw['source_shift'],cfg)
            maximum=max(maximum,compare(raw['bridge_write_states'][r,mi],path));entries.append(entry)
        writers.append(entries)
    np.testing.assert_array_equal(raw['bridge_write_states'],known['source_states'][0]);nested(meta['bridge_writers'],writers)
    cases=tuple((r,k) for r in (0,1) for k in ('native','learned','supplied','aligned','wrong_guide','ideal','zero'))
    nested(meta['bridge_cases'],[list(c) for c in cases]);readers=[]
    for ci,c in enumerate(cases):
        oldci=old.CASES.index(c);b=raw['bridge_packets'][ci].tobytes()
        assert b==known['packets'][0,oldci].tobytes()
        path,entry=read_trace(b,tissue,ladder,bp,generator(old.TAG,index,0,'birth'),generator(old.TAG,index,0,'read'),cfg,True,times=cfg.times)
        maximum=max(maximum,compare(raw['bridge_states'][ci],path));readers.append(entry)
        np.testing.assert_array_equal(raw['bridge_states'][ci],known['states'][0,oldci])
    nested(meta['bridge_readers'],readers)
    return dict(known_founder_acquisitions=2,known_pre_readers=2,known_source_writers=4,known_reader_paths=14,
        full_replay=True,max_abs=maximum,new_futures=0,whole_renewal_replayed=False,qualification_pool=False)


def check_summary(summary,blocks,cfg):
    assert len(blocks)==8
    v=np.stack([b['values'] for b in blocks]);q=np.stack([b['terminal_values'] for b in blocks])
    assert v.shape==(8,cfg.lives,22,3,len(cfg.read_times),12) and q.shape==(8,cfg.lives,34,len(cfg.times),12)
    assert np.isfinite(v).all() and np.isfinite(q).all()
    pairs=('learned_minus_native','learned_minus_supplied','learned_minus_aligned','learned_minus_copy',
        'learned_minus_read_off','learned_minus_write_off','learned_minus_wrong','learned_minus_lesion',
        'rescue_minus_lesion','learned_minus_wrong_guide')
    extras=('learned_minus_learned_shuffle','learned_minus_shuffle_learned','ideal_minus_zero','copy_minus_zero',
        'ideal_learned_minus_ideal_shifted','ideal_learned_minus_ideal','learned_minus_zero','aligned_minus_zero','supplied_minus_zero')
    draws=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        for stage in (1,2,3,4):
            values=v[:,:,:,stage-1,-1] if stage<4 else q[:,:,:,-1];cases=CASES if stage<4 else PROBES
            for name in pairs+(extras if stage==4 else ()):
                a,b=name.split('_minus_');effects=[]
                for r in (0,1):
                    ai,bi=cases.index((r,a)),cases.index((r,b))
                    effects.append((values[:,:,ai,col]-values[:,:,ai,col+1])-(values[:,:,bi,col]-values[:,:,bi,col+1]))
                for r,e in ((0,effects[0]),(1,effects[1]),('both',(effects[0]+effects[1])/2)):
                    rows.append(dict(name=name,stage=stage,role=r,observer=observer,**stats(e,draws)))
    get=lambda name,stage=4,role='both':next(x for x in rows if (x['name'],x['stage'],x['role'],x['observer'])==(name,stage,role,'qualified'))
    good=lambda name,stage=4,role='both':get(name,stage,role)['pointwise_block_bootstrap_95'][0]>0
    supported=lambda name,stage=4:good(name,stage) and all(get(name,stage,r)['mean']>0 for r in (0,1))
    disagreements=[[int((b['targets'][l,0]!=b['targets'][l,1]).sum()) for l in range(cfg.lives)] for b in blocks]
    gates=[get(name,role=r) for name in ('ideal_minus_zero','copy_minus_zero') for r in (0,1)]
    readable=bool(all(good(name,role=r) for name in ('ideal_minus_zero','copy_minus_zero') for r in (0,1)) and all(n>0 for row in disagreements for n in row))
    calibration=bool(readable and all(good('ideal_learned_minus_ideal_shifted',role=r) for r in (0,1)))
    continuity={name:bool(readable and all(supported('learned_minus_'+name,stage) for stage in (2,3,4))) for name in ('read_off','write_off')}
    content=bool(readable and all(good('learned_minus_zero',role=r) for r in (0,1)) and supported('learned_minus_learned_shuffle') and supported('learned_minus_shuffle_learned'))
    interventions={name:bool(readable and supported(name)) for name in ('learned_minus_wrong','learned_minus_lesion','rescue_minus_lesion','learned_minus_wrong_guide')}
    primary=get('learned_minus_native');directions=[get('learned_minus_native',role=r) for r in (0,1)]
    renewal=bool(all(continuity.values()) and content and all(interventions.values()))
    label='READOUT_NOT_QUALIFIED' if not readable else 'GUIDE_CALIBRATION_NOT_QUALIFIED' if not calibration else 'SERIAL_EFFECT_UNRESOLVED'
    if readable and calibration:
        if supported('learned_minus_native'):label='LEARNED_SERIAL_RENEWAL_QUALIFIED' if renewal else 'LEARNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION'
        elif primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions):label='LEARNED_HARM_DETECTED'
    expected=dict(schema='l20_guide_renewal_v1',label=label,primary=primary,directional_primary=directions,
        readout_qualified=readable,readout_gates=gates,calibration_qualified=calibration,continuity_qualified=continuity,
        content_qualified=content,interventions_qualified=interventions,renewal_controls_qualified=renewal,
        contrasts=rows,target_disagreement_cells=disagreements,cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],
        read_times=list(cfg.read_times),times=list(cfg.times),metrics=list(METRICS),generation_cell_means=v.mean(axis=(0,1)).tolist(),
        terminal_cell_means=q.mean(axis=(0,1)).tolist(),test_blocks=list(range(73000,73008)),training_blocks=[72500,72501],
        blocks=8,lives_per_block=cfg.lives,renewal_generations=3,transfer_interfaces_including_probe=4,
        generation_paths=8*cfg.lives*66,terminal_paths=8*cfg.lives*34,packet_bytes=2048,public_guide_bytes=4096,rescue_g1_extra_bytes=2048,
        guide_sha256=GUIDE_SHA256,new_guide_fits=0,fresh_founders=True,reused_source_starts=False,
        conditional_on_one_fitted_guide=True,supplied_groups_and_frame=True,unseen_pattern_families=False,
        learned_ontology=False,native_renewal_necessity=False,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False)
    nested(summary,expected);return True


if __name__=='__main__':
    from laws_confirmation.l20_guide_renewal_run import main
    main(default_command='audit')
