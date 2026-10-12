"""Independent retained-record extraction, classifications, graphs and inference."""
import hashlib
import json
import numpy as np
from E032_renewal_failure_diagnosis import audit as prior

CONDITIONS=('standard_preserve','standard_rewrite','bridge_preserve','bridge_rewrite',
    'contrast_preserve','bridge_read_blocked','bridge_write_blocked','protected_copy','masked_copy',
    'bridge_rewrite_read_blocked','bridge_rewrite_write_blocked')
ACTIVE=(0,1,2,3,4,5,6,9,10)
HORIZONS=(0,1,3,8,16,24,32)
RULES=np.array([1.,-1.,1.,-1.])


def load(source,name,complete):
    path=source/name; blob=path.read_bytes()
    assert hashlib.sha256(blob).hexdigest()==complete['outputs_sha256'][name]
    with np.load(path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
    if '__index__' in data:
        index=json.loads(data.pop('__index__').tobytes())
        assert index['format'] in ('E031_compact_v1','E041_source_v1') and sorted(data)==index['retained']
        for k,v in data.items():
            assert index['arrays'][k]['shape']==list(v.shape)
            assert index['arrays'][k]['dtype']==v.dtype.str
            assert index['arrays'][k]['sha256']==hashlib.sha256(v.tobytes()).hexdigest()
    return data


def available(mask):
    result=np.empty((*mask.shape[:-2],2,16,16),bool)
    for y in range(16):
        for x in range(16):
            result[...,0,y,x]=~(mask[...,y,x]|mask[...,y,(x+1)%16])
            result[...,1,y,x]=~(mask[...,y,x]|mask[...,(y+1)%16,x])
    return result


def repair(old,new,live,last_live,last_return):
    rows=[]
    for i in np.ndindex(new.shape[:-3]):
        a,b,ok,previous,young_mask=[x[i].ravel() for x in (old,new,live,last_live,last_return)]
        returning=ok&~previous; weak=ok&(a!=0)&(abs(a)<=.5); zero=ok&(a==0); young=weak&young_mask
        count=np.count_nonzero
        rows.append([count(ok),count(returning),count(b[returning]),count(abs(b[returning])>.5),abs(b[returning]).sum(),
            count(weak),count(abs(b[weak])>.5),count(b[weak]==0),count(zero),count(b[zero]),count(abs(b[zero])>.5),abs(b[zero]).sum(),
            count(young),count(abs(b[young])>.5),count(b[young]==0),abs(a[young]).sum(),abs(b[young]).sum()])
    return np.asarray(rows).reshape(*new.shape[:-3],17)


def joint(terminal,body):
    result=np.zeros((6,9,*body.shape[2:4],11))
    for t,h in enumerate((1,3,8,16,24,32)):
        for j,c in enumerate(ACTIVE):
            for f,r in np.ndindex(body.shape[2:4]):
                a,b,d=[bool(terminal[t+1,c,f,r,k,0]) for k in range(3)]
                current=bool(body[h-1,j,f,r,0]); after=bool(body[h,j,f,r,0]) if h!=32 else False
                result[t,j,f,r]=[a and b,a and not b,not a and b,not a and not b,
                    not b and d,not b and (a or d),not(a or b or d),not b and current,
                    not a and current,not b and after,not b and h!=32]
    return result


def inspect(source,block,complete,saved):
    acquired=load(source,f'source_{block:06d}.npz',complete)['acquired'][1]
    R=saved['packet'].shape[3]; original=prior.unpack(acquired)[:,None].repeat(R,axis=1)
    old=original[None].repeat(11,axis=0); live=np.ones_like(old,bool); returned=np.zeros_like(live)
    np.testing.assert_array_equal(saved['packet'][0],prior.record(old,old,original,live,True))
    packets={0:old[:4].copy()}; bodies=[]
    for g in range(1,33):
        raw=load(source,f'boundary_{block:06d}_g{g}.npz',complete)
        new=prior.unpack(raw['outgoing']); previous_live=live
        live=np.broadcast_to(available(raw['renewal_mask']),new.shape).copy();live[7]=True
        np.testing.assert_array_equal(saved['packet'][g],prior.record(old,new,original,live))
        np.testing.assert_allclose(saved['repair'][g-1],repair(old,new,live,previous_live,returned),rtol=1e-14,atol=1e-12)
        np.testing.assert_array_equal(saved['repair'][g-1][...,[0,1,2,3,5,6,7,8,9,10,12,13,14]],
            repair(old,new,live,previous_live,returned)[...,[0,1,2,3,5,6,7,8,9,10,12,13,14]])
        bodies.append(prior.output(raw['developed_mean_ports'],RULES[None,:,None]))
        if g in HORIZONS:packets[g]=new[:4].copy()
        returned=live&~previous_live; old=new
    bodies=np.stack(bodies);np.testing.assert_array_equal(saved['body'],bodies)
    np.testing.assert_array_equal(saved['transitions'],prior.history(bodies[...,0]))
    terminals=[]
    for t,h in enumerate(HORIZONS):
        raw=load(source,f'assay_{block:06d}_h{h}.npz',complete)
        n=len(raw['mean_ports'])//2
        ports=raw['mean_ports'][n:,:,:,:,:,0,:].transpose(0,1,2,4,3,5)
        if h==0:ports=ports.repeat(11,axis=0)
        values=prior.output(ports,RULES[None,:,None,None]);terminals.append(values)
        np.testing.assert_array_equal(saved['terminal'][t],values)
        weights=packets[h][:,:,:,None]*available(raw['masks'])[None]
        expected=np.concatenate([prior.graph((abs(weights)>cutoff).astype(float)) for cutoff in (0.,.5)],axis=-1)
        np.testing.assert_array_equal(saved['graph'][t],expected)
    terminal=np.stack(terminals)
    np.testing.assert_array_equal(saved['terminal_transitions'],prior.history(terminal[...,0]))
    np.testing.assert_array_equal(saved['joint'],joint(terminal,bodies))
    cases=load(source,f'cases_{block:06d}.npz',complete)
    np.testing.assert_array_equal(bodies[...,0],cases['body_correct'].all(axis=-1))
    np.testing.assert_array_equal(bodies[...,5],cases['body_margin'].min(axis=-1))
    offset=0
    for i,h in enumerate(HORIZONS):
        n=1 if h==0 else 11; rows=cases['correct'][offset+n:offset+2*n,:,:,:,:,0].all(axis=3)
        if h==0:rows=rows.repeat(11,axis=0)
        np.testing.assert_array_equal(terminal[i,...,0],rows);offset+=2*n
    return True


def check_summaries(summary,data):
    key=json.dumps(['E042','bootstrap','late_failure'],separators=(',',':')).encode()
    seed=int.from_bytes(hashlib.sha256(key).digest()[:16],'little'); count=len(summary['blocks'])
    draws=np.random.Generator(np.random.PCG64(seed)).integers(0,count,(10000,count)).T
    for name,spec in summary['definitions'].items():
        kind,stage,condition,feature=[spec[k] for k in ('kind','stage','condition','feature')]
        x=data[kind][:,stage,condition]
        if spec['injury'] is not None:x=x[:,:,:,spec['injury']]
        values=x[...,feature]
        selected=np.ones(values.shape,bool)
        if spec['subset'] is not None:
            q=spec['subset']; selected=data[q['kind']][:,q['stage'],q['condition'],:,:,q['injury'],q['feature']].astype(bool)
            if q['invert']:selected=~selected
        denominator=selected.sum(axis=(1,2)) if spec['denominator'] is None else (x[...,spec['denominator']]*selected).sum(axis=(1,2))
        numerator=(values*selected).sum(axis=(1,2)); stats=summary['series'][name]
        np.testing.assert_array_equal(numerator,stats['block_numerators'])
        np.testing.assert_array_equal(denominator,stats['block_denominators'])
        assert stats['mean']==(float(numerator.sum()/denominator.sum()) if denominator.sum() else None)
        n=numerator[draws].sum(axis=0);d=denominator[draws].sum(axis=0);valid=d>0
        expected=np.percentile(n[valid]/d[valid],[2.5,97.5]).tolist() if valid.any() else None
        if expected is None:assert stats['ci95'] is None
        else:np.testing.assert_allclose(stats['ci95'],expected,rtol=1e-14,atol=1e-12)
        assert stats['valid_bootstrap_draws']==int(valid.sum())
    assert set(summary['series'])==set(summary['definitions'])
