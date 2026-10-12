"""Integration, independent replay, fresh-cohort and confirmatory-gate checks."""
import copy
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np
from E055_stress_capture_recovery import model as pulse, audit_model as pulse_audit
from E056_sign_magnitude_substitution import model as factorial, audit_model as factorial_audit
from E057_fresh_capture_confirmation import data, source_model, source_audit, inference, audit
from E057_fresh_capture_confirmation.plan import HERE, settings


class ConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=settings('fixture');c=cls.cfg;cls.block=900041
        config=source_model.base.Config(**c['config'])
        cls.acquisition=source_model.acquisition.teach(cls.block,config)
        acquired,_=source_audit.source_record(cls.acquisition,cls.block,c['config'])
        initial=acquired[:,None].repeat(config.recipients,axis=1)
        incoming=np.stack((initial,initial)); cls.boundaries=[]; cls.replayed=[]
        for g in (1,2):
            raw=source_model.rebuild(incoming,cls.block,g,config,c['cycle'])
            other=source_audit.rebuild(incoming,cls.block,g,c['config'],c['cycle'])
            cls.boundaries.append(raw);cls.replayed.append(other);incoming=raw['outgoing'].copy()
        cls.records=np.concatenate((source_model.base.decode(initial)[None],source_model.base.decode(incoming)))
        cls.body=pulse.develop(cls.records,cls.block,c['body'])
        cls.outgoing=pulse.transmit(cls.body,c['body'])
        cls.paired=dict(packets=np.stack((cls.outgoing['packets'][:,:2],cls.outgoing['packets'][:,2:4]),axis=1))
        cls.inter=factorial.intervene(cls.paired['packets'])
        cls.fresh=factorial.assay(cls.inter['packets'],cls.block,c['reader'])
        cls.cases,cls.controls=factorial.diagnostics(cls.paired,cls.inter,cls.fresh,c['reader'])
        cls.cases.update(audit.added_cases(cls.body,cls.outgoing,[r['mean_ports'] for r in cls.boundaries],c))

    def test_01_fresh_register(self):
        spec=json.loads((HERE/'SOURCE_DATA.json').read_text())
        self.assertEqual(spec['blocks'],list(range(38000,38032)))
        self.assertFalse(set(spec['blocks'])&set(spec['prior_block_ids']))
        self.assertIsNone(data.receipt('scientific'))

    def test_02_literal_settings(self):
        for mode in ('fixture','benchmark','scientific'):audit.validate_settings(settings(mode))
        bad=settings('scientific');bad['body']['pulse_amplitude']=1.1
        with self.assertRaises(AssertionError):audit.validate_settings(bad)

    def test_03_source_independent_equations(self):
        for raw,replayed in zip(self.boundaries,self.replayed):data.compare(raw,replayed)

    def test_04_source_matches_original_branches(self):
        reference=data.receipt('fixture')
        data.compare(self.acquisition,data.load(reference/'source_900041.npz'))
        for g,raw in enumerate(self.boundaries,1):data.legacy_boundary(reference,self.block,g,raw)

    def test_05_packet_only_successor(self):
        self.assertEqual(self.boundaries[1]['incoming'].tobytes(),self.boundaries[0]['outgoing'].tobytes())
        self.assertFalse(np.shares_memory(self.boundaries[1]['incoming'],self.boundaries[0]['end']))

    def test_06_shared_birth_and_distinct_noise(self):
        raw=self.boundaries[0]
        self.assertTrue(np.array_equal(raw['birth'][0],raw['birth'][1]))
        self.assertTrue(np.array_equal(raw['birth'][:,:,:,0],raw['birth'][:,:,:,1]))
        self.assertEqual(raw['noise_moments'][0,2],raw['noise_moments'][0,4])
        self.assertNotEqual(raw['noise_moments'][1,2],raw['noise_moments'][1,4])

    def test_07_independent_pulse_and_capture(self):
        other=pulse_audit.develop(self.records,self.block,self.cfg['body'])
        data.compare(self.body,other)
        data.compare(self.outgoing,pulse_audit.transmit(other,self.cfg['body']))

    def test_08_independent_substitutions_and_reader(self):
        other=factorial_audit.intervene(self.paired['packets']);data.compare(self.inter,other)
        data.compare(self.fresh,factorial_audit.assay(other['packets'],self.block,self.cfg['reader']))

    def test_09_capture_mapping_and_controls(self):
        for t,p in np.ndindex(2,2):
            self.assertTrue(np.array_equal(self.paired['packets'][:,t,p],self.outgoing['packets'][:,2*t+p]))
        self.assertTrue(self.controls['pass'])
        self.assertTrue(all(audit.body_controls(self.body,self.outgoing,self.cfg).values()))

    def test_10_source_corruption_rejected(self):
        bad={k:v.copy() for k,v in self.boundaries[0].items()};bad['outgoing'].flat[0]^=1
        with self.assertRaises(AssertionError):data.compare(self.replayed[0],bad)

    def test_11_nonfinite_data_rejected_and_exclusive_output(self):
        with tempfile.TemporaryDirectory(dir=HERE/'analysis') as directory:
            path=Path(directory)/'data.npz'
            with path.open('xb') as f:np.savez(f,x=np.array([np.nan]))
            with self.assertRaises(AssertionError):data.load(path)
            with self.assertRaises(FileExistsError):data.save(path,dict(x=np.zeros(2)))

    def test_12_independent_block_statistics(self):
        cases=[copy.deepcopy(self.cases) for _ in range(3)]
        cases[1]['fresh_both'][1,0,1,1]=True
        cases[2]['fresh_both'][1,1,1,1]=True
        s=inference.analyze(cases,[self.controls]*3,'scientific')
        audit.check_summary(s,cases,[self.controls]*3,'scientific')
        self.assertEqual(len(s['statistics']['primary/early_pulse_loss']['block_means']),3)

    def positive_cases(self):
        cases=[copy.deepcopy(self.cases) for _ in range(4)]
        for c in cases:
            for t,a in np.ndindex(2,4):
                count=((6,2,2,5),(6,5,5,6))[t][a]
                c['fresh_both'][1,t,a,1]=np.array([True]*count+[False]*(8-count)).reshape(4,2)
        return cases

    def test_13_known_joint_positive_claim(self):
        cases=self.positive_cases();s=inference.analyze(cases,[self.controls]*4,'scientific')
        self.assertEqual(s['status'],'CONFIRMED')
        for name,value in dict(early_pulse_loss=.5,timing_benefit=.375,magnitude_on_pulse_signs=.375,magnitude_on_sham_signs=.5).items():
            self.assertEqual(s['statistics']['primary/'+name]['mean'],value)
            self.assertEqual(s['statistics']['primary/'+name]['confidence'],.9875)
        audit.check_summary(s,cases,[self.controls]*4,'scientific')

    def test_14_one_failed_requirement_blocks_confirmation(self):
        cases=self.positive_cases()
        for c in cases:c['fresh_both'][1,1,:,1]=c['fresh_both'][1,0,:,1]
        s=inference.analyze(cases,[self.controls]*4,'scientific')
        self.assertEqual(s['status'],'NOT_CONFIRMED');self.assertFalse(s['primary_confirmed'])
        self.assertEqual(s['primary_effects']['timing_benefit'],'UNRESOLVED')

    def test_15_technical_and_control_failures_suppress_claims(self):
        cases=self.positive_cases()
        for mode,controls,status in [('fixture',[self.controls]*4,'TECHNICAL_ONLY'),
            ('scientific',[dict(self.controls,**{'pass':False})]*4,'NUMERICAL_CONTROL_FAILURE')]:
            s=inference.analyze(cases,controls,mode)
            self.assertEqual(s['status'],status);self.assertIsNone(s['primary_confirmed'])
            self.assertTrue(all(v is None for v in s['primary_effects'].values()))

    def test_16_strict_zero_and_summary_corruption(self):
        self.assertEqual(inference.classify([0.,.2]),'UNRESOLVED')
        self.assertEqual(inference.classify([-.1,0.]),'UNRESOLVED')
        self.assertEqual(inference.classify([-.2,-.1]),'NEGATIVE_EFFECT')
        cases=self.positive_cases();s=inference.analyze(cases,[self.controls]*4,'scientific')
        s['statistics']['primary/timing_benefit']['mean']+=.01
        with self.assertRaises(AssertionError):audit.check_summary(s,cases,[self.controls]*4,'scientific')


if __name__=='__main__':unittest.main()
