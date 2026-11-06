"""H102-qualified gain-two bodies, one-shot interventions and four actual handoffs."""
import hashlib,json
import numpy as np
from h101 import model as original

SEED,N,Q,F,R,D,G=103103,64,8,2,2,2,4
ENGINEERING,DEVELOPMENT,CONFIRMATION=4,16,32
ACQUISITION_GAIN,ASSESSMENT_GAIN,SUPPLYING_GAIN=4.,2.,2.
INPUT,HIDDEN,OUTPUT=original.INPUT,original.HIDDEN,original.OUTPUT
ROUTES,CANDIDATES,VARIANTS=original.ROUTES,original.CANDIDATES,original.VARIANTS
TOL,UPPER=original.TOL,original.UPPER
symmetric,mask=original.symmetric,original.mask
read,write,acquire,interventions=original.read,original.write,original.acquire,original.interventions

def rng(cohort,block,stream):
    key=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))

def tapes(cohort,block):
    assert cohort in ('fixture','engineering','development','confirmation')
    bits=(np.arange(8)[:,None]>>np.arange(3))&1
    cues=(1-2*((bits@bits.T)%2)).astype(np.int8)
    targets=np.empty((F,Q,16),dtype=np.int8);gen=rng(cohort,block,'teaching')
    for f in range(F):
        for j in range(16):targets[f,:,j]=gen.permutation(np.r_[np.ones(4,dtype=np.int8),-np.ones(4,dtype=np.int8)])
    return dict(base=symmetric(rng(cohort,block,'base').normal(0,.12/np.sqrt(N),(N,N))),cues=cues,targets=targets,
        priority=rng(cohort,block,'weak_ties').random((F,len(UPPER[0]))),random_priority=rng(cohort,block,'random_control').random((F,len(UPPER[0]))),
        acquisition_birth=rng(cohort,block,'acquisition_birth').choice([-1,1],size=(F,Q,N)).astype(np.int8),
        acquisition_orders=np.stack([rng(cohort,block,'acquisition_order_'+str(s)).permutation(N) for s in range(8)]),
        writer_birth=rng(cohort,block,'writer_birth').choice([-1,1],size=(G,F,R,Q,N)).astype(np.int8),
        writer_orders=np.stack([np.stack([rng(cohort,block,f'writer_order_{g}_{s}').permutation(N) for s in range(8)]) for g in range(G)]),
        writer_mask=mask(rng(cohort,block,'writer_damage'),(G,F,R,N,N)),
        assay_birth=rng(cohort,block,'assay_birth').choice([-1,1],size=(D,F,R,Q,N)).astype(np.int8),
        assay_orders=np.stack([np.stack([rng(cohort,block,f'assay_order_{d}_{s}').permutation(N) for s in range(8)]) for d in range(D)]),
        assay_mask=mask(rng(cohort,block,'assay_damage'),(D,F,R,N,N)),
        assay_uniform=rng(cohort,block,'assay_damage').random((D,F,R,N,N)))

def effective(base,record,available):
    cue=np.arange(N)<8;gain=np.where(cue[:,None]^cue[None,:],2.,1.)
    return (base+record*available)*gain

def run_tapes(tape,variants=VARIANTS):
    initial,acquisition=acquire(tape);starting,selections,scales=interventions(initial,tape['priority'],tape['random_priority'],variants)
    current=np.broadcast_to(starting[:,None,:,None],(len(variants),len(ROUTES),F,R,N,N)).copy()
    raw=dict(initial_record=initial,starting_records=starting,
        setting_acquisition_gain=np.asarray(ACQUISITION_GAIN),setting_assessment_gain=np.asarray(ASSESSMENT_GAIN),
        setting_supplying_gain=np.asarray(SUPPLYING_GAIN),**{'acquisition_'+k:v for k,v in acquisition.items()},
        **{'selection_'+k:v for k,v in selections.items()},**{'scale_'+k:v for k,v in scales.items()})
    records=[current.copy()];assays=[];suppliers=[]
    for g in range(G+1):
        panels=[]
        for draw in range(D):
            weights=effective(tape['base'],current,tape['assay_mask'][draw])
            data=read(dict(weights=weights,birth=tape['assay_birth'][draw],orders=tape['assay_orders'][draw],clamp_indices=INPUT,clamp_values=tape['cues']))
            for k,v in data.items():raw[f'assay_g{g}_d{draw}_'+k]=v
            panels.append(data['final'])
        assays.append(np.stack(panels,axis=2)) # variant, route, draw, founder, lineage, cue, neuron
        if g==G:break
        weights=effective(tape['base'],current,tape['writer_mask'][g])
        body=read(dict(weights=weights,birth=tape['writer_birth'][g],orders=tape['writer_orders'][g],clamp_indices=INPUT,clamp_values=tape['cues']))
        for k,v in body.items():raw[f'writer_g{g}_'+k]=v
        suppliers.append(body['final']);outgoing=current.copy()
        outgoing[:,0]=write(dict(activity=body['final'][:,0]));outgoing[:,1]=write(dict(activity=body['final'][:,1]),True)
        # Only the copy route retains an incoming record; both writers are complete.
        current=outgoing;records.append(current.copy())
    raw.update(records=np.stack(records),assessments=np.stack(assays),supplying_bodies=np.stack(suppliers))
    return raw
