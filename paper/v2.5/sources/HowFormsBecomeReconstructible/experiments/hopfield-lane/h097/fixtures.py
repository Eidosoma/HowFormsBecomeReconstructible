"""Engineering-only checks of constrained optimization, physical copying and separate verdicts."""
from pathlib import Path
from copy import deepcopy
import time
import numpy as np
from h007.io import save
from h093.fixtures import rejects
from h094.fixtures import schedule_fixtures
from h093 import dynamics
from h083.audit import reference_deltas,Audit
from h097 import model as m,compiler as c,audit,measure,report,diagnostics


def solver_checks(out,tape):
    gen=np.random.default_rng(9709701);n=8;p=gen.normal(size=(11,n));target=gen.normal(size=p.shape)
    mask=np.triu(gen.random((n,n))>.5,1);mask|=mask.T
    prior=c.project(gen.normal(size=(n,n)),mask);j,stats=c.solve(p,target,prior,mask)
    edges=list(zip(*np.where(np.triu(mask,1))));basis=np.zeros((len(edges),n,n))
    for k,(i,l) in enumerate(edges):basis[k,i,l]=basis[k,l,i]=1
    design=np.stack([(p@b).ravel() for b in basis],axis=1)
    v=np.linalg.solve(design.T@design/len(p)+2*c.RIDGE*np.eye(len(edges)),design.T@(target-p@prior).ravel()/len(p))
    expected=prior+np.einsum('k,kij->ij',v,basis);np.testing.assert_allclose(j,expected,rtol=0,atol=2e-11)
    direction=c.project(gen.normal(size=(n,n)),mask);probe=prior+.2*direction;eps=1e-6
    loss=lambda x:np.square(p@x-target).sum()/len(p)+c.RIDGE*np.square(x-prior).sum()
    gradient=c.project(p.T@(p@probe-target)/len(p),mask)+c.RIDGE*(probe-prior)
    finite=(loss(probe+eps*direction)-loss(probe-eps*direction))/(2*eps)
    assert abs(finite-2*np.sum(gradient*direction))<1e-7
    completion=m.complete(dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN]))
    full=~np.eye(128,dtype=bool);available=np.ones(48,dtype=bool);ideal=m.compile_record(completion,'neural')
    intact,_=c.constrain(dict(completion=completion,mask=full,available=available,prior_record=None,mode='rewrite'))
    repaired,_=c.constrain(dict(completion=completion,mask=full,available=available,prior_record=ideal,mode='copy_repair'))
    for k in ideal:np.testing.assert_array_equal(ideal[k],intact[k]);np.testing.assert_array_equal(ideal[k],repaired[k])
    lost,loss_info=c.constrain(dict(completion=completion,mask=tape['body_mask'][1],available=tape['body_available'][1],prior_record=None,mode='rewrite'))
    repaired,_=c.constrain(dict(completion=completion,mask=tape['body_mask'][1],available=tape['body_available'][1],prior_record=ideal,mode='copy_repair'))
    for k in lost:np.testing.assert_array_equal(lost[k],repaired[k])
    copied=c.copy(dict(record=ideal,mask=tape['body_mask'][1],available=tape['body_available'][1]))
    copied2=c.copy(dict(record=copied,mask=full,available=available))
    for k in copied:np.testing.assert_array_equal(copied[k],copied2[k])
    assert not lost['J'][~tape['body_mask'][1]].any() and not lost['interaction_weights'][~tape['body_available'][1]].any()
    rejects(lambda:c.constrain(dict(completion=completion,mask=full,available=available,prior_record=None,mode='rewrite',true_labels=tape['responses_own'])))
    check=Audit();factor=audit.shifted_factor(lost['J'],check);state=gen.choice([-1,1],size=(2,128)).astype(np.int8)
    a=reference_deltas(lost['J'],state);b=reference_deltas(lost['J'],state,factor)
    for x,y in zip(a,b):check.same(x,y,'shifted factor versus direct changed energies',2e-11)
    with (out/'solver_raw.npz').open('xb') as f:np.savez_compressed(f,small_result=j,small_reference=expected,lost_J=lost['J'],lost_weights=lost['interaction_weights'],lost_mask=tape['body_mask'][1],state=state,factor=factor)
    return ['symmetric constrained solver agrees with an independent dense edge-basis solve',
        'nonstationary finite-difference derivative verifies the declared objective gradient',
        'intact reconstruction and repair preserve the H093 ideal exactly',
        'identical available priors give identical reconstruction and repair; both obey forbidden coefficients',
        'physical copying cannot restore destroyed values when availability returns',
        'writer rejects a hidden target and shifted-factor pair energies agree with direct energies']


def verdict_checks(summary):
    a={k:deepcopy(summary[k]) for k in measure.KINDS}
    for panel,g,reader in [('heldout',0,'pair'),('heldout',2,'ordinary'),('trained',2,'ordinary')]:
        report.score(a['cases'],'loss',panel,g,reader)['task_correct']=3
        for source in ('donor','erased'):report.score(a['cases'],'loss',panel,g,reader,source)['task_correct']=0
    effects={r['contrast']:r for r in a['effects'] if r['condition']=='loss' and r['panel']=='heldout'}
    for names in report.COMPARATOR_GROUPS.values():
        for name in names:effects[name].update(task_gains=1,task_losses=0,query_gains=1,query_losses=0)
    v=report.findings(a,True);assert v['heldout_g2']=='G2_HELDOUT_CAPABILITY_RETAINED_UNDER_LOSS'
    for group,names in report.COMPARATOR_GROUPS.items():
        for name in names:
            effects[name]['task_losses']=1
            failed=report.findings(a,True)
            assert failed[group].startswith('NO_') and all(not failed[k].startswith('NO_') for k in report.COMPARATOR_GROUPS if k!=group)
            effects[name]['task_losses']=0;effects[name]['query_losses']=2
            assert report.findings(a,True)[group].startswith('NO_');effects[name]['query_losses']=0
    report.score(a['cases'],'loss','heldout')['task_correct']=0
    v=report.findings(a,True);assert v['heldout_g0'].endswith('PASSED') and v['heldout_g2'].endswith('FAILED') and v['trained_g2'].endswith('PASSED')
    report.score(a['cases'],'loss','heldout')['task_correct']=3;report.score(a['cases'],'loss','heldout',0,'pair')['task_correct']=0
    assert report.findings(a,True)['heldout_g2'].endswith('FAILED')
    report.score(a['cases'],'loss','heldout',0,'pair')['task_correct']=3;report.score(a['cases'],'loss','heldout',0,'pair','donor')['task_correct']=3
    assert report.findings(a,True)['heldout_g0'].endswith('FAILED')
    # Perfect stability cannot overrule a failed retrieval score.
    for row in a['stability']:row['full_fixed']=row['patterns']
    assert report.findings(a,True)['heldout_g0'].endswith('FAILED')
    return ['copying, repair and native-comparator verdicts are independent; any task tie or negative query net fails its own gate',
        'initial, inherited unseen and taught capability are separate; donor-source gaps remain required',
        'perfect pattern fixedness cannot replace a failed retrieval score']


def run(out,binding):
    from h097.workflow import batch,load,read
    out=Path(out);out.mkdir(exist_ok=False);tests=[];tick=time.perf_counter()
    tape=load(binding['tape_path']);assert binding['cohort']=='engineering'
    for k,v in m.tapes('engineering',binding['block']).items():np.testing.assert_array_equal(tape[k],v)
    assert m.digest(tape)!=m.digest(m.tapes('fixture',binding['block']))
    tests.extend(solver_checks(out,tape));schedule=schedule_fixtures(tape);tests.extend(schedule['tests'])
    packet=dict(observed_inputs=m.X[m.TRAIN],observed_outputs=tape['responses_own'][m.TRAIN]);completion=m.complete(packet)
    for key,value in zip(('masks','signs','outputs'),audit.infer(packet['observed_outputs'])):np.testing.assert_array_equal(completion[key],value)
    rejects(lambda:m.complete(dict(packet,hidden_rule=tape['rule_masks_own'])))
    rejects(lambda:m.complete(dict(observed_inputs=m.X,observed_outputs=tape['responses_own'])))
    rejects(lambda:m.Build(tape,'loss'))
    tests.append('only eight actual observations enter the writer; full truth and hidden-rule packets are rejected')
    result=batch(out/'matched',[binding],1,lambda **kw:None);stem=f"block_{binding['block']:03d}"
    arrays={condition:load(out/'matched/new_raw'/(stem+'_'+condition+'.npz')) for condition in m.CONDITIONS}
    graphs={condition:read(out/'matched/paths'/(stem+'_'+condition+'.json')) for condition in m.CONDITIONS}
    tests.append('both conditions independently verify full actual ancestry, constrained fits, native fits, physical losses and every retrieval trajectory')
    tests.append('G0 and independent native paths are identical across conditions; all arrays and graphs reload exactly')
    altered={k:v.copy() for k,v in tape.items()}
    for origin in m.ORIGINS:
        altered['responses_'+origin][m.TEST]*=-1;altered['rule_masks_'+origin][:]=0;altered['rule_signs_'+origin]*=-1
    for condition in m.CONDITIONS:
        raw,graph=m.run_tapes(altered,condition)
        with (out/('altered_'+condition+'.npz')).open('xb') as f:np.savez_compressed(f,**raw)
        save(out/('altered_'+condition+'_graph.json'),graph)
        assert graph==graphs[condition]
        for key,value in arrays[condition].items():
            if not key.startswith(('responses_','rule_')):np.testing.assert_array_equal(value,raw[key],err_msg=condition+'/'+key)
    tests.append('changing all unseen targets and hidden rules changes neither condition physics, fits, records nor parent packets')
    raw,graph=arrays['loss'],graphs['loss'];values,data=audit.metadata(raw,graph,Audit())
    corrupt=deepcopy(graph);node=next(r for r in corrupt['records'] if r['scope']=='lineage' and r['generation']==2 and r['route']=='rewrite');node['parent_record']=0
    rejects(lambda:audit.metadata(raw,corrupt,Audit()))
    bad={**raw,'completion_outputs':raw['completion_outputs'].copy()};bad['completion_outputs'][0,0,0]*=-1
    rejects(lambda:audit.record_checks(bad,graph,values,data,Audit()))
    child=next(n for n in graph['records'] if n['generation']==1 and n['route']=='rewrite' and n['kind']=='neural')
    badvalues=deepcopy(values);j=badvalues[child['id']]['J'];i,k=np.argwhere(np.triu(raw['architecture_mask'][1],1))[0];j[i,k]+=.01;j[k,i]+=.01
    rejects(lambda:audit.record_checks(raw,graph,badvalues,data,Audit()))
    badvalues=deepcopy(values);j=badvalues[child['id']]['J'];i,k=np.argwhere(np.triu(~raw['architecture_mask'][1],1))[0];j[i,k]=j[k,i]=.01
    rejects(lambda:audit.record_checks(raw,graph,badvalues,data,Audit()))
    tests.append('audit rejects false ancestry, corrupted completion, an allowed-edge fit error and restored forbidden edges')
    comparison=load(out/'matched/raw'/(stem+'.npz'));metadata=read(out/'matched/paths'/(stem+'.json'));combined=read(out/'matched/blocks'/(stem+'.json'))
    neutral=measure.arm_effects(np.repeat(comparison['comparison_outputs'][:1],2,axis=0),metadata['cases'],tape['responses_own'],binding['block'])
    assert all(all(r[k]==0 for k in ('task_gains','task_losses','query_gains','query_losses','bit_gains','bit_losses')) for r in neutral)
    assert len(combined['completions'])==596 and len(combined['transitions'])==1152 and len(combined['stability'])==1296
    tests.append('both completion and stability tables retained; matched effects recount literally and identical outputs yield zero gains/losses')
    prefix='loss_stability__';bundle={k[len(prefix):]:v.copy() for k,v in comparison.items() if k.startswith(prefix)};bundle['energies'][0,0,0]+=.01
    rejects(lambda:diagnostics.verify(raw,graph,bundle));tests.append('independent actual-matrix geometry rejects a corrupt saved energy without using projector-floor identities')
    (out/'report').mkdir();summary=report.produce(out/'report',[combined],False)
    assert summary['experiment']=='H097' and summary['root_seed']==97097 and len(summary['primary_comparators'])==12
    assert all(v=='ENGINEERING_OR_SYNTHETIC_ONLY' for v in summary['findings'].values())
    tests.extend(verdict_checks(summary));tests.append('engineering reports retain all twelve controls and never emit main findings')
    return dict(passed=True,count=len(tests),tests=tests,engineering_only=True,main_outcomes_generated=False,
        numerical_checks=result['tasks'][0]['numerical_checks'],fixture_rows=result['tasks'][0]['independently_verified_rows'],active_seconds=time.perf_counter()-tick)
