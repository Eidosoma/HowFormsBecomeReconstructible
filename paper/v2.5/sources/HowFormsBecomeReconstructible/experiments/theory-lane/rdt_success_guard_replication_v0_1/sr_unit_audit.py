"""Separate scalar decisions and saved-chain/forcing verification, no policy imports."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

from sr_common import P,ev,read,digest,byte_equal


def raw_class(windows,rule):
    values=[math.fsum(float(windows[t,c,p]) for t in range(len(windows)))/len(windows)*rule*(1 if c==p else -1)
            for c in (0,1) for p in (0,1)]
    return (1 if min(values)>.25 else (-1 if max(values)<-.25 else 0)),values


def decision(policy,h,current):
    if policy==0:return True
    if policy==1:return h==0 or current==1
    if policy==2:return current==1
    if policy==3:return False
    raise ValueError('Four fixed policies only')


def independent_environment(stage,key,generation,injury,regime):
    # Construct protected port geometry independently of native.PORTS.
    ports={(y,x) for yy,xx in [(7,1),(3,10),(11,10)] for y in (yy,yy+1) for x in (xx,xx+1)}
    available=np.array([16*y+x for y in range(16) for x in range(16) if (y,x) not in ports],np.int64)
    def rng(channel):
        value=[P['namespace'],stage,*key,0,generation,'writer' if generation<33 else 'evaluation',channel]
        seed=int.from_bytes(hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).digest()[:16],'little')
        return np.random.Generator(np.random.PCG64(seed))
    order=rng('injury').permutation(available)
    mask=np.zeros((16,16),bool)
    for v in order[:injury]:mask[int(v)//16,int(v)%16]=True
    draws=rng('forcing').standard_normal((P['reader']['read_steps']+1,2,16,16))
    base=digest(draws)
    if regime=='matched':draws[:,1]=draws[:,0]
    birth=draws[0]*P['reader']['birth_sd']
    return mask,birth,dict(permutation_sha256=digest(order),base_forcing_sha256=base,mask_sha256=digest(mask),
                          birth_sha256=digest(birth),noise_sha256=digest(draws[1:]))


def audit_case(output,rows,stage,injury,regime,seal_hash):
    output=Path(output);receipt=read(output.with_suffix('.json'))
    raw=ev.load(output.with_suffix('.npz'),receipt['raw_sha256'])
    if receipt['rows']!=rows or receipt['policy_seal_sha256']!=seal_hash:raise ArithmeticError('Case binding mismatch')
    if raw['windows'].shape!=(19,4,32,4,2,2) or raw['incoming'].shape!=(19,4,4,2,16,16):
        raise ArithmeticError('Full horizon and four-policy evidence required')
    if raw['generations'].tolist()!=list(range(15,34)):raise ArithmeticError('Wrong generations')
    audit_index=min(range(4),key=lambda j:rows[j]['selection_hash'])
    if int(raw['audit_index'])!=audit_index:raise ArithmeticError('Flat case selected after outcomes')
    checked=0;max_error=0.
    for j,row in enumerate(rows):
        if digest(raw['initial_packets'][j])!=row['packet_sha256']:raise ArithmeticError('Wrong initial packet')
        if int(raw['histories'][j])!=row['current_pass'] or int(raw['rules'][j])!=row['rule']:
            raise ArithmeticError('Rule or historical class changed')
        for k,generation in enumerate(range(15,34)):
            mask,birth,hashes=independent_environment(stage,row['key'],generation,injury,regime)
            rec=receipt['forcing'][4*k+j]
            if rec['key']!=row['key'] or rec['generation']!=generation:raise ArithmeticError('Forcing key coverage')
            if any(rec[name]!=value for name,value in hashes.items()):raise ArithmeticError('Forcing stream mismatch')
            byte_equal(raw['mask'][k,j],mask,'independent injury regeneration')
            byte_equal(raw['birth'][k,j],birth,'independent birth regeneration')
            for arm in range(4):
                cls,means=raw_class(raw['windows'][k,j,:,arm],row['rule'])
                if cls!=int(raw['classes'][k,j,arm]) or (cls==1)!=bool(raw['passed'][k,j,arm]):
                    raise ArithmeticError('Independent native endpoint mismatch')
                max_error=max(max_error,float(np.max(abs(np.array(means).reshape(2,2)-raw['aligned'][k,j,arm]))))
                act=decision(arm,row['current_pass'],cls) if generation<33 else False
                if act!=bool(raw['actions'][k,j,arm]):raise ArithmeticError('Current-read action mismatch')
                if k==0:byte_equal(raw['incoming'][k,j,arm],raw['initial_packets'][j],'initial state')
                if k<18:
                    expected=raw['outgoing'][k,j,arm] if act else raw['incoming'][k,j,arm]
                    byte_equal(raw['incoming'][k+1,j,arm],expected,'guarded inheritance chain')
                if arm==3:byte_equal(raw['incoming'][k,j,arm],raw['initial_packets'][j],'protected history')
                checked+=1
            if row['current_pass']==0:
                for name in ('incoming','end','outgoing'):
                    byte_equal(raw[name][k,j,0],raw[name][k,j,1],'H0 identity '+name)
                byte_equal(raw['windows'][k,j,:,0],raw['windows'][k,j,:,1],'H0 identity windows')
            if k==0:
                for arm in (1,2,3):byte_equal(raw['windows'][0,j,:,0],raw['windows'][0,j,:,arm],'pre-action identity')
    if max_error>1e-12:raise ArithmeticError('Scalar response mean differs')
    byte_equal(raw['final_packets'],raw['incoming'][-1],'terminal outgoing not inherited')
    for k,generation in enumerate(range(15,34)):
        for name in ('incoming','end','windows','outgoing','actions'):
            byte_equal(raw['flat_'+name][k],raw[name][k,audit_index],'saved flat '+name)
        for arm in range(4):
            cls,_=raw_class(raw['flat_windows'][k,:,arm],rows[audit_index]['rule'])
            act=decision(arm,rows[audit_index]['current_pass'],cls) if k<18 else False
            if bool(raw['flat_actions'][k,arm])!=act:raise ArithmeticError('Independent flat policy update')
            if k<18:
                desired=raw['flat_outgoing'][k,arm] if act else raw['flat_incoming'][k,arm]
                byte_equal(raw['flat_incoming'][k+1,arm],desired,'independently inherited flat path')
    expected=[dict(generation=g,key=rows[audit_index]['key'],policies=4,byte_exact=True) for g in range(15,34)]
    if receipt['audits']!=expected or receipt['native_reads']!=304 or receipt['flat_native_reads']!=76:
        raise ArithmeticError('Native cost or flat audit schedule mismatch')
    return dict(status='PASS',native_readouts_independently_scored=checked,policy_chains=16,
                full_horizon_flat_policy_chains=4,flat_reads=76,forcing_contexts=76,maximum_mean_error=max_error)
