"""Rational projector checks, independently built records and long-double neural replay."""
import numpy as np
from h077.audit import exact_projector
from h103.audit import writer as integer_writer,weights,replay,unpack,equal
from h104 import model as m

def writer(x,rule):
    if rule in ('hebbian','centered'):return integer_writer(x,rule=='centered').astype(np.longdouble)
    values=[]
    for pattern in x.reshape((-1,8,64)):
        cue=pattern[:,:8].astype(np.int64);equal(cue@cue.T,8*np.eye(8,dtype=int))
        gram=pattern.astype(np.float64)@pattern.astype(np.float64).T
        ev=np.linalg.eigvalsh(gram);assert ev[0]>=8-1e-12 and ev[-1]/ev[0]<=64+1e-12
        q,rank=exact_projector(pattern);assert rank==8;q=(q+q.T)/2
        np.testing.assert_allclose(q@q,q,rtol=0,atol=4e-14)
        np.testing.assert_allclose(pattern.astype(np.longdouble)@q,pattern,rtol=0,atol=4e-14)
        p=q.copy();np.fill_diagonal(p,0)
        if rule=='norm_hebbian':
            h=integer_writer(pattern).astype(np.longdouble)
            p=h*np.sqrt(np.sum(p*p,dtype=np.longdouble)/np.sum(h*h,dtype=np.longdouble))
        values.append(p)
    return np.stack(values).reshape(x.shape[:-2]+(64,64))

def stats():return dict(passed=True,coordinate_decisions=0,field_arrays_checked=0,sweep_states_checked=0,reads_replayed=0,
    maximum_field_error=0.,maximum_energy_error=0.,minimum_boundary_distance=float('inf'),writer_packets_checked=0,
    maximum_writer_error=0.,static_patterns_checked=0,h103_first_boundary_parity_arrays=0)

def network(raw,tape):
    s=stats();initial=raw['initial_record'];empty=np.zeros((64,64));available=np.ones((64,64),dtype=bool)
    values=np.concatenate((np.broadcast_to(tape['cues'],(2,8,8)),tape['targets']),axis=-1)
    replay(weights(tape['base'],empty,available,4.),tape['acquisition_birth'],tape['acquisition_orders'],np.r_[m.INPUT,m.OUTPUT],
        values,unpack(raw,'acquisition_'),s)
    equal(initial,integer_writer(raw['acquisition_final']));equal(raw['acquisition_final'][...,48:],tape['targets'])
    replay(weights(tape['base'],initial[:,None],tape['supplier_mask']),tape['supplier_birth'],tape['supplier_orders'],m.INPUT,tape['cues'],unpack(raw,'supplier_'),s)
    actual=raw['supplier_final'];ancestral=np.broadcast_to(raw['acquisition_final'][:,None],actual.shape)
    refs=[];references=[]
    for pattern in (actual,ancestral):
        for rule in m.WRITERS:
            ref=writer(pattern,rule);index=len(refs);delta=float(np.max(np.abs(raw['records'][index]-ref)))
            assert delta<=4e-14;s['maximum_writer_error']=max(s['maximum_writer_error'],delta)
            refs.append(ref);references.append(pattern);s['writer_packets_checked']+=4
    copy=np.broadcast_to(initial[:,None],(2,2,64,64)).astype(np.longdouble)
    refs.extend((copy,copy[::-1],np.zeros_like(copy)));references.extend((actual,actual,actual))
    refs=np.stack(refs);reference=np.stack(references);equal(raw['reference'],reference)
    equal(raw['records'][8:],refs[8:]);equal(raw['records'][4],raw['records'][8])
    equal(raw['records'],raw['records'].swapaxes(-1,-2));assert not np.diagonal(raw['records'],axis1=-2,axis2=-1).any()
    for start in (0,4):
        np.testing.assert_allclose(np.linalg.norm(raw['records'][start+2],axis=(-2,-1)),np.linalg.norm(raw['records'][start+3],axis=(-2,-1)),rtol=0,atol=4e-14)
    for draw in range(2):
        intact=np.ones_like(tape['assay_mask'][draw]);intact[...,np.arange(64),np.arange(64)]=False
        mask=np.stack((intact,tape['assay_mask'][draw]));equal(raw['injury_masks'][draw],mask)
        equal(mask,mask.swapaxes(-1,-2));assert not np.diagonal(mask,axis1=-2,axis2=-1).any()
        fresh=np.broadcast_to(tape['assay_birth'][draw],reference.shape)
        births=np.stack((fresh,reference),axis=1)[:,None]
        w=weights(tape['base'],refs[:,None],mask);data=unpack(raw,f'assay_d{draw}_')
        replay(w[:,:,None],births,tape['assay_orders'][draw],m.INPUT,tape['cues'],data,s)
        equal(raw['assessments'][:,:,:,draw],data['final']);equal(data['final'][4,:,0],data['final'][8,:,0])
        fields=np.sum(w[...,None,:,:]*reference[:,None,...,None,:],axis=-1,dtype=np.longdouble)
        np.testing.assert_allclose(raw['static_fields'][:,:,draw],fields,rtol=0,atol=2e-11)
        tol=np.longdouble('1e-12');old=np.broadcast_to(reference[:,None],fields.shape)
        changed=np.where(fields>tol,1,np.where(fields < -tol,-1,old))!=old
        static_margin=float(np.min(np.abs(np.abs(fields[...,8:])-tol)));assert static_margin>=5e-14
        observed=raw['static_fields'][:,:,draw]
        equal(np.where(observed>m.TOL,1,np.where(observed < -m.TOL,-1,old)),np.where(fields>tol,1,np.where(fields < -tol,-1,old)))
        stable=~changed[...,8:].any(-1)
        for step in data['trace']:
            observed=step[:,:,1];equal(observed[stable],old[stable])
        s['static_patterns_checked']+=stable.size
    s['actual_pattern_writer_packets']=16;s['ancestral_diagnostic_writer_packets']=16
    s['primary_actual_handoff_readouts']=4*2*4;s['extra_information_branches_labeled']=True
    return s

def first_boundary_parity(raw,tape):
    """H103 primitives, on the same H104 fixture tapes, without a new cohort."""
    from h103 import model as old
    initial,acq=old.acquire(tape);equal(initial,raw['initial_record']);count=0
    supplier=old.read(dict(weights=old.effective(tape['base'],initial[:,None],tape['supplier_mask']),birth=tape['supplier_birth'],orders=tape['supplier_orders'],clamp_indices=old.INPUT,clamp_values=tape['cues']))
    for key in ('initial','final','trace','fields','energies'):equal(supplier[key],raw['supplier_'+key]);count+=1
    record=old.write({'activity':supplier['final']});equal(record,raw['records'][0])
    for draw in range(2):
        data=old.read(dict(weights=old.effective(tape['base'],record,tape['assay_mask'][draw]),birth=tape['assay_birth'][draw],orders=tape['assay_orders'][draw],clamp_indices=old.INPUT,clamp_values=tape['cues']))
        saved=unpack(raw,f'assay_d{draw}_')
        for key,axis in (('initial',0),('final',0),('trace',1),('fields',2),('energies',1)):
            panel=np.take(saved[key],0,axis=axis);panel=np.take(panel,1,axis=axis);panel=np.take(panel,0,axis=axis)
            equal(data[key],panel);count+=1
    return count
