import copy
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from analyze_history_crossover import audit_exposure, audit_histories, panel_summary
from analyze_pulse_spacing import expected_timeline
from history_delivery import inward_edge_rates, native_inward_rates, record_delivery, sample_window, summarize_exchange, transport_parameters
from memory_metrics import classify
from run_history_crossover import branch_worker, exposure_worker, history_file, historical_case, load_histories, validate_config
from run_memory_probe import Experiment, array_hash, write_json
import test_lineage_return as previous_tests


class HistoryCrossoverTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.config = json.loads((self.root / "configs/history_crossover_v1.json").read_text())
        self.previous = previous_tests.LineageReturnTests()
        self.previous.setUp()
        self.indices, self.refs = self.previous.indices, self.previous.refs

    def case(self, rh=1, ch=1, condition="pulse", origin="E", fine=False):
        return next(c for c in self.config["cases"] if (c["receiver_history"], c["cue_history"], c["condition"], c["origin_state"], c["fine"]) == (rh, ch, condition, origin, fine))

    def test_fixed_factorial_grid_resources_and_fine_scope(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 24)
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]), 8)
        self.assertEqual(sum(c["condition"] == "blocked" for c in self.config["cases"]), 8)
        self.assertTrue(all(c["history"] == "learned" for c in self.config["cases"]))
        self.assertEqual(len(self.config["cases"]) * (6 + 22), 672)
        self.assertEqual(len(self.config["cases"]) * 4, 96)

    def test_changed_checkpoint_age_grid_transport_or_source_rejected(self):
        for key, value in (("history_phase", "pulse_04"), ("history_age", 70), ("history_pulses", 5),
                ("probe_horizon", 100), ("delivery_window", 10), ("input_run", "runs/other"), ("workers", 3), ("cue_horizon", 10)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError): validate_config(config)
        for key, value in (("receiver_history", 0), ("cue_history", 0), ("history", "blocked"), ("fine", True), ("source_case", "m_to_e_pulse")):
            config = copy.deepcopy(self.config)
            config["cases"][0][key] = value
            with self.assertRaises(ValueError): validate_config(config)

    def inputs_fixture(self, temp, case):
        _, inputs, _, original, _, ids = self.previous.fixture(temp, origin=case["origin_state"])
        plan = expected_timeline(dict(mode="train", gap=10))
        for h in (0, 1):
            name = historical_case(case["origin_state"], h)
            cues = [f"{name}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, 6)]
            carriers, audits = [], []
            for i in (1, 2):
                target = self.refs[:, {"E": 0, "M": 1}[case["state"]], None]
                state = np.concatenate((original[:, i - 1:i], np.repeat(target, 5, axis=1)), axis=1)
                # Distinguish entire cell states and both receiver slots, not
                # merely the three regulators. Snail alone remains fixed.
                state[0] += 3 * h + i + np.arange(6) / 10
                state[8:] += h / 100
                if h:
                    state[5:8, :1] = .4 * target[5:8] + .6 * state[5:8, :1]
                labels = "".join(classify(state, self.indices))
                np.savez_compressed(inputs / history_file(case["origin_state"], h, i), initial=state,
                    times=np.array([.1, 7.5, 10.1]), concentrations=np.repeat(state[None], 3, axis=0), raw_final=state, final=state)
                episodes = [dict(p, recipient_label=labels[0], cue_labels=labels[1:]) for p in plan]
                carriers.append(dict(episodes=episodes))
                for p in plan + [dict(name="hold_1", horizon=10000), dict(name="hold_2", horizon=10000)]:
                    audits.append(dict(phase=f"carrier_{i}_" + p["name"], requested_horizon=p["horizon"], samples=3, all_labels=labels))
            write_json(inputs / history_file(case["origin_state"], h), dict(incoming_ids=ids, outgoing_ids=ids,
                cue_ids=cues, cue_refresh_count=0, new_reference_edits=0, timeline=plan, carriers=carriers, audits=audits))
        return inputs

    def parameters(self, active):
        d = np.zeros((17, 5))
        if active: d[:3] = 1e-18
        return dict(indices=self.indices, valences=[1., 1., -1., -1.] + [0.] * 13, diffusion=d.tolist(),
            miRNA_kd=2e-15 if active else 0, miRNA_valence=-1, F=96485, cell_vol=5.235987755982989e-16,
            cell_sa=3.1415926535897934e-10, cm=.05, kb=1.3806e-23, T=310, q=1.602e-19, GJ_len=1e-7)

    def fake_experiment(self, fine_seen):
        indices = self.indices

        class FakeExperiment:
            def __init__(self, folder, config, fine=False):
                self.folder, self.indices, self.audits = folder, indices, []
                fine_seen.append(fine)

            def build(self, count, state, active=False):
                self.state, self.active = state.copy(), active
                edges = np.array([(0, j) for j in range(1, count)], dtype=[("from", int), ("to", int)])
                self.sim = SimpleNamespace(cc_cells=self.state, GJ_connects=edges,
                    GJ_diffusion=np.full((17, count - 1), 2e-15 if active else 0.))
                return dict(cells=count, edges=count - 1, active=active, miRNA_kd=2e-15 if active else 0,
                    state_hash_before_derived_refresh=array_hash(state), environment_hash="standard")

            def phase(self, name, horizon):
                initial = self.state.copy()
                if self.active: self.state[5:8, 0] = self.state[5:8, 1]
                self.state[0] += (np.arange(self.state.shape[1]) + 1) * horizon / 1000
                final = self.state.copy()
                times = np.array([.05, .75 * horizon, horizon + .01])
                shots = np.repeat(final[None], 3, axis=0)
                labels = classify(final, indices)
                record = dict(phase=name, requested_horizon=horizon, samples=3, all_labels="".join(labels),
                    recipient_label=str(labels[0]), late_label_fractions={l: float(labels[0] == l) for l in ("E", "M", "X")},
                    miRNA_kd=2e-15 if self.active else 0, graph_edges=final.shape[1] - 1)
                np.savez_compressed(self.folder / (name + ".npz"), initial=initial, times=times, concentrations=shots, raw_final=final, final=final)
                self.audits.append(record)
                return final, record

        return FakeExperiment

    def fake_delivery(self, exp, phase, path, horizon):
        with patch("history_delivery.transport_parameters", lambda e: self.parameters(e.active)), patch(
                "history_delivery.native_inward_rates", lambda e, s: inward_edge_rates(s, self.parameters(e.active))):
            return record_delivery(exp, phase, path, horizon)

    def fixture(self, temp, case):
        inputs = self.inputs_fixture(temp, case)
        _, groups, ids, cue_ids, _, _ = load_histories(inputs, self.config, case, self.indices)
        folder = Path(temp) / "crossover"
        fine_seen = []
        with patch("run_history_crossover.Experiment", self.fake_experiment(fine_seen)), patch("run_history_crossover.record_delivery", self.fake_delivery):
            packet, result = exposure_worker(folder, self.config, case, groups, ids, cue_ids, self.indices)
        self.assertEqual(fine_seen, [case["fine"]])
        return folder, inputs, case, packet, result

    def audit(self, fixture):
        folder, inputs, case, *_ = fixture
        return audit_exposure(folder, inputs, self.config, case, self.indices)

    def mutate(self, path, action):
        with np.load(path) as f: values = {k: f[k].copy() for k in f.files}
        action(values)
        np.savez_compressed(path, **values)

    def test_all_four_crossovers_in_both_directions_keep_complete_cells_and_provenance(self):
        for origin in ("E", "M"):
            for rh in (0, 1):
                for ch in (0, 1):
                    with tempfile.TemporaryDirectory() as temp:
                        case = self.case(rh, ch, origin=origin)
                        inputs = self.inputs_fixture(temp, case)
                        loaded = load_histories(inputs, self.config, case, self.indices)
                        audited = audit_histories(inputs, self.config, case, self.indices)
                        self.assertTrue(all(audited[-1].values()))
                        self.assertEqual(loaded[-1], audited[-2])
                        self.assertEqual(len(loaded[4]), 42)
                        for i, group in enumerate(loaded[1], 1):
                            with np.load(inputs / history_file(origin, rh, i)) as f: np.testing.assert_array_equal(group[:, :1], f["final"][:, :1])
                            with np.load(inputs / history_file(origin, ch, i)) as f: np.testing.assert_array_equal(group[:, 1:], f["final"][:, 1:])

    def test_wrong_history_checkpoint_and_cue_identity_rejected(self):
        for change in ("age", "identity"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                inputs = self.inputs_fixture(temp, case)
                path = inputs / history_file("E", 1)
                meta = json.loads(path.read_text())
                if change == "age": meta["timeline"][7]["end"] = 90
                else: meta["cue_ids"][0] = meta["incoming_ids"][0]
                write_json(path, meta)
                with self.assertRaises(ValueError): load_histories(inputs, self.config, case, self.indices)

    def test_all_24_synthetic_exposures_and_independent_audits(self):
        for case in self.config["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, case)
                audit = self.audit(fixture)
                self.assertTrue(all(audit[5].values()), [k for k, v in audit[5].items() if not v])
                np.testing.assert_array_equal(audit[0], fixture[3])
                self.assertEqual(len(audit[6]), 6)

    def test_audit_detects_regulator_only_swap_and_wrong_receiver_history(self):
        for change in ("ionic", "receiver"):
            with tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, self.case(1, 0))
                self.mutate(fixture[0] / "endpoints.npz", lambda v: v["carrier_1_initial"].__setitem__((0 if change == "ionic" else 5, 0), 999.))
                self.assertFalse(self.audit(fixture)[5]["carrier_1/whole_cell_crossover_exact"])

    def test_audit_detects_cues_forwarded_and_probe_reset(self):
        for change in ("cue", "reset"):
            with tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, self.case())
                if change == "cue":
                    self.mutate(fixture[0] / "endpoints.npz", lambda v: v["continuing_packet"].__setitem__((slice(None), slice(0, 1)), v["carrier_1_contact"][:, 1:2]))
                    key = "carrier_1/actual_receiver_not_cue_forwarded"
                else:
                    self.mutate(fixture[0] / "carrier_1_probe.npz", lambda v: v["initial"].__setitem__((0, 0), 999.))
                    key = "carrier_1/probe/primary_continuity_all_cells"
                self.assertFalse(self.audit(fixture)[5][key])

    def test_audit_detects_nonzero_blocked_transport_and_changed_delivery_trace(self):
        for change in ("parameter", "trace"):
            with tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, self.case(condition="blocked"))
                if change == "parameter":
                    path = fixture[0] / "result.json"
                    r = json.loads(path.read_text())
                    r["deliveries"][0]["parameters"]["miRNA_kd"] = 2e-15
                    write_json(path, r)
                    key = "carrier_1/delivery/active_or_all_off_transport"
                else:
                    self.mutate(fixture[0] / "carrier_1_delivery.npz", lambda v: v["inward_edge_rates"].__setitem__((0, 5, 0), .1))
                    key = "carrier_1/delivery/blocked_transport_exactly_zero"
                self.assertFalse(self.audit(fixture)[5][key])

    def test_audit_detects_probe_duration_identity_and_starting_label_errors(self):
        for change in ("duration", "identity", "label"):
            with tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, self.case())
                path = fixture[0] / "result.json"
                r = json.loads(path.read_text())
                if change == "duration":
                    r["audits"][0]["requested_horizon"] = 100
                    key = "carrier_1/probe/phase_metadata"
                elif change == "identity":
                    r["cue_ids"][0] = r["incoming_ids"][0]
                    key = "selected_history_ids_preserved"
                else:
                    r["target_pair_at_start"] = not r["target_pair_at_start"]
                    key = "starting_and_strict_target_endpoints_recomputed"
                write_json(path, r)
                self.assertFalse(self.audit(fixture)[5][key])

    def test_native_flux_formula_and_readonly_restoration_without_integrating(self):
        env = dict(MPLBACKEND="Agg", MPLCONFIGDIR=str(self.root / ".cache/matplotlib"), XDG_CACHE_HOME=str(self.root / ".cache"))
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, env), redirect_stdout(io.StringIO()):
            exp = Experiment(Path(temp), self.config)
            for active in (True, False):
                exp.build(6, active=active)
                p = transport_parameters(exp)
                expected_parameters = self.parameters(active)
                expected_parameters["indices"] = dict(exp.indices)
                self.assertEqual(p, expected_parameters)
                self.assertTrue(all(exp.indices[k] == v for k, v in self.indices.items()))
                live, old_d, old_z = exp.sim.cc_cells.copy(), exp.sim.GJ_diffusion.copy(), exp.sim.z_array.copy()
                identity = exp.sim.cc_cells
                for polarity in (-1, 1):
                    state = live.copy()
                    state[0] += polarity * np.arange(6) * .001
                    state[5] = [70, 85, 20, 2, 40, 4]
                    state[6] = [20, 30, 40, 50, 60, 70]
                    expected, vm = inward_edge_rates(state, p)
                    actual, native_vm = native_inward_rates(exp, state)
                    np.testing.assert_allclose(expected, actual, rtol=1e-10, atol=1e-20)
                    np.testing.assert_allclose(vm, native_vm, rtol=1e-12, atol=1e-15)
                    self.assertIs(exp.sim.cc_cells, identity)
                    np.testing.assert_array_equal(exp.sim.cc_cells, live)
                    np.testing.assert_array_equal(exp.sim.GJ_diffusion, old_d)
                    np.testing.assert_array_equal(exp.sim.z_array, old_z)
                    if not active: self.assertFalse(np.any(actual))

    def test_common_window_uses_samples_not_overshot_live_endpoint(self):
        state = np.ones((17, 6))
        phase = dict(initial=state, times=np.array([2., 8., 11.]), concentrations=np.array([2 * state, 8 * state, 11 * state]), final=999 * state)
        t, s = sample_window(phase)
        np.testing.assert_array_equal(t, [0., 2., 8., 9.])
        np.testing.assert_array_equal(s[-1], 9 * state)
        phase["times"] = np.array([2., 4., 8.])
        with self.assertRaises(ValueError): sample_window(phase)

    def test_signed_gross_exchange_and_quadrature_are_distinct(self):
        t = np.array([0., 3., 6., 9.])
        rates = np.zeros((4, 17, 5))
        rates[:, 5, 0] = 2
        rates[:, 5, 1] = -1
        r = summarize_exchange(t, rates)
        self.assertEqual(r["signed_net"][5], 9.)
        self.assertEqual(r["gross_inward"][5], 18.)
        self.assertEqual(r["gross_outward"][5], 9.)
        self.assertEqual(r["quadrature_max_abs_difference"], 0.)

    def test_negative_probe_branch_continues_actual_pair_and_clock(self):
        with tempfile.TemporaryDirectory() as temp:
            case = self.case(0, 0, "blocked")
            inputs = self.inputs_fixture(temp, case)
            folder = Path(temp) / "branch"
            folder.mkdir()
            calls = []

            def fake_round(folder, config, case, packet, ids, seen, fresh, later, indices, n):
                calls.append(n)
                self.assertEqual(case["history"], "learned")
                self.assertEqual(len(seen), 42 + 2 * (n - 4))
                new_ids = [f"{case['id']}:round_{n:02}:child_{i}" for i in (1, 2)]
                return packet.copy(), new_ids, dict(round=n, round_success=False)

            with patch("run_history_crossover.Experiment", self.fake_experiment([])), patch("run_history_crossover.record_delivery", self.fake_delivery), patch("run_history_crossover.round_worker", fake_round), redirect_stdout(io.StringIO()):
                self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
            r = json.loads((folder / "result.json").read_text())
            self.assertEqual(calls, [4, 5])
            self.assertFalse(r["durable_rewrite"])
            self.assertEqual(r["distinct_fresh_targets"], 4)
            self.assertEqual(r["nominal_schedule"], [dict(round=4, start=109090, end=131090), dict(round=5, start=131090, end=153090)])

    def test_panel_does_not_credit_final_contact_when_blocked_control_succeeds(self):
        branches = []
        for c in self.config["cases"]:
            branches.append(dict(case=c, outcomes=dict(durable_rewrite=bool(c["receiver_history"])),
                exposure=dict(carriers=[dict(initial_label=c["old_state"])] * 2, deliveries=[])))
        for rows in panel_summary(branches).values():
            for r in rows[:2]:
                self.assertTrue(r["target_persists_without_final_contact"])
                self.assertFalse(r["active_succeeds_blocked_fails"])
                self.assertTrue(r["fine_outcomes_agree"])


if __name__ == "__main__":
    unittest.main()
