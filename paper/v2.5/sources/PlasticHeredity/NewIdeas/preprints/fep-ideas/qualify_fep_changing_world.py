"""Independent small-case likelihood enumeration for changing-world v1.

This is a separate numerical route in the same implementation, not an
independently authored audit. Called only after source/design freezing.
"""
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
from math import log, prod
from time import perf_counter, process_time
import numpy as np


@lru_cache(None)
def moment(initial, added):
    n = sum(added)
    numerator = prod(prod(2*initial[j]+1+2*k for k in range(added[j])) for j in range(4))
    denominator = prod(2*sum(initial)+4+2*k for k in range(n))
    return F(numerator, denominator)


@lru_cache(None)
def evidence(initial, history, resets):
    """Sum latent ordered error paths with independent Dirichlet moments."""
    options = [(y, 3-y) if w is None else (y ^ (3*w),) for y, w in history]
    total = F(0)
    for errors in product(*options):
        counts = [[0]*4 for _ in range(len(resets)+1)]
        for t, e in enumerate(errors, 1):
            segment = sum(t >= boundary for boundary in resets)
            counts[segment][e] += 1
        total += prod(moment(initial if j == 0 else (0, 0, 0, 0), tuple(c)) for j, c in enumerate(counts))
    return total/F(2)**len(history)


def direct_prediction(initial, history, y, arm, boundaries):
    if arm == 'F':
        history, configurations, prior = (), [()], [F(1)]
    elif arm == 'S':
        configurations, prior = [()], [F(1)]
    elif arm == 'R':
        configurations, prior = [tuple(boundaries)], [F(1)]
    else:
        configurations = [()]+[(t,) for t in boundaries]
        prior = [F(1, 2), F(1, 6), F(1, 6), F(1, 6)]
        if arm == 'C-Y':
            history = tuple((yy, None) for yy, _ in history)
    nums = [[prior[j]*evidence(initial, tuple(history)+((y, w),), conf) for w in (0, 1)]
            for j, conf in enumerate(configurations)]
    den = sum(map(sum, nums))
    orientation = sum(row[1-(y >> 1)] for row in nums)/den
    weights = [sum(row)/den for row in nums]
    if len(weights) == 1:
        weights += [F(0)]*3
    old = sum(p*evidence(initial, tuple(history), conf) for p, conf in zip(prior, configurations))
    return orientation, weights, den/old, nums


def compositions(n):
    for a in range(n+1):
        for b in range(n-a+1):
            for c in range(n-a-b+1):
                yield (a, b, c, n-a-b-c)


def qualify(M, cpus):
    start, cpu = perf_counter(), process_time()
    before = dict(M.CHECKS)
    check = M.check
    pop = M.population()
    check('population', 'complete and distinct laws', len(pop) == len({tuple(x['laws'][0]) for x in pop}) == 27)
    check('population', '270 conditions and balanced weight', len(M.CONDITIONS)*len(pop) == 270
          and 27*F(1, 54)+243*F(1, 486) == 1 and np.allclose(M.group_weights().sum(axis=1), 1))
    for meta in pop:
        a, b = F(meta['a']), F(meta['b'])
        laws = [tuple(map(F, x)) for x in meta['laws']]
        check('population', 'simplex and old marginals', all(min(q) >= 0 and sum(q) == 1 for q in laws)
              and laws[0][2]+laws[0][3] == a and laws[0][1]+laws[0][3] == b)
        q = laws[0]
        # A/B replacement by independent fair bits, direct kernel application.
        for which in (1, 2):
            derived = [F(0)]*4
            for e, bit in product(range(4), (0, 1)):
                e2 = (bit << 1) | (e & 1) if which == 1 else (e & 2) | bit
                derived[e2] += q[e]/2
            check('population', 'replacement law', tuple(derived) == laws[which])
        for y in range(4):
            check('identifiability', 'reversal warning equality', (q[y]+q[3-y])/2 == (laws[3][y]+laws[3][3-y])/2)
        swap = next(x for x in pop if x['a'] == meta['b'] and x['b'] == meta['a'] and x['d'] == meta['d'])
        check('population', 'both sensor orders', tuple(map(F, swap['laws'][0])) == (q[0], q[2], q[1], q[3]))
        for law in laws:
            # Independent enumeration of the four warning-conditional actions.
            total = F(0)
            for y in range(4):
                total += min(law[y]/2, law[3-y]/2, (law[y]+law[3-y])/20)
            check('floor', 'known-Q floor uses paid references', M.floor(law) == total <= F(1, 10))
    for n in range(4):
        for c in compositions(n):
            p = M.initial_parameters(np.array([c]))[0]
            g, u0, u1 = F(int(p[0]), int(p[1])), F(int(2*p[2]), int(2*p[3])), F(int(2*p[4]), int(2*p[5]))
            reconstructed = ((1-g)*(1-u0), g*(1-u1), g*u1, (1-g)*u0)
            for e in range(4):
                v = tuple(int(j == e) for j in range(4))
                check('factorization', 'conjugate Dirichlet prediction', reconstructed[e] == moment(c, v))

    # Every partial/complete observation history of length <=2, and every
    # calibration histogram through N=2. Both current parities are checked;
    # all four warning orientations and both revealed targets occur in histories.
    tokens = tuple((y, w) for y in range(4) for w in (None, 0, 1))
    cals = [c for n in range(3) for c in compositions(n)]
    boundaries = (2, 3, 4)
    histories_checked = 0
    for h in range(3):
        cases = [(c, hist, y) for c in cals for hist in product(tokens, repeat=h) for y in (0, 1)]
        filt = M.Filter(np.array([x[0] for x in cases]), boundaries)
        for t in range(1, h+1):
            filt.start(t)
            ys = np.array([x[1][t-1][0] for x in cases], dtype=np.int8)
            ws = np.array([-1 if x[1][t-1][1] is None else x[1][t-1][1] for x in cases], dtype=np.int8)
            filt.warning(ys)
            # These are forced-observation qualification paths, not main actions.
            filt.retain(np.broadcast_to(ws[:, None], (len(cases), 5)))
        filt.start(h+1)
        actions, nll, _, orient = filt.warning(np.array([x[2] for x in cases]))
        probs = np.exp(filt.logw)
        for i, (c, hist, y) in enumerate(cases):
            for j, arm in enumerate(M.ARMS):
                exact_u, weights, pred, joint = direct_prediction(c, hist, y, arm, boundaries)
                expected = 2 if min(exact_u, 1-exact_u) >= F(1, 10) else (y >> 1) ^ int(exact_u > F(1, 2))
                check('enumeration', 'orientation and action', abs(orient[i, j]-float(exact_u)) < 2e-12 and actions[i, j] == expected)
                check('enumeration', 'warning likelihood and change mixture', abs(nll[i, j]+log(float(pred))) < 2e-12
                      and np.allclose(probs[i, j], list(map(float, weights)), rtol=0, atol=2e-12))
                replay = M.rational_state(c, hist, arm, boundaries, current=y)
                check('rational', 'separate replay agrees with path sum', replay[2] == exact_u and replay[0] == weights)
                if arm == 'C' and h == 2 and y == 0:
                    mass = [v for row in joint for v in row]
                    z = sum(mass)
                    posterior = [v/z for v in mass]
                    trial = [F(1, len(mass))]*len(mass)
                    vfe = sum(float(q)*log(float(q/p)) for q, p in zip(trial, mass))
                    kl = sum(float(q)*log(float(q/p)) for q, p in zip(trial, posterior))
                    check('vfe', 'conditional finite VFE identity', abs(vfe-kl+log(float(z))) < 1e-11 and vfe >= -log(float(z))-1e-11)
            histories_checked += 1

    # Exact-action boundary replay is exercised both in common and mixed states.
    tie = M.Filter(np.array([[4, 0, 0, 0]]))
    tie.start(1)
    actions, _, _, _ = tie.warning(np.array([0]))
    check('ties', 'all exact .1 risks ask', np.all(actions == 2) and tie.fallback[0] == 5)
    for priors, bounds, comparator in [((F(1), F(0), F(0), F(0)), (2, 3, 4), 1),
                                       ((F(0), F(1), F(0), F(0)), (2, 101, 102), 3)]:
        filt = M.Filter(np.array([[16, 4, 0, 0], [0, 1, 3, 12]]), bounds, priors)
        for t in range(1, 9):
            filt.start(t)
            ys = np.array([t % 4, (t+1) % 4], dtype=np.int8)
            acts, nll, _, _ = filt.warning(ys)
            check('reductions', 'stationary/certain reset predictions', np.array_equal(acts[:, 2], acts[:, comparator])
                  and np.allclose(nll[:, 2], nll[:, comparator], rtol=0, atol=2e-12))
            # Matching policies obtain exactly matching labels on their asks.
            ws = np.array([t % 2, (t+1) % 2])
            filt.retain(np.where(acts == 2, ws[:, None], -1))

    # Hidden targets cannot change a policy state when warnings agree and paid
    # labels are discarded. The true targets are complemented in the second row.
    filt = M.Filter(np.array([[16, 4, 0, 0]]*2), (2, 3, 4))
    for t in range(1, 9):
        filt.start(t)
        acts, _, _, _ = filt.warning(np.array([t % 4]*2))
        check('access', 'identical warning-only/frozen actions', np.array_equal(acts[0, (0, 4)], acts[1, (0, 4)]))
        worlds = np.array([t % 2, t % 2 if t < 2 else 1-t % 2])
        filt.retain(np.where(acts == 2, worlds[:, None], -1))
        check('access', 'no hidden-target update', np.array_equal(filt.p[0, (0, 4)], filt.p[1, (0, 4)])
              and np.array_equal(filt.logw[0, (0, 4)], filt.logw[1, (0, 4)]))
    one = M.Filter(np.array([[0, 0, 0, 0]]))
    one.start(1)
    a, _, _, _ = one.warning(np.array([0]))
    check('retention', 'same last-task cost before label retention', a[0, 2] == a[0, 4] == 2)
    one.retain(np.array([[0]*5]))
    check('retention', 'paid-label evidence retained only by full arm', not np.array_equal(one.p[:, 2], one.p[:, 4])
          and np.all(one.labels[:, 4] == -1))

    # Independent three-task decision/cost comparison on all ordered hidden paths.
    paths = list(product(range(8), repeat=3))  # symbol 4*W+E
    c = (16, 4, 0, 0)
    filt = M.Filter(np.tile(c, (len(paths), 1)), (2, 3, 4))
    histories = [[[] for _ in M.ARMS] for _ in paths]
    fast_units = np.zeros((len(paths), 5), dtype=int)
    direct_units = np.zeros_like(fast_units)
    for t in range(1, 4):
        ws = np.array([p[t-1]//4 for p in paths])
        es = np.array([p[t-1]%4 for p in paths])
        ys = es ^ (3*ws)
        filt.start(t)
        acts, _, _, _ = filt.warning(ys)
        for row, path in enumerate(paths):
            y, w = int(ys[row]), int(ws[row])
            for j, arm in enumerate(M.ARMS):
                u, _, _, _ = direct_prediction(c, tuple(histories[row][j]), y, arm, (2, 3, 4))
                a = 2 if min(u, 1-u) >= F(1, 10) else (y >> 1) ^ int(u > F(1, 2))
                check('toy_episode', 'policy matches latent-path calculation', a == acts[row, j])
                direct_units[row, j] += 1 if a == 2 else 10*int(a != w)
                histories[row][j].append((y, w if a == 2 else None))
        fast_units += np.where(acts == 2, 1, 10*(acts != ws[:, None]))
        filt.retain(np.where(acts == 2, ws[:, None], -1))
    check('toy_episode', 'all realised costs exact', np.array_equal(fast_units, direct_units))
    q = tuple(F(x, 20) for x in (14, 3, 2, 1))
    mass = [prod(q[s % 4]/2 for s in path) for path in paths]
    check('toy_episode', 'physical path normalization', sum(mass) == 1)

    # Seeds, full horizon and worker-count reproducibility without main prefixes.
    meta = dict(label='synthetic_qualification', laws=[[str(F(x, 400)) for x in (221, 119, 39, 21)]])
    jobs = [(meta, list(range(i, i+1)), 'qualification-fep-changing-world-v1', None) for i in range(4)]
    with ProcessPoolExecutor(max_workers=1, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        serial = list(pool.map(M.worker, jobs))
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        parallel = list(pool.map(M.worker, jobs))
    check('replay', 'one and four workers identical', [v['fingerprint'] for v in serial] == [v['fingerprint'] for v in parallel])
    check('resources', 'all workers confined', all(v['cpus'] == cpus for v in serial+parallel))
    arrays, _ = M.run_batch(meta, [0], 'qualification-fep-changing-world-v1')
    check('replay', 'fixed-seed replay', M.fingerprint(arrays) == serial[0]['fingerprint'])
    check('records', 'per-block and profile schema', arrays['wrong'].shape == (1, 10, 5)
          and arrays['profile_sum'].shape == (9, 5, 100) and arrays['contrast_profile_sum'].shape == (9, 4, 100)
          and arrays['belief_profile_sum'].shape == (10, 2, 2, 100) and arrays['window_loss'].shape == (1, 10, 5, 3))
    check('seeds', 'independent prefixes and blocks', len({M.seed_for(meta['label'], i, p) for i in range(4)
          for p in ('fep-changing-world-v1', 'qualification-fep-changing-world-v1', 'benchmark-fep-changing-world-v1')}) == 12)
    constant = M.interval(np.full((27, 1024), F(1, 8), dtype=float))
    check('uncertainty', 'constant paired difference has zero MC error', constant['mean'] == .125 and constant['mc_se'] == 0)
    ramp = M.interval(np.tile(np.arange(1024)/1024, (27, 1)))
    expected_variance = 1025/(12*27*1024**2)
    check('uncertainty', 'stratified independent-block variance', abs(ramp['mc_se']**2-expected_variance) < 1e-16
          and ramp['mean'] == 1023/2048)
    test_weights = M.group_weights()
    check('uncertainty', 'coupled conditions have correct weights', test_weights[0, 0] == .5
          and np.allclose(test_weights[0, 1:], 1/18) and np.allclose(test_weights[2, 1:], 1/9))
    groups = {k:v-before.get(k, 0) for k, v in M.CHECKS.items() if v-before.get(k, 0)}
    return dict(status='PASS', groups=groups, checks=sum(groups.values()), wall_seconds=perf_counter()-start,
        cpu_seconds=process_time()-cpu, accessible_history_cases=histories_checked,
        exact_three_task_physical_paths=len(paths), worker_replay_blocks=4, worker_counts=[1, 4],
        independent_reference='latent-error sequence sums and rational Dirichlet moments; same authorship',
        no_main_population_performance_evaluated=True)
