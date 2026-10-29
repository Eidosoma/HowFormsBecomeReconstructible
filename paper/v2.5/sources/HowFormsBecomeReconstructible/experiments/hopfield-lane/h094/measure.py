"""Matched scores plus actual context, learned-rule and released-reader diagnostics."""
import numpy as np
from h093 import measure as previous
from h094 import model as m

old=previous.old
CASE_KEYS=previous.CASE_KEYS
KINDS=tuple(k for k in previous.KINDS if k!='repair')+('transitions',)
KEYS={k:v for k,v in previous.KEYS.items() if k!='repair'}|dict(transitions=('condition','scope','route','policy','generation','origin','reader','panel'))
DETAILS=previous.DETAILS
PRIMARY_COMPARATORS=previous.PRIMARY_COMPARATORS
CONTRASTS=previous.CONTRASTS
completion_rows=previous.completion_rows

def network(raw,graph,block,protected,literal=False):
    rows=previous.network(raw,graph,block,True,literal)
    for row in rows['cases']:
        row['context_updates_skipped']=0
        if protected and row['neural_assays']:
            data=m.get_read(raw,graph,row['read']);phases=('context','gap','query',row['reader'])
            row['coordinate_trials']=sum(int(data[p+'_coordinate_evaluations']) for p in phases)//2
            row['context_updates_skipped']=sum(int(data[p+'_context_updates_skipped']) for p in phases)//2
            assert row['coordinate_trials']==17152 and row['context_updates_skipped']==256
    for row in rows['trajectories']:
        row['context_updates_skipped']=0
        if protected:
            data=m.get_read(raw,graph,row['read_id']);phases=('context','gap','query','ordinary','pair')
            row['coordinate_trials']=sum(int(data[p+'_coordinate_evaluations']) for p in phases)
            row['context_updates_skipped']=sum(int(data[p+'_context_updates_skipped']) for p in phases)
            assert row['coordinate_trials']==44544 and row['context_updates_skipped']==512
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
        if entry['route'] not in ('rewrite','copy'):continue
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
    assert len(rows)==384
    return rows

def arm_effects(outputs,cases,target,block,literal=False):
    rows=previous.arm_effects(outputs,cases,target,block,literal)
    for row in rows:row['comparison']='protected_minus_unprotected'
    return rows

def combine(rows,geo,completed,outputs,cases,target,block,transition_rows):
    result={k:[] for k in KINDS}
    for condition in m.CONDITIONS:
        for bundle in (rows[condition],geo[condition]):
            for kind,values in bundle.items():result[kind].extend(dict(condition=condition,**r) for r in values)
        result['transitions'].extend(dict(condition=condition,**r) for r in transition_rows[condition])
    result['completions']=[dict(condition='protected',**r) for r in completed]
    result['arm_effects']=arm_effects(outputs,cases,target,block)
    return result

def anchor(rows,geo,archived):
    checked=0
    for kind,values in (rows|geo).items():
        expected=[{k:v for k,v in r.items() if k!='condition'} for r in archived[kind] if r['condition']=='interactions']
        assert len(values)==len(expected),(kind,'baseline count')
        for current,prior in zip(values,expected):
            for key,value in prior.items():assert current[key]==value,('H093 anchor',kind,key)
        checked+=len(values)
    return checked
