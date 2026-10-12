"""P2 software-only fixtures: native factories/gates, NEVER native integration."""
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

import paper_restoration_design as d
import run_paper_restoration as r
import analyze_paper_restoration as a
import run_paper_restoration_detached as detached
import paper_memory_design as p1d
from test_paper_memory import fixture_case as p1_fixture


def fixture_case(run,case,config):
    folder=run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,inputs=str(run/'inputs')))
    exp=r.RestorationExperiment(folder,dict(id=case['id'],fine=case['fine']))
    calls=[]
    def fake_sim(horizon):
        start=exp.sim.cc_cells.copy(); calls.append(horizon)
        if not exp.isolated and exp.z.GRN.miR200_free_GJ_diffusion_val>0:
            if case['kind']=='replay':
                if exp.expression_gate.power>=8 and np.any(a.labels(start,exp.indices)=='M'):
                    for i in range(start.shape[1]): exp.z.GRN.set_very_tumor(exp.sim.cc_cells,i)
            elif start.shape[1]==3 and (case['kind']=='assay' or len(calls)>3):
                setter=exp.z.GRN.set_very_healthy if np.sum(a.labels(start,exp.indices)=='E')>=2 else exp.z.GRN.set_very_tumor
                for i in range(3): setter(exp.sim.cc_cells,i)
            elif case['kind']!='assay':
                # Deliberately artificial positive, negative, partial and harmful outcomes.
                if case['strategy'] in ('voltage','both'):
                    for i in range(start.shape[1]): exp.z.GRN.set_very_healthy(exp.sim.cc_cells,i)
                elif case['strategy']=='expression':
                    exp.z.GRN.set_very_healthy(exp.sim.cc_cells,0)
                else:
                    for i in range(start.shape[1]): exp.z.GRN.set_very_tumor(exp.sim.cc_cells,i)
        exp.sim.cc_cells[exp.indices['Na']]+=.001
        last=exp.sim.cc_cells.copy(); last[exp.indices['Na']]-=.0005
        return np.array([0.,horizon*.8,float(horizon)]),np.array([start,last,last])
    with patch.object(exp.sim,'sim',side_effect=fake_sim):
        r.trajectory(exp,case,run/'inputs')
    result=dict(case=case,ion_indices=exp.indices,phases=exp.records,execution_pass=True,
        parameter_retuning=False,outcome_dependent_selection=False,cell_division_simulated=False,
        artificial_target_schedule=False)
    d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result)


class TestPaperRestoration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p2-software-fixture-')
        cls.base=Path(cls.temp.name); cls.fixture_run=cls.base/'run'; cls.fixture_run.mkdir()
        cls.pre=cls.base/'p1'; cls.pre.mkdir()
        cls.config=json.loads((d.ROOT/'configs/paper_restoration_v1.json').read_text())
        p1config=json.loads((d.ROOT/'configs/paper_memory_v1.json').read_text())
        with redirect_stdout(io.StringIO()):
            for name in d.REPLAYS:
                c=next(c for c in p1config['cases'] if c['id']==name)
                p1_fixture(cls.pre/name,c,p1config)
        for n in ('summary.json','independent_audit.json','benchmark_gate.json'):
            d.write_json(cls.pre/n,dict(software_fixture=True))
        sources={n:cls.pre/n for n in d.input_paths()}
        with patch.object(d,'input_paths',return_value=sources):
            hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.summary=dict(revision=d.REVISION,config=cls.config,cases=[],hashes_sha256=hashes,
            frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,gate=None)
        with redirect_stdout(io.StringIO()):
            for c in cls.config['cases']:
                cls.summary['cases'].append(fixture_case(cls.fixture_run,c,cls.config))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                if len(cls.summary['cases'])==6:
                    gate=a.gate_audit(cls.fixture_run); d.write_json(cls.fixture_run/'gate.json',gate)
                    cls.summary.update(gate=gate,gate_sha256=d.digest(cls.fixture_run/'gate.json'))
        cls.summary['all_execution_valid']=True
        d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.report=a.analyze(cls.fixture_run)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_01_fixed_panel(self):
        self.assertEqual(d.validate_config(self.config),self.config)
        self.assertEqual(self.config['cases'],a.expected_cases())
        self.assertEqual(len(self.config['cases']),48)
        self.assertEqual(sum(c['fine'] for c in self.config['cases']),6)

    def test_02_reject_changes(self):
        for key,val in (('workers',3),('primary','different'),('probe_kd',1e-15)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{key:val}))
        bad=copy.deepcopy(self.config); bad['cases'].pop()
        with self.assertRaises(ValueError): d.validate_config(bad)

    def test_03_full_truth_fixture(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate']); self.assertTrue(self.report['gate']['quality_gate'])
        self.assertEqual(self.report['native_integrations'],270)
        self.assertTrue(self.report['all_selected_fine_agree'])

    def test_04_positive_negative_partial_and_harmful_outcomes(self):
        by={b['case']['id']:b['outcomes'] for b in self.report['branches']}
        self.assertTrue(by['factorial__s6__k0__both']['strict_onward_restoration'])
        self.assertEqual(by['factorial__s6__k0__neither']['helper_contact_M'],19)
        self.assertEqual(by['factorial__s6__k0__expression']['carrier_labels'],'EM')
        self.assertFalse(by['factorial__s6__k0__expression']['strict_onward_restoration'])
        self.assertFalse(by['blocked__s6__k0__both']['strict_onward_restoration'])
        self.assertTrue(self.report['quality_gate'])

    def test_05_uses_actual_held_live_array_not_last_sample(self):
        folder=self.fixture_run/'factorial__s6__k0__both'
        with np.load(self.fixture_run/'inputs'/d.PRIMARY/'isolated_2.npz') as source,np.load(folder/'restoration.npz') as data:
            self.assertTrue(np.array_equal(data['initial'][:,:6],source['final'][:,:6]))
            self.assertFalse(np.array_equal(data['initial'][:,:6],source['concentrations'][-1][:,:6]))

    def test_06_withdrawal_removes_helpers_and_both_interventions(self):
        for c in self.config['cases'][6:]:
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            for rec in result['phases'][1:3]+result['phases'][4:]:
                s=rec['setup']
                self.assertTrue(s['isolated']); self.assertEqual(s['algorithm'],'depol')
                self.assertEqual(s['power'],1); self.assertEqual(s['mirna_kd'],0)
                self.assertFalse(any(i.startswith('helper:') for i in s['cell_ids']))

    def test_07_no_selection_of_successful_cells(self):
        folder=self.fixture_run/'factorial__s6__k0__expression'
        with np.load(folder/'isolated_2.npz') as held,np.load(folder/'onward_contact.npz') as contact:
            self.assertTrue(np.array_equal(contact['initial'][:,[0,2]],held['final'][:,:2]))
        result=json.loads((folder/'result.json').read_text())
        self.assertEqual(result['phases'][3]['setup']['cell_ids'],['original:06','probe:00','original:07'])

    def test_08_blocked_restoration_only_and_common_probe(self):
        folder=self.fixture_run/'blocked__s6__k0__both'
        result=json.loads((folder/'result.json').read_text())
        self.assertEqual(result['phases'][0]['setup']['mirna_kd'],0)
        with np.load(folder/'restoration.npz') as data: self.assertTrue(data['junction_diffusion'][:4].any())
        self.assertEqual(result['phases'][3]['setup']['mirna_kd'],1.25e-14)

    def test_09_helper_free_is_really_isolated(self):
        folder=self.fixture_run/'alone__s6__k0__voltage'
        result=json.loads((folder/'result.json').read_text())
        self.assertEqual(result['phases'][0]['setup']['cells'],6)
        self.assertTrue(result['phases'][0]['setup']['isolated'])
        with np.load(folder/'restoration.npz') as data: self.assertFalse(data['junction_diffusion'].any())

    def test_10_border_control_preserves_internal_rule(self):
        base=self.fixture_run/'factorial__s6__k0__neither'
        border=self.fixture_run/'border__s6__k0__neither'
        with np.load(base/'restoration.npz') as x,np.load(border/'restoration.npz') as y:
            self.assertTrue(np.array_equal(x['initial'],y['initial']))
            self.assertTrue(np.array_equal(x['expression_gate_initial'][:5],y['expression_gate_initial'][:5]))
            self.assertGreater(x['expression_gate_initial'][5],y['expression_gate_initial'][5])

    def test_11_gate_controls_do_not_require_new_positive_results(self):
        gate=self.report['gate']
        outcomes={b['case']['id']:b['outcomes'] for b in gate['branches']}
        self.assertTrue(outcomes['assay__E']['probe_stable_E'])
        self.assertTrue(outcomes['assay__M']['probe_stable_M'])
        self.assertEqual(sum(b['case']['kind']=='replay' for b in gate['branches']),4)

    def mutated_branch(self,edit,case_id='factorial__s6__k0__both'):
        temp=tempfile.TemporaryDirectory(prefix='p2-mutated-'); self.addCleanup(temp.cleanup)
        root=Path(temp.name); (root/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
        folder=root/case_id; shutil.copytree(self.fixture_run/case_id,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result)
        d.write_json(folder/'result.json',result)
        case=next(c for c in self.config['cases'] if c['id']==case_id); checks=a.Checks()
        a.branch(folder,case,checks)
        return checks.rows

    def test_12_donor_contamination_rejected(self):
        def edit(folder,result): result['phases'][3]['setup']['cell_ids'][0]='original:00'
        rows=self.mutated_branch(edit)
        self.assertFalse(rows['factorial__s6__k0__both/onward_contact/ids'])

    def test_13_concentration_reset_caught_even_when_hash_resealed(self):
        def edit(folder,result):
            path=folder/'isolated_1.npz'
            with np.load(path) as data: x=dict(data)
            x['initial'][0,0]+=.1; np.savez_compressed(path,**x)
            result['phases'][1]['sha256']=d.digest(path)
        rows=self.mutated_branch(edit)
        self.assertFalse(rows['factorial__s6__k0__both/withdrawal_no_reset'])

    def test_14_continued_treatment_caught(self):
        def edit(folder,result): result['phases'][1]['setup']['algorithm']='hypol'
        rows=self.mutated_branch(edit)
        self.assertFalse(rows['factorial__s6__k0__both/isolated_1/strategy'])

    def test_15_wrong_border_rule_caught(self):
        def edit(folder,result): result['phases'][0]['setup']['tumor_rule']['GJ_OiET']=.5
        rows=self.mutated_branch(edit,'border__s6__k0__neither')
        self.assertFalse(rows['border__s6__k0__neither/restoration/expression_constants'])

    def test_16_requires_both_holds(self):
        folder=self.fixture_run/'factorial__s6__k0__both'
        with np.load(folder/'isolated_1.npz') as x: first=dict(x)
        with np.load(folder/'isolated_2.npz') as x: second=dict(x)
        idx=json.loads((folder/'result.json').read_text())['ion_indices']
        self.assertTrue(a.stable(first,second,idx,'E').all())
        first['concentrations'][-1,idx['miR200_total']]=0
        self.assertFalse(a.stable(first,second,idx,'E').any())

    def test_17_replay_detects_modified_historical_arrays(self):
        def edit(folder,result):
            path=folder/'onward_contact.npz'
            with np.load(path) as data: x=dict(data)
            x['final'][0,0]+=.1; np.savez_compressed(path,**x)
            result['phases'][0]['sha256']=d.digest(path)
        cid='replay__'+d.PRIMARY
        rows=self.mutated_branch(edit,cid)
        self.assertFalse(rows[cid+'/replay/onward_contact/final'])

    def test_18_manifest_completeness(self):
        bad=copy.deepcopy(self.summary); bad['inputs']={}
        self.assertFalse(a.integrity(self.fixture_run,bad)['complete_manifest'])
        self.assertEqual(len(d.LOCAL_FILES),len({p.name for p in d.LOCAL_FILES}))

    def run_stage_fixture(self,gate_pass,predecessor_pass=True):
        with tempfile.TemporaryDirectory(prefix='p2-runner-fixture-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            pre=dict(quality_gate=predecessor_pass,native_integrations=372,independent_check_count=10)
            def fake_freeze(run):
                (run/'inputs').mkdir(); (run/'frozen').mkdir()
                d.write_json(run/'inputs/independent_audit.json',pre)
                return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                self.assertTrue((run/'frozen').exists())
                if case['kind'] not in ('replay','assay'):
                    self.assertTrue(json.loads((run/'summary.json').read_text())['gate']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch('analyze_paper_memory.analyze',return_value=pre),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':gate_pass}), \
                 patch.object(r,'run_worker',side_effect=fake_worker),redirect_stdout(io.StringIO()):
                if not predecessor_pass:
                    with self.assertRaisesRegex(RuntimeError,'P1 re-audit'): r.run(self.original_config_path)
                    return 1,called
                else:
                    code=r.run(self.original_config_path)
                    return code,called

    @property
    def original_config_path(self): return Path(__file__).resolve().parents[1]/'configs/paper_restoration_v1.json'

    def test_19_gate_failure_stops_all_new_cases(self):
        code,calls=self.run_stage_fixture(False)
        self.assertEqual(code,1); self.assertEqual(len(calls),6)

    def test_20_valid_gate_enables_full_registered_panel(self):
        code,calls=self.run_stage_fixture(True)
        self.assertEqual(code,0); self.assertEqual(set(calls),{c['id'] for c in self.config['cases']})

    def test_21_expired_budget_never_launches(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(self.config['cases'][6],self.config,Path('/tmp'),time.monotonic()-1,{})
            self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_22_timeout_no_retry(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(r.subprocess,'run',side_effect=subprocess.TimeoutExpired('fake',1)) as proc:
            result=r.run_worker(self.config['cases'][6],self.config,Path(temp),time.monotonic()+1,{})
            self.assertEqual(result['status'],'timeout'); self.assertFalse(result['execution_pass'])
            self.assertEqual(proc.call_count,1)

    def test_23_status_stale_and_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            job=Path(temp)
            d.write_json(job/'status.json',dict(phase='restoration_panel',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale'])
            d.write_json(job/'status.json',dict(phase='complete',heartbeat_epoch=time.time()-60))
            self.assertFalse(detached.status(job)['heartbeat_stale'])

    def test_24_reject_output_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            job=Path(temp); (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)

    def test_25_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-restoration.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervise_fixture(self,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p2-supervisor-fixture-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-restoration-test'; job.mkdir(parents=True)
            run=root/'runs/paper-restoration-test'; run.mkdir(); commands=[]
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={'/tmp/no-such-p2-input':'bad'} if bad_input else {}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time(),planned_cases=48))
            def fake_child(command,logfile,timeout,update):
                commands.append((command,logfile.name,timeout))
                if logfile.name=='runner.log':
                    if runner_rc:return runner_rc
                    logfile.write_text(f'Run artifacts: {run}\n')
                    d.write_json(run/'summary.json',dict(cases=[{'execution_pass':True}]*48,
                        predecessor_gate=True,gate={'quality_gate':True}))
                else:
                    d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,
                        independent_check_count=123,gate={'quality_gate':True},all_selected_fine_agree=True))
                update(12345); return 0
            read_fd,write_fd=os.pipe(); os.close(write_fd)
            with patch.object(detached,'ROOT',root),patch.object(detached,'run_child',side_effect=fake_child),redirect_stdout(io.StringIO()):
                code=detached.supervise(job,read_fd)
            return code,json.loads((job/'status.json').read_text()),commands

    def test_26_supervisor_valid_and_bounded(self):
        code,status,commands=self.supervise_fixture()
        self.assertEqual(code,0);self.assertEqual(status['phase'],'complete')
        self.assertEqual(status['completed_cases'],48)
        self.assertEqual([c[2] for c in commands],[29100,900])

    def test_27_supervisor_timeout_no_retry_or_audit(self):
        code,status,commands=self.supervise_fixture(runner_rc=124)
        self.assertEqual(code,1);self.assertEqual(len(commands),1)
        self.assertEqual(status['runner_exit_code'],124)

    def test_28_supervisor_audit_failure(self):
        code,status,commands=self.supervise_fixture(audit_quality=False)
        self.assertEqual(code,1);self.assertEqual(status['phase'],'failed')

    def test_29_supervisor_changed_source(self):
        code,status,commands=self.supervise_fixture(bad_input=True)
        self.assertEqual(code,1);self.assertEqual(commands,[])

    def test_30_predecessor_failure_prevents_any_integration(self):
        code,calls=self.run_stage_fixture(False,predecessor_pass=False)
        self.assertEqual(code,1);self.assertEqual(calls,[])

    def test_31_strict_label_boundaries(self):
        idx={'miR200_total':0,'Zeb_mRNA_total':1}
        self.assertEqual(a.labels(np.array([[10.,10.,10.,10.],[12.,8.,12.001,7.999]]),idx).tolist(),['X','X','M','E'])

    def test_32_missing_fine_case_cannot_pass(self):
        with tempfile.TemporaryDirectory(prefix='p2-missing-fine-') as temp:
            target=Path(temp)/'run';shutil.copytree(self.fixture_run,target)
            summary=json.loads((target/'summary.json').read_text())
            summary['cases']=[c for c in summary['cases'] if not c['id'].endswith('__fine')]
            d.write_json(target/'summary.json',summary)
            report=a.analyze(target)
            self.assertFalse(report['quality_gate']);self.assertFalse(report['all_selected_fine_agree'])

    def test_33_source_helpers_are_not_reused_in_onward(self):
        for b in self.report['branches']:
            c=b['case']
            if c['kind'] in ('replay','assay'):continue
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            for rec in result['phases'][3:]:
                self.assertFalse(any(i.startswith('helper:') for i in rec['setup']['cell_ids']))


if __name__=='__main__': unittest.main()
