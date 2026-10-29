"""D186: one-time R0=V0 capture, otherwise the immutable D184 equations."""

from dataclasses import asdict, dataclass
import time

import numpy as np

from . import l22_active_form_pilot as old

CONFIG, READOUT, BLOCKS = old.CONFIG, old.READOUT, old.BLOCKS
DISPOSABLE = 603186
boundary, source = old.boundary, old.source


@dataclass(frozen=True)
class Spec:
    base: old.Spec
    capture: bool = False

    def __post_init__(self):
        if not isinstance(self.base, old.Spec) or type(self.capture) is not bool:
            raise ValueError('declared base condition and boolean capture required')
        if self.capture and self.base.reset != 'zero':
            raise ValueError('native comparisons remain unchanged')


def plan():
    result = {name: Spec(s) for name, s in old.plan().items()}
    for name, s in old.plan().items():
        if s.reset == 'zero':
            key = 'capture__'+name.replace('reference_off', 'reference_held')
            result[key] = Spec(s, True)
    return result


def initial(built, original, spec):
    state = old.initial(built, original, spec.base)
    if spec.capture: state['R'] = state['V'].copy()
    return state


def repair(ctx, state, index, spec):
    if not spec.capture:
        result = old.repair(ctx, state, index, spec.base)
    else:
        if set(ctx) != set(boundary.RUNTIME_KEYS) or set(ctx['api']) != {'blueprint_step', 'project_theta'}:
            raise ValueError('only physical context may enter capture repair')
        if set(state) != set(boundary.STATE_KEYS): raise ValueError('only V, ema, R, theta allowed')
        cfg, s = ctx['config'], spec.base
        for v in state.values(): boundary.field(v, cfg.replicates)
        if state['R'].tobytes() != state['V'].tobytes() or np.any(state['ema'] != 0.):
            raise ValueError('capture must be exactly this body and ema must be zero')
        if not 0 < cfg.lam < 1 or not {0, 1, cfg.sweeps}.issubset(cfg.times):
            raise ValueError('invalid schedule')
        identity = source.base.state_digest(state)
        current = source.base.state_copy(state)
        local = ctx | {'native': state['theta'].copy()}
        mode = source.Mode(reference='zero', write=s.write, hold=not s.reference_write,
                           theta_read=s.reader == 'live')
        rng = boundary.RepairRNG(index, cfg.replicates)
        use_average = s.reader == 'fixed' and s.write
        total, averaged = state['V'].copy(), state['theta'].copy()
        raw, body_seconds, average_seconds = {}, 0., 0.

        def snapshot(t):
            raw.update({f's{t}_{k}': v.copy() for k, v in current.items()})
            if use_average:
                raw.update({f'a{t}_mean': total.copy()/(t+1), f'a{t}_theta': averaged.copy()})

        snapshot(0)
        for t in range(1, cfg.sweeps+1):
            tick = time.perf_counter()
            current = source.step(local, current, rng, mode)
            body_seconds += time.perf_counter()-tick
            if use_average:
                tick = time.perf_counter()
                total += current['V']
                averaged = ctx['api']['project_theta'](
                    (1-cfg.lam)*averaged+cfg.lam*np.tanh(total/(t+1)), cfg.norm)
                average_seconds += time.perf_counter()-tick
            if not all(np.isfinite(v).all() for v in current.values()): raise FloatingPointError('nonfinite state')
            if not s.write and current['theta'].tobytes() != state['theta'].tobytes():
                raise AssertionError('disabled writer changed input')
            if t in cfg.times: snapshot(t)
        assert source.base.state_digest(state) == identity
        result = dict(raw=raw, outgoing=boundary.encode(current['theta'], cfg.replicates),
            average=boundary.encode(averaged, cfg.replicates) if use_average else None,
            metadata=dict(input_sha256=identity, rng_final=rng.digest(),
                body_and_native_writer_seconds=body_seconds, averaging_writer_seconds=average_seconds,
                observations_per_record=cfg.sweeps+1 if use_average else 0,
                carrier_bytes_per_record=2048, conventional_extra_fields=2 if use_average else 0))
    result['metadata'].update(spec=asdict(spec), birth_capture_observations=int(spec.capture),
        body_observations_available_per_record=ctx['config'].sweeps+int(spec.capture),
        reference_held=not spec.base.reference_write)
    return result


def pairs():
    terms = {}
    for p in boundary.PACKETS:
        root = f'capture__{p}__'
        own = root+'own__live'
        for label, right in (('capture_gain', f'{p}__own__live'), ('source', root+'partner__live'),
                            ('gain', 'input__'+p), ('organization', root+'own_scrambled__live'),
                            ('erasure', root+'history_erased__live'), ('feedback', root+'own__fixed'),
                            ('versus_average', root+'own__average'), ('reference_refresh', root+'own__reference_held'),
                            ('writer', root+'own__writer_off')):
            terms[root+label] = (own, right)
        terms[root+'fixed_vs_average'] = (root+'own__fixed', root+'own__average')
        terms[root+'average_gain'] = (root+'own__average', 'input__'+p)
        terms[root+'average_source'] = (root+'own__average', root+'partner__average')
    return terms


def comparisons(records):
    result = old.comparisons(records)
    fields = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap', 'theta_corr_parent')
    for name, (left, right) in pairs().items():
        rows = [{k: a[k]-b[k] for k in fields} | {'message': a['message']}
                for a, b in zip(records[left], records[right])]
        result[name] = dict(left=left, right=right,
            mean={k:float(np.mean([r[k] for r in rows])) for k in fields},
            messages=[{k:float(np.mean([r[k] for r in rows if r['message'] == m])) for k in fields}
                      for m in range(4)])
    return result
