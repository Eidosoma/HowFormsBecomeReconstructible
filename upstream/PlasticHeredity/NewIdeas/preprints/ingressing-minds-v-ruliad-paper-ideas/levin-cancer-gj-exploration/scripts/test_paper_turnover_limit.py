"""P16 software fixtures; synthetic dynamics and archived replay are not new science."""
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
import paper_turnover_limit_design as d
import run_paper_turnover_limit as r
import analyze_paper_turnover_limit as a
import run_paper_turnover_limit_detached as detached

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.RateExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs):
        current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy()
        if c['stage']=='baseline' and c['readout']:
            src=run/'inputs/p15'/('readout__stock__stock_E__'+c['readout']+('__fine' if c['fine'] else ''))
            archived=a.arrays(src,name); np.testing.assert_array_equal(initial,archived['initial'])
            np.copyto(sim.cc_cells,archived['final'])
            records=json.loads((src/'result.json').read_text())['phases']
            meta=next(rec['clock'] for rec in records if rec['phase']==name)
            return archived['times'],archived['concentrations'],{
                k:archived[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        def mark(indices,lab):
            setter=exp.z.GRN.set_very_healthy if lab=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        if name.startswith('replacement') and c['route']=='open':
            limit={'single':10,'pair_center':100,'pair_edge':20000,'wipe':1000000}[c['scheme']]
            if c['founder']=='stock_E' and c['scheme']!='wipe': limit=1
            has_E=any(exp.z.GRN.state_char(x)=='E' for x in initial.T)
            mark(range(3),'E' if has_E and c['tau']>=limit and failure!='all_negative' else 'M')
        if name=='contact':
            donor_E=all(exp.z.GRN.state_char(x)=='E' for x in initial[:,:3].T)
            if (c['readout']=='open' and donor_E and failure!='all_negative') or failure=='positive_controls': mark(range(3,6),'E')
        if failure==name: mark([2],'M')
        if failure=='isolation' and name.startswith('isolated'): mark([2],'M')
        if failure=='late_recovery' and name.startswith('isolated'): mark(range(3),'E')
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.000001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=np.full(total//cap,cap,dtype=np.int64); proposed=np.full(len(steps),2*stride,dtype=np.int64)
        shots=np.arange(0,total+1,stride,dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        if failure=='late' and name=='isolated_1':
            for at in range(-2,-7,-1): exp.z.GRN.set_very_tumor(values[at],2)
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(steps),sample_count=len(shots),capped_steps=len(steps),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock):
        out=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestTurnoverLimit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p16-software-'); cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_matches_saved=True,
            prior_checks=24043,prior_cases=102,prior_calls=354,actual_onward_recipient_sources=True)
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
            predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),
            gates={},gate_hashes={},selection=None,attempted_stages=list(d.STAGES))
        with redirect_stdout(io.StringIO()):
            for stage in d.STAGES:
                for c in d.stage_cases(stage,cls.summary['selection']): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary); gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']: raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate)
                cls.summary['gates'][stage]=gate; cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
                if stage=='screen':
                    cls.summary['selection']=gate['selection']; cls.summary['registered_cases']=d.fixed_cases(gate['selection'])
            cls.summary.update(all_execution_valid=True,completion_reason='all_registered_stages_completed',stage='finished')
            d.write_json(cls.fixture_run/'summary.json',cls.summary)
            with patch.object(a,'predecessor_audit',return_value=cls.history): cls.report=a.analyze(cls.fixture_run)
        cls.primary=d.case(tau=10); cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}
        cls.selection=cls.summary['selection']; cls.cases=d.fixed_cases(cls.selection)

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p16-unit-') as temp:
            run=Path(temp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            for c in self.cases:
                if c['stage'] in ('screen','rna_controls'): (run/c['id']).symlink_to(self.fixture_run/c['id'],target_is_directory=True)
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
            self.assertEqual(len(data),3 if c['readout'] or c['stage']=='baseline' else len(d.schedule(c['scheme'],c['tau']))+2)
            return report['outcome']
    def corrupt_array(self,name,change,c=None):
        c=self.primary if c is None else c
        with self.copied_case(c) as (run,folder):
            value=a.arrays(folder,name); change(value); np.savez_compressed(folder/(name+'.npz'),**value)
            result=json.loads((folder/'result.json').read_text())
            next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))
    def corrupt_result(self,change,c=None):
        c=self.primary if c is None else c
        with self.copied_case(c) as (run,folder):
            result=json.loads((folder/'result.json').read_text()); change(result); d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def test_registration_and_limits(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases('screen'))
        self.assertEqual(self.cases,a.expected_cases(selection=self.selection))
        self.assertEqual([len(d.stage_cases(s,self.selection)) for s in d.STAGES],[12,96,18,108])
        self.assertEqual((len({c['id'] for c in self.cases}),sum(c['fine'] for c in self.cases)),(234,117))
        self.assertEqual(d.validate_config(json.loads((d.ROOT/'configs/paper_turnover_limit_v1.json').read_text())),d.FIXED)
        for key,value in (('intervals',[1,10]),('incoming_seed',502),('maximum_cases',235),('workers',3)):
            with self.assertRaises(ValueError): d.validate_config(dict(d.FIXED,**{key:value}))
    def test_manifests_and_native_source(self):
        self.assertEqual((len(d.LOCAL_FILES),len(d.execution_manifest()),len(d.input_paths())),(131,167,6545))
        d.source_check(); self.assertTrue(all(a.integrity(self.fixture_run,self.summary).values()))
    def test_complete_synthetic_panel(self):
        self.assertTrue(self.report['quality_gate'],[k for k,v in self.report['checks'].items() if not v])
        self.assertEqual((self.report['completed_cases'],self.report['integration_calls']),(234,1056))
        self.assertEqual(len(self.report['fine_comparisons']),117); self.assertTrue(self.report['all_fine_agree'])
        self.assertEqual((len(self.report['screen_outcomes']),len(self.report['selected_contrasts']),len(self.report['chain_outcomes'])),(48,9,18))
        self.assertTrue(self.report['readout_capacity']['qualified'])
    def test_draw_book_and_protein_only(self):
        self.assertEqual(d.draw_book(),a.expected_draws())
        for f in (False,True):
            _,M=r.stock(self.fixture_run,f)
            for cycle in (0,1):
                for pos in range(3):
                    x=d.incoming(M,cycle,pos); np.testing.assert_array_equal(x,a.incoming(M,cycle,pos))
                    np.testing.assert_array_equal(x[np.arange(17)!=7],M[np.arange(17)!=7])
                    self.assertEqual(''.join(a.labels(x,a.INDEX)),'M')
    def test_equal_burden_and_both_survivor_geometries(self):
        for scheme in d.SCHEMES:
            for tau in d.TAUS:
                slots=d.schedule(scheme,tau)
                self.assertEqual([(x['cycle'],x['positions'],x['horizon']) for x in slots],a.slots(scheme,tau))
                self.assertEqual(sum(x['horizon'] for x in slots),6*tau)
                self.assertEqual([sum(p in x['positions'] for x in slots) for p in range(3)],[2]*3)
        self.assertEqual(d.schedule('pair_center',1)[0]['positions'],[0,2])
        self.assertEqual(d.schedule('pair_edge',1)[0]['positions'],[0,1])
    def test_historical_source_clock_and_state(self):
        for h in ('written','ordinary'):
            for f in (False,True):
                c=d.case(founder=h,tau=10,fine=f); value,ids,base=r.founder(self.fixture_run,c)
                self.assertEqual(ids,a.source_ids(c)); self.assertEqual(base,1180000)
                np.testing.assert_array_equal(value,a.arrays(self.fixture_run/'inputs/p15'/a.source(c),'isolated_2')['final'])
                first=a.arrays(self.fixture_run/c['id'],'replacement_01')['initial']
                np.testing.assert_array_equal(first[:,1:],value[:,1:])
    def test_every_survivor_continues_without_reset(self):
        for c in d.stage_cases('screen'):
            value,ids,base=r.founder(self.fixture_run,c)
            for event,slot in enumerate(d.schedule(c['scheme'],c['tau']),1):
                data=a.arrays(self.fixture_run/c['id'],'replacement_%02d'%event)
                keep=[p for p in range(3) if p not in slot['positions']]
                np.testing.assert_array_equal(data['initial'][:,keep],value[:,keep]); value=data['final']
            np.testing.assert_array_equal(a.arrays(self.fixture_run/c['id'],'isolated_1')['initial'],value)
            self.assertEqual(len(self.by[c['id']]['replacements']),6)
            self.assertFalse(set(ids)&{x['inserted'] for x in self.by[c['id']]['replacements']})
    def test_rna_control_preserves_ionic_internal_coupling(self):
        for c in d.stage_cases('rna_controls',self.selection):
            data=a.arrays(self.fixture_run/c['id'],'replacement_01')
            self.assertEqual(len(data['edge_from']),2); self.assertTrue(np.all(data['edge_available_initial']==1))
            self.assertTrue(np.all(data['edge_power_initial']==60)); self.assertTrue(data['junction_diffusion'][:4].any())
            record=json.loads((self.fixture_run/c['id']/'result.json').read_text())['phases'][0]
            self.assertEqual(record['setup']['mirna_kd'],0)
    def test_onward_preserves_negative_and_positive_parents(self):
        for c in d.stage_cases('onward',self.selection):
            initial=a.arrays(self.fixture_run/c['id'],'contact')['initial']
            np.testing.assert_array_equal(initial[:,:3],a.arrays(self.fixture_run/d.parent(c)['id'],'isolated_2')['final'])
            self.assertEqual(''.join(a.labels(initial[:,3:],a.INDEX)),'MMM')
            self.assertEqual(self.by[c['id']]['donor_initial_labels'],'MMM' if c['route']=='rna' else 'EEE')
    def test_baseline_replays_exact_raw_arrays(self):
        for c in d.stage_cases('baseline'):
            if not c['readout']: continue
            checks,_,data=self.audit_branch(self.fixture_run,c)
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),3*33); self.assertTrue(all(replay))
    def test_each_logical_timeline(self):
        for row in self.summary['cases']:
            c=row['result']['case']; recs=row['result']['phases']
            cursor=0 if c['founder']=='stock_E' else 1180000
            if c['stage']=='onward': cursor+=6*c['tau']+20000
            for rec in recs:
                self.assertEqual(rec['logical_interval'],[cursor,cursor+rec['requested_horizon']]); cursor+=rec['requested_horizon']
            self.assertEqual(cursor,row['result']['outcome']['logical_end'])
    def test_short_phase_clock_kernel_and_independent_audit(self):
        from test_paper_contact_clock_recovery import TestBoundedClockKernel
        for fine in (False,True):
            for horizon in (1,2,3,10,20,30,100,200,300,10000,120000):
                system=TestBoundedClockKernel().system(fine)
                system.GP.time_step=.00005 if fine else .0001
                initial=system.cc_cells.copy()
                sample=min(100,horizon/20); cap=min(100,horizon/100)*(.5 if fine else 1)
                times,values,trace,meta=r.clock.integrate(system,horizon,sample,cap)
                data=dict(initial=initial,final=system.cc_cells.copy(),times=times,concentrations=values,**trace)
                checks=a.Checks(); a.audit_clock(data,dict(phase='kernel',requested_horizon=horizon,clock=meta),d.case(fine=fine),checks)
                self.assertTrue(all(checks.rows.values()),[k for k,v in checks.rows.items() if not v])
                self.assertGreaterEqual(len(times),21)
    def test_selection_uses_shared_actual_retention(self):
        self.assertEqual(self.selection,d.select(self.by)); self.assertEqual(self.selection,a.selection_from(self.by))
        self.assertEqual([self.selection[s]['tau'] for s in d.SCHEMES[:3]],[10,100,20000])
        self.assertTrue(self.by[d.case(founder='stock_E')['id']]['retained_E'])
        by=copy.deepcopy(self.by); by[d.case(tau=10,fine=True)['id']]['retained_E']=False
        self.assertEqual(a.selection_from(by)['single']['tau'],100)
    def test_selection_no_success_fallback_unconditional(self):
        by=copy.deepcopy(self.by)
        for c in d.stage_cases('screen'): by[c['id']]['retained_E']=False
        chosen=a.selection_from(by); self.assertEqual(chosen,d.select(by))
        self.assertTrue(all(v==dict(tau=20000,reason='no_shared_retention') for v in chosen.values()))
        self.assertEqual(len(d.fixed_cases(chosen)),234)
    def test_selection_missing_sources_cannot_qualify(self):
        by=copy.deepcopy(self.by); by.pop(d.case(tau=10,founder='ordinary',fine=True)['id'])
        self.assertEqual(a.selection_from(by)['single']['tau'],100)
        self.assertEqual(d.select({}),a.selection_from({}))
    def test_selection_nonmonotonic_grid_keeps_fastest_tested(self):
        by=copy.deepcopy(self.by)
        for c in d.stage_cases('screen'):
            if c['tau']==100: by[c['id']]['retained_E']=False
        self.assertEqual(a.selection_from(by)['single']['tau'],10)
    def test_negative_science_is_complete(self):
        out=self.fabricated('all_negative'); self.assertFalse(out['retained_E']); self.assertEqual(len(out['replacements']),6)
        out=self.fabricated('all_negative',d.case('onward',tau=10,readout='open')); self.assertFalse(out['transmitted_E'])
    def test_isolation_failure_separate_from_correction(self):
        out=self.fabricated('isolation'); self.assertTrue(out['all_windows_E']); self.assertFalse(out['retained_E'])
    def test_late_occupancy_separate_from_endpoint(self):
        out=self.fabricated('late'); self.assertEqual(out['observations']['isolated_1']['patch_labels'],'EEE')
        self.assertFalse(out['retained_E'])
    def test_delayed_retention_does_not_repair_earlier_windows(self):
        out=self.fabricated('late_recovery',d.case(tau=1))
        self.assertTrue(out['retained_E']); self.assertFalse(out['all_windows_E']); self.assertFalse(out['continuous_renewal'])
    def test_wipe_negative_in_fixture_and_no_onward_selection(self):
        self.assertFalse(any(self.by[c['id']]['retained_E'] for c in d.stage_cases('screen') if c['scheme']=='wipe'))
        self.assertFalse(any(c['scheme']=='wipe' for c in d.stage_cases('onward',self.selection)))
    def test_positive_controls_invalidate_qualification(self):
        c=d.case('onward',tau=10,readout='rna'); out=self.fabricated('positive_controls',c)
        self.assertTrue(out['transmitted_E']); by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case('onward',tau=10,readout='rna',fine=f)['id']]=out
        chain=a.contrasts(by,self.selection)['chain_outcomes'][0]
        self.assertTrue(chain['raw_retention_and_onward']); self.assertFalse(chain['control_qualified_chain'])
    def test_missing_capacity_and_onward_controls_cannot_qualify(self):
        by=copy.deepcopy(self.by); by.pop(d.case('baseline',readout='cut')['id'])
        report=a.contrasts(by,self.selection); self.assertFalse(report['readout_capacity']['qualified'])
        self.assertFalse(any(x['benchmark_supported_chain'] for x in report['chain_outcomes']))
        by=copy.deepcopy(self.by); by.pop(d.case('onward',tau=10,readout='cut')['id'])
        self.assertFalse(a.contrasts(by,self.selection)['chain_outcomes'][0]['control_qualified_chain'])
    def test_onward_cannot_repair_failed_retention(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(tau=10,fine=f)['id']]['retained_E']=False
        row=a.contrasts(by,self.selection)['chain_outcomes'][0]
        self.assertTrue(row['onward_transmission_both']); self.assertFalse(row['raw_retention_and_onward'])
    def test_positive_wipe_invalidates_carrier_dependent_chain(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(scheme='wipe',tau=10,fine=f)['id']]['retained_E']=True
        report=a.contrasts(by,self.selection); row=report['chain_outcomes'][0]
        self.assertTrue(row['raw_retention_and_onward']); self.assertTrue(row['control_qualified_transmission'])
        self.assertFalse(row['control_qualified_chain']); self.assertFalse(row['benchmark_supported_chain'])
        self.assertFalse(report['selected_contrasts'][0]['carrier_dependent_retention'])
    def test_missing_wipe_cannot_qualify_chain(self):
        by=copy.deepcopy(self.by); by.pop(d.case(scheme='wipe',tau=10,fine=True)['id'])
        row=a.contrasts(by,self.selection)['chain_outcomes'][0]
        self.assertTrue(row['raw_retention_and_onward']); self.assertFalse(row['negative_wipe_both'])
        self.assertFalse(row['control_qualified_chain'])
    def test_wipe_controls_do_not_choose_followup_interval(self):
        by=copy.deepcopy(self.by)
        for c in d.stage_cases('screen'):
            if c['scheme']=='wipe': by[c['id']]['retained_E']=True
        self.assertEqual(d.select(by),self.selection); self.assertEqual(a.selection_from(by),self.selection)
    def test_all_negative_readout_preserves_denominators(self):
        by=copy.deepcopy(self.by)
        for c in self.cases:
            if c['readout']: by[c['id']]['transmitted_E']=False
        result=a.contrasts(by,self.selection); self.assertEqual(len(result['chain_outcomes']),18)
        self.assertFalse(any(x['raw_retention_and_onward'] for x in result['chain_outcomes']))
        self.assertTrue(all(x['source_trials']==1 for x in result['chain_outcomes']))
    def test_fine_disagreement_is_technical_failure(self):
        by=copy.deepcopy(self.by); by[d.case(tau=10,fine=True)['id']]['retained_E']=False
        endpoints={c['id']:{'end':dict(final=np.ones((17,3)))} for c in self.cases}
        checks=a.Checks(); a.p12.compare_fine(self.cases,by,endpoints,checks); self.assertFalse(all(checks.rows.values()))
    def test_rehashed_survivor_reset_rejected(self):
        self.corrupt_array('replacement_01',lambda x:x['initial'].__setitem__((7,1),x['initial'][7,1]+1))
    def test_rehashed_second_cycle_reset_rejected(self):
        self.corrupt_array('replacement_04',lambda x:x['initial'].__setitem__((7,2),x['initial'][7,2]+1))
    def test_rehashed_incoming_change_rejected(self):
        self.corrupt_array('replacement_01',lambda x:x['initial'].__setitem__((0,0),x['initial'][0,0]+1))
    def test_rehashed_edge_cut_rejected(self):
        self.corrupt_array('replacement_01',lambda x:x['edge_available_initial'].__setitem__(0,0))
    def test_rehashed_clock_tick_rejected(self):
        self.corrupt_array('replacement_01',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))
    def test_rehashed_short_sampling_change_rejected(self):
        self.corrupt_array('replacement_01',lambda x:x['times'].__setitem__(1,x['times'][1]+.01))
    def test_rehashed_onward_donor_reset_rejected(self):
        self.corrupt_array('contact',lambda x:x['initial'].__setitem__((7,0),x['initial'][7,0]+1),d.case('onward',tau=10,readout='open'))
    def test_wrong_id_clock_and_claim_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(1,'wrong'))
        self.corrupt_result(lambda x:x['phases'][0].__setitem__('logical_interval',[0,10]))
        self.corrupt_result(lambda x:x.__setitem__('autonomous_reproduction',True))
    def test_forged_retention_rejected(self):
        self.corrupt_result(lambda x:x['outcome'].__setitem__('retained_E',False))
    def test_extra_and_missing_phase_rejected(self):
        with self.copied_case() as (run,folder):
            shutil.copyfile(folder/'replacement_01.npz',folder/'unregistered.npz')
            checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))
        with self.copied_case() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['phases'].pop(); d.write_json(folder/'result.json',result)
            with self.assertRaises(ValueError): self.audit_branch(run,self.primary)
    def test_predecessor_requires_original_and_archive(self):
        saved=json.loads((self.fixture_run/'inputs/p15/independent_audit.json').read_text())
        for fn in (r.predecessor_audit,a.predecessor_audit):
            archived=copy.deepcopy(saved); archived['run']=str(self.fixture_run/'inputs/p15')
            with patch.object(a.p15,'analyze',side_effect=[copy.deepcopy(saved),archived]) as check:
                self.assertTrue(fn(self.fixture_run)['quality_gate']); self.assertEqual(check.call_count,2)
            archived['quality_gate']=False
            with patch.object(a.p15,'analyze',side_effect=[copy.deepcopy(saved),archived]): self.assertFalse(fn(self.fixture_run)['quality_gate'])

    def flow(self,technical=True,execution=True,preflight=True):
        with tempfile.TemporaryDirectory(prefix='p16-flow-') as temp,redirect_stdout(io.StringIO()):
            output=Path(temp)/'output'; output.mkdir(); calls=[]
            def worker(c,config,run,deadline,env):
                calls.append(c); return dict(id=c['id'],execution_pass=execution)
            history=dict(self.history,quality_gate=preflight)
            with patch.object(r.tempfile,'mkdtemp',return_value=str(output)),patch.object(r,'freeze',return_value=({}, {}, {})),\
                 patch.object(r,'predecessor_audit',return_value=history),patch.object(r,'run_worker',side_effect=worker),\
                 patch.object(a,'stage_audit',return_value=dict(quality_gate=technical,eligible=True,selection=a.selection_from({}))),\
                 patch.object(a,'integrity',return_value={'fixture':True}),patch.object(d,'source_check'):
                try: code=r.run(d.ROOT/'configs/paper_turnover_limit_v1.json')
                except RuntimeError:
                    if preflight: raise
                    code=1
            return code,calls,json.loads((output/'summary.json').read_text())
    def test_all_fixed_stages_unconditional_on_science(self):
        code,calls,s=self.flow(); self.assertEqual((code,len(calls)),(0,234))
        self.assertEqual(len({c['id'] for c in calls}),234); self.assertEqual(s['attempted_stages'],list(d.STAGES))
        self.assertEqual(s['completion_reason'],'all_registered_stages_completed')
    def test_technical_and_execution_failures_stop_without_retry(self):
        for kw in ({'technical':False},{'execution':False}):
            code,calls,_=self.flow(**kw); self.assertEqual((code,len(calls)),(1,12))
    def test_preflight_failure_no_integrations(self):
        code,calls,_=self.flow(preflight=False); self.assertEqual((code,len(calls)),(1,0))
    def test_expired_worker_does_not_launch(self):
        with patch.object(r.subprocess,'run') as launch:
            result=r.run_worker(self.primary,d.FIXED,Path('/tmp'),time.monotonic()-1,{})
        launch.assert_not_called(); self.assertFalse(result['execution_pass'])
    def test_worker_guards_before_instantiation(self):
        for failure in ('case','stage','preflight','hash','draw','gate','selection','parent','parent_raw'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                run=Path(temp); (run/'frozen').mkdir()
                c=d.case('onward',tau=10,readout='open') if failure in ('selection','parent','parent_raw') else d.case('baseline',readout='open')
                if failure=='gate': c=d.case(tau=10)
                if failure=='case': c['route']='unregistered'
                folder=run/c['id']; folder.mkdir()
                d.write_json(folder/'spec.json',dict(config=d.FIXED,case=c,inputs=str(run/'inputs')))
                d.write_json(run/'predecessor_audit.json',self.history)
                summary=dict(stage='wrong' if failure=='stage' else c['stage'],predecessor_gate=failure!='preflight',
                    predecessor_audit=self.history,predecessor_audit_sha256='bad' if failure=='hash' else d.digest(run/'predecessor_audit.json'),
                    gates={},gate_hashes={},cases=[],selection=self.selection)
                for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
                    gate=dict(quality_gate=failure!='gate',selection={} if failure=='selection' else self.selection)
                    d.write_json(run/(stage+'_audit.json'),gate)
                    summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(run/(stage+'_audit.json'))
                if failure=='parent_raw':
                    parent=d.parent(c)['id']; shutil.copytree(self.fixture_run/parent,run/parent)
                    row=copy.deepcopy(next(x for x in self.summary['cases'] if x['id']==parent)); summary['cases']=[row]
                    (run/parent/'isolated_2.npz').write_bytes(b'changed')
                d.write_json(run/'summary.json',summary)
                d.write_json(run/'frozen/paper_turnover_limit_draws_v1.json',{} if failure=='draw' else d.draw_book())
                with self.assertRaises(ValueError),patch.object(r,'RateExperiment') as exp: r.worker(folder/'spec.json')
                exp.assert_not_called()

    def supervisor_fixture(self,verification_rc=0,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p16-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-turnover-limit-test'; job.mkdir(parents=True)
            run=root/'runs/paper-turnover-limit-test'; run.mkdir()
            source=root/'source'; source.write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={str(source):'bad' if bad_input else d.digest(source)}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time()))
            (job/'runner.log').write_text('Run artifacts: '+str(run)+'\n')
            d.write_json(run/'summary.json',dict(cases=[],registered_cases=[],stage='finished',
                completion_reason='all_registered_stages_completed',gates={}))
            d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,independent_check_count=1,
                all_fine_agree=True,readout_capacity={},selection={},selected_contrasts=[],chain_outcomes=[]))
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
    def test_supervisor_success_and_bounds(self):
        code,meta,calls=self.supervisor_fixture(); self.assertEqual(code,0)
        self.assertEqual(meta['phase'],'complete'); self.assertEqual(calls,['verification.log','runner.log','audit.log'])
    def test_verification_failure_or_timeout_blocks_science(self):
        for rc in (1,124):
            code,meta,calls=self.supervisor_fixture(verification_rc=rc)
            self.assertEqual(code,1); self.assertEqual(calls,['verification.log']); self.assertEqual(meta['phase'],'failed')
    def test_runner_timeout_no_retry(self):
        code,_,calls=self.supervisor_fixture(runner_rc=124); self.assertEqual(code,1)
        self.assertEqual(calls,['verification.log','runner.log'])
    def test_bad_audit_not_success(self):
        code,meta,_=self.supervisor_fixture(audit_quality=False); self.assertEqual(code,1); self.assertEqual(meta['phase'],'failed')
    def test_changed_input_blocks_everything(self):
        code,_,calls=self.supervisor_fixture(bad_input=True); self.assertEqual((code,calls),(1,[]))
    def test_status_does_not_relaunch(self):
        with tempfile.TemporaryDirectory() as temp:
            job=Path(temp); d.write_json(job/'status.json',dict(phase='turnover',heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)['heartbeat_stale'])
            (job/'runner.log').write_text('Run artifacts: /tmp/unrelated\n')
            with self.assertRaises(ValueError): detached.discover_run(job)

if __name__=='__main__': unittest.main()
