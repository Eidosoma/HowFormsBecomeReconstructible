"""Synthetic software tests only; no native biological integrations or pilot outcomes."""

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

from analyze_commitment_components import FLAGS, canonical_state
from analyze_group_transfer import arrays
from analyze_rewrite_tradeoff import analyze, audit_branch, expected_cases, expected_design
from memory_metrics import classify
from rewrite_tradeoff_exposure import exposure_steps
from rewrite_tradeoff_relay import round_worker
from run_memory_probe import Experiment, array_hash, write_json
from run_onward_transfer import file_hash
from run_rewrite_tradeoff import branch_worker, fixed_cases, load_source, readout_plans, source_name, validate_config


class RewriteTradeoffTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.config = json.loads((self.root / "configs/rewrite_tradeoff_v1.json").read_text())
        self.indices = dict(zip(("Na", "K", "Cl", "P", "snail", "miR200_total", "Zeb_mRNA_total", "ZEB_prot",
            "miR200_free", "bound0", "bound1", "bound2", "bound3", "bound4", "bound5", "bound6", "ST"), range(17)))
        refs = np.zeros((17, 2))
        refs[:5] = np.array([10, 150, 80, 80, 72])[:, None]
        refs[5:8] = np.array([[60, 10], [10, 60], [1, 50]])
        self.refs = dict(prepared=canonical_state(refs), later=canonical_state(refs))

    def case(self, name="protein_g1_active2"):
        return next(c for c in self.config["cases"] if c["id"] == name)

    def inputs_fixture(self, temp):
        inputs = Path(temp) / "inputs"
        inputs.mkdir()
        np.savez_compressed(inputs / "references.npz", **self.refs)
        write_json(inputs / "reference.json", dict(ion_indices=self.indices))
        for name in {source_name(c) for c in self.config["cases"]} - {None}:
            background, fine = name.split("_")[0], name.endswith("_fine")
            profile = "single" if "_single" in name else "pair"
            ids = [name+f":placed:carrier_{j}" for j in (1, 2)]
            prior = ids + [name+f":old_{i}" for i in range(6 if background == "ordinary" else 42)]
            old_rounds = [dict(outgoing_ids=[name+f":round_{n}:child_{j}" for j in (1, 2)]) for n in (4, 5)]
            packet = np.repeat(self.refs["prepared"][:, 1:2], 2, axis=1)
            packet[0] += dict(protein=1, rna=2, ordinary=3)[background] + .01*fine
            packet[0, 1] += .1
            np.savez_compressed(inputs / (name+"_source.npz"), source_packet=packet,
                final_packet=np.repeat(self.refs["prepared"][:, :1], 2, axis=1))
            np.savez_compressed(inputs / (name+"_contacts.npz"), placeholder=np.zeros(1))
            write_json(inputs / (name+".json"), dict(case=dict(id=name, background=background, profile=profile, fine=fine),
                execution_pass=True, source=dict(placement_ids=ids, excluded_ids=prior), rounds=old_rounds))
        write_json(inputs / "handover_summary.json", dict(started_utc="20260906T212435Z", revision=self.config["revision"]))
        return inputs

    def fake_experiment(self, calls, case, mode="prompt"):
        indices, refs = self.indices, self.refs["prepared"]

        class FakeExperiment:
            def __init__(self, folder, config, fine=False):
                self.folder, self.config, self.indices, self.reg = folder, config, indices, [5, 6, 7]
                self.fine, self.audits = fine, []

            def build(self, count, state, active=False):
                self.state, self.active = state.copy(), active
                kd = self.config["write_kd"] if active else 0
                edges = np.array([(0, j) for j in range(1, count)], dtype=[("from", int), ("to", int)])
                self.sim = SimpleNamespace(cc_cells=self.state, GJ_connects=edges, GJ_diffusion=np.full((17, count-1), kd))
                return dict(cells=count, edges=count-1, active=active, miRNA_kd=kd,
                    state_hash_before_derived_refresh=array_hash(state), environment_hash=f"standard-{count}")

            def refresh(self):
                self.state[:] = canonical_state(self.state)

            def phase(self, name, horizon):
                self.refresh()
                initial = self.state.copy()
                calls.append((name, horizon, initial.shape[1], self.active, self.fine))
                if self.active:
                    if self.folder.name == "exposure":
                        if initial.shape[1] == 2 and mode not in ("delayed", "no_rewrite"):
                            self.state[5:8, 1:] = self.state[5:8, :1]
                        self.state[7] += .01
                    else:
                        if mode != "failed_readout":
                            self.state[5:8, 0] = np.mean(self.state[5:8, 1:], axis=1)
                        self.state[7, 1:] += .01
                if self.folder.name == "exposure" and name.endswith("_hold_1") and mode == "delayed" and case["rewrite_width"] == 1 and case["condition"] in ("active1", "active2"):
                    self.state[5:8, 0] = refs[5:8, 0]
                if name.endswith(("_shadow", "_challenge")):
                    label = str(classify(self.state, indices)[0])
                    self.state[5:8, 0] = refs[5:8, 1 if label == "M" else 0]
                self.state[0] += horizon/10000
                self.refresh()
                final = self.state.copy()
                labels = classify(final, indices)
                record = dict(phase=name, requested_horizon=horizon, samples=3,
                    all_labels="".join(labels), recipient_label=str(labels[0]),
                    late_label_fractions={s: float(labels[0] == s) for s in ("E", "M", "X")},
                    miRNA_kd=self.config["write_kd"] if self.active else 0,
                    graph_edges=final.shape[1]-1, cpu_seconds=.001)
                np.savez_compressed(self.folder / (name+".npz"), initial=initial, raw_final=final, final=final,
                    times=np.array([.01, .75*horizon, horizon+.01]), concentrations=np.repeat(final[None], 3, axis=0))
                self.audits.append(record)
                return final, record
        return FakeExperiment

    def run_branch(self, folder, inputs, case, mode="prompt"):
        folder.mkdir()
        calls = []
        fake = self.fake_experiment(calls, case, mode)
        with patch("rewrite_tradeoff_exposure.Experiment", fake), patch("rewrite_tradeoff_relay.Experiment", fake), redirect_stdout(io.StringIO()):
            self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
        return calls

    def fixture(self, temp, case=None, mode="prompt"):
        case = case or self.case()
        inputs, folder = self.inputs_fixture(temp), Path(temp) / "branch"
        calls = self.run_branch(folder, inputs, case, mode)
        return folder, inputs, calls

    def audit(self, folder, inputs, case):
        return audit_branch(folder, inputs, self.config, case, self.indices, self.refs)

    def test_fixed_44_case_panel_and_independent_schedule(self):
        validate_config(self.config)
        self.assertEqual(fixed_cases(), expected_cases())
        self.assertEqual(len(self.config["cases"]), 44)
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]), 11)
        for case in self.config["cases"]:
            self.assertEqual(exposure_steps(case), expected_design(case)["steps"])
            self.assertEqual(readout_plans(case), expected_design(case)["readout"])
        for key, value in (("workers", 3), ("total_budget_seconds", 7200), ("write_kd", 4e-15),
                ("input_run", "other"), ("readout_start", 20000), ("conditions", ["active2"])):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError): validate_config(cfg)
        for operation in ("remove", "reorder", "widen"):
            cfg = copy.deepcopy(self.config)
            if operation == "remove": cfg["cases"].pop()
            elif operation == "reorder": cfg["cases"].reverse()
            else: cfg["cases"][3]["readout_width"] = 2
            with self.assertRaises(ValueError): validate_config(cfg)

    def test_source_is_original_H1_packet_not_descendants(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs = self.inputs_fixture(temp)
            self.assertEqual(len(list(inputs.iterdir())), 33)
            for name in ("protein_g1_active1", "protein_g2_active1", "rna_g1_active2_fine", "ordinary_g1_none", "reference_e_pair"):
                case = self.case(name)
                packet, ids, seen, provenance = load_source(inputs, case, self.refs, self.indices)
                reference = case["background"] == "reference"
                self.assertEqual(len(seen), 2 if reference else (14 if case["background"] == "ordinary" else 50))
                self.assertEqual(classify(packet, self.indices).tolist(), (["E"] if reference else ["M"])*2)
                if not reference:
                    old = arrays(inputs / (source_name(case)+"_source.npz"))
                    np.testing.assert_array_equal(packet, old["source_packet"])
                    self.assertFalse(np.array_equal(packet, old["final_packet"]))
                    self.assertTrue(provenance["source_before_H1_handover"])

    def test_bad_source_metadata_rejected(self):
        for change in ("fine", "valid", "exclusions"):
            with tempfile.TemporaryDirectory() as temp:
                inputs = self.inputs_fixture(temp)
                case = self.case()
                path = inputs / (source_name(case)+".json")
                record = json.loads(path.read_text())
                if change == "fine": record["case"]["fine"] = True
                elif change == "valid": record["execution_pass"] = False
                else: record["source"]["excluded_ids"].pop()
                write_json(path, record)
                with self.assertRaises(ValueError): load_source(inputs, case, self.refs, self.indices)

    def test_all_44_synthetic_branches_pass_independent_array_audit(self):
        for case in self.config["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temp:
                folder, inputs, calls = self.fixture(temp, case)
                branch, _, checks, audits = self.audit(folder, inputs, case)
                self.assertTrue(all(all(c.values()) for c in checks.values()), checks)
                self.assertEqual(len(calls), 28 if case["readout_width"] == 2 else 26)
                self.assertEqual(len(audits), len(calls))
                self.assertTrue(all(call[-1] == case["fine"] for call in calls))
                for n in (1, 2):
                    end = arrays(folder / f"round_{n:02}/endpoints.npz")
                    self.assertEqual(end["active_packet"].shape[1], case["readout_width"])
                if case["background"] == "reference":
                    self.assertIsNone(branch["outcomes"]["rewritten"])

    def test_same_cues_and_times_but_different_exposure_membership(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs = self.inputs_fixture(temp)
            records = []
            for name in ("protein_g1_active2", "protein_g2_active2"):
                folder, case = Path(temp) / name, self.case(name)
                self.run_branch(folder, inputs, case)
                end = arrays(folder / "exposure/endpoints.npz")
                for step in (1, 2):
                    np.testing.assert_array_equal(end[f"step_{step}_initial"][:, :1], self.refs["prepared"][:, :1])
                    self.assertEqual(end[f"step_{step}_initial"].shape[1], case["rewrite_width"]+1)
                np.testing.assert_array_equal(end["step_2_initial"][:, 1:], end["step_1_incumbents"])
                np.testing.assert_array_equal(end["readout_entry"], end["step_2_incumbents"][:, :1])
                self.assertEqual(end["continuing_packet"].shape, (17, 1))
                records.append(end)
            np.testing.assert_array_equal(records[0]["source_packet"], records[1]["source_packet"])

    def test_rewriting_retention_and_readout_are_separate(self):
        for mode, expected in (("prompt", (True, True, True)), ("delayed", (True, False, True)),
                ("failed_readout", (True, True, False)), ("no_rewrite", (False, False, False))):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case, mode)
                branch, _, checks, _ = self.audit(folder, inputs, case)
                self.assertTrue(all(all(c.values()) for c in checks.values()))
                outcome = branch["outcomes"]
                self.assertEqual((outcome["rewritten"], outcome["prompt_rewrite"], outcome["rewritten_and_renewed"]), expected)
                self.assertEqual(len(branch["rounds"]), 2)

    def test_new_recipients_not_original_cells_or_cues_are_forwarded(self):
        with tempfile.TemporaryDirectory() as temp:
            case = self.case()
            folder, inputs, _ = self.fixture(temp, case, "failed_readout")
            result = json.loads((folder / "result.json").read_text())
            first = arrays(folder / "round_01/endpoints.npz")
            second = arrays(folder / "round_02/endpoints.npz")
            np.testing.assert_array_equal(second["incoming_packet"], first["outgoing_packet"])
            np.testing.assert_array_equal(second["active_packet"], first["outgoing_packet"][:, 1:2])
            self.assertFalse(set(result["final_ids"]) & set(result["source"]["excluded_ids"]))
            self.assertFalse(set(result["final_ids"]) & set(result["exposure"]["removed_cue_ids"]))
            self.assertEqual(result["fresh_recipients"], 4)
            self.assertEqual(result["removed_carriers"], 2)

    def test_exposure_audit_detects_state_edit_cue_leak_and_wrong_selection(self):
        for key, check in (("source_packet", "exact_source"), ("group_start", "exact_initial_group"),
                ("step_2_initial", "step_2/exact_cue_and_continuous_incumbents"),
                ("readout_entry", "exact_selected_incumbents_no_cues"), ("continuing_packet", "held_endpoints_and_outcomes")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "exposure/endpoints.npz"
                data = arrays(path)
                data[key][7, 0] += 1
                np.savez_compressed(path, **data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]+"/exposure"][check])

    def test_exposure_identity_clock_and_transport_corruption_detected(self):
        for change, check in (("ids", "original_id_selection"), ("cues", "fresh_cues_excluded_from_lineage"),
                ("clock", "nominal_clock"), ("graph", "step_1/star_or_isolation_correct"),
                ("blocked", "step_1/all_transport_off_in_gaps_and_waits"), ("hold", "held_endpoints_and_outcomes")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case("protein_g2_blocked" if change == "blocked" else "protein_g2_active2")
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "exposure/result.json"
                data = json.loads(path.read_text())
                if change == "ids": data["selected_ids"][0] = data["removed_after"][0]
                elif change == "cues": data["removed_cue_ids"][0] = data["selected_ids"][0]
                elif change == "clock": data["nominal_readout_start"] += 1
                elif change == "graph": data["setups"][0]["edges_list"][-1] = [1, 2]
                elif change == "blocked": data["setups"][0]["all_gj_transport_zero"] = False
                else: data["E_retained"] = not data["E_retained"]
                write_json(path, data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]+"/exposure"][check])

    def test_relay_audit_detects_reset_wrong_fresh_and_diagnostic_leak(self):
        for key, check in (("second_initial", "second_write_uses_evolved_survivors"),
                ("active_packet", "exact_active_selection"), ("fresh_targets", "exact_fresh_targets"),
                ("outgoing_packet", "actual_held_pair_not_diagnostics")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "round_01/endpoints.npz"
                data = arrays(path)
                data[key][7, -1] += 1
                np.savez_compressed(path, **data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]+"/round_01"][check])

    def test_canonical_RNA_hold_continuity_and_final_outcomes_checked(self):
        for index, check in ((8, "canonical_RNA_and_ST"), (5, "primary_continuity_all_cells")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "exposure/incumbent_1_hold_2.npz"
                data = arrays(path)
                data["initial"][index, 0] += 1
                np.savez_compressed(path, **data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]+"/exposure"]["incumbent_1_hold_2/"+check])
        with tempfile.TemporaryDirectory() as temp:
            case = self.case()
            folder, inputs, _ = self.fixture(temp, case)
            path = folder / "result.json"
            data = json.loads(path.read_text())
            data["outcomes"]["rewritten_and_renewed"] = False
            write_json(path, data)
            self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]]["outcomes_recomputed"])

    def test_invalid_readout_plan_and_wrong_target_state_rejected(self):
        source = self.refs["prepared"][:, :1]
        fresh = np.repeat(self.refs["prepared"][:, 1:2], 2, axis=1)
        with tempfile.TemporaryDirectory() as temp:
            for key, value in (("active_columns", [1]), ("contacts", [1000, 2000]),
                    ("write_kd", 4e-15), ("connected", 1), ("nominal_end", 0)):
                plan = readout_plans(self.case())[0]
                plan[key] = value
                with self.assertRaises(ValueError):
                    round_worker(Path(temp), self.config, self.case(), source, ["a"], {"a"},
                        fresh, self.refs["later"], self.indices, 1, plan)
            with self.assertRaises(ValueError):
                round_worker(Path(temp), self.config, self.case(), source, ["a"], {"a"},
                    np.repeat(source, 2, axis=1), self.refs["later"], self.indices, 1, readout_plans(self.case())[0])

    def test_native_star_and_fully_blocked_setup_without_integration(self):
        if not (self.root / "upstream/bitsey/cancer_GJ_sims/zombie.py").exists():
            self.skipTest("Native checkout absent")
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            for count in (1, 2, 3):
                for active in (False, True):
                    if count == 1 and active:
                        continue
                    exp = Experiment(Path(temp), self.config)
                    state = np.repeat(self.refs["prepared"][:, :1], count, axis=1)
                    record = exp.build(count, state, active)
                    exp.refresh()
                    self.assertEqual(record["edges"], count-1)
                    self.assertEqual(record["miRNA_kd"], 2e-15 if active else 0)
                    np.testing.assert_array_equal(exp.sim.cc_cells[:8], state[:8])
                    np.testing.assert_allclose(exp.sim.cc_cells, canonical_state(state), rtol=1e-12, atol=1e-14)
                    if not active:
                        self.assertTrue(np.all(exp.sim.GJ_diffusion == 0))

    def full_panel_fixture(self, temp, changed_fine=False, failed_control=False):
        run = Path(temp) / "runs/rewrite-tradeoff-synthetic"
        run.mkdir(parents=True)
        inputs = self.inputs_fixture(run)
        records = []
        for case in self.config["cases"]:
            mode = "failed_readout" if (changed_fine and case["id"] == "protein_g1_active1_fine") or (failed_control and case["id"] == "reference_e_pair") else "prompt"
            folder = run / case["id"]
            self.run_branch(folder, inputs, case, mode)
            result = json.loads((folder / "result.json").read_text())
            records.append(dict(id=case["id"], execution_pass=True, returncode=0, result=result))
            if case["condition"] == "active2":
                end = arrays(folder / "exposure/endpoints.npz")
                np.savez_compressed(inputs / (source_name(case)+"_contacts.npz"),
                    first_initial=end["step_1_initial"], second_initial=end["step_2_initial"],
                    contact_1=end["step_1_full"], contact_2=end["step_2_full"])
        prior = {k: True for k in FLAGS}
        prior.update(ready_for_linked_design=True, array_check_count=12189,
            array_checks={"synthetic_fixture": {"not_a_biological_simulation_result": True}})
        write_json(run / "predecessor_audit.json", prior)
        (run / "frozen").mkdir()
        write_json(run / "frozen/config.json", self.config)
        write_json(Path(temp) / "synthetic_execution.json", {"fixture_only": True})
        manifest = {p.name: dict(source=str(p), sha256=file_hash(p)) for p in inputs.iterdir()}
        self.assertEqual(len(manifest), 33)
        summary = dict(all_execution_valid=True, config=self.config, revision=self.config["revision"], cases=records,
            inputs=manifest, frozen_hashes_sha256={"config.json": file_hash(run / "frozen/config.json")},
            hashes_sha256={"synthetic_execution.json": file_hash(Path(temp) / "synthetic_execution.json")},
            predecessor_audit_sha256=file_hash(run / "predecessor_audit.json"), elapsed_seconds=0.)
        write_json(run / "summary.json", summary)
        return run

    def test_full_panel_report_provenance_controls_counts_and_prefix_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            run = self.full_panel_fixture(temp)
            report = analyze(run)
            self.assertTrue(all(report[k] for k in FLAGS))
            self.assertTrue(report["ready_for_reliability_design"])
            self.assertEqual(len(report["historical_prefix_controls"]), 20)
            self.assertEqual(len(report["fine_comparisons"]), 11)
            for key, value in (("new_integrations", 1152), ("fresh_recipients", 176),
                    ("fresh_pair_handovers", 88), ("initial_placements", 86), ("new_cue_instances", 54), ("removed_carriers", 78)):
                self.assertEqual(report[key], value)
            path = run / "inputs/protein_single_contacts.npz"
            data = arrays(path)
            data["contact_2"][7, 0] += .01
            np.savez_compressed(path, **data)
            invalid = analyze(run)
            self.assertFalse(invalid["unchanged_prefixes_reproduced"])
            self.assertFalse(invalid["input_hashes_valid"])
            self.assertFalse(invalid["ready_for_reliability_design"])

    def test_fine_disagreement_blocks_downstream_but_not_data_validity(self):
        with tempfile.TemporaryDirectory() as temp:
            report = analyze(self.full_panel_fixture(temp, changed_fine=True))
            self.assertTrue(all(report[k] for k in FLAGS))
            self.assertTrue(report["unchanged_prefixes_reproduced"])
            self.assertFalse(report["all_tested_fine_outcomes_and_labels_agree"])
            self.assertFalse(report["ready_for_reliability_design"])

    def test_failed_reference_assay_blocks_downstream(self):
        with tempfile.TemporaryDirectory() as temp:
            report = analyze(self.full_panel_fixture(temp, failed_control=True))
            self.assertTrue(all(report[k] for k in FLAGS))
            self.assertFalse(report["assay_controls_pass"])
            self.assertFalse(report["ready_for_reliability_design"])


if __name__ == "__main__":
    unittest.main()

