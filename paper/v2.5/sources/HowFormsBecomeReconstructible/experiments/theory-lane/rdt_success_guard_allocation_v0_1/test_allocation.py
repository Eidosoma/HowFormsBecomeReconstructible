"""Disposable software qualification; no development outcomes generated."""
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
    for b in P['target_blocks']:
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


def pairing_fixture():
    mask=np.zeros((19,4,16,16),bool);mask.reshape(19,4,256)[:,:,:24]=True;birth=np.ones((19,4,2,16,16))
    receipts=[dict(key=[-2,'fixture',j,0],generation=g,injury=24,permutation_sha256='permutation',base_forcing_sha256=f'{j}_{g}',mask_sha256='mask') for g in range(15,34) for j in range(4)]
    a=dict(mask=mask,birth=birth,forcing=receipts,allocation_order=np.tile(np.arange(4),(19,1)));b=copy.deepcopy(a);b['birth'][:,:,1]=2
    return {(-2,24,'matched'):a,(-2,24,'independent'):b}


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

    def test_matched_and_independent_forcing_pairing(self):
        key=[-2,'noise_test',0,0];a,ra=sr_forcing.environment('qualification',key,15,24,'matched');b,rb=sr_forcing.environment('qualification',key,15,24,'independent')
        np.testing.assert_array_equal(a[0],b[0]);np.testing.assert_array_equal(a[1][0],b[1][0]);np.testing.assert_array_equal(a[2][:,0],b[2][:,0])
        np.testing.assert_array_equal(a[2][:,0],a[2][:,1]);self.assertFalse(np.array_equal(b[2][:,0],b[2][:,1]));self.assertEqual(ra['base_forcing_sha256'],rb['base_forcing_sha256'])

    def test_full_native_group_matches_independent_flat(self):
        rows,packets=sr_source.synthetic(-2);envs=[sr_forcing.environment('qualification',[-2,'software_full',j,0],15,24,'matched')[0] for j in range(4)]
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

    def test_verified_exposed_panel_has_all_original_packets(self):
        panel,packets=sr_source.panel();self.assertEqual(panel['blocks'],P['target_blocks']);self.assertEqual(len(panel['rows']),84);self.assertEqual(packets.shape,(21,4,2,16,16))
        rows,a=sr_source.load('development',P['target_blocks'][0]);self.assertEqual(len(rows),4);byte_equal(a,packets[0],'source copy')
        a[:]=0;self.assertFalse(np.array_equal(a,packets[0]))
        with self.assertRaises(ValueError):sr_source.load('development',1000)

    def test_source_selection_rejects_reordered_target_ids(self):
        with patch.dict(P,target_blocks=list(reversed(P['target_blocks']))):
            with self.assertRaises(ValueError):sr_source.panel()

    def test_primary_excludes_preaction_read_and_keeps_terminal_separate(self):
        a=sr_analysis.summarize(example_outcomes(initial=0),P['target_blocks']);b=sr_analysis.summarize(example_outcomes(initial=1),P['target_blocks'])
        self.assertEqual(a['primary'],b['primary']);self.assertEqual(a['cells'],b['cells'])
        self.assertGreater(a['cells']['24']['independent']['all']['writer_success_guard']['downstream_successes']['mean'],0)
        self.assertEqual(a['cells']['24']['independent']['all']['writer_success_guard']['terminal']['mean'],0)

    def test_single_primary_supported_unresolved_and_contradicted(self):
        for kwargs,wanted in [({},'DEVELOPMENT_ALLOCATION_ADVANTAGE_SUPPORTED'),({'tie':True},'DEVELOPMENT_ALLOCATION_UNRESOLVED'),({'negative':True},'DEVELOPMENT_ALLOCATION_PREDICTION_CONTRADICTED')]:
            rows=example_outcomes(**kwargs);a=sr_analysis.summarize(rows,P['target_blocks']);self.assertEqual(a['decision'],wanted);self.assertEqual(sr_analysis.audit_analysis(rows,a)['status'],'PASS')
        report=sr_analysis.report(a,dict(native_reads=12768,flat_reads=12768));self.assertGreater(report.count('\n'),10)

    def test_recovery_reduction_and_structural_first_success(self):
        rows=example_outcomes(initial=0);a=sr_analysis.summarize(rows,P['target_blocks']);self.assertEqual(sr_analysis.audit_recovery(rows,a)['recovery_cells'],16)
        bad=copy.deepcopy(rows);r=next(r for r in bad if r['policy']=='protected_retain');n=r['downstream_successes'];r['passed'][1]=0;r['passed'][n+1]=1
        with self.assertRaises(ArithmeticError):sr_analysis.summarize(bad,P['target_blocks'])

    def test_paired_noise_and_allocation_stage_check(self):
        self.assertEqual(len(sr_verification.verify_forcing_pairs(pairing_fixture(),[-2])),76)

    def test_paired_stage_rejects_allocation_and_forcing_mismatch(self):
        for kind in ['order','base','missing','cuecopy']:
            cases=pairing_fixture();i=cases[-2,24,'independent']
            if kind=='order':i['allocation_order'][0]=[3,2,1,0]
            if kind=='base':i['forcing'][0]['base_forcing_sha256']='wrong'
            if kind=='missing':del cases[-2,24,'matched']
            if kind=='cuecopy':i['birth'][:,:,1]=i['birth'][:,:,0]
            with self.subTest(kind=kind),self.assertRaises(ArithmeticError):sr_verification.verify_forcing_pairs(cases,[-2])

    def test_worker_failure_is_durable_without_target_output(self):
        output=WORK/'expected_failure';task=WORK/'invalid_task.json';write(task,dict(output=str(output),deadline=time.time()+20,parent_pid=-1))
        with (WORK/'expected_failure.log').open('xb') as log:p=subprocess.run([sys.executable,str(ROOT/'sr_worker.py'),str(task)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=25)
        self.assertNotEqual(p.returncode,0);self.assertTrue((output/'FAILED.json').is_file());self.assertFalse((output/'COMPLETE.json').exists())

    def test_pricing_and_fixed_sample_accounting(self):
        self.assertEqual(len(P['target_blocks']),21);self.assertEqual(P['resource']['workers'],7);self.assertEqual(P['counts']['total_full_native_reads'],28*19*4*4*2*2)
        self.assertEqual(P['counts']['target_outcomes'],21*4*4*2);self.assertEqual(P['resource']['combined_seconds'],3600)
        self.assertAlmostEqual(P['primary']['critical_two_sided95'],t.ppf(.975,20));self.assertAlmostEqual(P['primary']['critical_one_sided95'],t.ppf(.95,20))
        self.assertEqual(sr_run.timing_gate(0,100)['status'],'PASS');self.assertEqual(sr_run.timing_gate(700,100)['status'],'FAILED');self.assertEqual(sr_run.timing_gate(0,601)['status'],'FAILED')
        self.assertEqual(sha(ROOT/'context/PRICING.json'),P['source_pricing_sha256'])

    def test_qualified_native_and_forcing_bytes_unchanged(self):
        receipt=read(ROOT/'COPY_RECEIPT.json')
        for field in ['native_files_required_byte_identical','other_files_required_byte_identical']:
            for rel,expected in receipt[field].items():self.assertEqual(sha(ROOT/rel),expected,rel)
        self.assertEqual(bridge.verify_inputs(),len(read(ROOT/'native/INPUTS.json')['sha256']))


if __name__=='__main__':unittest.main()
