"""Independent D185 scalar geometry checks; no simulation or production import."""

import math

import numpy as np


def scalar(field, codes, parent, other_parent, message):
    x = list(map(float, field.flat))
    templates = [list(map(float, c.flat)) for c in codes]
    n = len(x)
    mean = math.fsum(x) / n
    xc = [v - mean for v in x]
    rms = math.sqrt(math.fsum(v*v for v in x) / n)
    crms = math.sqrt(math.fsum(v*v for v in xc) / n)
    scores = [math.fsum(a*b for a, b in zip(x, c)) / n for c in templates]
    partner = (message + 2) % 4
    gap = scores[message] - scores[partner]
    delta = [a-b for a, b in zip(templates[message], templates[partner])]
    den = crms * math.sqrt(math.fsum(v*v for v in delta) / n)
    ties = [abs(v - max(scores)) <= 1e-12 for v in scores]
    own, other = ties[message] / sum(ties), ties[partner] / sum(ties)

    def corr(target):
        y = list(map(float, target.flat))
        my = math.fsum(y) / n
        yc = [v-my for v in y]
        denom = math.sqrt(math.fsum(v*v for v in xc) * math.fsum(v*v for v in yc))
        return math.fsum(a*b for a, b in zip(xc, yc)) / denom if denom else 0.

    return [rms, crms, gap, gap/den if den else 0., own, other, own-other,
            corr(parent), corr(other_parent), *scores]


def check(field, codes, parent, other_parent, labels, reported):
    wanted = np.asarray([scalar(x, codes, p, q, int(m))
                         for x, p, q, m in zip(field, parent, other_parent, labels)])
    if reported.shape != wanted.shape:
        raise AssertionError('metric shape mismatch')
    np.testing.assert_allclose(reported, wanted, rtol=0., atol=2e-12)
    return float(np.max(np.abs(reported-wanted)))
