"""Physical damage, unchanged capture, information-flow and independent replay fixtures."""
from dataclasses import asdict, replace
import inspect
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from E021_damaged_renewal import model, run as study, audit
from E020_serial_capture import model as predecessor
import numpy as np


class DamagedRenewalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.cap_cpus()
        cls.cfg = replace(model.CFG, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cls.cycle = model.Cycle(read_steps=24, settling_steps=6, write_steps=8)
        source = model.acquisition.teach(study.BENCHMARK, cls.cfg)
        record = np.repeat(source["acquired"][1, :, None], cls.cfg.recipients, axis=1)
        cls.incoming = np.repeat(record[None], len(model.CONDITIONS), axis=0)

    def test_unchanged_activity_only_capture(self):
        self.assertEqual(tuple(inspect.signature(model.capture_from_activity).parameters), ("body", "cfg"))
        mask = model.base.damage_masks(study.BENCHMARK, "E021_renewal_g1", self.cfg)[:, :, 1]
        masks = np.repeat(mask[None], 4, axis=0)
        masks[1] = False
        body = study.rng("E021", "fixture", "writer").normal(0, .2, (4, 4, 2, 2, 16, 16))
        body *= (~masks)[:, :, :, None]
        before = body.copy()
        written = model.write_from_activity(body, masks, study.BENCHMARK, 1, self.cfg, self.cycle)
        with patch.object(model.base, "decode", side_effect=AssertionError("Writer decoded a record")), patch.object(model, "RULES", np.zeros(4)):
            changed = model.write_from_activity(body, masks, study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in written: np.testing.assert_array_equal(written[key], changed[key])
        np.testing.assert_array_equal(body, before)
        activity = np.tanh(3*before)
        expected = np.empty((4, 4, 2, 2, 16, 16))
        for y in range(16):
            for x in range(16):
                expected[..., 0, y, x] = (activity[..., y, x]*activity[..., y, (x+1)%16]).mean(axis=3)
                expected[..., 1, y, x] = (activity[..., y, x]*activity[..., (y+1)%16, x]).mean(axis=3)
        np.testing.assert_array_equal(model.base.decode(written["computed_packets"]), expected)
        old = predecessor.write_from_activity(body[:3], study.BENCHMARK, 1, self.cfg,
            predecessor.Cycle(read_steps=24, settling_steps=6, write_steps=8))
        np.testing.assert_array_equal(written["computed_packets"][:3], old["computed_packets"])
        later = model.write_from_activity(body, masks, study.BENCHMARK+1, 3, self.cfg, replace(self.cycle, write_steps=3))
        np.testing.assert_array_equal(written["computed_packets"], later["computed_packets"])
        self.assertFalse(np.array_equal(written["write_end"], later["write_end"]))

    def test_erasure_controls_labels_and_serial_reuse(self):
        before = self.incoming.copy()
        real_writer = model.write_from_activity
        with patch.object(model, "develop", wraps=model.develop) as develop:
            def guarded_writer(*args):
                self.assertFalse(develop.call_args.args[0].any(), "Incoming records not erased before capture")
                return real_writer(*args)
            with patch.object(model, "write_from_activity", side_effect=guarded_writer):
                raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        self.assertFalse(raw["erased_packets"].any())
        self.assertFalse(raw["read_packets"][2].any())
        self.assertFalse(raw["outgoing"][5].any())
        np.testing.assert_array_equal(raw["outgoing"][2], before[2])
        np.testing.assert_array_equal(self.incoming, before)
        with patch.object(model, "RULES", np.array([.3, .7, .2, -.8])), patch.object(model.base, "RULES", np.zeros(4)), patch.object(model, "score", side_effect=AssertionError("Scorer entered renewal")):
            changed = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
            changed_assay = model.assay(raw["outgoing"], study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in raw: np.testing.assert_array_equal(raw[key], changed[key])
        alternative = self.incoming.copy()
        alternative[4] = model.base.encode(np.ones((4, 2, 2, 16, 16)))
        disrupted = model.replace_record(alternative, study.BENCHMARK, 1, self.cfg, self.cycle)
        np.testing.assert_array_equal(raw["outgoing"][4], disrupted["outgoing"][4])
        assay = model.assay(raw["outgoing"], study.BENCHMARK, 1, self.cfg, self.cycle)
        for key in assay: np.testing.assert_array_equal(assay[key], changed_assay[key])
        for arm in (5, 6):
            np.testing.assert_array_equal(assay["late_ports"][:, :, :, :, 0, :, arm], assay["late_ports"][:, :, :, :, 1, :, arm])
        for generation in (2, 3):
            successor = model.replace_record(raw["outgoing"], study.BENCHMARK, generation, self.cfg, self.cycle)
            np.testing.assert_array_equal(successor["incoming"], raw["outgoing"])
            effective = model.base.encode(model.base.decode(raw["outgoing"][list(model.ACTIVE)])*model.surviving_edges(successor["body_masks"]))
            effective[2] = 0
            np.testing.assert_array_equal(successor["read_packets"], effective)
            np.testing.assert_array_equal(successor["outgoing"][2], before[2])
            masked = model.base.encode(model.base.decode(raw["outgoing"][3])*model.surviving_edges(successor["renewal_mask"]))
            np.testing.assert_array_equal(successor["outgoing"][3], masked)
            self.assertFalse(successor["outgoing"][5].any())
            self.assertFalse(np.array_equal(successor["birth"], raw["birth"]))
            self.assertFalse(np.array_equal(successor["renewal_mask"], raw["renewal_mask"]))
            raw = successor

    def test_dead_cells_edges_and_masked_copy(self):
        raw = model.replace_record(self.incoming, study.BENCHMARK, 1, self.cfg, self.cycle)
        masks = raw["body_masks"]
        np.testing.assert_array_equal(masks.sum(axis=(-2, -1)), np.broadcast_to(np.array([24, 0, 24, 24])[:, None, None], (4, 4, 2)))
        self.assertFalse((masks & model.PORTS.any(axis=0)).any())
        self.assertFalse((raw["developed_end"]*masks[:, :, :, None]).any())
        self.assertFalse((raw["write_states"]*masks[None, :, :, :, None]).any())
        edges = np.empty((4, 4, 2, 2, 16, 16), dtype=bool)
        for y in range(16):
            for x in range(16):
                edges[..., 0, y, x] = ~masks[..., y, x] & ~masks[..., y, (x+1)%16]
                edges[..., 1, y, x] = ~masks[..., y, x] & ~masks[..., (y+1)%16, x]
        self.assertFalse((model.base.decode(raw["read_packets"])*(~edges)).any())
        self.assertFalse((model.base.decode(raw["computed_packets"])*(~edges)).any())
        np.testing.assert_array_equal(raw["outgoing"][3], model.base.encode(model.base.decode(self.incoming[3])*edges[0]))
        np.testing.assert_array_equal(raw["read_packets"][1], self.incoming[1])
        self.assertTrue(np.array_equal(raw["renewal_mask"][0], raw["renewal_mask"][1]))
        self.assertTrue(np.array_equal(raw["renewal_mask"][2], raw["renewal_mask"][3]))

    def test_independent_end_to_end(self):
        parent = HERE/"analysis"
        parent.mkdir(exist_ok=True)
        attempt = 1
        while (parent/f"fixture_attempt{attempt}").exists(): attempt += 1
        started = time.monotonic()
        output = study.new_run(parent/f"fixture_attempt{attempt}", study.input_paths(), dict(experiment="E021",
            blocks=[study.BENCHMARK], gain=2., panels=model.PANELS, conditions=model.CONDITIONS,
            config=asdict(self.cfg), cycle=asdict(self.cycle), workers=1, mode="technical_fixture"))
        study.save_block(output, study.BENCHMARK, self.cfg, self.cycle)
        result = study.analyze(output, [study.BENCHMARK], True, self.cfg, self.cycle)
        self.assertEqual(result["status"], "TECHNICAL_ONLY")
        self.assertIsNone(result["primary"]["lower_bound_above_075"])
        self.assertIsNone(result["full_renewal_qualified"])
        self.assertEqual(len(result["boundary_gates"]), 12)
        study.finish(output, started, dict(experiment="E021", blocks_completed=1))
        receipt = audit.audit(output, workers=1)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["individual_observations"], 4368)


if __name__ == "__main__": unittest.main(verbosity=2)
