"""Intervention and feasibility-event invariants for coherent record swaps."""
from pathlib import Path
import io
import unittest
import numpy as np
from h007 import engine as e
from h007.inference import current_decision, transmission_decision


def fixture_source():
    cue = np.array([-1., 1.])
    bodies = np.broadcast_to(cue[:, None], (4, 4, 2, 64)).copy()
    for f, rule in enumerate(e.e.h001.RULES):
        bodies[f, :, :, 8:16] = (rule*cue)[None, :, None]
        bodies[f, :, :, 16:24] = (-rule*cue)[None, :, None]
    bodies[..., 44:64] = -cue[:, None]
    return dict(records=e.e.m.write_body(bodies), source_bodies=bodies, base=np.zeros((64, 64)))


class Fixtures(unittest.TestCase):
    def test_swaps_are_exact_writer_outputs_and_hidden_permutations(self):
        source = fixture_source()
        result = e.construct(970007, source)
        self.assertTrue(result['feasible'].all())
        for d, k in enumerate(e.DOSES):
            original, altered = result['packets'][d]
            np.testing.assert_array_equal(altered, e.e.m.write_body(result['changed_bodies'][d]))
            np.testing.assert_array_equal(altered[..., :24, :24], original[..., :24, :24])
            np.testing.assert_array_equal(np.sort(altered.reshape(4, 4, -1), axis=-1),
                                          np.sort(original.reshape(4, 4, -1), axis=-1))
            np.testing.assert_array_equal(np.sum(altered**2, axis=(-2, -1)), np.sum(original**2, axis=(-2, -1)))
            np.testing.assert_array_equal((altered != original).sum(axis=(-2, -1)), np.full((4, 4), 4*k*(64-2*k)))
            for f in range(4):
                for r in range(4):
                    p = result['permutations'][d, f, r]
                    np.testing.assert_array_equal(p[:24], np.arange(24))
                    np.testing.assert_array_equal(p[p], np.arange(64))
                    np.testing.assert_array_equal(altered[f, r], original[f, r][np.ix_(p, p)])
                    np.testing.assert_array_equal(altered[f, r][np.ix_(p, p)], original[f, r])
            if d:
                before = result['permutations'][d-1] != np.arange(64)
                self.assertFalse(np.any(before & (result['permutations'][d] == np.arange(64))))
        np.testing.assert_allclose(np.linalg.eigvalsh(result['packets'][-1, 0, 0, 0]),
                                   np.linalg.eigvalsh(result['packets'][-1, 1, 0, 0]), atol=1e-12, rtol=0)

    def test_insufficient_pools_and_nonantipodal_sources_are_excluded(self):
        source = fixture_source()
        source['source_bodies'][0, 0, :, 24:] = np.array([-1., 1.])[:, None]
        source['source_bodies'][1, 1, 0, 30] *= -1
        source['records'] = e.e.m.write_body(source['source_bodies'])
        result = e.construct(970007, source)
        self.assertFalse(result['feasible'][0, 0])
        self.assertFalse(result['feasible'][1, 1])
        observed = np.ones((8, 4, 2, 4, 4, 4))
        match = e.matched(observed, result['feasible'])
        self.assertFalse(match[:, 0, 0].any())
        self.assertFalse(match[:, 1, 1].any())
        observed[7, 2, 1, 2, 3, 0] = .75
        self.assertFalse(e.matched(observed, result['feasible'])[2, 2, 3])
        observed[:, 0, :, 3, 2, :] = .5
        self.assertFalse(e.matched(observed, result['feasible'])[0, 3, 2])

    def test_difference_alone_and_failed_function_cannot_count_as_retention(self):
        source = fixture_source()
        result = e.construct(970007, source)
        packets = result['packets']
        original = np.broadcast_to(source['source_bodies'], result['changed_bodies'].shape)
        states = np.stack([original, result['changed_bodies']], axis=1)
        states = np.broadcast_to(states[:, :, None], (4, 2, 7, 4, 4, 2, 64)).copy()
        outgoing = np.broadcast_to(packets[:, :, None], (4, 2, 7, 4, 4, 64, 64)).copy()
        self.assertTrue(e.metrics(outgoing, packets, states, states)['joint_functional_retention'].all())
        outgoing[:, 1, 0] = -packets[:, 1]  # remains different, but is not the intended record
        metrics = e.metrics(outgoing, packets, states, states)
        self.assertTrue(metrics['distinct'][:, 0].all())
        self.assertFalse(metrics['joint_functional_retention'][:, 0].any())
        outgoing[:, 1, 0] = packets[:, 1]
        readers = states.copy()
        readers[:, 1, 0, 0, 0, 0, 8:10] = 1  # strict .5 margin fails
        self.assertFalse(e.metrics(outgoing, packets, states, readers)['joint_functional_retention'][:, 0, 0, 0].any())

    def test_restore_and_dose_labels_have_no_effect_on_unchanged_reader(self):
        source = fixture_source()
        packets = e.construct(970007, source)['packets']
        records = e.initial_records(packets)
        states = e.read(records, source['base'], 970007, 'fixture')
        for d in range(4):
            np.testing.assert_array_equal(states[d, 0, 0], states[0, 0, 0])
            for v in range(2):
                np.testing.assert_array_equal(states[d, v, 1], states[d, 0, 0])
        reference = e.e.read_one(records, source['base'], 970007, ('h007', 'fixture'), 4., e.e.INPUTS)
        np.testing.assert_array_equal(states, reference)

    def test_exact_archive_and_original_endpoint(self):
        source = fixture_source()
        packets = e.construct(970007, source)['packets']
        np.testing.assert_array_equal(e.decode(e.encode(packets)), packets)
        states = source['source_bodies'][None]
        _, old = e.e.h001.score(states, 'function', None, np.array([-1., 1.]))
        np.testing.assert_array_equal(e.success(states), old)
        with self.assertRaises(AssertionError):
            e.encode(packets*.9)

    def test_screen_gates_reject_wrong_scope_and_small_retention(self):
        config = dict(analysis_seed=970007, bootstrap_draws=2000)
        current = np.ones((24, 2))
        outputs = np.ones((24, 2, 4))
        self.assertTrue(current_decision(current, outputs, [8]*24, config)['passed'])
        current[:, 1] = .98
        self.assertFalse(current_decision(current, outputs, [8]*24, config)['passed'])
        joint = np.zeros((24, 7))
        joint[:, 0] = .9
        self.assertTrue(transmission_decision(joint, True, config, True)[0]['passed'])
        self.assertFalse(transmission_decision(joint, False, config, True)[0]['passed'])
        joint[:, 0] = .79
        self.assertFalse(transmission_decision(joint, True, config, True)[0]['passed'])
        joint[:, 0] = .9
        joint[:, e.ARMS.index('read_off')] = .8
        self.assertFalse(transmission_decision(joint, True, config, True)[0]['passed'])
        self.assertFalse(current_decision(np.ones((24, 2)), outputs, [1]*24, config)['passed'])


def run_tests(path):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    Path(path).write_text(stream.getvalue())
    if not result.wasSuccessful():
        raise AssertionError('H007 scientific fixtures failed')
