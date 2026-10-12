#!/usr/bin/env python3
"""Small disposable portability checks; never a campaign or an original audit."""
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True

def tissue():
    sys.path.insert(0,str(ROOT/'experiments/E001_unprescribed_capture'))
    import tests
    tests.SOURCE=ROOT/'upstream/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas'
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(tests.ScientificChecks))
    assert result.wasSuccessful()
    return dict(checks=result.testsRun,reference='Vendored original cascade definitions; only reference lookup redirected')

def wagner():
    sys.path.insert(0,str(ROOT/'experiments/E002_history_accessibility'))
    import tests
    import numpy as np
    from model import encode,states,successors
    names=unittest.defaultTestLoader.getTestCaseNames(tests.ExactGraphChecks)
    suite=unittest.TestSuite(tests.ExactGraphChecks(n) for n in names if n!='test_scalar_native_parity_and_ties')
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    assert result.wasSuccessful()
    source=ROOT/'upstream/PlasticHeredity/replicators.13.8.2026.codex/wagner_cleanroom/src/wagner_cleanroom/dynamics.py'
    definition=next(x for x in ast.parse(source.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='sequential_sweep')
    module=ast.fix_missing_locations(ast.Module(body=ast.parse('from __future__ import annotations').body+[definition],type_ignores=[]))
    scope={'np':np}
    exec(compile(module,'vendored_native_sequential_sweep','exec'),scope)
    weights=np.random.default_rng(900001).normal(size=(10,10))
    expected=np.array([encode(scope['sequential_sweep'](x,weights)) for x in states()])
    np.testing.assert_array_equal(successors(weights),expected)
    np.testing.assert_array_equal(successors(np.zeros((10,10))),np.arange(1024))
    np.testing.assert_array_equal(successors(weights,np.ones(10),0.),successors(weights))
    return dict(checks=result.testsRun+1,reference='All 1024 states compared with vendored sequential update; public reference path only')

def repair():
    folder=ROOT/'experiments/theory-tests-lane/TT014'
    sys.path.insert(0,str(folder))
    import numpy as np
    import optimizer,repair
    options=json.loads((folder/'plan.json').read_text())['optimizer']
    rng=np.random.default_rng(900098)
    signs=1-2*rng.integers(0,2,size=256)
    signs[optimizer.INPUT_PINS]=1
    weights=(signs[optimizer.U]*signs[optimizer.V]*rng.uniform(.1,1.,512)).reshape(2,256)
    weights.ravel()[::7]=0.
    original=weights.copy()
    fixed,solution,m=repair.recipient(weights,options)
    again,solution2,m2=repair.recipient(weights,options)
    np.testing.assert_array_equal(weights,original)
    np.testing.assert_array_equal(fixed[original!=0],original[original!=0])
    np.testing.assert_array_equal(fixed,again)
    assert m==m2 and np.all(np.abs(fixed[original==0])==m)
    np.testing.assert_array_equal(solution['signs'],solution2['signs'])
    assert np.all(solution['signs'].ravel()[optimizer.INPUT_PINS]==1)
    empty,_,zero=repair.recipient(np.zeros((2,256),np.float64),options)
    assert zero==0. and not empty.any()
    return dict(checks=8,reference='Manufactured record: preservation, deterministic filling, pin constraints and empty-record behavior',
                new_performance_estimate=False)

if __name__=='__main__':
    if len(sys.argv)==2:
        print(json.dumps(dict(case=sys.argv[1],status='PASS',**{'tissue':tissue,'wagner':wagner,'repair':repair}[sys.argv[1]]())))
    else:
        results=[]
        for case in ['tissue','wagner','repair']:
            p=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),case],cwd=ROOT,text=True,capture_output=True,timeout=60)
            if p.returncode:
                print(p.stdout);print(p.stderr,file=sys.stderr);raise SystemExit(p.returncode)
            results.append(json.loads(p.stdout.strip().splitlines()[-1]))
        print(json.dumps(dict(status='PASS',python=sys.version.split()[0],numpy=importlib.metadata.version('numpy'),
                             scipy=importlib.metadata.version('scipy'),cases=results,
                             scope='Disposable component checks; no retained cohort replay, fitting or new result qualification'),indent=2))
