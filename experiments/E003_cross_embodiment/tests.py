"""Stencil oracle, intervention integrity and leakage checks on disposable data."""
from dataclasses import replace
import unittest
import numpy as np
import design as d


class TransferChecks(unittest.TestCase):
    def test_both_connectivities_match_scalar_oracle(self):
        random = np.random.default_rng(900003)
        v = random.normal(size=(16,16))*.3; field = random.normal(size=(16,16))*.2
        noise = random.normal(size=(16,16)); ema = v*.9; ref = v*.5
        for body in ("A", "B"):
            neighbors = np.zeros_like(v)
            offsets = ((-1,0),(1,0),(0,-1),(0,1)) if body == "A" else tuple((dy,dx) for dy in (-1,0,1) for dx in (-1,0,1) if dy or dx)
            for y in range(16):
                for x in range(16):
                    neighbors[y,x] = sum(v[(y+dy)%16,(x+dx)%16] for dy,dx in offsets)/len(offsets)
            drift = v-v**3+field+(neighbors-v); drift -= drift.mean()
            expected = np.clip(v+.2*drift+.3*(noise-noise.mean()),-2,2)
            got = d.step(v,ema,ref,field,noise,body)
            np.testing.assert_allclose(got[0], expected, atol=1e-15, rtol=1e-15)
            np.testing.assert_allclose(got[1], .9*ema+.1*expected, atol=1e-15)
            np.testing.assert_allclose(got[2], ref+.002*(expected-ref), atol=1e-15)
        impulse = np.zeros((16,16)); impulse[8,8] = 1
        self.assertFalse(np.array_equal(d.step(impulse,impulse,impulse,impulse*0,impulse*0,"A")[0], d.step(impulse,impulse,impulse,impulse*0,impulse*0,"B")[0]))

    def test_packet_only_read_masks_and_independent_body_noise(self):
        cfg = replace(d.CFG, formation=8, observation_window=4, capture=5, read=7, challenge_time=3)
        source = d.make_source(900003, cfg)
        a = d.read(source["acquired"],900003,"A",d.TEST,cfg)
        b = d.read(source["acquired"],900003,"B",d.TEST,cfg)
        np.testing.assert_array_equal(a["packets"], b["packets"])
        self.assertFalse(np.array_equal(a["birth"], b["birth"]))
        np.testing.assert_array_equal(a["after_damage"], np.where(a["body_masks"],-a["before_damage"],a["before_damage"]))
        for i,c in enumerate(d.TEST):
            self.assertTrue(np.all(a["body_masks"][:,:,i].sum(axis=(-2,-1)) == round(c["damage"]*256)))
            self.assertTrue(np.all(a["deletion_masks"][:,:,i].sum(axis=(-2,-1)) == round(c["deletion"]*256)))
        source["prototype"][:] = 999
        again = d.read(source["acquired"],900003,"A",d.TEST,cfg)
        for key in a: np.testing.assert_array_equal(a[key], again[key])

    def test_fixed_map_anchors_zero_and_joint_conditions_are_unseen(self):
        random = np.random.default_rng(13)
        prototype = random.normal(size=(4,16,16)); observed = random.random((4,9,4))
        x = d.features(prototype, observed, d.DEVELOPMENT)
        target = random.normal(size=(32,2))*.01
        models = {name:d.fit_ridge(values[:,1:].reshape(32,-1),target) for name,values in x.items()}
        predictions = d.predict(x,observed-observed[:,:1],models)
        for value in predictions.values(): np.testing.assert_array_equal(value[:,0],np.zeros((4,2)))
        for c in d.DEVELOPMENT: self.assertFalse(c["damage"] and (c["mixture"] or c["deletion"]))
        for c in d.JOINT: self.assertTrue(c["damage"] and (c["mixture"] or c["deletion"]))
        self.assertFalse(set(d.DEV_IDS)&set(d.TEST_IDS))


if __name__ == "__main__": unittest.main(verbosity=2)
