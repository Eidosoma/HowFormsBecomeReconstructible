"""Observation isolation, exact learnability, ancestry and corruption fixtures."""
from copy import deepcopy
from pathlib import Path
import json
import numpy as np
from h007.io import save
from h077.audit import exact_projector
from h083.audit import Audit as Check
from h086 import model as old
from h089 import model as m,audit,measure,report


def rejects(function):
    try:function()
    except (AssertionError,ValueError,KeyError,IndexError):return
    raise AssertionError('corrupt or forbidden input was accepted')


def load(path):
    with np.load(path,allow_pickle=False) as f:return {key:f[key] for key in f.files}


def run(out,archive):
    out=Path(out);out.mkdir(exist_ok=False);tests=[]
    assert set(m.TRAIN).isdisjoint(m.TEST) and sorted(np.r_[m.TRAIN,m.TEST])==list(range(16))
    for indices in (m.TRAIN,m.TEST):
        for values in (indices%4,indices//4):np.testing.assert_array_equal(np.bincount(values,minlength=4),[2]*4)
    assert len(np.unique(m.dictionary(m.X[m.TRAIN]).T,axis=0))==32
    assert len(np.unique(m.dictionary(m.X[:8]).T,axis=0))<32
    tests.append('balanced fixed split identifies all 32 signed parity rules; an unidentifiable split fails this certificate')
    tape=m.tapes('fixture',0);packet=dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN])
    rule=m.write(packet,'parity_erm')
    np.testing.assert_array_equal(rule['masks'],tape['rule_masks_own']);np.testing.assert_array_equal(rule['signs'],tape['rule_signs_own'])
    tests.append('eight permitted observations recover teacher rules without supplying their hidden masks or signs')
    # Exhaustively include every possible corrupted eight-label column, including ties.
    all_columns=1-2*((np.arange(256)[:,None]>>np.arange(8))&1);ties=0
    for column in all_columns:
        y=np.tile(column[:,None],(1,48));fit=m.write(dict(observed_inputs=m.X[m.TRAIN],observed_outputs=y),'parity_erm')
        losses=[sum(int(v)!=int(t) for v,t in zip(m.dictionary(m.X[m.TRAIN])[:,j],column)) for j in range(32)]
        best=losses.index(min(losses));ties+=sum(v==min(losses) for v in losses)>1
        assert (fit['masks']==best//2).all() and (fit['signs']==1-2*(best%2)).all()
    assert ties>0;tests.append('all 256 possible training columns satisfy minimum disagreement and deterministic parity ties')
    raw,graph=m.run_tapes(tape);checked=audit.network(raw,graph,'fixture',0)
    assert checked['propagated_lineages']==64 and checked['independent_networks']==1
    assert checked['copy_invariance'] and checked['all_aliases_verified'] and checked['parity_positive_control_exact']
    tests.append('both actual handoffs, every predecessor, native fit, source alias and unique neural trajectory independently verify')
    altered={k:v.copy() for k,v in tape.items()}
    for origin in m.ORIGINS:
        altered['responses_'+origin][m.TEST]*=-1;altered['rule_masks_'+origin][:]=0;altered['rule_signs_'+origin]*=-1
    assert m.digest(m.physics_inputs(tape))==m.digest(m.physics_inputs(altered))
    other,other_graph=m.run_tapes(altered);assert graph==other_graph
    excluded={k for k in tape if k.startswith(('rule_','responses_'))}
    for key in raw:
        if key not in excluded:np.testing.assert_array_equal(raw[key],other[key],err_msg=key)
    del other
    rejects(lambda:m.Build(tape))
    emitted=raw['responses_own'].copy();emitted[m.TEST]*=-1
    np.testing.assert_array_equal(m.observations(emitted),m.observations(raw['responses_own']))
    tests.append('changing every held-out target and hidden rule leaves all physical records, emitted packets and trajectories identical')
    assert len({m.digest(m.tapes(c,b)) for c,b in [('fixture',0),('fixture',1),('engineering',0)]})==3
    assert m.digest(tape)==m.digest(m.tapes('fixture',0))
    tests.append('fixed tapes replay exactly with distinct cohorts and network streams')
    for extra in ('target','teacher_rule','success','future_birth'):
        rejects(lambda extra=extra:m.write(dict(packet,**{extra:0}),'neural'))
    rejects(lambda:m.write(dict(observed_inputs=m.X,observed_outputs=raw['responses_own']),'neural'))
    tests.append('writers reject all sixteen responses and hidden targets, rule parameters, outcome filters and future states')
    emitted=packet['observed_outputs'].copy();emitted[0,0]*=-1
    assert not np.array_equal(m.write(dict(packet,observed_outputs=emitted),'neural')['J'],m.write(packet,'neural')['J'])
    y=np.tile(packet['observed_outputs'][0],(8,1));patterns=np.concatenate((m.X[m.TRAIN],y),axis=1)
    projection,rank=exact_projector(patterns);assert rank<8;reference=projection.copy();np.fill_diagonal(reference,0)
    np.testing.assert_allclose(m.write(dict(packet,observed_outputs=y),'neural')['J'],reference,rtol=0,atol=4e-14)
    tests.append('actual training errors alter the writer; rank-deficient packets retain a valid exact projection')
    source=load(archive['raw']);source_graph=json.loads(Path(archive['graph']).read_text())
    node=next(r for r in source_graph['reads'] if r['kind']=='neural');g,b=node['generation'],node['birth']
    reader_packet=dict(record=old.get_record(source,source_graph,node['record']),birth=source['birth'][g,b],observed_history=source['inputs'],
        **{'orders_'+phase:source['orders_'+phase][g] for phase in ('context','gap','query')})
    golden=m.neural(reader_packet);expected=old.get_read(source,source_graph,node['id']);matched=0;max_golden_error=0.
    assert set(golden)==set(expected)
    for key,value in golden.items():
        if value.dtype.kind=='f':
            np.testing.assert_allclose(value,expected[key],rtol=0,atol=2e-11,err_msg=key)
            max_golden_error=max(max_golden_error,float(np.max(np.abs(value-expected[key]))))
        else:np.testing.assert_array_equal(value,expected[key],err_msg=key)
        matched+=1
    rejects(lambda:m.neural(dict(reader_packet,target=0)))
    tests.append('unchanged neural update rule reproduces an archived H086 engineering reader within fixed numerical bounds')
    check=Check();values,data=audit.metadata(raw,graph,check)
    references,projectors,_=audit.record_checks(raw,graph,values,data,check)
    for node in graph['reads']:
        if graph['records'][node['record']]['operation']!='erase':continue
        saved=data[node['id']];birth=np.broadcast_to(raw['birth'][node['generation'],node['birth'],80:],(16,48))
        if node['kind']=='neural':
            assert (saved['kick_choice']==-1).all()
            for reader in m.READERS:np.testing.assert_array_equal(saved[reader+'_final'][:,0,80:],birth)
        else:np.testing.assert_array_equal(saved['final'],birth)
    tests.append('whole-record erasure in every representation retains the common birth response, including parity ERM')
    bad=deepcopy(graph);node=next(r for r in bad['records'] if r['scope']=='lineage' and r['generation']==2 and r['route']=='rewrite');node['parent_record']=0
    rejects(lambda:audit.metadata(raw,bad,Check()));tests.append('cross-generation predecessor substitution is rejected')
    bad=deepcopy(graph);next(r for r in bad['cases'] if r['source']=='donor')['record']=0
    rejects(lambda:audit.metadata(raw,bad,Check()));tests.append('source-control record and read-alias substitution is rejected')
    node=next(r for r in graph['records'] if r['operation']=='write')
    bad={**raw,'packet_outputs':raw['packet_outputs'].copy()};bad['packet_outputs'][node['packet_index'],0,0]*=-1
    rejects(lambda:audit.record_checks(bad,graph,values,data,Check()));tests.append('a writer packet differing from actual permitted emissions is rejected')
    altered=deepcopy(values);altered[0]['J'][0,1]+=.01
    rejects(lambda:audit.record_checks(raw,graph,altered,data,Check()))
    node=next(r for r in graph['records'] if r['kind']=='parity_erm');altered=deepcopy(values);altered[node['id']]['masks'][0]^=1
    rejects(lambda:audit.record_checks(raw,graph,altered,data,Check()));tests.append('corrupt neural coefficients and parity masks fail independent reconstruction')
    node=next(r for r in graph['reads'] if r['kind']=='neural');bad=deepcopy(data[node['id']]);bad['pair_trace'][-1,0,0,80]*=-1
    rejects(lambda:audit.trajectory(raw,node,values[node['record']],bad,references[node['record']],projectors[node['record']],Check()))
    tests.append('corrupt descendant trajectory is rejected by extended-precision replay')
    node=next(r for r in graph['reads'] if r['kind']=='linear_ls');bad=deepcopy(data[node['id']]);bad['fields'][0,0]+=.01
    rejects(lambda:audit.native_read(raw,node,values[node['record']],bad,Check()));tests.append('corrupt native read field is independently rejected')
    rows=measure.network(raw,graph,0);row_count=measure.verify(raw,graph,rows)
    tests.append('both panels, success combinations, source scores, paired gains/losses and G2 minus G0 effects literally recount')
    for kind,field in dict(cases='task_correct',effects='task_losses',generalization='trained_task_correct',records='changed_records',trajectories='pair_moves').items():
        bad=deepcopy(rows);bad[kind][0][field]+=1;rejects(lambda:measure.verify(raw,graph,bad))
    tests.append('corrupt scores, losses, generalization categories, record changes and trajectory counts are rejected')
    with (out/'raw.npz').open('xb') as f:np.savez_compressed(f,**raw)
    reloaded=load(out/'raw.npz');assert set(raw)==set(reloaded)
    for key in raw:np.testing.assert_array_equal(raw[key],reloaded[key],err_msg=key)
    save(out/'graph.json',graph);assert json.loads((out/'graph.json').read_text())==graph
    tests.append('all raw arrays and causal metadata survive exact serialization')
    summary=report.produce(out,[rows],False)
    assert all(v=='ENGINEERING_OR_SYNTHETIC_ONLY' for v in summary['findings'].values())
    assert len(summary['primary_comparators'])==10 and not summary['population_qualification']
    tests.append('complete serialized report separates trained capability, held-out capability, inheritance and ten comparators')
    scores=deepcopy(summary['scores']);effects=deepcopy(summary['effects'])
    report.score(scores,'trained',0,reader='pair')['task_correct']=4;report.score(scores,'heldout')['task_correct']=3
    for s in ('donor','erased'):report.score(scores,'heldout',source=s)['task_correct']=0
    for r in effects:r.update(task_gains=0,task_losses=0,query_gains=0,query_losses=0)
    assert report.findings(scores,effects,True)['heldout_capability']=='G2_HELDOUT_CAPABILITY_SCREEN_PASSED'
    report.score(scores,'heldout')['task_correct']=2
    result=report.findings(scores,effects,True)
    assert result['trained_capability']=='G0_TRAINED_CAPABILITY_SCREEN_PASSED' and result['heldout_capability']=='G2_HELDOUT_CAPABILITY_SCREEN_FAILED'
    lookup={(r['panel'],r['contrast']):r for r in effects}
    for k in measure.PRIMARY_COMPARATORS:lookup['heldout',k]['task_gains']=1
    assert report.findings(scores,effects,True)['comparators']=='POSITIVE_G2_HELDOUT_TASK_DIFFERENCE_AGAINST_EVERY_FIXED_COMPARATOR'
    lookup['heldout',measure.PRIMARY_COMPARATORS[-1]]['query_losses']=1
    assert report.findings(scores,effects,True)['comparators']=='NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'
    tests.append('trained success cannot substitute for held-out capability and one comparator failure defeats the joint label')
    return dict(passed=True,count=len(tests),tests=tests,synthetic_numerical_checks=checked['numerical_checks'],
        independently_verified_fixture_rows=row_count,archived_reader_arrays=matched,max_archived_reader_error=max_golden_error,
        saved_array_reload_checks=len(raw),unique_fixture_neural_reads=checked['unique_neural_reads'],synthetic_only=True,
        complete_report_fixture=True,fresh_pilot_outcomes_generated=False,heldout_isolation_exact=True,exhaustive_corrupted_columns=256)
