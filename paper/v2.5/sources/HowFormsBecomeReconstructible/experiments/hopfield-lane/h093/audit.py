"""Audit actual ancestry, all inherited coefficients and polynomial trajectories."""
import numpy as np
from h091 import audit as old
from h092 import audit as completion_audit
from h093 import model as m,reference

infer=completion_audit.infer
native_read=completion_audit.native_read

def metadata(raw,graph,check):
    assert set(graph)=={'records','reads','lineages','locals','cases'}
    records=graph['records'];reads=graph['reads'];assert len(records)==303
    assert [r['id'] for r in records]==list(range(len(records)))
    assert [r['id'] for r in reads]==list(range(len(reads)))
    for kind in m.KINDS:
        for nodes in (records,reads):assert [r['index'] for r in nodes if r['kind']==kind]==list(range(sum(r['kind']==kind for r in nodes)))
    values={r['id']:m.get_record(raw,graph,r['id']) for r in records}
    data={r['id']:m.get_read(raw,graph,r['id']) for r in reads}
    def alias(record,read,g,b):
        rr=reads[read];assert rr['kind']==records[record]['kind'] and rr['generation']==g and rr['birth']==b
        for key,value in values[record].items():check.same(value,values[rr['record']][key],'content-addressed read alias')
    key=lambda r:(r['origin'],r['route'],r['policy'],r['generation'],r['birth'])
    lineages={key(r):r for r in graph['lineages']};local={key(r):r for r in graph['locals']}
    expected={(o,route,p,g,b) for o in m.ORIGINS for route in m.ROUTES
        for p in (m.READERS if route in ('rewrite','copy') else ('direct',)) for g in range(3) for b in range(4)}
    assert len(lineages)==len(graph['lineages'])==192 and set(lineages)==expected
    expected={(o,route,p,g,b) for o in m.ORIGINS for route in ('copy',*m.BASELINES)
        for p in m.READERS for g in (1,2) for b in range(4)}
    assert len(local)==len(graph['locals'])==160 and set(local)==expected
    for scope,entries in (('lineage',lineages),('local',local)):
        for (origin,route,policy,g,b),item in entries.items():
            node=records[item['record']];kind='neural' if route in ('rewrite','copy') else route
            assert node['origin']==origin and node['kind']==kind
            alias(item['record'],item['read'],g,b)
            if g==0:
                assert scope=='lineage' and node['operation']=='founder' and node['generation']==0
            else:
                assert node['scope']==scope and node['route']==route and node['policy']==policy
                assert node['generation']==g and node['birth']==b
                parent=lineages[origin,'rewrite' if scope=='local' else route,policy,g-1,b]
                assert node['parent_record']==parent['record'] and node['parent_read']==parent['read']
                assert node['parent_reader']==policy and node['operation']==('copy' if route=='copy' else 'write')
    erased={r['kind']:r['id'] for r in records if r['operation']=='erase'};assert set(erased)==set(m.KINDS)
    expected_cases={}
    for scope,entries in (('lineage',lineages),('local',local)):
        for (origin,route,p,g,b),item in entries.items():
            if origin!='own':continue
            kind=records[item['record']]['kind']
            for source in ('own','donor','erased'):
                record=erased[kind] if source=='erased' else entries[source,route,p,g,b]['record']
                for reader in m.READERS if kind=='neural' else ('direct',):
                    expected_cases[scope,route,p,g,b,source,reader]=record
    seen=set()
    for case in graph['cases']:
        key=tuple(case[k] for k in ('scope','route','policy','generation','birth','source','reader'))
        assert key not in seen and expected_cases[key]==case['record'];seen.add(key)
        alias(case['record'],case['read'],case['generation'],case['birth'])
    assert seen==set(expected_cases) and len(seen)==720
    # Copying changes neither its coefficients nor its future record when expression policy changes.
    for origin in m.ORIGINS:
        for g in range(3):
            for b in range(4):
                a=lineages[origin,'copy','ordinary',g,b];z=lineages[origin,'copy','pair',g,b]
                for key in m.SCHEMAS['neural']:check.same(values[a['record']][key],values[z['record']][key],'complete copy policy invariance')
    return values,data


def record_checks(raw,graph,values,data,check):
    matrices,projectors,max_error=completion_audit.record_checks(raw,graph,values,data,check)
    references={};fits={}
    for node in graph['records']:
        if node['kind']!='neural':continue
        i=node['id'];record=values[i];operation=node['operation']
        assert record['interaction_masks'].shape==record['interaction_weights'].shape==(48,)
        assert record['interaction_masks'].dtype==np.dtype('int8') and record['interaction_weights'].dtype==np.dtype('float64')
        if operation=='erase':masks=np.zeros(48,dtype=np.int8);weights=np.zeros(48)
        elif operation=='copy':
            parent=references[node['parent_record']];masks=parent['interaction_masks'];weights=parent['interaction_weights']
            for key in m.SCHEMAS['neural']:check.same(record[key],values[node['parent_record']][key],'whole actual-parent copy')
        else:
            packet=raw['packet_outputs'][node['packet_index']];key=packet.tobytes()
            if key not in fits:fits[key]=infer(packet)
            masks,signs,_=fits[key]
            weights=np.asarray([float(sign) if any(int(mask)&(1<<b) for b in (0,1)) and any(int(mask)&(1<<b) for b in (2,3)) else 0. for mask,sign in zip(masks,signs)])
        check.same(record['interaction_masks'],masks,'independently fitted inherited masks')
        check.same(record['interaction_weights'],weights,'fixed unit strength only for context-query rules')
        references[i]=dict(J=matrices[i],interaction_masks=masks.copy(),interaction_weights=weights.astype(np.longdouble))
    return references,projectors,max_error


def network(raw,graph,cohort,block):
    check=old.pair_audit.Audit()
    for key,value in m.tapes(cohort,block).items():check.same(raw[key],value,'committed '+key)
    check.same(raw['inputs'],m.X,'unchanged feature inputs');check.same(raw['training_indices'],m.TRAIN,'training split');check.same(raw['heldout_indices'],m.TEST,'held-out split')
    assert len(np.unique(m.old.dictionary(m.X[m.TRAIN]).T,axis=0))==32
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
