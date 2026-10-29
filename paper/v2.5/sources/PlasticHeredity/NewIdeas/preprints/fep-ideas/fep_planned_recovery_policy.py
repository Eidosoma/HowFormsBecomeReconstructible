"""Clock-aware CT4 action selection; the structured inference model is unchanged."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import numpy as np
import fep_structured_reversal as R
import fep_planned_checking as A


class Clock(R.Filter):
    """Compute optional/compulsory future values together, sharing belief branches."""
    def before_pair(self, w, p, t, h, retain=True):
        if not h:
            return np.zeros(len(w)), np.zeros(len(w))
        p = self.advance(p, t)
        optional, compulsory = np.zeros(len(w)), np.zeros(len(w))
        for parity in (False, True):
            z = np.full(len(w), parity)
            ww, pp = self.observe_warning(w, p, z, self.active(t))
            answer, buy, _, _ = self.clock_scores(ww, pp, z, t, h, retain)
            optional += np.minimum(answer, buy)
            compulsory += buy
        return optional, compulsory

    def clock_scores(self, w, p, z, t, h=4, retain=True):
        h = min(h, 101-t)
        assert h >= 1
        kind = self.active(t)
        total = w.sum(axis=1)
        one = (w*self.orientation(p, z, kind)).sum(axis=1)
        risk = np.minimum(one, total-one)
        common, forced = self.before_pair(w, p, t+1, h-1, retain)
        labelled = np.zeros(len(w))
        if retain:
            for x in (False, True):
                ww, pp = self.observe_label(w, p, z, x, kind)
                next_optional, _ = self.before_pair(ww, pp, t+1, h-1, retain)
                labelled += next_optional
        else:
            labelled = common
        return risk+forced, .1*total+labelled, forced-common, common-labelled

    def choose_clock(self, steps=4, force_exact=False):
        """Optional root proposal; current compulsory action is applied by the runner."""
        answer, buy, clock, information = self.clock_scores(self.w, self.p, self.z, self.t, steps)
        y = self.ys[:, self.t-1]
        action = np.where(buy <= answer, 2, (y >> 1) ^ (self.u > .5)).astype(np.int8)
        risk = np.minimum(self.u, 1-self.u)
        myopic_buy = risk >= .1
        near = (np.abs(answer-buy) <= 1e-11) | (np.abs(risk-.1) <= 1e-12)
        if force_exact:
            near = np.ones(self.n, dtype=bool)
        for row in np.flatnonzero(near):
            assert self.share == R.SHARE
            history = [(int(self.ys[row, j]), None if self.labels[row, j] < 0 else int(self.labels[row, j]))
                       for j in range(self.t-1)]
            ref = A.Reference(tuple(map(int, self.counts[row])), self.boundaries)
            w, p = ref.pack(*ref.state(history, int(y[row])))
            h = min(steps, 101-self.t)
            value = ref.post(w, p, int(y[row]), self.t, h, 0, 'clock')
            common, _ = ref.pre(w, p, self.t+1, h-1, 0, 'clock')
            p1 = ref.label(w, [list(v) for v in p], int(y[row]), 1, self.t)[2]
            action[row] = 2 if value['buy'] else int(p1 > A.F(1, 2))
            myopic_buy[row] = min(p1, 1-p1) >= A.F(1, 10)
            answer[row], buy[row] = float(value['answer']), float(value['purchase'])
            clock[row] = float(value['answer_future']-common)
            information[row] = float(common-value['purchase_future'])
            self.fallback += 1
        assert np.all(clock >= -2e-12) and np.all(information >= -2e-12)
        assert not np.any(myopic_buy & (action != 2))
        return dict(proposed=action, information=information, clock_benefit=clock,
                    scores=np.column_stack((answer, buy)),
                    extra=(action == 2) & ~myopic_buy, fallback_mask=near)
