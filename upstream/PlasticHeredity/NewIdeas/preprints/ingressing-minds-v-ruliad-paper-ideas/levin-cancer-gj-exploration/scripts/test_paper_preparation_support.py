"""P19 synthetic full-panel checks; no new scientific dynamics in tests."""
from contextlib import contextmanager,redirect_stdout
import copy
from datetime import datetime,timezone,timedelta
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
import paper_preparation_support_design as d
import run_paper_preparation_support as r
import analyze_paper_preparation_support as a
import run_paper_preparation_support_detached as detached

def fixture_case(run,c,failure=None):
    folder=run/c['id']; folder.mkdir(); exp=r.RateExperiment(folder,dict(id=c['id'],fine=c['fine']))
    current={}; original=exp.phase
    def phase(name,horizon,**kwargs):
        current['name']=name; return original(name,horizon,**kwargs)
    def fake_clock(sim,horizon,sample_interval,max_step):
        name=current['name']; initial=sim.cc_cells.copy(); replay=d.replay_source(c)
        if replay is not None:
            src=run/'inputs/p18'/replay; archived=a.arrays(src,name)
            np.testing.assert_array_equal(initial,archived['initial']); np.copyto(sim.cc_cells,archived['final'])
            records=json.loads((src/'result.json').read_text())['phases']
            meta=next(rec['clock'] for rec in records if rec['phase']==name)
            return archived['times'],archived['concentrations'],{
                k:archived[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')},meta
        def mark(indices,lab):
            setter=exp.z.GRN.set_very_healthy if lab=='E' else exp.z.GRN.set_very_tumor
            for i in indices: setter(sim.cc_cells,i)
        if c['stage']=='renewal' and (name=='preparation_extra' or name.startswith('replacement')):
            present=any(exp.z.GRN.state_char(x)=='E' for x in initial.T)
            success=(c['mode']=='open' or (c['mode']=='isolated' and c['extra']==900)) and present and failure!='all_negative'
            if failure=='all_positive': success=True
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

class TestPreparationSupport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='p19-software-',dir=d.ROOT/'.cache'); cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture_run=Path(cls.temp.name)/'run'; cls.fixture_run.mkdir(); hashes,frozen,inputs=r.freeze(cls.fixture_run)
        cls.history=dict(quality_gate=True,original_matches_saved=True,archive_byte_identical=True,
            prior_checks=104607,prior_cases=282,prior_calls=1296,original_reaudit_count=1,
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
        cls.primary=d.case(); cls.by={b['case']['id']:b['outcome'] for b in gate['branches']}; cls.cases=d.fixed_cases()

    @contextmanager
    def isolated_run(self):
        with tempfile.TemporaryDirectory(prefix='p19-unit-') as temp:
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

    def corrupt_array(self,name,change,c=None):
        c=self.primary if c is None else c
        with self.copied_case(c) as (run,folder):
            value=a.arrays(folder,name); change(value); np.savez_compressed(folder/(name+'.npz'),**value)
            result=json.loads((folder/'result.json').read_text())
            next(p for p in result['phases'] if p['phase']==name)['sha256']=d.digest(folder/(name+'.npz'))
            d.write_json(folder/'result.json',result); checks,_,_=self.audit_branch(run,c)
            self.assertFalse(all(checks.rows.values()))

    def corrupt_result(self,change,c=None):
        c=self.primary if c is None else c
        with self.copied_case(c) as (run,folder):
            result=json.loads((folder/'result.json').read_text()); change(result); d.write_json(folder/'result.json',result)
            checks,_,_=self.audit_branch(run,c); self.assertFalse(all(checks.rows.values()))

    def fabricated(self,mode,c=None):
        c=self.primary if c is None else c
        with self.isolated_run() as run,redirect_stdout(io.StringIO()):
            if (run/c['id']).is_symlink(): (run/c['id']).unlink()
            fixture_case(run,c,mode); checks,report,_=self.audit_branch(run,c)
            self.assertTrue(all(checks.rows.values()),[k for k,v in checks.rows.items() if not v]); return report['outcome']

    def test_registration_and_independent_descriptors(self):
        self.assertEqual(self.cases,a.expected_cases())
        self.assertEqual([len(d.stage_cases(s)) for s in d.STAGES],[48,36,108])
        self.assertEqual((len({c['id'] for c in self.cases}),sum(c['fine'] for c in self.cases)),(192,96))
        self.assertEqual({(c['extra'],c['mode']) for c in d.stage_cases('renewal')},{(t,m) for t in (200,900) for m in ('open','rna','isolated')})

    def test_config_rejects_extra_modes_times_and_follow_on(self):
        self.assertEqual(d.validate_config(json.loads((d.ROOT/'configs/paper_preparation_support_v1.json').read_text())),d.FIXED)
        for key,value in [('later_interval',100),('extra_intervals',[200]),('incoming_seed',502),('archive_mode','copy'),('automatic_follow_on',True)]:
            with self.assertRaises(ValueError): d.validate_config(dict(d.FIXED,**{key:value}))

    def test_full_synthetic_panel_and_final_audit(self):
        self.assertTrue(self.report['quality_gate']); self.assertEqual((self.report['completed_cases'],self.report['integration_calls']),(192,870))
        self.assertEqual(len(self.report['fine_comparisons']),96); self.assertTrue(self.report['all_fine_agree'])
        self.assertEqual([len(self.report[k]) for k in ('preparation_grid','benchmark_consistency','mode_contrasts','chain_outcomes')],[18,6,12,18])
        self.assertEqual([self.summary['gates'][s]['integration_calls'] for s in d.STAGES],[258,546,870])

    def test_manifest_storage_sources_and_native_revision(self):
        self.assertEqual((len(d.LOCAL_FILES),len(d.execution_manifest()),len(d.input_paths())),(157,193,11182))
        d.source_check(); self.assertTrue(all(a.integrity(self.fixture_run,self.summary).values()))
        for name in ('storage/relocate_artifacts.py','storage/artifact_storage_v2.py'):
            self.assertIn(name,self.summary['hashes_sha256'])

    def test_linked_inputs_and_copied_execution(self):
        for name,meta in self.summary['inputs'].items():
            self.assertEqual(meta['storage'],'hardlink_immutable_v1'); self.assertTrue((self.fixture_run/'inputs'/name).samefile(meta['source']))
        for p in d.LOCAL_FILES: self.assertFalse((self.fixture_run/'frozen'/p.name).samefile(p))

    def test_immutable_copy_does_not_satisfy_hardlink_policy(self):
        with tempfile.TemporaryDirectory(prefix='p19-links-') as temp:
            root=Path(temp); source=root/'source'; source.write_text('immutable'); run=root/'run'
            (run/'inputs').mkdir(parents=True); (run/'frozen').mkdir(); shutil.copyfile(source,run/'inputs/a')
            summary=dict(revision=d.REVISION,hashes_sha256={},frozen_hashes_sha256={},inputs={'a':dict(source=str(source),sha256=d.digest(source),storage='hardlink_immutable_v1')})
            with patch.object(d,'input_paths',return_value={'a':source}),patch.object(d,'execution_manifest',return_value={}),patch.object(d,'LOCAL_FILES',[]):
                flags=a.integrity(run,summary); self.assertTrue(flags['inputs']); self.assertFalse(flags['linked_inputs'])

    def test_all_modes_and_extra_durations_share_exact_prefix(self):
        for h in d.FOUNDERS:
            for fine in (False,True):
                initials=[]
                for extra in d.EXTRAS:
                    for mode in d.MODES:
                        c=d.case(founder=h,extra=extra,mode=mode,fine=fine)
                        value,ids,cursor,record=r.prefix_checkpoint(self.fixture_run,c)
                        initial=a.arrays(self.fixture_run/c['id'],'preparation_extra')['initial']; initials.append(initial)
                        np.testing.assert_array_equal(initial,value)
                        self.assertEqual(record['case']['route'],'open'); self.assertEqual(record['case']['tau'],100)
                        self.assertEqual(cursor,(0 if h=='stock_E' else 1180000)+100)
                        result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
                        self.assertEqual(result['phases'][0]['setup']['cell_ids'],ids)
                        self.assertEqual(result['archived_prefix_source'],d.prefix_source(c))
                for x in initials[1:]: np.testing.assert_array_equal(x,initials[0])

    def test_extra_wait_uses_correct_coupling(self):
        for c in d.stage_cases('renewal'):
            folder=self.fixture_run/c['id']; result=json.loads((folder/'result.json').read_text()); first=result['phases'][0]
            data=a.arrays(folder,'preparation_extra')
            self.assertEqual(first['requested_horizon'],c['extra'])
            self.assertEqual(first['setup']['mirna_kd'],1.25e-14 if c['mode']=='open' else 0)
            self.assertEqual(bool(data['junction_diffusion'][:4].any()),c['mode']!='isolated')
            if c['mode']=='isolated': self.assertFalse(data['junction_diffusion'].any())

    def test_all_later_windows_restore_both_transport_routes(self):
        for c in d.stage_cases('renewal'):
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            for rec in result['phases'][1:6]:
                data=a.arrays(self.fixture_run/c['id'],rec['phase'])
                self.assertEqual(rec['requested_horizon'],300); self.assertEqual(rec['setup']['mirna_kd'],1.25e-14)
                self.assertTrue(data['junction_diffusion'][:4].any())
                self.assertEqual(rec['setup']['gate_classes']['gj_add'],['EMT_GJ_gate'])
                self.assertFalse(data['junction_diffusion'][4:].any())

    def test_surviving_columns_continue_without_reset(self):
        for c in d.stage_cases('renewal'):
            value=a.arrays(self.fixture_run/c['id'],'preparation_extra')['final']
            for at in range(1,6):
                data=a.arrays(self.fixture_run/c['id'],'replacement_%02d'%(at+1)); keep=[p for p in range(3) if p!=at%3]
                np.testing.assert_array_equal(data['initial'][:,keep],value[:,keep]); value=data['final']
            np.testing.assert_array_equal(a.arrays(self.fixture_run/c['id'],'isolated_1')['initial'],value)
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            self.assertFalse(set(result['outcome']['fork_ids'])&set(result['phases'][-1]['setup']['cell_ids']))

    def test_incoming_draws_unchanged_and_initially_M(self):
        self.assertEqual(d.draw_book(),a.expected_draws())
        for fine in (False,True):
            _,M=r.stock(self.fixture_run,fine)
            for cycle in (0,1):
                for pos in range(3):
                    x=d.incoming(M,cycle,pos); np.testing.assert_array_equal(x,a.incoming(M,cycle,pos))
                    np.testing.assert_array_equal(x[np.arange(17)!=7],M[np.arange(17)!=7]); self.assertEqual(''.join(a.labels(x,a.INDEX)),'M')

    def test_preparation_and_turnover_clocks_are_contiguous(self):
        for c in d.stage_cases('renewal'):
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text()); cursor=(0 if c['founder']=='stock_E' else 1180000)+100
            self.assertEqual([p['requested_horizon'] for p in result['phases']],[c['extra']]+[300]*5+[10000]*2)
            for phase in result['phases']:
                end=cursor+phase['requested_horizon']; self.assertEqual(phase['logical_interval'],[cursor,end]); cursor=end
            self.assertEqual(result['outcome']['logical_end'],cursor)

    def test_matched_wipes_match_coupling_elapsed_time_and_burden(self):
        for c in d.stage_cases('baseline'):
            if c['arm']!='wipe': continue
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text())
            self.assertEqual([p['requested_horizon'] for p in result['phases']],[100,c['extra'],600,900,10000,10000])
            self.assertEqual(len(result['outcome']['replacements']),6)
            self.assertEqual(result['outcome']['logical_end'],21600+c['extra'])
            self.assertEqual(result['phases'][1]['setup']['mirna_kd'],1.25e-14 if c['mode']=='open' else 0)
            for p in (result['phases'][0],*result['phases'][2:4]): self.assertEqual(p['setup']['mirna_kd'],1.25e-14)

    def test_exact_replays_have_full_array_continuity(self):
        cases=phases=0
        for c in d.stage_cases('baseline'):
            self.assertEqual(d.replay_source(c),a.replay_source(c))
            if d.replay_source(c) is None: continue
            checks,_,data=self.audit_branch(self.fixture_run,c); cases+=1; phases+=len(data)
            replay=[v for k,v in checks.rows.items() if '/historical_replay/' in k]
            self.assertEqual(len(replay),33*len(data)); self.assertTrue(all(replay))
        self.assertEqual((cases,phases),(36,186))

    def test_actual_parents_used_even_when_preparation_failed(self):
        for c in d.stage_cases('onward'):
            data=a.arrays(self.fixture_run/c['id'],'contact')
            np.testing.assert_array_equal(data['initial'][:,:3],a.arrays(self.fixture_run/d.parent(c)['id'],'isolated_2')['final'])
            self.assertEqual(''.join(a.labels(data['initial'][:,3:],a.INDEX)),'MMM')
            expect=c['mode']=='open' or (c['mode']=='isolated' and c['extra']==900)
            self.assertEqual(self.by[c['id']]['donor_initial_labels'],'EEE' if expect else 'MMM')

    def test_readout_clocks_include_preparation_and_parent_holds(self):
        for c in d.stage_cases('onward'):
            result=json.loads((self.fixture_run/c['id']/'result.json').read_text()); start=(0 if c['founder']=='stock_E' else 1180000)+21600+c['extra']
            self.assertEqual(result['phases'][0]['logical_interval'],[start,start+20000])
            self.assertEqual(result['outcome']['logical_end'],start+40000)

    def test_preparation_mode_dependence_is_not_presumed(self):
        for x in self.report['mode_contrasts']:
            expected=x['changed_mode']=='rna' or x['extra']==200
            self.assertEqual(x['control_qualified_preparation_dependence'],expected)
        for x in self.report['preparation_grid']:
            self.assertEqual(x['isolated_extra_time_sufficient'],x['mode']=='isolated' and x['extra']==900)

    def test_missing_mode_or_reference_cannot_qualify(self):
        by=copy.deepcopy(self.by); by.pop(d.case(mode='rna')['id'])
        rows=a.contrasts(by)['mode_contrasts']; selected=next(x for x in rows if x['founder']=='written' and x['extra']==200 and x['changed_mode']=='rna')
        self.assertFalse(selected['available']); self.assertFalse(selected['control_qualified_preparation_dependence'])
        by=copy.deepcopy(self.by); by.pop(d.case('baseline',arm='reference',first=300)['id'])
        selected=next(x for x in a.contrasts(by)['benchmark_consistency'] if x['founder']=='written' and x['extra']==200)
        self.assertFalse(selected['benchmark_recovery_qualified'])

    def test_positive_wipe_blocks_qualified_rescue_and_chain(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case('baseline',arm='wipe',fine=f)['id']]['retained_E']=True
        out=a.contrasts(by)
        for key in ('preparation_grid','chain_outcomes'):
            row=next(x for x in out[key] if x['founder']=='written' and x['extra']==200 and x['mode']=='open')
            self.assertFalse(row['control_qualified_rescue' if key=='preparation_grid' else 'control_qualified_chain'])

    def test_positive_onward_controls_block_qualified_transmission(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case('onward',readout='rna',fine=f)['id']]['transmitted_E']=True
        row=next(x for x in a.contrasts(by)['chain_outcomes'] if x['founder']=='written' and x['extra']==200 and x['mode']=='open')
        self.assertTrue(row['raw_retention_and_onward']); self.assertFalse(row['control_qualified_transmission'])

    def test_late_recovery_does_not_repair_first_cell_failure(self):
        out=self.fabricated('late_recovery',d.case(mode='rna'))
        self.assertTrue(out['retained_E']); self.assertFalse(out['first_cell_stable_E_after_second'])

    def test_E_endpoint_does_not_override_late_occupancy_failure(self):
        out=self.fabricated('late'); self.assertEqual(out['observations']['isolated_1']['patch_labels'],'EEE')
        self.assertFalse(out['retained_E'])

    def test_clock_corruption_rejected(self):
        self.corrupt_array('preparation_extra',lambda x:x['clock_step_ticks'].__setitem__(0,x['clock_step_ticks'][0]+1))

    def test_logical_extra_duration_corruption_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['logical_interval'].__setitem__(1,x['phases'][0]['logical_interval'][1]+1))

    def test_prefix_column_mutation_rejected(self):
        self.corrupt_array('preparation_extra',lambda x:x['initial'].__setitem__((0,0),x['initial'][0,0]+.01))

    def test_survivor_reset_rejected(self):
        self.corrupt_array('replacement_02',lambda x:x['initial'].__setitem__((0,2),x['initial'][0,2]+.01))

    def test_extra_RNA_transport_tampering_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup'].update(mirna_kd=1.25e-14),d.case(mode='rna'))

    def test_direct_RNA_diffusion_bypassing_native_gate_rejected(self):
        for species in ('miR200_free','miR200_total'):
            with self.subTest(species=species):
                self.corrupt_array('preparation_extra',lambda x:x['junction_diffusion'].__setitem__((a.INDEX[species],0),1e-18))

    def test_extra_isolation_ionic_leak_rejected(self):
        self.corrupt_array('preparation_extra',lambda x:x['junction_diffusion'].__setitem__((0,0),1.),d.case(mode='isolated'))

    def test_failure_to_restore_RNA_rejected(self):
        self.corrupt_result(lambda x:x['phases'][1]['setup'].update(mirna_kd=0.),d.case(mode='rna'))

    def test_wrong_prefix_route_provenance_rejected(self):
        self.corrupt_result(lambda x:x.update(archived_prefix_source=x['archived_prefix_source'].replace('open','rna')))

    def test_early_or_duplicate_identity_rejected(self):
        self.corrupt_result(lambda x:x['phases'][0]['setup']['cell_ids'].__setitem__(1,x['phases'][0]['setup']['cell_ids'][0]))

    def test_unregistered_extra_phase_rejected(self):
        with self.copied_case() as (run,folder):
            shutil.copyfile(folder/'preparation_extra.npz',folder/'extra.npz')
            checks,_,_=self.audit_branch(run,self.primary); self.assertFalse(all(checks.rows.values()))

    def test_saved_outcome_corruption_rejected(self):
        self.corrupt_result(lambda x:x['outcome'].update(retained_E=not x['outcome']['retained_E']))

    def test_discrete_fine_disagreement_rejected(self):
        by=copy.deepcopy(self.by); c=d.case(fine=True); by[c['id']]['retained_E']=False
        checks=a.Checks(); cases=[d.case(),c]
        data={x['id']:{'isolated_2':a.arrays(self.fixture_run/x['id'],'isolated_2')} for x in cases}
        result=a.p18.p12.compare_fine(cases,by,data,checks); self.assertFalse(result[0]['agree'])

    def test_failed_benchmark_is_flagged_without_dropping_modes(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case('baseline',arm='reference',first=300,fine=f)['id']]['retained_E']=False
        out=a.contrasts(by); row=next(x for x in out['benchmark_consistency'] if x['founder']=='written' and x['extra']==200)
        self.assertFalse(row['registered_metrics_agree_both']); self.assertFalse(row['benchmark_recovery_qualified'])
        self.assertEqual(len(out['preparation_grid']),18); self.assertEqual(len(out['chain_outcomes']),18)

    def test_readout_capacity_required_for_benchmark_support(self):
        by=copy.deepcopy(self.by)
        for f in (False,True): by[d.case('baseline',arm='capacity',readout='open',fine=f)['id']]['transmitted_E']=False
        out=a.contrasts(by); self.assertFalse(out['readout_capacity']['qualified'])
        self.assertFalse(any(x['benchmark_supported_chain'] for x in out['chain_outcomes']))

    def test_worker_refuses_wrong_stage(self):
        with self.copied_case() as (run,folder):
            d.write_json(run/'summary.json',dict(stage='baseline'))
            d.write_json(folder/'spec.json',dict(config=d.FIXED,case=self.primary,inputs=str(run/'inputs')))
            with self.assertRaisesRegex(ValueError,'Wrong P19 stage'): r.worker(folder/'spec.json')

    def test_no_new_case_when_either_filesystem_is_low(self):
        fake=type('Disk',(),{'free':4*1024**3})()
        with patch.object(r.shutil,'disk_usage',return_value=fake): self.assertFalse(r.space_available())
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'space_available',return_value=False):
            result=r.run_worker(self.primary,d.FIXED,Path(tmp),time.monotonic()+100,{})
            self.assertEqual(result['status'],'not_launched_disk'); self.assertFalse((Path(tmp)/self.primary['id']).exists())

    def test_provenance_failure_closes_quality_gate(self):
        changed=copy.deepcopy(self.summary); changed['inputs'][next(iter(changed['inputs']))]['sha256']='0'*64
        flags=a.integrity(self.fixture_run,changed); self.assertFalse(flags['sources']); self.assertFalse(flags['inputs'])

    def test_previous_audit_once_and_exactly_matched(self):
        saved=json.loads((self.fixture_run/'inputs/p18/independent_audit.json').read_text())
        with patch.object(a.p18,'analyze',return_value=saved) as called,patch.object(a,'integrity',return_value={'all':True}):
            value=a.predecessor_audit(self.fixture_run); self.assertTrue(value['quality_gate']); self.assertEqual(called.call_count,1)
        bad=copy.deepcopy(saved); bad['quality_gate']=False
        with patch.object(a.p18,'analyze',return_value=bad),patch.object(a,'integrity',return_value={'all':True}):
            self.assertFalse(a.predecessor_audit(self.fixture_run)['quality_gate'])


class TestPreparationSupportSupervisor(unittest.TestCase):
    @contextmanager
    def job(self):
        with tempfile.TemporaryDirectory(prefix='p19-supervisor-') as tmp:
            job=Path(tmp); (job/'frozen').mkdir(); (job/'verification.log').write_text('fixture')
            d.write_json(job/'launch.json',dict(hashes_sha256={},frozen_hashes_sha256={},input_hashes_sha256={},verification_hashes_sha256={}))
            d.write_json(job/'status.json',dict(phase='launching'))
            yield job

    def supervise(self,job,returns):
        with patch.object(detached.signal,'signal'),patch.object(detached,'verification_manifest',return_value={}), \
             patch.object(detached,'space_available',return_value=True),patch.object(detached,'start_storage_watcher',return_value=123), \
             patch.object(detached,'watcher_health',return_value=dict(heartbeat_utc=detached.now(),files_moved=0)), \
             patch.object(detached,'run_child',side_effect=returns) as child:
            fd=os.open(job/'lock',os.O_CREAT|os.O_RDWR,0o600)
            code=detached.supervise(job,fd)
        return code,child.call_count,json.loads((job/'status.json').read_text())

    def test_verification_failure_blocks_runner(self):
        with self.job() as job:
            code,calls,meta=self.supervise(job,[1]); self.assertEqual((code,calls),(1,1)); self.assertEqual(meta['phase'],'failed')

    def test_runner_failure_no_automatic_retry(self):
        with self.job() as job:
            code,calls,meta=self.supervise(job,[0,124]); self.assertEqual((code,calls),(1,2)); self.assertIn('Runner exited 124',meta['error'])

    def test_execution_mutation_blocks_all_children(self):
        with self.job() as job:
            value=json.loads((job/'launch.json').read_text()); value['hashes_sha256']={'scripts/run_paper_preparation_support.py':'0'*64}; d.write_json(job/'launch.json',value)
            code,calls,meta=self.supervise(job,[]); self.assertEqual((code,calls),(1,0)); self.assertIn('Execution files changed',meta['error'])

    def test_storage_start_failure_blocks_verification(self):
        with self.job() as job,patch.object(detached.signal,'signal'),patch.object(detached,'verification_manifest',return_value={}), \
             patch.object(detached,'space_available',return_value=True),patch.object(detached,'start_storage_watcher',side_effect=RuntimeError('store unavailable')), \
             patch.object(detached,'run_child') as child:
            fd=os.open(job/'lock',os.O_CREAT|os.O_RDWR,0o600); self.assertEqual(detached.supervise(job,fd),1); child.assert_not_called()

    def test_stale_storage_heartbeat_rejected(self):
        with self.job() as job:
            d.write_json(job/'storage-watcher-status.json',dict(job=str(job),pid=42,phase='watching',
                heartbeat_utc=(datetime.now(timezone.utc)-timedelta(seconds=121)).isoformat()))
            with self.assertRaises(RuntimeError): detached.watcher_health(job,42)

    def test_discover_run_rejects_foreign_output(self):
        with self.job() as job:
            (job/'runner.log').write_text('Run artifacts: /tmp/wrong-run\n')
            with self.assertRaises(ValueError): detached.discover_run(job)


if __name__=='__main__': unittest.main()
