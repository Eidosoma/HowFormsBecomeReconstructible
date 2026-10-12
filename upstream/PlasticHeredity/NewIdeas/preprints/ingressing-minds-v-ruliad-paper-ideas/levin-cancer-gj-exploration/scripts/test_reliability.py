"""Synthetic execution/audit fixtures; no native biological pilot integrations."""

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
from analyze_reliability import analyze, audit_branch, expected_cases, expected_design, expected_recipe
from memory_metrics import classify
from reliability_relay import donor_shock
from run_memory_probe import Experiment, array_hash, write_json
from run_onward_transfer import file_hash
from run_reliability import FAMILIES, H1_NAMES, H2_NAMES, branch_worker, design, fixed_cases, freeze_inputs, load_source, source_recipe, validate_config


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.configs = {s: json.loads((self.root / f"configs/reliability_{s}_v1.json").read_text()) for s in ("screen", "confirmation")}
        self.indices = dict(zip(("Na", "K", "Cl", "P", "snail", "miR200_total", "Zeb_mRNA_total", "ZEB_prot",
            "miR200_free", "bound0", "bound1", "bound2", "bound3", "bound4", "bound5", "bound6", "ST"), range(17)))
        refs = np.zeros((17, 2))
        refs[:5] = np.array([10, 150, 80, 80, 72])[:, None]
        refs[5:8] = np.array([[60, 10], [10, 60], [1, 50]])
        self.refs = dict(prepared=canonical_state(refs), later=canonical_state(refs))

    def case(self, family="protein_m_pair", profile="strong_s1", fine=False, stage="screen"):
        return next(c for c in self.configs[stage]["cases"] if (c["family"], c["profile"], c["fine"]) == (family, profile, fine))

    def inputs_fixture(self, temp):
        inputs = Path(temp) / "inputs"
        inputs.mkdir()
        np.savez_compressed(inputs / "references.npz", **self.refs)
        write_json(inputs / "reference.json", dict(ion_indices=self.indices))
        write_json(inputs / "rewrite_summary.json", dict(started_utc="20260906T233148Z", revision=self.configs["screen"]["revision"]))
        for name in H1_NAMES:
            ids = [name+f":placed:carrier_{j}" for j in (1, 2)]
            excluded = ids+[name+f":old_{j}" for j in range(6 if name.startswith("ordinary") else 42)]
            state = np.repeat(self.refs["prepared"][:, 1:2], 2, axis=1)
            state[0] += (1 if name.startswith("protein") else 2)+.01*name.endswith("_fine")
            state[0, 1] += .1
            rows = [dict(outgoing_ids=[name+f":round_{n}:child_{j}" for j in (1, 2)]) for n in (4, 5)]
            write_json(inputs / ("h1_"+name+".json"), dict(case=dict(id=name, fine=name.endswith("_fine")),
                execution_pass=True, source=dict(placement_ids=ids, excluded_ids=excluded), rounds=rows))
            np.savez_compressed(inputs / ("h1_"+name+"_source.npz"), source_packet=state)
            np.savez_compressed(inputs / ("h1_"+name+"_contacts.npz"), placeholder=np.zeros(1))
        for name in H2_NAMES:
            acquired = name.startswith(("protein", "rna"))
            pair = name.startswith(("reference_e_pair", "reference_e_blocked_pair"))
            count = 2 if pair else 1
            placed = [name+f":placed:incumbent_{j}" for j in range(1, 3 if acquired or pair else 2)]
            selected = placed[:count]
            excluded = placed+[name+f":old_{j}" for j in range(48 if acquired else 0)]
            cues = [name+f":cue:{j}" for j in (1, 2)] if acquired else []
            rows = [dict(outgoing_ids=[name+f":round_{n}:child_{j}" for j in (1, 2)]) for n in (1, 2)]
            state = np.repeat(self.refs["prepared"][:, :1], count, axis=1)
            state[0] += (3 if name.startswith("protein") else 4)+.01*name.endswith("_fine")
            write_json(inputs / ("h2_"+name+".json"), dict(case=dict(id=name, fine=name.endswith("_fine")), execution_pass=True,
                source=dict(excluded_ids=excluded), exposure=dict(selected_ids=selected, removed_cue_ids=cues),
                outcomes=dict(E_retained=True, rewritten=True if acquired else None), rounds=rows))
            np.savez_compressed(inputs / ("h2_"+name+"_source.npz"), continuing_packet=state)
            for n in (1, 2):
                np.savez_compressed(inputs / ("h2_"+name+f"_round_{n:02}.npz"), placeholder=np.zeros(1))
        self.assertEqual(len(list(inputs.iterdir())), 64)
        return inputs

    def fake_experiment(self, calls, case, mode="normal"):
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
                calls.append((name, horizon, self.state.shape[1], self.active, self.fine))
                if self.active:
                    fail = mode == "pairfails" or (mode == "poolfails" and case["family"] == "pooled_rewritten_e_pair")
                    if self.state.shape[1] == 3 and not fail:
                        self.state[5:8, 0] = np.mean(self.state[5:8, 1:], axis=1)
                    self.state[7, 1:] += .01
                if name.endswith(("_hold_1", "_hold_2", "_shadow", "_challenge")):
                    label = str(classify(self.state, indices)[0])
                    self.state[5:8, 0] = refs[5:8, 0 if label == "E" else 1]
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

    def run_branch(self, folder, inputs, case, stage="screen", mode="normal"):
        folder.mkdir()
        calls = []
        with patch("reliability_relay.Experiment", self.fake_experiment(calls, case, mode)), redirect_stdout(io.StringIO()):
            self.assertEqual(branch_worker(folder, self.configs[stage], case, inputs), 0)
        return calls

    def fixture(self, temp, case=None, stage="screen"):
        case = case or self.case(stage=stage)
        inputs, folder = self.inputs_fixture(temp), Path(temp) / "branch"
        calls = self.run_branch(folder, inputs, case, stage)
        return folder, inputs, calls

    def audit(self, folder, inputs, case, stage="screen"):
        return audit_branch(folder, inputs, self.configs[stage], case, self.indices, self.refs)

    def test_both_grids_fixed_disjoint_seeds_ids_and_independent_design(self):
        for stage, config in self.configs.items():
            validate_config(config)
            self.assertEqual(config["cases"], expected_cases(stage))
            self.assertEqual(fixed_cases(stage), expected_cases(stage))
            self.assertEqual(len(config["cases"]), 57 if stage == "screen" else 39)
            for case in config["cases"]:
                self.assertEqual(design(config, case), expected_design(config, case))
                self.assertEqual(source_recipe(case), expected_recipe(case))
        self.assertFalse(set(self.configs["screen"]["seeds"]) & set(self.configs["confirmation"]["seeds"]))
        self.assertFalse({c["id"] for c in self.configs["screen"]["cases"]} & {c["id"] for c in self.configs["confirmation"]["cases"]})
        for key, value in (("workers", 3), ("total_budget_seconds", 28800), ("round_count", 100),
                ("shocks_per_round", 1), ("input_run", "other")):
            cfg = copy.deepcopy(self.configs["screen"])
            cfg[key] = value
            with self.assertRaises(ValueError): validate_config(cfg)

    def test_common_draws_amplitude_scaling_and_fresh_randomness_each_round(self):
        cfg = self.configs["screen"]
        a, b = [design(cfg, self.case(profile=p)) for p in ("mild_s1", "strong_s1")]
        self.assertEqual(a["raw_uniform"], b["raw_uniform"])
        self.assertNotEqual(a["rounds"][0]["shock_factors"], a["rounds"][1]["shock_factors"])
        other = design(cfg, self.case("pooled_rewritten_e_pair", "strong_s1"))
        self.assertEqual(other["rounds"], b["rounds"])
        baseline = design(cfg, self.case(profile="none"))
        self.assertTrue(np.all(np.array([p["shock_factors"] for p in baseline["rounds"]]) == 1))
        fine = design(cfg, self.case("protein_m_pair", "strong_s3", True))
        self.assertEqual(fine, design(cfg, self.case("protein_m_pair", "strong_s3")))

    def test_pool_uses_two_distinct_rewritten_original_incumbents(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs = self.inputs_fixture(temp)
            case = self.case("pooled_rewritten_e_pair")
            packet, ids, seen, record = load_source(inputs, self.configs["screen"], case, self.indices)
            expected = np.concatenate([arrays(inputs / ("h2_"+n+"_source.npz"))["continuing_packet"] for n in ("protein_g1_active2", "rna_g1_active2")], axis=1)
            np.testing.assert_array_equal(packet, expected)
            self.assertEqual(len(set(record["source_ids"])), 2)
            self.assertFalse(np.array_equal(packet[:, :1], packet[:, 1:2]))
            self.assertTrue(record["pooled_across_routes"])
            self.assertFalse(record["cloned_source_cell"])
            spec = source_recipe(case)[0]
            with patch("run_reliability.source_recipe", return_value=[spec, spec]):
                with self.assertRaises(ValueError): load_source(inputs, self.configs["screen"], case, self.indices)

    def test_shocks_only_edit_primary_regulators(self):
        state = self.refs["prepared"]
        changed = donor_shock(state, np.full((3, 2), 1.25))
        np.testing.assert_array_equal(changed[5:8], state[5:8]*1.25)
        for section in (slice(0, 5), slice(8, 17)):
            np.testing.assert_array_equal(changed[section], state[section])
        np.testing.assert_array_equal(donor_shock(state, np.ones((3, 2))), state)
        for bad in (np.ones((2, 2)), np.full((3, 2), 1.26), np.full((3, 2), np.nan)):
            with self.assertRaises(ValueError): donor_shock(state, bad)

    def test_representative_full_branches_and_negative_continuation(self):
        for family, _, _, _ in FAMILIES:
            with self.subTest(family=family), tempfile.TemporaryDirectory() as temp:
                case = self.case(family)
                folder, inputs, calls = self.fixture(temp, case)
                branch, _, checks, audits = self.audit(folder, inputs, case)
                self.assertTrue(all(all(c.values()) for c in checks.values()), checks)
                self.assertEqual(len(calls), 88)
                self.assertEqual(len(audits), 88)
                self.assertEqual(len(branch["rounds"]), 8)
                if case["width"] == 1 or not case["connected"]:
                    self.assertEqual(branch["outcomes"]["first_failed_round"], 1)
                    self.assertFalse(branch["outcomes"]["censored"])

    def test_evolved_donors_receive_second_shock_and_actual_children_forward(self):
        with tempfile.TemporaryDirectory() as temp:
            case = self.case()
            folder, inputs, _ = self.fixture(temp, case)
            first = arrays(folder / "round_01/endpoints.npz")
            second = arrays(folder / "round_02/endpoints.npz")
            expected = donor_shock(first["contact_1"][:, 1:], first["shock_factors"][1])
            np.testing.assert_array_equal(first["second_initial"][:, 1:], expected)
            np.testing.assert_array_equal(second["incoming_packet"], first["outgoing_packet"])
            np.testing.assert_array_equal(first["fresh_targets"], np.repeat(self.refs["prepared"][:, :1], 2, axis=1))
            self.assertFalse(np.array_equal(first["second_initial"][:, 1:], first["active_packet"]))

    def test_audit_detects_shock_schedule_continuity_and_diagnostic_corruption(self):
        mutations = [("selected_packet", "selected_original_packet"), ("active_packet", "exact_active_selection"),
            ("after_second_shock", "exact_second_shock"), ("second_initial", "second_write_uses_evolved_survivors"),
            ("outgoing_packet", "actual_held_pair_not_diagnostics"), ("fresh_targets", "exact_fresh_targets"),
            ("shock_factors", "exact_fixed_shock_factors")]
        for key, check in mutations:
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "round_01/endpoints.npz"
                data = arrays(path)
                data[key].flat[0] += .01
                np.savez_compressed(path, **data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]+"/round_01"][check])

    def test_audit_detects_seed_clock_and_counter_corruption(self):
        for kind, key in (("seed", "full_seeded_schedule"), ("outcome", "outcomes_recomputed"), ("count", "shock_counts")):
            with tempfile.TemporaryDirectory() as temp:
                case = self.case()
                folder, inputs, _ = self.fixture(temp, case)
                path = folder / "result.json"
                data = json.loads(path.read_text())
                if kind == "seed": data["design"]["seed"] += 1
                elif kind == "outcome": data["outcomes"]["successful_prefix_rounds"] = 0
                else: data["nonzero_shocks"] = 1
                write_json(path, data)
                self.assertFalse(self.audit(folder, inputs, case)[2][case["id"]][key])

    def full_panel_fixture(self, temp, stage, screen=None):
        run = Path(temp) / "runs" / ("reliability-"+stage+"-synthetic")
        run.mkdir(parents=True)
        inputs = self.inputs_fixture(run)
        records = []
        cfg = self.configs[stage]
        for case in cfg["cases"]:
            folder = run / case["id"]
            self.run_branch(folder, inputs, case, stage, mode="poolfails")
            result = json.loads((folder / "result.json").read_text())
            records.append(dict(id=case["id"], execution_pass=True, returncode=0, result=result))
            if case["profile"] == "none" and case["family"] != "pooled_rewritten_e_pair" and not (case["fine"] and case["family"] == "ordinary_m_pair"):
                spec = source_recipe(case)[0]
                stem = spec["kind"]+"_"+spec["name"]
                for n in ((1,) if spec["kind"] == "h1" else (1, 2)):
                    path = inputs / (stem+("_contacts.npz" if spec["kind"] == "h1" else f"_round_{n:02}.npz"))
                    saved = arrays(folder / f"round_{n:02}/endpoints.npz")
                    for key in ("selected_packet", "shock_factors", "after_second_shock"): saved.pop(key)
                    np.savez_compressed(path, **saved)
        # Both stages must freeze exactly the same H2/H1 inputs, not descendants.
        if screen:
            for path in (screen / "inputs").iterdir():
                (inputs / path.name).write_bytes(path.read_bytes())
        prior = {k: True for k in FLAGS}
        prior.update(ready_for_reliability_design=True, array_check_count=18466,
            array_checks={"synthetic": {"not_a_biological_result": True}})
        write_json(run / "predecessor_audit.json", prior)
        (run / "frozen").mkdir()
        for s, config in self.configs.items():
            write_json(run / f"frozen/reliability_{s}_v1.json", config)
        write_json(Path(temp) / "synthetic_execution.json", {"fixture_only": True})
        if screen:
            screen_audit = analyze(screen)
            gate = dict(run=str(screen), audit=screen_audit,
                config_sha256=file_hash(screen / "frozen/reliability_confirmation_v1.json"),
                screen_summary_sha256=file_hash(screen / "summary.json"))
            write_json(run / "screening_gate.json", gate)
            write_json(inputs / "screening_gate.json", gate)
        manifest = {p.name: dict(source=str(p), sha256=file_hash(p)) for p in inputs.iterdir()}
        summary = dict(all_execution_valid=True, config=cfg, revision=cfg["revision"], cases=records,
            inputs=manifest, frozen_hashes_sha256={p.name: file_hash(p) for p in (run / "frozen").iterdir()},
            hashes_sha256={"synthetic_execution.json": file_hash(Path(temp) / "synthetic_execution.json")},
            predecessor_audit_sha256=file_hash(run / "predecessor_audit.json"), elapsed_seconds=0.)
        write_json(run / "summary.json", summary)
        return run

    def test_full_screen_confirmation_negative_hypothesis_and_quality_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            screen = self.full_panel_fixture(temp, "screen")
            report = analyze(screen)
            self.assertTrue(all(report[k] for k in FLAGS))
            self.assertTrue(report["eligible_for_confirmation"])
            self.assertEqual(len(report["historical_controls"]), 17)
            self.assertEqual(len(report["fine_comparisons"]), 12)
            self.assertEqual(report["new_integrations"], 5016)
            self.assertEqual(report["fresh_recipients"], 912)
            self.assertEqual(report["scheduled_shocks"], 912)
            pooled = [b for b in report["branches"] if b["case"]["family"] == "pooled_rewritten_e_pair"]
            self.assertTrue(all(not b["outcomes"]["strict_renewal"] for b in pooled))
            confirmation = self.full_panel_fixture(temp, "confirmation", screen)
            final = analyze(confirmation)
            self.assertTrue(all(final[k] for k in FLAGS), final["confirmation_checks"])
            self.assertTrue(final["ready_for_benefit_design"])
            self.assertEqual(len(final["historical_controls"]), 5)
            self.assertEqual(len(final["fine_comparisons"]), 4)
            self.assertEqual(final["new_integrations"], 5148)
            self.assertEqual(final["fresh_recipients"], 936)
            self.assertTrue(all(final["confirmation_checks"].values()))
            # A valid changed fine outcome must block the gate, not fail array validity.
            case = self.case("protein_m_pair", "strong_s3", True)
            folder = screen / case["id"]
            folder.rename(screen / "saved_original_fine_branch")
            self.run_branch(folder, screen / "inputs", case, mode="pairfails")
            summary = json.loads((screen / "summary.json").read_text())
            next(row for row in summary["cases"] if row["id"] == case["id"])["result"] = json.loads((folder / "result.json").read_text())
            write_json(screen / "summary.json", summary)
            changed = analyze(screen)
            self.assertTrue(all(changed[k] for k in FLAGS))
            self.assertTrue(changed["historical_prefixes_pass"])
            self.assertFalse(changed["selected_fine_outcomes_and_labels_agree"])
            self.assertFalse(changed["eligible_for_confirmation"])
            # Historical corruption is independently detected, as are its hashes.
            path = screen / "inputs/h1_protein_pair_contacts.npz"
            data = arrays(path)
            data["contact_1"][7, 0] += .01
            np.savez_compressed(path, **data)
            changed = analyze(screen)
            self.assertFalse(changed["historical_prefixes_pass"])
            self.assertFalse(changed["input_hashes_valid"])

    def test_actual_H2_preflight_and_all_source_recipes_without_new_integration(self):
        if not (self.root / self.configs["screen"]["input_run"]).exists():
            self.skipTest("Audited H2 artifacts absent")
        with tempfile.TemporaryDirectory() as temp:
            manifest = freeze_inputs(Path(temp), self.configs["screen"])
            self.assertEqual(len(manifest), 64)
            inputs = Path(temp) / "inputs"
            indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
            for config in self.configs.values():
                for case in config["cases"]:
                    source, *_ = load_source(inputs, config, case, indices)
                    self.assertEqual(classify(source, indices).tolist(), [case["state"]]*source.shape[1])

    def test_native_shock_refresh_without_integration(self):
        if not (self.root / "upstream/bitsey/cancer_GJ_sims/zombie.py").exists():
            self.skipTest("Native checkout absent")
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            source = np.repeat(self.refs["prepared"][:, 1:2], 2, axis=1)
            changed = donor_shock(source, np.array([[.75, 1.25], [1.25, .75], [.9, 1.1]]))
            state = np.concatenate((self.refs["prepared"][:, :1], changed), axis=1)
            exp = Experiment(Path(temp), self.configs["screen"])
            exp.build(3, state, True)
            exp.refresh()
            np.testing.assert_array_equal(exp.sim.cc_cells[:8], state[:8])
            np.testing.assert_allclose(exp.sim.cc_cells, canonical_state(state), rtol=1e-12, atol=1e-14)


if __name__ == "__main__":
    unittest.main()

