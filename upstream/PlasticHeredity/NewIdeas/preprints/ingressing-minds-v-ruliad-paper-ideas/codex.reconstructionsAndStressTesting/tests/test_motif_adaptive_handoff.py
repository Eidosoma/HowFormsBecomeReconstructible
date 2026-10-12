from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_acquisition_repair as ar
from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca.cli import build_parser
from plastic_ca.motif_adaptive_handoff import (
    ARCHITECTURES,
    CLAIM_GROUPS,
    DEFAULT_STAGE6H_ROOT,
    DEFAULT_STAGE6I_ROOT,
    PROFILES,
    TRAINING_TIERS,
    AdaptiveHandoffContract,
    _candidate_specs,
    _metric_audit,
    _parent_integrity,
    _phase_result_path,
    _reconstruct_cohorts,
    _seal_registry,
    run_motif_adaptive_handoff,
)
from tests.test_motif_phenotype_bridge import ROOTS


class AdaptiveHandoffIntegrityTests(unittest.TestCase):
    def test_phase_results_live_beside_private_stage_workspace(self) -> None:
        output = Path("results/campaign")
        self.assertEqual(
            _phase_result_path(output / "stage6j", "screen"),
            output / "screen/RESULTS.json",
        )

    def test_stage6i_boundary_and_reserve_are_frozen(self) -> None:
        result = _parent_integrity(DEFAULT_STAGE6I_ROOT, DEFAULT_STAGE6H_ROOT)
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["stage6i_screen_trajectory_count"], 320)
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_cohort_route_has_40_exposed_then_8_and_8(self) -> None:
        integrity = _parent_integrity(DEFAULT_STAGE6I_ROOT, DEFAULT_STAGE6H_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            _, cohorts, _, _, _ = _reconstruct_cohorts(
                Path(directory),
                PROFILES["reference"],
                integrity,
                ROOTS,
                auto_final_audit=True,
            )
            self.assertEqual(len(cohorts["development"]), 40)
            self.assertEqual(len(cohorts["screen"]), 8)
            self.assertEqual(len(cohorts["qualification"]), 8)
            self.assertEqual(len(cohorts["endurance"]), 8)
            self.assertEqual(
                [row["pair_id"] for row in cohorts["screen"]],
                [row["pair_id"] for row in cohorts["qualification"]],
            )

    def test_caps_precede_campaign_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                run_motif_adaptive_handoff(root, profile_name="smoke", workers=5)
            with self.assertRaises(ValueError):
                run_motif_adaptive_handoff(root, profile_name="smoke", max_hours=8.01)
            with self.assertRaises(ValueError):
                run_motif_adaptive_handoff(root, profile_name="reference")


class AdaptiveHandoffMechanismTests(unittest.TestCase):
    def test_factorial_has_24_balanced_candidates(self) -> None:
        specs = _candidate_specs(DEFAULT_STAGE6H_ROOT)
        self.assertEqual(len(specs), 24)
        self.assertEqual(len({row["candidate_id"] for row in specs}), 24)
        for tier in TRAINING_TIERS:
            self.assertEqual(
                sum(row["adaptive_claim_tier"] == tier for row in specs), 12
            )
        for architecture in ARCHITECTURES:
            self.assertEqual(
                sum(row["adaptive_architecture"] == architecture for row in specs),
                8,
            )
        self.assertEqual(len(CLAIM_GROUPS), 4)
        self.assertTrue(all(row["two_buffer_handoff"] for row in specs))
        self.assertTrue(all(not row["parent_field_exposed_to_writer"] for row in specs))
        stack_assisted = [
            row
            for row in specs
            if row["adaptive_claim_tier"] == "rulebook-assisted"
            and row.get("writer_transform", {}).get("input_mode", "stack") == "stack"
        ]
        self.assertTrue(stack_assisted)
        self.assertTrue(
            all(
                row["writer_transform"]["temporal_view"] == "tail-trained-window"
                and row["writer_transform"]["trained_trace_sweeps"] == 8
                for row in stack_assisted
            )
        )

    def test_directed_metric_flags_constant_degeneracy(self) -> None:
        audit = _metric_audit(AdaptiveHandoffContract())
        self.assertTrue(audit["stage_gate"])
        self.assertFalse(
            audit["diagnostics"]["constant-degenerate"]["reference"][
                "reference_temporally_identifiable"
            ]
        )
        self.assertLessEqual(
            audit["diagnostics"]["random-directed"]["cyclic_invariance_error"],
            1e-6,
        )

    def test_two_channel_codec_roundtrip(self) -> None:
        specs = _candidate_specs(DEFAULT_STAGE6H_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seal_registry(root, specs, "d" * 64)
            candidates, _ = pb._load_models(root, ROOTS["stage6br_root"])
            candidate = next(row for row in candidates if row["field_rank"] == 8)
            field_candidate = pb._field_codec_candidate(candidate)
            self.assertEqual(field_candidate["rank"], 16)
            rng = np.random.default_rng(61)
            raw = rng.uniform(-1.0, 1.0, size=(8, 16)).astype(np.float32)
            payload, _ = pb._quantize_frontend(raw, field_candidate)
            shares, active = pb._encode_carrier(
                payload,
                field_candidate,
                AdaptiveHandoffContract(),
                "unit-pair",
                5,
                "unit-two-channel-field",
            )
            copied, uncorrectable = pb._copy_carrier(
                shares,
                "unit-pair",
                5,
                4,
                AdaptiveHandoffContract(),
                purpose="unit-two-channel-copy",
                corruption=0.01,
            )
            restored, valid = pb._joint_payload(copied, active, field_candidate)
            self.assertTrue(np.all(valid))
            self.assertLess(uncorrectable, 0.10)
            self.assertLess(float(np.mean(np.abs(restored - payload))), 0.20)

    def test_adapter_interface_cannot_receive_parent_field(self) -> None:
        parameters = inspect.signature(pb._adaptive_handoff_update).parameters
        self.assertNotIn("parent_field", parameters)
        self.assertNotIn("incoming_payload", parameters)

    def test_real_lineage_uses_distinct_zero_born_buffers(self) -> None:
        integrity = _parent_integrity(DEFAULT_STAGE6I_ROOT, DEFAULT_STAGE6H_ROOT)
        specs = _candidate_specs(DEFAULT_STAGE6H_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage_root = root / "stage6j"
            frozen, cohorts, _, writer_contract, templates = _reconstruct_cohorts(
                stage_root,
                PROFILES["smoke"],
                integrity,
                ROOTS,
                auto_final_audit=True,
            )
            _seal_registry(stage_root, specs, "e" * 64)
            candidates, _ = pb._load_models(stage_root, ROOTS["stage6br_root"])
            candidate = next(
                row
                for row in candidates
                if row["candidate_id"]
                == "stage6j-label-free-phase-latch-distiller-r08-short"
            )
            item = ar._make_items(
                cohorts["development"][:1],
                [candidate],
                ar._template_pairs(templates, "development")[:1],
                frozen["stage4"]["configuration"],
                phase="unit-handoff",
                replicates=1,
                generations=6,
                conditions=("intact", "handoff_visible_scrub"),
            )[0]
            row = pb._phenotype_pair_task(
                (
                    item,
                    [candidate],
                    writer_contract,
                    AdaptiveHandoffContract(),
                    frozen["stage4"]["reference"],
                )
            )
            result = row["conditions"]["intact"]
            self.assertTrue(result["two_buffer_handoff"])
            self.assertTrue(result["daughter_field_zero_at_every_birth"])
            self.assertTrue(result["adaptive_state_zero_at_every_birth"])
            self.assertTrue(result["adaptive_state_zero_at_every_exit"])
            self.assertTrue(result["parent_field_erased_before_every_finalize"])
            self.assertTrue(result["parent_daughter_buffers_always_distinct"])
            self.assertTrue(result["handoff_trace"])

    def test_long_assisted_stack_translators_use_registered_tail_view(self) -> None:
        integrity = _parent_integrity(DEFAULT_STAGE6I_ROOT, DEFAULT_STAGE6H_ROOT)
        specs = _candidate_specs(DEFAULT_STAGE6H_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage_root = root / "stage6j"
            frozen, cohorts, _, writer_contract, templates = _reconstruct_cohorts(
                stage_root,
                PROFILES["smoke"],
                integrity,
                ROOTS,
                auto_final_audit=True,
            )
            _seal_registry(stage_root, specs, "f" * 64)
            candidates, _ = pb._load_models(stage_root, ROOTS["stage6br_root"])
            expected = {
                "stage6j-rulebook-assisted-phase-latch-distiller-r08-long": "linear",
                "stage6j-rulebook-assisted-dual-timescale-predictive-reservoir-r08-long": "rff-linear",
            }
            by_id = {row["candidate_id"]: row for row in candidates}
            for candidate_id, transform_kind in expected.items():
                with self.subTest(candidate_id=candidate_id):
                    candidate = by_id[candidate_id]
                    item = ar._make_items(
                        cohorts["development"][:1],
                        [candidate],
                        ar._template_pairs(templates, "development")[:1],
                        frozen["stage4"]["configuration"],
                        phase="unit-long-assisted-handoff",
                        replicates=1,
                        generations=6,
                        conditions=("intact",),
                    )[0]
                    row = pb._phenotype_pair_task(
                        (
                            item,
                            [candidate],
                            writer_contract,
                            AdaptiveHandoffContract(),
                            frozen["stage4"]["reference"],
                        )
                    )
                    result = row["conditions"]["intact"]
                    self.assertEqual(
                        result["writer_history"]["5"]["writer_transform_kind"],
                        transform_kind,
                    )
                    self.assertEqual(
                        result["writer_history"]["5"][
                            "writer_transform_temporal_view"
                        ],
                        "tail-trained-window",
                    )
                    self.assertTrue(result["two_buffer_handoff"])


class AdaptiveHandoffCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6j(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "adaptive-handoff",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6j",
                "--stage6i-root",
                str(DEFAULT_STAGE6I_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "adaptive-handoff")
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)


if __name__ == "__main__":
    unittest.main()
