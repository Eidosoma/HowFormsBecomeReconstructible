"""Disposable budget/selection, dynamics and all-foreign observer fixtures."""
from dataclasses import replace
import unittest
import numpy as np
import design as d
import audit


class StrengthChecks(unittest.TestCase):
    def test_budget_backup_rank_ties_and_selection_independence(self):
        cfg=replace(d.CFG,formation=8,observation_window=4,capture=5)
        for block in (900312,900313):
            source=d.make_source(block,cfg)
            audit.inspect_source(source,block)
            again=d.make_repairs(source["acquired"],block)
            for key,v in again.items():np.testing.assert_array_equal(v,source[key])
            # Alter every other founder's record; founder zero's repairs are unchanged.
            changed=source["acquired"].copy();changed[1:]=d.base.tissue.pack(np.full((3,2,16,16),.123))
            independent=d.make_repairs(changed,block)
            np.testing.assert_array_equal(independent["repair_restoration"][0],source["repair_restoration"][0])
            np.testing.assert_array_equal(independent["repair_packets"][0,6:],source["repair_packets"][0,6:])
            zeros=d.make_repairs(d.base.tissue.pack(np.full((4,2,16,16),.2)),block)
            for f in range(4):
                expected=np.flatnonzero(zeros["repair_injury"][f])[:64]
                for j in (0,1):np.testing.assert_array_equal(np.flatnonzero(zeros["repair_restoration"][f,j]),expected)
            with self.assertRaisesRegex(ValueError,"zero backup"):
                d.make_repairs(np.zeros_like(changed),block)
            fields=d.base.tissue.unpack(source["repair_packets"]).reshape(4,15,256)
            clean=d.base.tissue.unpack(source["acquired"][:,0]).reshape(4,256)
            for f in range(4):
                surviving=~source["repair_injury"][f]
                for c in range(6,15):
                    np.testing.assert_array_equal(fields[f,c,surviving],clean[f,surviving])
                    j=(c-6)%3;selected=source["repair_restoration"][f,j]
                    if c>=9:
                        amplitude=.15 if c<12 else .40
                        np.testing.assert_array_equal(abs(fields[f,c,selected]),np.full(64,amplitude))
                        np.testing.assert_array_equal(fields[f,c,selected]>0,clean[f,selected]>0)
        self.assertFalse(set(d.IDS)&{900311,900312,900313})

    def test_packet_only_paired_reader_against_short_oracle(self):
        cfg=replace(d.CFG,formation=8,observation_window=4,capture=5,read=7)
        block=900312;source=d.make_source(block,cfg)
        packets=source["repair_packets"].copy();packets[:,8]=packets[:,6]
        results={}
        for body in ("A","B"):
            raw=d.read(packets,block,body,source["graph_neighbors"],cfg);results[body]=raw
            np.testing.assert_array_equal(raw["end"][:,:,6],raw["end"][:,:,8])
            field=np.frombuffer(raw["packets"].tobytes(),dtype="<f8").reshape(4,8,15,16,16)
            v=np.repeat(raw["birth"],15,axis=2);ema=v.copy();ref=v.copy()
            random=audit.seed("E011",block,body,"read")
            for _ in range(7):
                noise=cfg.sigma*random.standard_normal((4,8,1,16,16))
                noise-=noise.mean(axis=(-2,-1),keepdims=True)
                if body=="A":neighbors=(np.roll(v,1,-1)+np.roll(v,-1,-1)+np.roll(v,1,-2)+np.roll(v,-1,-2))/4
                else:
                    flat=v.reshape(4,8,15,256);neighbors=np.empty_like(flat)
                    for node,js in enumerate(source["graph_neighbors"]):neighbors[:,:,:,node]=sum(flat[:,:,:,int(j)] for j in js)/4
                    neighbors=neighbors.reshape(v.shape)
                drift=v-v**3+field+neighbors-v;drift-=drift.mean(axis=(-2,-1),keepdims=True)
                v=np.clip(v+cfg.dt*drift+noise,-2,2);ema=.9*ema+.1*v;ref+=cfg.rho*(v-ref)
            np.testing.assert_allclose(raw["end"],np.stack((v,ema,ref),axis=3),rtol=0,atol=1e-12)
        self.assertFalse(np.array_equal(results["A"]["birth"],results["B"]["birth"]))
        source["prototype"][:]=999
        again=d.read(packets,block,"B",source["graph_neighbors"],cfg)
        for key in again:np.testing.assert_array_equal(again[key],results["B"][key])

    def test_all_foreign_observer_excludes_self_and_counts_unresolved(self):
        yy,xx=np.indices((16,16))
        prototype=np.array([np.ones((16,16)),-np.ones((16,16)),2*((yy+xx)%2)-1,2*(xx%2)-1],dtype=float)
        end=np.zeros((4,8,15,3,16,16))
        end[:,:,:,0]=prototype[:,None,None]
        end[:,:,1,0]=.1*prototype[:,None]
        end[:,:,2,0]=0
        for f in range(4):end[f,:,3,0]=prototype[(f+1)%4]
        got=d.observe(dict(end=end),prototype)
        for f in range(4):
            for c in range(15):
                v=end[f,0,c,0];values=[]
                for target in range(4):
                    expected=sum(abs(v[y,x])>.2 and (v[y,x]>0)==(prototype[target,y,x]>0) for y in range(16) for x in range(16))/256
                    values.append(expected)
                    np.testing.assert_array_equal(got["agreement"][f,:,c,target],np.full(8,expected))
                self.assertAlmostEqual(got["observed"][f,c,0],values[f])
                self.assertAlmostEqual(got["observed"][f,c,1],sum(values[j] for j in range(4) if j!=f)/3)
        np.testing.assert_array_equal(got["observed"][:,0,0],np.ones(4))
        np.testing.assert_array_equal(got["individual"][:,:,1:3,:3],np.zeros((4,8,2,3)))

    def test_interactions_vanish_for_additive_effects_and_recover_known_effect(self):
        utility=np.empty((2,4,9))
        for mode in range(3):
            for policy in range(3):utility[:,:,3*mode+policy]=10*mode+policy
        result=d.contrasts(utility)
        np.testing.assert_array_equal(result["interaction_strong"],np.zeros((2,4)))
        np.testing.assert_array_equal(result["interaction_random"],np.zeros((2,4)))
        np.testing.assert_array_equal(result["weak_high_minus_low"],np.full((2,4),10))
        utility[:,:,6]+=5
        result=d.contrasts(utility)
        for name in ("interaction_strong","interaction_random"):
            np.testing.assert_array_equal(result[name],np.full((2,4),5))
        np.testing.assert_array_equal(result["high_weak_minus_strong"],np.full((2,4),4))
        np.testing.assert_array_equal(result["high_weak_minus_random"],np.full((2,4),3))
        np.testing.assert_array_equal(result["high_weak_minus_original_weak"],np.full((2,4),25))
        independent=audit.contrasts(utility)
        self.assertEqual(set(result),set(independent))
        for name in result:np.testing.assert_array_equal(result[name],independent[name])


if __name__=="__main__":unittest.main(verbosity=2)
