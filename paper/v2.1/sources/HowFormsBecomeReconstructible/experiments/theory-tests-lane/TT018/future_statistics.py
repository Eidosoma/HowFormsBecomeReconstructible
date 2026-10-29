"""Draft analysis primitives for repeated futures; no native simulation or fitting."""
import hashlib
import json
import math
import numpy as np
from scipy.stats import beta, t


def require(condition, label):
    if not condition:
        raise ValueError(label)


def binomial_interval(successes, trials, alpha=.05):
    require(isinstance(successes, (int, np.integer)) and isinstance(trials, (int, np.integer)), 'Integer binomial counts')
    require(trials > 0 and 0 <= successes <= trials and 0 < alpha < 1, 'Binomial domain')
    lo = 0. if successes == 0 else float(beta.ppf(alpha/2, successes, trials-successes+1))
    hi = 1. if successes == trials else float(beta.ppf(1-alpha/2, successes+1, trials-successes))
    return [lo, hi]


def paired_probability_difference(treated, control, alpha=.05):
    x, y = np.asarray(treated), np.asarray(control)
    require(x.dtype == y.dtype == np.dtype(bool) and x.ndim == y.ndim == 1 and x.shape == y.shape and len(x) > 0,
            'Complete paired Boolean futures')
    plus, minus = int((x & ~y).sum()), int((y & ~x).sum())
    p = binomial_interval(plus, len(x), alpha/2)
    m = binomial_interval(minus, len(x), alpha/2)
    return dict(mean=(plus-minus)/len(x), treated_only=plus, control_only=minus,
                both=int((x & y).sum()), neither=int((~x & ~y).sum()),
                conservative_interval=[max(-1., p[0]-m[1]), min(1., p[1]-m[0])])


def endpoints(body_success, terminal_recipient_success):
    body, terminal = np.asarray(body_success), np.asarray(terminal_recipient_success)
    require(body.dtype == terminal.dtype == np.dtype(bool), 'Boolean outcome labels')
    require(body.ndim == 4 and body.shape[-1] == 18 and terminal.shape == body.shape[:-1],
            'Record, future, policy and 18-body shape; separate fresh-recipient outcome')
    return dict(uninterrupted=body.all(axis=-1), last_body=body[..., -1].copy(),
                terminal_record=terminal.copy())


def block_interval(record_differences, margin=.02):
    values = np.asarray(record_differences, dtype=float)
    require(values.shape == (64,) and np.isfinite(values).all() and np.max(abs(values)) <= 1,
            'Exactly 64 independent record/block averages')
    strata = values.reshape(16, 4).T
    mean = float(strata.mean())
    v = strata.var(axis=1, ddof=1)/16
    variance = float(v.sum()/16)
    if variance == 0:
        df = None
        radius = math.sqrt(2*math.log(20)/64)
        radius2 = math.sqrt(2*math.log(40)/64)
        method = 'Hoeffding zero-variance fallback'
    else:
        df = float(v.sum()**2 / np.sum(v*v/15))
        radius = float(t.ppf(.95, df))*math.sqrt(variance)
        radius2 = float(t.ppf(.975, df))*math.sqrt(variance)
        method = 'approximate stratified Welch-Satterthwaite'
    lo, hi = max(-1., mean-radius), min(1., mean+radius)
    return dict(mean=mean, se=math.sqrt(variance), df=df, independent_units=64, method=method,
                lower_one_sided95=lo, upper_one_sided95=hi,
                two_sided95=[max(-1., mean-radius2), min(1., mean+radius2)], margin=margin,
                verdict='PASS' if lo > margin else 'UNSUPPORTED' if hi < margin else 'INCONCLUSIVE')


def brier_per_record(probabilities, future_outcomes):
    p, y = np.asarray(probabilities, dtype=float), np.asarray(future_outcomes)
    require(y.dtype == np.dtype(bool) and y.ndim == 2 and y.shape[1] > 0 and p.shape == (len(y),),
            'One sealed forecast per record and repeated Bernoulli futures')
    require(np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all(), 'Finite probability forecasts')
    return ((p[:, None]-y)**2).mean(axis=1)


def split_half_covariance(future_outcomes):
    y = np.asarray(future_outcomes)
    require(y.dtype == np.dtype(bool) and y.shape == (64, 64), '64 records and 64 futures')
    a, b = y[:, :32].mean(axis=1), y[:, 32:].mean(axis=1)
    per_history = [float(np.cov(a[h::4], b[h::4], ddof=1)[0, 1]) for h in range(4)]
    return dict(by_history=per_history, mean_within_history_covariance=float(np.mean(per_history)),
                negative_estimates_retained=True, confirmatory_gate=False)


def stream_key(record_id, future, generation, source, cue=None):
    """Policy is absent: common draws within a future; futures use different keys.

    This checks a proposed allocation grammar. Native stream implementation and
    distributional regression still require qualification before registration.
    """
    require(isinstance(record_id, str) and record_id and isinstance(future, int) and future >= 0,
            'Record identity and future index')
    require(isinstance(generation, int) and 15 <= generation <= 32, 'Continuation or terminal generation')
    require(source in ('injury', 'reset', 'forcing', 'terminal_injury', 'terminal_reset', 'terminal_forcing'),
            'Explicit random source')
    require(cue in ((None,) if source.endswith('injury') else (0, 1)), 'Cue-specific reset/forcing stream')
    require(not source.startswith('terminal_') or generation == 32, 'Terminal source follows generation 32')
    payload = ['TT018_DRAFT_STREAM_CONTRACT_V1', record_id, future, generation, source, cue]
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()
