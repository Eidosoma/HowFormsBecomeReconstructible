"""Known displacement checks, independent of every pilot founder."""
import unittest
import numpy as np
from run import diagnostic,fit_shift,translate


class MotionChecks(unittest.TestCase):
    def test_known_shift_and_held_evaluation(self):
        x=np.random.default_rng(900005).normal(size=(16,16))
        y=translate(x,(2,-3))
        shift,correlation=fit_shift(x,y)
        self.assertEqual(shift,(-2,3))
        self.assertAlmostEqual(correlation,1.)
        own=np.stack((x,x,y,y));foreign=own.copy()
        result=diagnostic(own,foreign,np.stack((x,y)))
        self.assertEqual(result["own_aligned"],1.)
        self.assertGreater(result["own_gain"],0.)
        self.assertEqual(result["specific_gain"],0.)
        self.assertEqual(result["half_translation_ceiling"],1.)

    def test_stationary_and_degenerate_fields(self):
        x=np.random.default_rng(900006).normal(size=(16,16))
        self.assertEqual(fit_shift(x,x)[0],(0,0))
        self.assertEqual(fit_shift(np.zeros((16,16)),np.zeros((16,16))),( (0,0),0.))


if __name__=="__main__":unittest.main(verbosity=2)
