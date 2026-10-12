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

import test_commitment_window as fixture_module
from analyze_commitment_components import audit_branch, audit_retention, audit_sources, canonical_state, factorial_contrasts
from analyze_group_transfer import arrays
from memory_metrics import classify
from run_commitment_components import branch_worker, load_sources, mix_packet, retention_worker, validate_config
from run_commitment_window import checkpoint_file
from run_memory_probe import Experiment, array_hash, write_json


class CommitmentComponentsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.config = json.loads((self.root / "configs/commitment_components_v1.json").read_text())
        self.previous = fixture_module.CommitmentWindowTests()
        self.previous.setUp()
        self.indices, self.refs = self.previous.indices, self.previous.refs

    def case(self, mask=0, fine=False):
        return next(c for c in self.config["cases"] if c["mask"] == mask and c["fine"] == fine)

    def inputs_fixture(self, temp, case):
        inputs = Path(temp) / "inputs"
        inputs.mkdir()
        for n in (6, 8):
            parent = Path(temp) / f"source_{n}"
            parent.mkdir()
            old_case = self.previous.case(n=n, origin="M", fine=case["fine"])
            old_inputs = self.previous.inputs_fixture(parent, old_case)
            for path in old_inputs.iterdir():
                (inputs / path.name).write_bytes(path.read_bytes())
            for i in (1, 2):
                filename = inputs / checkpoint_file(old_case, i)
                data = arrays(filename)
                for key in ("initial", "raw_final", "final"):
                    data[key][5:8, 0] = [10 + n, 40 + n, n + i]
                    data[key][16] = 0
                    data[key] = canonical_state(data[key])
                data["concentrations"] = np.repeat(data["final"][None], 3, axis=0)
                data["concentrations"][-1, 0] += 7  # not the live endpoint
                np.savez_compressed(filename, **data)
        return inputs

    def fake_experiment(self, fine_seen, flip=False):
        indices = self.indices

        class FakeExperiment:
            def __init__(self, folder, config, fine=False):
                self.folder, self.indices, self.audits = folder, indices, []
                fine_seen.append(fine)

            def build(self, count, state, active=False):
                self.state = state.copy()
                self.sim = SimpleNamespace(cc_cells=self.state, GJ_connects=np.array([], dtype=[("from", int), ("to", int)]),
                    GJ_diffusion=np.zeros((17, 0)))
                return dict(cells=count, edges=0, active=active, miRNA_kd=0,
                    state_hash_before_derived_refresh=array_hash(state), environment_hash="standard")

            def refresh(self):
                self.state[:] = canonical_state(self.state)

            def phase(self, name, horizon):
                self.refresh()
                initial = self.state.copy()
                self.state[0] += horizon / 10000
                if flip:
                    self.state[5:8, 0] = [60, 10, 1]
                self.refresh()
                final = self.state.copy()
                labels = classify(final, indices)
                record = dict(phase=name, requested_horizon=horizon, samples=3, all_labels="".join(labels),
                    recipient_label=str(labels[0]), late_label_fractions={s: float(labels[0] == s) for s in ("E", "M", "X")},
                    miRNA_kd=0, graph_edges=0)
                np.savez_compressed(self.folder / (name + ".npz"), initial=initial, raw_final=final, final=final,
                    times=np.array([.1, 7500, 10000.1]), concentrations=np.repeat(final[None], 3, axis=0))
                self.audits.append(record)
                return final, record

        return FakeExperiment

    def fixture(self, temp, case):
        inputs = self.inputs_fixture(temp, case)
        packets, hybrid, ids, _, _ = load_sources(inputs, self.config, case, self.indices)
        folder, fine_seen = Path(temp) / "retention", []
        with patch("run_commitment_components.Experiment", self.fake_experiment(fine_seen)):
            packet, result = retention_worker(folder, self.config, case, packets, hybrid, ids, self.indices)
        self.assertEqual(fine_seen, [case["fine"]])
        return folder, inputs, packet, result

    def test_fixed_factorial_and_resources(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 16)
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]), 8)
        self.assertEqual(16 * 26, 416)
        for k, v in (("source_stops", [5, 8]), ("input_run", "other"), ("workers", 3),
                ("cue_horizon", 10), ("assay_time_origin", "source"), ("cue_holds", [10, 10])):
            config = copy.deepcopy(self.config)
            config[k] = v
            with self.assertRaises(ValueError): validate_config(config)
        for k, v in (("mask", 1), ("fine", True), ("history", "blocked"), ("state", "E")):
            config = copy.deepcopy(self.config)
            config["cases"][0][k] = v
            with self.assertRaises(ValueError): validate_config(config)
        config = copy.deepcopy(self.config)
        config["cases"].reverse()
        with self.assertRaises(ValueError): validate_config(config)

    def test_all_sixteen_sources_mixes_holds_and_independent_audits(self):
        for case in self.config["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temp:
                folder, inputs, packet, _ = self.fixture(temp, case)
                loaded = load_sources(inputs, self.config, case, self.indices)
                source_audit = audit_sources(inputs, self.config, case, self.indices)
                self.assertEqual(loaded[-1], source_audit[-2])
                self.assertEqual(len(loaded[3]), 32)
                self.assertTrue(all(source_audit[-1].values()), source_audit[-1])
                audit = audit_retention(folder, inputs, self.config, case, self.indices)
                self.assertTrue(all(audit[5].values()), [k for k, v in audit[5].items() if not v])
                np.testing.assert_array_equal(packet, audit[0])

    def test_block_selection_reciprocals_and_no_input_mutation(self):
        six, eight = [np.full((17, 2), float(n)) for n in (6, 8)]
        for value in (six, eight):
            value[4], value[16] = 72, 0
        before = [s.copy() for s in (six, eight)]
        for mask in range(8):
            hybrid = mix_packet(six, eight, self.case(mask))
            for rows, bit in (([0, 1, 2, 3], 4), ([5, 6], 2), ([7], 1)):
                np.testing.assert_array_equal(hybrid[rows], (eight if mask & bit else six)[rows])
            np.testing.assert_array_equal(hybrid[8:16], (eight if mask & 4 else six)[8:16])
        np.testing.assert_array_equal(mix_packet(six, eight, self.case(0)), six)
        np.testing.assert_array_equal(mix_packet(six, eight, self.case(7)), eight)
        for a, b in zip((six, eight), before): np.testing.assert_array_equal(a, b)

    def test_invalid_packet_and_fixed_species_rejected(self):
        six = np.ones((17, 2))
        six[4], six[16] = 72, 0
        for ion, value in ((0, -1), (7, np.nan), (4, 71), (16, 1)):
            changed = six.copy()
            changed[ion] = value
            with self.assertRaises(ValueError): mix_packet(six, changed, self.case())
        with self.assertRaises(ValueError): mix_packet(six[:, :1], six, self.case())

    def test_live_endpoint_and_full_source_refinement(self):
        for fine in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case(1, fine)
                inputs = self.inputs_fixture(temp, case)
                packets, *_ = load_sources(inputs, self.config, case, self.indices)
                for n in (6, 8):
                    p = arrays(inputs / checkpoint_file(dict(case, stop_count=n), 1))
                    np.testing.assert_array_equal(packets[n][:, :1], p["final"][:, :1])
                    self.assertFalse(np.array_equal(packets[n][:, :1], p["concentrations"][-1, :, :1]))

    def test_native_algebra_agrees_without_any_integration(self):
        if not (self.root / "upstream/bitsey/cancer_GJ_sims/zombie.py").exists():
            self.skipTest("Native checkout absent")
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            inputs = self.inputs_fixture(temp, self.case())
            packets, *_ = load_sources(inputs, self.config, self.case(), self.indices)
            exp = Experiment(Path(temp), self.config)
            for case in self.config["cases"]:
                hybrid = mix_packet(packets[6], packets[8], case)
                exp.build(2, hybrid, False)
                exp.refresh()
                np.testing.assert_array_equal(exp.sim.cc_cells[:8], hybrid[:8])
                np.testing.assert_allclose(exp.sim.cc_cells, canonical_state(hybrid), rtol=1e-12, atol=1e-14)

    def test_audit_detects_primary_derived_source_and_forwarding_corruption(self):
        changes = (("hybrid_before_refresh", 0, "exact_primary_component_mix"),
            ("hybrid_before_refresh", 5, "exact_primary_component_mix"),
            ("canonical_entry", 8, "native_derived_refresh_matches_formula"),
            ("canonical_entry", 7, "no_primary_change_during_refresh"),
            ("source_8", 7, "complete_sources_saved"),
            ("continuing_packet", 5, "carrier_1/actual_held_receiver_forwarded"))
        for array, ion, check in changes:
            with tempfile.TemporaryDirectory() as temp:
                case = self.case(1)
                folder, inputs, *_ = self.fixture(temp, case)
                p = arrays(folder / "endpoints.npz")
                p[array][ion, 0] += 1
                np.savez_compressed(folder / "endpoints.npz", **p)
                self.assertFalse(audit_retention(folder, inputs, self.config, case, self.indices)[5][check])

    def test_audit_detects_hold_reset_bad_derived_state_and_transport(self):
        for change in ("primary", "derived", "transport", "clock"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, *_ = self.fixture(temp, case)
                if change in ("primary", "derived"):
                    p = arrays(folder / "carrier_1_hold_2.npz")
                    p["initial"][5 if change == "primary" else 8, 0] += 1
                    np.savez_compressed(folder / "carrier_1_hold_2.npz", **p)
                    key = "carrier_1_hold_2/" + ("primary_continuity_all_cells" if change == "primary" else "canonical_initial_and_final")
                else:
                    path = folder / "result.json"
                    record = json.loads(path.read_text())
                    if change == "transport":
                        record["setups"][0]["active"] = True
                        key = "carrier_1_hold_1/all_transport_off_in_gaps_and_waits"
                    else:
                        record["audits"][0]["requested_horizon"] = 10
                        key = "carrier_1_hold_1/phase_metadata"
                    write_json(path, record)
                self.assertFalse(audit_retention(folder, inputs, self.config, case, self.indices)[5][key])

    def branch_fixture(self, temp, case):
        inputs = self.inputs_fixture(temp, case)
        folder = Path(temp) / "branch"
        folder.mkdir()
        calls = []

        def fake_round(stage, config, c, packet, ids, seen, fresh, later, indices, n):
            self.assertEqual(len(seen), 32 + 2 * (n - 4))
            self.assertEqual(c["history"], "learned")
            self.assertEqual(classify(packet, indices).tolist(), ["E", "E"])
            calls.append(n)
            new_ids = [f"{c['id']}:round_{n:02}:child_{i}" for i in (1, 2)]
            row = dict(round=n, round_success=False, children=[dict(id=i) for i in new_ids],
                outgoing_labels="".join(classify(packet, indices)))
            write_json(stage / "result.json", row)
            np.savez_compressed(stage / "endpoints.npz", outgoing_packet=packet)
            return packet.copy(), new_ids, row

        with patch("run_commitment_components.Experiment", self.fake_experiment([], flip=True)), patch(
                "run_commitment_components.round_worker", fake_round), redirect_stdout(io.StringIO()):
            self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
        self.assertEqual(calls, [4, 5])
        return folder, inputs

    def fake_audit_round(self, stage, *args):
        return arrays(stage / "endpoints.npz"), json.loads((stage / "result.json").read_text()), dict(mock_only=True), [dict(samples=3)] * 11

    def test_negative_actual_packet_continues_through_both_rounds(self):
        with tempfile.TemporaryDirectory() as temp:
            case = self.case()
            folder, inputs = self.branch_fixture(temp, case)
            with patch("analyze_commitment_components.audit_round", self.fake_audit_round):
                branch, _, checks, audits = audit_branch(folder, inputs, self.config, case, self.indices, dict(prepared=self.refs, later=self.refs))
            self.assertTrue(all(all(c.values()) for c in checks.values()), checks)
            self.assertFalse(branch["outcomes"]["durable_M"])
            self.assertEqual(len(audits), 26)

    def test_branch_audit_detects_clock_outcome_identity_and_packet_errors(self):
        for change in ("clock", "outcome", "identity", "packet"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs = self.branch_fixture(temp, case)
                path = folder / "result.json"
                record = json.loads(path.read_text())
                if change == "clock":
                    record["nominal_schedule"][0]["start"] += 110
                    key = "common_assay_clock"
                elif change == "outcome":
                    record["durable_M"] = True
                    key = "outcomes_recomputed"
                elif change == "identity":
                    record["final_ids"][0] = record["source"]["excluded_ids"][0]
                    key = "final_ids_correct"
                else:
                    data = arrays(folder / "endpoints.npz")
                    data["continuing_start"][7, 0] += 1
                    np.savez_compressed(folder / "endpoints.npz", **data)
                    key = "actual_held_pair_starts_relay"
                write_json(path, record)
                with patch("analyze_commitment_components.audit_round", self.fake_audit_round):
                    checks = audit_branch(folder, inputs, self.config, case, self.indices, dict(prepared=self.refs, later=self.refs))[2]
                self.assertFalse(checks[case["id"]][key])

    def test_factorial_reports_interactions_and_negative_effects_without_global_claim(self):
        branches = []
        for case in self.config["cases"]:
            success = case["mask"] in (1, 7)
            branches.append(dict(case=case, outcomes=dict(M_retained=success, M_renewed=success, durable_M=success)))
        for panel in factorial_contrasts(branches).values():
            self.assertEqual(len(panel["contrasts"]), 12)
            self.assertTrue(panel["controls_expected"])
            self.assertFalse(panel["global_necessity_or_sufficiency_established"])
            self.assertTrue(any(c["durable_difference"] == -1 for c in panel["contrasts"]))
            self.assertTrue(panel["add_to_six"]["protein"]["with_eight_block"]["durable_M"])
            self.assertFalse(panel["remove_from_eight"]["protein"]["with_six_block"]["durable_M"])


if __name__ == "__main__":
    unittest.main()
