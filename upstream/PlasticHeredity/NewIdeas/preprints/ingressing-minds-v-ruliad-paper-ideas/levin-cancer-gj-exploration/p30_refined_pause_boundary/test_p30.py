"""Full synthetic P30 panel and meaningful faults; no scientific predictions."""
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
import p30_design as d
import run_p30 as r
import analyze_p30 as a
import supervise_p30 as s

def fixture_root():
    value=os.environ.get('P30_TEST_ROOT')
    if not value: raise RuntimeError('Full P30 fixtures require external P30_TEST_ROOT')
    root=Path(value).resolve()
    if not root.is_relative_to(d.BASE): raise RuntimeError('P30 fixtures outside dedicated external store')
    return root

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.ResolutionExperiment(folder,c)
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs): current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy(); reference=d.replay(c)
        if reference and failure is None:
            archived=a.arrays(run/'inputs'/reference,name)
            np.testing.assert_array_equal(initial,archived['initial']); np.copyto(sim.cc_cells,archived['final'])
            meta=next(x['clock'] for x in d.read(run/'inputs'/reference/'result.json')['phases'] if x['phase']==name)
            return archived['times'],archived['concentrations'],{k:archived[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        # For the four P29 schedules, preserve real trajectory observations at
        # both new resolutions. Other schedules share the same archived prefix
        # only until their prescribed route first differs. The clock is fake.
        template=None
        if not c['readout'] and c['draw']=='heldout_17021' and failure is None:
            choices=('baseline','pause_0_5','pause_0_25','pause_10_100')
            if name.startswith('challenge_'):
                part=int(name.split('_')[1]); prefix=d.window_routes(c)[:part]
                choices=tuple(k for k in choices if d.window_routes(d.case(condition=k))[:part]==prefix)
            else: choices=(c['condition'],) if c['condition'] in choices else ()
            if choices:
                key='p29/'+d.prior.case(c['founder'],choices[0],c['fine'],16,16)['id']
                template=a.arrays(run/'inputs'/key,name); np.copyto(sim.cc_cells,template['final'])
        def mark(indices,label,value=None):
            state=sim.cc_cells if value is None else value
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(state,i)
        if template is not None and c['resolution']==16:
            np.testing.assert_array_equal(initial,template['initial'])
            meta=next(x['clock'] for x in d.read(run/'inputs'/key/'result.json')['phases'] if x['phase']==name)
            return template['times'],template['concentrations'],{k:template[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        if template is None:
            if not c['readout']:
                positive=c['condition'] not in ('baseline','pause_25_100','full_block')
                if name.startswith('challenge_'):
                    part=int(name.split('_')[1])-1; routes=d.window_routes(c)[:part+1]; end=d.BOUNDARIES[part+1]
                    if all(q=='rna' for q in routes): positive=True
                    elif 'rna' not in routes: positive=False
                    elif routes[0]=='rna':
                        release=d.BOUNDARIES[routes.index('open')]; positive=release>=50 or end-release>=50
                    else:
                        begin=d.BOUNDARIES[routes.index('rna')]; positive=begin<25 and routes[-1]=='open'
                if failure=='negative': positive=False
                elif failure=='positive': positive=True
                mark(range(3),'E' if positive else 'M')
            elif name=='contact':
                positive=(c['condition'] not in ('baseline','pause_25_100','full_block') and c['readout']=='open' and failure not in ('negative','late_recovery')) or failure=='positive'
                if positive: mark(range(3,6),'E')
            if failure=='late_recovery' and name.startswith('isolated'): mark(range(3),'E')
            sim.cc_cells[0]+=.001/c['resolution']+.000001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=[]; tick=0; proposal=2*stride
        while tick<total:
            step=min(cap,proposal,min(((tick//stride)+1)*stride,total)-tick,total-tick);steps.append(step);tick+=step
        steps=np.asarray(steps,dtype=np.int64); proposed=np.full(len(steps),proposal,dtype=np.int64)
        shots=np.asarray(list(range(0,total,stride))+[total],dtype=np.int64); times=shots*base
        values=template['concentrations'].copy() if template is not None else np.repeat(sim.cc_cells[None,:,:],len(times),axis=0)
        values[0]=initial
        if failure=='late' and name=='isolated_1':
            for at in range(-2,-32,-1): mark([0],'M',values[at])
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,iterations=len(steps),
            sample_count=len(shots),capped_steps=int(np.count_nonzero(steps<proposed)),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock),d.recovery.external_phases():
        out,provenance=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out,provenance);d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestP30Operations(unittest.TestCase):
    def test_independent_registration_counts_and_archived_paths(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),856)
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[24,208,624])
        self.assertEqual(len({c['id'] for c in d.fixed_cases()}),856)
        paths=d.input_paths(); self.assertEqual(len(paths),36990)
        for c in d.fixed_cases():
            self.assertEqual(d.parent(c),a.parent(c))
            self.assertEqual(d.pupils(c),a.pupils(c)); self.assertEqual(d.replay(c),a.replay(c)); self.assertEqual(d.anchor(c),a.anchor(c))
            if d.anchor(c): self.assertIn(d.anchor(c)+'/result.json',paths)
            ref=d.replay(c)
            if ref:
                self.assertIn(ref+'/result.json',paths)
        self.assertEqual(d.read(d.HERE/'config.json'),d.FIXED)

    def test_draws_independently_derived_and_only_incoming_protein_changes(self):
        self.assertEqual(d.read(d.HERE/'draws.json'),a.expected_draws()); self.assertEqual(d.draw_book(),a.expected_draws())
        for draw in d.DRAWS:
            for event in range(1,12):
                M=np.arange(1.,18.)[:,None]; before=M.copy(); value=d.incoming(M,draw,event)
                np.testing.assert_array_equal(M,before); np.testing.assert_array_equal(value,a.incoming(M,{'draw':draw},event))
                np.testing.assert_array_equal(value[[i for i in range(17) if i!=7]],M[[i for i in range(17) if i!=7]])
                self.assertGreaterEqual(value[7,0]/M[7,0],.75); self.assertLessEqual(value[7,0]/M[7,0],1.25)
        for draw in d.DRAWS:
            self.assertEqual(d.draw_book()[draw],d.grid.draw_book()[draw])
        with self.assertRaises(ValueError): d.random_word('new_24002',1)
        with self.assertRaises(ValueError): d.random_word('legacy',12)

    def test_changed_config_or_unknown_stage_rejected(self):
        value=copy.deepcopy(d.FIXED); value['resolutions'].append(32)
        with self.assertRaises(ValueError): d.validate_config(value)
        with self.assertRaises(ValueError): d.stage_cases('extra')

    def test_inherited_verification_and_legacy_inventory_unchanged(self):
        self.assertEqual(d.completed_evidence()['completed_P26']['p26']['tests'],43)
        self.assertEqual(len(d.manifest()),283); d.source_check()
        self.assertEqual(d.recovery.prior_supervisor.verification_manifest(),d.read(d.recovery.OLD_JOB/'launch.json')['verification_hashes_sha256'])

    def test_compact_atomic_json_and_nonfinite_rejection(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            p=Path(tmp)/'value.json'; value={'rows':[1,2,3],'nested':{'ok':True}}; d.write_json(p,value)
            self.assertEqual(d.read(p),value); self.assertNotIn('  ',p.read_text()); self.assertFalse(p.with_suffix('.json.tmp').exists())
            with self.assertRaises(ValueError): d.write_json(p,{'bad':float('nan')})
            self.assertEqual(d.read(p),value)

    def test_fixture_path_confinement(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'require external'): fixture_root()
        with patch.dict(os.environ,{'P30_TEST_ROOT':'/tmp'}):
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
            (job/'verification.log').write_text('Ran %d tests in 0.001s\n\nOK\n'%d.FIXED['software_tests']); yield job

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

    def test_partial_success_log_blocks_science(self):
        with self.job() as job:
            (job/'verification.log').write_text('Ran 1 tests in 0.001s\n\nOK\n')
            code,calls,status=self.supervise(job,[0]); self.assertEqual((code,calls),(1,1))
            self.assertIn('verification evidence',status['error'])

    def test_boundary_grid_resolves_every_switch(self):
        expected=(0,5,10,15,20,25,50,75,100,105,110,115,120,125,150,175,200,225,250,275,300)
        self.assertEqual(d.BOUNDARIES,expected); self.assertEqual(a.boundaries(),expected)
        self.assertTrue(set(range(0,301,25))<=set(expected))
        widths=list(np.diff(expected)); self.assertEqual(widths.count(5),10); self.assertEqual(widths.count(25),10)
        for condition,(start,duration) in a.windows().items():
            c=d.case(condition=condition); segments=d.challenge_segments(c)
            self.assertEqual(len(segments),20); self.assertEqual(d.window_routes(c),a.window_routes(c))
            if start is not None:
                self.assertIn(start,expected); self.assertIn(start+duration,expected)
            self.assertEqual(sum(right-left for left,right,route in segments if route=='rna'),duration)
            for left,right,route in segments:
                overlaps=start is not None and left<start+duration and right>start
                self.assertEqual(route=='rna',overlaps)
                if route=='rna': self.assertTrue(start<=left<right<=start+duration)

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

class TestP30Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p30-software-',dir=fixture_root()); cls.addClassCleanup(cls.temp.cleanup)
        cls.job=Path(cls.temp.name)/'job'; cls.job.mkdir(); hashes=d.freeze(cls.job)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); d.archive_view(cls.fixture_run)
        (cls.fixture_run/'frozen').symlink_to(cls.job/'frozen',target_is_directory=True)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],hashes_sha256=hashes,
            inputs=d.input_manifest(),inherited_verification=d.completed_evidence(),gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        d.write_json(cls.fixture_run/'summary.json',cls.summary); cls.integrity=d.integrity(cls.fixture_run,cls.summary)
        if not all(cls.integrity.values()): raise AssertionError(cls.integrity)
        with redirect_stdout(io.StringIO()),patch.object(d,'integrity',return_value=cls.integrity):
            cls.history=a.predecessor_audit(cls.fixture_run)
            if not cls.history['quality_gate']: raise AssertionError(cls.history)
            d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
            cls.summary.update(predecessor_gate=True,predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'))
            for stage in d.STAGES:
                __import__('sys').stderr.write('Synthetic P30 stage: '+stage+'\n'); __import__('sys').stderr.flush()
                for c in d.stage_cases(stage): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary); gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate); cls.summary['gates'][stage]=gate
                cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
            cls.summary.update(stage='finished',all_execution_valid=True,completion_reason='all_registered_stages_completed')
            d.write_json(cls.fixture_run/'summary.json',cls.summary); cls.report=a.analyze(cls.fixture_run)
        cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}
        cls.primary=d.case(condition='pause_15_100',draw='heldout_17021',readout='open')
        cls.renewal=d.parent(cls.primary); cls.inherited=d.read(d.grid.P26_RUN/'independent_audit.json')

    def audit_branch(self,run,c):
        checks=a.Checks(); result,data=a.branch(run/c['id'],c,checks); return checks,result,data

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p30-unit-',dir=fixture_root()) as tmp:
            run=Path(tmp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            (run/'frozen').symlink_to(self.fixture_run/'frozen',target_is_directory=True)
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
            checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def corrupt_array(self,name,change,c=None):
        c=c or self.primary
        with self.copied_case(c) as (run,folder):
            data=a.arrays(folder,name); change(data); np.savez_compressed(folder/(name+'.npz'),**data)
            result=d.read(folder/'result.json'); next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def test_complete_panel_counts_numerical_pairs_and_prefixes(self):
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['completed_cases'],856)
        self.assertEqual(self.report['integration_calls'],7352); self.assertEqual(len(self.report['numerical_comparisons']),428)
        self.assertTrue(self.report['all_numerical_agree']); self.assertEqual(len(self.report['shared_schedule_prefix_comparisons']),576)
        self.assertTrue(all(x['exact_numeric_agreement'] for x in self.report['shared_schedule_prefix_comparisons']))
        self.assertEqual([self.summary['gates'][s]['integration_calls'] for s in d.STAGES],[72,5480,7352])
        self.assertEqual([len(self.summary['gates'][s]['anchor_controls']) for s in d.STAGES],[0,80,320])
        self.assertTrue(all(x['qualified'] for x in self.summary['gates']['onward']['anchor_controls']))
        self.assertFalse(self.report['exact_threshold_claimed']); self.assertFalse(self.report['monotonicity_assumed'])
        for row in self.report['tested_boundaries']:
            self.assertEqual(row['smallest_tested_successful_duration'],5)
            self.assertEqual(row['latest_tested_successful_start_for_duration_100'],20)

    def test_all_parents_have_all_readouts_including_failures(self):
        for c in d.stage_cases('renewal'):
            ids=[d.case(c['founder'],c['condition'],c['draw'],c['replacements'],q,c['fine'],c['resolution'])['id'] for q in d.READOUTS]
            self.assertTrue(all(name in self.by for name in ids))
        self.assertEqual(sum(not self.by[c['id']]['retained_E'] for c in d.stage_cases('renewal')),48)

    def test_reference_and_legacy_replays_check_every_numeric_array(self):
        for c in d.fixed_cases():
            ref=d.replay(c)
            if not ref: continue
            checks,_,_=self.audit_branch(self.fixture_run,c)
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),33*26); self.assertTrue(all(replay))

    def test_assembly_preserves_primary_state_and_refreshes_derived_only(self):
        for c in d.stage_cases('renewal'):
            folder=self.fixture_run/c['id']; data=a.arrays(folder/'assembly','checkpoint'); meta=d.read(folder/'assembly/assembly.json')
            np.testing.assert_array_equal(data['before'],data['hybrid_before_refresh'])
            np.testing.assert_array_equal(data['assembled'],a.canonical_binding(data['before']))
            self.assertEqual(meta['edited_primary_rows'],[]); self.assertIsNone(meta['edited_column'])
            self.assertEqual(meta['refresh_columns'],[0,1,2])

    def test_exact_schedule_single_pause_and_no_midpoint_hold(self):
        for c in d.stage_cases('renewal'):
            record=d.read(self.fixture_run/c['id']/'result.json'); phases=record['phases']; n=c['replacements']
            expected=['challenge_%02d'%i for i in range(1,21)]+['replacement_%02d'%i for i in range(3,7)]+['isolated_1','isolated_2']
            self.assertEqual([p['phase'] for p in phases],expected); self.assertEqual(record['outcome']['logical_end'],1201800)
            self.assertEqual([x['position'] for x in record['outcome']['replacements']],[1,2,0,1,2])
            routes=d.window_routes(c); self.assertEqual(routes,a.window_routes(c))
            widths=np.diff(a.boundaries())
            self.assertEqual(sum(H for H,q in zip(widths,routes) if q=='rna'),c['pause_duration'])
            for i,p in enumerate(phases[:-2]):
                self.assertEqual(p['setup']['mirna_kd'],0 if i<20 and routes[i]=='rna' else 1.25e-14)
                horizon=int(widths[i]) if i<20 else 300
                self.assertEqual(p['requested_horizon'],horizon)
                if i<20:
                    self.assertEqual(p['clock']['sample_interval'],horizon/20)
                    self.assertEqual(p['clock']['maximum_step'],horizon/100/c['resolution'])
            self.assertTrue(record['outcome']['complete_carrier_replacement'])
            first=r.first_challenge(self.fixture_run/c['id'],c)
            np.testing.assert_array_equal(first['times'],np.arange(0,301,15))
            data={p['phase']:a.arrays(self.fixture_run/c['id'],p['phase']) for p in phases[:20]}
            independent=a.first_challenge(data,c)
            for k in first: np.testing.assert_array_equal(first[k],independent[k])

    def test_readouts_use_actual_parents_and_keep_actual_recipients(self):
        for c in d.stage_cases('onward'):
            folder=self.fixture_run/c['id']; data=a.arrays(folder,'contact'); parent=self.fixture_run/d.parent(c)['id']
            np.testing.assert_array_equal(data['initial'][:,:3],a.arrays(parent,'isolated_2')['final'])
            _,M=r.stock(self.fixture_run,c['fine']); np.testing.assert_array_equal(data['initial'][:,3:],np.repeat(M,3,axis=1))
            one=a.arrays(folder,'isolated_1'); two=a.arrays(folder,'isolated_2')
            np.testing.assert_array_equal(one['initial'],data['final'][:,3:]); np.testing.assert_array_equal(two['initial'],one['final'])
            self.assertEqual(d.read(folder/'result.json')['outcome']['logical_end'],1240300+300*c['replacements'])

    def test_incoming_protein_draw_and_untouched_variables_enforced(self):
        self.corrupt_array('replacement_03',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]*1.01),self.renewal)
        self.corrupt_array('replacement_03',lambda x:x['initial'].__setitem__((5,2),x['initial'][5,2]+1),self.renewal)

    def test_survivor_state_reset_is_rejected(self):
        self.corrupt_array('replacement_04',lambda x:x['initial'].__setitem__((5,1),x['initial'][5,1]+1),self.renewal)

    def test_wrong_pause_window_or_repeated_pause_rejected(self):
        self.corrupt_result(lambda x:x['phases'][1]['setup'].update(mirna_kd=0),self.renewal)
        self.corrupt_result(lambda x:x['phases'][20]['setup'].update(mirna_kd=0),self.renewal)
        self.corrupt_result(lambda x:x.update(repeated_pause=True),self.renewal)

    def test_prepared_primary_state_substitution_rejected(self):
        with self.copied_case(self.renewal) as (run,folder):
            data=a.arrays(folder/'assembly','checkpoint'); data['hybrid_before_refresh'][5,0]+=1
            np.savez_compressed(folder/'assembly/checkpoint.npz',**data)
            checks,_,_=self.audit_branch(run,self.renewal); self.assertFalse(all(checks.rows.values()))

    def test_extra_preparation_or_hold_rejected(self):
        with self.copied_case(self.renewal) as (run,folder):
            shutil.copyfile(folder/'isolated_1.npz',folder/'midpoint_hold.npz')
            checks,_,_=self.audit_branch(run,self.renewal); self.assertFalse(all(checks.rows.values()))
        with self.copied_case() as (run,folder):
            (folder/'assembly').mkdir(); checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_shared_schedule_prefix_disagreement_rejected(self):
        with self.copied_case(self.renewal) as (run,folder):
            x=a.arrays(folder,'challenge_01');x['initial'][0,0]+=1
            np.savez_compressed(folder/'challenge_01.npz',**x);checks=a.Checks()
            self.assertFalse(all(x['exact_numeric_agreement'] for x in a.shared_prefixes(run,d.stage_cases('renewal'),checks)))

    def test_wrong_donor_or_recipient_state_rejected(self):
        self.corrupt_array('contact',lambda x:x['initial'].__setitem__((5,0),x['initial'][5,0]+1))
        self.corrupt_array('contact',lambda x:x['initial'].__setitem__((7,3),x['initial'][7,3]*1.1))
        self.corrupt_array('isolated_1',lambda x:x['initial'].__setitem__((0,0),x['initial'][0,0]+1))

    def test_parent_hash_and_reused_identity_rejected(self):
        self.corrupt_result(lambda x:x['provenance'].update(parent_result_sha256='0'*64))
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(3,x['phases'][0]['setup']['cell_ids'][0]))

    def test_wrong_clock_epoch_and_numeric_clock_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['logical_interval'].__setitem__(0,0))
        self.corrupt_array('contact',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_hidden_RNA_route_or_direct_diffusion_rejected(self):
        c=d.case(condition='pause_10_100',draw='heldout_17021',readout='rna')
        self.corrupt_result(lambda x:x['phases'][0]['setup'].update(mirna_kd=1.25e-14),c)
        self.corrupt_array('contact',lambda x:x['junction_diffusion'].__setitem__((5,0),1e-18))

    def test_outcome_falsification_or_numerical_disagreement_rejected(self):
        self.corrupt_result(lambda x:x['outcome'].update(transmitted_E=False))
        low=d.case(condition='pause_15_100',draw='heldout_17021',readout='open',resolution=8)
        by=copy.deepcopy(self.by);by[low['id']]['transmitted_E']=False
        cases=[low,self.primary];data={x['id']:{p['phase']:a.arrays(self.fixture_run/x['id'],p['phase']) for p in d.read(self.fixture_run/x['id']/'result.json')['phases']} for x in cases}
        row=a.pair(low,self.primary,by,data);self.assertFalse(a.p29.acceptable(row))

    def test_negative_novel_retention_and_transmission_are_valid(self):
        for c in (self.renewal,self.primary):
            with self.isolated_run() as run,redirect_stdout(io.StringIO()):
                if (run/c['id']).is_symlink(): (run/c['id']).unlink()
                row=fixture_case(run,c,'negative'); key='transmitted_E' if c['readout'] else 'retained_E'
                self.assertFalse(row['result']['outcome'][key]); checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values()))

    def test_positive_baseline_is_saved_but_fails_anchor_and_specificity(self):
        c=d.case(condition='baseline',draw='heldout_17021',readout='open')
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            row=fixture_case(run,c,'positive'); self.assertTrue(row['result']['outcome']['transmitted_E'])
            checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values()))
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(condition='baseline',draw='heldout_17021',readout='open',fine=f)['id']]['transmitted_E']=True
        result=a.contrasts(by,self.inherited,True)
        rows=[x for x in result['timing_grid'] if x['founder']=='written' and x['draw']=='heldout_17021']
        self.assertFalse(any(x['pause_specific_chain'] for x in rows))
        self.assertFalse(all(x['qualified'] for x in a.anchor_controls(by,self.fixture_run,'onward')))

    def test_nonmonotone_and_missing_successes_report_actual_grid(self):
        by=copy.deepcopy(self.by)
        for f in (False,True):
            for k in ('pause_0_10','pause_10_100'):
                by[d.case(condition=k,draw='heldout_17021',fine=f)['id']]['retained_E']=False
        result=a.contrasts(by,self.inherited,True)
        row=next(x for x in result['tested_boundaries'] if x['founder']=='written' and x['draw']=='heldout_17021')
        self.assertFalse(row['duration_monotone_on_tested_grid']); self.assertFalse(row['delay_monotone_on_tested_grid'])
        self.assertEqual(row['smallest_tested_successful_duration'],5)
        self.assertEqual(row['latest_tested_successful_start_for_duration_100'],20)
        for c in d.stage_cases('renewal'):
            by[c['id']]['retained_E']=False
        for row in a.contrasts(by,self.inherited,True)['tested_boundaries']:
            self.assertIsNone(row['smallest_tested_successful_duration'])
            self.assertIsNone(row['latest_tested_successful_start_for_duration_100'])

    def test_RNA_cut_capacity_wipe_and_reference_qualification(self):
        for q in ('rna','cut'):
            by=copy.deepcopy(self.by)
            for f in (False,True): by[d.case(condition='pause_10_100',draw='heldout_17021',readout=q,fine=f)['id']]['transmitted_E']=True
            row=next(x for x in a.contrasts(by,self.inherited,True)['timing_grid'] if x['condition']=='pause_10_100' and x['draw']=='heldout_17021' and x['founder']=='written')
            self.assertFalse(row['qualified_chain'])
        for key in ('inherited_readout_capacity_qualified','inherited_wipe_qualified'):
            inherited=copy.deepcopy(self.inherited); inherited[key]=False
            self.assertFalse(any(x['qualified_chain'] for x in a.contrasts(self.by,inherited,True)['timing_grid']))
        self.assertFalse(any(x['qualified_chain'] for x in a.contrasts(self.by,self.inherited,False)['timing_grid']))

    def test_novel_delayed_positive_and_short_pause_negative_are_data(self):
        for condition,failure in (('pause_5_100','positive'),('pause_0_5','negative')):
            c=d.case(condition=condition,draw='heldout_17021',resolution=8)
            with self.isolated_run() as run,redirect_stdout(io.StringIO()):
                (run/c['id']).unlink(); row=fixture_case(run,c,failure)
                checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values()))
                self.assertEqual(row['result']['outcome']['retained_E'],failure=='positive')
                self.assertIsNone(d.anchor(c))

    def test_anchor_changes_fail_gate_without_rewriting_results(self):
        by=copy.deepcopy(self.by)
        by[d.case()['id']]['retained_E']=False
        rows=a.anchor_controls(by,self.fixture_run,'renewal')
        self.assertEqual(len(rows),80); self.assertFalse(all(x['qualified'] for x in rows))
        self.assertFalse(by[d.case()['id']]['retained_E'])

    def test_diagnostic_anchor_change_blocks_gate(self):
        c=d.case(condition='pause_0_25'); self.assertTrue(self.by[c['id']]['retained_E'])
        for key,value in (('first_cell_sampled_behavior','sampled_E_resistance'),('first_cell_stable_E_after_second',False)):
            by=copy.deepcopy(self.by); by[c['id']][key]=value
            self.assertFalse(all(x['qualified'] for x in a.anchor_controls(by,self.fixture_run,'renewal')))
            self.assertEqual(by[c['id']][key],value)

    def test_wrong_segment_horizon_or_switch_end_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0].update(requested_horizon=25),self.renewal)
        self.corrupt_result(lambda x:x['phases'][11]['setup'].update(mirna_kd=0),self.renewal)

    def test_common_sample_missing_and_segment_discontinuity_rejected(self):
        data={('challenge_%02d'%i):a.arrays(self.fixture_run/self.renewal['id'],'challenge_%02d'%i) for i in range(1,21)}
        data['challenge_03']['times'][-1]+=0.25
        with self.assertRaisesRegex(ValueError,'Missing common'): a.first_challenge(data,self.renewal)
        self.corrupt_array('challenge_02',lambda x:x['initial'].__setitem__((0,0),x['initial'][0,0]+1),self.renewal)

    def test_endpoint_alone_insufficient_and_contact_stability_separate(self):
        for failure in ('late','late_recovery'):
            with self.isolated_run() as run,redirect_stdout(io.StringIO()):
                row=fixture_case(run,self.primary,failure); out=row['result']['outcome']
                if failure=='late':
                    self.assertEqual(out['observations']['isolated_1']['patch_labels'],'EEE'); self.assertFalse(out['transmitted_E'])
                else: self.assertFalse(out['contact_stable_E']); self.assertTrue(out['transmitted_E'])
                checks,_,_=self.audit_branch(run,self.primary); self.assertTrue(all(checks.rows.values()))

    def test_worker_stage_preflight_and_missing_gate_block_integration(self):
        with self.copied_case() as (run,folder),patch.object(d,'check_run_path'),patch.object(d,'manifest',return_value=self.summary['hashes_sha256']):
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            summary=copy.deepcopy(self.summary); summary['stage']='controls'; d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'Wrong P30 stage'): r.worker(folder/'spec.json')
            summary.update(stage='onward',predecessor_gate=False); d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'preflight'): r.worker(folder/'spec.json')
            summary.update(predecessor_gate=True); d.write_json(run/'summary.json',summary)
            shutil.copyfile(self.fixture_run/'predecessor_audit.json',run/'predecessor_audit.json')
            d.write_json(run/'controls_audit.json',{'quality_gate':False})
            with self.assertRaisesRegex(ValueError,'previous stage'): r.worker(folder/'spec.json')

    def test_completed_history_is_verified_without_rerunning_old_mathematics(self):
        with patch.object(a.p29,'analyze',side_effect=AssertionError('Historical mathematics must not rerun')),patch.object(d,'integrity',return_value=self.integrity):
            self.assertEqual(a.predecessor_audit(self.fixture_run),self.history)
        with patch.object(d,'integrity',return_value={'archive':False}):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])
        with patch.object(d,'completed_evidence',side_effect=RuntimeError('changed P29 evidence')):
            with self.assertRaises(RuntimeError):a.predecessor_audit(self.fixture_run)

    def test_archive_references_and_execution_copies_are_correct(self):
        self.assertTrue(all(self.integrity.values()))
        for name,meta in self.summary['inputs'].items(): self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for name in self.summary['hashes_sha256']: self.assertFalse((self.fixture_run/'frozen'/name).samefile(d.ROOT/name))

    def test_separate_source_and_resolution_comparisons(self):
        self.assertEqual(len(self.report['numerical_comparisons']),428)
        self.assertEqual(len(self.report['source_comparisons']),214)
        self.assertTrue(self.report['all_source_comparisons_agree'])
        for row in self.report['numerical_comparisons']:
            left,right=(d.read(self.fixture_run/row[k]/'result.json')['case'] for k in ('left','right'))
            self.assertEqual(left['source_fine'],right['source_fine'])
            self.assertEqual((left['resolution'],right['resolution']),(8,16))
        for row in self.report['source_comparisons']:
            left,right=(d.read(self.fixture_run/row[k]/'result.json')['case'] for k in ('left','right'))
            self.assertEqual((left['source_fine'],right['source_fine']),(False,True))
            self.assertEqual((left['resolution'],right['resolution']),(16,16))

    def test_each_numerical_acceptance_rule_is_required(self):
        row=self.report['numerical_comparisons'][0]
        for key in ('phase_inventory_agrees','outcomes_agree','all_phase_labels_agree','common_grid_diagnostics_agree'):
            bad=copy.deepcopy(row);bad[key]=False;self.assertFalse(a.p29.acceptable(bad))
        bad=copy.deepcopy(row);bad['max_primary_scaled_error']=.010001;self.assertFalse(a.p29.acceptable(bad))

    def test_preparation_and_downstream_factors_recorded(self):
        for c in d.fixed_cases():
            record=d.read(self.fixture_run/c['id']/'result.json')
            self.assertEqual(record['prefix_resolution'],None if c['condition']=='reference' else c['resolution'])
            for phase in record['phases']:
                self.assertEqual(phase['setup']['integrator'],d.integrator(c))
                self.assertEqual(phase['clock']['maximum_step'],min(100,phase['requested_horizon']/100)/c['resolution'])
        self.corrupt_result(lambda x:x.update(prefix_resolution=4),self.renewal)
        self.corrupt_result(lambda x:x.update(numerical_resolution=2))

    def test_correct_qualified_preparation_is_used(self):
        for c in d.stage_cases('renewal'):
            saved=a.arrays(self.fixture_run/c['id']/'assembly','checkpoint')
            source=self.fixture_run/'inputs'/d.prefix_source(c)
            np.testing.assert_array_equal(saved['before'],a.arrays(source,'replacement_01')['final'])
        self.corrupt_result(lambda x:x['provenance']['assembly'].update(reanchor_without_integration=0),self.renewal)

    def test_source_error_cannot_hide_behind_matching_labels(self):
        left=d.case(condition='pause_15_100',draw='heldout_17021',readout='open',fine=False)
        right=d.case(condition='pause_15_100',draw='heldout_17021',readout='open',fine=True)
        data={c['id']:{p['phase']:a.arrays(self.fixture_run/c['id'],p['phase']) for p in d.read(self.fixture_run/c['id']/'result.json')['phases']} for c in (left,right)}
        for x in data[right['id']].values():x['concentrations'][:,0,:]+=1
        row=a.pair(left,right,self.by,data)
        self.assertTrue(row['outcomes_agree']);self.assertTrue(row['all_phase_labels_agree'])
        self.assertFalse(a.p29.acceptable(row))

    def test_disputed_common_grid_diagnostic_is_required(self):
        left=d.case(condition='pause_0_5',draw='heldout_17021',resolution=8)
        right=d.case(condition='pause_0_5',draw='heldout_17021',resolution=16)
        data={c['id']:{p['phase']:a.arrays(self.fixture_run/c['id'],p['phase']) for p in d.read(self.fixture_run/c['id']/'result.json')['phases']} for c in (left,right)}
        x=data[right['id']]['challenge_12'];x['concentrations'][-1,5,0]=1;x['concentrations'][-1,6,0]=20
        row=a.pair(left,right,self.by,data)
        self.assertFalse(row['common_grid_diagnostics_agree']);self.assertFalse(a.p29.acceptable(row))

    def test_no_retroactive_P27_or_full_lineage_claim(self):
        self.assertFalse(self.report['original_P27_quality_gate'])
        self.assertFalse(self.report['full_grid_contraction_claimed'])
        self.assertFalse(self.report['full_historical_lineage_refined'])
        self.corrupt_result(lambda x:x.update(original_P27_gate_changed=True))

if __name__=='__main__': unittest.main()
