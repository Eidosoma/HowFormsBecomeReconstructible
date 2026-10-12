"""P15 synthetic software fixtures and archived replay; not new scientific integrations."""
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
import paper_tissue_dependence_design as d
import run_paper_tissue_dependence as r
import analyze_paper_tissue_dependence as a
import run_paper_tissue_dependence_detached as detached

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir()
    exp=r.ClockBoundedExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs):
        current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy()
        if c['stage']=='turnover' and c['carrier']=='actual' and c['route']=='tissue':
            # Reuse saved arrays as a software replay fixture. No dynamics run here.
            src=run/'inputs/p14'/d.source(c); archived=a.arrays(src,name)
            np.testing.assert_array_equal(initial,archived['initial'])
            np.copyto(sim.cc_cells,archived['final'])
            records=json.loads((src/'result.json').read_text())['phases']
            meta=next(rec['clock'] for rec in records if rec['phase']==name)
            return archived['times'],archived['concentrations'],{
                k:archived[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        def mark(indices,lab):
            setter=exp.z.GRN.set_very_healthy if lab=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        is_turn=c['stage']=='turnover'
        if is_turn and name.startswith('replacement'):
            if c['route']!='patch_rna' and failure!='all_negative': mark(d.PATCH,'E')
            if failure=='all_negative': mark(d.PATCH,'M')
        if not is_turn and name=='contact':
            donor_E=all(exp.z.GRN.state_char(x)=='E' for x in initial[:,:3].T)
            if (c['readout']=='open' and donor_E and failure!='all_negative') or failure=='positive_controls':
                mark(range(3,6),'E')
        if failure==name:
            mark([d.PATCH[-1] if len(exp.ids)==169 else len(exp.ids)-1],'M')
        if failure=='isolation' and name.startswith('isolated'): mark([2],'M')
        if failure=='spread' and len(exp.ids)==169: mark([0],'M')
        sim.cc_cells[0]+=(.0011 if c['fine'] else .001)+.000001*np.arange(len(exp.ids))
        base=sim.GP.time_step; total=round(horizon/base); stride=round(sample_interval/base); cap=round(max_step/base)
        steps=np.full(total//cap,cap,dtype=np.int64); proposed=np.full(len(steps),2*stride,dtype=np.int64)
        shots=np.arange(0,total+1,stride,dtype=np.int64); times=shots*base
        values=np.repeat(sim.cc_cells[None,:,:],len(times),axis=0); values[0]=initial
        if failure=='late' and name in ('replacement_1','isolated_1'):
            pos=d.PATCH[-1] if len(exp.ids)==169 else 2
            for at in range(-2,-7,-1): exp.z.GRN.set_very_tumor(values[at],pos)
        meta=dict(method=r.clock.METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
            requested_horizon=horizon,actual_final_time=horizon,total_ticks=total,adaptive=True,
            iterations=len(steps),sample_count=len(shots),capped_steps=len(steps),initial_and_final_samples=True,integer_tick_clock=True)
        return times,values,dict(clock_step_ticks=steps,clock_proposed_ticks=proposed,clock_sample_ticks=shots),meta
    with patch.object(exp,'phase',side_effect=phase),patch.object(r.clock,'integrate',side_effect=fake_clock):
        out=r.trajectory(exp,c,run)
    result=r.result_record(exp,c,out); d.write_json(folder/'result.json',result)
    return dict(id=c['id'],execution_pass=True,status='finished',returncode=0,result=result,result_sha256=d.digest(folder/'result.json'))

class TestTissueDependence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p15-software-'); cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir()
        hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_matches_saved=True,
            prior_checks=18273,prior_cases=36,prior_calls=288,actual_pre_replacement_sources=True)
        d.write_json(cls.fixture_run/'predecessor_audit.json',cls.history)
        cls.summary=dict(revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],
            hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,predecessor_gate=True,
            predecessor_audit=cls.history,predecessor_audit_sha256=d.digest(cls.fixture_run/'predecessor_audit.json'),
            gates={},gate_hashes={},attempted_stages=list(d.STAGES))
        with redirect_stdout(io.StringIO()):
            for stage in d.STAGES:
                for c in d.stage_cases(stage): cls.summary['cases'].append(fixture_case(cls.fixture_run,c))
                d.write_json(cls.fixture_run/'summary.json',cls.summary)
                gate=a.stage_audit(cls.fixture_run,stage)
                if not gate['quality_gate']:
                    raise AssertionError([k for k,v in gate['checks'].items() if not v] or gate['integrity'])
                d.write_json(cls.fixture_run/(stage+'_audit.json'),gate)
                cls.summary['gates'][stage]=gate; cls.summary['gate_hashes'][stage]=d.digest(cls.fixture_run/(stage+'_audit.json'))
            cls.summary.update(all_execution_valid=True,completion_reason='all_registered_stages_completed',stage='finished')
            d.write_json(cls.fixture_run/'summary.json',cls.summary)
            with patch.object(a,'predecessor_audit',return_value=cls.history): cls.report=a.analyze(cls.fixture_run)
        cls.primary=d.case(); cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p15-unit-') as temp:
            run=Path(temp); (run/'inputs').symlink_to(self.fixture_run/'inputs',target_is_directory=True)
            for c in d.stage_cases('turnover'):
                (run/c['id']).symlink_to(self.fixture_run/c['id'],target_is_directory=True)
            yield run
    def audit_branch(self,run,c):
        checks=a.Checks(); report,data=a.branch(run/c['id'],c,checks)
        return checks,report,data
    @contextmanager
    def copied_case(self,c=None):
        c=self.primary if c is None else c
        with self.isolated_run() as run:
            folder=run/c['id']
            if folder.is_symlink(): folder.unlink()
            shutil.copytree(self.fixture_run/c['id'],folder)
            yield run,folder
    def fabricated(self,mode,c=None):
        c=self.primary if c is None else c
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            if (run/c['id']).is_symlink(): (run/c['id']).unlink()
            fixture_case(run,c,mode); checks,report,data=self.audit_branch(run,c)
            self.assertTrue(all(checks.rows.values()),[k for k,v in checks.rows.items() if not v])
            self.assertEqual(len(data),5 if c['stage']=='turnover' else 3)
            return report['outcome']
    def corrupt_array(self,name,change,c=None):
        c=self.primary if c is None else c
        with self.copied_case(c) as (run,folder):
            value=a.arrays(folder,name); change(value)
            np.savez_compressed(folder/(name+'.npz'),**value)
            result=json.loads((folder/'result.json').read_text())
            next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))
    def corrupt_result(self,change,c=None):
        c=self.primary if c is None else c
        with self.copied_case(c) as (run,folder):
            result=json.loads((folder/'result.json').read_text()); change(result)
            d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def test_registration_bounds_and_draw_book(self):
        self.assertEqual(d.fixed_cases(),a.expected_cases())
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[6,24,72])
        self.assertEqual(len({c['id'] for c in d.fixed_cases()}),102)
        self.assertEqual(sum(c['fine'] for c in d.fixed_cases()),51)
        self.assertEqual(d.validate_config(json.loads((d.ROOT/'configs/paper_tissue_dependence_v1.json').read_text())),d.FIXED)
        self.assertEqual(d.draw_book(),a.expected_draws())
        for key,value in (('source_arm','both'),('source_seed',302),('maximum_cases',103),('workers',3)):
            cfg=copy.deepcopy(d.FIXED); cfg[key]=value
            with self.assertRaises(ValueError): d.validate_config(cfg)
    def test_manifest_and_native_source(self):
        self.assertEqual(len(d.LOCAL_FILES),123); self.assertEqual(len(d.execution_manifest()),159)
        self.assertEqual(len(d.input_paths()),5960); d.source_check()
        self.assertTrue(all(a.integrity(self.fixture_run,self.summary).values()))
    def test_full_synthetic_audit(self):
        self.assertTrue(self.report['quality_gate'],[k for k,v in self.report['checks'].items() if not v])
        self.assertEqual((self.report['completed_cases'],self.report['integration_calls']),(102,354))
        self.assertEqual(len(self.report['fine_comparisons']),51); self.assertTrue(self.report['all_fine_agree'])
        self.assertTrue(self.report['readout_capacity']['qualified'])
        self.assertTrue(all(s['patch_RNA_dependence'] for s in self.report['support_contrasts']))
    def test_draws_change_only_protein_and_reuse_P14(self):
        for f in (False,True):
            _,M=r.stock(self.fixture_run,f)
            for i in range(3):
                x=d.incoming(M,i); np.testing.assert_array_equal(x,a.incoming(M,i))
                np.testing.assert_array_equal(x[np.arange(17)!=7],M[np.arange(17)!=7])
                self.assertEqual(''.join(a.labels(x,a.INDEX)),'M')
                archived=a.arrays(self.fixture_run/'inputs/p14'/d.source(d.case(fine=f)),'replacement_'+str(i+1))
                np.testing.assert_array_equal(x,archived['initial'][:,d.PATCH[i]:d.PATCH[i]+1])
    def test_actual_sources_background_and_ids(self):
        for c in d.stage_cases('turnover'):
            archived=a.arrays(self.fixture_run/'inputs/p14'/d.source(c),'withdrawal_2')['final']
            first=a.arrays(self.fixture_run/c['id'],'replacement_1')['initial']
            E,_=r.stock(self.fixture_run,c['fine']); keep=[i for i in range(169) if i not in d.PATCH]
            np.testing.assert_array_equal(first[:,keep],archived[:,keep])
            expected=archived[:,list(d.PATCH[1:])] if c['carrier']=='actual' else np.repeat(E,2,axis=1)
            np.testing.assert_array_equal(first[:,list(d.PATCH[1:])],expected)
            ids=self.by[c['id']]['original_ids']
            self.assertEqual(ids,[a.source_ids(c)[p] for p in d.PATCH] if c['carrier']=='actual' else d.stock_ids(c))
    def test_boundary_cut_preserves_internal_edges(self):
        for route in d.ROUTES:
            c=d.case(route=route); data=a.arrays(self.fixture_run/c['id'],'replacement_1')
            region=data['edge_region_initial']; available=data['edge_available_initial']
            self.assertEqual((len(region),sum(region==1),sum(region==2)),(312,2,8))
            self.assertTrue(np.all(available[region!=2]==1))
            self.assertTrue(np.all(available[region==2]==(1 if route=='tissue' else 0)))
            self.assertTrue(np.all(data['edge_power_initial'][region==1]==60))
            rec=next(x for x in self.summary['cases'] if x['id']==c['id'])['result']['phases'][0]
            self.assertEqual(rec['setup']['mirna_kd'],0 if route=='patch_rna' else 1.25e-14)
            self.assertTrue(data['junction_diffusion'][:4].any())
    def test_exact_archived_replay_all_arrays(self):
        for c in d.stage_cases('turnover'):
            if c['carrier']!='actual' or c['route']!='tissue': continue
            checks,_,data=self.audit_branch(self.fixture_run,c)
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),5*33); self.assertTrue(all(replay))
    def test_every_original_removed_one_column_at_a_time(self):
        for c in d.stage_cases('turnover'):
            before=None
            for i,pos in enumerate(d.PATCH):
                data=a.arrays(self.fixture_run/c['id'],'replacement_'+str(i+1))
                if before is not None:
                    keep=np.arange(169)!=pos; np.testing.assert_array_equal(data['initial'][:,keep],before[:,keep])
                before=data['final']
            isolated=a.arrays(self.fixture_run/c['id'],'isolated_1')
            np.testing.assert_array_equal(isolated['initial'],before[:,list(d.PATCH)])
            self.assertFalse(isolated['junction_diffusion'].any())
            self.assertEqual([x['inserted'] for x in self.by[c['id']]['replacements']],[d.new_id(c,i) for i in range(3)])
    def test_onward_uses_actual_parent_even_when_negative(self):
        for c in d.stage_cases('onward'):
            initial=a.arrays(self.fixture_run/c['id'],'contact')['initial']
            donors=a.arrays(self.fixture_run/d.parent(c)['id'],'isolated_2')['final']
            np.testing.assert_array_equal(initial[:,:3],donors)
            self.assertEqual(''.join(a.labels(initial[:,3:],a.INDEX)),'MMM')
            result=next(x for x in self.summary['cases'] if x['id']==c['id'])['result']
            self.assertEqual(len(result['phases']),3)
            self.assertFalse(set(result['phases'][0]['setup']['cell_ids'][:3])&set(result['phases'][-1]['setup']['cell_ids']))
    def test_timeline_and_fine_sources(self):
        for c in d.fixed_cases():
            records=next(x for x in self.summary['cases'] if x['id']==c['id'])['result']['phases']
            cursor={'readout':0,'turnover':1060000,'onward':1140000}[c['stage']]
            for rec in records:
                self.assertEqual(rec['logical_interval'],[cursor,cursor+rec['requested_horizon']]); cursor+=rec['requested_horizon']
            self.assertEqual(cursor,{'readout':40000,'turnover':1140000,'onward':1180000}[c['stage']])
            if c['stage']=='turnover': self.assertEqual(d.source(c).endswith('__fine'),c['fine'])
    def test_negative_science_retains_every_phase(self):
        out=self.fabricated('all_negative'); self.assertFalse(out['renewal_success'])
        out=self.fabricated('all_negative',d.case('readout',readout='open')); self.assertFalse(out['transmitted_E'])
    def test_any_replacement_failure_disqualifies(self):
        for n in (1,2,3):
            out=self.fabricated('replacement_'+str(n)); self.assertFalse(out['renewal_success'])
            self.assertTrue(out['isolated_E_memory'] if n<3 else not out['isolated_E_memory'])
    def test_late_occupancy_separate_from_endpoint(self):
        out=self.fabricated('late'); self.assertEqual(out['observations']['replacement_1']['patch_labels'],'EEE')
        self.assertFalse(out['renewal_success'])
        out=self.fabricated('late',d.case('readout',readout='open')); self.assertFalse(out['transmitted_E'])
    def test_isolated_retention_failure(self):
        out=self.fabricated('isolation'); self.assertTrue(out['all_replacements_corrected'])
        self.assertFalse(out['isolated_E_memory']); self.assertFalse(out['renewal_success'])
    def test_background_spread_observed(self):
        out=self.fabricated('spread'); self.assertEqual(out['observations']['replacement_3']['maximum_background_E_now_M'],1)
    def test_positive_controls_are_science_not_gate_failure(self):
        out=self.fabricated('positive_controls',d.case('onward',readout='rna'))
        self.assertTrue(out['transmitted_E'])
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case('onward',readout='rna',fine=f)['id']]=out
        row=next(x for x in a.contrasts(by)[2] if x['history']=='written' and x['carrier']=='actual' and x['route']=='patch')
        self.assertTrue(row['raw_full_chain']); self.assertFalse(row['control_qualified_full_chain'])
    def test_failed_turnover_cannot_be_repaired_by_readout(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case(fine=f)['id']]['renewal_success']=False
        row=next(x for x in a.contrasts(by)[2] if x['history']=='written' and x['carrier']=='actual' and x['route']=='patch')
        self.assertTrue(row['onward_transmission_both']); self.assertFalse(row['raw_full_chain'])
    def test_missing_controls_and_failed_capacity_do_not_qualify(self):
        by=copy.deepcopy(self.by); by.pop(d.case('readout',readout='cut')['id'])
        capacity,_,chains=a.contrasts(by); self.assertFalse(capacity['qualified'])
        self.assertFalse(any(x['benchmark_supported_full_chain'] for x in chains))
        by=copy.deepcopy(self.by); by.pop(d.case('onward',readout='cut')['id'])
        row=next(x for x in a.contrasts(by)[2] if x['history']=='written' and x['carrier']=='actual' and x['route']=='patch')
        self.assertFalse(row['control_qualified_full_chain'])
    def test_zero_onward_success_panel_preserves_denominators(self):
        by=copy.deepcopy(self.by)
        for c in d.fixed_cases():
            if c['stage']!='turnover': by[c['id']]['transmitted_E']=False
        capacity,support,chains=a.contrasts(by)
        self.assertFalse(capacity['qualified']); self.assertEqual((len(support),len(chains)),(4,12))
        self.assertFalse(any(x['raw_full_chain'] for x in chains))
        self.assertTrue(all(x['source_trials']==1 for x in support+chains))
    def test_all_four_support_classifications(self):
        for t,p,name in ((True,True,'both_renew'),(True,False,'tissue_only'),(False,True,'patch_only'),(False,False,'neither')):
            by=copy.deepcopy(self.by)
            for f in (False,True):
                by[d.case(route='tissue',fine=f)['id']]['renewal_success']=t
                by[d.case(route='patch',fine=f)['id']]['renewal_success']=p
            self.assertEqual(a.contrasts(by)[1][0]['comparison'],name)
    def test_fine_disagreement_is_technical_failure(self):
        by=copy.deepcopy(self.by); by[d.case(fine=True)['id']]['renewal_success']=False
        endpoints={c['id']:{'end':dict(final=np.ones((17,3)))} for c in d.fixed_cases()}
        checks=a.Checks(); a.p12.compare_fine(d.fixed_cases(),by,endpoints,checks)
        self.assertFalse(all(checks.rows.values()))
    def test_rehashed_old_carrier_reset_caught(self):
        self.corrupt_array('replacement_1',lambda x:x['initial'].__setitem__((7,84),x['initial'][7,84]+1))
    def test_rehashed_background_reset_caught(self):
        self.corrupt_array('replacement_2',lambda x:x['initial'].__setitem__((7,0),x['initial'][7,0]+1))
    def test_rehashed_incoming_state_corruption_caught(self):
        self.corrupt_array('replacement_2',lambda x:x['initial'].__setitem__((1,84),x['initial'][1,84]+1))
    def test_rehashed_boundary_reopening_caught(self):
        def reopen(x): x['edge_available_initial'][x['edge_region_initial']==2]=1
        self.corrupt_array('replacement_1',reopen)
    def test_rehashed_internal_cut_caught(self):
        def cut(x): x['edge_available_initial'][x['edge_region_initial']==1]=0
        self.corrupt_array('replacement_1',cut)
    def test_rehashed_clock_corruption_caught(self):
        self.corrupt_array('replacement_1',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))
    def test_rehashed_onward_donor_reset_caught(self):
        self.corrupt_array('contact',lambda x:x['initial'].__setitem__((7,0),x['initial'][7,0]+1),d.case('onward',readout='open'))
    def test_rehashed_onward_recipient_reset_caught(self):
        self.corrupt_array('contact',lambda x:x['initial'].__setitem__((7,3),x['initial'][7,3]+1),d.case('onward',readout='open'))
    def test_rehashed_replay_change_caught(self):
        self.corrupt_array('replacement_1',lambda x:x['concentrations'].__setitem__((1,0,0),x['concentrations'][1,0,0]+.1),d.case(route='tissue'))
    def test_wrong_id_time_and_claim_caught(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(84,'wrong'))
        self.corrupt_result(lambda x:x['phases'][0].__setitem__('logical_interval',[0,20000]))
        self.corrupt_result(lambda x:x.__setitem__('autonomous_reproduction',True))
    def test_forged_outcome_caught(self):
        self.corrupt_result(lambda x:x['outcome'].__setitem__('renewal_success',False))
    def test_extra_and_missing_phase_caught(self):
        with self.copied_case() as (run,folder):
            shutil.copyfile(folder/'replacement_1.npz',folder/'unregistered.npz')
            checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))
        with self.copied_case() as (run,folder):
            result=json.loads((folder/'result.json').read_text()); result['phases'].pop()
            d.write_json(folder/'result.json',result)
            with self.assertRaises(ValueError): self.audit_branch(run,self.primary)
    def test_predecessor_requires_both_exact_audits(self):
        saved=json.loads((self.fixture_run/'inputs/p14/independent_audit.json').read_text())
        for fn in (r.predecessor_audit,a.predecessor_audit):
            archived=copy.deepcopy(saved); archived['run']=str(self.fixture_run/'inputs/p14')
            with patch.object(a.p14,'analyze',side_effect=[copy.deepcopy(saved),archived]) as check:
                self.assertTrue(fn(self.fixture_run)['quality_gate']); self.assertEqual(check.call_count,2)
            archived['quality_gate']=False
            with patch.object(a.p14,'analyze',side_effect=[copy.deepcopy(saved),archived]):
                self.assertFalse(fn(self.fixture_run)['quality_gate'])

    def flow(self,technical=True,execution=True,preflight=True):
        with tempfile.TemporaryDirectory(prefix='p15-flow-') as temp,redirect_stdout(io.StringIO()):
            output=Path(temp)/'output'; output.mkdir(); calls=[]
            def worker(c,config,run,deadline,env):
                calls.append(c); return dict(id=c['id'],execution_pass=execution)
            history=dict(self.history,quality_gate=preflight)
            with patch.object(r.tempfile,'mkdtemp',return_value=str(output)),patch.object(r,'freeze',return_value=({}, {}, {})),\
                 patch.object(r,'predecessor_audit',return_value=history),patch.object(r,'run_worker',side_effect=worker),\
                 patch.object(a,'stage_audit',return_value=dict(quality_gate=technical,eligible=True)),\
                 patch.object(a,'integrity',return_value={'fixture':True}),patch.object(d,'source_check'):
                try: code=r.run(d.ROOT/'configs/paper_tissue_dependence_v1.json')
                except RuntimeError:
                    if preflight: raise
                    code=1
            return code,calls,json.loads((output/'summary.json').read_text())
    def test_all_fixed_stages_unconditional_on_science(self):
        code,calls,s=self.flow(); self.assertEqual((code,len(calls)),(0,102))
        self.assertEqual(len({c['id'] for c in calls}),102); self.assertEqual(s['attempted_stages'],list(d.STAGES))
        self.assertEqual(s['completion_reason'],'all_registered_stages_completed')
    def test_technical_and_execution_failures_stop_without_retry(self):
        for kw in ({'technical':False},{'execution':False}):
            code,calls,_=self.flow(**kw); self.assertEqual((code,len(calls)),(1,6))
    def test_preflight_failure_no_integrations(self):
        code,calls,_=self.flow(preflight=False); self.assertEqual((code,len(calls)),(1,0))
    def test_expired_worker_does_not_launch(self):
        with patch.object(r.subprocess,'run') as launch:
            result=r.run_worker(self.primary,d.FIXED,Path('/tmp'),time.monotonic()-1,{})
        launch.assert_not_called(); self.assertFalse(result['execution_pass'])
    def test_worker_guards_before_instantiation(self):
        for failure in ('case','stage','preflight','hash','draw','gate','parent','parent_raw'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                run=Path(temp); (run/'frozen').mkdir()
                c=d.case('onward',readout='open') if failure in ('parent','parent_raw') else d.case('readout',readout='open')
                if failure=='gate': c=d.case()
                if failure=='case': c['route']='unregistered'
                folder=run/c['id']; folder.mkdir()
                d.write_json(folder/'spec.json',dict(config=d.FIXED,case=c,inputs=str(run/'inputs')))
                d.write_json(run/'predecessor_audit.json',self.history)
                summary=dict(stage='wrong' if failure=='stage' else c['stage'],predecessor_gate=failure!='preflight',
                    predecessor_audit=self.history,predecessor_audit_sha256='bad' if failure=='hash' else d.digest(run/'predecessor_audit.json'),
                    gates={},gate_hashes={},cases=[])
                for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
                    gate=dict(quality_gate=failure!='gate'); d.write_json(run/(stage+'_audit.json'),gate)
                    summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(run/(stage+'_audit.json'))
                if failure=='parent_raw':
                    parent=d.parent(c)['id']; shutil.copytree(self.fixture_run/parent,run/parent)
                    row=copy.deepcopy(next(x for x in self.summary['cases'] if x['id']==parent)); summary['cases']=[row]
                    (run/parent/'isolated_2.npz').write_bytes(b'changed')
                d.write_json(run/'summary.json',summary)
                d.write_json(run/'frozen/paper_tissue_dependence_draws_v1.json',{} if failure=='draw' else d.draw_book())
                with self.assertRaises(ValueError),patch.object(r,'ClockBoundedExperiment') as exp: r.worker(folder/'spec.json')
                exp.assert_not_called()

    def supervisor_fixture(self,verification_rc=0,runner_rc=0,audit_quality=True,bad_input=False):
        with tempfile.TemporaryDirectory(prefix='p15-supervisor-') as temp:
            root=Path(temp); job=root/'runs/jobs/paper-tissue-dependence-test'; job.mkdir(parents=True)
            run=root/'runs/paper-tissue-dependence-test'; run.mkdir()
            source=root/'source'; source.write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},
                input_hashes_sha256={str(source):'bad' if bad_input else d.digest(source)}))
            d.write_json(job/'status.json',dict(phase='launching',heartbeat_epoch=time.time()))
            (job/'runner.log').write_text('Run artifacts: '+str(run)+'\n')
            d.write_json(run/'summary.json',dict(cases=[],registered_cases=[],stage='finished',
                completion_reason='all_registered_stages_completed',gates={}))
            d.write_json(run/'independent_audit.json',dict(quality_gate=audit_quality,independent_check_count=1,
                all_fine_agree=True,readout_capacity={},support_contrasts=[],chain_outcomes=[]))
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
