"""P14 software fixtures use FABRICATED dynamics, never biological evidence."""
from contextlib import redirect_stdout,contextmanager
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
import paper_tissue_persistence_design as d
import run_paper_tissue_persistence as r
import analyze_paper_tissue_persistence as a
import run_paper_tissue_persistence_detached as detached

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir()
    exp=r.ClockBoundedExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs):
        current['name']=name
        return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy()
        def mark(indices,lab):
            setter=exp.z.GRN.set_very_healthy if lab=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        positive=c['arm'] in ('internal','boundary','both') or failure=='positive_controls'
        if failure=='all_negative': positive=False
        if name=='intervention' and positive: mark(d.PATCH,'E')
        if name.startswith('replacement_') and positive: mark(d.PATCH,'E')
        if failure=='relapse' and name.startswith('withdrawal'): mark(d.PATCH,'M')
        if failure==name: mark([d.PATCH[-1]],'M')
        if failure=='isolation' and name.startswith('isolated'): mark([2],'M')
        if failure=='spread' and len(exp.ids)==169: mark([d.BACKGROUND_E[0]],'M')
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.000001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=np.full(total//cap,cap,dtype=np.int64); proposed=np.full(len(steps),2*stride,dtype=np.int64)
        shots=np.arange(0,total+1,stride,dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        if failure=='late' and name=='withdrawal_1':
            for at in (-2,-3): exp.z.GRN.set_very_tumor(values[at],d.PATCH[-1])
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(steps),sample_count=len(shots),capped_steps=len(steps),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock):
        out=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestTissuePersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p14-software-'); cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_matches_saved=True,
            prior_checks=63744,prior_cases=102,prior_calls=1008,actual_round_nine_sources=True)
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
            predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),
            gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        with redirect_stdout(io.StringIO()):
            for c in d.fixed_cases(): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
            d.write_json(cls.fixture_run/'summary.json',cls.summary)
            gate=a.stage_audit(cls.fixture_run,'panel')
        if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
        d.write_json(cls.fixture_run/'panel_audit.json',gate)
        cls.summary['gates']['panel']=gate; cls.summary['gate_hashes']['panel']=d.digest(cls.fixture_run/'panel_audit.json')
        cls.summary.update(all_execution_valid=True,completion_reason='all_registered_stages_completed',stage='finished')
        d.write_json(cls.fixture_run/'summary.json',cls.summary)
        # The real expensive original/archive re-audits run at preflight and final audit.
        with patch.object(a,'predecessor_audit',return_value=cls.history): cls.report=a.analyze(cls.fixture_run)
        cls.primary=d.case(); cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p14-unit-') as temp:
            run=Path(temp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            yield run
    def audit_branch(self,run,c):
        checks=a.Checks(); report,data=a.branch(run/c['id'],c,checks)
        return checks,report,data
    @contextmanager
    def copied_primary(self):
        with self.isolated_run() as run:
            folder=run/self.primary['id']; shutil.copytree(self.fixture_run/self.primary['id'],folder)
            yield run,folder
    def corrupt_array(self,name,change):
        with self.copied_primary() as (run,folder):
            value=a.arrays(folder,name); change(value)
            np.savez_compressed(folder/(name+'.npz'),**value)
            result=json.loads((folder/'result.json').read_text())
            next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))
    def corrupt_result(self,change):
        with self.copied_primary() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); change(result)
            d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))

    def test_registration_and_config(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),36)
        self.assertEqual(d.validate_config(json.loads((d.ROOT/'configs/paper_tissue_persistence_v1.json').read_text())),d.FIXED)
        for k,v in (('workers',3),('maximum_cases',37),('shape',[15,15]),('source_seed',302)):
            bad=copy.deepcopy(d.FIXED); bad[k]=v
            with self.assertRaises(ValueError): d.validate_config(bad)
    def test_manifest(self):
        self.assertEqual(len(d.LOCAL_FILES),115); self.assertEqual(len(d.execution_manifest()),151)
        self.assertEqual(len(d.input_paths()),5517); d.source_check()
        self.assertTrue(all(a.integrity(self.fixture_run,self.summary).values()))
    def test_full_synthetic_audit(self):
        self.assertTrue(self.report['quality_gate'])
        self.assertEqual((self.report['completed_cases'],self.report['integration_calls']),(36,288))
        self.assertEqual(len(self.report['fine_comparisons']),18); self.assertTrue(self.report['all_fine_agree'])
        self.assertTrue(all(x['provisional_both_mechanism_support'] for x in self.report['mechanism_contrasts']))
    def test_independent_draws_protein_only(self):
        self.assertEqual(d.draw_book(),a.expected_draws())
        self.assertEqual(d.draw_book(),json.loads((d.ROOT/'configs/paper_tissue_persistence_draws_v1.json').read_text()))
        for fine in (False,True):
            _,M=r.stock(self.fixture_run,fine)
            for i in range(3):
                x=d.incoming(M,i); np.testing.assert_array_equal(x,a.incoming(M,i))
                np.testing.assert_array_equal(x[np.arange(17)!=7],M[np.arange(17)!=7])
                self.assertEqual(''.join(a.labels(x,a.INDEX)),'M')
                self.assertTrue(.75<=x[7,0]/M[7,0]<=1.25)
    def test_actual_sources_and_ids(self):
        for c in d.fixed_cases():
            src,name,ids=d.source(c); _,M=r.stock(self.fixture_run,c['fine'])
            target=np.repeat(M,3,axis=1) if src is None else a.arrays(self.fixture_run/'inputs/p13'/src,name)['final']
            x=a.arrays(self.fixture_run/c['id'],'intervention')['initial']
            np.testing.assert_array_equal(x[:,list(d.PATCH)],target)
            rec=json.loads((self.fixture_run/c['id']/'result.json').read_text())['phases'][0]
            self.assertEqual([rec['setup']['cell_ids'][p] for p in d.PATCH],ids)
            self.assertEqual(rec['logical_interval'],[d.logical_base(c),d.logical_base(c)+20000])
    def test_native_2d_geometry(self):
        x=a.arrays(self.fixture_run/self.primary['id'],'intervention')
        self.assertEqual(x['initial'].shape,(17,169)); self.assertEqual(len(x['edge_from']),312)
        self.assertEqual(int(np.sum(x['edge_region_initial']==1)),2)
        self.assertEqual(int(np.sum(x['edge_region_initial']==2)),8)
        end=a.labels(x['initial'],a.INDEX)
        self.assertEqual((int(np.sum(end=='M')),int(np.sum(end=='E'))),(12,157))
    def test_withdrawal_removes_all_temporary_settings(self):
        for c in d.fixed_cases():
            folder=self.fixture_run/c['id']; first=a.arrays(folder,'intervention')['final']
            x=a.arrays(folder,'withdrawal_1'); np.testing.assert_array_equal(x['initial'],first)
            np.testing.assert_array_equal(x['edge_power_initial'],np.choose(x['edge_region_initial'],[60.,60.,1.]))
            self.assertTrue(np.all(x['edge_available_initial']==1))
            rec=json.loads((folder/'result.json').read_text())['phases'][1]
            self.assertEqual(rec['setup']['mirna_kd'],1.25e-14)
    def test_only_one_cell_replaced_per_step(self):
        for c in d.fixed_cases():
            folder=self.fixture_run/c['id']; _,M=r.stock(self.fixture_run,c['fine'])
            before=a.arrays(folder,'withdrawal_2')['final']
            for i,pos in enumerate(d.PATCH):
                x=a.arrays(folder,'replacement_'+str(i+1)); keep=np.arange(169)!=pos
                np.testing.assert_array_equal(x['initial'][:,keep],before[:,keep])
                np.testing.assert_array_equal(x['initial'][:,pos:pos+1],d.incoming(M,i))
                before=x['final']
    def test_originals_and_helpers_removed_at_isolation(self):
        for c in d.fixed_cases():
            folder=self.fixture_run/c['id']; record=json.loads((folder/'result.json').read_text())
            ids=record['phases'][-1]['setup']['cell_ids']
            self.assertEqual(ids,[d.new_id(c,i) for i in range(3)])
            self.assertFalse(set(ids)&set(d.source(c)[2]))
            np.testing.assert_array_equal(a.arrays(folder,'isolated_1')['initial'],
                                          a.arrays(folder,'replacement_3')['final'][:,list(d.PATCH)])
            self.assertFalse(a.arrays(folder,'isolated_1')['junction_diffusion'].any())
    def test_fine_uses_own_actual_source(self):
        c=d.case(fine=True); src,name,_=d.source(c)
        self.assertTrue(src.endswith('__fine'))
        np.testing.assert_array_equal(a.arrays(self.fixture_run/c['id'],'intervention')['initial'][:,list(d.PATCH)],
                                      a.arrays(self.fixture_run/'inputs/p13'/src,name)['final'])
    def test_clocks_exact_and_all_evolve(self):
        result=json.loads((self.fixture_run/self.primary['id']/'result.json').read_text())
        cursor=1020000
        for rec in result['phases']:
            x=a.arrays(self.fixture_run/self.primary['id'],rec['phase'])
            self.assertEqual(rec['logical_interval'],[cursor,cursor+rec['requested_horizon']])
            cursor+=rec['requested_horizon']; self.assertEqual(x['times'][0],0)
            self.assertEqual(x['times'][-1],rec['requested_horizon']); self.assertTrue(np.all(np.diff(x['times'])==100))
            self.assertTrue(np.all(x['final'][0]!=x['initial'][0]))
        self.assertEqual(cursor,1140000)
    def fabricated(self,mode,c=None):
        c=self.primary if c is None else c
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            row=fixture_case(run,c,mode); checks,report,data=self.audit_branch(run,c)
            self.assertTrue(all(checks.rows.values()),[k for k,v in checks.rows.items() if not v])
            self.assertEqual(len(data),8)
            return report['outcome']
    def test_negative_science_still_runs_all_phases(self):
        out=self.fabricated('all_negative')
        self.assertFalse(out['tissue_correction']); self.assertFalse(out['corrected_at_intervention_end'])
    def test_relapse_is_separate_from_initial_correction(self):
        out=self.fabricated('relapse')
        self.assertTrue(out['corrected_at_intervention_end']); self.assertTrue(out['M_return_after_withdrawal'])
        self.assertTrue(out['lost_stable_correction']); self.assertFalse(out['tissue_correction'])
    def test_late_occupancy_not_just_final_labels(self):
        out=self.fabricated('late'); self.assertEqual(out['observations']['withdrawal_1']['patch_labels'],'EEE')
        self.assertFalse(out['persistent_after_withdrawal']); self.assertFalse(out['tissue_correction'])
    def test_failure_of_any_replacement_disqualifies(self):
        for n in (1,2,3):
            out=self.fabricated('replacement_'+str(n))
            self.assertFalse(out['all_replacements_corrected']); self.assertFalse(out['tissue_correction'])
    def test_isolation_failure_disqualifies(self):
        out=self.fabricated('isolation')
        self.assertTrue(out['all_replacements_corrected']); self.assertFalse(out['isolated_E_memory'])
        self.assertFalse(out['tissue_correction'])
    def test_background_spread_separately_reported(self):
        out=self.fabricated('spread')
        self.assertEqual(out['observations']['intervention']['background_E_now_M'],1)
        self.assertEqual(out['observations']['replacement_3']['maximum_background_E_now_M'],1)
        self.assertTrue(out['tissue_correction'])
    def test_positive_control_is_valid_but_limits_attribution(self):
        out=self.fabricated('positive_controls',d.case(arm='rna')); self.assertTrue(out['tissue_correction'])
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(arm='rna',fine=f)['id']]=out
        comparisons,mechanism=a.contrasts(by)
        self.assertFalse(mechanism[0]['provisional_both_mechanism_support'])
        self.assertTrue(next(x for x in comparisons if x['history']=='written' and x['arm']=='both')['tissue_correction_both'])
    def test_missing_control_never_qualifies(self):
        by=copy.deepcopy(self.by); by.pop(d.case(arm='cut')['id'])
        self.assertFalse(a.contrasts(by)[1][0]['provisional_both_mechanism_support'])
    def test_fine_not_independent_replication(self):
        self.assertTrue(all(x['source_trials']==1 for x in self.report['comparisons']))
        self.assertFalse(self.report['independent_biological_replicates'])
    def test_fine_disagreement_is_failure(self):
        cases=d.fixed_cases(); by=copy.deepcopy(self.by)
        endpoints={c['id']:{'end':dict(final=np.ones((17,3)))} for c in cases}
        by[d.case(fine=True)['id']]['tissue_correction']=False
        checks=a.Checks(); a.p12.compare_fine(cases,by,endpoints,checks)
        self.assertFalse(all(checks.rows.values()))

    def test_rehashed_source_reset_caught(self):
        self.corrupt_array('intervention',lambda x:x['initial'].__setitem__((0,83),x['initial'][0,83]+1))

    def test_rehashed_background_reset_caught(self):
        self.corrupt_array('withdrawal_1',lambda x:x['initial'].__setitem__((7,0),x['initial'][7,0]+1))

    def test_rehashed_old_carrier_reset_caught(self):
        self.corrupt_array('replacement_1',lambda x:x['initial'].__setitem__((7,84),x['initial'][7,84]+1))

    def test_rehashed_new_cell_alteration_caught(self):
        self.corrupt_array('replacement_2',lambda x:x['initial'].__setitem__((1,84),x['initial'][1,84]+1))

    def test_rehashed_clock_corruption_caught(self):
        self.corrupt_array('withdrawal_1',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_rehashed_boundary_not_withdrawn_caught(self):
        self.corrupt_array('withdrawal_1',lambda x:x['edge_power_initial'].__setitem__(0,59))

    def test_rehashed_bath_change_caught(self):
        self.corrupt_array('intervention',lambda x:x['environment'].__setitem__(0,x['environment'][0]+1))

    def test_rehashed_helper_retained_caught(self):
        self.corrupt_array('isolated_1',lambda x:x['initial'].__setitem__((0,0),x['initial'][0,0]+1))

    def test_wrong_ID_caught(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(83,'wrong'))
    def test_wrong_time_origin_caught(self):
        self.corrupt_result(lambda x:x['phases'][0].__setitem__('logical_interval',[0,20000]))
    def test_forged_success_caught(self):
        self.corrupt_result(lambda x:x['outcome'].__setitem__('tissue_correction',False))
    def test_forged_PH_claim_caught(self):
        self.corrupt_result(lambda x:x.__setitem__('new_isolated_PH_handover',True))
    def test_extra_phase_caught(self):
        with self.copied_primary() as (run,folder):
            shutil.copyfile(folder/'intervention.npz',folder/'unregistered.npz')
            checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))
    def test_missing_phase_caught(self):
        with self.copied_primary() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['phases'].pop()
            d.write_json(folder/'result.json',result)
            with self.assertRaises(ValueError): self.audit_branch(run,self.primary)
    def test_worker_guards_before_instantiation(self):
        for failure in ('case','stage','preflight','hash','draw'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                run=Path(temp); folder=run/'case'; folder.mkdir(); (run/'frozen').mkdir()
                c=copy.deepcopy(self.primary)
                if failure=='case': c['arm']='unregistered'
                d.write_json(folder/'spec.json',dict(config=d.FIXED,case=c,inputs=str(run/'inputs')))
                d.write_json(run/'predecessor_audit.json',self.history)
                h=d.digest(run/'predecessor_audit.json')
                d.write_json(run/'summary.json',dict(stage='wrong' if failure=='stage' else 'panel',
                    predecessor_gate=failure!='preflight',predecessor_audit=self.history,
                    predecessor_audit_sha256='bad' if failure=='hash' else h))
                d.write_json(run/'frozen/paper_tissue_persistence_draws_v1.json',{} if failure=='draw' else d.draw_book())
                with self.assertRaises(ValueError),patch.object(r,'ClockBoundedExperiment') as exp: r.worker(folder/'spec.json')
                exp.assert_not_called()
    def test_predecessor_both_copies_runner_and_auditor(self):
        saved=json.loads((self.fixture_run/'inputs/p13/independent_audit.json').read_text())
        for fn in (r.predecessor_audit,a.predecessor_audit):
            archived=copy.deepcopy(saved); archived['run']=str(self.fixture_run/'inputs/p13')
            with patch.object(a.p13,'analyze',side_effect=[copy.deepcopy(saved),archived]) as check:
                result=fn(self.fixture_run)
            self.assertTrue(result['quality_gate']); self.assertEqual(check.call_count,2)
            archived['quality_gate']=False
            with patch.object(a.p13,'analyze',side_effect=[copy.deepcopy(saved),archived]):
                self.assertFalse(fn(self.fixture_run)['quality_gate'])
    def flow(self,technical=True,execution=True,preflight=True):
        with tempfile.TemporaryDirectory(prefix='p14-flow-') as temp,redirect_stdout(io.StringIO()):
            output=Path(temp)/'output'; output.mkdir(); calls=[]
            def worker(c,config,run,deadline,env):
                calls.append(c); return dict(id=c['id'],execution_pass=execution)
            history=dict(self.history,quality_gate=preflight)
            with patch.object(r.tempfile,'mkdtemp',return_value=str(output)),patch.object(r,'freeze',return_value=({}, {}, {})),\
                 patch.object(r,'predecessor_audit',return_value=history),patch.object(r,'run_worker',side_effect=worker),\
                 patch.object(a,'stage_audit',return_value=dict(quality_gate=technical,eligible=True)),\
                 patch.object(a,'integrity',return_value={'fixture':True}),patch.object(d,'source_check'):
                try: code=r.run(d.ROOT/'configs/paper_tissue_persistence_v1.json')
                except RuntimeError:
                    if preflight: raise
                    code=1
            return code,calls,json.loads((output/'summary.json').read_text())
    def test_one_fixed_panel_only(self):
        code,calls,s=self.flow(); self.assertEqual((code,len(calls)),(0,36))
        self.assertEqual(len({c['id'] for c in calls}),36); self.assertEqual(s['completion_reason'],'all_registered_stages_completed')
    def test_technical_failure_no_followon(self):
        code,calls,s=self.flow(technical=False); self.assertEqual((code,len(calls)),(1,36))
        self.assertEqual(s['completion_reason'],'technical_gate_failure')
    def test_execution_failure_no_retry(self):
        code,calls,s=self.flow(execution=False); self.assertEqual((code,len(calls)),(1,36))
        self.assertEqual(s['completion_reason'],'execution_failure')
    def test_preflight_failure_no_integration(self):
        code,calls,_=self.flow(preflight=False); self.assertEqual((code,len(calls)),(1,0))
    def test_expired_worker_does_not_launch(self):
        with patch.object(r.subprocess,'run') as launch:
            result=r.run_worker(self.primary,d.FIXED,Path('/tmp'),time.monotonic()-1,{})
        launch.assert_not_called(); self.assertFalse(result['execution_pass'])

    def supervisor_fixture(self,verification_rc=0,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p14-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-tissue-persistence-test'; job.mkdir(parents=True)
            run=root/'runs/paper-tissue-persistence-test'; run.mkdir()
            source=root/'source'; source.write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={str(source):'bad' if bad_input else d.digest(source)}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time()))
            (job/'runner.log').write_text('Run artifacts: '+str(run)+'\n')
            d.write_json(run/'summary.json',dict(cases=[],registered_cases=[],stage='finished',
                completion_reason='all_registered_stages_completed',gates={},selection={}))
            d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,independent_check_count=1,
                all_fine_agree=True,comparisons=[],mechanism_contrasts=[]))
            called=[]
            def child(command,logfile,timeout,update):
                called.append(logfile.name); update(123)
                if not logfile.exists(): logfile.write_text('test output\n')
                if logfile.name=='verification.log': return verification_rc
                return runner_rc if logfile.name=='runner.log' else 0
            with (root/'lock').open('a+') as lock,patch.object(detached,'ROOT',root),\
                 patch.object(detached,'run_child',side_effect=child),patch.object(detached.os,'close'),\
                 patch.object(detached.signal,'signal'),redirect_stdout(io.StringIO()),patch('sys.stderr',new=io.StringIO()):
                code=detached.supervise(job,lock.fileno())
            return code,json.loads((job/'status.json').read_text()),called

    def test_49_supervisor_success_no_followon(self):
        code,meta,calls=self.supervisor_fixture(); self.assertEqual(code,0)
        self.assertEqual(meta['phase'],'complete'); self.assertEqual(calls,['verification.log','runner.log','audit.log'])

    def test_50_verification_failure_blocks_science(self):
        code,meta,calls=self.supervisor_fixture(verification_rc=1); self.assertEqual(code,1)
        self.assertEqual(calls,['verification.log']); self.assertEqual(meta['phase'],'failed')

    def test_51_verification_timeout_blocks_science(self):
        code,_,calls=self.supervisor_fixture(verification_rc=124); self.assertEqual(code,1)
        self.assertEqual(calls,['verification.log'])

    def test_52_runner_timeout_no_retry(self):
        code,_,calls=self.supervisor_fixture(runner_rc=124); self.assertEqual(code,1)
        self.assertEqual(calls,['verification.log','runner.log'])

    def test_53_bad_audit_not_success(self):
        code,meta,_=self.supervisor_fixture(audit_quality=False); self.assertEqual(code,1)
        self.assertEqual(meta['phase'],'failed')

    def test_54_changed_input_blocks_everything(self):
        code,_,calls=self.supervisor_fixture(bad_input=True); self.assertEqual(code,1); self.assertEqual(calls,[])

    def test_55_stale_status_does_not_relaunch(self):
        with tempfile.TemporaryDirectory(prefix='p14-status-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='returns',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale'])

    def test_56_wrong_run_path_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p14-discover-') as temp:
            job=Path(temp); (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)


if __name__=='__main__': unittest.main()
