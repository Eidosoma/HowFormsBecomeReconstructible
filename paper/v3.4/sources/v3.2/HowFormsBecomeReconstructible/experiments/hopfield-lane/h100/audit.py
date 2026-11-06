"""Unchanged record and trajectory audits, plus explicit decoder and transport checks."""
import numpy as np
from h083.audit import Audit
from h093.audit import metadata,record_checks,native_read
from h094 import reference
from h096.null_check import STATE_FIELDS,transport
from h100 import model as m

def network(raw,graph,committed):
    check=Audit()
    for k,v in committed.items():check.same(raw[k],v,'committed '+k)
    check.same(raw['inputs'],m.X,'public input grid');check.same(raw['training_indices'],m.TRAIN,'teaching split');check.same(raw['heldout_indices'],m.TEST,'heldout split')
    values,data=metadata(raw,graph,check);refs,projectors,max_record=record_checks(raw,graph,values,data,check)
    neural=native=0
    for node in graph['reads']:
        rec=values[node['record']];saved=data[node['id']]
        if node['kind']=='neural':reference.trajectory(raw,node,rec,saved,refs[node['record']],projectors[node['record']],check);neural+=1
        else:check.max_field_error=max(check.max_field_error,native_read(raw,node,rec,saved,check));native+=1
    for node in graph['lineages']:
        if node['route']=='parity_erm':check.same(data[node['read']]['final'],raw['responses_'+node['origin']],'independent parity ceiling')
    return dict(passed=True,numerical_checks=check.count,records=len(graph['records']),writer_packets=len(raw['packet_outputs']),
        unique_neural_reads=neural,unique_native_reads=native,pair_energy_comparisons=check.pair_comparisons,single_energy_comparisons=check.single_comparisons,
        max_projection_record_error=max_record,max_field_error=check.max_field_error,max_pair_energy_error=check.max_pair_error,
        minimum_decision_boundary_distance=check.boundary_minimum,actual_parent_packets_verified=True)

def decoded_bank(bank,polarity):
    assert bank['signs'].shape==bank['known'].shape==(3,3,4,48)
    assert not bank['erased_signs'].any() and not bank['erased_known'].any();checks=2
    for g in range(3):
        for b in range(4):
            commands=bank['reference_commands'][g,b];measured=bank['measured_responses'][g,b]
            np.testing.assert_array_equal(commands,np.stack((np.ones(48,dtype=np.int8),-np.ones(48,dtype=np.int8))))
            np.testing.assert_array_equal(measured,commands*polarity);assert bank['observed'][g,b].all()
            inferred=commands*measured;np.testing.assert_array_equal(inferred[0],inferred[1]);checks+=4
            for mi,mode in enumerate(m.MODES):
                expected=np.zeros(48,dtype=np.int8) if g and mode=='erased_no_reference' else inferred[0]
                np.testing.assert_array_equal(bank['signs'][mi,g,b],expected)
                np.testing.assert_array_equal(bank['known'][mi,g,b],expected!=0);checks+=2
    return dict(passed=True,checks=checks,recipient_tapes=12,repaired_descendants=8,erased_unresolved_descendants=8,
        calibration_recovery_passed=True,no_reference_unresolved=True,reference_values_per_repair=96,learned_sign_bits=48)

def transport_graph(canonical,cg,physical,pg,polarity):
    d=np.r_[np.ones(80,dtype=np.int8),polarity];checks=0;max_record=max_float=0.
    for key in ('packet_outputs','completion_outputs','completion_signs'):
        np.testing.assert_array_equal(physical[key],canonical[key]*polarity);checks+=1
    np.testing.assert_array_equal(physical['completion_masks'],canonical['completion_masks']);checks+=1
    assert len(cg['records'])==len(pg['records'])==303
    for a,b in zip(cg['records'],pg['records']):
        assert {k:v for k,v in a.items() if k!='parent_read'}=={k:v for k,v in b.items() if k!='parent_read'}
        av,bv=m.get_record(canonical,cg,a['id']),m.get_record(physical,pg,b['id']);kind=a['kind']
        if kind=='neural':expected=transport(av,d)
        else:
            expected={k:v.copy() for k,v in av.items()}
            response_key='coeff' if kind in ('linear_ls','quadratic_ls') else 'outputs' if kind=='nearest_history' else 'signs'
            expected[response_key]*=polarity
        for key,wanted in expected.items():
            err=float(np.max(np.abs(bv[key].astype(float)-wanted.astype(float))));max_record=max(max_record,err)
            if wanted.dtype.kind in 'biu':np.testing.assert_array_equal(bv[key],wanted)
            else:np.testing.assert_allclose(bv[key],wanted,rtol=0,atol=4e-14 if kind=='neural' else 2e-12)
            checks+=1
    pairs=set()
    for group in ('lineages','locals','cases'):
        assert len(cg[group])==len(pg[group])
        for a,b in zip(cg[group],pg[group]):
            assert {k:v for k,v in a.items() if k!='read'}=={k:v for k,v in b.items() if k!='read'}
            pairs.add((a['read'],b['read']))
    covered=[set(),set()];discrete=0
    for i,j in sorted(pairs):
        a,b=cg['reads'][i],pg['reads'][j];assert all(a[k]==b[k] for k in ('kind','generation','birth'))
        av,bv=m.get_read(canonical,cg,i),m.get_read(physical,pg,j);assert av.keys()==bv.keys()
        covered[0].add(i);covered[1].add(j)
        for key,value in av.items():
            if a['kind']=='neural':wanted=value*d if (key.split('_',1)[-1] in STATE_FIELDS or key in ('kick_fields','kick_after')) else value
            else:wanted=value*polarity if key in ('final','fields') else value
            if value.dtype.kind in 'biu':np.testing.assert_array_equal(bv[key],wanted,err_msg=key);discrete+=1
            else:
                np.testing.assert_allclose(bv[key],wanted,rtol=0,atol=2e-11,err_msg=key)
                max_float=max(max_float,float(np.max(np.abs(bv[key]-wanted))))
            checks+=1
    assert covered[0]==set(range(len(cg['reads']))) and covered[1]==set(range(len(pg['reads'])))
    return dict(passed=True,checks=checks,discrete_reader_arrays=discrete,unique_read_pairs=len(pairs),
        maximum_record_error=max_record,maximum_reader_float_error=max_float,all_packets_transported=True,all_discrete_traces_transported=True)
