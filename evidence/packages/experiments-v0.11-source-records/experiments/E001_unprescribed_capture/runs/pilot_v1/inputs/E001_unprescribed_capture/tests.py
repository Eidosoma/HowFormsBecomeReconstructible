"""Scientific implementation checks on disposable states; no main cohort IDs."""
from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import ROOT, cap_cpus
from model import ARMS, CFG, capture, checks, generation, pack, project, simulate, step, unpack
import numpy as np

SOURCE = ROOT.parents[1] / "PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas"


def native_functions():
    functions = []
    for package, file, names in [
        ("ladder_web", "engine.py", ("ladder_step",)),
        ("blueprint_web", "engine.py", ("blueprint_step",)),
        ("writable_landlord", "pipeline.py", ("project_theta", "cascade_step")),
    ]:
        tree = ast.parse((SOURCE / package / "src" / package / file).read_text())
        functions.extend(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names)
    future = ast.parse("from __future__ import annotations").body
    module = ast.fix_missing_locations(ast.Module(body=future+functions, type_ignores=[]))
    scope = {"np": np}
    exec(compile(module, "read_only_native_function_definitions", "exec"), scope)
    return scope


class ScientificChecks(unittest.TestCase):
    def test_native_cascade_parity(self):
        native = native_functions()
        tissue = SimpleNamespace(dt=.2, coupling=1., sigma=.3, well_asym=0.)
        ladder = SimpleNamespace(ema_rate=.1)
        bp = SimpleNamespace(c_m=.2, rho=.002)
        for gain in (0., .2):
            for writing in (False, True):
                generator = np.random.default_rng(1921)
                state = [generator.normal(0,.2,(3,16,16)) for _ in range(3)]
                state.append(project(generator.normal(size=(3,16,16))))
                local = [x.copy() for x in state]
                noise1, noise2 = np.random.default_rng(451), np.random.default_rng(451)
                for _ in range(40):
                    state = native["cascade_step"](*state, tissue, ladder, bp, noise1, .001 if writing else 0., .3, c_m=gain)
                    local = step(*local, noise2.standard_normal((3,16,16)), gain=gain, writing=writing)
                    for a,b in zip(state,local):
                        np.testing.assert_array_equal(a,b)

    def test_packets_and_bottleneck(self):
        field = np.random.default_rng(2).normal(size=(4,16,16))
        np.testing.assert_array_equal(unpack(pack(field)), field)
        for factor in (2,4):
            decoded = unpack(pack(field, factor), factor)
            self.assertEqual(pack(field,factor).shape[-1],2048//factor**2)
            for i in range(0,16,factor):
                for j in range(0,16,factor):
                    np.testing.assert_allclose(decoded[:,i,j],field[:,i:i+factor,j:j+factor].mean(axis=(1,2)), atol=2e-16)
        with self.assertRaises(ValueError):
            unpack(np.zeros((2047,),np.uint8))
        field[0,0,0] = np.nan
        with self.assertRaises(ValueError):
            pack(field)
        with self.assertRaises(ValueError):
            unpack(np.frombuffer(np.full(256,np.nan,dtype="<f8").tobytes(),np.uint8))

    def test_zero_writer_first_projection(self):
        random = np.random.default_rng(817)
        v = random.normal(0,.2,(1,16,16))
        outcome = step(v,v.copy(),v.copy(),np.zeros_like(v),random.normal(size=v.shape),gain=.2,writing=True)
        np.testing.assert_allclose(outcome[3],project(np.tanh(outcome[2])), atol=3e-16)

    def test_complete_disposable_lifecycle_and_replay(self):
        small = replace(CFG, formation=12, observation_window=6, capture=9, read=6, write=8, challenge_time=3)
        raw = simulate(900001,"homogeneous",small)
        checks(raw)
        repeat = simulate(900001,"homogeneous",small)
        for key in raw:
            np.testing.assert_array_equal(raw[key],repeat[key])
        self.assertEqual(raw["outgoing"].shape, (3,4,2,10,2048))
        self.assertFalse(np.array_equal(raw["founder_birth"][:,None,None],raw["terminal_birth"]))


if __name__ == "__main__":
    cap_cpus()
    unittest.main(verbosity=2)
