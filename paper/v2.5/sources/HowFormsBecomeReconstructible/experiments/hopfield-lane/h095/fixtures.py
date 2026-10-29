"""Engineering-only validation of fresh acquisition and the unchanged six gates."""
from pathlib import Path
from copy import deepcopy
import numpy as np
from h007.io import save
from h093.fixtures import rejects
from h094.fixtures import schedule_fixtures
from h095 import model as m,audit,measure,report

def run(out,binding):
    from h095.workflow import batch,load,read
    out=Path(out);out.mkdir(exist_ok=False);tests=[]
    tape=load(binding['tape_path']);assert binding['cohort']=='engineering'
    for k,v in m.tapes('engineering',binding['block']).items():np.testing.assert_array_equal(tape[k],v)
    assert m.digest(tape)!=m.digest(m.original.tapes('engineering',binding['block']))
    assert m.digest(tape)!=m.digest(m.tapes('fixture',binding['block']))
    tests.append('fresh engineering streams reproduce exactly and differ from old and fixture streams')
    schedule=schedule_fixtures(tape);tests.extend(schedule['tests'])
    packet=dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN]);completion=m.complete(packet)
    for key,value in zip(('masks','signs','outputs'),audit.infer(packet['observed_outputs'])):np.testing.assert_array_equal(completion[key],value)
    rejects(lambda:m.complete(dict(packet,hidden_rule=tape['rule_masks_own'])))
    rejects(lambda:m.complete(dict(observed_inputs=m.X,observed_outputs=tape['responses_own'])))
    tests.append('completion accepts only eight observed responses; hidden rule and held-out observations rejected')
    result=batch(out/'matched',[binding],1,lambda **kw:None);stem=f"block_{binding['block']:03d}"
    arrays={c:load(out/'matched/new_raw'/(stem+'_'+c+'.npz')) for c in m.CONDITIONS}
    graphs={c:read(out/'matched/paths'/(stem+'_'+c+'.json')) for c in m.CONDITIONS}
    tests.append('both fresh conditions pass independent ancestry, writer, trajectory, geometry and literal table audits')
    tests.append('all matched founder records and G0 preparation/gap traces agree exactly')
    altered={k:v.copy() for k,v in tape.items()}
    for o in m.ORIGINS:
        altered['responses_'+o][m.TEST]*=-1;altered['rule_masks_'+o][:]=0;altered['rule_signs_'+o]*=-1
    for condition in m.CONDITIONS:
        raw,graph=m.run_tapes(altered,condition)
        with (out/('altered_'+condition+'.npz')).open('xb') as f:np.savez_compressed(f,**raw)
        assert graph==graphs[condition]
        for k,v in arrays[condition].items():
            if not k.startswith(('responses_','rule_')):np.testing.assert_array_equal(v,raw[k],err_msg=condition+'/'+k)
    tests.append('changing every held-out target and hidden rule leaves both conditions physics and records unchanged')
    raw,graph=arrays['protected'],graphs['protected'];check=audit.old.pair_audit.Audit();values,data=audit.metadata(raw,graph,check)
    bad={**raw,'completion_outputs':raw['completion_outputs'].copy()};bad['completion_outputs'][0,0,0]*=-1
    rejects(lambda:audit.record_checks(bad,graph,values,data,audit.old.pair_audit.Audit()))
    corrupt=deepcopy(graph);node=next(r for r in corrupt['records'] if r['scope']=='lineage' and r['generation']==2 and r['route']=='rewrite');node['parent_record']=0
    rejects(lambda:audit.metadata(raw,corrupt,audit.old.pair_audit.Audit()))
    copied=next(n for n in graph['records'] if n['operation']=='copy');bad={**raw,'record_neural_interaction_weights':raw['record_neural_interaction_weights'].copy()}
    bad['record_neural_interaction_weights'][copied['index'],0]+=.25
    rejects(lambda:audit.metadata(bad,graph,audit.old.pair_audit.Audit()))
    tests.append('corrupt completion, incorrect ancestry and damaged copied interaction are rejected')
    combined=read(out/'matched/blocks'/(stem+'.json'));comparison=load(out/'matched/raw'/(stem+'.npz'))
    metadata=read(out/'matched/paths'/(stem+'.json'))
    neutral=measure.arm_effects(np.repeat(comparison['comparison_outputs'][:1],2,axis=0),metadata['cases'],tape['responses_own'],0)
    assert all(all(r[k]==0 for k in ('task_gains','task_losses','query_gains','query_losses','bit_gains','bit_losses')) for r in neutral)
    assert len(combined['completions'])==468 and {r['condition'] for r in combined['completions']}==set(m.CONDITIONS)
    tests.append('both completion tables retained and identical matched outputs give zero gains/losses')
    (out/'report').mkdir();summary=report.produce(out/'report',[combined],False)
    assert summary['experiment']=='H095' and not summary['baseline_reused'] and summary['root_seed']==95095
    assert len(summary['primary_comparators'])==10 and all(v=='ENGINEERING_OR_SYNTHETIC_ONLY' for v in summary['findings'].values())
    tests.append('engineering report identifies new acquisition and retains all ten comparators without main findings')
    a={k:deepcopy(summary[k]) for k in measure.KINDS}
    for origin in m.ORIGINS:
        for reader in m.READERS:
            row=report.transition(a['transitions'],'protected',origin=origin,reader=reader)
            for k in ('context_matched_gap_end','context_matched_first_query_end','context_matched_recipient_end'):row[k]=row['queries']
    row=report.transition(a['transitions'],'unprotected');row['context_matched_recipient_end']=row['queries']-1
    report.score(a['cases'],'protected','heldout',0,'pair')['task_correct']=0
    v=report.findings(a,True);assert v['context_transition']=='G0_HELDOUT_CONTEXT_TRANSITION_SCREEN_PASSED' and v['heldout_g0']=='G0_HELDOUT_CAPABILITY_SCREEN_FAILED'
    row=report.transition(a['transitions'],'protected');row['context_matched_gap_end']-=1
    assert report.findings(a,True)['context_transition']=='G0_HELDOUT_CONTEXT_TRANSITION_SCREEN_FAILED'
    tests.append('holding wrong context fails the context gate; context success cannot replace capability')
    for panel,g,reader in [('heldout',0,'pair'),('trained',2,'ordinary')]:
        report.score(a['cases'],'protected',panel,g,reader)['task_correct']=3
        for source in ('donor','erased'):report.score(a['cases'],'protected',panel,g,reader,source)['task_correct']=0
    report.arm(a['arm_effects'],'heldout',0,'pair').update(task_gains=1,task_losses=0)
    report.score(a['cases'],'protected','heldout')['task_correct']=0
    v=report.findings(a,True);assert v['heldout_g0']=='G0_HELDOUT_CAPABILITY_SCREEN_PASSED' and v['heldout_g2']=='G2_HELDOUT_INHERITANCE_SCREEN_FAILED' and v['trained_g2']=='G2_TRAINED_CAPABILITY_SCREEN_PASSED'
    tests.append('G0, G2 unseen and taught capability remain separate unchanged decisions')
    effects=[r for r in a['effects'] if r['condition']=='protected' and r['panel']=='heldout' and r['contrast'] in measure.PRIMARY_COMPARATORS]
    for r in effects:r.update(task_gains=1,task_losses=0,query_gains=1,query_losses=0)
    assert report.findings(a,True)['comparators']=='OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    effects[0]['task_losses']=1
    assert report.findings(a,True)['comparators']=='NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    effects[0]['task_losses']=0;effects[0]['query_losses']=2
    assert report.findings(a,True)['comparators']=='NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    tests.append('a comparator tie or negative query net fails strict superiority even when other controls pass')
    tests.append('all raw arrays and graphs reload exactly before both independent audits')
    checked=result['tasks'][0]
    return dict(passed=True,count=len(tests),tests=tests,engineering_only=True,main_outcomes_generated=False,
        schedule_checks=schedule['numerical_checks'],new_numerical_checks=checked['numerical_checks'],
        unchanged_founder_and_prequery_arrays=checked['unchanged_founder_and_prequery_arrays'],fixture_rows=checked['independently_verified_rows'],
        saved_arrays=checked['saved_array_reload_checks'],active_seconds=result['active_seconds'])
