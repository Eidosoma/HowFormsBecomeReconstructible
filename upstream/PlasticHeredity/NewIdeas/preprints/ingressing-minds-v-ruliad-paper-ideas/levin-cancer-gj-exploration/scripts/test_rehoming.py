import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from analyze_rehoming import audit_source
from memory_metrics import REGULATORS
from run_rehoming import age_ordinary, fresh_recipient, frozen_manifest, load_source, source_spec, validate_config


class RehomingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/rehoming_v1.json").read_text())
        self.indices = dict(zip(REGULATORS, (5, 6, 7)))
        self.refs = np.ones((17, 2))
        self.refs[5:8] = [[84, 9], [6, 69], [.4, 63]]
        self.ids = ["old:child:1", "old:child:2"]
        self.meta = {"incoming_ids": self.ids.copy(), "outgoing_ids": self.ids.copy()}
        self.prefix = {"incoming_ids": ["founder:1", "founder:2"], "outgoing_ids": self.ids.copy()}

    def case(self, old="E", condition="rehomed", fine=False):
        return next(c for c in self.config["cases"] if c["old_state"] == old and c["condition"] == condition and c.get("fine", False) == fine)

    def test_fixed_grid(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 10)
        self.assertEqual(sum(c.get("fine", False) for c in self.config["cases"]), 2)

    def test_old_and_new_frozen_manifest_formats(self):
        old = {"hashes_sha256": {"scripts/runner.py": "a", "configs/run.json": "b", "upstream/native.py": "c"}}
        self.assertEqual(frozen_manifest(old), {"runner.py": "a", "run.json": "b"})
        self.assertEqual(frozen_manifest(dict(old, frozen_hashes_sha256={"other.py": "d"})), {"other.py": "d"})

    def test_ambiguous_or_empty_legacy_manifest_rejected(self):
        for hashes in ({}, {"scripts/a.py": "a", "other/a.py": "b"}):
            with self.assertRaises(ValueError):
                frozen_manifest({"hashes_sha256": hashes})

    def test_changed_polarity_history_or_grid_rejected(self):
        for key, value in (("old_state", "M"), ("state", "E"), ("history", "ordinary"), ("fine", True)):
            config = copy.deepcopy(self.config)
            config["cases"][0][key] = value
            with self.assertRaises(ValueError):
                validate_config(config)
        for key, value in (("cases", self.config["cases"][:-1]), ("workers", 3), ("intervention_horizon", 2000)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                validate_config(config)

    def test_active_blocked_and_fine_share_exact_baseline_source(self):
        for old in ("E", "M"):
            spec = source_spec(self.case(old))
            self.assertEqual(spec, source_spec(self.case(old, "blocked")))
            self.assertEqual(spec, source_spec(self.case(old, fine=True)))
            self.assertEqual(spec["key"], "after_2")
            self.assertEqual(spec["packet_file"], old.lower() + "_overwrite.npz")

    def test_sham_and_ordinary_select_correct_directions(self):
        self.assertEqual(source_spec(self.case("E", "sham"))["packet_file"], "e_sham.npz")
        self.assertEqual(source_spec(self.case("E", "ordinary"))["packet_file"], "m_ordinary.npz")
        self.assertEqual(source_spec(self.case("M", "ordinary"))["packet_file"], "e_ordinary.npz")

    def test_recipients_start_old_not_new_and_are_copied(self):
        for old, column in (("E", 0), ("M", 1)):
            target = fresh_recipient(self.refs, self.case(old), self.indices)
            np.testing.assert_array_equal(target, self.refs[:, column, None])
            self.assertFalse(np.shares_memory(target, self.refs))

    def test_already_new_or_invalid_recipient_rejected(self):
        swapped = self.refs[:, ::-1]
        for refs in (swapped, self.refs * np.nan, -self.refs):
            with self.assertRaises(ValueError):
                fresh_recipient(refs, self.case(), self.indices)

    def fixture(self, condition="rehomed"):
        case = self.case(condition=condition)
        column = 0 if condition == "sham" else 1
        packet = self.refs[:, column, None].repeat(2, axis=1)
        spec = source_spec(case)
        records = {spec["metadata_file"]: self.meta, "e_prefix.json": self.prefix}
        source = dict(spec, incoming_ids=self.ids, outgoing_ids=self.ids, source_labels="EE" if condition == "sham" else "MM",
                      relay_start_labels="EE" if condition == "sham" else "MM", extra_waits=0, new_reference_edits=0)
        records["source.json"] = source
        saved = {"source_packet": packet.copy(), "continuing_start": packet.copy()}
        return case, packet, records, saved

    def load_fixture(self, fixture):
        case, packet, records, saved = fixture
        def read(path, *args, **kwargs):
            return json.dumps(records[path.name])
        with patch("run_rehoming.arrays", return_value={"after_2": packet}), \
             patch.object(Path, "read_text", new=read):
            return load_source(Path("inputs"), case, self.indices)

    def test_load_source_preserves_full_state_and_ids(self):
        fixture = self.fixture()
        packet, ids, seen, _ = self.load_fixture(fixture)
        np.testing.assert_array_equal(packet, fixture[1])
        self.assertFalse(np.shares_memory(packet, fixture[1]))
        self.assertEqual(ids, self.ids)
        self.assertEqual(len(seen), 4)

    def test_wrong_source_label_rejected(self):
        fixture = self.fixture()
        fixture[1][5:8] = self.refs[5:8, 0, None]
        with self.assertRaises(ValueError):
            self.load_fixture(fixture)

    def test_renamed_or_duplicate_carriers_rejected(self):
        for ids in (["changed-a", "changed-b"], [self.ids[0], self.ids[0]]):
            fixture = self.fixture()
            fixture[2]["e_overwrite.json"] = dict(self.meta, outgoing_ids=ids)
            with self.assertRaises(ValueError):
                self.load_fixture(fixture)

    def audit_fixture(self, fixture):
        case, packet, records, saved = fixture
        def read(path, *args, **kwargs):
            return json.dumps(records[path.name])
        with patch("analyze_rehoming.arrays", side_effect=lambda p: saved if p.name == "endpoints.npz" else {"after_2": packet}), \
             patch.object(Path, "read_text", new=read), patch.object(Path, "exists", return_value=False):
            return audit_source(Path("branch"), Path("inputs"), self.config, case, self.refs, self.indices)

    def test_independent_source_audit_accepts_rehomed_and_sham(self):
        for condition in ("rehomed", "sham"):
            _, _, _, _, checks, _ = self.audit_fixture(self.fixture(condition))
            self.assertTrue(all(checks.values()), checks)

    def test_audit_rejects_rewriting_the_source_before_relay(self):
        fixture = self.fixture()
        fixture[3]["continuing_start"][5] += 1
        _, _, _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["exact_actual_start_enters_relay"])

    def test_audit_rejects_wrong_checkpoint_key_or_extra_wait(self):
        fixture = self.fixture()
        fixture[2]["source.json"]["key"] = "after_1"
        fixture[2]["source.json"]["extra_waits"] = 1
        _, _, _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["correct_source_selection"])
        self.assertFalse(checks["correct_wait_count"])

    def test_ordinary_aging_uses_actual_previous_output_without_edit(self):
        indices = self.indices
        class FakeExperiment:
            def __init__(self, folder, config):
                self.indices, self.audits = indices, []
            def build(self, count, state, active=False):
                self.state = state.copy()
                return {"cells": count, "active": active, "edges": 0, "miRNA_kd": 0}
            def phase(self, name, horizon):
                self.state[0] += 1
                record = {"phase": name, "requested_horizon": horizon}
                self.audits.append(record)
                return self.state.copy(), record
        packet = self.refs[:, 1, None].repeat(2, axis=1)
        with tempfile.TemporaryDirectory() as temp, patch("run_rehoming.Experiment", FakeExperiment):
            folder = Path(temp) / "wait"
            result = age_ordinary(folder, self.config, packet, self.ids, self.indices)
            with np.load(folder / "endpoints.npz") as saved:
                np.testing.assert_array_equal(saved["before_1"], packet)
                np.testing.assert_array_equal(saved["edited_1"], saved["before_1"])
                np.testing.assert_array_equal(saved["before_2"], saved["after_1"])
                np.testing.assert_array_equal(saved["edited_2"], saved["before_2"])
                np.testing.assert_array_equal(result, saved["after_2"])
            np.testing.assert_array_equal(result[1:], packet[1:])
            np.testing.assert_array_equal(result[0], packet[0] + 2)


if __name__ == "__main__":
    unittest.main()
