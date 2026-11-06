"""Phase replay, restart selection, equal budgets and actual record chains."""
import numpy as np
from h104.audit import writer
from h103.audit import writer as integer_writer,weights,replay,unpack,equal
from h106 import model as m

def stats():return dict(passed=True,coordinate_decisions=0,field_arrays_checked=0,sweep_states_checked=0,reads_replayed=0,
    maximum_field_error=0.,maximum_energy_error=0.,minimum_boundary_distance=float('inf'),writer_packets_checked=0,maximum_writer_error=0.,
    static_patterns_checked=0,minimum_static_boundary_distance=float('inf'),actual_handoffs=0,protected_record_copies=0,access_calls=0,
    access_coordinate_updates=0,selection_decisions=0,nonduplicate_selection_decisions=0,duplicate_endpoint_ties=0,
    minimum_selection_boundary_distance=float('inf'),endpoint_energy_values_checked=0,maximum_endpoint_energy_error=0.)

def check_access(w,births,orders,cues,policy,data,s):
    first=unpack(data,'phase0_');second=unpack(data,'phase1_');split=4 if policy=='two_start' else 1;pre=w
    if policy=='cue_prepare':pre=w.copy();pre[...,8:,8:]=0
    before=s['coordinate_decisions']
    replay(pre,births[0],orders[:split],m.INPUT,cues,first,s)
    replay(w,births[1] if policy=='two_start' else first['final'],orders[split:],m.INPUT,cues,second,s)
    energy=lambda x:-np.sum(x*np.einsum('...ij,...qj->...qi',w,x),axis=-1,dtype=np.longdouble)/2
    endpoints=np.stack((energy(first['final']),energy(second['final'])));delta=float(np.max(np.abs(endpoints-data['endpoint_energies'])))
    assert delta<=2e-11;s['maximum_endpoint_energy_error']=max(s['maximum_endpoint_energy_error'],delta)
    pre_energy=-np.sum(first['final']*np.einsum('...ij,...qj->...qi',pre,first['final']),axis=-1,dtype=np.longdouble)/2
    np.testing.assert_allclose(data['switch_work'],endpoints[0]-pre_energy,rtol=0,atol=2e-11)
    if policy=='two_start':
        difference=endpoints[1]-endpoints[0];selected=(difference < -np.longdouble('1e-12')).astype(np.int8)
        duplicates=(first['final']==second['final']).all(-1);equal(selected[duplicates],np.zeros(int(duplicates.sum()),dtype=np.int8))
        if (~duplicates).any():
            margin=float(np.min(np.abs(difference[~duplicates]+np.longdouble('1e-12'))));assert margin>=5e-14
            s['minimum_selection_boundary_distance']=min(s['minimum_selection_boundary_distance'],margin)
        s['selection_decisions']+=selected.size;s['nonduplicate_selection_decisions']+=int((~duplicates).sum());s['duplicate_endpoint_ties']+=int(duplicates.sum())
        final=np.where(selected[...,None]==1,second['final'],first['final'])
    else:selected=np.full(second['final'].shape[:-1],-1,dtype=np.int8);final=second['final']
    equal(data['selected_attempt'],selected);equal(data['final'],final)
    fields=np.einsum('...ij,...qj->...qi',w,final);np.testing.assert_allclose(data['endpoint_fields'],fields,rtol=0,atol=2e-11)
    margin=float(np.min(np.abs(np.abs(fields[...,8:])-np.longdouble('1e-12'))));assert margin>=5e-14
    s['minimum_static_boundary_distance']=min(s['minimum_static_boundary_distance'],margin)
    old=final;tol=np.longdouble('1e-12');observed=data['endpoint_fields']
    equal(np.where(fields>tol,1,np.where(fields < -tol,-1,old)),np.where(observed>m.TOL,1,np.where(observed < -m.TOL,-1,old)))
    count=8*56*int(np.prod(final.shape[:-1]));assert int(data['coordinate_updates'])==count==s['coordinate_decisions']-before
    assert int(data['full_endpoint_energy_evaluations'])==2 and int(data['total_energy_evaluations'])==12
    s['access_calls']+=1;s['access_coordinate_updates']+=count;s['endpoint_energy_values_checked']+=endpoints.size

def network(raw,tape):
    s=stats();assert raw['records'].shape==(5,6,2,2,64,64) and raw['suppliers'].shape==(4,3,2,2,8,64)
    equal(raw['records'],raw['records'].swapaxes(-1,-2));assert not np.diagonal(raw['records'],axis1=-2,axis2=-1).any()
    values=np.concatenate((np.broadcast_to(tape['cues'],(2,8,8)),tape['targets']),axis=-1)
    replay(weights(tape['base'],np.zeros((64,64)),np.ones((64,64),dtype=bool),4.),tape['acquisition_birth'],tape['acquisition_orders'],np.r_[m.INPUT,m.OUTPUT],values,unpack(raw,'acquisition_'),s)
    initial=integer_writer(raw['acquisition_final']);equal(initial,raw['initial_record']);equal(raw['acquisition_final'][...,48:],tape['targets'])
    copy=np.broadcast_to(initial[:,None],(2,2,64,64));current=np.stack([copy.copy() for _ in range(4)]+[copy[::-1],np.zeros_like(copy)]).astype(np.longdouble)
    equal(raw['records'][0],current)
    for g in range(5):
        np.testing.assert_allclose(raw['records'][g],current,rtol=0,atol=4e-14)
        for d in range(2):
            w=weights(tape['base'],current,tape['assay_mask'][d]);counts=[]
            for p,policy in enumerate(m.POLICIES):
                data=unpack(raw,f'assay_g{g}_p{p}_d{d}_');check_access(w,tape['assay_birth'][d],tape['assay_orders'][d],tape['cues'],policy,data,s)
                equal(raw['assessments'][g,p,:,d],data['final']);equal(raw['preparations'][g,p,:,d],data['phase0_final']);counts.append(int(data['coordinate_updates']))
            assert len(set(counts))==1
            if g:
                pattern=raw['suppliers'][g-1];fields=np.einsum('...ij,...qj->...qi',w[:3],pattern);observed=raw['static_fields'][g-1,:,d]
                np.testing.assert_allclose(observed,fields,rtol=0,atol=2e-11);tol=np.longdouble('1e-12')
                margin=float(np.min(np.abs(np.abs(fields[...,8:])-tol)));assert margin>=5e-14;s['minimum_static_boundary_distance']=min(s['minimum_static_boundary_distance'],margin)
                equal(np.where(fields>tol,1,np.where(fields < -tol,-1,pattern)),np.where(observed>m.TOL,1,np.where(observed < -m.TOL,-1,pattern)))
                s['static_patterns_checked']+=int(np.prod(pattern.shape[:-1]))
        if g==4:break
        counts=[]
        for p,policy in enumerate(m.POLICIES):
            data=unpack(raw,f'supplier_g{g}_p{p}_');check_access(weights(tape['base'],current[p],tape['supplier_mask'][g]),tape['supplier_birth'][g],tape['supplier_orders'][g],tape['cues'],policy,data,s)
            equal(raw['suppliers'][g,p],data['final']);reference=writer(data['final'],'projection');error=float(np.max(np.abs(raw['records'][g+1,p]-reference)));assert error<=4e-14
            current[p]=reference;s['maximum_writer_error']=max(s['maximum_writer_error'],error);s['writer_packets_checked']+=4;s['actual_handoffs']+=4;counts.append(int(data['coordinate_updates']))
        assert len(set(counts))==1;equal(raw['records'][g+1,3:],raw['records'][g,3:]);s['protected_record_copies']+=12
    for a in range(1,4):equal(raw['assessments'][0,:,a],raw['assessments'][0,:,0])
    equal(raw['assessments'][:,:,3:],np.broadcast_to(raw['assessments'][0,:,3:],raw['assessments'][:,:,3:].shape))
    s.update(activity_only_writers=True,assessment_matched_across_horizons=True,eight_sweeps_per_policy=True,protected_copy_invariant=True)
    return s

def standard_combined(data,key):
    if key=='initial':return data['phase0_initial']
    if key=='final':return data['phase1_final']
    if key=='fields':return np.concatenate((data['phase0_fields'],data['phase1_fields']),axis=0)
    return np.concatenate((data['phase0_'+key],data['phase1_'+key][1:]),axis=0)

def h105_parity(raw,tape):
    from h105 import model as prior
    t=dict(tape);t['supplier_birth']=tape['supplier_birth'][:,0];t['assay_birth']=tape['assay_birth'][:,0]
    old=prior.run_tapes(t);equal(raw['initial_record'],old['initial_record']);equal(raw['records'][:,[0,3,4,5]],old['records'][:,[2,4,5,6]]);count=2
    for g in range(5):
        for d in range(2):
            data=unpack(raw,f'assay_g{g}_p0_d{d}_')
            for key,axis in (('initial',0),('final',0),('trace',1),('fields',2),('energies',1)):
                equal(np.take(standard_combined(data,key),[0,3,4,5],axis=axis),np.take(old[f'assay_g{g}_d{d}_'+key],[2,4,5,6],axis=axis));count+=1
        if g==4:break
        data=unpack(raw,f'supplier_g{g}_p0_')
        for key,axis in (('initial',0),('final',0),('trace',1),('fields',2),('energies',1)):
            equal(standard_combined(data,key),np.take(old[f'supplier_g{g}_'+key],2,axis=axis));count+=1
    return count
