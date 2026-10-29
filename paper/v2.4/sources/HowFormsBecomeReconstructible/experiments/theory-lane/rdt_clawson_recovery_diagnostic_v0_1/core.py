"""Finite-state summaries; no dynamics, fitting, file access or future inputs."""
import math
import numpy as np


def binary(values):
    a = np.asarray(values).reshape(-1)
    if not a.size or not np.isin(a, [0, 1]).all():
        raise ValueError("Nonempty binary evidence required")
    return a.astype(np.int64)


def joint(w, s, d):
    w, s, d = map(binary, (w, s, d))
    if not (len(w) == len(s) == len(d)):
        raise ValueError("Paired observations required")
    return np.bincount(4*w+2*s+d, minlength=8).reshape(2, 2, 2)


def summarize_joint(counts):
    c = np.asarray(counts)
    if c.shape != (2, 2, 2) or (c < 0).any() or not np.equal(c, np.floor(c)).all():
        raise ValueError("Eight nonnegative integer counts required")
    def one(table):
        n = int(table.sum())
        s = int(table[1, :].sum())
        d = int(table[:, 1].sum())
        helped, harmed = int(table[1, 0]), int(table[0, 1])
        assert s-d == helped-harmed
        return dict(n=n, successor_successes=s, direct_successes=d, helped=helped, harmed=harmed,
                    successor_rate=s/n if n else None, direct_rate=d/n if n else None,
                    paired_benefit=(helped-harmed)/n if n else None, cells_S_D=table.astype(int).tolist())
    return dict(all=one(c.sum(axis=0)), writer_fail=one(c[0]), writer_pass=one(c[1]),
                counts_W_S_D=c.astype(int).tolist())


def markov(w, s, horizon=18, alpha=.5):
    w, s = binary(w), binary(s)
    if len(w) != len(s) or horizon < 0 or int(horizon) != horizon or alpha <= 0:
        raise ValueError("Paired probe evidence and valid fixed model required")
    n0, n1 = int((w == 0).sum()), int((w == 1).sum())
    recovery_count = int(((w == 0) & (s == 1)).sum())
    error_count = int(((w == 1) & (s == 0)).sum())
    r = (recovery_count+alpha)/(n0+2*alpha)
    e = (error_count+alpha)/(n1+2*alpha)
    p0 = (n1+alpha)/(len(w)+2*alpha)
    ps = [p0]
    for _ in range(horizon):
        ps.append(ps[-1]*(1-e)+(1-ps[-1])*r)
    fixed = r/(r+e)
    closed = fixed+(p0-fixed)*(1-r-e)**horizon
    assert abs(ps[-1]-closed) < 1e-12 and all(0 <= p <= 1 for p in ps)
    return dict(p0=p0, recovery=r, error_entry=e, trajectory=ps, terminal=ps[-1],
                uninterrupted=p0*(1-e)**horizon, recovery_denominator=n0, error_denominator=n1,
                empirical_recovery=recovery_count/n0 if n0 else None,
                empirical_error_entry=error_count/n1 if n1 else None,
                prior_only_recovery=(n0 == 0), prior_only_error_entry=(n1 == 0))


def classify(windows, rule):
    x = np.asarray(windows)
    if rule not in (-1, 1) or x.shape[-4:] != (32, 1, 2, 2) or not np.isfinite(x).all():
        raise ValueError("Full native cue/port windows required")
    aligned = x.mean(axis=-4)*rule*np.array([[1., -1.], [-1., 1.]])
    margin = aligned.min(axis=(-3, -2, -1))
    target = margin > .25
    opposite = aligned.max(axis=(-3, -2, -1)) < -.25
    assert not (target & opposite).any()
    return target.astype(int)-opposite.astype(int), margin


def brier(probability, outcomes):
    y = binary(outcomes)
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("A valid probability is required")
    return math.fsum((probability-int(v))**2 for v in y)/len(y)
