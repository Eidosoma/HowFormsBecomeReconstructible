"""Independently reconstruct every packet and replay each actual lineage."""
import numpy as np
from h104.audit import writer
from h103.audit import writer as integer_writer,weights,replay,unpack,equal
from h105 import model as m

def network(raw,tape):
    s=dict(passed=True,coordinate_decisions=0,field_arrays_checked=0,sweep_states_checked=0,reads_replayed=0,
        maximum_field_error=0.,maximum_energy_error=0.,minimum_boundary_distance=float('inf'),writer_packets_checked=0,
        maximum_writer_error=0.,static_patterns_checked=0,minimum_static_boundary_distance=float('inf'),actual_handoffs=0,protected_record_copies=0)
    assert raw['records'].shape==(5,7,2,2,64,64) and raw['suppliers'].shape==(4,4,2,2,8,64)
    equal(raw['records'],raw['records'].swapaxes(-1,-2));assert not np.diagonal(raw['records'],axis1=-2,axis2=-1).any()
    empty=np.zeros((64,64));available=np.ones((64,64),dtype=bool)
    values=np.concatenate((np.broadcast_to(tape['cues'],(2,8,8)),tape['targets']),axis=-1)
    replay(weights(tape['base'],empty,available,4.),tape['acquisition_birth'],tape['acquisition_orders'],np.r_[m.INPUT,m.OUTPUT],values,unpack(raw,'acquisition_'),s)
    initial=integer_writer(raw['acquisition_final']);equal(initial,raw['initial_record']);equal(raw['acquisition_final'][...,48:],tape['targets'])
    copy=np.broadcast_to(initial[:,None],(2,2,64,64));current=np.stack([copy.copy() for _ in range(5)]+[copy[::-1],np.zeros_like(copy)]).astype(np.longdouble)
    equal(raw['records'][0],current)
    for g in range(5):
        np.testing.assert_allclose(raw['records'][g],current,rtol=0,atol=4e-14)
        for d in range(2):
            data=unpack(raw,f'assay_g{g}_d{d}_');w=weights(tape['base'],current,tape['assay_mask'][d])
            replay(w,tape['assay_birth'][d],tape['assay_orders'][d],m.INPUT,tape['cues'],data,s)
            equal(raw['assessments'][g,:,d],data['final'])
            if g:
                pattern=raw['suppliers'][g-1];fields=np.sum(w[:4,...,None,:,:]*pattern[...,None,:],axis=-1,dtype=np.longdouble)
                observed=raw['static_fields'][g-1,:,d];np.testing.assert_allclose(observed,fields,rtol=0,atol=2e-11)
                tol=np.longdouble('1e-12');margin=float(np.min(np.abs(np.abs(fields[...,8:])-tol)));assert margin>=5e-14
                equal(np.where(fields>tol,1,np.where(fields < -tol,-1,pattern)),np.where(observed>m.TOL,1,np.where(observed < -m.TOL,-1,pattern)))
                s['static_patterns_checked']+=int(np.prod(pattern.shape[:-1]));s['minimum_static_boundary_distance']=min(s['minimum_static_boundary_distance'],margin)
        if g==4:break
        body=unpack(raw,f'supplier_g{g}_')
        replay(weights(tape['base'],current[:4],tape['supplier_mask'][g]),tape['supplier_birth'][g],tape['supplier_orders'][g],m.INPUT,tape['cues'],body,s)
        equal(raw['suppliers'][g],body['final'])
        if g==0:equal(body['final'],np.broadcast_to(body['final'][0],body['final'].shape))
        for a,rule in enumerate(m.WRITERS):
            reference=writer(body['final'][a],rule);delta=float(np.max(np.abs(raw['records'][g+1,a]-reference)));assert delta<=4e-14
            current[a]=reference;s['writer_packets_checked']+=4;s['actual_handoffs']+=4;s['maximum_writer_error']=max(s['maximum_writer_error'],delta)
        equal(raw['records'][g+1,4:],raw['records'][g,4:]);s['protected_record_copies']+=12
    for a in range(1,5):equal(raw['assessments'][0,a],raw['assessments'][0,0])
    equal(raw['assessments'][:,4:],np.broadcast_to(raw['assessments'][0,4:],raw['assessments'][:,4:].shape))
    s.update(activity_only_writers=True,actual_suppliers_write_successors=True,assessment_matched_across_horizons=True,protected_copy_invariant=True)
    return s

def first_boundary_parity(raw,tape):
    from h104 import model as prior
    first=dict(tape)
    for key in ('supplier_birth','supplier_orders','supplier_mask'):first[key]=tape[key][0]
    old=prior.run_tapes(first);equal(raw['initial_record'],old['initial_record']);indices=[0,1,2,3,8,9,10]
    equal(raw['records'][1],old['records'][indices]);count=2
    for key,axis in (('initial',0),('final',0),('trace',1),('fields',2),('energies',1)):
        observed=raw['supplier_g0_'+key];expected=np.expand_dims(old['supplier_'+key],axis)
        equal(observed,np.broadcast_to(expected,observed.shape));count+=1
    for d in range(2):
        for key,axis in (('initial',0),('final',0),('trace',1),('fields',2),('energies',1)):
            expected=np.take(old[f'assay_d{d}_'+key],indices,axis=axis)
            expected=np.take(np.take(expected,1,axis=axis+1),0,axis=axis+1)
            equal(raw[f'assay_g1_d{d}_'+key],expected);count+=1
    return count
