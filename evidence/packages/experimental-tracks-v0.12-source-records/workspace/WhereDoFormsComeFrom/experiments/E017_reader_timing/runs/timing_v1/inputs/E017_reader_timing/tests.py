"""Local-equation, information-flow, prefix and independent replay fixtures."""
from dataclasses import asdict, replace
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E017_reader_timing import model, run as study, audit
import numpy as np


class TimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, read_steps=10, observe_steps=4)
        cls.timing = model.Timing(baseline_steps=10, total_steps=24, settling_steps=6)
        cls.source = model.acquisition.teach(study.BENCHMARK, cls.cfg)
        cls.packets, _ = model.initial_packets(cls.source, study.BENCHMARK, cls.cfg)

    def test_removed_linear_term_and_locality(self):
        stream = study.rng("E017", "fixture", "locality")
        v = stream.normal(0, .1, (16, 16))
        weights = stream.uniform(-1, 1, (2, 16, 16))
        noise = stream.normal(size=v.shape)
        delta = model.base.step(v, weights, 2., noise, self.cfg)-model.unamplified(v, weights, noise, self.cfg)
        np.testing.assert_allclose(delta, self.cfg.dt*v, rtol=0, atol=1e-15)
        np.testing.assert_array_equal(model.unamplified(v, weights, noise, self.cfg), audit.advance_off(v, weights, noise, asdict(self.cfg)))
        impulse = np.zeros((16, 16))
        impulse[6, 7] = .1
        changed = model.unamplified(impulse, weights, np.zeros_like(impulse), self.cfg)
        local = np.zeros((16, 16), bool)
        for y, x in ((6, 7), (5, 7), (7, 7), (6, 6), (6, 8)): local[y, x] = True
        self.assertFalse(changed[~local].any())

    def test_label_exclusion_isolation_and_prefix(self):
        raw = model.read(self.packets, study.BENCHMARK, self.cfg, self.timing)
        with patch.object(model, "RULES", np.array([.3, -.2, .9, .4])), patch.object(model.base, "RULES", np.zeros(4)):
            changed = model.read(self.packets, study.BENCHMARK, self.cfg, self.timing)
        for key in raw: np.testing.assert_array_equal(raw[key], changed[key])
        for arm in (5, 6):
            np.testing.assert_array_equal(raw["port_trace"][:, :, :, :, :, 0, :, arm], raw["port_trace"][:, :, :, :, :, 1, :, arm])
        longer = model.read(self.packets, study.BENCHMARK, self.cfg, replace(self.timing, total_steps=30))
        np.testing.assert_array_equal(raw["port_trace"], longer["port_trace"][:24])
        np.testing.assert_array_equal(raw["endpoints"][0], longer["endpoints"][0])
        np.testing.assert_array_equal(raw["late_mean"][0], longer["late_mean"][0])
        np.testing.assert_array_equal(self.packets, raw["packets"])

    def test_independent_end_to_end(self):
        parent = HERE/"analysis"
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="fixture_", dir=parent) as folder:
            started = time.monotonic()
            output = study.new_run(Path(folder)/"run", study.input_paths(), dict(experiment="E017", blocks=[study.BENCHMARK],
                gain=2., regimes=model.REGIMES, conditions=model.CONDITIONS, config=asdict(self.cfg), timing=asdict(self.timing),
                workers=1, mode="technical_fixture"))
            study.save_block(output, study.BENCHMARK, self.cfg, self.timing)
            result = study.analyze(output, [study.BENCHMARK], True, self.cfg, self.timing)
            self.assertEqual(result["status"], "TECHNICAL_ONLY")
            self.assertIsNone(result["primary"]["lower_bound_above_zero"])
            study.finish(output, started, dict(experiment="E017", blocks_completed=1))
            receipt = audit.audit(output, workers=1)
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(receipt["individual_observations"], 2016)


if __name__ == "__main__": unittest.main(verbosity=2)
