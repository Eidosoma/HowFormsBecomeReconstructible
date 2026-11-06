"""Resolved coverage, task retention, and information-matched paired contrasts."""
from collections import defaultdict
import numpy as np
from h100 import model as m

CASE_KEYS=('scope','route','policy','generation','source','reader','mode','panel')
LEDGER_KEYS=('scope','route','policy','generation','origin','mode')
def select(scope,route,policy,g,source,reader,mode):return scope,route,policy,g,source,reader,mode
def primary(g=2,mode='erased_reference_repair',route='rewrite',scope='lineage'):
    return select(scope,route,'pair',g,'own','pair' if g==0 else 'ordinary',mode)
def contrasts():
    rows=[]
    def add(name,group,left,right):rows.append(dict(name=name,group=group,left=left,right=right))
    for g in (1,2):
        for route in ('rewrite','copy'):
            add(f'references_{route}_g{g}','reference_observations',primary(g,route=route),primary(g,'erased_no_reference',route))
    for scope in ('lineage','local'):
        for mode,group in (('erased_no_reference','observation_limited_copy'),('erased_reference_repair','adaptive_copy'),('retained','retained_copy_ceiling')):
            add(f'{group}_{scope}',group,primary(),primary(mode=mode,route='copy',scope=scope))
        for method in m.BASELINES:
            add(f'native_{scope}_{method}','native_controls',primary(),select(scope,method,'direct' if scope=='lineage' else 'pair',2,'own','direct','erased_reference_repair'))
    add('repaired_minus_retained_rewrite','decoder_identity',primary(),primary(mode='retained'))
    add('pair_minus_ordinary_parent','parent_policy',primary(),select('lineage','rewrite','ordinary',2,'own','ordinary','erased_reference_repair'))
    return tuple(rows)
CONTRASTS=contrasts()

def flags(output,target,known,literal=False):
    bits=output==target
    hits=np.asarray([sum(int(a)==int(b) for a,b in zip(row,t)) for row,t in zip(output,target)]) if literal else bits.sum(-1)
    resolved=np.asarray([all(bool(v) for v in row) for row in known]) if literal else known.all(-1)
    query=(hits>=44)&resolved
    return dict(task=np.asarray(bool(query.all())),query=query,bit=bits,exact=(hits==48)&resolved,resolved=resolved)
def counts(f,known):
    return dict(task_correct=int(f['task']),task_total=1,query_correct=int(f['query'].sum()),query_total=8,
        bit_correct=int(f['bit'].sum()),bit_total=384,exact_correct=int(f['exact'].sum()),
        resolved_queries=int(f['resolved'].sum()),unresolved_queries=int((~f['resolved']).sum()),unresolved_bits=int((~known).sum()))
def paired(a,b,literal=False):
    count=lambda x:sum(bool(v) for v in np.asarray(x).flat) if literal else int(np.count_nonzero(x))
    return {key:value for unit in ('task','query','bit','exact','resolved') for key,value in
        ((unit+'_gains',count(a[unit]&~b[unit])),(unit+'_losses',count(~a[unit]&b[unit])))}

def acquire_outputs(raw,graph,bank):
    physical=np.stack([m.response(m.get_read(raw,graph,r['read']),graph['reads'][r['read']]['kind'],r['reader']) for r in graph['cases']])
    outputs=[];known=[]
    for mi,mode in enumerate(m.MODES):
        ys=[];ks=[]
        for i,row in enumerate(graph['cases']):
            g,b=row['generation'],row['birth'];book=dict(signs=bank['signs'][mi,g,b],known=bank['known'][mi,g,b])
            decoded=m.calibration.decode(dict(codebook=book,physical_responses=physical[i]));ys.append(decoded['values']);ks.append(decoded['known'])
        outputs.append(np.stack(ys));known.append(np.stack(ks))
    return dict(physical_outputs=physical,decoded_outputs=np.stack(outputs),decoded_known=np.stack(known))

def network(bundle,graph,target,block,literal=False):
    rows=[];lookup={}
    assert bundle['decoded_outputs'].shape==bundle['decoded_known'].shape==(3,720,16,48)
    for mi,mode in enumerate(m.MODES):
        for i,case in enumerate(graph['cases']):
            output=bundle['decoded_outputs'][mi,i];known=bundle['decoded_known'][mi,i]
            identity=tuple(case[k] for k in CASE_KEYS[:6])+(mode,)
            for panel,indices in m.PANELS.items():
                f=flags(output[indices],target[indices],known[indices],literal);lookup[identity,panel,case['birth']]=f
                rows.append(dict(block=block,**case,mode=mode,panel=panel,**counts(f,known[indices])))
    effects=[]
    for contrast in CONTRASTS:
        for panel in m.PANELS:
            totals=defaultdict(int);improved=worsened=tied=0
            for birth in range(4):
                a=lookup[contrast['left'],panel,birth];b=lookup[contrast['right'],panel,birth]
                for k,v in paired(a,b,literal).items():totals[k]+=v
                net=int(a['task'])-int(b['task']);improved+=net>0;worsened+=net<0;tied+=net==0
            effects.append(dict(block=block,contrast=contrast['name'],group=contrast['group'],panel=panel,
                tasks=4,queries=32,bits=1536,**dict(totals),births_improved=int(improved),births_worsened=int(worsened),births_tied=int(tied)))
    ledger=[]
    for scope in ('lineages','locals'):
        for entry in graph[scope]:
            g=entry['generation'];kind=graph['records'][entry['record']]['kind']
            for mode in m.MODES:
                events=2 if g==0 or mode=='erased_reference_repair' else 0
                retained=int(g>0 and mode=='retained');erased=int(g>0 and mode!='retained')
                task_observations=8 if g==0 or entry['route']!='copy' else 0
                ledger.append(dict(block=block,scope='lineage' if scope=='lineages' else 'local',
                    **{k:entry[k] for k in ('origin','route','policy','generation','birth','record')},kind=kind,mode=mode,
                    recipients=1,decoder_erased=erased,reference_events=events,measured_reference_values=48*events,
                    retained_calibration_signs=48*retained,retained_coverage_flags=48*retained,
                    materialized_decoder_bytes=96,packed_sign_bytes=6,packed_coverage_bytes=6,
                    actual_task_observations=task_observations,actual_task_response_values=48*task_observations,
                    unresolved_signs=48 if g and mode=='erased_no_reference' else 0))
    assert len(rows)==4320 and len(effects)==40 and len(ledger)==1056
    return dict(cases=rows,effects=effects,ledger=ledger)

def verify_bundle(bundle,raw,graph,bank):
    checks=0
    for i,case in enumerate(graph['cases']):
        node=graph['reads'][case['read']];kind=node['kind'];ri=node['index']
        stored=raw['read_'+kind+'_'+(case['reader']+'_final' if kind=='neural' else 'final')][ri]
        expected=stored[:,0,80:] if kind=='neural' else stored
        np.testing.assert_array_equal(bundle['physical_outputs'][i],expected);checks+=1
        for mi in range(3):
            g,b=case['generation'],case['birth'];signs=bank['signs'][mi,g,b];known=bank['known'][mi,g,b]
            np.testing.assert_array_equal(bundle['decoded_outputs'][mi,i],expected*signs)
            np.testing.assert_array_equal(bundle['decoded_known'][mi,i],np.broadcast_to(known,(16,48)));checks+=2
    return checks
