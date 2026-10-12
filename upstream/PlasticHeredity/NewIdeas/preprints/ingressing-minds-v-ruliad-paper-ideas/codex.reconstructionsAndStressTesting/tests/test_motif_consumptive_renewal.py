from __future__ import annotations

import inspect
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca.motif_consumptive_renewal import (
    CONSUMPTIVE_RENEWAL_PROFILES,
    ConsumptiveRenewalContract,
    _destroy_carrier,
    _phenotype_intervention,
    _prepare_stage6d,
    build_consumptive_candidates,
    run_motif_consumptive_renewal,
    simulate_consumptive_lineage,
)
from plastic_ca.motif_acquisition_repair import apply_texture_reader, observe_texture


ROOTS = {
    "stage6cr_root": Path("results/ca-motif-acquisition-repair-stage-6cr"),
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


class ConsumptiveRenewalPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = ConsumptiveRenewalContract()
        cls.candidates, cls.anchor = build_consumptive_candidates()

    def test_candidate_grid_and_anchor_are_exact(self) -> None:
        self.assertEqual(len(self.candidates), 24)
        self.assertEqual({row["rank"] for row in self.candidates}, {16})
        self.assertEqual(
            {row["read_strength"] for row in self.candidates}, {0.60, 0.75, 0.90}
        )
        self.assertEqual({row["read_sweeps"] for row in self.candidates}, {40, 48})
        self.assertEqual(
            {row["washout_sweeps"] for row in self.candidates}, {4, 8}
        )
        self.assertEqual({row["write_gain"] for row in self.candidates}, {1.0, 1.5})
        self.assertTrue(all(row["promotable"] for row in self.candidates))
        self.assertFalse(self.anchor["promotable"])
        self.assertEqual(self.anchor["renewal_mode"], "legacy_anchor")

    def test_every_strict_timeline_has_a_carrier_free_gap(self) -> None:
        for candidate in self.candidates:
            read_end = int(candidate["read_sweeps"])
            writer_start = read_end + int(candidate["washout_sweeps"]) + 1
            writer_end = writer_start + self.contract.texture_trace_sweeps - 1
            self.assertGreater(writer_start, read_end)
            self.assertLessEqual(writer_end, self.contract.generation_sweeps)

    def test_physical_destruction_removes_values_and_occupancy(self) -> None:
        shares = np.arange(128, dtype=np.uint8).reshape(2, 4, 16)
        active = np.ones_like(shares, dtype=np.bool_)
        destroyed, disabled = _destroy_carrier(shares, active)
        self.assertFalse(bool(np.any(destroyed)))
        self.assertFalse(bool(np.any(disabled)))
        self.assertTrue(bool(np.any(shares)))
        self.assertTrue(bool(np.all(active)))

    def test_writer_and_reader_apis_exclude_targets_and_parent_payloads(self) -> None:
        for function in (observe_texture, apply_texture_reader):
            parameters = inspect.signature(function).parameters
            for forbidden in (
                "target",
                "template",
                "label",
                "prototype",
                "parent_payload",
                "incoming_payload",
            ):
                self.assertNotIn(forbidden, parameters)

    def test_phenotype_rescue_changes_visible_cells_not_writer_arguments(self) -> None:
        state = np.zeros((2, 16, 16), dtype=np.bool_)
        centers = np.asarray([[8, 8], [8, 8]], dtype=np.int16)
        environment = np.concatenate(
            (
                np.ones((1, 4, 4), dtype=np.bool_),
                np.zeros((1, 4, 4), dtype=np.bool_),
            ),
            axis=0,
        )
        changed = _phenotype_intervention(
            state,
            centers,
            environment,
            "phenotype_same_rescue",
            "pair",
            self.contract.intervention_generation,
            1,
            self.contract,
        )
        self.assertTrue(changed)
        observed = observe_texture(state, centers)
        np.testing.assert_array_equal(observed[0], 1.0)
        np.testing.assert_array_equal(observed[1], -1.0)


class ConsumptiveRenewalWorkflowTests(unittest.TestCase):
    def test_worker_and_wall_caps_precede_output_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_motif_consumptive_renewal(
                    Path(directory), profile_name="smoke", workers=5
                )
            with self.assertRaises(ValueError):
                run_motif_consumptive_renewal(
                    Path(directory), profile_name="smoke", max_hours=8.01
                )

    def test_preparation_keeps_the_reserve_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prepared = _prepare_stage6d(
                Path(directory),
                "smoke",
                auto_final_audit=True,
                **ROOTS,
            )
            cohorts = prepared[1]
            self.assertEqual(cohorts["final"], [])
            self.assertEqual(
                sum(
                    len(cohorts[key])
                    for key in ("screen", "qualification", "endurance")
                ),
                6,
            )
            payload = json.loads((Path(directory) / "COHORTS.json").read_text())
            self.assertEqual(payload["final_audit_trajectory_state"], "untouched")
            self.assertTrue(payload["final_audit_trajectories_not_loaded"])
            design = json.loads((Path(directory) / "DESIGN.json").read_text())
            self.assertFalse(design["final_audit_trajectories_loaded"])
            self.assertFalse(design["candidate_factorial"]["anchor_promotable"])

    def test_strict_simulation_erases_before_writer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prepared = _prepare_stage6d(
                Path(directory),
                "smoke",
                auto_final_audit=True,
                **ROOTS,
            )
            frozen, cohorts, _, contract, writer_contract, candidates = prepared[:6]
            template = prepared[7][0]
            result, _ = simulate_consumptive_lineage(
                pair=cohorts["screen"][0],
                configuration=frozen["stage4"]["configuration"],
                candidate=candidates[0],
                condition="intact",
                replicates=1,
                generations=5,
                reference=frozen["stage4"]["reference"],
                writer_contract=writer_contract,
                contract=contract,
                environmental_template=np.asarray(template["bits"], dtype=np.bool_),
            )
            writer = result["writer_history"]["5"]
            self.assertTrue(writer["carrier_erased_before_writer"])
            self.assertTrue(writer["carrier_absent_during_writer"])
            self.assertFalse(writer["incoming_payload_exposed_to_writer"])
            self.assertGreater(writer["writer_start"], writer["read_end"])
            self.assertEqual(writer["trace_count"], contract.texture_trace_sweeps)
            self.assertTrue(result["all_renewal_writer_windows_carrier_absent"])

    def test_reference_profile_uses_64_exposed_and_62_final_pairs(self) -> None:
        profile = CONSUMPTIVE_RENEWAL_PROFILES["reference"]
        self.assertEqual(
            profile.screen_pairs
            + profile.qualification_pairs
            + profile.endurance_pairs,
            64,
        )
        self.assertEqual(profile.final_pairs, 62)


if __name__ == "__main__":
    unittest.main()
