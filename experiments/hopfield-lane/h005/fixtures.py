"""Observer boundaries, pairing and lossless transmission fixtures."""
from pathlib import Path
import io
import unittest
import numpy as np
from h005 import engine as e


class Fixtures(unittest.TestCase):
    def test_matching_is_exact_and_all_probes_must_pass(self):
        observed = np.ones((4, 2, 4, 4, 4))
        self.assertTrue(e.match(observed).all())
        observed[3, 1, 2, 1, 2] = .75
        self.assertFalse(e.match(observed)[2, 1])
        observed[:, :, 0, 0, 3] = .5
        self.assertFalse(e.match(observed)[0, 0])
        observed[:, :, 1, 2, :] = .75
        self.assertTrue(e.match(observed)[1, 2])

    def test_observer_agrees_with_original_endpoint(self):
        random = np.random.default_rng(905005)
        states = random.choice([-1., 1.], size=(3, 2, 4, 4, 2, 64))
        for f, rule in enumerate([1, 1, -1, -1]):
            states[0, :, f, :, :, 8:16] = (rule * np.array([-1, 1]))[None, :, None]
            states[0, :, f, :, :, 16:24] = (-rule * np.array([-1, 1]))[None, :, None]
        _, original = e.e.h001.score(states, 'function', None, np.array([-1., 1.]))
        np.testing.assert_array_equal(e.success(states), original)
        self.assertTrue(e.success(states)[0].all())
        states[0, 0, 0, 0, 0, 8:10] = 1  # exactly .5 target margin is a failure
        self.assertFalse(e.success(states)[0, 0, 0, 0])

    def test_packet_code_is_lossless_and_rejects_wrong_boundary(self):
        random = np.random.default_rng(905006)
        states = random.choice([-1., 1.], size=(2, 4, 4, 2, 64))
        packet = e.e.m.write_body(states)
        np.testing.assert_array_equal(e.decode(e.encode(packet)), packet)
        packet[0, 0, 0, 0, 1] = .001
        with self.assertRaises(AssertionError):
            e.encode(packet)

    def test_history_label_cannot_change_equalized_reader(self):
        base, founder, initial, cues, stable = e.e.h001.acquire(12900, 'function')
        own = np.broadcast_to(initial[None, :, None], (2, 4, 4, 64, 64)).copy()
        own[0] = 0
        source = dict(base=base, records=own)
        packets = e.initial_records(source)
        actual = e.read(packets, base, 12900, 'fixture')
        equalized = e.ARMS.index('equalized')
        np.testing.assert_array_equal(actual[0, equalized], actual[1, equalized])
        existing = e.e.read_one(packets, base, 12900, ('h005', 'fixture'), 4., e.e.INPUTS)
        np.testing.assert_array_equal(actual, existing)
        self.assertFalse(np.array_equal(e.e.m.rng(12900, 'h005', 'screen', 0).random(20),
                                       e.e.m.rng(12900, 'h005', 'future', 0).random(20)))

    def test_future_advantage_cannot_rescue_failed_matching_validation(self):
        from h005.analysis import infer
        config = dict(mode='development', analysis_seed=950005, bootstrap_draws=2000)
        current = np.ones((24, 2)); outputs = np.ones((24, 2, 4))
        future = np.zeros((24, 4, 2, len(e.ARMS)))
        future[:, :, 0, 0] = .6; future[:, :, 1, 0] = .9
        decision, _ = infer(current, outputs, future, [4]*24, config, True)
        self.assertTrue(decision['qualified'])
        current[:, 0] = .8
        failed, _ = infer(current, outputs, future, [4]*24, config, True)
        self.assertFalse(failed['qualified'])
        self.assertTrue(failed['gates']['history_gain4_minus_gain1_minimum_effect'])
        self.assertFalse(failed['gates']['current_success_equivalent_within_5pp'])
        failed, _ = infer(np.ones((24, 2)), outputs, future, [1]*24, config, True)
        self.assertFalse(failed['qualified'])
        self.assertFalse(failed['gates']['at_least_64_matched_pairs'])


def run_tests(path):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    Path(path).write_text(stream.getvalue())
    if not result.wasSuccessful():
        raise AssertionError('H005 scientific fixtures failed')
