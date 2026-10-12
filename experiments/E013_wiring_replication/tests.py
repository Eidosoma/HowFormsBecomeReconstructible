"""Disposable replication identity and incorrect-graph control fixtures."""
from dataclasses import replace
import json
import unittest
import numpy as np
import design as d
import audit


class Source(dict):
    @property
    def files(self):return list(self)


class ReplicationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=replace(d.CFG,formation=8,observation_window=4,capture=5,read=7)
        cls.block=900514
        cls.source=Source(d.make_source(cls.block,cls.cfg))
        cls.a=d.read(cls.source["repair_packets"],cls.block,"A",cls.source["graph_neighbors"],cls.cfg)
        cls.observed=d.observe(cls.a,cls.source["prototype"])["observed"]
        cls.models=json.loads(d.MODEL_PATH.read_text())

    def test_unchanged_original_source_and_independent_wrong_graph_stream(self):
        original=d.previous.make_source(self.block,self.cfg)
        for key,value in original.items():np.testing.assert_array_equal(self.source[key],value)
        for block,source in ((self.block,self.source),(900515,Source(d.make_source(900515,self.cfg)))):
            audit.check_source(source,block)
            self.assertEqual(int(source["wrong_graph_seed"]),1000000+block)
        self.assertEqual(audit.sha(d.MODEL_PATH),d.MODEL_SHA)
        self.assertFalse(set(d.IDS)&set(d.previous.IDS))
        self.assertFalse(set(d.IDS)&{900513,900514,900515})
        self.assertEqual(len(d.IDS),128)

    def test_only_six_features_change_and_body_keeps_actual_graph(self):
        x,wrong=d.features_pair(self.source,self.a,self.observed)
        np.testing.assert_array_equal(x[...,:17],wrong[...,:17])
        np.testing.assert_allclose(x,audit.features(self.source,self.a,self.observed),rtol=0,atol=1e-12)
        substitute=dict(self.source);substitute["graph_neighbors"]=self.source["wrong_graph_neighbors"]
        np.testing.assert_allclose(wrong,audit.features(substitute,self.a,self.observed),rtol=0,atol=1e-12)
        self.assertGreater(float(abs(x[...,17:]-wrong[...,17:]).max()),1e-6)
        before=d.read(self.source["repair_packets"],self.block,"B",self.source["graph_neighbors"],self.cfg)
        changed=dict(self.source);changed["wrong_graph_neighbors"]=np.roll(self.source["wrong_graph_neighbors"],1,axis=0)
        after=d.read(changed["repair_packets"],self.block,"B",changed["graph_neighbors"],self.cfg)
        for key in before:np.testing.assert_array_equal(before[key],after[key])
        np.testing.assert_array_equal(before["applied_neighbors"],self.source["graph_neighbors"])
        self.assertFalse(np.array_equal(before["applied_neighbors"],self.source["wrong_graph_neighbors"]))

    def test_original_policies_bit_exact_and_identical_graph_control(self):
        x,wrong=d.features_pair(self.source,self.a,self.observed)
        a=(self.observed[:,4:,0]-self.observed[:,4:,1])[None]
        heuristic=self.source["repair_heuristic"][None]
        original=d.previous.select(x[None],a,heuristic,self.models)
        result=d.select(x[None],wrong[None],a,heuristic,self.models)
        np.testing.assert_array_equal(original["predicted"],result["predicted"][:,:,:3])
        np.testing.assert_array_equal(original["choices"],result["choices"][:,:,:4])
        np.testing.assert_array_equal(original["weights"][:,:,:4],result["weights"][:,:,:4])
        np.testing.assert_array_equal(original["weights"][:,:,4],result["weights"][:,:,5])
        np.testing.assert_array_equal(result["weights"].sum(axis=3),1.)
        same=d.select(x[None],x[None],a,heuristic,self.models)
        np.testing.assert_array_equal(same["predicted"][:,:,0],same["predicted"][:,:,3])
        np.testing.assert_array_equal(same["choices"][:,:,0],same["choices"][:,:,4])
        tied=d.select(np.zeros((1,4,8,23)),np.zeros((1,4,8,23)),np.zeros((1,4,8)),heuristic,self.models)
        np.testing.assert_array_equal(tied["choices"][:,:,[0,1,2,4]],0)
        np.testing.assert_array_equal(tied["choices"][:,:,3],heuristic)


if __name__=="__main__":unittest.main(verbosity=2)
