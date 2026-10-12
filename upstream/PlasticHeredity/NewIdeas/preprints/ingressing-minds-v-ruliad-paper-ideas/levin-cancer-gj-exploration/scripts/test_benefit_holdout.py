"""Synthetic H4b coverage; never integrates native biology during software tests."""

import copy
from contextlib import redirect_stdout
import inspect
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import analyze_benefit_holdout as audit
import benefit_holdout_design as design
import benefit_holdout_provenance as provenance
import test_changing_environment as fixtures
from analyze_commitment_components import FLAGS
from analyze_group_transfer import arrays
from changing_environment_design import source_case
from recover_reliability import snapshot
from run_benefit_holdout import branch_worker
from run_memory_probe import write_json
from run_onward_transfer import file_hash


class HoldoutTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EnvironmentTests()
        self.fixture.setUp()
        self.refs, self.indices = self.fixture.refs, self.fixture.indices
        self.config = json.loads((self.fixture.old.root / "configs/benefit_holdout_v1.json").read_text())

    def run_case(self, folder, inputs, case):
        folder.mkdir()
        calls = []
        with patch("benefit_dynamics.Experiment", self.fixture.fake(calls)), redirect_stdout(io.StringIO()):
            self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
        return calls

    def test_full_grid_independent_schedules_bounds_counts_and_heldout_seeds(self):
        design.validate_config(self.config)
        self.assertEqual(self.config, audit.expected_config())
        self.assertEqual(design.fixed_cases(), audit.expected_cases())
        self.assertEqual(len({c["id"] for c in self.config["cases"]}), 144)
        self.assertEqual(design.protocol_counts(), dict(cases=144, integrations=28016, fresh_recipients=3296, cue_cells=8720))
        self.assertFalse(set(design.SEEDS) & set(self.fixture.config["seeds"]))
        for c in self.config["cases"]:
            plan = design.schedule(c)
            self.assertEqual(plan, audit.expected_schedule(c))
            self.assertEqual(len(plan["visible_cues"]), 2 if c["kind"] == "prefix" else 12)
            self.assertEqual(plan["hidden_truth"][0], c["state"])
            self.assertEqual(plan["visible_cues"][0], c["state"])
        for key, value in (("epochs", 16), ("prefix_epochs", 1), ("workers", 3),
                ("total_budget_seconds", 90000), ("worker_timeout_seconds", 7200), ("cue_count", 6)):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError): design.validate_config(cfg)

    def test_shared_randomness_nested_scarcity_truth_and_error_noninterference(self):
        for seed in design.SEEDS:
            plans = {p: design.schedule(design.case_spec("rewritable", p, seed, "M")) for p in design.PROFILES}
            base = plans["slow_reliable"]
            self.assertTrue(all(p["raw_uniform"] == base["raw_uniform"] for p in plans.values()))
            for p in ("slow_sparse", "slow_noisy"):
                self.assertEqual(plans[p]["hidden_truth"], base["hidden_truth"])
            for low, normal in zip(plans["slow_sparse"]["visible_cues"], base["visible_cues"]):
                self.assertTrue(low is None or low == normal)
            for noisy, normal in zip(plans["slow_noisy"]["visible_cues"], base["visible_cues"]):
                self.assertEqual(noisy is None, normal is None)
            for policy in design.POLICIES:
                self.assertEqual(design.schedule(design.case_spec(policy, "slow_noisy", seed, "M")), plans["slow_noisy"])
            flipped = design.schedule(design.case_spec("rewritable", "slow_reliable", seed, "E"))
            self.assertTrue(all(x != y for x, y in zip(flipped["hidden_truth"], base["hidden_truth"])))

    def test_no_resampling_even_with_no_events(self):
        case = design.case_spec("rewritable", "slow_sparse", design.SEEDS[0], "M")
        with patch.object(design.np.random, "Generator") as generator:
            generator.return_value.random.return_value = np.full((11, 3), .999)
            result = design.schedule(case)
            generator.return_value.random.assert_called_once_with((11, 3))
        self.assertEqual(result["hidden_truth"], ["M"]*12)
        self.assertEqual(result["visible_cues"], ["M"]+[None]*11)
        self.assertFalse(result["resampling"])

    def test_twelve_epochs_all_policies_audit_and_forward_real_descendants(self):
        for policy in design.POLICIES:
            with tempfile.TemporaryDirectory() as temp:
                inputs = self.fixture.old.inputs_fixture(temp)
                folder = Path(temp) / "branch"
                case = design.case_spec(policy, "slow_noisy", design.SEEDS[-1], "E")
                calls = self.run_case(folder, inputs, case)
                b, _, checks, phases = audit.audit_branch(folder, inputs, self.config, case, self.indices, self.refs)
                self.assertTrue(all(all(c.values()) for c in checks.values()), {g: [k for k,v in c.items() if not v] for g,c in checks.items() if not all(c.values())})
                self.assertEqual(len(calls), 204)
                self.assertEqual(len(phases), 204)
                self.assertEqual(b["fresh_recipients"], 24)
                self.assertEqual(b["outcomes"]["subsets"]["all_scored"]["epochs"], 11)
                self.assertEqual(len(b["outcomes"]["utility_sensitivity"]), 64)
                for epoch in range(1, 12):
                    old = arrays(folder / f"epoch_{epoch:02}_cue/endpoints.npz")
                    new = arrays(folder / f"epoch_{epoch+1:02}_inheritance/endpoints.npz")
                    np.testing.assert_array_equal(old["outgoing_packet"], new["incoming_packet"])

    def test_hidden_truth_changes_do_not_change_arrays(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs = self.fixture.old.inputs_fixture(temp)
            case = design.case_spec("rewritable", "fast_reliable", design.SEEDS[0], "M")
            a, b = Path(temp) / "a", Path(temp) / "b"
            self.run_case(a, inputs, case)
            altered = design.schedule(case)
            altered["hidden_truth"] = ["E"]*12
            altered["probabilities"] = dict(flip=1, available=0, incorrect=1)
            with patch("run_benefit_holdout.schedule", return_value=altered):
                self.run_case(b, inputs, case)
            for path in a.rglob("*.npz"):
                left, right = arrays(path), arrays(b / path.relative_to(a))
                self.assertEqual(set(left), set(right))
                self.assertTrue(all(np.array_equal(v, right[k]) for k, v in left.items()))

    def test_fine_sources_keep_identical_old_history(self):
        for c in self.config["cases"]:
            self.assertFalse(source_case(c)["fine"])
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]), 8)

    def test_binary_reference_has_no_truth_input_and_tracks_last_visible_hint(self):
        case = design.case_spec("rewritable", "slow_noisy", design.SEEDS[0], "M")
        cues = ["M", None, "E", None]
        self.assertNotIn("truth", inspect.signature(audit.binary_reference).parameters)
        self.assertEqual(audit.binary_reference(case, cues), [
            ["MM"]*4, ["MM"]*4, ["MM", "EE", "EE", "EE"], ["EE"]*4])
        reactive = dict(case, parent_enabled=False)
        self.assertEqual(audit.binary_reference(reactive, cues)[1], ["ME"]*4)

    def test_zero_cues_empty_subsets_and_complete_cost_grid(self):
        rows = [audit.score_epoch(i, "M", "M" if i > 1 else None, "M" if i == 1 else None,
            ["MM"]*4, True, True) for i in range(1, 13)]
        result = audit.summarize_scores(rows)
        self.assertIsNone(result["subsets"]["misleading"]["final_match"])
        self.assertEqual(result["mean_normalized_cue_contact"], 0)
        self.assertEqual(result["late_epochs_final_match"], 1)
        self.assertEqual(len(result["utility_sensitivity"]), 64)
        self.assertAlmostEqual(result["utility_sensitivity"][-1]["value"], .7)
        self.assertAlmostEqual(result["all_epochs_utility_sensitivity"][-1]["value"], .675)

    def test_break_even_arithmetic_keeps_negative_and_zero_cue_cases(self):
        branches = []
        for c in design.fixed_cases():
            if c["kind"] != "main" or c["fine"]:
                continue
            # Synthetic scores deliberately make inheritance worse than reactive.
            value = dict(rewritable=.6, fixed=.5, reactive=.8, neither=.5)[c["policy"]]
            rows = [audit.score_epoch(i, "M", "M", None, ["MM"]*4, c["parent_enabled"], c["cue_enabled"]) for i in range(1, 13)]
            for row in rows:
                row["final_match"] = value
            branches.append(dict(case=c, outcomes=audit.summarize_scores(rows)))
        for r in audit.paired_contrasts(branches):
            self.assertAlmostEqual(r["break_even"]["parent_cost_vs_reactive"], -.2)
            self.assertFalse(r["break_even"]["nonnegative_parent_cost_can_strictly_win"])
            self.assertIsNone(r["break_even"]["cue_cost_vs_fixed"])
            self.assertEqual(len(r["cost_sensitivity"]), 64)
            self.assertIn("reactive", r["cost_sensitivity"][-1]["best_policies"])

    def panel_fixture(self, temp):
        root = Path(temp)
        run = root / "runs/benefit-holdout-synthetic"
        run.mkdir(parents=True)
        inputs = self.fixture.old.inputs_fixture(run)
        for name in ("screening_gate.json", "h3_summary", "h3_audit", "h3_recovery_manifest"):
            write_json(inputs / name, dict(synthetic=True))
        for a in ("M", "E"):
            for f in ("", "_fine"):
                np.savez_compressed(inputs / f"benchmark_{a}{f}.npz", unused=np.zeros(1))
        write_json(inputs / "h4_summary.json", dict(config=dict(seeds=[2026090801, 2026090811])))
        old = dict.fromkeys(FLAGS, True)
        old.update(quality_gate=True, array_check_count=112544, array_checks={"synthetic": {"fixture": True}})
        write_json(inputs / "h4_audit.json", old)
        previous = root / self.config["input_run"]
        previous.mkdir()
        write_json(previous / "fixture.json", dict(synthetic=True))
        job = root / "runs/jobs/h4-fixture"
        job.mkdir(parents=True)
        write_json(job / "status.json", dict(phase="complete"))
        prior = dict(run=str(previous), job=str(job), h4_audit=old, original_run_sha256=snapshot(previous),
            original_job_sha256=snapshot(job), historical_audit_not_rewritten=True, original_artifacts_unchanged=True,
            stored_audit_sha256=file_hash(inputs / "h4_audit.json"))
        write_json(run / "predecessor_audit.json", prior)
        (run / "frozen").mkdir()
        summary = dict(config=self.config, cases=[], all_execution_valid=False, inputs={},
            frozen_hashes_sha256={}, hashes_sha256={}, revision=self.config["revision"], elapsed_seconds=1,
            predecessor_audit_sha256=file_hash(run / "predecessor_audit.json"))
        for case in self.config["cases"]:
            folder = run / case["id"]
            self.run_case(folder, inputs, case)
            record = audit.read(folder / "result.json")
            summary["cases"].append(dict(id=case["id"], execution_pass=True, returncode=0, result=record))
            if case["kind"] == "prefix":
                legacy = copy.deepcopy(record)
                legacy["case"]["id"] = case["legacy_case_id"]
                write_json(inputs / (case["id"]+"_legacy_result.json"), legacy)
                for epoch in (1, 2):
                    for phase in ("inheritance", "cue"):
                        (inputs / (case["id"]+f"_epoch_{epoch:02}_{phase}.npz")).write_bytes((folder / f"epoch_{epoch:02}_{phase}/endpoints.npz").read_bytes())
            if len(summary["cases"]) == 8:
                write_json(run / "summary.json", summary)
                gate = audit.prefix_gate(run, self.config)
                self.assertTrue(gate["quality_gate"])
                write_json(run / "prefix_gate.json", gate)
                summary.update(prefix_gate=gate, prefix_gate_sha256=file_hash(run / "prefix_gate.json"))
        manifest = {p.name: dict(source=str(p), sha256=file_hash(p)) for p in inputs.iterdir()}
        self.assertEqual(len(manifest), 114)
        write_json(inputs / "manifest.json", manifest)
        summary.update(inputs=manifest, all_execution_valid=True)
        write_json(run / "summary.json", summary)
        return run

    def test_complete_panel_all_counts_gates_and_binary_reference_not_required(self):
        with tempfile.TemporaryDirectory() as temp:
            run = self.panel_fixture(temp)
            # A wrong cheap reference must not make scientifically valid cell data fail.
            def wrong_reference(case, cues):
                return [["XX"]*4 for _ in cues]
            with patch.object(audit, "binary_reference", wrong_reference):
                report = audit.analyze(run)
            self.assertTrue(all(report[k] for k in FLAGS), {g: [k for k,v in c.items() if not v] for g,c in report["array_checks"].items() if not all(c.values())})
            self.assertTrue(report["quality_gate"])
            self.assertEqual(report["new_integrations"], 28016)
            self.assertEqual(report["fresh_recipients"], 3296)
            self.assertEqual(report["cue_cells_supplied"], 8720)
            self.assertEqual(len(report["paired_contrasts"]), 32)
            self.assertEqual(len(report["fine_comparisons"]), 8)
            self.assertTrue(all(not b["binary_reference"]["all_checkpoints_agree"] for b in report["branches"]))
            target = run / "prefix__rewritable__M/epoch_01_cue/endpoints.npz"
            values = arrays(target)
            values["outgoing_packet"][0, 0] += 1
            np.savez_compressed(target, **values)
            self.assertFalse(audit.prefix_gate(run, self.config)["quality_gate"])

    def test_read_only_predecessor_gate_contains_no_save_operation(self):
        source = inspect.getsource(provenance.audit_predecessor)
        for operation in ("write_json(", "write_status(", "write_text("):
            self.assertNotIn(operation, source)
        self.assertIn("report = analyze(previous)", source)


if __name__ == "__main__":
    unittest.main()
