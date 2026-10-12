"""Information-flow, capture timing and short independent replay fixtures."""
from dataclasses import asdict, replace
import inspect
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E019_capture_timing import model, run as study, audit
import numpy as np


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cls.cycle = model.Cycle(read_steps=24, settling_steps=6, write_steps=8)
        source = model.acquisition.teach(study.BENCHMARK, cls.cfg)
        cls.incoming = np.repeat(source["acquired"][1, :, None], cls.cfg.recipients, axis=1)

    def test_current_activity_only_writer_and_timing(self):
        self.assertEqual(tuple(inspect.signature(model.write_from_activity).parameters), ("body", "block", "cfg", "cycle"))
        body = study.rng("E019", "fixture", "writer").normal(0, .2, (2, 4, 2, 2, 16, 16))
        original = body.copy()
        cycle = replace(self.cycle, write_steps=1)
        written = model.write_from_activity(body, study.BENCHMARK, self.cfg, cycle)
        with patch.object(model.base, "decode", side_effect=AssertionError("Writer decoded a record")), patch.object(model, "RULES", np.zeros(4)):
            changed = model.write_from_activity(body, study.BENCHMARK, self.cfg, cycle)
        for key in written: np.testing.assert_array_equal(written[key], changed[key])
        np.testing.assert_array_equal(body, original)
        expected = []
        for state in (body, written["write_end"]):
            activity = np.tanh(3*state)
            weights = np.empty((2, 4, 2, 2, 16, 16))
            for y in range(16):
                for x in range(16):
                    weights[..., 0, y, x] = (activity[..., y, x]*activity[..., y, (x+1)%16]).mean(axis=3)
                    weights[..., 1, y, x] = (activity[..., y, x]*activity[..., (y+1)%16, x]).mean(axis=3)
            expected.append(weights)
        packets = model.base.decode(written["computed_packets"])
        np.testing.assert_array_equal(packets[0], expected[0])
        np.testing.assert_array_equal(packets[1], expected[1])
        np.testing.assert_array_equal(packets[2], expected[1])
        self.assertFalse(np.array_equal(packets[0], packets[1]))
        longer = model.write_from_activity(body, study.BENCHMARK+1, self.cfg, self.cycle)
        np.testing.assert_array_equal(written["computed_packets"][0], longer["computed_packets"][0])

    def test_erasure_copy_controls_and_label_exclusion(self):
        before = self.incoming.copy()
        real_writer = model.write_from_activity
        with patch.object(model, "develop", wraps=model.develop) as develop:
            def guarded_writer(*args):
                self.assertFalse(develop.call_args.args[0].any(), "Incoming records not erased before writing")
                return real_writer(*args)
            with patch.object(model, "write_from_activity", side_effect=guarded_writer):
                raw = model.replace_record(self.incoming, study.BENCHMARK, self.cfg, self.cycle)
        self.assertFalse(raw["erased_packets"].any())
        self.assertFalse(raw["read_packets"][1].any())
        self.assertFalse(raw["outgoing"][7].any())
        np.testing.assert_array_equal(raw["outgoing"][3], before)
        np.testing.assert_array_equal(self.incoming, before)
        for k in range(3):
            np.testing.assert_array_equal(raw["outgoing"][k], raw["computed_packets"][k, 0])
            np.testing.assert_array_equal(raw["outgoing"][k+4], raw["computed_packets"][k, 1])
        with patch.object(model, "RULES", np.array([.3, .7, .2, -.8])), patch.object(model.base, "RULES", np.zeros(4)):
            changed = model.replace_record(self.incoming, study.BENCHMARK, self.cfg, self.cycle)
            changed_assay = model.assay(raw["outgoing"], study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in raw: np.testing.assert_array_equal(raw[key], changed[key])
        alternative = model.base.encode(np.ones((4, 2, 2, 16, 16)))
        disrupted = model.replace_record(alternative, study.BENCHMARK, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw["outgoing"][4:7], disrupted["outgoing"][4:7])
        assay = model.assay(raw["outgoing"], study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in assay: np.testing.assert_array_equal(assay[key], changed_assay[key])
        for arm in (5, 6):
            np.testing.assert_array_equal(assay["late_ports"][:, :, :, :, 0, :, arm], assay["late_ports"][:, :, :, :, 1, :, arm])

    def test_independent_end_to_end(self):
        parent = HERE/"analysis"
        parent.mkdir(exist_ok=True)
        attempt = 1
        while (parent/f"fixture_attempt{attempt}").exists(): attempt += 1
        started = time.monotonic()
        output = study.new_run(parent/f"fixture_attempt{attempt}", study.input_paths(), dict(experiment="E019",
            blocks=[study.BENCHMARK], gain=2., panels=model.PANELS, conditions=model.CONDITIONS,
            config=asdict(self.cfg), cycle=asdict(self.cycle), workers=1, mode="technical_fixture"))
        study.save_block(output, study.BENCHMARK, self.cfg, self.cycle)
        result = study.analyze(output, [study.BENCHMARK], True, self.cfg, self.cycle)
        self.assertEqual(result["status"], "TECHNICAL_ONLY")
        self.assertIsNone(result["primary"]["lower_bound_positive"])
        self.assertIsNone(result["full_early_capture_qualified"])
        study.finish(output, started, dict(experiment="E019", blocks_completed=1))
        receipt = audit.audit(output, workers=1)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["individual_observations"], 3024)


if __name__ == "__main__": unittest.main(verbosity=2)
