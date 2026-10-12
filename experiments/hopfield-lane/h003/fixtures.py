"""Scientific fixtures for symmetric gain, sequential dynamics and endpoints."""
from pathlib import Path
import io
import unittest
import numpy as np
from h003 import experiment as e


class Fixtures(unittest.TestCase):
    def test_symmetric_gain_geometry(self):
        base=e.m.symmetric(np.arange(144,dtype=float).reshape(12,12))
        record=e.m.symmetric(np.random.default_rng(22).normal(size=(12,12)))
        for sites in [np.arange(4),np.arange(8,12)]:
            weight=e.effective_weights(base,record,4,sites)
            np.testing.assert_array_equal(weight,weight.T)
            np.testing.assert_array_equal(np.diag(weight),0)
            selected=set(sites)
            changed=0
            for i in range(12):
                for j in range(12):
                    factor=4 if ((i in selected)!=(j in selected)) else 1
                    self.assertEqual(weight[i,j],factor*(base[i,j]+record[i,j]))
                    changed+=factor==4
            self.assertEqual(changed,2*4*8)
        np.testing.assert_array_equal(e.effective_weights(base,record,1,[0,1]),base+record)

    def test_scalar_dynamics_energy_and_uniform_gain(self):
        random=np.random.default_rng(931001)
        base=e.m.symmetric(random.normal(size=(12,12)))
        weight=e.effective_weights(base,np.zeros_like(base),4,[0,1])
        birth=random.choice([-1.,1.],size=12);birth[:2]=1
        orders=np.stack([random.permutation(12) for _ in range(8)])
        scalar=birth.copy();energy=[float(e.m.energy(scalar,weight))]
        for order in orders:
            for i in order:
                if i<2:continue
                field=sum(weight[i,j]*scalar[j] for j in range(12))
                if field:scalar[i]=1 if field>0 else -1
                energy.append(float(e.m.energy(scalar,weight)))
        actual=e.m.relax(weight,birth,orders,[0,1])
        np.testing.assert_array_equal(actual,scalar)
        np.testing.assert_array_equal(e.m.relax(4*weight,birth,orders,[0,1]),actual)
        self.assertLessEqual(max(np.diff(energy)),1e-12)

    def test_disjoint_response_categories_and_threshold(self):
        states=np.zeros((4,1,2,64))
        # One founder each: intended, opposite, collapsed, weak/mixed.
        for f,signs in enumerate([[-1,1],[1,-1],[1,1],[0,0]]):
            for t,sign in enumerate(signs):
                states[f,0,t,8:16]=sign
                states[f,0,t,16:24]=-sign
        np.testing.assert_array_equal(e.categories(states)[:,0],[0,1,2,3])
        states[0,0,0,8:16]=.5
        self.assertEqual(e.categories(states)[0,0],3)

    def test_long_read_extends_same_tape(self):
        short=e.h001.orders(12900,'h003','assay',16,'order',sweeps=8)
        long=e.h001.orders(12900,'h003','assay',16,'order',sweeps=32)
        np.testing.assert_array_equal(short,long[:8])


def run_tests(path):
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    Path(path).write_text(stream.getvalue())
    if not result.wasSuccessful():raise AssertionError('H003 fixtures failed; inspect fixtures.log')


if __name__=='__main__':unittest.main(verbosity=2)
