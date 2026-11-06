"""Exact finite-pool costs and hard-budget/common-margin linear programming."""
from fractions import Fraction as F
import math

import fep_burst_alltiming_core as previous

K = previous.K
PROFILES = previous.PROFILES
MUS = (0, 1, 2, 4, 8, 16)
FAMILIES = ('full', 'ablated')


def names(family):
    return tuple(f'{family}_mu{mu:02d}' for mu in MUS) + (family + '_floor',)


def costs(graph, profile, T=10, tau=None):
    assert len(profile) == T-1
    scales, transitions = [], []
    for a in profile:
        n, d = a.numerator, a.denominator
        scales.append(20*d)
        transitions.append(((19*d+n, d-n), (19*(d-n), d+19*n)))
    den = 20*math.prod(scales)
    suffix = [math.prod(scales[j:]) for j in range(T)]
    mass = [[0, 0] for _ in graph]
    mass[0] = [19, 1]
    totals, terminal = [0]*4, 0
    for i in sorted(range(len(graph)), key=lambda j: graph[j]['t']):
        node = graph[i]
        t = node['t']
        post = tau is not None and t >= tau
        bought = node['action'] == 'B'
        for z, probability in enumerate(mass[i]):
            if not probability:
                continue
            label = int(post)^z
            error = int(not bought and label != int(node['action'] == 'R'))
            for j, reward in enumerate((error, int(bought), error if post else 0, int(bought and post))):
                totals[j] += probability*suffix[t-1]*reward
            child = node['children'][str(label) if bought else 'N']
            if t == T:
                assert child is None
                terminal += probability
            else:
                for nextz, weight in enumerate(transitions[t-1][z]):
                    mass[child][nextz] += probability*weight
    assert terminal == den
    e, b, pe, pb = [F(v, den) for v in totals]
    return dict(onset=tau, errors=e, purchases=b, post_errors=pe, post_purchases=pb,
        cost=e+b/10, post_cost=pe+pb/10, recovery=None if tau is None else (pe+pb/10)/(T-tau+1))


def cost_record(graph, profile, T=10):
    worlds = [costs(graph, profile, T, tau) for tau in [None, *range(1, T+1)]]
    stable = worlds[0]['cost']/T
    full = stable/2 + sum(w['cost'] for w in worlds[1:])/(2*T*T)
    recovery = sum(w['recovery'] for w in worlds[1:])/T
    return dict(worlds=worlds, summary=dict(stable=stable, B=full, R=recovery, J=full+recovery))


def simplex(A, b, c, max_pivots=2000):
    """Max c*x for x>=0, A*x<=b>=0, with Bland pivots and exact certificates."""
    m, n = len(b), len(c)
    assert len(A) == m and all(len(row) == n for row in A) and all(v >= 0 for v in b)
    rows = [[F(v) for v in row] + [F(i == j) for j in range(m)] + [F(rhs)]
            for i, (row, rhs) in enumerate(zip(A, b))]
    objective = [-F(v) for v in c] + [F(0)]*(m+1)
    basis = list(range(n, n+m))
    pivots = []
    while True:
        enter = next((j for j, v in enumerate(objective[:-1]) if v < 0), None)
        if enter is None:
            break
        if len(pivots) >= max_pivots:
            raise RuntimeError('Predeclared simplex pivot ceiling exceeded')
        possible = [(row[-1]/row[enter], basis[i], i) for i, row in enumerate(rows) if row[enter] > 0]
        if not possible:
            raise RuntimeError('Unexpected unbounded linear program')
        ratio, leaving, i = min(possible)
        divisor = rows[i][enter]
        rows[i] = [v/divisor for v in rows[i]]
        for j, row in enumerate(rows):
            if j != i and row[enter]:
                scale = row[enter]
                rows[j] = [x-scale*y for x, y in zip(row, rows[i])]
        scale = objective[enter]
        objective = [x-scale*y for x, y in zip(objective, rows[i])]
        basis[i] = enter
        pivots.append(dict(enter=enter, leave=leaving, row=i, ratio=ratio, objective=objective[-1]))
    allx = [F(0)]*(n+m)
    for j, row in zip(basis, rows):
        allx[j] = row[-1]
    x, y, optimum = allx[:n], objective[n:n+m], objective[-1]
    assert min(x+y) >= 0
    assert all(sum(a*v for a, v in zip(row, x)) <= rhs for row, rhs in zip(A, b))
    assert all(sum(A[i][j]*y[i] for i in range(m)) >= c[j] for j in range(n))
    assert sum(u*v for u, v in zip(c, x)) == sum(u*v for u, v in zip(b, y)) == optimum
    return dict(x=x, dual=y, objective=optimum, basis=basis, pivots=pivots,
                primal_slacks=[rhs-sum(a*v for a, v in zip(row, x)) for row, rhs in zip(A, b)],
                dual_slacks=[sum(A[i][j]*y[i] for i in range(m))-c[j] for j in range(n)])


def problem(records, hybrid, family, budget=K, profile_order=None):
    order = tuple(PROFILES) if profile_order is None else tuple(profile_order)
    pool = names(family)
    other, floor = pool[:-1], pool[-1]
    labels = ['weights:sum']
    A, b = [[F(1)]*6+[F(0)]], [F(1)]
    for label in order:
        ps = records[label]
        floor_s, floor_r = ps[floor]['summary']['stable'], ps[floor]['summary']['R']
        assert floor_s < budget and floor_r < 1+min(F(1,10), hybrid[label])
        s = [ps[n]['summary']['stable']-floor_s for n in other]
        r = [ps[n]['summary']['R']-floor_r for n in other]
        labels.extend(label+':'+k for k in ('hard_budget', 'stable', 'always_recovery', 'hybrid_recovery'))
        A.extend([s+[F(0)], s+[F(1)], r+[F(1)], r+[F(1)]])
        b.extend([budget-floor_s, budget-floor_s+1, F(1,10)-floor_r+1, hybrid[label]-floor_r+1])
    return dict(A=A, b=b, c=[F(0)]*6+[F(1)], row_ids=labels,
                variables=list(other)+['shifted_margin'], floor=floor, profiles=order, budget=budget)


def solve(p):
    solution = simplex(p['A'], p['b'], p['c'])
    weights = solution['x'][:-1] + [1-sum(solution['x'][:-1])]
    labels = p['variables'][:-1] + [p['floor']]
    assert min(weights) >= 0 and sum(weights) == 1
    margin = solution['objective']-1
    return dict(problem=p, certificate=solution, margin=margin, feasible=margin > 0,
                components=[dict(policy=n, weight=w) for n, w in zip(labels, weights) if w],
                active=[n for n, slack in zip(p['row_ids'], solution['primal_slacks']) if not slack],
                dual_support=[dict(constraint=n, weight=w) for n, w in zip(p['row_ids'], solution['dual']) if w])
