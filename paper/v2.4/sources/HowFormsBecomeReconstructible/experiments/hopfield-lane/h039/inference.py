"""Paired whole-network intervals and the prospectively frozen three verdicts."""
import numpy as np
import model as m
from h039 import design as d


def infer(summaries, confirmation):
    ids = [s['block'] for s in summaries]
    assert len(ids) == len(set(ids))
    values = np.array([[d.endpoints(s)[k] for k in d.ENDPOINTS] for s in summaries])
    assert np.isfinite(values).all()
    count = len(values)
    estimates = {k: dict(mean=float(values[:, j].mean()), low=None, high=None,
        adjusted_lower=None, half_width=None, per_network=values[:, j].tolist())
        for j, k in enumerate(d.ENDPOINTS)}
    if not confirmation:
        return dict(classification='ENGINEERING_ONLY', networks=count, blocks=ids,
            estimates=estimates, decisions=None, bootstrap_draws=0)
    assert count >= 64 and ids == list(range(d.FIRST_BLOCK, d.FIRST_BLOCK+count))
    random = m.rng(d.ANALYSIS_SEED, 'H039 whole-network bootstrap')
    means = np.empty((d.BOOTSTRAPS, len(d.ENDPOINTS)))
    # Batch only the temporary gather; every endpoint uses identical network draws.
    for start in range(0, d.BOOTSTRAPS, 1000):
        end = min(start+1000, d.BOOTSTRAPS)
        indices = random.integers(0, count, (end-start, count))
        means[start:end] = values[indices].mean(1)
    for j, name in enumerate(d.ENDPOINTS):
        low, high = np.quantile(means[:, j], [.025, .975])
        estimates[name].update(low=float(low), high=float(high), half_width=float((high-low)/2))
        if name in d.FAMILY:
            estimates[name]['adjusted_lower'] = float(np.quantile(means[:, j], d.ALPHA/len(d.FAMILY)))
    return dict(classification=d.CLASSIFICATION, networks=count, blocks=ids,
        estimates=estimates, decisions=d.decisions(estimates), bootstrap_draws=d.BOOTSTRAPS,
        analysis_seed=d.ANALYSIS_SEED, directional_family=d.FAMILY,
        directional_quantile=d.ALPHA/len(d.FAMILY), whole_network_resampling=True,
        precision_target=.05, precision_target_is_gate=False)
