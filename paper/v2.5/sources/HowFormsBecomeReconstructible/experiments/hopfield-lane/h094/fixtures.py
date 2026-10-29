"""Engineering checks for target-free context holding and released dynamics."""
from pathlib import Path
from copy import deepcopy
import json
import numpy as np
from h007.io import save
from h093 import dynamics as legacy
from h093.fixtures import load,rejects
from h094 import model as m,dynamics,reference,audit,geometry,measure,report

def baseline_boundary_checks(source,source_graph,raw,graph):
    checks=0
    for origin in m.ORIGINS:
        for kind in m.KINDS:
            a=next(r for r in source_graph['records'] if r['operation']=='founder' and r['origin']==origin and r['kind']==kind)
            b=next(r for r in graph['records'] if r['operation']=='founder' and r['origin']==origin and r['kind']==kind)
            before=m.get_record(source,source_graph,a['id']);after=m.get_record(raw,graph,b['id'])
            for key in before:np.testing.assert_array_equal(before[key],after[key]);checks+=1
        for birth in range(4):
            reads=[]
            for rr,gg in ((source,source_graph),(raw,graph)):
                item=next(r for r in gg['lineages'] if (r['origin'],r['route'],r['policy'],r['generation'],r['birth'])==(origin,'rewrite','ordinary',0,birth))
                reads.append(m.get_read(rr,gg,item['read']))
            for key,value in reads[0].items():
                if key.startswith(('context_','gap_')):np.testing.assert_array_equal(value,reads[1][key],err_msg=key);checks+=1
    return checks

def schedule_fixtures(tape):
    completion=m.complete(dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN]))
    record=m.compile_record(completion,'neural')
    packet=dict(record=record,birth=tape['birth'][0,0],observed_history=m.X,
        **{'orders_'+p:tape['orders_'+p][0] for p in ('context','gap','query')})
    baseline=legacy.read(packet);zero=dynamics.read(packet,protect=False)
    for key,value in baseline.items():np.testing.assert_array_equal(value,zero[key],err_msg=key)
    tests=['all-false hold schedule exactly reproduces every H093 neural read array']
    check=audit.old.pair_audit.Audit()
    # A synthetic wrong internal context is held without any truth argument.
    j=np.zeros((128,128));j[:24,24:32]=1;j[24:32,:24]=1
    record=dict(J=j,interaction_masks=np.zeros(48,dtype=np.int8),interaction_weights=np.zeros(48))
    state=np.ones((1,1,128),dtype=np.int8);state[...,:24]=-1
    segment_packet=dict(record=record,state=state,orders=np.tile(np.arange(128),(8,1)),clamp_indices=np.arange(32,80),
        clamp_values=np.ones((1,1,48),dtype=np.int8),active_sweeps=8,feedback=np.r_[0.,np.ones(7)],hold_context=dynamics.HOLD.copy())
    data=dynamics.segment(segment_packet)
    np.testing.assert_array_equal(data['trace'][1,...,:32],state[...,:32])
    np.testing.assert_array_equal(data['trace'][2,...,:32],np.ones((1,1,32),dtype=np.int8))
    assert int(data['context_updates_skipped'])==32 and int(data['coordinate_evaluations'])==608
    ref={k:v.copy() for k,v in record.items()};ref['J']=ref['J'].astype(np.longdouble)
    reference.segment(record,ref,state,segment_packet['orders'],segment_packet['clamp_indices'],segment_packet['clamp_values'],
        segment_packet['feedback'],data,check,segment_packet['hold_context'])
    tests.append('wrong current context stays wrong in the held sweep; all context coordinates are released and change by the energy rule on sweep two')
    bad={k:v.copy() for k,v in data.items()};bad['hold_context'][0]=False
    rejects(lambda:reference.segment(record,ref,state,segment_packet['orders'],segment_packet['clamp_indices'],segment_packet['clamp_values'],
        segment_packet['feedback'],bad,check,segment_packet['hold_context']))
    bad={k:v.copy() for k,v in data.items()};bad['trace'][1,0,0,0]*=-1
    rejects(lambda:reference.segment(record,ref,state,segment_packet['orders'],segment_packet['clamp_indices'],segment_packet['clamp_values'],
        segment_packet['feedback'],bad,check,segment_packet['hold_context']))
    tests.append('independent replay rejects corrupt hold schedules and a changed held coordinate')
    rejects(lambda:dynamics.segment(dict(segment_packet,hold_context=np.ones(8))))
    rejects(lambda:dynamics.segment(dict(segment_packet,true_context=np.ones(32))))
    rejects(lambda:dynamics.read(dict(packet,hidden_target=tape['responses_own'])))
    tests.append('reader and segment packets reject context resupply, hidden targets and malformed hold tapes')
    return dict(passed=True,tests=tests,baseline_arrays=len(baseline),numerical_checks=check.count)

def run(out,binding):
    out=Path(out);out.mkdir(exist_ok=False);tests=[]
    source=load(binding['source_raw']);source_graph=json.loads(Path(binding['source_graph']).read_text())
    tape={k:source[k].copy() for k in m.tapes('engineering',binding['block'])}
    schedule=schedule_fixtures(tape);tests.extend(schedule['tests'])
    packet=dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN])
    completion=m.complete(packet)
    for key,value in zip(('masks','signs','outputs'),audit.infer(packet['observed_outputs'])):np.testing.assert_array_equal(completion[key],value)
    rejects(lambda:m.complete(dict(packet,hidden_rule=tape['rule_masks_own'])))
    rejects(lambda:m.complete(dict(observed_inputs=m.X,observed_outputs=tape['responses_own'])))
    rejects(lambda:m.Build(tape))
    tests.append('unchanged scalar completion uses only eight actual observations and rejects full truth and hidden-rule packets')
    raw,graph=m.run_tapes(tape)
    with (out/'acquired_raw.npz').open('xb') as f:np.savez_compressed(f,**raw)
    save(out/'acquired_graph.json',graph)
    checked=audit.network(raw,graph,'engineering',binding['block']);save(out/'acquired_audit.json',checked)
    tests.append('all actual packets, record fits, full copies and unique protected trajectories pass independent audit')
    unchanged=baseline_boundary_checks(source,source_graph,raw,graph)
    tests.append('all founder records and complete G0 pre-query traces are bitwise identical to H093')
    altered={k:v.copy() for k,v in tape.items()}
    for origin in m.ORIGINS:
        altered['responses_'+origin][m.TEST]*=-1;altered['rule_masks_'+origin][:]=0;altered['rule_signs_'+origin]*=-1
    alternate,alternate_graph=m.run_tapes(altered)
    with (out/'altered_raw.npz').open('xb') as f:np.savez_compressed(f,**alternate)
    assert alternate_graph==graph
    for key in raw:
        if not key.startswith(('responses_','rule_')):np.testing.assert_array_equal(raw[key],alternate[key],err_msg=key)
    tests.append('all held-out truth and hidden-rule changes leave protected physics and inherited records unchanged')
    check=audit.old.pair_audit.Audit();values,data=audit.metadata(raw,graph,check)
    bad={**raw,'completion_outputs':raw['completion_outputs'].copy()};bad['completion_outputs'][0,0,0]*=-1
    rejects(lambda:audit.record_checks(bad,graph,values,data,audit.old.pair_audit.Audit()))
    corrupt=deepcopy(graph);node=next(r for r in corrupt['records'] if r['scope']=='lineage' and r['generation']==2 and r['route']=='rewrite');node['parent_record']=0
    rejects(lambda:audit.metadata(raw,corrupt,audit.old.pair_audit.Audit()))
    copied=next(n for n in graph['records'] if n['operation']=='copy')
    bad={**raw,'record_neural_interaction_weights':raw['record_neural_interaction_weights'].copy()};bad['record_neural_interaction_weights'][copied['index'],0]+=.25
    rejects(lambda:audit.metadata(bad,graph,audit.old.pair_audit.Audit()))
    tests.append('corrupt completions, inherited predecessor and copied interaction coefficient are rejected')
    rows={};geo={};diagnostics={};metas={};transitions={};outputs=[];cases=None;geometry_checks=0
    for condition,r,g in [('unprotected',source,source_graph),('protected',raw,graph)]:
        rows[condition]=measure.network(r,g,binding['block'],condition=='protected')
        assert rows[condition]==measure.network(r,g,binding['block'],condition=='protected',True)
        diagnostics[condition],metas[condition],c=geometry.extract(r,g,condition=='protected')
        geometry_checks+=c['geometry_checks']+geometry.validate(diagnostics[condition],metas[condition])
        geo[condition]=geometry.tables(diagnostics[condition],metas[condition],binding['block']);geometry.verify(diagnostics[condition],metas[condition],geo[condition])
        transitions[condition]=measure.transitions(r,g,binding['block']);assert transitions[condition]==measure.transitions(r,g,binding['block'],True)
        output,metadata=measure.old.case_outputs(r,g);outputs.append(output)
        if cases is None:cases=metadata
        else:assert cases==metadata
    anchored=measure.anchor(rows['unprotected'],geo['unprotected'],json.loads(Path(binding['source_rows']).read_text()))
    tests.append('baseline scores, costs and geometry anchor to H093; both conditions and 768 context/learning rows literally recount')
    bad={**diagnostics['protected'],'endpoint_energy':diagnostics['protected']['endpoint_energy'].copy()};bad['endpoint_energy'][0,0,0,0]+=.01
    rejects(lambda:geometry.validate(bad,metas['protected']))
    tests.append('unchanged-energy geometry still rejects corrupted endpoint energies')
    completions=measure.completion_rows(raw,graph,binding['block']);assert completions==measure.completion_rows(raw,graph,binding['block'],True)
    for row in rows['protected']['trajectories']:assert row['coordinate_trials']==44544 and row['context_updates_skipped']==512
    for row in rows['protected']['records']:
        if row['kind']=='neural':assert row['packed_payload_bytes']==65456
    tests.append('skipped updates, performed work, unchanged record storage and actual versus predicted teaching data remain distinct')
    output=np.stack(outputs);combined=measure.combine(rows,geo,completions,output,cases,tape['responses_own'],binding['block'],transitions)
    assert combined['arm_effects']==measure.arm_effects(output,cases,tape['responses_own'],binding['block'],True)
    neutral=measure.arm_effects(np.repeat(output[:1],2,axis=0),cases,tape['responses_own'],0)
    assert all(all(r[k]==0 for k in ('task_gains','task_losses','query_gains','query_losses','bit_gains','bit_losses')) for r in neutral)
    tests.append('matched changes recount literally and identical outputs produce zero paired gains or losses')
    flat=dict(comparison_outputs=output,comparison_target=tape['responses_own'])
    flat.update({'protected__'+k:v for k,v in raw.items()})
    for condition in m.CONDITIONS:flat.update({condition+'_geometry__'+k:v for k,v in diagnostics[condition].items()})
    with (out/'raw.npz').open('xb') as f:np.savez_compressed(f,**flat)
    reloaded=load(out/'raw.npz');assert reloaded.keys()==flat.keys()
    for key in flat:np.testing.assert_array_equal(reloaded[key],flat[key])
    meta=dict(graphs={'unprotected':source_graph,'protected':graph},geometry_metadata=metas,cases=cases)
    save(out/'paths.json',meta);assert json.loads((out/'paths.json').read_text())==meta
    tests.append('all protected arrays, comparison evidence and metadata serialize exactly')
    summary=report.produce(out,[combined],False)
    assert len(summary['primary_comparators'])==10 and all(v=='ENGINEERING_OR_SYNTHETIC_ONLY' for v in summary['findings'].values())
    tests.append('engineering reporting retains all ten comparators and six separate unqualified findings')
    a={k:deepcopy(summary[k]) for k in measure.KINDS}
    for origin in m.ORIGINS:
        for reader in m.READERS:
            r=report.transition(a['transitions'],'protected',origin=origin,reader=reader)
            for key in ('context_matched_gap_end','context_matched_first_query_end','context_matched_recipient_end'):r[key]=r['queries']
    r=report.transition(a['transitions'],'unprotected');r['context_matched_recipient_end']=r['queries']-1
    report.score(a['cases'],'protected','heldout',0,'pair')['task_correct']=0
    verdict=report.findings(a,True)
    assert verdict['context_transition']=='G0_HELDOUT_CONTEXT_TRANSITION_SCREEN_PASSED' and verdict['heldout_g0']=='G0_HELDOUT_CAPABILITY_SCREEN_FAILED'
    r=report.transition(a['transitions'],'protected');r['context_matched_gap_end']-=1
    assert report.findings(a,True)['context_transition']=='G0_HELDOUT_CONTEXT_TRANSITION_SCREEN_FAILED'
    for panel,g,reader in [('heldout',0,'pair'),('trained',2,'ordinary')]:
        report.score(a['cases'],'protected',panel,g,reader)['task_correct']=3
        for passive in ('donor','erased'):report.score(a['cases'],'protected',panel,g,reader,passive)['task_correct']=0
    report.arm(a['arm_effects'],'heldout',0,'pair').update(task_gains=1,task_losses=0)
    report.score(a['cases'],'protected','heldout')['task_correct']=0
    verdict=report.findings(a,True)
    assert verdict['heldout_g0']=='G0_HELDOUT_CAPABILITY_SCREEN_PASSED' and verdict['heldout_g2']=='G2_HELDOUT_INHERITANCE_SCREEN_FAILED' and verdict['trained_g2']=='G2_TRAINED_CAPABILITY_SCREEN_PASSED'
    tests.append('preserving context cannot substitute for correctness, capability or inheritance; holding incorrect context fails the transition gate')
    effects=[r for r in a['effects'] if r['condition']=='protected' and r['panel']=='heldout' and r['contrast'] in measure.PRIMARY_COMPARATORS]
    for r in effects:r.update(task_gains=1,task_losses=0,query_gains=1,query_losses=0)
    assert report.findings(a,True)['comparators']=='OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    effects[0]['task_losses']=1
    assert report.findings(a,True)['comparators']=='NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    effects[0]['task_losses']=0;effects[0]['query_losses']=2
    assert report.findings(a,True)['comparators']=='NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    tests.append('any comparator tie or negative query net prevents joint superiority')
    assert sum(map(len,combined.values()))==7552+sum(len(rows[c]['trajectories']) for c in m.CONDITIONS)
    return dict(passed=True,count=len(tests),tests=tests,engineering_only=True,main_outcomes_generated=False,
        schedule_fixture_checks=schedule['numerical_checks'],baseline_reader_arrays=schedule['baseline_arrays'],
        archived_baseline_arrays=len(source),new_numerical_checks=checked['numerical_checks'],geometry_checks=geometry_checks,
        unchanged_founder_and_prequery_arrays=unchanged,baseline_rows_anchored=anchored,fixture_rows=sum(map(len,combined.values())),
        saved_arrays=len(flat),paired_rows=360,transition_rows=768)
