"""P4 software fixtures: real native factories and gates, synthetic integration only."""
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
import paper_topology_design as d
import run_paper_topology as r
import analyze_paper_topology as a
import run_paper_topology_detached as detached
from test_paper_sheet import fixture_case as p3_fixture_case
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
        if case['kind'] not in ('assay','capacity','blocked','cut') and len(calls)==1:
            positions=d.block(0 if case['location']=='edge' else 5,5,case['side'])
            i,b,v=case['internal'],case['boundary'],case['algorithm']
            if i==1 and (b==60 or v=='hypol'): mark(range(169),'E')
            elif i==1 and b==1: mark(positions[:1],'E')
            elif i==60 and b==60:
                if v=='hypol': mark(positions,'E'); mark([168],'M')
                else: mark(range(169),'M')
        if exp.shape in ([2,2],[2,3]) and not exp.isolated:
            mark(range(start.shape[1]),'E' if np.sum(a.labels(start[:,:3],exp.indices)=='E')==3 else 'M')
        exp.sim.cc_cells[exp.indices['Na']]+=.001
        last=exp.sim.cc_cells.copy(); last[exp.indices['Na']]-=.0005
        return np.array([0.,horizon*.8,float(horizon)]),np.array([start,last,last])
    with patch.object(exp.sim,'sim',side_effect=fake_sim): r.trajectory(exp,case,run/'inputs')
    result=dict(case=case,ion_indices=exp.indices,phases=exp.records,execution_pass=True,
        parameter_retuning=False,outcome_dependent_selection=False,cell_division_simulated=False,
        artificial_target_schedule=False,serial_relay_rounds=0,source_external_regional_intervention=True)
    d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result,
                result_sha256=d.digest(folder/'result.json'))


class TestPaperTopology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p4-software-fixture-')
        cls.source=Path(cls.temp.name)/'source'; cls.source.mkdir()
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        cls.config=json.loads((d.ROOT/'configs/paper_topology_v1.json').read_text())
        original_paths=d.input_paths()
        cls.input_patcher=patch.object(d,'input_paths',return_value={k:cls.source/k for k in original_paths})
        cls.input_patcher.start()
        for n in ('summary.json','gate.json','bank_gate.json'):
            d.write_json(cls.source/n,dict(synthetic_software_fixture=True,quality_gate=True))
        d.write_json(cls.source/'independent_audit.json',dict(quality_gate=True,
            independent_check_count=18941,native_integrations=465,synthetic_software_fixture=True))
        ids={'reference','assay__E','assay__M'}|{f'bank__{h}__edge' for h in ('depol','nbrDepol','hypol')}|{
            f'main__depol__edge__s3__{s}' for s in ('neither','voltage','expression','both')}
        ordered=sorted((c for c in p3d.fixed_cases() if c['id'] in ids),
            key=lambda c: {'reference':0,'bank':1,'main':2,'assay':3}[c['kind']])
        with redirect_stdout(io.StringIO()):
            for c in ordered: p3_fixture_case(cls.source,c,p3d.FIXED)
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,gate=None)
        with redirect_stdout(io.StringIO()):
            for c in d.fixed_cases():
                cls.summary['cases'].append(fixture_case(cls.fixture_run,c,cls.config))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                if len(cls.summary['cases'])==6:
                    gate=a.gate_audit(cls.fixture_run); d.write_json(cls.fixture_run/'gate.json',gate)
                    cls.summary.update(gate=gate,gate_sha256=d.digest(cls.fixture_run/'gate.json'))
        cls.summary['all_execution_valid']=True; d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.report=a.analyze(cls.fixture_run)
        cls.outcomes={b['case']['id']:b['outcomes'] for b in cls.report['branches']}
        cls.primary='main__depol__edge__s3__hypol__i1__b60'

    @classmethod
    def tearDownClass(cls): cls.input_patcher.stop(); cls.temp.cleanup()

    def test_01_registered_panel(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),146)
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),16)
        self.assertEqual(sum(c['kind']=='main' and not c['fine'] for c in d.fixed_cases()),96)

    def test_02_config_fixed(self):
        self.assertEqual(d.validate_config(self.config),self.config)
        for k,v in (('workers',3),('helper_power',1),('serial_relay_rounds',1),('kd',1e-14)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{k:v}))

    def test_03_complete_fixture_audit(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['native_integrations'],858)
        self.assertTrue(self.report['all_selected_fine_agree'])

    def test_04_exact_gate_replays(self):
        self.assertTrue(self.report['gate']['quality_gate'])
        replaychecks={k:v for k,v in self.report['gate']['checks'].items() if '/replay/' in k}
        self.assertGreater(len(replaychecks),500); self.assertTrue(all(replaychecks.values()))

    def test_05_all_inputs_from_edge(self):
        for c in d.fixed_cases():
            if 'bank' not in c: continue
            self.assertTrue(c['bank'].endswith('__edge'))
            _,ids=a.geometry(c,'isolated_1')
            self.assertTrue(all(int(s.split(':')[1][1:])<3 for s in ids))

    def test_06_identical_paired_states(self):
        for n in (2,3):
            e=a.arrays(self.fixture_run/f'main__depol__edge__s{n}__depol__i1__b60','restoration')
            c=a.arrays(self.fixture_run/f'main__depol__centre__s{n}__depol__i1__b60','restoration')
            self.assertTrue(np.array_equal(e['initial'][:,d.block(0,5,n)],c['initial'][:,d.block(5,5,n)]))

    def test_07_boundary_counts(self):
        for case in d.fixed_cases():
            if case['kind']!='main': continue
            shape,ids=a.geometry(case,'restoration')
            region,_,_,_=a.regional_settings(case,'restoration',shape,ids)
            n=case['side']
            self.assertEqual(int(np.sum(region==2)),(3 if case['location']=='edge' else 4)*n)
            self.assertEqual(int(np.sum(region==1)),2*n*(n-1))

    def test_08_common_fresh_helpers(self):
        E=r.reference(self.fixture_run/'inputs')[0]
        for case in d.fixed_cases():
            if case['kind'] not in ('main','helper','blocked','cut'): continue
            value=a.arrays(self.fixture_run/case['id'],'restoration')
            self.assertTrue(np.array_equal(value['initial'][:,168:169],E))

    def test_09_live_transfer_not_last_snapshot(self):
        source=a.arrays(self.fixture_run/'inputs/bank__depol__edge','acquired_isolated_2')
        value=a.arrays(self.fixture_run/'main__depol__centre__s2__depol__i1__b60','restoration')
        take=[0,1,3,4]; patchstate=value['initial'][:,d.block(5,5,2)]
        self.assertTrue(np.array_equal(patchstate,source['final'][:,take]))
        self.assertFalse(np.array_equal(patchstate,source['concentrations'][-1][:,take]))

    def test_10_reference_uses_native_snapshot(self):
        value=a.arrays(self.fixture_run/'inputs/reference','preparation'); E,_=r.reference(self.fixture_run/'inputs')
        self.assertTrue(np.array_equal(E,value['concentrations'][-1,:,168:169]))
        self.assertFalse(np.array_equal(E,value['final'][:,168:169]))

    def test_11_interventions_withdrawn(self):
        for case in d.fixed_cases():
            result=json.loads((self.fixture_run/case['id']/'result.json').read_text())
            for p in result['phases']:
                if 'isolated_' not in p['phase']: continue
                setup=p['setup']
                self.assertTrue(setup['isolated']); self.assertEqual(setup['algorithm'],'depol')
                self.assertEqual(setup['compartment_expression'],dict(internal=1,boundary=1,helper=1,boundary_cut=False))
                self.assertEqual(setup['mirna_kd'],0); self.assertFalse(setup['neighbor_voltage_reading'])

    def test_12_no_carrier_selection(self):
        cid='main__depol__edge__s3__depol__i1__b1'; folder=self.fixture_run/cid
        self.assertTrue(np.array_equal(a.arrays(folder,'onward_contact')['initial'][:,:3],
                                      a.arrays(folder,'isolated_2')['final'][:,[0,1,3]]))
        self.assertFalse(self.outcomes[cid]['fixed_carriers_stably_E'])

    def test_13_positive_negative_partial_harmful(self):
        self.assertTrue(self.outcomes[self.primary]['strict_full_patch_chain'])
        self.assertFalse(self.outcomes['main__depol__edge__s3__depol__i60__b1']['strict_full_patch_chain'])
        self.assertEqual(self.outcomes['main__depol__edge__s3__depol__i1__b1']['patch_stable_E'],1)
        self.assertEqual(self.outcomes['main__depol__edge__s3__depol__i60__b60']['helper_contact_M'],160)

    def test_14_both_holds_required(self):
        folder=self.fixture_run/self.primary
        one,two=a.arrays(folder,'isolated_1'),a.arrays(folder,'isolated_2')
        idx=json.loads((folder/'result.json').read_text())['ion_indices']
        self.assertTrue(a.stable(one,two,idx,'E').all())
        one['concentrations'][-1,idx['miR200_total']]=0
        self.assertFalse(a.stable(one,two,idx,'E').any())

    def test_15_only_rna_blocked_control(self):
        folder=self.fixture_run/'blocked__depol__edge__s3__depol__i60__b60'
        setup=json.loads((folder/'result.json').read_text())['phases'][0]['setup']
        self.assertEqual(setup['mirna_kd'],0); self.assertFalse(setup['isolated'])
        data=a.arrays(folder,'restoration')
        self.assertTrue(data['junction_diffusion'][:4].any()); self.assertTrue(np.all(data['edge_available_initial']==1))

    def test_16_boundary_cut_not_whole_patch_isolation(self):
        data=a.arrays(self.fixture_run/'cut__depol__edge__s3__depol__i60__b60','restoration')
        reg=data['edge_region_initial']; expression=data['expression_gate_initial']
        self.assertTrue(np.all(expression[reg==2]==0)); self.assertTrue(np.all(expression[reg!=2]>0))
        self.assertTrue(data['junction_diffusion'][:4].any())

    def test_17_helper_power_separate(self):
        data=a.arrays(self.fixture_run/'main__depol__edge__s3__depol__i1__b1','restoration')
        power=data['edge_power_initial']; reg=data['edge_region_initial']
        self.assertTrue(np.all(power[reg==0]==60)); self.assertTrue(np.all(power[reg!=0]==1))
        control=a.arrays(self.fixture_run/'helper__depol__edge__s3__depol__i1__b1','restoration')
        self.assertTrue(np.all(control['edge_power_initial']==1))

    def test_18_fixed_regions_despite_state_change(self):
        data=a.arrays(self.fixture_run/self.primary,'restoration')
        self.assertTrue(np.array_equal(data['edge_region_initial'],data['edge_region_final']))
        self.assertTrue(np.array_equal(data['edge_power_initial'],data['edge_power_final']))

    def test_19_finer_entire_continuation(self):
        for c in d.fixed_cases():
            if not c['fine']: continue
            info=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            self.assertTrue(all(p['setup']['integrator']['time_step']==.00005 for p in info['phases']))

    def test_20_contrast_counts(self):
        for k in ('location','internal','boundary','algorithm'):
            self.assertEqual(len(self.report['paired_contrasts'][k]),48)
        self.assertEqual(len(self.report['paired_contrasts']['helper']),12)

    def test_21_capacity_positive_and_negative(self):
        self.assertTrue(self.outcomes['capacity__ordinary_E']['three_to_three_capacity'])
        self.assertTrue(self.outcomes['capacity__restored_E']['three_to_three_capacity'])
        self.assertFalse(self.outcomes['capacity__ordinary_M']['three_to_three_capacity'])
        self.assertFalse(self.outcomes['capacity__failed_M']['three_to_three_capacity'])
        self.assertFalse(self.report['positive_capacity_required'])

    def test_22_capacity_actual_carriers(self):
        source=a.arrays(self.fixture_run/'inputs/main__depol__edge__s3__both','isolated_2')
        contact=a.arrays(self.fixture_run/'capacity__restored_E','onward_contact')
        self.assertTrue(np.array_equal(contact['initial'][:,:3],source['final'][:,[0,1,3]]))

    def test_23_capacity_no_old_carriers_after_withdrawal(self):
        info=json.loads((self.fixture_run/'capacity__restored_E/result.json').read_text())
        self.assertEqual(info['serial_relay_rounds'],0); self.assertEqual(len(info['phases']),3)
        for phase in info['phases'][1:]:
            self.assertEqual(phase['setup']['cell_ids'],['new:00','new:01','new:02'])
            self.assertFalse(a.arrays(self.fixture_run/'capacity__restored_E',phase['phase'])['junction_diffusion'].any())

    def mutate(self,edit,cid=None):
        cid=cid or self.primary
        temporary=tempfile.TemporaryDirectory(prefix='p4-mutated-'); self.addCleanup(temporary.cleanup)
        run=Path(temporary.name); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
        folder=run/cid; shutil.copytree(self.fixture_run/cid,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result)
        d.write_json(folder/'result.json',result)
        checks=a.Checks(); a.branch(folder,next(c for c in d.fixed_cases() if c['id']==cid),checks)
        return checks.rows

    def array_edit(self,key,change,phase=0):
        def edit(folder,result):
            rec=result['phases'][phase]; path=folder/(rec['phase']+'.npz')
            data=a.arrays(folder,rec['phase']); change(data[key]); np.savez_compressed(path,**data)
            rec['sha256']=d.digest(path)
        return edit

    def test_24_wrong_region_rehashed(self):
        rows=self.mutate(self.array_edit('edge_region_initial',lambda x:x.fill(0)))
        self.assertFalse(rows[self.primary+'/restoration/edge_region_initial'])

    def test_25_wrong_power_rehashed(self):
        rows=self.mutate(self.array_edit('edge_power_final',lambda x:x.fill(1)))
        self.assertFalse(rows[self.primary+'/restoration/edge_power_final'])

    def test_26_wrong_cut_rehashed(self):
        cid='cut__depol__edge__s3__depol__i60__b60'
        rows=self.mutate(self.array_edit('edge_available_initial',lambda x:x.fill(1)),cid)
        self.assertFalse(rows[cid+'/restoration/edge_available_initial'])

    def test_27_wrong_native_expression_rehashed(self):
        rows=self.mutate(self.array_edit('expression_gate_initial',lambda x:x.fill(1)))
        self.assertFalse(rows[self.primary+'/restoration/expression_initial'])

    def test_28_reset_after_withdrawal_rehashed(self):
        def change(x): x[0,0]+=.1
        rows=self.mutate(self.array_edit('initial',change,1))
        self.assertFalse(rows[self.primary+'/withdrawal_no_reset'])

    def test_29_helper_carryover_identity(self):
        def edit(folder,result): result['phases'][3]['setup']['cell_ids'][0]='helper:r00:c00'
        self.assertFalse(self.mutate(edit)[self.primary+'/onward_contact/ids'])

    def test_30_wrong_topology_rehashed(self):
        def change(x): x[0]=13
        self.assertFalse(self.mutate(self.array_edit('edge_to',change))[self.primary+'/restoration/topology'])

    def test_31_missing_fine_rejected(self):
        summary=copy.deepcopy(self.summary); summary['cases']=[r for r in summary['cases'] if not r['id'].endswith('__fine')]
        with tempfile.TemporaryDirectory(prefix='p4-missing-') as temp:
            run=Path(temp)
            for path in self.fixture_run.iterdir():
                if path.name!='summary.json': (run/path.name).symlink_to(path,target_is_directory=path.is_dir())
            d.write_json(run/'summary.json',summary); result=a.analyze(run)
        self.assertFalse(result['quality_gate']); self.assertFalse(result['checks']['all_sixteen_finer'])

    def test_32_complete_manifest(self):
        self.assertEqual(len(d.LOCAL_FILES),34); self.assertEqual(len(self.summary['inputs']),57)
        bad=copy.deepcopy(self.summary); bad['inputs']={}
        self.assertFalse(all(a.integrity(self.fixture_run,bad).values()))

    def test_33_uniform_wrapper_equals_native(self):
        with tempfile.TemporaryDirectory(prefix='p4-native-gate-') as temp,redirect_stdout(io.StringIO()):
            exp=r.TopologyExperiment(Path(temp),dict(id='gate',fine=False))
            state=a.arrays(self.fixture_run/'replay__neither','restoration')['initial']
            ids=a.geometry(d.fixed_cases()[0],'restoration')[1]
            exp.configure([13,13],ids,state,'depol',60,1.25e-14,patch=d.block(0,5,3))
            gate=exp.expression_gate; vm=exp.sim.compute_Vm(state)
            dv=vm[exp.sim.GJ_connects['from']]-vm[exp.sim.GJ_connects['to']]
            expected=type(gate).func(gate,state,vm,dv,0); actual=gate.func(state,vm,dv,0)
            self.assertTrue(np.array_equal(actual,expected)); self.assertEqual(gate.power,60)
            before=state.copy(); exp.diagnostics(state); self.assertTrue(np.array_equal(before,state))

    def test_34_bad_patch_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p4-native-bad-') as temp,redirect_stdout(io.StringIO()):
            exp=r.TopologyExperiment(Path(temp),dict(id='bad',fine=False))
            state=np.repeat(r.reference(self.fixture_run/'inputs')[0],4,axis=1)
            for members in ([0,0],[4],[-1]):
                with self.assertRaises(ValueError): exp.configure([2,2],list('abcd'),state,patch=members)

    def test_35_budget_before_launch(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(d.fixed_cases()[0],self.config,self.fixture_run,time.monotonic()-1,{})
        self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_36_timeout_no_retry(self):
        with tempfile.TemporaryDirectory(prefix='p4-timeout-') as temp,patch.object(r.subprocess,'run',
            side_effect=subprocess.TimeoutExpired('fixture',1)) as proc,redirect_stdout(io.StringIO()):
            result=r.run_worker(d.fixed_cases()[0],self.config,Path(temp),time.monotonic()+10,{})
        self.assertEqual(result['status'],'timeout'); self.assertEqual(proc.call_count,1)

    def stage_fixture(self,gate_pass=True,predecessor_pass=True):
        with tempfile.TemporaryDirectory(prefix='p4-stages-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            def fake_freeze(run): (run/'frozen').mkdir(); return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                summary=json.loads((run/'summary.json').read_text())
                self.assertTrue((run/'frozen').exists()); self.assertTrue(summary['predecessor_gate'])
                if case['kind'] not in ('replay','assay'): self.assertTrue(summary['gate']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            config_path=Path(__file__).resolve().parents[1]/'configs/paper_topology_v1.json'
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch.object(r,'predecessor_gate',return_value=predecessor_pass),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':gate_pass}), \
                 patch.object(r,'run_worker',side_effect=fake_worker),redirect_stdout(io.StringIO()):
                if not predecessor_pass:
                    with self.assertRaisesRegex(RuntimeError,'P3 re-audit fails'): r.run(config_path)
                    return 1,called
                return r.run(config_path),called

    def test_37_predecessor_failure_no_integration(self):
        code,calls=self.stage_fixture(predecessor_pass=False); self.assertEqual(code,1); self.assertEqual(calls,[])

    def test_38_gate_failure_only_six_cases(self):
        code,calls=self.stage_fixture(gate_pass=False); self.assertEqual(code,1); self.assertEqual(len(calls),6)

    def test_39_full_panel_only_after_gates(self):
        code,calls=self.stage_fixture(); self.assertEqual(code,0); self.assertEqual(set(calls),{c['id'] for c in d.fixed_cases()})

    def test_40_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory(prefix='p4-lock-') as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-topology.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p4-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-topology-test'; job.mkdir(parents=True)
            run=root/'runs/paper-topology-test'; run.mkdir(); commands=[]
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={'/tmp/no-such-p4-input':'bad'} if bad_input else {}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time(),planned_cases=146))
            def fake_child(command,logfile,timeout,update):
                commands.append((command,logfile.name,timeout))
                if logfile.name=='runner.log':
                    if runner_rc: return runner_rc
                    logfile.write_text(f'Run artifacts: {run}\n')
                    d.write_json(run/'summary.json',dict(cases=[dict(execution_pass=True)]*146,
                        predecessor_gate=True,gate=dict(quality_gate=True),stage='finished'))
                else:
                    d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,
                        independent_check_count=123,gate=dict(quality_gate=True),all_selected_fine_agree=True))
                update(12345); return 0
            read_fd,write_fd=os.pipe(); os.close(write_fd)
            with patch.object(detached,'ROOT',root),patch.object(detached,'run_child',side_effect=fake_child),redirect_stdout(io.StringIO()):
                code=detached.supervise(job,read_fd)
            return code,json.loads((job/'status.json').read_text()),commands

    def test_41_supervisor_success_and_caps(self):
        code,state,commands=self.supervisor_fixture()
        self.assertEqual(code,0); self.assertEqual(state['phase'],'complete')
        self.assertEqual(state['completed_cases'],146); self.assertEqual([c[2] for c in commands],[57900,1800])
        self.assertIn('no serial relay',state['next_action'])

    def test_42_supervisor_no_retry(self):
        code,state,commands=self.supervisor_fixture(runner_rc=124)
        self.assertEqual(code,1); self.assertEqual(len(commands),1)

    def test_43_supervisor_audit_failure(self):
        code,state,commands=self.supervisor_fixture(audit_quality=False)
        self.assertEqual(code,1); self.assertEqual(state['phase'],'failed')

    def test_44_supervisor_changed_input(self):
        code,state,commands=self.supervisor_fixture(bad_input=True)
        self.assertEqual(code,1); self.assertEqual(commands,[])

    def test_45_stale_heartbeat(self):
        with tempfile.TemporaryDirectory(prefix='p4-heartbeat-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='topology_panel',heartbeat_epoch=0))
            state=detached.status(job); self.assertTrue(state['heartbeat_stale'])
            d.write_json(job/'status.json',dict(phase='complete',heartbeat_epoch=0))
            self.assertFalse(detached.status(job)['heartbeat_stale'])


if __name__=='__main__': unittest.main()

