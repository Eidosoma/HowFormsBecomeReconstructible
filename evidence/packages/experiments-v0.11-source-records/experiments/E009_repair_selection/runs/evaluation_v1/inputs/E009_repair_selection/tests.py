"""Disposable fixtures for external repair, paired readers and frozen decisions."""
from dataclasses import replace
import json
import unittest
import numpy as np
import design as d
import audit


class RepairChecks(unittest.TestCase):
    def test_exact_menu_backup_contract_and_seed_replay(self):
        cfg=replace(d.CFG,formation=8,observation_window=4,capture=5)
        for block in (900110,900111):
            source=d.make_source(block,cfg)
            # The audit normally accepts an NpzFile. Supply its file-key interface.
            class Source(dict):
                @property
                def files(self):return list(self)
            audit.check_source(Source(source),block)
            again=d.make_menu(source["acquired"],block)
            for key,value in again.items():np.testing.assert_array_equal(value,source[key])
            # A zero backup gives the heuristic many ties; lower site index wins.
            empty=d.make_menu(np.zeros_like(source["acquired"]),block)
            for f in range(4):
                expected=np.flatnonzero(empty["repair_injury"][f])[:64]
                actual=np.flatnonzero(empty["repair_restoration"][f,empty["repair_heuristic"][f]])
                np.testing.assert_array_equal(actual,expected)

    def test_packet_only_read_and_independent_short_dynamics(self):
        cfg=replace(d.CFG,formation=8,observation_window=4,capture=5,read=7)
        block=900110;source=d.make_source(block,cfg)
        packets=source["repair_packets"].copy();packets[:,5]=packets[:,4]
        results={}
        for body in ("A","B"):
            raw=d.read(packets,block,body,source["graph_neighbors"],cfg)
            results[body]=raw
            # Equal packets under paired futures must have exactly equal endpoints.
            np.testing.assert_array_equal(raw["end"][:,:,4],raw["end"][:,:,5])
            field=np.frombuffer(raw["packets"].tobytes(),dtype="<f8").reshape(4,8,12,16,16)
            v=np.repeat(raw["birth"],12,axis=2);ema=v.copy();ref=v.copy()
            random=audit.seed("E009",block,body,"read")
            for _ in range(7):
                noise=random.standard_normal((4,8,1,16,16))
                if body=="A":neighbors=(np.roll(v,1,-1)+np.roll(v,-1,-1)+np.roll(v,1,-2)+np.roll(v,-1,-2))/4
                else:
                    flat=v.reshape(4,8,12,256);neighbors=np.empty_like(flat)
                    for node,js in enumerate(source["graph_neighbors"]):neighbors[:,:,:,node]=sum(flat[:,:,:,int(j)] for j in js)/4
                    neighbors=neighbors.reshape(v.shape)
                drift=v-v**3+field+neighbors-v
                drift-=drift.mean(axis=(-2,-1),keepdims=True)
                noise=cfg.sigma*noise;noise-=noise.mean(axis=(-2,-1),keepdims=True)
                v=np.clip(v+cfg.dt*drift+noise,-2,2)
                ema=.9*ema+.1*v;ref+=cfg.rho*(v-ref)
            np.testing.assert_allclose(raw["end"],np.stack((v,ema,ref),axis=3),rtol=1e-12,atol=1e-12)
        self.assertFalse(np.array_equal(results["A"]["birth"],results["B"]["birth"]))
        source["prototype"][:]=999
        again=d.read(packets,block,"B",source["graph_neighbors"],cfg)
        for key in again:np.testing.assert_array_equal(again[key],results["B"][key])

    def test_frozen_selector_specificity_ties_and_same_cost_features(self):
        self.assertEqual(audit.sha(d.MODEL_PATH),d.MODEL_SHA)
        models=json.loads(d.MODEL_PATH.read_text())
        prototype=audit.seed("E009",900111,"fixture").normal(size=(4,16,16))
        a=np.full((4,12,4),.6);heuristic=np.array([7,6,5,4])
        tied=d.select(prototype,a,heuristic,models)
        np.testing.assert_array_equal(tied["choices"][:,:2],np.zeros((4,2),dtype=int))
        np.testing.assert_array_equal(tied["choices"][:,2],heuristic)
        np.testing.assert_array_equal(tied["weights"].sum(axis=-1),np.ones((4,4)))
        # Own agreement alone would select option 0; specificity selects option 1.
        a[:,4,:2]=[.8,.79];a[:,5,:2]=[.7,.5]
        out=d.select(prototype,a,heuristic,models)
        np.testing.assert_array_equal(out["choices"][:,1],np.ones(4,dtype=int))
        coef=np.array(models["causal"]["coefficients"])/np.array(models["causal"]["scale"])[:,None]
        delta=a[:,4:]-a[:,4:5]
        # Fixed descriptors cancel between menu options; only last four response features vary.
        expected=delta@coef[-4:]
        np.testing.assert_allclose(out["predicted"][:,4:]-out["predicted"][:,4:5],expected,atol=1e-12)
        predicted=out["predicted"][:,4:,0]-out["predicted"][:,4:,1]
        for f in range(4):self.assertEqual(int(out["choices"][f,0]),list(predicted[f]).index(max(predicted[f])))
        self.assertFalse(set(d.IDS)&{900109,900110,900111})


if __name__=="__main__":unittest.main(verbosity=2)
