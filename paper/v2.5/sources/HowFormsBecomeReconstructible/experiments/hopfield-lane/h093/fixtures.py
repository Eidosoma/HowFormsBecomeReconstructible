"""Engineering-only boundary, scalar replay, serialization and report fixtures."""
from pathlib import Path
from copy import deepcopy
import json
import numpy as np
from h007.io import save
from h093 import model as m,audit,measure,geometry,report
from h093 import dynamics,reference


def load(path):
    with np.load(path,allow_pickle=False) as f:return {k:f[k] for k in f.files}


def rejects(fn):
    try:fn()
    except (AssertionError,ValueError,KeyError,IndexError):return
    raise AssertionError('forbidden or corrupt input accepted')


def finite_fixtures(tape):
    packet=dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN])
    record=m.compile_record(m.complete(packet),'neural');dynamics.validate(record)
    states=np.stack((tape['birth'][0,0],np.r_[m.X[3],tape['responses_own'][3]],tape['birth'][1,1]))
    assert any(np.any(np.abs(states[:,lo:hi].mean(-1))<1) for lo,hi in reference.RANGES)
    check=audit.old.pair_audit.Audit();h=dynamics.fields(record,states);ref=reference.fields(record,states)
    check.same(h,ref,'direct-product full fields',2e-11)
    original=reference.energy(record,states)
    for site in range(128):
        changed=states.copy();changed[:,site]*=-1
        check.same(reference.energy(record,changed)-original,2*states[:,site]*h[:,site],'finite single-site energy difference',2e-11)
    for i,j in ((80,81),(82,127),(90,111),(110,119),(126,127)):
        changed=states.copy();changed[:,[i,j]]*=-1
        delta=2*states[:,i]*h[:,i]+2*states[:,j]*h[:,j]-4*states[:,i]*states[:,j]*record['J'][i,j]
        check.same(reference.energy(record,changed)-original,delta,'finite response-pair energy difference',2e-11)
    tests=['independent polynomial fields equal all 128 finite coordinate energy differences and selected pair differences, including mixed block means']
    zero=m.copy_record(dict(record=record));zero['interaction_weights'][:]=0
    read_packet=dict(record=zero,birth=tape['birth'][0,0],observed_history=m.X,
        **{'orders_'+p:tape['orders_'+p][0] for p in ('context','gap','query')})
    result=dynamics.read(read_packet);baseline=m.old.neural(dict(read_packet,record={'J':record['J']}))
    for key,value in baseline.items():check.same(result[key],value,'zero interaction regression '+key,2e-11 if value.dtype.kind=='f' else 0)
    tests.append('zero interaction trajectories reproduce every legacy neural read array, with exact decisions and bounded energy rounding')
    rejects(lambda:dynamics.read(dict(read_packet,hidden_target=tape['responses_own'])))
    bad=m.copy_record(dict(record=record));bad['interaction_masks'][0]=16
    rejects(lambda:dynamics.read(dict(read_packet,record=bad)))
    bad=m.copy_record(dict(record=record));bad['interaction_masks'][0]=0;bad['interaction_weights'][0]=1
    rejects(lambda:dynamics.read(dict(read_packet,record=bad)))
    copied=m.copy_record(dict(record=record))
    for key in record:
        check.same(copied[key],record[key],'all record arrays copied')
        assert not np.shares_memory(copied[key],record[key])
    tests.append('strict reader packets reject hidden targets and malformed terms; copying independently owns all inherited arrays')
    return dict(passed=True,checks=check.count,tests=tests)


def run(out,binding):
    out=Path(out);out.mkdir(exist_ok=False);tests=[]
    source=load(binding['source_raw']);baseline_arrays=len(source);old_graph=json.loads(Path(binding['source_graph']).read_text())
    tape={k:source[k].copy() for k in m.tapes('engineering',binding['block'])}
    packet=dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN])
    completion=m.complete(packet);scalar=audit.infer(packet['observed_outputs'])
    for key,value in zip(('masks','signs','outputs'),scalar):np.testing.assert_array_equal(completion[key],value)
    np.testing.assert_array_equal(completion['outputs'],tape['responses_own'])
    rejects(lambda:m.complete(dict(observed_inputs=m.X,observed_outputs=tape['responses_own'])))
    rejects(lambda:m.complete(dict(packet,hidden_rule=tape['rule_masks_own'])))
    rejects(lambda:m.Build(tape))
    tests.append('writers accept only eight actual observations; scalar fitting reproduces identifiable engineering completion; hidden/full-target packets rejected')
    observed,observed_graph=source,old_graph
    numerical=finite_fixtures(tape)
    tests.extend(numerical['tests'])
    raw,graph=m.run_tapes(tape);checked=audit.network(raw,graph,'engineering',binding['block'])
    tests.append('independent scalar completion, exact record projection, ancestry, all native fits and every new neural trajectory pass')
    altered={k:v.copy() for k,v in tape.items()}
    for origin in m.ORIGINS:
        altered['responses_'+origin][m.TEST]*=-1;altered['rule_masks_'+origin][:]=0;altered['rule_signs_'+origin]*=-1
    alternate,alternate_graph=m.run_tapes(altered);assert alternate_graph==graph
    for key in raw:
        if not key.startswith(('responses_','rule_')):np.testing.assert_array_equal(alternate[key],raw[key],err_msg=key)
    tests.append('changing every held-out truth and hidden rule leaves all packets, completions, records and trajectories unchanged')
    check=audit.old.pair_audit.Audit();values,data=audit.metadata(raw,graph,check)
    bad={**raw,'completion_outputs':raw['completion_outputs'].copy()};bad['completion_outputs'][0,0,0]*=-1
    rejects(lambda:audit.record_checks(bad,graph,values,data,audit.old.pair_audit.Audit()))
    bad_graph=deepcopy(graph);node=next(r for r in bad_graph['records'] if r['scope']=='lineage' and r['generation']==2 and r['route']=='rewrite');node['parent_record']=0
    rejects(lambda:audit.metadata(raw,bad_graph,audit.old.pair_audit.Audit()))
    tests.append('corrupt generated response and wrong inherited predecessor are rejected')
    rows={};geo={};diagnostics={};metas={};outputs=[];cases=None;geometry_checks=0
    for condition,r,g in [('pairwise',observed,observed_graph),('interactions',raw,graph)]:
        rows[condition]=measure.network(r,g,binding['block'],condition=='interactions')
        assert rows[condition]==measure.network(r,g,binding['block'],condition=='interactions',True)
        diagnostics[condition],metas[condition],c=geometry.extract(r,g,condition=='interactions')
        geometry_checks+=c['geometry_checks']+geometry.validate(diagnostics[condition],metas[condition])
        geo[condition]=geometry.tables(diagnostics[condition],metas[condition],binding['block']);geometry.verify(diagnostics[condition],metas[condition],geo[condition])
        output,metadata=measure.old.case_outputs(r,g);outputs.append(output)
        if cases is None:cases=metadata
        else:assert cases==metadata
    anchored=measure.anchor(rows['pairwise'],geo['pairwise'],json.loads(Path(binding['source_rows']).read_text()))
    tests.append('all observed baseline tables and geometry anchor exactly to H092; both endpoint geometries independently rebuild')
    bad={**diagnostics['interactions'],'endpoint_energy':diagnostics['interactions']['endpoint_energy'].copy()};bad['endpoint_energy'][0,0,0,0]+=.01
    rejects(lambda:geometry.validate(bad,metas['interactions']))
    tests.append('corrupt completed-record geometry is rejected')
    completion_rows=measure.completion_rows(raw,graph,binding['block']);assert completion_rows==measure.completion_rows(raw,graph,binding['block'],True)
    nearest=[r for r in rows['interactions']['records'] if r['kind']=='nearest_history'];assert all(r['packed_payload_values']==2048 for r in nearest)
    assert len(completion_rows)==234 and all(r['observed_labels']==8 and r['generated_labels']==16 for r in completion_rows)
    tests.append('actual observations, generated responses and changed native storage are counted separately')
    output=np.stack(outputs);repairs=geometry.repair(diagnostics['pairwise'],diagnostics['interactions'],binding['block'])
    assert repairs==geometry.repair(diagnostics['pairwise'],diagnostics['interactions'],binding['block'],True)
    combined=measure.combine(rows,geo,completion_rows,output,cases,tape['responses_own'],binding['block'],repairs)
    assert combined['arm_effects']==measure.arm_effects(output,cases,tape['responses_own'],binding['block'],True)
    neutral=measure.arm_effects(np.repeat(output[:1],2,axis=0),cases,tape['responses_own'],0)
    assert all(all(r[k]==0 for k in ('task_gains','task_losses','query_gains','query_losses','bit_gains','bit_losses')) for r in neutral)
    tests.append('paired condition changes literally recount and identical physical outputs give zero changes')
    flat={'comparison_outputs':output,'comparison_target':tape['responses_own']}
    flat.update({'completed__'+k:v for k,v in raw.items()})
    for condition in m.CONDITIONS:flat.update({condition+'_geometry__'+k:v for k,v in diagnostics[condition].items()})
    with (out/'raw.npz').open('xb') as f:np.savez_compressed(f,**flat)
    reloaded=load(out/'raw.npz');assert reloaded.keys()==flat.keys()
    for key in flat:np.testing.assert_array_equal(reloaded[key],flat[key])
    meta=dict(graphs={'pairwise':observed_graph,'interactions':graph},geometry_metadata=metas,cases=cases)
    save(out/'paths.json',meta);assert json.loads((out/'paths.json').read_text())==meta
    tests.append('all new arrays, comparison evidence and metadata survive exact serialization')
    summary=report.produce(out,[combined],False)
    assert len(summary['primary_comparators'])==10 and all(v=='ENGINEERING_OR_SYNTHETIC_ONLY' for v in summary['findings'].values())
    tests.append('engineering reports keep six findings separate and make no capability claim')
    a={k:deepcopy(summary[k]) for k in measure.KINDS}
    for r in a['patterns']:
        if r['panel']=='heldout':r['full_fixed']=r['patterns']
    for r in a['repair']:r['archived_equal_energy_failed_queries']=r['repaired_failed_queries']=1;r['unrepaired_failed_queries']=0
    report.score(a['cases'],'interactions','heldout',0,'pair')['task_correct']=0
    r=report.findings(a,True);assert r['energy_repair']=='G0_HELDOUT_ENERGY_REPAIR_SCREEN_PASSED' and r['heldout_g0']=='G0_HELDOUT_CAPABILITY_SCREEN_FAILED'
    for panel,g,reader in [('heldout',0,'pair'),('trained',2,'ordinary')]:
        report.score(a['cases'],'interactions',panel,g,reader)['task_correct']=3
        for passive in ('donor','erased'):report.score(a['cases'],'interactions',panel,g,reader,passive)['task_correct']=0
    report.arm(a['arm_effects'],'heldout',0,'pair').update(task_gains=1,task_losses=0)
    report.score(a['cases'],'interactions','heldout')['task_correct']=0
    r=report.findings(a,True);assert r['heldout_g0']=='G0_HELDOUT_CAPABILITY_SCREEN_PASSED' and r['heldout_g2']=='G2_HELDOUT_INHERITANCE_SCREEN_FAILED' and r['trained_g2']=='G2_TRAINED_CAPABILITY_SCREEN_PASSED'
    tests.append('stable targets cannot replace retrieval; G0, G2 and taught capability gates cannot replace one another')
    # The full-copy coefficients are visible in the audit, not only J.
    copied=next(n for n in graph['records'] if n['operation']=='copy')
    damaged={k:v.copy() for k,v in raw.items()};damaged['record_neural_interaction_weights'][copied['index'],0]+=.25
    rejects(lambda:audit.metadata(damaged,graph,audit.old.pair_audit.Audit()))
    tests.append('changing an inherited interaction coefficient breaks actual-parent read alias validation')
    for r in rows['interactions']['records']:
        if r['kind']=='neural':assert r['packed_payload_bytes']==65456 and r['interaction_payload_bytes']==432
    tests.append('mixed mask and coefficient payload bytes counted for every neural record')
    r=next(r for r in a['repair'] if (r['origin'],r['reader'],r['panel'])==('own','pair','heldout'));r['repaired_failed_queries']=0
    assert report.findings(a,True)['energy_repair']=='G0_HELDOUT_ENERGY_REPAIR_SCREEN_FAILED'
    effects=[r for r in a['effects'] if r['condition']=='interactions' and r['panel']=='heldout' and r['contrast'] in measure.PRIMARY_COMPARATORS]
    for r in effects:r.update(task_gains=1,task_losses=0,query_gains=1,query_losses=0)
    assert report.findings(a,True)['comparators']=='OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    effects[0]['task_losses']=1
    assert report.findings(a,True)['comparators']=='NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    effects[0]['task_losses']=0;effects[0]['query_losses']=2
    assert report.findings(a,True)['comparators']=='NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    tests.append('unrepaired archived ties and any failed equal-information comparator each fail their own gate')
    return dict(passed=True,count=len(tests),finite_difference_checks=numerical['checks'],tests=tests,engineering_only=True,main_outcomes_generated=False,
        archived_baseline_arrays=baseline_arrays,new_numerical_checks=checked['numerical_checks'],geometry_checks=geometry_checks,
        baseline_rows_anchored=anchored,fixture_rows=sum(map(len,combined.values())),saved_arrays=len(flat),paired_rows=360)
