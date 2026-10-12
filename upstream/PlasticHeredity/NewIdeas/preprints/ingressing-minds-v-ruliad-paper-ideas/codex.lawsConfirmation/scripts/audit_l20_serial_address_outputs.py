"""D135 independent physics, reset/lineage, original-path, FFT and inference audit."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation.io import sha256_file

prior=old.checker();physics=prior.physics
compare,nested,generator=physics.compare,physics.nested,physics.generator
packet,unpack,sha,project,observe,stats=prior.packet,prior.unpack,prior.sha,prior.project,prior.observe,prior.stats
TAG='l20-serial-address-v1';ORIGINAL='l20-guide-renewal-v1'
KINDS=('translated','aligned','copy','aligned_read_off','aligned_write_off','aligned_wrong','aligned_lesion','aligned_rescue')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
PROBES=tuple((r,k) for r in (0,1) for k in KINDS+('aligned_post_shuffle','aligned_pre_shuffle','ideal','zero'))
GUIDE_SHA='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'

def check_life(raw,meta,cfg,source,replay=True):
    keys={'index','source_index','life','config','tag','stream_tag','cases','probes','times','read_times','source_times',
        'generations','terminal','host','guide_sha256','host_guide_bytes','ordinary_packet_bytes','rescue_g1_extra_bytes',
        'fresh_founders','reused_founder_packets','reused_noise_streams','reused_later_states','guide_refitted',
        'guide_inherited','target_labels_in_descendants','renewal_generations'}
    assert set(meta) in (keys,keys|{'replay'})
    index,life=meta['index'],meta['life'];assert type(index) is int and index in (*range(75000,75008),514235)
    assert type(life) is int and 0<=life<cfg.lives
    si=514232 if index==514235 else index-2000
    assert meta['source_index']==meta['host']['index']==si and meta['tag']==TAG and meta['stream_tag']==ORIGINAL
    assert set(meta['host'])=={'index','tissue','ladder','blueprint'}
    nested(meta['config'],asdict(cfg));nested(meta['cases'],[list(c) for c in CASES]);nested(meta['probes'],[list(c) for c in PROBES])
    for k in ('times','read_times','source_times'):nested(meta[k],list(getattr(cfg,k)))
    for k in ('reused_founder_packets','reused_noise_streams'):assert meta[k] is True
    for k in ('fresh_founders','reused_later_states','guide_refitted','guide_inherited','target_labels_in_descendants'):assert meta[k] is False
    assert (meta['host_guide_bytes'],meta['ordinary_packet_bytes'],meta['rescue_g1_extra_bytes'],meta['renewal_generations'])==(4096,2048,2048,3)
    shapes=dict(targets=(2,16,16),guide=(2,16,16),founder_packets=(2,2048),lesion_permutations=(2,256),terminal_permutations=(2,256),
        generation_shifts=(3,2),incoming=(16,3,2048),routed=(16,3,2048),backup_routed=(16,3,2048),outgoing=(16,3,2048),
        generation_read_states=(16,3,len(cfg.read_times),3,16,16),generation_write_states=(16,3,len(cfg.source_times),4,16,16),
        generation_scores=(16,3,2,2,16,16),terminal_inputs=(24,2048),terminal_packets=(24,2048),terminal_scores=(24,2,16,16),
        terminal_states=(24,len(cfg.times),3,16,16),values=(16,3,len(cfg.read_times),12),terminal_values=(24,len(cfg.times),12))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('founder_packets','incoming','routed','backup_routed','outgoing','terminal_inputs','terminal_packets') else np.int64 if k in ('lesion_permutations','terminal_permutations','generation_shifts') else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all()
    np.testing.assert_array_equal(raw['targets'],prior.prior.targets());np.testing.assert_array_equal(raw['targets'],source['targets'][life])
    np.testing.assert_array_equal(raw['guide'],source['guide'][life]);assert meta['guide_sha256']==sha(raw['guide'].astype('<f8').tobytes())==GUIDE_SHA
    for r in (0,1):assert raw['founder_packets'][r].tobytes()==packet(source['written_fields'][life,r,0])
    tissue,ladder,bp=physics.parameters(meta['host']);assert (tissue.sigma,bp.rho,bp.c_m)==(.3,.002,.2)
    lesions=np.stack([generator(ORIGINAL,si,life,f'lesion:{r}').permutation(256) for r in (0,1)])
    perms=np.stack([generator(ORIGINAL,si,life,f'terminal_shuffle:{r}').permutation(256) for r in (0,1)])
    np.testing.assert_array_equal(raw['lesion_permutations'],lesions);np.testing.assert_array_equal(raw['terminal_permutations'],perms)
    np.testing.assert_array_equal(lesions,source['lesion_permutations'][life]);np.testing.assert_array_equal(perms,source['terminal_permutations'][life])
    rmax=wmax=tmax=smax=0.;decisions=0;all_entries=[];last={}
    for ci,(r,k) in enumerate(CASES):
        f0=raw['founder_packets'][1-r if k=='aligned_wrong' else r].tobytes()
        incoming=packet(unpack(f0).ravel()[lesions[r]].reshape(16,16)) if k in ('aligned_lesion','aligned_rescue') else f0
        entries=[]
        for gi in range(3):
            g=gi+1;assert raw['incoming'][ci,gi].tobytes()==incoming
            routed,scores,selection=prior.prior.select(incoming,raw['guide']);decisions+=1
            assert raw['routed'][ci,gi].tobytes()==routed
            backup_source=raw['founder_packets'][r].tobytes() if k=='aligned_rescue' and g==1 else None
            if backup_source is None:backup,bscores,bselection=None,np.zeros((2,16,16)),None
            else:backup,bscores,bselection=prior.prior.select(backup_source,raw['guide']);decisions+=1
            assert raw['backup_routed'][ci,gi].tobytes()==(backup if backup is not None else bytes(2048))
            score=np.stack((scores,bscores));error=float(abs(raw['generation_scores'][ci,gi]-score).max());assert error<=1e-12;smax=max(smax,error)
            path,rm=prior.read_trace(routed,tissue,ladder,bp,generator(ORIGINAL,si,life,f'g{g}:birth'),
                generator(ORIGINAL,si,life,f'g{g}:read'),cfg,k!='aligned_read_off',backup,replay=replay)
            np.testing.assert_array_equal(raw['generation_read_states'][ci,gi,0],path[0])
            if replay:rmax=max(rmax,compare(raw['generation_read_states'][ci,gi],path))
            shift=np.asarray(divmod(int(generator(ORIGINAL,si,life,f'g{g}:source_shift').integers(1,256)),16),np.int64)
            np.testing.assert_array_equal(raw['generation_shifts'][gi],shift)
            start=raw['generation_read_states'][ci,gi,-1];enabled=k not in ('copy','aligned_write_off')
            mode='translated' if k in ('translated','copy') else 'aligned'
            path,wm=prior.write_trace(start,tissue,ladder,generator(ORIGINAL,si,life,f'g{g}:source_write'),mode,shift,cfg,enabled,replay)
            np.testing.assert_array_equal(raw['generation_write_states'][ci,gi,0],path[0])
            if replay:wmax=max(wmax,compare(raw['generation_write_states'][ci,gi],path))
            if k=='copy':outgoing=incoming
            elif k=='aligned_write_off':outgoing=bytes(2048)
            else:
                ref=raw['generation_write_states'][ci,gi,-1,2];assert np.tanh(ref).std()>1e-9
                outgoing=packet(project(np.tanh(ref)))
            assert raw['outgoing'][ci,gi].tobytes()==outgoing
            entries.append(dict(generation=g,kind=k,input_sha256=sha(incoming),output_sha256=sha(outgoing),
                rescue_input_sha256=sha(backup_source) if backup_source is not None else None,selector=selection,
                backup_selector=bselection,reader=rm,writer=wm,ordinary_packet_bytes=2048,extra_backup_bytes=2048 if backup_source is not None else 0,
                erased_before_writing=True,record_enabled=enabled,copied_input=k=='copy',host_guide_bytes=4096,guide_inherited=False))
            incoming=outgoing
        all_entries.append(entries);last[r,k]=incoming
    nested(meta['generations'],all_entries)
    selected={c:prior.prior.select(b,raw['guide']) for c,b in last.items()};inputs=last.copy();decisions+=16
    for r in (0,1):
        shuffle=lambda b:packet(unpack(b).ravel()[perms[r]].reshape(16,16))
        extras=dict(aligned_post_shuffle=shuffle(selected[r,'aligned'][0]),aligned_pre_shuffle=shuffle(last[r,'aligned']),
            ideal=packet(project(np.tanh(1.5*prior.prior.targets()[r]))),zero=bytes(2048))
        for k,b in extras.items():
            inputs[r,k]=b
            if k=='aligned_pre_shuffle':selected[r,k]=prior.prior.select(b,raw['guide']);decisions+=1
            else:selected[r,k]=(b,np.zeros((2,16,16)),None)
    terminal=[]
    for ci,c in enumerate(PROBES):
        b,scores,selection=selected[c]
        assert raw['terminal_inputs'][ci].tobytes()==inputs[c] and raw['terminal_packets'][ci].tobytes()==b
        error=float(abs(raw['terminal_scores'][ci]-scores).max());assert error<=1e-12;smax=max(smax,error)
        path,rm=prior.read_trace(b,tissue,ladder,bp,generator(ORIGINAL,si,life,'terminal:birth'),
            generator(ORIGINAL,si,life,'terminal:read'),cfg,times=cfg.times,replay=replay)
        np.testing.assert_array_equal(raw['terminal_states'][ci,0],path[0])
        if replay:tmax=max(tmax,compare(raw['terminal_states'][ci],path))
        terminal.append(dict(selector=selection,reader=rm))
    nested(meta['terminal'],terminal);assert decisions==68
    # Original ordinary/copy chains and terminal calibrations are exact known controls.
    for r in (0,1):
        for new,original in (('translated','learned'),('copy','copy')):
            ci,oi=CASES.index((r,new)),old.CASES.index((r,original))
            for key in ('incoming','routed','backup_routed','outgoing','generation_read_states','generation_write_states','generation_scores','values'):
                np.testing.assert_array_equal(raw[key][ci],source[key][life,oi])
        for new,original in (('translated','learned'),('copy','copy'),('ideal','ideal'),('zero','zero')):
            ci,oi=PROBES.index((r,new)),old.PROBES.index((r,original))
            for key in ('terminal_inputs','terminal_packets','terminal_scores','terminal_states','terminal_values'):
                np.testing.assert_array_equal(raw[key][ci],source[key][life,oi])
    metricmax=0.
    for key,state,cases in (('values','generation_read_states',CASES),('terminal_values','terminal_states',PROBES)):
        expected=observe(raw[state],raw['targets'],cases,cfg);error=float(abs(raw[key]-expected).max());assert error<=1e-12;metricmax=max(metricmax,error)
    aliases=check_aliases(raw,cfg)
    return dict(full_life_replay=replay,reader_max_abs=rmax,writer_max_abs=wmax,terminal_max_abs=tmax,selector_max_abs=smax,metric_max_abs=metricmax,
        generation_paths=48,enabled_rewrites=36,terminal_paths=24,selector_decisions=68,known_generation_paths=12,known_terminal_paths=8,
        **aliases,packet_lineage=True,fresh_reset=True,ordinary_exact_replay=True)

def check_aliases(raw,cfg):
    pairs=[((r,'aligned_wrong'),(1-r,'aligned'),g) for r in (0,1) for g in range(3)]
    pairs += [((0,'aligned_read_off'),(1,'aligned_read_off'),g) for g in range(3)]
    pairs += [((0,'aligned_write_off'),(1,'aligned_write_off'),g) for g in (1,2)]
    for a,b,g in pairs:
        for key in ('generation_read_states','generation_write_states'):np.testing.assert_array_equal(raw[key][CASES.index(a),g],raw[key][CASES.index(b),g])
    for r in (0,1):
        for k in ('aligned','copy','aligned_write_off'):
            np.testing.assert_array_equal(raw['generation_read_states'][CASES.index((r,k)),0],raw['generation_read_states'][CASES.index((r,'translated')),0])
        np.testing.assert_array_equal(raw['generation_write_states'][CASES.index((r,'aligned')),0,1],raw['generation_write_states'][CASES.index((r,'translated')),0,1])
        prefix=[i for i,t in enumerate(cfg.read_times) if t<=100]
        np.testing.assert_array_equal(raw['generation_read_states'][CASES.index((r,'aligned_rescue')),0,prefix],raw['generation_read_states'][CASES.index((r,'aligned_lesion')),0,prefix])
    tpairs=[((r,'aligned_wrong'),(1-r,'aligned')) for r in (0,1)]+[((r,'aligned_write_off'),(r,'zero')) for r in (0,1)]
    tpairs += [((0,'aligned_read_off'),(1,'aligned_read_off')),((0,'zero'),(1,'zero'))]
    for a,b in tpairs:np.testing.assert_array_equal(raw['terminal_states'][PROBES.index(a)],raw['terminal_states'][PROBES.index(b)])
    return dict(generation_aliases=11,read_only_aliases=6,first_writer_aliases=2,rescue_prefix_aliases=2,terminal_aliases=6,exact_alias_checks=27)

def check_block(raw,meta,cfg,source,source_paths,replay=False):
    assert set(meta)=={'index','config','source_sha256','lives'} and len(meta['lives'])==cfg.lives
    nested(meta['config'],asdict(cfg));assert all(x.shape[0]==cfg.lives for x in raw.values())
    assert meta['source_sha256']=={str(x):sha256_file(x) for x in source_paths}
    for life,row in enumerate(meta['lives']):
        assert row['index']==meta['index'] and row['life']==life
        proof=check_life({k:x[life] for k,x in raw.items()},row,cfg,source,replay)
        saved=row['replay'];assert saved['full_life_replay'] is True and set(saved)==set(proof)
        for key in proof:
            if key.endswith('_max_abs'):assert 0<=saved[key]<=(1e-12 if key in ('selector_max_abs','metric_max_abs') else 1e-10)
            elif key!='full_life_replay':assert proof[key]==saved[key]
    return True

def check_summary(summary,blocks,cfg):
    assert len(blocks)==8
    v=np.stack([b['values'] for b in blocks]);q=np.stack([b['terminal_values'] for b in blocks])
    assert v.shape==(8,cfg.lives,16,3,len(cfg.read_times),12) and q.shape==(8,cfg.lives,24,len(cfg.times),12)
    assert np.isfinite(v).all() and np.isfinite(q).all()
    pairs=(('aligned','translated'),('aligned','copy'),('aligned','aligned_read_off'),('aligned','aligned_write_off'),
        ('aligned','aligned_wrong'),('aligned','aligned_lesion'),('aligned_rescue','aligned_lesion'),('translated','copy'))
    extras=(('aligned','aligned_post_shuffle'),('aligned','aligned_pre_shuffle'),('ideal','zero'),
        ('copy','zero'),('aligned','zero'),('translated','zero'))
    draws=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        for stage in range(1,5):
            cases=CASES if stage<4 else PROBES
            for left,right in pairs+(extras if stage==4 else ()):
                effects=[]
                for role in (0,1):
                    ai,bi=cases.index((role,left)),cases.index((role,right))
                    a,b=(v[:,:,ai,stage-1,-1],v[:,:,bi,stage-1,-1]) if stage<4 else (q[:,:,ai,-1],q[:,:,bi,-1])
                    effects.append((a[...,col]-a[...,col+1])-(b[...,col]-b[...,col+1]))
                for role,effect in ((0,effects[0]),(1,effects[1]),('both',(effects[0]+effects[1])/2)):
                    rows.append(dict(name=left+'_minus_'+right,stage=stage,role=role,observer=observer,**stats(effect,draws)))
    get=lambda n,s=4,r='both':next(row for row in rows if (row['name'],row['stage'],row['role'],row['observer'])==(n,s,r,'qualified'))
    positive=lambda n,s=4,r='both':get(n,s,r)['pointwise_block_bootstrap_95'][0]>0
    supported=lambda n,s=4:positive(n,s) and all(get(n,s,r)['mean']>0 for r in (0,1))
    disagreements=[[int((b['targets'][life,0]!=b['targets'][life,1]).sum()) for life in range(cfg.lives)] for b in blocks]
    instrument=bool(all(positive(n,r=r) for n in ('ideal_minus_zero','copy_minus_zero') for r in (0,1)) and
        all(x>0 for row in disagreements for x in row))
    content=bool(instrument and all(positive('aligned_minus_zero',r=r) for r in (0,1)) and
        supported('aligned_minus_aligned_pre_shuffle') and supported('aligned_minus_aligned_post_shuffle'))
    continuity={k:bool(instrument and all(supported('aligned_minus_aligned_'+k,s) for s in (2,3,4))) for k in ('read_off','write_off')}
    interventions={n:bool(instrument and supported(n)) for n in
        ('aligned_minus_aligned_wrong','aligned_minus_aligned_lesion','aligned_rescue_minus_aligned_lesion')}
    primary=get('aligned_minus_translated');directions=[get('aligned_minus_translated',r=r) for r in (0,1)]
    renewal=bool(content and all(continuity.values()) and all(interventions.values()))
    label='SERIAL_ADDRESS_EFFECT_UNRESOLVED'
    if not instrument:label='READOUT_NOT_QUALIFIED'
    elif supported('aligned_minus_translated'):
        label='ALIGNED_SERIAL_RENEWAL_ADVANTAGE' if renewal else 'ALIGNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION'
    elif primary['pointwise_block_bootstrap_95'][1]<0 and all(row['mean']<0 for row in directions):label='ALIGNED_SERIAL_HARM_DETECTED'
    expected=dict(schema='l20_serial_address_v1',label=label,primary=primary,directional_primary=directions,
        readout_qualified=instrument,content_qualified=content,continuity_qualified=continuity,interventions_qualified=interventions,
        renewal_controls_qualified=renewal,contrasts=rows,target_disagreement_cells=disagreements,
        cases=[list(c) for c in CASES],probes=[list(c) for c in PROBES],read_times=list(cfg.read_times),times=list(cfg.times),
        metrics=list(prior.METRICS),generation_cell_means=v.mean(axis=(0,1)).tolist(),terminal_cell_means=q.mean(axis=(0,1)).tolist(),
        test_blocks=list(range(75000,75008)),source_blocks=list(range(73000,73008)),blocks=8,lives_per_block=cfg.lives,
        renewal_generations=3,generation_paths=8*cfg.lives*48,enabled_rewrites=8*cfg.lives*36,terminal_paths=8*cfg.lives*24,
        selector_decisions=8*cfg.lives*68,packet_bytes=2048,public_guide_bytes=4096,rescue_g1_extra_bytes=2048,
        guide_sha256=GUIDE_SHA,new_guide_fits=0,fresh_founders=False,reused_founder_packets=True,reused_noise_streams=True,
        reused_later_states=False,identical_initial_records=True,counterfactual_outputs_propagated=True,
        conditional_on_one_fitted_guide=True,supplied_groups_and_frame=True,learned_ontology=False,
        absolute_fidelity_gate=None,equivalence_test=False,secondary_intervals_multiplicity_adjusted=False,automatic_successor=False)
    nested(summary,expected);return True

if __name__=='__main__':
    from laws_confirmation.l20_serial_address_run import main
    main()
