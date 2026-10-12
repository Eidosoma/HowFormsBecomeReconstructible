"""P13 synthetic fixtures: fabricated dynamics are not biological evidence."""
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
import paper_lineage_return_design as d
import run_paper_lineage_return as r
import analyze_paper_lineage_return as a
import run_paper_lineage_return_detached as detached

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir()
    exp=r.ClockBoundedExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs):
        current['name']=name
        return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy()
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        if name=='writing_contact':
            if c['stage']=='returns' or failure=='positive_writing_control': mark(range(6,9),'M')
            if failure=='writer': mark([len(exp.ids)-1],'E')
        if '_segment_' in name:
            n=int(name[1:3])
            if exp.route=='open' or failure=='positive_relay_control':
                mark([3+i for i in exp.active],'M')
                if failure=='round'+str(n) and 2 in exp.active: mark([5],'E')
            if failure=='presignal' and name=='r07_segment_01': mark([3],'M')
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.00001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=np.full(total//cap,cap,dtype=np.int64); proposed=np.full(len(steps),2*stride,dtype=np.int64)
        shots=np.arange(0,total+1,stride,dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        if failure=='late_occupancy' and name=='writing_isolated_1':
            for at in (-2,-3): exp.z.GRN.set_very_healthy(values[at],2)
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(steps),sample_count=len(shots),capped_steps=len(steps),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock):
        out=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestLineageReturn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p13-software-'); cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_matches_saved=True,
            prior_checks=110444,prior_cases=158,prior_calls=1746,actual_round_six_sources=True)
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
            predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),
            gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        with redirect_stdout(io.StringIO()):
            for stage in d.STAGES:
                for c in d.stage_cases(stage):
                    cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate)
                cls.summary['gates'][stage]=gate; cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.summary.update(all_execution_valid=True,completion_reason='all_registered_stages_completed',stage='finished')
        d.write_json(cls.fixture_run/'summary.json',cls.summary)
        # Expensive real original/archive P12 re-audits run at biological preflight and final audit.
        with patch.object(a,'predecessor_audit',return_value=cls.history): cls.report=a.analyze(cls.fixture_run)
        cls.primary=d.case('returns')
        cls.by={b['case']['id']:b['outcome'] for b in cls.report['stages']['relay_controls']['branches']}

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p13-unit-') as temp:
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

    def test_01_registered_cases(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases())
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[6,12,48,36])
        self.assertEqual(len(d.fixed_cases()),102)

    def test_02_fixed_config(self):
        self.assertEqual(d.validate_config(json.loads((d.ROOT/'configs/paper_lineage_return_v1.json').read_text())),d.FIXED)
        for key,value in (('workers',3),('maximum_cases',103),('protein_percent',30),('round_numbers',[7,8,9,10])):
            modified=copy.deepcopy(d.FIXED); modified[key]=value
            with self.assertRaises(ValueError): d.validate_config(modified)

    def test_03_independent_draw_book(self):
        self.assertEqual(d.draw_book(),a.expected_draws())
        self.assertEqual(d.draw_book(),json.loads((d.ROOT/'configs/paper_lineage_return_draws_v1.json').read_text()))

    def test_04_schedules_keep_exact_dose_and_window(self):
        for seed in d.SEEDS:
            for n in (7,8,9):
                schedule=d.intervals(seed,n); self.assertEqual(schedule,a.schedule(seed,n))
                self.assertEqual(sum(e-s for s,e,_ in schedule),80000)
                self.assertEqual([sum(e-s for s,e,active in schedule if i in active) for i in range(3)],[20000]*3)
                self.assertTrue(all(e>s for s,e,_ in schedule))
                self.assertEqual([i for _,_,active in schedule for i in active],[0,1,2])

    def test_05_protein_only(self):
        for fine in (False,True):
            E,M=r.stock(self.fixture_run,fine)
            for reference in (E,M):
                for seed in d.SEEDS:
                    for role in ('benchmark','r07','r08','r09'):
                        value=d.recipient(reference,seed,role)
                        np.testing.assert_array_equal(value,a.incoming(reference,seed,role))
                        np.testing.assert_array_equal(value[np.arange(17)!=7],np.repeat(reference,3,axis=1)[np.arange(17)!=7])
                        self.assertEqual(''.join(a.labels(value,a.INDEX)),str(a.labels(reference,a.INDEX)[0])*3)
                        self.assertTrue(np.all((value[7]/reference[7]>=.75)&(value[7]/reference[7]<=1.25)))

    def test_06_complete_manifest(self):
        self.assertEqual(len(d.LOCAL_FILES),107); self.assertEqual(len(d.execution_manifest()),143)
        self.assertEqual(len(d.input_paths()),4293); d.source_check()
        self.assertTrue(all(a.integrity(self.fixture_run,self.summary).values()))

    def test_07_full_synthetic_audit(self):
        self.assertTrue(self.report['quality_gate'])
        self.assertEqual(self.report['completed_cases'],102); self.assertEqual(self.report['integration_calls'],1008)
        self.assertEqual(len(self.report['fine_comparisons']),51); self.assertTrue(self.report['all_fine_agree'])
        for row in self.report['trial_counts']:
            self.assertEqual(row['prior_lineages'],3)
            for key in ('raw_successes','control_qualified_successes','benchmark_supported_successes'): self.assertEqual(row[key],3)

    def test_08_actual_P12_descendants_are_unchanged(self):
        for c in d.stage_cases('returns'):
            old,name,ids=d.source(c); original=a.arrays(self.fixture_run/'inputs/p12'/old,name)['final']
            initial=a.arrays(self.fixture_run/c['id'],'writing_contact')['initial']
            np.testing.assert_array_equal(initial[:,6:],original)
            rec=json.loads((self.fixture_run/c['id']/'result.json').read_text())['phases'][0]
            self.assertEqual(rec['setup']['cell_ids'][6:],ids)
            self.assertEqual(rec['logical_interval'],[680000,700000])

    def test_09_cues_and_teachers_are_removed(self):
        for c in d.stage_cases('returns'):
            folder=self.fixture_run/c['id']; value=a.arrays(folder,'writing_contact')['final']
            np.testing.assert_array_equal(a.arrays(folder,'writing_isolated_1')['initial'],value[:,6:])
            for n in (7,8,9):
                final='r%02d_segment_%02d'%(n,len(d.intervals(c['seed'],n)))
                np.testing.assert_array_equal(a.arrays(folder,'r%02d_isolated_1'%n)['initial'],a.arrays(folder,final)['final'][:,3:])

    def test_10_rounds_continue_without_reset(self):
        for c in d.stage_cases('returns'):
            folder=self.fixture_run/c['id']
            previous=a.arrays(folder,'writing_isolated_2')['final']
            for n in (7,8,9):
                first=a.arrays(folder,'r%02d_segment_01'%n)['initial']
                np.testing.assert_array_equal(first[:,:3],previous)
                previous=a.arrays(folder,'r%02d_isolated_2'%n)['final']

    def test_11_fine_uses_own_prefix(self):
        c=d.case('returns',fine=True); src,name,_=d.source(c)
        self.assertTrue(src.endswith('__fine'))
        np.testing.assert_array_equal(a.arrays(self.fixture_run/c['id'],'writing_contact')['initial'][:,6:],
                                      a.arrays(self.fixture_run/'inputs/p12'/src,name)['final'])
        coarse=a.arrays(self.fixture_run/self.primary['id'],'writing_isolated_2')['final']
        fine=a.arrays(self.fixture_run/c['id'],'writing_isolated_2')['final']
        self.assertFalse(np.array_equal(coarse,fine))

    def test_12_clock_exact(self):
        for phase in json.loads((self.fixture_run/self.primary['id']/'result.json').read_text())['phases']:
            x=a.arrays(self.fixture_run/self.primary['id'],phase['phase'])
            self.assertEqual(x['times'][0],0); self.assertEqual(x['times'][-1],phase['requested_horizon'])
            self.assertEqual(phase['clock']['maximum_step'],100)
            self.assertTrue(np.all(np.diff(x['times'])==100))

    def test_13_return_writer_failure_stops(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            row=fixture_case(run,self.primary,'writer'); checks,report,data=self.audit_branch(run,self.primary)
            self.assertTrue(all(checks.rows.values())); self.assertFalse(report['outcome']['complete'])
            self.assertEqual(row['result']['outcome']['stop_reason'],'writer_not_M'); self.assertEqual(len(data),3)

    def test_14_failures_at_each_handover_stop(self):
        for n in (7,8,9):
            with self.subTest(round=n),self.isolated_run() as run,redirect_stdout(io.StringIO()):
                fixture_case(run,self.primary,'round'+str(n)); checks,report,_=self.audit_branch(run,self.primary)
                self.assertTrue(all(checks.rows.values())); out=report['outcome']
                self.assertEqual(out['stop_reason'],'round_%d_incomplete'%n)
                self.assertEqual(len(out['rounds']),n-6); self.assertFalse(out['complete'])

    def test_15_initial_label_is_not_enough(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            fixture_case(run,self.primary,'presignal'); checks,report,_=self.audit_branch(run,self.primary)
            self.assertTrue(all(checks.rows.values())); row=report['outcome']['rounds'][0]
            self.assertEqual(row['initial_labels'],'EEE'); self.assertEqual(row['presignal_labels'],'MEE')
            self.assertFalse(row['complete'])

    def test_16_terminal_label_is_not_enough(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            fixture_case(run,self.primary,'late_occupancy'); checks,report,_=self.audit_branch(run,self.primary)
            self.assertTrue(all(checks.rows.values()))
            self.assertEqual(''.join(a.labels(a.arrays(run/self.primary['id'],'writing_isolated_1')['final'],a.INDEX)),'MMM')
            self.assertFalse(report['outcome']['writing']['qualified'])

    def test_17_unavailable_control_is_real_zero_phase_skip(self):
        for history in ('written','ordinary','benchmark'):
            with self.isolated_run() as run,redirect_stdout(io.StringIO()):
                c=d.case('benchmarks' if history=='benchmark' else 'returns',history)
                fixture_case(run,c,'writer')
                for route in ('rna','cut'):
                    control=d.case('relay_controls',history,route=route)
                    row=fixture_case(run,control); checks,report,data=self.audit_branch(run,control)
                    self.assertTrue(all(checks.rows.values())); self.assertEqual(data,{})
                    self.assertEqual(row['result']['phases'],[]); self.assertIsNone(row['result']['ion_indices'])
                    self.assertFalse(report['outcome']['available']); self.assertFalse(report['outcome']['negative'])

    def test_18_later_failure_does_not_remove_qualified_writer_controls(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            fixture_case(run,self.primary,'round8')
            c=d.case('relay_controls',route='rna'); fixture_case(run,c)
            checks,report,_=self.audit_branch(run,c)
            self.assertTrue(all(checks.rows.values())); self.assertTrue(report['outcome']['available'])
            self.assertTrue(report['outcome']['negative'])

    def test_19_positive_writing_control_is_not_hidden(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            c=d.case('writing_controls',route='rna'); fixture_case(run,c,'positive_writing_control')
            checks,report,_=self.audit_branch(run,c)
            self.assertTrue(all(checks.rows.values())); self.assertFalse(report['outcome']['negative'])

    def test_20_positive_relay_control_is_not_hidden(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            fixture_case(run,self.primary)
            c=d.case('relay_controls',route='rna'); fixture_case(run,c,'positive_relay_control')
            checks,report,_=self.audit_branch(run,c)
            self.assertTrue(all(checks.rows.values())); self.assertFalse(report['outcome']['negative'])

    def test_21_denominators_survive_failures(self):
        by=copy.deepcopy(self.by); by[self.primary['id']]['complete']=False
        trials,counts,_=a.trial_counts(by); row=counts[0]
        self.assertEqual(row['prior_lineages'],3); self.assertEqual(row['raw_successes'],2)
        self.assertEqual(len(trials),6)

    def test_22_bad_control_only_removes_qualified_success(self):
        by=copy.deepcopy(self.by); by[d.case('writing_controls',route='rna')['id']]['negative']=False
        _,counts,_=a.trial_counts(by)
        self.assertEqual(counts[0]['raw_successes'],3); self.assertEqual(counts[0]['control_qualified_successes'],2)

    def test_23_benchmark_failures_are_separately_reported(self):
        by=copy.deepcopy(self.by); by[d.case('benchmarks','benchmark')['id']]['complete']=False
        _,counts,bench=a.trial_counts(by); self.assertFalse(bench[0]['qualified'])
        for row in counts:
            self.assertEqual(row['raw_successes'],3); self.assertEqual(row['control_qualified_successes'],3)
            self.assertEqual(row['benchmark_supported_successes'],2)

    def test_24_skipped_control_never_qualifies(self):
        by=copy.deepcopy(self.by); c=d.case('relay_controls',route='rna')
        by[c['id']]=dict(available=False,negative=False)
        _,counts,_=a.trial_counts(by); self.assertEqual(counts[0]['control_qualified_successes'],2)

    def test_25_rehashed_source_reset_is_caught(self):
        self.corrupt_array('writing_contact',lambda x:x['initial'].__setitem__((0,6),x['initial'][0,6]+1))

    def test_26_rehashed_waiting_pupil_reset_is_caught(self):
        self.corrupt_array('r07_segment_02',lambda x:x['initial'].__setitem__((7,5),x['initial'][7,5]+1))

    def test_27_rehashed_new_recipient_change_is_caught(self):
        self.corrupt_array('r08_segment_01',lambda x:x['initial'].__setitem__((1,3),x['initial'][1,3]+1))

    def test_28_rehashed_clock_error_is_caught(self):
        self.corrupt_array('r07_segment_01',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_29_rehashed_schedule_error_is_caught(self):
        self.corrupt_array('r07_segment_01',lambda x:x['edge_available_initial'].__setitem__(2,1))

    def test_30_rehashed_bath_error_is_caught(self):
        self.corrupt_array('writing_contact',lambda x:x['environment'].__setitem__(0,x['environment'][0]+1))

    def test_31_wrong_live_ID_is_caught(self):
        with self.copied_primary() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['phases'][0]['setup']['cell_ids'][6]='reference'
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))

    def test_32_hidden_extra_phase_is_caught(self):
        with self.copied_primary() as (run,folder):
            shutil.copyfile(folder/'writing_contact.npz',folder/'unregistered.npz')
            checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_33_forged_complete_outcome_is_caught(self):
        with self.copied_primary() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['outcome']['complete']=False
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))

    def test_34_forged_autonomy_is_caught(self):
        with self.copied_primary() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['autonomous_reproduction']=True
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))

    def test_35_missing_phase_is_caught(self):
        with self.copied_primary() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['phases'].pop()
            d.write_json(folder/'result.json',result)
            with self.assertRaises(ValueError): self.audit_branch(run,self.primary)

    def test_36_wrong_time_origin_is_caught(self):
        with self.copied_primary() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['phases'][0]['logical_interval']=[0,20000]
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,self.primary)
            self.assertFalse(all(checks.rows.values()))

    def test_37_fine_disagreement_is_technical_failure(self):
        cases=d.stage_cases('returns'); by={c['id']:copy.deepcopy(self.by[c['id']]) for c in cases}
        endpoints={c['id']:{'end':dict(final=np.ones((17,3)))} for c in cases}
        by[d.case('returns',fine=True)['id']]['complete']=False
        checks=a.Checks(); a.p12.compare_fine(cases,by,endpoints,checks)
        self.assertFalse(all(checks.rows.values()))

    def test_38_worker_rejects_unregistered_case(self):
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp); folder=run/'case'; folder.mkdir(); c=copy.deepcopy(self.primary); c['seed']=304
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=c,inputs=str(run/'inputs')))
            with self.assertRaises(ValueError),patch.object(r,'ClockBoundedExperiment') as exp: r.worker(folder/'spec.json')
            exp.assert_not_called()

    def test_39_worker_requires_stage_and_preflight(self):
        for stage,gate in (('benchmarks',True),('returns',False)):
            with tempfile.TemporaryDirectory() as temp:
                run=Path(temp); folder=run/'case'; folder.mkdir()
                d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
                d.write_json(run/'summary.json',dict(stage=stage,predecessor_gate=gate))
                with self.assertRaises(ValueError),patch.object(r,'ClockBoundedExperiment') as exp: r.worker(folder/'spec.json')
                exp.assert_not_called()

    def test_40_worker_requires_saved_technical_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp); folder=run/'case'; folder.mkdir()
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            d.write_json(run/'summary.json',dict(stage='returns',predecessor_gate=True,gates={'benchmarks':{'quality_gate':False}},gate_hashes={}))
            with self.assertRaises(ValueError),patch.object(r,'ClockBoundedExperiment') as exp: r.worker(folder/'spec.json')
            exp.assert_not_called()

    def test_41_predecessor_audit_checks_both_copies(self):
        saved=json.loads((self.fixture_run/'inputs/p12/independent_audit.json').read_text())
        archived=copy.deepcopy(saved); archived['run']=str(self.fixture_run/'inputs/p12')
        with patch.object(a.p12,'analyze',side_effect=[copy.deepcopy(saved),archived]) as analyze:
            result=a.predecessor_audit(self.fixture_run)
        self.assertTrue(result['quality_gate']); self.assertEqual(analyze.call_count,2)
        archived=copy.deepcopy(saved); archived['quality_gate']=False
        with patch.object(a.p12,'analyze',side_effect=[copy.deepcopy(saved),archived]):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])

    def test_42_runner_reaudits_predecessor(self):
        saved=json.loads((self.fixture_run/'inputs/p12/independent_audit.json').read_text())
        archived=copy.deepcopy(saved); archived['run']=str(self.fixture_run/'inputs/p12')
        with patch.object(a.p12,'analyze',side_effect=[copy.deepcopy(saved),archived]) as analyze:
            result=r.predecessor_audit(self.fixture_run)
        self.assertTrue(result['quality_gate']); self.assertEqual(analyze.call_count,2)
    def flow(self,negative=False,technical=None,execution=False,preflight=True):
        with tempfile.TemporaryDirectory(prefix='p13-flow-') as temp,redirect_stdout(io.StringIO()):
            output=Path(temp)/'output'; output.mkdir(); calls=[]
            def worker(c,config,run,deadline,env):
                calls.append(c); return dict(id=c['id'],execution_pass=not execution)
            def audit(run,stage):
                return dict(quality_gate=stage!=technical,eligible=not negative)
            history=dict(self.history,quality_gate=preflight)
            with patch.object(r.tempfile,'mkdtemp',return_value=str(output)),patch.object(r,'freeze',return_value=({}, {}, {})),\
                 patch.object(r,'predecessor_audit',return_value=history),patch.object(r,'run_worker',side_effect=worker),\
                 patch.object(a,'stage_audit',side_effect=audit),patch.object(a,'integrity',return_value={'fixture':True}),\
                 patch.object(d,'source_check'):
                try: code=r.run(d.ROOT/'configs/paper_lineage_return_v1.json')
                except RuntimeError:
                    if preflight: raise
                    code=1
            return code,calls,json.loads((output/'summary.json').read_text())

    def test_43_all_stages_once(self):
        code,calls,summary=self.flow()
        self.assertEqual((code,len(calls)),(0,102)); self.assertEqual(len({c['id'] for c in calls}),102)
        self.assertEqual(summary['completion_reason'],'all_registered_stages_completed')

    def test_44_benchmark_negative_does_not_suppress_descendants(self):
        code,calls,_=self.flow(negative=True); self.assertEqual((code,len(calls)),(0,102))

    def test_45_technical_failure_stops(self):
        code,calls,summary=self.flow(technical='returns')
        self.assertEqual((code,len(calls)),(1,18)); self.assertEqual(summary['completion_reason'],'technical_gate_failure')

    def test_46_execution_failure_stops(self):
        code,calls,_=self.flow(execution=True); self.assertEqual((code,len(calls)),(1,6))

    def test_47_bad_predecessor_blocks_all_cases(self):
        code,calls,summary=self.flow(preflight=False)
        self.assertEqual((code,len(calls)),(1,0)); self.assertFalse(summary['predecessor_gate'])

    def test_48_expired_worker_budget_does_not_launch(self):
        with patch.object(r.subprocess,'run') as launch:
            result=r.run_worker(self.primary,d.FIXED,Path('/tmp'),time.monotonic()-1,{})
        launch.assert_not_called(); self.assertFalse(result['execution_pass'])
        self.assertEqual(result['status'],'not_launched_budget')

    def supervisor_fixture(self,verification_rc=0,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p13-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-lineage-return-test'; job.mkdir(parents=True)
            run=root/'runs/paper-lineage-return-test'; run.mkdir()
            source=root/'source'; source.write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={str(source):'bad' if bad_input else d.digest(source)}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time()))
            (job/'runner.log').write_text('Run artifacts: '+str(run)+'\n')
            d.write_json(run/'summary.json',dict(cases=[],registered_cases=[],stage='finished',
                completion_reason='all_registered_stages_completed',gates={},selection={}))
            d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,independent_check_count=1,
                all_fine_agree=True,trial_counts=[],benchmarks=[]))
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
        with tempfile.TemporaryDirectory(prefix='p13-status-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='returns',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale'])

    def test_56_wrong_run_path_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p13-discover-') as temp:
            job=Path(temp); (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)

    def test_57_complete_negative_return_report(self):
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            (run/'frozen').symlink_to(self.fixture_run/'frozen',target_is_directory=True)
            summary=copy.deepcopy(self.summary); summary.update(cases=[],gates={},gate_hashes={})
            d.write_json(run/'predecessor_audit.json',self.history)
            rows={row['id']:row for row in self.summary['cases']}
            for stage in d.STAGES:
                for c in d.stage_cases(stage):
                    if stage=='returns':
                        row=fixture_case(run,c,'writer')
                    elif stage=='relay_controls' and c['history']!='benchmark':
                        row=fixture_case(run,c)
                    else:
                        (run/c['id']).symlink_to(self.fixture_run/c['id'],target_is_directory=True)
                        row=copy.deepcopy(rows[c['id']])
                    summary['cases'].append(row)
                d.write_json(run/'summary.json',summary)
                gate=a.stage_audit(run,stage); self.assertTrue(gate['quality_gate'])
                d.write_json(run/(stage+'_audit.json'),gate); summary['gates'][stage]=gate
                summary['gate_hashes'][stage]=d.digest(run/(stage+'_audit.json'))
                d.write_json(run/'summary.json',summary)
            with patch.object(a,'predecessor_audit',return_value=self.history): report=a.analyze(run)
            self.assertTrue(report['quality_gate']); self.assertEqual(report['completed_cases'],102)
            for row in report['trial_counts']:
                self.assertEqual(row['prior_lineages'],3); self.assertEqual(row['raw_successes'],0)
                self.assertEqual(row['control_qualified_successes'],0)
            self.assertEqual(report['integration_calls'],468)

    def test_58_worker_rejects_draw_book_change_before_instantiation(self):
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp); folder=run/'case'; folder.mkdir(); (run/'frozen').mkdir()
            c=d.case('benchmarks','benchmark')
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=c,inputs=str(run/'inputs')))
            d.write_json(run/'summary.json',dict(stage='benchmarks',predecessor_gate=True,gates={},gate_hashes={}))
            d.write_json(run/'frozen/paper_lineage_return_draws_v1.json',{})
            with self.assertRaises(ValueError),patch.object(r,'ClockBoundedExperiment') as exp: r.worker(folder/'spec.json')
            exp.assert_not_called()

if __name__=='__main__': unittest.main()


