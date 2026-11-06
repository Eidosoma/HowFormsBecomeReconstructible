"""Excluded fixtures for chain semantics, prior parity and separate decisions."""
import io
import numpy as np
from h105 import model as m,audit,measure,report

def rejects(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('invalid input accepted')

def run():
    names=[];tape=m.tapes('fixture',0);repeated=m.tapes('fixture',0)
    for k,v in tape.items():np.testing.assert_array_equal(v,repeated[k])
    assert not np.array_equal(tape['base'],m.tapes('fixture',1)['base']);names.append('deterministic_distinct_tapes')
    x=np.ones((8,64),dtype=np.int8);x[:,:8]=tape['cues']
    for rule in m.WRITERS:
        rejects(lambda rule=rule:m.write({'activity':x,'incoming_record':np.zeros((64,64))},rule))
        np.testing.assert_allclose(m.write({'activity':x},rule),audit.writer(x,rule),rtol=0,atol=4e-14)
    rejects(lambda:m.write({'activity':x.astype(float)},'projection'));names.append('activity_only_writers_and_correlated_full_rank_projection')
    rejects(lambda:m.read(dict(weights=tape['base'],birth=tape['supplier_birth'][0],orders=tape['supplier_orders'][0],clamp_indices=m.INPUT,clamp_values=tape['cues'],targets=tape['targets'])))
    names.append('strict_post_acquisition_reader')
    raw=m.run_tapes(tape);checked=audit.network(raw,tape);names.append('all_decisions_and_successive_packets_independently_verified')
    parity=audit.first_boundary_parity(raw,tape);assert parity==17;names.append('h104_first_boundary_parity')
    names.extend(('identical_initial_supplier_inputs','matched_assessments_and_protected_copy_invariance','captured_references_follow_own_supplier'))
    rows=measure.network(raw,tape,0);assert measure.independent_scores(raw,tape,rows)==600;names.append('independent_score_and_mechanism_recounts')
    stream=io.BytesIO();np.savez_compressed(stream,**raw);stream.seek(0)
    with np.load(stream,allow_pickle=False) as saved:
        for key,value in raw.items():np.testing.assert_array_equal(saved[key],value)
    names.append('complete_raw_array_serialization')
    contrasts=[dict(g=g,comparator=name,mean=.05,lower=1e-10,positive_networks=16) for g in range(1,5) for name in ('hebbian','centered','norm_hebbian')]
    fidelity=[dict(g=g,mean=.6,lower=.500000001) for g in range(1,5)]
    means=dict(projection=[.5]*4,copy=[.5]*4,donor=[.25]*4,erased=[.25]*4)
    assert report.decide(contrasts,fidelity,means)['verdict']=='FOUR_HANDOFF_TASK_AND_CAPTURE_QUALIFIED'
    for key,value in (('mean',.04999),('lower',0.),('positive_networks',15)):
        altered=[dict(r) for r in contrasts];altered[-1][key]=value;result=report.decide(altered,fidelity,means)
        assert not result['task_advantage'] and result['local_capture_fidelity']
    altered=[dict(r) for r in fidelity];altered[-1]['lower']=.5;result=report.decide(contrasts,altered,means)
    assert result['task_advantage'] and not result['local_capture_fidelity'];names.append('strict_boundaries_and_separate_verdicts')
    damaged={k:list(v) for k,v in means.items()};damaged['projection'][-1]=.499
    assert not report.decide(contrasts,fidelity,damaged)['task_advantage'];names.append('late_task_loss_cannot_be_hidden_by_early_or_capture_success')
    task=np.zeros((32,7,5,7));capture=np.zeros((32,4,4,4));task[:,2,:,0]=.8;task[:,4,:,0]=.8;capture[:,2,:,0]=.8
    draws=m.rng('fixture',0,'inference').integers(0,32,size=(20000,32));assert report.primary_result(task,capture,draws)['task_advantage']
    task[:,2,4,0]=.4;result=report.primary_result(task,capture,draws)
    assert not result['task_advantage'] and result['local_capture_fidelity'];names.append('full_primary_arrays_keep_four_horizons_and_local_fidelity_distinct')
    return dict(passed=True,tests=len(names),names=names,excluded_fixture_networks=1,h104_first_boundary_parity_arrays=parity,numerical=checked,independent_score_rows=600)
