"""Task-blind packet mixtures, physical half masks and uniform memory reset."""
from common import *
from inherited_repair import address as episode

def build(tissue,norm,project,original,role,index,c):
    model.boundary.field(original,4);before=original.tobytes()
    rng=np.random.default_rng(corruption_seed(role,index,c))
    noise=project(np.tile(rng.standard_normal((4,16,16)),(4,1,1)),norm)
    packets={name:(original.copy() if eta==0 else project((1-eta)*original+eta*noise,norm))
        for name,eta in MIX.items()}
    key=episode(index,0,1,'fission');injury=model.source.RNG(key,'fission',4)
    injury.integers(0,2,16);injury.integers(0,2,16)
    jitter=tissue.copy_jitter*injury.standard_normal(original.shape)
    assert original.tobytes()==before
    return dict(original=original.copy(),noise=noise,jitter=jitter,**packets),dict(
        corruption_seed=corruption_seed(role,index,c),
        corruption_rng_final=digest(json.dumps(rng.bit_generator.state,sort_keys=True,separators=(',',':')).encode()),
        fission_address=key,fission_rng_final=injury.digest(),mixture_weights=MIX,zero_damage_exact_identity=True)

def initial(developed,jitter,resting,incoming,mask,source):
    if mask not in MASKS or source not in SOURCES:raise ValueError('undeclared physical intervention')
    for v in (developed,jitter,incoming):model.boundary.field(v,4)
    mi=MASKS.index(mask);keep=np.indices((16,16))[mi//2]//8==mi%2
    v=np.where(keep,developed,resting)+jitter
    if source=='foreign':v=v[np.r_[8:16,0:8]].copy()
    elif source=='neutral':v=resting+jitter
    memory=v.copy();memory-=resting/2
    return dict(V=v,ema=np.zeros_like(v),R=memory,theta=incoming.copy())
