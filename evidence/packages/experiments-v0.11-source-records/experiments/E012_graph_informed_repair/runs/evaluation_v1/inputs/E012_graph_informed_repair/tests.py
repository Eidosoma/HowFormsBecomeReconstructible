"""Disposable checks of causal inputs, graph ablation and paired packet dynamics."""
from dataclasses import replace
import unittest
import numpy as np
import design as d
import audit


class Source(dict):
    @property
    def files(self):return list(self)


class GraphRepairChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=replace(d.CFG,formation=8,observation_window=4,capture=5,read=7)
        cls.block=900413
        cls.source=Source(d.make_source(cls.block,cls.cfg))
        cls.a=d.read(cls.source["repair_packets"],cls.block,"A",cls.source["graph_neighbors"],cls.cfg)

    def test_exact_menu_and_paired_packet_only_dynamics(self):
        audit.old.check_source(self.source,self.block)
        packets=self.source["repair_packets"].copy();packets[:,5]=packets[:,4]
        births=[]
        for body in ("A","B"):
            raw=d.read(packets,self.block,body,self.source["graph_neighbors"],self.cfg)
            np.testing.assert_array_equal(raw["end"][:,:,4],raw["end"][:,:,5]);births.append(raw["birth"])
            field=np.frombuffer(raw["packets"].tobytes(),dtype="<f8").reshape(4,8,12,16,16)
            v=np.repeat(raw["birth"],12,axis=2);ema=v.copy();ref=v.copy()
            random=audit.old.seed("E009",self.block,body,"read")
            for _ in range(7):
                noise=random.standard_normal((4,8,1,16,16))
                if body=="A":neighbor=(np.roll(v,1,-1)+np.roll(v,-1,-1)+np.roll(v,1,-2)+np.roll(v,-1,-2))/4
                else:
                    flat=v.reshape(4,8,12,256);neighbor=np.empty_like(flat)
                    for node,js in enumerate(self.source["graph_neighbors"]):neighbor[...,node]=sum(flat[...,int(j)] for j in js)/4
                    neighbor=neighbor.reshape(v.shape)
                drift=v-v**3+field+neighbor-v;drift-=drift.mean(axis=(-2,-1),keepdims=True)
                noise*=self.cfg.sigma;noise-=noise.mean(axis=(-2,-1),keepdims=True)
                v=np.clip(v+self.cfg.dt*drift+noise,-2,2);ema=.9*ema+.1*v;ref+=self.cfg.rho*(v-ref)
            np.testing.assert_allclose(raw["end"],np.stack((v,ema,ref),axis=3),rtol=1e-12,atol=1e-12)
        self.assertFalse(np.array_equal(*births))
        empty=d.previous.make_menu(np.zeros_like(self.source["acquired"]),900414)
        for f in range(4):
            np.testing.assert_array_equal(np.flatnonzero(empty["repair_restoration"][f,empty["repair_heuristic"][f]]),np.flatnonzero(empty["repair_injury"][f])[:64])

    def test_all_foreign_observer_and_independent_features(self):
        observed=d.observe(self.a,self.source["prototype"])
        independent=audit.observe(self.a,self.source["prototype"])
        for key in observed:np.testing.assert_allclose(observed[key],independent[key],rtol=0,atol=1e-12)
        x=d.features(self.source,self.a,observed["observed"])
        np.testing.assert_allclose(x,audit.features(self.source,self.a,observed["observed"]),rtol=0,atol=1e-12)
        self.assertEqual(x.shape,(4,8,23))
        # Removing the change of graph removes every added graph feature.
        native_source=self.source.copy()
        native_source["graph_neighbors"]=d.previous.old.adjacency(d.previous.old.native_edges())
        native=d.features(native_source,self.a,observed["observed"])
        np.testing.assert_array_equal(x[:,:,:17],native[:,:,:17])
        np.testing.assert_allclose(native[:,:,17:],0.,rtol=0,atol=1e-12)
        self.assertGreater(float(abs(x[:,:,17:]).max()),1e-6)

    def test_residual_zero_ties_centering_and_policy_budget(self):
        random=audit.old.seed("E012",900414,"fixture")
        x=random.normal(size=(3,4,8,23));a=np.zeros((3,4,8));h=np.full((3,4),7)
        models={name:d.fit(d.center_menu(x)[...,:count],np.zeros((3,4,8))) for name,count in (("graph",23),("native",17))}
        selected=d.select(x,a,h,models)
        np.testing.assert_array_equal(selected["choices"][:,:,:3],0)
        np.testing.assert_array_equal(selected["choices"][:,:,3],7)
        np.testing.assert_array_equal(selected["weights"].sum(axis=3),1)
        a[:,:,2]=.05
        selected=d.select(x,a,h,models)
        np.testing.assert_array_equal(selected["choices"][:,:,:3],2)
        shifted=d.select(x+random.normal(size=(3,4,1,23)),a+random.normal(size=(3,4,1)),h,models)
        np.testing.assert_array_equal(selected["choices"],shifted["choices"])
        np.testing.assert_allclose(selected["predicted"],shifted["predicted"],atol=1e-12)
        self.assertFalse(set(d.IDS)&set(d.DEV_IDS))
        self.assertFalse(set(d.IDS+d.DEV_IDS)&{900412,900413,900414})


if __name__=="__main__":unittest.main(verbosity=2)
