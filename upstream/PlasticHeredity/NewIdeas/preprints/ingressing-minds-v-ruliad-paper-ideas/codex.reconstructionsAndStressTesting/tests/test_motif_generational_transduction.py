from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca.cli import build_parser
from plastic_ca.motif_generational_transduction import (
    CLAIM_GROUPS,
    DEFAULT_STAGE6G_ROOT,
    PROFILES,
    GenerationalTransductionContract,
    _best_parent_spec,
    _candidate_specs,
    _equivariant_transform,
    _frontend,
    _linear_transform,
    _materialize,
    _mixture_transform,
    _parent_generation_curve,
    _parent_integrity,
    _reconstruct_cohorts,
    _rff_transform,
    run_motif_generational_transduction,
)
from tests.test_motif_phenotype_bridge import ROOTS


def identity_transform(identifier: str, dimension: int = 16) -> dict[str, object]:
    weights = np.zeros((dimension, 16), dtype=np.float32)
    weights[: min(dimension, 16), : min(dimension, 16)] = np.eye(
        min(dimension, 16), dtype=np.float32
    )
    return {
        "transform_id": identifier,
        "kind": "linear",
        "input_mode": "feature",
        "target_space": "visible-bits",
        "input_mean": [0.0] * dimension,
        "input_scale": [1.0] * dimension,
        "weights": weights.tolist(),
        "bias": [0.0] * 16,
        "model_frozen": True,
        "training_pair_count": 2,
        "training_pair_ids_sha256": "a" * 64,
        "model_sha256": "b" * 64,
    }


class GenerationalTransductionIntegrityTests(unittest.TestCase):
    def test_parent_is_complete_and_all_exposed_checkpoints_are_frozen(self) -> None:
        result = _parent_integrity(DEFAULT_STAGE6G_ROOT)
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["parent_verdict"], "DECODABLE_NOT_TRANSDUCIBLE")
        self.assertEqual(result["screen_checkpoint_count"], 448)
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_parent_decline_is_reconstructed_from_checkpoints(self) -> None:
        curve = _parent_generation_curve(DEFAULT_STAGE6G_ROOT)["generation_curve"]
        self.assertAlmostEqual(curve["5"]["carrier_balanced_accuracy_mean"], 0.916015625)
        self.assertAlmostEqual(curve["8"]["carrier_balanced_accuracy_mean"], 0.513671875)
        self.assertGreater(curve["5"]["read_match_mean"], curve["8"]["read_match_mean"])

    def test_reference_cohorts_are_disjoint_and_reserve_stays_sealed(self) -> None:
        integrity = _parent_integrity(DEFAULT_STAGE6G_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            _, cohorts, _, _, _, _, _ = _reconstruct_cohorts(
                Path(directory),
                PROFILES["reference"],
                integrity,
                ROOTS,
                auto_final_audit=True,
            )
            self.assertEqual(
                {name: len(rows) for name, rows in cohorts.items()},
                {"training": 16, "screen": 16, "qualification": 16, "endurance": 8, "final": 0},
            )
            ids = [str(pair["pair_id"]) for rows in cohorts.values() for pair in rows]
            self.assertEqual(len(ids), len(set(ids)))
            state = pb._load_json(Path(directory) / "STAGE6H_COHORTS.json")
            self.assertTrue(state["final_audit_trajectories_not_loaded"])
            self.assertEqual(state["final_audit_trajectory_state"], "untouched")

    def test_worker_wall_and_final_authorization_caps_precede_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                run_motif_generational_transduction(root, profile_name="smoke", workers=5)
            with self.assertRaises(ValueError):
                run_motif_generational_transduction(root, profile_name="smoke", max_hours=8.01)
            with self.assertRaises(ValueError):
                run_motif_generational_transduction(root, profile_name="reference")


class GenerationalTransductionModelTests(unittest.TestCase):
    @staticmethod
    def _runtime_candidate(transform: dict[str, object]) -> dict[str, object]:
        return {
            "candidate_id": "planted-runtime",
            "rank": 16,
            "promotable": True,
            "writer_transform": transform,
        }

    @staticmethod
    def _decode(transform: dict[str, object], feature: np.ndarray) -> np.ndarray:
        proposal, metadata = pb._transform_writer_proposal(
            GenerationalTransductionModelTests._runtime_candidate(transform),
            feature.reshape(-1, 4, 4),
            feature.reshape(1, -1, 4, 4),
            np.zeros((len(feature), 4, 4), dtype=np.bool_),
            "intact",
            5,
            len(feature) // 2,
            GenerationalTransductionContract(),
        )
        if metadata["target_exposed"]:
            raise AssertionError("a promotable transform exposed its target")
        return pb.ar.texture_decode(proposal, 16).reshape(-1, 16)

    def test_planted_linear_and_random_feature_maps_recover_outputs(self) -> None:
        rng = np.random.default_rng(61)
        features = rng.normal(size=(512, 16)).astype(np.float32)
        targets = np.tanh(features @ rng.normal(size=(16, 16))).astype(np.float32)
        groups = np.asarray([f"pair-{index // 32}" for index in range(512)])

        linear = _linear_transform("planted-linear", features, targets, groups)
        linear_prediction = self._decode(linear, features)
        self.assertGreater(
            float(np.mean((linear_prediction >= 0.0) == (targets >= 0.0))), 0.90
        )

        nonlinear_targets = np.tanh(
            np.sin(features) @ rng.normal(size=(16, 16))
        ).astype(np.float32)
        rff = _rff_transform(
            "planted-rff", features, nonlinear_targets, groups, seed=9, hidden=192
        )
        rff_prediction = self._decode(rff, features)
        self.assertGreater(
            float(np.mean((rff_prediction >= 0.0) == (nonlinear_targets >= 0.0))),
            0.80,
        )

    def test_equivariant_and_observation_gated_models_are_runtime_local(self) -> None:
        rng = np.random.default_rng(71)
        features = rng.normal(size=(320, 16)).astype(np.float32)
        targets = features.copy()
        groups = np.asarray([f"pair-{index // 20}" for index in range(320)])
        equivariant = _equivariant_transform(
            "planted-equivariant", features, targets, groups
        )
        prediction = self._decode(equivariant, features)
        self.assertGreater(float(np.mean(np.sign(prediction) == np.sign(targets))), 0.95)

        generations = np.repeat(np.asarray([5, 6, 7, 9], dtype=np.int16), 80)
        dialect = features.copy()
        for index in range(4):
            dialect[index * 80 : (index + 1) * 80] += np.float32(index * 3.0)
        mixture = _mixture_transform(
            "planted-mixture", dialect, targets, groups, generations
        )
        self.assertFalse(mixture["runtime_generation_index"])
        mixed_prediction = self._decode(mixture, dialect)
        self.assertEqual(mixed_prediction.shape, targets.shape)
        self.assertTrue(np.all(np.isfinite(mixed_prediction)))

    def test_candidate_registry_has_all_four_claim_groups_and_compression(self) -> None:
        parent_id = _parent_generation_curve(DEFAULT_STAGE6G_ROOT)[
            "best_parent_candidate_id"
        ]
        base = _best_parent_spec(DEFAULT_STAGE6G_ROOT, parent_id)["frontend"]
        visible = {
            name: copy.deepcopy(identity_transform(f"visible-{name}"))
            for name in ("pooled", "dagger", "rff", "equivariant", "mixture")
        }
        somatic = {
            name: copy.deepcopy(identity_transform(f"somatic-{name}"))
            for name in (
                "multi-timescale-ema",
                "local-reservoir",
                "transition-eligibility",
            )
        }
        specs = _candidate_specs(base, visible, somatic)
        self.assertEqual(len(specs), 16)
        self.assertEqual(
            {group: sum(row["selection_group"] == group for row in specs) for group in CLAIM_GROUPS},
            {
                "label-free-full": 4,
                "assisted-full": 8,
                "label-free-compressed": 2,
                "assisted-compressed": 2,
            },
        )
        models = _materialize(specs, ROOTS["stage6br_root"])
        self.assertEqual(len(models), 16)
        ranks = sorted(
            int(row["rank"])
            for row in models
            if row["form_scope"].startswith("compressed")
        )
        self.assertEqual(ranks, [4, 4, 8, 8])
        self.assertTrue(all(not row.get("runtime_generation_index", False) for row in specs))

    def test_frontend_scale_is_consistent_with_registered_rank(self) -> None:
        source = {"kind": "calibrated-q4", "bits": 4, "scale": [0.25] * 16}
        for rank in (4, 8, 16):
            frontend = _frontend(source, f"rank-{rank}", rank=rank)
            self.assertEqual(frontend["rank"], rank)
            self.assertEqual(len(frontend["scale"]), rank)


class GenerationalTransductionCliTests(unittest.TestCase):
    def test_cli_accepts_detached_generational_stage(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "generational-transduction",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6h",
                "--stage6g-root",
                str(DEFAULT_STAGE6G_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "generational-transduction")
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)


if __name__ == "__main__":
    unittest.main()
