"""Fresh source, four complete writing schedules and matched fresh recipients."""
from common import *
import itertools,time
import baseline,intervention,intervention_audit,kernel,repair_audit,receiving,receiving_audit
from inherited_repair import address as episode

def context(index):
    assert index in (*BLOCKS,*EXCLUDED,28000000)
    if index in BLOCKS:
        assert (ROOT/'FREEZE.json').is_file(),'production context requires freeze'
        frozen=read(ROOT/'FREEZE.json');assert frozen['blocks']==list(BLOCKS)
        assert frozen['new_production_outcomes_generated'] is False
    cfg,rcfg=configs();ctx=model.source.context(index,cfg)|{'readout':rcfg}
    exact(ctx['codes'],codebook(),'independent observer codebook');return ctx

def observation(ctx,raw):
    observed={}
    for t in SNAPSHOTS:
        obs=reader.measure(ctx,raw[f's{t}_V'],ctx['readout'])[1]
        ref.scores(ctx['codes'],dict(obs,**{f's{END}_V':raw[f's{t}_V']}),ctx['readout'])
        observed.update({f's{t}_{k}':v for k,v in obs.items()})
    return observed

def block(directory,index,role):
    import analysis
    assert index in selected(role);tick=time.monotonic()
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);(directory/'physical').mkdir()
    ctx=context(index);body_ctx=body_context(ctx);cc,dd,families=schedule(role)
    config=dict(study='TT039',block=index,role=role,corruptions=cc,draws=dd,families=families,arms=ARMS,
        original_writing_budgets=BUDGETS,original_writing_windows=WINDOWS,body_fields=BODY_FIELDS,
        body_endpoint=END,body_checkpoints=SNAPSHOTS,followup_start=START,reset='uniform',damage='mix100',record_bytes=2048,
        source_config=asdict(ctx['config']),config=asdict(body_ctx['config']),readout=asdict(ctx['readout']),
        production_population_reused=False,recipient_outcomes_reused=False)
    write(directory/'CONFIG.json',config)
    source,bproof=baseline.process(directory/'baseline',ctx,role,True)
    restored,_=baseline.process(directory/'baseline',ctx,role,False)
    for f in families:
        assert source[f]['history']==restored[f]['history']
        for k in source[f]['data']:exact(source[f]['data'][k],restored[f]['data'][k],'saved baseline '+k)
    source_seconds=time.monotonic()-tick
    repairs={};reads={};envs={};logical=[];trajectories=[];rows=[];initial_checks=0;input_checks=0
    repair_aliases=0;reader_aliases=0;repair_seconds=0.;reader_seconds=0.
    repair_address=episode(index,0,1,'repair');assert repair_address==repair_audit.address(index)

    def repair(initial,window):
        nonlocal repair_aliases,repair_seconds
        start=time.monotonic();blob=state_bytes(initial);key=(repair_address,window,digest(blob))
        if key in repairs:
            repair_aliases+=1;value=repairs[key];assert value['initial_bytes']==blob;return value
        name=f'physical/repair_{len(repairs):04d}'
        raw,meta=kernel.repair(model.boundary.runtime_context(body_ctx),initial,repair_address,*window)
        body=observation(body_ctx,raw);terminal={k:body[f's{END}_{k}'] for k in OBS_KEYS}
        proof=repair_audit.repair(body_ctx,initial,window,raw,meta,terminal,True)
        assert proof==dict(native_arrays=4*len(REPAIR_SNAPSHOTS),max_native_error=0.,rng_match=True)
        assert meta['input_sha256']==model.source.base.state_digest(initial)
        rp=directory/(name+'.npz');bp=directory/(name+'_body.npz');save(rp,raw);save(bp,body)
        record=dict(address=repair_address,window=window,state_sha256=key[2],metadata=meta,proof=proof,
            files=dict(repair=sha(rp),body=sha(bp)),arrays=dict(repair=identities(raw),body=identities(body)))
        write(directory/(name+'.json'),record)
        restored_raw=arrays(rp);restored_body=arrays(bp)
        repair_audit.repair(body_ctx,initial,window,restored_raw,meta,{k:restored_body[f's{END}_{k}'] for k in OBS_KEYS},False)
        for t in SNAPSHOTS:
            ref.scores(body_ctx['codes'],dict({k:restored_body[f's{t}_{k}'] for k in OBS_KEYS},
                **{f's{END}_V':restored_raw[f's{t}_V']}),body_ctx['readout'])
        value=dict(name=name,initial_bytes=blob,raw=raw,body=body,metadata=meta)
        repairs[key]=value;repair_seconds+=time.monotonic()-start;return value

    def receive(packet,c,d):
        nonlocal reader_aliases,reader_seconds
        start=time.monotonic();addr=address(role,index,c,d);key=(addr,digest(packet))
        assert addr==receiving_audit.address(role,index,c,d)
        if key in reads:
            reader_aliases+=1;value=reads[key];assert value['packet']==packet;return value
        name=f'physical/reader_{len(reads):04d}'
        raw,meta=receiving.read(ctx,packet,addr,ctx['readout'])
        proof=receiving_audit.read(ctx,packet,ctx['readout'],role,index,c,d,raw,meta,True)
        assert proof==dict(native_arrays=12,max_native_error=0.,rng_match=True,carrier_bytes_per_record=2048)
        env=receiving_audit.paired(raw,meta);assert envs.setdefault(f'{c}:{d}',env)==env
        rp=directory/(name+'.npz');save(rp,raw)
        write(directory/(name+'.json'),dict(address=addr,corruption=c,draw=d,packet_sha256=key[1],metadata=meta,
            proof=proof,environment=env,sha256=sha(rp),arrays=identities(raw)))
        receiving_audit.read(ctx,packet,ctx['readout'],role,index,c,d,arrays(rp),meta,False)
        value=dict(name=name,packet=packet,prob=raw['probabilities'],environment=env)
        reads[key]=value;reader_seconds+=time.monotonic()-start;return value

    for c,f in itertools.product(range(cc),families):
        data=source[f]['data']
        values,meta=intervention.build(ctx['tissue'],ctx['config'].norm,ctx['api']['project_theta'],data['incoming'],role,index,c)
        input_checks+=intervention_audit.check(ctx,data,role,c,values,meta)
        path=directory/'physical'/f'input_{c}_{f}';save(path.with_suffix('.npz'),values)
        write(path.with_suffix('.json'),dict(metadata=meta,arrays=identities(values),sha256=sha(path.with_suffix('.npz'))))
        for mi,m in enumerate(MASKS):
            for owner in SOURCES:
                initial=intervention.initial(data['developed_V'],values['jitter'],ctx['tissue'].resting,values['incoming'],m,owner)
                initial_checks+=intervention_audit.state(ctx,data['developed_V'],values['jitter'],values['incoming'],m,owner,initial)
                rr=[repair(initial,window) for window in WINDOWS];preserve,early,late,full=rr
                assert len({r['metadata']['rng_final'] for r in rr})==1
                for t in (0,1,100):
                    for k in KEYS:exact(early['raw'][f's{t}_{k}'],full['raw'][f's{t}_{k}'],'early full-writing prefix')
                for t in (0,1,100,101,900):
                    for k in KEYS:exact(late['raw'][f's{t}_{k}'],preserve['raw'][f's{t}_{k}'],'late preserved prefix')
                for r in rr:
                    for k in KEYS:exact(r['raw']['s0_'+k],initial[k],'matched initial state')
                    for t in SNAPSHOTS[1:]:exact(r['raw'][f's{t}_theta'],r['raw']['s1000_theta'],'all post-1000 packets held')
                exact(preserve['raw']['s1900_theta'],values['incoming'],'preservation packet')
                exact(early['raw']['s1900_theta'],full['raw']['s100_theta'],'early stopped packet equals full prefix')
                reader_links={};credit_sets={}
                for d in range(dd):
                    original=receive(values['original'].tobytes(),c,d)
                    received=[receive(r['raw']['s1900_theta'].tobytes(),c,d) for r in rr]
                    reader_links[str(d)]=dict(original=original['name'],arms=[r['name'] for r in received]);credit_sets[d]=(original,received)
                logical.append(dict(corruption=c,family=f,mask=m,body_source=owner,initial_state_sha256=digest(state_bytes(initial)),
                    repairs=[r['name'] for r in rr],readers=reader_links))
                for w in range(16):
                    base=dict(block=index,corruption=c,family=f,mask=m,body_source=owner,world=w,message=w//4,replicate=w%4,
                        geometry=GEOMETRIES[geometry(mi,w)],template_message=mi^1,reset='uniform',
                        developed_score=source[f]['history'][w]['developed_score'],repairs=[r['name'] for r in rr])
                    trajectories.append(dict(base,body_by_time={str(t):{field:credit(r['body'][f's{t}_probabilities'],w,mi).tolist()
                        for field,r in zip(BODY_FIELDS,rr)} for t in SNAPSHOTS}))
                    for d,(original,received) in credit_sets.items():
                        rows.append(dict(base,draw=d,original=credit(original['prob'],w,mi).tolist(),
                            **{field:credit(r['prob'],w,mi).tolist() for field,r in zip(READER_FIELDS,received)}))
    count=cc*len(families)*4*3
    assert len(logical)==count and len(trajectories)==count*16 and len(rows)==count*16*dd
    assert len(repairs)+repair_aliases==4*count and len(repairs)<=cc*(8*len(families)+1)*4
    assert len(reads)+reader_aliases==5*count*dd and len(reads)<=cc*dd*(len(families)+1+3*(8*len(families)+1))
    assert len(envs)==cc*dd and len({e['birth_sha256'] for e in envs.values()})==cc*dd
    proof=dict(labelled_cases=len(trajectories),body_checkpoint_observations=len(trajectories)*len(SNAPSHOTS),
        paired_rows=len(rows),logical_repairs=4*count,new_repair_batches=len(repairs),new_repair_worlds=16*len(repairs),
        repair_aliases=repair_aliases,new_reader_batches=len(reads),new_receiving_assays=16*len(reads),reader_aliases=reader_aliases,
        new_independent_receiving_draws=len(envs),baseline_native_arrays=bproof['baseline_native_arrays'],
        baseline_saved_arrays=bproof['baseline_saved_arrays'],
        native_arrays_replayed=bproof['baseline_native_arrays']+4*len(REPAIR_SNAPSHOTS)*len(repairs)+12*len(reads),
        saved_new_arrays=bproof['baseline_saved_arrays']+(4*len(REPAIR_SNAPSHOTS)+4*len(SNAPSHOTS))*len(repairs)+16*len(reads)+4*cc*len(families),
        body_scores_checked=len(SNAPSHOTS)*len(repairs),initial_state_arrays_checked=initial_checks,
        intervention_arrays_checked=input_checks,early_full_prefix_arrays_checked=12*count,
        late_preserve_prefix_arrays_checked=20*count,post1000_saved_packet_identities=16*count,
        preserved_packet_identities=count,early_packet_identities=count,max_native_error=0.)
    write(directory/'ROWS.json',rows);write(directory/'BODY_TRAJECTORY.json',trajectories);write(directory/'ALIASES.json',logical)
    write(directory/'CHECK.json',dict(status='PASS',verification=proof,environment=envs,all_cases_retained=True,
        independent_full_physical_replay=True,source_population_reused=False,matched_physical_endpoint=END))
    start=time.monotonic();aggregates,change=analysis.trajectory(config,rows,trajectories)
    for t,aggregate in zip(SNAPSHOTS,aggregates):save(directory/f'AGGREGATE_{t}.npz',aggregate)
    save(directory/'BODY_CHANGE.npz',change)
    saved,saved_change=analysis.trajectory(read(directory/'CONFIG.json'),read(directory/'ROWS.json'),read(directory/'BODY_TRAJECTORY.json'))
    for a,b in zip(aggregates,saved):
        for k in a:exact(a[k],b[k],'saved aggregation '+k)
    for k in change:exact(change[k],saved_change[k],'saved body change '+k)
    analysis_seconds=time.monotonic()-start;write(directory/'USED_INPUTS.json',{})
    result=dict(status='PASS',block=index,seconds=time.monotonic()-tick,source_seconds=source_seconds,
        repair_seconds=repair_seconds,reader_seconds=reader_seconds,analysis_seconds=analysis_seconds,verification=proof,
        outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        retained_bytes=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()))
    write(directory/'COMPLETE.json',result);return result
