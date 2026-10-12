"""Synthetic P28 ladder, archived diagonal replays, and deliberate failures."""
from contextlib import contextmanager,redirect_stdout
import copy,io,os,shutil,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import p28_design as d
import run_p28 as r
import analyze_p28 as a
import supervise_p28 as s

def fixture_root():
    value=os.environ.get('P28_TEST_ROOT')
    if not value: raise RuntimeError('P28 tests require external P28_TEST_ROOT')
    root=Path(value).resolve()
    if not root.is_relative_to(d.BASE): raise RuntimeError('P28 fixture outside dedicated store')
    return root

def fixture_case(run,c,negative=False):
    folder=run/c['id']; folder.mkdir(); exp=r.ResolutionExperiment(folder,c)
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs): current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy(); replay=d.replay(c)
        if replay and not negative:
            old=a.arrays(run/'inputs'/replay,name)
            np.testing.assert_array_equal(initial,old['initial']); np.copyto(sim.cc_cells,old['final'])
            record=d.read(run/'inputs'/replay/'result.json')
            meta=next(p['clock'] for p in record['phases'] if p['phase']==name)
            return old['times'],old['concentrations'],{k:old[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        positive=c['condition']!='baseline'
        if name.startswith('challenge_'):
            part=int(name.split('_')[1])-1; routes=d.prior.window_routes(c)[:part+1]; end=d.prior.BOUNDARIES[part+1]
            if all(q=='rna' for q in routes): positive=True
            elif 'rna' not in routes: positive=False
            elif routes[0]=='rna':
                released=d.prior.BOUNDARIES[routes.index('open')]; positive=end-released>=50
            else: positive=routes[-1]=='open'
        if negative: positive=False
        setter=exp.z.GRN.set_very_healthy if positive else exp.z.GRN.set_very_tumor
        for i in range(3): setter(sim.cc_cells,i)
        sim.cc_cells[0]+=.001/c['resolution']+.000001*np.arange(3)
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=[]; tick=0; proposal=2*stride
        while tick<total:
            step=min(cap,proposal,min(((tick//stride)+1)*stride,total)-tick,total-tick); steps.append(step); tick+=step
        steps=np.asarray(steps,dtype=np.int64); proposed=np.full(len(steps),proposal,dtype=np.int64)
        shots=np.asarray(list(range(0,total,stride))+[total],dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,iterations=len(steps),
            sample_count=len(shots),capped_steps=int(np.count_nonzero(steps<proposed)),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock),d.recovery.external_phases():
        out,provenance=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out,provenance); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestOperations(unittest.TestCase):
    def test_independent_registration_and_archive(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),80)
        self.assertEqual([len(d.stage_cases(k)) for k in d.STAGES],[16,64])
        self.assertEqual(len({c['id'] for c in d.fixed_cases()}),80)
        paths=d.input_paths(); self.assertEqual(len(paths),31265); self.assertEqual(len(d.manifest()),265)
        for c in d.fixed_cases():
            self.assertEqual(d.replay(c),a.replay(c)); self.assertEqual(d.original_case(c)['id'],a.old_id(c))
            self.assertIn('p27/'+a.old_id(c)+'/result.json',paths)
        self.assertEqual(d.read(d.HERE/'config.json'),d.FIXED)
    def test_source_factor_separate_from_solver(self):
        for h in d.FOUNDERS:
            for condition in d.CONDITIONS:
                for f in (False,True):
                    cases=[d.case(h,condition,f,q) for q in d.LEVELS]
                    self.assertEqual(len({d.prior.source(c) for c in cases}),1)
                    self.assertTrue(all(c['fine'] is f and c['source_fine'] is f for c in cases))
                    self.assertEqual([d.integrator(c)['time_step'] for c in cases],[.0001/q for q in (1,2,4,8,16)])
        self.assertNotEqual(d.prior.source(d.case(source_fine=False)),d.prior.source(d.case(source_fine=True)))
    def test_clock_ladder_and_sampling_grid(self):
        for q in d.LEVELS:
            for f in (False,True):
                c=d.case(source_fine=f,resolution=q)
                self.assertEqual(d.integrator(c),dict(time_step=.0001/q,sim_integ_max_delt_cc=.001/q,sim_integ_max_delt_Vm=.0001/q,use_implicit=False))
                for H in (5,25,300,10000):
                    sample,maximum=d.phase_settings(c,H)
                    self.assertEqual(sample,min(100,H/20)); self.assertEqual(maximum,min(100,H/100)/q)
                    for value in (sample,maximum,H):
                        ticks=r.clock.ticks(value,.0001/q); self.assertAlmostEqual(ticks*(.0001/q),value)
    def test_unchanged_single_draw_and_configuration(self):
        self.assertEqual(d.draw_book(),{'heldout_17021':a.p27.expected_draws()['heldout_17021']})
        self.assertEqual(d.read(d.HERE/'draws.json'),d.draw_book())
        altered=copy.deepcopy(d.FIXED); altered['resolutions'].append(32)
        with self.assertRaises(ValueError): d.validate_config(altered)
        with self.assertRaises(ValueError): d.stage_cases('onward')
    def test_stopped_predecessor_is_not_promoted_to_success(self):
        evidence=d.stopped_evidence(); self.assertTrue(evidence['diagnostic_archive_valid'])
        self.assertIs(evidence['predecessor_quality_gate'],False); self.assertEqual(len(evidence['known_failed_checks']),4)
    def test_changed_predecessor_pin_rejected(self):
        pins=copy.deepcopy(d.PINS); pins['job/status.json']='0'*64
        with patch.object(d,'PINS',pins):
            with self.assertRaisesRegex(RuntimeError,'evidence changed'): d.stopped_evidence()
    def test_legacy_inventory_unchanged(self):
        d.source_check()
        self.assertEqual(d.recovery.prior_supervisor.verification_manifest(),d.read(d.recovery.OLD_JOB/'launch.json')['verification_hashes_sha256'])
    def test_atomic_json_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            p=Path(tmp)/'test.json'; d.write_json(p,{'ok':True})
            with self.assertRaises(ValueError): d.write_json(p,{'x':float('nan')})
            self.assertEqual(d.read(p),{'ok':True})
    def test_fixture_path_confinement(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'require external'): fixture_root()
        with patch.dict(os.environ,{'P28_TEST_ROOT':'/tmp'}):
            with self.assertRaisesRegex(RuntimeError,'outside dedicated'): fixture_root()
    def test_disk_budget_and_output_confinement(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,patch.object(d,'space_available',return_value=False):
            self.assertEqual(r.run_worker(d.case(),Path(tmp),time.monotonic()+1,{})['status'],'not_launched_disk')
            self.assertEqual(r.run_worker(d.case(),Path(tmp),time.monotonic()-1,{})['status'],'not_launched_budget')
            self.assertEqual(list(Path(tmp).iterdir()),[])
            with self.assertRaises(ValueError): d.check_run_path(Path(tmp))
        disk=type('Disk',(),{'free':5*1024**3})()
        with patch.object(d.shutil,'disk_usage',return_value=disk):
            self.assertTrue(d.space_available(Path('/mnt/workspaces'))); disk.free-=1; self.assertFalse(d.space_available(Path('/mnt/workspaces')))
    def test_queue_stops_after_failure(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,patch.object(r,'run_worker',side_effect=lambda c,*args:dict(id=c['id'],execution_pass=False)) as called:
            summary={'cases':[]}; self.assertFalse(r.execute_stage(d.stage_cases('replay'),Path(tmp),summary,time.monotonic()+1,{})); self.assertEqual(called.call_count,2)
    @contextmanager
    def job(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            job=Path(tmp); d.write_json(job/'status.json',dict(phase='launching'))
            (job/'verification.log').write_text('Ran %d tests in 0.001s\n\nOK\n'%d.FIXED['software_tests'])
            yield job
    def supervise(self,job,returns,error=None):
        with patch.object(s.signal,'signal'),patch.object(d,'verify_launch',side_effect=error),patch.object(d,'space_available',return_value=True),patch.object(s,'discover_run',return_value=None),patch.object(s,'run_child',side_effect=returns) as child:
            fd=os.open(job/'lock',os.O_CREAT|os.O_RDWR,0o600); code=s.supervise(job,fd)
        return code,child.call_count,d.read(job/'status.json')
    def test_partial_or_missing_success_log_blocks_science(self):
        for log in ('partial','Ran 1 tests in 0.001s\n\nOK\n'):
            with self.job() as job:
                (job/'verification.log').write_text(log); code,n,status=self.supervise(job,[0])
                self.assertEqual((code,n),(1,1)); self.assertIn('verification evidence',status['error'])
    def test_failed_software_and_changed_source_block_science(self):
        with self.job() as job:
            self.assertEqual(self.supervise(job,[1])[:2],(1,1))
        with self.job() as job:
            self.assertEqual(self.supervise(job,[],RuntimeError('changed source'))[:2],(1,0))
    def test_runner_failure_has_no_retry(self):
        with self.job() as job:
            code,n,status=self.supervise(job,[0,124]); self.assertEqual((code,n),(1,2)); self.assertIn('no retry',status['error'])
    def test_timeout_terminates_owned_group(self):
        with self.job() as job,patch.object(s,'child_env',return_value={}),patch.object(s.subprocess,'Popen') as popen,patch.object(s,'terminate_owned') as stop:
            proc=popen.return_value; proc.poll.return_value=None; proc.pid=42
            self.assertEqual(s.run_child(['fixture'],job,'child.log',0,lambda pid:None),124); stop.assert_called_once_with(proc)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])

class TestPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p28-software-',dir=fixture_root()); cls.addClassCleanup(cls.temp.cleanup)
        cls.job=Path(cls.temp.name)/'job'; cls.job.mkdir(); hashes=d.freeze(cls.job)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); d.archive_view(cls.fixture_run)
        (cls.fixture_run/'frozen').symlink_to(cls.job/'frozen',target_is_directory=True)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],hashes_sha256=hashes,inputs=d.input_manifest(),
            inherited_verification=d.stopped_evidence(),gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        d.write_json(cls.fixture_run/'summary.json',cls.summary); cls.integrity=d.integrity(cls.fixture_run,cls.summary)
        if not all(cls.integrity.values()): raise AssertionError(cls.integrity)
        with redirect_stdout(io.StringIO()),patch.object(d,'integrity',return_value=cls.integrity):
            cls.history=a.predecessor_audit(cls.fixture_run); d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
            cls.summary.update(predecessor_gate=True,predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'))
            for stage in d.STAGES:
                for c in d.stage_cases(stage): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary); gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate); cls.summary['gates'][stage]=gate; cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
            cls.summary.update(stage='finished',all_execution_valid=True,completion_reason='all_registered_stages_completed')
            d.write_json(cls.fixture_run/'summary.json',cls.summary); cls.report=a.analyze(cls.fixture_run)
        cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}
        cls.data={c['id']:{p['phase']:{k:x[k] for k in ('times','concentrations','initial','final')} for p in d.read(cls.fixture_run/c['id']/'result.json')['phases'] if (x:=a.arrays(cls.fixture_run/c['id'],p['phase']))} for c in d.fixed_cases()}
        cls.primary=d.case(condition='pause_10_100',source_fine=False,resolution=8)
    @contextmanager
    def copied_case(self,c=None):
        c=c or self.primary
        with tempfile.TemporaryDirectory(prefix='p28-unit-',dir=fixture_root()) as tmp:
            run=Path(tmp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True); folder=run/c['id']
            shutil.copytree(self.fixture_run/c['id'],folder); yield run,folder
    def corrupt_result(self,change,c=None):
        c=c or self.primary
        with self.copied_case(c) as (run,folder):
            record=d.read(folder/'result.json'); change(record); d.write_json(folder/'result.json',record)
            checks=a.Checks(); a.branch(folder,c,checks); self.assertFalse(all(checks.rows.values()))
    def corrupt_array(self,name,change,c=None):
        c=c or self.primary
        with self.copied_case(c) as (run,folder):
            data=a.arrays(folder,name); change(data); np.savez_compressed(folder/(name+'.npz'),**data)
            record=d.read(folder/'result.json'); next(p for p in record['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz')); d.write_json(folder/'result.json',record)
            checks=a.Checks(); a.branch(folder,c,checks); self.assertFalse(all(checks.rows.values()))
    def test_complete_panel_counts_and_comparisons(self):
        self.assertTrue(self.report['quality_gate']); self.assertTrue(self.report['ready_for_refined_full_panel'])
        self.assertEqual((self.report['completed_cases'],self.report['integration_calls']),(80,2080))
        self.assertEqual(len(self.report['adjacent_resolution_comparisons']),64); self.assertEqual(len(self.report['finest_resolution_comparisons']),16)
        self.assertEqual(len(self.report['source_precision_comparisons']),8)
        self.assertEqual([self.summary['gates'][k]['integration_calls'] for k in d.STAGES],[416,2080])
        self.assertEqual([len(self.summary['gates'][k]['shared_schedule_prefix_comparisons']) for k in d.STAGES],[8,40])
        self.assertFalse(self.report['original_P27_quality_gate']); self.assertFalse(self.report['qualified_onward_transmission_established'])
    def test_diagonal_replays_all_numeric_arrays(self):
        for c in d.stage_cases('replay'):
            checks=a.Checks(); a.branch(self.fixture_run/c['id'],c,checks)
            rows=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(rows),26*33); self.assertTrue(all(rows))
    def test_fixed_sources_and_full_live_trajectory(self):
        for h in d.FOUNDERS:
            for k in d.CONDITIONS:
                for f in (False,True):
                    states=[a.arrays(self.fixture_run/d.case(h,k,f,q)['id']/'assembly','checkpoint')['assembled'] for q in d.LEVELS]
                    for state in states[1:]: np.testing.assert_array_equal(state,states[0])
        for c in d.fixed_cases():
            result=d.read(self.fixture_run/c['id']/'result.json')
            self.assertEqual(result['outcome']['logical_end'],1201800); self.assertTrue(result['outcome']['complete_carrier_replacement'])
            self.assertEqual([x['position'] for x in result['outcome']['replacements']],[1,2,0,1,2])
    def test_all_numeric_controls_scaled_but_samples_unchanged(self):
        for c in d.fixed_cases():
            for p in d.read(self.fixture_run/c['id']/'result.json')['phases']:
                H=p['requested_horizon']; q=c['resolution']
                self.assertEqual(p['setup']['integrator'],dict(time_step=.0001/q,sim_integ_max_delt_cc=.001/q,sim_integ_max_delt_Vm=.0001/q,use_implicit=False))
                self.assertEqual(p['clock']['maximum_step'],min(100,H/100)/q)
                self.assertEqual(p['clock']['sample_interval'],min(100,H/20))
    def test_old_fine_flag_cannot_override_registered_level(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['integrator'].update(time_step=.0001))
        self.corrupt_result(lambda x:x['phases'][0]['clock'].update(maximum_step=.05))
        self.corrupt_result(lambda x:x.update(source_precision='fine'))
    def test_sample_grid_clock_clip_and_epoch_corruption_rejected(self):
        self.corrupt_array('challenge_01',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))
        self.corrupt_result(lambda x:x['phases'][0]['clock'].update(sample_interval=.5))
        self.corrupt_result(lambda x:x['phases'][0]['logical_interval'].__setitem__(0,0))
    def test_incoming_draw_survivor_reset_and_boundary_discontinuity_rejected(self):
        self.corrupt_array('replacement_03',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]*1.01))
        self.corrupt_array('replacement_04',lambda x:x['initial'].__setitem__((5,1),x['initial'][5,1]+1))
        self.corrupt_array('challenge_02',lambda x:x['initial'].__setitem__((0,0),x['initial'][0,0]+1))
    def test_primary_state_preparation_or_extra_phase_rejected(self):
        with self.copied_case() as (_,folder):
            data=a.arrays(folder/'assembly','checkpoint'); data['hybrid_before_refresh'][5,0]+=1
            np.savez_compressed(folder/'assembly/checkpoint.npz',**data); checks=a.Checks(); a.branch(folder,self.primary,checks)
            self.assertFalse(all(checks.rows.values()))
        with self.copied_case() as (_,folder):
            shutil.copyfile(folder/'isolated_1.npz',folder/'extra_hold.npz'); checks=a.Checks(); a.branch(folder,self.primary,checks)
            self.assertFalse(all(checks.rows.values()))
    def test_wrong_pause_end_or_repeated_pause_rejected(self):
        self.corrupt_result(lambda x:x['phases'][10]['setup'].update(mirna_kd=0))
        self.corrupt_result(lambda x:x['phases'][20]['setup'].update(mirna_kd=0))
        self.corrupt_result(lambda x:x.update(repeated_pause=True))
    def test_reference_anchor_failure_does_not_rewrite_output(self):
        by=copy.deepcopy(self.by); c=d.case(condition='pause_0_25',resolution=16); by[c['id']]['retained_E']=False
        rows=a.control_anchors(by,self.fixture_run,d.fixed_cases()); self.assertEqual(len(rows),40); self.assertFalse(all(x['qualified'] for x in rows))
        self.assertFalse(by[c['id']]['retained_E'])
    def test_transient_label_disagreement_fails_finest_convergence(self):
        data=copy.deepcopy(self.data); c=d.case(resolution=16)
        data[c['id']]['challenge_12']['final'][5,0]=0; data[c['id']]['challenge_12']['final'][6,0]=100
        out=a.convergence_report(self.by,data)
        self.assertFalse(out['all_finest_converged']); self.assertFalse(out['refined_full_panel_supported'])
    def test_recovery_timing_disagreement_fails_even_with_matching_phase_ends(self):
        data=copy.deepcopy(self.data); c=d.case(resolution=16)
        # t=15 is the end of challenge_03; alter the recorded common sample
        # while leaving final arrays fixed to isolate this independent criterion.
        data[c['id']]['challenge_03']['concentrations'][-1,5,0]=100
        data[c['id']]['challenge_03']['concentrations'][-1,6,0]=0
        row=a.pair(d.case(resolution=8),c,self.by,data)
        self.assertTrue(row['all_phase_labels_agree']); self.assertFalse(row['common_grid_diagnostics_agree'])
        self.assertFalse(a.convergence_report(self.by,data)['all_finest_converged'])
    def test_large_continuous_error_is_not_hidden_by_labels(self):
        data=copy.deepcopy(self.data); c=d.case(resolution=16)
        for phase in data[c['id']].values(): phase['concentrations'][:,0,:]+=10
        out=a.convergence_report(self.by,data); self.assertFalse(out['all_finest_converged'])
    def test_noncontracting_error_rejects_finest_pair(self):
        original=a.pair
        def changed(left,right,*args):
            row=original(left,right,*args)
            if left['source_fine']==right['source_fine']:
                row['max_primary_scaled_error']=.003 if right['resolution']==16 else .002
            return row
        with patch.object(a,'pair',side_effect=changed):
            self.assertFalse(a.convergence_report(self.by,self.data)['all_finest_converged'])
    def test_source_sensitivity_reported_separately(self):
        by=copy.deepcopy(self.by)
        for q in d.LEVELS: by[d.case(source_fine=True,resolution=q)['id']]['retained_E']=False
        out=a.convergence_report(by,self.data)
        self.assertTrue(out['all_finest_converged']); self.assertFalse(out['all_source_comparisons_agree']); self.assertFalse(out['refined_full_panel_supported'])
    def test_unfavorable_novel_result_is_valid_diagnostic_data(self):
        c=d.case(condition='pause_10_100',resolution=16)
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,redirect_stdout(io.StringIO()):
            run=Path(tmp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            row=fixture_case(run,c,negative=True); self.assertFalse(row['result']['outcome']['retained_E'])
            checks=a.Checks(); a.branch(run/c['id'],c,checks); self.assertTrue(all(checks.rows.values()))
    def test_partial_replay_does_not_qualify(self):
        c=d.stage_cases('replay')[0]
        self.corrupt_array('challenge_01',lambda x:x['concentrations'].__setitem__((1,0,0),x['concentrations'][1,0,0]+.001),c)
    def test_negative_convergence_is_saved_without_technical_reclassification(self):
        with patch.object(d,'integrity',return_value=self.integrity),patch.object(a,'convergence_report',return_value=dict(all_finest_converged=False,all_source_comparisons_agree=False,refined_full_panel_supported=False,adjacent_resolution_comparisons=[{}]*64,finest_resolution_comparisons=[{}]*16,source_precision_comparisons=[{}]*8)):
            gate=a.stage_audit(self.fixture_run,'convergence')
            self.assertTrue(gate['quality_gate']); self.assertFalse(gate['convergence']['refined_full_panel_supported'])
    def test_worker_stage_and_preflight_guard(self):
        with self.copied_case() as (run,folder),patch.object(d,'check_run_path'),patch.object(d,'manifest',return_value=self.summary['hashes_sha256']):
            (run/'frozen').symlink_to(self.fixture_run/'frozen',target_is_directory=True)
            summary=copy.deepcopy(self.summary); summary['stage']='replay'; d.write_json(run/'summary.json',summary)
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            with self.assertRaisesRegex(ValueError,'Wrong P28 stage'): r.worker(folder/'spec.json')
            summary.update(stage='convergence',predecessor_gate=False); d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'preflight'): r.worker(folder/'spec.json')
    def test_saved_failed_history_used_without_mathematical_rerun(self):
        with patch.object(a.p27,'analyze',side_effect=AssertionError('Do not rerun historical mathematics')),patch.object(d,'integrity',return_value=self.integrity):
            self.assertEqual(a.predecessor_audit(self.fixture_run),self.history)
        with patch.object(d,'integrity',return_value={'archive':False}): self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])
    def test_execution_copies_and_input_references(self):
        self.assertTrue(all(self.integrity.values()))
        for name,meta in self.summary['inputs'].items(): self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for name in self.summary['hashes_sha256']: self.assertFalse((self.fixture_run/'frozen'/name).samefile(d.ROOT/name))

if __name__=='__main__': unittest.main()
