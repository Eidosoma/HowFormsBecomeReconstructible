"""End-to-end reporting and fresh-formation checks on disposable inputs."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from run import HERE, analyze, compact, tissue


class ConfirmationChecks(unittest.TestCase):
    def test_disposable_complete_reporting_and_single_size_gate(self):
        cfg = replace(tissue.CFG, formation=12, observation_window=8, capture=7, read=5, write=7, challenge_time=2)
        source = tissue.formation(900007, "heterogeneous", cfg)
        acquired, end, first = tissue.capture(source["founder_state"], 900007, cfg)
        source.update(acquired=acquired, capture_end=end, capture_first=first)
        with tempfile.TemporaryDirectory(prefix="test_", dir=HERE) as directory:
            output = Path(directory)
            np.savez_compressed(output/"source_900007.npz", **source)
            for factor in (1, 4):
                raw = compact.simulate(source, 900007, factor, cfg)
                np.savez_compressed(output/f"block_900007_factor_{factor}.npz", **raw)
            analyze(output, [900007], True)
            summary = json.loads((output/"summary.json").read_text())
            self.assertEqual(summary["status"], "TECHNICAL_ONLY")
            self.assertEqual(set(summary["groups"]), {"1", "4"})
            self.assertEqual(len((output/"observations.csv").read_text().splitlines()), 641)
            self.assertFalse(summary["complete_sequence_confirmed"])
            for g in summary["groups"].values():
                self.assertEqual(g["gates"]["terminal_specificity"], g["contrasts"]["terminal"]["rewrite_minus_foreign"]["ci95"][0] > 0)


if __name__ == "__main__": unittest.main(verbosity=2)
