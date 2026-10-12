"""Six packet constructions from the same replayed delayed-renewal body."""
import hashlib
import json
from E034_settled_rebuilding import model as history
import numpy as np

base, evidence = history.base, history.evidence
CFG, Cycle = history.CFG, history.Cycle
ARMS, DAMAGE, RECEIVERS = history.ARMS, history.DAMAGE, history.RECEIVERS
CONDITIONS = ('standard_preserve', 'standard_rewrite', 'contrast_preserve',
              'contrast_rewrite', 'matched_preserve', 'matched_rewrite')
PANELS = tuple((r, c) for r in RECEIVERS for c in CONDITIONS)
PAIRS = (('standard_rewrite', 'standard_preserve'), ('contrast_preserve', 'standard_preserve'),
         ('contrast_rewrite', 'standard_rewrite'), ('contrast_rewrite', 'contrast_preserve'),
         ('contrast_rewrite', 'standard_preserve'), ('matched_preserve', 'standard_preserve'),
         ('matched_rewrite', 'standard_rewrite'), ('matched_rewrite', 'matched_preserve'),
         ('contrast_preserve', 'matched_preserve'), ('contrast_rewrite', 'matched_rewrite'))


def verify_source(raw, saved):
    values = dict(raw, developed_mean_ports=raw['developed_late_ports'].mean(axis=0))
    meta = json.loads(saved['__index__'].tobytes())
    assert meta['format'] == 'E031_compact_v1' and meta['kind'] == 'boundary'
    assert set(values) == set(meta['arrays'])
    assert set(saved) == set(meta['retained']) | {'__index__'}
    for name, value in values.items():
        value = np.asarray(value)
        actual = dict(shape=list(value.shape), dtype=value.dtype.str,
                      sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest())
        assert actual == meta['arrays'][name], ('source commitment', name)
        if name in saved:
            np.testing.assert_array_equal(value, saved[name])


def captures(body, beta=3.):
    assert body.ndim == 5 and body.shape[2:] == (2, 16, 16)
    x = np.tanh(beta*body)
    mean = (x[:, :, 0]+x[:, :, 1])/2
    cue = (x[:, :, 0]-x[:, :, 1])/2
    standard = base.correlations(body, beta).mean(axis=2)
    contrast = np.stack((cue*np.roll(cue, -1, -1), cue*np.roll(cue, -1, -2)), axis=-3)
    matched = np.where(contrast > 0, abs(standard), np.where(contrast < 0, -abs(standard), standard))
    return mean, cue, standard, contrast, matched


def construct(body, incoming, available, cfg=CFG):
    assert incoming.shape == (4, cfg.recipients, 4096)
    assert body.shape == (4, cfg.recipients, 2, 16, 16)
    assert available.shape == (4, cfg.recipients, 2, 16, 16) and available.dtype == bool
    mean, cue, standard, contrast, matched = captures(body, cfg.writer_beta)
    old = base.decode(incoming)
    retained = available & (abs(old) > .5)
    weights = []
    for candidate in (standard, contrast, matched):
        assert not (candidate*(~available)).any()
        weights.extend((np.where(retained, old, np.where(available, candidate, 0.)),
                        np.where(available, candidate, 0.)))
    records = base.encode(np.stack(weights))
    np.testing.assert_array_equal(abs(weights[0]), abs(weights[4]))
    np.testing.assert_array_equal(abs(weights[1]), abs(weights[5]))
    return dict(body=body.copy(), incoming=incoming.copy(), available=available.copy(), retained=retained,
                mean_component=mean, cue_component=cue, standard=standard, contrast=contrast,
                matched=matched, records=records)


def reconstruct(incoming, block, cfg, cycle, factor, saved):
    raw = history.boundary(incoming, block, cfg, cycle, factor)
    verify_source(raw, saved)
    available = raw['retained_edges'][1] | raw['eligible_edges'][1]
    data = construct(raw['developed_end'][1], incoming, available, cfg)
    np.testing.assert_array_equal(data['records'][0], raw['outgoing'][1])
    np.testing.assert_array_equal(base.encode(data['standard']), raw['computed_packets'][1])
    return data, raw['developed_late_ports'].mean(axis=0)


def terminal_cycle(cycle, factor):
    return history.schedules(cycle, factor)[1]


def assay(records, block, cfg, cycle):
    raw = history.assay(records, block, cfg, cycle)
    for a, b in ((0, 4), (1, 5)):
        np.testing.assert_array_equal(abs(base.decode(raw['packets'][a])), abs(base.decode(raw['packets'][b])))
        for offset in (0, 6):
            np.testing.assert_array_equal(raw['receiver_denominators'][offset+a], raw['receiver_denominators'][offset+b])
    return raw


def check_baseline(raw, saved):
    for name in ('masks', 'permutations'):
        np.testing.assert_array_equal(raw[name], saved[name])
    np.testing.assert_array_equal(raw['late_ports'].mean(axis=0)[[0, 6]], saved['mean_ports'][[1, 3]])


score = history.score
