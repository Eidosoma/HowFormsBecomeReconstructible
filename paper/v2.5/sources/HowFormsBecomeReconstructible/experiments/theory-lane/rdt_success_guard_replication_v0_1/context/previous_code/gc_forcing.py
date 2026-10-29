"""Paired policies/noise, nested injury masks, distinct qualification streams."""
import hashlib
import json
from gc_common import P,np,native,digest


def seed(stage,key,generation,channel):
    if stage not in P['stages'] or generation not in P['generations'] or channel not in ('injury','forcing'):
        raise ValueError('Unspecified forcing identity')
    purpose='writer' if generation<33 else 'evaluation'
    payload=[P['namespace'],stage,*key,0,int(generation),purpose,channel]
    return int.from_bytes(hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).digest()[:16],'little')


def environment(stage,key,generation,injury,regime):
    if injury not in P['injury_levels'] or regime not in P['regimes']:
        raise ValueError('Unspecified injury or cue regime')
    available=np.flatnonzero(~native.PORTS.any(axis=0).ravel())
    assert len(available)==244
    order=np.random.Generator(np.random.PCG64(seed(stage,key,generation,'injury'))).permutation(available)
    mask=np.zeros((16,16),bool);mask.ravel()[order[:injury]]=True
    draws=np.random.Generator(np.random.PCG64(seed(stage,key,generation,'forcing'))).standard_normal((P['reader']['read_steps']+1,2,16,16))
    base_digest=digest(draws)
    if regime=='matched':draws[:,1]=draws[:,0]
    birth=P['reader']['birth_sd']*draws[0];noise=draws[1:]
    record=dict(key=key,generation=generation,injury=injury,regime=regime,
                permutation_sha256=digest(order),base_forcing_sha256=base_digest,
                mask_sha256=digest(mask),birth_sha256=digest(birth),noise_sha256=digest(noise))
    return (mask,birth,noise),record
