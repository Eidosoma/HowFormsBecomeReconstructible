"""Four fixed writing policies through four actual supplying-body handoffs."""
import hashlib,json
import numpy as np
from h101 import model as original
from h103.model import effective
from h104.model import write

SEED,N,Q,F,R,D,G=105105,64,8,2,2,2,4
INPUT,HIDDEN,OUTPUT=original.INPUT,original.HIDDEN,original.OUTPUT
TOL=original.TOL
WRITERS=('hebbian','centered','projection','norm_hebbian')
ARMS=WRITERS+('copy','donor','erased')
read,acquire=original.read,original.acquire

def rng(cohort,block,stream):
    key=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))

def tapes(cohort,block):
    assert cohort in ('fixture','engineering','main')
    bits=(np.arange(8)[:,None]>>np.arange(3))&1;cues=(1-2*((bits@bits.T)%2)).astype(np.int8)
    targets=np.empty((F,Q,16),dtype=np.int8);gen=rng(cohort,block,'teaching')
    for f in range(F):
        for j in range(16):targets[f,:,j]=gen.permutation(np.r_[np.ones(4,dtype=np.int8),-np.ones(4,dtype=np.int8)])
    def orders(name):return np.stack([rng(cohort,block,name+str(s)).permutation(N) for s in range(8)])
    return dict(base=original.symmetric(rng(cohort,block,'base').normal(0,.12/np.sqrt(N),(N,N))),cues=cues,targets=targets,
        acquisition_birth=rng(cohort,block,'acquisition_birth').choice([-1,1],size=(F,Q,N)).astype(np.int8),
        acquisition_orders=orders('acquisition_order_'),
        supplier_birth=rng(cohort,block,'supplier_birth').choice([-1,1],size=(G,F,R,Q,N)).astype(np.int8),
        supplier_orders=np.stack([orders(f'supplier_order_{g}_') for g in range(G)]),
        supplier_mask=original.mask(rng(cohort,block,'supplier_damage'),(G,F,R,N,N)),
        assay_birth=rng(cohort,block,'assay_birth').choice([-1,1],size=(D,F,R,Q,N)).astype(np.int8),
        assay_orders=np.stack([orders(f'assay_order_{d}_') for d in range(D)]),
        assay_mask=original.mask(rng(cohort,block,'assay_damage'),(D,F,R,N,N)))

def run_tapes(tape):
    initial,acquisition=acquire(tape);copy=np.broadcast_to(initial[:,None],(F,R,N,N)).copy()
    current=np.stack([copy.copy() for _ in range(5)]+[copy[::-1],np.zeros_like(copy)])
    raw=dict(initial_record=initial,**{'acquisition_'+k:v for k,v in acquisition.items()})
    records=[current.copy()];assessments=[];suppliers=[];static=[]
    for g in range(G+1):
        panels=[];fixed_fields=[]
        for d in range(D):
            w=effective(tape['base'],current,tape['assay_mask'][d])
            data=read(dict(weights=w,birth=tape['assay_birth'][d],orders=tape['assay_orders'][d],clamp_indices=INPUT,clamp_values=tape['cues']))
            for k,v in data.items():raw[f'assay_g{g}_d{d}_'+k]=v
            panels.append(data['final'])
            if g:fixed_fields.append(np.einsum('...ij,...qj->...qi',w[:4],suppliers[-1]))
        assessments.append(np.stack(panels,axis=1)) # arm,draw,founder,lineage,cue,neuron
        if g:static.append(np.stack(fixed_fields,axis=1))
        if g==G:break
        body=read(dict(weights=effective(tape['base'],current[:4],tape['supplier_mask'][g]),birth=tape['supplier_birth'][g],
            orders=tape['supplier_orders'][g],clamp_indices=INPUT,clamp_values=tape['cues']))
        for k,v in body.items():raw[f'supplier_g{g}_'+k]=v
        suppliers.append(body['final']);outgoing=current.copy()
        for a,rule in enumerate(WRITERS):outgoing[a]=write({'activity':body['final'][a]},rule)
        current=outgoing;records.append(current.copy())
    raw.update(records=np.stack(records),assessments=np.stack(assessments),suppliers=np.stack(suppliers),static_fields=np.stack(static))
    return raw
