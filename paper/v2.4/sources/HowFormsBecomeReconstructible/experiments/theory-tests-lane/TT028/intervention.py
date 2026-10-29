"""Task-blind corruption and declared body-source substitutions."""
from common import *
import design
from inherited_repair import address

def build(tissue,norm,project,data,role,index,history):
    if set(data)!= {'incoming','injured_V','fresh'}:raise ValueError('only physical input fields accepted')
    for name in ('incoming','injured_V'):model.boundary.field(data[name],4)
    fresh=data['fresh']
    if fresh.dtype!=np.bool_ or fresh.shape!=(16,16,16) or not np.all(fresh.sum((1,2))==128):
        raise ValueError('declared half-body mask required')
    before=identities(data)
    seed=design.corruption_seed(role,index,history);rng=np.random.default_rng(seed)
    draw=rng.standard_normal((4,16,16));noise=project(np.tile(draw,(4,1,1)),norm)
    corrupted={name:(data['incoming'].copy() if eta==0 else project((1-eta)*data['incoming']+eta*noise,norm))
        for name,eta in design.MIX.items()}
    key=address(index,0,1,'fission');injury=model.source.RNG(key,'fission',4)
    axes=injury.integers(0,2,16);sides=injury.integers(0,2,16)
    grid=np.indices((16,16));kept=np.stack([grid[a]//8==side for a,side in zip(axes,sides)])
    assert np.array_equal(~kept,fresh)
    jitter=tissue.copy_jitter*injury.standard_normal(data['injured_V'].shape)
    donor=model.boundary.partners(4)
    assert fresh[donor].tobytes()==fresh.tobytes() and jitter[donor].tobytes()==jitter.tobytes()
    values=dict(original=data['incoming'].copy(),noise=noise,**corrupted,
        own_V=data['injured_V'].copy(),foreign_V=data['injured_V'][donor].copy(),
        neutral_V=tissue.resting+ jitter,fresh=fresh.copy(),jitter=jitter,donor_indices=donor)
    assert set(values)==set(design.INTERVENTION_ARRAYS)
    for field in ('neutral_V','noise','mix100'):
        assert all(values[field][i*4:(i+1)*4].tobytes()==values[field][:4].tobytes() for i in range(4))
    assert identities(data)==before
    return values,dict(corruption_seed=seed,corruption_rng_final=digest(json.dumps(rng.bit_generator.state,
        sort_keys=True,separators=(',',':')).encode()),fission_address=key,fission_rng_final=injury.digest(),
        zero_damage_byte_identity=True,foreign_packet_transported=False,old_memory_transported=False,
        foreign_message_map=[2,3,0,1],neutral_initially_message_independent=True,
        norm=norm,corruption_weights=design.MIX)

def data(values,damage,body):
    if damage not in design.DAMAGE or body not in design.BODIES:raise ValueError('declared intervention cell required')
    return dict(incoming=values[damage],injured_V=values[body+'_V'],fresh=values['fresh'])
