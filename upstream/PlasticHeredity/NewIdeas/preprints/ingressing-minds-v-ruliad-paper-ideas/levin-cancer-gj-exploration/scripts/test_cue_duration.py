import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import test_lineage_return as previous_tests
from analyze_cue_duration import panel_summary, reconstruct_writing
from run_cue_duration import branch_worker, effective_config, validate_config, writing_outcomes
from run_exposure_rehoming import cue_names
from run_lineage_return import clock_offset


class CueDurationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/cue_duration_v1.json").read_text())
        self.previous = previous_tests.LineageReturnTests()
        self.previous.setUp()

    def case(self, duration=10, origin="E", condition="pulse", fine=False):
        return next(c for c in self.config["cases"] if c["cue_duration"] == duration and c["origin_state"] == origin
                    and c["condition"] == condition and c.get("fine", False) == fine)

    def test_fixed_twenty_case_grid_and_four_fine_repeats(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 20)
        self.assertEqual(sum(c.get("fine", False) for c in self.config["cases"]), 4)
        self.assertEqual(sum(len(cue_names(c, 5)) for c in self.config["cases"]), 160)
        self.assertTrue(all(c["history"] == "learned" and c["cue_duration"] != 1000 for c in self.config["cases"]))

    def test_tuning_or_ambiguous_duration_rejected(self):
        for key, value in (("cue_durations", [10, 30, 100]), ("cue_horizon", 1000), ("source_round", 5), ("workers", 3)):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError):
                validate_config(cfg)
        for key, value in (("cue_duration", 1000), ("history", "blocked"), ("source_case", "m_to_e_pulse")):
            cfg = copy.deepcopy(self.config)
            cfg["cases"][0][key] = value
            with self.assertRaises(ValueError):
                validate_config(cfg)

    def test_only_per_case_cue_horizon_changes_and_original_config_is_untouched(self):
        original = copy.deepcopy(self.config)
        for duration in (10, 100):
            effective = effective_config(self.config, self.case(duration))
            self.assertEqual(effective["cue_horizon"], duration)
            self.assertEqual({k: v for k, v in effective.items() if k != "cue_horizon"}, original)
            self.assertEqual(clock_offset(effective), 43000 + duration)
        self.assertEqual(self.config, original)

    def fixture_outcomes(self, contact=("E", "E"), held="E", fraction=1.0, onward=True):
        hold = dict(recipient_label=held, late_label_fractions={"E": fraction if held == "E" else 0., "M": fraction if held == "M" else 0., "X": 0.})
        exposure = dict(carriers=[dict(contact_label=c, holds=[copy.deepcopy(hold), copy.deepcopy(hold)]) for c in contact])
        rounds = [dict(round_success=onward), dict(round_success=onward)]
        return exposure, rounds

    def outcomes(self, exposure, rounds):
        actual = writing_outcomes(exposure, rounds, self.case(), self.config)
        audited = reconstruct_writing(exposure, rounds, "E", .95)
        self.assertEqual(actual, audited)
        return actual

    def test_prompt_writing_matches_previous_strict_endpoint(self):
        outcome = self.outcomes(*self.fixture_outcomes())
        self.assertTrue(outcome["durable_rewrite"])
        self.assertTrue(outcome["prompt_rewrite"])
        self.assertFalse(outcome["delayed_rewrite"])

    def test_delayed_writing_does_not_require_contact_end_label(self):
        for contacts in (("M", "M"), ("M", "E"), ("X", "E")):
            outcome = self.outcomes(*self.fixture_outcomes(contact=contacts))
            self.assertTrue(outcome["durable_rewrite"])
            self.assertTrue(outcome["delayed_rewrite"])
            self.assertFalse(outcome["contact_acquired"])
            self.assertFalse(outcome["prompt_rewrite"])

    def test_transient_switch_late_instability_or_failed_relay_is_not_durable(self):
        for args in (dict(held="M"), dict(fraction=.94), dict(onward=False)):
            outcome = self.outcomes(*self.fixture_outcomes(**args))
            self.assertFalse(outcome["durable_rewrite"])
            self.assertFalse(outcome["prompt_rewrite"])
            self.assertFalse(outcome["delayed_rewrite"])

    def test_one_failed_cell_or_round_prevents_durable_rewrite(self):
        exposure, rounds = self.fixture_outcomes()
        exposure["carriers"][1]["holds"][1]["recipient_label"] = "M"
        self.assertFalse(self.outcomes(exposure, rounds)["durable_rewrite"])
        exposure, rounds = self.fixture_outcomes(contact=("M", "M"))
        rounds[1]["round_success"] = False
        self.assertFalse(self.outcomes(exposure, rounds)["durable_rewrite"])

    def test_incomplete_exposure_record_is_rejected(self):
        exposure, rounds = self.fixture_outcomes()
        exposure["carriers"] = exposure["carriers"][:1]
        with self.assertRaises(ValueError):
            writing_outcomes(exposure, rounds, self.case(), self.config)
        self.assertFalse(reconstruct_writing(exposure, rounds, "E", .95)["durable_rewrite"])

    def test_duration_reaches_exposure_and_clock_with_failed_branches_continuing(self):
        for duration, condition in ((10, "blocked"), (100, "alone")):
            with tempfile.TemporaryDirectory() as temp:
                _, inputs, _, source, _, ids = self.previous.fixture(temp, condition)
                case = self.case(duration, condition=condition)
                called = []

                def fake_exposure(folder, config, case, packet, got_ids, prepared, indices):
                    self.assertEqual(config["cue_horizon"], duration)
                    self.assertEqual(config["cue_holds"], [10000, 10000])
                    np.testing.assert_array_equal(packet, source)
                    self.assertEqual(got_ids, ids)
                    exposure, _ = self.fixture_outcomes(contact=("M", "M"), held="M", onward=False)
                    exposure.update(cue_ids=cue_names(case, 5), retained_switch=False)
                    return packet.copy(), exposure

                def fake_round(folder, config, case, packet, ids, seen, fresh, later, indices, number):
                    called.append(number)
                    self.assertEqual(case["history"], "learned")
                    self.assertEqual(config["contact_horizon"], 1000)
                    self.assertTrue(len(seen) >= 18)
                    new_ids = [f"{case['id']}:round_{number:02}:child_{i}" for i in (1, 2)]
                    self.assertFalse(set(new_ids) & seen)
                    return packet.copy(), new_ids, dict(round=number, round_success=False, nominal_round_start=(number - 1) * 22000, nominal_round_end=number * 22000)

                folder = Path(temp) / "branch"
                folder.mkdir()
                with patch("run_cue_duration.exposure_worker", fake_exposure), patch("run_cue_duration.round_worker", fake_round), redirect_stdout(io.StringIO()):
                    self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
                result = json.loads((folder / "result.json").read_text())
                self.assertEqual(called, [4, 5])
                self.assertEqual(result["effective_cue_horizon"], duration)
                self.assertEqual(result["distinct_fresh_targets"], 4)
                self.assertEqual(result["nominal_schedule"], [dict(round=4, start=109000 + duration, end=131000 + duration), dict(round=5, start=131000 + duration, end=153000 + duration)])
                self.assertFalse(result["durable_rewrite"])

    def test_panel_keeps_reuse_explicit_and_does_not_invent_exact_threshold(self):
        rows = []
        for origin in ("E", "M"):
            for duration in (10, 100, 1000):
                for condition, fine in (("pulse", False), ("blocked", False), ("same", False), ("alone", False), ("pulse", True)):
                    success = condition == "pulse" and duration >= 100
                    exposure, rounds = self.fixture_outcomes(onward=success)
                    outcome = reconstruct_writing(exposure, rounds, "E", .95)
                    rows.append(dict(case=dict(origin_state=origin, condition=condition, fine=fine), cue_duration=duration,
                        historical_reuse=duration == 1000, exposure=exposure, rounds=[dict(r, outgoing_labels="EE") for r in rounds], outcomes=outcome))
        panel = panel_summary(rows, [10, 100, 1000])
        for p in panel.values():
            self.assertEqual(p["smallest_tested_success"], 100)
            self.assertEqual(p["largest_tested_failure_below_it"], 10)
            self.assertFalse(p["exact_minimum_or_global_monotonicity_established"])
            self.assertEqual([r["historical_reuse"] for r in p["durations"]], [False, False, True])


if __name__ == "__main__":
    unittest.main()
