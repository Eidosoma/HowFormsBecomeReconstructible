"""Acquire all fresh arms and paired recipients with independent physical replay."""
from common import *
import itertools,time
import baseline,intervention,intervention_audit,kernel,repair_audit,receiving,receiving_audit

def context(index):
    assert index in (*BLOCKS,*EXCLUDED,28000000)
    if index in BLOCKS:
        assert (ROOT/'FREEZE.json').is_file(),'production context requires freeze'
        frozen=read(ROOT/'FREEZE.json');assert frozen['blocks']==list(BLOCKS)
        assert frozen['new_production_outcomes_generated'] is False
    cfg,rcfg=configs();ctx=model.source.context(index,cfg)|{'readout':rcfg}
    exact(ctx['codes'],codebook(),'independent observer codebook');return ctx
def observation(ctx,v):
    obs=reader.measure(ctx,v,ctx['readout'])[1]
    ref.scores(ctx['codes'],dict(s1000_V=v,**obs),ctx['readout']);return obs

def block(directory,index,role):
    import analysis
    assert index in selected(role);tick=time.monotonic()
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);(directory/'physical').mkdir()
    ctx=context(index);cc,dd,families=schedule(role)
    config=dict(study='TT036',block=index,role=role,corruptions=cc,draws=dd,families=families,budgets=BUDGETS,
        body_endpoint=1000,reset='uniform',damage='mix100',record_bytes=2048,config=asdict(ctx['config']),readout=asdict(ctx['readout']))
    write(directory/'CONFIG.json',config)
    source,bproof=baseline.process(directory/'baseline',ctx,role,True)
    restored,_=baseline.process(directory/'baseline',ctx,role,False)
    for f in families:
        assert source[f]['history']==restored[f]['history']
        for k in source[f]['data']:exact(source[f]['data'][k],restored[f]['data'][k],'saved baseline '+k)
    source_seconds=time.monotonic()-tick
    repairs={};reads={};envs={};logical=[];bodies=[];rows=[];initial_checks=0;input_checks=0
    repair_aliases=0;reader_aliases=0;repair_seconds=0.;reader_seconds=0.
    repair_address=kernel.repair_address(index,0,1,'repair');assert repair_address==repair_audit.address(index)

    def repair(initial,budget):
        nonlocal repair_aliases,repair_seconds
        start=time.monotonic();blob=state_bytes(initial);key=(repair_address,budget,digest(blob))
        if key in repairs:
            repair_aliases+=1;value=repairs[key];assert value['initial_bytes']==blob;return value
        name=f'physical/repair_{len(repairs):04d}'
        raw,meta=kernel.repair(model.boundary.runtime_context(ctx),initial,repair_address,budget)
        body=observation(ctx,raw['s1000_V']);proof=repair_audit.repair(ctx,initial,budget,raw,meta,body,True)
        assert proof==dict(native_arrays=20,max_native_error=0.,rng_match=True)
        assert meta['input_sha256']==model.source.base.state_digest(initial)
        rp=directory/(name+'.npz');bp=directory/(name+'_body.npz');save(rp,raw);save(bp,body)
        record=dict(address=repair_address,budget=budget,state_sha256=key[2],metadata=meta,proof=proof,
            files=dict(repair=sha(rp),body=sha(bp)),arrays=dict(repair=identities(raw),body=identities(body)))
        write(directory/(name+'.json'),record)
        repair_audit.repair(ctx,initial,budget,arrays(rp),meta,arrays(bp),False)
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
        data=source[f]['data'];values,meta=intervention.build(ctx['tissue'],ctx['config'].norm,ctx['api']['project_theta'],data['incoming'],role,index,c)
        input_checks+=intervention_audit.check(ctx,data,role,c,values,meta)
        path=directory/'physical'/f'input_{c}_{f}'
        save(path.with_suffix('.npz'),values);write(path.with_suffix('.json'),dict(metadata=meta,arrays=identities(values),sha256=sha(path.with_suffix('.npz'))))
        for mi,m in enumerate(MASKS):
            for o in SOURCES:
                initial=intervention.initial(data['developed_V'],values['jitter'],ctx['tissue'].resting,values['incoming'],m,o)
                initial_checks+=intervention_audit.state(ctx,data['developed_V'],values['jitter'],values['incoming'],m,o,initial)
                rr=[repair(initial,b) for b in BUDGETS];preserve,stop,full=rr
                assert len({r['metadata']['rng_final'] for r in rr})==1
                for t in (0,1,100):
                    for k in KEYS:exact(stop['raw'][f's{t}_{k}'],full['raw'][f's{t}_{k}'],'full-writing prefix')
                for r in rr:
                    for k in KEYS:exact(r['raw']['s0_'+k],initial[k],'matched initial state')
                exact(preserve['raw']['s1000_theta'],values['incoming'],'preservation packet')
                exact(stop['raw']['s1000_theta'],full['raw']['s100_theta'],'stopped packet equals writing prefix')
                reader_links={};credit_sets={}
                for d in range(dd):
                    original=receive(values['original'].tobytes(),c,d)
                    received=[receive(r['raw']['s1000_theta'].tobytes(),c,d) for r in rr]
                    reader_links[str(d)]=dict(original=original['name'],budgets=[r['name'] for r in received])
                    credit_sets[d]=(original,received)
                logical.append(dict(corruption=c,family=f,mask=m,body_source=o,initial_state_sha256=digest(state_bytes(initial)),
                    repairs=[r['name'] for r in rr],readers=reader_links))
                for w in range(16):
                    base=dict(block=index,corruption=c,family=f,mask=m,body_source=o,world=w,message=w//4,replicate=w%4,
                        geometry=GEOMETRIES[geometry(mi,w)],template_message=mi^1,reset='uniform',
                        developed_score=source[f]['history'][w]['developed_score'],repairs=[r['name'] for r in rr])
                    body=dict(base,**{field:credit(r['body']['probabilities'],w,mi).tolist() for field,r in zip(('preserve1000','stopped1000','body1000'),rr)})
                    bodies.append(body)
                    for d,(original,received) in credit_sets.items():
                        rows.append(dict(base,draw=d,original=credit(original['prob'],w,mi).tolist(),
                            **{field:credit(r['prob'],w,mi).tolist() for field,r in zip(('incoming','after100','after1000'),received)}))
    count=cc*len(families)*4*3
    assert len(logical)==count and len(bodies)==count*16 and len(rows)==count*16*dd
    assert len(repairs)+repair_aliases==3*count and len(repairs)<=cc*(8*len(families)+1)*3
    assert len(reads)+reader_aliases==4*count*dd and len(reads)<=cc*dd*(len(families)+1+2*(8*len(families)+1))
    assert len(envs)==cc*dd and len({e['birth_sha256'] for e in envs.values()})==cc*dd
    proof=dict(labelled_cases=len(bodies),paired_rows=len(rows),logical_repairs=3*count,
        new_repair_batches=len(repairs),new_repair_worlds=16*len(repairs),repair_aliases=repair_aliases,
        new_reader_batches=len(reads),new_receiving_assays=16*len(reads),reader_aliases=reader_aliases,
        new_independent_receiving_draws=len(envs),baseline_native_arrays=bproof['baseline_native_arrays'],
        baseline_saved_arrays=bproof['baseline_saved_arrays'],native_arrays_replayed=bproof['baseline_native_arrays']+20*len(repairs)+12*len(reads),
        saved_new_arrays=bproof['baseline_saved_arrays']+24*len(repairs)+16*len(reads)+4*cc*len(families),
        initial_state_arrays_checked=initial_checks,intervention_arrays_checked=input_checks,prefix_arrays_checked=12*count,
        preserved_packet_identities=count,stopped_packet_identities=count,max_native_error=0.)
    write(directory/'ROWS.json',rows);write(directory/'BODIES.json',bodies);write(directory/'ALIASES.json',logical)
    write(directory/'CHECK.json',dict(status='PASS',verification=proof,environment=envs,all_cases_retained=True,
        independent_full_physical_replay=True,source_population_reused=False,matched_physical_endpoint=1000))
    start=time.monotonic();agg=analysis.block(config,rows,bodies);save(directory/'AGGREGATE.npz',agg)
    again=analysis.block(read(directory/'CONFIG.json'),read(directory/'ROWS.json'),read(directory/'BODIES.json'))
    for k in agg:exact(agg[k],again[k],'saved aggregation '+k)
    analysis_seconds=time.monotonic()-start;write(directory/'USED_INPUTS.json',{})
    result=dict(status='PASS',block=index,seconds=time.monotonic()-tick,source_seconds=source_seconds,
        repair_seconds=repair_seconds,reader_seconds=reader_seconds,analysis_seconds=analysis_seconds,verification=proof,
        outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        retained_bytes=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()))
    write(directory/'COMPLETE.json',result);return result
