"""Short physics fixtures; never contribute scientific observations."""
from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import time
import unittest

import run as study
from E014_long_renewal import audit
import numpy as np


class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(study.CFG, formation=12, observation_window=8, capture=7,
                          read=5, write=7, challenge_time=2)
        cls.block = study.BENCHMARK
        cls.source = study.tissue.formation(cls.block, "heterogeneous", cls.cfg)
        acquired, end, first = study.tissue.capture(cls.source["founder_state"], cls.block, cls.cfg)
        cls.source.update(acquired=acquired, capture_end=end, capture_first=first)
        cls.raw = {factor: study.simulate(cls.source, cls.block, factor, cls.cfg) for factor in study.FACTORS}

    def test_original_three_rewrite_prefix_and_probe(self):
        for factor in study.FACTORS:
            original = study.compact.simulate(self.source, self.block, factor, self.cfg)
            extended = self.raw[factor]
            for key in ("incoming", "outgoing", "generation_read", "generation_birth", "generation_mask",
                        "generation_write_birth", "generation_written"):
                np.testing.assert_array_equal(original[key], extended[key][:3])
            np.testing.assert_array_equal(original["terminal"], extended["checkpoint_read"][1])
            self.assertEqual(extended["outgoing"].shape, (16, 4, 2, 10, 2048 // factor**2))

    def test_no_probe_or_observer_feedback(self):
        changed = {key: value.copy() for key, value in self.source.items()}
        changed["prototype"][:] = 0.; changed["prototype_halves"][:] = 0.
        for factor in study.FACTORS:
            sparse = study.simulate(changed, self.block, factor, self.cfg, checkpoints=(16,))
            for key in ("incoming", "outgoing", "generation_read", "generation_written", "terminal"):
                np.testing.assert_array_equal(sparse[key], self.raw[factor][key])

    def test_independent_end_to_end_audit(self):
        parent = study.HERE / "analysis"; parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="fixture_", dir=parent) as tmp:
            started = time.monotonic()
            output = study.new_run(Path(tmp) / "run", study.input_paths(), dict(experiment="E014", blocks=[self.block],
                factors=study.FACTORS, checkpoints=study.CHECKPOINTS, config=asdict(self.cfg), workers=1, mode="technical_fixture"))
            source_path = output / f"source_{self.block:06d}.npz"
            np.savez_compressed(source_path, **self.source)
            for factor in study.FACTORS:
                np.savez_compressed(output / f"block_{self.block:06d}_factor_{factor}.npz", **self.raw[factor])
                study.dump(output / f"block_{self.block:06d}_factor_{factor}.json", dict(
                    source_file=str(source_path.relative_to(study.ROOT)), source_sha256=study.sha(source_path)))
            result = study.analyze(output, [self.block], True)
            self.assertEqual(result["status"], "TECHNICAL_ONLY")
            self.assertFalse(result["complete_sequence_confirmed"])
            study.finish(output, started, dict(experiment="E014"))
            receipt = audit.audit(output, workers=1)
            self.assertEqual(receipt["individual_observations"], 3200)
            self.assertEqual(receipt["independent_checkpoint_replays"], 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
