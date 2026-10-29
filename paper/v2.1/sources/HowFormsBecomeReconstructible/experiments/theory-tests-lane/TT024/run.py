"""Four serial policies, preserving exact prefixes and evolving each new branch."""
from dataclasses import asdict
import hashlib
import shutil
import time
from common import *
import audit
import baseline
import design
import kernel

def digest(packet):return hashlib.sha256(packet).hexdigest()
def environment(developed,boundary,read_meta,injury_meta,repair_meta):
    return dict(birth_sha256=digest(developed['s0_V'].tobytes()),mask_sha256=digest(boundary['fresh'].tobytes()),
        read_rng=read_meta['rng_final'],birth_rng=read_meta['birth_rng_final'],
        fission_rng=injury_meta['rng_final'],repair_rng=repair_meta['rng_final'])
def strata(ctx,boundary):
    cfg=ctx['config'];labels=np.arange(4*cfg.replicates)//cfg.replicates
    value=(ctx['codes'][labels]*~boundary['fresh']).sum((1,2))/128
    assert set(value)<={-1.,0.,1.}
    return [design.STRATA[0] if x==1 else design.STRATA[1] if x==-1 else design.STRATA[2] for x in value]
def rows(before,after,terminal,parents,injuries):
    before=np.stack(before,axis=1);after=np.stack(after,axis=1)
    return [dict(world=i,message=i//parents,replicate=i%parents,terminal=float(terminal[i]),
        development=[float(v) for v in before[i]],repaired=[float(v) for v in after[i]],
        uninterrupted_development=bool(np.all(before[i]==1.)),uninterrupted_repaired=bool(np.all(after[i]==1.)),
        injury_strata=[value[i] for value in injuries]) for i in range(4*parents)]
def check_old_rows(source,arm,data):
    if arm in design.CACHED:
        original=read_json(source['paths'][arm]/'records.json')
        assert [{k:v for k,v in row.items() if k!='injury_strata'} for row in data]==original
    else:
        original=read_json(source['paths'][arm]/'records.json')
        for new,old in zip(data,original):
            assert (new['world'],new['message'],new['replicate'])==(old['world'],old['message'],old['replicate'])
            assert new['development'][0]==old['first_body'] and new['repaired'][0]==old['repaired_body']
            assert new['development'][1]==old['recipient'] and new['injury_strata'][0]==old['injury_stratum']

def run_chain(directory,ctx,source,arm,future,generations,rcfg):
    directory.mkdir(parents=True,exist_ok=False);cfg=ctx['config'];memory,write=design.options(arm)
    original=incoming=source['initial'];before=[];after=[];injuries=[];new_reads=0;new_repairs=0
    for generation in range(1,generations+1):
        cache=baseline.components(source,arm,generation);values=cache['values']
        fresh_read='develop' not in values;fresh_repair='repair' not in values
        if fresh_read:developed,read_meta=kernel.read(ctx,incoming,rcfg,future,generation,'develop')
        else:developed,read_meta=values['develop'],cache['read_meta']
        read_proof=audit.read(ctx,incoming,rcfg,future,generation,'develop',developed,read_meta,fresh_read)
        if fresh_repair:
            state,boundary,injury_meta=kernel.injure(ctx,incoming,developed[f's{cfg.sweeps}_V'],future,generation,memory)
            repaired,repair_meta=kernel.repair(model.boundary.runtime_context(ctx),state,
                kernel.address(ctx['index'],future,generation,'repair'),write)
            body=kernel.body(ctx,repaired[f's{cfg.sweeps}_V'],rcfg)
        else:boundary,injury_meta,repaired,repair_meta,body=(values['boundary'],cache['injury_meta'],values['repair'],cache['repair_meta'],values['body'])
        outgoing=repaired[f's{cfg.sweeps}_theta'].tobytes()
        repair_proof=audit.repair(ctx,incoming,developed[f's{cfg.sweeps}_V'],rcfg,future,generation,memory,write,
            boundary,injury_meta,repaired,repair_meta,body,outgoing,fresh_repair)
        env=environment(developed,boundary,read_meta,injury_meta,repair_meta)
        assert env==source['checks']['full_on']['environment'][generation-1], 'original paired environment'
        artifacts=dict(develop=developed,boundary=boundary,repair=repaired,body=body);stem=f'g{generation:02d}'
        for label,value in artifacts.items():write_arrays(directory/f'{stem}_{label}.npz',value)
        meta=dict(arm=arm,generation=generation,memory=memory,write=write,new_read=fresh_read,new_repair=fresh_repair,
            addresses={p:kernel.address(ctx['index'],future,generation,p) for p in ('develop','fission','repair')},
            input_sha256=digest(incoming),outgoing_sha256=digest(outgoing),read=read_meta,injury=injury_meta,repair=repair_meta,
            read_proof=read_proof,repair_proof=repair_proof,environment=env,
            files={k:sha(directory/f'{stem}_{k}.npz') for k in artifacts},arrays={k:identities(v) for k,v in artifacts.items()})
        write_json(directory/(stem+'.json'),meta)
        before.append(developed['correctness'][:,0]);after.append(body['correctness'][:,0]);injuries.append(strata(ctx,boundary))
        incoming=outgoing;new_reads+=int(fresh_read);new_repairs+=int(fresh_repair)
    new_terminal=arm in design.NEW
    if new_terminal:terminal,metadata=kernel.read(ctx,incoming,rcfg,future,generations,'terminal')
    else:terminal,old=baseline.terminal(source,arm);metadata=old['metadata']
    terminal_proof=audit.read(ctx,incoming,rcfg,future,generations,'terminal',terminal,metadata,new_terminal)
    assert digest(terminal['s0_V'].tobytes())==source['checks']['full_on']['terminal_birth_sha256']
    assert metadata['rng_final']==source['checks']['full_on']['terminal_rng']
    write_arrays(directory/'terminal.npz',terminal)
    write_json(directory/'terminal.json',dict(address=kernel.address(ctx['index'],future,generations,'terminal'),
        new_read=new_terminal,metadata=metadata,proof=terminal_proof,sha256=sha(directory/'terminal.npz'),arrays=identities(terminal)))
    write_arrays(directory/'packets.npz',dict(initial=audit.packet_array(original,cfg.replicates),final=audit.packet_array(incoming,cfg.replicates)))
    data=rows(before,after,terminal['correctness'][:,0],cfg.replicates,injuries);check_old_rows(source,arm,data)
    write_json(directory/'records.json',data);new_reads+=int(new_terminal)
    proof=dict(status='PASS',arm=arm,generations=generations,new_reads=new_reads,new_repairs=new_repairs,
        retained_repairs=generations-new_repairs,reused_read_slots=generations+1-new_reads,
        native_arrays=12*(new_reads+new_repairs),max_native_error=0.,records=len(data))
    write_json(directory/'CHECK.json',proof)
    return proof

def saved_chain(directory,ctx,source,arm,future,generations,rcfg):
    cfg=ctx['config'];memory,write=design.options(arm);incoming=source['initial']
    before=[];after=[];injuries=[];count=0;new_reads=0;new_repairs=0
    for generation in range(1,generations+1):
        stem=f'g{generation:02d}';meta=read_json(directory/(stem+'.json'));cache=baseline.components(source,arm,generation)
        expected_read='develop' not in cache['values'];expected_repair='repair' not in cache['values']
        assert meta['arm']==arm and meta['generation']==generation and meta['memory']==memory and meta['write']==write
        assert meta['new_read']==expected_read and meta['new_repair']==expected_repair
        assert meta['input_sha256']==digest(incoming)
        assert meta['addresses']=={p:audit.address(ctx['index'],future,generation,p) for p in ('develop','fission','repair')}
        values={}
        for label in ('develop','boundary','repair','body'):
            path=directory/f'{stem}_{label}.npz';assert sha(path)==meta['files'][label]
            values[label]=arrays(path);assert identities(values[label])==meta['arrays'][label];count+=len(values[label])
            if label in cache['values']:assert identities(values[label])==identities(cache['values'][label])
        developed,boundary,repaired,body=(values[k] for k in ('develop','boundary','repair','body'))
        if not expected_read:assert meta['read']==cache['read_meta']
        if not expected_repair:assert meta['repair']==cache['repair_meta'] and meta['injury']==cache['injury_meta']
        audit.read(ctx,incoming,rcfg,future,generation,'develop',developed,meta['read'],False)
        outgoing=repaired[f's{cfg.sweeps}_theta'].tobytes();assert digest(outgoing)==meta['outgoing_sha256']
        audit.repair(ctx,incoming,developed[f's{cfg.sweeps}_V'],rcfg,future,generation,memory,write,
            boundary,meta['injury'],repaired,meta['repair'],body,outgoing,False)
        env=environment(developed,boundary,meta['read'],meta['injury'],meta['repair'])
        assert env==meta['environment']==source['checks']['full_on']['environment'][generation-1]
        for kind,required in (('read',expected_read),('repair',expected_repair)):
            assert meta[kind+'_proof']['native_arrays']==12*int(required)
            assert meta[kind+'_proof']['max_native_error']==0.
        before.append(developed['correctness'][:,0]);after.append(body['correctness'][:,0]);injuries.append(strata(ctx,boundary))
        incoming=outgoing;new_reads+=int(expected_read);new_repairs+=int(expected_repair)
    meta=read_json(directory/'terminal.json');terminal=arrays(directory/'terminal.npz')
    assert sha(directory/'terminal.npz')==meta['sha256'] and identities(terminal)==meta['arrays']
    assert meta['address']==audit.address(ctx['index'],future,generations,'terminal')
    assert meta['new_read']==(arm in design.NEW)
    audit.read(ctx,incoming,rcfg,future,generations,'terminal',terminal,meta['metadata'],False)
    assert meta['proof']['native_arrays']==12*int(arm in design.NEW) and meta['proof']['max_native_error']==0.
    assert digest(terminal['s0_V'].tobytes())==source['checks']['full_on']['terminal_birth_sha256']
    assert meta['metadata']['rng_final']==source['checks']['full_on']['terminal_rng']
    if arm in design.CACHED:
        retained,old=baseline.terminal(source,arm)
        assert identities(terminal)==identities(retained) and meta['metadata']==old['metadata']
    packets=arrays(directory/'packets.npz')
    assert set(packets)=={'initial','final'} and packets['initial'].tobytes()==source['initial'] and packets['final'].tobytes()==incoming
    data=rows(before,after,terminal['correctness'][:,0],cfg.replicates,injuries)
    assert data==read_json(directory/'records.json');check_old_rows(source,arm,data)
    new_reads+=int(arm in design.NEW)
    expected=dict(status='PASS',arm=arm,generations=generations,new_reads=new_reads,new_repairs=new_repairs,
        retained_repairs=generations-new_repairs,reused_read_slots=generations+1-new_reads,
        native_arrays=12*(new_reads+new_repairs),max_native_error=0.,records=len(data))
    assert expected==read_json(directory/'CHECK.json')
    return dict(status='PASS',arrays=count+len(terminal)+len(packets),records=len(data),packet_handoffs=generations+1,new_dynamics=0)

def saved_check(directory):
    config=read_json(directory/'CONFIG.json');role,index=config['role'],config['tissue'];cfg,rcfg=design.configs(role)
    futures,generations=design.schedule(role);ctx=model.source.context(index,cfg)
    assert config==dict(role=role,tissue=index,config=json.loads(serialized(asdict(cfg))),readout=json.loads(serialized(asdict(rcfg))),
        futures=futures,generations=generations,arms=list(design.ARMS),families=list(design.FAMILIES))
    checks=[];distinct=set()
    for future in range(futures):
        paired_environment=None
        for family in design.FAMILIES:
            source=baseline.load(ctx,rcfg,role,future,family);base=directory/f'future_{future:02d}'/family
            actual_environment={k:source['checks']['full_on'][k] for k in ('environment','terminal_birth_sha256','terminal_rng')}
            if paired_environment is None:paired_environment=actual_environment
            else:assert paired_environment==actual_environment
            assert {p.name for p in base.iterdir()}==set(design.ARMS)
            if family==design.FAMILIES[0]:
                births=[v['birth_sha256'] for v in source['checks']['full_on']['environment']]+[source['checks']['full_on']['terminal_birth_sha256']]
                assert len(set(births))==len(births) and not distinct.intersection(births);distinct.update(births)
            reference=None
            for arm in design.ARMS:
                checks.append(saved_chain(base/arm,ctx,source,arm,future,generations,rcfg))
                masks=[r['injury_strata'] for r in read_json(base/arm/'records.json')]
                if reference is None:reference=masks
                else:assert reference==masks
    result=dict(status='PASS',**{k:sum(v[k] for v in checks) for k in ('arrays','records','packet_handoffs','new_dynamics')})
    assert result==read_json(directory/'SAVED_CHECK.json')
    return result

def run_block(directory,index,role):
    if role=='development':
        frozen=read_json(ROOT/'FREEZE.json');assert frozen['inputs']==runtime_hashes() and index in BLOCKS
    else:assert role in ('qualification','benchmark') and index in DISPOSABLE
    directory.mkdir(parents=True,exist_ok=False);tick=time.monotonic();cfg,rcfg=design.configs(role)
    futures,generations=design.schedule(role);ctx=model.source.context(index,cfg)
    write_json(directory/'CONFIG.json',dict(role=role,tissue=index,config=asdict(cfg),readout=asdict(rcfg),
        futures=futures,generations=generations,arms=list(design.ARMS),families=list(design.FAMILIES)))
    checks=[];saved=[]
    for future in range(futures):
        assert shutil.disk_usage(ROOT).free>=2*1024**3
        for family in design.FAMILIES:
            source=baseline.load(ctx,rcfg,role,future,family)
            for arm in design.ARMS:
                path=directory/f'future_{future:02d}'/family/arm
                checks.append(run_chain(path,ctx,source,arm,future,generations,rcfg))
                saved.append(saved_chain(path,ctx,source,arm,future,generations,rcfg))
    fields=('new_repairs','new_reads','retained_repairs','reused_read_slots','native_arrays')
    proof=dict(arm_batches=len(checks),**{k:sum(v[k] for v in checks) for k in fields},max_native_error=0.)
    assert proof==design.expected(role,1)
    write_json(directory/'CHECK.json',dict(proof,status='PASS',seconds=time.monotonic()-tick))
    write_json(directory/'SAVED_CHECK.json',dict(status='PASS',**{k:sum(v[k] for v in saved) for k in ('arrays','records','packet_handoffs','new_dynamics')}))
    saved_check(directory)
    return proof
