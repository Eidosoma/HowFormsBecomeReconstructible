"""Engineering fixtures only; no fresh scientific acquisition or outcome reads."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys
import time
import pytest
import numpy as np

import ff_common as common
from ff_common import C,P,ev,read,ledger,configure,specification,identity
import ff_selection as selection
import ff_analysis as analysis
import ff_audit as audit
import ff_evidence as evidence
import ff_run as runner
import ff_worker as worker
import futures
import probes


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    configure('qualification')
    monkeypatch.setattr(common,'binding',lambda:dict(input_manifest_sha256='fixture',protocol_sha256='fixture',models_sha256=C['models_sha256']))
    for module in (evidence,runner,worker):monkeypatch.setattr(module,'binding',common.binding)
    yield
    configure('qualification')


def row(block,c,founder=0,recipient=0,history=None):
    h=history or P['acquisition']['histories'][0];key=[block,h,founder,recipient]
    rank=hashlib.sha256(json.dumps([P['selection']['namespace'],*key],separators=(',',':')).encode()).hexdigest()
    return dict(key=key,block=block,history=h,founder=founder,recipient=recipient,
        rule=1 if founder%2==0 else -1,current_pass=c,boundary=[0.,0.,0.,0.,0.,float(c),0.,0.,0.,0.,0.],
        selection_hash=rank,packet_sha256='fixture')


def toy_panel():
    rows=[row(0,0,0),row(0,1,1),row(0,1,2),row(1,0,0),row(1,0,1),row(1,1,2)]
    forecasts=[];outcomes=[]
    for i,r in enumerate(rows):
        for g in common.REGIMES:
            forecasts.append(dict(**r,regime=g,probabilities=dict(successor32=.2+.1*(i%4),direct64=.46,pooled32=.47,direct8=.45,tt008=.6)))
            for rep in range(4):outcomes.append(dict(key=r['key'],regime=g,replicate=rep,passed=(i+rep)%2))
    spec=dict(scope='qualification',eligible_blocks=2,repeats=[0,1,2,3])
    return rows,forecasts,outcomes,spec


def test_adapter_changes_only_declared_namespaces():
    before=deepcopy(common.ORIGINAL);changes=configure('scientific');actual=deepcopy(P)
    assert len(changes)==4
    for name in changes:
        section,field=name.split('.')
        assert actual[section][field].startswith(C['namespace']+'/')
        actual[section][field]=before[section][field]
    assert actual==before
    provenance=read(common.ROOT/'NATIVE_PROVENANCE.json')['sha256']
    assert common.manifest(common.NATIVE)==provenance
    assert ev.sha(common.QUALIFIED/'FROZEN_MODELS.json')==C['models_sha256']


def test_seed_pairing_replica_and_namespace_separation():
    key=[-6,P['acquisition']['histories'][0],0,0]
    stage=C['stage']+'/replicate_0'
    m=futures.environment(stage,key,15,'writer','matched')
    i=futures.environment(stage,key,15,'writer','independent')
    assert np.array_equal(m[0],i[0])
    assert np.array_equal(m[1][0],i[1][0]) and np.array_equal(m[1][0],m[1][1])
    assert np.array_equal(m[2][:,0],i[2][:,0]) and np.array_equal(m[2][:,0],m[2][:,1])
    assert not np.array_equal(i[2][:,0],i[2][:,1])
    digest=lambda env:hashlib.sha256(env[2].tobytes()).hexdigest()
    hashes=[digest(i),digest(futures.environment(C['stage']+'/replicate_1',key,15,'writer','independent')),
        digest(futures.environment(stage,key,15,'evaluation','independent')),
        digest(probes.environment(C['stage'],key,15,'writer','independent'))]
    configure('scientific');hashes.append(digest(futures.environment(stage,key,15,'writer','independent')))
    assert len(set(hashes))==5


def test_selection_boundary_only_rule_balance_and_singletons():
    rows=[row(0,0,0),row(0,0,1),row(0,0,2),row(0,1,3)]
    got=selection.select(rows)
    assert len(got)==3 and [r['rule'] for r in got[:2]]==[-1,1]
    assert got[-1]==rows[-1]
    with_unused_predictions=[dict(r,unused_future=(i%2)) for i,r in enumerate(rows)]
    assert [r['key'] for r in selection.select(with_unused_predictions)]==[r['key'] for r in got]
    assert selection.select(list(reversed(rows)))==got


def test_first_eligible_order_surplus_and_ineligible():
    spec=dict(first_block=0,maximum_attempts=16,eligible_blocks=2,wave_size=8)
    attempts={b:[row(b,0,0)]+([] if b in (0,1,5) else [row(b,1,1)]) for b in reversed(range(8))}
    result=selection.cohort(attempts,spec)
    assert result['blocks']==[2,3] and result['surplus_blocks']==[4,6,7]
    assert result['ineligible_blocks']==[0,1,5]
    assert result['attempted_blocks']==list(range(8))


@pytest.mark.parametrize('count',[7,9,24])
def test_partial_wave_or_cap_overrun_rejected(count):
    spec=dict(first_block=0,maximum_attempts=16,eligible_blocks=10,wave_size=8)
    with pytest.raises(ValueError):selection.cohort({b:[row(b,0)] for b in range(count)},spec)


def test_attempt_cap_returns_incomplete_without_replacement():
    spec=dict(first_block=0,maximum_attempts=8,eligible_blocks=2,wave_size=8)
    result=selection.cohort({b:[row(b,0)] for b in range(8)},spec)
    assert not result['complete'] and result['blocks']==[] and result['attempted_blocks']==list(range(8))


def test_extra_wave_after_sufficient_cohort_rejected():
    spec=dict(first_block=0,maximum_attempts=16,eligible_blocks=2,wave_size=8)
    attempts={b:[row(b,0),row(b,1,1)] for b in range(16)}
    with pytest.raises(ValueError,match='beyond'):selection.cohort(attempts,spec)


def test_unequal_classes_repeat_loss_and_independent_scalar_audit():
    rows,f,y,spec=toy_panel();result=analysis.analyze(rows,f,y,spec)
    assert audit.evaluate(rows,f,y,result,spec['repeats'])['status']=='PASS'
    p=[x['probabilities']['successor32'] for x in f if x['regime']=='matched']
    loss=[((x-0)**2+(x-1)**2)/2 for x in p]
    expected=((loss[0]+(loss[1]+loss[2])/2)/2+((loss[3]+loss[4])/2+loss[5])/2)/2
    assert result['regimes']['matched']['brier']['successor32']==pytest.approx(expected,abs=1e-14)
    assert abs(expected-sum(loss)/len(loss))>1e-4
    assert abs(expected-sum((x-.5)**2 for x in p)/len(p))>.2
    for regime in common.REGIMES:
        a=result['regimes'][regime]
        assert sum(a['strata']['current_pass'][str(c)]['weight'] for c in (0,1))==pytest.approx(1)


@pytest.mark.parametrize('defect',['missing','duplicate','extra_repeat','extra_key','missing_forecast','duplicate_forecast','nan','wrong_metadata'])
def test_no_scoring_of_incomplete_or_corrupt_data(defect):
    rows,f,y,spec=toy_panel()
    if defect=='missing':y.pop()
    elif defect=='duplicate':y.append(y[-1])
    elif defect=='extra_repeat':y[-1]=dict(y[-1],replicate=4)
    elif defect=='extra_key':y[-1]=dict(y[-1],key=[99,'wrong',0,0])
    elif defect=='missing_forecast':f.pop()
    elif defect=='duplicate_forecast':f.append(f[-1])
    elif defect=='nan':f[0]['probabilities']['successor32']=float('nan')
    elif defect=='wrong_metadata':f[0]['current_pass']=1-f[0]['current_pass']
    with pytest.raises(ValueError):analysis.analyze(rows,f,y,spec)


def test_joint_decision_requires_all_four_components():
    rows,f,y,spec=toy_panel()
    for v in y:v['passed']=0
    for v in f:v['probabilities']=dict(successor32=.1,direct64=.6,pooled32=.6,direct8=.6,tt008=.7)
    assert analysis.analyze(rows,f,y,spec)['decision']=='ALL_FOUR_EQUAL_READ_ADVANTAGES_SUPPORTED'
    for v in f:
        if v['regime']=='independent':v['probabilities']['direct64']=.1
    result=analysis.analyze(rows,f,y,spec)
    assert result['decision']=='AT_LEAST_ONE_ADVANTAGE_REJECTED'
    assert result['regimes']['independent']['primary']['direct64']['upper']==0.


def test_bin_endpoints_empty_bins_and_diagnostic_mass():
    rows,f,y,spec=toy_panel()
    for i,v in enumerate(f):v['probabilities']={m:float(i%2) for m in common.MODELS}
    result=analysis.analyze(rows,f,y,spec)
    assert audit.evaluate(rows,f,y,result,spec['repeats'])['status']=='PASS'
    for g in common.REGIMES:
        bins=result['regimes'][g]['calibration']['successor32']
        assert sum(b['weight'] for b in bins)==pytest.approx(1.)
        assert all(b['brier'] is None for b in bins if b['weight']==0)
        assert bins[0 if g=='matched' else 9]['weight']==pytest.approx(1.)


class FixtureGuard:
    def check(self):pass
    def account(self):return 0


def make_acquisitions(root,spec):
    refs=[]
    for b in range(spec['first_block'],spec['first_block']+8):
        folder=root/f'units/acquire/b{b}';folder.mkdir(parents=True)
        payload=worker.acquire(folder,dict(spec=spec,block=b),FixtureGuard())
        ledger.atomic_json(folder/'RESOURCES.json',dict(cpu_seconds=0,wall_seconds=0))
        ledger.commit(folder,identity(spec,'acquire',block=b),payload)
        refs.append(ledger.reference(root,folder))
    return refs


def fake_measurements(root,spec,selection_ref,monkeypatch):
    plan=evidence.selection(root,selection_ref,spec);refs=[]
    for b in plan['blocks']:
        folder=root/f'units/measure/b{b}';folder.mkdir(parents=True)
        rows=[r for r in plan['rows'] if r['block']==b]
        f=[dict(**r,regime=g,probabilities=dict(successor32=.3,direct64=.45,pooled32=.42,direct8=.4,tt008=.5)) for r in rows for g in common.REGIMES]
        payload=dict(block=b,forecasts=f,native_reads=len(rows)*256,flat_native_reads=len(rows)*8)
        ledger.atomic_json(folder/'FORECASTS.json',f)
        ledger.atomic_json(folder/'RESOURCES.json',dict(cpu_seconds=0,wall_seconds=0))
        ledger.commit(folder,identity(spec,'measure',block=b),payload);refs.append(ledger.reference(root,folder))
    def verify(root,ref,rows,spec):
        _,entry=ledger.referenced(root,ref,identity(spec,'measure',block=rows[0]['block']))
        return entry['payload']['forecasts']
    monkeypatch.setattr(evidence,'verify_measurement',verify)
    return refs


def test_full_cohort_barrier_and_tampered_seal(tmp_path,monkeypatch):
    spec=specification('qualification');refs=make_acquisitions(tmp_path,spec)
    selected=evidence.seal_selection(tmp_path,refs,spec)
    measurements=fake_measurements(tmp_path,spec,selected,monkeypatch)
    with pytest.raises(ValueError,match='Incomplete forecasts'):
        evidence.seal_forecasts(tmp_path,spec,selected,measurements[:-1])
    assert not (tmp_path/'forecast_seal').exists()
    seal=evidence.seal_forecasts(tmp_path,spec,selected,measurements)
    path,value=evidence.check_seal(tmp_path,seal,spec)
    assert value['blocks']==[-6,-5] and len(value['forecasts'])==14
    path.write_text(path.read_text()+' ')
    with pytest.raises(ValueError,match='unchanged'):evidence.check_seal(tmp_path,seal,spec)


def test_future_cannot_start_without_seal(tmp_path):
    spec=specification('qualification');folder=tmp_path/'future';folder.mkdir()
    task=dict(run=str(tmp_path),spec=spec,block=-6,replicate=0,seal=dict(path='absent.json',sha256='absent',ref={}))
    with pytest.raises(ValueError,match='seal'):worker.future(folder,task,FixtureGuard())
    assert list(folder.iterdir())==[]


def test_committed_evidence_tamper_and_additions_rejected(tmp_path):
    (tmp_path/'data').write_text('original');ledger.commit(tmp_path,{}, {})
    (tmp_path/'extra').write_text('uncommitted')
    with pytest.raises(ValueError,match='coverage'):ledger.verify(tmp_path)
    (tmp_path/'extra').unlink();(tmp_path/'data').write_text('edited')
    with pytest.raises(ValueError,match='changed'):ledger.verify(tmp_path)


def test_timeout_cleans_all_waiting_children(tmp_path):
    ps=[subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],cwd=tmp_path) for _ in range(2)]
    start=time.monotonic()
    with pytest.raises(TimeoutError):runner.await_workers([(str(i),p) for i,p in enumerate(ps)],time.time()+.1)
    assert all(p.poll() is not None for p in ps) and time.monotonic()-start<5


def test_one_worker_failure_stops_peers(tmp_path):
    ps=[subprocess.Popen([sys.executable,'-c',code],cwd=tmp_path) for code in ('raise SystemExit(4)','import time;time.sleep(60)')]
    with pytest.raises(ValueError,match='Worker failed'):runner.await_workers([(str(i),p) for i,p in enumerate(ps)],time.time()+5)
    assert all(p.poll() is not None for p in ps)


def test_deadline_is_enforced():
    with pytest.raises(TimeoutError):common.Guard(Path('.'),time.time()-1).check()


def test_failed_run_is_durable_and_cannot_restart(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'verify_snapshot',lambda:1)
    monkeypatch.setattr(runner,'admission',lambda _:dict(within_limit=False))
    root=tmp_path/'failed'
    with pytest.raises(ValueError,match='budget'):runner.run(root,'qualification')
    assert read(root/'STATUS.json')['status']=='FAILED'
    failure=read(root/'FAILED.json')
    assert failure['inferential_verdict'] is None and not failure['automatic_retry']
    with pytest.raises(FileExistsError):runner.run(root,'qualification')


def test_science_requires_matching_qualification_before_cpu_or_dynamics(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'verify_snapshot',lambda:1)
    monkeypatch.setattr(runner,'admission',lambda _:pytest.fail('CPU admission reached without qualification'))
    root=tmp_path/'unqualified'
    with pytest.raises(ValueError,match='qualified'):runner.run(root,'scientific')
    assert not (root/'units').exists()


def test_completion_manifest_ignores_only_mutable_status(tmp_path,monkeypatch):
    # completed_outputs hashes the input manifest; use a tiny isolated stand-in.
    inputs=tmp_path/'inputs';inputs.mkdir();(inputs/'INPUTS.json').write_text('{}')
    monkeypatch.setattr(common,'ROOT',inputs)
    out=tmp_path/'run';out.mkdir();(out/'data').write_text('sealed')
    common.completed_outputs(out,dict(status='COMPLETE',scope='qualification',decision='fixture'))
    ev.status(out,status='COMPLETE',scope='qualification',decision='fixture',extra_status_only=True)
    assert common.verify_completed(out)['decision']=='fixture'
    (out/'data').write_text('changed')
    with pytest.raises(ValueError):common.verify_completed(out)


def test_pytest_aliases_are_outside_completion_evidence(tmp_path,monkeypatch):
    inputs=tmp_path/'inputs';inputs.mkdir();(inputs/'INPUTS.json').write_text('{}')
    monkeypatch.setattr(common,'ROOT',inputs)
    out=tmp_path/'run';out.mkdir();(out/'tests.xml').write_text('<testsuite tests="1" failures="0"/>')
    workspace=runner.test_workspace(out)
    fixture=workspace/'test_example0';fixture.mkdir();(fixture/'data').write_text('fixture')
    (workspace/'test_examplecurrent').symlink_to(fixture,target_is_directory=True)
    common.completed_outputs(out,dict(status='COMPLETE',scope='qualification',decision='fixture'))
    assert common.verify_completed(out)['decision']=='fixture'
    assert read(out/'TEST_WORKSPACE.json')['path']==str(workspace)
    assert workspace.parent==out.parent and not workspace.is_relative_to(out)
    assert 'tests.xml' in read(out/'OUTPUTS.json')['sha256']
    with pytest.raises(ValueError,match='Symlink'):common.manifest(workspace)
    with pytest.raises(FileExistsError):runner.test_workspace(out)


def test_completion_still_rejects_evidence_symlinks(tmp_path,monkeypatch):
    inputs=tmp_path/'inputs';inputs.mkdir();(inputs/'INPUTS.json').write_text('{}')
    monkeypatch.setattr(common,'ROOT',inputs)
    out=tmp_path/'run';out.mkdir();(out/'data').write_text('evidence')
    (out/'data_alias').symlink_to(out/'data')
    with pytest.raises(ValueError,match='Symlink'):
        common.completed_outputs(out,dict(status='COMPLETE',scope='qualification',decision='fixture'))
    assert not (out/'COMPLETE.json').exists() and not (out/'OUTPUTS.json').exists()


@pytest.mark.parametrize('missing_final',[False,True])
def test_complete_orchestration_fixture_scores_only_after_all_futures(tmp_path,monkeypatch,missing_final):
    """Cheap work products; production control flow and scoring are exercised unchanged."""
    spec=specification('qualification');events=[]
    def submit(tasks):
        kind=tasks[0]['kind'];events.append(kind)
        if kind=='legacy':
            folder=tmp_path/'units/legacy';folder.mkdir(parents=True)
            ledger.atomic_json(folder/'RESOURCES.json',dict(cpu_seconds=0,wall_seconds=0))
            ledger.commit(folder,identity(spec,'legacy'),dict(native_reads=896,flat_native_reads=12))
            return [ledger.reference(tmp_path,folder)]
        if kind=='acquire':
            return list(reversed(make_acquisitions(tmp_path,spec)))  # completion-order trap
        if kind=='measure':
            return fake_measurements(tmp_path,spec,tasks[0]['selection'],monkeypatch)
        assert kind=='future' and events==['legacy','acquire','measure','future']
        seal=tasks[0]['seal'];_,value=evidence.check_seal(tmp_path,seal,spec)
        assert len(value['forecasts'])==14 and len(tasks)==8
        refs=[]
        for task in tasks[:-1] if missing_final else tasks:
            b,rep=task['block'],task['replicate'];rows=[r for r in value['rows'] if r['block']==b]
            folder=tmp_path/task['output'];folder.mkdir(parents=True)
            labels=[dict(key=r['key'],regime=g,replicate=rep,passed=rep%2) for r in rows for g in common.REGIMES]
            payload=dict(block=b,replicate=rep,outcomes=labels,native_reads=len(rows)*38,flat_native_reads=38)
            ledger.atomic_json(folder/'RESOURCES.json',dict(cpu_seconds=0,wall_seconds=0))
            ledger.commit(folder,identity(spec,'future',block=b,replicate=rep,seal_sha256=seal['sha256']),payload)
            refs.append(ledger.reference(tmp_path,folder))
        return refs
    def future_check(root,ref,rows,rep,spec,seal):
        _,value=ledger.referenced(root,ref,identity(spec,'future',block=rows[0]['block'],replicate=rep,seal_sha256=seal['sha256']))
        return value['payload']['outcomes']
    monkeypatch.setattr(evidence,'verify_future',future_check)
    monkeypatch.setattr(runner,'forcing_checks',lambda *_:dict(status='FIXTURE_ONLY'))
    if missing_final:
        with pytest.raises(ValueError,match='Complete future cohort'):runner.pipeline_run(tmp_path,spec,submit,FixtureGuard())
        assert not (tmp_path/'ANALYSIS.json').exists()
    else:
        result=runner.pipeline_run(tmp_path,spec,submit,FixtureGuard())
        assert result['decision']=='RUNNER_QUALIFICATION_PASS' and result['scientific_future_outcomes']==0
        assert result['synthetic_outcomes']==56 and result['selected_packets']==7
        assert result['primary_native_reads']==3752 and result['flat_native_reads']==372
        assert read(tmp_path/'VERIFICATION.json')['status']=='PASS'


def test_acquisition_cap_prevents_measurement_and_inference(tmp_path,monkeypatch):
    spec=specification('scientific');spec.update(first_block=0,maximum_attempts=8,eligible_blocks=2)
    calls=[]
    def submit(tasks):
        calls.append(tasks);return [dict(path=str(i)) for i in range(8)]
    monkeypatch.setattr(evidence,'attempt_rows',lambda *_:{i:[row(i,0)] for i in range(8)})
    chosen,refs=runner.collect_cohort(tmp_path,spec,submit)
    assert chosen is None and len(refs)==8 and len(calls)==1
    assert not (tmp_path/'forecast_seal').exists() and not (tmp_path/'ANALYSIS.json').exists()


@pytest.mark.parametrize('scenario',['insufficient_at_cap','last_wave_completion','first_sufficient_wave'])
def test_full_size_amended_cap_keeps80_eligible_blocks(scenario):
    spec=specification('scientific')
    assert (spec['eligible_blocks'],spec['maximum_attempts'],spec['wave_size'])==(80,136,8)
    count=80 if scenario=='first_sufficient_wave' else 136
    if scenario=='insufficient_at_cap':eligible=set(range(0,136,2))
    elif scenario=='last_wave_completion':eligible=set(range(79))|{129}
    else:eligible=set(range(80))
    attempts={b:[row(b,0,0)]+([row(b,1,1)] if b in eligible else []) for b in range(count)}
    result=selection.cohort(attempts,spec)
    assert result['attempted_blocks']==list(range(count))
    if scenario=='insufficient_at_cap':
        assert not result['complete'] and len(result['blocks'])==68
    else:
        assert result['complete'] and len(result['blocks'])==80
        assert result['blocks']==sorted(eligible)[:80]
        assert result['surplus_blocks']==sorted(eligible)[80:]


def test_budget_amendment_changes_only_declared_resource_fields():
    parent=read(common.ROOT/'context/BEFORE_RESOURCE_AMENDMENT.json')
    amended=deepcopy(C)
    assert amended['cohort']['maximum_attempts']==136 and amended['resources']['hard_wall_seconds']==21600
    assert amended['amendment']['parent_protocol_sha256']==ev.sha(common.ROOT/'context/BEFORE_RESOURCE_AMENDMENT.json')
    amended.pop('amendment')
    for field in ('version','status','planning_limits'):amended[field]=parent[field]
    amended['cohort']['maximum_attempts']=parent['cohort']['maximum_attempts']
    amended['seed_contract']['scientific_ids']=parent['seed_contract']['scientific_ids']
    amended['resource_basis']['full_cap_forecast_seconds']=parent['resource_basis']['full_cap_forecast_seconds']
    assert amended==parent


def test_secondary_failure_is_reported_without_changing_the_primary_claim():
    rows, forecasts, outcomes, spec = toy_panel()
    for outcome in outcomes:
        outcome['passed'] = 0
    for forecast in forecasts:
        forecast['probabilities'] = dict(successor32=.1, direct64=.6, pooled32=.6, direct8=.1, tt008=.1)
    result = analysis.analyze(rows, forecasts, outcomes, spec)
    assert result['decision'] == 'ALL_FOUR_EQUAL_READ_ADVANTAGES_SUPPORTED'
    for regime in common.REGIMES:
        assert set(result['regimes'][regime]['primary']) == {'direct64', 'pooled32'}
        assert all(v['decision'] == 'REJECTED' for v in result['regimes'][regime]['secondary'].values())
    assert audit.evaluate(rows, forecasts, outcomes, result, spec['repeats'])['independent_scalar_contrasts'] == 8


def test_missing_secondary_forecast_keeps_the_global_barrier_closed(tmp_path, monkeypatch):
    spec = specification('qualification')
    selected = evidence.seal_selection(tmp_path, make_acquisitions(tmp_path, spec), spec)
    refs = fake_measurements(tmp_path, spec, selected, monkeypatch)
    original = evidence.verify_measurement
    def missing(*args):
        values = deepcopy(original(*args))
        values[0]['probabilities'].pop('tt008')
        return values
    monkeypatch.setattr(evidence, 'verify_measurement', missing)
    with pytest.raises(ValueError, match='All five'):
        evidence.seal_forecasts(tmp_path, spec, selected, refs)
    assert not (tmp_path / 'forecast_seal').exists()


def test_execution_scopes_keep_separate_declared_worker_budgets(monkeypatch):
    import cpu_preflight
    monkeypatch.setattr(cpu_preflight, 'collect', lambda: dict(other_active_or_recently_busy_threads=7))
    assert common.worker_count('qualification') == 4
    assert common.worker_count('scientific') == 8
    assert common.admission('qualification')['within_limit']
    assert not common.admission('scientific')['within_limit']
    assert common.admission('qualification')['planned_threads'] == 5
    assert common.admission('scientific')['planned_threads'] == 9
