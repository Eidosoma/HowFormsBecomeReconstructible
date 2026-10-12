import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np

from analyze_exposure_rehoming import audit_exposure
from memory_metrics import REGULATORS, classify
from run_exposure_rehoming import cue_group, cue_names, exposure_worker, validate_config
from run_memory_probe import array_hash, write_json


class ExposureRehomingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/exposure_rehoming_v1.json").read_text())
        self.indices = dict(zip(REGULATORS, (5, 6, 7)), snail=4)
        self.refs = np.ones((17, 2))
        self.refs[4] = 72
        self.refs[5:8] = [[84, 9], [6, 69], [.4, 63]]
        self.ids = ["incumbent:1", "incumbent:2"]

    def case(self, condition="pulse", old="E", fine=False):
        return next(c for c in self.config["cases"] if c["condition"] == condition and c["old_state"] == old and c.get("fine", False) == fine)

    def test_fixed_grid_and_always_active_relay(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 10)
        self.assertTrue(all(c["history"] == "learned" for c in self.config["cases"]))

    def test_blocking_onward_relay_is_rejected(self):
        cfg = copy.deepcopy(self.config)
        next(c for c in cfg["cases"] if c["condition"] == "blocked")["history"] = "blocked"
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_tuning_grid_polarity_or_bounds_rejected(self):
        for key, value in (("cue_donors", 6), ("cue_horizon", 2000), ("cue_holds", [1000, 1000]),
                           ("workers", 3), ("inherited_wait", 0), ("cases", self.config["cases"][:-1])):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError):
                validate_config(cfg)
        cfg = copy.deepcopy(self.config)
        cfg["cases"][0]["state"] = "E"
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_cues_do_not_reset_incumbent_or_modify_inputs(self):
        for old, column in (("E", 0), ("M", 1)):
            carrier = self.refs[:, column, None].copy()
            carrier[0] += 9
            before = carrier.copy()
            for condition in ("pulse", "blocked", "same", "alone"):
                group, active = cue_group(carrier, self.refs, self.case(condition, old), 5)
                np.testing.assert_array_equal(group[:, :1], before)
                self.assertFalse(np.shares_memory(group, carrier))
                self.assertFalse(np.shares_memory(group, self.refs))
                self.assertEqual(active, condition in ("pulse", "same"))
                if condition != "alone":
                    cue_col = column if condition == "same" else 1 - column
                    np.testing.assert_array_equal(group[:, 1:], self.refs[:, cue_col, None].repeat(5, axis=1))
                else:
                    self.assertEqual(group.shape, (17, 1))
                np.testing.assert_array_equal(carrier, before)

    def test_blocked_and_fine_share_exact_active_cue_assembly(self):
        a, _ = cue_group(self.refs[:, :1], self.refs, self.case(), 5)
        for case in (self.case("blocked"), self.case(fine=True)):
            b, _ = cue_group(self.refs[:, :1], self.refs, case, 5)
            np.testing.assert_array_equal(a, b)

    def test_invalid_cue_inputs_rejected(self):
        for carrier in (self.refs, self.refs[:, :1] * np.nan, -self.refs[:, :1]):
            with self.assertRaises(ValueError):
                cue_group(carrier, self.refs, self.case(), 5)
        with self.assertRaises(ValueError):
            cue_group(self.refs[:, :1], self.refs, self.case(), 4)

    def test_distinct_cue_names_and_fixed_total_instances(self):
        names = [n for c in self.config["cases"] for n in cue_names(c, 5)]
        self.assertEqual(len(names), 80)
        self.assertEqual(len(set(names)), 80)
        self.assertFalse(set(names) & set(self.ids))

    def make_fixture(self, temp, condition="pulse", old="E", fine=False):
        case = self.case(condition, old, fine)
        inputs, folder = Path(temp) / "inputs", Path(temp) / "exposure"
        inputs.mkdir()
        source = self.refs[:, {"E": 0, "M": 1}[old], None].repeat(2, axis=1)
        source[0] = [7, 13]  # Deliberately distinguish incumbents and cues.
        stem = old.lower() + "_sham"
        np.savez_compressed(inputs / (stem + ".npz"), after_2=source)
        np.savez_compressed(inputs / ("historical_" + stem + ".npz"), continuing_start=source)
        write_json(inputs / (stem + ".json"), {"outgoing_ids": self.ids})
        write_json(inputs / (old.lower() + "_prefix.json"), {"incoming_ids": ["founder:1", "founder:2"], "outgoing_ids": self.ids})
        write_json(inputs / ("historical_" + stem + ".json"), {"case": {"state": old, "intervention": "sham"}, "all_rounds_transmitted": True})
        indices = self.indices
        fine_seen = []

        class FakeExperiment:
            def __init__(self, folder, config, fine=False):
                self.folder, self.indices, self.audits = folder, indices, []
                fine_seen.append(fine)

            def build(self, count, state, active=False):
                self.state, self.active = state.copy(), active
                edges = np.array([(0, j) for j in range(1, count)], dtype=[("from", int), ("to", int)])
                self.sim = SimpleNamespace(GJ_connects=edges)
                return dict(cells=count, edges=count - 1, active=active, miRNA_kd=2e-15 if active else 0,
                    state_hash_before_derived_refresh=array_hash(state), environment_hash="standard")

            def phase(self, name, horizon):
                initial = self.state.copy()
                if self.active:
                    self.state[5:8, 0] = self.state[5:8, 1]
                self.state[0] += 1
                final = self.state.copy()
                times = np.array([0, .75 * horizon, horizon])
                shots = np.repeat(final[None], 3, axis=0)
                labels = classify(final, indices)
                record = dict(phase=name, requested_horizon=horizon, samples=3, all_labels="".join(labels),
                    recipient_label=str(labels[0]), late_label_fractions={l: float(labels[0] == l) for l in ("E", "M", "X")},
                    miRNA_kd=2e-15 if self.active else 0, graph_edges=final.shape[1] - 1)
                np.savez_compressed(self.folder / (name + ".npz"), initial=initial, times=times, concentrations=shots, raw_final=final, final=final)
                self.audits.append(record)
                return final, record

        with patch("run_exposure_rehoming.Experiment", FakeExperiment):
            packet, record = exposure_worker(folder, self.config, case, source, self.ids, self.refs, self.indices)
        self.assertEqual(fine_seen, [fine])
        return folder, inputs, case, source, packet, record

    def audit_fixture(self, fixture):
        folder, inputs, case, *_ = fixture
        return audit_exposure(folder, inputs, self.config, case, self.refs, self.indices)

    def test_exposure_and_independent_audit_both_directions_all_conditions(self):
        for old in ("E", "M"):
            for condition in ("pulse", "blocked", "same", "alone"):
                with self.subTest(old=old, condition=condition), tempfile.TemporaryDirectory() as temp:
                    fixture = self.make_fixture(temp, condition, old)
                    packet, ids, seen, row, checks, audits, _ = self.audit_fixture(fixture)
                    self.assertTrue(all(checks.values()), {k: v for k, v in checks.items() if not v})
                    self.assertEqual(row["retained_switch"], condition == "pulse")
                    self.assertEqual(ids, self.ids)
                    self.assertEqual(len(seen), 4 if condition == "alone" else 14)
                    self.assertEqual(len(audits), 6)
                    np.testing.assert_array_equal(packet, fixture[4])
                    np.testing.assert_array_equal(packet[0], fixture[3][0] + 3)

    def test_fine_flag_applies_to_exposure(self):
        with tempfile.TemporaryDirectory() as temp:
            self.make_fixture(temp, fine=True)

    def test_audit_rejects_cue_substituted_for_carrier(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.make_fixture(temp)
            folder = fixture[0]
            with np.load(folder / "endpoints.npz") as f:
                saved = {k: f[k].copy() for k in f.files}
            saved["continuing_packet"][:, :1] = saved["carrier_1_contact"][:, 1:2]
            np.savez_compressed(folder / "endpoints.npz", **saved)
            checks = self.audit_fixture(fixture)[4]
            self.assertFalse(checks["carrier_1/actual_incumbent_enters_forward_pair"])

    def test_audit_rejects_direct_carrier_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.make_fixture(temp)
            folder = fixture[0]
            with np.load(folder / "endpoints.npz") as f:
                saved = {k: f[k].copy() for k in f.files}
            saved["carrier_1_initial"][5:8, 0] = self.refs[5:8, 1]
            np.savez_compressed(folder / "endpoints.npz", **saved)
            checks = self.audit_fixture(fixture)[4]
            self.assertFalse(checks["carrier_1/full_initial_assembly"])
            self.assertFalse(checks["carrier_1/actual_carrier_is_target_zero"])

    def test_audit_rejects_misreported_success_cue_id_or_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.make_fixture(temp, "blocked")
            path = fixture[0] / "result.json"
            record = json.loads(path.read_text())
            record["retained_switch"] = True
            record["cue_ids"][0] = self.ids[0]
            record["setups"][0]["active"] = True
            write_json(path, record)
            checks = self.audit_fixture(fixture)[4]
            for key in ("pair_switch_recomputed", "cue_ids_distinct_and_fixed", "carrier_1/cue_transport_correct"):
                self.assertFalse(checks[key])


if __name__ == "__main__":
    unittest.main()
