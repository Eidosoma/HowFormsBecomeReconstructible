"""Normalize retained serial controls and exact TT023 prefixes without simulation."""
from dataclasses import asdict
from common import *
import design
import audit

def load(ctx,rcfg,role,future,family):
    cfg=ctx['config'];entry=baseline_entry(role,ctx['index'],future,family)
    for name in entry['configs'].values():
        value=read_json(ROOT/name)
        assert value['role']==role and value['tissue']==ctx['index']
        assert serialized(value['config'])==serialized(asdict(cfg))
        assert serialized(value['readout'])==serialized(asdict(rcfg))
        assert value['futures']==design.schedule(role)[0]
    paths={arm:ROOT/name for arm,name in entry['arms'].items()}
    checks={arm:read_json(paths[arm]/'CHECK.json') for arm in design.CACHED}
    for check in checks.values():
        generations=design.schedule(role)[1]
        assert check['status']=='PASS' and check['generations']==generations
        assert check['native_arrays']==12*(2*generations+1) and check['max_native_error']==0.
        assert check['native_reader_contexts']==generations+1 and check['native_repair_contexts']==generations
    initial=arrays(paths['full_on']/'packets.npz')['initial'].tobytes()
    assert initial==arrays(paths['zero_off']/'packets.npz')['initial'].tobytes()
    assert checks['full_on']['environment']==checks['zero_off']['environment']
    assert checks['full_on']['terminal_birth_sha256']==checks['zero_off']['terminal_birth_sha256']
    assert checks['full_on']['terminal_rng']==checks['zero_off']['terminal_rng']
    audit.packet_array(initial,cfg.replicates)
    for arm in design.NEW:
        meta=read_json(paths[arm]/'META.json')
        assert meta['arm']==arm and meta['future']==future
        assert meta['memory']==design.options(arm)[0] and meta['write'] is True
        assert meta['repair_address']==audit.address(ctx['index'],future,1,'repair')
        assert meta['read_address']==audit.address(ctx['index'],future,2,'develop')
        assert meta['new_repair'] and meta['new_read']
        for proof in meta['proofs'].values():assert proof['native_arrays']==12 and proof['max_native_error']==0.
        for label in ('repair','body','read','packets'):
            path=paths[arm]/(label+'.npz')
            assert sha(path)==meta['files'][label] and identities(arrays(path))==meta['arrays'][label]
        packets=arrays(paths[arm]/'packets.npz')
        assert packets['initial'].tobytes()==initial
        assert packets['outgoing'].tobytes()==arrays(paths[arm]/'repair.npz')[f's{cfg.sweeps}_theta'].tobytes()
    return dict(paths=paths,checks=checks,initial=initial,role=role)

def serial_step(source,arm,generation):
    path=source['paths'][arm];stem=f'g{generation:02d}';meta=read_json(path/(stem+'.json'))
    values={label:arrays(path/f'{stem}_{label}.npz') for label in ('develop','boundary','repair','body')}
    for label,value in values.items():
        assert sha(path/f'{stem}_{label}.npz')==meta['files'][label]
        assert identities(value)==meta['arrays'][label]
    for proof in (meta['read_proof'],meta['repair_proof']):
        assert proof['native_arrays']==12 and proof['max_native_error']==0. and proof['rng_match']
    assert meta['generation']==generation
    return values,meta

def components(source,arm,generation):
    """Return only fields with an exact declared predecessor; others must be new."""
    if arm in design.CACHED:
        values,meta=serial_step(source,arm,generation)
        return dict(values=values,read_meta=meta['read'],injury_meta=meta['injury'],repair_meta=meta['repair'])
    prefix=source['paths'][arm];meta=read_json(prefix/'META.json')
    if generation==1:
        values,first=serial_step(source,'full_on',1)
        return dict(values=dict(develop=values['develop'],boundary=values['boundary'],
            repair=arrays(prefix/'repair.npz'),body=arrays(prefix/'body.npz')),
            read_meta=first['read'],injury_meta=first['injury'],repair_meta=meta['repair'])
    if generation==2:return dict(values=dict(develop=arrays(prefix/'read.npz')),read_meta=meta['read'])
    return dict(values={})

def terminal(source,arm):
    assert arm in design.CACHED
    path=source['paths'][arm];meta=read_json(path/'terminal.json');raw=arrays(path/'terminal.npz')
    assert sha(path/'terminal.npz')==meta['sha256'] and identities(raw)==meta['arrays']
    assert meta['proof']['native_arrays']==12 and meta['proof']['max_native_error']==0.
    return raw,meta
