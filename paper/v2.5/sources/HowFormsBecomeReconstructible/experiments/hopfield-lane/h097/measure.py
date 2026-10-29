"""Literal task scores; separate physical-copy, informed-repair and native comparisons."""
from collections import defaultdict
import numpy as np
from h091 import measure as old
from h097 import model as m
CASE_KEYS=old.CASE_KEYS
KINDS=(*old.KINDS,'completions','transitions','arm_effects','writer','stability')
KEYS={k:('condition',)+v for k,v in old.KEYS.items()}|dict(
    completions=('condition','kind','origin','scope','route','policy','generation','operation'),
    transitions=('condition','scope','route','policy','generation','origin','reader','panel'),
    arm_effects=('comparison',)+CASE_KEYS+('panel',),
    writer=('condition','kind','origin','scope','route','policy','generation','operation'),
    stability=('condition','origin','scope','route','policy','generation','pattern_set','panel'))
DETAILS=old.ALL_DETAILS
PAYLOAD=dict(old.PAYLOAD,neural=8224,nearest_history=2048)
case_score,flags,paired=old.case_score,old.flags,old.paired
case_outputs=old.case_outputs

def selector(scope,route,policy,g,reader,source='own'):return scope,route,policy,g,source,reader


def comparison(scope,method,g,policy,reader):return f'against_{scope}_{method}_g{g}_parent_{policy}_reader_{reader}'


def contrasts():
    result=[]
    def add(name,family,g,left,right):result.append((name,family,g,left,right))
    for g in range(3):
        for route in m.NEURAL_ROUTES:
            for p in m.READERS:
                add(f'expression_g{g}_{route}_{p}','expression',g,
                    selector('lineage',route,p,g,'pair'),selector('lineage',route,p,g,'ordinary'))
    for g in (1,2):
        for reader in m.READERS:
            for route in m.NEURAL_ROUTES:
                name=f'inherited_g{g}_{reader}' if route=='rewrite' else f'{route}_parent_effect_g{g}_{reader}'
                add(name,'inherited_record' if route=='rewrite' else 'copy_invariance' if route=='copy' else 'repair_parent_effect',g,
                    selector('lineage',route,'pair',g,reader),selector('lineage',route,'ordinary',g,reader))
            for p in m.READERS:
                left=selector('lineage','rewrite',p,g,reader)
                for scope in ('lineage','local'):
                    for method in ('copy','copy_repair',*m.BASELINES):
                        pp=p if method in ('copy','copy_repair') or scope=='local' else 'direct'
                        rr=reader if method in ('copy','copy_repair') else 'direct'
                        add(comparison(scope,method,g,p,reader),'comparator',g,left,selector(scope,method,pp,g,rr))
        for route in m.ROUTES:
            neural=route in m.NEURAL_ROUTES
            for p in m.READERS if neural else ('direct',):
                for reader in m.READERS if neural else ('direct',):
                    own=selector('lineage',route,p,g,reader)
                    for source in ('donor','erased'):
                        add(f'source_{route}_{p}_{reader}_g{g}_own_minus_{source}','source',g,
                            own,selector('lineage',route,p,g,reader,source))
    for route in m.ROUTES:
        neural=route in m.NEURAL_ROUTES
        for p in m.READERS if neural else ('direct',):
            for reader in m.READERS if neural else ('direct',):
                add(f'progression_{route}_{p}_{reader}','generation',2,
                    selector('lineage',route,p,2,reader),selector('lineage',route,p,1,reader))
                add(f'two_handoffs_{route}_{p}_{reader}','two_handoffs',2,
                    selector('lineage',route,p,2,reader),selector('lineage',route,p,0,reader))
    assert len({r[0] for r in result})==len(result)
    return result


CONTRASTS=contrasts()
PRIMARY_COMPARATORS=tuple(comparison(scope,method,2,'pair','ordinary') for scope in ('lineage','local') for method in ('copy','copy_repair',*m.BASELINES))

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
    assert len(table['cases'])==1920 and len(table['effects'])==2*len(CONTRASTS) and len(table['generalization'])==960
    return table


def network(raw,graph,block,literal=False):
    interactions=True
    rows=interaction_network(raw,graph,block,literal)
    for row in rows['records']:
        active=interactions and row['kind']=='neural'
        row.update(interaction_mask_values=48 if active else 0,interaction_coefficient_values=48 if active else 0,
            interaction_payload_bytes=432 if active else 0,
            active_interaction_terms=int(np.count_nonzero(m.get_record(raw,graph,row['record_id'])['interaction_weights'])) if active else 0)
        if active:row['packed_payload_bytes']=65456
    for row in rows['trajectories']:
        data=m.get_read(raw,graph,row['read_id'])
        row['interaction_coordinate_field_evaluations']=sum(int(data[p+'_interaction_site_evaluations']) for p in ('context','gap','query','ordinary','pair')) if interactions else 0
    for row in rows['cases']:
        row['context_updates_skipped']=0
        if row['neural_assays']:
            data=m.get_read(raw,graph,row['read']);phases=('context','gap','query',row['reader'])
            row['coordinate_trials']=sum(int(data[p+'_coordinate_evaluations']) for p in phases)//2
            row['context_updates_skipped']=sum(int(data[p+'_context_updates_skipped']) for p in phases)//2
            assert row['coordinate_trials']==17152 and row['context_updates_skipped']==256
    for row in rows['trajectories']:
        data=m.get_read(raw,graph,row['read_id']);phases=('context','gap','query','ordinary','pair')
        row['coordinate_trials']=sum(int(data[p+'_coordinate_evaluations']) for p in phases)
        row['context_updates_skipped']=sum(int(data[p+'_context_updates_skipped']) for p in phases)
        assert row['coordinate_trials']==44544 and row['context_updates_skipped']==512
    return rows

def completion_rows(raw,graph,block,literal=False):
    count=lambda a:sum(bool(v) for v in np.asarray(a).flat) if literal else int(np.count_nonzero(a))
    rows=[]
    for node in graph['records']:
        pi=node['packet_index']
        if pi<0:continue
        pred=raw['completion_outputs'][pi];observed=raw['packet_outputs'][pi];target=raw['responses_'+node['origin']]
        row={k:node[k] for k in ('kind','origin','scope','route','policy','generation','birth','operation','parent_record','parent_read','packet_index')}
        row.update(block=block,record_id=node['id'],packets=1,observed_labels=8,generated_labels=16,
            observed_response_values=384,generated_response_values=768,fitted_rule_values=96,hypothesis_bit_comparisons=32*8*48,
            observed_wrong_bits=count(observed!=target[m.TRAIN]),observed_wrong_queries=count((observed!=target[m.TRAIN]).any(-1)),teaching_disagreement_bits=count(pred[m.TRAIN]!=observed),teaching_disagreement_queries=count((pred[m.TRAIN]!=observed).any(-1)))
        for panel,indices in m.PANELS.items():
            for key,value in old.case_score(pred[indices],target[indices],literal).items():row[panel+'_'+key]=value
        rows.append(row)
    assert len(rows)==298
    return rows


def arm_effects(outputs,cases,target,block,literal=False):
    bycase=defaultdict(dict)
    for i,case in enumerate(cases):bycase[tuple(case[k] for k in CASE_KEYS)][case['birth']]=i
    assert len(bycase)==240 and outputs.shape==(2,960,16,48)
    rows=[]
    for key,births in sorted(bycase.items()):
        assert sorted(births)==list(range(4));indices=[births[b] for b in range(4)]
        for panel,queries in m.PANELS.items():
            values=outputs[:,indices][:,:,queries].transpose(0,2,1,3)
            a,b=[old.flags(v,target[queries],literal) for v in values]
            rows.append(dict(block=block,comparison='loss_minus_intact',**dict(zip(CASE_KEYS,key)),panel=panel,
                tasks=4,queries=32,bits=1536,**old.paired(b,a,literal)))
    assert len(rows)==480
    return rows

def transitions(raw,graph,block,literal=False):
    def count(value):return sum(bool(v) for v in np.asarray(value).flat) if literal else int(np.count_nonzero(value))
    def same(a,b):
        b=np.broadcast_to(b,a.shape)
        return np.asarray([all(int(x)==int(y) for x,y in zip(u,v)) for u,v in zip(a,b)]) if literal else (a==b).all(-1)
    def success(a,b):
        hits=np.asarray([sum(int(x)==int(y) for x,y in zip(u,v)) for u,v in zip(a,b)]) if literal else (a==b).sum(-1)
        return hits>=44
    rows=[];data={r['id']:m.get_read(raw,graph,r['id']) for r in graph['reads'] if r['kind']=='neural'}
    for entry in graph['lineages']:
        if entry['route'] not in m.NEURAL_ROUTES:continue
        node=graph['records'][entry['record']];ancestor=node
        while ancestor['packet_index']<0:ancestor=graph['records'][ancestor['parent_record']]
        learned=raw['completion_outputs'][ancestor['packet_index']];target=raw['responses_'+entry['origin']]
        read=data[entry['read']];c=raw['inputs'][:,:32]
        before=read['gap_final'][:,0,:32];first=read['query_trace'][1,:,0,:32]
        initial=same(read['context_final'][:,0,:32],c);gap=same(before,c);one=same(first,c)
        query=same(read['query_final'][:,0,:32],c);preserved=same(first,before)
        for reader in m.READERS:
            state=read[reader+'_final'][:,0];end=same(state[:,:32],c);output=state[:,80:]
            actual_ok=success(output,target);learned_ok=success(learned,target);read_exact=same(output,learned)
            if literal:valid=np.asarray([any(all(int(u)==int(v) for u,v in zip(row,x)) for x in raw['inputs']) for row in state[:,:80]])
            else:valid=np.any((state[:,:80,None]==raw['inputs'].T[None]).all(1),axis=-1)
            for panel,queries in m.PANELS.items():
                failed=~actual_ok[queries];intact=end[queries];good_rule=learned_ok[queries]
                row={k:entry[k] for k in ('origin','route','policy','generation','birth','record','read')}
                row.update(block=block,scope='lineage',reader=reader,panel=panel,tasks=1,queries=8,
                    task_correct=int(all(actual_ok[queries])),successful_queries=count(actual_ok[queries]),exact_queries=count(same(output,target)[queries]),
                    learned_task_correct=int(all(good_rule)),learned_query_correct=count(good_rule),
                    exact_retrieval_of_completion=count(read_exact[queries]),failed_queries=count(failed),
                    context_matched_context_end=count(initial[queries]),context_matched_gap_end=count(gap[queries]),
                    context_matched_first_query_end=count(one[queries]),context_matched_query_eight_end=count(query[queries]),
                    context_matched_recipient_end=count(intact),valid_input_encoding=count(valid[queries]),
                    context_preserved_first_sweep=count(preserved[queries]),
                    incorrect_context_preserved_first_sweep=count(~gap[queries]&preserved[queries]),
                    first_sweep_context_bit_changes=count(first[queries]!=before[queries]),
                    gap_context_losses=count(initial[queries]&~gap[queries]),
                    new_final_context_losses=count(gap[queries]&~intact),recovered_prequery_context=count(~gap[queries]&intact),
                    failed_with_context_lost=count(failed&~intact),failed_with_context_intact=count(failed&intact),
                    failed_with_wrong_completion=count(failed&~good_rule),failed_despite_correct_completion=count(failed&good_rule),
                    wrong_completion_exactly_retrieved=count(~good_rule&read_exact[queries]))
                rows.append(row)
    assert len(rows)==576
    return rows

def writers(raw,graph,block):
    rows=[]
    for node in graph['records']:
        pi=node['packet_index']
        if pi<0:continue
        row={k:node[k] for k in ('kind','origin','scope','route','policy','generation','birth','operation','parent_record','parent_read','packet_index')}
        neural=node['kind']=='neural';executed=int(raw['compiler_fit_executed'][pi]);iterations=int(raw['compiler_iterations'][pi])
        row.update(block=block,record_id=node['id'],packets=1,constrained_writes=int(neural),solver_executions=executed,
            cached_fits=int(neural)-executed,logical_solver_iterations=iterations,executed_solver_iterations=iterations*executed,
            maximum_normal_residual=float(raw['compiler_normal_residual'][pi]),field_error=float(raw['compiler_field_error'][pi]),
            prior_distance=float(raw['compiler_prior_distance'][pi]),starting_field_error=float(raw['compiler_starting_field_error'][pi]),
            available_edges=int(raw['architecture_mask'][node['generation']].sum()//2) if neural else 0,
            available_interaction_channels=int(raw['architecture_available'][node['generation']].sum()) if neural else 0)
        rows.append(row)
    assert len(rows)==298;return rows


def combine(rows,completed,transition_rows,writer_rows,stability,outputs,cases,target,block):
    result={k:[] for k in KINDS}
    for condition in m.CONDITIONS:
        for kind,values in rows[condition].items():result[kind].extend(dict(condition=condition,**r) for r in values)
        for kind,bundle in [('completions',completed),('transitions',transition_rows),('writer',writer_rows),('stability',stability)]:
            result[kind].extend(dict(condition=condition,**r) for r in bundle[condition])
    result['arm_effects']=arm_effects(outputs,cases,target,block)
    return result
