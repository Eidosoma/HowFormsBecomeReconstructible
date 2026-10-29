"""Software checks use disposable inputs; no scientific futures are generated."""
from contextlib import contextmanager
import copy
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import sr_acquire
import sr_run
import acquisition
import sr_verification
from scipy.stats import t

from sr_common import ROOT,P,POLICIES,np,bridge,fast_reader,flat,ev,read,write,sha,Deadline,byte_equal
import sr_policy
import sr_forcing
import sr_source
import sr_worker
import sr_unit_audit
import sr_analysis

WORK=Path(os.environ['RDT_REPLICATION_TEST_DIR'])


@contextmanager
def short_reader():
    a=copy.deepcopy(P['reader']);b=copy.deepcopy(bridge.P['reader'])
    try:
        for cfg in (P['reader'],bridge.P['reader']):cfg.update(read_steps=32,settling_steps=16,observe_steps=32)
        yield
    finally:
        P['reader'].clear();P['reader'].update(a)
        bridge.P['reader'].clear();bridge.P['reader'].update(b)


def short_case():
    output=WORK/'short_reader_case'
    rows,packets=sr_source.synthetic(-2)
    for r in rows:r['key'][1]='software_only_32_steps'
    if not output.with_suffix('.json').exists():
        seal=WORK/'short_seal.json';write(seal,dict(rows=rows,software_only=True))
        with short_reader():
            sr_worker.evolve(rows,packets,'qualification',24,'independent',output,
                             Deadline(time.time()+60),seal,sha(seal))
    return output,rows


def example_outcomes(tie=False,initial=0):
    rows=[]
    for b in range(P['cohort']['eligible_blocks']):
        for n in P['injury_levels']:
            for regime in ('matched','independent'):
                for i in range(4):
                    h=int(i>=2)
                    for policy in POLICIES:
                        count=6 if h==0 else 15
                        if policy=='history_guard' and h==1:count=16+b%2
                        if policy=='protected_retain':count=(2 if h==0 else 10)+b%2
                        if policy=='writer_success_guard' and h==0:
                            count=(12+b%3 if n==18 else 11+b%4) if regime=='independent' else 5+b%2
                            if tie and n==24 and regime=='independent':count=6
                        rows.append(dict(block=b,injury=n,regime=regime,history_class=h,policy=policy,
                            downstream_successes=count,terminal=0,uninterrupted=0,opposite_reads=0,promotions=9,initial_pass=initial))
    return rows


def selection_fixture(block,eligible=True):
    return [dict(key=[block,'fixture',i,0],block=block,current_pass=int(i>=2) if eligible else 0,
                 rule=1 if i%2==0 else -1,selection_hash=f'{i:064x}') for i in range(4)]


class Checks(unittest.TestCase):
    def test_each_policy_uses_its_own_current_outcome(self):
        y=np.array([[1,0,1,0],[0,1,0,1]],np.uint8)
        np.testing.assert_array_equal(sr_policy.actions([1,1],y),[[1,0,1,0],[1,1,0,0]])

    def test_immutable_retention_and_no_alias(self):
        incoming=np.zeros((2,4,2,16,16));outgoing=np.ones_like(incoming)
        next_,a=sr_policy.advance(incoming,outgoing,[0,1],np.zeros((2,4),np.uint8))
        np.testing.assert_array_equal(next_[:,3],incoming[:,3])
        self.assertTrue(a[0,1]);self.assertFalse(a[1,1])
        next_[0,0]=4
        self.assertEqual(float(incoming.sum()),0);self.assertEqual(float(outgoing.min()),1)

    def test_historical_and_shape_validation(self):
        with self.assertRaises(ValueError):sr_policy.actions([2],np.zeros((1,4)))
        with self.assertRaises(ValueError):sr_policy.actions([0],np.zeros((1,3)))

    def test_strict_threshold_and_opposite_identity(self):
        pattern=np.array([[1.,-1.],[-1.,1.]])
        x=np.zeros((1,32,4,2,2))
        for arm,v in enumerate([.25,.25001,-.5,0]):x[0,:,arm]=v*pattern
        y,cls,a=sr_policy.classify(x,[1])
        self.assertEqual(y.tolist(),[[0,1,0,0]])
        self.assertEqual(cls.tolist(),[[0,1,-1,0]])

    def test_only_declared_injury_and_correct_marginal_counts(self):
        env,_=sr_forcing.environment('qualification',[-2,'forcing_test',0,0],15,24,'independent')
        self.assertEqual(int(env[0].sum()),24)
        self.assertFalse(np.any(env[0]&bridge.e.PORTS.any(axis=0)))
        with self.assertRaises(ValueError):
            sr_forcing.environment('qualification',[-2,'forcing_test',0,0],15,18,'independent')

    def test_matched_and_independent_share_only_declared_noise(self):
        key=[-2,'noise_test',0,0]
        a,ra=sr_forcing.environment('qualification',key,15,24,'matched')
        b,rb=sr_forcing.environment('qualification',key,15,24,'independent')
        np.testing.assert_array_equal(a[0],b[0]);np.testing.assert_array_equal(a[1][0],b[1][0])
        np.testing.assert_array_equal(a[2][:,0],b[2][:,0]);np.testing.assert_array_equal(a[2][:,0],a[2][:,1])
        self.assertFalse(np.array_equal(b[2][:,0],b[2][:,1]))
        self.assertEqual(ra['base_forcing_sha256'],rb['base_forcing_sha256'])

    def test_stage_generation_and_purpose_keys_are_distinct(self):
        key=[-2,'seed_test',0,0]
        ids=[sr_forcing.seed(s,key,g,c) for s in ('qualification','scientific') for g in (15,16,33) for c in ('injury','forcing')]
        self.assertEqual(len(ids),len(set(ids)))

    def test_full_native_four_policy_batch_matches_flat(self):
        rows,packets=sr_source.synthetic(-2)
        chosen=[2,3]
        envs=[sr_forcing.environment('qualification',[-2,'software_full',j,0],15,24,'matched')[0] for j in chosen]
        inputs=np.repeat(packets[chosen,None],4,axis=1)
        got=fast_reader.read_batch(inputs,envs)
        for k,j in enumerate(chosen):
            independent=flat.read_write(inputs[k],*envs[k],P['reader'],3.)
            for name in ('end','windows','outgoing'):byte_equal(got[name][k],independent[name],'full native software check')
        y,_,_=sr_policy.classify(got['windows'],[rows[j]['rule'] for j in chosen])
        self.assertTrue(y[0].all(),'Disposable signed grid must exercise promotion')
        self.assertFalse(y[1].any(),'Disconnected control must exercise retention')

    def test_short_complete_chain_and_scalar_audit(self):
        output,rows=short_case()
        with short_reader():
            receipt=read(output.with_suffix('.json'))
            check=sr_unit_audit.audit_case(output,rows,'qualification',24,'independent',receipt['policy_seal_sha256'])
        self.assertEqual(check['native_readouts_independently_scored'],304)
        self.assertEqual(check['flat_reads'],76)

    def test_recommitted_broken_chain_is_rejected(self):
        original,rows=short_case();receipt=read(original.with_suffix('.json'))
        arrays=ev.load(original.with_suffix('.npz'),receipt['raw_sha256'])
        arrays['incoming'][1,0,0,0,0,0]+=.125
        broken=WORK/'broken_chain'
        receipt['raw_sha256']=ev.save(broken.with_suffix('.npz'),arrays)
        write(broken.with_suffix('.json'),receipt)
        with short_reader():
            with self.assertRaises(ArithmeticError):
                sr_unit_audit.audit_case(broken,rows,'qualification',24,'independent',receipt['policy_seal_sha256'])

    def test_archived_legacy_boundary_labels_and_selection(self):
        raw=ev.load(ROOT/'native/context/legacy_g14.npz',sha(ROOT/'native/context/legacy_g14.npz'))
        rows=acquisition.boundary_records(34000,raw)
        sr_acquire.check_rows(rows,34000)
        chosen=sr_source.select_block(rows)
        self.assertEqual(len(rows),64);self.assertEqual(len(chosen),4)
        self.assertEqual([sum(r['current_pass']==h for r in chosen) for h in (0,1)],[2,2])

    def test_primary_occupancy_excludes_initial_and_is_not_terminal(self):
        a=sr_analysis.summarize(example_outcomes(initial=0),list(range(P['cohort']['eligible_blocks'])));b=sr_analysis.summarize(example_outcomes(initial=1),list(range(P['cohort']['eligible_blocks'])))
        self.assertEqual(a,b)
        self.assertGreater(a['cells']['24']['matched']['all']['history_guard']['downstream_successes']['mean'],0)
        self.assertEqual(a['cells']['24']['matched']['all']['history_guard']['terminal']['mean'],0)

    def test_scalar_analysis_and_failed_primary_cannot_be_rescued(self):
        rows=example_outcomes();result=sr_analysis.summarize(rows,list(range(P['cohort']['eligible_blocks'])))
        self.assertEqual(result['decision'],'ALL_THREE_PREDICTIONS_SUPPORTED')
        self.assertEqual(sr_analysis.audit_analysis(rows,result)['status'],'PASS')
        failed=sr_analysis.summarize(example_outcomes(tie=True),list(range(P['cohort']['eligible_blocks'])))
        self.assertEqual(failed['decision'],'NOISE_PRECISION_UNRESOLVED')
        self.assertFalse(failed['all_three_point_directions_positive'])

    def test_worker_failure_is_durable_without_outcomes(self):
        output=WORK/'expected_failure';task=WORK/'invalid_task.json'
        write(task,dict(output=str(output),deadline=time.time()+15,parent_pid=-1))
        with (WORK/'expected_failure.log').open('xb') as log:
            p=subprocess.run([sys.executable,str(ROOT/'sr_worker.py'),str(task)],stdin=subprocess.DEVNULL,
                             stdout=log,stderr=subprocess.STDOUT,timeout=20)
        self.assertNotEqual(p.returncode,0)
        self.assertTrue((output/'FAILED.json').is_file());self.assertFalse((output/'COMPLETE.json').exists())


    def test_only_acquisition_and_selection_namespaces_change(self):
        before=copy.deepcopy(bridge.P)
        try:
            namespaces=sr_acquire.configure('scientific')
            altered=copy.deepcopy(bridge.P)
            self.assertIn(P['namespace'],namespaces['acquisition'])
            for section in ('acquisition','selection'):altered[section]['namespace']=sr_acquire.ORIGINAL[section]['namespace']
            self.assertEqual(altered,sr_acquire.ORIGINAL)
        finally:bridge.P.clear();bridge.P.update(before)

    def test_fresh_acquisition_streams_differ_from_legacy_and_qualification(self):
        before=copy.deepcopy(bridge.P)
        try:
            sr_acquire.configure('scientific')
            a=acquisition.stream('scientific','E016',0,'teach',0).standard_normal(16)
            legacy=acquisition.stream('scientific','E016',0,'teach',0,legacy=True).standard_normal(16)
            sr_acquire.configure('qualification')
            b=acquisition.stream('qualification','E016',0,'teach',0).standard_normal(16)
            self.assertFalse(np.array_equal(a,b));self.assertFalse(np.array_equal(a,legacy))
        finally:bridge.P.clear();bridge.P.update(before)

    def test_boundary_selector_preserves_classes_and_rules(self):
        rows=selection_fixture(0)
        chosen=sr_source.select_block(rows)
        self.assertEqual([(r['current_pass'],r['rule']) for r in chosen],[(0,-1),(0,1),(1,-1),(1,1)])
        self.assertEqual(sr_source.select_block(selection_fixture(0,False)),[])
        self.assertEqual(sr_source.select_block(list(reversed(rows))),chosen)

    def test_first_eligible_panel_preserves_rejections_and_surplus(self):
        attempts={b:selection_fixture(b,b not in (0,3)) for b in range(72)}
        panel=sr_source.select_panel(attempts)
        self.assertEqual(panel['blocks'],[b for b in range(50) if b not in (0,3)])
        self.assertEqual(panel['ineligible_blocks'],[0,3]);self.assertEqual(panel['surplus_blocks'],list(range(50,72)))
        self.assertEqual(sr_source.verify_selection(attempts,panel)['status'],'PASS')
        broken=copy.deepcopy(panel);broken['blocks'][-1]=71
        with self.assertRaises(ArithmeticError):sr_source.verify_selection(attempts,broken)

    def test_incomplete_cohort_cannot_seal_or_release_futures(self):
        run=WORK/'incomplete_cohort';run.mkdir()
        with patch.object(sr_source.sr_acquire,'verify',side_effect=lambda folder,stage,b:(selection_fixture(b),{})),patch.object(sr_source,'sha',return_value='fixed'):
            with self.assertRaises(ValueError):sr_source.seal_panel(run,list(range(7)))
        self.assertFalse((run/'COHORT.json').exists());self.assertFalse((run/'scientific').exists())
        with self.assertRaises(FileNotFoundError):sr_source.load('scientific',0,run)

    def test_pricing_charges_full_attempt_cap_and_rejects_overrun(self):
        value=sr_run.timing_gate(0,0,100)
        self.assertEqual(value['status'],'PASS')
        expected=180+1.5*(11*P['resource']['historical_acquisition_floor']+7*P['resource']['historical_continuation_floor'])
        self.assertAlmostEqual(value['target_forecast_seconds'],expected)
        self.assertEqual(sr_run.timing_gate(1000,1000,100)['status'],'FAILED')
        self.assertEqual(sr_run.timing_gate(0,0,601)['status'],'FAILED')



    def test_qualified_core_and_native_bytes_are_unchanged(self):
        receipt=read(ROOT/'COPY_RECEIPT.json')
        for field in ('core_files_required_byte_identical','copied_native_files'):
            for rel,expected in receipt[field].items():self.assertEqual(sha(ROOT/rel),expected,rel)
        self.assertEqual(bridge.verify_inputs(),len(read(ROOT/'native/INPUTS.json')['sha256']))

    def test_frozen_statistics_and_resource_accounting(self):
        self.assertEqual(P['cohort']['eligible_blocks'],48)
        self.assertEqual(P['cohort']['maximum_attempts'],72)
        self.assertAlmostEqual(P['primary']['critical_two_sided95'],float(t.ppf(.975,47)),places=14)
        self.assertAlmostEqual(P['primary']['critical_one_sided95'],float(t.ppf(.95,47)),places=14)
        self.assertEqual(P['counts']['total_reads_cap'],72*908+48*760+4*908+4*760)
        self.assertEqual(P['counts']['target_terminal_outcomes'],48*4*4*2)
        self.assertEqual(P['resource']['acquisition_waves_cap'],11)
        self.assertEqual(P['resource']['continuation_waves'],7)
        self.assertLessEqual(P['resource']['qualification_seconds']+P['resource']['target_seconds'],P['resource']['combined_seconds'])
        self.assertEqual(P['resource']['combined_seconds'],9000)
        self.assertEqual(sha(ROOT/'context/PRICING_AND_PRECISION.json'),P['source_pricing_sha256'])
        with self.assertRaises(ValueError):sr_analysis.description(np.zeros(16))
        with self.assertRaises(ValueError):sr_source.select_panel({b:selection_fixture(b) for b in range(50)})

    def test_single_injury_pairing_accepts_declared_case(self):
        cases=pairing_fixture()
        self.assertEqual(len(sr_verification.verify_forcing_pairs(cases,[-2])),76)

    def test_pairing_rejects_missing_misaligned_and_corrupt_cases(self):
        for failure in ('missing','base','mask','cuecopy','key'):
            cases=pairing_fixture();i=cases[-2,24,'independent']
            if failure=='missing':del cases[-2,24,'matched']
            if failure=='base':i['forcing'][0]['base_forcing_sha256']='unpaired'
            if failure=='mask':i['mask'][0,0,0,0]=False
            if failure=='cuecopy':i['birth'][:,:,1]=i['birth'][:,:,0]
            if failure=='key':i['forcing'][0]['key']=[-2,'wrong',0,0]
            with self.subTest(failure=failure),self.assertRaises(ArithmeticError):
                sr_verification.verify_forcing_pairs(cases,[-2])

    def test_new_namespaces_differ_from_exposed_study(self):
        previous=read(ROOT/'context/previous_protocol.json')
        self.assertNotEqual(P['namespace'],previous['namespace'])
        new=sr_forcing.seed('scientific',[0,'example',0,0],15,'forcing')
        with patch.dict(P,namespace=previous['namespace']):
            old=sr_forcing.seed('scientific',[0,'example',0,0],15,'forcing')
        self.assertNotEqual(new,old)
        before=copy.deepcopy(bridge.P)
        try:
            newnames=sr_acquire.configure('scientific')
            with patch.dict(P,namespace=previous['namespace']):oldnames=sr_acquire.configure('scientific')
            self.assertNotEqual(newnames['acquisition'],oldnames['acquisition'])
            self.assertNotEqual(newnames['selection'],oldnames['selection'])
        finally:bridge.P.clear();bridge.P.update(before)


    def test_resource_amendment_preserves_science_and_selected_panel(self):
        prior=read(ROOT/'context/pre_resource_amendment_protocol.json')
        proof=read(ROOT/'context/RESOURCE_AMENDMENT.json')
        for key in proof['unchanged_science']:self.assertEqual(P[key],prior[key],key)
        self.assertEqual(P['resource']['workers']+P['resource']['parent_reserve']+4,12)
        self.assertTrue(proof['launch_receipt_absent']);self.assertTrue(proof['run_directory_absent'])
        self.assertEqual(proof['scientific_acquisitions'],0);self.assertEqual(proof['scientific_futures'],0)
        results=[];attempted=[]
        for width in (8,7):
            attempts={}
            with patch.dict(P['cohort'],wave_size=width):
                for start in range(0,72,width):
                    for b in range(start,min(start+width,72)):attempts[b]=selection_fixture(b)
                    panel=sr_source.select_panel(attempts)
                    if panel['complete']:break
            results.append(panel['rows']);attempted.append(len(attempts))
        self.assertEqual(results[0],results[1]);self.assertEqual(attempted,[48,49])


def pairing_fixture():
    mask=np.zeros((19,4,16,16),bool);mask.reshape(19,4,256)[:,:,:24]=True
    birth=np.ones((19,4,2,16,16))
    receipts=[dict(key=[-2,'fixture',j,0],generation=g,injury=24,permutation_sha256='permutation',
                   base_forcing_sha256=f'{j}_{g}',mask_sha256='mask') for g in range(15,34) for j in range(4)]
    a=dict(mask=mask,birth=birth,forcing=receipts);b=copy.deepcopy(a);b['birth'][:,:,1]=2
    return {(-2,24,'matched'):a,(-2,24,'independent'):b}


if __name__=='__main__':unittest.main()
