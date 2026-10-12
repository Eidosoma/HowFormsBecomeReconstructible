"""Complete synthetic P23 readouts plus provenance, observation and fault tests.

Synthetic ODE trajectories exercise software, not scientific predictions.
Native setup, output arrays, gating, clock traces and independent audits run.
"""
from contextlib import contextmanager,redirect_stdout
import copy
import io
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
import p23_design as d
import run_p23 as r
import analyze_p23 as a
import supervise_p23 as s

def fixture_root():
    value=os.environ.get('P23_TEST_ROOT')
    if not value: raise RuntimeError('Full P23 fixtures require external P23_TEST_ROOT')
    root=Path(value).resolve()
    if not root.is_relative_to(d.BASE): raise RuntimeError('P23 fixtures outside dedicated external store')
    return root

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.RateExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs): current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy(); reference=d.replay(c)
        if reference and failure is None:
            src=run/'inputs'/reference['source']; archived=a.arrays(src,name)
            np.testing.assert_array_equal(initial,archived['initial']); np.copyto(sim.cc_cells,archived['final'])
            meta=next(x['clock'] for x in d.read(src/'result.json')['phases'] if x['phase']==name)
            return archived['times'],archived['concentrations'],{k:archived[k] for k in
                ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        def mark(indices,label,value=None):
            state=sim.cc_cells if value is None else value
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(state,i)
        if name=='contact':
            positive=(c['condition']=='early_pause' and c['readout']=='open' and failure not in ('negative','late_recovery')) or failure=='positive'
            if positive: mark(range(3,6),'E')
        if failure=='late_recovery' and name.startswith('isolated'): mark(range(3),'E')
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.000001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=[]; tick=0; proposed_step=2*stride
        while tick<total:
            step=min(cap,proposed_step,min(((tick//stride)+1)*stride,total)-tick,total-tick); steps.append(step); tick+=step
        steps=np.asarray(steps,dtype=np.int64); proposed=np.full(len(steps),proposed_step,dtype=np.int64)
        shots=np.asarray(list(range(0,total,stride))+[total],dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        if failure=='late' and name=='isolated_1':
            for at in range(-2,-32,-1): mark([0],'M',values[at])
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,iterations=len(steps),
            sample_count=len(shots),capped_steps=int(np.count_nonzero(steps<proposed)),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock),d.recovery.external_phases():
        out,provenance=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out,provenance); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestP23Operations(unittest.TestCase):
    def test_independent_registration_and_fixed_counts(self):
        cases=d.fixed_cases(); self.assertEqual(cases,a.expected_cases()); self.assertEqual(len(cases),48)
        self.assertEqual(len({c['id'] for c in cases}),48); self.assertEqual(sum(c['fine'] for c in cases),24)
        self.assertEqual([len(d.stage_cases(x)) for x in d.STAGES],[12,36])
        self.assertEqual(len({d.source(c) for c in cases}),16)
        for c in cases:
            self.assertEqual(d.parent(c),a.parent(c)); self.assertEqual(d.source(c),a.source(c))
            self.assertEqual(d.pupils(c),a.pupils(c)); self.assertEqual(d.replay(c),a.replay(c))
        self.assertEqual(d.read(d.HERE/'config.json'),d.FIXED)

    def test_changed_configuration_rejected(self):
        value=copy.deepcopy(d.FIXED); value['repeated_pause']=True
        with self.assertRaises(ValueError): d.validate_config(value)
        with self.assertRaises(ValueError): d.stage_cases('renewal')

    def test_inherited_evidence_and_unchanged_legacy_globs(self):
        evidence=d.inherited_verification(); self.assertEqual(evidence['p22']['tests'],55)
        self.assertEqual(evidence['legacy'],d.prior.inherited_verification())
        self.assertEqual(len(d.manifest()),225); self.assertEqual(len(d.input_paths()),18916); d.source_check()
        self.assertEqual(d.recovery.prior_supervisor.verification_manifest(),d.read(d.recovery.OLD_JOB/'launch.json')['verification_hashes_sha256'])

    def test_all_parent_states_and_clocks_come_from_registered_P22_sources(self):
        for c in d.fixed_cases():
            old=d.read(d.P22_RUN/d.source(c)/'result.json')
            self.assertEqual(old['case'],a.parent(c)); self.assertEqual(old['outcome']['logical_end'],1201800)
            self.assertEqual(old['phases'][-1]['setup']['cell_ids'],a.donor_ids(c))
            self.assertEqual(old['outcome']['retained_E'],c['condition'] in ('reference','early_pause'))
            self.assertFalse(set(d.pupils(c))&set(old['phases'][-1]['setup']['cell_ids']+old['outcome']['original_ids']))

    def test_fresh_recipients_are_not_prepared_or_draw_perturbed(self):
        for fine in (False,True):
            _,M=r.p22.stock(d.P22_RUN,fine)
            self.assertEqual(M.shape,(17,1)); self.assertEqual(''.join(a.labels(M,a.INDEX)),'M')
        self.assertFalse(d.FIXED['new_renewal_trajectories']); self.assertFalse(d.FIXED['parent_states_edited'])

    def test_fixture_path_confinement(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'require external'): fixture_root()
        with patch.dict(os.environ,{'P23_TEST_ROOT':'/tmp'}):
            with self.assertRaisesRegex(RuntimeError,'outside dedicated'): fixture_root()

    def test_disk_and_budget_stop_before_case_creation(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,patch.object(d,'space_available',return_value=False):
            self.assertEqual(r.run_worker(d.case(),Path(tmp),time.monotonic()+100,{})['status'],'not_launched_disk')
            self.assertEqual(r.run_worker(d.case(),Path(tmp),time.monotonic()-1,{})['status'],'not_launched_budget')
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_external_reserve_is_exactly_five_GiB(self):
        disk=type('Disk',(),{'free':5*1024**3})(); path=Path('/mnt/workspaces/output')
        with patch.object(d.shutil,'disk_usage',return_value=disk) as call:
            self.assertTrue(d.space_available(path)); call.assert_called_once_with(path)
        disk.free-=1
        with patch.object(d.shutil,'disk_usage',return_value=disk): self.assertFalse(d.space_available(path))

    def test_output_confinement(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            job=Path(tmp); (job/'runner.log').write_text('Run artifacts: /tmp/unregistered\n')
            with self.assertRaises(ValueError): s.discover_run(job)
            with self.assertRaises(ValueError): d.check_run_path(job)

    def test_queue_stops_after_observed_failure(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,patch.object(r,'run_worker',side_effect=lambda c,*args:dict(id=c['id'],execution_pass=False)) as called:
            summary={'cases':[]}; self.assertFalse(r.execute_stage(d.stage_cases('controls'),Path(tmp),summary,time.monotonic()+10,{}))
            self.assertEqual(called.call_count,2)

    @contextmanager
    def job(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            job=Path(tmp); d.write_json(job/'status.json',dict(phase='launching'))
            (job/'verification.log').write_text('Ran 1 tests in 0.001s\n\nOK\n'); yield job

    def supervise(self,job,returns,error=None):
        with patch.object(s.signal,'signal'),patch.object(d,'verify_launch',side_effect=error),patch.object(d,'space_available',return_value=True),\
             patch.object(s,'discover_run',return_value=None),patch.object(s,'run_child',side_effect=returns) as child:
            fd=os.open(job/'lock',os.O_CREAT|os.O_RDWR,0o600); code=s.supervise(job,fd)
        return code,child.call_count,d.read(job/'status.json')

    def test_verification_failure_blocks_science(self):
        with self.job() as job:
            code,calls,status=self.supervise(job,[1]); self.assertEqual((code,calls),(1,1)); self.assertEqual(status['phase'],'failed')

    def test_incomplete_verification_log_blocks_science(self):
        with self.job() as job:
            (job/'verification.log').write_text('incomplete')
            code,calls,status=self.supervise(job,[0]); self.assertEqual((code,calls),(1,1)); self.assertIn('verification evidence',status['error'])

    def test_runner_failure_no_retry(self):
        with self.job() as job:
            code,calls,status=self.supervise(job,[0,124]); self.assertEqual((code,calls),(1,2)); self.assertIn('no retry',status['error'])

    def test_source_change_blocks_all_children(self):
        with self.job() as job:
            code,calls,status=self.supervise(job,[],RuntimeError('source changed')); self.assertEqual((code,calls),(1,0))

    def test_timeout_terminates_owned_group(self):
        with self.job() as job,patch.object(s,'child_env',return_value={}),patch.object(s.subprocess,'Popen') as popen,patch.object(s,'terminate_owned') as stop:
            proc=popen.return_value; proc.poll.return_value=None; proc.pid=42
            self.assertEqual(s.run_child(['fixture'],job,'child.log',0,lambda pid:None),124); stop.assert_called_once_with(proc)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])

class TestP23Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p23-software-',dir=fixture_root()); cls.addClassCleanup(cls.temp.cleanup)
        cls.job=Path(cls.temp.name)/'job'; cls.job.mkdir(); hashes=d.freeze(cls.job)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); d.archive_view(cls.fixture_run)
        (cls.fixture_run/'frozen').symlink_to(cls.job/'frozen',target_is_directory=True)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_byte_identical=True,prior_checks=219181,prior_cases=544,prior_calls=2944,
            original_reaudit_count=1,archive_separate_mathematical_reaudit=False,reference_is_independent_backup=False,original_audit_file_rewritten=False)
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],hashes_sha256=hashes,
            inputs=d.input_manifest(),inherited_verification=d.inherited_verification(),predecessor_gate=True,predecessor_audit=cls.history,
            predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        cls.integrity=d.integrity(cls.fixture_run,cls.summary)
        if not all(cls.integrity.values()): raise AssertionError(cls.integrity)
        with redirect_stdout(io.StringIO()),patch.object(d,'integrity',return_value=cls.integrity):
            for stage in d.STAGES:
                for c in d.stage_cases(stage): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary); gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate); cls.summary['gates'][stage]=gate
                cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
            cls.summary.update(stage='finished',all_execution_valid=True,completion_reason='all_registered_stages_completed')
            d.write_json(cls.fixture_run/'summary.json',cls.summary)
            with patch.object(a,'predecessor_audit',return_value=cls.history): cls.report=a.analyze(cls.fixture_run)
        cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}; cls.primary=d.case()
        cls.inherited=d.read(d.P22_RUN/'independent_audit.json')

    def audit_branch(self,run,c):
        checks=a.Checks(); result,data=a.branch(run/c['id'],c,checks); return checks,result,data

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p23-unit-',dir=fixture_root()) as tmp:
            run=Path(tmp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True); yield run

    @contextmanager
    def copied_case(self,c=None):
        c=c or self.primary
        with self.isolated_run() as run:
            folder=run/c['id']; shutil.copytree(self.fixture_run/c['id'],folder); yield run,folder

    def corrupt_result(self,change,c=None):
        c=c or self.primary
        with self.copied_case(c) as (run,folder):
            result=d.read(folder/'result.json'); change(result); d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def corrupt_array(self,name,change,c=None):
        c=c or self.primary
        with self.copied_case(c) as (run,folder):
            data=a.arrays(folder,name); change(data); np.savez_compressed(folder/(name+'.npz'),**data)
            result=d.read(folder/'result.json'); next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def test_complete_panel_and_all_numerical_pairs(self):
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['completed_cases'],48)
        self.assertEqual(self.report['integration_calls'],144); self.assertEqual(len(self.report['fine_comparisons']),24)
        self.assertTrue(self.report['all_fine_agree']); self.assertTrue(self.report['early_pause_specific_both_histories'])
        self.assertEqual([self.summary['gates'][s]['integration_calls'] for s in d.STAGES],[36,144])

    def test_every_parent_has_every_readout_and_exact_live_donors(self):
        sources={}
        for c in d.fixed_cases():
            sources.setdefault(d.source(c),set()).add(c['readout']); folder=self.fixture_run/c['id']
            data=a.arrays(folder,'contact'); source=self.fixture_run/'inputs/p22'/d.source(c)
            np.testing.assert_array_equal(data['initial'][:,:3],a.arrays(source,'isolated_2')['final'])
            _,M=r.stock(self.fixture_run,c['fine']); np.testing.assert_array_equal(data['initial'][:,3:],np.repeat(M,3,axis=1))
            self.assertFalse((folder/'assembly').exists())
        self.assertEqual(len(sources),16); self.assertTrue(all(q=={'open','rna','cut'} for q in sources.values()))

    def test_actual_recipients_retained_after_donors_removed(self):
        for c in d.fixed_cases():
            folder=self.fixture_run/c['id']; contact=a.arrays(folder,'contact'); one=a.arrays(folder,'isolated_1'); two=a.arrays(folder,'isolated_2')
            np.testing.assert_array_equal(contact['final'][:,3:],one['initial']); np.testing.assert_array_equal(one['final'],two['initial'])
            self.assertEqual(one['final'].shape,(17,3)); record=d.read(folder/'result.json')
            self.assertEqual(record['phases'][1]['setup']['cell_ids'],d.pupils(c))

    def test_all_phase_intervals_and_no_repeated_pause(self):
        for c in d.fixed_cases():
            result=d.read(self.fixture_run/c['id']/'result.json')
            self.assertEqual([x['phase'] for x in result['phases']],['contact','isolated_1','isolated_2'])
            self.assertEqual([x['logical_interval'] for x in result['phases']],[[1201800,1221800],[1221800,1231800],[1231800,1241800]])
            self.assertFalse(result['repeated_pause']); self.assertFalse(result['parent_states_edited'])
            self.assertEqual(result['outcome']['logical_end'],1241800)

    def test_reference_replays_all_33_numeric_arrays_each_phase(self):
        count=0
        for c in d.stage_cases('controls'):
            checks,_,data=self.audit_branch(self.fixture_run,c); count+=len(data)
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),99); self.assertTrue(all(replay))
        self.assertEqual(count,36)

    def test_wrong_donor_state_rejected_even_when_hash_updated(self):
        self.corrupt_array('contact',lambda x:x['initial'].__setitem__((5,0),x['initial'][5,0]+1))

    def test_wrong_fresh_recipient_state_rejected(self):
        self.corrupt_array('contact',lambda x:x['initial'].__setitem__((7,3),x['initial'][7,3]*1.1))

    def test_donor_state_substituted_for_recipient_hold_rejected(self):
        with self.copied_case() as (run,folder):
            donor=a.arrays(folder,'contact')['final'][:,:3]
            data=a.arrays(folder,'isolated_1'); data['initial']=donor; np.savez_compressed(folder/'isolated_1.npz',**data)
            result=d.read(folder/'result.json'); result['phases'][1]['sha256']=d.digest(folder/'isolated_1.npz'); d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_changed_parent_hash_and_parent_id_rejected(self):
        self.corrupt_result(lambda x:x['provenance'].update(parent_result_sha256='0'*64))
        self.corrupt_result(lambda x:x['provenance'].update(actual_parent='p22/'+d.source(d.case(condition='baseline'))))

    def test_wrong_parent_clock_or_identity_rejected(self):
        with self.copied_case() as (run,folder):
            (run/'inputs').unlink(); (run/'inputs/p22').mkdir(parents=True)
            for p in (self.fixture_run/'inputs/p22').iterdir(): (run/'inputs/p22'/p.name).symlink_to(p,target_is_directory=p.is_dir())
            par=run/'inputs/p22'/d.source(self.primary); par.unlink(); shutil.copytree(d.P22_RUN/d.source(self.primary),par)
            old=d.read(par/'result.json'); old['phases'][-1]['logical_interval'][1]-=1; d.write_json(par/'result.json',old)
            result=d.read(folder/'result.json'); result['provenance']['parent_result_sha256']=d.digest(par/'result.json'); d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_reused_or_missing_cell_identity_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(3,x['phases'][0]['setup']['cell_ids'][0]))
        self.corrupt_result(lambda x:x['phases'][1]['setup']['cell_ids'].__setitem__(0,a.donor_ids(self.primary)[0]))

    def test_wrong_logical_epoch_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['logical_interval'].__setitem__(0,0))

    def test_unregistered_partial_contact_and_clock_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0].update(requested_horizon=100))
        self.corrupt_array('contact',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_hidden_transport_route_change_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup'].update(mirna_kd=1.25e-14),d.case(readout='rna'))
        self.corrupt_array('contact',lambda x:x['junction_diffusion'].__setitem__((5,0),1e-18))

    def test_claim_of_repeated_pause_or_reset_rejected(self):
        self.corrupt_result(lambda x:x.update(repeated_pause=True))
        self.corrupt_result(lambda x:x.update(parent_states_edited=True))

    def test_extra_phase_or_assembly_rejected(self):
        with self.copied_case() as (run,folder):
            shutil.copyfile(folder/'isolated_2.npz',folder/'preparation.npz'); checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))
        with self.copied_case() as (run,folder):
            (folder/'assembly').mkdir(); checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_saved_outcome_mutation_rejected(self):
        self.corrupt_result(lambda x:x['outcome'].update(transmitted_E=False))

    def test_numerical_disagreement_rejected(self):
        by=copy.deepcopy(self.by); c=d.case(fine=True); by[c['id']]['transmitted_E']=False
        cases=[self.primary,c]; checks=a.Checks(); data={x['id']:{'isolated_2':a.arrays(self.fixture_run/x['id'],'isolated_2')} for x in cases}
        self.assertFalse(a.p19.p18.p12.compare_fine(cases,by,data,checks)[0]['agree'])

    def test_negative_early_pause_result_is_technically_valid(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            row=fixture_case(run,self.primary,'negative'); self.assertFalse(row['result']['outcome']['transmitted_E'])
            checks,_,_=self.audit_branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_positive_nonretaining_parent_is_technically_valid(self):
        c=d.case(condition='baseline')
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            row=fixture_case(run,c,'positive'); out=row['result']['outcome']
            self.assertTrue(out['transmitted_E']); self.assertFalse(out['parent_retained_E'])
            checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values()))

    def test_positive_matched_parent_withholds_pause_specificity(self):
        for condition in ('baseline','full_block'):
            by=copy.deepcopy(self.by)
            for f in (False,True): by[d.case(condition=condition,fine=f)['id']]['transmitted_E']=True
            row=a.contrasts(by,self.inherited,True)['early_pause_comparisons'][0]
            self.assertTrue(row['qualified_chain']); self.assertFalse(row['early_pause_specific_chain'])

    def test_positive_RNA_or_cut_readout_disqualifies_chain(self):
        for route in ('rna','cut'):
            by=copy.deepcopy(self.by)
            for f in (False,True): by[d.case(readout=route,fine=f)['id']]['transmitted_E']=True
            self.assertFalse(a.contrasts(by,self.inherited,True)['early_pause_comparisons'][0]['qualified_chain'])

    def test_inherited_capacity_wipe_and_reference_are_required(self):
        for key in ('inherited_readout_capacity_qualified','inherited_wipe_qualified'):
            inherited=copy.deepcopy(self.inherited); inherited[key]=False
            self.assertFalse(any(x['qualified_chain'] for x in a.contrasts(self.by,inherited,True)['readout_grid']))
        self.assertFalse(any(x['qualified_chain'] for x in a.contrasts(self.by,self.inherited,False)['readout_grid']))

    def test_reference_disagreement_stops_qualification(self):
        by=copy.deepcopy(self.by); by[d.case(condition='reference')['id']]['transmitted_E']=False
        self.assertFalse(all(x['qualified'] for x in a.reference_controls(by)))

    def test_late_endpoint_alone_is_insufficient(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            row=fixture_case(run,self.primary,'late'); out=row['result']['outcome']
            self.assertEqual(out['observations']['isolated_1']['patch_labels'],'EEE'); self.assertFalse(out['transmitted_E'])
            checks,_,_=self.audit_branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_contact_stability_is_reported_separately_from_hold_retention(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            row=fixture_case(run,self.primary,'late_recovery'); out=row['result']['outcome']
            self.assertFalse(out['contact_stable_E']); self.assertTrue(out['transmitted_E'])
            checks,_,_=self.audit_branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_worker_stage_and_preflight_rejected_before_integration(self):
        with self.copied_case() as (run,folder),patch.object(d,'check_run_path'),patch.object(d,'manifest',return_value=self.summary['hashes_sha256']):
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            summary=copy.deepcopy(self.summary); summary['stage']='controls'; d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'Wrong P23 stage'): r.worker(folder/'spec.json')
            summary.update(stage='onward',predecessor_gate=False); d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'preflight'): r.worker(folder/'spec.json')

    def test_archives_referenced_and_execution_copies_distinct(self):
        self.assertTrue(all(self.integrity.values()))
        for name,meta in self.summary['inputs'].items(): self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for name in self.summary['hashes_sha256']: self.assertFalse((self.fixture_run/'frozen'/name).samefile(d.ROOT/name))

    def test_predecessor_reaudit_must_match_saved_P22_report(self):
        with patch.object(a.p22,'analyze',return_value=self.inherited) as called,patch.object(d,'integrity',return_value={'all':True}):
            self.assertEqual(a.predecessor_audit(self.fixture_run),self.history); self.assertEqual(called.call_count,1)
        bad=copy.deepcopy(self.inherited); bad['quality_gate']=False
        with patch.object(a.p22,'analyze',return_value=bad),patch.object(d,'integrity',return_value={'all':True}):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])

if __name__=='__main__': unittest.main()
