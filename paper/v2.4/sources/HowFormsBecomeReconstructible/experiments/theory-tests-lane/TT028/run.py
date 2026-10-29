"""Actual packet/body interventions, gated repair and paired finite readers."""
from dataclasses import asdict
import time
from common import *
import audit
import baseline
import design
import intervention
import intervention_audit
import kernel
import receiving
import receiving_audit

def context(index,role):
    if role=='confirmation':assert index in BLOCKS and (ROOT/'FREEZE.json').exists()
    cfg,rcfg=design.configs(role)
    return model.source.context(index,cfg)|{'readout':rcfg}
def rows(index,corruption,family,role,source,bodies,measured):
    _,draws=design.schedule(role);cfg,_=design.configs(role)
    paired=[];body_rows=[]
    for damage in design.damage_levels(role):
        for owner in design.BODIES:
            for arm in design.arms(owner):
                _,budget=design.options(arm,cfg.sweeps)
                value=bodies[damage,owner,arm]
                for world,h in enumerate(source['history']):
                    donor=((world//4+2)%4)*4+world%4;partner=donor//4
                    b=dict(block=index,corruption=corruption,family=family,damage=damage,eta=design.MIX[damage],
                        body_source=owner,arm=arm,world=world,message=world//4,replicate=world%4,budget=budget,
                        developed_score=h['developed_score'],injury_stratum=h['injury_stratum'],donor_world=donor,
                        source_developed_score=None if owner=='neutral' else source['history'][donor if owner=='foreign' else world]['developed_score'],
                        repaired_score=float(value['correctness'][world,0]),
                        repaired_donor_score=float(value['probabilities'][world,partner]),
                        preserve_body=float(bodies[damage,owner,design.PRESERVE]['correctness'][world,0]),
                        full_budget_body=float(bodies[damage,owner,design.FULL]['correctness'][world,0]))
                    body_rows.append(b)
                    for draw in range(draws):
                        m=measured[draw];initial=m[design.incoming_version(damage)];original=m['original']
                        outgoing=m[design.alias(damage,owner,arm)]
                        x=float(initial['correctness'][world,0]);y=float(outgoing['correctness'][world,0])
                        r=dict(b,draw=draw,original=float(original['correctness'][world,0]),incoming=x,outgoing=y,
                            effect=y-x,packet_version=design.alias(damage,owner,arm),
                            original_donor=float(original['probabilities'][world,partner]),
                            incoming_donor=float(initial['probabilities'][world,partner]),
                            outgoing_donor=float(outgoing['probabilities'][world,partner]),
                            full_budget_outgoing=float(m[design.alias(damage,owner,design.FULL)]['correctness'][world,0]),
                            incoming_margin=float(initial['margins'][world,0]),outgoing_margin=float(outgoing['margins'][world,0]))
                        for comparator in design.BODIES:
                            r[comparator+'_outgoing']=(float(m[design.alias(damage,comparator,arm)]['correctness'][world,0]) if arm in design.arms(comparator) else None)
                        if arm==design.PRESERVE:assert x==y
                        paired.append(r)
    return paired,body_rows

def process(directory,index,role,acquire):
    tick=time.monotonic();ctx=context(index,role);cfg=ctx['config'];rcfg=ctx['readout']
    corruptions,draws=design.schedule(role)
    config=json.loads(serialized(dict(role=role,block=index,config=asdict(cfg),readout=asdict(rcfg),
        corruptions=corruptions,draws=draws,arms=design.ARMS,families=design.families(role),
        damage=design.damage_levels(role),body_sources=design.BODIES)))
    if acquire:
        directory.mkdir(parents=True,exist_ok=False);write_json(directory/'CONFIG.json',config)
    else:assert read_json(directory/'CONFIG.json')==config
    start=time.monotonic();sources,baseproof=baseline.process(directory/'baseline',ctx,role,acquire)
    baseline_seconds=time.monotonic()-start
    all_rows=[];all_bodies=[];envs={};repair_envs={};corrupt_envs={};zero_damage={}
    native=baseproof['baseline_native_arrays'];saved_count=baseproof['baseline_saved_arrays']
    repairs=reads=intervention_count=0
    repair_seconds=reader_seconds=0.
    for corruption in range(corruptions):
        for family in design.families(role):
            source=sources[family]
            target=directory/f'corruption_{corruption:02d}'/family
            ipath=target/'INTERVENTIONS.npz';mpath=target/'INTERVENTIONS.json'
            if acquire:
                target.mkdir(parents=True)
                inputs={k:source['data'][k] for k in ('incoming','injured_V','fresh')}
                values,imeta=intervention.build(ctx['tissue'],cfg.norm,ctx['api']['project_theta'],inputs,role,index,corruption)
                iproof=intervention_audit.verify(ctx,source,role,corruption,values,imeta)
                write_arrays(ipath,values)
                write_json(mpath,dict(metadata=imeta,proof=iproof,sha256=sha(ipath),arrays=identities(values)))
            else:
                values=arrays(ipath);record=read_json(mpath);imeta=record['metadata']
                assert sha(ipath)==record['sha256'] and identities(values)==record['arrays']
                assert intervention_audit.verify(ctx,source,role,corruption,values,imeta)==record['proof']
            saved_count+=len(values);intervention_count+=len(values)
            ce={k:digest(values[k].tobytes()) for k in ('noise','mix100','fresh','jitter','neutral_V')}
            ce.update(seed=imeta['corruption_seed'],rng=imeta['corruption_rng_final'])
            if str(corruption) in corrupt_envs:assert corrupt_envs[str(corruption)]==ce
            else:corrupt_envs[str(corruption)]=ce
            packets={'original':values['original'].tobytes()}
            for damage in design.damage_levels(role):packets[design.incoming_version(damage)]=values[damage].tobytes()
            bodies={}
            t=time.monotonic()
            for damage in design.damage_levels(role):
                for owner in design.BODIES:
                    dest=target/damage/owner
                    if acquire:dest.mkdir(parents=True)
                    else:assert {p.name for p in dest.iterdir()}=={a+s for a in design.arms(owner) for s in ('.json','_repair.npz','_body.npz')}
                    data=intervention.data(values,damage,owner)
                    for arm in design.arms(owner):
                        memory,budget=design.options(arm,cfg.sweeps)
                        state=kernel.initial(data['injured_V'],data['incoming'],data['fresh'],ctx['tissue'].resting,memory)
                        key=kernel.repair_address(index,0,1,'repair');assert key==audit.repair_address(index,0)
                        rp=dest/(arm+'_repair.npz');bp=dest/(arm+'_body.npz');mp=dest/(arm+'.json')
                        declared=dict(role=role,block=index,corruption=corruption,family=family,damage=damage,
                            body_source=owner,arm=arm,memory=memory,budget=budget,address=key)
                        if acquire:
                            raw,meta=kernel.repair(model.boundary.runtime_context(ctx),state,key,budget)
                            body=reader.measure(ctx,raw[f's{cfg.sweeps}_V'],rcfg)[1]
                            proof=audit.repair(ctx,data,memory,budget,0,raw,meta,body,True)
                            write_arrays(rp,raw);write_arrays(bp,body)
                            record=dict(declared,metadata=meta,proof=proof,
                                input_packet_sha256=digest(data['incoming'].tobytes()),
                                outgoing_sha256=digest(raw[f's{cfg.sweeps}_theta'].tobytes()),
                                files=dict(repair=sha(rp),body=sha(bp)),arrays=dict(repair=identities(raw),body=identities(body)))
                            write_json(mp,record)
                        else:
                            raw=arrays(rp);body=arrays(bp);record=read_json(mp);meta=record['metadata']
                            for k,v in declared.items():assert record[k]==v
                            assert record['files']==dict(repair=sha(rp),body=sha(bp))
                            assert record['arrays']==dict(repair=identities(raw),body=identities(body))
                            audit.repair(ctx,data,memory,budget,0,raw,meta,body,False)
                            proof=record['proof']
                        assert proof==dict(native_arrays=len(cfg.times)*4,max_native_error=0.,rng_match=True)
                        assert meta['input_sha256']==model.source.base.state_digest(state)
                        incoming=data['incoming'].tobytes();outgoing=raw[f's{cfg.sweeps}_theta'].tobytes()
                        assert record['input_packet_sha256']==digest(incoming) and record['outgoing_sha256']==digest(outgoing)
                        version=design.alias(damage,owner,arm)
                        if arm==design.PRESERVE:assert incoming==outgoing==packets[version]
                        else:packets[version]=outgoing
                        if owner=='neutral' and damage=='mix100':
                            for name in ('V','ema','R','theta'):
                                v=raw[f's{cfg.sweeps}_{name}']
                                for m in range(4):ref.exact(v[4*m:4*m+4],v[:4],'neutral full-erasure message independence')
                            assert abs(float(body['correctness'].mean())-.25)<2e-15
                        if damage=='mix000':
                            zk=(family,owner,arm);zv=identities(raw)
                            if zk in zero_damage:assert zero_damage[zk]==zv
                            else:zero_damage[zk]=zv
                        bodies[damage,owner,arm]=body
                        env=dict(mask_sha256=digest(data['fresh'].tobytes()),repair_rng=meta['rng_final'])
                        if str(corruption) in repair_envs:assert repair_envs[str(corruption)]==env
                        else:repair_envs[str(corruption)]=env
                        native+=proof['native_arrays'];repairs+=1;saved_count+=len(raw)+len(body)
            repair_seconds+=time.monotonic()-t
            assert set(packets)==set(design.versions(role));measured={};t=time.monotonic()
            for draw in range(draws):
                dest=target/f'draw_{draw:02d}';key=design.address(role,index,corruption,draw)
                assert key==receiving_audit.address(role,index,corruption,draw)
                if acquire:dest.mkdir()
                else:assert {p.name for p in dest.iterdir()}=={v+s for v in design.versions(role) for s in ('.npz','.json')}
                measured[draw]={}
                for version in design.versions(role):
                    path=dest/(version+'.npz');mp=dest/(version+'.json')
                    declared=dict(role=role,block=index,corruption=corruption,draw=draw,family=family,version=version,address=key)
                    if acquire:
                        raw,meta=receiving.read(ctx,packets[version],key,rcfg)
                        proof=receiving_audit.read(ctx,packets[version],rcfg,role,index,corruption,draw,raw,meta,True)
                        env=receiving_audit.paired(raw,meta);write_arrays(path,raw)
                        write_json(mp,dict(declared,metadata=meta,proof=proof,environment=env,sha256=sha(path),arrays=identities(raw)))
                    else:
                        raw=arrays(path);record=read_json(mp);meta=record['metadata'];proof=record['proof']
                        for k,v in declared.items():assert record[k]==v
                        assert sha(path)==record['sha256'] and identities(raw)==record['arrays']
                        receiving_audit.read(ctx,packets[version],rcfg,role,index,corruption,draw,raw,meta,False)
                        env=receiving_audit.paired(raw,meta);assert env==record['environment']
                    assert proof==dict(native_arrays=12,max_native_error=0.,rng_match=True,carrier_bytes_per_record=2048)
                    env_key=f'{corruption}:{draw}'
                    if env_key in envs:assert envs[env_key]==env
                    else:envs[env_key]=env
                    measured[draw][version]={k:raw[k] for k in ('correctness','probabilities','margins')}
                    if version.startswith('mix100_neutral_') or version=='mix100_incoming':
                        assert abs(float(raw['correctness'].mean())-.25)<2e-15
                    native+=proof['native_arrays'];reads+=1;saved_count+=len(raw)
            reader_seconds+=time.monotonic()-t
            paired,body_rows=rows(index,corruption,family,role,source,bodies,measured)
            all_rows.extend(paired);all_bodies.extend(body_rows)
    expected=design.expected(role,1)
    observed=dict(native_batches=repairs+reads,repair_batches=repairs,reader_batches=reads,individual_repairs=repairs*16,
        individual_assays=reads*16,native_arrays=native,intervention_arrays=intervention_count,saved_arrays=saved_count,
        paired_rows=len(all_rows),body_rows=len(all_bodies),max_native_error=0.,baseline_native_arrays=baseproof['baseline_native_arrays'],baseline_saved_arrays=baseproof['baseline_saved_arrays'])
    assert observed==expected,(observed,expected)
    assert len({v['birth_sha256'] for v in envs.values()})==corruptions*draws
    if acquire:
        write_json(directory/'ROWS.json',all_rows);write_json(directory/'BODIES.json',all_bodies)
        write_json(directory/'CHECK.json',dict(expected,status='PASS',seconds=time.monotonic()-tick,
            repair_seconds=repair_seconds,reader_seconds=reader_seconds,baseline_seconds=baseline_seconds,
            receiving_environments=envs,repair_environments=repair_envs,corruption_environments=corrupt_envs))
        return expected
    assert all_rows==read_json(directory/'ROWS.json') and all_bodies==read_json(directory/'BODIES.json')
    proof=read_json(directory/'CHECK.json');assert proof['status']=='PASS'
    for k,v in expected.items():assert proof[k]==v
    assert proof['receiving_environments']==envs and proof['repair_environments']==repair_envs and proof['corruption_environments']==corrupt_envs
    return dict(status='PASS',arrays=saved_count,paired_rows=len(all_rows),body_rows=len(all_bodies),
        distinct_receiving_environments=len(envs),baseline_saved_arrays=baseproof['baseline_saved_arrays'],new_dynamics=0)
def block(directory,index,role):
    expected=process(directory,index,role,True);tick=time.monotonic()
    proof=saved(directory);write_json(directory/'SAVED_CHECK.json',proof)
    check=read_json(directory/'CHECK.json')
    import analysis
    summary,conditional=analysis.block_summary(directory,role)
    write_json(directory/'SUMMARY.json',summary);write_json(directory/'CONDITIONAL.json',conditional)
    sizes=dict(repair=0,reader=0,baseline=0,other=0)
    for path in directory.rglob('*'):
        if path.is_file():
            kind='baseline' if path.parent.name=='baseline' else 'reader' if path.parent.name.startswith('draw_') else 'repair' if path.parent.name in design.BODIES else 'other'
            sizes[kind]+=path.stat().st_size
    write_json(directory/'TIMING.json',dict(baseline_seconds=check['baseline_seconds'],repair_seconds=check['repair_seconds'],reader_seconds=check['reader_seconds'],
        saved_seconds=time.monotonic()-tick,acquisition_seconds=check['seconds'],
        repair_batches=expected['repair_batches'],reader_batches=expected['reader_batches'],saved_arrays=expected['saved_arrays'],
        paired_rows=expected['paired_rows'],storage_bytes=sizes))
    return expected
def saved(directory):
    config=read_json(directory/'CONFIG.json')
    return process(directory,config['block'],config['role'],False)
