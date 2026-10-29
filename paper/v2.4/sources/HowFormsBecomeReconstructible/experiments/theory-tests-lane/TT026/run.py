"""Actual gated repairs and paired packet-only receiving assays."""
from dataclasses import asdict
import time
from common import *
import audit
import baseline
import design
import kernel
import receiving
import receiving_audit

def context(index, role):
    cfg,rcfg = design.configs(role)
    return model.source.context(index,cfg) | {'readout':rcfg}
def native_prefix(source, arm, raw, metadata):
    short = {'corrected_1000':'corrected','full_1000':'full','zero_1000':'zero'}.get(arm)
    if short is None: return 0
    old = source['controls'][short]; count = 0
    for key in sorted(set(old) & set(raw)):
        ref.exact(raw[key],old[key],'inherited full-writing prefix '+key); count += 1
    old_n = source['provenance']['source_config']['config']['sweeps']
    if metadata['total_updates'] == old_n:
        assert metadata['rng_final'] == source['provenance']['source_metadata'][short]['repair']['rng_final']
    return count
def data_rows(index, history, family, role, source, bodies, measured):
    _, draws = design.schedule(role); cfg,_ = design.configs(role)
    rows = []; body_rows = []
    for arm in design.ARMS:
        _,budget = design.options(arm,cfg.sweeps)
        for world,h in enumerate(source['history']):
            body = float(bodies[arm]['correctness'][world,0])
            full_body = float(bodies[design.FULL]['correctness'][world,0])
            b = dict(block=index,history=history,family=family,arm=arm,world=world,message=world//4,
                replicate=world % 4,budget=budget,developed_score=h['developed_score'],
                injury_stratum=h['injury_stratum'],repaired_score=body,full_budget_body=full_body,
                body_effect_vs_full=body-full_body)
            body_rows.append(b)
            for draw in range(draws):
                x = float(measured[draw]['initial']['correctness'][world,0])
                y = float(measured[draw][design.alias(arm)]['correctness'][world,0])
                full = float(measured[draw][design.FULL]['correctness'][world,0])
                if arm == design.PRESERVE: assert x == y
                rows.append(dict(b,draw=draw,incoming=x,outgoing=y,effect=y-x,full_budget_outgoing=full,
                    effect_vs_full=y-full,packet_version=design.alias(arm),
                    incoming_margin=float(measured[draw]['initial']['margins'][world,0]),
                    outgoing_margin=float(measured[draw][design.alias(arm)]['margins'][world,0])))
    return rows,body_rows

def block(directory,index,role):
    directory.mkdir(parents=True,exist_ok=False); tick=time.monotonic()
    ctx=context(index,role); cfg=ctx['config']; rcfg=ctx['readout']; histories,draws=design.schedule(role)
    write_json(directory/'CONFIG.json',dict(role=role,block=index,config=asdict(cfg),readout=asdict(rcfg),
        histories=histories,draws=draws,arms=design.ARMS,families=design.FAMILIES))
    all_rows=[];all_bodies=[];receiving_env={};repair_env={};native_arrays=0;prefix_arrays=0;repairs=0;reads=0
    for history in range(histories):
        for family in design.FAMILIES:
            source=baseline.load(ctx,role,history,family); data=source['data']
            target=directory/f'future_{history:02d}'/family; target.mkdir(parents=True)
            packets={'initial':data['incoming'].tobytes()}; bodies={}
            for arm in design.ARMS:
                memory,budget=design.options(arm,cfg.sweeps)
                state=kernel.initial(data['injured_V'],data['incoming'],data['fresh'],ctx['tissue'].resting,memory)
                key=kernel.repair_address(index,history,1,'repair'); assert key==audit.repair_address(index,history)
                raw,meta=kernel.repair(model.boundary.runtime_context(ctx),state,key,budget)
                body=reader.measure(ctx,raw[f's{cfg.sweeps}_V'],rcfg)[1]
                proof=audit.repair(ctx,data,memory,budget,history,raw,meta,body,True)
                prefix=native_prefix(source,arm,raw,meta); prefix_arrays+=prefix
                outgoing=raw[f's{cfg.sweeps}_theta'].tobytes()
                if arm==design.PRESERVE: assert outgoing==packets['initial']
                else: packets[arm]=outgoing
                bodies[arm]=body
                write_arrays(target/(arm+'_repair.npz'),raw);write_arrays(target/(arm+'_body.npz'),body)
                write_json(target/(arm+'.json'),dict(role=role,block=index,history=history,family=family,arm=arm,
                    memory=memory,budget=budget,address=key,metadata=meta,proof=proof,legacy_control_arrays=prefix,
                    outgoing_sha256=digest(outgoing),input_packet_sha256=digest(packets['initial']),
                    files={k:sha(target/(arm+'_'+k+'.npz')) for k in ('repair','body')},
                    arrays=dict(repair=identities(raw),body=identities(body))))
                env=dict(mask_sha256=digest(data['fresh'].tobytes()),repair_rng=meta['rng_final'])
                if str(history) in repair_env: assert repair_env[str(history)]==env
                else: repair_env[str(history)]=env
                repairs+=1;native_arrays+=proof['native_arrays']
            assert set(packets)==set(design.versions())
            measured={}
            for draw in range(draws):
                dest=target/f'draw_{draw:02d}';dest.mkdir();measured[draw]={}
                key=design.address(role,index,history,draw)
                assert key==receiving_audit.address(role,index,history,draw)
                for version in design.versions():
                    raw,meta=receiving.read(ctx,packets[version],key,rcfg)
                    proof=receiving_audit.read(ctx,packets[version],rcfg,role,index,history,draw,raw,meta,True)
                    env=receiving_audit.paired(raw,meta);env_key=f'{history}:{draw}'
                    if env_key in receiving_env: assert receiving_env[env_key]==env
                    else: receiving_env[env_key]=env
                    write_arrays(dest/(version+'.npz'),raw)
                    write_json(dest/(version+'.json'),dict(role=role,block=index,history=history,draw=draw,family=family,
                        version=version,address=key,metadata=meta,proof=proof,environment=env,
                        sha256=sha(dest/(version+'.npz')),arrays=identities(raw)))
                    measured[draw][version]={k:raw[k] for k in ('correctness','margins')}
                    reads+=1;native_arrays+=proof['native_arrays']
            rows,body_rows=data_rows(index,history,family,role,source,bodies,measured)
            all_rows.extend(rows);all_bodies.extend(body_rows)
    assert len({v['birth_sha256'] for v in receiving_env.values()})==histories*draws
    expected=design.expected(role,1)
    assert (repairs,reads,native_arrays,prefix_arrays,len(all_rows),len(all_bodies))==tuple(expected[k] for k in
        ('repair_batches','reader_batches','native_arrays','legacy_control_arrays','paired_rows','body_rows'))
    write_json(directory/'ROWS.json',all_rows);write_json(directory/'BODIES.json',all_bodies)
    write_json(directory/'CHECK.json',dict(expected,status='PASS',seconds=time.monotonic()-tick,
        receiving_environments=receiving_env,repair_environments=repair_env))
    proof=saved(directory);write_json(directory/'SAVED_CHECK.json',proof)
    return expected

def saved(directory):
    config=read_json(directory/'CONFIG.json');role,index=config['role'],config['block']
    ctx=context(index,role);cfg=ctx['config'];rcfg=ctx['readout'];histories,draws=design.schedule(role)
    assert config==json.loads(serialized(dict(role=role,block=index,config=asdict(cfg),readout=asdict(rcfg),
        histories=histories,draws=draws,arms=design.ARMS,families=design.FAMILIES)))
    all_rows=[];all_bodies=[];receiving_env={};repair_env={};count=0;prefix_arrays=0
    for history in range(histories):
        for family in design.FAMILIES:
            source=baseline.load(ctx,role,history,family);data=source['data'];target=directory/f'future_{history:02d}'/family
            assert {p.name for p in target.iterdir()}=={a+s for a in design.ARMS for s in ('.json','_repair.npz','_body.npz')}|{f'draw_{d:02d}' for d in range(draws)}
            packets={'initial':data['incoming'].tobytes()};bodies={}
            for arm in design.ARMS:
                meta=read_json(target/(arm+'.json'));memory,budget=design.options(arm,cfg.sweeps)
                for k,v in dict(role=role,block=index,history=history,family=family,arm=arm,memory=memory,budget=budget).items(): assert meta[k]==v
                values={}
                for label in ('repair','body'):
                    path=target/(arm+'_'+label+'.npz');values[label]=arrays(path)
                    assert sha(path)==meta['files'][label] and identities(values[label])==meta['arrays'][label]
                    count+=len(values[label])
                raw,body=values['repair'],values['body'];bodies[arm]=body
                assert meta['address']==audit.repair_address(index,history)
                audit.repair(ctx,data,memory,budget,history,raw,meta['metadata'],body,False)
                assert meta['proof']==dict(native_arrays=len(cfg.times)*4,max_native_error=0.,rng_match=True)
                prefix=native_prefix(source,arm,raw,meta['metadata']);assert prefix==meta['legacy_control_arrays'];prefix_arrays+=prefix
                outgoing=raw[f's{cfg.sweeps}_theta'].tobytes();assert digest(outgoing)==meta['outgoing_sha256']
                assert meta['input_packet_sha256']==digest(packets['initial'])
                if arm==design.PRESERVE:assert outgoing==packets['initial']
                else:packets[arm]=outgoing
                env=dict(mask_sha256=digest(data['fresh'].tobytes()),repair_rng=meta['metadata']['rng_final'])
                if str(history) in repair_env:assert repair_env[str(history)]==env
                else:repair_env[str(history)]=env
            measured={}
            for draw in range(draws):
                dest=target/f'draw_{draw:02d}';measured[draw]={}
                assert {p.name for p in dest.iterdir()}=={v+s for v in design.versions() for s in ('.npz','.json')}
                for version in design.versions():
                    path=dest/(version+'.npz');raw=arrays(path);meta=read_json(dest/(version+'.json'))
                    assert sha(path)==meta['sha256'] and identities(raw)==meta['arrays'];count+=len(raw)
                    for k,v in dict(role=role,block=index,history=history,draw=draw,family=family,version=version).items():assert meta[k]==v
                    assert meta['address']==receiving_audit.address(role,index,history,draw)
                    assert meta['proof']['native_arrays']==12 and meta['proof']['max_native_error']==0.
                    receiving_audit.read(ctx,packets[version],rcfg,role,index,history,draw,raw,meta['metadata'],False)
                    env=receiving_audit.paired(raw,meta['metadata']);assert env==meta['environment'];key=f'{history}:{draw}'
                    if key in receiving_env:assert receiving_env[key]==env
                    else:receiving_env[key]=env
                    measured[draw][version]={k:raw[k] for k in ('correctness','margins')}
            rows,body_rows=data_rows(index,history,family,role,source,bodies,measured)
            all_rows.extend(rows);all_bodies.extend(body_rows)
    assert all_rows==read_json(directory/'ROWS.json') and all_bodies==read_json(directory/'BODIES.json')
    proof=read_json(directory/'CHECK.json');expected=design.expected(role,1)
    assert proof['status']=='PASS'
    for k,v in expected.items():assert proof[k]==v
    assert proof['receiving_environments']==receiving_env and proof['repair_environments']==repair_env
    assert len({v['birth_sha256'] for v in receiving_env.values()})==histories*draws
    assert count==expected['saved_arrays'] and prefix_arrays==expected['legacy_control_arrays']
    return dict(status='PASS',arrays=count,paired_rows=len(all_rows),body_rows=len(all_bodies),
        distinct_receiving_environments=len(receiving_env),legacy_control_arrays=prefix_arrays,new_dynamics=0)
