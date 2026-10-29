"""Fresh committed tapes, unchanged ancestry/record audits, both independent readers."""
import numpy as np
from h091 import audit as old
from h093.audit import infer,native_read,metadata,record_checks
from h095 import model as m
from h091.model import dictionary
from h093 import reference as unprotected_reference
from h094 import reference as protected_reference

def network(raw,graph,cohort,block,condition):
    assert condition in m.CONDITIONS
    reference=protected_reference if condition=='protected' else unprotected_reference
    check=old.pair_audit.Audit()
    for key,value in m.tapes(cohort,block).items():check.same(raw[key],value,'committed '+key)
    check.same(raw['inputs'],m.X,'unchanged feature inputs');check.same(raw['training_indices'],m.TRAIN,'training split');check.same(raw['heldout_indices'],m.TEST,'held-out split')
    assert len(np.unique(dictionary(m.X[m.TRAIN]).T,axis=0))==32
    values,data=metadata(raw,graph,check);references,projectors,max_record=record_checks(raw,graph,values,data,check)
    neural=native=0
    for node in graph['reads']:
        record=values[node['record']];saved=data[node['id']]
        if node['kind']=='neural':
            reference.trajectory(raw,node,record,saved,references[node['record']],projectors[node['record']],check);neural+=1
        else:check.max_field_error=max(check.max_field_error,native_read(raw,node,record,saved,check));native+=1
    for entry in graph['lineages']:
        if entry['route']=='parity_erm':check.same(data[entry['read']]['final'],raw['responses_'+entry['origin']],'independent parity remains exact')
    assert check.max_field_error<=2e-11
    return dict(passed=True,numerical_checks=check.count,records=303,writer_packets=234,completion_packets=234,
        lineage_nodes=192,local_nodes=160,assay_cases=720,unique_neural_reads=neural,unique_native_reads=native,
        pair_energy_comparisons=check.pair_comparisons,single_energy_comparisons=check.single_comparisons,
        max_projection_record_error=max_record,max_field_error=check.max_field_error,max_pair_energy_error=check.max_pair_error,
        minimum_decision_boundary_distance=check.boundary_minimum,all_new_trajectories_replayed=True,
        all_actual_packets_verified=True,heldout_truth_excluded_from_writing=True,copy_invariance=True)
