"""P8 software tests: native factories and gates, replaced integration only."""
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
import paper_calibrated_rewrite_design as d
import run_paper_calibrated_rewrite as r
import analyze_paper_calibrated_rewrite as a
import run_paper_calibrated_rewrite_detached as detached


def fixture_case(run,case,config):
    folder=run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,inputs=str(run/'inputs')))
    exp=r.TopologyExperiment(folder,dict(id=case['id'],fine=case['fine'])); names=a.phase_names(case)
    def fake_sim(horizon):
        name=names[len(exp.records)]; start=exp.sim.cc_cells.copy()
        reference=None
        if case['kind']=='replay': reference=(case['source'],name)
        elif (case.get('background')=='fresh_E' and name.startswith('writing') and
              case['condition'] in ('M_open','M_probe_rna','M_probe_cut')):
            reference=('capacity__six_to_three__depol__high__M_open',name.removeprefix('writing_'))
        if reference:
            data=a.arrays(run/'inputs/p7'/reference[0],reference[1])
            if not np.array_equal(start,data['initial']): raise AssertionError('Historical fixture start differs')
            np.copyto(exp.sim.cc_cells,data['final'])
            return data['times'].copy(),data['concentrations'].copy()
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(exp.sim.cc_cells,i)
        if case['kind']=='rewrite':
            c=case['condition']; h=case['background']
            if name=='writing_contact' and c in ('M_open','M_probe_rna','M_probe_cut'):
                mark(range(9),'M')
                if h=='restored_E': mark([8],'E')  # partial writing, not a biological forecast
            if name=='probe_contact' and c not in ('M_probe_rna','M_probe_cut'):
                if np.any(a.labels(start[:,:3],exp.indices)=='M'): mark(range(4),'M')
                if h=='ordinary_E' and c=='M_open': mark([3],'E')  # full writing, failed onward transfer
        exp.sim.cc_cells[exp.indices['Na']]+=.001+.00001*np.arange(len(exp.ids))
        if case['kind']=='age' and case['fine']: exp.sim.cc_cells[exp.indices['Na']]+=.000001
        last=exp.sim.cc_cells.copy(); last[exp.indices['Na']]-=.0005
        return np.array([0.,horizon*.8,float(horizon)]),np.array([start,last,last])
    with patch.object(exp.sim,'sim',side_effect=fake_sim): r.trajectory(exp,case,run)
    result=r.result_record(exp,case); d.write_json(folder/'result.json',result)
    return dict(id=case['id'],execution_pass=True,status='finished',returncode=0,result=result,
                result_sha256=d.digest(folder/'result.json'))


class TestPaperCalibratedRewrite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p8-software-fixture-'); cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        cls.config=json.loads((d.ROOT/'configs/paper_calibrated_rewrite_v1.json').read_text())
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,gate=None,age_gate=None)
        with redirect_stdout(io.StringIO()):
            for c in d.fixed_cases():
                cls.summary['cases'].append(fixture_case(cls.fixture_run,c,cls.config))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                key='gate' if len(cls.summary['cases'])==3 else 'age_gate' if len(cls.summary['cases'])==5 else None
                if key:
                    gate=a.gate_audit(cls.fixture_run) if key=='gate' else a.age_gate_audit(cls.fixture_run)
                    d.write_json(cls.fixture_run/(key+'.json'),gate)
                    cls.summary[key]=gate; cls.summary[key+'_sha256']=d.digest(cls.fixture_run/(key+'.json'))
        cls.summary['all_execution_valid']=True; d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.report=a.analyze(cls.fixture_run); cls.reports={b['case']['id']:b for b in cls.report['branches']}
        cls.primary='rewrite__aged_E__M_open'

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_01_panel(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases()); self.assertEqual(len(d.fixed_cases()),61)
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),29)
        self.assertEqual(sum(len(a.phase_names(c)) for c in d.fixed_cases()),351)

    def test_02_fixed_config(self):
        self.assertEqual(d.validate_config(self.config),d.FIXED)
        for k,v in (('workers',3),('cue_cells',3),('algorithm','hypol'),('serial_relay',True)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{k:v}))

    def test_03_full_fixture_audit(self):
        self.assertEqual([k for k,v in self.report['checks'].items() if not v],[])
        for key in ('gate','age_gate'):
            self.assertEqual([k for k,v in self.report[key]['checks'].items() if not v],[])
        self.assertTrue(self.report['quality_gate']); self.assertEqual(self.report['native_integrations'],351)

    def test_04_historical_replays(self):
        out=[b['outcomes'] for b in self.report['gate']['branches']]
        self.assertTrue(out[0]['all_recipient_M']); self.assertTrue(out[1]['all_recipient_M']); self.assertTrue(out[2]['all_recipient_E'])
        self.assertEqual(sum('/replay/' in k for k in self.report['gate']['checks']),279)

    def test_05_real_historical_carriers_not_stock(self):
        for h in ('ordinary_E','restored_E'):
            old=a.arrays(self.fixture_run/'inputs/p5'/('relay__'+h+'__open'),'r06_isolated_2')
            contact=a.arrays(self.fixture_run/('rewrite__'+h+'__M_open'),'writing_contact')
            self.assertTrue(np.array_equal(contact['initial'][:,6:],old['final']))
            self.assertFalse(np.array_equal(contact['initial'][:,6:],old['concentrations'][-1]))

    def test_06_round_six_cell_age_not_six_cell_lifetimes(self):
        self.assertTrue(self.report['cell_age_is_not_lineage_age'])
        self.assertTrue(all(s['cell_elapsed_units']==40000 for s in self.report['gate']['lineage_sources']))
        for c in ('age__E','age__E__fine'):
            info=json.loads((self.fixture_run/c/'result.json').read_text())
            self.assertEqual([p['requested_horizon'] for p in info['phases']],[20000,10000,10000])

    def test_07_fine_age_bank_is_used(self):
        coarse=a.arrays(self.fixture_run/'age__E','age_3')['final']
        fine=a.arrays(self.fixture_run/'age__E__fine','age_3')['final']
        self.assertFalse(np.array_equal(coarse,fine))
        start=a.arrays(self.fixture_run/(self.primary+'__fine'),'writing_contact')['initial'][:,6:]
        self.assertTrue(np.array_equal(start,fine)); self.assertFalse(np.array_equal(start,coarse))

    def test_08_cues_removed_original_targets_retained(self):
        folder=self.fixture_run/self.primary; contact=a.arrays(folder,'writing_contact'); hold=a.arrays(folder,'writing_isolated_1')
        self.assertTrue(np.array_equal(hold['initial'],contact['final'][:,6:]))
        self.assertFalse(np.array_equal(hold['initial'],contact['final'][:,:3]))
        info=json.loads((folder/'result.json').read_text())
        self.assertTrue(all(not i.startswith('cue:') for p in info['phases'][1:] for i in p['setup']['cell_ids']))

    def test_09_actual_written_states_enter_probe(self):
        folder=self.fixture_run/self.primary
        self.assertTrue(np.array_equal(a.arrays(folder,'probe_contact')['initial'][:,:3],a.arrays(folder,'writing_isolated_2')['final']))

    def test_10_probe_is_fresh_E_and_all_targets_removed(self):
        folder=self.fixture_run/self.primary; contact=a.arrays(folder,'probe_contact'); hold=a.arrays(folder,'probe_isolated_1')
        self.assertTrue(np.array_equal(hold['initial'],contact['final'][:,3:4]))
        self.assertEqual(self.reports[self.primary]['probe']['recipient_start_labels'],'E')
        info=json.loads((folder/'result.json').read_text())
        self.assertEqual(info['phases'][-1]['setup']['cell_ids'],['probe:00'])

    def test_11_full_writing_and_transfer(self):
        b=self.reports[self.primary]
        self.assertTrue(b['outcomes']['complete_M_rewriting']); self.assertTrue(b['outcomes']['complete_rewriting_and_transfer'])
        self.assertEqual(self.report['totals']['control_qualified_backgrounds'],['fresh_E','aged_E'])

    def test_12_partial_not_promoted_by_successful_probe(self):
        b=self.reports['rewrite__restored_E__M_open']
        self.assertEqual(b['writing']['retained_M'],2); self.assertTrue(b['probe']['all_recipient_M'])
        self.assertFalse(b['outcomes']['complete_rewriting_and_transfer'])

    def test_13_writing_and_transmission_failures_separate(self):
        b=self.reports['rewrite__ordinary_E__M_open']
        self.assertTrue(b['outcomes']['complete_M_rewriting']); self.assertFalse(b['outcomes']['onward_M_acquisition'])

    def test_14_separate_stage_blocks(self):
        for suffix in ('rna','cut'):
            write=self.reports['rewrite__aged_E__M_write_'+suffix]; probe=self.reports['rewrite__aged_E__M_probe_'+suffix]
            self.assertTrue(write['writing']['all_targets_E']); self.assertTrue(probe['writing']['all_targets_M'])
            self.assertTrue(write['probe']['all_recipient_E']); self.assertTrue(probe['probe']['all_recipient_E'])

    def test_15_qualifier_requires_all_controls(self):
        conditions=copy.deepcopy(self.report['contrasts'][1]['conditions']); self.assertTrue(a.qualify(conditions))
        for c in ('E_sham','no_cue','M_write_rna','M_write_cut','M_probe_rna','M_probe_cut'):
            bad=copy.deepcopy(conditions); bad[c]['probe']['all_recipient_E']=False; self.assertFalse(a.qualify(bad))
        del conditions['M_probe_cut']; self.assertFalse(a.qualify(conditions))

    def test_16_two_holds_required(self):
        folder=self.fixture_run/self.primary; idx=json.loads((folder/'result.json').read_text())['ion_indices']
        one,two=a.arrays(folder,'writing_isolated_1'),a.arrays(folder,'writing_isolated_2')
        self.assertTrue(a.stable(one,two,idx,'M').all())
        one['concentrations'][-1,idx['miR200_total']]=10000; self.assertFalse(a.stable(one,two,idx,'M').any())

    def test_17_finer_all_new_phases(self):
        self.assertEqual(len(self.report['fine_comparisons']),29); self.assertTrue(self.report['all_selected_fine_agree'])
        for c in d.fixed_cases():
            if c['fine']:
                info=json.loads((self.fixture_run/c['id']/'result.json').read_text())
                self.assertTrue(all(p['setup']['integrator']['time_step']==.00005 for p in info['phases']))

    def test_18_no_cue_fully_isolated_same_duration(self):
        folder=self.fixture_run/'rewrite__aged_E__no_cue'; rec=json.loads((folder/'result.json').read_text())['phases'][0]
        self.assertEqual(rec['requested_horizon'],20000); self.assertEqual(rec['setup']['grid_shape'],[1,3])
        self.assertFalse(a.arrays(folder,'writing_contact')['junction_diffusion'].any())

    def test_19_RNA_block_preserves_ions(self):
        for c,phase in (('M_write_rna','writing_contact'),('M_probe_rna','probe_contact')):
            folder=self.fixture_run/('rewrite__aged_E__'+c)
            rec=next(p for p in json.loads((folder/'result.json').read_text())['phases'] if p['phase']==phase)
            self.assertEqual(rec['setup']['mirna_kd'],0); self.assertTrue(a.arrays(folder,phase)['junction_diffusion'][:4].any())

    def test_20_boundaries_only_cut(self):
        for c,phase,n in (('M_write_cut','writing_contact',3),('M_probe_cut','probe_contact',2)):
            x=a.arrays(self.fixture_run/('rewrite__aged_E__'+c),phase); region=x['edge_region_initial']
            self.assertEqual(sum(region==2),n); self.assertTrue(np.all(x['edge_available_initial'][region==2]==0))
            self.assertTrue(np.all(x['edge_available_initial'][region!=2]==1))

    def test_21_manifest_and_input_count(self):
        self.assertEqual(len(d.LOCAL_FILES),62); self.assertEqual(len(self.summary['hashes_sha256']),98)
        self.assertEqual(len(self.summary['inputs']),50)
        bad=copy.deepcopy(self.summary); bad['inputs']={}; self.assertFalse(all(a.integrity(self.fixture_run,bad).values()))

    def mutate(self,edit,cid=None):
        cid=cid or self.primary; temp=tempfile.TemporaryDirectory(prefix='p8-mutated-'); self.addCleanup(temp.cleanup); run=Path(temp.name)
        for path in self.fixture_run.iterdir():
            if path.name==cid: continue
            (run/path.name).symlink_to(path,target_is_directory=path.is_dir())
        folder=run/cid; shutil.copytree(self.fixture_run/cid,folder)
        result=json.loads((folder/'result.json').read_text()); edit(folder,result); d.write_json(folder/'result.json',result)
        checks=a.Checks(); a.branch(folder,next(c for c in d.fixed_cases() if c['id']==cid),checks); return checks.rows

    def array_edit(self,phase,key,change):
        def edit(folder,result):
            rec=next(p for p in result['phases'] if p['phase']==phase); data=a.arrays(folder,phase); change(data[key])
            np.savez_compressed(folder/(phase+'.npz'),**data); rec['sha256']=d.digest(folder/(phase+'.npz'))
        return edit

    def test_22_rehashed_wrong_source(self):
        rows=self.mutate(self.array_edit('writing_contact','initial',lambda x:x.__setitem__((0,6),0)))
        self.assertFalse(rows[self.primary+'/actual_target_start'])

    def test_23_rehashed_cue_recycling(self):
        def edit(folder,result):
            data=a.arrays(folder,'writing_isolated_1'); data['initial']=a.arrays(folder,'writing_contact')['final'][:,:3]
            np.savez_compressed(folder/'writing_isolated_1.npz',**data); result['phases'][1]['sha256']=d.digest(folder/'writing_isolated_1.npz')
        self.assertFalse(self.mutate(edit)[self.primary+'/all_cues_removed_targets_retained'])

    def test_24_wrong_identity(self):
        def edit(folder,result): result['phases'][1]['setup']['cell_ids'][0]='cue:00'
        self.assertFalse(self.mutate(edit)[self.primary+'/writing_isolated_1/ids'])

    def test_25_rehashed_reset_before_probe(self):
        rows=self.mutate(self.array_edit('probe_contact','initial',lambda x:x.__setitem__((0,0),0)))
        self.assertFalse(rows[self.primary+'/probe_actual_held_targets'])

    def test_26_rehashed_wrong_recipient(self):
        rows=self.mutate(self.array_edit('probe_contact','initial',lambda x:x.__setitem__((5,3),0)))
        self.assertFalse(rows[self.primary+'/probe_fresh_E'])

    def test_27_rehashed_wrong_cut(self):
        cid='rewrite__aged_E__M_write_cut'
        rows=self.mutate(self.array_edit('writing_contact','edge_available_initial',lambda x:x.fill(1)),cid)
        self.assertFalse(rows[cid+'/writing_contact/edge_available_initial'])

    def test_28_wrong_expression(self):
        rows=self.mutate(self.array_edit('writing_contact','expression_gate_final',lambda x:x.fill(1)))
        self.assertFalse(rows[self.primary+'/writing_contact/expression_final'])

    def test_29_budget_prevents_launch(self):
        with patch.object(r.subprocess,'run') as proc:
            result=r.run_worker(d.fixed_cases()[0],self.config,self.fixture_run,time.monotonic()-1,{})
        self.assertEqual(result['status'],'not_launched_budget'); proc.assert_not_called()

    def test_30_timeout_no_retry(self):
        with tempfile.TemporaryDirectory(prefix='p8-timeout-') as temp,patch.object(r.subprocess,'run',
            side_effect=subprocess.TimeoutExpired('fixture',1)) as proc,redirect_stdout(io.StringIO()):
            result=r.run_worker(d.fixed_cases()[0],self.config,Path(temp),time.monotonic()+10,{})
        self.assertEqual(result['status'],'timeout'); self.assertEqual(proc.call_count,1)

    def stage_fixture(self,predecessor=True,replay=True,age=True):
        with tempfile.TemporaryDirectory(prefix='p8-stages-') as temp:
            root=Path(temp); (root/'runs').mkdir(); called=[]
            def fake_freeze(run): (run/'frozen').mkdir(); return {},{},{}
            def fake_worker(case,config,run,deadline,env):
                s=json.loads((run/'summary.json').read_text()); self.assertTrue(s['predecessor_gate'])
                if case['kind']!='replay': self.assertTrue(s['gate']['quality_gate'])
                if case['kind']=='rewrite': self.assertTrue(s['age_gate']['quality_gate'])
                called.append(case['id']); return dict(id=case['id'],execution_pass=True)
            path=Path(__file__).resolve().parents[1]/'configs/paper_calibrated_rewrite_v1.json'
            with patch.object(d,'ROOT',root),patch.object(d,'source_check'),patch.object(r,'freeze',side_effect=fake_freeze), \
                 patch.object(r,'predecessor_gate',return_value=predecessor),patch.object(a,'integrity',return_value={'ok':True}), \
                 patch.object(a,'gate_audit',return_value={'quality_gate':replay}),patch.object(a,'age_gate_audit',return_value={'quality_gate':age}), \
                 patch.object(r,'run_worker',side_effect=fake_worker),redirect_stdout(io.StringIO()):
                if not predecessor:
                    with self.assertRaisesRegex(RuntimeError,'Historical re-audit failed'): r.run(path)
                    return 1,called
                return r.run(path),called

    def test_31_predecessor_failure_stops_native(self):
        code,calls=self.stage_fixture(predecessor=False); self.assertEqual(code,1); self.assertEqual(calls,[])

    def test_32_replay_failure_stops_new_work(self):
        code,calls=self.stage_fixture(replay=False); self.assertEqual(code,1); self.assertEqual(len(calls),3)

    def test_33_age_failure_stops_rewriting(self):
        code,calls=self.stage_fixture(age=False); self.assertEqual(code,1); self.assertEqual(len(calls),5)

    def test_34_full_panel_without_outcome_filter(self):
        code,calls=self.stage_fixture(); self.assertEqual(code,0); self.assertEqual(len(calls),61)
        self.assertFalse(self.report['positive_new_rewriting_required']); self.assertFalse(self.report['positive_new_transfer_required'])

    def test_35_exclusive_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory(prefix='p8-lock-') as temp:
            root=Path(temp); (root/'runs').mkdir()
            with (root/'runs/paper-calibrated-rewrite.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(detached,'ROOT',root),patch.object(detached,'JOBS',root/'runs/jobs'):
                    with self.assertRaisesRegex(RuntimeError,'already supervised'): detached.launch()

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p8-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-calibrated-rewrite-test'; job.mkdir(parents=True)
            run=root/'runs/paper-calibrated-rewrite-test'; run.mkdir(); commands=[]
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={'/tmp/no-such-p8-input':'bad'} if bad_input else {}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time(),planned_cases=61))
            def fake_child(command,logfile,timeout,update):
                commands.append((command,logfile.name,timeout))
                if logfile.name=='runner.log':
                    if runner_rc: return runner_rc
                    logfile.write_text(f'Run artifacts: {run}\n')
                    cases=[dict(execution_pass=True,result=dict(case=dict(kind='rewrite')))]*56
                    cases += [dict(execution_pass=True,result=dict(case=dict(kind='age')))]*5
                    d.write_json(run/'summary.json',dict(cases=cases,predecessor_gate=True,gate=dict(quality_gate=True),
                        age_gate=dict(quality_gate=True),stage='finished'))
                else: d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,
                    independent_check_count=123,gate=dict(quality_gate=True),all_selected_fine_agree=True))
                update(12345); return 0
            read_fd,write_fd=os.pipe(); os.close(write_fd)
            with patch.object(detached,'ROOT',root),patch.object(detached,'run_child',side_effect=fake_child),redirect_stdout(io.StringIO()):
                code=detached.supervise(job,read_fd)
            return code,json.loads((job/'status.json').read_text()),commands

    def test_36_supervisor_progress_caps(self):
        code,state,commands=self.supervisor_fixture(); self.assertEqual(code,0); self.assertEqual(state['phase'],'complete')
        self.assertEqual(state['completed_cases'],61); self.assertEqual(state['completed_rewrite_cases'],56)
        self.assertTrue(state['age_gate_pass']); self.assertEqual([c[2] for c in commands],[29100,1800])

    def test_37_supervisor_failure_no_retry(self):
        code,state,commands=self.supervisor_fixture(runner_rc=124); self.assertEqual(code,1); self.assertEqual(len(commands),1)

    def test_38_supervisor_bad_audit(self):
        code,state,commands=self.supervisor_fixture(audit_quality=False); self.assertEqual(code,1); self.assertEqual(state['phase'],'failed')

    def test_39_supervisor_changed_input(self):
        code,state,commands=self.supervisor_fixture(bad_input=True); self.assertEqual(code,1); self.assertEqual(commands,[])

    def test_40_stale_heartbeat(self):
        with tempfile.TemporaryDirectory(prefix='p8-heartbeat-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='coarse_rewriting',heartbeat_epoch=0))
            self.assertTrue(detached.status(job)['heartbeat_stale'])
            d.write_json(job/'status.json',dict(phase='complete',heartbeat_epoch=0)); self.assertFalse(detached.status(job)['heartbeat_stale'])

    def test_41_unregistered_worker_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p8-invalid-') as temp:
            path=Path(temp)/'spec.json'; d.write_json(path,dict(case={'id':'extra'},config=self.config,inputs=str(path.parent/'inputs')))
            with patch.object(r,'TopologyExperiment') as factory:
                with self.assertRaisesRegex(ValueError,'Unregistered'): r.worker(path)
            factory.assert_not_called()

    def test_42_all_controls_and_no_extra_generation(self):
        self.assertEqual(len(self.report['contrasts']),4); self.assertTrue(all(len(c['conditions'])==7 for c in self.report['contrasts']))
        self.assertEqual(self.report['totals']['new_onward_handovers'],56)
        for key in ('serial_renewal_demonstrated','automatic_follow_on','autonomous_heredity_demonstrated','cell_division_simulated'):
            self.assertFalse(self.report[key])

    def test_43_missing_fine_panel_rejected(self):
        summary=copy.deepcopy(self.summary); summary['cases']=[r for r in summary['cases'] if not r['id'].endswith('__fine')]
        with tempfile.TemporaryDirectory(prefix='p8-missing-') as temp:
            run=Path(temp)
            for path in self.fixture_run.iterdir():
                if path.name!='summary.json': (run/path.name).symlink_to(path,target_is_directory=path.is_dir())
            d.write_json(run/'summary.json',summary); report=a.analyze(run)
        self.assertFalse(report['quality_gate']); self.assertFalse(report['checks']['all_twenty_nine_finer'])

    def test_44_exact_fresh_baseline_writing(self):
        rows={k:v for k,v in self.report['checks'].items() if '/P7_matched/' in k}
        self.assertEqual(len(rows),93); self.assertTrue(all(rows.values()))

    def test_45_probe_policy_cannot_change_prior_writing(self):
        rows={k:v for k,v in self.report['checks'].items() if '/same_writing/' in k}
        self.assertEqual(len(rows),48); self.assertTrue(all(rows.values()))


if __name__=='__main__': unittest.main()
