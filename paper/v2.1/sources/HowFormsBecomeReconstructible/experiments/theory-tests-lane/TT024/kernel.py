"""Serial routing around the byte-identical TT023 memory/repair adapter."""
import hashlib
import json
from common import model
from inherited23_kernel import initial,repair
from design import PHASES

def address(index,future,generation,phase):
    if any(type(v) is not int or v<0 for v in (index,future,generation)) or phase not in PHASES:
        raise ValueError('declared TT022 serial address required')
    value=json.dumps(['TT022_serial_capture_v1',index,future,generation,phase],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:16],'little')
def read(ctx,packet,rcfg,future,generation,phase):
    assert phase in ('develop','terminal')
    result=model.boundary.fresh_read(dict(ctx,index=address(ctx['index'],future,generation,phase)),packet,rcfg)
    return result['raw'],{k:v for k,v in result.items() if k not in ('raw','metrics')}
def injure(ctx,incoming,developed,future,generation,memory):
    theta=model.boundary.decode(incoming,ctx['config'].replicates)
    rng=model.source.RNG(address(ctx['index'],future,generation,'fission'),'fission',ctx['config'].replicates)
    v,no_memory,fresh=ctx['api']['fission_with_mask'](developed,None,ctx['tissue'],rng)
    assert no_memory is None
    return initial(v,theta,fresh,ctx['tissue'].resting,memory),dict(fresh=fresh,injured_V=v),dict(rng_final=rng.digest())
def body(ctx,v,rcfg):return model.old.readout.measure(ctx,v,rcfg)[1]
