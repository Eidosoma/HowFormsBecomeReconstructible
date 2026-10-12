"""P18 synthetic fixtures and archived replays; no new scientific integrations."""
from contextlib import contextmanager,redirect_stdout
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
import paper_preparation_turnover_design as d
import run_paper_preparation_turnover as r
import analyze_paper_preparation_turnover as a
import run_paper_preparation_turnover_detached as detached

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.RateExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs):
        current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy(); replay=d.replay_source(c)
        if replay is not None:
            src=run/'inputs/p17'/replay; archived=a.arrays(src,name)
            np.testing.assert_array_equal(initial,archived['initial']); np.copyto(sim.cc_cells,archived['final'])
            records=json.loads((src/'result.json').read_text())['phases']
            meta=next(rec['clock'] for rec in records if rec['phase']==name)
            return archived['times'],archived['concentrations'],{
                k:archived[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        def mark(indices,lab):
            setter=exp.z.GRN.set_very_healthy if lab=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        if c['stage']=='renewal' and name.startswith('replacement'):
            present=any(exp.z.GRN.state_char(x)=='E' for x in initial.T)
            success=c['route']=='open' and present and (c['first']>=1000 or c['later']>=300) and failure!='all_negative'
            mark(range(3),'E' if success else 'M')
        if name=='contact':
            donor_E=all(exp.z.GRN.state_char(x)=='E' for x in initial[:,:3].T)
            if (c['readout']=='open' and donor_E and failure!='all_negative') or failure=='positive_controls': mark(range(3,6),'E')
        if failure==name: mark([0],'M')
        if failure=='isolation' and name.startswith('isolated'): mark([0],'M')
        if failure=='all_negative' and name.startswith('isolated'): mark(range(3),'M')
        if failure=='late_recovery' and name.startswith('isolated'): mark(range(3),'E')
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.000001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=[]; now=0; proposal=2*stride
        while now<total:
            step=min(cap,proposal,min(((now//stride)+1)*stride,total)-now,total-now)
            steps.append(step); now+=step
        steps=np.array(steps,dtype=np.int64); proposed=np.full(len(steps),proposal,dtype=np.int64)
        shots=np.array(list(range(0,total,stride))+[total],dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        if failure=='late' and name=='isolated_1':
            for at in range(-2,-7,-1): exp.z.GRN.set_very_tumor(values[at],0)
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(steps),sample_count=len(shots),capped_steps=int(np.count_nonzero(steps<proposed)),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock):
        out=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestPreparationTurnover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p18-software-',dir=d.ROOT/'.cache'); cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_byte_identical=True,
            prior_checks=75638,prior_cases=312,prior_calls=1020,original_reaudit_count=1,
            archive_separate_mathematical_reaudit=False,hardlinked_inputs_not_independent_backup=True,actual_P17_prefix_sources=True)
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
            predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),
            gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        with redirect_stdout(io.StringIO()):
            for stage in d.STAGES:
                for c in d.stage_cases(stage): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary); gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate)
                cls.summary['gates'][stage]=gate; cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
            cls.summary.update(all_execution_valid=True,completion_reason='all_registered_stages_completed',stage='finished')
            d.write_json(cls.fixture_run/'summary.json',cls.summary)
            with patch.object(a,'predecessor_audit',return_value=cls.history): cls.report=a.analyze(cls.fixture_run)
        cls.primary=d.case(first=1000,later=100); cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}; cls.cases=d.fixed_cases()

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p18-unit-') as temp:
            run=Path(temp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            for c in d.stage_cases('renewal'): (run/c['id']).symlink_to(self.fixture_run/c['id'],target_is_directory=True)
            yield run

    def audit_branch(self,run,c):
        checks=a.Checks(); report,data=a.branch(run/c['id'],c,checks); return checks,report,data

    @contextmanager
    def copied_case(self,c=None):
        c=self.primary if c is None else c
        with self.isolated_run() as run:
            folder=run/c['id']
            if folder.is_symlink(): folder.unlink()
            shutil.copytree(self.fixture_run/c['id'],folder); yield run,folder

    def fabricated(self,mode,c=None):
        c=self.primary if c is None else c
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            if (run/c['id']).is_symlink(): (run/c['id']).unlink()
            fixture_case(run,c,mode); checks,report,data=self.audit_branch(run,c)
            self.assertTrue(all(checks.rows.values()),[k for k,v in checks.rows.items() if not v])
            self.assertEqual(len(data),3 if c['readout'] else 7); return report['outcome']

    def corrupt_array(self,name,change,c=None):
        c=self.primary if c is None else c
        with self.copied_case(c) as (run,folder):
            value=a.arrays(folder,name); change(value); np.savez_compressed(folder/(name+'.npz'),**value)
            result=json.loads((folder/'result.json').read_text())
            next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def corrupt_result(self,change,c=None):
        c=self.primary if c is None else c
        with self.copied_case(c) as (run,folder):
            result=json.loads((folder/'result.json').read_text()); change(result); d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def test_registration_full_factorial_and_fixed_readouts(self):
        self.assertEqual(self.cases,a.expected_cases()); self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[30,108,144])
        self.assertEqual((len({c['id'] for c in self.cases}),sum(c['fine'] for c in self.cases)),(282,141))
        self.assertEqual({(c['first'],c['later']) for c in d.stage_cases('renewal')},{(u,v) for u in (100,300,1000) for v in (100,300,1000)})
        self.assertEqual({(c['first'],c['later']) for c in d.stage_cases('onward')},{(100,100),(100,300),(300,300),(1000,100)})
        self.assertEqual(d.validate_config(json.loads((d.ROOT/'configs/paper_preparation_turnover_v1.json').read_text())),d.FIXED)
        for key,value in [('later_intervals',[100]),('incoming_seed',502),('archive_mode','copy'),('maximum_cases',283)]:
            with self.assertRaises(ValueError): d.validate_config(dict(d.FIXED,**{key:value}))

    def test_complete_synthetic_panel(self):
        self.assertTrue(self.report['quality_gate']); self.assertEqual((self.report['completed_cases'],self.report['integration_calls']),(282,1296))
        self.assertEqual(len(self.report['fine_comparisons']),141); self.assertTrue(self.report['all_fine_agree'])
        self.assertEqual([len(self.report[k]) for k in ['timing_grid','RNA_contrasts','timing_contrasts','chain_outcomes']],[54,27,12,24])
        self.assertTrue(self.report['readout_capacity']['qualified'])

    def test_manifest_inventory_and_unchanged_native_source(self):
        self.assertEqual((len(d.LOCAL_FILES),len(d.execution_manifest()),len(d.input_paths())),(147,183,9451))
        d.source_check(); self.assertTrue(all(a.integrity(self.fixture_run,self.summary).values()))

    def test_inputs_linked_but_frozen_execution_is_copied(self):
        for name,meta in self.summary['inputs'].items():
            self.assertEqual(meta['storage'],'hardlink_immutable_v1')
            self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for p in d.LOCAL_FILES: self.assertFalse((self.fixture_run/'frozen'/p.name).samefile(p))

    def test_byte_identical_copy_does_not_satisfy_linked_archive_policy(self):
        with tempfile.TemporaryDirectory(prefix='p18-archive-') as temp:
            root=Path(temp); source=root/'source'; source.write_text('immutable fixture')
            run=root/'run'; (run/'inputs').mkdir(parents=True); (run/'frozen').mkdir(); shutil.copyfile(source,run/'inputs/a')
            summary=dict(revision=d.REVISION,hashes_sha256={},frozen_hashes_sha256={},inputs={'a':dict(source=str(source),sha256=d.digest(source),storage='hardlink_immutable_v1')})
            with patch.object(d,'input_paths',return_value={'a':source}),patch.object(d,'execution_manifest',return_value={}),patch.object(d,'LOCAL_FILES',[]):
                flags=a.integrity(run,summary); self.assertTrue(flags['inputs']); self.assertFalse(flags['linked_inputs'])

    def test_draws_match_P16_and_change_only_ZEB_protein(self):
        self.assertEqual(d.draw_book(),a.expected_draws()); self.assertEqual(d.draw_book(),a.p17.expected_draws())
        for f in (False,True):
            _,M=r.stock(self.fixture_run,f)
            for cycle in (0,1):
                for pos in range(3):
                    x=d.incoming(M,cycle,pos); np.testing.assert_array_equal(x,a.incoming(M,cycle,pos))
                    np.testing.assert_array_equal(x[np.arange(17)!=7],M[np.arange(17)!=7]); self.assertEqual(''.join(a.labels(x,a.INDEX)),'M')

    def test_all_later_forks_start_from_same_actual_prefix(self):
        for h in d.FOUNDERS:
            for first in d.TIMES:
                for route in d.ROUTES:
                    for fine in (False,True):
                        sources=[]
                        for later in d.TIMES:
                            c=d.case(founder=h,first=first,later=later,route=route,fine=fine)
                            value,ids,cursor,record=r.prefix_checkpoint(self.fixture_run,c); sources.append(value)
                            data=a.arrays(self.fixture_run/c['id'],'replacement_02')
                            np.testing.assert_array_equal(data['initial'][:,[0,2]],value[:,[0,2]])
                            _,M=r.stock(self.fixture_run,fine); np.testing.assert_array_equal(data['initial'][:,1:2],d.incoming(M,0,1))
                            self.assertEqual(cursor,(0 if h=='stock_E' else 1180000)+first)
                            self.assertEqual(ids[0],a.prefix_stem(c)+':replacement:0:0'); self.assertEqual(record['case']['tau'],first)
                            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
                            self.assertEqual(result['archived_prefix_source'],d.prefix_source(c))
                            self.assertNotIn('prefix_source',result['outcome'])
                        for x in sources[1:]: np.testing.assert_array_equal(x,sources[0])

    def test_every_survivor_and_second_cycle_continues(self):
        for c in d.stage_cases('renewal'):
            value,_,_,_=r.prefix_checkpoint(self.fixture_run,c)
            for at in range(1,6):
                data=a.arrays(self.fixture_run/c['id'],'replacement_%02d'%(at+1)); keep=[p for p in range(3) if p!=at%3]
                np.testing.assert_array_equal(data['initial'][:,keep],value[:,keep]); value=data['final']
            np.testing.assert_array_equal(a.arrays(self.fixture_run/c['id'],'isolated_1')['initial'],value)
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            self.assertEqual(result['phases'][-1]['setup']['cell_ids'],[d.new_id(c,1,p) for p in range(3)])
            self.assertFalse(set(result['outcome']['fork_ids'])&set(result['phases'][-1]['setup']['cell_ids']))

    def test_first_duration_does_not_leak_into_later_windows(self):
        for c in d.stage_cases('renewal'):
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            self.assertEqual([p['requested_horizon'] for p in result['phases']],[c['later']]*5+[10000]*2)
            start=(0 if c['founder']=='stock_E' else 1180000)+c['first']
            self.assertEqual(result['phases'][0]['logical_interval'],[start,start+c['later']])
            self.assertEqual(result['outcome']['logical_end'],start+5*c['later']+20000)

    def test_wipes_match_total_exposure_and_incoming_burden(self):
        for c in d.stage_cases('baseline'):
            if c['arm']!='wipe': continue
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            self.assertEqual([p['requested_horizon'] for p in result['phases']],[c['first']+2*c['later'],3*c['later'],10000,10000])
            self.assertEqual(len(result['outcome']['replacements']),6); self.assertEqual(result['outcome']['logical_end'],d.duration(c)+20000)

    def test_RNA_counterparts_use_RNA_prefix_and_keep_ions(self):
        for c in d.stage_cases('renewal'):
            value,_,_,record=r.prefix_checkpoint(self.fixture_run,c)
            self.assertEqual(record['case']['route'],c['route'])
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            for rec in result['phases'][:5]:
                self.assertEqual(rec['setup']['mirna_kd'],0 if c['route']=='rna' else 1.25e-14)
                self.assertTrue(a.arrays(self.fixture_run/c['id'],rec['phase'])['junction_diffusion'][:4].any())

    def test_exact_P17_replays_all_diagonal_anchors(self):
        cases=phases=0
        for c in self.cases:
            self.assertEqual(d.replay_source(c),a.replay_source(c))
            if d.replay_source(c) is None: continue
            checks,_,data=self.audit_branch(self.fixture_run,c); cases+=1; phases+=len(data)
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),33*len(data)); self.assertTrue(all(replay))
        self.assertEqual((cases,phases),(126,528))

    def test_negative_and_positive_onward_use_actual_parents(self):
        for c in d.stage_cases('onward'):
            initial=a.arrays(self.fixture_run/c['id'],'contact')['initial']
            np.testing.assert_array_equal(initial[:,:3],a.arrays(self.fixture_run/d.parent(c)['id'],'isolated_2')['final'])
            self.assertEqual(''.join(a.labels(initial[:,3:],a.INDEX)),'MMM')
            expected='EEE' if c['route']=='open' and (c['first'],c['later'])!=(100,100) else 'MMM'
            self.assertEqual(self.by[c['id']]['donor_initial_labels'],expected)

    def test_clocks_continue_through_onward_and_isolation(self):
        for row in self.summary['cases']:
            c=row['result']['case']; cursor=0 if c['founder']=='stock_E' else 1180000
            if c['stage']=='renewal': cursor+=c['first']
            if c['stage']=='onward': cursor+=c['first']+5*c['later']+20000
            for rec in row['result']['phases']:
                self.assertEqual(rec['logical_interval'],[cursor,cursor+rec['requested_horizon']]); cursor+=rec['requested_horizon']
            self.assertEqual(cursor,row['result']['outcome']['logical_end'])

    def test_off_diagonal_wipe_clock_boundaries(self):
        from test_paper_contact_clock_recovery import TestBoundedClockKernel
        for fine in (False,True):
            for horizon in sorted({u+2*v for u in d.TIMES for v in d.TIMES}|{3*v for v in d.TIMES}):
                system=TestBoundedClockKernel().system(fine); system.GP.time_step=.00005 if fine else .0001; initial=system.cc_cells.copy()
                times,values,trace,meta=r.clock.integrate(system,horizon,min(100,horizon/20),min(100,horizon/100)*(.5 if fine else 1))
                checks=a.Checks(); a.p16.audit_clock(dict(initial=initial,final=system.cc_cells.copy(),times=times,concentrations=values,**trace),
                    dict(phase='kernel',requested_horizon=horizon,clock=meta),d.case(fine=fine),checks)
                self.assertTrue(all(checks.rows.values()),[k for k,v in checks.rows.items() if not v])

    def test_scientific_negative_is_not_execution_failure(self):
        out=self.fabricated('all_negative'); self.assertFalse(out['retained_E']); self.assertTrue(out['available'])

    def test_one_bad_hold_and_late_occupancy_each_fail_retention(self):
        for mode in ('isolated_1','isolated_2','late'):
            self.assertFalse(self.fabricated(mode)['retained_E'])

    def test_first_window_and_later_windows_are_separate(self):
        out=self.by[d.case(first=100,later=1000)['id']]
        self.assertTrue(out['later_windows_E']); self.assertFalse(out['all_windows_E']); self.assertTrue(out['retained_E'])

    def test_timing_rescues_require_failed_reference(self):
        report=a.contrasts(self.by); row=next(x for x in report['timing_contrasts'] if x['founder']=='written' and x['first']==1000)
        self.assertTrue(row['control_qualified_rescue'])
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(fine=f)['id']]['retained_E']=True
        row=next(x for x in a.contrasts(by)['timing_contrasts'] if x['founder']=='written' and x['first']==1000)
        self.assertTrue(row['changed_retained_E_both']); self.assertFalse(row['raw_rescue'])

    def test_missing_and_positive_RNA_or_wipe_cannot_qualify_rescue(self):
        for case in (d.case(first=1000,later=100,route='rna'),d.case('baseline',first=1000,later=100,arm='wipe')):
            for missing in (False,True):
                by=copy.deepcopy(self.by)
                if missing: by.pop(case['id'])
                else: by[case['id']]['retained_E']=True
                row=next(x for x in a.contrasts(by)['timing_contrasts'] if x['founder']=='written' and x['first']==1000)
                self.assertTrue(row['raw_rescue']); self.assertFalse(row['control_qualified_rescue'])

    def test_missing_and_positive_readout_controls_block_chain(self):
        for stage,readout in [('onward','rna'),('onward','cut'),('baseline','cut')]:
            by=copy.deepcopy(self.by)
            c=d.case(stage,first=1000,later=100,arm='capacity',readout=readout)
            by.pop(c['id'])
            row=next(x for x in a.contrasts(by)['chain_outcomes'] if x['founder']=='written' and x['first']==1000 and x['route']=='open')
            self.assertTrue(row['raw_retention_and_onward']); self.assertFalse(row['benchmark_supported_chain'])
        by=copy.deepcopy(self.by); by[d.case('onward',first=1000,later=100,readout='cut')['id']]['transmitted_E']=True
        row=next(x for x in a.contrasts(by)['chain_outcomes'] if x['founder']=='written' and x['first']==1000 and x['route']=='open')
        self.assertFalse(row['control_qualified_chain'])

    def test_onward_cannot_repair_failed_retention(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(first=1000,later=100,fine=f)['id']]['retained_E']=False
        row=next(x for x in a.contrasts(by)['chain_outcomes'] if x['founder']=='written' and x['first']==1000 and x['route']=='open')
        self.assertTrue(row['onward_transmission_both']); self.assertFalse(row['raw_retention_and_onward'])

    def test_all_negative_outcomes_preserve_fixed_grid_and_denominators(self):
        by=copy.deepcopy(self.by)
        for out in by.values():
            if 'retained_E' in out: out['retained_E']=False
            if 'transmitted_E' in out: out['transmitted_E']=False
        report=a.contrasts(by); self.assertEqual(len(report['timing_grid']),54); self.assertEqual(len(report['chain_outcomes']),24)
        self.assertFalse(any(x['raw_retention_and_onward'] for x in report['chain_outcomes']))
        self.assertTrue(all(x['source_trials']==1 for x in report['timing_grid']+report['timing_contrasts']+report['chain_outcomes']))

    def test_fine_disagreement_blocks_quality(self):
        by=copy.deepcopy(self.by); by[d.case(first=1000,later=100,fine=True)['id']]['retained_E']=False
        endpoints={c['id']:{'end':dict(final=np.ones((17,3)))} for c in self.cases}; checks=a.Checks()
        a.p12.compare_fine(self.cases,by,endpoints,checks); self.assertFalse(all(checks.rows.values()))

    def test_rehashed_survivor_reset_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['initial'].__setitem__((7,0),x['initial'][7,0]+1))

    def test_rehashed_incoming_state_change_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['initial'].__setitem__((0,1),x['initial'][0,1]+1))

    def test_rehashed_second_cycle_reset_rejected(self):
        self.corrupt_array('replacement_04',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]+1))

    def test_rehashed_missing_edge_and_isolation_contact_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['edge_available_initial'].__setitem__(0,0))
        self.corrupt_array('isolated_1',lambda x:x['junction_diffusion'].__setitem__(0,1e-14))

    def test_rehashed_bad_clock_tick_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_rehashed_onward_donor_reset_rejected(self):
        self.corrupt_array('contact',lambda x:x['initial'].__setitem__((7,0),x['initial'][7,0]+1),d.case('onward',first=1000,later=100,readout='open'))

    def test_rehashed_diagonal_replay_change_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['concentrations'].__setitem__((1,0,0),x['concentrations'][1,0,0]+.1),d.case(first=300,later=300))

    def test_wrong_identity_duration_and_claim_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(0,'wrong'))
        self.corrupt_result(lambda x:x['phases'][0].__setitem__('logical_interval',[1181000,1182000]))
        self.corrupt_result(lambda x:x.__setitem__('autonomous_reproduction',True))
        self.corrupt_result(lambda x:x.__setitem__('archived_prefix_source','wrong'))

    def test_forged_retention_rejected(self):
        self.corrupt_result(lambda x:x['outcome'].__setitem__('retained_E',False))

    def test_extra_and_missing_phase_rejected(self):
        with self.copied_case() as (run,folder):
            shutil.copyfile(folder/'replacement_02.npz',folder/'unregistered.npz')
            checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))
        with self.copied_case() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['phases'].pop(); d.write_json(folder/'result.json',result)
            with self.assertRaises(ValueError): self.audit_branch(run,self.primary)

    def test_predecessor_reaudit_once_plus_verified_linked_archive(self):
        saved=json.loads((self.fixture_run/'inputs/p17/independent_audit.json').read_text())
        for fn in (r.predecessor_audit,a.predecessor_audit):
            with patch.object(a.p17,'analyze',return_value=copy.deepcopy(saved)) as check:
                report=fn(self.fixture_run); self.assertTrue(report['quality_gate']); self.assertEqual(check.call_count,1)
                self.assertFalse(report['archive_separate_mathematical_reaudit'])
            with patch.object(a.p17,'analyze',return_value=copy.deepcopy(saved)),patch.object(a,'integrity',return_value={'linked_inputs':False}):
                self.assertFalse(fn(self.fixture_run)['quality_gate'])
            changed=copy.deepcopy(saved); changed['quality_gate']=False
            with patch.object(a.p17,'analyze',return_value=changed): self.assertFalse(fn(self.fixture_run)['quality_gate'])

    def flow(self,technical=True,execution=True,preflight=True):
        with tempfile.TemporaryDirectory(prefix='p18-flow-') as temp,redirect_stdout(io.StringIO()):
            output=Path(temp)/'output'; output.mkdir(); calls=[]
            def worker(c,config,run,deadline,env): calls.append(c); return dict(id=c['id'],execution_pass=execution)
            history=dict(self.history,quality_gate=preflight)
            with patch.object(r.tempfile,'mkdtemp',return_value=str(output)),patch.object(r,'freeze',return_value=({}, {}, {})),\
                 patch.object(r,'predecessor_audit',return_value=history),patch.object(r,'run_worker',side_effect=worker),\
                 patch.object(a,'stage_audit',return_value=dict(quality_gate=technical,eligible=True)),\
                 patch.object(a,'integrity',return_value={'fixture':True}),patch.object(d,'source_check'):
                try: code=r.run(d.ROOT/'configs/paper_preparation_turnover_v1.json')
                except RuntimeError:
                    if preflight: raise
                    code=1
            return code,calls,json.loads((output/'summary.json').read_text())

    def test_all_fixed_stages_run_unconditionally_on_science(self):
        code,calls,s=self.flow(); self.assertEqual((code,len(calls)),(0,282)); self.assertEqual(len({c['id'] for c in calls}),282)
        self.assertEqual(s['attempted_stages'],list(d.STAGES)); self.assertEqual(s['completion_reason'],'all_registered_stages_completed')

    def test_technical_and_execution_failures_stop_without_retry(self):
        for kw in ({'technical':False},{'execution':False}):
            code,calls,_=self.flow(**kw); self.assertEqual((code,len(calls)),(1,30))

    def test_preflight_failure_prevents_new_integrations(self):
        code,calls,_=self.flow(preflight=False); self.assertEqual((code,len(calls)),(1,0))

    def test_expired_worker_does_not_launch(self):
        with patch.object(r.subprocess,'run') as launch:
            result=r.run_worker(self.primary,d.FIXED,Path('/tmp'),time.monotonic()-1,{})
        launch.assert_not_called(); self.assertFalse(result['execution_pass'])

    def test_worker_guards_before_instantiation(self):
        for failure in ('case','stage','preflight','hash','draw','gate','parent','parent_raw','prefix_missing','prefix_raw'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                run=Path(temp); (run/'frozen').mkdir()
                c=d.case('baseline',arm='capacity',readout='open')
                if failure in ('parent','parent_raw'): c=d.case('onward',first=1000,later=100,readout='open')
                if failure in ('gate','prefix_missing','prefix_raw'): c=self.primary
                if failure=='case': c=dict(c,route='unregistered')
                folder=run/c['id']; folder.mkdir(); d.write_json(folder/'spec.json',dict(config=d.FIXED,case=c,inputs=str(run/'inputs')))
                d.write_json(run/'predecessor_audit.json',self.history)
                summary=dict(stage='wrong' if failure=='stage' else c['stage'],predecessor_gate=failure!='preflight',
                    predecessor_audit=self.history,predecessor_audit_sha256='bad' if failure=='hash' else d.digest(run/'predecessor_audit.json'),
                    gates={},gate_hashes={},cases=[],inputs={})
                for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
                    gate=dict(quality_gate=failure!='gate'); d.write_json(run/(stage+'_audit.json'),gate)
                    summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(run/(stage+'_audit.json'))
                if failure=='parent_raw':
                    par=d.parent(c)['id']; shutil.copytree(self.fixture_run/par,run/par)
                    summary['cases']=[copy.deepcopy(next(x for x in self.summary['cases'] if x['id']==par))]
                    (run/par/'isolated_2.npz').write_bytes(b'changed')
                if failure=='prefix_raw':
                    for tail in ('result.json','replacement_01.npz'):
                        key='p17/'+d.prefix_source(c)+'/'+tail; target=run/'inputs'/key; target.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(self.fixture_run/'inputs'/key,target); summary['inputs'][key]=copy.deepcopy(self.summary['inputs'][key])
                    (run/'inputs/p17'/d.prefix_source(c)/'replacement_01.npz').write_bytes(b'changed')
                d.write_json(run/'summary.json',summary); d.write_json(run/'frozen/paper_preparation_turnover_draws_v1.json',{} if failure=='draw' else d.draw_book())
                with self.assertRaises(ValueError),patch.object(r,'RateExperiment') as exp: r.worker(folder/'spec.json')
                exp.assert_not_called()

    def supervisor_fixture(self,verification_rc=0,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p18-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-preparation-turnover-test'; job.mkdir(parents=True)
            run=root/'runs/paper-preparation-turnover-test'; run.mkdir(); source=root/'source'; source.write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},input_hashes_sha256={str(source):'bad' if bad_input else d.digest(source)}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time())); (job/'runner.log').write_text('Run artifacts: '+str(run)+'\n')
            d.write_json(run/'summary.json',dict(cases=[],registered_cases=[],stage='finished',completion_reason='all_registered_stages_completed',gates={}))
            d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,independent_check_count=1,all_fine_agree=True,readout_capacity={},timing_contrasts=[],chain_outcomes=[]))
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

    def test_supervisor_success_and_stage_order(self):
        code,meta,calls=self.supervisor_fixture(); self.assertEqual(code,0); self.assertEqual(meta['phase'],'complete')
        self.assertEqual(calls,['verification.log','runner.log','audit.log'])

    def test_verification_failure_or_timeout_blocks_science(self):
        for rc in (1,124):
            code,meta,calls=self.supervisor_fixture(verification_rc=rc); self.assertEqual(code,1)
            self.assertEqual(calls,['verification.log']); self.assertEqual(meta['phase'],'failed')

    def test_runner_timeout_does_not_retry(self):
        code,_,calls=self.supervisor_fixture(runner_rc=124); self.assertEqual((code,calls),(1,['verification.log','runner.log']))

    def test_bad_audit_does_not_report_success(self):
        code,meta,_=self.supervisor_fixture(audit_quality=False); self.assertEqual(code,1); self.assertEqual(meta['phase'],'failed')

    def test_changed_input_blocks_everything(self):
        code,_,calls=self.supervisor_fixture(bad_input=True); self.assertEqual((code,calls),(1,[]))

    def test_status_does_not_relaunch(self):
        with tempfile.TemporaryDirectory() as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='renewal',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale']); (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)

if __name__=='__main__': unittest.main()
