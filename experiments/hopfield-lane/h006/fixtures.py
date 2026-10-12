"""Scientific boundary checks for the H006 intervention and decision rules."""
from pathlib import Path
import io
import unittest
import numpy as np
from h006 import engine as e
from h006.inference import current_decision, future_decision, select_dose


def fixture_source():
    states = np.ones((4, 4, 2, 64))
    states[..., :4] = np.array([-1., 1.])[:, None]
    for f, rule in enumerate(e.e.h001.RULES):
        states[f, :, :, 8:16] = (rule * np.array([-1., 1.]))[None, :, None]
        states[f, :, :, 16:24] = (-rule * np.array([-1., 1.]))[None, :, None]
    states[..., 24:44] = np.array([-1., 1.])[:, None]
    states[..., 44:64] = -np.array([-1., 1.])[:, None]
    return dict(records=e.e.m.write_body(states), source_bodies=states, base=np.zeros((64, 64)))


class Fixtures(unittest.TestCase):
    def test_exact_strength_location_and_nested_doses(self):
        source = fixture_source()
        result = e.interventions(960006, source)
        packets = result['packets']
        self.assertTrue(result['feasible'].all())
        original = source['records']
        for d, dose in enumerate(e.DOSES):
            np.testing.assert_array_equal(packets[d, 0], original)
            for v, sites in ((1, np.arange(8, 24)), (2, np.arange(24, 64))):
                mask = result['flip_masks'][d, v]
                np.testing.assert_array_equal(mask.sum(axis=(-2, -1)), np.full((4, 4), 2*dose))
                allowed = np.zeros((64, 64), bool)
                allowed[np.ix_(np.arange(4), sites)] = True
                allowed |= allowed.T.copy()
                self.assertFalse(np.any(mask & ~allowed))
                np.testing.assert_array_equal(packets[d, v], packets[d, v].swapaxes(-1, -2))
                self.assertFalse(np.diagonal(packets[d, v], axis1=-1, axis2=-2).any())
                for value in (-1/64, 0., 1/64):
                    np.testing.assert_array_equal((packets[d, v] == value).sum(axis=(-2, -1)),
                                                  (original == value).sum(axis=(-2, -1)))
                np.testing.assert_array_equal(np.sum(packets[d, v]**2, axis=(-2, -1)),
                                              np.sum(original**2, axis=(-2, -1)))
                if d:
                    self.assertFalse(np.any(result['flip_masks'][d-1, v] & ~mask))
            np.testing.assert_array_equal(result['flip_masks'][d, 1, ..., :4, :].sum(axis=-1),
                                          result['flip_masks'][d, 2, ..., :4, :].sum(axis=-1))
            deltas = e.e.effective_weights(source['base'], packets[d], 4., e.e.INPUTS)
            np.testing.assert_array_equal(np.sum((deltas[1]-deltas[0])**2, axis=(-2, -1)),
                                          np.sum((deltas[2]-deltas[0])**2, axis=(-2, -1)))
            np.testing.assert_array_equal(e.cue_link(packets[d, 1]), np.full((4, 4), 1-dose/32))
            np.testing.assert_array_equal(e.cue_link(packets[d, 2]), np.ones((4, 4)))

    def test_infeasible_sources_cannot_enter_the_match(self):
        source = fixture_source()
        source['records'][0, 0] = 0
        result = e.interventions(960006, source)
        self.assertFalse(result['feasible'][0, 0])
        self.assertFalse(result['flip_masks'][:, :, 0, 0].any())
        observed = np.ones((8, 5, 3, 4, 4, 4))
        matched = e.matched(observed, result['feasible'])
        self.assertFalse(matched[:, 0, 0].any())
        observed[7, 1, 2, 1, 2, 0] = .75
        self.assertFalse(e.matched(observed, result['feasible'])[1, 1, 2])
        observed[:, 2, :, 2, 3, :] = .5
        self.assertFalse(e.matched(observed, result['feasible'])[2, 2, 3])

    def test_restoration_removes_variant_identity(self):
        source = fixture_source()
        packets = e.interventions(960006, source, (32,))['packets'][0]
        records = e.initial_records(packets)
        state = e.read(records, source['base'], 960006, 'fixture')
        for v in range(3):
            np.testing.assert_array_equal(records[v, 1], records[0, 0])
            np.testing.assert_array_equal(state[v, 1], state[0, 0])
        reference = e.e.read_one(records, source['base'], 960006, ('h006', 'fixture'), 4., e.e.INPUTS)
        np.testing.assert_array_equal(state, reference)

    def test_observer_and_lossless_archive(self):
        source = fixture_source()
        states = source['source_bodies']
        _, reference = e.e.h001.score(states[None], 'function', None, np.array([-1., 1.]))
        np.testing.assert_array_equal(e.success(states[None]), reference)
        self.assertTrue(e.success(states).all())
        states[0, 0, 0, 8:10] = 1
        self.assertFalse(e.success(states)[0, 0])
        packets = e.interventions(960006, fixture_source())['packets']
        np.testing.assert_array_equal(e.decode(e.encode(packets)), packets)

    def test_dose_and_current_gates_cannot_be_rescued_by_futures(self):
        config = dict(mode='development', analysis_seed=960006, bootstrap_draws=2000)
        current = np.ones((16, 3))
        outputs = np.ones((16, 3, 4))
        present = current_decision(current, outputs, [8]*16, config, 'assay')
        self.assertTrue(present['passed'])
        current[:, 1] = .98  # passes old five-point tolerance, fails new one-point gate
        failed = current_decision(current, outputs, [8]*16, config, 'assay')
        self.assertFalse(failed['passed'])
        future = np.zeros((16, 4, 3, 7))
        future[:, :, 0, 0] = .95
        future[:, :, 1, 0] = .5
        future[:, :, 2, 0] = .9
        self.assertTrue(future_decision(future, True, config, True)[0]['qualified'])
        self.assertFalse(future_decision(future, False, config, True)[0]['qualified'])
        future[:, :, 1, 0] = .86
        self.assertFalse(future_decision(future, True, config, True)[0]['qualified'])
        self.assertEqual(select_dose([dict(dose=4, passed=True), dict(dose=32, passed=False),
                                      dict(dose=16, passed=True)]), 16)
        self.assertIsNone(select_dose([dict(dose=4, passed=False)]))
        self.assertFalse(current_decision(np.ones((16, 3)), outputs, [1]*16, config, 'assay')['passed'])

    def test_probe_stages_and_future_tapes_are_distinct(self):
        streams = [e.e.m.rng(960006, 'h006', *key).random(20) for key in
                   [('selection', 'screen', 0), ('selection', 'validation', 0),
                    ('assay', 'screen', 0), ('assay', 'validation', 0),
                    ('future', 0, 'body', 1), ('future', 1, 'body', 1)]]
        for i, a in enumerate(streams):
            for b in streams[i+1:]:
                self.assertFalse(np.array_equal(a, b))


def run_tests(path):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    Path(path).write_text(stream.getvalue())
    if not result.wasSuccessful():
        raise AssertionError('H006 scientific fixtures failed')
