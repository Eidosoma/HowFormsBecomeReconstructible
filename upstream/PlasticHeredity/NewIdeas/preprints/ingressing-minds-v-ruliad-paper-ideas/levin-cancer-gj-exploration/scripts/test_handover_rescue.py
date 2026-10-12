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
from analyze_handover_rescue import analyze, audit_branch, expected_design
from handover_rescue_relay import round_worker
from memory_metrics import classify
from run_handover_rescue import branch_worker, design, load_source, source_name, validate_config
from run_memory_probe import Experiment, array_hash, write_json
from run_onward_transfer import file_hash


class HandoverRescueTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.config = json.loads((self.root / "configs/handover_rescue_v1.json").read_text())
        self.indices = dict(zip(("Na", "K", "Cl", "P", "snail", "miR200_total", "Zeb_mRNA_total", "ZEB_prot",
            "miR200_free", "bound0", "bound1", "bound2", "bound3", "bound4", "bound5", "bound6", "ST"), range(17)))
        refs = np.zeros((17, 2))
        refs[:5] = np.array([10, 150, 80, 80, 72])[:, None]
        refs[5:8] = np.array([[60, 10], [10, 60], [1, 50]])
        self.refs = dict(prepared=canonical_state(refs), later=canonical_state(refs))

    def case(self, profile="single_long", background="protein", fine=False):
        return next(c for c in self.config["cases"] if (c["profile"], c["background"], c["fine"]) == (profile, background, fine))

    def inputs_fixture(self, temp):
        inputs = Path(temp) / "inputs"
        inputs.mkdir()
        np.savez_compressed(inputs / "references.npz", **self.refs)
        write_json(inputs / "reference.json", dict(ion_indices=self.indices))
        names = {source_name(c) for c in self.config["cases"]} | {b+"_loss" for b in ("protein", "rna", "ordinary")}
        for name in names:
            background, fine = name.split("_")[0], name.endswith("_fine")
            profile = "loss" if "_loss" in name else "none"
            source_ids = [name + f":placed:carrier_{i}" for i in (1, 2)]
            exclusions = source_ids + ([] if background == "ordinary" else [name + f":old_{i}" for i in range(36)])
            future = [dict(outgoing_ids=[name + f":round_{n}:child_{i}" for i in (1, 2)]) for n in (4, 5)]
            packet = np.repeat(self.refs["prepared"][:, 1:2], 2, axis=1)
            packet[0] += dict(protein=1, rna=2, ordinary=3)[background] + .01*fine
            packet[0, 1] += .1  # survivor choice must matter to the audit
            earlier = packet.copy()
            earlier[0] += 3
            np.savez_compressed(inputs / (name+"_held.npz"), continuing_packet=packet, canonical_entry=earlier)
            meta = dict(case=dict(id=name, background=background, profile=profile, fine=fine),
                execution_pass=True, M_retained=True, M_renewed=True, durable_M=True,
                source=dict(excluded_ids=exclusions, placement_ids=source_ids),
                retention=dict(incoming_ids=source_ids, outgoing_ids=source_ids, M_retained=True), rounds=future)
            write_json(inputs / (name+".json"), meta)
        return inputs

    def fake_experiment(self, calls, mode="prompt"):
        indices, refs = self.indices, self.refs["prepared"]

        class FakeExperiment:
            def __init__(self, folder, config, fine=False):
                self.folder, self.config, self.indices, self.reg = folder, config, indices, [5, 6, 7]
                self.fine, self.audits = fine, []

            def build(self, count, state, active=False):
                self.state, self.active = state.copy(), active
                kd = self.config["write_kd"] if active else 0
                edges = np.array([(0, i) for i in range(1, count)], dtype=[("from", int), ("to", int)])
                self.sim = SimpleNamespace(cc_cells=self.state, GJ_connects=edges, GJ_diffusion=np.full((17, count-1), kd))
                return dict(cells=count, edges=count-1, active=active, miRNA_kd=kd,
                    state_hash_before_derived_refresh=array_hash(state), environment_hash=f"standard-{count}")

            def refresh(self):
                self.state[:] = canonical_state(self.state)

            def phase(self, name, horizon):
                self.refresh()
                initial = self.state.copy()
                calls.append((name, horizon, initial.shape[1], self.active, self.fine, self.config["write_kd"]))
                if self.active:
                    if mode == "prompt":
                        self.state[5:8, 0] = np.mean(self.state[5:8, 1:], axis=1)
                    else:
                        self.state[5:8, 0] = refs[5:8, 0]
                    self.state[7, 1:] += .01
                if mode == "delayed" and name.endswith("_hold_1"):
                    self.state[5:8, 0] = refs[5:8, 1]
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

    def fixture(self, temp, case, mode="prompt"):
        inputs = self.inputs_fixture(temp)
        folder = Path(temp) / "branch"
        folder.mkdir()
        calls = []
        with patch("handover_rescue_relay.Experiment", self.fake_experiment(calls, mode)), redirect_stdout(io.StringIO()):
            self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
        return folder, inputs, calls

    def audit(self, folder, inputs, case):
        return audit_branch(folder, inputs, self.config, case, self.indices, self.refs)

    def test_grid_bounds_and_full_route_refinement(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 35)
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]), 14)
        self.assertEqual(sum(design(c)["profile"]["donors"] == 1 for c in self.config["cases"]), 25)
        for key, value in (("workers", 3), ("total_budget_seconds", 7200), ("write_kd", 4e-15),
                ("input_run", "other"), ("survivor_columns", [1, 0])):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError): validate_config(cfg)
        for change in ("missing", "order", "profile"):
            cfg = copy.deepcopy(self.config)
            if change == "missing": cfg["cases"].pop()
            elif change == "order": cfg["cases"].reverse()
            else: cfg["profiles"][0]["kd_factor"] = 3
            with self.assertRaises(ValueError): validate_config(cfg)

    def test_independent_design_all_cases_and_budget_matching(self):
        for case in self.config["cases"]:
            self.assertEqual(design(case), expected_design(case))
        for first, second, metric in (("pair", "single_long", "time"), ("pair", "single_strong", "kd"), ("single", "pair_weak", "kd")):
            a, b = [design(self.case(p))["profile"] for p in (first, second)]
            key = "contact_horizon" if metric == "time" else "kd_factor"
            self.assertEqual(a["donors"]*a[key], b["donors"]*b[key])

    def test_loads_held_checkpoint_not_entry_or_old_descendants(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs = self.inputs_fixture(temp)
            for case in (self.case(), self.case(background="ordinary"), self.case(fine=True)):
                packet, ids, seen, record = load_source(inputs, case, self.indices)
                saved = arrays(inputs / (source_name(case)+"_held.npz"))
                np.testing.assert_array_equal(packet, saved["continuing_packet"])
                self.assertFalse(np.array_equal(packet, saved["canonical_entry"]))
                self.assertEqual(len(seen), 8 if case["background"] == "ordinary" else 44)
                self.assertTrue(record["source_after_holds"])
                self.assertEqual(record["new_initial_holds"], 0)

    def test_wrong_source_metadata_and_identity_rejected(self):
        for change in ("fine", "memory", "ids"):
            with tempfile.TemporaryDirectory() as temp:
                inputs = self.inputs_fixture(temp)
                case = self.case()
                path = inputs / (source_name(case)+".json")
                meta = json.loads(path.read_text())
                if change == "fine": meta["case"]["fine"] = True
                elif change == "memory": meta["M_retained"] = False
                else: meta["source"]["excluded_ids"].pop()
                write_json(path, meta)
                with self.assertRaises(ValueError): load_source(inputs, case, self.indices)

    def test_all_35_synthetic_branches_have_full_independent_audits(self):
        for case in self.config["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temp:
                folder, inputs, calls = self.fixture(temp, case)
                branch, _, checks, audits = self.audit(folder, inputs, case)
                self.assertTrue(all(all(c.values()) for c in checks.values()), checks)
                self.assertEqual(len(calls), 22)
                self.assertEqual(len(audits), 22)
                self.assertTrue(branch["outcomes"]["M_renewed"])
                for name, horizon, count, active, fine, kd in calls:
                    self.assertEqual(fine, case["fine"])
                    self.assertEqual(kd, design(case)["rounds"][0]["write_kd"])
                    self.assertEqual(count, 1+design(case)["profile"]["donors"] if active else 1)

    def test_prompt_delayed_and_failed_transfer_are_separate(self):
        for mode, expected in (("prompt", (True, True, False)), ("delayed", (False, True, True)), ("failed", (False, False, False))):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case, mode)
                b, _, checks, _ = self.audit(folder, inputs, case)
                self.assertTrue(all(all(c.values()) for c in checks.values()))
                self.assertEqual(tuple(b["outcomes"].values()), expected)
                self.assertEqual(len(b["rounds"]), 2)

    def test_survivors_evolve_without_reset_and_negative_pair_is_forwarded(self):
        for mode in ("prompt", "failed"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case, mode)
                previous = arrays(folder / "endpoints.npz")["source_packet"]
                for j, n in enumerate((4, 5)):
                    e = arrays(folder / f"round_{n:02}/endpoints.npz")
                    np.testing.assert_array_equal(e["incoming_packet"], previous)
                    np.testing.assert_array_equal(e["active_packet"], previous[:, [j]])
                    np.testing.assert_array_equal(e["second_initial"][:, 1:], e["contact_1"][:, 1:])
                    self.assertFalse(np.array_equal(e["active_packet"], e["contact_1"][:, 1:]))
                    previous = e["outgoing_packet"]

    def test_wait_and_clock_follow_long_contacts(self):
        for profile in ("single_long", "single_longer"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case(profile)
                folder, inputs, _ = self.fixture(temp, case)
                for j, n in enumerate((4, 5)):
                    r = json.loads((folder / f"round_{n:02}/result.json").read_text())
                    wait = next(p for p in r["audits"] if p["phase"] == "wait_1")
                    self.assertEqual(wait["requested_horizon"], design(case)["profile"]["contact_horizon"])
                    self.assertEqual(r["nominal_round_end"], design(case)["rounds"][j]["nominal_end"])

    def test_audit_detects_source_and_outcome_corruption(self):
        for change in ("source", "outcome"):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                if change == "source":
                    path = folder / "endpoints.npz"
                    data = arrays(path)
                    data["source_packet"][7, 0] += 1
                    np.savez_compressed(path, **data)
                    key = "no_state_edit_at_entry"
                else:
                    path = folder / "result.json"
                    result = json.loads(path.read_text())
                    result["settled_M_renewed"] = not result["settled_M_renewed"]
                    write_json(path, result)
                    key = "outcomes_recomputed"
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]][key])

    def test_audit_detects_donor_reset_selection_and_diagnostic_leak(self):
        for change, key in (("second_initial", "second_write_uses_evolved_survivors"),
                ("active_packet", "exact_active_selection"), ("outgoing_packet", "actual_held_pair_not_diagnostics"),
                ("fresh_targets", "exact_fresh_targets")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "round_04/endpoints.npz"
                data = arrays(path)
                data[change][7, -1] += 1
                np.savez_compressed(path, **data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]+"/round_04"][key])

    def test_audit_detects_wrong_kd_wait_clock_loss_donor_trace_and_budget(self):
        for change, key in (("kd", "write_1/transport_metadata"), ("wait", "wait_1/phase_metadata"),
                ("clock", "correct_common_clock"), ("loss", "exact_loss_no_dummy_or_rescue"),
                ("donor", "donor_history_reconstructed"), ("budget", "nominal_accounting_recomputed")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "round_04/result.json"
                data = json.loads(path.read_text())
                if change == "kd": next(p for p in data["audits"] if p["phase"] == "write_1")["miRNA_kd"] = 4e-15
                elif change == "wait": next(p for p in data["audits"] if p["phase"] == "wait_1")["requested_horizon"] = 1000
                elif change == "clock": data["nominal_round_end"] += 1
                elif change == "loss": data["lost_ids"][0] = data["active_ids"][0]
                elif change == "donor": data["donor_contact_history"][0]["end_labels"] = "E"
                else: data["nominal_accounting"]["summed_miRNA_kd_time"] *= 2
                write_json(path, data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]+"/round_04"][key])

    def test_audit_detects_derived_RNA_and_hold_reset(self):
        for change, key in ((8, "canonical_initial_final"), (5, "primary_continuity_all_cells")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "round_04/child_1_hold_2.npz"
                data = arrays(path)
                data["initial"][change, 0] += 1
                np.savez_compressed(path, **data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]+"/round_04"]["child_1_hold_2/"+key])

    def test_invalid_plan_and_wrong_fresh_state_rejected(self):
        packet = np.repeat(self.refs["prepared"][:, 1:2], 2, axis=1)
        fresh = np.repeat(self.refs["prepared"][:, :1], 2, axis=1)
        with tempfile.TemporaryDirectory() as temp:
            for key, value in (("active_columns", [0, 0]), ("contacts", [1000, 3000]), ("write_kd", 8e-15), ("nominal_end", 0)):
                plan = design(self.case())["rounds"][0]
                plan[key] = value
                with self.assertRaises(ValueError):
                    round_worker(Path(temp), self.config, self.case(), packet, ["a", "b"], {"a", "b"}, fresh, self.refs["later"], self.indices, 4, plan)
            with self.assertRaises(ValueError):
                round_worker(Path(temp), self.config, self.case(), packet, ["a", "b"], {"a", "b"}, packet, self.refs["later"],
                    self.indices, 4, design(self.case())["rounds"][0])

    def test_native_kd_graphs_algebra_without_integration(self):
        if not (self.root / "upstream/bitsey/cancer_GJ_sims/zombie.py").exists():
            self.skipTest("Native checkout absent")
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            for count in (2, 3):
                matrices = {}
                for kd in (1e-15, 2e-15, 4e-15):
                    exp = Experiment(Path(temp), dict(self.config, write_kd=kd))
                    state = np.repeat(self.refs["prepared"][:, :1], count, axis=1)
                    state[:, 1:] = self.refs["prepared"][:, 1:2]
                    record = exp.build(count, state, True)
                    exp.refresh()
                    self.assertEqual(record["miRNA_kd"], kd)
                    self.assertEqual(record["edges"], count-1)
                    np.testing.assert_array_equal(exp.sim.cc_cells[:8], state[:8])
                    np.testing.assert_allclose(exp.sim.cc_cells, canonical_state(state), rtol=1e-12, atol=1e-14)
                    matrices[kd] = exp.sim.GJ_diffusion.copy()
                for kd in (1e-15, 4e-15):
                    np.testing.assert_array_equal(matrices[kd][:4], matrices[2e-15][:4])

    def full_panel_fixture(self, temp, changed_fine=False):
        run = Path(temp) / "runs" / "handover-rescue-synthetic"
        run.mkdir(parents=True)
        inputs = self.inputs_fixture(run)
        records = []
        for case in self.config["cases"]:
            folder = run / case["id"]
            folder.mkdir()
            mode = "failed" if changed_fine and case["id"] == "protein_single_weak_fine" else "prompt"
            with patch("handover_rescue_relay.Experiment", self.fake_experiment([], mode)), redirect_stdout(io.StringIO()):
                branch_worker(folder, self.config, case, inputs)
            result = json.loads((folder / "result.json").read_text())
            records.append(dict(id=case["id"], execution_pass=True, returncode=0, result=result))
            benchmark = source_name(case) if case["profile"] == "pair" else case["background"]+"_loss"
            if case["profile"] == "pair" or (case["profile"] == "single" and not case["fine"]):
                for n in (4, 5):
                    np.savez_compressed(inputs / (benchmark+f"_round_{n:02}.npz"), **arrays(folder / f"round_{n:02}/endpoints.npz"))
        write_json(inputs / "robustness_summary.json", dict(started_utc="20260906T193416Z", revision=self.config["revision"]))
        prior = {k: True for k in FLAGS}
        prior.update(ready_for_stage3_design=True, array_check_count=14567, array_checks={"synthetic_fixture": {"explicitly_not_a_simulation_result": True}})
        write_json(run / "predecessor_audit.json", prior)
        (run / "frozen").mkdir()
        write_json(run / "frozen/config.json", self.config)
        write_json(Path(temp) / "synthetic_execution.json", {"fixture_only": True})
        manifest = {p.name: dict(source=str(p), sha256=file_hash(p)) for p in inputs.iterdir()}
        self.assertEqual(len(manifest), 35)
        summary = dict(all_execution_valid=True, config=self.config, revision=self.config["revision"], cases=records,
            inputs=manifest, frozen_hashes_sha256={"config.json": file_hash(run / "frozen/config.json")},
            hashes_sha256={"synthetic_execution.json": file_hash(Path(temp) / "synthetic_execution.json")},
            predecessor_audit_sha256=file_hash(run / "predecessor_audit.json"), elapsed_seconds=0.)
        write_json(run / "summary.json", summary)
        return run

    def test_full_panel_report_controls_refinements_and_resource_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            run = self.full_panel_fixture(temp)
            report = analyze(run)
            self.assertTrue(all(report[k] for k in FLAGS))
            self.assertTrue(report["ready_for_linked_design"])
            self.assertEqual(len(report["controls"]), 8)
            self.assertEqual(len(report["fine_comparisons"]), 14)
            self.assertEqual(report["new_integrations"], 770)
            self.assertEqual(report["fresh_recipients"], 140)
            self.assertEqual(report["lost_carriers"], 50)
            self.assertEqual(report["new_initial_holds"], 0)
            for row in report["panel"].values():
                self.assertFalse(row["ecological_fitness_measured"])
                self.assertFalse(row["autonomous_reproduction"])
            # A changed historical benchmark is a control failure, not silently accepted.
            path = run / "inputs/protein_none_round_04.npz"
            data = arrays(path)
            data["outgoing_packet"][7, 0] += .01
            np.savez_compressed(path, **data)
            invalid = analyze(run)
            self.assertFalse(invalid["unchanged_controls_reproduced"])
            self.assertFalse(invalid["input_hashes_valid"])
            self.assertFalse(invalid["ready_for_linked_design"])

    def test_valid_negative_fine_difference_blocks_downstream_not_data_validity(self):
        with tempfile.TemporaryDirectory() as temp:
            report = analyze(self.full_panel_fixture(temp, changed_fine=True))
            self.assertTrue(all(report[k] for k in FLAGS))
            self.assertTrue(report["unchanged_controls_reproduced"])
            self.assertFalse(report["all_tested_fine_outcomes_and_labels_agree"])
            self.assertFalse(report["ready_for_linked_design"])


if __name__ == "__main__":
    unittest.main()
