"""Independent corruption/body construction; imports no production builder."""
import hashlib
import json
import numpy as np
import physical_reference as ref

def corruption_seed(role,index,history):
    assert role in ('qualification','benchmark','confirmation')
    assert all(type(v) is int and v>=0 for v in (index,history))
    material=json.dumps(['TT028_conditional_correction_v1','corruption',role,index,history],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:16],'little')
def verify(ctx,source,role,history,values,meta):
    data=source['data'];seed=corruption_seed(role,ctx['index'],history)
    generator=np.random.Generator(np.random.PCG64(seed))
    draw=generator.standard_normal((4,16,16))
    noise=ref.project(np.concatenate([draw.copy() for _ in range(4)]),ctx['config'].norm)
    expected={'original':data['incoming'].copy(),'noise':noise}
    for name,weight in (('mix000',0.),('mix050',.5),('mix100',1.)):
        expected[name]=data['incoming'].copy() if weight==0 else ref.project((1.-weight)*data['incoming']+weight*noise,ctx['config'].norm)
    material=json.dumps(['TT022_serial_capture_v1',ctx['index'],0,1,'fission'],separators=(',',':')).encode()
    key=int.from_bytes(hashlib.sha256(material).digest()[:16],'little')
    rng=ref.Coupled(ref.SOURCE_TAG,key,'fission',4)
    axes=rng.integers(0,2,16);sides=rng.integers(0,2,16);grid=np.indices((16,16))
    kept=np.stack([(grid[a]//8)==side for a,side in zip(axes,sides)])
    jitter=ctx['tissue'].copy_jitter*rng.standard_normal((16,16,16))
    ref.exact(data['injured_V'],np.where(kept,data['developed_V'],ctx['tissue'].resting)+jitter,'actual body and jitter')
    donor=np.asarray([((i//4+2)%4)*4+i%4 for i in range(16)],dtype=np.int64)
    expected.update(own_V=data['injured_V'].copy(),foreign_V=np.stack([data['injured_V'][i] for i in donor]),
        neutral_V=ctx['tissue'].resting+jitter,fresh=~kept,jitter=jitter,donor_indices=donor)
    assert set(values)==set(expected)
    for name,v in expected.items():ref.exact(values[name],v,'intervention '+name)
    ref.exact(values['mix000'],data['incoming'],'zero damage exact identity')
    for name in ('noise','mix000','mix050','mix100'):
        assert np.isfinite(values[name]).all()
        assert np.max(np.abs(values[name].mean(axis=(-2,-1))))<1e-14
        assert np.max(np.abs(values[name].std(axis=(-2,-1))-.3))<1e-14
    for name in ('neutral_V','noise','mix100','jitter','fresh'):
        for m in range(4):ref.exact(values[name][4*m:4*m+4],values[name][:4],'message-independent '+name)
    assert meta==dict(corruption_seed=seed,corruption_rng_final=hashlib.sha256(json.dumps(generator.bit_generator.state,
        sort_keys=True,separators=(',',':')).encode()).hexdigest(),fission_address=key,fission_rng_final=rng.digest(),
        zero_damage_byte_identity=True,foreign_packet_transported=False,old_memory_transported=False,
        foreign_message_map=[2,3,0,1],neutral_initially_message_independent=True,
        norm=ctx['config'].norm,corruption_weights=dict(mix000=0.,mix050=.5,mix100=1.))
    return dict(status='PASS',arrays=len(expected),new_dynamics=0,independent_construction=True)
