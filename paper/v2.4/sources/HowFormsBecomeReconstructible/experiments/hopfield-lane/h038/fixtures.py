"""Small executable controls before serial guidance interventions."""
import io
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import model as m
from h035 import design as d, experiment as old
from h038 import experiment as e
from h038.audit import audit, bit_score, reference_read


class Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = old.lineage('fixture', 0, generations=1)
        cls.raw = e.generate(cls.source, 'fixture', 0, count=1)

    def test_full_independent_replay(self):
        self.assertTrue(audit(self.source, self.raw, 'fixture', 0)['passed'])

    def test_gain_geometry_and_original_reader(self):
        rec = self.source['records'][0]
        np.testing.assert_array_equal(e.weights(self.source['base'], rec, 4), old.effective_weights(self.source['base'], rec))
        w = e.weights(self.source['base'], rec, 8)
        np.testing.assert_array_equal(w, w.swapaxes(-1, -2))
        self.assertFalse(np.diagonal(w, axis1=-2, axis2=-1).any())

    def test_no_formation_or_observer_labels_after_acquisition(self):
        with (patch.object(old, 'acquire', side_effect=AssertionError('Formation called')),
              patch.object(d, 'RULES', -d.RULES),
              patch.object(d, 'TARGETS', np.full_like(d.TARGETS, np.nan))):
            raw = e.generate(self.source, 'fixture', 0, count=1)
        for k in raw:
            np.testing.assert_array_equal(raw[k], self.raw[k])

    def test_assay_does_not_change_inheritance(self):
        births, orders = e.probes(self.source, 'fixture', 0, 1)
        births = -births
        with patch.object(e, 'probes', return_value=(births, orders)):
            raw = e.generate(self.source, 'fixture', 0, count=1)
        for k in ('records', 'bodies'):
            np.testing.assert_array_equal(raw[k], self.raw[k])

    def test_source_immutable(self):
        before = {k: v.copy() for k, v in self.source.items()}
        e.generate(self.source, 'fixture', 0, count=1)
        for k in before:
            np.testing.assert_array_equal(before[k], self.source[k])

    def test_probe_namespaces_and_legacy_control(self):
        a, b = [e.probes(self.source, cohort, 0, 1) for cohort in ('pilot', 'engineering')]
        for k in (0, 1):
            np.testing.assert_array_equal(a[k][:, 0], b[k][:, 0])
            self.assertFalse(np.array_equal(a[k][:, 1], b[k][:, 1]))
            np.testing.assert_array_equal(a[k], e.probes(self.source, 'pilot', 0, 1)[k])

    def test_strict_observer_and_single_rule_body(self):
        x = np.ones((4, 2, 4, 64))
        x[..., 8:16] = d.TARGETS[:, None, :, None]
        x[..., 16:24] = -d.TARGETS[:, None, :, None]
        self.assertTrue(bit_score(x)[1].all())
        for l, schedule in enumerate(d.SCHEDULES):
            self.assertTrue(e.body_success(x[:, :, schedule], l).all())
        x[0, 0, 0, 8:10] *= -1
        self.assertFalse(bit_score(x)[1][0, 0])
        self.assertFalse(e.score(x, 2)[0][0, 0])

    def test_zero_field_retains_free_bits(self):
        rec = np.zeros((4, 2, 64, 64)); base = np.zeros((64, 64))
        birth = self.source['assay_birth'][0]; order = self.source['assay_orders'][0]
        expected = np.broadcast_to(birth, (4, 2, 4, 64)).copy(); expected[..., :4] = d.CUES
        for gain in e.GAINS:
            np.testing.assert_array_equal(e.read(rec, base, birth, order, d.CUES, gain), expected)
            np.testing.assert_array_equal(reference_read(rec, base, birth, order, d.CUES, gain), expected)


def run_tests(path):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    Path(path).write_text(stream.getvalue())
    if not result.wasSuccessful():
        raise AssertionError(stream.getvalue())
    return dict(tests=result.testsRun, passed=True)
