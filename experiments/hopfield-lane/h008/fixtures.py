"""Independent enrollment, serial-boundary and two-sided-decision fixtures."""
from pathlib import Path
import io
import unittest
from unittest.mock import patch
import numpy as np
from h008 import engine as e
from h008.inference import current_decision, future_decision, mean_pairs
from h007.fixtures import fixture_source


def fixture_inputs():
    source = fixture_source()
    changed = e.selected.construct(980008, source)
    d = e.selected.DOSES.index(e.DOSE)
    candidate = dict(packet_codes=e.encode(changed['packets'][d]),
                     changed_bodies=changed['changed_bodies'][d], permutations=changed['permutations'][d],
                     feasible=changed['feasible'], eligible=np.ones((4, 4), bool))
    return source, candidate


class Fixtures(unittest.TestCase):
    def test_new_validation_cannot_rematch_or_change_the_input(self):
        source, candidate = fixture_inputs()
        candidate['eligible'][0, 0] = False
        before = {k: v.copy() for k, v in candidate.items()}
        failed = np.ones((2, 4, 4, 2, 64))
        with patch.object(e, 'read', return_value=failed):
            measured = e.measure(980008, source, candidate)
        self.assertFalse(measured['validation_success'].any())
        np.testing.assert_array_equal(measured['eligible'], before['eligible'])
        for name, value in before.items():
            np.testing.assert_array_equal(candidate[name], value)
        np.testing.assert_array_equal(e.decode(candidate['packet_codes'])[0], source['records'])

    def test_new_random_tapes_and_original_reader_compatibility(self):
        source, candidate = fixture_inputs()
        packets = e.decode(candidate['packet_codes'])
        observed = e.read(packets, source['base'], 980008, 'fixture')
        reference = e.model.read_one(packets, source['base'], 980008, ('h008', 'fixture'), 4., e.model.INPUTS)
        np.testing.assert_array_equal(observed, reference)
        a = e.model.m.rng(980008, 'h008', 'future', 0, 'damage', 1).random(32)
        b = e.model.m.rng(980008, 'h007', 'replacement', 0, 'damage').random(32)
        c = e.model.m.rng(980008, 'h008', 'current', 'validation', 0).random(32)
        self.assertFalse(np.array_equal(a, b))
        self.assertFalse(np.array_equal(a, c))

    def test_serial_copy_restore_and_original_function_boundaries(self):
        source, candidate = fixture_inputs()
        with patch.multiple(e, GENERATIONS=3, CHECKPOINTS=(1, 3)):
            raw = e.rollout(980008, source, candidate, 0)
        packets = e.decode(raw['record_codes'])
        for v in range(2):
            np.testing.assert_array_equal(packets[:, v, 1], packets[:, 0, 0])
            np.testing.assert_array_equal(raw['bodies'][:, v, 1], raw['bodies'][:, 0, 0])
            np.testing.assert_array_equal(raw['reader_states'][:, v, 1], raw['reader_states'][:, 0, 0])
        retained = packets[0, :, 4].copy()
        for g in range(1, 4):
            retained *= raw['damage'][g-1]
            np.testing.assert_array_equal(packets[g, :, 4], retained)
            np.testing.assert_array_equal(packets[g, :, 3], packets[0, :, 3])
            self.assertFalse(packets[g, :, 6].any())
            np.testing.assert_array_equal(packets[g, :, 0], e.model.m.write_body(raw['bodies'][g-1, :, 0]))
        _, endpoint = e.model.h001.score(raw['reader_states'], 'function', None, np.array([-1., 1.]))
        _, body = e.model.h001.score(raw['bodies'], 'function', None, np.array([-1., 1.]))
        np.testing.assert_array_equal(raw['success'], endpoint)
        np.testing.assert_array_equal(raw['uninterrupted'], body.all(axis=0) & endpoint[-1])
        own = np.all(packets == e.decode(candidate['packet_codes'])[:, None], axis=(-2, -1))
        distinct = np.any(packets[:, 0] != packets[:, 1], axis=(-2, -1))
        np.testing.assert_array_equal(raw['own_retained'], own)
        np.testing.assert_array_equal(raw['distinct'], distinct)
        joint = (own[[1, 3]] & body[[0, 2]] & endpoint).all(axis=1) & distinct[[1, 3]]
        np.testing.assert_array_equal(raw['joint_functional_retention'], joint)

    def test_current_gate_and_network_weighting(self):
        config = dict(analysis_seed=980008, bootstrap_draws=2000, mode='development')
        outputs = np.ones((24, 2, 4))
        self.assertTrue(current_decision(np.ones((24, 2)), outputs, [8]*24, config)['passed'])
        self.assertFalse(current_decision(np.tile([1., .98], (24, 1)), outputs, [8]*24, config)['passed'])
        self.assertFalse(current_decision(np.ones((24, 2)), outputs, [1]*24, config)['passed'])
        one, all_pairs = np.zeros((4, 4), bool), np.ones((4, 4), bool)
        one[0, 0] = True
        a = mean_pairs(np.ones((2, 4, 4)), one)
        b = mean_pairs(np.zeros((2, 4, 4)), all_pairs)
        np.testing.assert_array_equal(np.stack([a, b]).mean(axis=0), [.5, .5])

    def test_two_sided_primary_has_fixed_magnitude_and_route_requirements(self):
        config = dict(analysis_seed=980008, bootstrap_draws=2000, mode='development')
        future = np.zeros((24, 4, 2, 7))
        future[:, :, 0, 0], future[:, :, 1, 0] = .78, .92
        decision, _ = future_decision(future, True, config, True)
        self.assertTrue(decision['qualified'])
        self.assertEqual(decision['primary_direction'], 'hidden_swap_higher')
        reverse, _ = future_decision(future[:, :, ::-1], True, config, True)
        self.assertTrue(reverse['qualified'])
        self.assertEqual(reverse['primary_direction'], 'unchanged_higher')
        self.assertEqual(decision['family_size'], 9)
        self.assertFalse(future_decision(future, False, config, True)[0]['qualified'])
        future[:, -1, 1, 0] = .85  # excellent intermediate effect cannot rescue terminal <10pp
        self.assertFalse(future_decision(future, True, config, True)[0]['qualified'])
        future[:, -1, 1, 0] = .92
        future[:, -1, 0, e.ARMS.index('damaged_copy')] = .70
        self.assertFalse(future_decision(future, True, config, True)[0]['qualified'])
        config['mode'] = 'benchmark'
        self.assertIsNone(future_decision(future, True, config, True)[0]['qualified'])


def run_tests(path):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    Path(path).write_text(stream.getvalue())
    if not result.wasSuccessful():
        raise AssertionError('H008 scientific fixtures failed')
