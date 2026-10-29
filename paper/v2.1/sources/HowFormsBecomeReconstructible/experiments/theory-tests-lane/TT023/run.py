"""All six conditions with explicit retained-control custody and new replay."""
from dataclasses import asdict
import hashlib
from pathlib import Path
import shutil
import time
import numpy as np
from common import *
import audit
import design
import kernel

def load_source(role,index,future,family,ctx,rcfg):
    entry=baseline_entry(role,index,future,family);cfg=ctx['config']
    config=read_json(ROOT/entry['config'])
    assert config['role']==role and config['tissue']==index
    assert serialized(config['config'])==serialized(asdict(cfg)) and serialized(config['readout'])==serialized(asdict(rcfg))
    result={}
    for policy in ('capture','capture_once'):
        path=ROOT/entry['policies'][policy]
        first,second=read_json(path/'g01.json'),read_json(path/'g02.json')
        values={}
        for name,meta,label in (('develop',first,'develop'),('boundary',first,'boundary'),
                               ('repair',first,'repair'),('body',first,'body'),('read',second,'develop')):
            file=path/('g02_develop.npz' if name=='read' else f'g01_{name}.npz')
            assert sha(file)==meta['files'][label]
            values[name]=arrays(file);assert identities(values[name])==meta['arrays'][label]
        assert read_json(path/'CHECK.json')['status']=='PASS'
        for proof in (first['repair_proof'],second['read_proof']):
            assert proof['native_arrays']==4*len(cfg.times) and proof['max_native_error']==0. and proof['rng_match']
        assert first['addresses']=={phase:audit.address(index,future,1,phase) for phase in ('develop','fission','repair')}
        assert second['addresses']['develop']==audit.address(index,future,2,'develop')
        packet=values['repair'][f's{cfg.sweeps}_theta'].tobytes()
        assert first['outgoing_sha256']==second['input_sha256']==hashlib.sha256(packet).hexdigest()
        audit.read(ctx,packet,rcfg,future,values['read'],second['read'],False)
        ref.scores(ctx['codes'],dict(values['body'],**{f's{cfg.sweeps}_V':values['repair'][f's{cfg.sweeps}_V']}),rcfg)
        values.update(first=first,second=second,path=str(path));result[policy]=values
    a,b=result['capture'],result['capture_once']
    assert identities(a['develop'])==identities(b['develop']) and identities(a['boundary'])==identities(b['boundary'])
    assert a['first']['repair']['rng_final']==b['first']['repair']['rng_final']
    assert a['second']['read']['rng_final']==b['second']['read']['rng_final']
    assert a['second']['read']['birth_rng_final']==b['second']['read']['birth_rng_final']
    ref.exact(a['read']['s0_V'],b['read']['s0_V'],'same cached receiver birth')
    audit.source(ctx,future,a['develop'][f's{cfg.sweeps}_V'],a['boundary'],a['repair'],b['repair'],
        a['first'],b['read'],b['second']['read'],rcfg)
    result.update(v=a['repair']['s0_V'],theta=a['repair']['s0_theta'],fresh=a['boundary']['fresh'])
    return result

def records(ctx,source,body,read):
    parents=ctx['config'].replicates
    labels=np.arange(4*parents)//parents
    content=(ctx['codes'][labels]*~source['fresh']).sum((1,2))/128
    assert set(content)<={-1.,0.,1.}
    return [dict(world=i,message=int(labels[i]),replicate=i%parents,
        injury_stratum=design.STRATA[0] if value==1 else design.STRATA[1] if value==-1 else design.STRATA[2],
        first_body=float(source['capture']['develop']['correctness'][i,0]),
        repaired_body=float(body['correctness'][i,0]),recipient=float(read['correctness'][i,0]))
        for i,value in enumerate(content)]

def saved_arm(directory,ctx,source,arm,future,rcfg):
    cfg=ctx['config'];memory,write=design.options(arm);meta=read_json(directory/'META.json')
    assert meta['arm']==arm and meta['future']==future and meta['memory']==memory and meta['write']==write
    assert meta['repair_address']==audit.address(ctx['index'],future,1,'repair')
    assert meta['read_address']==audit.address(ctx['index'],future,2,'develop')
    expected_new_repair=arm not in design.CACHED;expected_new_read=write and arm!='full_on'
    assert meta['new_repair']==expected_new_repair and meta['new_read']==expected_new_read
    values={}
    for label in ('repair','body','read','packets'):
        path=directory/(label+'.npz');assert sha(path)==meta['files'][label]
        values[label]=arrays(path);assert identities(values[label])==meta['arrays'][label]
    raw,body,read,packets=(values[k] for k in ('repair','body','read','packets'))
    audit.repairs(ctx,source['v'],source['theta'],source['fresh'],memory,write,future,raw,meta['repair'],False)
    ref.scores(ctx['codes'],dict(body,**{f's{cfg.sweeps}_V':raw[f's{cfg.sweeps}_V']}),rcfg)
    ref.exact(packets['initial'],source['theta'],'same incoming packet')
    ref.exact(packets['outgoing'],raw[f's{cfg.sweeps}_theta'],'actual outgoing packet')
    outgoing=packets['outgoing'].tobytes()
    assert meta['outgoing_sha256']==hashlib.sha256(outgoing).hexdigest()
    audit.read(ctx,outgoing,rcfg,future,read,meta['read'],False)
    assert meta['repair']['rng_final']==source['capture']['first']['repair']['rng_final']
    assert meta['read']['rng_final']==source['capture_once']['second']['read']['rng_final']
    assert meta['read']['birth_rng_final']==source['capture_once']['second']['read']['birth_rng_final']
    ref.exact(read['s0_V'],source['capture_once']['read']['s0_V'],'paired fresh birth')
    if not expected_new_repair:
        assert identities(raw)==identities(source[design.CACHED[arm]]['repair'])
        assert identities(body)==identities(source[design.CACHED[arm]]['body'])
    if not expected_new_read:
        cache=source['capture'] if arm=='full_on' else source['capture_once']
        assert identities(read)==identities(cache['read']) and meta['read']==cache['second']['read']
    for name,new in (('repair',expected_new_repair),('read',expected_new_read)):
        assert meta['proofs'][name]['native_arrays']==(4*len(cfg.times) if new else 0)
        assert meta['proofs'][name]['max_native_error']==0.
    assert records(ctx,source,body,read)==read_json(directory/'records.json')
    return dict(status='PASS',arrays=sum(len(v) for v in values.values()),records=4*cfg.replicates,packet_handoffs=1,new_dynamics=0)

def run_arm(directory,ctx,source,arm,future,rcfg):
    directory.mkdir(parents=True,exist_ok=False);cfg=ctx['config'];memory,write=design.options(arm)
    initial=kernel.initial(source['v'],source['theta'],source['fresh'],ctx['tissue'].resting,memory)
    new_repair=arm not in design.CACHED;new_read=write and arm!='full_on'
    if new_repair:
        raw,repair_meta=kernel.repair(model.boundary.runtime_context(ctx),initial,kernel.address(ctx['index'],future,1,'repair'),write)
        _,body=model.old.readout.measure(ctx,raw[f's{cfg.sweeps}_V'],rcfg)
    else:
        cache=source[design.CACHED[arm]];raw=cache['repair'];body=cache['body'];repair_meta=cache['first']['repair']
    repair_proof=audit.repairs(ctx,source['v'],source['theta'],source['fresh'],memory,write,future,raw,repair_meta,new_repair)
    ref.scores(ctx['codes'],dict(body,**{f's{cfg.sweeps}_V':raw[f's{cfg.sweeps}_V']}),rcfg)
    outgoing=raw[f's{cfg.sweeps}_theta'].tobytes()
    if new_read:read,read_meta=kernel.read(ctx,outgoing,rcfg,future)
    else:
        cache=source['capture'] if arm=='full_on' else source['capture_once']
        read,read_meta=cache['read'],cache['second']['read']
    read_proof=audit.read(ctx,outgoing,rcfg,future,read,read_meta,new_read)
    values=dict(repair=raw,body=body,read=read,packets=dict(initial=source['theta'],outgoing=raw[f's{cfg.sweeps}_theta']))
    for name,value in values.items():write_arrays(directory/(name+'.npz'),value)
    meta=dict(arm=arm,memory=memory,write=write,future=future,new_repair=new_repair,new_read=new_read,
        source_full=source['capture']['path'],source_zero_off=source['capture_once']['path'],
        repair_address=kernel.address(ctx['index'],future,1,'repair'),read_address=kernel.address(ctx['index'],future,2,'develop'),
        outgoing_sha256=hashlib.sha256(outgoing).hexdigest(),repair=repair_meta,read=read_meta,
        proofs=dict(repair=repair_proof,read=read_proof),
        files={name:sha(directory/(name+'.npz')) for name in values},arrays={name:identities(value) for name,value in values.items()})
    write_json(directory/'META.json',meta);write_json(directory/'records.json',records(ctx,source,body,read))
    saved=saved_arm(directory,ctx,source,arm,future,rcfg)
    return dict(new_repairs=int(new_repair),new_reads=int(new_read),retained_repairs=int(not new_repair),
        reused_read_slots=int(not new_read),native_arrays=repair_proof['native_arrays']+read_proof['native_arrays'],
        max_native_error=0.,saved=saved)

def saved_check(directory):
    config=read_json(directory/'CONFIG.json');role,index=config['role'],config['tissue']
    cfg,rcfg=design.configs(role);ctx=model.source.context(index,cfg)
    assert serialized(config['config'])==serialized(asdict(cfg)) and serialized(config['readout'])==serialized(asdict(rcfg))
    assert config['futures']==design.futures(role) and config['arms']==list(design.ARMS) and config['families']==list(design.FAMILIES)
    checks=[]
    for future in range(design.futures(role)):
        for family in design.FAMILIES:
            source=load_source(role,index,future,family,ctx,rcfg)
            base=directory/f'future_{future:02d}'/family
            assert {p.name for p in base.iterdir()}==set(design.ARMS)
            checks += [saved_arm(base/arm,ctx,source,arm,future,rcfg) for arm in design.ARMS]
    result=dict(status='PASS',**{k:sum(v[k] for v in checks) for k in ('arrays','records','packet_handoffs','new_dynamics')})
    assert result==read_json(directory/'SAVED_CHECK.json')
    return result

def run_block(directory,index,role):
    if role=='development':
        frozen=read_json(ROOT/'FREEZE.json');assert frozen['inputs']==runtime_hashes() and index in BLOCKS
    else:assert role in ('qualification','benchmark') and index in DISPOSABLE
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
    cfg,rcfg=design.configs(role);ctx=model.source.context(index,cfg)
    write_json(directory/'CONFIG.json',dict(role=role,tissue=index,config=asdict(cfg),readout=asdict(rcfg),
        futures=design.futures(role),arms=list(design.ARMS),families=list(design.FAMILIES)))
    results=[]
    for future in range(design.futures(role)):
        for family in design.FAMILIES:
            assert shutil.disk_usage(ROOT).free>=2*1024**3,'free-space reserve'
            source=load_source(role,index,future,family,ctx,rcfg)
            for arm in design.ARMS:
                results.append(run_arm(directory/f'future_{future:02d}'/family/arm,ctx,source,arm,future,rcfg))
    fields=('new_repairs','new_reads','retained_repairs','reused_read_slots','native_arrays')
    proof=dict(status='PASS',role=role,tissue=index,seconds=time.monotonic()-tick,
        arm_batches=len(results),**{k:sum(v[k] for v in results) for k in fields},max_native_error=0.)
    write_json(directory/'CHECK.json',proof)
    write_json(directory/'SAVED_CHECK.json',dict(status='PASS',**{k:sum(v['saved'][k] for v in results) for k in ('arrays','records','packet_handoffs','new_dynamics')}))
    return proof
