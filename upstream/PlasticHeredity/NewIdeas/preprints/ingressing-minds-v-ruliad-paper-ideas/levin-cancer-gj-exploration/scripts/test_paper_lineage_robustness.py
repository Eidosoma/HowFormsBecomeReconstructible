"""P12 software fixtures: fabricated transitions, never biological evidence."""
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
import paper_lineage_robustness_design as d
import run_paper_lineage_robustness as r
import analyze_paper_lineage_robustness as a
import run_paper_lineage_robustness_detached as detached

def fixture_case(run,c,selection,folder_override=None,failure=None):
    folder=folder_override or run/c['id']; folder.mkdir(exist_ok=True)
    exp=r.ClockBoundedExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original_phase=exp.phase
    def wrapper(name,horizon,**kwargs):
        current['name']=name
        return original_phase(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy()
        if c['stage']=='baseline':
            oldcase=('before__ordinary__open' if c['label']=='M' else 'after__ordinary__E_open__open')+('__fine' if c['fine'] else '')
            oldname=name.replace('r01_','r01_' if c['label']=='M' else 'r04_')
            path=run/'inputs/p11'/oldcase; data=a.arrays(path,oldname)
            rec=next(p for p in json.loads((path/'result.json').read_text())['phases'] if p['phase']==oldname)
            sim.cc_cells[:]=data['final']
            return data['times'],data['concentrations'],{k:data[k] for k in (
                'clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},rec['clock']
        def mark(indices,label):
            setter=exp.z.GRN.set_very_healthy if label=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        if name=='founder_contact' and c['stage']=='combined':
            if failure=='founder': mark(range(len(exp.ids)-3,len(exp.ids)),'E')
            elif c['history']=='written': mark(range(6,9),'M')
        if name=='rewrite_contact' and c['stage']=='combined' and failure!='rewrite': mark(range(6,9),'E')
        if '_segment_' in name:
            n=int(name[1:3]); desired=c['label'] if c['stage'] in ('timing','cells') else 'M' if n<4 else 'E'
            opposite='E' if desired=='M' else 'M'
            if exp.route=='open' or failure=='positive_control':
                mark([3+i for i in exp.active],desired)
                bad=(failure=='partial' or failure=='screen_all' or
                     (failure=='screen_strong' and c['level']=='strong') or
                     (failure=='before' and n==2) or (failure=='after' and n==5))
                if bad and 2 in exp.active: mark([5],opposite)
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.00001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=np.full(total//cap,cap,dtype=np.int64); proposed=np.full(len(steps),2*stride,dtype=np.int64)
        shots=np.arange(0,total+1,stride,dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(steps),sample_count=len(shots),capped_steps=len(steps),
            initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=wrapper),patch.object(r.clock,'integrate',side_effect=fake_clock):
        outcome=r.trajectory(exp,c,run,selection)
    result=r.result_record(exp,c,outcome,selection); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestLineageRobustness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p12-software-'); cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        cls.config=json.loads((d.ROOT/'configs/paper_lineage_robustness_v1.json').read_text())
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        # Historical raw inputs are real and fully hash-checked. The expensive original/
        # archived P11 re-audit is tested by routing fixtures here and runs for real at preflight.
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_matches_saved=True,
            prior_checks=27610,prior_cases=74,prior_calls=434,shared_stock_and_replay_sources=True)
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=cls.config,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
            predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),
            gates={},gate_hashes={},selection={},attempted_stages=list(d.STAGES))
        with redirect_stdout(io.StringIO()):
            for stage in d.STAGES:
                for c in d.stage_cases(stage):
                    cls.summary['cases'].append(fixture_case(cls.fixture_run,c,cls.summary['selection']))
                    d.write_json(cls.fixture_run/'summary.json',cls.summary)
                gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                if not gate['eligible']: raise AssertionError('Synthetic positive stage did not qualify: '+stage)
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate)
                cls.summary['gates'][stage]=gate; cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
                if stage in ('timing','cells'): cls.summary['selection'][stage]=gate['selected']
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
        cls.summary.update(all_execution_valid=True,completion_reason='combined_and_controls_completed',stage='finished')
        d.write_json(cls.fixture_run/'summary.json',cls.summary)
        with patch.object(a,'predecessor_audit',return_value=cls.history): cls.report=a.analyze(cls.fixture_run)
        cls.by={b['case']['id']:b['outcome'] for b in cls.report['stages']['controls']['branches']}
        cls.primary=d.case('combined',seed=201,history='written')
        cls.selection={'timing':'strong','cells':'strong'}

    def test_01_registration(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases())
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[4,32,32,12,78])
        self.assertEqual(len(d.fixed_cases()),158)

    def test_02_config_and_draw_registration(self):
        self.assertEqual(d.validate_config(self.config),d.FIXED)
        self.assertEqual(d.draw_book(),a.expected_draws())
        self.assertEqual(json.loads((d.ROOT/'configs/paper_lineage_robustness_draws_v1.json').read_text()),a.expected_draws())
        for key,value in (('workers',3),('maximum_cases',159),('protein_index',5)):
            with self.assertRaises(ValueError): d.validate_config(dict(self.config,**{key:value}))

    def test_03_manifest(self):
        self.assertEqual(len(d.LOCAL_FILES),99); self.assertEqual(len(d.execution_manifest()),135)
        self.assertEqual(len(d.input_paths()),2282)
        self.assertTrue(all(self.report['integrity'].values()))

    def test_04_full_audit(self):
        self.assertTrue(self.report['quality_gate'],[k for k,v in self.report['checks'].items() if not v])
        self.assertEqual(self.report['completed_cases'],158)
        self.assertLessEqual(self.report['integration_calls'],1746)
        self.assertEqual(len(self.report['fine_comparisons']),79)
        self.assertTrue(self.report['all_fine_agree'])

    def test_05_trial_denominators(self):
        self.assertEqual(len(self.report['trials']),6)
        self.assertEqual([r['challenge_trials'] for r in self.report['trial_counts']],[3,3])
        self.assertEqual([r['control_qualified_successes'] for r in self.report['trial_counts']],[3,3])
        self.assertFalse(self.report['independent_biological_replicates'])

    def test_06_schedules_independent_oracle(self):
        for seed in (0,101,102,201,202,203):
            for n in range(1,7):
                for level in (None,'mild','strong'):
                    x=d.intervals(seed,n,level)
                    self.assertEqual(x,a.schedule(seed,n,level))
                    self.assertEqual(sum(b-a for a,b,_ in x),80000)
                    self.assertEqual([sum(b-a for a,b,active in x if i in active) for i in range(3)],[20000]*3)
                    self.assertTrue(all(b>a and a%100==b%100==0 for a,b,_ in x))

    def test_07_exact_zero_stress_schedule(self):
        self.assertEqual(d.intervals(201,1,None),[(0,20000,[0]),(20000,40000,[1]),(40000,60000,[2]),(60000,80000,[])])

    def test_08_only_ZEB_protein_changes(self):
        E,M=r.stock(self.fixture_run,False)
        for stock in (E,M):
            for seed in d.SCREEN_SEEDS+d.TEST_SEEDS:
                for level in (None,'mild','strong'):
                    x=d.recipient(stock,seed,'r01',level)
                    self.assertTrue(np.array_equal(x,a.incoming(stock,seed,'r01',level)))
                    keep=[i for i in range(17) if i!=7]
                    self.assertTrue(np.array_equal(x[keep],np.repeat(stock,3,axis=1)[keep]))
                    self.assertEqual(''.join(a.labels(x,a.INDEX)),str(a.labels(stock,a.INDEX)[0])*3)
                    self.assertTrue(np.isfinite(x).all() and (x>=0).all())

    def test_09_held_out_seeds(self):
        self.assertTrue(set(d.SCREEN_SEEDS).isdisjoint(d.TEST_SEEDS))
        self.assertEqual({c['seed'] for c in d.stage_cases('combined')},{201,202,203})

    def test_10_exact_archived_baseline(self):
        checks=self.report['stages']['baseline']['checks']
        exact=[v for k,v in checks.items() if k.endswith('/exact_replay')]
        self.assertEqual(len(exact),24); self.assertTrue(all(exact))

    def test_11_founder_written_anew(self):
        c=self.primary; x=a.arrays(self.fixture_run/c['id'],'founder_contact')['initial']
        E,M=a.stock(self.fixture_run,False)
        self.assertTrue(np.array_equal(x[:,6:],a.incoming(E,201,'founder','strong')))
        self.assertEqual(''.join(a.labels(x[:,6:],a.INDEX)),'EEE')

    def test_12_all_actual_third_round_carriers_rewritten(self):
        folder=self.fixture_run/self.primary['id']
        self.assertTrue(np.array_equal(a.arrays(folder,'rewrite_contact')['initial'][:,6:],
                                       a.arrays(folder,'r03_isolated_2')['final']))

    def test_13_post_rewrite_actual_source(self):
        folder=self.fixture_run/self.primary['id']
        self.assertTrue(np.array_equal(a.arrays(folder,'r04_segment_01')['initial'][:,:3],
                                       a.arrays(folder,'rewrite_isolated_2')['final']))
        self.assertEqual(''.join(a.labels(a.arrays(folder,'r04_segment_01')['initial'][:,3:],a.INDEX)),'MMM')

    def test_14_six_complete_handovers(self):
        out=self.by[self.primary['id']]
        self.assertEqual([r['round'] for r in out['rounds']],list(range(1,7)))
        self.assertEqual(out['rounds'][-1]['logical_end'],680000)
        self.assertTrue(out['complete'])

    def test_15_matched_control_challenges(self):
        for route,n,source in (('before_rna',1,'founder_isolated_2'),('after_cut',4,'rewrite_isolated_2')):
            c=d.case('controls',seed=201,history='written',route=route)
            x=a.arrays(self.fixture_run/c['id'],f'r{n:02d}_segment_01')['initial']
            y=a.arrays(self.fixture_run/self.primary['id'],f'r{n:02d}_segment_01')['initial']
            self.assertTrue(np.array_equal(x,y))
            self.assertTrue(np.array_equal(x[:,:3],a.arrays(self.fixture_run/self.primary['id'],source)['final']))

    def test_16_shams_use_actual_current_carriers(self):
        for route in ('rewrite_sham','rewrite_none'):
            c=d.case('controls',seed=201,history='written',route=route)
            x=a.arrays(self.fixture_run/c['id'],'rewrite_contact')['initial']
            targets=x[:,6:] if route=='rewrite_sham' else x
            self.assertTrue(np.array_equal(targets,a.arrays(self.fixture_run/self.primary['id'],'r03_isolated_2')['final']))
            self.assertTrue(self.by[c['id']]['negative'])

    def test_17_founder_no_cue_same_varied_targets(self):
        c=d.case('controls',seed=201,history='written',route='founder_none')
        x=a.arrays(self.fixture_run/c['id'],'founder_contact')['initial']
        y=a.arrays(self.fixture_run/self.primary['id'],'founder_contact')['initial'][:,6:]
        self.assertTrue(np.array_equal(x,y)); self.assertTrue(self.by[c['id']]['negative'])

    def test_18_fine_own_states(self):
        c=d.case('combined',seed=201,history='written',fine=True)
        x=a.arrays(self.fixture_run/c['id'],'founder_contact')['initial']
        E,M=a.stock(self.fixture_run,True)
        self.assertTrue(np.array_equal(x[:,:6],np.repeat(M,6,axis=1)))
        self.assertTrue(np.array_equal(x[:,6:],a.incoming(E,201,'founder','strong')))

    def test_19_all_prior_files_unchanged(self):
        self.assertTrue(all(p11_integrity() for _ in range(1)))

    def mutate(self,edit,c=None):
        c=c or self.primary
        with tempfile.TemporaryDirectory(prefix='mutation-',dir=self.fixture_run) as temp:
            folder=Path(temp); shutil.copytree(self.fixture_run/c['id'],folder,dirs_exist_ok=True)
            result=json.loads((folder/'result.json').read_text()); edit(folder,result)
            d.write_json(folder/'result.json',result); checks=a.Checks()
            a.branch(folder,c,self.selection,checks)
            return checks.rows

    def array_edit(self,phase,key,change):
        def edit(folder,result):
            data=a.arrays(folder,phase); change(data[key]); np.savez_compressed(folder/(phase+'.npz'),**data)
            next(p for p in result['phases'] if p['phase']==phase)['sha256']=d.digest(folder/(phase+'.npz'))
        return edit

    def test_20_rehashed_founder_reset_rejected(self):
        rows=self.mutate(self.array_edit('r01_segment_01','initial',lambda x:x.__setitem__((0,0),x[0,0]+.1)))
        self.assertFalse(rows[self.primary['id']+'/r01_segment_01/actual_initial'])

    def test_21_rehashed_waiting_reset_rejected(self):
        rows=self.mutate(self.array_edit('r01_segment_02','initial',lambda x:x.__setitem__((0,5),x[0,5]+.1)))
        self.assertFalse(rows[self.primary['id']+'/r01_segment_02/actual_initial'])

    def test_22_wrong_protein_draw_rejected(self):
        rows=self.mutate(self.array_edit('r04_segment_01','initial',lambda x:x.__setitem__((7,3),x[7,3]+.1)))
        self.assertFalse(rows[self.primary['id']+'/r04_segment_01/actual_initial'])

    def test_23_hidden_ion_jitter_rejected(self):
        rows=self.mutate(self.array_edit('founder_contact','initial',lambda x:x.__setitem__((1,6),x[1,6]+.1)))
        self.assertFalse(rows[self.primary['id']+'/founder_contact/actual_initial'])

    def test_24_retained_teacher_rejected(self):
        rows=self.mutate(self.array_edit('r01_isolated_1','initial',lambda x:x.__setitem__((0,0),x[0,0]+.1)))
        self.assertFalse(rows[self.primary['id']+'/r01_isolated_1/actual_initial'])

    def test_25_retained_cue_rejected(self):
        rows=self.mutate(self.array_edit('rewrite_isolated_1','initial',lambda x:x.__setitem__((0,0),x[0,0]+.1)))
        self.assertFalse(rows[self.primary['id']+'/rewrite_isolated_1/actual_initial'])

    def test_26_clock_overshoot_rejected(self):
        rows=self.mutate(self.array_edit('r01_isolated_1','clock_step_ticks',lambda x:x.__setitem__(-1,int(x[-1])+1)))
        self.assertFalse(rows[self.primary['id']+'/r01_isolated_1/clock/exact_final_tick'])

    def test_27_wrong_mask_rejected(self):
        def edit(folder,result): result['phases'][3]['setup']['scheduled_pupils']=[2,1,0]
        self.assertFalse(all(self.mutate(edit).values()))

    def test_28_wrong_identity_rejected(self):
        def edit(folder,result): result['phases'][0]['setup']['cell_ids'][-1]='substitute_cell'
        self.assertFalse(self.mutate(edit)[self.primary['id']+'/founder_contact/ids'])

    def test_29_reported_success_not_trusted(self):
        def edit(folder,result): result['outcome']['complete']=False
        self.assertFalse(self.mutate(edit)[self.primary['id']+'/independent_outcome'])

    def test_30_selection_not_replaced(self):
        def edit(folder,result): result['selection']['timing']='mild'
        self.assertFalse(self.mutate(edit)[self.primary['id']+'/selection'])

    def test_31_unregistered_extra_phase_rejected(self):
        def edit(folder,result): result['phases'].append(copy.deepcopy(result['phases'][-1]))
        self.assertFalse(self.mutate(edit)[self.primary['id']+'/no_extra_phases'])

    def partial(self,failure):
        with tempfile.TemporaryDirectory(prefix='partial-',dir=self.fixture_run) as temp,redirect_stdout(io.StringIO()):
            row=fixture_case(self.fixture_run,self.primary,self.selection,Path(temp),failure)
            checks=a.Checks(); report,_=a.branch(Path(temp),self.primary,self.selection,checks)
            self.assertTrue(all(checks.rows.values()),[k for k,v in checks.rows.items() if not v])
            return report['outcome'],len(row['result']['phases'])

    def test_32_failed_founder_stops(self):
        out,calls=self.partial('founder'); self.assertEqual(calls,3)
        self.assertEqual(out['stop_reason'],'founder_not_M')

    def test_33_failed_before_round_stops(self):
        out,_=self.partial('before'); self.assertEqual(len(out['rounds']),2)
        self.assertEqual(out['stop_reason'],'before_round_2_incomplete'); self.assertIsNone(out['rewrite'])

    def test_34_failed_rewrite_stops(self):
        out,_=self.partial('rewrite'); self.assertEqual(len(out['rounds']),3)
        self.assertEqual(out['stop_reason'],'rewrite_not_E')

    def test_35_failed_after_round_stops(self):
        out,_=self.partial('after'); self.assertEqual(len(out['rounds']),5)
        self.assertEqual(out['stop_reason'],'after_round_5_incomplete')

    def test_36_selection_rule_strong_then_mild_then_none(self):
        for mode in ('timing','cells'):
            by=copy.deepcopy(self.by); self.assertEqual(a.selection_from_outcomes(mode,by)[0],'strong')
            for c in a.expected_stage(mode):
                if c['level']=='strong' and c['route']=='open': by[c['id']]['complete']=False
            self.assertEqual(a.selection_from_outcomes(mode,by)[0],'mild')
            for c in a.expected_stage(mode):
                if c['route']=='open': by[c['id']]['complete']=False
            self.assertIsNone(a.selection_from_outcomes(mode,by)[0])

    def test_37_controls_needed_for_selection(self):
        for mode in ('timing','cells'):
            by=copy.deepcopy(self.by)
            for c in a.expected_stage(mode):
                if c['route']=='rna': by[c['id']]['negative']=False
            self.assertIsNone(a.selection_from_outcomes(mode,by)[0])

    def test_38_failed_trial_stays_in_denominator(self):
        by=copy.deepcopy(self.by); by[self.primary['id']]['complete']=False
        trials,counts=a.trial_counts(by)
        self.assertEqual(counts[0]['challenge_trials'],3)
        self.assertEqual(counts[0]['control_qualified_successes'],2)
        self.assertFalse(next(t for t in trials if t['history']=='written' and t['seed']==201)['raw_success_both'])

    def test_39_missing_control_cannot_qualify(self):
        by=copy.deepcopy(self.by)
        c=d.case('controls',seed=201,history='written',route='rewrite_none'); by[c['id']]['available']=False
        _,counts=a.trial_counts(by); self.assertEqual(counts[0]['control_qualified_successes'],2)

    def test_40_false_positive_control_cannot_qualify(self):
        by=copy.deepcopy(self.by)
        c=d.case('controls',seed=201,history='written',route='founder_none'); by[c['id']]['negative']=False
        _,counts=a.trial_counts(by); self.assertEqual(counts[0]['raw_successes'],3)
        self.assertEqual(counts[0]['control_qualified_successes'],2)

    def test_41_parent_availability_uses_actual_arrays(self):
        c=d.case('controls',seed=201,history='written',route='after_rna')
        source,name,ids,available=a.control_parent(c,self.fixture_run,self.selection)
        self.assertEqual(source,self.primary['id']); self.assertEqual(name,'rewrite_isolated_2'); self.assertTrue(available)

    def test_42_source_manifest_wrong_origin(self):
        summary=copy.deepcopy(self.summary); key=next(iter(summary['inputs']))
        summary['inputs'][key]['source']=str(d.PREDECESSOR/'independent_audit.json')
        self.assertFalse(a.integrity(self.fixture_run,summary)['input_origins'])

    def test_43_no_global_probability_claim(self):
        self.assertFalse(self.report['probability_estimate_precision_claim'])
        self.assertFalse(self.report['unique_PH_demonstrated'])
        self.assertFalse(self.report['autonomous_reproduction'])

    def flow(self,missing=None,technical=None,execution=False):
        with tempfile.TemporaryDirectory(prefix='p12-flow-') as temp,redirect_stdout(io.StringIO()):
            output=Path(temp)/'output'; output.mkdir(); calls=[]
            def worker(c,config,run,deadline,env):
                calls.append(c); return dict(id=c['id'],execution_pass=not execution)
            def audit(run,stage):
                return dict(quality_gate=stage!=technical,eligible=True,
                            selected=None if stage==missing else 'strong' if stage in ('timing','cells') else None)
            with patch.object(r.tempfile,'mkdtemp',return_value=str(output)),patch.object(r,'freeze',return_value=({}, {}, {})),\
                 patch.object(r,'predecessor_audit',return_value=self.history),patch.object(r,'run_worker',side_effect=worker),\
                 patch.object(a,'stage_audit',side_effect=audit),patch.object(a,'integrity',return_value={'fixture':True}),\
                 patch.object(d,'source_check'):
                code=r.run(d.ROOT/'configs/paper_lineage_robustness_v1.json')
            return code,calls,json.loads((output/'summary.json').read_text())

    def test_44_no_timing_level_still_tests_cells(self):
        code,calls,summary=self.flow(missing='timing')
        self.assertEqual((code,len(calls)),(0,68)); self.assertIn('cells',summary['attempted_stages'])
        self.assertEqual(summary['completion_reason'],'no_qualified_combined_challenge')

    def test_45_no_cell_level_stops_combined(self):
        code,calls,_=self.flow(missing='cells'); self.assertEqual((code,len(calls)),(0,68))

    def test_46_all_stages_run_once(self):
        code,calls,summary=self.flow(); self.assertEqual((code,len(calls)),(0,158))
        self.assertEqual(summary['completion_reason'],'combined_and_controls_completed')

    def test_47_technical_failure_not_negative(self):
        code,calls,summary=self.flow(technical='timing'); self.assertEqual((code,len(calls)),(1,36))
        self.assertEqual(summary['completion_reason'],'technical_gate_failure')

    def test_48_execution_failure_blocks_later_stages(self):
        code,calls,_=self.flow(execution=True); self.assertEqual((code,len(calls)),(1,4))

    def supervisor_fixture(self,verification_rc=0,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p12-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-lineage-robustness-test'; job.mkdir(parents=True)
            run=root/'runs/paper-lineage-robustness-test'; run.mkdir()
            source=root/'source'; source.write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={str(source):'bad' if bad_input else d.digest(source)}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time()))
            (job/'runner.log').write_text('Run artifacts: '+str(run)+'\n')
            d.write_json(run/'summary.json',dict(cases=[],registered_cases=[],stage='finished',
                completion_reason='no_qualified_combined_challenge',gates={},selection={}))
            d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,independent_check_count=1,
                all_fine_agree=True,trial_counts=[],selection={}))
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
        with tempfile.TemporaryDirectory(prefix='p12-status-') as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='combined',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale'])

    def test_56_wrong_run_path_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p12-discover-') as temp:
            job=Path(temp); (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)

    def worker_rejection(self,c,stage,gates=None,selection=None):
        with tempfile.TemporaryDirectory(prefix='p12-worker-') as temp:
            run=Path(temp); folder=run/'case'; folder.mkdir()
            d.write_json(folder/'spec.json',dict(case=c,config=self.config,inputs=str(run/'inputs')))
            d.write_json(run/'summary.json',dict(stage=stage,gates=gates or {},gate_hashes={},selection=selection or {}))
            with patch.object(r,'ClockBoundedExperiment') as exp:
                with self.assertRaises(ValueError): r.worker(folder/'spec.json')
                exp.assert_not_called()

    def test_57_unregistered_worker_rejected(self):
        self.worker_rejection(dict(self.primary,id='unregistered'),'combined')

    def test_58_wrong_stage_worker_rejected(self):
        self.worker_rejection(self.primary,'cells')

    def test_59_missing_gate_blocks_worker(self):
        self.worker_rejection(self.primary,'combined')

    def test_60_predecessor_original_and_archive_checked(self):
        saved=json.loads((self.fixture_run/'inputs/p11/independent_audit.json').read_text())
        archived=copy.deepcopy(saved); archived['run']=str(self.fixture_run/'inputs/p11')
        with patch.object(a.p11,'analyze',side_effect=[copy.deepcopy(saved),archived]) as analyze:
            result=a.predecessor_audit(self.fixture_run)
        self.assertTrue(result['quality_gate']); self.assertEqual(analyze.call_count,2)
        archived=copy.deepcopy(saved); archived['quality_gate']=False
        with patch.object(a.p11,'analyze',side_effect=[copy.deepcopy(saved),archived]):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])

    def test_61_truncated_parent_produces_real_control_skips(self):
        for failure in ('founder','before','rewrite','after'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory(prefix='p12-prefix-') as temp,redirect_stdout(io.StringIO()):
                run=Path(temp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
                fixture_case(run,self.primary,self.selection,failure=failure)
                for route in a.CONTROLS+('founder_none',):
                    c=d.case('controls',seed=201,history='written',route=route)
                    row=fixture_case(run,c,self.selection)
                    checks=a.Checks(); report,data=a.branch(run/c['id'],c,self.selection,checks)
                    self.assertTrue(all(checks.rows.values()),[k for k,v in checks.rows.items() if not v])
                    expected=(route=='founder_none' or (route.startswith('before') and failure!='founder') or
                              (route.startswith('rewrite') and failure in ('rewrite','after')) or
                              (route.startswith('after') and failure=='after'))
                    self.assertEqual(report['outcome']['available'],expected)
                    if not expected:
                        self.assertEqual(data,{}); self.assertEqual(row['result']['phases'],[])
                        self.assertIsNone(row['result']['ion_indices'])
                        self.assertFalse(report['outcome']['negative'])

    def test_62_full_negative_screen_report_is_valid(self):
        with tempfile.TemporaryDirectory(prefix='p12-negative-screen-') as temp,redirect_stdout(io.StringIO()):
            run=Path(temp)
            for name in ('inputs','frozen'): (run/name).symlink_to(self.fixture_run/name,target_is_directory=True)
            summary=copy.deepcopy(self.summary)
            summary.update(cases=[],gates={},gate_hashes={},selection={},attempted_stages=['baseline','timing','cells'])
            d.write_json(run/'predecessor_audit.json',self.history)
            for stage in ('baseline','timing','cells'):
                for c in d.stage_cases(stage):
                    if stage=='baseline':
                        (run/c['id']).symlink_to(self.fixture_run/c['id'],target_is_directory=True)
                        row=copy.deepcopy(next(r for r in self.summary['cases'] if r['id']==c['id']))
                    else:
                        row=fixture_case(run,c,summary['selection'],failure='screen_all' if stage=='timing' else None)
                    summary['cases'].append(row); d.write_json(run/'summary.json',summary)
                gate=a.stage_audit(run,stage)
                self.assertTrue(gate['quality_gate'],[k for k,v in gate['checks'].items() if not v])
                d.write_json(run/(stage+'_audit.json'),gate)
                summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(run/(stage+'_audit.json'))
                if stage!='baseline': summary['selection'][stage]=gate['selected']
                d.write_json(run/'summary.json',summary)
            summary.update(completion_reason='no_qualified_combined_challenge',all_execution_valid=True)
            d.write_json(run/'summary.json',summary)
            with patch.object(a,'predecessor_audit',return_value=self.history): result=a.analyze(run)
            self.assertTrue(result['quality_gate'],[k for k,v in result['checks'].items() if not v])
            self.assertEqual(result['completed_cases'],68); self.assertEqual(result['trial_counts'],[])
            self.assertEqual(result['selection'],dict(timing=None,cells='strong'))

    def test_63_real_positive_control_does_not_qualify_trial(self):
        c=d.case('controls',seed=201,history='written',route='after_rna')
        with tempfile.TemporaryDirectory(prefix='control-positive-',dir=self.fixture_run) as temp,redirect_stdout(io.StringIO()):
            fixture_case(self.fixture_run,c,self.selection,Path(temp),failure='positive_control')
            checks=a.Checks(); result,_=a.branch(Path(temp),c,self.selection,checks)
            self.assertTrue(all(checks.rows.values()))
            self.assertFalse(result['outcome']['negative'])
            by=copy.deepcopy(self.by); by[c['id']]=result['outcome']
            _,counts=a.trial_counts(by)
            self.assertEqual(counts[0]['raw_successes'],3); self.assertEqual(counts[0]['control_qualified_successes'],2)

    def test_64_worker_rejects_postscreen_level_replacement(self):
        with tempfile.TemporaryDirectory(prefix='p12-bad-selection-') as temp:
            run=Path(temp); folder=run/'case'; folder.mkdir()
            gates={}; hashes={}
            for stage in ('baseline','timing','cells'):
                gate=dict(quality_gate=True,eligible=True,selected='strong' if stage!='baseline' else None)
                d.write_json(run/(stage+'_audit.json'),gate)
                gates[stage]=gate; hashes[stage]=d.digest(run/(stage+'_audit.json'))
            d.write_json(run/'summary.json',dict(stage='combined',gates=gates,gate_hashes=hashes,
                                                selection=dict(timing='mild',cells='strong')))
            d.write_json(folder/'spec.json',dict(case=self.primary,config=self.config,inputs=str(run/'inputs')))
            with patch.object(r,'ClockBoundedExperiment') as exp:
                with self.assertRaisesRegex(ValueError,'Selection differs'): r.worker(folder/'spec.json')
                exp.assert_not_called()

def p11_integrity():
    summary=json.loads((d.PREDECESSOR/'summary.json').read_text())
    return all(a.p11.integrity(d.PREDECESSOR,summary).values())

if __name__=='__main__': unittest.main()
