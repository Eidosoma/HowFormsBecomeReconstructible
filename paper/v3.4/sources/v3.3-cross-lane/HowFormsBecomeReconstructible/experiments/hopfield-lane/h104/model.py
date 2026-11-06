"""One supplying-body handoff, with matched source, writer, injury and birth factors."""
import hashlib,json
import numpy as np
from h101 import model as original
from h103.model import effective

SEED,N,Q,F,R,D=104104,64,8,2,2,2
INPUT,HIDDEN,OUTPUT=original.INPUT,original.HIDDEN,original.OUTPUT
TOL=original.TOL
WRITERS=('hebbian','centered','projection','norm_hebbian')
SOURCES=('actual','ancestral')
BRANCHES=tuple(s+'_'+w for s in SOURCES for w in WRITERS)+('copy','donor','erased')
INJURIES=('intact','damaged');BIRTHS=('fresh','captured')
read,acquire=original.read,original.acquire

def rng(cohort,block,stream):
    key=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))

def tapes(cohort,block):
    assert cohort in ('fixture','engineering','main')
    bits=(np.arange(8)[:,None]>>np.arange(3))&1
    cues=(1-2*((bits@bits.T)%2)).astype(np.int8)
    targets=np.empty((F,Q,16),dtype=np.int8);gen=rng(cohort,block,'teaching')
    for f in range(F):
        for j in range(16):targets[f,:,j]=gen.permutation(np.r_[np.ones(4,dtype=np.int8),-np.ones(4,dtype=np.int8)])
    def orders(name):return np.stack([rng(cohort,block,name+str(s)).permutation(N) for s in range(8)])
    return dict(base=original.symmetric(rng(cohort,block,'base').normal(0,.12/np.sqrt(N),(N,N))),cues=cues,targets=targets,
        acquisition_birth=rng(cohort,block,'acquisition_birth').choice([-1,1],size=(F,Q,N)).astype(np.int8),
        acquisition_orders=orders('acquisition_order_'),
        supplier_birth=rng(cohort,block,'supplier_birth').choice([-1,1],size=(F,R,Q,N)).astype(np.int8),
        supplier_orders=orders('supplier_order_'),supplier_mask=original.mask(rng(cohort,block,'supplier_damage'),(F,R,N,N)),
        assay_birth=rng(cohort,block,'assay_birth').choice([-1,1],size=(D,F,R,Q,N)).astype(np.int8),
        assay_orders=np.stack([orders(f'assay_order_{d}_') for d in range(D)]),
        assay_mask=original.mask(rng(cohort,block,'assay_damage'),(D,F,R,N,N)))

def write(packet,rule):
    assert set(packet)=={'activity'} and rule in WRITERS
    x=packet['activity'];assert x.shape[-2:]==(Q,N) and x.dtype==np.int8 and np.isin(x,[-1,1]).all()
    if rule in ('hebbian','centered'):return original.write(packet,rule=='centered')
    y=x.astype(np.float64);gram=y@y.swapaxes(-1,-2)
    # The orthogonal cue columns make every Gram matrix full rank. No cutoff.
    np.testing.assert_array_equal(x[...,:8]@x[...,:8].swapaxes(-1,-2),np.broadcast_to(8*np.eye(8),gram.shape))
    q=y.swapaxes(-1,-2)@np.linalg.solve(gram,y);p=(q+q.swapaxes(-1,-2))/2
    p[...,np.arange(N),np.arange(N)]=0
    if rule=='projection':return p
    h=original.write(packet);scale=np.linalg.norm(p,axis=(-2,-1))/np.linalg.norm(h,axis=(-2,-1))
    return h*scale[...,None,None]

def panel_births(tape,reference,draw):
    fresh=np.broadcast_to(tape['assay_birth'][draw],reference.shape)
    return np.stack((fresh,reference),axis=1)[:,None] # branch, injury singleton, birth, F,R,Q,N

def panel_masks(tape,draw):
    intact=np.ones_like(tape['assay_mask'][draw]);intact[...,np.arange(N),np.arange(N)]=False
    return np.stack((intact,tape['assay_mask'][draw]))

def run_tapes(tape):
    initial,acquisition=acquire(tape)
    body=read(dict(weights=effective(tape['base'],initial[:,None],tape['supplier_mask']),birth=tape['supplier_birth'],
        orders=tape['supplier_orders'],clamp_indices=INPUT,clamp_values=tape['cues']))
    actual=body['final'];ancestral=np.broadcast_to(acquisition['final'][:,None],actual.shape).copy()
    records=[];reference=[]
    for x in (actual,ancestral):
        for rule in WRITERS:records.append(write({'activity':x},rule));reference.append(x)
    copy=np.broadcast_to(initial[:,None],(F,R,N,N)).copy()
    records.extend((copy,copy[::-1],np.zeros_like(copy)));reference.extend((actual,actual,actual))
    records=np.stack(records);reference=np.stack(reference)
    raw=dict(initial_record=initial,records=records,reference=reference,
        **{'acquisition_'+k:v for k,v in acquisition.items()},**{'supplier_'+k:v for k,v in body.items()})
    assessments=[];static=[];masks=[]
    for draw in range(D):
        available=panel_masks(tape,draw);w=effective(tape['base'],records[:,None],available)
        data=read(dict(weights=w[:,:,None],birth=panel_births(tape,reference,draw),orders=tape['assay_orders'][draw],
            clamp_indices=INPUT,clamp_values=tape['cues']))
        for k,v in data.items():raw[f'assay_d{draw}_'+k]=v
        assessments.append(data['final']);masks.append(available)
        static.append(np.einsum('...ij,...qj->...qi',w,reference[:,None]))
    raw.update(assessments=np.stack(assessments,axis=3),static_fields=np.stack(static,axis=2),injury_masks=np.stack(masks))
    return raw
