import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from analyze_pulse_spacing import audit_exposure, expected_timeline, panel_summary
from memory_metrics import classify
from run_memory_probe import array_hash, write_json
from run_pulse_spacing import branch_worker, exposure_worker, timeline, validate_config
from run_exposure_rehoming import cue_names
import test_lineage_return as previous_tests


class PulseSpacingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/pulse_spacing_v1.json").read_text())
        self.previous = previous_tests.LineageReturnTests()
        self.previous.setUp()
        self.indices, self.refs = self.previous.indices, self.previous.refs

    def case(self, gap=10, mode="train", condition="pulse", origin="E", fine=False):
        return next(c for c in self.config["cases"] if (c["gap"], c["mode"], c["condition"], c["origin_state"], c["fine"]) == (gap, mode, condition, origin, fine))

    def test_fixed_grid_and_resource_counts(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 32)
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]), 6)
        self.assertEqual(sum(len(cue_names(c, 5)) for c in self.config["cases"]), 280)
        self.assertEqual(sum(2 * (len(timeline(self.config, c)) + 2) + 22 for c in self.config["cases"]), 1704)
        self.assertTrue(all(c["history"] == "learned" for c in self.config["cases"]))

    def test_changed_pulses_gaps_grid_history_or_bounds_rejected(self):
        for key, value in (("pulse_count", 9), ("pulse_horizon", 20), ("gaps", [0, 10, 100]), ("cue_horizon", 100), ("source_round", 5), ("workers", 3)):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError): validate_config(cfg)
        for key, value in (("gap", 100), ("mode", "single"), ("history", "blocked"), ("source_case", "m_to_e_pulse"), ("fine", True)):
            cfg = copy.deepcopy(self.config)
            cfg["cases"][0][key] = value
            with self.assertRaises(ValueError): validate_config(cfg)

    def test_independent_timelines_equal_and_have_no_zero_or_trailing_gap(self):
        for c in self.config["cases"]:
            plan = timeline(self.config, c)
            self.assertEqual(plan, expected_timeline(c))
            self.assertEqual(plan[-1]["kind"], "contact")
            self.assertTrue(all(p["horizon"] > 0 for p in plan))
            self.assertEqual(plan[0]["start"], 0)
            self.assertTrue(all(a["end"] == b["start"] for a, b in zip(plan, plan[1:])))
            self.assertEqual(plan[-1]["end"], 100 + 9 * c["gap"])

    def test_ten_contacts_nine_gaps_and_matched_comparison_ages(self):
        for gap in (10, 1000):
            train = timeline(self.config, self.case(gap))
            continuous = timeline(self.config, self.case(gap, "continuous"))
            single = timeline(self.config, self.case(gap, "single"))
            self.assertEqual(sum(p["kind"] == "contact" for p in train), 10)
            self.assertEqual(sum(p["kind"] == "gap" for p in train), 9)
            self.assertEqual(sum(p["horizon"] for p in train if p["kind"] == "contact"), 100)
            self.assertEqual(continuous[0]["horizon"], 9 * gap)
            self.assertEqual(single[0]["horizon"], 90 + 9 * gap)
            self.assertEqual([v[-1]["end"] for v in (train, continuous, single)], [100 + 9 * gap] * 3)
            self.assertEqual([v[-1]["horizon"] for v in (continuous, single)], [100, 10])

    def fake_experiment(self, fine_seen):
        indices = self.indices

        class FakeExperiment:
            def __init__(self, folder, config, fine=False):
                self.folder, self.indices, self.audits = folder, indices, []
                fine_seen.append(fine)

            def build(self, count, state, active=False):
                self.state, self.active = state.copy(), active
                edges = np.array([(0, j) for j in range(1, count)], dtype=[("from", int), ("to", int)])
                self.sim = SimpleNamespace(GJ_connects=edges, GJ_diffusion=np.full((17, count - 1), 2e-15 if active else 0.))
                return dict(cells=count, edges=count - 1, active=active, miRNA_kd=2e-15 if active else 0,
                    state_hash_before_derived_refresh=array_hash(state), environment_hash="standard")

            def phase(self, name, horizon):
                initial = self.state.copy()
                if self.active: self.state[5:8, 0] = self.state[5:8, 1]
                self.state[0] += (np.arange(self.state.shape[1]) + 1) * horizon / 1000
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

        return FakeExperiment

    def fixture(self, temp, case):
        _, inputs, _, source, _, ids = self.previous.fixture(temp, case["condition"], case["origin_state"], case["fine"])
        folder = Path(temp) / "spacing"
        fine_seen = []
        with patch("run_pulse_spacing.Experiment", self.fake_experiment(fine_seen)):
            packet, record = exposure_worker(folder, self.config, case, source, ids, self.refs, self.indices)
        self.assertEqual(fine_seen, [case["fine"]])
        return folder, inputs, case, source, packet, record

    def audit(self, fixture):
        folder, inputs, c, *_ = fixture
        return audit_exposure(folder, inputs, self.config, c, self.refs, self.indices)

    def test_exposure_and_independent_audit_all_schedules_controls_and_directions(self):
        for origin in ("E", "M"):
            for gap, mode, condition in ((0, "train", "pulse"), (10, "train", "pulse"), (1000, "train", "pulse"),
                    (10, "train", "blocked"), (1000, "train", "same"), (1000, "train", "alone"), (10, "continuous", "pulse"), (1000, "single", "pulse")):
                with self.subTest(origin=origin, gap=gap, mode=mode, condition=condition), tempfile.TemporaryDirectory() as temp:
                    fixture = self.fixture(temp, self.case(gap, mode, condition, origin))
                    packet, ids, seen, row, checks, audits, _, trace = self.audit(fixture)
                    self.assertTrue(all(checks.values()), [k for k, v in checks.items() if not v])
                    self.assertEqual(len(seen), 18 if condition == "alone" else 28)
                    self.assertEqual(len(audits), 2 * (len(expected_timeline(fixture[2])) + 2))
                    np.testing.assert_array_equal(packet, fixture[4])
                    np.testing.assert_allclose(packet[0], fixture[3][0] + (100 + 9 * gap + 20000) / 1000)
                    self.assertEqual(row["retained_switch"], condition == "pulse")

    def test_fine_flag_applies_to_all_new_exposure_phases(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertTrue(all(self.audit(self.fixture(temp, self.case(fine=True)))[4].values()))

    def mutate_arrays(self, path, change):
        with np.load(path) as f: values = {k: f[k].copy() for k in f.files}
        change(values)
        np.savez_compressed(path, **values)

    def test_audit_detects_donor_reset_between_pulses(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.fixture(temp, self.case())
            self.mutate_arrays(fixture[0] / "carrier_1_pulse_02.npz", lambda v: v["initial"].__setitem__((0, 1), self.refs[0, 0]))
            self.assertFalse(self.audit(fixture)[4]["carrier_1_pulse_02/primary_continuity_all_cells"])

    def test_audit_detects_gap_transport_and_wrong_gap_duration(self):
        for change in ("transport", "duration"):
            with tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, self.case())
                path = fixture[0] / "result.json"
                r = json.loads(path.read_text())
                if change == "transport": r["setups"][1]["all_gj_transport_zero"] = False
                else: r["audits"][1]["requested_horizon"] = 1000
                write_json(path, r)
                key = "all_transport_off_in_gaps_and_waits" if change == "transport" else "phase_metadata"
                self.assertFalse(self.audit(fixture)[4]["carrier_1_gap_01/" + key])

    def test_audit_detects_cue_forwarded_instead_of_incumbent(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.fixture(temp, self.case())
            self.mutate_arrays(fixture[0] / "endpoints.npz", lambda v: v["continuing_packet"].__setitem__((slice(None), slice(0, 1)), v["carrier_1_contact"][:, 1:2]))
            self.assertFalse(self.audit(fixture)[4]["carrier_1/actual_incumbent_forwarded"])

    def test_audit_detects_reused_identity_and_false_refresh_count(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.fixture(temp, self.case())
            path = fixture[0] / "result.json"
            r = json.loads(path.read_text())
            r["cue_ids"][0] = r["incoming_ids"][0]
            r["cue_refresh_count"] = 1
            write_json(path, r)
            checks = self.audit(fixture)[4]
            self.assertFalse(checks["ten_cues_initialized_only_once"])
            self.assertFalse(checks["no_declared_refresh_or_reset"])

    def test_negative_branch_still_replaces_carriers_and_preserves_clock(self):
        with tempfile.TemporaryDirectory() as temp:
            c = self.case(1000, condition="blocked")
            _, inputs, _, source, _, ids = self.previous.fixture(temp, "blocked")
            folder = Path(temp) / "branch"
            folder.mkdir()
            calls = []

            def fake_round(folder, config, case, packet, ids, seen, fresh, later, indices, n):
                calls.append(n)
                self.assertEqual(case["history"], "learned")
                self.assertEqual(len(seen), 28 + 2 * (n - 4))
                new_ids = [f"{case['id']}:round_{n:02}:child_{i}" for i in (1, 2)]
                return packet.copy(), new_ids, dict(round=n, round_success=False)

            with patch("run_pulse_spacing.Experiment", self.fake_experiment([])), patch("run_pulse_spacing.round_worker", fake_round), redirect_stdout(io.StringIO()):
                self.assertEqual(branch_worker(folder, self.config, c, inputs), 0)
            r = json.loads((folder / "result.json").read_text())
            self.assertEqual(calls, [4, 5])
            self.assertFalse(r["durable_rewrite"])
            self.assertEqual(r["distinct_fresh_targets"], 4)
            self.assertEqual(r["cue_instances"], 10)
            self.assertEqual(r["nominal_schedule"], [dict(round=4, start=118100, end=140100), dict(round=5, start=140100, end=162100)])

    def test_panel_separates_accumulation_from_failure_of_aged_continuous_cue(self):
        branches = []
        for origin in ("E", "M"):
            for gap in (10, 1000):
                for mode, condition, fine in [("train", c, False) for c in ("pulse", "blocked", "same", "alone")] + [("continuous", "pulse", False), ("single", "pulse", False), ("train", "pulse", True)]:
                    success = gap == 10 and condition == "pulse" and mode != "single"
                    branches.append(dict(case=dict(origin_state=origin, gap=gap, mode=mode, condition=condition, fine=fine),
                        outcomes=dict(durable_rewrite=success), exposure=dict(first_joint_target_pulse=2 if success else None)))
        for rows in panel_summary(branches).values():
            self.assertTrue(rows[0]["train_succeeds_late_single_fails"])
            self.assertTrue(rows[0]["all_controls_negative"])
            self.assertTrue(rows[0]["fine_train_outcomes_agree"])
            self.assertTrue(rows[1]["both_train_and_matched_continuous_fail"])
            self.assertFalse(rows[1]["train_fails_matched_continuous_succeeds"])


if __name__ == "__main__":
    unittest.main()
