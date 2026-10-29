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
            sr_worker.evolve(rows,packets,'qualification',18,'independent',output,
                             Deadline(time.time()+60),seal,sha(seal))
    return output,rows


def example_outcomes(tie=False,initial=0):
    rows=[]
    for b in range(16):
        for n in (18,24):
            for regime in ('matched','independent'):
                for i in range(4):
                    h=int(i>=2)
                    for policy in POLICIES:
                        count=6 if h==0 else 15
                        if policy=='history_guard' and h==1:count=16+b%2
                        if policy=='protected_retain':count=(2 if h==0 else 10)+b%2
                        if policy=='writer_success_guard' and h==0:
                            count=(12+b%3 if n==18 else 11+b%4) if regime=='independent' else 5+b%2
                            if tie and n==18 and regime=='independent':count=6
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

    def test_nested_injuries_and_correct_marginal_counts(self):
        a,ra=sr_forcing.environment('qualification',[-2,'forcing_test',0,0],15,18,'independent')
        b,rb=sr_forcing.environment('qualification',[-2,'forcing_test',0,0],15,24,'independent')
        self.assertEqual(int(a[0].sum()),18);self.assertEqual(int(b[0].sum()),24)
        self.assertFalse(np.any(a[0]&~b[0]));self.assertFalse(np.any(a[0]&bridge.e.PORTS.any(axis=0)))
        for j in (1,2):np.testing.assert_array_equal(a[j],b[j])
        self.assertEqual(ra['base_forcing_sha256'],rb['base_forcing_sha256'])

    def test_matched_and_independent_share_only_declared_noise(self):
        key=[-2,'noise_test',0,0]
        a,ra=sr_forcing.environment('qualification',key,15,18,'matched')
        b,rb=sr_forcing.environment('qualification',key,15,18,'independent')
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
            check=sr_unit_audit.audit_case(output,rows,'qualification',18,'independent',receipt['policy_seal_sha256'])
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
                sr_unit_audit.audit_case(broken,rows,'qualification',18,'independent',receipt['policy_seal_sha256'])

    def test_archived_legacy_boundary_labels_and_selection(self):
        raw=ev.load(ROOT/'native/context/legacy_g14.npz',sha(ROOT/'native/context/legacy_g14.npz'))
        rows=acquisition.boundary_records(34000,raw)
        sr_acquire.check_rows(rows,34000)
        chosen=sr_source.select_block(rows)
        self.assertEqual(len(rows),64);self.assertEqual(len(chosen),4)
        self.assertEqual([sum(r['current_pass']==h for r in chosen) for h in (0,1)],[2,2])

    def test_primary_occupancy_excludes_initial_and_is_not_terminal(self):
        a=sr_analysis.summarize(example_outcomes(initial=0),list(range(16)));b=sr_analysis.summarize(example_outcomes(initial=1),list(range(16)))
        self.assertEqual(a,b)
        self.assertGreater(a['cells']['18']['matched']['all']['history_guard']['downstream_successes']['mean'],0)
        self.assertEqual(a['cells']['18']['matched']['all']['history_guard']['terminal']['mean'],0)

    def test_scalar_analysis_and_failed_primary_cannot_be_rescued(self):
        rows=example_outcomes();result=sr_analysis.summarize(rows,list(range(16)))
        self.assertEqual(result['decision'],'ALL_SIX_PREDICTIONS_SUPPORTED')
        self.assertEqual(sr_analysis.audit_analysis(rows,result)['status'],'PASS')
        failed=sr_analysis.summarize(example_outcomes(tie=True),list(range(16)))
        self.assertEqual(failed['decision'],'REPLICATION_UNRESOLVED')
        self.assertFalse(failed['all_six_point_directions_positive'])

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
        attempts={b:selection_fixture(b,b not in (0,3)) for b in range(24)}
        panel=sr_source.select_panel(attempts)
        self.assertEqual(panel['blocks'],[b for b in range(18) if b not in (0,3)])
        self.assertEqual(panel['ineligible_blocks'],[0,3]);self.assertEqual(panel['surplus_blocks'],list(range(18,24)))
        self.assertEqual(sr_source.verify_selection(attempts,panel)['status'],'PASS')
        broken=copy.deepcopy(panel);broken['blocks'][-1]=23
        with self.assertRaises(ArithmeticError):sr_source.verify_selection(attempts,broken)

    def test_incomplete_cohort_cannot_seal_or_release_futures(self):
        run=WORK/'incomplete_cohort';run.mkdir()
        with patch.object(sr_source.sr_acquire,'verify',side_effect=lambda folder,stage,b:(selection_fixture(b),{})),patch.object(sr_source,'sha',return_value='fixed'):
            with self.assertRaises(ValueError):sr_source.seal_panel(run,list(range(8)))
        self.assertFalse((run/'COHORT.json').exists());self.assertFalse((run/'scientific').exists())
        with self.assertRaises(FileNotFoundError):sr_source.load('scientific',0,run)

    def test_pricing_charges_full_attempt_cap_and_rejects_overrun(self):
        value=sr_run.timing_gate(0,0,100)
        self.assertEqual(value['status'],'PASS')
        expected=180+1.5*(3*P['resource']['historical_acquisition_floor']+4*P['resource']['historical_continuation_floor'])
        self.assertAlmostEqual(value['target_forecast_seconds'],expected)
        self.assertEqual(sr_run.timing_gate(1000,1000,100)['status'],'FAILED')
        self.assertEqual(sr_run.timing_gate(0,0,601)['status'],'FAILED')


if __name__=='__main__':unittest.main()
