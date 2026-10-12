from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from plastic_ca.motif_lineage import MotifContract
from plastic_ca.motif_minimality import load_frozen_stage5r
from plastic_ca.motif_synergistic_heredity import (
    ANCHOR_CONTROL_ID,
    DEFAULT_STAGE6BR_ROOT,
    SYNERGY_PROFILES,
    SynergyContract,
    _apply_acquisition,
    _prepare_stage6c,
    _run_adjudicate,
    acquisition_templates,
    build_synergy_candidates,
    build_synergy_scale_variants,
    carrier_code_roundtrip,
    propagate_share_channels,
    reconstruct_share_field,
    run_motif_synergistic_heredity,
    simulate_synergistic_lineage,
    xor_reconstruct_codes,
    xor_share_codes,
)


class SynergisticPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidates, cls.controls, cls.anchor = build_synergy_candidates(
            DEFAULT_STAGE6BR_ROOT
        )

    def test_xor_shares_reconstruct_every_nibble_exactly(self) -> None:
        payload = np.tile(np.arange(16, dtype=np.uint8), (7, 1))
        for count in (2, 4):
            shares = xor_share_codes(payload, count, 6100 + count)
            np.testing.assert_array_equal(
                xor_reconstruct_codes(shares), payload
            )

    def test_every_single_xor_share_is_payload_independent(self) -> None:
        payload = np.repeat(np.arange(16, dtype=np.uint8), 4096)[:, None]
        shares = xor_share_codes(payload, 4, 6110)
        # Each share has the same empirical distribution for each payload code.
        for share in range(4):
            distributions = []
            for code in range(16):
                values = shares[payload[:, 0] == code, share, 0]
                distributions.append(
                    np.bincount(values, minlength=16) / len(values)
                )
            self.assertLess(
                float(np.max(np.ptp(np.stack(distributions), axis=0))),
                0.06,
            )

    def test_hamming_protects_share_code_fifteen(self) -> None:
        values = np.arange(16, dtype=np.uint8)
        baseline, flags = carrier_code_roundtrip(values, "hamming84")
        np.testing.assert_array_equal(baseline, values)
        self.assertEqual(flags, 0.0)
        for bit in range(8):
            flips = np.zeros((16, 8), dtype=np.uint8)
            flips[:, bit] = 1
            decoded, flags = carrier_code_roundtrip(
                values, "hamming84", flips
            )
            np.testing.assert_array_equal(decoded, values)
            self.assertEqual(flags, 0.0)

    def test_templates_are_balanced_complement_pairs_and_split(self) -> None:
        rows = acquisition_templates(SynergyContract())
        self.assertEqual(len(rows), 20)
        self.assertEqual(
            [sum(row["split"] == value for row in rows) for value in (
                "development", "qualification", "audit"
            )],
            [8, 8, 4],
        )
        for index in range(0, 20, 2):
            left = np.asarray(rows[index]["bits"], dtype=np.uint8)
            right = np.asarray(rows[index + 1]["bits"], dtype=np.uint8)
            self.assertEqual(int(left.sum()), 8)
            np.testing.assert_array_equal(1 - left, right)

    def test_cut_prevents_required_share_reunion(self) -> None:
        candidate = {**self.candidates[0], "germination_hops": 2}
        payload_codes = np.full((1, 16), 7, dtype=np.uint8)
        shares = xor_share_codes(payload_codes, 2, 6120)
        active = np.ones_like(shares, dtype=np.bool_)
        origins = np.asarray([[[2, 1], [2, 5]]], dtype=np.int16)
        intact_field, intact_occ, _ = propagate_share_channels(
            shares, active, origins, 8, 2
        )
        _, intact_complete = reconstruct_share_field(
            intact_field, intact_occ, candidate
        )
        cut_field, cut_occ, _ = propagate_share_channels(
            shares, active, origins, 8, 2, cut_axis="vertical"
        )
        _, cut_complete = reconstruct_share_field(
            cut_field, cut_occ, candidate
        )
        self.assertGreater(int(np.count_nonzero(intact_complete)), 0)
        self.assertEqual(int(np.count_nonzero(cut_complete)), 0)

    def test_visible_acquisition_does_not_mutate_carrier_arrays(self) -> None:
        state = np.zeros((2, 16, 16), dtype=np.bool_)
        origins = np.asarray(
            [[[4, 4], [12, 12]], [[5, 5], [13, 13]]], dtype=np.int16
        )
        carrier = np.arange(64, dtype=np.uint8).reshape(2, 2, 16).copy()
        before = carrier.copy()
        template = np.asarray(
            acquisition_templates(SynergyContract())[0]["bits"],
            dtype=np.bool_,
        )
        _apply_acquisition(state, origins, template)
        np.testing.assert_array_equal(carrier, before)
        self.assertGreater(int(np.count_nonzero(state)), 0)

    def test_registered_grid_and_scale_modes_are_exact(self) -> None:
        self.assertEqual(len(self.candidates), 24)
        self.assertEqual(
            {row["seed_count"] for row in self.candidates}, {2, 4}
        )
        self.assertEqual(
            {row["germination_hops"] for row in self.candidates}, {5, 6, 7}
        )
        self.assertEqual({row["rho"] for row in self.candidates}, {0.25, 0.5})
        variants = build_synergy_scale_variants(self.candidates[:1])
        self.assertEqual(len(variants), 6)
        self.assertEqual(
            {(row["extent"], row["scale_mode"]) for row in variants},
            {
                (16, "fixed"),
                (16, "diameter"),
                (32, "fixed"),
                (32, "diameter"),
                (64, "fixed"),
                (64, "diameter"),
            },
        )

    def test_runtime_api_has_no_label_or_target_arguments(self) -> None:
        parameters = inspect.signature(simulate_synergistic_lineage).parameters
        for forbidden in ("label", "prototype", "target", "parent_payload"):
            self.assertNotIn(forbidden, parameters)


class SynergisticWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frozen = load_frozen_stage5r()
        cls.candidates, cls.controls, cls.anchor = build_synergy_candidates(
            DEFAULT_STAGE6BR_ROOT
        )

    def test_worker_and_wall_caps_precede_output_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_motif_synergistic_heredity(
                    Path(directory), profile_name="smoke", workers=5
                )
            with self.assertRaises(ValueError):
                run_motif_synergistic_heredity(
                    Path(directory), profile_name="smoke", max_hours=8.01
                )

    def test_preparation_keeps_final_pairs_out_of_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prepared = _prepare_stage6c(
                Path(directory),
                "smoke",
                auto_final_audit=True,
                stage6br_root=DEFAULT_STAGE6BR_ROOT,
                stage5r_root=Path("results/ca-motif-lineage-stage-5r"),
                stage5_root=Path("results/ca-motif-lineage-stage-5"),
                stage4_root=Path("results/ca-motif-lineage-stage-4"),
                stage3r_root=Path("results/ca-motif-lineage-stage-3r"),
                stage3_root=Path("results/ca-motif-lineage-stage-3"),
                stage2_root=Path("results/ca-motif-lineage-stage-2"),
                stage1_root=Path("results/ca-motif-lineage-stage-1"),
            )
            cohorts = prepared[1]
            self.assertEqual(cohorts["final"], [])
            payload = __import__("json").loads(
                (Path(directory) / "COHORTS.json").read_text()
            )
            self.assertTrue(payload["final_audit_trajectories_not_loaded"])
            self.assertEqual(payload["final_audit_trajectory_state"], "untouched")

    def test_positive_branch_seals_before_opening(self) -> None:
        profile = SYNERGY_PROFILES["smoke"]
        candidate = self.candidates[0]
        positive = {
            "crossover": {"mean": 0.5, "ci": [0.4, 0.6]},
            "active_rewrite_advantage": {"mean": 0.2, "ci": [0.1, 0.3]},
            "direction_a_mean": 0.5,
            "direction_b_mean": 0.5,
            "fraction_pairs_positive": 1.0,
            "survival_mean": 1.0,
            "translation_retention": 1.0,
            "anchor_retention": 1.0,
            "joint_decoder": {"mean": 1.0, "ci": [1.0, 1.0]},
            "proper_subset_decoder": {"mean": 0.5, "ci": [0.5, 0.5]},
            "control_retention": {
                "no_rewrite": 0.0,
                "communication_cut_vertical": 0.0,
                "communication_cut_horizontal": 0.0,
            },
        }
        acquired = {
            "effect": {"mean": 0.5, "ci": [0.4, 0.6]},
            "active_rewrite_advantage": {"mean": 0.2, "ci": [0.1, 0.3]},
            "fraction_templates_positive": 1.0,
            "template_means": {"acq-16": 0.5},
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "endurance").mkdir()
            (output / "synergy").mkdir()
            (output / "forensics").mkdir()
            (output / "endurance/RESULTS.json").write_text(
                '{"enduring_candidate_ids": ["'
                + candidate["candidate_id"]
                + '"]}\n'
            )
            (output / "synergy/RESULTS.json").write_text(
                '{"candidate_summaries": {}}\n'
            )
            (output / "forensics/RESULTS.json").write_text(
                '{"stage_gate": true}\n'
            )
            (output / "COHORTS.json").write_text(
                '{"final_audit_trajectory_state": "untouched", '
                '"final_audit_trajectories_not_loaded": true}\n'
            )
            with (
                patch(
                    "plastic_ca.motif_synergistic_heredity._run_json_checkpoints",
                    return_value=([], True),
                ),
                patch(
                    "plastic_ca.motif_synergistic_heredity._candidate_summary",
                    return_value=dict(positive),
                ),
                patch(
                    "plastic_ca.motif_synergistic_heredity._acquisition_summary",
                    return_value=dict(acquired),
                ),
                patch(
                    "plastic_ca.motif_synergistic_heredity._causal_qualification",
                    return_value=(True, {"causal_test_double": True}),
                ),
            ):
                result = _run_adjudicate(
                    output,
                    self.frozen,
                    profile,
                    "smoke",
                    SynergyContract(),
                    MotifContract(),
                    "d" * 64,
                    self.candidates,
                    self.controls,
                    self.anchor,
                    acquisition_templates(SynergyContract()),
                    DEFAULT_STAGE6BR_ROOT,
                    workers=1,
                    resume=False,
                    deadline=float("inf"),
                    status=lambda *args, **kwargs: None,
                    scientific=False,
                    auto_final_audit=True,
                )
            self.assertTrue(result["stage_gate"])
            self.assertEqual(
                result["verdict"], "CONFIRMED_SYNERGISTIC_ACQUIRED_CA_PH"
            )
            self.assertTrue((output / "FINAL_AUDIT_DESIGN.json").exists())
            cohorts = __import__("json").loads(
                (output / "COHORTS.json").read_text()
            )
            self.assertEqual(cohorts["final_audit_trajectory_state"], "complete")


if __name__ == "__main__":
    unittest.main()
