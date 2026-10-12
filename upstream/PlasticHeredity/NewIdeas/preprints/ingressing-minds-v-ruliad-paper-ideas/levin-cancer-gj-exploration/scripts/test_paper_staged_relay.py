"""P9 software-only fixtures: native factories/gates, integration replaced."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import paper_staged_relay_design as d
import run_paper_staged_relay as r
import analyze_paper_staged_relay as a
import run_paper_staged_relay_detached as detached


def fixture_case(run,case,config):
    folder=run/case['id']; folder.mkdir()
    exp=r.TopologyExperiment(folder,dict(id=case['id'],fine=case['fine']))
    names=a.phase_names(case)
    def fake_sim(horizon):
        name=names[len(exp.records)]; start=exp.sim.cc_cells.copy(); source=None
        source_parent=run/'inputs/p8/inputs/p7'
        if case['kind']=='replay': source=(case['source'],name)
        elif case['founder']=='ordinary_M' and not case['fine']:
            if case['condition']=='sequential' and name=='r01_contact_1': source=(a.old_case('three_to_one')['id'],'contact')
            if case['condition']=='simultaneous_20' and name=='r01_contact': source=(a.old_case('three_to_three')['id'],'contact')
        elif case['founder'].startswith('rewritten_') and not case['fine'] and case['condition']=='sequential' and name=='r01_contact_1':
            source_parent=run/'inputs/p8'
            source=('rewrite__'+case['founder'].removeprefix('rewritten_')+'__M_open','probe_contact')
        if source:
            x=a.arrays(source_parent/source[0],source[1])
            if not np.array_equal(start,x['initial']): raise AssertionError('Historical fixture start mismatch')
            np.copyto(exp.sim.cc_cells,x['final']); return x['times'].copy(),x['concentrations'].copy()
        number,part=a.parts(case,name)
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(exp.sim.cc_cells,i)
        if part.startswith('contact'):
            condition=case['condition']; h=case['founder']
            if condition=='sequential' and h!='ordinary_E_sham':
                mark(range(4),'M')
                if h=='rewritten_restored_E' and number==3 and part=='contact_3': mark([3],'E')
            elif condition=='simultaneous_20': mark(range(6),'E')
            elif condition=='simultaneous_60': mark(range(6),'M' if h=='ordinary_M' else 'E')
        exp.sim.cc_cells[exp.indices['Na']]+=.001+.00001*np.arange(len(exp.ids))
        last=exp.sim.cc_cells.copy(); last[exp.indices['Na']]-=.0005
        return np.array([0.,horizon*.8,float(horizon)]),np.array([start,last,last])
    with patch.object(exp.sim,'sim',side_effect=fake_sim): rounds=r.trajectory(exp,case,run)
    result=r.result_record(exp,case,rounds); d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result,
                result_sha256=d.digest(folder/'result.json'))


class TestPaperStagedRelay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p9-software-fixture-')
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        cls.config=json.loads((d.ROOT/'configs/paper_staged_relay_v1.json').read_text())
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,gate=None)
        with redirect_stdout(io.StringIO()):
            for case in d.fixed_cases():
                cls.summary['cases'].append(fixture_case(cls.fixture_run,case,cls.config))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                if len(cls.summary['cases'])==2:
                    gate=a.gate_audit(cls.fixture_run); d.write_json(cls.fixture_run/'gate.json',gate)
                    cls.summary.update(gate=gate,gate_sha256=d.digest(cls.fixture_run/'gate.json'))
        cls.summary['all_execution_valid']=True; d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.report=a.analyze(cls.fixture_run); cls.reports={b['case']['id']:b for b in cls.report['branches']}
        cls.primary='relay__rewritten_ordinary_E__sequential'

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_01_panel(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),34)
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),16)
        self.assertEqual(sum(len(a.phase_names(c,1)) for c in d.fixed_cases()),188)
        self.assertEqual(sum(len(a.phase_names(c,6)) for c in d.fixed_cases()),1098)

    def test_02_fixed_config(self):
        self.assertEqual(d.validate_config(self.config),d.FIXED)
        for key,value in (('maximum_rounds',12),('workers',3),('waiting_cells_evolve',False),('kd',0)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{key:value}))

    def test_03_full_fixture_audit(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        self.assertEqual([k for k,v in self.report['gate']['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['native_integrations'],386)

    def test_04_replays_positive_and_negative(self):
        reports=self.report['gate']['branches']
        self.assertTrue(reports[0]['outcomes']['all_recipient_M']); self.assertTrue(reports[1]['outcomes']['all_recipient_E'])

    def test_05_actual_written_founders(self):
        for h in ('ordinary_E','restored_E'):
            folder=self.fixture_run/('relay__rewritten_'+h+'__sequential')
            start=a.arrays(folder,'r01_contact_1')['initial'][:,:3]
            source=a.arrays(self.fixture_run/'inputs/p8'/('rewrite__'+h+'__M_open'),'writing_isolated_2')
            self.assertTrue(np.array_equal(start,source['final']))
            self.assertFalse(np.array_equal(start,source['concentrations'][-1]))

    def test_06_old_one_cell_probe_not_duplicated(self):
        x=a.arrays(self.fixture_run/'inputs/p8/rewrite__ordinary_E__M_open','probe_isolated_2')['final']
        start=a.arrays(self.fixture_run/self.primary,'r01_contact_1')['initial'][:,:3]
        self.assertFalse(np.array_equal(start,np.repeat(x,3,axis=1)))

    def test_07_same_teachers_continuously_updated(self):
        folder=self.fixture_run/self.primary
        for slot in (2,3):
            prior=a.arrays(folder,f'r01_contact_{slot-1}')['final'][:,:3]
            current=a.arrays(folder,f'r01_contact_{slot}')['initial'][:,:3]
            self.assertTrue(np.array_equal(current,prior))
            self.assertFalse(np.array_equal(current,a.arrays(folder,'r01_contact_1')['initial'][:,:3]))

    def test_08_waiting_cells_advance(self):
        folder=self.fixture_run/self.primary
        one=a.arrays(folder,'r01_waiting_2'); two=a.arrays(folder,'r01_waiting_3')
        self.assertFalse(np.array_equal(one['initial'],one['final']))
        self.assertTrue(np.array_equal(two['initial'][:,:1],one['final']))
        self.assertTrue(np.array_equal(two['initial'][:,1:2],a.arrays(folder,'r01_contact_2')['final'][:,3:4]))

    def test_09_all_pupils_assembled_without_selection(self):
        folder=self.fixture_run/self.primary
        assembled=np.concatenate((a.arrays(folder,'r01_waiting_3')['final'],a.arrays(folder,'r01_contact_3')['final'][:,3:4]),axis=1)
        self.assertTrue(np.array_equal(a.arrays(folder,'r01_isolated_1')['initial'],assembled))

    def test_10_full_replacement_between_rounds(self):
        folder=self.fixture_run/self.primary
        self.assertTrue(np.array_equal(a.arrays(folder,'r02_contact_1')['initial'][:,:3],a.arrays(folder,'r01_isolated_2')['final']))
        info=json.loads((folder/'result.json').read_text())
        for phase in info['phases']:
            if phase['phase'].startswith('r02'):
                self.assertTrue(all(not x.startswith('relay:06:') for x in phase['setup']['cell_ids']))

    def test_11_every_pupil_fresh_E(self):
        E,_,_=a.stock(self.fixture_run); folder=self.fixture_run/self.primary
        for number in range(1,7):
            for slot in range(1,4):
                self.assertTrue(np.array_equal(a.arrays(folder,f'r{number:02d}_contact_{slot}')['initial'][:,3:4],E))

    def test_12_six_rounds_no_shrinking(self):
        report=self.reports[self.primary]
        self.assertTrue(report['outcomes']['complete_six_rounds'])
        self.assertEqual([x['retained_M'] for x in report['rounds']],[3]*6)
        self.assertEqual(report['outcomes']['newly_exposed_pupils'],18)

    def test_13_partial_round_stops_after_all_pupils(self):
        report=self.reports['relay__rewritten_restored_E__sequential']
        self.assertEqual(report['outcomes']['successful_rounds'],2)
        self.assertEqual(report['outcomes']['first_incomplete_round'],3)
        self.assertEqual(report['rounds'][-1]['retained_M'],2)
        self.assertFalse(report['outcomes']['complete_six_rounds'])
        folder=self.fixture_run/report['case']['id']
        self.assertTrue((folder/'r03_isolated_2.npz').exists()); self.assertFalse((folder/'r04_contact_1.npz').exists())

    def test_14_logical_waits_overlap_contacts(self):
        info=json.loads((self.fixture_run/self.primary/'result.json').read_text())
        phases={p['phase']:p for p in info['phases']}
        for slot in (2,3):
            self.assertEqual(phases[f'r01_contact_{slot}']['logical_interval'],phases[f'r01_waiting_{slot}']['logical_interval'])
        self.assertEqual(phases['r01_isolated_2']['logical_interval'],[70000,80000])
        self.assertEqual(phases['r02_contact_1']['logical_interval'],[80000,100000])

    def test_15_pupil_elapsed_ages(self):
        info=json.loads((self.fixture_run/self.primary/'result.json').read_text())
        for slot,age in enumerate((80000,60000,40000)):
            found=[p for p in info['phases'] if p['phase'].startswith('r01') and f'pupil:01:{slot:02d}' in p['setup']['cell_ids']]
            self.assertEqual(sum(p['requested_horizon'] for p in found),age)

    def test_16_short_simultaneous_matches_round_duration(self):
        case=next(c for c in d.fixed_cases() if c.get('condition')=='simultaneous_20')
        self.assertEqual([a.settings(case,n)[-1] for n in a.round_phase_names(case,1)],[20000,40000,10000,10000])
        self.assertEqual(a.logical_interval(case,'r01_isolated_2')[-1],80000)

    def test_17_long_simultaneous_allowed_to_succeed(self):
        report=self.reports['relay__ordinary_M__simultaneous_60']
        self.assertTrue(report['outcomes']['complete_six_rounds'])
        self.assertTrue(self.report['contrasts'][2]['control_qualified_renewal'])
        info=json.loads((self.fixture_run/report['case']['id']/'result.json').read_text())
        self.assertEqual(info['phases'][0]['requested_horizon'],60000)

    def test_18_matched_blocked_routes(self):
        for condition in ('sequential_rna','sequential_cut'):
            report=self.reports['relay__rewritten_ordinary_E__'+condition]
            self.assertEqual(report['outcomes']['completed_rounds'],1)
            self.assertTrue(report['outcomes']['all_pupils_E_in_first_round'])

    def test_19_RNA_keeps_small_ions(self):
        folder=self.fixture_run/'relay__rewritten_ordinary_E__sequential_rna'
        info=json.loads((folder/'result.json').read_text())['phases'][0]
        self.assertEqual(info['setup']['mirna_kd'],0)
        self.assertTrue(a.arrays(folder,'r01_contact_1')['junction_diffusion'][:4].any())

    def test_20_cut_preserves_within_teacher_edges(self):
        x=a.arrays(self.fixture_run/'relay__rewritten_ordinary_E__sequential_cut','r01_contact_1')
        region=x['edge_region_initial']; available=x['edge_available_initial']
        self.assertEqual(sum(region==2),2); self.assertTrue(np.all(available[region==2]==0))
        self.assertTrue(np.all(available[region!=2]==1))

    def test_21_two_retention_holds(self):
        folder=self.fixture_run/self.primary; idx=json.loads((folder/'result.json').read_text())['ion_indices']
        one,two=a.arrays(folder,'r01_isolated_1'),a.arrays(folder,'r01_isolated_2')
        self.assertTrue(a.stable(one,two,idx,'M').all())
        one['concentrations'][-1,idx['miR200_total']]=10000
        self.assertFalse(a.stable(one,two,idx,'M').any())

    def test_22_all_sixteen_finer(self):
        self.assertEqual(len(self.report['fine_comparisons']),16); self.assertTrue(self.report['all_selected_fine_agree'])
        for c in d.fixed_cases():
            if c['fine']:
                info=json.loads((self.fixture_run/c['id']/'result.json').read_text())
                self.assertTrue(all(p['setup']['integrator']['time_step']==.00005 for p in info['phases']))

    def test_23_manifest_complete(self):
        self.assertEqual(len(d.LOCAL_FILES),69); self.assertEqual(len(self.summary['hashes_sha256']),105)
        self.assertEqual(len(self.summary['inputs']),68)
        bad=copy.deepcopy(self.summary); bad['inputs']={}
        self.assertFalse(all(a.integrity(self.fixture_run,bad).values()))

    def mutate(self,edit,cid=None):
        cid=cid or self.primary; temp=tempfile.TemporaryDirectory(prefix='p9-mutated-'); self.addCleanup(temp.cleanup); run=Path(temp.name)
        for path in self.fixture_run.iterdir():
            if path.name==cid: continue
            (run/path.name).symlink_to(path,target_is_directory=path.is_dir())
        folder=run/cid; shutil.copytree(self.fixture_run/cid,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result); d.write_json(folder/'result.json',result)
        checks=a.Checks(); a.branch(folder,next(c for c in d.fixed_cases() if c['id']==cid),checks); return checks.rows

    def array_edit(self,phase,key,change):
        def edit(folder,result):
            rec=next(p for p in result['phases'] if p['phase']==phase); x=a.arrays(folder,phase); change(x[key])
            np.savez_compressed(folder/(phase+'.npz'),**x); rec['sha256']=d.digest(folder/(phase+'.npz'))
        return edit

    def test_24_rehashed_wrong_founder(self):
        rows=self.mutate(self.array_edit('r01_contact_1','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r01_contact_1/live_teachers'])

    def test_25_rehashed_teacher_reset(self):
        rows=self.mutate(self.array_edit('r01_contact_2','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r01_contact_2/live_teachers'])

    def test_26_rehashed_frozen_waiting_cell(self):
        rows=self.mutate(self.array_edit('r01_waiting_3','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r01_waiting_3/live_waiting_pupils'])

    def test_27_rehashed_pupil_substitution(self):
        rows=self.mutate(self.array_edit('r01_isolated_1','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r01_all_teachers_removed_all_pupils_kept'])

    def test_28_rehashed_between_round_reset(self):
        rows=self.mutate(self.array_edit('r02_contact_1','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r02_contact_1/live_teachers'])

    def test_29_wrong_identity(self):
        def edit(folder,result): result['phases'][1]['setup']['cell_ids'][0]='replacement:M:00'
        self.assertFalse(self.mutate(edit)[self.primary+'/r01_contact_2/ids'])

    def test_30_wrong_waiting_time(self):
        def edit(folder,result): result['phases'][2]['logical_interval']=[40000,60000]
        self.assertFalse(self.mutate(edit)[self.primary+'/r01_waiting_2/logical_interval'])

    def test_31_partial_cannot_claim_full(self):
        cid='relay__rewritten_restored_E__sequential'
        def edit(folder,result): result['rounds'][-1]['complete']=True
        self.assertFalse(self.mutate(edit,cid)[cid+'/r03_record'])

    def test_32_wrong_stop_reason(self):
        cid='relay__rewritten_restored_E__sequential'
        def edit(folder,result): result['stop_reason']='six_complete_rounds'
        self.assertFalse(self.mutate(edit,cid)[cid+'/stop_reason'])

    def test_33_rehashed_bad_boundary(self):
        cid='relay__rewritten_ordinary_E__sequential_cut'
        rows=self.mutate(self.array_edit('r01_contact_1','edge_available_initial',lambda x:x.fill(1)),cid)
        self.assertFalse(rows[cid+'/r01_contact_1/edge_available_initial'])

    def test_34_rehashed_bad_expression(self):
        rows=self.mutate(self.array_edit('r01_contact_1','expression_gate_final',lambda x:x.fill(1)))
        self.assertFalse(rows[self.primary+'/r01_contact_1/expression_final'])

    def test_35_qualifier_needs_blocks_and_sham(self):
        conditions=copy.deepcopy(self.report['contrasts'][0]['conditions']); sham=self.report['ordinary_E_sham']
        self.assertTrue(a.qualify(conditions,sham))
        for key in ('sequential_rna','sequential_cut'):
            bad=copy.deepcopy(conditions); bad[key]['all_pupils_E_in_first_round']=False
            self.assertFalse(a.qualify(bad,sham))
        self.assertFalse(a.qualify(conditions,{}))

    def test_36_budget_prevents_worker(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(d.fixed_cases()[0],self.config,self.fixture_run,time.monotonic()-1,{})
        self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_37_timeout_no_retry(self):
        with tempfile.TemporaryDirectory(prefix='p9-timeout-') as temp,patch.object(r.subprocess,'run',
            side_effect=subprocess.TimeoutExpired('fixture',1)) as proc,redirect_stdout(io.StringIO()):
            result=r.run_worker(d.fixed_cases()[0],self.config,Path(temp),time.monotonic()+10,{})
        self.assertEqual(result['status'],'timeout'); self.assertEqual(proc.call_count,1)

    def stage_fixture(self,predecessor=True,replay=True):
        with tempfile.TemporaryDirectory(prefix='p9-stages-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            def fake_freeze(run): (run/'frozen').mkdir(); return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                summary=json.loads((run/'summary.json').read_text()); self.assertTrue(summary['predecessor_gate'])
                if case['kind']=='relay': self.assertTrue(summary['gate']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            path=Path(__file__).resolve().parents[1]/'configs/paper_staged_relay_v1.json'
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch.object(r,'predecessor_gate',return_value=predecessor),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':replay}), \
                 patch.object(r,'run_worker',side_effect=fake_worker),redirect_stdout(io.StringIO()):
                if not predecessor:
                    with self.assertRaisesRegex(RuntimeError,'Historical re-audit failed'): r.run(path)
                    return 1,called
                return r.run(path),called

    def test_38_predecessor_failure_stops_native(self):
        code,calls=self.stage_fixture(predecessor=False); self.assertEqual(code,1); self.assertEqual(calls,[])

    def test_39_replay_failure_stops_relays(self):
        code,calls=self.stage_fixture(replay=False); self.assertEqual(code,1); self.assertEqual(len(calls),2)

    def test_40_all_branches_run_regardless_other_outcomes(self):
        code,calls=self.stage_fixture(); self.assertEqual(code,0); self.assertEqual(len(calls),34)
        self.assertFalse(self.report['positive_new_renewal_required'])

    def test_41_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory(prefix='p9-lock-') as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-staged-relay.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p9-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-staged-relay-test'; job.mkdir(parents=True)
            run=root/'runs/paper-staged-relay-test'; run.mkdir()
            source=root/'source'; source.write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={str(source):'wrong' if bad_input else d.digest(source)}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time()))
            (job/'runner.log').write_text('Run artifacts: '+str(run)+'\n')
            d.write_json(run/'summary.json',dict(cases=[],registered_cases=[],predecessor_gate=True,gate={'quality_gate':True},stage='historical_replays'))
            d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,independent_check_count=1,
                gate={'quality_gate':True},all_selected_fine_agree=True))
            called=[]
            def child(command,logfile,timeout,update):
                called.append(logfile.name); update(123)
                return runner_rc if logfile.name=='runner.log' else 0
            with (root/'lock').open('a+') as lock,patch.object(detached,'ROOT',root), \
                 patch.object(detached,'run_child',side_effect=child),patch.object(detached.os,'close'), \
                 patch.object(detached.signal,'signal'),redirect_stdout(io.StringIO()),patch('sys.stderr',new=io.StringIO()):
                code=detached.supervise(job,lock.fileno())
            return code,json.loads((job/'status.json').read_text()),called

    def test_42_supervisor_success_stops_after_audit(self):
        code,meta,called=self.supervisor_fixture(); self.assertEqual(code,0)
        self.assertEqual(meta['phase'],'complete'); self.assertEqual(called,['runner.log','audit.log'])

    def test_43_supervisor_runner_failure_no_retry(self):
        code,meta,called=self.supervisor_fixture(runner_rc=124); self.assertEqual(code,1)
        self.assertEqual(meta['phase'],'failed'); self.assertEqual(called,['runner.log'])

    def test_44_supervisor_audit_failure(self):
        code,meta,called=self.supervisor_fixture(audit_quality=False); self.assertEqual(code,1)
        self.assertEqual(meta['phase'],'failed'); self.assertEqual(called,['runner.log','audit.log'])

    def test_45_supervisor_rejects_changed_input(self):
        code,meta,called=self.supervisor_fixture(bad_input=True); self.assertEqual(code,1)
        self.assertEqual(called,[]); self.assertIn('inputs changed',meta['error'])

    def test_46_stale_heartbeat_not_automatic_relaunch(self):
        with tempfile.TemporaryDirectory(prefix='p9-status-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='coarse_relays',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale'])

    def test_47_discover_rejects_unrelated_output(self):
        with tempfile.TemporaryDirectory(prefix='p9-path-') as temp:
            job=Path(temp); (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)

    def test_48_rewritten_first_contacts_exact_P8(self):
        for h in ('ordinary_E','restored_E'):
            folder=self.fixture_run/('relay__rewritten_'+h+'__sequential')
            old=a.arrays(self.fixture_run/'inputs/p8'/('rewrite__'+h+'__M_open'),'probe_contact')
            current=a.arrays(folder,'r01_contact_1')
            self.assertEqual(set(current),set(old))
            for key in old: self.assertTrue(np.array_equal(current[key],old[key]))

    def test_49_waiting_readouts_identify_slots(self):
        waits=self.reports[self.primary]['rounds'][0]['pupil_waiting']
        self.assertEqual([x['pupil_slots'] for x in waits],[[0],[0,1]])
        self.assertEqual([x['final_labels'] for x in waits],['M','MM'])


if __name__=='__main__': unittest.main()
