"""Synthetic complete programme and independent P22 intervention/fault checks.

Synthetic trajectories exercise software; they are not scientific predictions.
Only the ODE integrator is replaced. Native setup, algebraic refresh, saved
arrays, clocks, lineage, observations and the independent audit remain active.
"""
from contextlib import contextmanager, redirect_stdout
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
import p22_design as d
import run_p22 as r
import analyze_p22 as a
import supervise_p22 as s

def fixture_root():
    value=os.environ.get('P22_TEST_ROOT')
    if not value: raise RuntimeError('Full P22 fixtures require external P22_TEST_ROOT')
    root=Path(value).resolve()
    if not root.is_relative_to(d.BASE): raise RuntimeError('P22 fixtures outside dedicated external store')
    return root

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.RateExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs): current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy(); reference=d.replay(c)
        archive_source=None
        if reference and name in reference['phases'] and failure is None:
            archive_source=run/'inputs'/reference['source']
        if c['panel']=='timing_controls' and not name.startswith('challenge') and failure is None:
            archive_source=run/'inputs/p21'/d.reference(c)
        if archive_source is not None:
            archived=a.arrays(archive_source,name); np.testing.assert_array_equal(initial,archived['initial'])
            np.copyto(sim.cc_cells,archived['final'])
            meta=next(x['clock'] for x in d.read(archive_source/'result.json')['phases'] if x['phase']==name)
            return archived['times'],archived['concentrations'],{k:archived[k] for k in
                ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=[]; tick=0; proposed_step=2*stride
        while tick<total:
            step=min(cap,proposed_step,min(((tick//stride)+1)*stride,total)-tick,total-tick)
            steps.append(step); tick+=step
        steps=np.asarray(steps,dtype=np.int64); proposed=np.full(len(steps),proposed_step,dtype=np.int64)
        shots=np.asarray(list(range(0,total,stride))+[total],dtype=np.int64); times=shots*base
        def mark(indices,label,value=None):
            state=sim.cc_cells if value is None else value
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(state,i)
        success=c['route'] not in ('none','newcomer_zebmrna','neighbour_mir200') and failure!='all_negative'
        if c['panel']=='robust' and c['draw']=='heldout_17022' and c['replacements']==11 and c['route']=='newcomer_protein': success=False
        if c['panel']=='timing' and c['window'] in ('rna_middle','rna_full'): success=False
        if c['panel']=='timing_controls' and name.startswith('challenge') and failure is None:
            archived=a.arrays(run/'inputs/p21'/d.reference(c),'replacement_02'); start=(int(name[-2:])-1)*100
            values=np.empty((len(times),17,3))
            for i in range(17):
                for j in range(3): values[:,i,j]=np.interp(times+start,archived['times'],archived['concentrations'][:,i,j])
            np.testing.assert_array_equal(values[0],initial); np.copyto(sim.cc_cells,values[-1])
        else:
            if not c['readout'] and (name.startswith('replacement') or name.startswith('challenge')):
                mark(range(3),'E' if success else 'M')
            if name=='contact':
                donor_E=all(exp.z.GRN.state_char(x)=='E' for x in initial[:,:3].T)
                if (c['readout']=='open' and donor_E) or failure=='positive_controls': mark(range(3,6),'E')
            if failure=='all_negative' and name.startswith('isolated'): mark(range(3),'M')
            if failure=='late_recovery' and name.startswith('isolated'): mark(range(3),'E')
            sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.000001*np.arange(len(exp.ids))
            values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
            if name=='replacement_02' and success and c['route'].startswith('neighbour'):
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

class TestP22Operations(unittest.TestCase):
    def test_independent_registration_and_fixed_counts(self):
        cases=d.fixed_cases(); self.assertEqual(cases,a.expected_cases()); self.assertEqual(len(cases),544)
        self.assertEqual(len({c['id'] for c in cases}),544); self.assertEqual(sum(c['fine'] for c in cases),272)
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[16,16,16,80,80,336])
        self.assertEqual(sum(c['replacements'] for c in cases if not c['readout']),1328)
        self.assertEqual(sum(3 for c in cases if c['readout']),1008)
        for c in cases:
            self.assertEqual(d.replay(c),a.replay(c)); self.assertEqual(d.source(c),a.source(c))
            self.assertEqual(d.window_routes(c),a.window_routes(c))
            if c['readout']: self.assertIn(d.parent(c),cases); self.assertEqual(d.parent(c),a.parent(c))
        self.assertEqual(d.read(d.HERE/'config.json'),d.FIXED)

    def test_changed_configuration_rejected(self):
        value=copy.deepcopy(d.FIXED); value['timing_boundaries']=[0,50,200,300]
        with self.assertRaises(ValueError): d.validate_config(value)
        with self.assertRaises(ValueError): d.stage_cases('unregistered')

    def test_inherited_evidence_and_unchanged_legacy_globs(self):
        evidence=d.inherited_verification(); self.assertEqual(evidence['p21']['tests'],51)
        self.assertEqual(evidence['legacy']['p20']['tests'],42)
        self.assertEqual(evidence['legacy']['legacy']['native']['tests'],1342)
        self.assertEqual(evidence['legacy']['legacy']['recovery']['tests'],58)
        self.assertEqual(len(d.manifest()),218); self.assertEqual(len(d.input_paths()),14781); d.source_check()
        self.assertEqual(d.recovery.prior_supervisor.verification_manifest(),d.read(d.recovery.OLD_JOB/'launch.json')['verification_hashes_sha256'])

    def test_all_routes_native_refresh_and_known_P21_assemblies(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,redirect_stdout(io.StringIO()):
            exp=r.RateExperiment(Path(tmp),dict(id='RNA-verification',fine=False))
            for founder in ('written','ordinary'):
                for fine in (False,True):
                    for route in d.ROUTES:
                        c=d.case(founder=founder,route=route,fine=fine)
                        checkpoint=a.arrays(d.P21_RUN/d.source(c)/'assembly','checkpoint'); before,after=checkpoint['before'],checkpoint['after']
                        mixed=r.mix_primary(before,after,c); pos,selected=d.ROUTES[route]
                        for j in range(3):
                            for i in range(17): self.assertEqual(mixed[i,j],after[i,j] if j==pos and i in selected else before[i,j])
                        refreshed=r.native_refresh(exp,mixed,['a','b','c']); np.testing.assert_array_equal(refreshed,a.canonical_binding(mixed))
                        np.testing.assert_array_equal(refreshed[list(range(8))+[16]],mixed[list(range(8))+[16]])
                        if route in d.KNOWN:
                            np.testing.assert_array_equal(refreshed,a.arrays(d.P21_RUN/d.reference(c)/'assembly','checkpoint')['assembled'])

    def test_refresh_cannot_modify_primary(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp,redirect_stdout(io.StringIO()):
            exp=r.RateExperiment(Path(tmp),dict(id='refresh-fault',fine=False))
            value=a.arrays(d.P21_RUN/d.source(d.case())/'assembly','checkpoint')['before']
            def bad(cc,*args): cc[5,0]+=1
            with patch.object(exp.z.GRN,'compute_bound_complex_concs_simple',side_effect=bad):
                with self.assertRaisesRegex(RuntimeError,'primary'): r.native_refresh(exp,value,['a','b','c'])

    def test_invalid_source_state_rejected(self):
        before=np.ones((17,3)); before[4]=72; before[16]=0; after=before.copy(); after[0,0]=np.nan
        with self.assertRaises(ValueError): r.mix_primary(before,after,d.case())
        after=before.copy(); after[16,0]=1
        with self.assertRaises(ValueError): r.mix_primary(before,after,d.case())

    def test_draws_independent_legacy_prefix_and_only_protein_changed(self):
        M=np.arange(1,18,dtype=float).reshape(17,1)
        self.assertEqual(d.draw_book(),a.expected_draws()); self.assertEqual(d.draw_book(),d.read(d.HERE/'draws.json'))
        for draw in d.DRAWS:
            for at in range(1,12):
                c=d.case(draw=draw); x=d.incoming(M,draw,at); np.testing.assert_array_equal(x,a.incoming(M,c,at))
                np.testing.assert_array_equal(np.delete(x,7,axis=0),np.delete(M,7,axis=0))
                self.assertTrue(.75<=x[7,0]/M[7,0]<=1.25)
                if draw=='legacy': np.testing.assert_array_equal(x,a.p19.incoming(M,*divmod(at,3)))
        for args in [('legacy',0),('legacy',12),('new',1)]:
            with self.assertRaises(ValueError): d.random_word(*args)

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
            summary={'cases':[]}; self.assertFalse(r.execute_stage(d.stage_cases('replay'),Path(tmp),summary,time.monotonic()+10,{}))
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

class TestP22Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p22-software-',dir=fixture_root()); cls.addClassCleanup(cls.temp.cleanup)
        cls.job=Path(cls.temp.name)/'job'; cls.job.mkdir(); hashes=d.freeze(cls.job)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); d.archive_view(cls.fixture_run)
        (cls.fixture_run/'frozen').symlink_to(cls.job/'frozen',target_is_directory=True)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_byte_identical=True,prior_checks=87985,prior_cases=288,prior_calls=1152,
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
        cls.inherited=d.read(d.P21_RUN/'independent_audit.json')

    def audit_branch(self,run,c):
        checks=a.Checks(); result,data=a.branch(run/c['id'],c,checks); return checks,result,data

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p22-unit-',dir=fixture_root()) as tmp:
            run=Path(tmp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            for stage in d.STAGES[:-1]:
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

    def test_complete_programme_and_numerical_pairs(self):
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['completed_cases'],544)
        self.assertEqual(self.report['integration_calls'],2944); self.assertEqual(len(self.report['fine_comparisons']),272)
        self.assertTrue(self.report['all_fine_agree'])
        self.assertEqual([self.summary['gates'][s]['integration_calls'] for s in d.STAGES],[112,224,368,1088,1936,2944])
        self.assertEqual([len(self.report[k]) for k in ('rna_grid','rna_interpretations','timing_grid','robustness_grid')],[16,4,48,48])

    def test_synthetic_RNA_findings_differ_by_location(self):
        for row in self.report['rna_interpretations']:
            expected=1 if row['target']=='newcomer' else 2
            self.assertEqual(row['minimal_tested_rescue_masks'],[expected])
            self.assertEqual(row['miR200_removal_loses_rescue'],expected==1)
            self.assertEqual(row['Zeb_mRNA_removal_loses_rescue'],expected==2)

    def test_joint_and_alternative_RNA_sufficiency_interpretations(self):
        for success,expected in (((),[3]),(('newcomer_mir200','newcomer_zebmrna'),[1,2])):
            by=copy.deepcopy(self.by)
            for fine in (False,True):
                for route in ('newcomer_mir200','newcomer_zebmrna'):
                    by[d.case(route=route,fine=fine)['id']]['retained_E']=route in success
            row=next(x for x in a.contrasts(by,self.inherited,True)['rna_interpretations'] if x['target']=='newcomer' and x['founder']=='written')
            self.assertEqual(row['minimal_tested_rescue_masks'],expected)
        self.assertFalse(any(x['control_qualified_rescue'] for x in a.contrasts(self.by,self.inherited,False)['rna_grid']))

    def test_new_draw_baseline_success_does_not_count_as_preparation_rescue(self):
        by=copy.deepcopy(self.by)
        for f in (False,True):
            by[d.case('robust',route='none',draw='heldout_17021',fine=f)['id']]['retained_E']=True
        rows=[x for x in a.contrasts(by,self.inherited,True)['robustness_grid'] if x['founder']=='written' and x['draw']=='heldout_17021' and x['replacements']==5]
        self.assertTrue(any(x['retained_E_both'] for x in rows)); self.assertFalse(any(x['preparation_specific_rescue'] for x in rows))

    def test_synthetic_long_challenge_failure_is_technically_valid(self):
        row=next(x for x in self.report['robustness_grid'] if x['founder']=='written' and x['route']=='newcomer_protein' and x['draw']=='heldout_17022' and x['replacements']==11)
        self.assertTrue(row['retained_E_false_both']); self.assertFalse(row['qualified_chain']); self.assertTrue(self.report['quality_gate'])

    def test_all_208_assemblies_refreshed_once_and_identity_preserved(self):
        count=0
        for stage in d.STAGES[:-1]:
            for c in d.stage_cases(stage):
                folder=self.fixture_run/c['id']; data=a.arrays(folder/'assembly','checkpoint'); record=d.read(folder/'result.json')
                np.testing.assert_array_equal(data['assembled'],a.canonical_binding(data['hybrid_before_refresh']))
                meta=d.read(folder/'assembly/assembly.json'); self.assertEqual(meta,record['provenance']['assembly'])
                self.assertEqual(meta['cell_ids'],record['outcome']['fork_ids'])
                self.assertFalse(set(meta['cell_ids'])&set(record['phases'][-1]['setup']['cell_ids'])); count+=1
        self.assertEqual(count,208)

    def test_historical_controls_and_long_prefix_replay_all_arrays(self):
        cases=phases=0
        for c in d.fixed_cases():
            ref=d.replay(c)
            if not ref: continue
            checks,_,_=self.audit_branch(self.fixture_run,c); cases+=1; phases+=len(ref['phases'])
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),33*len(ref['phases'])); self.assertTrue(all(replay))
        self.assertEqual((cases,phases),(80,336))

    def test_segmentation_controls_qualified_and_one_disagreement_blocks(self):
        self.assertTrue(all(x['qualified'] for x in self.report['stages']['onward']['timing_controls']))
        by=copy.deepcopy(self.by); c=d.case('timing_controls',route='newcomer_protein')
        by[c['id']]['observations']['replacement_02']['stable_E'][0]=False
        self.assertFalse(all(x['qualified'] for x in a.timing_controls(by)))

    def test_timing_common_grid_continuity_and_independent_reconstruction(self):
        for c in d.stage_cases('timing_controls')+d.stage_cases('timing'):
            folder=self.fixture_run/c['id']; data={n:a.arrays(folder,n) for n in ['challenge_%02d'%i for i in (1,2,3)]}
            made=r.first_challenge(folder,c); expected=a.first_challenge(data,c)
            for k in made: np.testing.assert_array_equal(made[k],expected[k])
            np.testing.assert_array_equal(made['times'],np.arange(0,301,15))
            for i in (1,2): np.testing.assert_array_equal(data['challenge_%02d'%i]['final'],data['challenge_%02d'%(i+1)]['initial'])
            self.assertEqual(len(made['times']),21)

    def test_timing_panels_have_no_onward_claim(self):
        self.assertFalse(any(c['panel'].startswith('timing') for c in d.stage_cases('onward')))
        self.assertFalse(any(x['onward_assayed'] or x['qualified_chain'] for x in self.report['timing_grid']))
        self.assertTrue(any(x['loss_of_retention_vs_open'] for x in self.report['timing_grid']))

    def test_RNA_block_retains_ions_and_isolation_cuts_all_junctions(self):
        for window in d.WINDOWS:
            c=d.case('timing',route='newcomer_rna',window=window); folder=self.fixture_run/c['id']
            for number,route in enumerate(d.window_routes(c),1):
                x=a.arrays(folder,'challenge_%02d'%number)
                if route=='isolated': self.assertFalse(x['junction_diffusion'].any())
                else: self.assertTrue(x['junction_diffusion'][:4].any())
                self.assertFalse(x['junction_diffusion'][4:].any())
            checks,_,_=self.audit_branch(self.fixture_run,c); self.assertTrue(all(checks.rows.values()))

    def test_every_assayed_parent_including_failures_has_three_readouts(self):
        parents=set()
        for c in d.stage_cases('onward'):
            x=a.arrays(self.fixture_run/c['id'],'contact'); par=d.parent(c); parents.add(par['id'])
            np.testing.assert_array_equal(x['initial'][:,:3],a.arrays(self.fixture_run/par['id'],'isolated_2')['final'])
            self.assertEqual(''.join(a.labels(x['initial'][:,3:],a.INDEX)),'MMM')
        self.assertEqual(len(parents),112); self.assertTrue(any(not self.by[p]['retained_E'] for p in parents))

    def test_survivors_never_reset_and_four_cycles_complete(self):
        for c in d.stage_cases('robust'):
            folder=self.fixture_run/c['id']; value=a.arrays(folder/'assembly','checkpoint')['assembled']
            for at in range(1,c['replacements']+1):
                data=a.arrays(folder,'replacement_%02d'%(at+1)); keep=[p for p in range(3) if p!=at%3]
                np.testing.assert_array_equal(value[:,keep],data['initial'][:,keep]); value=data['final']
            record=d.read(folder/'result.json'); cursor=1180300
            for phase in record['phases']:
                self.assertEqual(phase['logical_interval'],[cursor,cursor+phase['requested_horizon']]); cursor+=phase['requested_horizon']
            self.assertEqual(cursor,1203600 if c['replacements']==11 else 1201800)
            cycle=3 if c['replacements']==11 else 1
            self.assertEqual(record['phases'][-1]['setup']['cell_ids'],[d.new_id(c,cycle,i) for i in range(3)])

    def test_both_resistance_and_recovery_scored(self):
        self.assertEqual(self.by[d.case()['id']]['first_cell_sampled_behavior'],'sampled_E_resistance')
        rec=self.by[d.case(route='neighbour_zebmrna')['id']]
        self.assertEqual(rec['first_cell_sampled_behavior'],'sampled_recovery_to_E'); self.assertTrue(rec['first_cell_M_observed'])

    def test_wrong_unselected_RNA_edit_rejected(self):
        self.corrupt_assembly(lambda x:x['hybrid_before_refresh'].__setitem__((6,0),x['hybrid_before_refresh'][6,0]+1))

    def test_wrong_refresh_rejected(self):
        self.corrupt_assembly(lambda x:x['assembled'].__setitem__((8,0),x['assembled'][8,0]+1))

    def test_wrong_target_column_rejected(self):
        self.corrupt_assembly(lambda x:x['assembled'].__setitem__((5,2),x['after'][5,2]))

    def test_wrong_trajectory_diagnostic_rejected(self):
        self.corrupt_result(lambda x:x['provenance']['trajectory_diagnostics'].update(first_non_E_bracket=[0,15]))

    def test_survivor_mutation_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]+1))

    def test_wrong_incoming_draw_rejected(self):
        c=d.case('robust',route='newcomer_rna',draw='heldout_17021',replacements=11)
        self.corrupt_array('replacement_12',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]+1),c)

    def test_clock_mutation_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_segment_boundary_mutation_rejected(self):
        c=d.case('timing',route='newcomer_rna',window='rna_middle')
        self.corrupt_array('challenge_02',lambda x:x['initial'].__setitem__((7,0),x['initial'][7,0]+1),c)

    def test_segment_sample_omission_rejected(self):
        c=d.case('timing',route='newcomer_rna',window='rna_middle')
        with self.copied_case(c) as (run,folder):
            data=a.arrays(folder,'challenge_02'); data['times'][1]=6; np.savez_compressed(folder/'challenge_02.npz',**data)
            with self.assertRaisesRegex(ValueError,'sampling grid'): r.first_challenge(folder,c)
            with self.assertRaisesRegex(ValueError,'common challenge sample'):
                data['times'][3]=16
                a.first_challenge({n:data if n=='challenge_02' else a.arrays(folder,n) for n in ('challenge_01','challenge_02','challenge_03')},c)

    def test_segment_duration_and_route_rejected(self):
        c=d.case('timing',route='newcomer_rna',window='rna_middle')
        self.corrupt_result(lambda x:x['phases'][1].update(requested_horizon=99),c)
        self.corrupt_result(lambda x:x['phases'][1]['setup'].update(mirna_kd=1.25e-14),c)

    def test_wrong_logical_epoch_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['logical_interval'].__setitem__(0,1180100))

    def test_duplicate_or_old_carrier_identity_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(1,x['phases'][0]['setup']['cell_ids'][0]))
        c=d.case('robust',route='newcomer_rna',draw='heldout_17021',replacements=11)
        self.corrupt_result(lambda x:x['phases'][-1]['setup']['cell_ids'].__setitem__(0,d.new_id(c,1,0)),c)

    def test_direct_RNA_diffusion_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['junction_diffusion'].__setitem__((5,0),1e-18))

    def test_actual_parent_hash_rejected(self):
        self.corrupt_result(lambda x:x['provenance'].update(parent_result_sha256='0'*64),d.case(readout='open'))

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
        for route in ('rna','cut'):
            by=copy.deepcopy(self.by)
            for f in (False,True): by[d.case(readout=route,fine=f)['id']]['transmitted_E']=True
            row=next(x for x in a.contrasts(by,self.inherited,True)['rna_grid'] if x['founder']=='written' and x['target']=='newcomer' and x['mask']==1)
            self.assertTrue(row['retained_E_both']); self.assertFalse(row['qualified_chain'])

    def test_inherited_capacity_and_wipe_required(self):
        for key in ('inherited_readout_capacity_qualified','inherited_wipe_qualified'):
            inherited=copy.deepcopy(self.inherited); inherited[key]=False
            report=a.contrasts(self.by,inherited,True)
            self.assertFalse(any(x['qualified_chain'] for x in report['rna_grid']+report['robustness_grid']))

    def test_late_endpoint_alone_insufficient(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/self.primary['id']).unlink(); row=fixture_case(run,self.primary,'late'); out=row['result']['outcome']
            self.assertEqual(out['observations']['isolated_1']['patch_labels'],'EEE'); self.assertFalse(out['retained_E'])
            checks,_,_=self.audit_branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_late_recovery_distinct_from_first_challenge(self):
        c=d.case(route='neighbour_mir200')
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/c['id']).unlink(); row=fixture_case(run,c,'late_recovery'); out=row['result']['outcome']
            self.assertTrue(out['retained_E']); self.assertEqual(out['first_cell_sampled_behavior'],'no_E_recovery_by_300')
            checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values()))

    def test_negative_RNA_outcome_still_passes_technical_audit(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/self.primary['id']).unlink(); row=fixture_case(run,self.primary,'all_negative'); self.assertFalse(row['result']['outcome']['retained_E'])
            checks,_,_=self.audit_branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_worker_stage_and_history_rejected_before_integration(self):
        with self.copied_case() as (run,folder),patch.object(d,'check_run_path'),patch.object(d,'manifest',return_value=self.summary['hashes_sha256']):
            (run/'frozen').symlink_to(self.fixture_run/'frozen',target_is_directory=True)
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            summary=copy.deepcopy(self.summary); summary['stage']='replay'; d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'Wrong P22 stage'): r.worker(folder/'spec.json')
            summary.update(stage='rna',predecessor_gate=False); d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'preflight'): r.worker(folder/'spec.json')

    def test_archive_references_and_distinct_execution_copies(self):
        self.assertTrue(all(self.integrity.values()))
        for name,meta in self.summary['inputs'].items(): self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for name in self.summary['hashes_sha256']: self.assertFalse((self.fixture_run/'frozen'/name).samefile(d.ROOT/name))

    def test_predecessor_reaudit_must_match_saved_report(self):
        with patch.object(a.p21,'analyze',return_value=self.inherited) as called,patch.object(d,'integrity',return_value={'all':True}):
            self.assertEqual(a.predecessor_audit(self.fixture_run),self.history); self.assertEqual(called.call_count,1)
        bad=copy.deepcopy(self.inherited); bad['quality_gate']=False
        with patch.object(a.p21,'analyze',return_value=bad),patch.object(d,'integrity',return_value={'all':True}):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])

if __name__=='__main__': unittest.main()
