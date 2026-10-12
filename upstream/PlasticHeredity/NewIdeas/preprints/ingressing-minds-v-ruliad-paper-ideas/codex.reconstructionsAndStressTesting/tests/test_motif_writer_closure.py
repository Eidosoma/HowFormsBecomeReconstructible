from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca.cli import build_parser
from plastic_ca.life import named_patterns
from plastic_ca.life_family import parse_life_rule
from plastic_ca.motif_writer_closure import (
    DEFAULT_STAGE6H_ROOT,
    DEFAULT_STAGE6I_ROOT,
    DEFAULT_STAGE6J_ROOT,
    PROFILES,
    WriterClosureContract,
    _board_to_array,
    _closure_candidates,
    _detect_mover,
    _direction_paired_metric,
    _fit_one_writer,
    _known_anchor_pairs,
    _oracle_candidates,
    _pair_blocked_folds,
    _parent_integrity,
    _ridge_fit,
    _writer_configs,
    run_motif_writer_closure,
)


class WriterClosureIntegrityTests(unittest.TestCase):
    def test_parent_has_48_exposed_8_heldout_and_62_sealed(self) -> None:
        result = _parent_integrity(
            DEFAULT_STAGE6J_ROOT, DEFAULT_STAGE6I_ROOT, DEFAULT_STAGE6H_ROOT
        )
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["exposed_pair_count"], 48)
        self.assertEqual(result["untouched_endurance_pair_count"], 8)
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_caps_are_checked_before_campaign_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                run_motif_writer_closure(root, profile_name="smoke", workers=5)
            with self.assertRaises(ValueError):
                run_motif_writer_closure(root, profile_name="smoke", max_hours=8.01)


class WriterClosureModelTests(unittest.TestCase):
    def test_factorial_has_exactly_24_cells(self) -> None:
        configs = _writer_configs()
        self.assertEqual(len(configs), 24)
        self.assertEqual(len({row["config_id"] for row in configs}), 24)
        self.assertEqual(
            {row["kind"] for row in configs},
            {"equivariant-ridge", "rff", "local-reservoir"},
        )

    def test_runtime_writer_interface_has_no_parent_or_label(self) -> None:
        parameters = inspect.signature(pb._adaptive_handoff_update).parameters
        self.assertNotIn("parent_field", parameters)
        self.assertNotIn("target", parameters)
        self.assertNotIn("environment", parameters)
        self.assertNotIn("pair_id", parameters)
        self.assertNotIn("generation", parameters)

    def test_local_features_and_frozen_prediction(self) -> None:
        rng = np.random.default_rng(6)
        history = [rng.random((3, 16, 16)) < 0.35 for _ in range(8)]
        centers = np.asarray([[5, 7], [8, 8], [12, 3]], dtype=np.int16)
        features, orientation = pb._closure_local_features(
            history, centers, 2, 8, True
        )
        self.assertEqual(features.shape, (3, 101))
        self.assertEqual(orientation.shape, (3,))
        model = {
            "kind": "equivariant-ridge",
            "radius": 2,
            "window": 8,
            "canonicalize": True,
            "input_mean": np.zeros(101).tolist(),
            "input_scale": np.ones(101).tolist(),
            "weights": np.zeros((101, 32)).tolist(),
            "bias": np.linspace(-1.0, 1.0, 32).tolist(),
            "model_frozen": True,
            "runtime_target_labels": False,
        }
        predicted = pb._closure_model_predict(history, centers, model)
        self.assertEqual(predicted.shape, (3, 2, 4, 4))
        self.assertTrue(np.all(np.isfinite(predicted)))

    def test_pair_blocked_folds_never_split_a_pair(self) -> None:
        groups = np.asarray(
            [pair for pair in ("a", "b", "c", "d", "e", "f", "g", "h") for _ in range(5)]
        )
        folds = _pair_blocked_folds(groups)
        self.assertEqual(set(folds.tolist()), set(range(6)))
        for pair in set(groups.tolist()):
            self.assertEqual(len(set(folds[groups == pair].tolist())), 1)

    def test_ridge_recovers_a_planted_map(self) -> None:
        rng = np.random.default_rng(61)
        x = rng.normal(size=(400, 12)).astype(np.float32)
        planted = rng.normal(size=(12, 5)).astype(np.float32)
        planted_bias = rng.normal(size=5).astype(np.float32)
        y = x @ planted + planted_bias
        weights, bias = _ridge_fit(x, y, 1e-6)
        prediction = x @ weights + bias
        self.assertLess(float(np.mean((prediction - y) ** 2)), 1e-8)

    def test_oracles_are_never_promotable(self) -> None:
        source = {
            "candidate_id": "source",
            "field_rank": 16,
            "field_channels": 2,
        }
        rows = _oracle_candidates(source)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(not row["promotable"] for row in rows))
        self.assertTrue(all(row["runtime_target_labels"] for row in rows))


class WriterClosureMoverTests(unittest.TestCase):
    def test_named_glider_and_lwss_are_exact_movers(self) -> None:
        anchors = _known_anchor_pairs()
        self.assertEqual(len(anchors), 8)
        self.assertEqual({row["pair_id"].split("-")[1] for row in anchors}, {"glider", "lwss"})
        for row in anchors:
            self.assertLessEqual(row["forward"]["period"], 16)
            self.assertNotEqual(tuple(row["forward"]["displacement_yx"]), (0, 0))

    def test_still_life_is_not_a_mover(self) -> None:
        conway = parse_life_rule("B3/S23")
        block = _board_to_array(named_patterns(32, 32)["block_descriptive"])
        from plastic_ca.motif_writer_closure import _simulate_history

        self.assertIsNone(_detect_mover(_simulate_history(block, conway)))

    def test_direction_metric_retains_velocity_after_alignment(self) -> None:
        base = np.zeros((16, 16), dtype=np.bool_)
        base[7:9, 7:9] = True
        sequence = [np.roll(base, index, axis=1) for index in range(4)]
        opposite = [np.roll(base, -index, axis=1) for index in range(4)]
        result = _direction_paired_metric(
            sequence,
            (0, 1),
            sequence,
            (0, 1),
            opposite,
            (0, -1),
        )
        self.assertGreater(result["direction_margin"], 0.25)


class WriterClosureCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6k_and_parent_root(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "writer-closure",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6k",
                "--stage6j-root",
                str(DEFAULT_STAGE6J_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "writer-closure")
        self.assertEqual(args.stage6j_root, DEFAULT_STAGE6J_ROOT)
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)


if __name__ == "__main__":
    unittest.main()
