"""The cable equation on a batch of periodic sheets with arbitrary junction conductances, as one sparse system.

(g_l + L_g) v = I, where (L_g v)_i = sum_j g_ij (v_i - v_j) over the four neighbours; gH[i, j] couples (i, j)-(i, j + 1)
and gW[i, j] couples (i, j)-(i + 1, j) (lr001's convention, as be001.sim.apply_A). The batch is one block-diagonal CSR
matrix with a fixed five-point pattern, solved by Jacobi-preconditioned conjugate gradients per branch (be001.sim.
cable_cg's algorithm and stopping rule; only the summation order of its dot products differs).
"""
from __future__ import annotations

import numpy as np
from scipy import sparse

from . import design as D


class Cable:
    def __init__(self, k, n=D.SIDE):
        i = np.arange(k * n * n).reshape(k, n, n)
        cols = np.stack([i, np.roll(i, -1, -1), np.roll(i, 1, -1), np.roll(i, -1, -2), np.roll(i, 1, -2)], -1)
        self.k, self.n, self.size = k, n, k * n * n
        self.indices = cols.reshape(-1).astype(np.int64)
        self.indptr = np.arange(0, 5 * self.size + 1, 5, dtype=np.int64)

    def matrix(self, gH, gW):
        """The system matrix and its diagonal (k, n * n)."""
        gl, gu = np.roll(gH, 1, -1), np.roll(gW, 1, -2)
        diag = D.G_LEAK + gH + gl + gW + gu
        data = np.stack([diag, -gH, -gl, -gW, -gu], -1).reshape(-1)
        A = sparse.csr_matrix((data, self.indices, self.indptr), shape=(self.size, self.size))
        return A, diag.reshape(self.k, -1)

    def solve(self, I, gH, gW, x0, tol=D.CG_TOL, maxit=D.CG_MAXIT):
        """Solve per branch from x0; returns the potentials (k, n, n) and the iterations used."""
        A, diag = self.matrix(gH, gW)
        k = self.k
        b = I.reshape(k, -1)
        x = x0.reshape(k, -1).copy()
        res = b - (A @ x.reshape(-1)).reshape(k, -1)
        z = res / diag
        p = z.copy()
        rz = np.einsum("ij,ij->i", res, z)[:, None]
        norm = np.sqrt(np.einsum("ij,ij->i", b, b))[:, None] + 1e-300
        it = 0
        for it in range(maxit):
            if (np.sqrt(np.einsum("ij,ij->i", res, res))[:, None] <= tol * norm).all():
                break
            Ap = (A @ p.reshape(-1)).reshape(k, -1)
            pAp = np.einsum("ij,ij->i", p, Ap)[:, None]
            alpha = np.divide(rz, pAp, out=np.zeros_like(rz), where=pAp > 0)     # a branch already exact stays put
            x += alpha * p
            res -= alpha * Ap
            z = res / diag
            rz_new = np.einsum("ij,ij->i", res, z)[:, None]
            p = z + np.divide(rz_new, rz, out=np.zeros_like(rz), where=rz > 0) * p
            rz = rz_new
        return x.reshape(I.shape), it
