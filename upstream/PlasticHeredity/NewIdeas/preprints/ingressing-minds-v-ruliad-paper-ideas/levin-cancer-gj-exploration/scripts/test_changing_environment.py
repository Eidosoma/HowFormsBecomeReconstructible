"""Synthetic H4 plumbing tests. No native integrations or result-dependent tuning."""

import copy
from contextlib import redirect_stdout
import io
import inspect
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

import test_reliability as fixtures
import analyze_changing_environment as audit
import benefit_dynamics as dynamics
import benefit_provenance as provenance
from analyze_commitment_components import FLAGS, canonical_state
from analyze_group_transfer import arrays
from changing_environment_design import (FIXED, POLICIES, REGIMES, SEEDS, case_spec, fixed_cases,
    validate_config, schedule, source_case, handover_plan)
from memory_metrics import classify
from run_changing_environment import branch_worker, trajectory
from run_memory_probe import array_hash, write_json
from run_onward_transfer import file_hash


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.old = fixtures.ReliabilityTests()
        self.old.setUp()
        self.refs, self.indices = self.old.refs, self.old.indices
        self.config = json.loads((self.old.root / "configs/changing_environment_v1.json").read_text())

    def fake(self, calls):
        refs, indices = self.refs["prepared"], self.indices

        class Fake:
            def __init__(self, folder, config, fine=False):
                self.folder, self.config, self.fine = folder, config, fine
                self.indices, self.reg, self.audits = indices, [5, 6, 7], []

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
        return Fake

    def run_case(self, folder, inputs, case):
        folder.mkdir()
        calls = []
        fake = self.fake(calls)
        with patch("benefit_dynamics.Experiment", fake), patch("reliability_relay.Experiment", fake), redirect_stdout(io.StringIO()):
            self.assertEqual(branch_worker(folder, self.config, case, inputs), 0)
        return calls

    def test_exact_grid_independent_schedules_and_config_rejection(self):
        validate_config(self.config)
        self.assertEqual(self.config, dict(FIXED, cases=fixed_cases()))
        self.assertEqual(fixed_cases(), audit.expected_cases())
        self.assertEqual(len({c["id"] for c in fixed_cases()}), 76)
        for case in fixed_cases():
            if case["kind"] == "main":
                self.assertEqual(schedule(case), audit.expected_schedule(case))
                for epoch in range(1, 7):
                    self.assertEqual(handover_plan(epoch, case["parent_enabled"]), audit.expected_handover(epoch, case["parent_enabled"]))
        for k, v in (("epochs", 8), ("workers", 3), ("total_budget_seconds", 50000), ("cue_horizon", 10), ("costs", [0, 1])):
            bad = copy.deepcopy(self.config)
            bad[k] = v
            with self.assertRaises(ValueError): validate_config(bad)

    def test_resource_opportunities_are_common_across_policy_world_and_polarity(self):
        for seed in SEEDS:
            plans = [schedule(case_spec(p, r, seed, a)) for p in POLICIES for r in REGIMES for a in ("E", "M")]
            self.assertTrue(all(p["availability_order"] == plans[0]["availability_order"] for p in plans))
            self.assertTrue(all(len(p["available_epochs"]) == 4 and 1 in p["available_epochs"] for p in plans))
            for r in REGIMES:
                e, m = [schedule(case_spec("rewritable", r, seed, a)) for a in ("E", "M")]
                self.assertTrue(all(x != y for x, y in zip(e["hidden_truth"], m["hidden_truth"])))
                self.assertEqual(len(e["corrupted_epochs"]), 2 if r == "misleading" else 0)
                self.assertNotIn(1, e["corrupted_epochs"])

    def test_main_fine_sources_are_identical_and_benchmark_sources_refined(self):
        for anchor in ("E", "M"):
            a = case_spec("rewritable", "misleading", SEEDS[1], anchor)
            b = case_spec("rewritable", "misleading", SEEDS[1], anchor, True)
            self.assertFalse(source_case(a)["fine"])
            self.assertFalse(source_case(b)["fine"])
        self.assertTrue(source_case(dict(id="bench", kind="benchmark", state="E", fine=True))["fine"])

    def test_each_policy_full_history_audits_and_descendants_not_reset(self):
        for p in POLICIES:
            with self.subTest(policy=p), tempfile.TemporaryDirectory() as temp:
                inputs = self.old.inputs_fixture(temp)
                folder = Path(temp) / "branch"
                case = case_spec(p, "misleading", SEEDS[0], "M")
                calls = self.run_case(folder, inputs, case)
                branch, _, checks, phases = audit.audit_branch(folder, inputs, self.config, case, self.indices, self.refs)
                self.assertTrue(all(all(c.values()) for c in checks.values()), {g: [k for k, v in c.items() if not v] for g, c in checks.items() if not all(c.values())})
                self.assertEqual(len(calls), 102)
                self.assertEqual(len(phases), 102)
                self.assertEqual(branch["fresh_recipients"], 12)
                self.assertEqual(branch["cue_cells_supplied"], 40)
                self.assertEqual(sum(c[3] and c[2] == 3 for c in calls), 12 if POLICIES[p][0] else 0)
                self.assertEqual(sum(c[3] and c[2] == 6 for c in calls), 8 if POLICIES[p][1] else 0)
                for epoch in range(1, 7):
                    inherited = arrays(folder / f"epoch_{epoch:02}_inheritance/endpoints.npz")
                    exposed = arrays(folder / f"epoch_{epoch:02}_cue/endpoints.npz")
                    np.testing.assert_array_equal(inherited["outgoing_packet"], exposed["incoming_packet"])
                    np.testing.assert_array_equal(inherited["fresh_targets"], self.refs["prepared"][:, [0, 1] if epoch % 2 else [1, 0]])
                    if epoch < 6:
                        after = arrays(folder / f"epoch_{epoch+1:02}_inheritance/endpoints.npz")
                        np.testing.assert_array_equal(exposed["outgoing_packet"], after["incoming_packet"])

    def test_hidden_truth_cannot_steer_trajectories(self):
        self.assertNotIn("truth", inspect.signature(trajectory).parameters)
        self.assertNotIn("truth", inspect.signature(dynamics.cue_worker).parameters)
        with tempfile.TemporaryDirectory() as temp:
            inputs = self.old.inputs_fixture(temp)
            case = case_spec("rewritable", "misleading", SEEDS[1], "E")
            a, b = Path(temp) / "a", Path(temp) / "b"
            self.run_case(a, inputs, case)
            changed = schedule(case)
            changed["hidden_truth"] = [{"E": "M", "M": "E"}[x] for x in changed["hidden_truth"]]
            with patch("run_changing_environment.schedule", return_value=changed):
                self.run_case(b, inputs, case)
            paths = list(a.rglob("*.npz"))
            self.assertGreater(len(paths), 100)
            for path in paths:
                aa, bb = arrays(path), arrays(b / path.relative_to(a))
                self.assertEqual(set(aa), set(bb))
                self.assertTrue(all(np.array_equal(v, bb[k]) for k, v in aa.items()))

    def test_scoring_bootstrap_costs_and_coarse_correction(self):
        first = audit.score_epoch(1, "M", None, "M", ["MM"]*4, True, True)
        switched = audit.score_epoch(2, "E", "M", "M", ["MM", "EE", "EM", "EE"], True, True)
        self.assertEqual(switched["checkpoint_match_fractions"], [0, 1, .5, 1])
        self.assertEqual(switched["earliest_sustained_correct_checkpoint"], 42100)
        self.assertTrue(switched["misleading"])
        missing = audit.score_epoch(3, "E", "E", None, ["XX"]*4, True, True)
        self.assertIsNone(missing["earliest_sustained_correct_checkpoint"])
        out = audit.summarize_scores([first, switched, missing])
        self.assertEqual(out["subsets"]["all_scored"]["final_match"], .5)
        self.assertEqual(out["all_six_final_match"], 2/3)
        self.assertAlmostEqual(out["utility_sensitivity"][-1]["value"], .05)
        self.assertEqual(out["mean_normalized_cue_contact"], .5)

    def test_mutated_cue_or_packet_is_caught(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs = self.old.inputs_fixture(temp)
            case = case_spec("reactive", "rapid", SEEDS[0], "M")
            folder = Path(temp) / "branch"
            self.run_case(folder, inputs, case)
            path = folder / "epoch_02_cue/endpoints.npz"
            raw = arrays(path)
            raw["incoming_packet"][0, 0] += 1
            np.savez_compressed(path, **raw)
            _, _, checks, _ = audit.audit_branch(folder, inputs, self.config, case, self.indices, self.refs)
            self.assertFalse(checks["epoch_2/cue"]["exact_incoming"])

    def panel_fixture(self, temp):
        root = Path(temp)
        run = root / "runs/changing-environment-synthetic"
        run.mkdir(parents=True)
        inputs = self.old.inputs_fixture(run)
        for name in ("screening_gate.json", "h3_summary", "h3_audit", "h3_recovery_manifest"):
            write_json(inputs / name, dict(synthetic=True))
        records = []
        for case in self.config["cases"]:
            folder = run / case["id"]
            self.run_case(folder, inputs, case)
            records.append(dict(id=case["id"], execution_pass=True, returncode=0, result=audit.read(folder / "result.json")))
            if case["kind"] == "benchmark":
                suffix = "_fine" if case["fine"] else ""
                (inputs / f"benchmark_{case['state']}{suffix}.npz").write_bytes((folder / "round_01/endpoints.npz").read_bytes())
        manifest = {p.name: dict(source=str(p), sha256=file_hash(p)) for p in inputs.iterdir()}
        self.assertEqual(len(manifest), 72)
        write_json(inputs / "manifest.json", manifest)
        old = dict.fromkeys(FLAGS, True)
        old.update(quality_gate=True, ready_for_benefit_design=True, array_check_count=79113, array_checks={"synthetic": {"fixture": True}})
        write_json(run / "predecessor_audit.json", dict(h3_audit=old, recovery_provenance_pass=True,
            original_artifacts_unchanged=True, historical_audit_not_rewritten=True, stored_audit_sha256=file_hash(inputs / "h3_audit")))
        (run / "frozen").mkdir()
        write_json(run / "summary.json", dict(all_execution_valid=True, config=self.config, cases=records,
            inputs=manifest, frozen_hashes_sha256={}, hashes_sha256={}, revision=self.config["revision"],
            predecessor_audit_sha256=file_hash(run / "predecessor_audit.json"), elapsed_seconds=1))
        return run

    def test_entire_panel_counts_contrasts_and_quality_do_not_require_a_PH_win(self):
        with tempfile.TemporaryDirectory() as temp:
            run = self.panel_fixture(temp)
            report = audit.analyze(run)
            self.assertTrue(all(report[k] for k in FLAGS), {g: [k for k, v in c.items() if not v] for g, c in report["array_checks"].items() if not all(c.values())})
            self.assertTrue(report["quality_gate"])
            self.assertEqual(report["new_integrations"], 7388)
            self.assertEqual(len(report["paired_contrasts"]), 16)
            self.assertEqual(len(report["fine_comparisons"]), 8)
            self.assertTrue(any(g["contrasts"]["all_scored"]["rewritable_minus_reactive"] <= 0 for g in report["paired_contrasts"]))
            # A reproducibility failure is separate from ordinary negative utility.
            target = run / "benchmark__M/round_01/endpoints.npz"
            saved = arrays(target)
            saved["incoming_packet"][0, 0] += .2
            np.savez_compressed(target, **saved)
            bad = audit.analyze(run)
            self.assertFalse(bad["quality_gate"])
            self.assertFalse(bad["historical_benchmarks_pass"])

    def test_read_only_preflight_never_calls_saving_recovery_auditor(self):
        source = inspect.getsource(provenance.audit_predecessor)
        self.assertNotIn("audit_recovery(", source)
        self.assertNotIn("write_json(", source)
        self.assertNotIn("write_status(", source)
        self.assertIn("audit = analyze(previous)", source)


if __name__ == "__main__":
    unittest.main()
