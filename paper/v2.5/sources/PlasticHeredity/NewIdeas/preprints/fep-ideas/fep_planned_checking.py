"""Finite checking-clock design; inference is imported unchanged."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
from fractions import Fraction as F
import numpy as np
import fep_structured_reversal as R

MODES = ('free', 'hybrid', 'clock')
NEAR = 1e-11
TOL = 1e-10


class Vector:
    """Unnormalized probability-mass recursion, with two warning parities."""
    def __init__(self, model):
        self.model = model
        self.near = {mode: np.zeros(model.n, dtype=np.int64) for mode in MODES}

    def pre(self, w, p, t, h, d, mode, retain=True):
        if h == 0:
            return np.zeros(len(w)), np.zeros(len(w))
        m = self.model
        p = m.advance(p, t)
        value, number = np.zeros(len(w)), np.zeros(len(w))
        for parity in (False, True):
            z = np.full(len(w), parity)
            ww, pp = m.observe_warning(w, p, z, m.active(t))
            out = self.post(ww, pp, z, t, h, d, mode, retain)
            value += out['value']
            number += out['purchases']
        return value, number

    def post(self, w, p, z, t, h, d, mode, retain=True):
        assert mode in MODES and d in (0, 1) and h >= 1
        h = min(h, 101-t)
        m = self.model
        total = w.sum(axis=1)
        one = (w*m.orientation(p, z, m.active(t))).sum(axis=1)
        risk = np.minimum(one, total-one)
        v0, n0 = self.pre(w, p, t+1, h-1, 0 if mode == 'free' else 1, mode, retain)
        v1, n1 = np.zeros(len(w)), np.zeros(len(w))
        if retain:
            for x in (False, True):
                ww, pp = m.observe_label(w, p, z, x, m.active(t))
                v, n = self.pre(ww, pp, t+1, h-1, 0, mode, retain)
                v1 += v
                n1 += n
        else:
            v1, n1 = self.pre(w, p, t+1, h-1, 0, mode, retain)
        answer, purchase = risk+v0, .1*total+v1
        eligible = mode == 'free' or d == 0
        if not eligible:
            buy = np.ones(len(w), dtype=bool)
            near = np.zeros(len(w), dtype=bool)
        else:
            if mode == 'hybrid':
                ar, aq, _ = m.scores(w, p, z, t, h, retain)
            else:
                ar, aq = answer, purchase
            buy = aq <= ar
            near = np.abs(aq-ar) <= NEAR*total
            self.near[mode] += near
        return dict(value=np.where(buy, purchase, answer),
                    purchases=np.where(buy, total+n1, n0),
                    answer=answer, purchase=purchase, buy=buy, near_root=near,
                    answer_future=v0, purchase_future=v1, risk=risk)

    def inspect(self, h, d, retain=True):
        m = self.model
        w, p, z, t = m.w, m.p, m.z, m.t
        out = {mode: self.post(w, p, z, t, h, d, mode, retain) for mode in MODES}
        common, _ = self.pre(w, p, t+1, h-1, 0, 'clock', retain)
        clock = out['clock']['answer_future']-common
        information = common-out['clock']['purchase_future']
        return out, clock, information


class Reference(R.Reference):
    """Independent normalized rational enumeration of all four warnings."""
    def __init__(self, counts, boundaries=R.BOUNDS):
        super().__init__(counts, boundaries)
        self.pre_cache, self.post_cache = {}, {}

    @staticmethod
    def pack(w, p):
        return tuple(w), tuple(tuple(row) for row in p)

    def pre(self, w, p, t, h, d, mode, retain=True):
        if not h:
            return F(0), F(0)
        key = (w, p, t, h, d, mode, retain)
        if key in self.pre_cache:
            return self.pre_cache[key]
        pp = self.advance([list(row) for row in p], t)
        value, number = F(0), F(0)
        for y in range(4):
            ww, ppp, prob = self.warning(w, pp, y, t)
            out = self.post(*self.pack(ww, ppp), y, t, h, d, mode, retain)
            value += prob*out['value']
            number += prob*out['purchases']
        self.pre_cache[key] = value, number
        return value, number

    def post(self, w, p, y, t, h, d, mode, retain=True):
        h = min(h, 101-t)
        key = (w, p, y, t, h, d, mode, retain)
        if key in self.post_cache:
            return self.post_cache[key]
        branches = [self.label(w, [list(row) for row in p], y, x, t) for x in (0, 1)]
        risk = min(branches[0][2], branches[1][2])
        v0, n0 = self.pre(w, p, t+1, h-1, 0 if mode == 'free' else 1, mode, retain)
        v1, n1 = F(0), F(0)
        if retain:
            for ww, pp, prob in branches:
                v, n = self.pre(*self.pack(ww, pp), t+1, h-1, 0, mode, retain)
                v1 += prob*v
                n1 += prob*n
        else:
            v1, n1 = self.pre(w, p, t+1, h-1, 0, mode, retain)
        answer, purchase = risk+v0, F(1, 10)+v1
        if mode != 'free' and d == 1:
            buy = True
        elif mode == 'hybrid':
            free = self.post(w, p, y, t, h, 0, 'free', retain)
            buy = free['purchase'] <= free['answer']
        else:
            buy = purchase <= answer
        out = dict(value=purchase if buy else answer, purchases=1+n1 if buy else n0,
                   answer=answer, purchase=purchase, buy=buy,
                   answer_future=v0, purchase_future=v1, risk=risk)
        self.post_cache[key] = out
        return out

    def inspect(self, history, y, h, d, retain=True):
        w, p = self.state(history, y)
        w, p = self.pack(w, p)
        t = len(history)+1
        out = {mode: self.post(w, p, y, t, h, d, mode, retain) for mode in MODES}
        common, _ = self.pre(w, p, t+1, h-1, 0, 'clock', retain)
        return out, out['clock']['answer_future']-common, common-out['clock']['purchase_future']


CALIBRATIONS = ((58, 3, 3, 0), (20, 4, 8, 32), (16, 16, 16, 16))
TEMPLATES = ('consistent', 'contradictions', 'mixed')


def history(template, t):
    paid = [j for j in range(1, t) if j % 2 == 0]
    last_two = set(paid[-2:])
    out = []
    for j in range(1, t):
        y = (j-1) % 4 if template == 'mixed' else 0
        target = None
        if j % 2 == 0:
            target = y >> 1
            if template == 'contradictions' and j in last_two:
                target = 1
        out.append((y, target))
    return out


def contexts():
    return [dict(id=f'{template}-t{t}-c{ci}-y{y}', template=template, t=t,
                 counts=list(counts), history=history(template, t), y=y,
                 horizon=101-t, clock=(t-1) % 2)
            for t in (97, 98, 99, 100) for template in TEMPLATES
            for ci, counts in enumerate(CALIBRATIONS) for y in range(4)]


def load(cases, boundaries=R.BOUNDS):
    t = cases[0]['t']
    assert all(c['t'] == t and len(c['history']) == t-1 for c in cases)
    f = R.Filter(np.array([c['counts'] for c in cases]), boundaries)
    for j in range(1, t):
        f.start(j)
        f.warning(np.array([c['history'][j-1][0] for c in cases], dtype=np.int8))
        f.retain(np.array([-1 if c['history'][j-1][1] is None else c['history'][j-1][1]
                           for c in cases], dtype=np.int8))
    f.start(t)
    f.warning(np.array([c['y'] for c in cases], dtype=np.int8))
    return f


def known_law():
    """Exact two-task scheduling example, plus agreement and constant-risk controls."""
    laws = dict(varying=(F(890, 1000), F(92, 1000), F(8, 1000), F(10, 1000)),
                constant=(F(891, 1000), F(99, 1000), F(1, 1000), F(9, 1000)))
    out = []
    for name, q in laws.items():
        future = sum(min(q[y], q[y ^ 3], F(1, 10)*(q[y]+q[y ^ 3])) for y in (0, 1))
        for y in range(4):
            risk = min(q[y], q[y ^ 3])/(q[y]+q[y ^ 3])
            free = risk+future
            hybrid = risk+F(1, 10) if risk < F(1, 10) else F(1, 10)+future
            coherent = min(risk+F(1, 10), F(1, 10)+future)
            out.append(dict(law=name, warning=y, risk=str(risk), future_risk=str(future),
                            free=str(free), hybrid=str(hybrid), clock=str(coherent),
                            clock_benefit=str(F(1, 10)-future), information='0',
                            hybrid_purchases='1', clock_purchases='1'))
    return out
