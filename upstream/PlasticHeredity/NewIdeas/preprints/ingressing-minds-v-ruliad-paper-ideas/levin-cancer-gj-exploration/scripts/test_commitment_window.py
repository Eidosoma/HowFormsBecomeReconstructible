import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import test_history_crossover as fixtures
from analyze_commitment_window import audit_branch, audit_checkpoint, audit_exposure, historical_benchmarks, panel_summary
from analyze_cue_duration import reconstruct_writing
from analyze_group_transfer import arrays
from analyze_pulse_spacing import expected_timeline
from memory_metrics import classify
from run_commitment_window import branch_worker, checkpoint_file, exposure_worker, history_name, load_checkpoint, validate_config
from run_cue_duration import writing_outcomes
from run_memory_probe import write_json


class CommitmentWindowTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.config = json.loads((self.root / "configs/commitment_window_v1.json").read_text())
        self.fixtures = fixtures.HistoryCrossoverTests()
        self.fixtures.setUp()
        self.indices, self.refs = self.fixtures.indices, self.fixtures.refs

    def case(self, n=4, origin="E", condition="pulse", fine=False):
        return next(c for c in self.config["cases"] if (c["stop_count"], c["origin_state"], c["condition"], c["fine"]) == (n, origin, condition, fine))

    def inputs_fixture(self, temp, case):
        _, inputs, _, original, _, old_ids = self.fixtures.previous.fixture(temp, origin=case["origin_state"])
        name, n = history_name(case), case["stop_count"]
        plan = expected_timeline(dict(mode="train", gap=10))
        cues = [f"{name}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, 6)]
        carriers, audits, setups = [], [], []
        target = self.refs[:, {"E": 0, "M": 1}[case["state"]], None]
        for i in (1, 2):
            state = np.concatenate((original[:, i - 1:i], np.repeat(target, 5, axis=1)), axis=1)
            state[0] += i + n / 10 + (.01 if case["fine"] else 0)
            state[8:] += i / 100
            if case["condition"] == "pulse" and n >= 4:
                state[5:8, :1] = target[5:8]
            labels = "".join(classify(state, self.indices))
            # Last saved shot intentionally differs from the live endpoint.
            shots = np.repeat(state[None], 3, axis=0)
            shots[-1, 0] += 7
            np.savez_compressed(inputs / checkpoint_file(case, i), initial=state, raw_final=state, final=state,
                times=np.array([.1, 7.5, 10.1]), concentrations=shots)
            carriers.append(dict(episodes=[dict(p, recipient_label=labels[0], cue_labels=labels[1:]) for p in plan]))
            for p in plan + [dict(name="hold_1", horizon=10000), dict(name="hold_2", horizon=10000)]:
                active = case["condition"] == "pulse" and p["name"].startswith("pulse")
                audits.append(dict(phase=f"carrier_{i}_" + p["name"], requested_horizon=p["horizon"],
                    samples=3, all_labels=labels, recipient_label=labels[0], miRNA_kd=2e-15 if active else 0))
            for p in plan + [dict(name="hold_1")]:
                active = case["condition"] == "pulse" and p["name"].startswith("pulse")
                setups.append(dict(active=active, miRNA_kd=2e-15 if active else 0, all_gj_transport_zero=not active))
        write_json(inputs / checkpoint_file(case), dict(incoming_ids=old_ids, outgoing_ids=old_ids,
            cue_ids=cues, cue_refresh_count=0, new_reference_edits=0, timeline=plan, carriers=carriers, audits=audits, setups=setups))
        write_json(inputs / "spacing_summary.json", dict(config=dict(cases=[dict(id=name, fine=case["fine"],
            condition=case["condition"], mode="train", gap=10)])))
        return inputs

    def fixture(self, temp, case):
        inputs = self.inputs_fixture(temp, case)
        _, groups, ids, cues, _, _ = load_checkpoint(inputs, self.config, case, self.indices)
        before = [g.copy() for g in groups]
        folder, fine_seen = Path(temp) / "commitment", []
        with patch("run_commitment_window.Experiment", self.fixtures.fake_experiment(fine_seen)):
            packet, result = exposure_worker(folder, self.config, case, groups, ids, cues, self.indices)
        self.assertEqual(fine_seen, [case["fine"]])
        for a, b in zip(groups, before): np.testing.assert_array_equal(a, b)
        return folder, inputs, case, packet, result

    def audit(self, fixture):
        folder, inputs, case, *_ = fixture
        return audit_exposure(folder, inputs, self.config, case, self.indices)

    def test_fixed_grid_resources_and_refinement(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 30)
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]), 10)
        self.assertEqual(sum(c["condition"] == "blocked" for c in self.config["cases"]), 10)
        self.assertEqual(30 * 26, 780)
        self.assertTrue(all(c["history"] == "learned" for c in self.config["cases"]))

    def test_changed_grid_stop_gap_source_clock_and_transport_rejected(self):
        for key, value in (("stop_counts", [2, 3, 4, 5, 8]), ("history_gap", 0), ("pulse_horizon", 100),
                ("input_run", "runs/other"), ("benchmark_run", "runs/other"), ("source_nominal_time", 0),
                ("workers", 3), ("cue_horizon", 10), ("cue_holds", [1000, 1000])):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError): validate_config(cfg)
        for key, value in (("stop_count", 5), ("fine", True), ("history", "blocked"), ("source_case", "m_to_e_pulse")):
            cfg = copy.deepcopy(self.config)
            cfg["cases"][0][key] = value
            with self.assertRaises(ValueError): validate_config(cfg)

    def test_all_30_synthetic_sources_holds_and_independent_audits(self):
        for case in self.config["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, case)
                loaded = load_checkpoint(fixture[1], self.config, case, self.indices)
                audited = self.audit(fixture)
                self.assertTrue(all(audited[5].values()), [k for k, v in audited[5].items() if not v])
                self.assertEqual(audited[3], loaded[-1])
                self.assertEqual(len(loaded[4]), 30)
                self.assertEqual(audited[1], loaded[2])
                np.testing.assert_array_equal(audited[0], fixture[3])
                self.assertEqual(len(audited[6]), 4)
                self.assertEqual(audited[3]["checkpoint"]["history_age"], 20 * case["stop_count"] - 10)
                self.assertEqual(audited[3]["checkpoint"]["source_settings"], "fine" if case["fine"] else "baseline")

    def test_live_endpoint_not_last_saved_sample_is_used(self):
        with tempfile.TemporaryDirectory() as temp:
            case = self.case()
            inputs = self.inputs_fixture(temp, case)
            loaded = load_checkpoint(inputs, self.config, case, self.indices)
            p = arrays(inputs / checkpoint_file(case, 1))
            np.testing.assert_array_equal(loaded[1][0], p["final"])
            self.assertFalse(np.array_equal(loaded[1][0], p["concentrations"][-1]))

    def test_wrong_checkpoint_metadata_refinement_and_identity_rejected(self):
        for change in ("phase", "age", "ids", "refresh", "fine"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case(fine=True)
                inputs = self.inputs_fixture(temp, case)
                path = inputs / ("spacing_summary.json" if change == "fine" else checkpoint_file(case))
                m = json.loads(path.read_text())
                if change == "phase": m["audits"][6]["phase"] = "carrier_1_gap_04"
                elif change == "age": m["timeline"][6]["end"] += 10
                elif change == "ids": m["cue_ids"][0] = m["incoming_ids"][0]
                elif change == "refresh": m["cue_refresh_count"] = 1
                else: m["config"]["cases"][0]["fine"] = False
                write_json(path, m)
                with self.assertRaises(ValueError): load_checkpoint(inputs, self.config, case, self.indices)

    def test_audit_detects_historical_transport_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.fixture(temp, self.case(condition="blocked"))
            path = fixture[1] / checkpoint_file(fixture[2])
            meta = json.loads(path.read_text())
            meta["setups"][6]["active"] = True
            write_json(path, meta)
            checks = self.audit(fixture)[5]
            self.assertFalse(checks[checkpoint_file(fixture[2], 1) + "/selected_history_transport"])

    def test_audit_detects_receiver_reset_in_hold_entry(self):
        for ion in (0, 5):
            with tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, self.case())
                self.fixtures.mutate(fixture[0] / "carrier_1_hold_1.npz", lambda v: v["initial"].__setitem__((ion, 0), 999.))
                self.assertFalse(self.audit(fixture)[5]["carrier_1/hold_1/primary_continuity_all_cells"])

    def test_audit_detects_cue_forwarding_or_incomplete_checkpoint_copy(self):
        for change in ("cue", "copy"):
            with tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, self.case())
                if change == "cue":
                    self.fixtures.mutate(fixture[0] / "endpoints.npz",
                        lambda v: v["continuing_packet"].__setitem__((slice(None), slice(0, 1)), v["carrier_1_checkpoint"][:, 1:2]))
                    key = "carrier_1/actual_receiver_not_cue_forwarded"
                else:
                    self.fixtures.mutate(fixture[0] / "endpoints.npz", lambda v: v["carrier_1_checkpoint"].__setitem__((8, 0), 999.))
                    key = "carrier_1/full_checkpoint_saved"
                self.assertFalse(self.audit(fixture)[5][key])

    def test_audit_detects_reset_between_holds_and_shortened_hold(self):
        for change in ("reset", "duration"):
            with tempfile.TemporaryDirectory() as temp:
                fixture = self.fixture(temp, self.case())
                if change == "reset":
                    self.fixtures.mutate(fixture[0] / "carrier_1_hold_2.npz", lambda v: v["initial"].__setitem__((5, 0), 999.))
                    key = "carrier_1/hold_2/primary_continuity_all_cells"
                else:
                    path = fixture[0] / "result.json"
                    meta = json.loads(path.read_text())
                    meta["audits"][0]["requested_horizon"] = 100
                    write_json(path, meta)
                    key = "carrier_1/hold_1/phase_metadata"
                self.assertFalse(self.audit(fixture)[5][key])

    def test_delayed_and_transient_writing_are_not_conflated(self):
        case = self.case()
        for removal, held, onward, delayed, durable in (("M", "E", True, True, True),
                ("E", "M", False, False, False), ("E", "E", True, False, True)):
            h = dict(recipient_label=held, late_label_fractions={v: float(v == held) for v in ("E", "M", "X")})
            e = dict(carriers=[dict(contact_label=removal, holds=[h, h])] * 2)
            rounds = [dict(round_success=onward)] * 2
            result = writing_outcomes(e, rounds, case, self.config)
            self.assertEqual(result, reconstruct_writing(e, rounds, "E", .95))
            self.assertEqual(result["delayed_rewrite"], delayed)
            self.assertEqual(result["durable_rewrite"], durable)

    def branch_fixture(self, temp, case):
        inputs = self.inputs_fixture(temp, case)
        folder = Path(temp) / "branch"
        folder.mkdir()
        calls = []

        def fake_round(stage, config, c, packet, ids, seen, fresh, later, indices, n):
            calls.append(n)
            self.assertEqual(c["history"], "learned")
            self.assertEqual(len(seen), 30 + 2 * (n - 4))
            new_ids = [f"{c['id']}:round_{n:02}:child_{i}" for i in (1, 2)]
            # Negative assay still passes its actual packet onward.
            row = dict(round=n, round_success=False, children=[dict(id=i) for i in new_ids],
                outgoing_labels="".join(classify(packet, indices)))
            write_json(stage / "result.json", row)
            np.savez_compressed(stage / "endpoints.npz", outgoing_packet=packet)
            return packet.copy(), new_ids, row

        with patch("run_commitment_window.Experiment", self.fixtures.fake_experiment([])), patch(
                "run_commitment_window.round_worker", fake_round), redirect_stdout(io.StringIO()):
            self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
        self.assertEqual(calls, [4, 5])
        return folder, inputs

    def fake_audit_round(self, stage, *args):
        return arrays(stage / "endpoints.npz"), json.loads((stage / "result.json").read_text()), dict(mock_only=True), [dict(samples=3)] * 11

    def test_negative_branch_still_runs_both_rounds_with_all_thirty_exclusions(self):
        for n in (2, 3, 4, 6, 8):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case(n=n, condition="blocked")
                folder, inputs = self.branch_fixture(temp, case)
                r = json.loads((folder / "result.json").read_text())
                self.assertFalse(r["durable_rewrite"])
                self.assertEqual(r["distinct_fresh_targets"], 4)
                self.assertEqual(r["nominal_schedule"], [dict(round=4, start=109000 + 20 * n - 10, end=131000 + 20 * n - 10),
                    dict(round=5, start=131000 + 20 * n - 10, end=153000 + 20 * n - 10)])
                with patch("analyze_commitment_window.audit_round", self.fake_audit_round):
                    b, _, checks, pa = audit_branch(folder, inputs, self.config, case, self.indices, dict(prepared=self.refs, later=self.refs))
                self.assertTrue(all(all(v.values()) for v in checks.values()), checks)
                self.assertFalse(b["outcomes"]["durable_rewrite"])
                self.assertEqual(len(pa), 26)

    def test_branch_audit_detects_clock_outcome_identity_and_packet_mutations(self):
        for change in ("clock", "outcome", "id", "packet"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case(condition="blocked")
                folder, inputs = self.branch_fixture(temp, case)
                path = folder / "result.json"
                r = json.loads(path.read_text())
                if change == "clock":
                    r["nominal_schedule"][0]["start"] += 10
                    key = "nominal_clock_correct"
                elif change == "outcome":
                    r["durable_rewrite"] = True
                    key = "six_outcomes_recomputed"
                elif change == "id":
                    r["final_ids"][0] = r["source"]["checkpoint"]["excluded_ids"][0]
                    key = "final_ids_correct_and_disjoint"
                else:
                    self.fixtures.mutate(folder / "endpoints.npz", lambda v: v["continuing_start"].__setitem__((5, 0), 999.))
                    key = "actual_held_pair_seeds_relay"
                write_json(path, r)
                with patch("analyze_commitment_window.audit_round", self.fake_audit_round):
                    checks = audit_branch(folder, inputs, self.config, case, self.indices, dict(prepared=self.refs, later=self.refs))[2]
                self.assertFalse(checks[case["id"]][key])

    def synthetic_branches(self):
        rows = []
        for c in self.config["cases"]:
            success = c["stop_count"] in (3, 6, 8) and c["condition"] == "pulse"
            h = dict(recipient_label=c["state"], late_label_fractions={c["state"]: 1.})
            rows.append(dict(case=c, historical_reuse=False, outcomes=dict(durable_rewrite=success),
                exposure=dict(carriers=[dict(contact_label=c["state"], holds=[h, h])] * 2),
                rounds=[dict(outgoing_labels=c["state"] * 2)] * 2))
        return rows

    def test_panel_keeps_nonmonotonicity_and_does_not_invent_exact_threshold(self):
        p = panel_summary(self.synthetic_branches(), [])
        for r in p.values():
            self.assertEqual(r["earliest_successful_sampled_stop"], 3)
            self.assertEqual(r["last_sampled_failure_before_first_success"], 2)
            self.assertEqual(r["sampled_success_to_failure_reversals"], [[3, 4]])
            self.assertFalse(r["exact_threshold_established"])

    def test_benchmarks_are_eight_reused_results_not_new_or_fully_fine_five_prefixes(self):
        reports = dict(history=dict(run="old_history", branches=[]), spacing=dict(run="old_spacing", branches=[]))
        for o in ("E", "M"):
            stem = o.lower() + "_to_" + ("m" if o == "E" else "e") + "_to_" + o.lower()
            for section, suffix, condition, fine in (("history", "_r1c1_pulse", "pulse", False),
                    ("spacing", "_train_g0010_pulse", "pulse", False),
                    ("spacing", "_train_g0010_blocked", "blocked", False),
                    ("spacing", "_train_g0010_pulse_fine", "pulse", True)):
                reports[section]["branches"].append(dict(case=dict(id=stem + suffix, origin_state=o, condition=condition, fine=fine),
                    exposure={}, rounds=[], outcomes=dict(durable_rewrite=True)))
        rows = historical_benchmarks(reports)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["historical_reuse"] for r in rows))
        self.assertEqual(sum(r["case"]["stop_count"] == 5 for r in rows), 2)
        self.assertFalse(any(r["case"]["fine"] for r in rows if r["case"]["stop_count"] == 5))


if __name__ == "__main__":
    unittest.main()

