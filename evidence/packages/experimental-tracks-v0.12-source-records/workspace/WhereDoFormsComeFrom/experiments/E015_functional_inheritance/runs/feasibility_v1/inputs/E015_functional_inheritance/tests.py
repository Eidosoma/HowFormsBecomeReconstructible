"""Short locality, information-flow and end-to-end scientific fixtures."""
from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E015_functional_inheritance import run as study, model as tissue, audit
import numpy as np


class FunctionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(tissue.CFG, recipients=2, teach_steps=12, capture_steps=6, read_steps=10, observe_steps=4)
        cls.source = tissue.teach(study.BENCHMARK, cls.cfg)
        cls.packets, _ = tissue.initial_packets(cls.source["acquired"], study.BENCHMARK, cls.cfg)

    def test_reciprocal_edges_and_locality(self):
        random = study.rng("E015", "fixture", "locality")
        weights = random.uniform(-1, 1, (2, 16, 16)); v = random.normal(0, .2, (16, 16))
        matrix = np.zeros((256, 256))
        for y in range(16):
            for x in range(16):
                i = 16*y+x
                for channel, yy, xx in ((0, y, (x+1) % 16), (1, (y+1) % 16, x)):
                    j = 16*yy+xx; matrix[i, j] = matrix[j, i] = weights[channel, y, x]
        np.testing.assert_allclose(tissue.neighbor_sum(v, weights).ravel(), matrix @ v.ravel(), rtol=1e-14, atol=1e-14)
        stimulus = np.zeros((16, 16)); stimulus[6, 7] = .1
        changed = tissue.step(stimulus, weights, 2., np.zeros_like(stimulus))
        neighborhood = np.zeros((16, 16), bool)
        for y, x in ((6, 7), (5, 7), (7, 7), (6, 6), (6, 8)): neighborhood[y, x] = True
        self.assertFalse(changed[~neighborhood].any())
        marker = stimulus != 0
        incident = np.stack((marker | np.roll(marker, -1, -1), marker | np.roll(marker, -1, -2)))
        np.testing.assert_array_equal(tissue.correlations(v)[~incident], tissue.correlations(v+stimulus)[~incident])

    def test_reader_excludes_labels_and_input_cut_is_exact(self):
        normal = tissue.read(self.packets, study.BENCHMARK, "fixture", cfg=self.cfg)
        with patch.object(tissue, "RULES", np.array([.7, .4, -.2, -.9])):
            changed = tissue.read(self.packets, study.BENCHMARK, "fixture", cfg=self.cfg)
        for key in normal: np.testing.assert_array_equal(normal[key], changed[key])
        for arm in ("communication_off", "source_cut"):
            a = tissue.ARMS.index(arm)
            np.testing.assert_array_equal(normal["end"][:, :, :, 0, :, a][..., ~tissue.PORTS[0]],
                                          normal["end"][:, :, :, 1, :, a][..., ~tissue.PORTS[0]])
        np.testing.assert_array_equal(tissue.encode(tissue.decode(self.packets)), self.packets)

    def test_independent_end_to_end(self):
        parent = HERE / "analysis"; parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="fixture_", dir=parent) as temp:
            started = time.monotonic()
            run = study.new_run(Path(temp) / "run", study.input_paths(), dict(experiment="E015", stage="feasibility",
                blocks=[study.BENCHMARK], gains=tissue.GAINS, config=asdict(self.cfg), workers=1, mode="technical_fixture"))
            study.save_block(run, study.BENCHMARK, self.cfg)
            summary = study.analyze(run, [study.BENCHMARK], True, self.cfg)
            self.assertEqual(summary["status"], "TECHNICAL_ONLY"); self.assertIsNone(summary["selected_gain"])
            study.finish(run, started, dict(experiment="E015", blocks_completed=1))
            receipt = audit.audit(run, workers=1)
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(receipt["individual_observations"], 672)


if __name__ == "__main__": unittest.main(verbosity=2)
