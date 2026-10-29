"""D195 fixed recipient pulse; inherited D193 physical kernel and addresses."""
from dataclasses import asdict, dataclass, replace
import hashlib
import time
import numpy as np
from . import l22_yoked_reference as inherited

boundary, source, capture = inherited.boundary, inherited.source, inherited.capture
CONFIG, READOUT = inherited.CONFIG, inherited.READOUT
BLOCKS, DISPOSABLE, QUALIFICATION = inherited.BLOCKS, inherited.DISPOSABLE, inherited.QUALIFICATION
TAG, STREAMS = inherited.TAG, inherited.STREAMS
RepairRNG, Trace = inherited.RepairRNG, inherited.Trace
canonical, array_hash, physical_hash = inherited.canonical, inherited.array_hash, inherited.physical_hash
validate_trace, trace_header = inherited.validate_trace, inherited.trace_header
KINDS = ('LL', 'YL', 'LL_pulse', 'YL_pulse', 'writer_off', 'writer_off_pulse', 'trace_writer', 'snapshot_writer')
TRACE_KINDS = ('YL', 'YL_pulse', 'trace_writer')

@dataclass(frozen=True)
class Spec:
    packet: str
    kind: str = 'LL'
    def __post_init__(self):
        if self.packet not in boundary.PACKETS or self.kind not in KINDS:
            raise ValueError('fixed D195 family and path required')

def base_kind(kind): return kind.removesuffix('_pulse')
def initial(built, spec): return boundary.initial(built, 'own', spec.packet)
def pulse_contract(cfg, enabled):
    return dict(enabled=enabled, step=cfg.sweeps//2+1 if enabled else None,
                rows=[4,12], columns=[4,12], operation='sign_inversion_V_only', random_draws=0)
def plan(): return {p+'__'+k: Spec(p,k) for p in boundary.PACKETS for k in KINDS}

def comparisons():
    out={}
    for p in boundary.PACKETS:
        terms=dict(disturbance_interaction={'LL_pulse':1.,'YL_pulse':-1.,'LL':-1.,'YL':1.},
            contingent_body_undisturbed={'LL':1.,'YL':-1.},
            contingent_body_disturbed={'LL_pulse':1.,'YL_pulse':-1.},
            own_disturbance={'LL_pulse':1.,'LL':-1.},
            yoked_disturbance={'YL_pulse':1.,'YL':-1.})
        for k in ('LL','YL','LL_pulse','YL_pulse'):
            terms[k+'_vs_snapshot']={k:1.,'snapshot_writer':-1.}
        for name,a,b in (('writer_undisturbed','LL','writer_off'),
            ('writer_disturbed','LL_pulse','writer_off_pulse'),
            ('off_pulse_identity','writer_off_pulse','writer_off'),
            ('writer_off_identity','writer_off','incoming'),
            ('trace_vs_snapshot','trace_writer','snapshot_writer'),
            ('trace_vs_LL_structural','trace_writer','LL'),
            ('snapshot_gain','snapshot_writer','incoming')):
            terms[name]={a:1.,b:-1.}
        out.update({p+'__'+k:{p+'__'+a:w for a,w in v.items()} for k,v in terms.items()})
    return out

def repair(ctx, state, index, stream, spec, donor=None, *, capture_trace=False):
    if not isinstance(spec, Spec): raise ValueError("declared D195 specification required")
    inherited._validate(ctx, state, index, stream, inherited.Spec(spec.packet, base_kind(spec.kind)))
    if type(capture_trace) is not bool or capture_trace and spec.kind != 'LL':
        raise ValueError('only LL can generate a donor trace')
    uses_trace = spec.kind in TRACE_KINDS
    if uses_trace != (donor is not None):
        raise ValueError('a donor is required only for the declared trace paths')
    donor_stream = stream if spec.kind == 'self_replay' else STREAMS[1-STREAMS.index(stream)]
    donor_identity = validate_trace(ctx, state, index, spec.packet, donor_stream, donor) if uses_trace else None
    identity, physical = source.base.state_digest(state), physical_hash(ctx)
    cfg, bp, kind = ctx['config'], ctx['bp'], spec.kind
    tick = time.perf_counter()
    free = kind in ('trace_writer', 'snapshot_writer')
    body_yoked = kind in ('YL', 'YL_pulse')
    writer_yoked = kind == 'trace_writer'
    write = kind not in ('writer_off', 'writer_off_pulse')
    pulse = kind.endswith('_pulse'); event = cfg.sweeps//2+1
    snapshot = state['V'].copy()
    current = source.base.state_copy(state); current['R'] = snapshot.copy()
    theta = state['theta'].copy()
    rng = None if free else RepairRNG(index, stream, cfg.replicates)
    frames = np.empty((cfg.sweeps+1, *snapshot.shape), dtype=np.float64) if capture_trace else None
    if capture_trace: frames[0] = snapshot
    body_input, writer_input = snapshot.copy(), snapshot.copy()
    raw, inputs = {}, hashlib.sha256()

    def checkpoint(t):
        if free:
            raw[f's{t}_theta'] = theta.copy()
        else:
            raw.update({f's{t}_{k}': v.copy() for k, v in current.items()})
            raw[f's{t}_body_input'] = body_input.copy()
        raw[f's{t}_S'] = snapshot.copy()
        raw[f's{t}_writer_input'] = writer_input.copy()

    checkpoint(0)
    call_bp = replace(bp, rho=0.) if body_yoked else bp
    for t in range(1, cfg.sweeps+1):
        if pulse and t == event:
            raw.update({'pulse_before_'+k: v.copy() for k, v in current.items()})
            current['V'] = current['V'].copy()
            current['V'][:, 4:12, 4:12] *= -1.
            raw.update({'pulse_after_'+k: v.copy() for k, v in current.items()})
        if not free:
            previous = current['R']
            body_input = donor.frames[t-1] if body_yoked else previous
            v, ema, reference = ctx['api']['blueprint_step'](current['V'], current['ema'],
                body_input, state['theta'], ctx['tissue'], ctx['ladder'], call_bp, 'T', rng)
            if body_yoked: reference = previous+bp.rho*(v-previous)
            inputs.update(body_input.tobytes())
        writer_input = donor.frames[t] if writer_yoked else (snapshot if free else reference)
        if write:
            theta = ctx['api']['project_theta']((1-cfg.lam)*theta+cfg.lam*np.tanh(writer_input), cfg.norm)
        inputs.update(writer_input.tobytes())
        if not free:
            current = dict(V=v, ema=ema, R=reference, theta=theta)
            if not all(np.isfinite(value).all() for value in current.values()):
                raise FloatingPointError('nonfinite recipient state')
        if not np.isfinite(theta).all(): raise FloatingPointError('nonfinite outgoing packet')
        if pulse and t == event:
            raw.update({'pulse_step_'+k: v.copy() for k, v in current.items()})
        if capture_trace: frames[t] = reference
        if t in cfg.times: checkpoint(t)
    assert source.base.state_digest(state) == identity and physical_hash(ctx) == physical
    assert array_hash(snapshot) == array_hash(state['V'])
    if uses_trace:
        assert validate_trace(ctx, state, index, spec.packet, donor_stream, donor) == donor_identity
    trace = None
    if capture_trace:
        frames.setflags(write=False)
        trace = Trace(frames, trace_header(ctx, state, index, spec.packet, stream, frames, rng.digest()))
    return dict(raw=raw, outgoing=boundary.encode(theta, cfg.replicates), trace=trace,
        metadata=dict(pulse=pulse_contract(cfg, pulse), spec=asdict(spec), index=index, stream=stream, boundary_input_sha256=identity,
            physical_sha256=physical, snapshot_sha256=array_hash(snapshot), donor_sha256=donor_identity,
            donor_stream=donor_stream if uses_trace else None, body_free=free, body_theta_fixed=True,
            rng_final=None if free else rng.digest(), inputs_sha256=inputs.hexdigest(),
            body_sweeps=0 if free else cfg.sweeps, writer_sweeps=cfg.sweeps if write else 0,
            carrier_bytes_per_record=2048, snapshot_bytes_per_record=2048,
            trace_input_bytes_per_record=(cfg.sweeps+1)*2048 if uses_trace else 0,
            trace_output_bytes_per_record=(cfg.sweeps+1)*2048 if capture_trace else 0,
            capture_trace=capture_trace, seconds=time.perf_counter()-tick))
