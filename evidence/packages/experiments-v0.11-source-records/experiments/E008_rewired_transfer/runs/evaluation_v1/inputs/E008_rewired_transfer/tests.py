"""Structural invariants and scalar/read oracles on disposable cases only."""
from dataclasses import replace
import unittest
import numpy as np
import design as d


class RewiringChecks(unittest.TestCase):
    def test_exact_fraction_degree_distance_and_replay(self):
        for block in (900009,900010,900011):
            graph = d.rewire(block)
            original = set(map(tuple,graph["graph_original_edges"].tolist()))
            edges = set(map(tuple,graph["graph_edges"].tolist()))
            self.assertEqual(len(original),512); self.assertEqual(len(edges),512)
            self.assertEqual(len(original-edges),128); self.assertEqual(len(edges-original),128)
            self.assertTrue(all(d.distance(a,b)>=4 for a,b in edges-original))
            degree = np.bincount(np.array(sorted(edges)).ravel(),minlength=256)
            np.testing.assert_array_equal(degree,np.full(256,4))
            self.assertTrue(d.connected(edges))
            replay = original.copy()
            for removed_a,removed_b,added_a,added_b in graph["graph_swaps"]:
                replay.remove(tuple(removed_a)); replay.remove(tuple(removed_b))
                replay.add(tuple(added_a)); replay.add(tuple(added_b))
            self.assertEqual(replay,edges)
            again = d.rewire(block)
            for key in graph: np.testing.assert_array_equal(graph[key],again[key])

    def test_graph_step_scalar_oracle_and_unrewired_native(self):
        random = np.random.default_rng(900009)
        v = random.normal(size=(2,16,16))*.3; field = random.normal(size=v.shape)*.2
        noise = random.normal(size=v.shape); ema = .9*v; ref = .5*v
        graph = d.rewire(900009)["graph_neighbors"]
        neighbors = np.zeros_like(v)
        for k in range(2):
            for i in range(256):
                y,x = divmod(i,16)
                neighbors[k,y,x] = sum(v[k,j//16,j%16] for j in graph[i])/4
        drift = v-v**3+field+neighbors-v
        drift -= drift.mean(axis=(-2,-1),keepdims=True)
        expected = np.clip(v+.2*drift+.3*(noise-noise.mean(axis=(-2,-1),keepdims=True)),-2,2)
        got = d.step(v,ema,ref,field,noise,"B",graph)
        np.testing.assert_allclose(got[0],expected,rtol=1e-14,atol=1e-14)
        np.testing.assert_allclose(got[1],.9*ema+.1*expected,atol=1e-14)
        np.testing.assert_allclose(got[2],ref+.002*(expected-ref),atol=1e-14)
        unchanged = d.adjacency(d.native_edges())
        actual = d.step(v,ema,ref,field,noise,"B",unchanged)
        native = d.step(v,ema,ref,field,noise,"A")
        for a,b in zip(actual,native): np.testing.assert_allclose(a,b,rtol=1e-14,atol=1e-14)

    def test_source_read_identical_to_e003_and_target_uses_saved_graph(self):
        cfg = replace(d.CFG,formation=8,observation_window=4,capture=5,read=7,challenge_time=3)
        source = d.make_source(900009,cfg)
        a = d.read(source["acquired"],900009,"A",d.TEST,source["graph_neighbors"],cfg)
        original = d.base.read(source["acquired"],900009,"A",d.TEST,cfg)
        for key in original: np.testing.assert_array_equal(a[key],original[key])
        b = d.read(source["acquired"],900009,"B",d.TEST,source["graph_neighbors"],cfg)
        np.testing.assert_array_equal(a["packets"],b["packets"])
        self.assertFalse(np.array_equal(a["birth"],b["birth"]))
        np.testing.assert_array_equal(b["applied_neighbors"],source["graph_neighbors"])
        np.testing.assert_array_equal(b["after_damage"],np.where(b["body_masks"],-b["before_damage"],b["before_damage"]))
        source["prototype"][:] = 999
        again = d.read(source["acquired"],900009,"B",d.TEST,source["graph_neighbors"],cfg)
        for key in b: np.testing.assert_array_equal(b[key],again[key])
        self.assertEqual(d.DEVELOPMENT,d.base.DEVELOPMENT)
        self.assertEqual(d.TEST,d.base.TEST)
        self.assertFalse(set(d.DEV_IDS)&set(d.TEST_IDS))


if __name__=="__main__": unittest.main(verbosity=2)
