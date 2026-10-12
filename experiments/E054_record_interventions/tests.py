"""Structural invariants, independent replay, fault injection and launch refusal."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import cap_cpus, rng, sha, dump
from E054_record_interventions import model, audit_model, inference, audit, data
from E054_record_interventions.plan import HERE, settings
from E054_record_interventions.workflow import predecessor_gate
import numpy as np


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cap_cpus(1); stream = rng('E054', 'synthetic_validation')
        cls.records = stream.uniform(-1, 1, (5, 4, 1, 2, 16, 16))
        cls.records[stream.random(cls.records.shape) < .2] = 0
        cls.records[0, 0, 0] = 0
        cls.repair = (stream.random(cls.records.shape) < .2) & (cls.records != 0)
        cls.repair[0] = False
        cls.inter = model.intervene(cls.records, cls.repair, 900041)
        cls.cfg = dict(settings('benchmark'), read_steps=8, settling_steps=4, observe_steps=4)
        cls.raw = model.assay(cls.inter, 900041, cls.cfg)

    def test_01_signed_graph_torus(self):
        w = np.ones((2, 16, 16)); expected = np.array([512, 1, 257, 0, 256, 4, 4], np.int64)
        audit_model.equal(model.graph(w), expected); audit_model.equal(audit_model.graph(w), expected)

    def test_02_bridge_flip_introduces_no_cycle(self):
        w = np.zeros((2, 16, 16)); w[0, 0, 0] = -1
        self.assertEqual(model.graph(w)[2], 0); self.assertEqual(model.graph(w)[3], 0)

    def test_03_single_negative_plaquette_and_switch(self):
        w = np.zeros(512); w[[0, 16, 256, 257]] = 1; w[0] = -1
        self.assertEqual(model.graph(w.reshape(2, 16, 16))[3], 1)
        s = np.ones(256); s[0] = -1; switched = w*s[model.U]*s[model.V]
        audit_model.equal(model.graph(w.reshape(2, 16, 16)), model.graph(switched.reshape(2, 16, 16)))

    def test_04_interventions_independently_recreated(self):
        audit_model.interventions(self.inter, self.records, self.repair, 900041)

    def test_05_anchored_eight_cells(self):
        self.assertTrue((self.inter['cell_signs'][..., model.P.any(axis=0)] == 1).all())
        self.assertTrue(((self.inter['cell_signs'] < 0).sum(axis=(-2, -1)) == 8).all())

    def test_06_double_endpoint_flip_is_unchanged(self):
        s = np.ones(256); s[[0, 1]] = -1
        self.assertEqual(s[model.U[0]]*s[model.V[0]], 1)

    def test_07_matched_sign_dose(self):
        w = self.inter['weights']; changed = (w[:, 4] != w[:, 0]).reshape(5, 4, 1, 512)
        for b in range(8):
            audit_model.equal((changed & (self.inter['bins'] == b)).sum(axis=-1),
                (self.inter['isolated'] & (self.inter['bins'] == b)).sum(axis=-1))

    def test_08_magnitude_only_invariants(self):
        for h, f, r in np.ndindex(5, 4, 1):
            old = self.records[h, f, r]; new = self.inter['weights'][h, 2, f, r]
            np.testing.assert_array_equal(np.sign(old), np.sign(new))
            for sign in (-1, 1): np.testing.assert_array_equal(np.sort(abs(old[old*sign > 0])), np.sort(abs(new[new*sign > 0])))

    def test_09_repair_matching_and_no_acquisition_tags(self):
        a, b = self.inter['delete_returning'], self.inter['delete_other']
        self.assertFalse(a[0].any()); self.assertFalse(b[0].any())
        self.assertFalse((a & ~self.repair.reshape(5, 4, 1, 512)).any())
        self.assertFalse((b & self.repair.reshape(5, 4, 1, 512)).any())
        for k in range(8): audit_model.equal((a & (self.inter['bins'] == k)).sum(-1), (b & (self.inter['bins'] == k)).sum(-1))

    def test_10_deletion_survivors_and_restoration(self):
        mask = self.inter['isolated'].reshape(self.records.shape)
        np.testing.assert_array_equal(self.inter['weights'][:, 6][~mask], self.records[~mask])
        audit_model.equal(self.inter['weights'][:, 7], self.records)

    def test_11_source_fixture_independent_extraction(self):
        expected = data.source('fixture', 900041); run, _ = data.receipt('fixture')
        independent = audit_model.source(run, 900041)
        for k in expected: audit_model.equal(expected[k], independent[k])

    def test_12_fresh_reader_full_independent_replay(self):
        replay = audit_model.replay(self.inter, 900041, self.cfg)
        for k in self.raw: audit_model.equal(self.raw[k], replay[k])
        for k, v in model.scores(self.raw).items(): audit_model.equal(v, audit_model.scores(replay)[k])

    def test_13_normalization_symmetry_and_controls(self):
        values, controls = inference.diagnostics(self.inter, self.raw)
        independent, expected = audit.independent_diagnostics(self.inter, self.raw)
        self.assertEqual(controls, expected); self.assertTrue(controls['pass'])
        for k in values: audit_model.equal(values[k], independent[k])
        self.assertEqual(controls['scale_output_error'], 0.)

    def test_14_signed_transfer_detects_reversal(self):
        means = np.zeros((55, 4, 1, 2, 3, 2))
        for f, rule in enumerate((1, -1, 1, -1)):
            for c, cue in enumerate((1, -1)):
                means[:, f, :, c, :, 0] = rule*cue; means[:, f, :, c, :, 1] = -rule*cue
        result = model.scores(dict(mean_ports=means)); self.assertTrue(result['both'].all())
        np.testing.assert_array_equal(result['aligned_transfer'], 1)
        result = model.scores(dict(mean_ports=-means)); self.assertFalse(result['both'].any())
        np.testing.assert_array_equal(result['aligned_transfer'], -1)

    def test_15_tampered_intervention_rejected(self):
        bad = {k:v.copy() for k, v in self.inter.items()}; bad['weights'][0, 0, 0, 0, 0, 0, 0] = .7
        with self.assertRaises(AssertionError): audit_model.interventions(bad, self.records, self.repair, 900041)

    def test_16_scale_underflow_rejected(self):
        w = np.zeros_like(self.records); w[0, 0, 0, 0, 0, 0] = np.nextafter(0., 1.)
        with self.assertRaisesRegex(AssertionError, 'support'): model.intervene(w, np.zeros_like(w, bool), 900041)

    def test_17_inference_and_control_failure_suppression(self):
        measures, controls = inference.diagnostics(self.inter, self.raw)
        c = dict(**model.scores(self.raw), **measures)
        changed = {k:v.copy() for k, v in c.items()}
        changed['both'][1, 0] = True
        changed['both'][1, 2] = False
        changed['aligned_transfer'][1, 2] *= -1
        cases = [c, changed]
        result = inference.analyze(cases, [controls, controls], 'fixture')
        audit.check_summary(result, cases, [controls, controls], 'fixture')
        expected = [float((x['both'][1, 2, ..., 1].astype(float)-x['both'][1, 0, ..., 1]).mean()) for x in cases]
        self.assertEqual(result['statistics']['primary/magnitude_permute']['block_means'], expected)
        self.assertTrue(all(x is None for x in result['primary_classifications'].values()))
        bad = dict(controls, scale_output_error=.1, **{'pass':False})
        result = inference.analyze(cases, [bad, bad], 'scientific')
        self.assertEqual(result['status'], 'NUMERICAL_CONTROL_FAILURE')
        audit.check_summary(result, cases, [bad, bad], 'scientific')
        self.assertTrue(all(x is None for x in result['primary_classifications'].values()))

    def test_18_missing_predecessor_refuses_without_waiting(self):
        with tempfile.TemporaryDirectory(dir=HERE/'analysis', prefix='gate_check_') as tmp:
            with self.assertRaisesRegex(RuntimeError, 'E053 completion'): predecessor_gate(Path(tmp))

    def test_19_predecessor_receipt_chain_and_tamper(self):
        with tempfile.TemporaryDirectory(dir=HERE/'analysis', prefix='gate_check_') as tmp:
            root = Path(tmp); base = root/'E053_combined_numerical_confirmation'
            run = base/'runs/robustness_v1'; run.mkdir(parents=True)
            job = base/'jobs/robustness_v1'; job.mkdir(parents=True)
            (base/'analysis').mkdir()
            complete = run/'COMPLETE.json'; audited = run/'INDEPENDENT_AUDIT.json'
            dump(complete, dict(status='COMPLETE'))
            dump(audited, dict(status='PASS', complete_sha256=sha(complete),
                all_dynamics_channels_and_assays_replayed=True, all_mechanism_diagnostics_replayed=True))
            dump(job/'status.json', dict(status='COMPLETE', complete_sha256=sha(complete), audit_sha256=sha(audited)))
            dump(base/'analysis/closeout_v1.json', dict(status='PASS', figure_inspected=True,
                evidence_sha256={str(p.relative_to(root)):sha(p) for p in (complete, audited)}))
            self.assertEqual(len(predecessor_gate(root)), 4)
            dump(complete, dict(status='COMPLETE', changed=True))
            with self.assertRaises(AssertionError): predecessor_gate(root)


if __name__ == '__main__': unittest.main(verbosity=2)
