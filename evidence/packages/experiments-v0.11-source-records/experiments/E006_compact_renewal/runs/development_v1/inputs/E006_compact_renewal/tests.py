"""Codec-boundary checks on algebraic/disposable data only."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from run import ARMS,CFG,HERE,analyze,generation,initial,simulate,tissue


class CompactChecks(unittest.TestCase):
    def fixture(self):
        random=np.random.default_rng(900006)
        field=tissue.project(random.normal(size=(4,16,16)))
        return dict(acquired=tissue.pack(np.stack((field,np.zeros_like(field)),axis=1)),
                    background=np.zeros((16,16)),prototype=field,
                    prototype_halves=np.stack((field,field)))

    def test_full_field_matches_native_generation_exactly(self):
        source=self.fixture();cfg=replace(CFG,read=7,write=9,challenge_time=3)
        packets,_=initial(source,1900006,1)
        expected,trace=tissue.generation(packets,1900006,1,cfg)
        actual,adapted=generation(packets,1900006,1,1,cfg)
        np.testing.assert_array_equal(actual,expected)
        for key in trace:np.testing.assert_array_equal(adapted[key],trace[key])

    def test_compressed_boundaries_copy_shuffle_and_aliases(self):
        cfg=replace(CFG,read=7,write=9,challenge_time=3)
        for factor in (2,4):
            raw=simulate(self.fixture(),900006,factor,cfg)
            self.assertEqual(raw["outgoing"].shape,(3,4,2,10,2048//factor**2))
            tissue.checks(raw)
            self.assertTrue(np.any(raw["outgoing"][:,:,:,0]!=raw["incoming"][:,:,:,0]))

    def test_analysis_writes_complete_disposable_report(self):
        cfg=replace(CFG,read=4,write=5,challenge_time=2)
        with tempfile.TemporaryDirectory(prefix="analysis_check_",dir=HERE) as directory:
            output=Path(directory)
            for factor in (1,2,4):
                raw=simulate(self.fixture(),900006,factor,cfg)
                np.savez_compressed(output/f"block_900006_factor_{factor}.npz",**raw)
            analyze(output,[900006],technical=True)
            summary=json.loads((output/"summary.json").read_text())
            self.assertEqual(set(summary["groups"]),{"1","2","4"})
            self.assertTrue((output/"REPORT.md").read_text().startswith("# E006"))
            self.assertEqual(len((output/"observations.csv").read_text().splitlines()),961)


if __name__=="__main__":unittest.main(verbosity=2)
