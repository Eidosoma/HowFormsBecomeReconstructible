"""Duration extension, compact evidence integrity and independent full replay."""
from dataclasses import asdict, replace
import copy
import inspect
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E031_renewal_durability import model, run as study, audit, evidence
from E030_maturing_confirmation import model as confirmed
import numpy as np


class DurabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus(8)
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cls.cycle = model.Cycle(read_steps=24, settling_steps=6, write_steps=8, generations=16)
        source = model.acquisition.teach(study.FIXTURE_BLOCK, cls.cfg)
        packet = np.repeat(source['acquired'][1, :, None], 2, axis=1)
        cls.incoming = np.repeat(packet[None], 10, axis=0)

    def test_unchanged_numerical_operations(self):
        self.assertEqual(model.CFG, confirmed.CFG)
        self.assertEqual(replace(model.CYCLE, generations=3), confirmed.CYCLE)
        self.assertEqual(model.HORIZONS, (0, 1, 3, 8, 16))
        self.assertEqual(len(model.PANELS), 82)
        for name in ('selective_packet', 'reading_denominators', 'develop', 'write_from_activity'):
            self.assertEqual(inspect.getsource(getattr(model, name)), inspect.getsource(getattr(confirmed, name)))
        new = inspect.getsource(model.replace_record).replace('cycle.generations in (3, 16) and 1 <= generation <= cycle.generations', 'cycle.generations == 3 and 1 <= generation <= 3')
        self.assertEqual(new, inspect.getsource(confirmed.replace_record))
        for name in ('assay', 'score', 'receiver_denominators'):
            self.assertIs(getattr(model, name), getattr(confirmed, name))
        for name in ('CONDITIONS', 'ACTIVE', 'READER_MODES', 'THRESHOLDS', 'REFRESH', 'SELECTORS'):
            self.assertEqual(getattr(model, name), getattr(confirmed, name))

    def test_all_three_generation_branches_match_confirmed(self):
        incoming = self.incoming.copy()
        for g in range(1, 4):
            new = model.replace_record(incoming, study.FIXTURE_BLOCK, g, self.cfg, self.cycle)
            old = confirmed.replace_record(incoming, study.FIXTURE_BLOCK, g, self.cfg, replace(self.cycle, generations=3))
            self.assertEqual(new.keys(), old.keys())
            for key in new:
                self.assertEqual(new[key].dtype, old[key].dtype)
                self.assertEqual(new[key].shape, old[key].shape)
                self.assertEqual(new[key].tobytes(), old[key].tobytes(), key)
            incoming = new['outgoing'].copy()
        with self.assertRaises(AssertionError):
            model.replace_record(incoming, study.FIXTURE_BLOCK, 17, self.cfg, self.cycle)

    def test_cutoff_and_repeated_weak_refresh(self):
        old = np.zeros((4, 2, 2, 16, 16))
        above = np.nextafter(.5, 1.)
        old.flat[:9] = [.7, -.7, 1e-250, .5, -.5, above, -above, -0., -.8]
        available = np.ones_like(old, bool); available.flat[8] = False
        packet = model.base.encode(old)
        new, kept, eligible = model.selective_packet(packet, model.base.encode(np.full_like(old, .42)), available)
        np.testing.assert_array_equal(model.base.decode(new).ravel()[:9], [.7, -.7, .42, .42, .42, above, -above, .42, 0.])
        np.testing.assert_array_equal(kept | eligible, available)
        self.assertFalse((kept & eligible).any())
        for v in (.4, .8, .1):
            new, _, _ = model.selective_packet(new, model.base.encode(np.full_like(old, v)), available)
        self.assertEqual(model.base.decode(new).flat[2], .8)
        blocked, _, eligible = model.selective_packet(packet, new, available, refresh=False)
        self.assertFalse(model.base.decode(blocked)[eligible].any())
        legacy, _, _ = model.selective_packet(packet, new, available, threshold=0.)
        self.assertEqual(model.base.decode(legacy).flat[2], 1e-250)

    def test_activity_only_capture_and_explicit_copy(self):
        self.assertEqual(tuple(inspect.signature(model.renewal.capture_from_activity).parameters), ('body', 'cfg'))
        writer = model.write_from_activity
        with patch.object(model, 'develop', wraps=model.develop) as develop:
            def guard(*args):
                self.assertFalse(develop.call_args.args[0].any())
                return writer(*args)
            with patch.object(model, 'write_from_activity', side_effect=guard), patch.object(model, 'assay', side_effect=AssertionError('Feedback')):
                raw = model.replace_record(self.incoming, study.FIXTURE_BLOCK, 16, self.cfg, self.cycle)
        self.assertFalse(raw['erased_packets'].any())
        self.assertFalse(raw['read_packets'][[1, 4]].any())
        self.assertFalse(raw['outgoing'][7].any())
        self.assertTrue(raw['retained_packets'][1].any())
        old = model.base.decode(raw['retained_packets'])
        new = model.base.decode(raw['outgoing'][[0, 1, 8, 9]])
        np.testing.assert_array_equal(new[raw['retained_edges']], old[raw['retained_edges']])
        self.assertFalse(new[3][raw['eligible_edges'][3]].any())
        np.testing.assert_array_equal(raw['computed_packets'], model.renewal.capture_from_activity(raw['developed_end'], self.cfg))

    def test_zero_drive_and_post_damage_denominators(self):
        raw = model.replace_record(self.incoming, study.FIXTURE_BLOCK, 8, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw['read_denominators'], audit.local_denominators(model.base.decode(raw['read_packets']), model.renewal.surviving_edges(raw['body_masks'])))
        self.assertFalse(raw['read_denominators'][[1, 4]].any())
        v = study.rng('E031', 'zero_fixture').normal(0, .1, (2, 16, 16))
        for amplified in (False, True):
            observed = model.renewal.compensated_step(v, np.zeros((2, 16, 16)), np.zeros((16, 16)), np.zeros_like(v), self.cfg, amplified)
            expected = v+self.cfg.dt*((v-v**3 if amplified else -v**3)-2*v)
            np.testing.assert_array_equal(observed, expected)

    def test_compact_terminal_replay_and_mean_scoring(self):
        observed = model.assay(self.incoming, study.FIXTURE_BLOCK, 16, self.cfg, self.cycle)
        path = HERE/'analysis/terminal_evidence_fixture.npz'
        evidence.save(path, observed, 'assay')
        compact = audit.load_compact(path, 'assay')
        replayed = audit.replay_assay(compact, self.incoming, study.FIXTURE_BLOCK, 16, asdict(self.cfg), asdict(self.cycle))
        scored = evidence.score_mean(compact['mean_ports'], self.cfg, model.RULES, model.CUES)
        for original, independent, compressed in zip(model.score(observed['late_ports'], self.cfg), replayed, scored):
            np.testing.assert_array_equal(original, independent)
            np.testing.assert_array_equal(original, compressed)
        self.assertLess(path.stat().st_size, sum(x.nbytes for x in observed.values())/10)

    def test_compact_corruption_and_missing_evidence_rejected(self):
        observed = model.replace_record(self.incoming, study.FIXTURE_BLOCK, 8, self.cfg, self.cycle)
        path = HERE/'analysis/boundary_evidence_fixture.npz'
        evidence.save(path, observed, 'boundary')
        compact = audit.load_compact(path, 'boundary')
        audit.replay_boundary(compact, self.incoming, study.FIXTURE_BLOCK, 8, asdict(self.cfg), asdict(self.cycle))
        bad = copy.deepcopy(compact); bad['outgoing'].flat[0] ^= 1
        with self.assertRaises(AssertionError):
            audit.replay_boundary(bad, self.incoming, study.FIXTURE_BLOCK, 8, asdict(self.cfg), asdict(self.cycle))
        bad = copy.deepcopy(compact); bad.descriptors['developed_end']['sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'array commitment'):
            audit.replay_boundary(bad, self.incoming, study.FIXTURE_BLOCK, 8, asdict(self.cfg), asdict(self.cycle))
        bad = copy.deepcopy(compact); bad['write_state_hashes'][2, 7, 0] ^= 1
        with self.assertRaisesRegex(AssertionError, 'holding digest'):
            audit.replay_boundary(bad, self.incoming, study.FIXTURE_BLOCK, 8, asdict(self.cfg), asdict(self.cycle))
        with np.load(path) as data:
            payload = {k: data[k] for k in data.files}
        index = json.loads(payload['__index__'].tobytes()); del index['arrays']['developed_end']
        payload['__index__'] = np.frombuffer(json.dumps(index).encode(), dtype=np.uint8)
        damaged = HERE/'analysis/missing_evidence_fixture.npz'
        with damaged.open('xb') as handle: np.savez_compressed(handle, **payload)
        with self.assertRaises(AssertionError): audit.load_compact(damaged, 'boundary')
        bad = copy.deepcopy(compact); bad.checked.remove('incoming')
        with self.assertRaisesRegex(AssertionError, 'unreplayed arrays'): audit.coverage(bad)

    def test_primary_and_noninferiority_use_sixteenth_own_scattered_panel(self):
        rates = np.full((3, 82, 3, 7), .25)
        candidate, full = [model.PANELS.index((16, c, 'local_strength')) for c in ('maturing', 'strength_compensated')]
        rates[:, candidate, 1, 0] = [.875, .75, .625]
        rates[:, full, 1, 0] = [.9, .7, .6]
        np.testing.assert_array_equal(study.primary_values(rates), [.875, .75, .625])
        ni = study.noninferiority_values(rates).copy()
        np.testing.assert_array_equal(ni, rates[:, candidate, 1, 0]-rates[:, full, 1, 0])
        rates[:, :72] = .9
        rates[:, :, (0, 2)] = 0.
        rates[:, :, :, 1:] = .8
        np.testing.assert_array_equal(study.primary_values(rates), [.875, .75, .625])
        np.testing.assert_array_equal(study.noninferiority_values(rates), ni)

    def test_independent_end_to_end_all_sixteen_boundaries(self):
        output = HERE/'analysis/fixture_attempt1'
        started = time.monotonic()
        study.new_run(output, study.input_paths(), dict(experiment='E031', blocks=[study.FIXTURE_BLOCK], gain=2.,
            panels=model.PANELS, conditions=model.CONDITIONS, receivers=model.RECEIVERS,
            config=asdict(self.cfg), cycle=asdict(self.cycle), workers=1, mode='technical_fixture'))
        study.save_block(output, study.FIXTURE_BLOCK, self.cfg, self.cycle)
        result = study.analyze(output, [study.FIXTURE_BLOCK], True, self.cfg, self.cycle)
        self.assertEqual(result['status'], 'TECHNICAL_ONLY')
        self.assertIsNone(result['primary']['lower_bound_above_075'])
        self.assertIsNone(result['noninferiority']['lower_bound_above_minus_005'])
        self.assertIsNone(result['full_durability_qualified'])
        self.assertIsNone(result['qualification_requirements_pass'])
        self.assertEqual(len(result['qualification_gates']), 23)
        self.assertEqual(len(result['boundary_gates']), 12)
        self.assertEqual(result['primary']['statistics'], result['groups']['16']['local_strength']['maturing']['both_cues']['scattered']['own'])
        study.finish(output, started, dict(experiment='E031', blocks_completed=1))
        receipt = audit.audit(output, workers=1)
        self.assertEqual(receipt['status'], 'PASS')
        self.assertEqual(receipt['individual_observations'], 27552)
        self.assertEqual(receipt['body_individual_observations'], 2048)


if __name__ == '__main__': unittest.main(verbosity=2)
