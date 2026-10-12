import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import test_exposure_rehoming as previous_tests
from analyze_lineage_return import audit_exposure, source_inputs
from run_exposure_rehoming import cue_names
from run_lineage_return import branch_worker, clock_offset, load_descendants, validate_config
from run_memory_probe import write_json


class LineageReturnTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/lineage_return_v1.json").read_text())
        self.previous = previous_tests.ExposureRehomingTests()
        self.previous.setUp()
        self.indices, self.refs = self.previous.indices, self.previous.refs

    def case(self, condition="pulse", origin="E", fine=False):
        return next(c for c in self.config["cases"] if c["condition"] == condition and c["origin_state"] == origin and c.get("fine", False) == fine)

    def test_fixed_grid_source_and_return_polarity(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 10)
        for c in self.config["cases"]:
            self.assertEqual(c["state"], c["origin_state"])
            self.assertNotEqual(c["state"], c["old_state"])
            self.assertEqual(c["history"], "learned")
            self.assertFalse(c["source_case"].endswith("fine"))

    def test_changed_round_grid_source_or_transport_rejected(self):
        for key, value in (("source_round", 2), ("continuing_rounds", [2, 3]), ("source_nominal_time", 0), ("cue_donors", 6), ("workers", 3)):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError):
                validate_config(cfg)
        for key, value in (("source_case", "m_to_e_pulse"), ("state", "M"), ("history", "blocked")):
            cfg = copy.deepcopy(self.config)
            cfg["cases"][0][key] = value
            with self.assertRaises(ValueError):
                validate_config(cfg)

    def test_clock_continues_from_source_not_zero(self):
        self.assertEqual(clock_offset(self.config), 44000)
        self.assertEqual(3 * 22000 + clock_offset(self.config), 89000 + 21000)
        self.assertEqual(5 * 22000 + clock_offset(self.config), 154000)

    def fixture(self, temp, condition="pulse", origin="E", fine=False):
        case = self.case(condition, origin, fine)
        folder, inputs, _, source, packet, exposure = self.previous.make_fixture(temp, condition, case["old_state"], fine)
        stem = case["source_case"]
        ancestors = ["original:founder:1", "original:founder:2"]
        first = ["first:child:1", "first:child:2"]
        second = [f"{stem}:round_02:child_{i}" for i in (1, 2)]
        ids = [f"{stem}:round_03:child_{i}" for i in (1, 2)]
        old_case = dict(id=stem, old_state=origin, state=case["old_state"], condition="pulse", history="learned")
        rounds = [dict(round=2, incoming_ids=first, outgoing_ids=second, round_success=True),
                  dict(round=3, incoming_ids=second, outgoing_ids=ids, round_success=True)]
        top = dict(case=old_case, retained_switch=True, new_state_transmitted=True, exposure_rehomed=True,
            final_ids=ids, rounds=rounds, nominal_schedule=[dict(round=3, end=89000)],
            exposure=dict(incoming_ids=first, outgoing_ids=first, cue_ids=cue_names(old_case, 5)))
        write_json(inputs / (origin.lower() + "_prefix.json"), dict(incoming_ids=ancestors, outgoing_ids=first))
        write_json(inputs / (stem + ".json"), top)
        write_json(inputs / (stem + "_round_03.json"), rounds[-1])
        np.savez_compressed(inputs / (stem + ".npz"), final_packet=source)
        np.savez_compressed(inputs / (stem + "_round_03.npz"), outgoing_packet=source)
        np.savez_compressed(inputs / "references.npz", prepared=self.refs, later=self.refs)
        write_json(inputs / "reference.json", dict(ion_indices=self.indices))
        exposure["incoming_ids"] = ids
        exposure["outgoing_ids"] = ids
        exposure["cue_ids"] = cue_names(case, 5)
        for c, name in zip(exposure["carriers"], ids):
            c["id"] = name
        write_json(folder / "result.json", exposure)
        return folder, inputs, case, source, packet, ids

    def test_source_load_preserves_full_checkpoint_and_all_18_ids(self):
        for origin in ("E", "M"):
            with tempfile.TemporaryDirectory() as temp:
                _, inputs, case, original, _, ids = self.fixture(temp, origin=origin)
                source, got_ids, seen, record = load_descendants(inputs, self.config, case, self.indices)
                np.testing.assert_array_equal(source, original)
                self.assertFalse(np.shares_memory(source, original))
                self.assertEqual(got_ids, ids)
                self.assertEqual(len(seen), 18)
                self.assertEqual(record["excluded_ids"], sorted(seen))
                _, aid, aseen, arecord, checks = source_inputs(inputs, self.config, case, self.indices)
                self.assertTrue(all(checks.values()), checks)
                self.assertEqual((aid, aseen, arecord), (got_ids, seen, record))

    def test_all_conditions_and_fine_use_same_baseline_descendants(self):
        for origin in ("E", "M"):
            sources = [c["source_case"] for c in self.config["cases"] if c["origin_state"] == origin]
            self.assertEqual(len(set(sources)), 1)

    def test_independent_exposure_audit_both_directions_and_controls(self):
        for origin in ("E", "M"):
            for condition in ("pulse", "blocked", "same", "alone"):
                with self.subTest(origin=origin, condition=condition), tempfile.TemporaryDirectory() as temp:
                    folder, inputs, case, _, expected, ids = self.fixture(temp, condition, origin)
                    packet, got_ids, seen, row, checks, audits, _ = audit_exposure(folder, inputs, self.config, case, self.refs, self.indices)
                    self.assertTrue(all(checks.values()), {k: v for k, v in checks.items() if not v})
                    self.assertEqual(got_ids, ids)
                    self.assertEqual(len(seen), 18 if condition == "alone" else 28)
                    self.assertEqual(row["retained_switch"], condition == "pulse")
                    self.assertEqual(len(audits), 6)
                    np.testing.assert_array_equal(packet, expected)

    def test_nonfinal_checkpoint_substitution_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            _, inputs, case, source, *_ = self.fixture(temp)
            changed = source.copy()
            changed[0, 0] += 1
            np.savez_compressed(inputs / (case["source_case"] + "_round_03.npz"), outgoing_packet=changed)
            with self.assertRaises(ValueError):
                load_descendants(inputs, self.config, case, self.indices)
            checks = source_inputs(inputs, self.config, case, self.indices)[-1]
            self.assertFalse(checks["actual_final_pair_not_prior_incumbents"])

    def test_failed_or_fine_history_rejected(self):
        for change in ("failed", "fine"):
            with tempfile.TemporaryDirectory() as temp:
                _, inputs, case, *_ = self.fixture(temp)
                path = inputs / (case["source_case"] + ".json")
                top = json.loads(path.read_text())
                if change == "failed":
                    top["exposure_rehomed"] = False
                else:
                    top["case"]["fine"] = True
                write_json(path, top)
                with self.assertRaises(ValueError):
                    load_descendants(inputs, self.config, case, self.indices)
                self.assertFalse(all(source_inputs(inputs, self.config, case, self.indices)[-1].values()))

    def test_historical_cue_reuse_and_clock_errors_rejected(self):
        for change in ("cue", "clock"):
            with tempfile.TemporaryDirectory() as temp:
                _, inputs, case, _, _, ids = self.fixture(temp)
                path = inputs / (case["source_case"] + ".json")
                top = json.loads(path.read_text())
                if change == "cue":
                    top["exposure"]["cue_ids"][0] = ids[0]
                else:
                    top["nominal_schedule"][-1]["end"] = 67000
                write_json(path, top)
                with self.assertRaises(ValueError):
                    load_descendants(inputs, self.config, case, self.indices)
                self.assertFalse(all(source_inputs(inputs, self.config, case, self.indices)[-1].values()))

    def test_audit_rejects_reset_at_new_exposure_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            folder, inputs, case, *_ = self.fixture(temp)
            path = folder / "endpoints.npz"
            with np.load(path) as saved:
                values = {k: saved[k].copy() for k in saved.files}
            values["carrier_1_initial"][5, 0] += 2
            np.savez_compressed(path, **values)
            checks = audit_exposure(folder, inputs, self.config, case, self.refs, self.indices)[4]
            self.assertFalse(checks["carrier_1/full_initial_assembly"])
            self.assertFalse(checks["carrier_1/actual_carrier_is_target_zero"])

    def test_branch_runs_rounds_four_five_and_excludes_historical_ids(self):
        for condition in ("blocked", "alone"):
            with tempfile.TemporaryDirectory() as temp:
                _, inputs, case, source, _, original_ids = self.fixture(temp, condition)
                seen_before = load_descendants(inputs, self.config, case, self.indices)[2]
                called = []

                def fake_exposure(folder, config, case, packet, ids, prepared, indices):
                    np.testing.assert_array_equal(packet, source)
                    self.assertEqual(ids, original_ids)
                    return packet.copy(), dict(cue_ids=cue_names(case, 5), retained_switch=False)

                def fake_round(folder, config, case, packet, ids, seen, fresh, later, indices, number):
                    called.append(number)
                    self.assertTrue(seen_before <= seen)
                    self.assertEqual(case["history"], "learned")
                    new_ids = [f"{case['id']}:round_{number:02}:child_{i}" for i in (1, 2)]
                    self.assertFalse(set(new_ids) & seen)
                    return packet.copy(), new_ids, dict(round=number, round_success=False,
                        nominal_round_start=(number - 1) * 22000, nominal_round_end=number * 22000)

                folder = Path(temp) / "branch"
                folder.mkdir()
                with patch("run_lineage_return.exposure_worker", fake_exposure), patch("run_lineage_return.round_worker", fake_round), redirect_stdout(io.StringIO()):
                    self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
                result = json.loads((folder / "result.json").read_text())
                self.assertEqual(called, [4, 5])
                self.assertEqual(result["distinct_fresh_targets"], 4)
                self.assertEqual(result["nominal_schedule"], [dict(round=4, start=110000, end=132000), dict(round=5, start=132000, end=154000)])
                self.assertFalse(result["renewed_return"])


if __name__ == "__main__":
    unittest.main()
