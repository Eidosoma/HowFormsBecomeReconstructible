"""P5 software-only fixtures: real factories/gates, synthetic integration."""
from contextlib import redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import paper_relay_design as d
import run_paper_relay as r
import analyze_paper_relay as a
import run_paper_relay_detached as detached
import paper_topology_design as p4d
import run_paper_topology as p4r
from test_paper_topology import fixture_case as p4_fixture
from test_paper_sheet import fixture_case as p3_fixture
import paper_sheet_design as p3d


def fixture_case(run,case,config):
    folder=run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,inputs=str(run/'inputs')))
    exp=r.TopologyExperiment(folder,dict(id=case['id'],fine=case['fine'])); calls=[]
    def fake_sim(horizon):
        start=exp.sim.cc_cells.copy(); calls.append(horizon)
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(exp.sim.cc_cells,i)
        if exp.shape==[2,3] and not exp.isolated:
            if case['kind']=='replay' or case['route']=='open':
                mark(range(6),'E' if np.sum(a.labels(start[:,:3],exp.indices)=='E')==3 else 'M')
            if case['kind']=='relay' and case['route']=='open':
                number=2+(len(calls)-1)//3
                # Synthetic failure/recovery and partial outcomes test the bookkeeping,
                # not the biology. All corresponding coarse/fine fixtures agree.
                if case['ancestry']=='ordinary_E' and number in (5,6):
                    mark(range(6),'M' if number==5 else 'E')
                if case['ancestry']=='failed_M' and number==4: mark([3,4],'E')
        # A synthetic round-specific ionic tag makes unintended historical-state
        # reuse observable. Exact P4 replay fixtures retain their original increment.
        increment=.001 if case['kind']=='replay' else .001+.0001*(2+(len(calls)-1)//3)
        exp.sim.cc_cells[exp.indices['Na']]+=increment
        last=exp.sim.cc_cells.copy(); last[exp.indices['Na']]-=.0005
        return np.array([0.,horizon*.8,float(horizon)]),np.array([start,last,last])
    with patch.object(exp.sim,'sim',side_effect=fake_sim): r.trajectory(exp,case,run/'inputs')
    replay=case['kind']=='replay'
    result=dict(case=case,ion_indices=exp.indices,phases=exp.records,execution_pass=True,
        parameter_retuning=False,outcome_dependent_selection=False,cell_division_simulated=False,
        artificial_target_schedule=False,external_handover_schedule=True,source_external_regional_intervention=True,
        historical_rounds=0 if replay else 1,newly_simulated_rounds=1 if replay else 11,
        total_rounds=1 if replay else 12,midway_rewriting=False,stress_panel=False)
    d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result,
                result_sha256=d.digest(folder/'result.json'))


class TestPaperRelay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p5-software-fixture-')
        temp=Path(cls.temp.name)
        p3source=temp/'p3'; p3source.mkdir()
        p4source=temp/'p4'; p4source.mkdir()
        cls.fixture_run=temp/'run'; cls.fixture_run.mkdir()
        original_paths=p4d.input_paths()
        for name in ('summary.json','gate.json','bank_gate.json'):
            d.write_json(p3source/name,dict(quality_gate=True,synthetic_software_fixture=True))
        d.write_json(p3source/'independent_audit.json',dict(quality_gate=True,
            independent_check_count=18941,native_integrations=465,synthetic_software_fixture=True))
        wanted={'reference','assay__E','assay__M'}|{f'bank__{h}__edge' for h in ('depol','nbrDepol','hypol')}|{
            f'main__depol__edge__s3__{s}' for s in ('neither','voltage','expression','both')}
        cases=sorted((c for c in p3d.fixed_cases() if c['id'] in wanted),
            key=lambda c:{'reference':0,'bank':1,'main':2,'assay':3}[c['kind']])
        with redirect_stdout(io.StringIO()):
            for c in cases: p3_fixture(p3source,c,p3d.FIXED)
            with patch.object(p4d,'input_paths',return_value={k:p3source/k for k in original_paths}):
                p4r.freeze(p4source)
            for c in p4d.fixed_cases():
                if c['kind']=='capacity': p4_fixture(p4source,c,p4d.FIXED)
        for name in ('summary.json','gate.json'):
            d.write_json(p4source/name,dict(quality_gate=True,synthetic_software_fixture=True))
        d.write_json(p4source/'independent_audit.json',dict(quality_gate=True,
            independent_check_count=42565,native_integrations=858,synthetic_software_fixture=True))
        cls.input_patcher=patch.object(d,'PREDECESSOR',p4source); cls.input_patcher.start()
        cls.config=json.loads((d.ROOT/'configs/paper_relay_v1.json').read_text())
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,gate=None)
        with redirect_stdout(io.StringIO()):
            for c in d.fixed_cases():
                cls.summary['cases'].append(fixture_case(cls.fixture_run,c,cls.config))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                if len(cls.summary['cases'])==4:
                    gate=a.gate_audit(cls.fixture_run); d.write_json(cls.fixture_run/'gate.json',gate)
                    cls.summary.update(gate=gate,gate_sha256=d.digest(cls.fixture_run/'gate.json'))
        cls.summary['all_execution_valid']=True; d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.report=a.analyze(cls.fixture_run)
        cls.reports={b['case']['id']:b for b in cls.report['branches']}
        cls.primary='relay__restored_E__open'

    @classmethod
    def tearDownClass(cls): cls.input_patcher.stop(); cls.temp.cleanup()

    def test_01_exact_panel(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),28)
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),12)
        self.assertEqual(sum(c['kind']=='replay' for c in d.fixed_cases()),4)

    def test_02_config_fixed(self):
        self.assertEqual(d.validate_config(self.config),self.config)
        for k,v in (('total_rounds',20),('recipients',4),('workers',3),('midway_rewriting',True)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{k:v}))

    def test_03_complete_fixture_audit(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['native_integrations'],804)
        self.assertEqual(self.report['totals']['continuation_rounds_simulated'],264)

    def test_04_exact_historical_replay(self):
        self.assertTrue(self.report['gate']['quality_gate'])
        rows={k:v for k,v in self.report['gate']['checks'].items() if '/replay/' in k}
        self.assertGreater(len(rows),300); self.assertTrue(all(rows.values()))

    def test_05_eleven_new_not_twelve_new(self):
        for c in d.fixed_cases():
            if c['kind']!='relay': continue
            report=self.reports[c['id']]
            self.assertEqual([x['round'] for x in report['rounds']],list(range(1,13)))
            self.assertTrue(report['rounds'][0]['historical'])
            self.assertEqual(report['outcomes']['newly_simulated_rounds'],11)
            self.assertEqual(len(a.phase_names(c)),33)

    def test_06_continuation_uses_actual_p4_recipients(self):
        old=a.arrays(self.fixture_run/'inputs/capacity__restored_E','onward_isolated_2')
        new=a.arrays(self.fixture_run/self.primary,'r02_contact')
        self.assertTrue(np.array_equal(new['initial'][:,:3],old['final']))
        self.assertFalse(np.array_equal(new['initial'][:,:3],old['concentrations'][-1]))

    def test_07_later_live_endpoints_not_reset(self):
        folder=self.fixture_run/self.primary
        first=a.arrays(folder,'r02_isolated_2'); following=a.arrays(folder,'r03_contact')
        historical=a.arrays(self.fixture_run/'inputs/capacity__restored_E','onward_isolated_2')
        self.assertTrue(np.array_equal(following['initial'][:,:3],first['final']))
        self.assertFalse(np.array_equal(following['initial'][:,:3],first['concentrations'][-1]))
        self.assertFalse(np.array_equal(following['initial'][:,:3],historical['final']))

    def test_08_every_recipient_initially_fresh_M(self):
        _,M=r.reference(self.fixture_run/'inputs/p4_inputs')
        for case in d.fixed_cases():
            if case['kind']!='relay': continue
            for num in range(2,13):
                value=a.arrays(self.fixture_run/case['id'],f'r{num:02d}_contact')
                self.assertTrue(np.array_equal(value['initial'][:,3:],np.repeat(M,3,axis=1)))

    def test_09_identity_turnover(self):
        info=json.loads((self.fixture_run/self.primary/'result.json').read_text())
        incoming=set(['new:00','new:01','new:02'])
        all_removed=set()
        for number in range(2,13):
            contact,first,second=info['phases'][3*(number-2):3*(number-1)]
            ids=contact['setup']['cell_ids']; fresh=ids[3:]
            self.assertEqual(set(ids[:3]),incoming); self.assertFalse(set(ids)&all_removed)
            self.assertEqual(first['setup']['cell_ids'],fresh); self.assertEqual(second['setup']['cell_ids'],fresh)
            self.assertFalse(set(fresh)&incoming); all_removed.update(incoming); incoming=set(fresh)

    def test_10_three_to_three_counts_and_geometry(self):
        for case in d.fixed_cases():
            for name in a.phase_names(case):
                shape,ids=a.geometry(case,name)
                self.assertEqual(shape,[2,3] if name.endswith('_contact') else [1,3])
                self.assertEqual(len(ids),6 if name.endswith('_contact') else 3)

    def test_11_positive_full_renewal(self):
        out=self.reports[self.primary]['outcomes']
        self.assertTrue(out['all_rounds_E']); self.assertEqual(out['unbroken_E_prefix'],12)
        self.assertIsNone(out['first_failed_E_round']); self.assertEqual(out['final_recipient_E'],3)

    def test_12_late_failure_then_recovery_not_hidden(self):
        out=self.reports['relay__ordinary_E__open']['outcomes']
        self.assertFalse(out['all_rounds_E']); self.assertEqual(out['first_failed_E_round'],5)
        self.assertEqual(out['unbroken_E_prefix'],4); self.assertEqual(out['E_rounds_after_first_failure'],7)
        self.assertEqual(out['final_recipient_E'],3)

    def test_13_partial_state_not_full_success(self):
        report=self.reports['relay__failed_M__open']
        round4=report['rounds'][3]
        self.assertEqual(round4['recipient_stable_E'],2); self.assertFalse(round4['all_recipient_E'])
        self.assertFalse(report['outcomes']['all_rounds_E'])

    def test_14_failure_does_not_stop_following_rounds(self):
        for route in ('rna_blocked','border_cut'):
            report=self.reports['relay__restored_E__'+route]
            self.assertEqual(report['outcomes']['first_failed_E_round'],2)
            self.assertEqual(report['outcomes']['total_rounds'],12)
            self.assertEqual(report['rounds'][-1]['round'],12)

    def test_15_ordinary_founder_control_is_not_reset(self):
        old=a.arrays(self.fixture_run/'inputs/capacity__ordinary_E','onward_isolated_2')
        new=a.arrays(self.fixture_run/'relay__ordinary_E__open','r02_contact')
        self.assertTrue(np.array_equal(new['initial'][:,:3],old['final']))

    def test_16_both_isolated_holds_required(self):
        folder=self.fixture_run/self.primary
        one,two=a.arrays(folder,'r02_isolated_1'),a.arrays(folder,'r02_isolated_2')
        idx=json.loads((folder/'result.json').read_text())['ion_indices']
        self.assertTrue(a.stable(one,two,idx,'E').all())
        one['concentrations'][-1,idx['miR200_total']]=0
        self.assertFalse(a.stable(one,two,idx,'E').any())

    def test_17_held_cells_fully_disconnected(self):
        info=json.loads((self.fixture_run/self.primary/'result.json').read_text())
        for phase in info['phases']:
            setup=phase['setup']
            if not setup['isolated']: continue
            self.assertEqual(setup['algorithm'],'depol'); self.assertEqual(setup['mirna_kd'],0)
            self.assertFalse(setup['neighbor_voltage_reading'])
            self.assertFalse(a.arrays(self.fixture_run/self.primary,phase['phase'])['junction_diffusion'].any())

    def test_18_rna_block_retains_ionic_connections(self):
        folder=self.fixture_run/'relay__restored_E__rna_blocked'
        info=json.loads((folder/'result.json').read_text())
        for phase in info['phases']:
            if not phase['phase'].endswith('_contact'): continue
            data=a.arrays(folder,phase['phase'])
            self.assertEqual(phase['setup']['mirna_kd'],0)
            self.assertTrue(data['junction_diffusion'][:4].any())
            self.assertTrue(np.all(data['expression_gate_initial']==1))

    def test_19_border_cut_only_crosses_between_groups(self):
        folder=self.fixture_run/'relay__restored_E__border_cut'
        for num in range(2,13):
            data=a.arrays(folder,f'r{num:02d}_contact'); reg=data['edge_region_initial']
            self.assertEqual(int(np.sum(reg==2)),3)
            self.assertTrue(np.all(data['expression_gate_initial'][reg==2]==0))
            self.assertTrue(np.all(data['expression_gate_initial'][reg!=2]==1))

    def test_20_all_new_fine_phases_refined(self):
        self.assertTrue(self.report['all_selected_fine_agree'])
        for case in d.fixed_cases():
            if not case['fine']: continue
            info=json.loads((self.fixture_run/case['id']/'result.json').read_text())
            self.assertTrue(all(p['setup']['integrator']['time_step']==.00005 for p in info['phases']))

    def test_21_fine_input_prefix_not_refined(self):
        for case in d.fixed_cases():
            if not case['fine']: continue
            coarse=case['id'].removesuffix('__fine')
            self.assertTrue(np.array_equal(a.arrays(self.fixture_run/case['id'],'r02_contact')['initial'],
                                           a.arrays(self.fixture_run/coarse,'r02_contact')['initial']))

    def test_22_complete_manifests(self):
        self.assertEqual(len(d.LOCAL_FILES),41); self.assertEqual(len(self.summary['inputs']),76)
        bad=copy.deepcopy(self.summary); bad['inputs']={}
        self.assertFalse(all(a.integrity(self.fixture_run,bad).values()))

    def mutate(self,edit,cid=None):
        cid=cid or self.primary
        temporary=tempfile.TemporaryDirectory(prefix='p5-mutated-'); self.addCleanup(temporary.cleanup)
        run=Path(temporary.name); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
        folder=run/cid; shutil.copytree(self.fixture_run/cid,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result); d.write_json(folder/'result.json',result)
        checks=a.Checks(); a.branch(folder,next(c for c in d.fixed_cases() if c['id']==cid),checks)
        return checks.rows

    def array_edit(self,phase,key,change):
        def edit(folder,result):
            rec=next(p for p in result['phases'] if p['phase']==phase)
            path=folder/(phase+'.npz'); data=a.arrays(folder,phase)
            change(data[key]); np.savez_compressed(path,**data); rec['sha256']=d.digest(path)
        return edit

    def test_23_source_reset_caught_after_rehash(self):
        def change(x): x[0,0]+=.1
        rows=self.mutate(self.array_edit('r03_contact','initial',change))
        self.assertFalse(rows[self.primary+'/r03/actual_incoming_carriers'])

    def test_24_donor_carryover_caught_after_rehash(self):
        def edit(folder,result):
            phase='r02_isolated_1'; data=a.arrays(folder,phase)
            data['initial']=a.arrays(folder,'r02_contact')['final'][:,:3]
            path=folder/(phase+'.npz'); np.savez_compressed(path,**data)
            result['phases'][1]['sha256']=d.digest(path)
        self.assertFalse(self.mutate(edit)[self.primary+'/r02/complete_turnover'])

    def test_25_old_identity_return_detected(self):
        def edit(folder,result): result['phases'][3]['setup']['cell_ids'][0]='new:00'
        self.assertFalse(self.mutate(edit)[self.primary+'/r03_contact/ids'])

    def test_26_wrong_boundary_cut_rehashed(self):
        cid='relay__restored_E__border_cut'
        rows=self.mutate(self.array_edit('r02_contact','edge_available_initial',lambda x:x.fill(1)),cid)
        self.assertFalse(rows[cid+'/r02_contact/edge_available_initial'])

    def test_27_wrong_native_gate_rehashed(self):
        rows=self.mutate(self.array_edit('r03_contact','expression_gate_final',lambda x:x.fill(60)))
        self.assertFalse(rows[self.primary+'/r03_contact/expression_final'])

    def test_28_wrong_region_rehashed(self):
        rows=self.mutate(self.array_edit('r03_contact','edge_region_initial',lambda x:x.fill(0)))
        self.assertFalse(rows[self.primary+'/r03_contact/edge_region_initial'])

    def test_29_fresh_E_initializer_caught(self):
        def edit(folder,result):
            name='r04_contact'; data=a.arrays(folder,name); data['initial'][:,3:]=data['initial'][:,:3]
            path=folder/(name+'.npz'); np.savez_compressed(path,**data)
            next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(path)
        self.assertFalse(self.mutate(edit)[self.primary+'/r04/fresh_M'])

    def test_30_wrong_round_metadata(self):
        def edit(folder,result): result['newly_simulated_rounds']=12
        self.assertFalse(self.mutate(edit)[self.primary+'/round_count_metadata'])

    def test_31_missing_fine_rejected(self):
        summary=copy.deepcopy(self.summary)
        summary['cases']=[rec for rec in summary['cases'] if not rec['id'].endswith('__fine')]
        with tempfile.TemporaryDirectory(prefix='p5-missing-') as temp:
            run=Path(temp)
            for path in self.fixture_run.iterdir():
                if path.name!='summary.json': (run/path.name).symlink_to(path,target_is_directory=path.is_dir())
            d.write_json(run/'summary.json',summary); report=a.analyze(run)
        self.assertFalse(report['quality_gate']); self.assertFalse(report['checks']['all_twelve_finer'])

    def test_32_new_success_not_a_gate(self):
        self.assertFalse(self.report['positive_new_renewal_required'])
        self.assertFalse(self.reports['relay__ordinary_E__open']['outcomes']['all_rounds_E'])
        self.assertTrue(self.report['quality_gate'])

    def test_33_budget_before_launch(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(d.fixed_cases()[0],self.config,self.fixture_run,time.monotonic()-1,{})
        self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_34_timeout_no_retry(self):
        with tempfile.TemporaryDirectory(prefix='p5-timeout-') as temp,patch.object(r.subprocess,'run',
            side_effect=subprocess.TimeoutExpired('fixture',1)) as proc,redirect_stdout(io.StringIO()):
            result=r.run_worker(d.fixed_cases()[0],self.config,Path(temp),time.monotonic()+10,{})
        self.assertEqual(result['status'],'timeout'); self.assertEqual(proc.call_count,1)

    def stage_fixture(self,gate_pass=True,predecessor_pass=True):
        with tempfile.TemporaryDirectory(prefix='p5-stages-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            def fake_freeze(run): (run/'frozen').mkdir(); return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                summary=json.loads((run/'summary.json').read_text())
                self.assertTrue(summary['predecessor_gate']); self.assertTrue((run/'frozen').exists())
                if case['kind']=='relay': self.assertTrue(summary['gate']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            config_path=Path(__file__).resolve().parents[1]/'configs/paper_relay_v1.json'
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch.object(r,'predecessor_gate',return_value=predecessor_pass),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':gate_pass}), \
                 patch.object(r,'run_worker',side_effect=fake_worker),redirect_stdout(io.StringIO()):
                if not predecessor_pass:
                    with self.assertRaisesRegex(RuntimeError,'P4 re-audit fails'): r.run(config_path)
                    return 1,called
                return r.run(config_path),called

    def test_35_bad_predecessor_prevents_integration(self):
        code,calls=self.stage_fixture(predecessor_pass=False); self.assertEqual(code,1); self.assertEqual(calls,[])

    def test_36_bad_replay_prevents_all_relays(self):
        code,calls=self.stage_fixture(gate_pass=False); self.assertEqual(code,1); self.assertEqual(len(calls),4)

    def test_37_full_panel_only_after_gates(self):
        code,calls=self.stage_fixture(); self.assertEqual(code,0); self.assertEqual(set(calls),{c['id'] for c in d.fixed_cases()})

    def test_38_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory(prefix='p5-lock-') as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-relay.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p5-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-relay-test'; job.mkdir(parents=True)
            run=root/'runs/paper-relay-test'; run.mkdir(); commands=[]
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={'/tmp/no-such-p5-input':'bad'} if bad_input else {}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time(),planned_cases=28))
            def fake_child(command,logfile,timeout,update):
                commands.append((command,logfile.name,timeout))
                if logfile.name=='runner.log':
                    if runner_rc: return runner_rc
                    logfile.write_text(f'Run artifacts: {run}\n')
                    d.write_json(run/'summary.json',dict(cases=[dict(execution_pass=True)]*28,
                        predecessor_gate=True,gate=dict(quality_gate=True),stage='finished',
                        registered_cases=[dict(id='relay_fixture',kind='relay')]))
                    (run/'relay_fixture').mkdir()
                    d.write_json(run/'relay_fixture/progress.json',[dict(phase=f'r{n:02d}_isolated_2') for n in range(2,13)])
                else:
                    d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,
                        independent_check_count=123,gate=dict(quality_gate=True),all_selected_fine_agree=True))
                update(12345); return 0
            read_fd,write_fd=os.pipe(); os.close(write_fd)
            with patch.object(detached,'ROOT',root),patch.object(detached,'run_child',side_effect=fake_child),redirect_stdout(io.StringIO()):
                code=detached.supervise(job,read_fd)
            return code,json.loads((job/'status.json').read_text()),commands

    def test_39_supervisor_success_caps_and_round_progress(self):
        code,state,commands=self.supervisor_fixture()
        self.assertEqual(code,0); self.assertEqual(state['phase'],'complete')
        self.assertEqual(state['completed_cases'],28); self.assertEqual([c[2] for c in commands],[29100,1800])
        self.assertEqual(state['completed_continuation_rounds'],11)
        self.assertIn('no rewriting',state['next_action'])

    def test_40_supervisor_runner_failure_no_retry(self):
        code,state,commands=self.supervisor_fixture(runner_rc=124)
        self.assertEqual(code,1); self.assertEqual(len(commands),1)

    def test_41_supervisor_audit_failure(self):
        code,state,commands=self.supervisor_fixture(audit_quality=False)
        self.assertEqual(code,1); self.assertEqual(state['phase'],'failed')

    def test_42_supervisor_changed_input(self):
        code,state,commands=self.supervisor_fixture(bad_input=True)
        self.assertEqual(code,1); self.assertEqual(commands,[])

    def test_43_stale_heartbeat(self):
        with tempfile.TemporaryDirectory(prefix='p5-heartbeat-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='relay_panel',heartbeat_epoch=0))
            self.assertTrue(detached.status(job)['heartbeat_stale'])
            d.write_json(job/'status.json',dict(phase='complete',heartbeat_epoch=0))
            self.assertFalse(detached.status(job)['heartbeat_stale'])

    def test_44_no_midway_rewriting_or_automatic_followon(self):
        self.assertFalse(self.config['midway_rewriting']); self.assertFalse(self.config['stress_panel'])
        self.assertFalse(self.report['automatic_follow_on']); self.assertFalse(self.report['autonomous_heredity_demonstrated'])

    def test_45_frozen_ordinary_M_is_not_acquired_M(self):
        report=self.reports['relay__ordinary_M__open']
        self.assertEqual(report['rounds'][0]['recipient_start_labels'],'MMM')
        self.assertFalse(report['outcomes']['all_rounds_E'])
        self.assertEqual(report['outcomes']['first_failed_E_round'],1)


if __name__=='__main__': unittest.main()
