"""Unselected fresh blocks, fixed writing episode, paired future reads."""
from common import *
from sources import Source, observe, identity
import analysis, audit, kernel, storage, itertools, time


def endpoints(body, world, mask):
    probability=[]; margin=[]
    for t in TIMES:
        probability.append(credit(body[f's{t}_probabilities'],world,mask))
        s=body[f's{t}_scores'][world]
        margin.append([s[k]-max(s[j] for j in range(4) if j!=k) for k in labels(world,mask)])
    return np.asarray(probability),np.asarray(margin)


def paired(branches, role):
    streams={}
    for profile in PROFILES:
        assert len(branches[profile])==initial_count(profile,role)
        for by_future in branches[profile]:
            assert len(by_future)==futures(role)
            for future,pair in enumerate(by_future):
                for packet,v in enumerate(pair):
                    m=v['metadata']; signature=(m['rng_start'],m['rng_final'],encoded(m['checkpoint_rng']))
                    assert streams.setdefault(future,signature)==signature
                    assert m['profile']=='fresh' and m['feedback'] is False and m['c_m']==0
                    for k in KEYS:exact(v['initial'][k],by_future[0][packet]['initial'][k],'restored fixed start')
                    exact(v['initial']['theta'],branches['continuing'][0][0][packet]['initial']['theta'],'same supplied packet')
                for k in BODY_KEYS:exact(pair[0]['initial'][k],pair[1]['initial'][k],'matched receiver')
    assert len(streams)==len({v[0] for v in streams.values()})==futures(role)


def block(directory,index,role):
    assert index in selected(role)
    if role=='confirmation':
        frozen=read(ROOT/'FREEZE.json');assert frozen['blocks']==list(BLOCKS) and not frozen['new_production_outcomes_generated']
    tick=time.monotonic(); directory=Path(directory); directory.mkdir(parents=True,exist_ok=False); (directory/'physical').mkdir()
    source=Source(directory/'source',index,role); ctx=with_times(source.ctx,TIMES); nf=futures(role)
    seeds=read(ROOT/'SEEDS.json')['addresses'][role][str(index)]
    assert seeds['future']==[future_address(role,index,k) for k in range(nf)]
    write(directory/'CONFIG.json',dict(study='TT046',block=index,role=role,profiles=PROFILES,arms=ARMS,times=TIMES,
        config=asdict(ctx['config']),readout=asdict(ctx['readout']),feedback_gain=0.,rho=.002,
        writing_windows=WINDOWS,actual_starting_states={p:initial_count(p,role) for p in PROFILES},new_futures_per_fixed_state=nf,
        addresses=seeds,source_population_reused=False,population_confirmation=role=='confirmation',all_cases_retained=True))
    physical={}; streams={}; logical=[]; cases=[]; original={}
    data={name:[] for name in (*PROFILES,*(p+'_margin' for p in PROFILES),'original')}
    aliases=logical_count=0; owners=dict.fromkeys(PROFILES,0); physical_seconds=0.; physical_bytes=0
    def continued(profile,addr,initial):
        nonlocal aliases,physical_seconds,physical_bytes
        h=identity(addr,initial); blob=state_bytes(initial)
        if h in physical:
            aliases+=1;value=physical[h];assert value['bytes']==blob
            return dict(name=value['name'],body=arrays(directory/(value['name']+'_body.npz')),
                metadata=read(directory/(value['name']+'.json'))['metadata'],initial=initial)
        assert len(physical)<physical_bound(role);batch_space();start=time.monotonic()
        name=f'physical/continuation_{len(physical):05d}'
        raw,meta=kernel.resume(model.boundary.runtime_context(ctx),initial,'fresh',addr,False)
        body=observe(ctx,raw,TIMES);proof=audit.replay(ctx,initial,'fresh',addr,False,raw,meta,body)
        assert proof==dict(native_arrays=24,body_scores=6,max_native_error=0.,rng_match=True)
        p=directory/(name+'.npz');bp=directory/(name+'_body.npz');storage.save_raw(p,raw);save(bp,body)
        write(p.with_suffix('.json'),dict(physical_identity=h,metadata=meta,proof=proof,files=dict(state=sha(p),body=sha(bp)),
            arrays=dict(expanded_state=identities(raw),packed_state=identities(storage.pack(raw)),body=identities(body)),
            stored_state_arrays=19,expanded_state_arrays=24,storage_lossless=True))
        retained=sum(x.stat().st_size for x in (p,bp,p.with_suffix('.json')));assert retained<=BATCH_BYTES
        physical_bytes+=retained;physical[h]=dict(name=name,bytes=blob);owners[profile]+=1;physical_seconds+=time.monotonic()-start
        return dict(name=name,body=body,metadata=meta,initial=initial)
    for damage,mask in itertools.product(DAMAGE,MASKS):
        branches={p:[[[None]*2 for _ in range(nf)] for _ in range(initial_count(p,role))] for p in PROFILES}
        for p in PROFILES:
            for b in range(initial_count(p,role)):
                for f in range(nf):
                    for packet in (0,1):
                        initial=source.initial(damage,mask,p,b,packet);addr=future_address(role,index,f)
                        value=continued(p,addr,initial);branches[p][b][f][packet]=value;logical_count+=1
                        m=value['metadata'];sig=(m['rng_start'],m['rng_final'],encoded(m['checkpoint_rng']))
                        assert streams.setdefault(f,sig)==sig
                        if damage=='mix000' and p=='fresh':
                            if packet==0:original.setdefault((b,f),value)
        paired(branches,role);mi=MASKS.index(mask)
        logical.append(dict(damage=damage,family='residual',mask=mask,body_source='own',
            source_writers=[r['name'] for r in source.episode(damage,mask)],
            profiles={p:[[[v['name'] for v in pair] for pair in by_future] for by_future in branches[p]] for p in PROFILES},
            original=[[original[b,f]['name'] for f in range(nf)] for b in range(births(role))]))
        for w in range(16):
            cases.append(dict(block=index,corruption=0,family='residual',damage=damage,mask=mask,body_source='own',world=w,
                message=w//4,replicate=w%4,geometry=GEOMETRIES[geometry(mi,w)],developed_score=source.history[w]['developed_score']))
            for p in PROFILES:
                by_packet=[[[endpoints(pair[packet]['body'],w,mi) for pair in by_future] for by_future in branches[p]] for packet in (0,1)]
                data[p].append([[[v[0] for v in one] for one in each] for each in by_packet])
                data[p+'_margin'].append([[[v[1] for v in one] for one in each] for each in by_packet])
            data['original'].append([[credit(original[b,f]['body']['s1000_probabilities'],w,mi) for f in range(nf)] for b in range(births(role))])
    values={k:np.asarray(v,dtype=np.float64) if k.endswith('_margin') else analysis.units(v) for k,v in data.items()}
    assert len(cases)==192 and len(logical)==12 and logical_count==12*2*(1+births(role))*nf
    assert len(physical)+aliases==logical_count and len(physical)<=physical_bound(role)
    write(directory/'ALIASES.json',logical);write(directory/'CASES.json',cases);save(directory/'ENDPOINTS.npz',values)
    start=time.monotonic();local=analysis.local(values);save(directory/'LOCAL.npz',local)
    agg=analysis.block(cases,values);save(directory/'AGGREGATE.npz',agg)
    restored=arrays(directory/'ENDPOINTS.npz');again=analysis.block(read(directory/'CASES.json'),restored)
    for k in agg:exact(agg[k],again[k],'saved aggregation '+k)
    for k,v in analysis.local(restored).items():exact(local[k],v,'saved local '+k)
    source_bytes=sum(p.stat().st_size for p in source.folder.rglob('*') if p.is_file());assert source_bytes<=SOURCE_BYTES
    proof=dict(labelled_cases=len(cases),logical_continuations=logical_count,physical_continuations=len(physical),continuation_aliases=aliases,
        continuing_physical=owners['continuing'],fresh_physical=owners['fresh'],simulated_world_continuations=16*len(physical),
        independent_native_arrays=24*len(physical),body_scores_checked=6*len(physical),source_native_arrays=source.proof['baseline_native_arrays'],
        source_saved_arrays=source.proof['baseline_saved_arrays'],writer_native_arrays=source.writer_native_arrays,writer_batches=24,
        source_bridge_arrays=source.bridge_arrays,initial_state_arrays_checked=source.initial_checks,mixture_arrays_checked=source.mixture_checks,
        independent_block_future_banks=nf,losslessly_stored_physical_packages=len(physical),max_native_error=0.)
    write(directory/'CHECK.json',dict(status='PASS',verification=proof,all_cases_retained=True,source_population_reused=False,
        full_independent_replay=True,physical_package_bytes=physical_bytes,source_writer_bytes=source_bytes,
        actual_starting_states={p:initial_count(p,role) for p in PROFILES},new_futures_per_fixed_state=nf))
    verify(source.used);write(directory/'USED_INPUTS.json',source.used)
    receipt=dict(status='PASS',block=index,seconds=time.monotonic()-tick,source_seconds=source.source_seconds,
        writer_seconds=source.writer_seconds,physical_seconds=physical_seconds,analysis_seconds=time.monotonic()-start,verification=proof,
        physical_package_bytes=physical_bytes,source_writer_bytes=source_bytes,
        outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        retained_bytes=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()))
    write(directory/'COMPLETE.json',receipt);space();return receipt
