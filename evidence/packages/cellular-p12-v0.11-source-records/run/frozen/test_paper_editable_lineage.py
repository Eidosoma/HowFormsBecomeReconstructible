"""P11 software-only fixtures. Native construction/gates, but no biological integrations."""
from contextlib import redirect_stdout
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
import paper_editable_lineage_design as d
import run_paper_editable_lineage as r
import analyze_paper_editable_lineage as a
import run_paper_editable_lineage_detached as detached


def fixture_case(run,c,config=None,folder_override=None,partial=False,failure=None):
    folder=folder_override or run/c['id']; folder.mkdir(exist_ok=True)
    exp=r.ClockBoundedExperiment(folder,dict(id=c['id'],fine=c['fine']))
    names=a.phase_names(c,a.max_rounds(c) if a.is_relay(c) else 1)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=names[len(exp.records)]; initial=sim.cc_cells.copy()
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        k=c['kind']
        if k=='stock' and failure=='stocks': mark([1],'E')
        if k=='write_M' and name=='writing_contact' and c['condition']=='M_open' and failure!='calibration': mark(range(6,9),'M')
        if k=='rewrite_E' and name=='writing_contact' and c['condition']=='E_open' and failure!='rewrite': mark(range(6,9),'E')
        if a.is_graph(c,name):
            route=a.relay_route(c)
            good=(k=='before' or (k=='calibration_E' and c['condition']=='E_open') or (k=='after' and c['condition']=='E_open'))
            if good and route=='open':
                mark([3+i for i in exp.active],'M' if k=='before' else 'E')
                if (partial or failure==k) and 2 in exp.active: mark([5],'E' if k=='before' else 'M')
        sim.cc_cells[exp.indices['Na']]+=(.0011 if c['fine'] else .001)+.00001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=np.full(total//cap,cap,dtype=np.int64); proposed=np.full(len(steps),2*stride,dtype=np.int64)
        shots=np.arange(0,total+1,stride,dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        trace=dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots)
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(steps),sample_count=len(shots),capped_steps=len(steps),
            initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,trace,meta
    with patch.object(r.clock,'integrate',side_effect=fake_clock):
        rounds=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,rounds); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,
                result_sha256=d.digest(folder/'result.json'))


class TestEditableLineage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p11-software-fixture-')
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        cls.config=json.loads((d.ROOT/'configs/paper_editable_lineage_v1.json').read_text())
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.history=r.predecessor_audit(cls.fixture_run)
        if not cls.history['quality_gate']: raise AssertionError('P10R historical archive does not audit')
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
            predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),
            gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        with redirect_stdout(io.StringIO()):
            for stage in d.STAGES:
                for c in d.stage_cases(stage):
                    cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                    d.write_json(cls.fixture_run/'summary.json',cls.summary)
                gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']:
                    raise AssertionError([k for k,v in gate['checks'].items() if not v])
                if not gate['eligible']: raise AssertionError(gate['requirements'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate)
                cls.summary['gates'][stage]=gate; cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.summary.update(all_execution_valid=True,completion_reason='after_completed',stage='finished')
        d.write_json(cls.fixture_run/'summary.json',cls.summary)
        with patch.object(a,'predecessor_audit',return_value=cls.history):
            cls.report=a.analyze(cls.fixture_run)
        cls.by={b['case']['id']:b for b in cls.report['stages']['after']['branches']}
        cls.primary=d.case('after','E_open','written',False,'open')

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_01_registration(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases())
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[2,20,12,20,20])
        self.assertEqual(len(d.fixed_cases()),74)

    def test_02_config_rejects_retuning(self):
        self.assertEqual(d.validate_config(self.config),d.FIXED)
        for key,val in (('workers',3),('before_rounds',6),('kd',0),('historical_endpoint_used_as_founder',True)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{key:val}))

    def test_03_manifest_and_inputs(self):
        self.assertEqual(len(d.LOCAL_FILES),91); self.assertEqual(len(d.execution_manifest()),127)
        self.assertEqual(len(d.input_paths()),1675)
        self.assertTrue(all(self.report['integrity'].values()))

    def test_04_full_independent_audit(self):
        self.assertTrue(self.report['quality_gate'])
        self.assertEqual(self.report['completed_cases'],74)
        self.assertEqual(self.report['integration_calls'],434)
        self.assertEqual(self.report['control_qualified_editable_lineages'],2)

    def test_05_all_finer_comparisons(self):
        self.assertEqual(len(self.report['fine_comparisons']),37)
        self.assertTrue(self.report['all_fine_agree'])

    def test_06_all_stage_gates(self):
        self.assertTrue(all(v['quality_gate'] and v['eligible'] for v in self.report['stages'].values()))

    def test_07_fresh_initial_witness(self):
        old=a.arrays(self.fixture_run/'inputs'/a.SEED,'preparation')
        for fine in (False,True):
            now=a.arrays(self.fixture_run/d.case('stock',fine=fine)['id'],'preparation')
            self.assertTrue(np.array_equal(now['initial'],old['initial']))
            self.assertFalse(np.array_equal(now['final'],old['final']))
            self.assertEqual(now['times'].tolist(),list(range(0,1001,100)))

    def test_08_fine_uses_its_own_stock(self):
        c=d.case('write_M','M_open',fine=True); x=a.arrays(self.fixture_run/c['id'],'writing_contact')['initial']
        E,M=a.stock(self.fixture_run,True); oldE,oldM=a.stock(self.fixture_run,False)
        self.assertTrue(np.array_equal(x[:,:6],np.repeat(M,6,axis=1)))
        self.assertTrue(np.array_equal(x[:,6:],np.repeat(E,3,axis=1)))
        self.assertFalse(np.array_equal(M,oldM)); self.assertFalse(np.array_equal(E,oldE))

    def test_09_all_source_bindings(self):
        for c in d.fixed_cases():
            if c['kind']=='stock': continue
            src,phase=a.source_spec(c)
            self.assertEqual((d.source_case(c),d.source_phase(c)),(src['id'],phase))

    def test_10_new_written_founder(self):
        c=d.case('before',history='written',route='open')
        x=a.arrays(self.fixture_run/c['id'],'r01_segment_01')['initial'][:,:3]
        y=a.arrays(self.fixture_run/d.case('write_M','M_open')['id'],'writing_isolated_2')['final']
        self.assertTrue(np.array_equal(x,y))

    def test_11_rewrite_actual_third_round(self):
        c=d.case('rewrite_E','E_open','written')
        x=a.arrays(self.fixture_run/c['id'],'writing_contact')['initial'][:,6:]
        y=a.arrays(self.fixture_run/d.case('before',history='written',route='open')['id'],'r03_isolated_2')['final']
        self.assertTrue(np.array_equal(x,y))

    def test_12_post_rewrite_actual_carriers(self):
        c=self.primary
        x=a.arrays(self.fixture_run/c['id'],'r04_segment_01')['initial'][:,:3]
        y=a.arrays(self.fixture_run/d.case('rewrite_E','E_open','written')['id'],'writing_isolated_2')['final']
        self.assertTrue(np.array_equal(x,y))

    def test_13_after_recipients_really_start_M(self):
        for n in range(4,7):
            x=a.arrays(self.fixture_run/self.primary['id'],f'r{n:02d}_segment_01')['initial']
            self.assertEqual(''.join(a.labels(x,a.INDEX)[3:]),'MMM')

    def test_14_three_rounds_on_each_side(self):
        for h in d.HISTORIES:
            for fine in (False,True):
                before=self.by[d.case('before',history=h,fine=fine,route='open')['id']]
                after=self.by[d.case('after','E_open',h,fine,'open')['id']]
                self.assertEqual([r['round'] for r in before['rounds']],[1,2,3])
                self.assertEqual([r['round'] for r in after['rounds']],[4,5,6])
                self.assertEqual(after['rounds'][-1]['logical_end'],680000)

    def test_15_all_teachers_replaced(self):
        c=self.primary; result=next(x['result'] for x in self.summary['cases'] if x['id']==c['id'])
        for n in range(4,7):
            start=next(p for p in result['phases'] if p['phase']==f'r{n:02d}_segment_01')['setup']['cell_ids']
            hold=next(p for p in result['phases'] if p['phase']==f'r{n:02d}_isolated_1')['setup']['cell_ids']
            self.assertEqual(hold,start[3:]); self.assertTrue(set(hold).isdisjoint(start[:3]))

    def test_16_before_blocks_negative(self):
        for c in d.stage_cases('before'):
            if c['route']!='open': self.assertTrue(self.by[c['id']]['outcomes']['first_round_negative'])

    def test_17_rewrite_blocks_preserve_M(self):
        for c in d.stage_cases('rewrite'):
            if c['condition']!='E_open': self.assertTrue(self.by[c['id']]['outcomes']['all_M'])

    def test_18_after_blocks_distinct_from_write_blocks(self):
        for c in d.stage_cases('after'):
            if c['route'] in ('rna','cut'):
                self.assertEqual(d.source_case(c),d.case('rewrite_E','E_open',c['history'],c['fine'])['id'])
                self.assertTrue(self.by[c['id']]['outcomes']['first_round_negative'])

    def test_19_after_sham_controls_not_E_inheritance(self):
        for c in d.stage_cases('after'):
            if c['condition']!='E_open':
                self.assertFalse(self.by[c['id']]['outcomes']['complete_all'])
                self.assertTrue(self.by[c['id']]['outcomes']['first_round_negative'])

    def test_20_same_clock_for_waiting_cells(self):
        x=a.arrays(self.fixture_run/self.primary['id'],'r04_segment_01')
        self.assertFalse(np.array_equal(x['initial'][:,5],x['final'][:,5]))
        self.assertEqual(x['times'][-1],20000)

    def mutate(self,edit,c=None):
        c=c or self.primary
        with tempfile.TemporaryDirectory(prefix='mutation-',dir=self.fixture_run) as temp:
            folder=Path(temp); shutil.copytree(self.fixture_run/c['id'],folder,dirs_exist_ok=True)
            result=json.loads((folder/'result.json').read_text()); edit(folder,result)
            d.write_json(folder/'result.json',result); checks=a.Checks()
            a.branch(folder,c,checks)
            return checks.rows

    def array_edit(self,phase,key,change):
        def edit(folder,result):
            data=a.arrays(folder,phase); change(data[key]); np.savez_compressed(folder/(phase+'.npz'),**data)
            next(p for p in result['phases'] if p['phase']==phase)['sha256']=d.digest(folder/(phase+'.npz'))
        return edit

    def test_21_rehashed_teacher_reset_rejected(self):
        rows=self.mutate(self.array_edit('r04_segment_01','initial',lambda x:x.__setitem__((0,0),x[0,0]+.01)))
        self.assertFalse(rows[self.primary['id']+'/r04_actual_teachers'])

    def test_22_rehashed_waiting_reset_rejected(self):
        rows=self.mutate(self.array_edit('r04_segment_02','initial',lambda x:x.__setitem__((0,5),x[0,5]+.01)))
        self.assertFalse(rows[self.primary['id']+'/r04_segment_02/all_six_continuous'])

    def test_23_rehashed_live_pupil_selection_rejected(self):
        rows=self.mutate(self.array_edit('r04_isolated_1','initial',lambda x:x.__setitem__((0,1),x[0,1]+.01)))
        self.assertFalse(rows[self.primary['id']+'/r04_remove_every_teacher'])

    def test_24_rehashed_cue_withdrawal_reset_rejected(self):
        c=d.case('rewrite_E','E_open','written')
        rows=self.mutate(self.array_edit('writing_isolated_1','initial',lambda x:x.__setitem__((0,1),x[0,1]+.01)),c)
        self.assertFalse(rows[c['id']+'/remove_all_cues'])

    def test_25_rehashed_wrong_initial_recipient_rejected(self):
        rows=self.mutate(self.array_edit('r04_segment_01','initial',lambda x:x.__setitem__((5,slice(3,None)),1000)))
        self.assertFalse(rows[self.primary['id']+'/r04_fresh_opposite_recipients'])
        self.assertFalse(rows[self.primary['id']+'/r04_recipient_start_labels'])

    def test_26_changed_source_binding_rejected(self):
        rows=self.mutate(lambda folder,result:result.update(source_case='historical_endpoint'))
        self.assertFalse(rows[self.primary['id']+'/source_binding'])

    def test_27_clock_overshoot_rejected(self):
        rows=self.mutate(self.array_edit('r04_isolated_1','clock_step_ticks',lambda x:x.__setitem__(-1,int(x[-1])+1)))
        self.assertFalse(rows[self.primary['id']+'/r04_isolated_1/clock/exact_final_tick'])

    def test_28_clock_boundary_not_only_endpoint(self):
        def change(x): x[0]+=1; x[1]-=1
        rows=self.mutate(self.array_edit('r04_segment_01','clock_step_ticks',change))
        self.assertFalse(rows[self.primary['id']+'/r04_segment_01/clock/exact_step_clipping'])

    def test_29_wrong_graph_rejected(self):
        rows=self.mutate(self.array_edit('r04_segment_01','edge_to',lambda x:x.__setitem__(-1,4)))
        self.assertFalse(rows[self.primary['id']+'/r04_segment_01/topology'])

    def test_30_wrong_cell_identity_rejected(self):
        def edit(folder,result): result['phases'][0]['setup']['cell_ids'][0]='cue_left_behind'
        rows=self.mutate(edit)
        self.assertFalse(rows[self.primary['id']+'/r04_segment_01/ids'])

    def test_31_clock_stock_correction_not_skipped(self):
        c=d.case('stock')
        rows=self.mutate(self.array_edit('preparation','times',lambda x:x.__setitem__(-1,10000000)),c)
        self.assertFalse(rows[c['id']+'/preparation/clock/observations'])

    def test_32_fresh_initialization_witness_rejected_if_changed(self):
        c=d.case('stock')
        rows=self.mutate(self.array_edit('preparation','initial',lambda x:x.__setitem__((0,0),0)),c)
        self.assertFalse(rows[c['id']+'/fresh_native_initialization'])

    def test_33_both_holds_required(self):
        def change(x):
            x[-2:,5,:]=0; x[-2:,6,:]=1000
        rows=self.mutate(self.array_edit('r04_isolated_1','concentrations',change))
        self.assertFalse(rows[self.primary['id']+'/round_records'])

    def test_34_recorded_success_not_trusted(self):
        def edit(folder,result): result['rounds'][0]['retained']=[False]*3
        self.assertFalse(self.mutate(edit)[self.primary['id']+'/round_records'])

    def test_35_future_rounds_not_fabricated(self):
        def edit(folder,result): result['rounds'][0]['round']=9
        self.assertFalse(self.mutate(edit)[self.primary['id']+'/round_records'])

    def test_36_partial_failure_stops_after_complete_round(self):
        c=d.case('before',history='written',route='open')
        with tempfile.TemporaryDirectory(prefix='partial-',dir=self.fixture_run) as temp,redirect_stdout(io.StringIO()):
            row=fixture_case(self.fixture_run,c,folder_override=Path(temp),partial=True)
            checks=a.Checks(); report,data,idx=a.branch(Path(temp),c,checks)
        self.assertTrue(all(checks.rows.values()))
        self.assertEqual(len(data),6); self.assertEqual(len(report['rounds']),1)
        self.assertEqual(report['rounds'][0]['retained'],[True,True,False])
        self.assertFalse(report['outcomes']['complete_all'])

    def test_37_qualifying_controls_are_required(self):
        by={k:copy.deepcopy(v['outcomes']) for k,v in self.by.items()}
        for stage in ('calibration','before','rewrite','after'):
            c=next(c for c in a.expected_stage(stage) if c['condition'].endswith('_rna') or c['route']=='rna')
            bad=copy.deepcopy(by); bad[c['id']]={}
            self.assertFalse(all(x['qualified'] for x in a.eligibility(stage,bad)))

    def test_38_wrong_manifest_origin_rejected(self):
        summary=copy.deepcopy(self.summary); key=next(iter(summary['inputs']))
        summary['inputs'][key]['source']=str(d.PREDECESSOR/'independent_audit.json')
        self.assertFalse(a.integrity(self.fixture_run,summary)['input_origins'])
        summary['inputs'][key]['source']='/tmp/not-the-registered-source'
        self.assertFalse(all(a.integrity(self.fixture_run,summary).values()))

    def test_39_missing_case_is_not_valid(self):
        checks=a.Checks()
        with patch.object(a,'branch',side_effect=AssertionError('Must not audit a missing case')):
            c=dict(self.primary,id='missing-case')
            reports,_,_=a.audited_records(self.fixture_run,[c],checks)
        self.assertEqual(reports,[]); self.assertFalse(checks.rows['missing-case/record'])

    def flow(self,stop=None,technical=False,execution=False):
        with tempfile.TemporaryDirectory(prefix='p11-flow-') as temp,redirect_stdout(io.StringIO()):
            output=Path(temp)/'output'; output.mkdir(); calls=[]
            def worker(c,config,run,deadline,env):
                calls.append(c); return dict(id=c['id'],execution_pass=not execution)
            def audit(run,stage):
                return dict(quality_gate=not (technical and stage==stop),eligible=stage!=stop)
            with patch.object(r.tempfile,'mkdtemp',return_value=str(output)),patch.object(r,'freeze',return_value=({}, {}, {})),\
                 patch.object(r,'predecessor_audit',return_value=self.history),patch.object(r,'run_worker',side_effect=worker),\
                 patch.object(a,'stage_audit',side_effect=audit),patch.object(a,'integrity',return_value={'fixture':True}),\
                 patch.object(d,'source_check'):
                code=r.run(d.ROOT/'configs/paper_editable_lineage_v1.json')
            return code,calls,json.loads((output/'summary.json').read_text())

    def test_40_valid_stock_negative_stops(self):
        code,calls,summary=self.flow('stocks'); self.assertEqual((code,len(calls)),(0,2))
        self.assertEqual(summary['completion_reason'],'stocks_not_qualified')

    def test_41_valid_calibration_negative_stops(self):
        code,calls,_=self.flow('calibration'); self.assertEqual((code,len(calls)),(0,22))

    def test_42_valid_pre_lineage_negative_stops(self):
        code,calls,_=self.flow('before'); self.assertEqual((code,len(calls)),(0,34))

    def test_43_valid_rewriting_negative_stops(self):
        code,calls,_=self.flow('rewrite'); self.assertEqual((code,len(calls)),(0,54))

    def test_44_valid_negative_after_is_reported(self):
        code,calls,summary=self.flow('after'); self.assertEqual((code,len(calls)),(0,74))
        self.assertEqual(summary['completion_reason'],'after_completed')

    def test_45_technical_failure_not_biological_negative(self):
        code,calls,summary=self.flow('calibration',technical=True)
        self.assertEqual((code,len(calls)),(1,22)); self.assertFalse(summary['all_execution_valid'])

    def test_46_execution_failure_stops(self):
        code,calls,_=self.flow(execution=True); self.assertEqual((code,len(calls)),(1,2))

    def test_47_fine_forks_never_coarse_prefixes(self):
        for c in d.fixed_cases():
            if c['fine'] and c['kind']!='stock': self.assertTrue(d.source_case(c).endswith('__fine'))

    def test_48_no_history_advantage_or_autonomy_claim(self):
        self.assertFalse(self.report['historical_endpoint_used_as_founder'])
        self.assertFalse(self.report['unique_PH_demonstrated'])
        self.assertFalse(self.report['autonomous_reproduction'])
        self.assertFalse(self.report['independent_random_replicates'])

    def supervisor_fixture(self,runner_rc=0,audit_quality=True,bad_input=False,verification_rc=0,negative=False):
        with tempfile.TemporaryDirectory(prefix='p11-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-editable-lineage-test'; job.mkdir(parents=True)
            run=root/'runs/paper-editable-lineage-test'; run.mkdir()
            source=root/'source'; source.write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={str(source):'wrong' if bad_input else d.digest(source)}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time()))
            (job/'runner.log').write_text('Run artifacts: '+str(run)+'\n')
            d.write_json(run/'summary.json',dict(cases=[],registered_cases=[],predecessor_gate=True,
                gates={'stocks':dict(quality_gate=True,eligible=not negative)},stage='finished',
                completion_reason='stocks_not_qualified' if negative else 'after_completed'))
            d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,independent_check_count=1,
                all_fine_agree=True,editable_lineages=[]))
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

    def test_49_supervisor_success_stops_after_audit(self):
        code,meta,called=self.supervisor_fixture(); self.assertEqual(code,0)
        self.assertEqual(meta['phase'],'complete'); self.assertEqual(called,['verification.log','runner.log','audit.log'])

    def test_50_supervisor_runner_timeout_no_retry(self):
        code,meta,called=self.supervisor_fixture(runner_rc=124); self.assertEqual(code,1)
        self.assertEqual(meta['phase'],'failed'); self.assertEqual(called,['verification.log','runner.log'])

    def test_51_supervisor_audit_failure(self):
        code,meta,called=self.supervisor_fixture(audit_quality=False); self.assertEqual(code,1)
        self.assertEqual(meta['phase'],'failed'); self.assertEqual(called,['verification.log','runner.log','audit.log'])

    def test_52_supervisor_changed_input_stops(self):
        code,meta,called=self.supervisor_fixture(bad_input=True); self.assertEqual(code,1)
        self.assertEqual(called,[]); self.assertIn('inputs changed',meta['error'])

    def test_53_verification_failure_prevents_simulation(self):
        code,meta,called=self.supervisor_fixture(verification_rc=1); self.assertEqual(code,1)
        self.assertEqual(called,['verification.log']); self.assertIn('no biological runner launch',meta['error'])

    def test_54_verification_timeout_prevents_simulation(self):
        code,meta,called=self.supervisor_fixture(verification_rc=124); self.assertEqual(code,1)
        self.assertEqual(called,['verification.log']); self.assertEqual(meta['phase'],'failed')

    def test_55_negative_result_is_complete_not_supervisor_failure(self):
        code,meta,called=self.supervisor_fixture(negative=True); self.assertEqual(code,0)
        self.assertEqual(meta['completion_reason'],'stocks_not_qualified')
        self.assertEqual(meta['planned_cases'],0); self.assertTrue(meta['ready_for_interpretation'])
        self.assertEqual(called,['verification.log','runner.log','audit.log'])

    def test_56_stale_heartbeat_does_not_relaunch(self):
        with tempfile.TemporaryDirectory(prefix='p11-status-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='before',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale'])

    def test_57_discover_rejects_unrelated_output(self):
        with tempfile.TemporaryDirectory(prefix='p11-path-') as temp:
            job=Path(temp); (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)

    def worker_rejection(self,case,stage,gate=None):
        with tempfile.TemporaryDirectory(prefix='p11-worker-') as temp:
            run=Path(temp); folder=run/'case'; folder.mkdir()
            d.write_json(folder/'spec.json',dict(case=case,config=self.config,inputs=str(run/'inputs')))
            d.write_json(run/'summary.json',dict(stage=stage,gates={'stocks':gate or {}},gate_hashes={}))
            with patch.object(r,'ClockBoundedExperiment') as exp:
                with self.assertRaises(ValueError): r.worker(folder/'spec.json')
                exp.assert_not_called()

    def test_58_unregistered_worker_rejected(self):
        self.worker_rejection(dict(self.primary,id='unregistered'),'after')

    def test_59_wrong_stage_worker_rejected(self):
        self.worker_rejection(self.primary,'calibration')

    def test_60_negative_gate_blocks_worker(self):
        self.worker_rejection(d.case('write_M','M_open'),'calibration',dict(quality_gate=True,eligible=False))

    def negative_full_audit(self,stop):
        with tempfile.TemporaryDirectory(prefix='p11-negative-') as temp,redirect_stdout(io.StringIO()):
            run=Path(temp); hashes,frozen,inputs=r.freeze(run)
            d.write_json(run/'predecessor_audit.json',self.history)
            stages=list(d.STAGES[:d.STAGES.index(stop)+1])
            summary=dict(revision=d.REVISION,config=self.config,registered_cases=d.fixed_cases(),cases=[],
                hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
                predecessor_audit=self.history,predecessor_audit_sha256=d.digest(run/'predecessor_audit.json'),
                gates={},gate_hashes={},attempted_stages=stages)
            for stage in stages:
                for c in d.stage_cases(stage):
                    summary['cases'].append(fixture_case(run,c,failure=stop if stage==stop else None))
                    d.write_json(run/'summary.json',summary)
                gate=a.stage_audit(run,stage)
                self.assertTrue(gate['quality_gate']); self.assertEqual(gate['eligible'],stage!=stop)
                d.write_json(run/(stage+'_audit.json'),gate)
                summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(run/(stage+'_audit.json'))
                d.write_json(run/'summary.json',summary)
            summary.update(all_execution_valid=True,stage='finished',completion_reason=
                           'after_completed' if stop=='after' else stop+'_not_qualified')
            d.write_json(run/'summary.json',summary)
            with patch.object(a,'predecessor_audit',return_value=self.history): report=a.analyze(run)
            self.assertTrue(report['quality_gate'],[k for k,v in report['checks'].items() if not v])
            self.assertEqual(report['completed_cases'],len(a.expected_cases(stop)))
            self.assertFalse(report['stages'][stop]['eligible'])
            self.assertEqual(report['control_qualified_editable_lineages'],0)

    def test_61_negative_stock_full_audit(self): self.negative_full_audit('stocks')
    def test_62_negative_calibration_full_audit(self): self.negative_full_audit('calibration')
    def test_63_negative_before_full_audit(self): self.negative_full_audit('before')
    def test_64_negative_rewrite_full_audit(self): self.negative_full_audit('rewrite')
    def test_65_negative_after_full_audit(self): self.negative_full_audit('after')


if __name__=='__main__': unittest.main()
