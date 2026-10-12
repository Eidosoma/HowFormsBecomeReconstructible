"""P7 software fixtures: native factories/gates, never native integration."""
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
import paper_m_calibration_design as d
import run_paper_m_calibration as r
import analyze_paper_m_calibration as a
import run_paper_m_calibration_detached as detached
import paper_sheet_design as p3d
import paper_rewrite_design as p6d
from test_paper_sheet import fixture_case as p3_fixture


def fixture_case(run,case,config,historical=False):
    folder=run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,inputs=str(run/'inputs')))
    exp=r.TopologyExperiment(folder,dict(id=case['id'],fine=False)) if historical else r.factory(folder,case)
    names=a.p6.phase_names(case) if historical else a.phase_names(case)
    def fake_sim(horizon):
        name=names[len(exp.records)]; start=exp.sim.cc_cells.copy()
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(exp.sim.cc_cells,i)
        if case.get('source')=='p3':
            if name=='acquisition': mark(p3d.block(0,5,3),'M')
            exp.sim.cc_cells[exp.indices['Na']]+=.001
        else:
            if name=='onward_contact': mark(range(6),'E')
            if case['kind']=='capacity':
                _,nd,nr=d.LAYOUTS[case['layout']]
                if name=='contact' and case['condition']=='M_open':
                    if case['anchor']=='low':
                        mark(range(nd+nr),'M')
                        if case['layout']=='three_to_three' and case['algorithm']=='hypol': mark([nd+nr-1],'E')
                    elif case['layout']=='six_to_three': mark(range(nd+nr),'M')
                    else: mark(range(nd+nr),'E')
                if name=='isolated_1' and case['condition']=='M_open' and case['anchor']=='high': mark(range(nr),'E')
            exp.sim.cc_cells[exp.indices['Na']]+=.001+.00001*np.arange(len(exp.ids))
        last=exp.sim.cc_cells.copy(); last[exp.indices['Na']]-=.0005
        return np.array([0.,horizon*.8,float(horizon)]),np.array([start,last,last])
    with patch.object(exp.sim,'sim',side_effect=fake_sim):
        if historical: r.p6.trajectory(exp,case,run/'inputs')
        else: r.trajectory(exp,case,run/'inputs')
    result=r.p6.result_record(exp,case) if historical else r.result_record(exp,case)
    d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))


class TestPaperMCalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p7-software-fixture-'); temp=Path(cls.temp.name)
        p3source=temp/'p3'; p3source.mkdir(); p6source=temp/'p6'; p6source.mkdir()
        cls.fixture_run=temp/'run'; cls.fixture_run.mkdir()
        for name in ('result.json','endpoints.npz'):
            target=p3source/'inputs/pilot'/name; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(d.P3_SOURCE/'inputs/pilot'/name,target)
        with redirect_stdout(io.StringIO()):
            ref=next(c for c in p3d.fixed_cases() if c['id']=='reference')
            history3=[p3_fixture(p3source,c,p3d.FIXED) for c in (ref,d.P3_CASE)]
            target=p6source/'inputs/p5/inputs/p4_inputs/reference/preparation.npz'; target.parent.mkdir(parents=True)
            shutil.copyfile(p3source/'reference/preparation.npz',target)
            history6=[fixture_case(p6source,d.P6_CASE,p6d.FIXED,True)]
        for folder,history,n,calls in ((p3source,history3,18941,465),(p6source,history6,56484,1194)):
            d.write_json(folder/'summary.json',dict(cases=history,synthetic_software_fixture=True))
            d.write_json(folder/'independent_audit.json',dict(quality_gate=True,independent_check_count=n,
                native_integrations=calls,synthetic_software_fixture=True))
            d.write_json(folder/'gate.json',dict(quality_gate=True,synthetic_software_fixture=True))
        d.write_json(p3source/'bank_gate.json',dict(quality_gate=True,synthetic_software_fixture=True))
        cls.patch3=patch.object(d,'P3_SOURCE',p3source); cls.patch6=patch.object(d,'PREDECESSOR',p6source)
        cls.patch3.start(); cls.patch6.start()
        cls.config=json.loads((d.ROOT/'configs/paper_m_calibration_v1.json').read_text())
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
        cls.primary='capacity__three_to_three__depol__low__M_open'

    @classmethod
    def tearDownClass(cls): cls.patch3.stop(); cls.patch6.stop(); cls.temp.cleanup()

    def test_01_panel(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),98)
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),48)
        self.assertEqual(sum(len(a.phase_names(c)) for c in d.fixed_cases()),295)

    def test_02_fixed_config(self):
        self.assertEqual(d.validate_config(self.config),d.FIXED)
        for key,value in (('workers',3),('contact_horizon',40000),('serial_relay',True),('contact_power',100)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{key:value}))

    def test_03_full_fixture_audit(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        self.assertEqual([k for k,v in self.report['gate']['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['native_integrations'],295)

    def test_04_two_opposite_historical_gates(self):
        checks=self.report['gate']['checks']
        self.assertTrue(checks['p3/known_positive']); self.assertTrue(checks['p6/known_negative'])
        self.assertEqual(sum('/replay/' in k for k in checks),193)

    def test_05_replay_factory_schema_preserved(self):
        p3=a.arrays(self.fixture_run/'replay__p3_M_acquisition','acquisition')
        p6=a.arrays(self.fixture_run/'replay__p6_M_failure','onward_contact')
        self.assertNotIn('edge_region_initial',p3); self.assertIn('edge_region_initial',p6)

    def test_06_live_recipients_not_donors_or_snapshot(self):
        folder=self.fixture_run/self.primary; contact=a.arrays(folder,'contact'); one=a.arrays(folder,'isolated_1')
        self.assertTrue(np.array_equal(one['initial'],contact['final'][:,3:]))
        self.assertFalse(np.array_equal(one['initial'],contact['final'][:,:3]))
        self.assertFalse(np.array_equal(one['initial'],contact['concentrations'][-1,:,3:]))

    def test_07_every_recipient_starts_E(self):
        for b in self.report['branches']:
            if b['case']['kind']=='capacity':
                self.assertEqual(b['outcomes']['recipient_start_labels'],'E'*b['outcomes']['recipients'])

    def test_08_actual_full_stock_initialization(self):
        stock=a.arrays(self.fixture_run/'inputs/p3/reference','preparation')['concentrations'][-1]
        for c in d.fixed_cases()[2:]:
            _,nd,nr=a.layout(c); initial=a.arrays(self.fixture_run/c['id'],'contact')['initial']
            self.assertTrue(np.array_equal(initial[:,nd:],np.repeat(stock[:,168:169],nr,axis=1)))
            source=stock[:,168:169] if c['condition']=='E_sham' else stock[:,1:2]
            self.assertTrue(np.array_equal(initial[:,:nd],np.repeat(source,nd,axis=1)))

    def test_09_partial_not_complete(self):
        out=self.reports['capacity__three_to_three__hypol__low__M_open']['outcomes']
        self.assertTrue(out['partial_M']); self.assertEqual(out['acquired_M'],2); self.assertFalse(out['all_recipient_M'])

    def test_10_transient_not_retained(self):
        out=self.reports['capacity__six_to_three__depol__high__M_open']['outcomes']
        self.assertEqual(out['contact_M_not_retained'],3); self.assertEqual(out['retained_M'],0)

    def test_11_donor_conversion_reported(self):
        out=self.reports['capacity__three_to_three__depol__high__M_open']['outcomes']
        self.assertEqual(out['donor_start_labels'],'MMM'); self.assertEqual(out['donor_contact_labels'],'EEE')

    def test_12_matched_controls_required(self):
        conditions=copy.deepcopy(self.report['contrasts'][0]['conditions']); self.assertTrue(a.qualify(conditions))
        for c in ('E_sham','M_rna','M_cut'):
            bad=copy.deepcopy(conditions); bad[c]['all_recipient_E']=False; self.assertFalse(a.qualify(bad))
        del conditions['M_cut']; self.assertFalse(a.qualify(conditions))

    def test_13_candidate_priority_and_size(self):
        self.assertEqual(self.report['candidates'][0],dict(layout='three_to_three',algorithm='depol',anchor='low',same_size=True))
        self.assertEqual(self.report['totals']['same_size_candidates'],1)
        self.assertEqual(self.report['totals']['unequal_size_candidates'],4)

    def test_14_no_renewal_or_followon_claim(self):
        for key in ('serial_renewal_demonstrated','automatic_follow_on','midway_rewriting','stress_panel',
                    'autonomous_heredity_demonstrated','clinical_therapy','full_paper_replication'):
            self.assertFalse(self.report[key])

    def test_15_both_holds_required(self):
        folder=self.fixture_run/self.primary; idx=json.loads((folder/'result.json').read_text())['ion_indices']
        one,two=a.arrays(folder,'isolated_1'),a.arrays(folder,'isolated_2')
        self.assertTrue(a.stable(one,two,idx,'M').all())
        one['concentrations'][-1,idx['miR200_total']]=10000
        self.assertFalse(a.stable(one,two,idx,'M').any())

    def test_16_all_fine_phases_and_starts(self):
        self.assertTrue(self.report['all_selected_fine_agree']); self.assertEqual(len(self.report['fine_comparisons']),48)
        for c in d.fixed_cases()[50:]:
            folder=self.fixture_run/c['id']; rec=json.loads((folder/'result.json').read_text())
            self.assertTrue(all(p['setup']['integrator']['time_step']==.00005 for p in rec['phases']))
            self.assertTrue(np.array_equal(a.arrays(folder,'contact')['initial'],
                a.arrays(self.fixture_run/c['id'].removesuffix('__fine'),'contact')['initial']))

    def test_17_zero_Kd_duplicates_are_not_a_dose_gradient(self):
        self.assertTrue(self.report['zero_kd_anchor_controls_physically_duplicate'])
        for layout in d.LAYOUTS:
            low=self.fixture_run/f'capacity__{layout}__depol__low__M_rna'
            high=self.fixture_run/f'capacity__{layout}__depol__high__M_rna'
            for name in ('contact','isolated_1','isolated_2'):
                x,y=a.arrays(low,name),a.arrays(high,name)
                self.assertTrue(all(np.array_equal(v,y[k]) for k,v in x.items()))

    def test_18_RNA_block_preserves_ions(self):
        c=next(c for c in d.fixed_cases() if c.get('condition')=='M_rna')
        self.assertEqual(a.settings(c,'contact')[2],0)
        self.assertTrue(a.arrays(self.fixture_run/c['id'],'contact')['junction_diffusion'][:4].any())

    def test_19_boundary_cut_all_crossing_edges_only(self):
        for layout,n in (('three_to_three',3),('three_to_one',2),('six_to_three',3)):
            folder=self.fixture_run/f'capacity__{layout}__depol__low__M_cut'; data=a.arrays(folder,'contact')
            region=data['edge_region_initial']; self.assertEqual(sum(region==2),n)
            self.assertTrue(np.all(data['edge_available_initial'][region==2]==0))
            self.assertTrue(np.all(data['edge_available_initial'][region!=2]==1))

    def test_20_all_holds_fully_isolated(self):
        for c in d.fixed_cases()[2:]:
            info=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            for p in info['phases'][1:]:
                self.assertFalse(p['setup']['neighbor_voltage_reading'])
                self.assertFalse(a.arrays(self.fixture_run/c['id'],p['phase'])['junction_diffusion'].any())
                self.assertTrue(all(x.startswith('recipient:') for x in p['setup']['cell_ids']))

    def test_21_manifest_and_inputs(self):
        self.assertEqual(len(d.LOCAL_FILES),55); self.assertEqual(len(self.summary['inputs']),21)
        self.assertEqual(len(self.summary['hashes_sha256']),91)
        bad=copy.deepcopy(self.summary); bad['inputs']={}; self.assertFalse(all(a.integrity(self.fixture_run,bad).values()))

    def mutate(self,edit,cid=None):
        cid=cid or self.primary; temporary=tempfile.TemporaryDirectory(prefix='p7-mutated-')
        self.addCleanup(temporary.cleanup); run=Path(temporary.name)
        (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
        folder=run/cid; shutil.copytree(self.fixture_run/cid,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result); d.write_json(folder/'result.json',result)
        checks=a.Checks(); a.branch(folder,next(c for c in d.fixed_cases() if c['id']==cid),checks)
        return checks.rows

    def array_edit(self,phase,key,change):
        def edit(folder,result):
            rec=next(p for p in result['phases'] if p['phase']==phase); data=a.arrays(folder,phase); change(data[key])
            np.savez_compressed(folder/(phase+'.npz'),**data); rec['sha256']=d.digest(folder/(phase+'.npz'))
        return edit

    def test_22_rehashed_wrong_recipient_stock(self):
        rows=self.mutate(self.array_edit('contact','initial',lambda x:x.__setitem__((5,3),0)))
        self.assertFalse(rows[self.primary+'/fresh_recipients'])

    def test_23_rehashed_donor_recycling(self):
        def edit(folder,result):
            data=a.arrays(folder,'isolated_1'); data['initial']=a.arrays(folder,'contact')['final'][:,:3]
            np.savez_compressed(folder/'isolated_1.npz',**data); result['phases'][1]['sha256']=d.digest(folder/'isolated_1.npz')
        self.assertFalse(self.mutate(edit)[self.primary+'/donors_removed_actual_recipients'])

    def test_24_wrong_identity(self):
        def edit(folder,result): result['phases'][1]['setup']['cell_ids'][0]='donor:00'
        self.assertFalse(self.mutate(edit)[self.primary+'/isolated_1/ids'])

    def test_25_rehashed_wrong_cut(self):
        cid=self.primary.replace('M_open','M_cut')
        rows=self.mutate(self.array_edit('contact','edge_available_initial',lambda x:x.fill(1)),cid)
        self.assertFalse(rows[cid+'/contact/edge_available_initial'])

    def test_26_wrong_expression_gate(self):
        rows=self.mutate(self.array_edit('contact','expression_gate_final',lambda x:x.fill(1)))
        self.assertFalse(rows[self.primary+'/contact/expression_final'])

    def test_27_wrong_mode(self):
        def edit(folder,result): result['phases'][0]['setup']['algorithm']='hypol'
        self.assertFalse(self.mutate(edit)[self.primary+'/contact/strategy'])

    def test_28_rehashed_hold_reset(self):
        rows=self.mutate(self.array_edit('isolated_2','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/hold_live_continuity'])

    def test_29_budget_blocks_launch(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(d.fixed_cases()[0],self.config,self.fixture_run,time.monotonic()-1,{})
        self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_30_timeout_no_retry(self):
        with tempfile.TemporaryDirectory(prefix='p7-timeout-') as temp,patch.object(r.subprocess,'run',
            side_effect=subprocess.TimeoutExpired('fixture',1)) as proc,redirect_stdout(io.StringIO()):
            result=r.run_worker(d.fixed_cases()[0],self.config,Path(temp),time.monotonic()+10,{})
        self.assertEqual(result['status'],'timeout'); self.assertEqual(proc.call_count,1)

    def stage_fixture(self,gate_pass=True,predecessor_pass=True):
        with tempfile.TemporaryDirectory(prefix='p7-stages-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            def fake_freeze(run): (run/'frozen').mkdir(); return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                summary=json.loads((run/'summary.json').read_text()); self.assertTrue(summary['predecessor_gate'])
                if case['kind']!='replay': self.assertTrue(summary['gate']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            path=Path(__file__).resolve().parents[1]/'configs/paper_m_calibration_v1.json'
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch.object(r,'predecessor_gate',return_value=predecessor_pass),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':gate_pass}),patch.object(r,'run_worker',side_effect=fake_worker), \
                 redirect_stdout(io.StringIO()):
                if not predecessor_pass:
                    with self.assertRaisesRegex(RuntimeError,'Historical re-audit failed'): r.run(path)
                    return 1,called
                return r.run(path),called

    def test_31_predecessor_failure_stops_native(self):
        code,calls=self.stage_fixture(predecessor_pass=False); self.assertEqual(code,1); self.assertEqual(calls,[])

    def test_32_replay_failure_stops_new_panel(self):
        code,calls=self.stage_fixture(gate_pass=False); self.assertEqual(code,1); self.assertEqual(len(calls),2)

    def test_33_full_panel_without_positive_filter(self):
        code,calls=self.stage_fixture(); self.assertEqual(code,0); self.assertEqual(len(calls),98)
        self.assertFalse(self.report['positive_new_capacity_required'])

    def test_34_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory(prefix='p7-lock-') as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-m-calibration.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p7-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-m-calibration-test'; job.mkdir(parents=True)
            run=root/'runs/paper-m-calibration-test'; run.mkdir(); commands=[]
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={'/tmp/no-such-p7-input':'bad'} if bad_input else {}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time(),planned_cases=98))
            def fake_child(command,logfile,timeout,update):
                commands.append((command,logfile.name,timeout))
                if logfile.name=='runner.log':
                    if runner_rc: return runner_rc
                    logfile.write_text(f'Run artifacts: {run}\n')
                    cases=[dict(execution_pass=True,result=dict(case=dict(kind='capacity')))]*96
                    cases += [dict(execution_pass=True,result=dict(case=dict(kind='replay')))]*2
                    d.write_json(run/'summary.json',dict(cases=cases,predecessor_gate=True,gate=dict(quality_gate=True),stage='finished'))
                else: d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,
                    independent_check_count=123,gate=dict(quality_gate=True),all_selected_fine_agree=True))
                update(12345); return 0
            read_fd,write_fd=os.pipe(); os.close(write_fd)
            with patch.object(detached,'ROOT',root),patch.object(detached,'run_child',side_effect=fake_child),redirect_stdout(io.StringIO()):
                code=detached.supervise(job,read_fd)
            return code,json.loads((job/'status.json').read_text()),commands

    def test_35_supervisor_progress_and_caps(self):
        code,state,commands=self.supervisor_fixture(); self.assertEqual(code,0)
        self.assertEqual(state['phase'],'complete'); self.assertEqual(state['completed_cases'],98)
        self.assertEqual(state['completed_calibration_cases'],96); self.assertEqual([c[2] for c in commands],[29100,1800])

    def test_36_supervisor_runner_failure(self):
        code,state,commands=self.supervisor_fixture(runner_rc=124); self.assertEqual(code,1); self.assertEqual(len(commands),1)

    def test_37_supervisor_audit_failure(self):
        code,state,commands=self.supervisor_fixture(audit_quality=False); self.assertEqual(code,1); self.assertEqual(state['phase'],'failed')

    def test_38_supervisor_changed_input(self):
        code,state,commands=self.supervisor_fixture(bad_input=True); self.assertEqual(code,1); self.assertEqual(commands,[])

    def test_39_stale_heartbeat(self):
        with tempfile.TemporaryDirectory(prefix='p7-heartbeat-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='coarse_calibration',heartbeat_epoch=0))
            self.assertTrue(detached.status(job)['heartbeat_stale'])
            d.write_json(job/'status.json',dict(phase='complete',heartbeat_epoch=0)); self.assertFalse(detached.status(job)['heartbeat_stale'])

    def test_40_unregistered_worker_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p7-invalid-') as temp:
            path=Path(temp)/'spec.json'; d.write_json(path,dict(case={'id':'extra'},config=self.config,inputs=str(path.parent/'inputs')))
            with patch.object(r,'factory') as factory:
                with self.assertRaisesRegex(ValueError,'Unregistered'): r.worker(path)
            factory.assert_not_called()

    def test_41_all_matched_conditions_present(self):
        self.assertEqual(len(self.report['contrasts']),12)
        self.assertTrue(all(len(c['conditions'])==len(c['fine_conditions'])==4 for c in self.report['contrasts']))

    def test_42_missing_finer_rejected(self):
        summary=copy.deepcopy(self.summary); summary['cases']=[r for r in summary['cases'] if not r['id'].endswith('__fine')]
        with tempfile.TemporaryDirectory(prefix='p7-missing-') as temp:
            run=Path(temp)
            for path in self.fixture_run.iterdir():
                if path.name!='summary.json': (run/path.name).symlink_to(path,target_is_directory=path.is_dir())
            d.write_json(run/'summary.json',summary); report=a.analyze(run)
        self.assertFalse(report['quality_gate']); self.assertFalse(report['checks']['all_forty_eight_finer']); self.assertEqual(report['candidates'],[])

    def test_43_reference_stocks_identical_across_anchors(self):
        self.assertTrue(self.report['gate']['checks']['same_P3_P6_prepared_states'])
        self.assertTrue(self.report['gate']['checks']['same_P3_P6_bath'])

    def test_44_P6_matched_negative_raw_reproduced(self):
        rows={k:v for k,v in self.report['checks'].items() if '/P6_matched/' in k}
        self.assertGreater(len(rows),75); self.assertTrue(all(rows.values()))


if __name__=='__main__': unittest.main()
