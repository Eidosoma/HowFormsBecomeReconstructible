"""Fixed shared-law reversal mixture, vector planner and scalar rational reference."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
from fractions import Fraction as F
from itertools import product
import numpy as np
import check_fep_reversal_feedback_audit as OLD

Q, A = OLD.Q, OLD.A
BOUNDS = tuple(range(1, 101))
SHARE = F(1, 2)


def priors(boundaries, share=SHARE):
    b = F(1, 6*len(boundaries))
    return [F(1, 2)]+[value for _ in boundaries for value in (b*(1-share), b, b, b*share)]


class Reference:
    """Four-warning, rational arithmetic implementation independent of the vector recursion."""
    def __init__(self, counts, boundaries=BOUNDS, share=SHARE):
        self.counts = tuple(counts)
        self.boundaries = tuple(boundaries)
        self.share = share
        self.hypotheses = [(101, 0)]+[(t, k) for t in boundaries for k in range(4)]
        self.prior = priors(boundaries, share)
        self.reset = []
        for _, kind in self.hypotheses:
            row = [F(1), F(2), F(1, 2), F(1), F(1, 2), F(1)]
            if kind in (1, 2):
                row[2:4] = [F(1), F(2)]
            self.reset.append(row)

    def initial(self):
        return self.prior[:], [Q.initial(self.counts) for _ in self.hypotheses]

    def kind(self, j, t):
        tau, kind = self.hypotheses[j]
        return kind if t >= tau else 0

    def advance(self, p, t):
        out = [row[:] for row in p]
        for j, (tau, kind) in enumerate(self.hypotheses):
            if j and tau == t and kind != 3:
                out[j] = self.reset[j][:]
        return out

    def law(self, row, kind):
        q = Q.law(row, 0 if kind == 3 else kind)
        return tuple(reversed(q)) if kind == 3 else q

    def warning(self, w, p, y, t):
        mass, out = [], [row[:] for row in p]
        z = (y >> 1) ^ (y & 1)
        for j, row in enumerate(p):
            kind = self.kind(j, t)
            q = self.law(row, kind)
            mass.append(w[j]*(q[y]+q[y ^ 3])/2)
            if kind in (0, 3):
                out[j][0] += z
                out[j][1] += 1
        total = sum(mass)
        return [v/total for v in mass], out, total

    def label(self, w, p, y, target, t):
        mass, out = [], [row[:] for row in p]
        e = y ^ (3*target)
        for j, row in enumerate(p):
            kind = self.kind(j, t)
            q = self.law(row, kind)
            mass.append(w[j]*q[e]/(q[y]+q[y ^ 3]))
            if kind in (0, 3):
                base = e ^ (3 if kind == 3 else 0)
                offset = 2+2*((y >> 1) ^ (y & 1))
                out[j][offset] += base >> 1
                out[j][offset+1] += 1
            else:
                out[j][2] += (e & 1) if kind == 1 else (e >> 1)
                out[j][3] += 1
        total = sum(mass)
        return [v/total for v in mass], out, total

    def state(self, history, current):
        w, p = self.initial()
        for t, (y, target) in enumerate(history, 1):
            p = self.advance(p, t)
            w, p, _ = self.warning(w, p, y, t)
            if target is not None:
                w, p, _ = self.label(w, p, y, target, t)
        t = len(history)+1
        return self.warning(w, self.advance(p, t), current, t)[:2]

    def before(self, w, p, t, steps, retain=True):
        if not steps:
            return F(0)
        p = self.advance(p, t)
        value = F(0)
        for y in range(4):
            ww, pp, probability = self.warning(w, p, y, t)
            r, q, _, _ = self.scores(ww, pp, y, t, steps, retain)
            value += probability*min(r, q)
        return value

    def scores(self, w, p, y, t, steps=4, retain=True):
        steps = min(steps, 101-t)
        branches = [self.label(w, p, y, target, t) for target in (0, 1)]
        pw1 = branches[1][2]
        v0 = self.before(w, p, t+1, steps-1, retain)
        v1 = sum(probability*self.before(ww, pp, t+1, steps-1, retain)
                 for ww, pp, probability in branches) if retain else v0
        u = 1-pw1 if y >> 1 else pw1
        return min(pw1, 1-pw1)+v0, F(1, 10)+v1, v0-v1, u


class Filter:
    """Vector belief and finite-horizon task-cost planner; R never resets its latent law."""
    def __init__(self, counts, boundaries=BOUNDS, share=SHARE):
        self.boundaries = tuple(boundaries)
        assert self.boundaries == tuple(sorted(set(self.boundaries))) and self.boundaries
        assert 1 <= min(self.boundaries) <= max(self.boundaries) <= 100
        assert 0 <= share <= 1
        self.share = share
        self.counts = np.array(counts, dtype=np.int16, copy=True)
        assert self.counts.shape[1:] == (4,) and np.all(self.counts >= 0)
        self.times = np.array([101]+[t for t in boundaries for _ in range(4)])
        self.kinds = np.array([0]+[0, 1, 2, 3]*len(boundaries))
        self.n, self.nh = len(counts), len(self.times)
        self.priors = priors(boundaries, share)
        assert sum(self.priors) == 1
        self.w = np.broadcast_to(np.array(self.priors, dtype=float), (self.n, self.nh)).copy()
        initial = np.array([Q.initial(row) for row in counts], dtype=float)
        self.p = np.broadcast_to(initial[:, None, :], (self.n, self.nh, 6)).copy()
        self.reset = np.broadcast_to(np.array([1., 2., .5, 1., .5, 1.]), (1, self.nh, 6)).copy()
        self.reset[:, np.isin(self.kinds, [1, 2]), 2:4] = (1., 2.)
        self.ys = np.zeros((self.n, 100), dtype=np.int8)
        self.labels = np.full((self.n, 100), -1, dtype=np.int8)
        self.fallback = 0
        self.t = 0

    def active(self, t):
        return np.where(self.times <= t, self.kinds, 0)

    def advance(self, p, t):
        if t in self.boundaries:
            out = p.copy()
            selected = (self.times == t) & (self.kinds != 3)
            out[:, selected] = self.reset[:, selected]
            return out
        return p

    @staticmethod
    def observe_warning(w, p, z, kind):
        general = np.isin(kind, [0, 3])
        g = np.where(general[None, :], p[..., 0]/p[..., 1], .5)
        mass = w*np.where(z[:, None], g, 1-g)
        out = p.copy()
        out[..., 0] += z[:, None]*general[None, :]
        out[..., 1] += general[None, :]
        return mass, out

    @staticmethod
    def orientation(p, z, kind):
        u = np.where(z[:, None], p[..., 4]/p[..., 5], p[..., 2]/p[..., 3])
        rate = p[..., 2]/p[..., 3]
        return np.where(kind[None, :] == 1, np.where(z[:, None], 1-rate, rate),
                        np.where(kind[None, :] == 2, rate,
                                 np.where(kind[None, :] == 3, 1-u, u)))

    def observe_label(self, w, p, z, x, kind, observed=None):
        x = np.broadcast_to(x, z.shape).astype(bool)
        if observed is None:
            observed = np.ones(len(z), dtype=bool)
        u = self.orientation(p, z, kind)
        mass = w*np.where(observed[:, None], np.where(x[:, None], u, 1-u), 1.)
        out = p.copy()
        base_error = x[:, None] ^ (kind[None, :] == 3)
        for parity, offset in ((False, 2), (True, 4)):
            use = observed[:, None] & (z[:, None] == parity) & np.isin(kind, [0, 3])[None, :]
            out[..., offset] += use*base_error
            out[..., offset+1] += use
        use = observed[:, None] & np.isin(kind, [1, 2])[None, :]
        error = np.where(kind[None, :] == 1, (x ^ z)[:, None], x[:, None])
        out[..., 2] += use*error
        out[..., 3] += use
        return mass, out

    def before(self, w, p, t, steps, retain=True):
        if not steps:
            return np.zeros(len(w))
        p = self.advance(p, t)
        kind = self.active(t)
        value = np.zeros(len(w))
        for parity in (False, True):
            z = np.full(len(w), parity)
            ww, pp = self.observe_warning(w, p, z, kind)
            r, q, _ = self.scores(ww, pp, z, t, steps, retain)
            value += np.minimum(r, q)
        return value

    def scores(self, w, p, z, t, steps=4, retain=True):
        steps = min(steps, 101-t)
        kind = self.active(t)
        one = (w*self.orientation(p, z, kind)).sum(axis=1)
        total = w.sum(axis=1)
        risk = np.minimum(one, total-one)
        if steps == 1:
            return risk, .1*total, np.zeros(len(w))
        v0 = self.before(w, p, t+1, steps-1, retain)
        v1 = np.zeros(len(w)) if retain else v0
        if retain:
            for x in (False, True):
                ww, pp = self.observe_label(w, p, z, x, kind)
                v1 += self.before(ww, pp, t+1, steps-1, retain)
        return risk+v0, .1*total+v1, v0-v1

    def start(self, t):
        self.t = t
        self.p = self.advance(self.p, t)

    def warning(self, y):
        self.ys[:, self.t-1] = y
        self.z = ((y >> 1) ^ (y & 1)).astype(bool)
        self.w, self.p = self.observe_warning(self.w, self.p, self.z, self.active(self.t))
        norm = self.w.sum(axis=1, keepdims=True)
        assert np.all(norm > 0)
        self.w /= norm
        self.u = (self.w*self.orientation(self.p, self.z, self.active(self.t))).sum(axis=1)
        return self.u.copy()

    def retain(self, labels):
        labels = np.asarray(labels, dtype=np.int8)
        self.labels[:, self.t-1] = labels
        x = (self.ys[:, self.t-1] >> 1) ^ np.maximum(labels, 0)
        self.w, self.p = self.observe_label(self.w, self.p, self.z, x, self.active(self.t), labels >= 0)
        norm = self.w.sum(axis=1, keepdims=True)
        assert np.all(norm > 0)
        self.w /= norm

    def choose(self, steps=4, retain=True):
        r, q, delta = self.scores(self.w, self.p, self.z, self.t, steps, retain)
        y = self.ys[:, self.t-1]
        action = np.where(q <= r, 2, (y >> 1) ^ (self.u > .5)).astype(np.int8)
        myopic = np.where(np.minimum(self.u, 1-self.u) >= .1, 2, (y >> 1) ^ (self.u > .5)).astype(np.int8)
        near = (np.abs(r-q) <= 1e-12) | (np.abs(np.minimum(self.u, 1-self.u)-.1) <= 1e-12)
        for row in np.flatnonzero(near):
            history = [(int(self.ys[row, k]), None if self.labels[row, k] < 0 else int(self.labels[row, k]))
                       for k in range(self.t-1)]
            ref = Reference(self.counts[row], self.boundaries, self.share)
            w, p = ref.state(history, int(y[row]))
            er, eq, _, u = ref.scores(w, p, int(y[row]), self.t, steps, retain)
            action[row] = Q.exact_action(er, eq, u, int(y[row]))
            myopic[row] = Q.exact_action(min(u, 1-u), F(1, 10), u, int(y[row]))
            self.fallback += 1
        assert np.all(delta >= -2e-12)
        assert not np.any((myopic == 2) & (action != 2))
        extra = (action == 2) & (myopic != 2)
        return action, delta, np.where(extra, r-q, 0.), extra


def integrated(counts, history, boundaries=BOUNDS, share=SHARE):
    """Direct Beta integrals of whole histories; independent of filter updates."""
    probability = [OLD.segment(counts, history)]
    for tau in boundaries:
        old, new = history[:tau-1], history[tau-1:]
        prefix = OLD.segment(counts, old)
        probability.extend(prefix*OLD.segment((0, 0, 0, 0), new, kind) for kind in range(3))
        transformed = list(old)+[(y, None if target is None else target ^ 1) for y, target in new]
        probability.append(OLD.segment(counts, transformed))
    return [p*v for p, v in zip(priors(boundaries, share), probability)]


def latent_paths(counts, history, boundaries):
    """Complete error-path enumeration with four-category Dirichlet moments."""
    hypotheses = [(101, 0)]+[(t, k) for t in boundaries for k in range(4)]
    evidence = [F(0)]*len(hypotheses)
    unknown = [i for i, (_, target) in enumerate(history) if target is None]
    for values in product((0, 1), repeat=len(unknown)):
        targets = [target for _, target in history]
        for i, value in zip(unknown, values):
            targets[i] = value
        errors = [y ^ (3*target) for (y, _), target in zip(history, targets)]
        for j, (tau, kind) in enumerate(hypotheses):
            if kind == 3:
                base_errors = [e ^ (3 if t >= tau else 0) for t, e in enumerate(errors, 1)]
                total = [base_errors.count(k) for k in range(4)]
                probability = Q.moment([F(2*c+1, 2) for c in counts], total)
            else:
                old = [sum(e == k and t < tau for t, e in enumerate(errors, 1)) for k in range(4)]
                new = [sum(e == k and t >= tau for t, e in enumerate(errors, 1)) for k in range(4)]
                probability = Q.moment([F(2*c+1, 2) for c in counts], old)
                if kind == 0:
                    probability *= Q.moment([F(1, 2)]*4, new)
                else:
                    ones = new[1]+new[3] if kind == 1 else new[2]+new[3]
                    probability *= Q.moment([F(1), F(1)], [sum(new)-ones, ones])/2**sum(new)
            evidence[j] += probability/2**len(history)
    return [p*v for p, v in zip(priors(boundaries), evidence)]
