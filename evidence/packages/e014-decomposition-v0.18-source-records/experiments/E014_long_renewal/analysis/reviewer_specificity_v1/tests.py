"""Small exact score/decomposition checks; original observations validate the cohort."""
import argparse
from pathlib import Path
import time
from analysis import field_counts, transitions, bootstrap_weights, STAGES, write_json, sha
from common import cap_cpus, rng, utc
import numpy as np


def main(out):
    cap_cpus(1); started = time.monotonic(); checks = []
    p = np.ones((4, 16, 16))
    v = np.zeros((20, 4, 2, 10, 16, 16))
    # Equal groups: matching/resolved, matching/unresolved, mismatching/resolved,
    # mismatching/unresolved. abs(v)==.2 remains unqualified.
    v[..., :4, :] = .3; v[..., 4:8, :] = .2; v[..., 8:12, :] = -.3; v[..., 12:, :] = -.2
    c, codes = field_counts(v, p)
    np.testing.assert_array_equal(c, np.full(c.shape, 64, np.uint16))
    checks.append('strict threshold and four exhaustive categories')
    v.fill(0); p.fill(0)
    c, _ = field_counts(v, p)
    assert (c[..., 1] == 256).all() and not c[..., 0].any()
    checks.append('original >0 convention: zero matches zero but never qualifies')
    # Marginals are not generally independent: Q=.5, S=.5, A=.5, S*A=.25.
    p.fill(1); v.fill(-.1); v[..., :8, :] = .3
    c, codes = field_counts(v, p)
    assert (c[..., 0] == 128).all() and (c[..., 3] == 128).all()
    checks.append('joint score is not the product of marginal rates')
    codes[STAGES.index('after_3')] = 0
    codes[STAGES.index('after_16'), ..., :4, :] = 0
    codes[STAGES.index('after_16'), ..., 4:8, :] = 1
    codes[STAGES.index('after_16'), ..., 8:12, :] = 2
    codes[STAGES.index('after_16'), ..., 12:, :] = 3
    t = transitions(codes)
    np.testing.assert_array_equal(t[..., 0, :], np.full(t[..., 0, :].shape, 64, np.uint16))
    assert not t[..., 1:, :].any()
    checks.append('paired endpoint categories retain the joint-loss category')
    vals = np.arange(64, dtype=float)/2048
    draws = rng('E014', 'bootstrap').integers(0, 64, (10000, 64))
    np.testing.assert_array_equal(bootstrap_weights() @ vals, vals[draws].mean(axis=1))
    checks.append('weighted whole-block bootstrap exactly matches original sampled means')
    write_json(out, dict(status='PASS', utc=utc(), checks=checks, seconds=time.monotonic()-started, code_sha256=sha(__file__)))
    print('Passed', len(checks), 'exact score and inference checks')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True); main(p.parse_args().output)
