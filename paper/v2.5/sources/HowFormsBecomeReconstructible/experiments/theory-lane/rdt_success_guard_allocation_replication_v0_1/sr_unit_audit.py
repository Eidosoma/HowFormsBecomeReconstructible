"""Independent scalar outcomes, full coupled lineage and subset/forcing audit."""
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


def independent_order(stage,block,generation):
    value=[P['namespace'],stage,int(block),0,int(generation),'promotion_subset']
    seed=int.from_bytes(hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed)).permutation(np.arange(4,dtype=np.int64))


def scalar_actions(classes,order,generation):
    if generation==33:return np.zeros((4,4),bool)
    k=sum(classes[j][2]==1 for j in range(4));chosen=set(int(v) for v in order[:k])
    return np.array([[True,j in chosen,classes[j][2]==1,False] for j in range(4)],bool)


def independent_environment(stage,key,generation,injury,regime):
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
    if raw['windows'].shape!=(19,4,32,4,2,2) or raw['incoming'].shape!=(19,4,4,2,16,16):raise ArithmeticError('Full coupled horizon required')
    if raw['generations'].tolist()!=list(range(15,34)):raise ArithmeticError('Wrong generations')
    checked=0;max_error=0.;seen_success=[False]*4;interior=0;different=0
    for j,row in enumerate(rows):
        if digest(raw['initial_packets'][j])!=row['packet_sha256']:raise ArithmeticError('Wrong initial packet')
        if int(raw['histories'][j])!=row['current_pass'] or int(raw['rules'][j])!=row['rule']:raise ArithmeticError('Source labels changed')
    for k,generation in enumerate(range(15,34)):
        primary_classes=[];flat_classes=[]
        for j,row in enumerate(rows):
            mask,birth,hashes=independent_environment(stage,row['key'],generation,injury,regime)
            rec=receipt['forcing'][4*k+j]
            if rec['key']!=row['key'] or rec['generation']!=generation or rec['injury']!=injury or rec['regime']!=regime:raise ArithmeticError('Forcing key coverage')
            if any(rec[name]!=value for name,value in hashes.items()):raise ArithmeticError('Forcing stream mismatch')
            byte_equal(raw['mask'][k,j],mask,'independent injury regeneration');byte_equal(raw['birth'][k,j],birth,'independent birth regeneration')
            primary_one=[];flat_one=[]
            for arm in range(4):
                cls,means=raw_class(raw['windows'][k,j,:,arm],row['rule']);fc,_=raw_class(raw['flat_windows'][k,j,:,arm],row['rule'])
                if cls!=int(raw['classes'][k,j,arm]) or (cls==1)!=bool(raw['passed'][k,j,arm]):raise ArithmeticError('Independent native endpoint mismatch')
                if fc!=cls:raise ArithmeticError('Independently propagated endpoint differs')
                max_error=max(max_error,float(np.max(abs(np.array(means).reshape(2,2)-raw['aligned'][k,j,arm]))))
                primary_one.append(cls);flat_one.append(fc);checked+=1
                if k==0:
                    byte_equal(raw['incoming'][k,j,arm],raw['initial_packets'][j],'initial state')
                    byte_equal(raw['flat_incoming'][k,j,arm],raw['initial_packets'][j],'flat initial state')
                if arm==3:byte_equal(raw['incoming'][k,j,arm],raw['initial_packets'][j],'protected record')
            primary_classes.append(primary_one);flat_classes.append(flat_one)
            if not seen_success[j]:
                byte_equal(raw['incoming'][k,j,2],raw['incoming'][k,j,3],'guard/protected identity until first success')
                byte_equal(raw['windows'][k,j,:,2],raw['windows'][k,j,:,3],'shared first recovery by construction')
            seen_success[j]|=primary_one[2]==1
            if k==0:
                for arm in (1,2,3):byte_equal(raw['windows'][0,j,:,0],raw['windows'][0,j,:,arm],'pre-action identity')
        order=independent_order(stage,rows[0]['block'],generation)
        byte_equal(raw['allocation_order'][k],order,'independent random subset order')
        acts=scalar_actions(primary_classes,order,generation);fa=scalar_actions(flat_classes,order,generation)
        byte_equal(raw['actions'][k],acts,'independent coupled action rule');byte_equal(raw['flat_actions'][k],fa,'independent flat coupled rule')
        count=int(acts[:,2].sum())
        if int(raw['quota_count'][k])!=count or int(acts[:,1].sum())!=count:raise ArithmeticError('Quota count mismatch')
        wanted=dict(generation=generation,block=rows[0]['block'],order=order.tolist(),guard_promotions=count,random_promotions=int(acts[:,1].sum()))
        if receipt['allocation'][k]!=wanted:raise ArithmeticError('Allocation receipt differs')
        if generation<33:
            interior+=int(0<count<4);different+=int(not np.array_equal(acts[:,1],acts[:,2]))
            for j in range(4):
                for arm in range(4):
                    expected=raw['outgoing'][k,j,arm] if acts[j,arm] else raw['incoming'][k,j,arm]
                    flat_expected=raw['flat_outgoing'][k,j,arm] if fa[j,arm] else raw['flat_incoming'][k,j,arm]
                    byte_equal(raw['incoming'][k+1,j,arm],expected,'primary inheritance')
                    byte_equal(raw['flat_incoming'][k+1,j,arm],flat_expected,'independent full-group inheritance')
        for name in ('incoming','end','windows','outgoing','actions'):byte_equal(raw['flat_'+name][k],raw[name][k],'full coupled flat '+name)
    if max_error>1e-12:raise ArithmeticError('Scalar mean differs')
    byte_equal(raw['final_packets'],raw['incoming'][-1],'terminal candidate not inherited')
    expected=[dict(generation=g,packets=4,policies=4,byte_exact=True) for g in range(15,34)]
    if receipt['audits']!=expected or receipt['native_reads']!=304 or receipt['flat_native_reads']!=304:raise ArithmeticError('Full-group audit cost mismatch')
    return dict(status='PASS',native_readouts_independently_scored=checked,policy_chains=16,full_horizon_flat_policy_chains=16,
                flat_reads=304,forcing_contexts=76,quota_generations_checked=19,interior_quota_generations=interior,
                different_guard_random_action_generations=different,maximum_mean_error=max_error)
