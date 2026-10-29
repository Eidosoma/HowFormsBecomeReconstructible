"""D192 causal kernel: protected capture access, with fixed body theta reading.

No executor, data writer, model fitting or scientific cohort is run here.
Historical modules remain immutable. Repair accepts only physical context and
the declared zero-memory boundary, never scoring templates or parent memories.
"""

from dataclasses import asdict, dataclass, replace
import hashlib
import time

import numpy as np

from . import l22_early_capture as capture

boundary, source = capture.boundary, capture.source
CONFIG, READOUT = capture.CONFIG, capture.READOUT
BLOCKS, DISPOSABLE, QUALIFICATION = (319100, 319101, 319102, 319103), 603191, 703192
TAG = 'd192-snapshot-routes-v1'
KINDS = ('gated', 'held', 'snapshot_only', 'scrambled', 'ordinary_fixed',
         'ordinary_live', 'captured_live', 'captured_held_live')
ROUTE_KEYS = ('S', 'U', 'body_input', 'writer_input', 'a')


@dataclass(frozen=True)
class Spec:
    packet: str
    kind: str = 'gated'
    body_access: bool = True
    writer_access: bool = True
    write: bool = True

    def __post_init__(self):
        if self.packet not in boundary.PACKETS or self.kind not in KINDS:
            raise ValueError('undeclared packet family or route kind')
        if any(type(v) is not bool for v in (self.body_access, self.writer_access, self.write)):
            raise ValueError('route switches must be booleans')
        if self.kind not in ('gated', 'held') and not all((self.body_access, self.writer_access, self.write)):
            raise ValueError('only declared gated/held paths accept switches')
        if self.kind == 'held' and (not self.writer_access or not self.write):
            raise ValueError('held comparators always use protected snapshot writing')
        if not self.write and (not self.body_access or not self.writer_access):
            raise ValueError('writer-off comparator retains both direct accesses')


def plan():
    result = {}
    for packet in boundary.PACKETS:
        for b in (0, 1):
            for w in (0, 1):
                result[f'{packet}__B{b}W{w}'] = Spec(packet, body_access=bool(b), writer_access=bool(w))
        result[f'{packet}__held_B1W1'] = Spec(packet, 'held')
        result[f'{packet}__held_B0W1'] = Spec(packet, 'held', body_access=False)
        result[f'{packet}__snapshot_only'] = Spec(packet, 'snapshot_only')
        result[f'{packet}__writer_off'] = Spec(packet, write=False)
        result[f'{packet}__scrambled_B1W1'] = Spec(packet, 'scrambled')
        for name in ('ordinary_fixed', 'ordinary_live', 'captured_live', 'captured_held_live'):
            result[f'{packet}__{name}'] = Spec(packet, name)
    return result


def comparisons():
    """Signed linear coefficients, fixed before scientific outcomes."""
    result = {}
    for p in boundary.PACKETS:
        terms = {
            'body_at_W1': {'B1W1': 1., 'B0W1': -1.},
            'body_at_W0': {'B1W0': 1., 'B0W0': -1.},
            'writer_at_B1': {'B1W1': 1., 'B1W0': -1.},
            'writer_at_B0': {'B0W1': 1., 'B0W0': -1.},
            'interaction': {'B1W1': 1., 'B0W1': -1., 'B1W0': -1., 'B0W0': 1.},
            'body_mean': {'B1W1': .5, 'B0W1': -.5, 'B1W0': .5, 'B0W0': -.5},
            'writer_mean': {'B1W1': .5, 'B1W0': -.5, 'B0W1': .5, 'B0W0': -.5},
        }
        for name in ('B1W1', 'B0W1', 'B1W0', 'B0W0'):
            terms[name+'_vs_snapshot'] = {name: 1., 'snapshot_only': -1.}
            terms[name+'_gain'] = {name: 1., 'incoming': -1.}
        for name, left, right in (
            ('snapshot_gain', 'snapshot_only', 'incoming'),
            ('writer', 'B1W1', 'writer_off'), ('organization', 'B1W1', 'scrambled_B1W1'),
            ('capture_fixed', 'B1W1', 'ordinary_fixed'),
            ('capture_live', 'captured_live', 'ordinary_live'),
            ('theta_feedback', 'captured_live', 'B1W1'),
            ('live_reference_refresh', 'captured_live', 'captured_held_live'),
            ('captured_average', 'B1W1', 'captured_average'),
            ('ordinary_average', 'ordinary_fixed', 'ordinary_average'),
            ('held_body_equality', 'held_B1W1', 'snapshot_only'),
            ('held_no_body_equality', 'held_B0W1', 'snapshot_only'),
            ('writer_off_equality', 'writer_off', 'incoming'),
        ):
            terms[name] = {left: 1., right: -1.}
        result.update({p+'__'+name: {p+'__'+arm: c for arm, c in row.items()} for name, row in terms.items()})
    assert len(result) == 54
    return result


def initial(built, spec):
    return boundary.initial(built, 'own', spec.packet)


def shuffled(snapshot, index, replicates):
    boundary.field(snapshot, replicates)
    if type(index) is not int or index < 0:
        raise ValueError('integer physical source index required')
    address = f'{TAG}:{index}:snapshot_shuffle'.encode()
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(address).digest()[:16], 'little'))
    permutations = np.asarray([rng.permutation(256) for _ in range(replicates)])
    out = np.stack([v.ravel()[permutations[i % replicates]].reshape(16, 16) for i, v in enumerate(snapshot)])
    return out, permutations


def _validate(ctx, state, index, spec):
    if not isinstance(spec, Spec) or type(index) is not int or index < 0:
        raise ValueError('declared spec and integer physical source index required')
    if set(ctx) != set(boundary.RUNTIME_KEYS) or set(ctx['api']) != {'blueprint_step', 'project_theta'}:
        raise ValueError('only whitelisted physical context may enter repair')
    if set(state) != set(boundary.STATE_KEYS):
        raise ValueError('only V, ema, R, theta may enter the boundary')
    cfg = ctx['config']
    for v in state.values(): boundary.field(v, cfg.replicates)
    if np.any(state['R'] != 0.) or np.any(state['ema'] != 0.):
        raise ValueError('only the zero-memory boundary may enter; capture is internal')
    if (type(cfg.sweeps) is not int or cfg.sweeps < 1 or not {0, 1, cfg.sweeps}.issubset(cfg.times)
            or tuple(sorted(set(cfg.times))) != cfg.times or max(cfg.times) != cfg.sweeps
            or min(cfg.times) != 0 or not 0 < cfg.lam < 1 or not 0 < ctx['bp'].rho < 1
            or not np.isfinite(cfg.norm) or cfg.norm <= 0 or not ctx['bp'].c_m > 0):
        raise ValueError('invalid schedule, strength or native reference configuration')


def repair(ctx, state, index, spec):
    _validate(ctx, state, index, spec)
    cfg = ctx['config']
    identity = source.base.state_digest(state)
    # These deliberately remain unmodified historical comparators.
    if spec.kind in ('ordinary_fixed', 'ordinary_live', 'captured_live', 'captured_held_live'):
        captured = spec.kind.startswith('captured')
        base = capture.old.Spec(spec.packet, 'own', reader='fixed' if spec.kind == 'ordinary_fixed' else 'live',
                                reference_write=spec.kind != 'captured_held_live')
        start = source.base.state_copy(state)
        if captured: start['R'] = start['V'].copy()
        result = capture.repair(ctx, start, index, capture.Spec(base, captured))
        result['metadata'].update(route_spec=asdict(spec), boundary_input_sha256=identity,
                                  native_bridge=True, body_free=False)
        assert source.base.state_digest(state) == identity
        return result

    tick = time.perf_counter()
    snapshot = state['V'].copy()
    permutations = None
    if spec.kind == 'scrambled': snapshot, permutations = shuffled(snapshot, index, cfg.replicates)
    snapshot_identity = hashlib.sha256(snapshot.tobytes()).hexdigest()
    body_free = spec.kind == 'snapshot_only'
    held = spec.kind in ('held', 'snapshot_only')
    rho = 0. if held else ctx['bp'].rho
    bp = replace(ctx['bp'], rho=rho)
    theta = state['theta'].copy()
    current = source.base.state_copy(state)
    current['R'] = snapshot.copy()
    a = 1.
    rng = None if body_free else boundary.RepairRNG(index, cfg.replicates)
    use_average = spec.kind == 'gated' and spec.body_access and spec.writer_access and spec.write
    total, averaged = state['V'].copy(), state['theta'].copy()
    observation_only = np.zeros_like(snapshot)  # Verification recurrence only, never read by physics.
    decomp_max = 0.
    raw, input_digest = {}, hashlib.sha256()
    body_input = snapshot.copy() if spec.body_access else np.zeros_like(snapshot)
    writer_input = snapshot.copy() if spec.writer_access else np.zeros_like(snapshot)

    def checkpoint(t):
        if body_free:
            raw[f's{t}_theta'] = theta.copy()
            raw[f's{t}_S'] = snapshot.copy()
            raw[f's{t}_writer_input'] = snapshot.copy()
        else:
            raw.update({f's{t}_{k}': v.copy() for k, v in current.items()})
            raw.update({f's{t}_S': snapshot.copy(), f's{t}_U': current['R']-a*snapshot,
                f's{t}_a': np.asarray(a, dtype=np.float64), f's{t}_body_input': body_input.copy(),
                f's{t}_writer_input': writer_input.copy()})
        if use_average:
            raw.update({f'a{t}_mean': total.copy()/(t+1), f'a{t}_theta': averaged.copy()})

    checkpoint(0)
    for t in range(1, cfg.sweeps+1):
        if body_free:
            theta = ctx['api']['project_theta']((1-cfg.lam)*theta+cfg.lam*np.tanh(snapshot), cfg.norm)
            input_digest.update(snapshot.tobytes())
        else:
            previous = current['R']
            body_input = previous if spec.body_access else previous-a*snapshot
            call_bp = bp if spec.body_access else replace(bp, rho=0.)
            v, ema, reference = ctx['api']['blueprint_step'](current['V'], current['ema'], body_input,
                state['theta'], ctx['tissue'], ctx['ladder'], call_bp, 'T', rng)
            if not spec.body_access: reference = previous+rho*(v-previous)
            a = (1-rho)*a
            observation_only = (1-rho)*observation_only+rho*v
            u = reference-a*snapshot
            decomp_max = max(decomp_max, float(np.max(np.abs(u-observation_only))))
            if decomp_max > 2e-12: raise AssertionError('snapshot decomposition exceeded frozen numerical tolerance')
            writer_input = reference if spec.writer_access else u
            theta = ctx['api']['project_theta']((1-cfg.lam)*current['theta']+cfg.lam*np.tanh(writer_input), cfg.norm) if spec.write else current['theta'].copy()
            current = dict(V=v, ema=ema, R=reference, theta=theta)
            input_digest.update(body_input.tobytes()); input_digest.update(writer_input.tobytes())
            if use_average:
                total += v
                averaged = ctx['api']['project_theta']((1-cfg.lam)*averaged+cfg.lam*np.tanh(total/(t+1)), cfg.norm)
            if not all(np.isfinite(v).all() for v in current.values()):
                raise FloatingPointError('nonfinite route state')
        if not np.isfinite(theta).all(): raise FloatingPointError('nonfinite route packet')
        if t in cfg.times: checkpoint(t)
    assert source.base.state_digest(state) == identity
    assert hashlib.sha256(snapshot.tobytes()).hexdigest() == snapshot_identity
    if permutations is not None: raw['snapshot_permutations'] = permutations
    return dict(raw=raw, outgoing=boundary.encode(theta, cfg.replicates),
        average=boundary.encode(averaged, cfg.replicates) if use_average else None,
        metadata=dict(route_spec=asdict(spec), boundary_input_sha256=identity, native_bridge=False,
            body_free=body_free, body_theta_fixed=True, snapshot_sha256=snapshot_identity,
            rng_final=None if body_free else rng.digest(), inputs_sha256=input_digest.hexdigest(),
            snapshot_bytes_per_record=2048, carrier_bytes_per_record=2048,
            body_sweeps=0 if body_free else cfg.sweeps, writer_sweeps=cfg.sweeps if spec.write else 0,
            snapshot_observations_per_record=1, decomposition_max_abs=decomp_max,
            average_observations_per_record=cfg.sweeps+1 if use_average else 0,
            seconds=time.perf_counter()-tick))
