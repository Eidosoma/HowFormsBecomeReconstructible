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

from analyze_commitment_components import canonical_state
from analyze_commitment_robustness import audit_branch, expected_design, summarize_panel
from analyze_group_transfer import arrays
from memory_metrics import classify
from robust_relay import round_worker
from run_commitment_robustness import branch_worker, design, load_source, perturb_state, source_name, validate_config
from run_memory_probe import Experiment, array_hash, write_json


class CommitmentRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.config = json.loads((self.root / "configs/commitment_robustness_v1.json").read_text())
        self.indices = dict(zip(("Na", "K", "Cl", "P", "snail", "miR200_total", "Zeb_mRNA_total", "ZEB_prot",
            "miR200_free", "bound0", "bound1", "bound2", "bound3", "bound4", "bound5", "bound6", "ST"), range(17)))
        refs = np.zeros((17, 2))
        refs[:5] = np.array([10, 150, 80, 80, 72])[:, None]
        refs[5:8] = np.array([[60, 10], [10, 60], [1, 50]])
        self.refs = dict(prepared=canonical_state(refs), later=canonical_state(refs))

    def case(self, background="protein", profile="combined", fine=False):
        return next(c for c in self.config["cases"] if (c["background"], c["profile"], c["fine"]) == (background, profile, fine))

    def inputs_fixture(self, temp):
        inputs = Path(temp) / "inputs"
        inputs.mkdir()
        np.savez_compressed(inputs / "references.npz", **self.refs)
        write_json(inputs / "reference.json", dict(ion_indices=self.indices))
        for fine, backgrounds in ((False, ("transient", "protein", "rna", "committed")), (True, ("protein", "rna"))):
            for background in backgrounds:
                case = self.case(background, "none", fine)
                name = source_name(case)
                ids = [name + f":intervened:carrier_{i}" for i in (1, 2)]
                old = [name + f":older_{i}" for i in range(30)] + ids
                rounds = [dict(outgoing_ids=[name + f":round_{n}:child_{i}" for i in (1, 2)]) for n in (4, 5)]
                mask = {"transient": 0, "protein": 1, "rna": 2, "committed": 7}[background]
                packet = np.repeat(self.refs["prepared"][:, 1:2], 2, axis=1)
                packet[0] += mask + .01 * fine
                packet[5:8] += np.array([1, 2, 3])[:, None] * mask / 10
                packet = canonical_state(packet)
                meta = dict(case=dict(id=name, mask=mask, fine=fine), execution_pass=True,
                    durable_M=background != "transient", M_retained=background != "transient", M_renewed=background != "transient",
                    source=dict(intervention_ids=ids, excluded_ids=old), retention=dict(incoming_ids=ids), rounds=rounds)
                write_json(inputs / (name + ".json"), meta)
                np.savez_compressed(inputs / (name + "_entry.npz"), canonical_entry=packet, continuing_packet=packet + 1)
        return inputs

    def fake_experiment(self, case, calls, fail_write=False):
        indices, refs = self.indices, self.refs["prepared"]

        class FakeExperiment:
            def __init__(self, folder, config, fine=False):
                self.folder, self.indices, self.audits, self.reg = folder, indices, [], [5, 6, 7]
                self.fine = fine

            def build(self, count, state, active=False):
                self.state, self.active = state.copy(), active
                edges = np.array([(0, i) for i in range(1, count)], dtype=[("from", int), ("to", int)])
                self.sim = SimpleNamespace(cc_cells=self.state, GJ_connects=edges,
                    GJ_diffusion=np.full((17, count - 1), 2e-15 if active else 0))
                return dict(cells=count, edges=count - 1, active=active, miRNA_kd=2e-15 if active else 0,
                    state_hash_before_derived_refresh=array_hash(state), environment_hash=f"standard-{count}")

            def refresh(self):
                self.state[:] = canonical_state(self.state)

            def phase(self, name, horizon):
                self.refresh()
                initial = self.state.copy()
                calls.append((name, horizon, self.state.shape[1], self.active, self.fine))
                if self.active and not fail_write:
                    self.state[5:8, 0] = np.mean(self.state[5:8, 1:], axis=1)
                    self.state[7, 1:] += .01  # evolving donors must not be reset
                if name.startswith("carrier_") and case["background"] == "transient":
                    self.state[5:8, 0] = refs[5:8, 0]
                if name.endswith(("_shadow", "_challenge")):
                    label = str(classify(self.state, indices)[0])
                    self.state[5:8, 0] = refs[5:8, 1 if label == "M" else 0]
                self.state[0] += horizon / 10000
                self.refresh()
                final = self.state.copy()
                labels = classify(final, indices)
                record = dict(phase=name, requested_horizon=horizon, samples=3, all_labels="".join(labels),
                    recipient_label=str(labels[0]), late_label_fractions={s: float(labels[0] == s) for s in ("E", "M", "X")},
                    miRNA_kd=2e-15 if self.active else 0, graph_edges=final.shape[1] - 1, cpu_seconds=.001)
                np.savez_compressed(self.folder / (name + ".npz"), initial=initial, raw_final=final, final=final,
                    times=np.array([.01, .75 * horizon, horizon + .01]), concentrations=np.repeat(final[None], 3, axis=0))
                self.audits.append(record)
                return final, record

        return FakeExperiment

    def fixture(self, temp, case, fail_write=False):
        inputs = self.inputs_fixture(temp)
        folder = Path(temp) / "branch"
        folder.mkdir()
        calls = []
        with patch("robust_relay.Experiment", self.fake_experiment(case, calls, fail_write)), redirect_stdout(io.StringIO()):
            self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
        self.assertEqual(len(calls), 26)
        return folder, inputs, calls

    def audit(self, folder, inputs, case):
        return audit_branch(folder, inputs, self.config, case, self.indices, self.refs)

    def test_fixed_grid_bounds_and_fine_coverage(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 36)
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]), 6)
        self.assertEqual(sum(c["profile"] in ("loss", "combined", "validation") for c in self.config["cases"]), 19)
        self.assertEqual(36 * 26, 936)
        for key, value in (("jitter_fraction", .2), ("irregular_contacts", [400, 1600]), ("workers", 3),
                ("total_budget_seconds", 7200), ("input_run", "other"), ("jitter_indices", [0, 5, 6, 7])):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError): validate_config(cfg)
        for key, value in (("seed", 42), ("fine", True), ("background", "ordinary")):
            cfg = copy.deepcopy(self.config)
            cfg["cases"][0][key] = value
            with self.assertRaises(ValueError): validate_config(cfg)

    def test_all_seeded_designs_independent_and_paired(self):
        for case in self.config["cases"]:
            self.assertEqual(design(case), expected_design(case))
        for profile in self.config["profiles"]:
            plans = [design(self.case(b, profile)) for b in self.config["backgrounds"]]
            self.assertTrue(all(p == plans[0] for p in plans))
        base = design(self.case(profile="combined"))
        self.assertEqual(base["multipliers"], design(self.case(profile="jitter"))["multipliers"])
        for j in range(2):
            self.assertEqual(base["rounds"][j]["contacts"], design(self.case(profile="timing"))["rounds"][j]["contacts"])
            self.assertEqual(base["rounds"][j]["active_columns"], design(self.case(profile="loss"))["rounds"][j]["active_columns"])
        self.assertNotEqual(base["raw_multipliers"], design(self.case(profile="validation"))["raw_multipliers"])
        self.assertEqual(base, design(self.case(fine=True)))

    def test_edits_only_three_primaries_without_input_mutation(self):
        source = self.refs["prepared"].copy()
        old = source.copy()
        factors = np.array([[.9, 1.1], [.95, 1.05], [1.02, .98]])
        edited = perturb_state(source, factors)
        np.testing.assert_array_equal(source, old)
        np.testing.assert_array_equal(edited[5:8], source[5:8] * factors)
        untouched = [i for i in range(17) if i not in (5, 6, 7)]
        np.testing.assert_array_equal(edited[untouched], source[untouched])
        for f in (np.ones((2, 2)), np.full((3, 2), 1.2), np.full((3, 2), np.nan)):
            with self.assertRaises(ValueError): perturb_state(source, f)

    def test_entry_not_settled_descendants_and_ordinary_control_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs = self.inputs_fixture(temp)
            for background in self.config["backgrounds"]:
                case = self.case(background, "none")
                packet, ids, seen, record = load_source(inputs, case, self.indices, self.refs)
                self.assertEqual(len(seen), 2 if background == "ordinary" else 38)
                self.assertTrue(record["source_before_holds"])
                if background == "ordinary":
                    np.testing.assert_array_equal(packet[:, :1], self.refs["prepared"][:, 1:2])
                else:
                    source = arrays(inputs / (source_name(case) + "_entry.npz"))
                    np.testing.assert_array_equal(packet, source["canonical_entry"])
                    self.assertFalse(np.array_equal(packet, source["continuing_packet"]))

    def test_wrong_source_refinement_and_phenotype_rejected(self):
        for change in ("fine", "phenotype", "ids"):
            with tempfile.TemporaryDirectory() as temp:
                inputs = self.inputs_fixture(temp)
                case = self.case()
                path = inputs / (source_name(case) + ".json")
                meta = json.loads(path.read_text())
                if change == "fine": meta["case"]["fine"] = True
                elif change == "phenotype": meta["durable_M"] = False
                else: meta["source"]["excluded_ids"].pop()
                write_json(path, meta)
                with self.assertRaises(ValueError): load_source(inputs, case, self.indices, self.refs)

    def test_all_36_synthetic_branches_and_full_independent_audits(self):
        for case in self.config["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temp:
                folder, inputs, calls = self.fixture(temp, case)
                branch, _, checks, audits = self.audit(folder, inputs, case)
                self.assertTrue(all(all(c.values()) for c in checks.values()), {k: [n for n, v in c.items() if not v] for k, c in checks.items() if not all(c.values())})
                self.assertEqual(len(audits), 26)
                for name, horizon, count, connected, fine in calls:
                    self.assertEqual(fine, case["fine"])
                    if name.startswith("write_"):
                        self.assertTrue(connected)
                        self.assertEqual(count, 2 if case["profile"] in ("loss", "combined", "validation") else 3)
                    else:
                        self.assertFalse(connected)
                        self.assertEqual(count, 1)

    def test_first_recipient_waits_second_write_duration(self):
        for profile in ("timing", "combined", "validation"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case(profile=profile)
                folder, inputs, _ = self.fixture(temp, case)
                for j, n in enumerate((4, 5)):
                    r = json.loads((folder / f"round_{n:02}/result.json").read_text())
                    phases = {p["phase"]: p for p in r["audits"]}
                    self.assertEqual(phases["wait_1"]["requested_horizon"], design(case)["rounds"][j]["contacts"][1])
                    self.assertEqual(phases["write_1"]["requested_horizon"] + phases["write_2"]["requested_horizon"], 2000)

    def test_loss_uses_actual_survivor_with_no_dummy_and_no_reseed(self):
        with tempfile.TemporaryDirectory() as temp:
            case = self.case()
            folder, inputs, _ = self.fixture(temp, case)
            previous = arrays(folder / "retention/endpoints.npz")["continuing_packet"]
            for j, n in enumerate((4, 5)):
                saved = arrays(folder / f"round_{n:02}/endpoints.npz")
                columns = design(case)["rounds"][j]["active_columns"]
                np.testing.assert_array_equal(saved["incoming_packet"], previous)
                np.testing.assert_array_equal(saved["active_packet"], previous[:, columns])
                self.assertEqual(saved["first_initial"].shape, (17, 2))
                np.testing.assert_array_equal(saved["second_initial"][:, 1:], saved["contact_1"][:, 1:])
                self.assertFalse(np.array_equal(saved["active_packet"], saved["contact_1"][:, 1:]))
                previous = saved["outgoing_packet"]

    def test_negative_retention_and_negative_transfer_are_separate(self):
        for background, fail_write, expected in (("transient", False, "retention"), ("protein", True, "round_4")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case(background)
                folder, inputs, _ = self.fixture(temp, case, fail_write)
                branch, _, checks, _ = self.audit(folder, inputs, case)
                self.assertTrue(all(all(c.values()) for c in checks.values()))
                self.assertEqual(branch["first_failed_stage"], expected)
                self.assertFalse(branch["outcomes"]["durable_M"])
                self.assertEqual(len(branch["rounds"]), 2)

    def test_audit_detects_wrong_source_jitter_seed_and_outcome(self):
        for change in ("source", "jitter", "seed", "outcome"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                if change in ("source", "jitter"):
                    saved = arrays(folder / "endpoints.npz")
                    saved["source_packet" if change == "source" else "perturbed_entry"][7, 0] += 1
                    np.savez_compressed(folder / "endpoints.npz", **saved)
                    key = "exact_initial_source_and_perturbation"
                else:
                    path = folder / "result.json"
                    record = json.loads(path.read_text())
                    if change == "seed":
                        record["design"]["seed"] = 0
                        key = "exact_seeded_design"
                    else:
                        record["durable_M"] = not record["durable_M"]
                        key = "outcomes_recomputed"
                    write_json(path, record)
                checks = self.audit(folder, inputs, case)[2]
                self.assertFalse(checks[case["id"]][key])

    def test_audit_detects_donor_reset_loss_target_and_diagnostic_forwarding(self):
        for change, key in (("second_initial", "second_write_uses_evolved_survivors"),
                ("active_packet", "exact_active_selection"), ("fresh_targets", "exact_fresh_targets"),
                ("outgoing_packet", "actual_held_pair_not_diagnostics")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "round_04/endpoints.npz"
                saved = arrays(path)
                saved[change][7, -1] += 1
                np.savez_compressed(path, **saved)
                checks = self.audit(folder, inputs, case)[2]
                self.assertFalse(checks[case["id"] + "/round_04"][key])

    def test_audit_detects_hold_reset_noncanonical_species_and_wrong_wait(self):
        for change in ("hold", "derived", "wait", "lost_id", "clock"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                group = case["id"] + "/round_04"
                if change in ("hold", "derived"):
                    path = folder / "retention/carrier_1_hold_2.npz"
                    saved = arrays(path)
                    saved["initial"][5 if change == "hold" else 8, 0] += 1
                    np.savez_compressed(path, **saved)
                    group = case["id"] + "/retention"
                    key = "carrier_1_hold_2/" + ("primary_continuity_all_cells" if change == "hold" else "canonical_initial_final")
                else:
                    path = folder / "round_04/result.json"
                    record = json.loads(path.read_text())
                    if change == "wait":
                        next(p for p in record["audits"] if p["phase"] == "wait_1")["requested_horizon"] = 1000
                        key = "wait_1/phase_metadata"
                    elif change == "lost_id":
                        record["lost_ids"][0] = record["active_ids"][0]
                        key = "exact_loss_no_dummy_or_rescue"
                    else:
                        record["nominal_round_start"] += 1
                        key = "correct_common_clock"
                    write_json(path, record)
                self.assertFalse(self.audit(folder, inputs, case)[2][group][key])

    def test_native_one_and_two_donor_graphs_without_integration(self):
        if not (self.root / "upstream/bitsey/cancer_GJ_sims/zombie.py").exists():
            self.skipTest("Native checkout absent")
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            exp = Experiment(Path(temp), self.config)
            for count in (2, 3):
                state = np.repeat(self.refs["prepared"][:, :1], count, axis=1)
                state[:, 1:] = self.refs["prepared"][:, 1:2]
                setup = exp.build(count, state, True)
                exp.refresh()
                self.assertEqual(setup["edges"], count - 1)
                self.assertEqual([[int(e["from"]), int(e["to"])] for e in exp.sim.GJ_connects], [[0, i] for i in range(1, count)])
                np.testing.assert_array_equal(exp.sim.cc_cells[:8], state[:8])
                np.testing.assert_allclose(exp.sim.cc_cells, canonical_state(state), rtol=1e-12, atol=1e-14)

    def test_invalid_survivor_and_non_E_fresh_target_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            packet = np.repeat(self.refs["prepared"][:, 1:2], 2, axis=1)
            fresh = np.repeat(self.refs["prepared"][:, :1], 2, axis=1)
            for columns in ([0, 0], [], [2]):
                with self.assertRaises(ValueError): round_worker(Path(temp), self.config, self.case(), packet, ["a", "b"], {"a", "b"}, fresh,
                    self.refs["later"], self.indices, 4, dict(active_columns=columns, contacts=[1000, 1000]))
            with self.assertRaises(ValueError): round_worker(Path(temp), self.config, self.case(), packet, ["a", "b"], {"a", "b"}, packet,
                self.refs["later"], self.indices, 4, dict(active_columns=[0], contacts=[1000, 1000]))

    def test_summary_keeps_bad_validation_and_improved_negative_controls(self):
        branches = []
        for case in self.config["cases"]:
            success = case["profile"] != "validation" and (case["background"] != "transient" or case["profile"] == "jitter")
            branches.append(dict(case=case, outcomes=dict(M_retained=success, M_renewed=success, durable_M=success),
                first_failed_stage=None if success else "retention"))
        panel = summarize_panel(branches)
        self.assertFalse(panel["protein"]["both_combined_draws_durable"])
        self.assertEqual(next(r for r in panel["transient"]["rows"] if r["profile"] == "jitter")["durable_difference_from_unstressed"], 1)
        self.assertFalse(panel["protein"]["seed_generalization_established"])
        self.assertFalse(panel["protein"]["ecological_fitness_measured"])


if __name__ == "__main__":
    unittest.main()
