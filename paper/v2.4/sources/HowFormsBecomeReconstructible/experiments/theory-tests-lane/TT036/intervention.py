"""Task-blind noise replacement, physical masks and uniform memory reset."""
from common import *
from inherited_repair import address as episode

def build(tissue,norm,project,original,role,index,c):
    model.boundary.field(original,4)
    rng=np.random.default_rng(corruption_seed(role,index,c))
    noise=project(np.tile(rng.standard_normal((4,16,16)),(4,1,1)),norm)
    incoming=project(0.*original+noise,norm)
    key=episode(index,0,1,'fission');injury=model.source.RNG(key,'fission',4)
    injury.integers(0,2,16);injury.integers(0,2,16)
    jitter=tissue.copy_jitter*injury.standard_normal(original.shape)
    return dict(original=original.copy(),noise=noise,incoming=incoming,jitter=jitter),dict(
        corruption_seed=corruption_seed(role,index,c),corruption_rng_final=digest(json.dumps(rng.bit_generator.state,sort_keys=True,separators=(',',':')).encode()),
        fission_address=key,fission_rng_final=injury.digest())

def initial(developed,jitter,resting,incoming,mask,source):
    if mask not in MASKS or source not in SOURCES:raise ValueError('undeclared physical intervention')
    for v in (developed,jitter,incoming):model.boundary.field(v,4)
    mi=MASKS.index(mask);keep=np.indices((16,16))[mi//2]//8==mi%2
    v=np.where(keep,developed,resting)+jitter
    if source=='foreign':v=v[np.r_[8:16,0:8]].copy()
    elif source=='neutral':v=resting+jitter
    memory=v.copy();memory-=resting/2
    return dict(V=v,ema=np.zeros_like(v),R=memory,theta=incoming.copy())
