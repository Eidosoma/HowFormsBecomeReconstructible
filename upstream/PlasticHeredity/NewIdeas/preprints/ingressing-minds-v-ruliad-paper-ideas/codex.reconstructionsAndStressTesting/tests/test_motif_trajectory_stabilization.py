from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_acquisition_repair as ar
from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca.cli import build_parser
from plastic_ca.motif_trajectory_stabilization import (
    CLAIM_GROUPS,
    DEFAULT_STAGE6H_ROOT,
    MECHANISM_TIERS,
    PROFILES,
    TrajectoryStabilizationContract,
    _candidate_specs,
    _parent_integrity,
    _reconstruct_cohorts,
    _seal_registry,
    run_motif_trajectory_stabilization,
)
from tests.test_motif_phenotype_bridge import ROOTS


class TrajectoryStabilizationIntegrityTests(unittest.TestCase):
    def test_parent_and_unused_reserve_are_frozen(self) -> None:
        result = _parent_integrity(DEFAULT_STAGE6H_ROOT)
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["validation_checkpoint_count"], 576)
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_cohort_route_uses_32_exposed_then_two_fresh_eights(self) -> None:
        integrity = _parent_integrity(DEFAULT_STAGE6H_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            _, cohorts, profile, _, _ = _reconstruct_cohorts(
                Path(directory),
                PROFILES["reference"],
                integrity,
                ROOTS,
                auto_final_audit=True,
            )
            self.assertEqual(
                {key: len(value) for key, value in cohorts.items()},
                {
                    "development": 32,
                    "screen": 8,
                    "qualification": 8,
                    "endurance": 8,
                    "final": 0,
                },
            )
            self.assertEqual(profile.candidate_limit, 18)
            heldout = [
                str(pair["pair_id"])
                for key in ("screen", "qualification", "endurance")
                for pair in cohorts[key]
            ]
            self.assertEqual(len(heldout), len(set(heldout)))
            state = pb._load_json(Path(directory) / "STAGE6I_COHORTS.json")
            self.assertTrue(state["final_audit_trajectories_not_loaded"])

    def test_worker_wall_and_authorization_caps_precede_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                run_motif_trajectory_stabilization(root, profile_name="smoke", workers=5)
            with self.assertRaises(ValueError):
                run_motif_trajectory_stabilization(root, profile_name="smoke", max_hours=8.01)
            with self.assertRaises(ValueError):
                run_motif_trajectory_stabilization(root, profile_name="reference")


class TrajectoryStabilizationMechanismTests(unittest.TestCase):
    def test_registry_has_six_candidates_per_tier(self) -> None:
        specs = _candidate_specs(DEFAULT_STAGE6H_ROOT)
        self.assertEqual(len(specs), 18)
        self.assertEqual(
            {
                tier: sum(row["mechanism_tier"] == tier for row in specs)
                for tier in MECHANISM_TIERS
            },
            {"visible-only": 6, "transient-field": 6, "inherited-field": 6},
        )
        self.assertEqual(len(CLAIM_GROUPS), 6)
        self.assertTrue(all(not row.get("runtime_generation_index", False) for row in specs))

    def test_registry_materializes_18_promotable_models(self) -> None:
        specs = _candidate_specs(DEFAULT_STAGE6H_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seal_registry(root, specs, "d" * 64)
            models, _ = pb._load_models(root, ROOTS["stage6br_root"])
            self.assertEqual(len(models), 18)
            inherited = [row for row in models if row["mechanism"] == "inherited-field"]
            self.assertEqual(sorted(int(row["field_rank"]) for row in inherited), [4, 4, 8, 8, 16, 16])

    def test_encoded_field_roundtrip_uses_independent_noisy_channel(self) -> None:
        specs = _candidate_specs(DEFAULT_STAGE6H_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seal_registry(root, specs, "e" * 64)
            models, _ = pb._load_models(root, ROOTS["stage6br_root"])
            candidate = next(row for row in models if row["mechanism"] == "inherited-field" and row["field_rank"] == 8)
            field_candidate = pb._field_codec_candidate(candidate)
            rng = np.random.default_rng(6)
            raw = rng.uniform(-1.0, 1.0, size=(8, 8)).astype(np.float32)
            payload, _ = pb._quantize_frontend(raw, field_candidate)
            shares, active = pb._encode_carrier(
                payload,
                field_candidate,
                TrajectoryStabilizationContract(),
                "unit-pair",
                5,
                "unit-field",
            )
            copied, uncorrectable = pb._copy_carrier(
                shares,
                "unit-pair",
                5,
                4,
                TrajectoryStabilizationContract(),
                purpose="unit-field-copy",
                corruption=0.01,
            )
            restored, valid = pb._joint_payload(copied, active, field_candidate)
            self.assertTrue(np.all(valid))
            self.assertLess(uncorrectable, 0.10)
            self.assertLess(float(np.mean(np.abs(restored - payload))), 0.20)

    def test_orbit_score_is_phase_invariant_but_order_sensitive(self) -> None:
        rng = np.random.default_rng(17)
        target = np.where(rng.random((13, 6, 4, 4)) < 0.35, 1.0, -1.0).astype(np.float32)
        opposite = -target
        phase = list(np.roll(target, 4, axis=0))
        intact = pb._orbit_metrics(list(target), list(target), list(opposite), "intact", 1)
        shifted = pb._orbit_metrics(phase, list(target), list(opposite), "intact", 1)
        reversed_score = pb._orbit_metrics(list(target), list(target), list(opposite), "orbit_temporal_reverse", 1)
        shuffled = pb._orbit_metrics(list(target), list(target), list(opposite), "orbit_temporal_shuffle", 1)
        self.assertAlmostEqual(intact["margin_mean"], shifted["margin_mean"], places=6)
        self.assertGreater(intact["margin_mean"], reversed_score["margin_mean"] + 0.25)
        self.assertGreater(intact["margin_mean"], shuffled["margin_mean"] + 0.25)

    def test_visible_controller_never_receives_a_target(self) -> None:
        state = np.zeros((2, 8, 8), dtype=np.bool_)
        state[:, 3:5, 3:5] = True
        predicted = ~state
        result = pb._apply_visible_stabilizer(
            predicted,
            state,
            np.zeros_like(state, dtype=np.float64),
            1.0,
            "hysteresis",
        )
        self.assertTrue(np.array_equal(result, state))

    def test_real_inherited_lineage_resets_visible_state_and_copies_field(self) -> None:
        integrity = _parent_integrity(DEFAULT_STAGE6H_ROOT)
        specs = _candidate_specs(DEFAULT_STAGE6H_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage_root = root / "stage6i"
            frozen, cohorts, _, writer_contract, templates = _reconstruct_cohorts(
                stage_root,
                PROFILES["smoke"],
                integrity,
                ROOTS,
                auto_final_audit=True,
            )
            _seal_registry(stage_root, specs, "f" * 64)
            models, _ = pb._load_models(stage_root, ROOTS["stage6br_root"])
            candidate = next(
                row
                for row in models
                if row["candidate_id"] == "stage6i-inherited-local-latch-r08"
            )
            item = ar._make_items(
                cohorts["development"][:1],
                [candidate],
                ar._template_pairs(templates, "development")[:1],
                frozen["stage4"]["configuration"],
                phase="unit-lineage",
                replicates=1,
                generations=5,
                conditions=("intact",),
            )[0]
            row = pb._phenotype_pair_task(
                (
                    item,
                    [candidate],
                    writer_contract,
                    TrajectoryStabilizationContract(),
                    frozen["stage4"]["reference"],
                )
            )
            result = row["conditions"]["intact"]
            self.assertTrue(result["reset_asserted_before_every_generation"])
            self.assertTrue(result["inherited_field_crosses_visible_reset"])
            self.assertTrue(result["inherited_field_encoded_bottleneck"])
            self.assertIn("5", result["orbit_history"])
            self.assertIn("5", result["inherited_field_history"])
            self.assertGreater(
                result["inherited_field_history"]["5"]["entry_valid_fraction"],
                0.0,
            )


class TrajectoryStabilizationCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6i(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "trajectory-stabilization",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6i",
                "--stage6h-root",
                str(DEFAULT_STAGE6H_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "trajectory-stabilization")
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)


if __name__ == "__main__":
    unittest.main()
