"""P6 software fixtures use native factories/gates but NEVER native integration."""
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
import paper_rewrite_design as d
import run_paper_rewrite as r
import analyze_paper_rewrite as a
import run_paper_rewrite_detached as detached
import paper_relay_design as p5d
import run_paper_relay as p5r
import paper_topology_design as p4d
import run_paper_topology as p4r
import paper_sheet_design as p3d
from test_paper_topology import fixture_case as p4_fixture
from test_paper_sheet import fixture_case as p3_fixture


def fixture_case(run,case,config,historical=False):
    folder=run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,inputs=str(run/'inputs')))
    exp=r.TopologyExperiment(folder,dict(id=case['id'],fine=case['fine']))
    names=a.p5.phase_names(case) if historical else a.phase_names(case)
    def fake_sim(horizon):
        name=names[len(exp.records)]; start=exp.sim.cc_cells.copy()
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(exp.sim.cc_cells,i)
        if name.endswith('_contact'):
            if historical or case['kind']=='replay': mark(range(6),'E')
            elif name=='writing_contact':
                if case['condition'] in ('M_open','M_relay_rna','M_relay_cut'):
                    mark(range(6),'M')
                    if case['ancestry']=='restored_E' and case['algorithm']=='hypol' and case['condition']=='M_open':
                        mark([2],'E')  # deliberately partial rewrite, not a native prediction
            elif case.get('condition') not in ('M_relay_rna','M_relay_cut'):
                # A synthetic partial carrier group may eventually write all three;
                # that must NOT retroactively count as complete original rewriting.
                mark(range(6),'M' if np.any(a.labels(start[:,:3],exp.indices)=='M') else 'E')
                if case['kind']=='rewrite' and case['ancestry']=='ordinary_E' and case['algorithm']=='hypol' and case['condition']=='M_open':
                    if name=='r09_contact': mark(range(6),'E')
                    if name=='r10_contact': mark(range(6),'M')
        number=int(name[1:3]) if name.startswith('r') else 0
        # Unequal cell/round tags distinguish donor recycling and stale snapshots.
        exp.sim.cc_cells[exp.indices['Na']]+=.001+.0001*number+.00001*np.arange(len(exp.ids))
        last=exp.sim.cc_cells.copy(); last[exp.indices['Na']]-=.0005
        return np.array([0.,horizon*.8,float(horizon)]),np.array([start,last,last])
    with patch.object(exp.sim,'sim',side_effect=fake_sim):
        if historical: p5r.trajectory(exp,case,run/'inputs')
        else: r.trajectory(exp,case,run/'inputs')
    if historical:
        result=dict(case=case,ion_indices=exp.indices,phases=exp.records,execution_pass=True,
            parameter_retuning=False,outcome_dependent_selection=False,cell_division_simulated=False,
            artificial_target_schedule=False,external_handover_schedule=True,source_external_regional_intervention=True,
            historical_rounds=1,newly_simulated_rounds=11,total_rounds=12,midway_rewriting=False,stress_panel=False)
    else: result=r.result_record(exp,case)
    d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result,
                result_sha256=d.digest(folder/'result.json'))


class TestPaperRewrite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p6-software-fixture-'); temp=Path(cls.temp.name)
        p3source=temp/'p3'; p3source.mkdir(); p4source=temp/'p4'; p4source.mkdir()
        p5source=temp/'p5'; p5source.mkdir(); cls.fixture_run=temp/'run'; cls.fixture_run.mkdir()
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
            with patch.object(p5d,'PREDECESSOR',p4source): p5r.freeze(p5source)
            selected=[c for c in p5d.fixed_cases() if c['id'] in ('relay__ordinary_E__open','relay__restored_E__open')]
            history=[fixture_case(p5source,c,p5d.FIXED,True) for c in selected]
            d.write_json(p5source/'summary.json',dict(cases=history,synthetic_software_fixture=True))
            d.write_json(p5source/'gate.json',dict(quality_gate=True,synthetic_software_fixture=True))
            d.write_json(p5source/'independent_audit.json',dict(quality_gate=True,
                independent_check_count=42065,native_integrations=804,synthetic_software_fixture=True))
        cls.input_patcher=patch.object(d,'PREDECESSOR',p5source); cls.input_patcher.start()
        cls.config=json.loads((d.ROOT/'configs/paper_rewrite_v1.json').read_text())
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,gate=None)
        with redirect_stdout(io.StringIO()):
            for c in d.fixed_cases():
                cls.summary['cases'].append(fixture_case(cls.fixture_run,c,cls.config))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                if len(cls.summary['cases'])==2:
                    gate=a.gate_audit(cls.fixture_run); d.write_json(cls.fixture_run/'gate.json',gate)
                    cls.summary.update(gate=gate,gate_sha256=d.digest(cls.fixture_run/'gate.json'))
        cls.summary['all_execution_valid']=True; d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.report=a.analyze(cls.fixture_run); cls.reports={b['case']['id']:b for b in cls.report['branches']}
        cls.primary='rewrite__restored_E__depol__M_open'

    @classmethod
    def tearDownClass(cls): cls.input_patcher.stop(); cls.temp.cleanup()

    def test_01_registered_panel(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),62)
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),30)
        self.assertEqual(sum(c['kind']=='rewrite' for c in d.fixed_cases()),56)

    def test_02_fixed_config(self):
        self.assertEqual(d.validate_config(self.config),d.FIXED)
        for k,v in (('new_rounds',12),('workers',3),('relay_power',1),('return_to_E',True)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{k:v}))

    def test_03_full_fixture_audit(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        self.assertEqual([k for k,v in self.report['gate']['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['native_integrations'],1194)
        self.assertEqual(self.report['totals']['continuation_rounds_simulated'],336)

    def test_04_exact_historical_replays(self):
        rows={k:v for k,v in self.report['gate']['checks'].items() if '/replay/' in k}
        self.assertGreater(len(rows),150); self.assertTrue(all(rows.values()))

    def test_05_actual_round_six_live_input(self):
        old=a.arrays(self.fixture_run/'inputs/p5/relay__restored_E__open','r06_isolated_2')
        new=a.arrays(self.fixture_run/self.primary,'writing_contact')
        self.assertTrue(np.array_equal(new['initial'][:,:3],old['final']))
        self.assertFalse(np.array_equal(new['initial'][:,:3],old['concentrations'][-1]))

    def test_06_cue_removed_originals_retained(self):
        folder=self.fixture_run/self.primary
        before=a.arrays(folder,'writing_contact'); after=a.arrays(folder,'writing_isolated_1')
        self.assertTrue(np.array_equal(after['initial'],before['final'][:,:3]))
        self.assertFalse(np.array_equal(after['initial'],before['final'][:,3:]))
        info=json.loads((folder/'result.json').read_text())
        self.assertFalse(any(name.startswith('cue:') for p in info['phases'][1:] for name in p['setup']['cell_ids']))

    def test_07_six_new_not_twelve_new(self):
        for b in self.report['branches']:
            if b['case']['kind']!='rewrite': continue
            self.assertEqual([v['round'] for v in b['rounds']],list(range(7,13)))
            self.assertEqual(b['outcomes']['new_handover_rounds'],6)

    def test_08_opposite_state_fresh_recipients(self):
        for b in self.report['branches']:
            if b['case']['kind']=='replay': continue
            self.assertTrue(all(v['recipient_start_labels']=='EEE' for v in b['rounds']))

    def test_09_complete_positive_chain(self):
        b=self.reports[self.primary]
        self.assertTrue(b['writing']['all_carriers_M'])
        self.assertTrue(b['outcomes']['complete_rewrite_and_relay'])
        self.assertEqual(b['outcomes']['unbroken_M_handovers'],6)

    def test_10_partial_rewrite_not_promoted_by_later_success(self):
        b=self.reports['rewrite__restored_E__hypol__M_open']
        self.assertEqual(b['writing']['retained_M'],2)
        self.assertTrue(b['outcomes']['all_new_rounds_M'])
        self.assertFalse(b['outcomes']['complete_rewrite_and_relay'])

    def test_11_failed_round_then_recovery_not_hidden(self):
        b=self.reports['rewrite__ordinary_E__hypol__M_open']['outcomes']
        self.assertEqual(b['first_failed_M_round'],9); self.assertEqual(b['unbroken_M_handovers'],2)
        self.assertEqual(b['M_rounds_after_first_failure'],3); self.assertFalse(b['complete_rewrite_and_relay'])

    def test_12_write_blocks_separate_from_relay_blocks(self):
        for suffix in ('rna','cut'):
            write=self.reports['rewrite__restored_E__depol__M_write_'+suffix]
            relay=self.reports['rewrite__restored_E__depol__M_relay_'+suffix]
            self.assertFalse(write['writing']['all_carriers_M']); self.assertTrue(relay['writing']['all_carriers_M'])
            self.assertFalse(relay['outcomes']['all_new_rounds_M'])

    def test_13_sham_and_no_cue_controls(self):
        for condition in ('E_sham','no_cue'):
            b=self.reports['rewrite__restored_E__depol__'+condition]
            self.assertTrue(b['writing']['all_carriers_E']); self.assertFalse(b['outcomes']['all_new_rounds_M'])

    def test_14_ordinary_capacity_opposite_acquisition(self):
        self.assertEqual(self.reports['assay__M']['rounds'][0]['recipient_start_labels'],'EEE')
        self.assertTrue(self.reports['assay__M']['rounds'][0]['all_recipient_M'])
        self.assertTrue(self.reports['assay__E']['rounds'][0]['all_recipient_E'])

    def test_15_phase_specific_blocks(self):
        c=next(c for c in d.fixed_cases() if c['id']=='rewrite__restored_E__depol__M_write_rna')
        self.assertEqual(a.settings(c,'writing_contact')[2],0); self.assertEqual(a.settings(c,'r07_contact')[2],1.25e-14)
        c=dict(c,condition='M_relay_rna')
        self.assertEqual(a.settings(c,'writing_contact')[2],1.25e-14); self.assertEqual(a.settings(c,'r07_contact')[2],0)

    def test_16_full_turnover_live_carry(self):
        folder=self.fixture_run/self.primary; info=json.loads((folder/'result.json').read_text())
        gone=set(); incoming={f'relay:06:{i:02d}' for i in range(3)}
        previous=a.arrays(folder,'writing_isolated_2')['final']
        for number in range(7,13):
            contact,one,two=info['phases'][3+3*(number-7):6+3*(number-7)]
            ids=contact['setup']['cell_ids']; fresh=ids[3:]
            self.assertEqual(set(ids[:3]),incoming); self.assertFalse(set(ids)&gone)
            self.assertEqual(one['setup']['cell_ids'],fresh); self.assertEqual(two['setup']['cell_ids'],fresh)
            data=a.arrays(folder,contact['phase']); self.assertTrue(np.array_equal(data['initial'][:,:3],previous))
            previous=a.arrays(folder,two['phase'])['final']; gone.update(incoming); incoming=set(fresh)

    def test_17_two_stable_holds_required(self):
        folder=self.fixture_run/self.primary; idx=json.loads((folder/'result.json').read_text())['ion_indices']
        one,two=a.arrays(folder,'writing_isolated_1'),a.arrays(folder,'writing_isolated_2')
        self.assertTrue(a.stable(one,two,idx,'M').all())
        one['concentrations'][-1,idx['miR200_total']]=10000
        self.assertFalse(a.stable(one,two,idx,'M').any())

    def test_18_every_fine_phase_refined_same_prefix(self):
        self.assertTrue(self.report['all_selected_fine_agree'])
        for c in d.fixed_cases():
            if not c['fine']: continue
            folder=self.fixture_run/c['id']; info=json.loads((folder/'result.json').read_text())
            self.assertTrue(all(p['setup']['integrator']['time_step']==.00005 for p in info['phases']))
            name=a.phase_names(c)[0]
            self.assertTrue(np.array_equal(a.arrays(folder,name)['initial'],
                a.arrays(self.fixture_run/c['id'].removesuffix('__fine'),name)['initial']))

    def test_19_no_new_success_gate(self):
        self.assertFalse(self.report['positive_new_rewrite_required']); self.assertFalse(self.report['positive_new_capacity_required'])
        self.assertTrue(self.report['quality_gate'])

    def test_20_manifests_and_input_counts(self):
        self.assertEqual(len(d.LOCAL_FILES),48); self.assertEqual(len(self.summary['inputs']),147)
        bad=copy.deepcopy(self.summary); bad['inputs']={}
        self.assertFalse(all(a.integrity(self.fixture_run,bad).values()))

    def mutate(self,edit,cid=None):
        cid=cid or self.primary; temporary=tempfile.TemporaryDirectory(prefix='p6-mutated-')
        self.addCleanup(temporary.cleanup); run=Path(temporary.name)
        (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
        folder=run/cid; shutil.copytree(self.fixture_run/cid,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result); d.write_json(folder/'result.json',result)
        checks=a.Checks(); a.branch(folder,next(c for c in d.fixed_cases() if c['id']==cid),checks)
        return checks.rows

    def array_edit(self,phase,key,change):
        def edit(folder,result):
            rec=next(p for p in result['phases'] if p['phase']==phase)
            path=folder/(phase+'.npz'); data=a.arrays(folder,phase); change(data[key])
            np.savez_compressed(path,**data); rec['sha256']=d.digest(path)
        return edit

    def test_21_rehashed_stale_source_caught(self):
        rows=self.mutate(self.array_edit('writing_contact','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/writing/actual_round_six_carriers'])

    def test_22_cue_carryover_caught(self):
        def edit(folder,result):
            name='writing_isolated_1'; data=a.arrays(folder,name)
            data['initial']=a.arrays(folder,'writing_contact')['final'][:,3:]
            np.savez_compressed(folder/(name+'.npz'),**data); result['phases'][1]['sha256']=d.digest(folder/(name+'.npz'))
        self.assertFalse(self.mutate(edit)[self.primary+'/writing/cue_withdrawal'])

    def test_23_later_carrier_reset_caught(self):
        rows=self.mutate(self.array_edit('r08_contact','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/r08/actual_incoming_carriers'])

    def test_24_old_identity_return_caught(self):
        def edit(folder,result):
            next(p for p in result['phases'] if p['phase']=='r08_contact')['setup']['cell_ids'][0]='relay:06:00'
        self.assertFalse(self.mutate(edit)[self.primary+'/r08_contact/ids'])

    def test_25_wrong_fresh_stock_caught(self):
        rows=self.mutate(self.array_edit('r07_contact','initial',lambda x:x.__setitem__((5,slice(3,None)),0)))
        self.assertFalse(rows[self.primary+'/r07/fresh_recipients'])

    def test_26_wrong_cut_rehashed_caught(self):
        cid='rewrite__restored_E__depol__M_write_cut'
        rows=self.mutate(self.array_edit('writing_contact','edge_available_initial',lambda x:x.fill(1)),cid)
        self.assertFalse(rows[cid+'/writing_contact/edge_available_initial'])

    def test_27_wrong_expression_gate_caught(self):
        rows=self.mutate(self.array_edit('r07_contact','expression_gate_final',lambda x:x.fill(1)))
        self.assertFalse(rows[self.primary+'/r07_contact/expression_final'])

    def test_28_wrong_power_or_voltage_mode_caught(self):
        def edit(folder,result): result['phases'][3]['setup']['algorithm']='hypol'
        self.assertFalse(self.mutate(edit)[self.primary+'/r07_contact/strategy'])

    def test_29_cue_block_preserves_ions(self):
        folder=self.fixture_run/'rewrite__restored_E__depol__M_write_rna'
        self.assertTrue(a.arrays(folder,'writing_contact')['junction_diffusion'][:4].any())
        folder=self.fixture_run/'rewrite__restored_E__depol__M_write_cut'
        data=a.arrays(folder,'writing_contact'); region=data['edge_region_initial']
        self.assertEqual(sum(region==2),3)
        self.assertTrue(np.all(data['edge_available_initial'][region==2]==0))
        self.assertTrue(np.all(data['edge_available_initial'][region!=2]==1))

    def test_30_all_holds_isolated(self):
        info=json.loads((self.fixture_run/self.primary/'result.json').read_text())
        for p in info['phases']:
            if '_isolated_' not in p['phase']: continue
            self.assertFalse(p['setup']['neighbor_voltage_reading'])
            self.assertFalse(a.arrays(self.fixture_run/self.primary,p['phase'])['junction_diffusion'].any())

    def test_31_budget_prevents_launch(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(d.fixed_cases()[0],self.config,self.fixture_run,time.monotonic()-1,{})
        self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_32_timeout_has_no_retry(self):
        with tempfile.TemporaryDirectory(prefix='p6-timeout-') as temp,patch.object(r.subprocess,'run',
            side_effect=subprocess.TimeoutExpired('fixture',1)) as proc,redirect_stdout(io.StringIO()):
            result=r.run_worker(d.fixed_cases()[0],self.config,Path(temp),time.monotonic()+10,{})
        self.assertEqual(result['status'],'timeout'); self.assertEqual(proc.call_count,1)

    def stage_fixture(self,gate_pass=True,predecessor_pass=True):
        with tempfile.TemporaryDirectory(prefix='p6-stages-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            def fake_freeze(run): (run/'frozen').mkdir(); return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                summary=json.loads((run/'summary.json').read_text())
                self.assertTrue(summary['predecessor_gate'])
                if case['kind']!='replay': self.assertTrue(summary['gate']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            path=Path(__file__).resolve().parents[1]/'configs/paper_rewrite_v1.json'
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch.object(r,'predecessor_gate',return_value=predecessor_pass),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':gate_pass}),patch.object(r,'run_worker',side_effect=fake_worker), \
                 redirect_stdout(io.StringIO()):
                if not predecessor_pass:
                    with self.assertRaisesRegex(RuntimeError,'P5 re-audit fails'): r.run(path)
                    return 1,called
                return r.run(path),called

    def test_33_bad_predecessor_stops_before_native(self):
        code,calls=self.stage_fixture(predecessor_pass=False); self.assertEqual(code,1); self.assertEqual(calls,[])

    def test_34_bad_replay_stops_extension(self):
        code,calls=self.stage_fixture(gate_pass=False); self.assertEqual(code,1); self.assertEqual(len(calls),2)

    def test_35_full_panel_after_gate(self):
        code,calls=self.stage_fixture(); self.assertEqual(code,0); self.assertEqual(set(calls),{c['id'] for c in d.fixed_cases()})

    def test_36_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory(prefix='p6-lock-') as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-rewrite.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p6-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-rewrite-test'; job.mkdir(parents=True)
            run=root/'runs/paper-rewrite-test'; run.mkdir(); commands=[]
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={'/tmp/no-such-p6-input':'bad'} if bad_input else {}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time(),planned_cases=62))
            def fake_child(command,logfile,timeout,update):
                commands.append((command,logfile.name,timeout))
                if logfile.name=='runner.log':
                    if runner_rc: return runner_rc
                    logfile.write_text(f'Run artifacts: {run}\n')
                    d.write_json(run/'summary.json',dict(cases=[dict(execution_pass=True)]*62,predecessor_gate=True,
                        gate=dict(quality_gate=True),stage='finished',registered_cases=[dict(id='rewrite_fixture',kind='rewrite')]))
                    (run/'rewrite_fixture').mkdir()
                    d.write_json(run/'rewrite_fixture/progress.json',[dict(phase='writing_isolated_2')]+
                        [dict(phase=f'r{n:02d}_isolated_2') for n in range(7,13)])
                else:
                    d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,
                        independent_check_count=123,gate=dict(quality_gate=True),all_selected_fine_agree=True))
                update(12345); return 0
            read_fd,write_fd=os.pipe(); os.close(write_fd)
            with patch.object(detached,'ROOT',root),patch.object(detached,'run_child',side_effect=fake_child),redirect_stdout(io.StringIO()):
                code=detached.supervise(job,read_fd)
            return code,json.loads((job/'status.json').read_text()),commands

    def test_37_supervisor_counts_writing_separately(self):
        code,state,commands=self.supervisor_fixture()
        self.assertEqual(code,0); self.assertEqual(state['phase'],'complete')
        self.assertEqual(state['completed_cases'],62); self.assertEqual([c[2] for c in commands],[29100,1800])
        self.assertEqual(state['completed_continuation_rounds'],6); self.assertEqual(state['completed_writing_stages'],1)

    def test_38_supervisor_runner_failure_no_retry(self):
        code,state,commands=self.supervisor_fixture(runner_rc=124)
        self.assertEqual(code,1); self.assertEqual(len(commands),1)

    def test_39_supervisor_bad_audit(self):
        code,state,commands=self.supervisor_fixture(audit_quality=False)
        self.assertEqual(code,1); self.assertEqual(state['phase'],'failed')

    def test_40_changed_input_stops_supervisor(self):
        code,state,commands=self.supervisor_fixture(bad_input=True)
        self.assertEqual(code,1); self.assertEqual(commands,[])

    def test_41_stale_heartbeat(self):
        with tempfile.TemporaryDirectory(prefix='p6-heartbeat-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='rewrite_panel',heartbeat_epoch=0))
            self.assertTrue(detached.status(job)['heartbeat_stale'])
            d.write_json(job/'status.json',dict(phase='complete',heartbeat_epoch=0))
            self.assertFalse(detached.status(job)['heartbeat_stale'])

    def test_42_no_followon_or_autonomy_claim(self):
        self.assertFalse(self.report['return_to_E']); self.assertFalse(self.report['stress_panel'])
        self.assertFalse(self.report['automatic_follow_on']); self.assertFalse(self.report['autonomous_heredity_demonstrated'])
        self.assertFalse(self.report['same_readout_as_P5'])

    def test_43_matched_condition_mappings(self):
        self.assertEqual(len(self.report['contrasts']),4)
        self.assertTrue(all(len(c['conditions'])==7 for c in self.report['contrasts']))

    def test_44_missing_finer_panel_rejected(self):
        summary=copy.deepcopy(self.summary); summary['cases']=[r for r in summary['cases'] if not r['id'].endswith('__fine')]
        with tempfile.TemporaryDirectory(prefix='p6-missing-') as temp:
            run=Path(temp)
            for path in self.fixture_run.iterdir():
                if path.name!='summary.json': (run/path.name).symlink_to(path,target_is_directory=path.is_dir())
            d.write_json(run/'summary.json',summary); report=a.analyze(run)
        self.assertFalse(report['quality_gate']); self.assertFalse(report['checks']['all_thirty_finer'])

    def test_45_unregistered_worker_rejected_before_factory(self):
        with tempfile.TemporaryDirectory(prefix='p6-invalid-') as temp:
            path=Path(temp)/'spec.json'; d.write_json(path,dict(case={'id':'extra'},config=self.config,inputs=str(path.parent/'inputs')))
            with patch.object(r,'TopologyExperiment') as factory:
                with self.assertRaisesRegex(ValueError,'Unregistered'): r.worker(path)
            factory.assert_not_called()

    def test_46_reference_not_fit_to_synthetic_failures(self):
        ref=self.report['binary_reference']
        self.assertEqual(ref['coarse_checkpoints'],198)
        self.assertEqual(ref['matching_checkpoints'],196)
        self.assertFalse(ref['agreement_required']); self.assertTrue(self.report['quality_gate'])

    def test_47_reference_blocked_relay_does_not_copy_M(self):
        b=self.reports['rewrite__restored_E__depol__M_relay_cut']['reference_checks']
        self.assertEqual(b[0]['predicted'],'MMM')
        self.assertTrue(all(x['predicted']=='EEE' for x in b[1:]))


if __name__=='__main__': unittest.main()
