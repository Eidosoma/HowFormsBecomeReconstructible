from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import ROOT, cap_cpus
from model import access, encode, graph, simulate, states, successors
import numpy as np


class ExactGraphChecks(unittest.TestCase):
    def test_known_mixed_graph(self):
        mapped=graph(np.array([1,2,1,4,4,3,5]))
        self.assertEqual(mapped["cycles"],[(1,2),(4,)])
        np.testing.assert_array_equal(mapped["distance"],[1,0,0,1,0,2,3])
        np.testing.assert_array_equal(mapped["counts"],[3,4])
        self.assertEqual(access(mapped,(1,2),0),(2/7,3/7))
        self.assertEqual(access(mapped,(0,),16),(0.,0.))

    def test_long_transient_is_not_censored(self):
        successor=np.minimum(np.arange(1024)+1,1023)
        mapped=graph(successor)
        self.assertEqual(mapped["cycles"],[(1023,)])
        self.assertEqual(mapped["distance"][0],1023)

    def test_scalar_native_parity_and_ties(self):
        source=ROOT.parents[1]/"PlasticHeredity/replicators.13.8.2026.codex/wagner_cleanroom/src/wagner_cleanroom/dynamics.py"
        definition=next(x for x in ast.parse(source.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=="sequential_sweep")
        module=ast.fix_missing_locations(ast.Module(body=ast.parse("from __future__ import annotations").body+[definition],type_ignores=[]))
        scope={"np":np}
        exec(compile(module,"read_only_native_sequential_sweep","exec"),scope)
        weights=np.random.default_rng(900001).normal(size=(10,10))
        expected=np.array([encode(scope["sequential_sweep"](x,weights)) for x in states()])
        np.testing.assert_array_equal(successors(weights),expected)
        np.testing.assert_array_equal(successors(np.zeros((10,10))),np.arange(1024))
        np.testing.assert_array_equal(successors(weights,np.ones(10),0.),successors(weights))

    def test_partial_reader_against_scalar_and_orbits(self):
        weights=np.random.default_rng(770).normal(size=(4,4))
        record=np.array([.25,0.,-.5,0.])
        successor=successors(weights,record,.5)
        mapped=graph(successor)
        for i,start in enumerate(states(4)):
            x=start.copy()
            for j in range(4):
                h=float(np.dot(weights[j],x))+.5*record[j]
                if h!=0:x[j]=1 if h>0 else -1
            self.assertEqual(int(encode(x)),int(successor[i]))
            path=[];current=i
            while current not in path:
                path.append(current);current=int(successor[current])
            cycle=path[path.index(current):]
            self.assertEqual(set(cycle),set(mapped["cycles"][mapped["labels"][i]]))
            self.assertEqual(path.index(current),int(mapped["distance"][i]))

    def test_complete_disposable_rulebook(self):
        raw,meta=simulate(900001)
        self.assertEqual(raw["successors"].shape,(49,1024))
        self.assertEqual(raw["payload_2"].shape,(4,16))
        self.assertEqual(raw["payload_5"].shape,(4,40))
        self.assertEqual(len(meta["entries"]),49)


if __name__=="__main__":
    cap_cpus()
    unittest.main(verbosity=2)
