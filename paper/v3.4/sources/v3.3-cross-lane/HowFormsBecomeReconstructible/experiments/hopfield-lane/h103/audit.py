"""Independent long-double update replay and integer coactivity verification."""
import numpy as np
from h103 import model as m

def equal(a,b):np.testing.assert_array_equal(a,b)
def writer(x,centered=False):
    y=x.astype(np.int64);result=np.zeros(y.shape[:-2]+(64,64))
    totals=y.sum(-2)
    for i in range(64):
        for j in range(i):
            numerator=np.sum(y[...,i]*y[...,j],axis=-1,dtype=np.int64)
            if centered:numerator=8*numerator-totals[...,i]*totals[...,j]
            result[...,i,j]=result[...,j,i]=numerator/(512 if centered else 64)
    return result
def weights(base,record,mask,gain=2.):
    value=(np.asarray(base,dtype=np.longdouble)+np.asarray(record,dtype=np.longdouble)*mask)
    value[...,:8,8:]*=gain;value[...,8:,:8]*=gain
    return value
def replay(w,birth,orders,indices,values,saved,stats):
    assert np.array_equal(w,w.swapaxes(-1,-2)) and not np.diagonal(w,axis1=-2,axis2=-1).any()
    shape=np.broadcast_shapes(w.shape[:-2],birth.shape[:-2])+(8,64)
    x=np.broadcast_to(birth,shape).copy();x[...,indices]=values;equal(saved['initial'],x)
    fixed=set(map(int,indices));tol=np.longdouble('1e-12')
    def energy():return -np.sum(x*np.einsum('...ij,...qj->...qi',w,x),axis=-1,dtype=np.longdouble)/2
    prior=energy();np.testing.assert_allclose(saved['energies'][0],prior,rtol=0,atol=2e-11)
    for s,order in enumerate(orders):
        for i in order:
            if i in fixed:assert not saved['fields'][s,i].any();continue
            field=np.sum(x*w[...,None,i,:],axis=-1,dtype=np.longdouble)
            delta=float(np.max(np.abs(field-saved['fields'][s,i])));assert delta<=2e-11
            margin=float(np.min(np.abs(np.abs(field)-tol)));assert margin>=5e-14,'ambiguous update at guarded threshold'
            old=x[...,i].copy();new=np.where(field>tol,1,np.where(field < -tol,-1,old)).astype(np.int8)
            observed=np.where(saved['fields'][s,i]>m.TOL,1,np.where(saved['fields'][s,i]<-m.TOL,-1,old)).astype(np.int8)
            equal(new,observed);change=-(new-old)*field;assert np.max(change)<=2e-11
            x[...,i]=new;stats['coordinate_decisions']+=field.size;stats['field_arrays_checked']+=1
            stats['maximum_field_error']=max(stats['maximum_field_error'],delta)
            stats['minimum_boundary_distance']=min(stats['minimum_boundary_distance'],margin)
        equal(x,saved['trace'][s+1]);current=energy();assert np.max(current-prior)<=2e-11
        np.testing.assert_allclose(saved['energies'][s+1],current,rtol=0,atol=2e-11)
        stats['maximum_energy_error']=max(stats['maximum_energy_error'],float(np.max(np.abs(saved['energies'][s+1]-current))))
        prior=current;stats['sweep_states_checked']+=1
    equal(x,saved['final']);equal(saved['trace'][0],saved['initial']);stats['reads_replayed']+=1
def unpack(raw,prefix):return {k[len(prefix):]:v for k,v in raw.items() if k.startswith(prefix)}
def current_parity(raw,tape,variants):
    from h102 import model as calibration
    assert calibration.REGIMES[3]==(2.,.2)
    initial=raw['initial_record'];source=np.stack((initial,initial[::-1],np.zeros_like(initial)))
    reference=calibration.assess(dict(base=tape['base'],records=source,cues=tape['cues'],
        birth=tape['assay_birth'],orders=tape['assay_orders'],uniform=tape['assay_uniform']),(3,))
    equal(reference['injury_masks'][0],tape['assay_mask'])
    indices=[variants.index(name) for name in ('unchanged','donor','erased')];count=0
    for draw in range(2):
        left=unpack(raw,f'assay_g0_d{draw}_');right=unpack(reference,f'assay_d{draw}_')
        for key,axis in (('initial',0),('final',0),('trace',1),('fields',2),('energies',1)):
            observed=np.take(np.take(left[key],indices,axis=axis),0,axis=axis+1)
            equal(observed,np.take(right[key],0,axis=axis));count+=1
    for route in (1,2):equal(raw['assessments'][0,:,0],raw['assessments'][0,:,route])
    return count
def network(raw,tape,variants):
    stats=dict(passed=True,coordinate_decisions=0,field_arrays_checked=0,sweep_states_checked=0,reads_replayed=0,
        maximum_field_error=0.,maximum_energy_error=0.,minimum_boundary_distance=float('inf'),writer_packets_checked=0)
    assert len(variants)==len(set(variants)) and set(variants)<=set(m.VARIANTS)
    assert (m.ACQUISITION_GAIN,m.ASSESSMENT_GAIN,m.SUPPLYING_GAIN)==(4.,2.,2.)
    for name,value in (('acquisition',4.),('assessment',2.),('supplying',2.)):
        assert float(raw['setting_'+name+'_gain'])==value
    shape=(5,len(variants),3,2,2,64,64);assert raw['records'].shape==shape
    equal(raw['records'],raw['records'].swapaxes(-1,-2));assert not np.diagonal(raw['records'],axis1=-2,axis2=-1).any()
    empty=np.zeros((64,64));available=np.ones((64,64),dtype=bool)
    values=np.concatenate((np.broadcast_to(tape['cues'],(2,8,8)),tape['targets']),axis=-1)
    replay(weights(tape['base'],empty,available,4.),tape['acquisition_birth'],tape['acquisition_orders'],np.r_[m.INPUT,m.OUTPUT],values,unpack(raw,'acquisition_'),stats)
    equal(raw['initial_record'],writer(raw['acquisition_final']));equal(raw['acquisition_final'][...,m.OUTPUT],tape['targets'])
    initial=raw['initial_record'];upper=np.triu_indices(64,1)
    for candidate in m.CANDIDATES:
        chosen=raw['selection_'+candidate];random=raw['selection_random_'+candidate]
        equal(chosen,chosen.swapaxes(-1,-2));equal(random,random.swapaxes(-1,-2));assert not (chosen&(initial==0)).any()
        for f in range(2):
            eligible=[i for i,(a,b) in enumerate(zip(*upper)) if initial[f,a,b]!=0]
            if candidate=='output_all':selected=[i for i in eligible if upper[0][i]>=48 and upper[1][i]>=48]
            else:selected=sorted(eligible,key=lambda i:(abs(initial[f,upper[0][i],upper[1][i]]),tape['priority'][f,i]))[:int(len(eligible)*(.25 if candidate=='weak25' else .5))]
            expected=np.zeros((64,64),dtype=bool)
            for i in selected:a,b=upper[0][i],upper[1][i];expected[a,b]=expected[b,a]=True
            equal(chosen[f],expected)
            rs=sorted(eligible,key=lambda i:tape['random_priority'][f,i])[:len(selected)];expected[:]=False
            for i in rs:a,b=upper[0][i],upper[1][i];expected[a,b]=expected[b,a]=True
            equal(random[f],expected)
        candidate_record=np.where(chosen,0.,initial)
        for name,expected in ((candidate,candidate_record),('random_'+candidate,np.where(random,0.,initial)),
            ('strength_'+candidate,initial*raw['scale_'+candidate][:,None,None])):
            if name in variants:equal(raw['starting_records'][variants.index(name)],expected)
        attenuated=initial*raw['scale_'+candidate][:,None,None]
        np.testing.assert_allclose(np.linalg.norm(attenuated,axis=(-2,-1)),np.linalg.norm(candidate_record,axis=(-2,-1)),rtol=0,atol=2e-13)
    for name,expected in (('unchanged',initial),('erased',np.zeros_like(initial)),('donor',initial[::-1])):
        if name in variants:equal(raw['starting_records'][variants.index(name)],expected)
    equal(raw['records'][0],np.broadcast_to(raw['starting_records'][:,None,:,None],shape[1:]))
    for g in range(5):
        for draw in range(2):
            data=unpack(raw,f'assay_g{g}_d{draw}_')
            replay(weights(tape['base'],raw['records'][g],tape['assay_mask'][draw]),tape['assay_birth'][draw],tape['assay_orders'][draw],m.INPUT,tape['cues'],data,stats)
            equal(raw['assessments'][g,:,:,draw],data['final'])
        if g==4:continue
        body=unpack(raw,f'writer_g{g}_')
        replay(weights(tape['base'],raw['records'][g],tape['writer_mask'][g]),tape['writer_birth'][g],tape['writer_orders'][g],m.INPUT,tape['cues'],body,stats)
        equal(raw['supplying_bodies'][g],body['final'])
        for route in (0,1):
            equal(raw['records'][g+1,:,route],writer(body['final'][:,route],route==1));stats['writer_packets_checked']+=len(variants)*4
        equal(raw['records'][g+1,:,2],raw['records'][g,:,2])
    equal(raw['assessments'][:,:,2],np.broadcast_to(raw['assessments'][0,:,2],raw['assessments'][:,:,2].shape))
    stats.update(actual_handoffs=4*len(variants)*3*4,source_label_only_at_acquisition=True,assessment_tapes_identical_across_horizons=True,
        writer_has_no_exact_zero_fallback=True,protected_copy_assessments_exactly_invariant=True,
        h102_current_parity_arrays=current_parity(raw,tape,variants),acquisition_gain=4.,assessment_gain=2.,supplying_gain=2.)
    return stats
