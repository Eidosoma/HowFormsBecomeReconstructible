"""Separate expression, inherited-record and native-comparator contrasts."""
from collections import defaultdict
import numpy as np
from h083.measure import flags,paired
from h089 import model as m

CASE_KEYS=('scope','route','policy','generation','source','reader')
KINDS=('cases','effects','generalization','records','trajectories')
KEYS=dict(cases=CASE_KEYS+('panel',),effects=('contrast','family','generation','panel'),
    generalization=CASE_KEYS+('success_class',),
    records=('scope','route','policy','generation','origin','operation','kind'),trajectories=('generation',))
DETAILS={'block','birth','record','read','record_id','read_id','parent_record','parent_read','packet_index',
    'left','right','policy_index','rank','record_change_l2','minimum_selected_delta'}
PAYLOAD=dict(neural=8128,linear_ls=640,quadratic_ls=1120,nearest_history=1024,parity_erm=96)


def selector(scope,route,policy,g,reader,source='own'):return scope,route,policy,g,source,reader


def comparison(scope,method,g,policy,reader):return f'against_{scope}_{method}_g{g}_parent_{policy}_reader_{reader}'


def contrasts():
    result=[]
    def add(name,family,g,left,right):result.append((name,family,g,left,right))
    for g in range(3):
        for route in ('rewrite','copy'):
            for p in m.READERS:
                add(f'expression_g{g}_{route}_{p}','expression',g,
                    selector('lineage',route,p,g,'pair'),selector('lineage',route,p,g,'ordinary'))
    for g in (1,2):
        for reader in m.READERS:
            for route in ('rewrite','copy'):
                name=f'inherited_g{g}_{reader}' if route=='rewrite' else f'copy_invariance_g{g}_{reader}'
                add(name,'inherited_record' if route=='rewrite' else 'copy_invariance',g,
                    selector('lineage',route,'pair',g,reader),selector('lineage',route,'ordinary',g,reader))
            for p in m.READERS:
                left=selector('lineage','rewrite',p,g,reader)
                for scope in ('lineage','local'):
                    for method in ('copy',*m.BASELINES):
                        pp=p if method=='copy' or scope=='local' else 'direct'
                        rr=reader if method=='copy' else 'direct'
                        add(comparison(scope,method,g,p,reader),'comparator',g,left,selector(scope,method,pp,g,rr))
        for route in m.ROUTES:
            neural=route in ('rewrite','copy')
            for p in m.READERS if neural else ('direct',):
                for reader in m.READERS if neural else ('direct',):
                    own=selector('lineage',route,p,g,reader)
                    for source in ('donor','erased'):
                        add(f'source_{route}_{p}_{reader}_g{g}_own_minus_{source}','source',g,
                            own,selector('lineage',route,p,g,reader,source))
    for route in m.ROUTES:
        neural=route in ('rewrite','copy')
        for p in m.READERS if neural else ('direct',):
            for reader in m.READERS if neural else ('direct',):
                add(f'progression_{route}_{p}_{reader}','generation',2,
                    selector('lineage',route,p,2,reader),selector('lineage',route,p,1,reader))
                add(f'two_handoffs_{route}_{p}_{reader}','two_handoffs',2,
                    selector('lineage',route,p,2,reader),selector('lineage',route,p,0,reader))
    assert len({r[0] for r in result})==len(result)
    return result


CONTRASTS=contrasts()
PRIMARY_COMPARATORS=tuple(comparison(scope,method,2,'pair','ordinary') for scope in ('lineage','local') for method in ('copy',*m.BASELINES))


def case_score(output,target,literal):
    if literal:hits=np.asarray([sum(int(x)==int(y) for x,y in zip(row,t)) for row,t in zip(output,target)])
    else:hits=(output==target).sum(-1)
    return dict(task_correct=int(all(v>=44 for v in hits)),task_total=1,
        query_correct=sum(int(v>=44) for v in hits),query_total=8,bit_correct=int(hits.sum()),bit_total=384,
        exact_correct=sum(int(v==48) for v in hits))


def network(raw,graph,block,literal=False):
    table={k:[] for k in KINDS};outputs=defaultdict(dict);target=raw['responses_own'];donor=raw['responses_donor']
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
        row.update(block=block,record_id=node['id'],records=1,changed_values=changed,record_change_l2=distance,
            changed_records=int(changed>0),comparable_parent=int(same_kind),zero_records=int(all(not v.any() for v in values.values())),
            packed_payload_values=PAYLOAD[node['kind']],packed_payload_bytes=(1 if node['kind']=='parity_erm' else 8)*PAYLOAD[node['kind']],
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


def verify(raw,graph,table):
    expected=network(raw,graph,table['cases'][0]['block'],True)
    assert table==expected,'independent literal table recount'
    for row in table['effects']:
        if row['family']=='copy_invariance':assert row['task_gains']==row['task_losses']==row['query_gains']==row['query_losses']==row['bit_gains']==row['bit_losses']==0
    return sum(map(len,table.values()))
