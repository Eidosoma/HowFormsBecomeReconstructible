"""Exact parity alignment; no task outcomes or missing own signs are inputs."""
from collections import deque
import numpy as np


def grid_edges(side=16):
    nodes = np.arange(side * side).reshape(side, side)
    return (np.tile(nodes.ravel(), 2),
            np.concatenate((np.roll(nodes, -1, 1).ravel(),
                            np.roll(nodes, -1, 0).ravel())))


def parity(n, u, v, rhs, pins=()):
    """Solve x[u] XOR x[v]=rhs with x[pins]=0 by a spanning forest.

    Returns deterministic forest coordinates even for inconsistent inputs; callers
    must check ok before using them as an alignment. Witness indices refer to the
    supplied edges followed by virtual-ground-to-pin constraints.
    """
    u, v, rhs = (np.asarray(a, dtype=int) for a in (u, v, rhs))
    pins = np.asarray(pins, dtype=int)
    assert u.shape == v.shape == rhs.shape and u.ndim == 1
    assert np.all((rhs == 0) | (rhs == 1))
    assert np.all((u >= 0) & (u < n) & (v >= 0) & (v < n))
    assert len(set(pins.tolist())) == len(pins)
    if len(pins):
        assert np.all((pins >= 0) & (pins < n))
        u = np.concatenate((u, np.full(len(pins), n)))
        v = np.concatenate((v, pins))
        rhs = np.concatenate((rhs, np.zeros(len(pins), int)))
    size = n + bool(len(pins))
    adjacency = [[] for _ in range(size)]
    for e, (a, b) in enumerate(zip(u, v)):
        adjacency[a].append((b, e)); adjacency[b].append((a, e))
    bits = np.zeros(size, np.uint8)
    component = np.full(size, -1, int)
    parent = np.full(size, -1, int)
    parent_edge = np.full(size, -1, int)
    count = 0
    for root in ([n] if len(pins) else []) + list(range(n)):
        if component[root] >= 0:
            continue
        component[root] = count; count += 1
        queue = deque([root])
        while queue:
            a = queue.popleft()
            for b, edge in adjacency[a]:
                if component[b] < 0:
                    component[b] = component[a]
                    bits[b] = bits[a] ^ rhs[edge]
                    parent[b], parent_edge[b] = a, edge
                    queue.append(b)
    residual = bits[u] ^ bits[v] ^ rhs
    bad = np.flatnonzero(residual)
    witness = []
    if len(bad):
        edge = int(bad[0]); witness = [edge]
        # XOR of the two root paths cancels their shared tail.
        path = set()
        for node in (int(u[edge]), int(v[edge])):
            while parent[node] != -1:
                pe = int(parent_edge[node])
                if pe in path: path.remove(pe)
                else: path.add(pe)
                node = int(parent[node])
        witness += sorted(path)
        incidence = np.zeros(size, np.uint8)
        for e in witness:
            incidence[u[e]] ^= 1; incidence[v[e]] ^= 1
        assert not incidence.any() and np.bitwise_xor.reduce(rhs[witness]) == 1
    free = [c for c in range(count) if not len(pins) or c != component[n]]
    return dict(ok=not len(bad), bits=bits[:n], component=component[:n],
                free_components=free, rank=n-len(free), residual=residual,
                witness=witness)


def bit_rank(values):
    pivots = {}
    for value in values:
        value = int(value)
        while value:
            pivot = value.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = value
                break
            value ^= pivots[pivot]
    return len(pivots)


def packed_bits(a):
    return int.from_bytes(np.packbits(a, bitorder='little').tobytes(), 'little')


def align(outgoing, donor, pins):
    assert outgoing.shape == donor.shape == (2, 16, 16)
    u, v = grid_edges()
    overlap = (outgoing.ravel() != 0) & (donor.ravel() != 0)
    rhs = (np.signbit(outgoing.ravel()[overlap]) ^
           np.signbit(donor.ravel()[overlap])).astype(np.uint8)
    return dict(overlap=overlap, rhs=rhs,
                unpinned=parity(256, u[overlap], v[overlap], rhs),
                pinned=parity(256, u[overlap], v[overlap], rhs, pins))


def edge_flip(bits):
    u, v = grid_edges()
    return (1 - 2 * (np.asarray(bits, int)[u] ^ np.asarray(bits, int)[v])).reshape(2, 16, 16)


def hybrid(outgoing, donor, common, magnitude, bits):
    assert not np.any((outgoing != 0) & common)
    assert np.all(donor[common] != 0) and np.all(magnitude[common] > 0)
    result = outgoing.copy()
    result[common] = magnitude[common] * np.sign(donor[common]) * edge_flip(bits)[common]
    return result


def equivalent(a, b, pins):
    assert a.shape == b.shape == (2, 16, 16)
    # Only sign changes are allowed; this is not arbitrary dynamical equivalence.
    if not np.array_equal(abs(a), abs(b)):
        return dict(ok=False, reason='different magnitudes or support')
    u, v = grid_edges(); support = a.ravel() != 0
    rhs = (np.signbit(a.ravel()[support]) ^ np.signbit(b.ravel()[support])).astype(np.uint8)
    return parity(256, u[support], v[support], rhs, pins)


def ambiguity(n, u, v, keep, backup, solution, pins):
    """Rank of admissible backup changes modulo full-hybrid pinned switching.

    keep/backup select disjoint edges from u,v. Each unconstrained alignment
    component can flip. Forest residuals are a linear, complete test of whether
    the resulting change is a whole-hybrid gauge transformation.
    """
    assert solution['ok'] and not np.any(keep & backup)
    support = keep | backup
    a, b = u[support], v[support]
    on_backup = backup[support]
    syndromes = []; bad_components = []
    for component in solution['free_components']:
        flip = solution['component'] == component
        rhs = on_backup & (flip[a] ^ flip[b])
        check = parity(n, a, b, rhs, pins)
        syndromes.append(packed_bits(check['residual']))
        if not check['ok']:
            bad_components.append(dict(component=int(component),
                                       witness=check['witness']))
    return dict(dimension=bit_rank(syndromes),
                free_bits=len(solution['free_components']),
                non_equivalent_generators=bad_components)
