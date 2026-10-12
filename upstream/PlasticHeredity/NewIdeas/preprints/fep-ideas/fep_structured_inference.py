"""Finite grid inference and shared decisions; no execution on import.

Tensor axes follow increasing node id, with the last bit varying fastest.
Only NumPy and the Python standard library are required.
"""
from dataclasses import dataclass
import hashlib
import math
import os
import time

import numpy as np

PROB_TOL = 1e-10
WORK_LEVELS = (256, 1024, 4096)


class ResourceStop(RuntimeError):
    pass


def rss_bytes():
    with open('/proc/self/statm') as stream:
        return int(stream.read().split()[1]) * os.sysconf('SC_PAGE_SIZE')


class Budget:
    def __init__(self, cpu=300.0, memory=512*1024**2):
        self.start = time.process_time()
        self.cpu, self.memory = cpu, memory
        self.peak = rss_bytes()

    def check(self, extra=0):
        current = rss_bytes()
        self.peak = max(self.peak, current)
        if current + extra > self.memory:
            raise ResourceStop('memory_preflight' if extra else 'memory_limit')
        if time.process_time() - self.start >= self.cpu:
            raise ResourceStop('cpu_limit')


def normalize_log(values):
    return values - np.logaddexp.reduce(values.ravel())


def bits(n):
    return np.array(list(np.ndindex(*(2,)*n)), dtype=np.int8)


@dataclass
class Model:
    rows: int
    cols: int
    h: float
    record: str
    prior: np.ndarray
    edges: list
    observations: list
    psi: list
    main: bool

    @property
    def n(self):
        return self.rows*self.cols

    def description(self):
        return {'rows': self.rows, 'cols': self.cols, 'h': self.h,
                'record': self.record, 'main': self.main,
                'prior': self.prior.tolist(), 'edges': self.edges,
                'observations': self.observations,
                'tensor_convention': 'increasing node id; last bit fastest'}


def model(rows, cols, h, record, main=False):
    if rows < 1 or cols < 1 or not 0 < h < .1:
        raise ValueError('invalid grid or physical baseline')
    prior = np.full((rows*cols, 2), .5)
    if main:
        for r in range(rows):
            for c in range(cols):
                byte = hashlib.sha256(f'fep-grid-v1|{r}|{c}'.encode()).digest()[0]
                theta = .05 if byte % 2 == 0 else -.05
                p = 1/(1+math.exp(-theta))
                prior[r*cols+c] = [1-p, p]
    edges, observations = [], []
    for r in range(rows):
        for c in range(cols):
            for k, present, j in [(0, c+1 < cols, r*cols+c+1),
                                   (1, r+1 < rows, (r+1)*cols+c)]:
                if not present:
                    continue
                idx = len(edges)
                edges.append((r*cols+c, j))
                if record == 'fail':
                    o = 1
                elif record == 'success':
                    o = 0
                elif record == 'alternating' and not main:
                    o = int(idx % 2 == 0)
                elif record == 'mixed' and main:
                    o = int((r+c+k) % 4 != 0)
                else:
                    raise ValueError('invalid record for this fixture class')
                observations.append(o)
    a, b, c = h*(2-h), .1+h-.1*h, .1*1.9
    failure = np.array([[a, b], [b, c]])
    # Success uses its exact factorization rather than a cancellation at tiny h.
    success = np.outer([1-h, .9], [1-h, .9])
    psi = [(failure if o else success).copy() for o in observations]
    return Model(rows, cols, h, record, prior, edges, observations, psi, main)


def marginal(table, scope, keep):
    axes = tuple(k for k, v in enumerate(scope) if v not in keep)
    return table.sum(axis=axes) if axes else table.copy()


def enumerate_exact(m):
    if m.n > 16:
        raise ValueError('enumeration restricted to at most sixteen nodes')
    states = bits(m.n)
    weights = np.ones(len(states))
    for i in range(m.n):
        weights *= m.prior[i, states[:, i]]
    for (i, j), psi in zip(m.edges, m.psi):
        weights *= psi[states[:, i], states[:, j]]
    z = float(weights.sum())
    joint = (weights/z).reshape((2,)*m.n)
    return {'log_z': math.log(z), 'nodes': np.array([
                marginal(joint, range(m.n), (i,)) for i in range(m.n)]),
            'pairs': np.array([marginal(joint, range(m.n), e) for e in m.edges]),
            'joint': joint}


def chain_exact(m):
    if m.rows != 1 or m.edges != [(i, i+1) for i in range(m.n-1)]:
        raise ValueError('chain reference requires a single row')
    alpha = [m.prior[0].copy()]
    scales = []
    for j in range(1, m.n):
        a = (alpha[-1] @ m.psi[j-1])*m.prior[j]
        scales.append(float(a.sum()))
        alpha.append(a/a.sum())
    beta = [None]*m.n
    beta[-1] = np.ones(2)
    for i in range(m.n-2, -1, -1):
        b = m.psi[i] @ (m.prior[i+1]*beta[i+1])
        beta[i] = b/b.sum()
    nodes = np.array([a*b/(a*b).sum() for a, b in zip(alpha, beta)])
    pairs = []
    for i in range(m.n-1):
        p = alpha[i][:, None]*m.psi[i]*(m.prior[i+1]*beta[i+1])[None, :]
        pairs.append(p/p.sum())
    return {'log_z': sum(math.log(s) for s in scales),
            'nodes': nodes, 'pairs': np.array(pairs)}


def elimination_layout(m):
    # Query scopes keep every requested pair available during one backward pass.
    scopes = [(i,) for i in range(m.n)] + list(m.edges)
    layout = []
    for v in range(m.n):
        involved = [s for s in scopes if v in s]
        scopes = [s for s in scopes if v not in s]
        scope = tuple(sorted(set().union(*map(set, involved))))
        sep = scope[1:]
        layout.append(scope)
        if sep:
            scopes.append(sep)
    return layout


def exact_elimination(m, limit=None):
    limit = limit or Budget()
    begin = time.process_time()
    layout = elimination_layout(m)
    cells = [2**len(s) for s in layout]
    # Stored backward kernels + forward workspace/messages + model/marginal slack.
    planned = 8*(sum(cells) + 4*max(cells) + 32*(m.n+len(m.edges)))
    limit.check(extra=planned)
    unary = np.log(m.prior).copy()
    pair_factors = []
    for (i, j), o, psi in zip(m.edges, m.observations, m.psi):
        if o:
            pair_factors.append(((i, j), np.log(psi)))
        else:
            unary[i] += np.log([1-m.h, .9])
            unary[j] += np.log([1-m.h, .9])
            # Unit query scope, no likelihood interaction or evidence contribution.
            pair_factors.append(((i, j), np.zeros((2, 2))))
    factors = [((i,), unary[i]) for i in range(m.n)] + pair_factors
    kernels, shifts = [], []
    for v, scope in enumerate(layout):
        limit.check()
        involved = [(s, a) for s, a in factors if v in s]
        factors = [(s, a) for s, a in factors if v not in s]
        table = np.zeros((2,)*len(scope))
        for s, a in involved:
            table += a.reshape(tuple(2 if i in s else 1 for i in scope))
        raw = np.logaddexp.reduce(table, axis=0)
        table -= raw  # log P(v | separator, already eliminated variables summed).
        kernels.append(table)
        shift = float(np.max(raw))
        shifts.append(shift)
        if len(scope) > 1:
            factors.append((scope[1:], raw-shift))
    nodes = np.zeros((m.n, 2))
    pairs = np.zeros((len(m.edges), 2, 2))
    by_first = [[] for _ in range(m.n)]
    for e, (i, j) in enumerate(m.edges):
        by_first[i].append((e, j))
    max_norm = 0.0
    for v in range(m.n-1, -1, -1):
        limit.check()
        scope, joint = layout[v], kernels[v]
        np.exp(joint, out=joint)
        sep = scope[1:]
        if sep:
            parent = sep[0]
            joint *= marginal(kernels[parent], layout[parent], sep)
        max_norm = max(max_norm, abs(float(joint.sum())-1))
        nodes[v] = marginal(joint, scope, (v,))
        for e, j in by_first[v]:
            pairs[e] = marginal(joint, scope, (v, j))
    if max_norm > PROB_TOL:
        raise ArithmeticError(f'exact normalization residual {max_norm}')
    return {'log_z': sum(shifts), 'nodes': nodes, 'pairs': pairs,
            'metadata': {'order': list(range(m.n)), 'scopes': layout,
                         'max_frontier': max(map(len, layout))-1,
                         'table_cells': cells, 'normalization_shifts': shifts,
                         'planned_extra_bytes': planned,
                         'compiled_success_edges': m.observations.count(0),
                         'unit_query_scopes': m.observations.count(0),
                         'normalization_residual': max_norm,
                         'cpu_seconds': time.process_time()-begin}}


def risks(pair, h):
    p = np.asarray(pair, dtype=float)
    if p.shape != (2, 2) or np.min(p) < 0 or abs(float(p.sum())-1) > PROB_TOL:
        raise ArithmeticError('invalid decision belief')
    p = p/p.sum()
    t = np.array([h, .1])
    f0 = float(p.sum(axis=0) @ t)
    f1 = float(np.sum(p*(t[:, None]+t[None, :]-t[:, None]*t[None, :])))
    return f0, f1


def objective(r, f0, f1):
    risk = (1-r)*f0+r*f1
    utility = 1.25+.15*r-.5*risk
    kl = math.log(2)
    if r:
        kl += r*math.log(r)
    if r != 1:
        kl += (1-r)*math.log1p(-r)
    return {'risk': risk, 'utility': utility, 'J': kl-4*utility}


def decision(pair, h):
    f0, f1 = risks(pair, h)
    free = 1/(1+math.exp(-4*(.15-.5*(f1-f0))))
    cap = (.1-f0)/(f1-f0)
    if cap < -PROB_TOL or f1 <= f0:
        raise ArithmeticError('economy infeasible or nonpositive risk increment')
    r = min(free, 1., max(0., cap))
    feasible = [a for a, f in [(0, f0), (1, f1)] if f <= .1+PROB_TOL]
    scores = {a: objective(a, f0, f1)['J'] for a in feasible}
    best = min(scores.values())
    return {'r': r, 'r_free': free, 'cap': cap,
            'negative_cap_roundoff': min(0., cap), 'f0': f0, 'f1': f1,
            'deterministic_optimum_set': [a for a in feasible if abs(scores[a]-best) <= 1e-8],
            **objective(r, f0, f1)}


def decode(m, nodes, pairs, reference=None, block_owner=None):
    records = []
    for e, (i, j) in enumerate(m.edges):
        for reverse in (False, True):
            p = pairs[e].T if reverse else pairs[e]
            source, target = (j, i) if reverse else (i, j)
            chosen = decision(p, m.h)
            record = {'edge': e, 'source': source, 'target': target,
                      'internal': None if block_owner is None else bool(block_owner[i] == block_owner[j]),
                      'chosen': chosen}
            if reference is not None:
                p_true = reference['pairs'][e].T if reverse else reference['pairs'][e]
                exact = decision(p_true, m.h)
                actual = objective(chosen['r'], exact['f0'], exact['f1'])
                excess = actual['risk']-.1
                record.update(exact=exact, actual=actual,
                              economy_actual=objective(0., exact['f0'], exact['f1']),
                              action_error=chosen['r']-exact['r'],
                              risk_errors=[chosen['f0']-exact['f0'], chosen['f1']-exact['f1']],
                              risk_excess=max(0., excess), signed_risk_excess=excess,
                              violated=excess > PROB_TOL,
                              feasible_regret=None if excess > PROB_TOL else actual['J']-exact['J'])
            records.append(record)
    return records


class Inference:
    def __init__(self, m, family, order='forward', limit=None):
        if family not in ('mf', 'block') or order not in ('forward', 'reverse'):
            raise ValueError('unknown family/order')
        start = time.process_time()
        self.m, self.family, self.order = m, family, order
        self.limit = limit or Budget()
        self.groups = []
        step = 1 if family == 'mf' else 2
        for r in range(0, m.rows, step):
            for c in range(0, m.cols, step):
                self.groups.append(tuple(rr*m.cols+cc
                    for rr in range(r, min(r+step, m.rows))
                    for cc in range(c, min(c+step, m.cols))))
        self.owner = np.zeros(m.n, dtype=int)
        self.block = []
        self.nodes = np.zeros((m.n, 2))
        self.work = self.updates = self.normalizations = self.exponentiations = 0
        self.inference_cpu = self.diagnostic_cpu = self.decoding_cpu = 0.
        self.max_descent_increase = self.max_odds_residual = 0.
        self.sweeps, self.offending_updates = [], []
        for g, group in enumerate(self.groups):
            for i in group:
                self.owner[i] = g
            s = bits(len(group))
            pos = {v: k for k, v in enumerate(group)}
            internal, boundary = [], []
            base = np.zeros(len(s))
            for i in group:
                base += np.log(m.prior[i, s[:, pos[i]]])
            for e, (i, j) in enumerate(m.edges):
                if i in pos and j in pos:
                    internal.append(e)
                    base += np.log(m.psi[e][s[:, pos[i]], s[:, pos[j]]])
                elif i in pos or j in pos:
                    inside, outside = (i, j) if i in pos else (j, i)
                    log_factor = np.log(m.psi[e] if inside == i else m.psi[e].T)
                    boundary.append((pos[inside], outside, log_factor))
            logq = normalize_log(base)
            b = {'group': group, 'states': s, 'pos': pos, 'internal': internal,
                 'boundary': boundary, 'base': base, 'logq': logq, 'q': np.exp(logq),
                 'cost': len(s)*(len(group)+len(internal)+2*len(boundary))}
            self.work += len(s)*(len(group)+len(internal))
            self.normalizations += 1
            self.exponentiations += len(s)
            self.block.append(b)
            self._set_nodes(b)
        self.initial_work = self.work
        self.sequence = list(range(len(self.block)))
        if order == 'reverse':
            self.sequence.reverse()
        self.cursor = 0
        self.initialization_cpu = time.process_time()-start
        self.initial = self.snapshot(None)

    def _set_nodes(self, b):
        for k, i in enumerate(b['group']):
            self.nodes[i] = [b['q'][b['states'][:, k] == z].sum() for z in (0, 1)]

    def statistics(self):
        pairs = []
        for i, j in self.m.edges:
            if self.owner[i] == self.owner[j]:
                b = self.block[self.owner[i]]
                p = marginal(b['q'].reshape((2,)*len(b['group'])), b['group'], (i, j))
            else:
                p = np.outer(self.nodes[i], self.nodes[j])
            pairs.append(p)
        return self.nodes.copy(), np.array(pairs)

    def free_energy(self, pairs=None):
        if pairs is None:
            _, pairs = self.statistics()
        entropy_term = sum(float(b['q'] @ b['logq']) for b in self.block)
        unary_term = float(np.sum(self.nodes*np.log(self.m.prior)))
        pair_term = sum(float(np.sum(p*np.log(psi))) for p, psi in zip(pairs, self.m.psi))
        return entropy_term-unary_term-pair_term

    def odds_residual(self, b):
        maximum = 0.
        table = b['logq'].reshape((2,)*len(b['group']))
        for e in b['internal']:
            i, j = self.m.edges[e]
            a, c = b['pos'][i], b['pos'][j]
            axes = [a, c]+[v for v in range(len(b['group'])) if v not in (a, c)]
            q = table.transpose(axes).reshape(2, 2, -1)
            physical = np.log(self.m.psi[e])
            target = physical[0, 0]+physical[1, 1]-physical[0, 1]-physical[1, 0]
            maximum = max(maximum, float(np.max(np.abs(q[0, 0]+q[1, 1]-q[0, 1]-q[1, 0]-target))))
        return maximum

    def update(self):
        if self.updates % 128 == 0:
            self.limit.check()
        start = time.process_time()
        g = self.sequence[self.cursor]
        b = self.block[g]
        target = b['base'].copy()
        for pos, outside, log_factor in b['boundary']:
            target += (log_factor @ self.nodes[outside])[b['states'][:, pos]]
        logstar = normalize_log(target)
        newlog = normalize_log(.75*b['logq']+.25*logstar)
        newq = np.exp(newlog)
        delta = float(newq @ (newlog-logstar)-b['q'] @ (b['logq']-logstar))
        b['logq'], b['q'] = newlog, newq
        self._set_nodes(b)
        self.work += b['cost']
        self.updates += 1
        self.normalizations += 2
        self.exponentiations += len(newq)
        self.cursor = (self.cursor+1) % len(self.block)
        self.inference_cpu += time.process_time()-start
        diag = time.process_time()
        residual = self.odds_residual(b)
        self.max_descent_increase = max(self.max_descent_increase, delta)
        self.max_odds_residual = max(self.max_odds_residual, residual)
        if delta > 1e-9 or residual > PROB_TOL:
            self.offending_updates.append({'update': self.updates, 'block': g,
                                           'delta_F': delta, 'odds_residual': residual})
            raise ArithmeticError('coordinate descent or retained interaction failed')
        if self.cursor == 0:
            self.sweeps.append({'sweep': self.updates//len(self.block),
                                'work': self.work, 'F': self.free_energy()})
        self.diagnostic_cpu += time.process_time()-diag
        return {'block': g, 'delta_F': delta, 'odds_residual': residual}

    def advance(self, budget):
        if budget < self.work:
            raise ValueError('checkpoint precedes completed work')
        while self.work+self.block[self.sequence[self.cursor]]['cost'] <= budget:
            self.update()
        return self.snapshot(budget)

    def snapshot(self, budget):
        start = time.process_time()
        nodes, pairs = self.statistics()
        f = self.free_energy(pairs)
        logs = [b['logq'].copy() for b in self.block]
        self.diagnostic_cpu += time.process_time()-start
        start = time.process_time()
        decisions = decode(self.m, nodes, pairs, block_owner=self.owner)
        self.decoding_cpu += time.process_time()-start
        start = time.process_time()
        product = np.array([np.outer(nodes[i], nodes[j]) for i, j in self.m.edges])
        product_decisions = decode(self.m, nodes, product, block_owner=self.owner)
        self.diagnostic_cpu += time.process_time()-start
        return {'budget': budget, 'work': self.work,
                'unused_budget': None if budget is None else budget-self.work,
                'updates': self.updates, 'next_block': self.sequence[self.cursor],
                'nodes': nodes, 'pairs': pairs, 'block_log_probabilities': logs,
                'groups': self.groups, 'owner': self.owner.copy(), 'F': f,
                'decisions': decisions, 'product_pairs': product,
                'product_decisions': product_decisions,
                'exponentiations': self.exponentiations, 'normalizations': self.normalizations,
                'max_descent_increase': self.max_descent_increase,
                'max_odds_residual': self.max_odds_residual,
                'timing': {'initialization_cpu': self.initialization_cpu,
                           'inference_cpu': self.inference_cpu,
                           'decoding_cpu': self.decoding_cpu,
                           'diagnostic_cpu': self.diagnostic_cpu}}


def full_q(inference):
    if inference.m.n > 16:
        raise ValueError('joint expansion restricted to small qualification/reference cases')
    states = bits(inference.m.n)
    q = np.ones(len(states))
    for b in inference.block:
        idx = states[:, b['group']] @ (2**np.arange(len(b['group'])-1, -1, -1))
        q *= b['q'][idx]
    return q.reshape((2,)*inference.m.n)
