"""Synthetic complete P21 panel and independent component/provenance fault tests."""
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
import p21_design as d
import run_p21 as r
import analyze_p21 as a
import supervise_p21 as s

def fixture_root():
    value=os.environ.get('P21_TEST_ROOT')
    if not value: raise RuntimeError('Full P21 fixtures require external P21_TEST_ROOT')
    root=Path(value).resolve()
    if not root.is_relative_to(d.BASE): raise RuntimeError('P21 fixtures outside dedicated external store')
    return root

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.RateExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs): current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy()
        if (c['kind']=='historical' or c['mask'] in (0,7)) and failure is None:
            src=run/'inputs/p20'/d.control_source(c); archived=a.arrays(src,name)
            if c['kind']=='historical': np.testing.assert_array_equal(initial,archived['initial'])
            else: np.testing.assert_array_equal(initial[list(range(8))+[16]],archived['initial'][list(range(8))+[16]])
            np.copyto(sim.cc_cells,archived['final']); values=archived['concentrations'].copy(); values[0]=initial
            meta=next(x['clock'] for x in d.read(src/'result.json')['phases'] if x['phase']==name)
            return archived['times'],values,{k:archived[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        def mark(indices,label,value=None):
            state=sim.cc_cells if value is None else value
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(state,i)
        success=bool(c['mask']&(1 if c['target']=='newcomer' else 2)) and failure!='all_negative'
        if c['stage']!='onward' and name.startswith('replacement'): mark(range(3),'E' if success else 'M')
        if name=='contact':
            donor_E=all(exp.z.GRN.state_char(x)=='E' for x in initial[:,:3].T)
            if c['readout']=='open' and donor_E or failure=='positive_controls': mark(range(3,6),'E')
        if failure=='all_negative' and name.startswith('isolated'): mark(range(3),'M')
        if failure=='late_recovery' and name.startswith('isolated'): mark(range(3),'E')
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.000001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=[]; tick=0; proposed_step=2*stride
        while tick<total:
            step=min(cap,proposed_step,min(((tick//stride)+1)*stride,total)-tick,total-tick); steps.append(step); tick+=step
        steps=np.asarray(steps,dtype=np.int64); proposed=np.full(len(steps),proposed_step,dtype=np.int64)
        shots=np.asarray(list(range(0,total,stride))+[total],dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        if name=='replacement_02' and success and c['target']=='neighbour':
            for at in range(1,10): mark([0,1],'M',values[at])
        if failure=='late' and name=='isolated_1':
            for at in range(-2,-7,-1): mark([0],'M',values[at])
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,iterations=len(steps),
            sample_count=len(shots),capped_steps=int(np.count_nonzero(steps<proposed)),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock),d.recovery.external_phases():
        out,provenance=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out,provenance); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestP21Operations(unittest.TestCase):
    def test_independent_registration_and_every_parent(self):
        cases=d.fixed_cases(); self.assertEqual(cases,a.expected_cases()); self.assertEqual(len(cases),288)
        self.assertEqual(len({c['id'] for c in cases}),288); self.assertEqual(sum(c['fine'] for c in cases),144)
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[24,48,216])
        for c in cases:
            self.assertEqual(d.replay(c),a.replay(c)); self.assertEqual(d.source(c),a.source(c))
            if c['stage']=='onward': self.assertIn(d.parent(c),cases); self.assertEqual(d.parent(c),a.parent(c))
        self.assertEqual(d.read(d.HERE/'config.json'),d.FIXED)

    def test_changed_configuration_rejected(self):
        value=copy.deepcopy(d.FIXED); value['blocks']['protein']['rows']=[5,7]
        with self.assertRaises(ValueError): d.validate_config(value)

    def test_inherited_evidence_and_unchanged_legacy_globs(self):
        evidence=d.inherited_verification(); self.assertEqual(evidence['p20']['tests'],42)
        self.assertEqual(evidence['legacy']['native']['tests'],1342); self.assertEqual(evidence['legacy']['recovery']['tests'],58)
        self.assertEqual(len(d.manifest()),210); d.source_check()
        self.assertEqual(d.recovery.prior_supervisor.verification_manifest(),d.read(d.recovery.OLD_JOB/'launch.json')['verification_hashes_sha256'])

    def test_all_component_rows_and_native_binding_formula(self):
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(io.StringIO()):
            folder=Path(tmp); exp=r.RateExperiment(folder,dict(id='component-verification',fine=False))
            for founder in ('written','ordinary'):
                for fine in (False,True):
                    src=d.prior.case(founder=founder,fine=fine)['id']; checkpoint=a.arrays(d.P20_RUN/src/'assembly','checkpoint')
                    before,after=checkpoint['before'],checkpoint['after']
                    for target in ('newcomer','neighbour'):
                        for mask in range(8):
                            c=d.case(founder=founder,target=target,mask=mask,fine=fine); mixed=r.mix_primary(before,after,c)
                            pos=0 if target=='newcomer' else 2
                            selected=([7] if mask&1 else [])+([5,6] if mask&2 else [])+([0,1,2,3] if mask&4 else [])
                            for j in range(3):
                                for i in range(17): self.assertEqual(mixed[i,j],after[i,j] if j==pos and i in selected else before[i,j])
                            refreshed=r.native_refresh(exp,mixed,['a','b','c'])
                            np.testing.assert_array_equal(refreshed,a.canonical_binding(mixed))
                            np.testing.assert_array_equal(refreshed[list(range(8))+[16]],mixed[list(range(8))+[16]])
                            np.testing.assert_array_equal(checkpoint['before'],before)

    def test_refresh_cannot_modify_a_primary_variable(self):
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(io.StringIO()):
            exp=r.RateExperiment(Path(tmp),dict(id='refresh-fault',fine=False)); src=d.P20_RUN/d.prior.case()['id']
            value=a.arrays(src/'assembly','checkpoint')['before']
            def bad(cc,*args): cc[5,0]+=1
            with patch.object(exp.z.GRN,'compute_bound_complex_concs_simple',side_effect=bad):
                with self.assertRaisesRegex(RuntimeError,'primary'): r.native_refresh(exp,value,['a','b','c'])

    def test_invalid_source_state_rejected(self):
        before=np.ones((17,3)); before[4]=72; before[16]=0; after=before.copy(); after[0,0]=np.nan
        with self.assertRaises(ValueError): r.mix_primary(before,after,d.case())
        after=before.copy(); after[16,0]=1
        with self.assertRaises(ValueError): r.mix_primary(before,after,d.case())

    def test_draws_independently_reconstructed(self):
        M=np.ones((17,1))
        for at in range(1,6): np.testing.assert_array_equal(d.incoming(M,*divmod(at,3)),a.p19.incoming(M,*divmod(at,3)))

    def test_output_confinement(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp); (job/'runner.log').write_text('Run artifacts: /tmp/unregistered\n')
            with self.assertRaises(ValueError): s.discover_run(job)
            with self.assertRaises(ValueError): d.check_run_path(job)

    def test_disk_and_budget_stop_before_case_creation(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(d,'space_available',return_value=False):
            self.assertEqual(r.run_worker(d.case(),Path(tmp),time.monotonic()+100,{})['status'],'not_launched_disk')
            self.assertEqual(r.run_worker(d.case(),Path(tmp),time.monotonic()-1,{})['status'],'not_launched_budget')
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_external_reserve_is_exactly_five_GiB(self):
        disk=type('Disk',(),{'free':5*1024**3})(); path=Path('/mnt/workspaces/output')
        with patch.object(d.shutil,'disk_usage',return_value=disk) as call:
            self.assertTrue(d.space_available(path)); call.assert_called_once_with(path)
        disk.free-=1
        with patch.object(d.shutil,'disk_usage',return_value=disk): self.assertFalse(d.space_available(path))

    def test_queue_stops_after_observed_failure(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'run_worker',side_effect=lambda c,*args:dict(id=c['id'],execution_pass=False)) as called:
            summary={'cases':[]}; self.assertFalse(r.execute_stage(d.stage_cases('controls'),Path(tmp),summary,time.monotonic()+10,{}))
            self.assertEqual(called.call_count,2)

    @contextmanager
    def job(self):
        with tempfile.TemporaryDirectory() as tmp:
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

    def test_nonmonotone_factorial_and_reciprocal_inference(self):
        inherited=dict(inherited_readout_capacity_qualified=True,inherited_isolated_200_wipe_negative=True)
        by={}
        for c in d.fixed_cases():
            yes=c['mask'] in (1,2,7)
            by[c['id']]=dict(available=True,retained_E=yes,transmitted_E=yes and c['readout']=='open',first_cell_sampled_behavior='sampled_E_resistance')
        result=a.contrasts(by,inherited,True)
        for row in result['component_interpretations']:
            self.assertEqual(row['minimal_tested_rescue_masks'],[1,2]); self.assertEqual(row['minimal_tested_chain_masks'],[1,2])
            self.assertTrue(all(x['loss_of_renewal_after_erasure'] for x in row['reciprocal_interventions']))
        result=a.contrasts(by,inherited,False)
        self.assertFalse(any(x['control_qualified_rescue'] for x in result['component_grid']))

class TestP21Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p21-software-',dir=fixture_root()); cls.addClassCleanup(cls.temp.cleanup)
        cls.job=Path(cls.temp.name)/'job'; cls.job.mkdir(); hashes=d.freeze(cls.job)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); d.archive_view(cls.fixture_run)
        (cls.fixture_run/'frozen').symlink_to(cls.job/'frozen',target_is_directory=True)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_byte_identical=True,prior_checks=21938,prior_cases=64,prior_calls=256,
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
        cls.inherited=d.read(d.P20_RUN/'independent_audit.json')

    def audit_branch(self,run,c):
        checks=a.Checks(); result,data=a.branch(run/c['id'],c,checks); return checks,result,data

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p21-unit-',dir=fixture_root()) as tmp:
            run=Path(tmp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            for stage in ('controls','components'):
                for c in d.stage_cases(stage): (run/c['id']).symlink_to(self.fixture_run/c['id'],target_is_directory=True)
            yield run

    @contextmanager
    def copied_case(self,c=None):
        c=c or self.primary
        with self.isolated_run() as run:
            folder=run/c['id']
            if folder.is_symlink(): folder.unlink()
            shutil.copytree(self.fixture_run/c['id'],folder); yield run,folder

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

    def corrupt_assembly(self,change):
        with self.copied_case() as (run,folder):
            path=folder/'assembly'; data=a.arrays(path,'checkpoint'); change(data); np.savez_compressed(path/'checkpoint.npz',**data)
            meta=d.read(path/'assembly.json'); meta['checkpoint_sha256']=d.digest(path/'checkpoint.npz'); d.write_json(path/'assembly.json',meta)
            result=d.read(folder/'result.json'); result['provenance'].update(assembly=meta,assembly_metadata_sha256=d.digest(path/'assembly.json'))
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_complete_panel_and_numerical_pairs(self):
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['completed_cases'],288)
        self.assertEqual(self.report['integration_calls'],1152); self.assertEqual(len(self.report['fine_comparisons']),144)
        self.assertTrue(self.report['all_fine_agree']); self.assertEqual([self.summary['gates'][s]['integration_calls'] for s in d.STAGES],[168,504,1152])

    def test_factorial_finds_distinct_fixture_components(self):
        for row in self.report['component_interpretations']:
            expected=1 if row['target']=='newcomer' else 2
            self.assertEqual(row['minimal_tested_rescue_masks'],[expected]); self.assertEqual(row['minimal_tested_chain_masks'],[expected])
            necessity=[x['block'] for x in row['reciprocal_interventions'] if x['loss_of_renewal_after_erasure']]
            self.assertEqual(necessity,['protein' if expected==1 else 'rna'])

    def test_full_native_refresh_checks_for_all_assemblies(self):
        count=0
        for stage in ('controls','components'):
            for c in d.stage_cases(stage):
                data=a.arrays(self.fixture_run/c['id']/'assembly','checkpoint')
                if c['kind']=='component':
                    np.testing.assert_array_equal(data['assembled'],a.canonical_binding(data['hybrid_before_refresh'])); count+=1
                else: np.testing.assert_array_equal(data['assembled'],data['hybrid_before_refresh'])
        self.assertEqual(count,60)

    def test_source_identity_provenance_not_mutated_by_replacements(self):
        for c in d.stage_cases('controls')+d.stage_cases('components'):
            record=d.read(self.fixture_run/c['id']/'result.json'); meta=d.read(self.fixture_run/c['id']/'assembly/assembly.json')
            self.assertEqual(meta,record['provenance']['assembly']); self.assertEqual(meta['cell_ids'],record['outcome']['fork_ids'])
            self.assertFalse(set(meta['cell_ids'])&set(record['phases'][-1]['setup']['cell_ids']))

    def test_historical_controls_replay_every_numeric_array(self):
        cases=phases=0
        for c in d.fixed_cases():
            if c['kind']!='historical': continue
            checks,_,data=self.audit_branch(self.fixture_run,c); cases+=1; phases+=len(data)
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),33*len(data)); self.assertTrue(all(replay))
        self.assertEqual((cases,phases),(48,192))

    def test_all_refreshed_controls_qualified(self):
        self.assertEqual(len(self.report['stages']['onward']['refresh_controls']),12)
        self.assertTrue(all(x['qualified'] for x in self.report['stages']['onward']['refresh_controls']))

    def test_changed_refresh_control_stops_qualification(self):
        by=copy.deepcopy(self.by); c=d.case('controls',mask=7); by[c['id']]['retained_E']=False
        self.assertFalse(all(x['qualified'] for x in a.refresh_controls(by)))
        by=copy.deepcopy(self.by); c=d.case('onward',mask=7,readout='open'); by[c['id']]['transmitted_E']=False
        self.assertFalse(all(x['qualified'] for x in a.refresh_controls(by,True)))

    def test_every_parent_including_failures_has_all_readouts(self):
        for c in d.stage_cases('onward'):
            data=a.arrays(self.fixture_run/c['id'],'contact'); par=d.parent(c)
            np.testing.assert_array_equal(data['initial'][:,:3],a.arrays(self.fixture_run/par['id'],'isolated_2')['final'])
            self.assertEqual(''.join(a.labels(data['initial'][:,3:],a.INDEX)),'MMM')
        self.assertTrue(any(not self.by[c['id']]['retained_E'] for c in d.stage_cases('components')))

    def test_surviving_cells_are_not_reset(self):
        for c in d.stage_cases('components'):
            folder=self.fixture_run/c['id']; value=a.arrays(folder/'assembly','checkpoint')['assembled']
            for at in range(1,6):
                data=a.arrays(folder,'replacement_%02d'%(at+1)); keep=[p for p in range(3) if p!=at%3]
                np.testing.assert_array_equal(value[:,keep],data['initial'][:,keep]); value=data['final']

    def test_common_logical_clock_and_final_replacement(self):
        for c in d.stage_cases('components'):
            record=d.read(self.fixture_run/c['id']/'result.json'); cursor=1180300
            for phase in record['phases']:
                self.assertEqual(phase['logical_interval'],[cursor,cursor+phase['requested_horizon']]); cursor+=phase['requested_horizon']
            self.assertEqual(cursor,1201800); self.assertTrue(record['outcome']['complete_carrier_replacement'])

    def test_both_observed_resistance_and_recovery_are_scored(self):
        resist=self.by[d.case(target='newcomer',mask=1)['id']]; recover=self.by[d.case(target='neighbour',mask=2)['id']]
        self.assertEqual(resist['first_cell_sampled_behavior'],'sampled_E_resistance')
        self.assertEqual(recover['first_cell_sampled_behavior'],'sampled_recovery_to_E'); self.assertTrue(recover['first_cell_M_observed'])

    def test_wrong_unselected_primary_edit_rejected(self):
        self.corrupt_assembly(lambda x:x['hybrid_before_refresh'].__setitem__((5,0),x['hybrid_before_refresh'][5,0]+1))

    def test_stale_derived_RNA_after_refresh_rejected(self):
        self.corrupt_assembly(lambda x:x['assembled'].__setitem__((8,0),x['before'][8,0]))

    def test_wrong_target_column_rejected(self):
        self.corrupt_assembly(lambda x:x['assembled'].__setitem__((7,2),x['after'][7,2]))

    def test_extra_assembly_file_rejected(self):
        with self.copied_case() as (run,folder):
            (folder/'assembly/extra.txt').write_text('unregistered'); checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))

    def test_wrong_trajectory_diagnostic_rejected(self):
        self.corrupt_result(lambda x:x['provenance']['trajectory_diagnostics'].update(first_non_E_bracket=[0,15]))

    def test_survivor_initial_mutation_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]+1))

    def test_clock_mutation_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_bad_logical_interval_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['logical_interval'].__setitem__(0,1180100))

    def test_duplicate_cell_identity_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(1,x['phases'][0]['setup']['cell_ids'][0]))

    def test_hidden_RNA_route_change_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup'].update(mirna_kd=0))

    def test_direct_RNA_diffusion_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['junction_diffusion'].__setitem__((5,0),1e-18))

    def test_changed_parent_hash_rejected(self):
        self.corrupt_result(lambda x:x['provenance'].update(parent_result_sha256='0'*64),d.case('onward',readout='open'))

    def test_extra_raw_phase_rejected(self):
        with self.copied_case() as (run,folder):
            shutil.copyfile(folder/'isolated_2.npz',folder/'extra.npz'); checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))

    def test_saved_outcome_mutation_rejected(self):
        self.corrupt_result(lambda x:x['outcome'].update(retained_E=False))

    def test_numerical_disagreement_rejected(self):
        by=copy.deepcopy(self.by); c=d.case(fine=True); by[c['id']]['first_cell_sampled_behavior']='sampled_recovery_to_E'
        cases=[self.primary,c]; checks=a.Checks(); data={x['id']:{'isolated_2':a.arrays(self.fixture_run/x['id'],'isolated_2')} for x in cases}
        self.assertFalse(a.p19.p18.p12.compare_fine(cases,by,data,checks)[0]['agree'])

    def test_positive_readout_control_disqualifies_chain(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case('onward',readout='rna',fine=f)['id']]['transmitted_E']=True
        row=next(x for x in a.contrasts(by,self.inherited,True)['component_grid'] if x['founder']=='written' and x['target']=='newcomer' and x['mask']==1)
        self.assertTrue(row['retained_E_both']); self.assertFalse(row['control_qualified_chain'])

    def test_inherited_capacity_and_wipe_required(self):
        for key in ('inherited_readout_capacity_qualified','inherited_isolated_200_wipe_negative'):
            inherited=copy.deepcopy(self.inherited); inherited[key]=False
            self.assertFalse(any(x['control_qualified_chain'] for x in a.contrasts(self.by,inherited,True)['component_grid']))

    def test_late_endpoint_alone_is_insufficient(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/self.primary['id']).unlink(); row=fixture_case(run,self.primary,'late'); out=row['result']['outcome']
            self.assertEqual(out['observations']['isolated_1']['patch_labels'],'EEE'); self.assertFalse(out['retained_E'])
            checks,_,_=self.audit_branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_late_recovery_separated_from_first_challenge(self):
        c=d.case(target='neighbour',mask=1)
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/c['id']).unlink(); row=fixture_case(run,c,'late_recovery'); out=row['result']['outcome']
            self.assertTrue(out['retained_E']); self.assertEqual(out['first_cell_sampled_behavior'],'no_E_recovery_by_300')
            checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values()))

    def test_negative_component_result_still_passes_technical_branch(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/self.primary['id']).unlink(); row=fixture_case(run,self.primary,'all_negative'); self.assertFalse(row['result']['outcome']['retained_E'])
            checks,_,_=self.audit_branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_worker_stage_and_history_rejected_before_integration(self):
        with self.copied_case() as (run,folder),patch.object(d,'check_run_path'),patch.object(d,'manifest',return_value=self.summary['hashes_sha256']):
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            summary=copy.deepcopy(self.summary); summary['stage']='controls'; d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'Wrong P21 stage'): r.worker(folder/'spec.json')
            summary.update(stage='components',predecessor_gate=False); d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'preflight'): r.worker(folder/'spec.json')

    def test_archive_references_and_distinct_execution_copies(self):
        self.assertTrue(all(self.integrity.values()))
        for name,meta in self.summary['inputs'].items(): self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for name in self.summary['hashes_sha256']: self.assertFalse((self.fixture_run/'frozen'/name).samefile(d.ROOT/name))

    def test_predecessor_reaudit_must_match_saved_report(self):
        with patch.object(a.p20,'analyze',return_value=self.inherited) as called,patch.object(d,'integrity',return_value={'all':True}):
            self.assertEqual(a.predecessor_audit(self.fixture_run),self.history); self.assertEqual(called.call_count,1)
        bad=copy.deepcopy(self.inherited); bad['quality_gate']=False
        with patch.object(a.p20,'analyze',return_value=bad),patch.object(d,'integrity',return_value={'all':True}):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])

if __name__=='__main__': unittest.main()
