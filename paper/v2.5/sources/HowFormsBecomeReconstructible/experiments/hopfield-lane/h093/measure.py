"""Literal scores, complete inherited payloads, work and matched comparisons."""
from collections import defaultdict
import numpy as np
from h091 import measure as old
from h092 import measure as completed
from h093 import model as m,geometry

CASE_KEYS=old.CASE_KEYS
KINDS=(*completed.KINDS,'repair')
KEYS=dict(completed.KEYS,repair=('origin','reader','panel'))
DETAILS=old.ALL_DETAILS
PRIMARY_COMPARATORS=old.PRIMARY_COMPARATORS
CONTRASTS=old.CONTRASTS
PAYLOAD=dict(old.PAYLOAD,neural=8224,nearest_history=2048)
case_score,flags,paired=old.case_score,old.flags,old.paired
completion_rows=completed.completion_rows

def interaction_network(raw,graph,block,literal=False):
    table={k:[] for k in old.KINDS};outputs=defaultdict(dict);target=raw['responses_own'];donor=raw['responses_donor']
    read_data={r['id']:m.get_read(raw,graph,r['id']) for r in graph['reads']}
    for case in graph['cases']:
        kind=graph['reads'][case['read']]['kind'];data=read_data[case['read']];output=m.response(data,kind,case['reader']);scores={}
        for panel,indices in m.PANELS.items():
            own=case_score(output[indices],target[indices],literal);other=case_score(output[indices],donor[indices],literal);scores[panel]=own
            key=(panel,)+tuple(case[k] for k in CASE_KEYS);assert case['birth'] not in outputs[key]
            outputs[key][case['birth']]=output[indices]
            row=dict(block=block,**case,panel=panel,**own,**{'donor_'+k:v for k,v in other.items() if k.endswith('_correct')})
            if kind=='neural':
                row.update(neural_assays=1,query_eight_correct=case_score(data['query_final'][indices,0,80:],target[indices],literal)['query_correct'],
                    final_fixed=int(data[case['reader']+'_conditional_fixed'][indices].sum()),
                    context_correct_bits=int((data[case['reader']+'_final'][indices,0,:32]==raw['inputs'][indices,:32]).sum()),
                    coordinate_flips=int(sum(data[p+'_changes'][:,indices].sum() for p in ('context','gap','query',case['reader']))),
                    pair_moves=int((data['kick_choice'][indices]>=0).sum()) if case['reader']=='pair' else 0,
                    coordinate_trials=17408,selector_field_dot_products=1024 if case['reader']=='pair' else 0,
                    selector_pair_evaluations=9024 if case['reader']=='pair' else 0)
            else:row.update(neural_assays=0,query_eight_correct=0,final_fixed=0,context_correct_bits=0,
                coordinate_flips=0,pair_moves=0,coordinate_trials=0,selector_field_dot_products=0,selector_pair_evaluations=0)
            table['cases'].append(row)
        train,held=scores['trained'],scores['heldout'];a,b=train['task_correct'],held['task_correct']
        label='both_success' if a and b else 'trained_only' if a else 'heldout_only' if b else 'neither'
        table['generalization'].append(dict(block=block,**case,success_class=label,assays=1,
            trained_task_correct=a,heldout_task_correct=b,trained_query_correct=train['query_correct'],heldout_query_correct=held['query_correct']))
    stacks={key:np.stack([bybirth[b] for b in range(4)],axis=1) for key,bybirth in outputs.items()}
    for panel,indices in m.PANELS.items():
        for name,family,g,left,right in CONTRASTS:
            a=flags(stacks[(panel,)+left],target[indices],literal);b=flags(stacks[(panel,)+right],target[indices],literal)
            table['effects'].append(dict(block=block,contrast=name,family=family,generation=g,panel=panel,left='|'.join(map(str,left)),
                right='|'.join(map(str,right)),tasks=4,queries=32,bits=1536,**paired(a,b,literal)))
    for node in graph['records']:
        values=m.get_record(raw,graph,node['id']);parent=node['parent_record']
        same_kind=parent>=0 and graph['records'][parent]['kind']==node['kind'];changed=0;distance=-1.
        if same_kind:
            before=m.get_record(raw,graph,parent)
            changed=sum(int(np.count_nonzero(values[k]!=before[k])) for k in values)
            distance=float(np.sqrt(sum(np.square(values[k].astype(float)-before[k].astype(float)).sum() for k in values)))
        row={k:node[k] for k in ('kind','origin','scope','route','policy','generation','birth','operation','parent_record','parent_read','packet_index')}
        payload=PAYLOAD[node['kind']] if node['kind'] not in ('linear_ls','quadratic_ls') else sum(v.size for v in values.values())
        row.update(block=block,record_id=node['id'],records=1,changed_values=changed,record_change_l2=distance,
            changed_records=int(changed>0),comparable_parent=int(same_kind),zero_records=int(all(not v.any() for v in values.values())),
            packed_payload_values=payload,packed_payload_bytes=(1 if node['kind']=='parity_erm' else 8)*payload,
            materialized_record_bytes=sum(v.nbytes for v in values.values()),observed_packet_values=1024 if node['packet_index']>=0 else 0)
        table['records'].append(row)
    for node in graph['reads']:
        if node['kind']!='neural':continue
        data=read_data[node['id']];moves=data['kick_choice']>=0
        row=dict(block=block,read_id=node['id'],record_id=node['record'],generation=node['generation'],birth=node['birth'],
            executed_reads=1,queries=16,pair_moves=int(moves.sum()),pair_bit_flips=int(2*moves.sum()),
            minimum_selected_delta=float(data['kick_selected_delta'].min()),coordinate_trials=45056,
            selector_field_dot_products=2048,selector_pair_evaluations=18048)
        for phase in ('context','gap','query','ordinary','pair'):
            row[phase+'_flips']=int(data[phase+'_changes'].sum())
            row[phase+'_fixed']=int(data[phase+'_conditional_fixed'].sum())
        table['trajectories'].append(row)
    assert len(table['cases'])==1440 and len(table['effects'])==2*len(CONTRASTS) and len(table['generalization'])==720
    return table


def network(raw,graph,block,interactions,literal=False):
    rows=interaction_network(raw,graph,block,literal) if interactions else completed.network(raw,graph,block,True,literal)
    for row in rows['records']:
        active=interactions and row['kind']=='neural'
        row.update(interaction_mask_values=48 if active else 0,interaction_coefficient_values=48 if active else 0,
            interaction_payload_bytes=432 if active else 0,
            active_interaction_terms=int(np.count_nonzero(m.get_record(raw,graph,row['record_id'])['interaction_weights'])) if active else 0)
        if active:row['packed_payload_bytes']=65456
    for row in rows['trajectories']:
        data=m.get_read(raw,graph,row['read_id'])
        row['interaction_coordinate_field_evaluations']=sum(int(data[p+'_interaction_site_evaluations']) for p in ('context','gap','query','ordinary','pair')) if interactions else 0
    return rows


def arm_effects(outputs,cases,target,block,literal=False):
    rows=completed.arm_effects(outputs,cases,target,block,literal)
    for row in rows:row['comparison']='interactions_minus_pairwise'
    return rows


def combine(rows,geo,completions,outputs,cases,target,block,repairs):
    result={k:[] for k in KINDS}
    for condition in m.CONDITIONS:
        for bundle in (rows[condition],geo[condition]):
            for kind,values in bundle.items():result[kind].extend(dict(condition=condition,**r) for r in values)
    result['completions']=[dict(condition='interactions',**r) for r in completions]
    result['arm_effects']=arm_effects(outputs,cases,target,block)
    result['repair']=repairs
    return result


def anchor(rows,geo,archived):
    checked=0
    for kind,values in (rows|geo).items():
        expected=[{k:v for k,v in r.items() if k!='condition'} for r in archived[kind] if r['condition']=='completed']
        assert len(values)==len(expected),(kind,'baseline row count')
        for current,prior in zip(values,expected):
            for key,value in prior.items():assert current[key]==value,('H092 pairwise anchor',kind,key)
        checked+=len(values)
    return checked
