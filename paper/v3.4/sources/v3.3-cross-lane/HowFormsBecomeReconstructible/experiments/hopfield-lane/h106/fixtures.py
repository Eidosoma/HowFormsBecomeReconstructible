"""Excluded invariants for access information, budgets, history parity and decisions."""
import io
import numpy as np
from h106 import model as m,audit,measure,report

def rejects(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('invalid condition accepted')

def run():
    names=[];tape=m.tapes('fixture',0);repeat=m.tapes('fixture',0)
    for key,value in tape.items():np.testing.assert_array_equal(value,repeat[key])
    assert not np.array_equal(tape['base'],m.tapes('fixture',1)['base']);names.append('deterministic_distinct_tapes')
    packet=dict(weights=tape['base'],births=tape['supplier_birth'][0],orders=tape['supplier_orders'][0],cues=tape['cues'])
    for policy in m.POLICIES:rejects(lambda policy=policy:m.access(dict(packet,targets=tape['targets']),policy))
    x=np.ones((8,64),dtype=np.int8);x[:,:8]=tape['cues']
    rejects(lambda:m.write({'activity':x,'incoming_record':tape['base']},'projection'))
    np.testing.assert_allclose(m.write({'activity':x},'projection'),audit.writer(x,'projection'),rtol=0,atol=4e-14)
    names.append('strict_information_and_correlated_full_rank_projection')
    zero=dict(packet,weights=np.zeros((64,64)),births=np.ones_like(packet['births']))
    duplicate=m.access(zero,'two_start');assert not duplicate['selected_attempt'].any()
    zero['births'][1]*=-1;distinct=m.access(zero,'two_start');assert not distinct['selected_attempt'].any()
    names.append('duplicate_and_equal_energy_restart_ties_choose_first')
    raw=m.run_tapes(tape);checked=audit.network(raw,tape);names.append('all_phases_selections_and_packets_independently_replayed')
    assert audit.h105_parity(raw,tape)==72;names.append('h105_standard_history_and_all_horizon_parity')
    w=m.effective(tape['base'],raw['records'][0],tape['assay_mask'][0]);drive=np.einsum('...ij,qj->...qi',w[...,8:,:8],tape['cues'])
    expected=np.where(drive>m.TOL,1,np.where(drive < -m.TOL,-1,tape['assay_birth'][0,0,...,8:]))
    np.testing.assert_array_equal(expected,raw['assay_g0_p1_d0_phase0_final'][...,8:]);names.append('preparation_uses_only_surviving_cue_drive')
    data=audit.unpack(raw,'supplier_g0_p2_');bad=dict(data,selected_attempt=1-data['selected_attempt'])
    rejects(lambda:audit.check_access(audit.weights(tape['base'],raw['records'][0,2],tape['supplier_mask'][0]),tape['supplier_birth'][0],tape['supplier_orders'][0],tape['cues'],'two_start',bad,audit.stats()))
    names.append('corrupted_restart_selection_rejected')
    names.extend(('equal_update_and_energy_evaluation_budgets','matched_assessments_and_protected_records','actual_supplier_packets_and_common_reader_crossing'))
    rows=measure.network(raw,tape,0);assert measure.independent_scores(raw,tape,rows)==1152;names.append('literal_score_recounts')
    stream=io.BytesIO();np.savez_compressed(stream,**raw);stream.seek(0)
    with np.load(stream,allow_pickle=False) as stored:
        for key,value in raw.items():np.testing.assert_array_equal(stored[key],value)
    names.append('all_raw_arrays_roundtrip')
    contrasts=[dict(endpoint=kind,g=g,comparator=p,mean=.05,lower=1e-10,positive_networks=16) for kind in ('access','supply') for g in range(1,5) for p in ('standard','two_start')]
    means=dict(access_fidelity=[.8]*4,supply_task=[.5]*4,copy_task=[.5]*4,donor_task=[.25]*4,erased_task=[.25]*4)
    assert report.decide(contrasts,means)['verdict']=='ACCESS_AND_SUPPLY_TRANSFER_QUALIFIED'
    for key,value in (('mean',.04999),('lower',0.),('positive_networks',15)):
        bad=[dict(r) for r in contrasts];bad[0][key]=value;result=report.decide(bad,means)
        assert not result['access_gain'] and result['supply_gain']
    for key in ('access_fidelity','supply_task'):
        altered={k:list(v) for k,v in means.items()};altered[key][-1]-=.001;result=report.decide(contrasts,altered)
        assert result['access_gain']==(key!='access_fidelity') and result['supply_gain']==(key!='supply_task')
    names.append('exact_boundaries_and_separate_verdicts')
    task=np.zeros((32,3,6,5,8));capture=np.zeros((32,3,3,4,4));task[:,0,1,:,0]=.8;task[:,0,3,:,0]=.8;capture[:,1,0,:,0]=.95
    draws=m.rng('fixture',0,'inference').integers(0,32,size=(20000,32));assert report.primary_result(task,capture,draws)['supply_gain']
    task[:,0,1,4,0]=.4;bad=report.primary_result(task,capture,draws);task[:,1,1,:,0]=1
    assert report.primary_result(task,capture,draws)==bad and not bad['supply_gain'] and bad['access_gain']
    names.append('coupled_policy_success_cannot_rescue_common_reader_failure')
    return dict(passed=True,tests=len(names),names=names,excluded_fixture_networks=1,h105_parity_arrays=72,numerical=checked,independent_score_rows=1152)
