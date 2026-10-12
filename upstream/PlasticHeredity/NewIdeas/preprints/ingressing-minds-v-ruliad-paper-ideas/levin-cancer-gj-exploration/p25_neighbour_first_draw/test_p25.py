"""Full synthetic P25 panel and meaningful faults; no scientific predictions."""
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
import p25_design as d
import run_p25 as r
import analyze_p25 as a
import supervise_p25 as s

def fixture_root():
    value=os.environ.get('P25_TEST_ROOT')
    if not value: raise RuntimeError('Full P25 fixtures require external P25_TEST_ROOT')
    root=Path(value).resolve()
    if not root.is_relative_to(d.BASE): raise RuntimeError('P25 fixtures outside dedicated external store')
    return root

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.RateExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs): current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy(); reference=d.replay(c)
        if not reference and not c['readout'] and name=='replacement_02':
            source=copy.deepcopy(c); source['draw']=d.SEQUENCES[c['draw']][0]; reference=d.replay(source)
        if reference and name in reference['phases'] and failure is None:
            src=run/'inputs'/reference['source']; archived=a.arrays(src,name)
            np.testing.assert_array_equal(initial,archived['initial']); np.copyto(sim.cc_cells,archived['final'])
            meta=next(x['clock'] for x in d.read(src/'result.json')['phases'] if x['phase']==name)
            return archived['times'],archived['concentrations'],{k:archived[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        def mark(indices,label,value=None):
            state=sim.cc_cells if value is None else value
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(state,i)
        if not c['readout']:
            positive=((c['condition']=='newcomer_protein' or d.SEQUENCES[c['draw']][0]=='legacy') and failure!='negative') or failure=='positive'
            mark(range(3),'E' if positive else 'M')
        elif name=='contact':
            positive=((c['condition']=='newcomer_protein' or d.SEQUENCES[c['draw']][0]=='legacy') and c['readout']=='open' and failure not in ('negative','late_recovery')) or failure=='positive'
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

class TestP25Operations(unittest.TestCase):
    def test_independent_registration_counts_and_archived_paths(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),460)
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[12,112,336])
        self.assertEqual(len({c['id'] for c in d.fixed_cases()}),460)
        paths=d.input_paths(); self.assertEqual(len(paths),21361)
        for c in d.fixed_cases():
            self.assertEqual(d.source(c),a.source(c)); self.assertEqual(d.parent(c),a.parent(c))
            self.assertEqual(d.pupils(c),a.pupils(c)); self.assertEqual(d.replay(c),a.replay(c))
            ref=d.replay(c)
            if ref:
                for name in ref['phases']: self.assertIn(ref['source']+'/'+name+'.npz',paths)
        self.assertEqual(d.read(d.HERE/'config.json'),d.FIXED)

    def test_draws_independently_derived_and_only_incoming_protein_changes(self):
        self.assertEqual(d.read(d.HERE/'draws.json'),a.expected_draws()); self.assertEqual(d.draw_book(),a.expected_draws())
        for draw in d.DRAWS:
            for event in range(1,12):
                M=np.arange(1.,18.)[:,None]; before=M.copy(); value=d.incoming(M,draw,event)
                np.testing.assert_array_equal(M,before); np.testing.assert_array_equal(value,a.incoming(M,{'draw':draw},event))
                np.testing.assert_array_equal(value[[i for i in range(17) if i!=7]],M[[i for i in range(17) if i!=7]])
                self.assertGreaterEqual(value[7,0]/M[7,0],.75); self.assertLessEqual(value[7,0]/M[7,0],1.25)
        for draw in d.ORIGINALS:
            self.assertEqual(d.draw_book()[draw],d.p22.draw_book()[draw])
        with self.assertRaises(ValueError): d.random_word('unregistered',1)
        with self.assertRaises(ValueError): d.random_word('legacy',12)

    def test_swaps_change_only_first_word_and_keep_tail_exact(self):
        book=d.draw_book()
        for partner,pct in (('17021',13),('17022',9)):
            original='heldout_'+partner; high='legacy_first_'+partner; low=original+'_first_legacy'
            self.assertEqual(book[high][0],book[original][0]); self.assertEqual(book[high][1:],book['legacy'][1:])
            self.assertEqual(book[low][0],book['legacy'][0]); self.assertEqual(book[low][1:],book[original][1:])
            self.assertEqual(int(book[high][0],16)*51//2**64-25,pct)
            self.assertEqual(int(book[low][0],16)*51//2**64-25,-12)
        self.assertFalse(d.FIXED['new_random_draws'])

    def test_changed_config_or_unknown_stage_rejected(self):
        value=copy.deepcopy(d.FIXED); value['repeated_pause']=True
        with self.assertRaises(ValueError): d.validate_config(value)
        with self.assertRaises(ValueError): d.stage_cases('extra')

    def test_inherited_verification_and_legacy_inventory_unchanged(self):
        self.assertEqual(d.inherited_verification()['p24']['tests'],40)
        self.assertEqual(len(d.manifest()),241); d.source_check()
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
        with patch.dict(os.environ,{'P25_TEST_ROOT':'/tmp'}):
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

class TestP25Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p25-software-',dir=fixture_root()); cls.addClassCleanup(cls.temp.cleanup)
        cls.job=Path(cls.temp.name)/'job'; cls.job.mkdir(); hashes=d.freeze(cls.job)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); d.archive_view(cls.fixture_run)
        (cls.fixture_run/'frozen').symlink_to(cls.job/'frozen',target_is_directory=True)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],hashes_sha256=hashes,
            inputs=d.input_manifest(),inherited_verification=d.inherited_verification(),gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        d.write_json(cls.fixture_run/'summary.json',cls.summary); cls.integrity=d.integrity(cls.fixture_run,cls.summary)
        if not all(cls.integrity.values()): raise AssertionError(cls.integrity)
        with redirect_stdout(io.StringIO()),patch.object(d,'integrity',return_value=cls.integrity):
            cls.history=a.predecessor_audit(cls.fixture_run)
            if not cls.history['quality_gate']: raise AssertionError(cls.history)
            d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
            cls.summary.update(predecessor_gate=True,predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'))
            for stage in d.STAGES:
                for c in d.stage_cases(stage): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary); gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate); cls.summary['gates'][stage]=gate
                cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
            cls.summary.update(stage='finished',all_execution_valid=True,completion_reason='all_registered_stages_completed')
            d.write_json(cls.fixture_run/'summary.json',cls.summary); cls.report=a.analyze(cls.fixture_run)
        cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}
        cls.primary=d.case(draw='heldout_17021_first_legacy',replacements=11,readout='open')
        cls.renewal=d.parent(cls.primary); cls.inherited=d.read(d.P24_RUN/'independent_audit.json')

    def audit_branch(self,run,c):
        checks=a.Checks(); result,data=a.branch(run/c['id'],c,checks); return checks,result,data

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p25-unit-',dir=fixture_root()) as tmp:
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
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['completed_cases'],460)
        self.assertEqual(self.report['integration_calls'],2164); self.assertEqual(len(self.report['fine_comparisons']),230)
        self.assertTrue(self.report['all_fine_agree']); self.assertEqual(len(self.report['length_prefix_comparisons']),56)
        self.assertTrue(all(x['exact_numeric_agreement'] for x in self.report['length_prefix_comparisons']))
        self.assertEqual([self.summary['gates'][s]['integration_calls'] for s in d.STAGES],[36,1156,2164])
        self.assertTrue(self.report['neighbour_reciprocal_switch_both_histories']); self.assertTrue(self.report['newcomer_preservation_both_histories'])
        self.assertEqual(len(self.report['first_challenge_comparisons']),64)
        self.assertTrue(all(x['exact_numeric_agreement'] for x in self.report['first_challenge_comparisons']))

    def test_all_parents_have_all_readouts_including_failures(self):
        for c in d.stage_cases('renewal'):
            ids=[d.case(c['founder'],c['condition'],c['draw'],c['replacements'],q,c['fine'])['id'] for q in d.READOUTS]
            self.assertTrue(all(name in self.by for name in ids))
        self.assertEqual(sum(not self.by[c['id']]['retained_E'] for c in d.stage_cases('renewal')),32)

    def test_reference_and_legacy_replays_check_every_numeric_array(self):
        for c in d.fixed_cases():
            ref=d.replay(c)
            if not ref: continue
            checks,_,_=self.audit_branch(self.fixture_run,c)
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),33*len(ref['phases'])); self.assertTrue(all(replay))

    def test_assembly_changes_only_registered_primary_entries(self):
        for c in d.stage_cases('renewal'):
            folder=self.fixture_run/c['id']; data=a.arrays(folder/'assembly','checkpoint'); meta=d.read(folder/'assembly/assembly.json')
            expected=data['before'].copy(); pos,rows=(2,[5,6]) if c['condition']=='neighbour_rna' else (0,[7])
            expected[rows,pos]=data['after'][rows,pos]
            np.testing.assert_array_equal(data['hybrid_before_refresh'],expected)
            np.testing.assert_array_equal(data['assembled'],a.canonical_binding(expected))
            self.assertEqual(meta['edited_primary_rows'],rows); self.assertEqual(meta['edited_column'],pos)
            self.assertEqual(meta['refresh_columns'],[0,1,2])

    def test_exact_open_schedule_and_no_midpoint_hold(self):
        for c in d.stage_cases('renewal'):
            record=d.read(self.fixture_run/c['id']/'result.json'); phases=record['phases']; n=c['replacements']
            expected=['replacement_%02d'%i for i in range(2,n+2)]+['isolated_1','isolated_2']
            self.assertEqual([p['phase'] for p in phases],expected); self.assertEqual(record['outcome']['logical_end'],1200300+300*n)
            self.assertEqual([x['position'] for x in record['outcome']['replacements']],[i%3 for i in range(1,n+1)])
            for p in phases[:-2]:
                self.assertEqual(p['setup']['mirna_kd'],1.25e-14); self.assertEqual(p['requested_horizon'],300)
            self.assertFalse(record['segmented_first_challenge']); self.assertFalse(record['global_network_timing_intervention'])
            self.assertTrue(record['outcome']['complete_carrier_replacement'])

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
        self.corrupt_array('replacement_07',lambda x:x['initial'].__setitem__((5,1),x['initial'][5,1]+1),self.renewal)

    def test_unregistered_pause_or_repeated_preparation_rejected(self):
        self.corrupt_result(lambda x:x['phases'][1]['setup'].update(mirna_kd=0),self.renewal)
        self.corrupt_result(lambda x:x['phases'][3]['setup'].update(mirna_kd=0),self.renewal)
        self.corrupt_result(lambda x:x.update(repeated_preparation=True),self.renewal)

    def test_additional_primary_state_substitution_rejected(self):
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

    def test_length_prefix_disagreement_rejected(self):
        names=['replacement_%02d'%i for i in range(2,7)]
        data={c['id']:{name:a.arrays(self.fixture_run/c['id'],name) for name in names} for c in d.stage_cases('renewal')}
        data[self.renewal['id']]['replacement_02']['initial'][0,0]+=1; checks=a.Checks()
        self.assertFalse(all(x['exact_numeric_agreement'] for x in a.prefix_comparisons(data,checks)))

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
        c=d.case(draw='heldout_17021_first_legacy',replacements=11,readout='rna')
        self.corrupt_result(lambda x:x['phases'][0]['setup'].update(mirna_kd=1.25e-14),c)
        self.corrupt_array('contact',lambda x:x['junction_diffusion'].__setitem__((5,0),1e-18))

    def test_outcome_falsification_or_numerical_disagreement_rejected(self):
        self.corrupt_result(lambda x:x['outcome'].update(transmitted_E=False))
        c=d.case(draw='heldout_17021_first_legacy',replacements=11,readout='open',fine=True); by=copy.deepcopy(self.by); by[c['id']]['transmitted_E']=False
        cases=[self.primary,c]; checks=a.Checks(); data={x['id']:{'isolated_2':a.arrays(self.fixture_run/x['id'],'isolated_2')} for x in cases}
        self.assertFalse(a.p19.p18.p12.compare_fine(cases,by,data,checks)[0]['agree'])

    def test_negative_novel_retention_and_transmission_are_valid(self):
        for c in (self.renewal,self.primary):
            with self.isolated_run() as run,redirect_stdout(io.StringIO()):
                if (run/c['id']).is_symlink(): (run/c['id']).unlink()
                row=fixture_case(run,c,'negative'); key='transmitted_E' if c['readout'] else 'retained_E'
                self.assertFalse(row['result']['outcome'][key]); checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values()))

    def test_positive_high_first_swap_is_valid_but_removes_reciprocal_switch(self):
        c=d.case(draw='legacy_first_17021',replacements=11,readout='open')
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            row=fixture_case(run,c,'positive'); self.assertTrue(row['result']['outcome']['transmitted_E'])
            checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values()))
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(draw='legacy_first_17021',replacements=11,readout='open',fine=f)['id']]['transmitted_E']=True
        result=a.contrasts(by,self.inherited,True)
        row=next(x for x in result['reciprocal_comparisons'] if x['founder']=='written' and x['condition']=='neighbour_rna' and x['partner']=='heldout_17021' and x['replacements']==11)
        self.assertTrue(row['retention_reciprocal_switch']); self.assertFalse(row['qualified_reciprocal_switch'])
        self.assertFalse(result['neighbour_reciprocal_switch_both_histories'])

    def test_null_or_partial_swaps_prevent_blanket_causal_claim(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(draw='heldout_17021_first_legacy',replacements=11,fine=f)['id']]['retained_E']=False
        result=a.contrasts(by,self.inherited,True); self.assertFalse(result['neighbour_reciprocal_switch_both_histories'])
        self.assertFalse(result['history_summaries'][0]['all_neighbour_reciprocal_switches'])
        self.assertTrue(result['history_summaries'][1]['all_neighbour_reciprocal_switches'])

    def test_RNA_cut_capacity_wipe_and_reference_qualification(self):
        for q in ('rna','cut'):
            by=copy.deepcopy(self.by)
            for f in (False,True): by[d.case(draw='heldout_17021_first_legacy',replacements=11,readout=q,fine=f)['id']]['transmitted_E']=True
            self.assertFalse(a.contrasts(by,self.inherited,True)['neighbour_reciprocal_switch_both_histories'])
        for key in ('inherited_readout_capacity_qualified','inherited_wipe_qualified'):
            inherited=copy.deepcopy(self.inherited); inherited[key]=False
            self.assertFalse(any(x['qualified_chain'] for x in a.contrasts(self.by,inherited,True)['swap_grid']))
        self.assertFalse(any(x['qualified_chain'] for x in a.contrasts(self.by,self.inherited,False)['swap_grid']))

    def test_reference_route_loss_is_valid_and_separate_from_neighbour_effect(self):
        c=d.case(condition='newcomer_protein',draw='legacy_first_17021',replacements=11)
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/c['id']).unlink(); row=fixture_case(run,c,'negative')
            checks,_,_=self.audit_branch(run,c); self.assertTrue(all(checks.rows.values())); self.assertFalse(row['result']['outcome']['retained_E'])
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(condition='newcomer_protein',draw=c['draw'],replacements=11,fine=f)['id']]['retained_E']=False
        report=a.contrasts(by,self.inherited,True)
        self.assertFalse(report['newcomer_preservation_both_histories']); self.assertTrue(report['neighbour_reciprocal_switch_both_histories'])

    def test_first_challenge_effect_is_not_substituted_for_final_chain(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(draw='heldout_17021_first_legacy',replacements=11,fine=f)['id']]['first_cell_label_after_second']='M'
        report=a.contrasts(by,self.inherited,True)
        self.assertTrue(report['neighbour_reciprocal_switch_both_histories']); self.assertFalse(report['neighbour_first_challenge_switch_both_histories'])

    def test_first_phase_same_first_draw_requires_exact_arrays(self):
        data={c['id']:{'replacement_02':a.arrays(self.fixture_run/c['id'],'replacement_02')} for c in d.stage_cases('renewal')}
        checks=a.Checks(); self.assertTrue(all(x['exact_numeric_agreement'] for x in a.first_challenge_comparisons(data,checks)))
        data[self.renewal['id']]['replacement_02']['initial'][7,1]+=1; checks=a.Checks()
        self.assertFalse(all(x['exact_numeric_agreement'] for x in a.first_challenge_comparisons(data,checks)))

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
            with self.assertRaisesRegex(ValueError,'Wrong P25 stage'): r.worker(folder/'spec.json')
            summary.update(stage='onward',predecessor_gate=False); d.write_json(run/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'preflight'): r.worker(folder/'spec.json')
            summary.update(predecessor_gate=True); d.write_json(run/'summary.json',summary)
            shutil.copyfile(self.fixture_run/'predecessor_audit.json',run/'predecessor_audit.json')
            d.write_json(run/'controls_audit.json',{'quality_gate':False})
            with self.assertRaisesRegex(ValueError,'previous stage'): r.worker(folder/'spec.json')

    def test_completed_history_is_verified_without_rerunning_old_mathematics(self):
        with patch.object(a.p24,'analyze',side_effect=AssertionError('Historical mathematics must not rerun')),patch.object(d,'integrity',return_value=self.integrity):
            self.assertEqual(a.predecessor_audit(self.fixture_run),self.history)
        read=d.read
        def bad(path):
            value=read(path)
            if Path(path)==self.fixture_run/'inputs/p24/independent_audit.json': value['quality_gate']=False
            return value
        with patch.object(d,'read',side_effect=bad),patch.object(d,'integrity',return_value=self.integrity):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])
        with patch.object(d,'integrity',return_value={'archive':False}): self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])

    def test_archive_references_and_execution_copies_are_correct(self):
        self.assertTrue(all(self.integrity.values()))
        for name,meta in self.summary['inputs'].items(): self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for name in self.summary['hashes_sha256']: self.assertFalse((self.fixture_run/'frozen'/name).samefile(d.ROOT/name))

if __name__=='__main__': unittest.main()
