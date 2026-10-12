"""P20 full synthetic panel, causal-contrast faults and fail-closed operations."""
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
import p20_design as d
import run_p20 as r
import analyze_p20 as a
import supervise_p20 as s

def test_root():
    value=os.environ.get('P20_TEST_ROOT')
    if not value: raise RuntimeError('Full P20 fixtures require external P20_TEST_ROOT')
    root=Path(value).resolve()
    if not root.is_relative_to(d.BASE): raise RuntimeError('P20 test data must remain in dedicated external store')
    return root

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.RateExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs):
        current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy(); replay=d.replay(c)
        if replay is not None and failure is None:
            src=run/'inputs'/replay; archived=a.arrays(src,name)
            np.testing.assert_array_equal(initial,archived['initial']); np.copyto(sim.cc_cells,archived['final'])
            meta=next(rec['clock'] for rec in d.read(src/'result.json')['phases'] if rec['phase']==name)
            return archived['times'],archived['concentrations'],{
                k:archived[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        if c['stage']=='renewal' and name.startswith('replacement'):
            success=c['newcomer']=='after' and failure!='all_negative'
            mark(range(3),'E' if success else 'M')
        if name=='contact':
            success=c['readout']=='open' and all(exp.z.GRN.state_char(x)=='E' for x in initial[:,:3].T)
            if success or failure=='positive_controls': mark(range(3,6),'E')
        if failure=='all_negative' and name.startswith('isolated'): mark(range(3),'M')
        if failure=='late_recovery' and name.startswith('isolated'): mark(range(3),'E')
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.000001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=[]; tick=0; proposal=2*stride
        while tick<total:
            step=min(cap,proposal,min(((tick//stride)+1)*stride,total)-tick,total-tick)
            steps.append(step); tick+=step
        steps=np.array(steps,dtype=np.int64); proposed=np.full(len(steps),proposal,dtype=np.int64)
        shots=np.array(list(range(0,total,stride))+[total],dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        if failure=='late' and name=='isolated_1':
            for at in range(-2,-7,-1): exp.z.GRN.set_very_tumor(values[at],0)
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(steps),sample_count=len(shots),capped_steps=int(np.count_nonzero(steps<proposed)),
            initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock),d.recovery.external_phases():
        out,provenance=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out,provenance); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestP20Operations(unittest.TestCase):
    def test_registration_and_independent_enumeration(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),64)
        self.assertEqual([len(d.stage_cases(x)) for x in d.STAGES],[16,48])
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),32)
        for c in d.fixed_cases(): self.assertEqual(d.replay(c),a.replay(c))
        self.assertEqual(d.read(d.HERE/'config.json'),d.FIXED)

    def test_changed_config_rejected(self):
        x=copy.deepcopy(d.FIXED); x['extra_interval']=900
        with self.assertRaises(ValueError): d.validate_config(x)

    def test_inherited_evidence_and_source_pinning(self):
        evidence=d.inherited_verification(); self.assertEqual(evidence['native']['tests'],1342)
        self.assertEqual(evidence['recovery']['tests'],58); d.source_check()
        self.assertEqual(len(d.manifest()),203)

    def test_old_globs_unchanged(self):
        self.assertEqual(len(d.recovery.prior_supervisor.verification_manifest()),264)
        self.assertEqual(d.recovery.prior_supervisor.verification_manifest(),
            d.read(d.recovery.OLD_JOB/'launch.json')['verification_hashes_sha256'])

    def test_incoming_draw_independent_derivation(self):
        M=np.ones((17,1))
        for at in range(1,6):
            cycle,pos=divmod(at,3)
            np.testing.assert_array_equal(d.incoming(M,cycle,pos),a.p19.incoming(M,cycle,pos))

    def test_output_and_discovery_confinement(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp); (job/'runner.log').write_text('Run artifacts: /tmp/foreign\n')
            with self.assertRaises(ValueError): s.discover_run(job)
            with self.assertRaises(ValueError): d.check_run_path(job)

    def test_no_new_case_below_reserve_or_after_budget(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(d,'space_available',return_value=False):
            out=r.run_worker(d.case(),Path(tmp),time.monotonic()+10,{})
            self.assertEqual(out['status'],'not_launched_disk'); self.assertEqual(list(Path(tmp).iterdir()),[])
            out=r.run_worker(d.case(),Path(tmp),time.monotonic()-1,{})
            self.assertEqual(out['status'],'not_launched_budget')

    def test_only_actual_output_filesystem_controls_reserve(self):
        path=Path('/mnt/workspaces/example'); usage=type('Disk',(),{'free':5*1024**3})()
        with patch.object(d.shutil,'disk_usage',return_value=usage) as call:
            self.assertTrue(d.space_available(path)); call.assert_called_once_with(path)
        usage.free-=1
        with patch.object(d.shutil,'disk_usage',return_value=usage): self.assertFalse(d.space_available(path))

    def test_no_queued_cases_after_observed_failure(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'run_worker',side_effect=lambda c,*args:dict(id=c['id'],execution_pass=False)) as call:
            summary={'cases':[]}
            self.assertFalse(r.execute_stage(d.stage_cases('renewal'),Path(tmp),summary,time.monotonic()+10,{}))
            self.assertEqual(call.call_count,2); self.assertEqual(len(summary['cases']),2)

    @contextmanager
    def job(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp); d.write_json(job/'status.json',dict(phase='launching'))
            (job/'verification.log').write_text('Ran 1 tests in 0.001s\n\nOK\n')
            yield job

    def supervise(self,job,returns,verify_error=None):
        with patch.object(s.signal,'signal'),patch.object(d,'verify_launch',side_effect=verify_error),\
             patch.object(d,'space_available',return_value=True),patch.object(s,'discover_run',return_value=None),\
             patch.object(s,'run_child',side_effect=returns) as child:
            fd=os.open(job/'lock',os.O_CREAT|os.O_RDWR,0o600); code=s.supervise(job,fd)
        return code,child.call_count,d.read(job/'status.json')

    def test_verification_failure_blocks_science(self):
        with self.job() as job:
            code,calls,status=self.supervise(job,[1]); self.assertEqual((code,calls),(1,1)); self.assertEqual(status['phase'],'failed')

    def test_missing_verification_evidence_blocks_science(self):
        with self.job() as job:
            (job/'verification.log').write_text('incomplete')
            code,calls,status=self.supervise(job,[0]); self.assertEqual((code,calls),(1,1)); self.assertIn('verification evidence',status['error'])

    def test_runner_failure_has_no_retry(self):
        with self.job() as job:
            code,calls,status=self.supervise(job,[0,124]); self.assertEqual((code,calls),(1,2)); self.assertIn('no retry',status['error'])

    def test_source_change_blocks_all_children(self):
        with self.job() as job:
            code,calls,status=self.supervise(job,[],RuntimeError('source changed'))
            self.assertEqual((code,calls),(1,0)); self.assertIn('source changed',status['error'])

    def test_owned_child_terminated_on_timeout(self):
        with self.job() as job,patch.object(s,'child_env',return_value={}),patch.object(s.subprocess,'Popen') as popen,\
             patch.object(s,'terminate_owned') as stop:
            proc=popen.return_value; proc.poll.return_value=None; proc.pid=42
            self.assertEqual(s.run_child(['synthetic'],job,'child.log',0,lambda pid:None),124)
            stop.assert_called_once_with(proc); self.assertTrue(popen.call_args.kwargs['start_new_session'])

    def test_all_four_localization_results_and_missing_data(self):
        inherited=dict(readout_capacity=dict(qualified=True),wipe_controls=[dict(extra=200,mode='isolated',negative_both=True)])
        for ab,ba,expected in ((True,False,'newcomer_preparation_alone_sufficient'),
                (False,True,'surviving_neighbour_preparation_alone_sufficient'),
                (True,True,'alternative_sufficient_routes'),(False,False,'joint_prepared_states_required_in_tested_contrast')):
            by={}
            for c in d.stage_cases('renewal'):
                value={(False,False):False,(True,True):True,(True,False):ab,(False,True):ba}[(c['newcomer']=='after',c['neighbours']=='after')]
                by[c['id']]=dict(available=True,retained_E=value)
            findings=a.contrasts(by,inherited)['localization']
            self.assertTrue(all(x['renewal_localization']==expected for x in findings))
            by.pop(d.case(newcomer='after',fine=True)['id'])
            self.assertEqual(a.contrasts(by,inherited)['localization'][0]['renewal_localization'],'unqualified')

class TestP20Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p20-software-',dir=test_root()); cls.addClassCleanup(cls.temp.cleanup)
        cls.job=Path(cls.temp.name)/'job'; cls.job.mkdir(); hashes=d.freeze(cls.job)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); d.archive_view(cls.fixture_run)
        (cls.fixture_run/'frozen').symlink_to(cls.job/'frozen',target_is_directory=True)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_byte_identical=True,prior_checks=65479,
            prior_cases=192,prior_calls=870,original_reaudit_count=1,archive_separate_mathematical_reaudit=False,
            reference_is_independent_backup=False,original_audit_file_rewritten=False)
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],hashes_sha256=hashes,
            inputs=d.input_manifest(),inherited_verification=d.inherited_verification(),predecessor_gate=True,
            predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),
            gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        cls.integrity=d.integrity(cls.fixture_run,cls.summary)
        if not all(cls.integrity.values()): raise AssertionError(cls.integrity)
        with redirect_stdout(io.StringIO()),patch.object(d,'integrity',return_value=cls.integrity):
            for stage in d.STAGES:
                for c in d.stage_cases(stage): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary); gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate)
                cls.summary['gates'][stage]=gate; cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
            cls.summary.update(stage='finished',all_execution_valid=True,completion_reason='all_registered_stages_completed')
            d.write_json(cls.fixture_run/'summary.json',cls.summary)
            with patch.object(a,'predecessor_audit',return_value=cls.history): cls.report=a.analyze(cls.fixture_run)
        cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}; cls.primary=d.case(newcomer='after')
        cls.inherited=d.read(d.P19_RUN/'independent_audit.json')

    def branch(self,run,c):
        checks=a.Checks(); result,data=a.branch(run/c['id'],c,checks); return checks,result,data

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p20-unit-',dir=test_root()) as tmp:
            run=Path(tmp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            for c in d.stage_cases('renewal'): (run/c['id']).symlink_to(self.fixture_run/c['id'],target_is_directory=True)
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
            checks,_,_=self.branch(run,c); self.assertFalse(all(checks.rows.values()))

    def corrupt_array(self,name,change,c=None):
        c=c or self.primary
        with self.copied_case(c) as (run,folder):
            value=a.arrays(folder,name); change(value); np.savez_compressed(folder/(name+'.npz'),**value)
            result=d.read(folder/'result.json'); next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',result); checks,_,_=self.branch(run,c); self.assertFalse(all(checks.rows.values()))

    def test_full_panel_and_checks(self):
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['completed_cases'],64)
        self.assertEqual(self.report['integration_calls'],256); self.assertEqual(len(self.report['fine_comparisons']),32)
        self.assertTrue(self.report['all_fine_agree']); self.assertEqual([self.summary['gates'][s]['integration_calls'] for s in d.STAGES],[112,256])
        self.assertTrue(all(x['renewal_localization']=='newcomer_preparation_alone_sufficient' for x in self.report['localization']))

    def test_full_column_transfer_and_discarded_neighbour(self):
        for c in d.stage_cases('renewal'):
            folder=self.fixture_run/c['id']; checkpoint=a.arrays(folder/'assembly','checkpoint')
            for pos,age in enumerate((c['newcomer'],c['neighbours'],c['neighbours'])):
                np.testing.assert_array_equal(checkpoint['assembled'][:,pos],checkpoint[age][:,pos])
            first=a.arrays(folder,'replacement_02'); np.testing.assert_array_equal(first['initial'][:,[0,2]],checkpoint['assembled'][:,[0,2]])
            self.assertFalse(np.array_equal(first['initial'][:,1],checkpoint['assembled'][:,1]))

    def test_exact_historical_replays(self):
        cases=phases=0
        for c in d.fixed_cases():
            if d.replay(c) is None: continue
            checks,_,data=self.branch(self.fixture_run,c); cases+=1; phases+=len(data)
            selected=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(selected),33*len(data)); self.assertTrue(all(selected))
        self.assertEqual((cases,phases),(32,128))

    def test_common_clock_and_complete_lineage_replacement(self):
        for c in d.stage_cases('renewal'):
            record=d.read(self.fixture_run/c['id']/'result.json'); cursor=1180300
            self.assertEqual([p['requested_horizon'] for p in record['phases']],[300]*5+[10000]*2)
            for rec in record['phases']:
                self.assertEqual(rec['logical_interval'],[cursor,cursor+rec['requested_horizon']]); cursor+=rec['requested_horizon']
            self.assertEqual(cursor,1201800); self.assertTrue(record['outcome']['complete_carrier_replacement'])
            self.assertFalse(set(record['phases'][-1]['setup']['cell_ids'])&set(record['outcome']['fork_ids']+record['outcome']['original_ids']))

    def test_actual_parents_including_failures_used_in_all_readouts(self):
        for c in d.stage_cases('onward'):
            contact=a.arrays(self.fixture_run/c['id'],'contact'); parent=a.arrays(self.fixture_run/d.parent(c)['id'],'isolated_2')
            np.testing.assert_array_equal(contact['initial'][:,:3],parent['final'])
            self.assertEqual(''.join(a.labels(contact['initial'][:,3:],a.INDEX)),'MMM')
            self.assertEqual(d.read(self.fixture_run/c['id']/'result.json')['phases'][0]['logical_interval'],[1201800,1221800])
        self.assertTrue(any(not self.by[c['id']]['retained_E'] for c in d.stage_cases('renewal')))

    def test_every_survivor_continues_without_reset(self):
        for c in d.stage_cases('renewal'):
            value=a.arrays(self.fixture_run/c['id']/'assembly','checkpoint')['assembled']
            for at in range(1,6):
                data=a.arrays(self.fixture_run/c['id'],'replacement_%02d'%(at+1)); keep=[p for p in range(3) if p!=at%3]
                np.testing.assert_array_equal(data['initial'][:,keep],value[:,keep]); value=data['final']
            np.testing.assert_array_equal(a.arrays(self.fixture_run/c['id'],'isolated_1')['initial'],value)

    def test_bad_assembly_caught_even_with_refreshed_hashes(self):
        with self.copied_case() as (run,folder):
            path=folder/'assembly'; checkpoint=a.arrays(path,'checkpoint'); checkpoint['assembled'][7,0]=checkpoint['before'][7,0]
            np.savez_compressed(path/'checkpoint.npz',**checkpoint); meta=d.read(path/'assembly.json')
            meta['checkpoint_sha256']=d.digest(path/'checkpoint.npz'); d.write_json(path/'assembly.json',meta)
            result=d.read(folder/'result.json'); result['provenance']=dict(assembly=meta,assembly_metadata_sha256=d.digest(path/'assembly.json'))
            d.write_json(folder/'result.json',result); checks,_,_=self.branch(run,self.primary)
            self.assertFalse(checks.rows[self.primary['id']+'/assembly/assembled'])

    def test_extra_assembly_component_rejected(self):
        with self.copied_case() as (run,folder):
            (folder/'assembly/unregistered.txt').write_text('extra')
            checks,_,_=self.branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_surviving_neighbour_reset_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]+1))

    def test_wrong_logical_reanchor_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['logical_interval'].__setitem__(0,1180100))

    def test_clock_corruption_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_duplicate_identity_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(1,x['phases'][0]['setup']['cell_ids'][0]))

    def test_unrestored_RNA_route_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup'].update(mirna_kd=0))

    def test_direct_RNA_diffusion_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['junction_diffusion'].__setitem__((5,0),1e-18))

    def test_wrong_parent_hash_rejected(self):
        self.corrupt_result(lambda x:x['provenance'].update(parent_result_sha256='0'*64),d.case('onward',newcomer='after',readout='open'))

    def test_changed_saved_outcome_rejected(self):
        self.corrupt_result(lambda x:x['outcome'].update(retained_E=False))

    def test_extra_phase_rejected(self):
        with self.copied_case() as (run,folder):
            shutil.copyfile(folder/'isolated_2.npz',folder/'extra.npz')
            checks,_,_=self.branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_fine_disagreement_rejected(self):
        by=copy.deepcopy(self.by); c=d.case(newcomer='after',fine=True); by[c['id']]['retained_E']=False
        cases=[self.primary,c]; checks=a.Checks()
        data={x['id']:{'isolated_2':a.arrays(self.fixture_run/x['id'],'isolated_2')} for x in cases}
        result=a.p19.p18.p12.compare_fine(cases,by,data,checks); self.assertFalse(result[0]['agree'])

    def test_positive_readout_controls_block_chain(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case('onward',newcomer='after',readout='rna',fine=f)['id']]['transmitted_E']=True
        row=next(x for x in a.contrasts(by,self.inherited)['cell_state_grid'] if x['founder']=='written' and x['newcomer']=='after' and x['neighbours']=='before')
        self.assertTrue(row['retained_E_both']); self.assertFalse(row['control_qualified_chain'])

    def test_failed_sham_blocks_localization(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(newcomer='after',neighbours='after',fine=f)['id']]['retained_E']=False
        self.assertEqual(a.contrasts(by,self.inherited)['localization'][0]['renewal_localization'],'unqualified')

    def test_inherited_controls_required_for_chain(self):
        inherited=copy.deepcopy(self.inherited); inherited['readout_capacity']['qualified']=False
        self.assertFalse(any(x['control_qualified_chain'] for x in a.contrasts(self.by,inherited)['cell_state_grid']))
        inherited=copy.deepcopy(self.inherited)
        for row in inherited['wipe_controls']: row['negative_both']=False
        self.assertFalse(any(x['control_qualified_chain'] for x in a.contrasts(self.by,inherited)['cell_state_grid']))

    def test_endpoint_label_does_not_override_late_failure(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/self.primary['id']).unlink(); row=fixture_case(run,self.primary,'late')
            out=row['result']['outcome']; self.assertEqual(out['observations']['isolated_1']['patch_labels'],'EEE')
            self.assertFalse(out['retained_E']); checks,_,_=self.branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_late_recovery_does_not_erase_first_cell_failure(self):
        c=d.case(neighbours='after')
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/c['id']).unlink(); row=fixture_case(run,c,'late_recovery'); out=row['result']['outcome']
            self.assertTrue(out['retained_E']); self.assertFalse(out['first_cell_stable_E_after_second'])
            checks,_,_=self.branch(run,c); self.assertTrue(all(checks.rows.values()))

    def test_negative_scientific_outcome_passes_technical_audit(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/self.primary['id']).unlink(); row=fixture_case(run,self.primary,'all_negative')
            self.assertFalse(row['result']['outcome']['retained_E'])
            checks,_,_=self.branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_worker_wrong_stage_or_missing_history_fails_before_integration(self):
        with self.copied_case() as (run,folder),patch.object(d,'check_run_path'),patch.object(d,'manifest',return_value=self.summary['hashes_sha256']):
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            summary=copy.deepcopy(self.summary); summary['stage']='onward'; d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'Wrong P20 stage'): r.worker(folder/'spec.json')
            summary.update(stage='renewal',predecessor_gate=False); d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'preflight'): r.worker(folder/'spec.json')

    def test_archive_references_and_execution_copies_are_distinct(self):
        self.assertTrue(all(self.integrity.values()))
        for name,meta in self.summary['inputs'].items():
            self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source'])); self.assertEqual(meta['storage'],'reference_directory_v1')
        for name in self.summary['hashes_sha256']: self.assertFalse((self.fixture_run/'frozen'/name).samefile(d.ROOT/name))

    def test_predecessor_reaudit_exact_match_required(self):
        saved=self.inherited
        with patch.object(a,'reconstructed_p19',return_value=saved) as call,patch.object(d,'integrity',return_value={'all':True}):
            report=a.predecessor_audit(self.fixture_run); self.assertEqual(report,self.history); self.assertEqual(call.call_count,1)
        bad=copy.deepcopy(saved); bad['quality_gate']=False
        with patch.object(a,'reconstructed_p19',return_value=bad),patch.object(d,'integrity',return_value={'all':True}):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])

if __name__=='__main__': unittest.main()
