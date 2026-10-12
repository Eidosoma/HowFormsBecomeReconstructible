"""P10R software fixtures and bounded-clock unit tests; no biological integrations."""
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
import paper_contact_clock_recovery_design as d
import run_paper_contact_clock_recovery as r
import analyze_paper_contact_clock_recovery as a
import run_paper_contact_clock_recovery_detached as detached


def fixture_case(run,case,config,negative_kind=None):
    folder=run/case['id']; folder.mkdir()
    exp=r.ClockBoundedExperiment(folder,dict(id=case['id'],fine=case['fine']),native_replay=case['kind']=='replay')
    names=a.phase_names(case,5 if case['kind']=='continuation' else 1)
    def fake_native(horizon):
        name=names[len(exp.records)]; start=exp.sim.cc_cells.copy()
        x=a.arrays(run/'inputs/p9/inputs/p8/inputs/p7'/case['source'],name)
        if not np.array_equal(start,x['initial']): raise AssertionError('Historical replay start mismatch')
        np.copyto(exp.sim.cc_cells,x['final']); return x['times'].copy(),x['concentrations'].copy()
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=names[len(exp.records)]; start=sim.cc_cells.copy(); number,part=a.parts(case,name)
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        if part.startswith('segment') and case['route']=='open' and case['founder']!='ordinary_E_sham' and case['kind']!=negative_kind:
            if case['schedule']=='simultaneous': mark(range(6),'E')
            elif case['schedule']!='short_10':
                mark([3+i for i in exp.active],'M')
                if case['kind']=='continuation' and case['founder']=='rewritten_restored_E' and case['schedule']=='sequential' and number==3 and 2 in exp.active:
                    mark([5],'E')
        sim.cc_cells[exp.indices['Na']]+=(.0011 if case['fine'] else .001)+.00001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        step=np.full(total//cap,cap,dtype=np.int64); proposed=np.full(len(step),2*stride,dtype=np.int64)
        shot_ticks=np.arange(0,total+1,stride,dtype=np.int64); times=shot_ticks*base
        shots=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); shots[0]=start
        trace=dict(clock_step_ticks=step,clock_proposed_ticks=proposed,clock_sample_ticks=shot_ticks)
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(step),sample_count=len(shots),capped_steps=len(step),
            initial_and_final_samples=True,integer_tick_clock=True)
        return times,shots,trace,meta
    with patch.object(exp.sim,'sim',side_effect=fake_native),patch.object(r.clock,'integrate',side_effect=fake_clock):
        rounds=r.trajectory(exp,case,run)
    result=r.result_record(exp,case,rounds); d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result,
                result_sha256=d.digest(folder/'result.json'))


class TestPaperContactClockRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p10r-software-fixture-')
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        cls.config=json.loads((d.ROOT/'configs/paper_contact_clock_recovery_v1.json').read_text())
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
            gate=None,failed_attempt_audit=None,clock_probe_audit=None,calibration_audit=None,screen_audit=None,selected=[])
        def checkpoint(name,fn):
            report=fn(cls.fixture_run); d.write_json(cls.fixture_run/(name+'.json'),report)
            cls.summary.update({name:report,name+'_sha256':d.digest(cls.fixture_run/(name+'.json'))})
            d.write_json(cls.fixture_run/'summary.json',cls.summary)
        with redirect_stdout(io.StringIO()):
            d.write_json(cls.fixture_run/'summary.json',cls.summary)
            checkpoint('failed_attempt_audit',a.failed_attempt_audit)
            for case in d.fixed_cases():
                cls.summary['cases'].append(fixture_case(cls.fixture_run,case,cls.config))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                if len(cls.summary['cases'])==2: checkpoint('gate',a.gate_audit)
                if len(cls.summary['cases'])==14: checkpoint('clock_probe_audit',a.clock_probe_audit)
                if len(cls.summary['cases'])==22: checkpoint('calibration_audit',a.calibration_audit)
            checkpoint('screen_audit',a.screen_audit)
            selected=cls.summary['screen_audit']['selected']; cls.summary['selected']=selected
            more=d.continuation_cases(selected); cls.summary['registered_cases']+=more
            for case in more: cls.summary['cases'].append(fixture_case(cls.fixture_run,case,cls.config))
        cls.summary.update(all_execution_valid=True,completion_reason='selected_continuations_completed')
        d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.report=a.analyze(cls.fixture_run); cls.reports={b['case']['id']:b for b in cls.report['branches']}
        cls.primary=d.make_case('screen','rewritten_restored_E')['id']
        cls.cont=d.make_case('continuation','ordinary_M')['id']

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_01_independent_registration(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),72)
        self.assertEqual(len(d.continuation_cases(['sequential','overlap_50'])),24)
        self.assertEqual(d.fixed_cases()+d.continuation_cases(['sequential','overlap_50']),a.expected_cases(['sequential','overlap_50']))

    def test_02_fixed_config(self):
        self.assertEqual(d.validate_config(self.config),d.FIXED)
        for key,value in (('maximum_rounds',12),('workers',3),('all_six_cells_evolve',False),('kd',0)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{key:value}))

    def test_03_full_fixture_audit(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate'])
        self.assertTrue(self.report['gate']['quality_gate']); self.assertTrue(self.report['calibration']['eligible'])
        self.assertEqual(self.report['totals']['executed_cases'],96)

    def test_04_known_replays(self):
        b=self.report['gate']['branches']
        self.assertTrue(b[0]['outcomes']['all_recipient_M']); self.assertTrue(b[1]['outcomes']['all_recipient_E'])

    def test_05_graph_and_segments(self):
        self.assertEqual(d.GRAPH,a.GRAPH)
        for schedule in list(d.SCHEDULES)+['single']: self.assertEqual(d.segments(schedule),a.intervals(schedule))
        self.assertEqual([len(d.segments(s)) for s in d.SCHEDULES],[4,2,6,5,5,6,6])

    def test_06_equal_per_pupil_contact_time_except_short(self):
        for schedule in d.SCHEDULES:
            for pupil in range(3):
                self.assertEqual(sum(b-a for a,b,active in d.segments(schedule) if pupil in active),
                                 10000 if schedule=='short_10' else 20000)
            self.assertEqual(sum(b-a for a,b,_ in d.segments(schedule)),80000)

    def test_07_actual_P9_live_group(self):
        x=a.arrays(self.fixture_run/self.primary,'r01_segment_01')['initial'][:,:3]
        old=a.arrays(self.fixture_run/'inputs/p9'/d.LINEAGE,'r06_isolated_2')
        self.assertTrue(np.array_equal(x,old['final']))
        self.assertFalse(np.array_equal(x,old['concentrations'][-1]))

    def test_08_common_graph_exact_edges(self):
        for b in self.report['branches']:
            if b['case']['kind'] in ('replay','clock_probe'): continue
            x=a.arrays(self.fixture_run/b['case']['id'],a.phase_names(b['case'])[0])
            self.assertEqual(list(zip(x['edge_from'],x['edge_to'])),list(d.GRAPH))

    def test_09_all_six_states_continuous(self):
        folder=self.fixture_run/self.primary
        for slot in range(2,5):
            previous=a.arrays(folder,f'r01_segment_{slot-1:02d}')['final']
            current=a.arrays(folder,f'r01_segment_{slot:02d}')['initial']
            self.assertTrue(np.array_equal(previous,current))

    def test_10_waiting_pupils_not_frozen(self):
        x=a.arrays(self.fixture_run/self.primary,'r01_segment_01')
        self.assertFalse(np.array_equal(x['initial'][:,4:],x['final'][:,4:]))
        self.assertEqual(x['edge_available_initial'].tolist(),[1,1,1,1,0,0,0,0])

    def test_11_active_mask_overlap(self):
        case=d.make_case('screen','ordinary_M','overlap_50'); names=a.phase_names(case)
        x=a.arrays(self.fixture_run/case['id'],names[1])
        self.assertEqual(x['edge_available_initial'].tolist(),[1,1,1,1,1,1,0,0])
        x=a.arrays(self.fixture_run/case['id'],names[2])
        self.assertEqual(x['edge_available_initial'].tolist(),[1,1,0,0,1,1,1,1])

    def test_12_explicit_metadata_no_lattice_claim(self):
        rec=self.summary['cases'][22]['result']['phases'][0]['setup']
        self.assertIsNone(rec['grid_shape']); self.assertFalse(rec['orthogonal_only'])
        self.assertEqual(rec['storage_shape'],[1,6]); self.assertEqual(rec['network_mode'],'explicit_common_graph')

    def test_13_all_teachers_removed(self):
        folder=self.fixture_run/self.primary
        last=a.arrays(folder,'r01_segment_04')['final']
        self.assertTrue(np.array_equal(a.arrays(folder,'r01_isolated_1')['initial'],last[:,3:]))
        self.assertEqual(last.shape,(17,6))

    def test_14_actual_screen_prefix_continues(self):
        start=a.arrays(self.fixture_run/self.cont,'r02_segment_01')['initial'][:,:3]
        source=a.arrays(self.fixture_run/d.make_case('screen','ordinary_M')['id'],'r01_isolated_2')
        self.assertTrue(np.array_equal(start,source['final']))
        self.assertTrue(np.array_equal(start,source['concentrations'][-1]))

    def test_15_fine_uses_own_screen_not_coarse(self):
        coarse=a.arrays(self.fixture_run/self.cont,'r02_segment_01')['initial'][:,:3]
        fine=a.arrays(self.fixture_run/(self.cont+'__fine'),'r02_segment_01')['initial'][:,:3]
        prefix=a.arrays(self.fixture_run/d.make_case('screen','ordinary_M',fine=True)['id'],'r01_isolated_2')['final']
        self.assertTrue(np.array_equal(fine,prefix)); self.assertFalse(np.array_equal(fine,coarse))

    def test_16_complete_replacements_without_reset(self):
        folder=self.fixture_run/self.cont
        for number in range(3,7):
            start=a.arrays(folder,f'r{number:02d}_segment_01')['initial'][:,:3]
            self.assertTrue(np.array_equal(start,a.arrays(folder,f'r{number-1:02d}_isolated_2')['final']))
        self.assertTrue(self.reports[self.cont]['outcomes']['complete_six_rounds'])
        self.assertEqual(self.reports[self.cont]['outcomes']['new_rounds'],5)

    def test_17_partial_failure_stops_after_all_holds(self):
        case=d.make_case('continuation','rewritten_restored_E'); b=self.reports[case['id']]
        self.assertEqual(b['outcomes']['new_rounds'],2); self.assertEqual(b['rounds'][-1]['retained_M'],2)
        self.assertFalse(b['outcomes']['complete_six_rounds'])
        self.assertTrue((self.fixture_run/case['id']/'r03_isolated_2.npz').exists())
        self.assertFalse((self.fixture_run/case['id']/'r04_segment_01.npz').exists())

    def test_18_controls_use_same_actual_prefix(self):
        for route in ('rna','cut'):
            c=d.make_case('continuation','ordinary_M',route=route)
            x=a.arrays(self.fixture_run/c['id'],'r02_segment_01')
            self.assertTrue(np.array_equal(x['initial'],a.arrays(self.fixture_run/self.cont,'r02_segment_01')['initial']))
            self.assertEqual(self.reports[c['id']]['outcomes']['new_rounds'],1)

    def test_19_rna_preserves_small_ions(self):
        c=d.make_case('screen','ordinary_M',route='rna'); x=a.arrays(self.fixture_run/c['id'],'r01_segment_01')
        self.assertTrue(x['junction_diffusion'][:4].any())
        rec=next(v for v in self.summary['cases'] if v['id']==c['id'])['result']['phases'][0]
        self.assertEqual(rec['setup']['mirna_kd'],0)

    def test_20_boundary_cut_preserves_teacher_edges(self):
        c=d.make_case('screen','ordinary_M',route='cut'); x=a.arrays(self.fixture_run/c['id'],'r01_segment_01')
        self.assertEqual(x['edge_available_initial'].tolist(),[1,1,0,0,0,0,0,0])

    def test_21_all_pupils_same_round_age(self):
        rec=next(v for v in self.summary['cases'] if v['id']==self.primary)['result']
        for i in range(3):
            phases=[p for p in rec['phases'] if f'p10:pupil:01:{i:02d}' in p['setup']['cell_ids']]
            self.assertEqual(sum(p['requested_horizon'] for p in phases),100000)
        self.assertEqual(rec['phases'][-1]['logical_interval'],[90000,100000])

    def test_22_all_finer_comparisons(self):
        self.assertEqual(len(self.report['fine_comparisons']),47)
        self.assertTrue(self.report['all_selected_fine_agree'])

    def test_23_manifest(self):
        self.assertEqual(len(d.LOCAL_FILES),84); self.assertEqual(len(self.summary['hashes_sha256']),120)
        self.assertEqual(len(self.summary['inputs']),734)
        bad=copy.deepcopy(self.summary); bad['inputs']={}
        self.assertFalse(all(a.integrity(self.fixture_run,bad).values()))

    def test_24_selection_priority_and_common_founders(self):
        self.assertEqual(self.summary['selected'],['sequential','overlap_50'])
        by=copy.deepcopy({b['case']['id']:b for b in self.report['screen']['branches']})
        by[d.make_case('screen','ordinary_M','overlap_50',fine=True)['id']]['outcomes']['all_recipient_M']=False
        self.assertEqual(a.choose_schedules(by)[0],['sequential','overlap_25'])

    def test_25_selection_requires_sham_and_baseline_controls(self):
        by=copy.deepcopy({b['case']['id']:b for b in self.report['screen']['branches']})
        by[d.make_case('screen','ordinary_M',route='rna')['id']]['outcomes']['all_recipient_E']=False
        self.assertEqual(a.choose_schedules(by)[0],['overlap_50'])
        by[d.make_case('screen','ordinary_E_sham','overlap_50')['id']]['outcomes']['all_recipient_E']=False
        self.assertEqual(a.choose_schedules(by)[0],['overlap_25'])
        self.assertEqual(a.choose_schedules({})[0],[])

    def test_26_two_holds_required(self):
        one=a.arrays(self.fixture_run/self.primary,'r01_isolated_1'); two=a.arrays(self.fixture_run/self.primary,'r01_isolated_2')
        idx=next(v for v in self.summary['cases'] if v['id']==self.primary)['result']['ion_indices']
        self.assertTrue(a.stable(one,two,idx,'M').all())
        one['concentrations'][-2,idx['miR200_total']]=10000
        self.assertTrue(a.stable(one,two,idx,'M').all())
        one['concentrations'][-3,idx['miR200_total']]=10000
        self.assertFalse(a.stable(one,two,idx,'M').any())

    def mutate(self,edit,cid=None):
        cid=cid or self.primary; temp=tempfile.TemporaryDirectory(prefix='p10r-mutated-'); self.addCleanup(temp.cleanup); run=Path(temp.name)
        for path in self.fixture_run.iterdir():
            if path.name==cid: continue
            (run/path.name).symlink_to(path,target_is_directory=path.is_dir())
        folder=run/cid; shutil.copytree(self.fixture_run/cid,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result); d.write_json(folder/'result.json',result)
        checks=a.Checks(); a.branch(folder,result['case'],checks); return checks.rows

    def array_edit(self,phase,key,change):
        def edit(folder,result):
            rec=next(p for p in result['phases'] if p['phase']==phase); x=a.arrays(folder,phase); change(x[key])
            np.savez_compressed(folder/(phase+'.npz'),**x); rec['sha256']=d.digest(folder/(phase+'.npz'))
        return edit

    def test_27_rehashed_wrong_founder(self):
        rows=self.mutate(self.array_edit('r01_segment_01','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r01_segment_01/all_six_live_states'])

    def test_28_rehashed_teacher_reset(self):
        rows=self.mutate(self.array_edit('r01_segment_02','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r01_segment_02/all_six_live_states'])

    def test_29_rehashed_frozen_waiting_pupil(self):
        rows=self.mutate(self.array_edit('r01_segment_02','initial',lambda x:x.__setitem__((0,5),0)))
        self.assertFalse(rows[self.primary+'/r01_segment_02/all_six_live_states'])

    def test_30_rehashed_pupil_substitution(self):
        rows=self.mutate(self.array_edit('r01_isolated_1','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r01_all_teachers_removed_all_pupils_kept'])

    def test_31_rehashed_wrong_screen_prefix(self):
        rows=self.mutate(self.array_edit('r02_segment_01','initial',lambda x:x.__setitem__((0,0),0)),self.cont)
        self.assertFalse(rows[self.cont+'/r02_segment_01/all_six_live_states'])

    def test_32_rehashed_bad_edge(self):
        rows=self.mutate(self.array_edit('r01_segment_01','edge_to',lambda x:x.__setitem__(0,5)))
        self.assertFalse(rows[self.primary+'/r01_segment_01/topology'])

    def test_33_rehashed_bad_mask(self):
        rows=self.mutate(self.array_edit('r01_segment_01','edge_available_initial',lambda x:x.fill(1)))
        self.assertFalse(rows[self.primary+'/r01_segment_01/edge_available_initial'])

    def test_34_rehashed_bad_expression(self):
        rows=self.mutate(self.array_edit('r01_segment_01','expression_gate_final',lambda x:x.fill(1)))
        self.assertFalse(rows[self.primary+'/r01_segment_01/expression_final'])

    def test_35_wrong_clock(self):
        def edit(folder,result): result['phases'][1]['logical_interval']=[40000,60000]
        self.assertFalse(self.mutate(edit)[self.primary+'/r01_segment_02/logical_interval'])

    def test_36_wrong_identity(self):
        def edit(folder,result): result['phases'][1]['setup']['cell_ids'][0]='replacement:M:00'
        self.assertFalse(self.mutate(edit)[self.primary+'/r01_segment_02/ids'])

    def test_37_partial_cannot_claim_full(self):
        cid=d.make_case('continuation','rewritten_restored_E')['id']
        def edit(folder,result): result['rounds'][-1]['complete']=True
        self.assertFalse(self.mutate(edit,cid)[cid+'/r03_record'])

    def test_38_wrong_stop_reason(self):
        cid=d.make_case('continuation','rewritten_restored_E')['id']
        def edit(folder,result): result['stop_reason']='six_complete_rounds'
        self.assertFalse(self.mutate(edit,cid)[cid+'/stop_reason'])

    def test_39_native_hooks_restored_and_masks_no_reset(self):
        with tempfile.TemporaryDirectory(prefix='p10r-construction-') as temp,redirect_stdout(io.StringIO()):
            exp=r.CommonGraphExperiment(Path(temp),dict(id='fixture',fine=False))
            before=(exp.z.setup_GJ_3D,exp.z.GJs_3D_give_to_sim); E,M=r.reference(r.stock_root(self.fixture_run))
            state=np.concatenate((np.repeat(M,3,axis=1),np.repeat(E,3,axis=1)),axis=1)
            exp.configure_graph([str(i) for i in range(6)],state,'open')
            self.assertEqual(before,(exp.z.setup_GJ_3D,exp.z.GJs_3D_give_to_sim))
            self.assertTrue(np.array_equal(state,exp.sim.cc_cells))
            for active in ([],[0],[0,1],[0,1,2]):
                exp.set_active(active); self.assertTrue(np.array_equal(state,exp.sim.cc_cells))
            with self.assertRaises(ValueError): exp.set_active([3])
            with patch.object(exp.z.GRN,'seed3D_inputs',side_effect=RuntimeError('fixture')):
                with self.assertRaises(RuntimeError): exp.configure_graph([str(i) for i in range(6)],state,'open')
            self.assertEqual(before,(exp.z.setup_GJ_3D,exp.z.GJs_3D_give_to_sim))

    def test_40_budget_prevents_worker(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(d.fixed_cases()[0],self.config,self.fixture_run,time.monotonic()-1,{})
        self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_41_timeout_no_retry(self):
        with tempfile.TemporaryDirectory(prefix='p10r-timeout-') as temp,patch.object(r.subprocess,'run',
            side_effect=subprocess.TimeoutExpired('fixture',1)) as proc,redirect_stdout(io.StringIO()):
            result=r.run_worker(d.fixed_cases()[0],self.config,Path(temp),time.monotonic()+10,{})
        self.assertEqual(result['status'],'timeout'); self.assertEqual(proc.call_count,1)

    def stage_fixture(self,predecessor=True,replay=True,calibration=True,screen=True,eligible=True,selected=('sequential','overlap_50'),clock_checks=True,failed_history=True):
        with tempfile.TemporaryDirectory(prefix='p10r-stages-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            def fake_freeze(run): (run/'frozen').mkdir(); return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                summary=json.loads((run/'summary.json').read_text()); self.assertTrue(summary['predecessor_gate'])
                if case['kind']!='replay': self.assertTrue(summary['gate']['quality_gate'])
                if case['kind'] in ('screen','continuation'): self.assertTrue(summary['calibration_audit']['eligible'])
                if case['kind']=='continuation': self.assertTrue(summary['screen_audit']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            path=Path(__file__).resolve().parents[1]/'configs/paper_contact_clock_recovery_v1.json'
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch.object(r,'predecessor_gate',return_value=predecessor),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':replay}), \
                 patch.object(a,'failed_attempt_audit',return_value={'quality_gate':failed_history}), \
                 patch.object(a,'clock_probe_audit',return_value={'quality_gate':clock_checks}), \
                 patch.object(a,'calibration_audit',return_value={'quality_gate':calibration,'eligible':eligible}), \
                 patch.object(a,'screen_audit',return_value={'quality_gate':screen,'selected':list(selected)}), \
                 patch.object(r,'run_worker',side_effect=fake_worker),redirect_stdout(io.StringIO()):
                if not predecessor:
                    with self.assertRaisesRegex(RuntimeError,'P9 re-audit failed'): r.run(path)
                    return 1,called
                return r.run(path),called

    def test_42_bad_predecessor_stops_native(self):
        code,calls=self.stage_fixture(predecessor=False); self.assertEqual((code,len(calls)),(1,0))

    def test_43_bad_replay_stops_graph(self):
        code,calls=self.stage_fixture(replay=False); self.assertEqual((code,len(calls)),(1,2))

    def test_44_negative_calibration_valid_stop(self):
        code,calls=self.stage_fixture(eligible=False); self.assertEqual((code,len(calls)),(0,22))

    def test_45_calibration_quality_failure_stops(self):
        code,calls=self.stage_fixture(calibration=False); self.assertEqual((code,len(calls)),(1,22))

    def test_46_screen_fine_failure_stops(self):
        code,calls=self.stage_fixture(screen=False); self.assertEqual((code,len(calls)),(1,72))

    def test_47_no_candidate_valid_stop(self):
        code,calls=self.stage_fixture(selected=()); self.assertEqual((code,len(calls)),(0,72))

    def test_48_full_selected_panel(self):
        code,calls=self.stage_fixture(); self.assertEqual((code,len(calls)),(0,96))
        self.assertEqual(len(set(calls)),96)
    def test_49_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory(prefix='p10r-lock-') as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-contact-clock-recovery.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False,verification_rc=0):
        with tempfile.TemporaryDirectory(prefix='p10r-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-contact-clock-recovery-test'; job.mkdir(parents=True)
            run=root/'runs/paper-contact-clock-recovery-test'; run.mkdir()
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
                if not logfile.exists(): logfile.write_text('software fixture output\n')
                if logfile.name=='verification.log': return verification_rc
                return runner_rc if logfile.name=='runner.log' else 0
            with (root/'lock').open('a+') as lock,patch.object(detached,'ROOT',root), \
                 patch.object(detached,'run_child',side_effect=child),patch.object(detached.os,'close'), \
                 patch.object(detached.signal,'signal'),redirect_stdout(io.StringIO()),patch('sys.stderr',new=io.StringIO()):
                code=detached.supervise(job,lock.fileno())
            return code,json.loads((job/'status.json').read_text()),called

    def test_50_supervisor_success_stops_after_audit(self):
        code,meta,called=self.supervisor_fixture(); self.assertEqual(code,0)
        self.assertEqual(meta['phase'],'complete'); self.assertEqual(called,['verification.log','runner.log','audit.log'])

    def test_51_supervisor_runner_failure_no_retry(self):
        code,meta,called=self.supervisor_fixture(runner_rc=124); self.assertEqual(code,1)
        self.assertEqual(meta['phase'],'failed'); self.assertEqual(called,['verification.log','runner.log'])

    def test_52_supervisor_audit_failure(self):
        code,meta,called=self.supervisor_fixture(audit_quality=False); self.assertEqual(code,1)
        self.assertEqual(meta['phase'],'failed'); self.assertEqual(called,['verification.log','runner.log','audit.log'])

    def test_53_supervisor_rejects_changed_input(self):
        code,meta,called=self.supervisor_fixture(bad_input=True); self.assertEqual(code,1)
        self.assertEqual(called,[]); self.assertIn('inputs changed',meta['error'])

    def test_54_stale_heartbeat_not_automatic_relaunch(self):
        with tempfile.TemporaryDirectory(prefix='p10r-status-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='coarse_screen',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale'])

    def test_55_discover_rejects_unrelated_output(self):
        with tempfile.TemporaryDirectory(prefix='p10r-path-') as temp:
            job=Path(temp); (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)


    def test_56_selection_has_no_post_result_substitution(self):
        self.assertEqual(self.report['screen']['selected'],['sequential','overlap_50'])
        failed=self.reports[d.make_case('continuation','rewritten_restored_E')['id']]
        self.assertFalse(failed['outcomes']['complete_six_rounds'])
        self.assertFalse(any(b['case'].get('kind')=='continuation' and b['case']['schedule']=='overlap_25' for b in self.report['branches']))

    def test_57_calibration_reports_unexposed_pupils(self):
        c=d.make_case('calibration','ordinary_M','single')
        b=self.reports[c['id']]
        self.assertEqual(b['outcomes']['retained_M_by_pupil'],[True,False,False])
        self.assertEqual(b['outcomes']['retained_E_by_pupil'],[False,True,True])
        self.assertEqual(b['rounds'][0]['presignal_labels'],['E',None,None])

    def test_58_worker_rejects_unregistered_case_before_integration(self):
        with tempfile.TemporaryDirectory(prefix='p10r-spec-') as temp:
            run=Path(temp); folder=run/'case'; folder.mkdir()
            bad=d.make_case('screen','ordinary_M','unregistered')
            d.write_json(folder/'spec.json',dict(case=bad,config=self.config,inputs=str(run/'inputs')))
            with patch.object(r,'CommonGraphExperiment') as exp:
                with self.assertRaises(ValueError): r.worker(folder/'spec.json')
                exp.assert_not_called()

    def test_59_six_rounds_counts_screen_once(self):
        c=self.reports[self.cont]['outcomes']
        self.assertEqual(c['new_rounds']+c['shared_screen_rounds'],6)
        self.assertEqual([x['round'] for x in self.reports[self.cont]['rounds']],[2,3,4,5,6])
        self.assertFalse((self.fixture_run/self.cont/'r01_segment_01.npz').exists())

    def test_60_all_presignal_labels_and_no_hidden_freshening(self):
        for b in self.report['screen']['branches']:
            if b['case']['founder']=='ordinary_E_sham': continue
            self.assertEqual(b['rounds'][0]['presignal_labels'],['E']*3)

    def negative_fixture(self,kind):
        with tempfile.TemporaryDirectory(prefix='p10r-negative-') as temp,redirect_stdout(io.StringIO()):
            run=Path(temp); hashes,frozen,inputs=r.freeze(run)
            summary=dict(revision=d.REVISION,config=self.config,registered_cases=d.fixed_cases(),cases=[],
                hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
                gate=None,calibration_audit=None,screen_audit=None,selected=[])
            d.write_json(run/'summary.json',summary)
            failed=a.failed_attempt_audit(run); d.write_json(run/'failed_attempt_audit.json',failed)
            summary.update(failed_attempt_audit=failed,failed_attempt_audit_sha256=d.digest(run/'failed_attempt_audit.json'))
            for case in d.fixed_cases()[:22 if kind=='calibration' else 72]:
                summary['cases'].append(fixture_case(run,case,self.config,negative_kind=kind))
                d.write_json(run/'summary.json',summary)
                gate=('gate',a.gate_audit) if len(summary['cases'])==2 else ('clock_probe_audit',a.clock_probe_audit) if len(summary['cases'])==14 else ('calibration_audit',a.calibration_audit) if len(summary['cases'])==22 else ('screen_audit',a.screen_audit) if len(summary['cases'])==72 else None
                if gate:
                    name,fn=gate; result=fn(run); d.write_json(run/(name+'.json'),result)
                    summary.update({name:result,name+'_sha256':d.digest(run/(name+'.json'))})
                    d.write_json(run/'summary.json',summary)
            summary.update(all_execution_valid=True,completion_reason='common_graph_not_qualified' if kind=='calibration' else 'no_eligible_schedule')
            d.write_json(run/'summary.json',summary)
            return a.analyze(run)

    def test_61_negative_calibration_full_audit_valid(self):
        report=self.negative_fixture('calibration')
        self.assertTrue(report['quality_gate']); self.assertFalse(report['calibration']['eligible'])
        self.assertEqual(report['totals']['executed_cases'],22); self.assertIsNone(report['screen'])

    def test_62_negative_screen_full_audit_valid(self):
        report=self.negative_fixture('screen')
        self.assertTrue(report['quality_gate']); self.assertTrue(report['calibration']['eligible'])
        self.assertEqual(report['totals']['executed_cases'],72); self.assertEqual(report['totals']['selected_schedules'],[])

    def test_63_fine_disagreement_detected(self):
        cases=a.expected_cases()[22:72]; checks=a.Checks()
        reports,endpoints,_=a.audited_records(self.fixture_run,cases,checks)
        cid=d.make_case('screen','ordinary_M',fine=True)['id']; name='r01_segment_01'
        start,end,labs=endpoints[cid][name]; labs=labs.copy(); labs[0]='E'
        endpoints[cid][name]=(start,end,labs)
        checks=a.Checks(); a.compare_fine(cases,reports,endpoints,checks)
        self.assertFalse(checks.rows[cid+'/fine'])

    def test_64_more_than_two_candidates_rejected(self):
        with self.assertRaises(ValueError): d.continuation_cases(['sequential','overlap_25','overlap_50'])



    def test_65_clock_probe_uses_actual_pre_hold_initial(self):
        for c in d.probe_cases():
            start=a.arrays(self.fixture_run/c['id'],'isolated_1')['initial']
            old=a.arrays(self.fixture_run/'inputs/failed_attempt'/c['source'],'r01_isolated_1')
            self.assertTrue(np.array_equal(start,old['initial']))
            if c['fine']:
                other=a.arrays(self.fixture_run/c['id'].removesuffix('__fine'),'isolated_1')['initial']
                self.assertTrue(np.array_equal(start,other))

    def test_66_exact_observation_grid_and_live_endpoint(self):
        for b in self.report['branches']:
            if b['case']['kind']=='replay': continue
            info=next(c['result'] for c in self.summary['cases'] if c['id']==b['case']['id'])
            for rec in info['phases']:
                x=a.arrays(self.fixture_run/b['case']['id'],rec['phase'])
                self.assertEqual(x['times'][0],0); self.assertEqual(x['times'][-1],rec['requested_horizon'])
                self.assertTrue(np.all(np.diff(x['times'])==100))
                self.assertTrue(np.array_equal(x['concentrations'][-1],x['final']))

    def test_67_rehashed_clock_overshoot_rejected(self):
        rows=self.mutate(self.array_edit('r01_segment_01','clock_step_ticks',lambda x:x.__setitem__(-1,int(x[-1])+1)))
        self.assertFalse(rows[self.primary+'/r01_segment_01/clock/exact_final_tick'])
        self.assertFalse(rows[self.primary+'/r01_segment_01/clock/every_boundary_respected'])

    def test_68_rehashed_clock_boundaries_not_just_final_time(self):
        def change(x): x[0]+=1; x[1]-=1
        rows=self.mutate(self.array_edit('r01_segment_01','clock_step_ticks',change))
        self.assertFalse(rows[self.primary+'/r01_segment_01/clock/exact_step_clipping'])
        self.assertTrue(rows[self.primary+'/r01_segment_01/clock/exact_final_tick'])

    def test_69_rehashed_relabelled_observation_rejected(self):
        rows=self.mutate(self.array_edit('r01_isolated_1','times',lambda x:x.__setitem__(-1,10000000)))
        self.assertFalse(rows[self.primary+'/r01_isolated_1/clock/observations'])

    def test_70_missing_sample_trace_rejected(self):
        def edit(folder,result):
            name='r01_isolated_1'; x=a.arrays(folder,name); del x['clock_sample_ticks']
            np.savez_compressed(folder/(name+'.npz'),**x)
            next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
        self.assertFalse(self.mutate(edit)[self.primary+'/r01_isolated_1/clock/required_arrays'])

    def test_71_rehashed_fake_first_observation_rejected(self):
        rows=self.mutate(self.array_edit('r01_isolated_1','concentrations',lambda x:x.__setitem__((0,0,0),0)))
        self.assertFalse(rows[self.primary+'/r01_isolated_1/clock/first_live_sample'])

    def test_72_bad_clock_gate_stops_before_calibration(self):
        code,calls=self.stage_fixture(clock_checks=False); self.assertEqual((code,len(calls)),(1,14))

    def test_73_failed_history_must_stay_auditable(self):
        code,calls=self.stage_fixture(failed_history=False); self.assertEqual((code,len(calls)),(1,0))

    def test_74_failed_attempt_not_reclassified(self):
        old=self.report['failed_attempt']
        self.assertTrue(old['quality_gate']); self.assertFalse(old['old_attempt_quality_gate'])
        self.assertEqual(len(old['old_failure_keys']),6); self.assertEqual(len(old['large_overshoots']),10)
        self.assertTrue(old['failed_attempt_is_not_reclassified_as_success'])
        self.assertFalse(self.reports[self.primary]['case']['kind']=='clock_probe')

    def test_75_bounded_function_restored_on_error(self):
        with tempfile.TemporaryDirectory(prefix='p10r-restore-') as temp,redirect_stdout(io.StringIO()):
            exp=r.ClockBoundedExperiment(Path(temp),dict(id='fixture',fine=False))
            E,M=r.reference(r.stock_root(self.fixture_run))
            exp.configure([1,3],[str(i) for i in range(3)],np.repeat(M,3,axis=1),isolated=True)
            original=exp.sim.sim
            with patch.object(r.clock,'integrate',side_effect=RuntimeError('fixture')):
                with self.assertRaises(RuntimeError): exp.phase('isolated_1',10000)
            self.assertIs(exp.sim.sim,original)

    def test_76_verification_failure_prevents_native_runner(self):
        code,meta,called=self.supervisor_fixture(verification_rc=1)
        self.assertEqual(code,1); self.assertEqual(meta['phase'],'failed')
        self.assertEqual(called,['verification.log'])


class TestBoundedClockKernel(unittest.TestCase):
    def system(self,fine=False,adaptive=True):
        from types import SimpleNamespace as N
        p=N(time_step=.005 if fine else .01,use_implicit=False,no_dumps=True,adaptive_timestep=adaptive,
            cell_vol=1.,cell_sa=1.,F=1.,cm=1.,GJ_len=1.,
            sim_integ_max_delt_cc=.0005 if fine else .001,sim_integ_max_delt_Vm=.0005 if fine else .001)
        sim=N(GP=p,cc_cells=np.ones((2,1)),z_array=np.array([1.,0.]),GJ_diffusion=np.zeros(2))
        sim.sim_slopes=lambda t:np.zeros_like(sim.cc_cells)
        return sim

    def test_01_zero_slope_exact_horizon(self):
        s=self.system(); t,x,tr,m=r.clock.integrate(s,10000,100,100)
        self.assertEqual(len(t),101); self.assertEqual(t[-1],10000)
        self.assertTrue(np.array_equal(x[0],x[-1])); self.assertEqual(m['iterations'],100)
        self.assertEqual(tr['clock_step_ticks'].sum(),1000000)

    def test_02_fine_halves_step_cap_but_not_observation_grid(self):
        s=self.system(True); t,x,tr,m=r.clock.integrate(s,10000,100,50)
        self.assertEqual(len(t),101); self.assertEqual(m['iterations'],200)
        self.assertLessEqual(tr['clock_step_ticks'].max()*s.GP.time_step,50)

    def test_03_partial_last_observation_interval(self):
        s=self.system(); t,x,tr,m=r.clock.integrate(s,250,100,100)
        self.assertEqual(t.tolist(),[0,100,200,250]); self.assertEqual(tr['clock_step_ticks'].tolist(),[10000,10000,5000])

    def test_04_timed_input_is_not_skipped(self):
        s=self.system(); s.sim_slopes=lambda t:np.full_like(s.cc_cells,.001 if 100<=t<200 else 0)
        t,x,tr,m=r.clock.integrate(s,250,100,100)
        self.assertTrue(np.allclose(x[1],1,rtol=0,atol=1e-12))
        self.assertTrue(np.allclose(x[-1],1.1,rtol=0,atol=1e-12))

    def test_05_native_proposal_formula_preserved(self):
        s=self.system(); rng=np.random.default_rng(19)
        for _ in range(20):
            slope=rng.uniform(-.01,.01,(2,1)); slope[1,0]=0; before=slope.copy()
            dv=(slope*s.z_array[:,None]).sum(0)*s.GP.cell_vol/s.GP.cell_sa*s.GP.F/s.GP.cm
            vm=s.GP.sim_integ_max_delt_Vm/np.abs(dv).max()
            v=np.absolute(s.cc_cells/np.where(slope==0,1,slope)); v[slope==0]=1e10
            cc=s.GP.sim_integ_max_delt_cc*v.min()
            expected=max(1,int(min(vm,cc)/s.GP.time_step))
            self.assertEqual(r.clock.proposal(s,slope),expected)
            self.assertTrue(np.array_equal(slope,before))

    def test_06_minimum_tick_still_advances(self):
        s=self.system(); s.GP.sim_integ_max_delt_Vm=1e-10
        s.sim_slopes=lambda t:np.full_like(s.cc_cells,.1)
        t,x,tr,m=r.clock.integrate(s,.03,.01,.01)
        self.assertEqual(tr['clock_step_ticks'].tolist(),[1,1,1]); self.assertAlmostEqual(x[-1,0,0],1.003)

    def test_07_nonadaptive_uses_base_ticks(self):
        s=self.system(adaptive=False); t,x,tr,m=r.clock.integrate(s,.04,.02,.02)
        self.assertEqual(tr['clock_step_ticks'].tolist(),[1,1,1,1]); self.assertFalse(m['adaptive'])

    def test_08_negative_state_rejected(self):
        s=self.system(); s.cc_cells.fill(0); s.sim_slopes=lambda t:-np.ones_like(s.cc_cells)
        with self.assertRaises(ValueError): r.clock.integrate(s,1,1,1)

    def test_09_nonfinite_slope_rejected(self):
        s=self.system(); s.sim_slopes=lambda t:np.full_like(s.cc_cells,np.nan)
        with self.assertRaises(ValueError): r.clock.integrate(s,1,1,1)

    def test_10_wrong_slope_shape_rejected(self):
        s=self.system(); s.sim_slopes=lambda t:np.zeros((2,2))
        with self.assertRaises(ValueError): r.clock.integrate(s,1,1,1)

    def test_11_incompatible_clock_rejected(self):
        for horizon in (0,-1,float('nan'),float('inf'),.005):
            with self.assertRaises(ValueError): r.clock.integrate(self.system(),horizon,1,1)

    def test_12_implicit_or_dumping_rejected(self):
        for key,val in (('use_implicit',True),('no_dumps',False)):
            s=self.system(); setattr(s.GP,key,val)
            with self.assertRaises(ValueError): r.clock.integrate(s,1,1,1)

    def test_13_native_stability_precheck_preserved(self):
        s=self.system(); s.GJ_diffusion.fill(100)
        with self.assertRaises(ValueError): r.clock.integrate(s,1,1,1)

    def test_14_observation_snapshots_are_independent(self):
        s=self.system(); t,x,tr,m=r.clock.integrate(s,300,100,100)
        s.cc_cells.fill(5)
        self.assertTrue(np.all(x==1)); self.assertEqual(m['capped_steps'],m['iterations'])

    def test_15_native_zero_slope_bug_reproduced_and_prevented(self):
        with tempfile.TemporaryDirectory(prefix='p10r-native-zero-') as temp,redirect_stdout(io.StringIO()):
            exp=r.CommonGraphExperiment(Path(temp),dict(id='zero-slope-fixture',fine=False))
            exp.configure([1,1],['synthetic:00'],None,isolated=True); original=exp.sim.cc_cells.copy()
            with patch.object(exp.sim,'sim_slopes',side_effect=lambda t:np.zeros_like(exp.sim.cc_cells)),np.errstate(divide='ignore'):
                old_t,_=exp.sim.sim(10000)
                self.assertEqual(old_t,[10000000.])
                np.copyto(exp.sim.cc_cells,original)
                t,x,tr,m=r.clock.integrate(exp.sim,10000,100,100)
            self.assertEqual(t[-1],10000); self.assertEqual(len(t),101)
            self.assertTrue(np.array_equal(x[-1],original))


if __name__=='__main__': unittest.main()
