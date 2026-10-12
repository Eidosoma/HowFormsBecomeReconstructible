"""Boundary information-flow fixtures and a short independent full replay."""
from dataclasses import asdict, replace
import inspect
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E020_serial_capture import model, run as study, audit
from E019_capture_timing import model as predecessor
import numpy as np


class RenewalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cls.cycle = model.Cycle(read_steps=24, settling_steps=6, write_steps=8)
        cls.source = model.acquisition.teach(study.BENCHMARK, cls.cfg)
        record = np.repeat(cls.source["acquired"][1, :, None], cls.cfg.recipients, axis=1)
        cls.incoming = np.repeat(record[None], 4, axis=0)

    def test_current_activity_only_writer(self):
        self.assertEqual(tuple(inspect.signature(model.write_from_activity).parameters), ("body", "block", "generation", "cfg", "cycle"))
        body = study.rng("E020", "fixture", "writer").normal(0, .2, (3, 4, 2, 2, 16, 16))
        original = body.copy()
        cycle = replace(self.cycle, write_steps=1)
        written = model.write_from_activity(body, study.BENCHMARK, 1, self.cfg, cycle)
        with patch.object(model.base, "decode", side_effect=AssertionError("Writer decoded a record")), patch.object(model, "RULES", np.zeros(4)):
            changed = model.write_from_activity(body, study.BENCHMARK, 1, self.cfg, cycle)
        for key in written: np.testing.assert_array_equal(written[key], changed[key])
        np.testing.assert_array_equal(body, original)
        activity = np.tanh(3*original)
        expected = np.empty((3, 4, 2, 2, 16, 16))
        for y in range(16):
            for x in range(16):
                expected[..., 0, y, x] = (activity[..., y, x]*activity[..., y, (x+1)%16]).mean(axis=3)
                expected[..., 1, y, x] = (activity[..., y, x]*activity[..., (y+1)%16, x]).mean(axis=3)
        np.testing.assert_array_equal(model.base.decode(written["computed_packets"]), expected)
        old = predecessor.write_from_activity(body[:2], study.BENCHMARK, self.cfg,
            predecessor.Cycle(read_steps=24, settling_steps=6, write_steps=8))
        np.testing.assert_array_equal(written["computed_packets"][:2], old["computed_packets"][0])
        longer = model.write_from_activity(body, study.BENCHMARK+1, 3, self.cfg, self.cycle)
        np.testing.assert_array_equal(written["computed_packets"], longer["computed_packets"])
        self.assertFalse(np.array_equal(written["write_end"], longer["write_end"]))

    def test_erasure_copy_and_label_exclusion(self):
        before = self.incoming.copy()
        real_writer = model.write_from_activity
        with patch.object(model, "develop", wraps=model.develop) as develop:
            def guarded_writer(*args):
                self.assertFalse(develop.call_args.args[0].any(), "Incoming records not erased before writing")
                return real_writer(*args)
            with patch.object(model, "write_from_activity", side_effect=guarded_writer):
                raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        self.assertFalse(raw["erased_packets"].any())
        self.assertFalse(raw["read_packets"][1].any())
        self.assertFalse(raw["outgoing"][3].any())
        np.testing.assert_array_equal(raw["outgoing"][1], before[1])
        np.testing.assert_array_equal(self.incoming, before)
        with patch.object(model, "RULES", np.array([.3, .7, .2, -.8])), patch.object(model.base, "RULES", np.zeros(4)):
            changed = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
            assay_changed = model.assay(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in raw: np.testing.assert_array_equal(raw[key], changed[key])
        different = self.incoming.copy()
        different[2] = model.base.encode(np.ones((4, 2, 2, 16, 16)))
        disrupted = model.replace_record(different, study.BENCHMARK, 1, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw["outgoing"][2], disrupted["outgoing"][2])
        for g in (2, 3):
            successor = model.replace_record(raw["outgoing"], study.BENCHMARK, g, self.cfg, self.cycle)
            np.testing.assert_array_equal(successor["incoming"], raw["outgoing"])
            np.testing.assert_array_equal(successor["read_packets"][0], raw["outgoing"][0])
            np.testing.assert_array_equal(successor["outgoing"][1], before[1])
            self.assertFalse(successor["read_packets"][1].any())
            self.assertFalse(successor["outgoing"][3].any())
            self.assertFalse(np.array_equal(successor["birth"], raw["birth"]))
            raw = successor
        assay = model.assay(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in assay: np.testing.assert_array_equal(assay[key], assay_changed[key])
        for arm in (5, 6):
            np.testing.assert_array_equal(assay["late_ports"][:, :, :, :, 0, :, arm], assay["late_ports"][:, :, :, :, 1, :, arm])

    def test_independent_end_to_end(self):
        parent = HERE/"analysis"
        parent.mkdir(exist_ok=True)
        # Preserve each fixture attempt, including failures, without overwriting.
        attempt = 1
        while (parent/f"fixture_attempt{attempt}").exists(): attempt += 1
        started = time.monotonic()
        output = study.new_run(parent/f"fixture_attempt{attempt}", study.input_paths(), dict(experiment="E020",
            blocks=[study.BENCHMARK], gain=2., panels=model.PANELS, conditions=model.CONDITIONS,
            config=asdict(self.cfg), cycle=asdict(self.cycle), workers=1, mode="technical_fixture"))
        study.save_block(output, study.BENCHMARK, self.cfg, self.cycle)
        result = study.analyze(output, [study.BENCHMARK], True, self.cfg, self.cycle)
        self.assertEqual(result["status"], "TECHNICAL_ONLY")
        self.assertIsNone(result["primary"]["lower_bound_above_075"])
        self.assertIsNone(result["full_renewal_qualified"])
        study.finish(output, started, dict(experiment="E020", blocks_completed=1))
        receipt = audit.audit(output, workers=1)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["individual_observations"], 3024)


if __name__ == "__main__": unittest.main(verbosity=2)
