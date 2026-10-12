"""Independent integer GF(2) elimination, with no graph-solver imports."""


def eliminate(n, coefficients, rhs):
    basis = {}
    consistent = True
    for coefficient, value in zip(coefficients, rhs, strict=True):
        row = int(coefficient); value = int(value)
        assert 0 <= row < (1 << n) and value in (0, 1)
        while row:
            pivot = (row & -row).bit_length() - 1
            if pivot in basis:
                old, old_value = basis[pivot]
                row ^= old; value ^= old_value
            else:
                basis[pivot] = (row, value)
                break
        if not row and value:
            consistent = False
    free = [j for j in range(n) if j not in basis]

    def backsub(value, homogeneous):
        for pivot in sorted(basis, reverse=True):
            row, right = basis[pivot]
            need = ((row & value).bit_count() & 1) ^ (0 if homogeneous else right)
            value ^= need << pivot
        return value

    return dict(ok=consistent, rank=len(basis),
                particular=backsub(0, False),
                null=[backsub(1 << j, True) for j in free])


def constraint_rows(u, v, pins=()):
    return [(1 << int(a)) ^ (1 << int(b)) for a, b in zip(u, v, strict=True)] + [1 << int(p) for p in pins]


def vector_rank(values):
    # Generic row rank; unlike alignment.bit_rank this eliminates low bits.
    n = max((int(v).bit_length() for v in values), default=0)
    return eliminate(n, values, [0] * len(values))['rank']


def ambiguity_rank(n, u, v, keep, backup, overlap, pins):
    """rank([M,T])-rank(M), where M maps pinned gauges to hybrid edge changes."""
    constraints = constraint_rows(u[overlap], v[overlap], pins)
    freedom = eliminate(n, constraints, [0] * len(constraints))['null']
    support_indices = [i for i in range(len(u)) if keep[i] or backup[i]]
    pinned = set(int(p) for p in pins)
    gauge_columns = []
    for node in range(n):
        if node not in pinned:
            column = 0
            for edge, index in enumerate(support_indices):
                if (u[index] == node) != (v[index] == node):
                    column |= 1 << edge
            gauge_columns.append(column)
    change_columns = []
    for null in freedom:
        column = 0
        for edge, index in enumerate(support_indices):
            if backup[index] and (((null >> int(u[index])) ^ (null >> int(v[index]))) & 1):
                column |= 1 << edge
        change_columns.append(column)
    return vector_rank(gauge_columns + change_columns) - vector_rank(gauge_columns)
