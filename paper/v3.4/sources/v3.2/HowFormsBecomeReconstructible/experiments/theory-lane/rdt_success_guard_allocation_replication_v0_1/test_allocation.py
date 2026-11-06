"""Disposable software qualification; no scientific outcomes generated."""
from collections import Counter
from contextlib import contextmanager
import copy
from itertools import permutations
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from scipy.stats import t
from sr_common import ROOT,P,POLICIES,np,bridge,fast_reader,flat,ev,read,write,sha,Deadline,byte_equal
import sr_policy
import sr_quota
import sr_forcing
import sr_source
import sr_worker
import sr_unit_audit
import sr_verification
import sr_analysis
import sr_run
import sr_acquire
import acquisition
WORK=Path(os.environ['RDT_REPLICATION_TEST_DIR'])


@contextmanager
def short_reader():
    a=copy.deepcopy(P['reader']);b=copy.deepcopy(bridge.P['reader'])
    try:
        for cfg in (P['reader'],bridge.P['reader']):cfg.update(read_steps=32,settling_steps=16,observe_steps=32)
        yield
    finally:
        P['reader'].clear();P['reader'].update(a);bridge.P['reader'].clear();bridge.P['reader'].update(b)


def short_case():
    output=WORK/'short_reader_case';rows,packets=sr_source.synthetic(-2)
    for r in rows:r['key'][1]='software_only_32_steps'
    if not output.with_suffix('.json').exists():
        seal=WORK/'short_seal.json';write(seal,dict(rows=rows,software_only=True))
        with short_reader():sr_worker.evolve(rows,packets,'qualification',24,'independent',output,Deadline(time.time()+90),seal,sha(seal))
    return output,rows


def example_outcomes(tie=False,negative=False,initial=1):
    rows=[]
    for b in list(range(P['cohort']['eligible_blocks'])):
        for regime in P['regimes']:
            for i in range(4):
                for policy in POLICIES:
                    count={'always_promote':8+b%2,'matched_random':10+b%2,'writer_success_guard':14+b%3,'protected_retain':5+b%2}[policy]
                    if policy=='writer_success_guard' and regime=='independent':
                        if tie:count=10+b%2
                        if negative:count=3+b%3
                    y=[initial]+[1]*count+[0]*(18-count)
                    rows.append(dict(key=[b,'fixture',i,0],block=b,injury=24,regime=regime,history_class=int(i>=2),rule=1 if i%2==0 else -1,policy=policy,
                        downstream_successes=count,downstream_reads=18,terminal=y[-1],uninterrupted=int(all(y[1:])),opposite_reads=0,promotions=9,initial_pass=initial,passed=y))
    return rows


def selection_fixture(block,eligible=True):
    return [dict(key=[block,'fixture',i,0],block=block,current_pass=int(i>=2) if eligible else 0,
                 rule=1 if i%2==0 else -1,selection_hash=f'{i:064x}') for i in range(4)]


def pairing_fixture():
    mask=np.zeros((19,4,16,16),bool);mask.reshape(19,4,256)[:,:,:24]=True
    birth=np.ones((19,4,2,16,16));birth[:,:,1]=2
    rows=selection_fixture(-2)
    receipts=[dict(key=r['key'],generation=g,injury=24,regime='independent',permutation_sha256='permutation',base_forcing_sha256=f"{r['key']}_{g}",mask_sha256='mask') for g in range(15,34) for r in rows]
    return {(-2,24,'independent'):dict(mask=mask,birth=birth,forcing=receipts,rows=rows,allocation_order=np.tile(np.arange(4),(19,1)))}


class Checks(unittest.TestCase):
    def test_control_ignores_own_and_other_non_guard_labels(self):
        y=np.zeros((4,4),np.uint8);y[[0,2],2]=1;rank=np.array([3,1,0,2])
        got=sr_policy.actions(y,rank);changed=y.copy();changed[:,[0,1,3]]=1
        np.testing.assert_array_equal(got,sr_policy.actions(changed,rank))
        np.testing.assert_array_equal(got[:,1],[0,1,0,1]);np.testing.assert_array_equal(got[:,2],[1,0,1,0])

    def test_uniform_subsets_and_exact_quota_for_every_count(self):
        for k in range(5):
            y=np.zeros((4,4),np.uint8);y[:k,2]=1;counts=Counter()
            for order in permutations(range(4)):
                a=sr_policy.actions(y,np.array(order));self.assertEqual(int(a[:,1].sum()),k);self.assertEqual(int(a[:,2].sum()),k)
                self.assertTrue(a[:,0].all());self.assertFalse(a[:,3].any());counts[tuple(np.flatnonzero(a[:,1]))]+=1
            self.assertEqual(len(set(counts.values())),1)
            self.assertEqual(len(counts),[1,4,6,4,1][k])

    def test_invalid_shapes_and_orders_rejected(self):
        with self.assertRaises(ValueError):sr_policy.actions(np.zeros((3,4)),np.arange(4))
        for order in [np.array([0,0,2,3]),np.array([0,1,2,4]),np.arange(4,dtype=float)]:
            with self.assertRaises(ValueError):sr_policy.actions(np.zeros((4,4)),order)
        with self.assertRaises(ValueError):sr_policy.actions(np.full((4,4),2),np.arange(4))

    def test_retention_and_packet_arrays_do_not_alias(self):
        a=np.zeros((4,4,2,16,16));b=np.ones_like(a);y=np.zeros((4,4),np.uint8);y[0,2]=1
        out,act=sr_policy.advance(a,b,y,np.array([2,1,0,3]));self.assertEqual(float(out[2,1].sum()),512.)
        self.assertEqual(float(out[:,3].sum()),0.);out[0,0]=4;self.assertEqual(float(a.sum()),0.);self.assertEqual(float(b.min()),1.)

    def test_strict_threshold_and_opposite_identity(self):
        x=np.zeros((4,32,4,2,2));pattern=np.array([[1.,-1.],[-1.,1.]])
        for arm,v in enumerate([.25,.25001,-.5,0]):x[:,:,arm]=v*pattern
        y,cls,_=sr_policy.classify(x,[1]*4);self.assertEqual(y[0].tolist(),[0,1,0,0]);self.assertEqual(cls[0].tolist(),[0,1,-1,0])

    def test_independent_allocation_derivation_matches_primary(self):
        outputs=[]
        for stage in P['stages']:
            for block in [-2,2,45]:
                for g in [15,16,33]:
                    a=sr_quota.order(stage,block,g);b=sr_unit_audit.independent_order(stage,block,g)
                    np.testing.assert_array_equal(a,b);outputs.append(tuple(a))
        self.assertGreater(len(set(outputs)),5)
        with self.assertRaises(ValueError):sr_quota.order('undeclared',2,15)

    def test_forcing_stage_and_channels_are_distinct(self):
        key=[2,'fixture',0,0];ids=[sr_forcing.seed(s,key,g,c) for s in P['stages'] for g in [15,16,33] for c in ['injury','forcing']]
        self.assertEqual(len(ids),len(set(ids)))
        prior=read(ROOT/'context/previous_protocol.json');new=sr_forcing.seed('qualification',key,15,'forcing')
        with patch.dict(P,namespace=prior['namespace']):old=sr_forcing.seed('qualification',key,15,'forcing')
        self.assertNotEqual(new,old)

    def test_declared_injury_preserves_ports(self):
        env,_=sr_forcing.environment('qualification',[-2,'mask',0,0],15,24,'independent')
        self.assertEqual(int(env[0].sum()),24);self.assertFalse(np.any(env[0]&bridge.e.PORTS.any(axis=0)))
        with self.assertRaises(ValueError):sr_forcing.environment('qualification',[-2,'mask',0,0],15,18,'independent')

    def test_independent_forcing_rejects_matched_regime(self):
        key=[-2,'noise_test',0,0];a,receipt=sr_forcing.environment('qualification',key,15,24,'independent')
        self.assertFalse(np.array_equal(a[1][0],a[1][1]));self.assertFalse(np.array_equal(a[2][:,0],a[2][:,1]))
        with self.assertRaises(ValueError):sr_forcing.environment('qualification',key,15,24,'matched')


    def test_full_native_group_matches_independent_flat(self):
        rows,packets=sr_source.synthetic(-2);envs=[sr_forcing.environment('qualification',[-2,'software_full',j,0],15,24,'independent')[0] for j in range(4)]
        incoming=np.repeat(packets[:,None],4,axis=1);got=fast_reader.read_batch(incoming,envs);flat_results=[]
        for j in range(4):
            independent=flat.read_write(incoming[j],*envs[j],P['reader'],3.);flat_results.append(independent)
            for name in ['end','windows','outgoing']:byte_equal(got[name][j],independent[name],'full software group')
        y,_,_=sr_policy.classify(got['windows'],[r['rule'] for r in rows]);self.assertEqual(y[:,2].tolist(),[0,1,1,0])
        # The full native reader supplies the real mixed outcome;32 steps need not.
        order=np.array([0,3,1,2]);after,actions=sr_policy.advance(incoming,got['outgoing'],y,order)
        fclasses=[[sr_unit_audit.raw_class(flat_results[j]['windows'][:,arm],rows[j]['rule'])[0] for arm in range(4)] for j in range(4)]
        fa=sr_unit_audit.scalar_actions(fclasses,order,15);byte_equal(actions,fa,'native mixed quota decisions')
        self.assertEqual(int(fa[:,1].sum()),2);self.assertEqual(int(fa[:,2].sum()),2);self.assertFalse(np.array_equal(fa[:,1],fa[:,2]))
        expected=incoming.copy()
        for j in range(4):
            for arm in range(4):
                if fa[j,arm]:expected[j,arm]=flat_results[j]['outgoing'][arm]
        byte_equal(after,expected,'mixed full-read inheritance')

    def test_complete_short_chain_full_group_audit(self):
        output,rows=short_case();receipt=read(output.with_suffix('.json'))
        with short_reader():audit=sr_unit_audit.audit_case(output,rows,'qualification',24,'independent',receipt['policy_seal_sha256'])
        self.assertEqual(audit['native_readouts_independently_scored'],304);self.assertEqual(audit['flat_reads'],304);self.assertEqual(audit['full_horizon_flat_policy_chains'],16)
        self.assertEqual(audit['quota_generations_checked'],19)
        # Mixed allocations are checked using full2048-step outcomes in the full native test,
        # and over complete native lineages by the mandatory runtime qualification.

    def test_recommitted_quota_corruption_is_rejected(self):
        original,rows=short_case();receipt=read(original.with_suffix('.json'));raw=ev.load(original.with_suffix('.npz'),receipt['raw_sha256']);raw['quota_count'][0]+=1
        path=WORK/'broken_quota';receipt['raw_sha256']=ev.save(path.with_suffix('.npz'),raw);write(path.with_suffix('.json'),receipt)
        with short_reader(),self.assertRaises(ArithmeticError):sr_unit_audit.audit_case(path,rows,'qualification',24,'independent',receipt['policy_seal_sha256'])

    def test_recommitted_flat_donor_chain_corruption_is_rejected(self):
        original,rows=short_case();receipt=read(original.with_suffix('.json'));raw=ev.load(original.with_suffix('.npz'),receipt['raw_sha256']);raw['flat_incoming'][1,1,2,0,0,0]+=.125
        path=WORK/'broken_donor';receipt['raw_sha256']=ev.save(path.with_suffix('.npz'),raw);write(path.with_suffix('.json'),receipt)
        with short_reader(),self.assertRaises(ArithmeticError):sr_unit_audit.audit_case(path,rows,'qualification',24,'independent',receipt['policy_seal_sha256'])

    def test_terminal_read_is_not_inherited(self):
        original,_=short_case();raw=ev.load(original.with_suffix('.npz'),read(original.with_suffix('.json'))['raw_sha256'])
        self.assertFalse(raw['actions'][-1].any());self.assertFalse(raw['flat_actions'][-1].any());self.assertEqual(int(raw['quota_count'][-1]),0)
        byte_equal(raw['final_packets'],raw['incoming'][-1],'terminal boundary')

    def test_archived_legacy_boundary_labels_and_selection(self):
        raw=ev.load(ROOT/'native/context/legacy_g14.npz',sha(ROOT/'native/context/legacy_g14.npz'))
        rows=acquisition.boundary_records(34000,raw);sr_acquire.check_rows(rows,34000)
        chosen=sr_source.select_block(rows);self.assertEqual(len(rows),64);self.assertEqual(len(chosen),4)
        self.assertEqual([sum(r['current_pass']==h for r in chosen) for h in (0,1)],[2,2])


    def test_source_selection_rejects_incomplete_waves(self):
        with self.assertRaises(ValueError):sr_source.select_panel({b:selection_fixture(b) for b in range(8)})


    def test_primary_excludes_preaction_read_and_keeps_terminal_separate(self):
        a=sr_analysis.summarize(example_outcomes(initial=0),list(range(P['cohort']['eligible_blocks'])));b=sr_analysis.summarize(example_outcomes(initial=1),list(range(P['cohort']['eligible_blocks'])))
        self.assertEqual(a['primary'],b['primary']);self.assertEqual(a['cells'],b['cells'])
        self.assertGreater(a['cells']['24']['independent']['all']['writer_success_guard']['downstream_successes']['mean'],0)
        self.assertEqual(a['cells']['24']['independent']['all']['writer_success_guard']['terminal']['mean'],0)

    def test_single_primary_supported_unresolved_and_contradicted(self):
        for kwargs,wanted in [({},'ALLOCATION_REPLICATION_SUPPORTED'),({'tie':True},'ALLOCATION_REPLICATION_UNRESOLVED'),({'negative':True},'ALLOCATION_REPLICATION_CONTRADICTED')]:
            rows=example_outcomes(**kwargs);a=sr_analysis.summarize(rows,list(range(P['cohort']['eligible_blocks'])));self.assertEqual(a['decision'],wanted);self.assertEqual(sr_analysis.audit_analysis(rows,a)['status'],'PASS')
        report=sr_analysis.report(a,dict(native_reads=8512,flat_reads=8512),dict(units=28,native_reads=25088,flat_reads=336,teaching_episodes=56));self.assertGreater(report.count('\n'),10)

    def test_recovery_reduction_and_structural_first_success(self):
        rows=example_outcomes(initial=0);a=sr_analysis.summarize(rows,list(range(P['cohort']['eligible_blocks'])));self.assertEqual(sr_analysis.audit_recovery(rows,a)['recovery_cells'],8)
        bad=copy.deepcopy(rows);r=next(r for r in bad if r['policy']=='protected_retain');n=r['downstream_successes'];r['passed'][1]=0;r['passed'][n+1]=1
        with self.assertRaises(ArithmeticError):sr_analysis.summarize(bad,list(range(P['cohort']['eligible_blocks'])))

    def test_independent_forcing_stage_check(self):
        self.assertEqual(len(sr_verification.verify_forcing_pairs(pairing_fixture(),[-2])),76)


    def test_stage_rejects_forcing_context_corruption(self):
        for kind in ['duplicate','missing','cuecopy','key','regime','injury']:
            cases=pairing_fixture();case=cases[-2,24,'independent']
            if kind=='duplicate':case['forcing'][1]['base_forcing_sha256']=case['forcing'][0]['base_forcing_sha256']
            if kind=='missing':del cases[-2,24,'independent']
            if kind=='cuecopy':case['birth'][:,:,1]=case['birth'][:,:,0]
            if kind=='key':case['forcing'][0]['key']=[-2,'wrong',0,0]
            if kind=='regime':case['forcing'][0]['regime']='matched'
            if kind=='injury':case['mask'][0,0,0,0]=False
            with self.subTest(kind=kind),self.assertRaises(ArithmeticError):sr_verification.verify_forcing_pairs(cases,[-2])


    def test_worker_failure_is_durable_without_target_output(self):
        output=WORK/'expected_failure';task=WORK/'invalid_task.json';write(task,dict(output=str(output),deadline=time.time()+20,parent_pid=-1))
        with (WORK/'expected_failure.log').open('xb') as log:p=subprocess.run([sys.executable,str(ROOT/'sr_worker.py'),str(task)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=25)
        self.assertNotEqual(p.returncode,0);self.assertTrue((output/'FAILED.json').is_file());self.assertFalse((output/'COMPLETE.json').exists())

    def test_pricing_and_fixed_sample_accounting(self):
        self.assertEqual(P['cohort']['eligible_blocks'],28);self.assertEqual(P['cohort']['maximum_attempts'],35)
        self.assertEqual(P['resource']['workers'],7);self.assertEqual(P['counts']['total_full_native_reads_cap'],35*908+28*608+3*908+4*608)
        self.assertEqual(P['counts']['target_outcomes'],28*4*4);self.assertEqual(P['resource']['combined_seconds'],5400)
        self.assertAlmostEqual(P['primary']['critical_two_sided95'],t.ppf(.975,27));self.assertAlmostEqual(P['primary']['critical_one_sided95'],t.ppf(.95,27))
        self.assertEqual(sr_run.timing_gate(0,0,100)['status'],'PASS');self.assertEqual(sr_run.timing_gate(700,700,100)['status'],'FAILED');self.assertEqual(sr_run.timing_gate(0,0,601)['status'],'FAILED')
        self.assertEqual(sha(ROOT/'context/PRICING.json'),P['source_pricing_sha256'])
        expected=180+1.5*(5*P['resource']['historical_acquisition_floor']+4*P['resource']['historical_continuation_floor'])
        self.assertAlmostEqual(sr_run.timing_gate(0,0,100)['target_forecast_seconds'],expected)
        self.assertEqual(len(P['qualification_blocks'])+len(P['qualification_acquisition_blocks'])+1,7)


    def test_qualified_native_and_forcing_bytes_unchanged(self):
        receipt=read(ROOT/'COPY_RECEIPT.json')
        for field in ['native_files_required_byte_identical','other_files_required_byte_identical']:
            for rel,expected in receipt[field].items():self.assertEqual(sha(ROOT/rel),expected,rel)
        self.assertEqual(bridge.verify_inputs(),len(read(ROOT/'native/INPUTS.json')['sha256']))


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
        attempts={b:selection_fixture(b,b not in (0,3)) for b in range(35)}
        panel=sr_source.select_panel(attempts)
        self.assertEqual(panel['blocks'],[b for b in range(30) if b not in (0,3)])
        self.assertEqual(panel['ineligible_blocks'],[0,3]);self.assertEqual(panel['surplus_blocks'],list(range(30,35)))
        self.assertEqual(sr_source.verify_selection(attempts,panel)['status'],'PASS')
        broken=copy.deepcopy(panel);broken['blocks'][-1]=34
        with self.assertRaises(ArithmeticError):sr_source.verify_selection(attempts,broken)

    def test_incomplete_cohort_cannot_seal_or_release_futures(self):
        run=WORK/'incomplete_cohort';run.mkdir()
        with patch.object(sr_source.sr_acquire,'verify',side_effect=lambda folder,stage,b:(selection_fixture(b),{})),patch.object(sr_source,'sha',return_value='fixed'):
            with self.assertRaises(ValueError):sr_source.seal_panel(run,list(range(7)))
        self.assertFalse((run/'COHORT.json').exists());self.assertFalse((run/'scientific').exists())
        with self.assertRaises(FileNotFoundError):sr_source.load('scientific',0,run)

if __name__=='__main__':unittest.main()
