"""Small scientific fixtures for the new interventions and independent replay."""
from dataclasses import asdict, replace
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E016_teaching_consistency import model, run as study, audit
import numpy as np


class ConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, read_steps=10, observe_steps=4)
        cls.source = model.teach(study.BENCHMARK, cls.cfg)
        cls.packets, _ = model.initial_packets(cls.source["acquired"], study.BENCHMARK, cls.cfg)

    def test_coordinated_teaching_and_gauge_identity(self):
        states = self.source["capture_states"]
        np.testing.assert_allclose(states[1, 0], -states[1, 1], rtol=0, atol=1e-10)
        np.testing.assert_array_equal(states[0, 0], states[1, 0])
        np.testing.assert_allclose(self.source["episode_weights"][1, 0], self.source["episode_weights"][1, 1], rtol=0, atol=1e-10)
        random = study.rng("E016", "fixture", "gauge")
        v = random.normal(0, .3, (4, 16, 16))
        noise = random.normal(size=v.shape)
        s = self.source["engineered_signs"]
        actual = s * model.base.step(v, self.source["weights"][2], 2., noise, self.cfg)
        expected = model.base.step(s*v, np.ones((2, 16, 16)), 2., s*noise, self.cfg)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=2e-15)

    def test_label_exclusion_and_control_pairing(self):
        normal = model.read(self.packets, study.BENCHMARK, self.cfg)
        with patch.object(model, "RULES", np.array([.2, .8, -.4, -.7])), patch.object(model.base, "RULES", np.zeros(4)):
            changed = model.read(self.packets, study.BENCHMARK, self.cfg)
        for key in normal: np.testing.assert_array_equal(normal[key], changed[key])
        for a in (5, 6):
            np.testing.assert_array_equal(normal["end"][:, :, :, 0, :, a][..., ~model.PORTS[0]],
                                          normal["end"][:, :, :, 1, :, a][..., ~model.PORTS[0]])
        for a in (3, 4):
            for m in (1, 2): np.testing.assert_array_equal(normal["port_trace"][:, 0, ..., a, :], normal["port_trace"][:, m, ..., a, :])
        np.testing.assert_array_equal(model.base.encode(model.base.decode(self.packets)), self.packets)

    def test_independent_end_to_end(self):
        parent = HERE / "analysis"
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="fixture_", dir=parent) as directory:
            started = time.monotonic()
            output = study.new_run(Path(directory)/"run", study.input_paths(), dict(experiment="E016",
                blocks=[study.BENCHMARK], gain=2., regimes=model.REGIMES, config=asdict(self.cfg), workers=1, mode="technical_fixture"))
            study.save_block(output, study.BENCHMARK, self.cfg)
            summary = study.analyze(output, [study.BENCHMARK], True, self.cfg)
            self.assertEqual(summary["status"], "TECHNICAL_ONLY")
            self.assertIsNone(summary["primary"]["lower_bound_above_zero"])
            study.finish(output, started, dict(experiment="E016", blocks_completed=1))
            receipt = audit.audit(output, workers=1)
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(receipt["individual_observations"], 1008)


if __name__ == "__main__":
    unittest.main(verbosity=2)
