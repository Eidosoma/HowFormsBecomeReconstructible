from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca.cli import build_parser
from plastic_ca.motif_polarity_closure import (
    DEFAULT_STAGE6O_ROOT,
    PolarityClosureContract,
    _best_bijection,
    _capacity_balance_verified,
    _compact_decoder,
    _corrected_motion_lineage,
    _load_parent_motion_model,
    _parent_integrity,
    _payload_bits,
    _payload_code,
    _wrap_crop_centered,
    run_motif_polarity_closure,
)
from plastic_ca import motif_counterfactual_carrier as co


class PolarityClosureIntegrityTests(unittest.TestCase):
    def test_frozen_stage6o_parent_and_reserve(self) -> None:
        result = _parent_integrity()
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["parent_design_digest"], co._load_json(
            DEFAULT_STAGE6O_ROOT / "DESIGN.json"
        )["design_digest"])
        self.assertTrue(result["procedural_trajectories_sealed"])
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_caps_precede_output_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "stage6p"
            with self.assertRaises(ValueError):
                run_motif_polarity_closure(root, profile_name="smoke", workers=5)
            self.assertFalse(root.exists())
            with self.assertRaises(ValueError):
                run_motif_polarity_closure(
                    root, profile_name="smoke", max_hours=8.01
                )
            self.assertFalse(root.exists())


class PolarityClosureMotionTests(unittest.TestCase):
    def test_capacity_constrained_rule_balance(self) -> None:
        available = {"a": 100, "b": 100, "c": 2, "d": 5, "e": 0}
        self.assertTrue(
            _capacity_balance_verified(
                {"a": 8, "b": 9, "c": 2, "d": 5, "e": 0}, available
            )
        )
        self.assertFalse(
            _capacity_balance_verified(
                {"a": 7, "b": 10, "c": 2, "d": 5, "e": 0}, available
            )
        )

    def test_wrap_crop_treats_toroidal_seam_as_adjacent(self) -> None:
        seam = np.zeros((32, 32), dtype=np.bool_)
        seam[15:18, (31, 0, 1)] = True
        centered = np.zeros((32, 32), dtype=np.bool_)
        centered[15:18, 15:18] = True
        seam_crop = _wrap_crop_centered(seam)
        centered_crop = _wrap_crop_centered(centered)
        self.assertTrue(np.array_equal(seam_crop, centered_crop))

    def test_bijective_calibration_recovers_known_permutation(self) -> None:
        permutation = np.asarray((3, 0, 6, 1, 7, 2, 5, 4), dtype=np.int8)
        raw = np.repeat(np.arange(8, dtype=np.int8), 3)
        target = permutation[raw]
        self.assertEqual(_best_bijection(raw, target), permutation.tolist())

    def test_redundant_polarity_payload_majority_repairs_one_vote(self) -> None:
        model = _load_parent_motion_model(co.DEFAULT_STAGE6N_ROOT)
        candidate = {
            "model": model,
            "threefold_polarity_bit": True,
        }
        bits = _payload_bits(candidate, 5, 3)
        self.assertLessEqual(len(bits), 8)
        bits[-1] ^= np.uint8(1)
        shape, orientation, diagnostics = _payload_code(candidate, bits)
        self.assertEqual(shape, 5)
        self.assertEqual(orientation, 3)
        self.assertEqual(diagnostics["polarity_majority"], 1)

    def test_opposite_is_seeded_once_not_reapplied(self) -> None:
        bank = co._load_json(
            co.DEFAULT_STAGE6M_ROOT / "stage6m/MOTION_BANK.json"
        )
        model = _load_parent_motion_model(co.DEFAULT_STAGE6N_ROOT)
        candidate = {
            "candidate_id": "test-stage6p-baseline",
            "model": model,
            "feature_mode": "legacy",
            "writer_kind": "ridge-head",
            "calibration_kind": "none",
            "endpoint": 48,
            "payload_bits": int(model["payload_bits"]),
        }
        result = _corrected_motion_lineage(
            candidate,
            bank["pairs"][0],
            "forward",
            "opposite_seed",
            generations=2,
            corruption=0.0,
        )
        self.assertEqual(
            result["generations"][0]["intervention"],
            "frozen-opposite-seed-once",
        )
        self.assertEqual(
            result["generations"][1]["intervention"], "learned-write"
        )

    def test_rescue_uses_frozen_parent_code(self) -> None:
        bank = co._load_json(
            co.DEFAULT_STAGE6M_ROOT / "stage6m/MOTION_BANK.json"
        )
        model = _load_parent_motion_model(co.DEFAULT_STAGE6N_ROOT)
        candidate = {
            "candidate_id": "test-stage6p-baseline",
            "model": model,
            "feature_mode": "legacy",
            "writer_kind": "ridge-head",
            "calibration_kind": "none",
            "endpoint": 48,
            "payload_bits": int(model["payload_bits"]),
        }
        result = _corrected_motion_lineage(
            candidate,
            bank["pairs"][0],
            "forward",
            "opposite_rescue",
            generations=3,
            corruption=0.0,
        )
        rescue = result["generations"][2]
        self.assertEqual(rescue["intervention"], "frozen-parent-opposite-rescue")
        self.assertEqual(
            rescue["written_shape_code"], rescue["frozen_parent_shape_code"]
        )
        self.assertEqual(
            rescue["written_orientation"],
            rescue["frozen_parent_opposite_orientation"],
        )


class PolarityClosureCompactTests(unittest.TestCase):
    def test_all_registered_compact_decoders_are_orthonormal(self) -> None:
        rng = np.random.default_rng(17)
        targets = rng.normal(size=(48, 32)).astype(np.float32)
        groups = np.asarray([f"p{index // 4}" for index in range(48)], dtype=str)
        design = rng.normal(size=(48, 9)).astype(np.float32)
        train = np.ones(48, dtype=np.bool_)
        for kind in (
            "pca",
            "paired-history-contrast-svd",
            "hybrid-pca8-contrast8",
            "supervised-reduced-rank-regression",
        ):
            decoder, mean = _compact_decoder(
                kind, targets, groups, design, train, 16
            )
            self.assertEqual(decoder.shape, (16, 32))
            self.assertEqual(mean.shape, (32,))
            self.assertTrue(
                np.allclose(decoder @ decoder.T, np.eye(16), atol=1e-5)
            )


class PolarityClosureCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6p(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "polarity-closure",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6p",
                "--stage6o-root",
                str(DEFAULT_STAGE6O_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "polarity-closure")
        self.assertEqual(args.stage6o_root, DEFAULT_STAGE6O_ROOT)
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)

    def test_contract_registers_absolute_commands_and_causal_bases(self) -> None:
        contract = PolarityClosureContract().to_dict()
        self.assertEqual(
            contract["motion_semantics"],
            "absolute-seed-once-then-visible-renewal",
        )
        self.assertEqual(contract["rescue_target"], "frozen-parental-code")
        self.assertEqual(len(contract["compact_basis_families"]), 4)


if __name__ == "__main__":
    unittest.main()
