from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_acquisition_repair as ar
from plastic_ca.motif_phenotype_bridge import (
    PHENOTYPE_BRIDGE_PROFILES,
    PhenotypeBridgeContract,
    _copy_carrier,
    _encode_carrier,
    _joint_payload,
    _prepare_stage6e,
    build_phenotype_bridge_candidates,
    run_motif_phenotype_bridge,
    simulate_phenotype_lineage,
)


ROOTS = {
    "stage6d_root": Path("results/ca-motif-consumptive-renewal-stage-6d"),
    "stage6c_root": Path("results/ca-motif-lineage-stage-6c"),
    "stage6br_root": Path("results/ca-motif-lineage-stage-6br"),
    "stage5r_root": Path("results/ca-motif-lineage-stage-5r"),
    "stage5_root": Path("results/ca-motif-lineage-stage-5"),
    "stage4_root": Path("results/ca-motif-lineage-stage-4"),
    "stage3r_root": Path("results/ca-motif-lineage-stage-3r"),
    "stage3_root": Path("results/ca-motif-lineage-stage-3"),
    "stage2_root": Path("results/ca-motif-lineage-stage-2"),
    "stage1_root": Path("results/ca-motif-lineage-stage-1"),
}


def frontends() -> list[dict[str, object]]:
    return [
        {
            "frontend_id": "test-q4",
            "encoder_id": "test-q4",
            "kind": "calibrated-q4",
            "bits": 4,
            "scale": [0.25] * 16,
            "read_sweeps": 40,
            "clearance_updates": 1,
            "trace_sweeps": 2,
        },
        {
            "frontend_id": "test-q8",
            "encoder_id": "test-q8",
            "kind": "unit-q8",
            "bits": 8,
            "scale": [1.0] * 16,
            "read_sweeps": 48,
            "clearance_updates": 2,
            "trace_sweeps": 4,
        },
    ]


class PhenotypeBridgePrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidates, cls.anchors = build_phenotype_bridge_candidates(frontends())

    def test_registered_candidate_ladder_is_exact(self) -> None:
        self.assertEqual(len(self.candidates), 26)
        self.assertEqual(len(self.anchors), 3)
        self.assertEqual(
            sum(row["mechanism"] == "timing-only" for row in self.candidates), 2
        )
        self.assertEqual(
            sum(row["mechanism"] == "visible-hysteresis" for row in self.candidates), 8
        )
        self.assertEqual(
            sum(row["mechanism"] == "somatic-field" for row in self.candidates), 16
        )
        self.assertEqual(
            sum(row["claim_tier"] == "broad" for row in self.candidates), 8
        )

    def test_eight_bit_carrier_roundtrip_uses_two_hamming_nibbles(self) -> None:
        candidate = next(row for row in self.candidates if row["bits"] == 8)
        contract = replace(PhenotypeBridgeContract(), bit_corruption=0.0)
        rng = np.random.default_rng(3)
        raw = rng.uniform(-0.9, 0.9, size=(8, 16)).astype(np.float32)
        payload, _ = ar._quantize(raw, candidate["codec_model"])
        shares, active = _encode_carrier(
            payload, candidate, contract, "pair", 4, "test"
        )
        copied, uncorrectable = _copy_carrier(shares, "pair", 5, 4, contract)
        decoded, valid = _joint_payload(copied, active, candidate)
        self.assertEqual(shares.shape[-1], 32)
        self.assertEqual(uncorrectable, 0.0)
        self.assertTrue(bool(np.all(valid)))
        np.testing.assert_allclose(decoded, payload, atol=1e-6)

    def test_promotable_writer_api_has_no_somatic_or_target_argument(self) -> None:
        parameters = inspect.signature(ar.observe_texture).parameters
        for forbidden in ("somatic", "target", "template", "label", "parent_payload"):
            self.assertNotIn(forbidden, parameters)


class PhenotypeBridgeWorkflowTests(unittest.TestCase):
    def test_worker_and_wall_caps_precede_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_motif_phenotype_bridge(Path(directory), profile_name="smoke", workers=5)
            with self.assertRaises(ValueError):
                run_motif_phenotype_bridge(Path(directory), profile_name="smoke", max_hours=8.01)

    def test_preparation_uses_disjoint_exposed_pairs_and_seals_reserve(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, cohorts, profile, _, _, _, _ = _prepare_stage6e(
                Path(directory), "reference", auto_final_audit=True, **ROOTS
            )
            used = [
                pair["pair_id"]
                for name, rows in cohorts.items()
                if name != "final"
                for pair in rows
            ]
            self.assertEqual(len(used), 64)
            self.assertEqual(len(set(used)), 64)
            self.assertEqual(cohorts["final"], [])
            self.assertEqual(profile.final_pairs, 62)
            state = json.loads((Path(directory) / "COHORTS.json").read_text())
            self.assertEqual(state["final_audit_trajectory_state"], "untouched")
            self.assertTrue(state["final_audit_trajectories_not_loaded"])

    def test_strict_and_broad_simulations_enforce_distinct_field_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            frozen, cohorts, _, contract, writer_contract, templates, _ = _prepare_stage6e(
                Path(directory), "smoke", auto_final_audit=True, **ROOTS
            )
            candidates, _ = build_phenotype_bridge_candidates(frontends())
            strict = next(
                row
                for row in candidates
                if row["mechanism"] == "somatic-field"
                and row["claim_tier"] == "strict"
            )
            broad = next(
                row
                for row in candidates
                if row["mechanism"] == "somatic-field"
                and row["claim_tier"] == "broad"
            )
            timing = next(
                row for row in candidates if row["mechanism"] == "timing-only"
            )
            common = dict(
                pair=cohorts["bridge"][0],
                configuration=frozen["stage4"]["configuration"],
                condition="intact",
                replicates=1,
                generations=5,
                reference=frozen["stage4"]["reference"],
                writer_contract=writer_contract,
                contract=contract,
                environmental_template=np.asarray(templates[0]["bits"], dtype=np.bool_),
            )
            strict_result, _ = simulate_phenotype_lineage(candidate=strict, **common)
            broad_result, _ = simulate_phenotype_lineage(candidate=broad, **common)
            timing_result, _ = simulate_phenotype_lineage(candidate=timing, **common)
            self.assertTrue(strict_result["all_renewal_writer_windows_carrier_absent"])
            self.assertTrue(strict_result["all_strict_writer_windows_field_absent"])
            self.assertTrue(strict_result["somatic_zero_at_every_birth"])
            self.assertTrue(strict_result["somatic_zero_at_every_exit"])
            self.assertTrue(strict_result["somatic_not_passed_to_writer"])
            self.assertTrue(broad_result["all_renewal_writer_windows_carrier_absent"])
            self.assertFalse(broad_result["all_strict_writer_windows_field_absent"])
            self.assertTrue(broad_result["somatic_zero_at_every_birth"])
            self.assertTrue(broad_result["somatic_zero_at_every_exit"])
            self.assertTrue(broad_result["somatic_not_passed_to_writer"])
            self.assertTrue(timing_result["all_strict_writer_windows_field_absent"])

    def test_acquisition_writer_seeds_founder_without_incoming_carrier(self) -> None:
        """Regression for the invalid Stage-6E v1 acquisition gate.

        Generation four has no incoming texture carrier by construction.  Its
        environmental writer must nevertheless seed the first carrier; only
        the explicit acquisition-write-disabled control may suppress it.
        """

        with tempfile.TemporaryDirectory() as directory:
            frozen, cohorts, _, contract, writer_contract, templates, _ = _prepare_stage6e(
                Path(directory), "smoke", auto_final_audit=True, **ROOTS
            )
            candidates, _ = build_phenotype_bridge_candidates(frontends())
            timing = next(
                row for row in candidates if row["mechanism"] == "timing-only"
            )
            common = dict(
                pair=cohorts["bridge"][0],
                configuration=frozen["stage4"]["configuration"],
                candidate=timing,
                replicates=1,
                generations=5,
                reference=frozen["stage4"]["reference"],
                writer_contract=writer_contract,
                contract=contract,
                environmental_template=np.asarray(templates[0]["bits"], dtype=np.bool_),
                retain_bridge_trace=True,
            )
            intact, _ = simulate_phenotype_lineage(condition="intact", **common)
            sham, _ = simulate_phenotype_lineage(condition="sham", **common)
            disabled, _ = simulate_phenotype_lineage(
                condition="acquisition_write_disabled", **common
            )

            founder = intact["writer_history"]["4"]
            self.assertFalse(founder["writer_connected"])
            self.assertFalse(founder["writer_connection_required"])
            self.assertTrue(founder["acquisition_writer_independent"])
            self.assertTrue(founder["fresh_carrier_written"])
            self.assertTrue(sham["writer_history"]["4"]["fresh_carrier_written"])
            self.assertFalse(disabled["writer_history"]["4"]["fresh_carrier_written"])
            self.assertEqual(intact["carrier_history"]["4"]["joint_valid_fraction"], 1.0)
            self.assertEqual(disabled["carrier_history"]["4"]["joint_valid_fraction"], 0.0)
            self.assertEqual(intact["carrier_history"]["5"]["entry_complete_fraction"], 1.0)

            intact_trace = intact["bridge_trace"]["5"]["patches_after_read"]
            sham_trace = sham["bridge_trace"]["5"]["patches_after_read"]
            self.assertNotEqual(intact_trace, sham_trace)

    def test_reference_profile_preserves_registered_split(self) -> None:
        profile = PHENOTYPE_BRIDGE_PROFILES["reference"]
        self.assertEqual(
            profile.bridge_pairs
            + profile.screen_pairs
            + profile.qualification_pairs
            + profile.endurance_pairs,
            64,
        )
        self.assertEqual(profile.final_pairs, 62)


if __name__ == "__main__":
    unittest.main()
