"""Information-boundary, ancestry, serialization and independent-verdict fixtures."""
from copy import deepcopy
import numpy as np
from h007.io import save
from h083.audit import Audit
from h093.fixtures import rejects
from h099.engineering import information_checks
from h100 import model as m,audit,measure,report


def gate_checks(tables,calibration):
    base={k:deepcopy(tables[k]) for k in report.KEYS}
    for g,panel in ((0,'heldout'),(2,'heldout'),(2,'trained')):
        report.score(base['cases'],g,panel)['task_correct']=3
        for source in ('donor','erased'):report.score(base['cases'],g,panel,source)['task_correct']=0
    for r in base['effects']:r.update(task_gains=1,task_losses=0,query_gains=1,query_losses=0)
    good=[calibration];assert all(report.decisions(base,good).values())
    tests=[]
    broken=[dict(calibration,calibration_recovery_passed=False)]
    v=report.decisions(base,broken);assert not v['calibration_recovery'] and all(v[k] for k in v if k!='calibration_recovery')
    tests.append('calibration recovery cannot be replaced by successful task scores')
    for g,panel,failed in ((0,'heldout',{'heldout_g0','heldout_g2'}),(2,'heldout',{'heldout_g2'}),(2,'trained',{'trained_g2'})):
        altered=deepcopy(base);report.score(altered['cases'],g,panel)['task_correct']=2
        v=report.decisions(altered,good);assert {k for k in v if not v[k]}==failed
    tests.append('acquisition, unseen inheritance and taught retention have separate capability gates')
    for source in ('donor','erased'):
        altered=deepcopy(base);report.score(altered['cases'],2,'heldout',source)['task_correct']=3
        assert not report.decisions(altered,good)['heldout_g2']
    tests.append('both donor and erased source gaps are necessary for retention')
    groups=('reference_observations','observation_limited_copy','adaptive_copy','native_controls')
    for group in groups:
        for tied in (True,False):
            altered=deepcopy(base);row=next(r for r in altered['effects'] if r['group']==group and r['panel']=='heldout' and ('g2' in r['contrast'] if group=='reference_observations' else True))
            row.update(task_losses=1 if tied else 0,query_losses=0 if tied else 2)
            v=report.decisions(altered,good);assert {k for k in v if not v[k]}=={group}
    tests.append('ties and negative query nets independently fail each observation/comparator benefit gate')
    altered=deepcopy(base)
    for r in altered['effects']:
        if r['group'] in ('adaptive_copy','native_controls'):r.update(task_gains=0,task_losses=0,query_gains=0,query_losses=0)
    v=report.decisions(altered,good)
    assert v['reference_observations'] and v['observation_limited_copy'] and not v['adaptive_copy'] and not v['native_controls']
    tests.append('additional-information benefit survives as a separate verdict when every equally informed control ties')
    return tests


def local_checks(out,raw,graph,tape):
    out.mkdir(parents=True,exist_ok=False);polarity=tape['calibration_polarity']
    information=information_checks(m.core_tape(tape,'canonical'),polarity,out/'information.npz')
    tests=list(information['tests']);bank=m.calibration_bank(polarity);checked=audit.decoded_bank(bank,polarity)
    for key,index in (('signs',(2,2,0,0)),('known',(2,2,0,0)),('erased_signs',(2,2,0,0)),('measured_responses',(2,0,0,0))):
        bad={k:v.copy() for k,v in bank.items()}
        if key=='erased_signs':bad[key][index]=1
        elif key=='known':bad[key][index]=False
        else:bad[key][index]*=-1
        rejects(lambda:audit.decoded_bank(bad,polarity))
    tests.append('changed reference, decoder, coverage and surviving erased signs are rejected')
    bundle=measure.acquire_outputs(raw,graph,bank);assert measure.verify_bundle(bundle,raw,graph,bank)==5040
    bad={k:v.copy() for k,v in bundle.items()};bad['decoded_outputs'][2,0,0,0]*=-1
    rejects(lambda:measure.verify_bundle(bad,raw,graph,bank))
    tests.append('decoded outputs are independently reconstructed from saved physical reads and corrupted values rejected')
    tables=measure.network(bundle,graph,tape['responses_own'],0)
    assert tables==measure.network(bundle,graph,tape['responses_own'],0,True)
    assert [len(tables[k]) for k in ('cases','effects','ledger')]==[4320,40,1056]
    tests.append('all scores and contrasts agree with literal recounts; calibration ledger excludes panel and reader duplication')
    yes=np.ones((8,48),dtype=np.int8);known=np.ones_like(yes,dtype=bool)
    unresolved=measure.flags(yes,yes,~known);assert not unresolved['task'] and not unresolved['query'].any()
    zero=measure.paired(unresolved,unresolved);assert all(v==0 for v in zero.values())
    tests.append('unresolved coverage blocks semantic task credit and identical outcomes yield zero paired benefit')
    (out/'report').mkdir();summary=report.produce(out/'report',[tables],[checked],False)
    assert summary['diagnostic_rows']==5416 and all(v=='ENGINEERING_OR_SYNTHETIC_ONLY' for v in summary['findings'].values())
    tests.append('serialized engineering reports cannot create confirmation verdicts')
    tests+=gate_checks(summary,checked)
    values,data=audit.metadata(raw,graph,Audit())
    corrupt=deepcopy(graph);node=next(r for r in corrupt['records'] if r['scope']=='lineage' and r['generation']==2 and r['route']=='rewrite');node['parent_record']=0
    rejects(lambda:audit.metadata(raw,corrupt,Audit()))
    bad={**raw,'packet_outputs':raw['packet_outputs'].copy()};node=next(r for r in graph['records'] if r['operation']=='write');bad['packet_outputs'][node['packet_index'],0,0]*=-1
    rejects(lambda:audit.record_checks(bad,graph,values,data,Audit()))
    tests.append('false parent ancestry and a substituted actual-parent packet are rejected')
    # Identity transport exercises the entire graph without acquiring a new network.
    identity=np.ones(48,dtype=np.int8);transported=audit.transport_graph(raw,graph,raw,graph,identity)
    bad={**raw,'read_neural_ordinary_final':raw['read_neural_ordinary_final'].copy()};bad['read_neural_ordinary_final'][0,0,0,80]*=-1
    rejects(lambda:audit.transport_graph(raw,graph,bad,graph,identity))
    tests.append('transport covers every logical read and rejects a single changed discrete response')
    result=dict(passed=True,count=len(tests),tests=tests,engineering_only=True,main_outcomes_generated=False,
        fixture_rows=5416,calibration_checks=checked['checks'],identity_transport_checks=transported['checks'])
    save(out/'result.json',result);return result


def run(out,binding):
    from h100.workflow import batch,load,read
    out.mkdir(parents=True,exist_ok=False)
    result=batch(out/'matched',[binding],1,lambda **kw:None);block=binding['block'];stem=f'block_{block:03d}'
    tape=load(binding['tape_path']);arrays={s:load(out/'matched/new_raw'/(stem+'_'+s+'.npz')) for s in m.SPACES}
    graphs={s:read(out/'matched/paths'/(stem+'_'+s+'.json')) for s in m.SPACES}
    checks=local_checks(out/'checks',arrays['physical'],graphs['physical'],tape)
    altered={k:v.copy() for k,v in tape.items()}
    for origin in m.ORIGINS:
        altered['responses_'+origin][m.TEST]*=-1;altered['rule_masks_'+origin][:]=0;altered['rule_signs_'+origin]*=-1
    for space in m.SPACES:
        raw,graph=m.run_tapes(m.core_tape(altered,space))
        with (out/('altered_'+space+'.npz')).open('xb') as f:np.savez_compressed(f,**raw)
        save(out/('altered_'+space+'.json'),graph);assert graph==graphs[space]
        for key,value in arrays[space].items():
            if not key.startswith(('responses_','rule_')):np.testing.assert_array_equal(raw[key],value,err_msg=space+'/'+key)
    checks['tests']+=['fresh engineering physics passes unchanged extended-precision audits in both coordinate systems',
        'changing every unseen label and hidden rule leaves both acquisitions and all inherited records unchanged']
    checks.update(count=len(checks['tests']),new_numerical_checks=result['tasks'][0]['numerical_checks'],active_seconds=result['active_seconds'])
    save(out/'result.json',checks);return checks
