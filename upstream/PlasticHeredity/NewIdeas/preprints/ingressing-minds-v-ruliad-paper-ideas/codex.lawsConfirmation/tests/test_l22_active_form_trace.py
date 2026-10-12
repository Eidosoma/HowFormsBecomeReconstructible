"""Synthetic qualification only: no simulation, saved-outcome selection or fit."""

import ast
import json
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l22_active_form_trace as trace


@pytest.fixture
def fields():
    h = np.tile(np.r_[np.ones(8), -np.ones(8)], (16, 1))
    v = h.T.copy()
    codes = np.array([h, -h, v, -v])
    labels = np.arange(16)//4
    parent = codes[labels].copy()
    other = codes[(labels+2) % 4].copy()
    return codes, labels, parent, other


@pytest.mark.parametrize('kind', ['zero', 'constant', 'own', 'partner', 'mixed', 'tiny', 'tie'])
def test_scalar_matches_vector(fields, kind):
    codes, labels, parent, other = fields
    x = dict(zero=np.zeros_like(parent), constant=np.full_like(parent, 2.), own=parent,
             partner=other, mixed=.8*parent+.3*other+.1,
             tiny=parent*1e-14, tie=parent+other)[kind]
    value = trace.metrics(x, codes, parent, other, labels)
    assert trace.load_checker().check(x, codes, parent, other, labels, value) < 2e-12
    if kind == 'zero':
        np.testing.assert_array_equal(value[:, [0, 1, 2, 3, 6, 7, 8]], 0.)
        np.testing.assert_array_equal(value[:, [4, 5]], .25)
    if kind == 'own': np.testing.assert_array_equal(value[:, 4], 1.)


def test_normalized_gap_scale_invariant(fields):
    codes, labels, p, q = fields
    a = trace.metrics(p+.2*q, codes, p, q, labels)
    b = trace.metrics(3*(p+.2*q)+.1, codes, p, q, labels)
    np.testing.assert_allclose(a[:, 3], b[:, 3], atol=1e-14, rtol=0.)
    np.testing.assert_allclose(3*a[:, 2], b[:, 2], atol=1e-14, rtol=0.)


@pytest.mark.parametrize('kind', ['shape', 'nan', 'labels', 'uncentered_codes', 'parent_shape'])
def test_bad_field_rejected(fields, kind):
    codes, labels, p, q = fields
    x = p.copy()
    if kind == 'shape': x = x[:, :8]
    if kind == 'nan': x[0, 0, 0] = np.nan
    if kind == 'labels': labels[0] = 4
    if kind == 'uncentered_codes': codes += 1.
    if kind == 'parent_shape': q = q[:8]
    with pytest.raises(ValueError): trace.metrics(x, codes, p, q, labels)


def test_scalar_tampering_detected(fields):
    codes, labels, p, q = fields
    value = trace.metrics(p, codes, p, q, labels)
    value[5, 2] += .01
    with pytest.raises(AssertionError): trace.load_checker().check(p, codes, p, q, labels, value)


def test_complete_scope():
    assert len(set(trace.plan())) == 36
    assert len(trace.contrasts()) == 6
    assert trace.TIMES == (0, 1, 50, 250, 500, 1000)
    assert trace.READ_TIMES == (0, 1, 1000)
    assert len(trace.FIELDS) == 13


def test_aggregate_full_block_message_strata():
    blocks = {b: {'x': np.full((16, 13), i, dtype=float)} for i, b in enumerate(trace.BLOCKS)}
    result = trace.aggregate(blocks)['x']
    assert result['mean'] == [1.5]*13
    assert result['by_block'] == [[float(i)]*13 for i in range(4)]
    assert result['by_message'] == [[1.5]*13]*4
    assert len(result['by_block_message']) == 4
    del blocks[trace.BLOCKS[-1]]
    with pytest.raises(ValueError): trace.aggregate(blocks)


def test_endpoint_bridge_and_tampering():
    value = np.zeros((16, 13))
    rows = [dict(world=i, message=i//4, replicate=i%4, accuracy=0., partner_accuracy=0.,
                 preference=0., projection_gap=0.) for i in range(16)]
    trace.endpoint_bridge(value, rows)
    rows[0]['accuracy'] = 1.
    with pytest.raises(AssertionError): trace.endpoint_bridge(value, rows)


def test_write_once_and_external_guard(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, 'ROOT', tmp_path)
    dest = tmp_path/'receipt.json'
    trace.write(dest, dict(passes=True))
    assert trace.read(dest)['passes']
    with pytest.raises(FileExistsError): trace.write(dest, {})
    with pytest.raises(ValueError): trace.target(tmp_path.parent/'outside.json')


def test_hash_tamper_rejected(tmp_path):
    path = tmp_path/'value.json'
    path.write_text(json.dumps({'a': 1}))
    hashes = {str(path): trace.digest(path)}
    trace.verify(hashes)
    path.write_text(json.dumps({'a': 2}))
    with pytest.raises(AssertionError): trace.verify(hashes)


def test_no_dynamics_or_subprocess_imports():
    module = ast.parse(Path(trace.__file__).read_text())
    imports = {n.module for n in ast.walk(module) if isinstance(n, ast.ImportFrom)}
    imports |= {a.name for n in ast.walk(module) if isinstance(n, ast.Import) for a in n.names}
    assert all(not x.startswith(('laws_confirmation', 'blueprint', 'ladder')) for x in imports)
    assert 'subprocess' not in imports and 'multiprocessing' not in imports
    calls = {n.func.attr for n in ast.walk(module) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not {'repair', 'fresh_read', 'source_step', 'blueprint_step', 'default_rng'} & calls
