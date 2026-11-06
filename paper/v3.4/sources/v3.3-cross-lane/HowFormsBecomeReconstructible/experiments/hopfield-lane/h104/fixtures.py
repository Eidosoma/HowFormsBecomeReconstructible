"""Excluded engineering checks for information boundaries and frozen decisions."""
import io
import numpy as np
from h104 import model as m,audit,measure,report

def rejects(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('invalid input was accepted')

def run():
    names=[];tape=m.tapes('fixture',0)
    for k,v in tape.items():np.testing.assert_array_equal(v,m.tapes('fixture',0)[k])
    assert not np.array_equal(tape['base'],m.tapes('fixture',1)['base']);names.append('deterministic_disjoint_tapes')
    x=np.ones((8,64),dtype=np.int8);x[:,:8]=tape['cues']
    for rule in m.WRITERS:
        rejects(lambda rule=rule:m.write({'activity':x,'targets':tape['targets']},rule))
        np.testing.assert_allclose(m.write({'activity':x},rule),audit.writer(x,rule),rtol=0,atol=4e-14)
    rejects(lambda:m.write({'activity':x.astype(float)},'projection'));names.append('strict_writer_information_and_types')
    rejects(lambda:m.read(dict(weights=tape['base'],birth=tape['supplier_birth'],orders=tape['supplier_orders'],
        clamp_indices=m.INPUT,clamp_values=tape['cues'],targets=tape['targets'])))
    names.append('strict_post_acquisition_reader_information')
    p=m.write({'activity':x},'projection');bad=p.copy();bad[0,1]+=1e-5;bad[1,0]+=1e-5
    rejects(lambda:np.testing.assert_allclose(bad,audit.writer(x,'projection'),rtol=0,atol=4e-14));names.append('correlated_full_rank_projection_and_corruption_detection')
    raw=m.run_tapes(tape);checked=audit.network(raw,tape);names.append('all_reads_independently_replayed')
    parity=audit.first_boundary_parity(raw,tape);assert parity==15;names.append('h103_first_boundary_parity')
    names.extend(('source_controls_and_matched_assessments','stable_patterns_survive_captured_starts','exact_copy_ancestral_hebbian_identity'))
    rows=measure.network(raw,tape,0);assert measure.independent_scores(raw,tape,rows)==532;names.append('literal_score_recounts')
    stream=io.BytesIO();np.savez_compressed(stream,**raw);stream.seek(0)
    with np.load(stream,allow_pickle=False) as saved:
        for key,value in raw.items():np.testing.assert_array_equal(saved[key],value)
    names.append('all_raw_arrays_roundtrip')
    comparisons=[dict(metric=metric,comparator=control,mean=.05,lower=1e-10,upper=.1,positive_networks=16) for metric in ('task_query','captured_output_exact') for control in ('hebbian','centered','norm_hebbian')]
    means=dict(projection_task=.5,copy_task=.5,donor_task=.25,erased_task=.25,projection_capture=.5)
    assert report.decide(comparisons,means)['verdict']=='FRESH_WRITER_FIDELITY_AND_TASK_GAIN'
    for key in ('projection_task','copy_task','projection_capture'):
        lowered=dict(means);lowered[key]=.499;decision=report.decide(comparisons,lowered)
        assert decision['verdict']=='NO_JOINT_FRESH_WRITER_GAIN'
        assert decision['task_gain']==(key=='projection_capture')
        assert decision['captured_output_gain']==(key!='projection_capture')
    for key,value in (('mean',.04999),('lower',0.),('positive_networks',15)):
        altered=[dict(r) for r in comparisons];altered[0][key]=value;assert not report.decide(altered,means)['task_gain']
    names.append('separate_verdicts_and_exact_gate_boundaries')
    values=np.zeros((32,11,2,2,8));values[:,2,1,0,0]=.9;values[:,2,1,0,4]=.9;values[:,8,1,0,0]=.8
    draws=m.rng('fixture',0,'inference').integers(0,32,size=(20000,32));good=report.primary_result(values,draws)
    assert good['task_gain'] and good['captured_output_gain']
    values[:,2,1,0,:]=0;bad=report.primary_result(values,draws)
    values[:,4:8]=1;values[:,:,0]=1;values[:,:,:,1]=1
    assert report.primary_result(values,draws)==bad;names.append('extra_information_cannot_promote_failed_primary')
    return dict(passed=True,tests=len(names),names=names,excluded_fixture_networks=1,
        h103_first_boundary_parity_arrays=parity,numerical=checked,independent_score_rows=532)
