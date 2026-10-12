"""P3 software fixtures: real native factories/gates, replaced integration only."""
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
import paper_sheet_design as d
import run_paper_sheet as r
import analyze_paper_sheet as a
import run_paper_sheet_detached as detached


def fixture_case(run,case,config):
    folder=run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,run=str(run)))
    if case['kind']=='benchmark':
        for name in ('result.json','endpoints.npz','trajectory-0.npz','trajectory-1.npz'):
            shutil.copyfile(run/'inputs/pilot'/name,folder/name)
        result=json.loads((folder/'result.json').read_text())
    else:
        exp=r.SheetExperiment(folder,dict(id=case['id'],fine=case['fine'])); calls=[]
        def fake_sim(horizon):
            start=exp.sim.cc_cells.copy(); calls.append(horizon)
            def mark(indices,label):
                setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
                for i in indices: setter(exp.sim.cc_cells,i)
            if case['kind']=='bank' and len(calls)==2 and not case['blocked']:
                selected=d.block(0 if case['location']=='edge' else 4,5,3)
                if case['history']=='hypol' and case['location']=='centre': selected=[]
                elif case['history']=='nbrDepol' and case['location']=='centre': selected=selected[:4]
                mark(selected,'M')
            elif case['kind'] not in ('reference','bank','assay') and len(calls)==1:
                if case['kind'] not in ('blocked','alone'):
                    positions=d.block(0 if case['location']=='edge' else 5,5,case['side'])
                    if case['strategy']=='both': mark(range(169),'E')
                    elif case['strategy']=='expression': mark(positions[:1],'E')
                    elif case['strategy']=='voltage':
                        mark(positions,'E'); mark([168],'M')
                    else: mark(range(169),'M')
            if exp.shape==[2,2] and not exp.isolated:
                mark(range(4),'E' if np.sum(a.labels(start,exp.indices)=='E')>=3 else 'M')
            exp.sim.cc_cells[exp.indices['Na']]+=.001
            last=exp.sim.cc_cells.copy(); last[exp.indices['Na']]-=.0005
            return np.array([0.,horizon*.8,float(horizon)]),np.array([start,last,last])
        with patch.object(exp.sim,'sim',side_effect=fake_sim): r.trajectory(exp,case,run)
        result=dict(case=case,ion_indices=exp.indices,phases=exp.records,execution_pass=True,
            parameter_retuning=False,outcome_dependent_selection=False,cell_division_simulated=False,
            artificial_target_schedule=False)
        d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result,
                result_sha256=d.digest(folder/'result.json'))


class TestPaperSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p3-software-fixture-'); cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        cls.config=json.loads((d.ROOT/'configs/paper_sheet_v1.json').read_text())
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,gate=None,bank_gate=None)
        with redirect_stdout(io.StringIO()):
            for c in d.fixed_cases():
                cls.summary['cases'].append(fixture_case(cls.fixture_run,c,cls.config))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                key='gate' if len(cls.summary['cases'])==4 else 'bank_gate' if len(cls.summary['cases'])==19 else None
                if key:
                    value=a.gate_audit(cls.fixture_run) if key=='gate' else a.bank_gate(cls.fixture_run)
                    d.write_json(cls.fixture_run/(key+'.json'),value)
                    cls.summary[key]=value; cls.summary[key+'_sha256']=d.digest(cls.fixture_run/(key+'.json'))
        cls.summary['all_execution_valid']=True; d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.report=a.analyze(cls.fixture_run)
        cls.outcomes={b['case']['id']:b['outcomes'] for b in cls.report['branches']}

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_01_panel(self):
        self.assertEqual(d.validate_config(self.config),self.config)
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),85)
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),9)
        self.assertEqual(sum(c['kind']=='main' and not c['fine'] for c in d.fixed_cases()),48)

    def test_02_config_fixed(self):
        for key,value in (('workers',3),('source_side',5),('acquisition_kd',1e-14),('probe_carriers',2)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{key:value}))

    def test_03_full_fixture_audit(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['native_integrations'],465)
        self.assertTrue(self.report['all_selected_fine_agree'])

    def test_04_2d_topology(self):
        fr,to=a.edges([13,13]); self.assertEqual(len(fr),312)
        degree=np.bincount(np.r_[fr,to],minlength=169)
        self.assertEqual(np.sum(degree==2),4); self.assertEqual(np.sum(degree==3),44)
        self.assertEqual(np.sum(degree==4),121)
        self.assertEqual(a.edges([2,2]).tolist(),[[0,0,1,2],[1,2,3,3]])
        self.assertEqual(a.edges([1,1]).shape,(2,0))

    def test_05_fixed_geometry_translations(self):
        for location in ('edge','centre'):
            source,sample,dest=d.origins(location)
            self.assertFalse(set(d.block(*source,4))&set(d.block(*sample,3)))
            self.assertEqual(len(d.block(*source,4)),16)
            self.assertEqual(len(d.block(*sample,3)),9)
        self.assertEqual(np.subtract(d.block(4,5,3),d.block(0,5,3)).tolist(),[52]*9)

    def test_06_true_failed_and_partial_acquisition(self):
        self.assertEqual(self.outcomes['bank__depol__edge']['acquired_M_count'],9)
        self.assertEqual(self.outcomes['bank__hypol__centre']['acquired_M_count'],0)
        self.assertEqual(self.outcomes['bank__nbrDepol__centre']['acquired_M_count'],4)
        self.assertEqual(self.outcomes['bank__depol__edge__blocked']['acquired_M_count'],0)
        self.assertTrue(self.report['bank_gate']['quality_gate'])

    def test_07_no_acquisition_never_counts_as_restoration(self):
        out=self.outcomes['main__hypol__centre__s3__both']
        self.assertTrue(out['all_patch_stably_E']); self.assertTrue(out['probe_stable_E'])
        self.assertFalse(out['patch_eligible']); self.assertFalse(out['strict_full_patch_chain'])
        self.assertFalse(out['strict_carrier_chain'])

    def test_08_partial_acquisition_kept_separate(self):
        out=self.outcomes['main__nbrDepol__centre__s3__both']
        self.assertEqual(out['patch_acquired_M'],4)
        self.assertFalse(out['strict_full_patch_chain']); self.assertTrue(out['strict_carrier_chain'])

    def test_09_positive_and_harmful_outcomes(self):
        self.assertTrue(self.outcomes['main__depol__edge__s3__both']['strict_full_patch_chain'])
        self.assertEqual(self.outcomes['main__depol__edge__s3__neither']['helper_contact_M'],160)
        self.assertFalse(self.outcomes['main__depol__edge__s3__expression']['strict_full_patch_chain'])

    def test_10_native_preparation_last_snapshot(self):
        folder=self.fixture_run/'bank__depol__edge'; pre=a.arrays(folder,'preparation'); acq=a.arrays(folder,'acquisition')
        self.assertTrue(np.array_equal(acq['initial'],pre['concentrations'][-1]))
        self.assertFalse(np.array_equal(acq['initial'],pre['final']))

    def test_11_live_state_transfer_and_square_selection(self):
        source=a.arrays(self.fixture_run/'bank__depol__edge','acquired_isolated_2')
        start=a.arrays(self.fixture_run/'main__depol__edge__s2__both','restoration')
        positions=d.block(0,5,2)
        self.assertTrue(np.array_equal(start['initial'][:,positions],source['final'][:,[0,1,3,4]]))
        self.assertFalse(np.array_equal(start['initial'][:,positions],source['concentrations'][-1,:,[0,1,3,4]].T))

    def test_12_common_helpers_across_histories(self):
        E=r.reference(self.fixture_run)[0]
        for c in d.fixed_cases()[19:]:
            if c['kind']=='alone': continue
            start=a.arrays(self.fixture_run/c['id'],'restoration')['initial']
            self.assertTrue(np.array_equal(start[:,168:169],E))

    def test_13_interventions_and_helpers_withdrawn(self):
        for c in d.fixed_cases()[19:]:
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            for p in result['phases'][1:3]+result['phases'][4:]:
                self.assertEqual(p['setup']['algorithm'],'depol'); self.assertEqual(p['setup']['power'],1)
                self.assertTrue(p['setup']['isolated']); self.assertEqual(p['setup']['mirna_kd'],0)
                self.assertFalse(any(i.startswith('helper:') for i in p['setup']['cell_ids']))

    def test_14_no_carrier_selection(self):
        folder=self.fixture_run/'main__depol__edge__s3__expression'
        held=a.arrays(folder,'isolated_2')['final']; contact=a.arrays(folder,'onward_contact')['initial']
        self.assertTrue(np.array_equal(contact[:,:3],held[:,[0,1,3]]))
        self.assertFalse(self.outcomes[folder.name]['fixed_carriers_stably_E'])

    def test_15_blocked_is_mirna_only(self):
        for cid,name in (('bank__nbrDepol__edge__blocked','acquisition'),('blocked__depol__edge__s3__both','restoration')):
            arr=a.arrays(self.fixture_run/cid,name); result=json.loads((self.fixture_run/cid/'result.json').read_text())
            setup=next(p['setup'] for p in result['phases'] if p['phase']==name)
            self.assertEqual(setup['mirna_kd'],0); self.assertFalse(setup['isolated'])
            self.assertTrue(arr['junction_diffusion'][:4].any())

    def test_16_alone_is_fully_isolated(self):
        data=a.arrays(self.fixture_run/'alone__depol__edge__s3__neither','restoration')
        self.assertEqual(data['initial'].shape,(17,9)); self.assertFalse(data['junction_diffusion'].any())

    def test_17_all_finer_trajectory_phases(self):
        for c in d.fixed_cases():
            if not c['fine']: continue
            info=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            self.assertTrue(all(p['setup']['integrator']['time_step']==.00005 for p in info['phases']))

    def test_18_both_holds_required(self):
        folder=self.fixture_run/'main__depol__edge__s3__both'
        first=a.arrays(folder,'isolated_1'); second=a.arrays(folder,'isolated_2')
        idx=json.loads((folder/'result.json').read_text())['ion_indices']
        self.assertTrue(a.stable(first,second,idx,'E').all())
        first['concentrations'][-1,idx['miR200_total']]=0
        self.assertFalse(a.stable(first,second,idx,'E').any())

    def test_19_manifest_complete(self):
        bad=copy.deepcopy(self.summary); bad['inputs']={}
        self.assertFalse(a.integrity(self.fixture_run,bad)['complete_manifest'])
        self.assertEqual(len(d.LOCAL_FILES),len({p.name for p in d.LOCAL_FILES}))

    def mutate(self,edit,cid='main__depol__edge__s3__both'):
        temporary=tempfile.TemporaryDirectory(prefix='p3-mutated-'); self.addCleanup(temporary.cleanup)
        run=Path(temporary.name)
        for path in self.fixture_run.iterdir():
            if path.is_dir() and path.name!=cid: (run/path.name).symlink_to(path,target_is_directory=True)
        folder=run/cid; shutil.copytree(self.fixture_run/cid,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result)
        d.write_json(folder/'result.json',result)
        checks=a.Checks(); a.branch(folder,next(c for c in d.fixed_cases() if c['id']==cid),checks)
        return checks.rows

    def test_20_wrong_topology_caught_after_rehash(self):
        def edit(folder,result):
            path=folder/'restoration.npz'; values=a.arrays(folder,'restoration')
            values['edge_to'][0]=13; np.savez_compressed(path,**values); result['phases'][0]['sha256']=d.digest(path)
        rows=self.mutate(edit); self.assertFalse(rows['main__depol__edge__s3__both/restoration/topology'])

    def test_21_state_reset_caught_after_rehash(self):
        def edit(folder,result):
            path=folder/'isolated_1.npz'; values=a.arrays(folder,'isolated_1')
            values['initial'][0,0]+=.1; np.savez_compressed(path,**values); result['phases'][1]['sha256']=d.digest(path)
        self.assertFalse(self.mutate(edit)['main__depol__edge__s3__both/withdrawal_no_reset'])

    def test_22_hidden_helpers_caught(self):
        def edit(folder,result): result['phases'][3]['setup']['cell_ids'][0]='helper:r00:c00'
        self.assertFalse(self.mutate(edit)['main__depol__edge__s3__both/onward_contact/ids'])

    def test_23_neighbor_rule_caught(self):
        def edit(folder,result): result['phases'][1]['setup']['neighbor_voltage_reading']=False
        self.assertFalse(self.mutate(edit,'bank__nbrDepol__edge')['bank__nbrDepol__edge/acquisition/neighbor'])

    def test_24_directional_gate_checked(self):
        def edit(folder,result):
            path=folder/'acquisition.npz'; values=a.arrays(folder,'acquisition')
            values['potassium_gate_initial']=values['potassium_gate_initial'][::-1].copy()
            np.savez_compressed(path,**values); result['phases'][1]['sha256']=d.digest(path)
        self.assertFalse(self.mutate(edit,'bank__nbrDepol__edge')['bank__nbrDepol__edge/acquisition/potassium_initial'])

    def test_25_reference_probe_gate(self):
        self.assertTrue(self.outcomes['assay__E']['probe_stable_E']); self.assertTrue(self.outcomes['assay__M']['probe_stable_M'])
        self.assertTrue(self.report['gate']['quality_gate']); self.assertFalse(self.report['bank_gate']['positive_acquisition_required'])

    def test_26_budget_stops_before_launch(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(d.fixed_cases()[0],self.config,self.fixture_run,time.monotonic()-1,{})
        self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_27_timeout_no_retry(self):
        with tempfile.TemporaryDirectory(prefix='p3-timeout-') as temp,patch.object(r.subprocess,'run',side_effect=subprocess.TimeoutExpired('fixture',1)) as proc:
            with redirect_stdout(io.StringIO()): result=r.run_worker(d.fixed_cases()[0],self.config,Path(temp),time.monotonic()+10,{})
        self.assertEqual(result['status'],'timeout'); self.assertEqual(proc.call_count,1)
        self.assertFalse(result['execution_pass'])

    def test_28_duplicate_identity_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p3-identities-') as temp,redirect_stdout(io.StringIO()):
            exp=r.SheetExperiment(Path(temp),dict(id='test',fine=False))
            with self.assertRaises(ValueError): exp.configure([2,2],['same']*4)

    def test_29_snapshot_is_not_live(self):
        pre=a.arrays(self.fixture_run/'reference','preparation'); E,M=r.reference(self.fixture_run)
        self.assertTrue(np.array_equal(E,pre['concentrations'][-1,:,168:169]))
        self.assertFalse(np.array_equal(E,pre['final'][:,168:169]))

    def test_30_detached_paths_and_status(self):
        self.assertEqual(detached.RUNNER,d.ROOT/'scripts/run_paper_sheet.py')
        self.assertEqual(detached.ANALYZER,d.ROOT/'scripts/analyze_paper_sheet.py')
        with tempfile.TemporaryDirectory(prefix='p3-status-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='complete',heartbeat_epoch=0))
            self.assertEqual(detached.status(job)['phase'],'complete')
            self.assertIsNone(detached.discover_run(job))

    def stage_fixture(self,gate_pass=True,bank_pass=True,predecessor_pass=True):
        with tempfile.TemporaryDirectory(prefix='p3-stages-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            def fake_freeze(run):
                (run/'frozen').mkdir(); return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                summary=json.loads((run/'summary.json').read_text())
                self.assertTrue((run/'frozen').exists()); self.assertTrue(summary['predecessor_gate'])
                if case['kind']=='bank': self.assertTrue(summary['gate']['quality_gate'])
                if case['kind'] in ('main','blocked','alone'): self.assertTrue(summary['bank_gate']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            config_path=Path(__file__).resolve().parents[1]/'configs/paper_sheet_v1.json'
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch.object(r,'predecessor_gate',return_value=predecessor_pass),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':gate_pass}), \
                 patch.object(a,'bank_gate',return_value={'quality_gate':bank_pass}), \
                 patch.object(r,'run_worker',side_effect=fake_worker),redirect_stdout(io.StringIO()):
                if not predecessor_pass:
                    with self.assertRaisesRegex(RuntimeError,'P2 read-only re-audit'): r.run(config_path)
                    return 1,called
                return r.run(config_path),called

    def test_31_predecessor_failure_prevents_integration(self):
        code,calls=self.stage_fixture(predecessor_pass=False)
        self.assertEqual(code,1); self.assertEqual(calls,[])

    def test_32_gate_failure_stops_banks(self):
        code,calls=self.stage_fixture(gate_pass=False)
        self.assertEqual(code,1); self.assertEqual(len(calls),4)

    def test_33_bank_data_failure_stops_restoration(self):
        code,calls=self.stage_fixture(bank_pass=False)
        self.assertEqual(code,1); self.assertEqual(len(calls),19)

    def test_34_full_panel_runs_only_after_gates(self):
        code,calls=self.stage_fixture()
        self.assertEqual(code,0); self.assertEqual(set(calls),{c['id'] for c in d.fixed_cases()})

    def test_35_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory(prefix='p3-lock-') as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-sheet.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p3-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-sheet-test'; job.mkdir(parents=True)
            run=root/'runs/paper-sheet-test'; run.mkdir(); commands=[]
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={'/tmp/no-such-p3-input':'bad'} if bad_input else {}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time(),planned_cases=85))
            def fake_child(command,logfile,timeout,update):
                commands.append((command,logfile.name,timeout))
                if logfile.name=='runner.log':
                    if runner_rc: return runner_rc
                    logfile.write_text(f'Run artifacts: {run}\n')
                    d.write_json(run/'summary.json',dict(cases=[dict(execution_pass=True)]*85,
                        predecessor_gate=True,gate=dict(quality_gate=True),bank_gate=dict(quality_gate=True),stage='finished'))
                else:
                    d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,
                        independent_check_count=123,gate=dict(quality_gate=True),all_selected_fine_agree=True))
                update(12345); return 0
            read_fd,write_fd=os.pipe(); os.close(write_fd)
            with patch.object(detached,'ROOT',root),patch.object(detached,'run_child',side_effect=fake_child),redirect_stdout(io.StringIO()):
                code=detached.supervise(job,read_fd)
            return code,json.loads((job/'status.json').read_text()),commands

    def test_36_supervisor_success_and_caps(self):
        code,state,commands=self.supervisor_fixture()
        self.assertEqual(code,0); self.assertEqual(state['phase'],'complete')
        self.assertEqual(state['completed_cases'],85); self.assertEqual([c[2] for c in commands],[57900,1800])

    def test_37_supervisor_no_retry(self):
        code,state,commands=self.supervisor_fixture(runner_rc=124)
        self.assertEqual(code,1); self.assertEqual(len(commands),1)
        self.assertEqual(state['runner_exit_code'],124)

    def test_38_supervisor_audit_failure(self):
        code,state,commands=self.supervisor_fixture(audit_quality=False)
        self.assertEqual(code,1); self.assertEqual(state['phase'],'failed')

    def test_39_supervisor_changed_input(self):
        code,state,commands=self.supervisor_fixture(bad_input=True)
        self.assertEqual(code,1); self.assertEqual(commands,[])

    def test_40_no_voltage_charge_from_total_mirna(self):
        def edit(folder,result):
            path=folder/'restoration.npz'; data=a.arrays(folder,'restoration')
            data['valences'][5]=-1; np.savez_compressed(path,**data); result['phases'][0]['sha256']=d.digest(path)
        self.assertFalse(self.mutate(edit)['main__depol__edge__s3__both/restoration/membrane_valences'])


if __name__=='__main__': unittest.main()
