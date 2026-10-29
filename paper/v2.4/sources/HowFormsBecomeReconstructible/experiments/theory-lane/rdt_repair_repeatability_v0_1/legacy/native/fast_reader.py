"""Compiled stencil; NumPy power, port reductions and original writer unchanged."""
import ctypes

import numpy as np

from bridge import ROOT, P, e, ev, read


_LIBRARY = None


def kernel():
    global _LIBRARY
    if _LIBRARY is None:
        receipt = read(ROOT/'BUILD.json')
        path = ROOT/receipt['binary']
        if ev.sha(path) != receipt['binary_sha256']:
            raise ValueError('Compiled kernel changed')
        library = ctypes.CDLL(str(path))
        function = library.rdt_step
        function.argtypes = [ctypes.c_size_t]*5 + [ctypes.c_double]*2 + [ctypes.c_void_p]*7
        function.restype = None
        _LIBRARY = library
    return _LIBRARY.rdt_step


def finite_double(value, shape, label):
    a = np.asarray(value)
    if a.dtype != np.float64 or a.shape != shape or not np.isfinite(a).all():
        raise ValueError('Finite binary64 array with exact shape required: '+label)
    return np.ascontiguousarray(a)


class Stepper:
    """Validated buffers, with time-varying body/output ownership kept in Python."""
    def __init__(self, effective, denominator, masks, noises):
        if effective.ndim != 5 or effective.shape[2:] != (2, 16, 16):
            raise ValueError('Environments x branches x two native weight planes required')
        self.nenv, self.branches = effective.shape[:2]
        if not self.nenv or not self.branches:
            raise ValueError('Nonempty native batch required')
        self.steps = P['reader']['read_steps']
        self.shape = (self.nenv, self.branches, 2, 16, 16)
        self.weights = finite_double(effective, self.shape, 'effective weights')
        self.denominator = finite_double(denominator, (self.nenv, self.branches, 16, 16), 'denominator')
        self.noises = finite_double(noises, (self.nenv, self.steps, 2, 16, 16), 'noise')
        if masks.dtype != np.bool_ or masks.shape != (self.nenv, 16, 16):
            raise ValueError('Boolean native injury masks required')
        self.masks = np.ascontiguousarray(masks)
        self.cube = np.empty(self.shape, np.float64)
        self.function = kernel()
        self.prefix = (self.nenv, self.branches, self.steps)

    def advance(self, body, out, t):
        if (body.shape != self.shape or out.shape != self.shape or
            body.dtype != np.float64 or out.dtype != np.float64 or
            not body.flags.c_contiguous or not out.flags.c_contiguous or
            not out.flags.writeable or np.shares_memory(body, out) or
            not isinstance(t, (int, np.integer)) or not 0 <= t < self.steps):
            raise ValueError('Distinct contiguous binary64 state buffers and a valid time index required')
        # Use the same ufunc and exponent as value**3 in the frozen equations.
        np.power(body, 3, out=self.cube)
        cfg = P['reader']
        self.function(*self.prefix, t, cfg['settling_steps'], cfg['dt'], cfg['noise'],
            self.weights.ctypes.data, self.denominator.ctypes.data, body.ctypes.data,
            self.cube.ctypes.data, self.noises.ctypes.data, self.masks.ctypes.data, out.ctypes.data)


def read_batch(weights, envs):
    a = np.asarray(weights)
    if a.ndim != 5 or a.shape[2:] != (2, 16, 16) or len(envs) != len(a):
        raise ValueError('Environments x branches x two native weight planes required')
    weights = finite_double(a, a.shape, 'input packet')
    if not len(a) or not a.shape[1]:
        raise ValueError('Nonempty native batch required')
    masks, births, noises = [np.stack([v[k] for v in envs]) for k in range(3)]
    births = finite_double(births, (len(a), 2, 16, 16), 'birth')
    if masks.dtype != np.bool_ or masks.shape != (len(a), 16, 16):
        raise ValueError('Boolean native masks required')
    effective = weights*e.native.available_edges(masks)[:, None]
    denominator = e.native.incident(abs(effective))
    stepper = Stepper(effective, denominator, masks, noises)
    body = np.repeat(births[:, None], a.shape[1], axis=1)
    body *= (~masks)[:, None, None]
    body[..., e.PORTS[0]] = np.array([1., -1.])[None, None, :, None]
    out = np.empty_like(body)
    windows = []
    cfg = P['reader']
    for t in range(cfg['read_steps']):
        stepper.advance(body, out, t)
        body, out = out, body
        if t >= cfg['read_steps']-cfg['observe_steps']:
            windows.append(e.native.read_ports(body))
    outgoing = []
    for j in range(len(weights)):
        pairs, _ = e.native.writer_components(body[j, :, None, None], masks[j, None, None],
                                            P['writer']['beta'], 1e-4)
        outgoing.append(pairs['exact_rewrite'][:, 0, 0])
    return dict(end=body, windows=np.stack(windows, axis=1), outgoing=np.stack(outgoing))
