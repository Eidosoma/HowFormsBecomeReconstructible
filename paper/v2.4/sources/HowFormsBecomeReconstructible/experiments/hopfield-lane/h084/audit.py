"""Independent fresh-source audit followed by the unchanged H083 pair audit."""
import numpy as np
from h077.audit import exact_projector
from h081.audit import Check,segment as gated_segment
from h081.legacy_audit import Audit as SourceAudit
from h083 import audit as pair_audit
from h084 import model as m


def source(raw,cohort,block):
    check=SourceAudit('delayed');gate=Check();old=m.old
    for key,value in m.tapes(cohort,block).items():check.same(raw[key],value,'committed tape '+key)
    check.same(raw['training_inputs'],old.X,'fixed input alphabet')
    check.same(raw['history_own'],old.X,'complete actual observed input history')
    y=raw['responses'];assert y.shape==(8,48) and np.isin(y,[-1,1]).all() and (y.sum(-1)==0).all()
    patterns=np.concatenate((old.X,y),axis=1).astype(np.int64)
    projector,rank=exact_projector(patterns);reference=projector.copy();np.fill_diagonal(reference,0)
    record=raw['source_J_projection'][0];check.reference=reference
    check.same(raw['source_projector'][0],projector,'exact Gram projector',4e-14)
    check.same(record,reference,'exact learned record',4e-14)
    assert rank==int(raw['source_projector_rank'][0])
    check.same(patterns@projector,patterns.astype(np.longdouble),'training span',2e-13)
    check.same(projector@projector,projector,'idempotence',2e-13)
    check.same(patterns*(patterns@reference.T),np.broadcast_to(1-np.diag(projector),patterns.shape),'target margins',2e-11)
    mean=np.asarray([sum(old.X[:,i])/8 for i in range(80)])
    check.same(raw['source_mean'][0],mean,'input-only mean')
    basis=raw['source_basis'][0]
    check.same(basis.T@basis,np.eye(4),'orthonormal input basis',2e-12)
    check.same((old.X-mean)@basis@basis.T,old.X-mean,'complete input span',2e-12)
    z=(old.X-mean)@basis
    for name,degree in (('linear',1),('quadratic',2)):
        cols=[np.ones(8)]+[z[:,i] for i in range(4)]
        if degree==2:cols += [z[:,i]*z[:,j] for i in range(4) for j in range(i,4)]
        fitted=np.linalg.pinv(np.column_stack(cols),rcond=1e-12)@y
        check.same(raw['source_'+name][0],fitted,'independent minimum norm '+name,2e-12)
    check.same(raw['source_prototype_inputs'][0],old.X,'prototype inputs')
    check.same(raw['source_prototype_outputs'][0],y,'prototype outputs')
    initial=np.broadcast_to(raw['birth'][None],(8,4,128))
    for gap in m.GAPS:
        p=f'd{gap}_own_'
        check.segment(raw,p+'context_',dict(record=record,state=initial,orders=raw['orders_context'],
            clamp_indices=old.CONTEXT,clamp_values=old.X[:,None,:32],active_sweeps=4))
        check.segment(raw,p+'gap_',dict(record=record,state=raw[p+'context_final'],orders=raw['orders_gap'][:gap],
            clamp_indices=np.asarray([],dtype=int),clamp_values=np.empty((8,1,0),dtype=np.int8),active_sweeps=gap))
        for horizon in (0,1,8):
            check.segment(raw,f'delayed_d{gap}_own_read{horizon}_',dict(record=record,state=raw[p+'gap_final'],
                orders=raw['orders_query'],clamp_indices=old.QUERY,clamp_values=old.X[:,None,32:],
                active_sweeps=horizon,feedback=old.FEEDBACK['delayed']))
        prefix=m.source_prefix('cue_hysteresis',gap)
        data={key[len(prefix):]:value for key,value in raw.items() if key.startswith(prefix)}
        gated_segment(record,reference,raw[p+'gap_final'],raw['orders_query'],old.X[:,None,32:],'cue_hysteresis',data,gate)
        check.same(data['trace'][1],raw[f'delayed_d{gap}_own_read1_final'],'shared first cue sweep')
        assert not data['veto'][0].any()
    for method in m.BASELINES:check.conventional(raw,'own',method)
    return dict(source_numerical_checks=check.checks+gate.count,
        max_source_record_error=float(np.max(np.abs(record-reference))),
        max_source_field_error=max(check.max_field_error,gate.max_field_error),
        source_boundary_distance=min(check.boundary_minimum,gate.boundary_minimum),
        fresh_acquisition_audited=True,preparation_paths_audited=True,conventional_controls_audited=True)


def network(raw,data,cohort,block):
    a=source(raw,cohort,block);b=pair_audit.network(m.reader_source(raw),data)
    result=dict(b,**a);result['numerical_checks']+=a['source_numerical_checks']
    result['max_projection_record_error']=max(a['max_source_record_error'],b['max_projection_record_error'])
    result['max_field_error']=max(a['max_source_field_error'],b['max_field_error'])
    result['minimum_decision_boundary_distance']=min(a['source_boundary_distance'],b['minimum_decision_boundary_distance'])
    result['new_records']=1;result['inherited_transitions']=0
    return result
