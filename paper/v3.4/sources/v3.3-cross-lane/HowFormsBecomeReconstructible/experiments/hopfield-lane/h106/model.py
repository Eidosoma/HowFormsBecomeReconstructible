"""Matched eight-sweep access policies and three actual projection-written histories."""
import hashlib,json,time
import numpy as np
from h101 import model as original
from h103.model import effective
from h104.model import write

SEED,N,Q,F,R,D,G=106106,64,8,2,2,2,4
INPUT,HIDDEN,OUTPUT=original.INPUT,original.HIDDEN,original.OUTPUT
TOL=original.TOL
POLICIES=('standard','cue_prepare','two_start')
BRANCHES=POLICIES+('copy','donor','erased')
acquire,energy=original.acquire,original.energy

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
        acquisition_birth=rng(cohort,block,'acquisition_birth').choice([-1,1],size=(F,Q,N)).astype(np.int8),acquisition_orders=orders('acquisition_order_'),
        supplier_birth=rng(cohort,block,'supplier_birth').choice([-1,1],size=(G,2,F,R,Q,N)).astype(np.int8),
        supplier_orders=np.stack([orders(f'supplier_order_{g}_') for g in range(G)]),supplier_mask=original.mask(rng(cohort,block,'supplier_damage'),(G,F,R,N,N)),
        assay_birth=rng(cohort,block,'assay_birth').choice([-1,1],size=(D,2,F,R,Q,N)).astype(np.int8),
        assay_orders=np.stack([orders(f'assay_order_{d}_') for d in range(D)]),assay_mask=original.mask(rng(cohort,block,'assay_damage'),(D,F,R,N,N)))

def phase(packet):
    assert set(packet)=={'weights','birth','orders','clamp_indices','clamp_values'}
    w,birth,orders,indices,values=(packet[k] for k in ('weights','birth','orders','clamp_indices','clamp_values'))
    assert w.shape[-2:]==(N,N) and np.isfinite(w).all() and np.array_equal(w,w.swapaxes(-1,-2))
    assert not np.diagonal(w,axis1=-2,axis2=-1).any() and np.isin(birth,[-1,1]).all()
    steps=len(orders);assert steps in (1,4,7,8) and orders.shape==(steps,N)
    assert np.array_equal(np.sort(orders,axis=1),np.broadcast_to(np.arange(N),(steps,N)))
    shape=np.broadcast_shapes(w.shape[:-2],birth.shape[:-2])+(Q,N)
    state=np.broadcast_to(birth,shape).copy();state[...,indices]=values
    fixed=np.zeros(N,dtype=bool);fixed[indices]=True
    initial=state.copy();trace=[state.copy()];local=np.zeros((steps,N)+shape[:-1]);energies=[energy(w,state)];maximum=0.;margin=np.inf
    for s,order in enumerate(orders):
        for i in order:
            if fixed[i]:continue
            h=np.einsum('...qj,...j->...q',state,w[...,i,:]);local[s,i]=h
            old=state[...,i].copy();new=np.where(h>TOL,1,np.where(h < -TOL,-1,old)).astype(np.int8)
            maximum=max(maximum,float(np.max(-(new-old)*h)));margin=min(margin,float(np.min(np.abs(np.abs(h)-TOL))));state[...,i]=new
        trace.append(state.copy());energies.append(energy(w,state))
    return dict(initial=initial,final=state,trace=np.stack(trace),fields=local,energies=np.stack(energies),
        maximum_update_energy_increase=np.asarray(maximum),minimum_boundary_distance=np.asarray(margin))

def access(packet,policy):
    assert set(packet)=={'weights','births','orders','cues'} and policy in POLICIES
    w,births,orders,cues=(packet[k] for k in ('weights','births','orders','cues'))
    assert births.shape[0]==2 and orders.shape==(8,64)
    split=4 if policy=='two_start' else 1;first_w=w
    if policy=='cue_prepare':first_w=w.copy();first_w[...,8:,8:]=0
    first=phase(dict(weights=first_w,birth=births[0],orders=orders[:split],clamp_indices=INPUT,clamp_values=cues))
    second=phase(dict(weights=w,birth=births[1] if policy=='two_start' else first['final'],orders=orders[split:],clamp_indices=INPUT,clamp_values=cues))
    endpoint_energies=np.stack((energy(w,first['final']),energy(w,second['final'])))
    if policy=='two_start':
        selected=(endpoint_energies[1]<endpoint_energies[0]-TOL).astype(np.int8)
        final=np.where(selected[...,None]==1,second['final'],first['final'])
    else:selected=np.full(second['final'].shape[:-1],-1,dtype=np.int8);final=second['final'].copy()
    return dict(**{'phase0_'+k:v for k,v in first.items()},**{'phase1_'+k:v for k,v in second.items()},
        final=final,selected_attempt=selected,endpoint_energies=endpoint_energies,
        switch_work=endpoint_energies[0]-first['energies'][-1],endpoint_fields=np.einsum('...ij,...qj->...qi',w,final),
        coordinate_updates=np.asarray(8*56*int(np.prod(final.shape[:-1]))),full_endpoint_energy_evaluations=np.asarray(2),total_energy_evaluations=np.asarray(12))

def run_tapes(tape,timings=None):
    def timed_access(packet,policy):
        tick=time.perf_counter();data=access(packet,policy)
        if timings is not None:
            value=timings.setdefault(policy,dict(calls=0,seconds=0.));value['calls']+=1;value['seconds']+=time.perf_counter()-tick
        return data
    initial,acquisition=acquire(tape);copy=np.broadcast_to(initial[:,None],(F,R,N,N)).copy()
    current=np.stack([copy.copy() for _ in range(4)]+[copy[::-1],np.zeros_like(copy)])
    raw=dict(initial_record=initial,**{'acquisition_'+k:v for k,v in acquisition.items()})
    records=[current.copy()];assessments=[];preparations=[];suppliers=[];static=[]
    for g in range(5):
        panels=[];pre=[]
        for p,policy in enumerate(POLICIES):
            draws=[];starts=[]
            for d in range(2):
                data=timed_access(dict(weights=effective(tape['base'],current,tape['assay_mask'][d]),births=tape['assay_birth'][d],orders=tape['assay_orders'][d],cues=tape['cues']),policy)
                for k,v in data.items():raw[f'assay_g{g}_p{p}_d{d}_'+k]=v
                draws.append(data['final']);starts.append(data['phase0_final'])
            panels.append(np.stack(draws,axis=1));pre.append(np.stack(starts,axis=1))
        assessments.append(np.stack(panels));preparations.append(np.stack(pre)) # reader,history,draw,F,R,Q,N
        if g:
            fields=[np.einsum('...ij,...qj->...qi',effective(tape['base'],current[:3],tape['assay_mask'][d]),suppliers[-1]) for d in range(2)]
            static.append(np.stack(fields,axis=1))
        if g==4:break
        bodies=[];outgoing=current.copy()
        for p,policy in enumerate(POLICIES):
            data=timed_access(dict(weights=effective(tape['base'],current[p],tape['supplier_mask'][g]),births=tape['supplier_birth'][g],orders=tape['supplier_orders'][g],cues=tape['cues']),policy)
            for k,v in data.items():raw[f'supplier_g{g}_p{p}_'+k]=v
            bodies.append(data['final']);outgoing[p]=write({'activity':data['final']},'projection')
        suppliers.append(np.stack(bodies));current=outgoing;records.append(current.copy())
    raw.update(records=np.stack(records),assessments=np.stack(assessments),preparations=np.stack(preparations),suppliers=np.stack(suppliers),static_fields=np.stack(static))
    return raw
