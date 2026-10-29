"""Native reset interventions, independent replay, and exact-state reuse."""
from dataclasses import asdict
import time
from common import *
import design
import kernel
import masks
import reset
import reset_audit
import receiving
import receiving_audit


def context(index,role):
    assert index in design.indices(role)
    if role=='development':assert (ROOT/'FREEZE.json').exists()
    cfg,rcfg=design.configs(role)
    return model.source.context(index,cfg)|{'readout':rcfg}


def credit(probabilities,w,template):
    labels=(w//4,(w//4+2)%4,template,template^1)
    return [float(probabilities[w,m]) for m in labels]


def templates(ctx,data):
    shape=np.where(data['fresh'][0],1.,-1.)
    labels=[i for i,v in enumerate(ctx['codes']) if np.array_equal(v,shape)]
    assert len(labels)==1 and np.array_equal(ctx['codes'][labels[0]^1],-shape)
    return labels[0]


def bridge(source,owner,label,entries,custody):
    stem=source['target']/'mix100'/owner/f'corrected_{label:04d}'
    meta=custody.json(str(stem)+'.json');raw=custody.arrays(str(stem)+'_repair.npz');body=custody.arrays(str(stem)+'_body.npz')
    assert meta['files']==dict(repair=sha(str(stem)+'_repair.npz'),body=sha(str(stem)+'_body.npz'))
    assert meta['arrays']==dict(repair=identities(raw),body=identities(body))
    for k,v in raw.items():ref.exact(np.stack([entries[m]['raw'][k][w] for w,m in enumerate(source['actual'])]),v,'TT028 corrected actual mask '+k)
    for k,v in body.items():ref.exact(np.stack([entries[m]['body'][k][w] for w,m in enumerate(source['actual'])]),v,'TT028 corrected body '+k)
    return len(raw)+len(body)


def process(directory,index,role,acquire):
    tick=time.monotonic();ctx=context(index,role);cfg=ctx['config'];rcfg=ctx['readout'];cc,dd=design.schedule(role);custody=Custody(role)
    config=json.loads(serialized(dict(block=index,role=role,config=asdict(cfg),readout=asdict(rcfg),
        families=design.families(role),damage=['mix100'],masks=design.MASKS,bodies=design.BODIES,resets=design.RESETS,
        budgets=design.BUDGETS,credits=design.CREDITS,corruptions=cc,draws=dd)))
    if acquire:directory.mkdir(parents=True,exist_ok=False);(directory/'physical').mkdir();write_json(directory/'CONFIG.json',config)
    else:assert config==read_json(directory/'CONFIG.json')
    repairs={};readers={};rows=[];brows=[];envs={};geometries={};original_masks={};logical=[];sources={}
    timings=dict(source_seconds=0.,repair_seconds=0.,reader_seconds=0.,row_seconds=0.)
    proof=dict(design.expected(role,1));bridges=bridge_arrays=reader_requests=0;repair_rng=None
    repair_key=kernel.repair_address(index,0,1,'repair');assert repair_key==reset_audit.repair_address(index)

    def do_repair(data,variant,label):
        nonlocal repair_rng
        state=reset.initial(data,ctx['tissue'].resting,variant);budget=design.budget(label,role);state_bytes=reset.state_bytes(state)
        key=(budget,digest(state_bytes));first=key not in repairs
        if first:
            name=f'physical/repair_{len(repairs):04d}';rp=directory/(name+'.npz');bp=directory/(name+'_body.npz');mp=directory/(name+'.json')
            if acquire:
                raw,meta=kernel.repair(model.boundary.runtime_context(ctx),state,repair_key,budget)
                body=reader.measure(ctx,raw[f's{cfg.sweeps}_V'],rcfg)[1]
                checked=reset_audit.repair(ctx,data,variant,budget,raw,meta,body,True)
                write_arrays(rp,raw);write_arrays(bp,body)
                record=dict(address=repair_key,budget=budget,state_sha256=key[1],metadata=meta,proof=checked,
                    files=dict(repair=sha(rp),body=sha(bp)),arrays=dict(repair=identities(raw),body=identities(body)))
                write_json(mp,record)
            else:
                raw=arrays(rp);body=arrays(bp);record=read_json(mp);meta=record['metadata'];checked=record['proof']
                assert record['address']==repair_key and record['budget']==budget and record['state_sha256']==key[1]
                assert record['files']==dict(repair=sha(rp),body=sha(bp)) and record['arrays']==dict(repair=identities(raw),body=identities(body))
                reset_audit.repair(ctx,data,variant,budget,raw,meta,body,False)
            assert checked==dict(native_arrays=20,max_native_error=0.,rng_match=True)
            assert meta['input_sha256']==model.source.base.state_digest(state)
            if repair_rng is None:repair_rng=meta['rng_final']
            else:assert repair_rng==meta['rng_final']
            repairs[key]=dict(name=name,raw=raw,body=body,meta=meta,initial_bytes=state_bytes,budget=budget)
        value=repairs[key]
        assert value['initial_bytes']==state_bytes and value['budget']==budget
        if not first:reset_audit.repair(ctx,data,variant,budget,value['raw'],value['meta'],value['body'],False)
        return value,not first

    def do_read(packet,c,draw):
        nonlocal reader_requests
        reader_requests+=1;address=design.address(role,index,c,draw);assert address==receiving_audit.address(role,index,c,draw)
        key=(address,digest(packet));first=key not in readers
        if first:
            name=f'physical/reader_{len(readers):04d}';rp=directory/(name+'.npz');mp=directory/(name+'.json')
            if acquire:
                raw,meta=receiving.read(ctx,packet,address,rcfg)
                checked=receiving_audit.read(ctx,packet,rcfg,role,index,c,draw,raw,meta,True)
                env=receiving_audit.paired(raw,meta);write_arrays(rp,raw)
                write_json(mp,dict(address=address,corruption=c,draw=draw,packet_sha256=key[1],metadata=meta,
                    proof=checked,environment=env,sha256=sha(rp),arrays=identities(raw)))
            else:
                raw=arrays(rp);record=read_json(mp);meta=record['metadata'];checked=record['proof'];env=record['environment']
                assert record['address']==address and record['corruption']==c and record['draw']==draw and record['packet_sha256']==key[1]
                assert record['sha256']==sha(rp) and record['arrays']==identities(raw)
                receiving_audit.read(ctx,packet,rcfg,role,index,c,draw,raw,meta,False)
                assert env==receiving_audit.paired(raw,meta)
            assert checked==dict(native_arrays=12,max_native_error=0.,rng_match=True,carrier_bytes_per_record=2048)
            ek=f'{c}:{draw}';assert envs.setdefault(ek,env)==env
            readers[key]=dict(name=name,packet=packet,probabilities=raw['probabilities'],environment=env)
        value=readers[key];assert value['packet']==packet
        return value

    for c in range(cc):
        for family in design.families(role):
            t=time.monotonic();source=masks.source(ctx,role,c,family,custody);sources[c,family]=source
            original_masks[family]=source['actual'];timings['source_seconds']+=time.monotonic()-t
            entries={};label_links={};t=time.monotonic()
            for mask in design.MASKS:
                own=masks.physical(source['initial']['developed_V'],source['values']['jitter'],ctx['tissue'].resting,source['values']['mix100'],mask)
                geo=masks.audit_mask(ctx,source,'mix100',mask,own);assert geometries.setdefault(mask,geo)==geo
                template=templates(ctx,own)
                for owner in design.BODIES:
                    data=reset.physical(own,owner,source['values']['jitter'],ctx['tissue'].resting)
                    reset_audit.physical(own,source['values']['jitter'],ctx['tissue'].resting,owner,data)
                    for variant in design.RESETS:
                        for label in design.BUDGETS:
                            value,alias=do_repair(data,variant,label)
                            entries[mask,owner,variant,label]=value
                            link=dict(corruption=c,family=family,mask=mask,body_source=owner,reset=variant,budget_label=label,
                                budget=design.budget(label,role),repair=value['name'],exact_initial_state_alias=alias,
                                template_message=template,reader_by_draw={})
                            logical.append(link);label_links[mask,owner,variant,label]=link
                            if label==0:assert value['raw'][f's{cfg.sweeps}_theta'].tobytes()==source['values']['mix100'].tobytes()
            if role=='development':
                for owner in design.BODIES:
                    for label in design.BUDGETS:
                        bridge_arrays+=bridge(source,owner,label,{m:entries[m,owner,'corrected',label] for m in design.MASKS},custody);bridges+=1
            # The neutral ablation truly removes the physical mask from the initial state.
            for label in design.BUDGETS:
                uniform=[entries[m,'neutral','uniform',label] for m in design.MASKS]
                assert len({v['name'] for v in uniform})==1
                for mi,m in enumerate(design.MASKS):
                    assert entries[m,'neutral','reversed',label]['name']==entries[design.MASKS[mi^1],'neutral','corrected',label]['name']
            timings['repair_seconds']+=time.monotonic()-t
            measured={};baseline={};t=time.monotonic()
            for draw in range(dd):
                original=do_read(source['values']['original'].tobytes(),c,draw)
                incoming=do_read(source['values']['mix100'].tobytes(),c,draw)
                assert abs(float(incoming['probabilities'][np.arange(16),np.arange(16)//4].mean())-.25)<2e-15
                baseline[draw]=dict(original=original,incoming=incoming)
                for mask in design.MASKS:
                    for owner in design.BODIES:
                        for variant in design.RESETS:
                            output=do_read(entries[mask,owner,variant,1000]['raw'][f's{cfg.sweeps}_theta'].tobytes(),c,draw)
                            measured[draw,mask,owner,variant,0]=incoming;measured[draw,mask,owner,variant,1000]=output
                            for label,value in ((0,incoming),(1000,output)):
                                label_links[mask,owner,variant,label]['reader_by_draw'][str(draw)]=value['name']
            timings['reader_seconds']+=time.monotonic()-t;t=time.monotonic()
            for mask in design.MASKS:
                template=label_links[mask,'neutral','corrected',0]['template_message']
                for owner in design.BODIES:
                    for variant in design.RESETS:
                        for label in design.BUDGETS:
                            for w,h in enumerate(source['history']):
                                donor=((w//4+2)%4)*4+w%4
                                common=dict(block=index,corruption=c,family=family,damage='mix100',mask=mask,body_source=owner,
                                    reset=variant,budget_label=label,budget=design.budget(label,role),world=w,message=w//4,replicate=w%4,
                                    geometry=geometries[mask][w],actual_mask=source['actual'][w],developed_score=h['developed_score'],
                                    donor_world=donor,source_developed_score=None if owner=='neutral' else source['history'][donor if owner=='foreign' else w]['developed_score'],
                                    template_message=template,repair=entries[mask,owner,variant,label]['name'])
                                body=credit(entries[mask,owner,variant,label]['body']['probabilities'],w,template)
                                preserved=credit(entries[mask,owner,variant,0]['body']['probabilities'],w,template)
                                brows.append(dict(common,credit=body,preserve_credit=preserved))
                                for draw in range(dd):
                                    obs=measured[draw,mask,owner,variant,label]
                                    before=credit(baseline[draw]['incoming']['probabilities'],w,template)
                                    after=credit(obs['probabilities'],w,template)
                                    rows.append(dict(common,draw=draw,incoming=before,outgoing=after,
                                        original=credit(baseline[draw]['original']['probabilities'],w,template),
                                        effect=[a-b for a,b in zip(after,before)],reader=obs['name']))
            timings['row_seconds']+=time.monotonic()-t
    assert bridges==proof['actual_mask_bridges'] and bridge_arrays==proof['actual_mask_arrays']
    assert len(logical)==proof['logical_repairs'] and reader_requests==proof['logical_reader_requests']
    assert len(rows)==proof['paired_rows'] and len(brows)==proof['body_rows'] and len(envs)==proof['receiving_environments']
    assert len({e['birth_sha256'] for e in envs.values()})==len(envs)
    limit=design.upper(role,1);assert len(repairs)<=limit['repair_batches'] and len(readers)<=limit['reader_batches']
    proof.update(repair_batches=len(repairs),reader_batches=len(readers),repair_aliases=len(logical)-len(repairs),
        reader_aliases=reader_requests-len(readers),native_arrays=20*len(repairs)+12*len(readers),saved_arrays=24*len(repairs)+16*len(readers))
    check=dict(status='PASS',verification=proof,geometries=geometries,actual_masks=original_masks,environment=envs,
        all_cases_retained=True,mask_independent_neutral_ablation=True,reversal_complement_identity=True)
    values={'ROWS.json':rows,'BODIES.json':brows,'ALIASES.json':logical,'CHECK.json':check,'USED_SOURCE_FILES.json':custody.used}
    for name,value in values.items():
        if acquire:write_json(directory/name,value)
        else:assert json.loads(serialized(value))==read_json(directory/name),name
    timings.update(seconds=time.monotonic()-tick,repair_batches=len(repairs),reader_batches=len(readers),
        paired_rows=len(rows),body_rows=len(brows),saved_arrays=proof['saved_arrays'])
    if acquire:write_json(directory/'TIMING.json',timings)
    return proof


def saved(directory):
    config=read_json(directory/'CONFIG.json')
    return process(directory,config['block'],config['role'],False)


def block(directory,index,role):
    from analysis import block as summarize
    proof=process(directory,index,role,True);t=time.monotonic()
    assert saved(directory)==proof
    write_json(directory/'SAVED_CHECK.json',dict(status='PASS',verification=proof,new_dynamics=0))
    saved_seconds=time.monotonic()-t;t=time.monotonic();summary=summarize(directory)
    write_json(directory/'SUMMARY.json',summary)
    assert json.loads(serialized(summary))==summarize(directory)
    timing=read_json(directory/'TIMING.json');timing.update(saved_seconds=saved_seconds,analysis_seconds=time.monotonic()-t,
        storage_bytes=dict(repair=sum(p.stat().st_size for p in (directory/'physical').glob('repair_*')),
            reader=sum(p.stat().st_size for p in (directory/'physical').glob('reader_*')),
            other=sum(p.stat().st_size for p in directory.iterdir() if p.is_file())))
    write_json(directory/'BLOCK_TIMING.json',timing)
    return proof
