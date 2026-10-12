"""Twelve checks on synthetic and excluded inputs before fresh scientific receiving."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, rng
from E050_fresh_rollback_confirmation import model, run, audit
import numpy as np


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cap_cpus(8); _, cls.cfg, cls.cycle = run.configuration('fixture')
        cls.source = model.acquisition.teach(900041, cls.cfg)
        cls.original = ROOT/'E041_full_rewrite_confirmation/runs/fixture_v1'
        cls.reference = ROOT/'E049_rollback_persistence/runs/fixture_v1'
        cls.initial = np.repeat(cls.source['acquired'][1, :, None], cls.cfg.recipients, axis=1)
        records = cls.initial.copy(); cls.boundaries = {}; observations = dict(correct=[], margin=[], ports=[])
        for g in range(1, 33):
            raw = model.baseline(records, 900041, g, cls.cfg, cls.cycle); cls.boundaries[g] = raw
            for k,v in model.baseline_score(raw['mean_ports'], cls.cfg).items(): observations[k].append(v)
            records = raw['outgoing'].copy()
        cls.baseline_cases = {k:np.stack(v) for k,v in observations.items()}

    def selection(self, index):
        n = len(index); old = np.empty((n, 4096), np.uint8); new = old.copy(); dead = np.empty((n, 16, 16), bool)
        for j, (f,r,g) in enumerate(index.tolist()):
            old[j] = self.boundaries[g]['incoming'][f,r]; new[j] = self.boundaries[g]['outgoing'][f,r]
            dead[j] = self.boundaries[g]['masks'][f,r]
        return model.construct(old, new, dead, index, 900041)

    def test_01_fresh_ids_and_fixed_configuration(self):
        ids,cfg,cycle = run.configuration('scientific')
        spec = json.loads((HERE/'SOURCE_DATA.json').read_text())
        self.assertEqual(ids, list(range(33000,33032))); self.assertFalse(set(ids) & set(spec['prior_block_ids']))
        self.assertEqual(asdict(cfg), audit.EXPECTED)
        self.assertEqual(asdict(cycle), dict(read_steps=2048, settling_steps=1024, write_steps=128, generations=32))
        self.assertEqual(len(run.input_paths()), 23)

    def test_02_teaching_replay_and_reference_capture_commitment(self):
        audit.equal_dict(self.source, audit.teaching(900041, asdict(self.cfg)))
        expected = run.load(self.original/'source_900041.npz'); meta = json.loads(expected.pop('__index__').tobytes())
        audit.equal_dict({k:v for k,v in self.source.items() if k != 'capture_states'}, expected)
        self.assertEqual(hashlib.sha256(self.source['capture_states'].tobytes()).hexdigest(), meta['arrays']['capture_states']['sha256'])

    def test_03_all_32_baselines_reproduce_e041_original(self):
        prior = run.load(self.original/'cases_900041.npz')
        for k in self.baseline_cases: run.equal(self.baseline_cases[k], prior['body_'+k][:,3], k)
        for g,raw in self.boundaries.items():
            expected = run.load(self.original/f'boundary_900041_g{g}.npz')
            run.equal(raw['outgoing'], expected['outgoing'][3]); run.equal(raw['masks'], expected['renewal_mask'])

    def test_04_independent_all_array_baseline_replay(self):
        records = self.initial.copy()
        for g in range(1,33):
            raw = audit.replay_baseline(records, 900041, g, asdict(self.cfg), asdict(self.cycle))
            audit.equal_dict(raw, self.boundaries[g]); records = raw['outgoing'].copy()

    def test_05_complete_eligible_continuation_reproduces_e049(self):
        first,index = model.first_failures(self.baseline_cases['correct']); selection = self.selection(index)
        expected = run.load(self.reference/'selection_900041.npz')
        for k in selection: run.equal(selection[k], expected[k], k)
        run.equal(first, expected['first_failure'])
        records = selection['packets'].copy(); observations = dict(correct=[], margin=[], ports=[])
        for d in (1,2,3):
            raw = model.rebuild(records,index,d,900041,self.cfg,self.cycle)
            audit.equal_dict(raw, run.load(self.reference/f'boundary_900041_d{d}.npz'))
            for k,v in model.score(raw['mean_ports'],index,self.cfg).items(): observations[k].append(v)
            records = raw['outgoing'].copy()
        audit.equal_dict({k:np.stack(v) for k,v in observations.items()}, run.load(self.reference/'cases_900041.npz'))

    def test_06_acquisition_start_and_full_paired_birth_stream(self):
        run.equal(self.boundaries[1]['incoming'], self.initial)
        for g in (1,17,32):
            expected = self.cfg.birth_sd*model.base.paired_founders(rng('E022',900041,'develop',g).standard_normal((2,self.cfg.recipients,16,16)))
            run.equal(self.boundaries[g]['birth'], expected)
        self.assertEqual(self.cycle.settling_steps, 12)
        with self.assertRaises(AssertionError): model.baseline(self.initial,900041,33,self.cfg,self.cycle)

    def test_07_mixed_onset_chain_including_generation_32(self):
        index = np.array([[0,0,1],[1,1,2],[2,0,5],[3,1,29]], np.int64)
        selection = self.selection(index); records = selection['packets'].copy(); replay = records.copy()
        for d in (1,2,3):
            actual = model.rebuild(records,index,d,900041,self.cfg,self.cycle)
            independent = audit.branch.replay(replay,index,d,900041,asdict(self.cfg),asdict(self.cycle))
            audit.equal_dict(actual, independent)
            for j,(f,r,g) in enumerate(index.tolist()): run.equal(actual['outgoing'][0,j],self.boundaries[g+d]['outgoing'][f,r])
            records,replay = actual['outgoing'].copy(),independent['outgoing'].copy()

    def test_08_capture_before_holding_and_full_physical_rewriting(self):
        raw = self.boundaries[7]; available = model.renewal.surviving_edges(raw['masks'])
        run.equal(raw['computed_packets'],audit.baseline_capture(raw['end'],self.cfg.writer_beta))
        self.assertNotEqual(raw['end'].tobytes(),raw['write_end'].tobytes())
        self.assertNotEqual(raw['computed_packets'].tobytes(),audit.baseline_capture(raw['write_end'],self.cfg.writer_beta).tobytes())
        outgoing,computed = model.base.decode(raw['outgoing']),model.base.decode(raw['computed_packets'])
        run.equal(outgoing[available],computed[available]); run.equal(outgoing[~available],np.zeros_like(outgoing[~available]))
        self.assertTrue(np.any(outgoing[available] != model.base.decode(raw['incoming'])[available]))

    def test_09_cohort_boundaries_and_later_outcomes_do_not_select(self):
        correct = np.ones((32,4,2,2),bool)
        correct[0,0,0,0]=False; correct[28,1,0,1]=False; correct[29,2,0]=False; correct[31,3,0]=False
        first,index=model.first_failures(correct)
        np.testing.assert_array_equal(index,[[0,0,1],[1,0,29]])
        self.assertEqual(first[2,0],30); self.assertEqual(first[3,0],32)
        changed=correct.copy(); changed[1:,0,0]=False; changed[29:,1,0]=False
        again,other=model.first_failures(changed); run.equal(first,again); run.equal(index,other)

    def test_10_empty_cohort_and_block_pooled_inference(self):
        _,index=model.first_failures(np.ones((32,4,2,2),bool)); self.assertEqual(index.shape,(0,3))
        packet=np.empty((3,0,4096),np.uint8)
        for d in (1,2,3):
            actual=model.rebuild(packet,index,d,900041,self.cfg,self.cycle)
            audit.equal_dict(actual,audit.branch.replay(packet,index,d,900041,asdict(self.cfg),asdict(self.cycle)))
            packet=actual['outgoing']
        st=run.statistics([1,0,0],[1,9,0]); self.assertEqual(st['mean'],.1); self.assertLess(st['bootstrap_valid'],10000)
        st=run.statistics([0,0],[0,0]); self.assertIsNone(st['mean']); self.assertEqual(st['bootstrap_valid'],0)

    def test_11_episodes_losses_and_three_strict_gates(self):
        patterns=np.array([[7,4,2,0],[7,6,1,0],[0,5,3,7]],np.int8)
        correct=np.repeat(np.stack([(patterns & bit)!=0 for bit in (4,2,1)])[...,None],2,axis=-1)
        episodes,codes=run.episode_values(correct); run.equal(codes,patterns)
        np.testing.assert_array_equal(episodes['sustained'].sum(axis=1),[1,1,1]); np.testing.assert_array_equal(run.loss_counts(correct[2]),[0,1])
        keys=('original','full_rollback','loss_reduction')
        def decision(values,technical=False): return run.decision({k:dict(ci95=[lo,.2]) for k,lo in zip(keys,values)},technical)
        self.assertTrue(decision([.051,.001,.001]))
        for values in ([.05,.01,.01],[.06,0,.01],[.06,.01,0],[None,None,None]): self.assertFalse(decision(values))
        self.assertIsNone(decision([.1,.1,.1],True))

    def test_12_source_packet_and_holding_corruption_detected(self):
        altered={k:v.copy() for k,v in self.source.items()}; altered['capture_states'].flat[0]+=.01
        with self.assertRaises(AssertionError): audit.equal_dict(self.source,altered)
        raw=self.boundaries[1]
        for key in ('outgoing','write_state_hashes','computed_packets'):
            altered={k:v.copy() for k,v in raw.items()}; altered[key].flat[0]^=np.uint8(1)
            with self.assertRaises(AssertionError): audit.equal_dict(raw,altered)


if __name__=='__main__': unittest.main(verbosity=2)
