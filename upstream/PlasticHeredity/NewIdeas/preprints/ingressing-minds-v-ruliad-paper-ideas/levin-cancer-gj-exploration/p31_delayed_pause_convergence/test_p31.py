"""Synthetic P31 ladder, archived diagonal replays, and deliberate failures."""
from contextlib import contextmanager,redirect_stdout
import copy,io,os,shutil,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import p31_design as d
import run_p31 as r
import analyze_p31 as a
import supervise_p31 as s

def fixture_root():
    value=os.environ.get('P31_TEST_ROOT')
    if not value: raise RuntimeError('P31 tests require external P31_TEST_ROOT')
    root=Path(value).resolve()
    if not root.is_relative_to(d.BASE): raise RuntimeError('P31 fixture outside dedicated store')
    return root

def fixture_case(run,c,negative=False):
    folder=run/c['id'];folder.mkdir();exp=r.ResolutionExperiment(folder,c)
    current={};original=exp.phase
    def phase(name,horizon,**kwargs):current['name']=name;return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name'];initial=sim.cc_cells.copy();reference=d.replay(c)
        if reference and not negative:
            old=a.arrays(run/'inputs'/reference,name)
            np.testing.assert_array_equal(initial,old['initial']);np.copyto(sim.cc_cells,old['final'])
            meta=next(p['clock'] for p in d.read(run/'inputs'/reference/'result.json')['phases'] if p['phase']==name)
            return old['times'],old['concentrations'],{k:old[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        if c['kind']=='prefix':
            key='p29/'+d.prefix_design.prefix(c['founder'],c['fine'],16)['id'];drift=.0001/c['resolution']
        else:
            key='p30/'+d.prior.case(c['founder'],c['condition'],'heldout_17021',fine=c['fine'],resolution=16)['id'];drift=.001/c['resolution']
        template=a.arrays(run/'inputs'/key,name)
        values=template['concentrations'].copy();values[:,0,:]+=drift;values[0]=initial
        if negative and name.startswith('isolated_'):
            for value in values[1:]:
                for i in range(3):exp.z.GRN.set_very_healthy(value,i)
        np.copyto(sim.cc_cells,values[-1])
        base=sim.GP.time_step;total=round(horizon/base);stride=round(sample_interval/base);cap=round(max_step/base)
        steps=[];tick=0;proposal=2*stride
        while tick<total:
            step=min(cap,proposal,min(((tick//stride)+1)*stride,total)-tick,total-tick);steps.append(step);tick+=step
        steps=np.asarray(steps,dtype=np.int64);proposed=np.full(len(steps),proposal,dtype=np.int64)
        shots=np.asarray(list(range(0,total,stride))+[total],dtype=np.int64);times=shots*base
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,iterations=len(steps),
            sample_count=len(shots),capped_steps=int(np.count_nonzero(steps<proposed)),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock),d.recovery.external_phases():
        out,provenance=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out,provenance);d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestOperations(unittest.TestCase):
    def test_independent_registration(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases());self.assertEqual(len(d.fixed_cases()),96)
        self.assertEqual([len(d.stage_cases(k)) for k in d.STAGES],[8,8,32,48])
        self.assertEqual(len({c['id'] for c in d.fixed_cases()}),96)
        self.assertEqual(d.read(d.HERE/'config.json'),d.FIXED)
    def test_factors_and_no_extra_cases(self):
        for c in d.fixed_cases():
            self.assertEqual(c['fine'],c['source_fine']);self.assertEqual(d.replay(c),a.replay(c))
            if c['kind']=='renewal':self.assertEqual(d.prefix_source(c),a.prefix_source(c))
            self.assertEqual(d.integrator(c)['time_step'],.0001/c['resolution'])
        self.assertEqual({(c['prefix_resolution'],c['resolution']) for c in d.stage_cases('refinement')},set(d.AXES))
        with self.assertRaises(ValueError):d.stage_cases('onward')
    def test_native_draws_and_source_paths(self):
        word=int.from_bytes(__import__('hashlib').sha256(b'P16_turnover_limit_v1|501|turnover|0').digest()[:8],'big')
        self.assertEqual(d.draw_book()['prefix_legacy_event_zero'],'%016x'%word)
        self.assertEqual(d.draw_book()['downstream'],{'heldout_17021':a.p27.expected_draws()['heldout_17021']})
        self.assertEqual(d.read(d.HERE/'draws.json'),d.draw_book())
        paths=d.input_paths()
        for c in d.fixed_cases():
            self.assertIn(d.stock_source(c)+'/preparation.npz',paths)
            self.assertIn(d.founder_source(c)+'/isolated_2.npz',paths)
    def test_unregistered_parameters_rejected(self):
        x=copy.deepcopy(d.FIXED);x['prefix_resolutions'].append(128)
        with self.assertRaises(ValueError):d.validate_config(x)
        self.assertEqual(d.phase_settings(d.prefix(resolution=16),100),(5,.0625))
    def test_completed_diagnosis_preserves_negative_gate(self):
        evidence=d.completed_evidence();self.assertTrue(evidence['diagnostic_archive_valid'])
        self.assertFalse(evidence['p30_quality_gate']);self.assertFalse(evidence['original_P27_quality_gate']);self.assertTrue(evidence['p29_targeted_repair_qualified'])
    def test_legacy_inventory_unchanged(self):
        d.source_check();self.assertEqual(len(d.manifest()),292)
        self.assertEqual(d.recovery.prior_supervisor.verification_manifest(),d.read(d.recovery.OLD_JOB/'launch.json')['verification_hashes_sha256'])
    def test_fixture_confinement_and_finite_json(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):fixture_root()
        with patch.dict(os.environ,{'P31_TEST_ROOT':'/tmp'}):
            with self.assertRaises(RuntimeError):fixture_root()
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            p=Path(tmp)/'finite.json';d.write_json(p,{'ok':True})
            with self.assertRaises(ValueError):d.write_json(p,{'x':float('nan')})
            self.assertEqual(d.read(p),{'ok':True})
    def test_disk_budget_and_paths(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,patch.object(d,'space_available',return_value=False):
            self.assertEqual(r.run_worker(d.prefix(),Path(tmp),time.monotonic()+1,{})['status'],'not_launched_disk')
            self.assertEqual(r.run_worker(d.prefix(),Path(tmp),time.monotonic()-1,{})['status'],'not_launched_budget')
            self.assertEqual(list(Path(tmp).iterdir()),[])
            with self.assertRaises(ValueError):d.check_run_path(Path(tmp))
    def test_queue_stops_after_failure(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,patch.object(r,'run_worker',side_effect=lambda c,*x:dict(id=c['id'],execution_pass=False)) as called:
            self.assertFalse(r.execute_stage(d.stage_cases('prefix_replay'),Path(tmp),{'cases':[]},time.monotonic()+1,{}))
            self.assertEqual(called.call_count,2)
    @contextmanager
    def job(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            job=Path(tmp);d.write_json(job/'status.json',dict(phase='launching'))
            (job/'verification.log').write_text('Ran %d tests in 0.001s\n\nOK\n'%d.FIXED['software_tests']);yield job
    def supervise(self,job,returns,error=None):
        with patch.object(s.signal,'signal'),patch.object(d,'verify_launch',side_effect=error),patch.object(d,'space_available',return_value=True),patch.object(s,'discover_run',return_value=None),patch.object(s,'run_child',side_effect=returns) as child:
            fd=os.open(job/'lock',os.O_CREAT|os.O_RDWR,0o600);code=s.supervise(job,fd)
        return code,child.call_count,d.read(job/'status.json')
    def test_partial_software_log_blocks_science(self):
        for log in ('partial','Ran 1 tests in 0.001s\n\nOK\n'):
            with self.job() as job:
                (job/'verification.log').write_text(log);code,n,status=self.supervise(job,[0])
                self.assertEqual((code,n),(1,1));self.assertIn('verification evidence',status['error'])
    def test_software_failure_and_changed_source_block_science(self):
        with self.job() as job:self.assertEqual(self.supervise(job,[1])[:2],(1,1))
        with self.job() as job:self.assertEqual(self.supervise(job,[],RuntimeError('changed source'))[:2],(1,0))
    def test_runner_failure_has_no_retry(self):
        with self.job() as job:
            code,n,status=self.supervise(job,[0,124]);self.assertEqual((code,n),(1,2));self.assertIn('no retry',status['error'])
    def test_watchdog_terminates_owned_group(self):
        with self.job() as job,patch.object(s,'child_env',return_value={}),patch.object(s.subprocess,'Popen') as popen,patch.object(s,'terminate_owned') as stop:
            proc=popen.return_value;proc.poll.return_value=None;proc.pid=42
            self.assertEqual(s.run_child(['fixture'],job,'child.log',0,lambda pid:None),124);stop.assert_called_once_with(proc)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])

class TestPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p31-software-',dir=fixture_root());cls.addClassCleanup(cls.temp.cleanup)
        cls.job_dir=Path(cls.temp.name)/'job';cls.job_dir.mkdir();hashes=d.freeze(cls.job_dir)
        cls.fixture_run=Path(cls.temp.name)/'run';cls.fixture_run.mkdir();d.archive_view(cls.fixture_run)
        (cls.fixture_run/'frozen').symlink_to(cls.job_dir/'frozen',target_is_directory=True)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],hashes_sha256=hashes,
            inputs=d.input_manifest(),inherited_verification=d.completed_evidence(),gates={},gate_hashes={},attempted_stages=[],
            stage='preflight',predecessor_gate=False)
        d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.history=a.predecessor_audit(cls.fixture_run);cls.integrity=cls.history['integrity']
        assert cls.history['quality_gate'],cls.history
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary.update(predecessor_gate=True,predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'))
        with patch.object(d,'integrity',return_value=cls.integrity),redirect_stdout(io.StringIO()):
            for stage in d.STAGES:
                cls.summary['stage']=stage;cls.summary['attempted_stages'].append(stage)
                for c in d.stage_cases(stage):
                    cls.summary['cases'].append(fixture_case(cls.fixture_run,c));d.write_json(cls.fixture_run/'summary.json',cls.summary)
                gate=a.stage_audit(cls.fixture_run,stage)
                assert gate['quality_gate'],[k for k,v in gate['checks'].items() if not v]
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate);cls.summary['gates'][stage]=gate
                cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
            cls.summary.update(stage='finished',all_execution_valid=True,completion_reason='all_registered_stages_completed')
            d.write_json(cls.fixture_run/'summary.json',cls.summary);cls.report=a.analyze(cls.fixture_run)
        cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}
        cls.data={c['id']:{p['phase']:{k:x[k] for k in ('times','concentrations','initial','final')}
            for p in d.read(cls.fixture_run/c['id']/'result.json')['phases'] if (x:=a.arrays(cls.fixture_run/c['id'],p['phase']))} for c in d.fixed_cases()}
        cls.primary=d.case(condition='pause_15_100',prefix_resolution=64,resolution=32)
    @contextmanager
    def copied_case(self,c=None):
        c=c or self.primary
        with tempfile.TemporaryDirectory(prefix='p31-unit-',dir=fixture_root()) as tmp:
            run=Path(tmp);(run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            (run/'summary.json').symlink_to(self.fixture_run/'summary.json')
            if c['kind']=='renewal':
                key=d.prefix_source(c);(run/key).symlink_to(self.fixture_run/key,target_is_directory=True)
            folder=run/c['id'];shutil.copytree(self.fixture_run/c['id'],folder);yield run,folder
    def corrupt_result(self,change,c=None):
        c=c or self.primary
        with self.copied_case(c) as (run,folder):
            result=d.read(folder/'result.json');change(result);d.write_json(folder/'result.json',result)
            checks=a.Checks();a.branch(folder,c,checks);self.assertFalse(all(checks.rows.values()))
    def corrupt_array(self,name,change,c=None):
        c=c or self.primary
        with self.copied_case(c) as (run,folder):
            x=a.arrays(folder,name);change(x);np.savez_compressed(folder/(name+'.npz'),**x)
            rec=d.read(folder/'result.json');next(p for p in rec['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',rec);checks=a.Checks();a.branch(folder,c,checks);self.assertFalse(all(checks.rows.values()))
    def test_complete_panel_and_registered_comparisons(self):
        self.assertTrue(self.report['quality_gate']);self.assertTrue(self.report['focused_repair_qualified'])
        self.assertEqual((self.report['completed_cases'],self.report['integration_calls']),(96,2096))
        self.assertEqual([self.summary['gates'][k]['integration_calls'] for k in d.STAGES],[8,16,848,2096])
        self.assertEqual([len(self.report[k]) for k in ('prefix_finest_comparisons','upstream_finest_comparisons','downstream_finest_comparisons','joint_finest_comparisons','prefix_source_comparisons','source_precision_comparisons')],[4,4,4,16,2,8])
        self.assertFalse(self.report['original_P27_quality_gate']);self.assertFalse(self.report['qualified_onward_transmission_established'])
    def test_all_forty_replays_match_every_array(self):
        for c in d.stage_cases('prefix_replay')+d.stage_cases('replay'):
            checks=a.Checks();a.branch(self.fixture_run/c['id'],c,checks)
            rows=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(rows),33*(1 if c['kind']=='prefix' else 26));self.assertTrue(all(rows))
    def test_regenerated_prefix_is_actual_assembly_source(self):
        for c in d.fixed_cases():
            if c['kind']=='prefix':continue
            x=a.arrays(self.fixture_run/c['id']/'assembly','checkpoint')
            np.testing.assert_array_equal(x['before'],a.arrays(self.fixture_run/d.prefix_source(c),'replacement_01')['final'])
            self.assertEqual(d.read(self.fixture_run/c['id']/'result.json')['outcome']['logical_end'],1201800)
    def test_prefix_and_downstream_controls_are_independent(self):
        for c in d.fixed_cases():
            rec=d.read(self.fixture_run/c['id']/'result.json')
            for phase in rec['phases']:
                self.assertEqual(phase['setup']['integrator'],d.integrator(c))
                self.assertEqual(phase['clock']['maximum_step'],min(100,phase['requested_horizon']/100)/c['resolution'])
    def test_wrong_source_precision_and_solver_rejected(self):
        self.corrupt_result(lambda x:x.update(source_precision='fine'))
        self.corrupt_result(lambda x:x['phases'][0]['setup']['integrator'].update(time_step=.0001))
        self.corrupt_result(lambda x:x.update(prefix_resolution=16))
    def test_prefix_legacy_draw_and_survivors_rejected(self):
        c=d.prefix(resolution=16)
        self.corrupt_array('replacement_01',lambda x:x['initial'].__setitem__((7,0),x['initial'][7,0]*1.01),c)
        self.corrupt_array('replacement_01',lambda x:x['initial'].__setitem__((5,2),x['initial'][5,2]+1),c)
    def test_prefix_epoch_corruption_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['logical_interval'].__setitem__(0,1180200),d.prefix())
    def test_assembly_state_and_time_reanchor_corruption_rejected(self):
        with self.copied_case() as (_,folder):
            x=a.arrays(folder/'assembly','checkpoint');x['hybrid_before_refresh'][5,0]+=1
            np.savez_compressed(folder/'assembly/checkpoint.npz',**x);checks=a.Checks();a.branch(folder,self.primary,checks)
            self.assertFalse(all(checks.rows.values()))
        self.corrupt_result(lambda x:x['provenance']['assembly'].update(reanchor_without_integration=0))
    def test_phase_clock_and_sampling_corruption_rejected(self):
        self.corrupt_array('challenge_01',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))
        self.corrupt_result(lambda x:x['phases'][0]['clock'].update(sample_interval=.5))
    def test_downstream_draw_and_state_transfer_rejected(self):
        self.corrupt_array('replacement_03',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]*1.01))
        self.corrupt_array('challenge_02',lambda x:x['initial'].__setitem__((0,0),x['initial'][0,0]+1))
    def test_wrong_pause_or_extra_phase_rejected(self):
        self.corrupt_result(lambda x:x['phases'][10]['setup'].update(mirna_kd=1.25e-14))
        self.corrupt_result(lambda x:x.update(repeated_pause=True))
        with self.copied_case() as (_,folder):
            shutil.copyfile(folder/'isolated_1.npz',folder/'extra.npz');checks=a.Checks();a.branch(folder,self.primary,checks)
            self.assertFalse(all(checks.rows.values()))
    def test_control_anchor_change_is_retained_and_rejected(self):
        by=copy.deepcopy(self.by);c=d.case(condition='pause_10_100');by[c['id']]['retained_E']=False
        rows=a.control_anchors(by,self.fixture_run,d.fixed_cases());self.assertEqual(len(rows),48)
        self.assertFalse(all(x['qualified'] for x in rows));self.assertFalse(by[c['id']]['retained_E'])
    def test_each_convergence_criterion_is_required(self):
        row=self.report['downstream_finest_comparisons'][0]['finest']
        for key in ('phase_inventory_agrees','outcomes_agree','all_phase_labels_agree','common_grid_diagnostics_agree'):
            bad=copy.deepcopy(row);bad[key]=False;self.assertFalse(a.acceptable(bad))
        bad=copy.deepcopy(row);bad['max_primary_scaled_error']=.01001;self.assertFalse(a.acceptable(bad))
    def test_noncontracting_error_rejected(self):
        row=copy.deepcopy(self.report['downstream_finest_comparisons'][0]['finest']);row['max_primary_scaled_error']=.009
        previous=copy.deepcopy(row);previous['max_primary_scaled_error']=.001
        self.assertFalse(a.contracted(previous,row))
    def test_prefix_transient_labels_reject_false_convergence(self):
        data=copy.deepcopy(self.data);c=d.prefix(resolution=64);x=data[c['id']]['replacement_01']
        sample=x['concentrations'][3];before=str(a.labels(sample,a.INDEX)[0])
        sample[5,0],sample[6,0]=(1,20) if before=='E' else (20,1)
        self.assertNotEqual(str(a.labels(sample,a.INDEX)[0]),before)
        row=a.prefix_pair(d.prefix(resolution=32),c,self.by,data);self.assertFalse(row['common_grid_diagnostics_agree'])
        self.assertTrue(row['outcomes_agree']);self.assertTrue(row['all_phase_labels_agree'])
        report=a.convergence_report(self.by,data);self.assertFalse(report['all_finest_converged'])
    def test_recovery_time_difference_rejects_qualification(self):
        data=copy.deepcopy(self.data);c=d.case();x=data[c['id']]['challenge_12']
        x['concentrations'][-1,5,0]=20;x['concentrations'][-1,6,0]=1;x['final']=x['concentrations'][-1].copy()
        report=a.convergence_report(self.by,data);self.assertFalse(report['all_source_comparisons_agree'])
    def test_source_sensitivity_cannot_be_hidden_by_equal_labels(self):
        data=copy.deepcopy(self.data)
        for c in d.fixed_cases():
            if not c['source_fine']:continue
            for x in data[c['id']].values():x['concentrations'][:,0,:]+=1
        report=a.convergence_report(self.by,data);self.assertFalse(report['all_source_comparisons_agree']);self.assertFalse(report['focused_convergence_supported'])
    def test_valid_negative_diagnosis_is_saved_without_retry(self):
        c=d.case(condition='pause_15_100',source_fine=True)
        with tempfile.TemporaryDirectory(prefix='p31-negative-',dir=fixture_root()) as tmp:
            run=Path(tmp)
            for name in ('inputs','frozen','predecessor_audit.json'):
                (run/name).symlink_to(self.fixture_run/name,target_is_directory=(name!='predecessor_audit.json'))
            for item in d.fixed_cases():
                if item['id']!=c['id']:(run/item['id']).symlink_to(self.fixture_run/item['id'],target_is_directory=True)
            summary=copy.deepcopy(self.summary);d.write_json(run/'summary.json',summary)
            with redirect_stdout(io.StringIO()):row=fixture_case(run,c,negative=True)
            summary['cases']=[row if x['id']==c['id'] else x for x in summary['cases']];d.write_json(run/'summary.json',summary)
            with patch.object(d,'integrity',return_value=self.integrity):negative=a.stage_audit(run,'refinement')
            self.assertTrue(negative['quality_gate'],[k for k,v in negative['checks'].items() if not v])
            self.assertFalse(negative['convergence']['all_source_comparisons_agree'])
            summary['gates']['refinement']=negative
            for stage,gate in summary['gates'].items():
                d.write_json(run/(stage+'_audit.json'),gate);summary['gate_hashes'][stage]=d.digest(run/(stage+'_audit.json'))
            d.write_json(run/'summary.json',summary)
            with patch.object(d,'integrity',return_value=self.integrity),patch.object(a,'stage_audit',side_effect=lambda run,stage:summary['gates'][stage]):
                report=a.analyze(run)
            self.assertTrue(report['quality_gate']);self.assertFalse(report['focused_repair_qualified'])
            self.assertFalse(report['automatic_follow_on'])
    def test_worker_requires_history_and_stage(self):
        with self.copied_case() as (run,folder),patch.object(d,'check_run_path'),patch.object(d,'manifest',return_value=self.summary['hashes_sha256']):
            (run/'summary.json').unlink();(run/'frozen').symlink_to(self.fixture_run/'frozen',target_is_directory=True)
            summary=copy.deepcopy(self.summary);summary['stage']='replay';d.write_json(run/'summary.json',summary)
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            with self.assertRaisesRegex(ValueError,'Wrong P31 stage'):r.worker(folder/'spec.json')
            summary.update(stage='refinement',predecessor_gate=False);d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'preflight'):r.worker(folder/'spec.json')
    def test_all_input_references_and_frozen_copies(self):
        self.assertTrue(all(self.integrity.values()))
        for name,meta in self.summary['inputs'].items():self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for name in self.summary['hashes_sha256']:self.assertFalse((self.fixture_run/'frozen'/name).samefile(d.ROOT/name))
    def test_historical_mathematics_not_rerun(self):
        with patch.object(a.p28,'analyze',side_effect=AssertionError('No historical mathematical rerun')),patch.object(d,'integrity',return_value=self.integrity):
            self.assertEqual(a.predecessor_audit(self.fixture_run),self.history)

    def test_three_original_label_failures_are_preserved(self):
        rows=self.report['baseline_comparisons'];self.assertEqual(len(rows),16)
        failed={(x['founder'],x['condition'],x['source_fine']) for x in rows if not x['qualified_under_P30_criteria']}
        self.assertEqual(failed,{('written','pause_15_100',False),('written','pause_15_100',True),('ordinary','pause_15_100',True)})
        self.assertTrue(all(x['outcomes_agree'] and x['common_grid_diagnostics_agree'] for x in rows))
    def test_raw_threshold_values_and_grid(self):
        self.assertEqual(len(self.report['threshold_diagnostics']),80)
        for row in self.report['threshold_diagnostics']:
            self.assertEqual(row['times'],[150+1.25*i for i in range(41)])
            self.assertEqual(len(row['labels']),41)
            c=row['case'];x=self.data[c['id']]['challenge_15']['final']
            self.assertEqual(row['at_175']['miR200_minus_Zeb'],float(x[5,2]-x[6,2]))
            self.assertEqual(row['at_175']['label'],str(a.labels(x,a.INDEX)[2]))
    def test_strict_classifier_cutoff_is_not_relaxed(self):
        raw=copy.deepcopy(self.data[d.case()['id']])
        for delta,expected in ((2.,'X'),(2.000001,'E'),(-2.,'X'),(-2.000001,'M')):
            raw['challenge_15']['concentrations'][-1,5,2]=10+delta
            raw['challenge_15']['concentrations'][-1,6,2]=10
            self.assertEqual(a.threshold_neighborhood(raw)['at_175']['label'],expected)
    def test_interior_neighborhood_label_difference_rejects_qualification(self):
        data=copy.deepcopy(self.data);c=d.case();x=data[c['id']]['challenge_15']
        old=str(a.labels(x['concentrations'][2],a.INDEX)[2]);x['concentrations'][2,5,2]=1 if old=='E' else 20
        x['concentrations'][2,6,2]=20 if old=='E' else 1
        row=a.pair(d.case(prefix_resolution=32,resolution=32),c,self.by,data)
        self.assertTrue(row['all_phase_labels_agree']);self.assertFalse(row['target_neighborhood_labels_agree'])
        self.assertFalse(a.acceptable(row))
    def test_threshold_sample_grid_cannot_be_changed(self):
        raw=copy.deepcopy(self.data[d.case()['id']]);raw['challenge_16']['times'][1]+=.1
        with self.assertRaisesRegex(ValueError,'sample grid'):a.threshold_neighborhood(raw)
    def test_neighborhood_criteria_are_required(self):
        row=self.report['downstream_finest_comparisons'][0]['finest']
        for key in ('target_neighborhood_labels_agree','target_neighborhood_switches_agree'):
            bad=copy.deepcopy(row);bad[key]=False;self.assertFalse(a.acceptable(bad))
    def test_no_extra_axis_for_controls_or_omitted_target_axis(self):
        for condition in ('baseline','pause_10_100','pause_20_100'):
            axes={(c['prefix_resolution'],c['resolution']) for c in d.stage_cases('refinement') if c['condition']==condition}
            self.assertEqual(axes,{(32,32),(64,64)})
        axes={(c['prefix_resolution'],c['resolution']) for c in d.stage_cases('refinement') if c['condition']=='pause_15_100'}
        self.assertEqual(axes,{(16,64),(32,64),(64,16),(64,32),(32,32),(64,64)})
    def test_favorable_diagnosis_does_not_relabel_prior_panel(self):
        self.assertTrue(self.report['focused_repair_qualified'])
        for key in ('original_P27_quality_gate','original_P30_quality_gate','full_pause_panel_qualified',
                    'qualified_onward_transmission_established','full_historical_lineage_refined','automatic_follow_on'):
            self.assertFalse(self.report[key])

if __name__=='__main__':unittest.main()
