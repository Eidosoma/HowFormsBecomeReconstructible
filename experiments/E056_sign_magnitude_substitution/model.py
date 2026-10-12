"""Record-only substitutions and fresh-reader assays; no targets enter either."""
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import rng
from E022_reader_compensation import model as reader
from E054_record_interventions.model import coupling, graph_batch, U, V
from E056_sign_magnitude_substitution.plan import ARMS
import numpy as np

base = reader.base
P = base.PORTS


def digest(x):
    return np.frombuffer(hashlib.sha256(np.asarray(x, dtype='<f8').tobytes(order='C')).digest(), dtype=np.uint8)


def anchored(w):
    """Input-anchored signed forest; cycles separately diagnose path ambiguity."""
    parent = np.arange(256); parity = np.zeros(256, bool)
    def find(i):
        bit = False
        while parent[i] != i:
            bit ^= bool(parity[i]); i = parent[i]
        return int(i), bit
    for e in np.flatnonzero(w.ravel()):
        a, sa = find(U[e]); b, sb = find(V[e])
        if a != b:
            parent[b] = a; parity[b] = sa ^ sb ^ bool(w.ravel()[e] < 0)
    roots = [find(i) for i in range(256)]; anchors = {}
    for i in np.flatnonzero(P[0]):
        root, bit = roots[i]; anchors.setdefault(root, bit)
    out = np.zeros(256, np.int8)
    for i, (root, bit) in enumerate(roots):
        if root in anchors: out[i] = -1 if bit ^ anchors[root] else 1
    return out.reshape(16, 16)


def anchored_batch(w):
    return np.stack([anchored(x) for x in w.reshape(-1, 2, 16, 16)]).reshape(*w.shape[:-3],16,16)


def intervene(packets):
    w = base.decode(packets)
    assert w.shape[2] == 2 and np.isfinite(w).all()
    c, p = w[:, :, 0], w[:, :, 1]
    assert np.array_equal(c != 0, p != 0), 'Pulse/sham support mismatch: retain failure, never subset'
    result = np.zeros((*w.shape[:2], len(ARMS), *w.shape[3:]))
    result[:, :, 0] = c; result[:, :, 1] = p
    result[:, :, 2] = np.where(p != 0, np.copysign(abs(p), c), 0.)
    result[:, :, 3] = np.where(c != 0, np.copysign(abs(c), p), 0.)
    d, k = coupling(result)
    return dict(packets=base.encode(result), denominator=d, coupling=k,
                graph=graph_batch(result), anchor=anchored_batch(result))


def assay(packets, block, cfg):
    """Only packet bytes and identical public reader conditions cross this boundary."""
    H, T, A, F, R = packets.shape[:5]; N = H*T*A
    w = base.decode(packets).reshape(N, F, R, 2, 16, 16)
    config = base.Config(recipients=R, dt=cfg['dt'], noise=cfg['noise'])
    masks = base.damage_masks(block, 'E056_fresh_reader', config)
    effective = w[:, :, :, None]*reader.surviving_edges(masks)[None]
    d, k = coupling(effective)
    stream = rng('E056', block, 'fresh_reader')
    birth = cfg['birth_sd']*base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (N, F, R, 2, 3, 16, 16)).copy()
    live = (~masks)[None, :, :, None]; cue = base.CUES.reshape(1,1,1,2,1,1)
    v *= live; v[..., P[0]] = cue
    trace = []; hashes = []
    for t in range(cfg['read_steps']):
        noise = base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None]
        v = reader.compensated_step(v, effective[:, :, :, None], d[:, :, :, None], noise,
                                   config, t >= cfg['settling_steps'])
        v *= live; v[..., P[0]] = cue; hashes.append(digest(v))
        if t >= cfg['read_steps']-cfg['observe_steps']:
            trace.append(np.stack([v[..., P[j]].mean(axis=-1) for j in (1,2)], axis=-1))
    trace = np.stack(trace)
    return dict(masks=masks, effective=effective, denominator=d, coupling=k, birth=birth,
        end=v, late_ports=trace, mean_ports=trace.mean(axis=0), state_hashes=np.stack(hashes),
        graph=graph_batch(effective), anchor=anchored_batch(effective))


def score(values, margin):
    target = base.RULES.reshape((1,)*(values.ndim-4)+(4,1,1))*base.CUES
    m = np.minimum(target*values[..., 0], -target*values[..., 1])
    transfer = ((values[..., 0,0]-values[..., 1,0])-(values[..., 0,1]-values[..., 1,1]))/4
    return dict(margin=m, minimum_margin=m.min(axis=-1), both=(m > margin).all(axis=-1),
        transfer=transfer, aligned_transfer=transfer*base.RULES.reshape((1,)*(transfer.ndim-2)+(4,1)))


def diagnostics(source, inter, fresh, cfg):
    w = base.decode(inter['packets']); H,T,A,F,R = w.shape[:5]
    ref = w[:, :, :1]; shared = (w != 0)&(ref != 0); axes=(-3,-2,-1)
    cases = dict(shared_support=shared.sum(axis=axes),
        sign_disagreements=(shared & (np.sign(w)!=np.sign(ref))).sum(axis=axes),
        support_gained=((w!=0)&(ref==0)).sum(axis=axes),
        support_lost=((w==0)&(ref!=0)).sum(axis=axes),
        coupling_l1=abs(inter['coupling']-inter['coupling'][:, :, :1]).sum(axis=axes)/256,
        denominator_l1=abs(inter['denominator']-inter['denominator'][:, :, :1]).sum(axis=(-2,-1))/256,
        graph=inter['graph'],
        port_alignment=np.stack([inter['anchor'][..., mask].mean(axis=-1) for mask in P],axis=-1),
        port_unreachable=np.stack([(inter['anchor'][..., mask]==0).sum(axis=-1) for mask in P],axis=-1))
    values = fresh['mean_ports'].reshape(H,T,A,F,R,2,3,2).transpose(0,1,2,6,3,4,5,7)
    cases.update({f'fresh_{key}':x for key,x in score(values,cfg['margin']).items()})
    K=fresh['coupling'].reshape(H,T,A,F,R,3,4,16,16)
    cases['postinjury_coupling_l1']=(abs(K-K[:,:,:1]).sum(axis=(-3,-2,-1))/256).transpose(0,1,2,5,3,4)
    c,p = base.decode(source['packets'])[:,:,0],base.decode(source['packets'])[:,:,1]
    support=c!=0
    checks=dict(
        sources_same_support=bool(np.array_equal(c!=0,p!=0)),
        sham_bytes_unchanged=bool(np.array_equal(inter['packets'][:,:,0],source['packets'][:,:,0])),
        pulse_bytes_unchanged=bool(np.array_equal(inter['packets'][:,:,1],source['packets'][:,:,1])),
        hybrid_support_unchanged=bool(np.array_equal(w[:,:,:4]!=0,np.broadcast_to(support[:,:,None],w[:,:,:4].shape))),
        sign_restoration_exact=bool(np.array_equal(np.sign(w[:,:,2]),np.sign(c))),
        magnitude_restoration_exact=bool(np.array_equal(abs(w[:,:,3]),abs(c))),
        pulse_magnitudes_preserved=bool(np.array_equal(abs(w[:,:,2]),abs(p))),
        pulse_signs_preserved=bool(np.array_equal(np.sign(w[:,:,3]),np.sign(p))),
        sign_swap_denominators_fixed=bool(np.array_equal(inter['denominator'][:,:,0],inter['denominator'][:,:,3]) and
                                           np.array_equal(inter['denominator'][:,:,1],inter['denominator'][:,:,2])),
        ports_protected=bool(not fresh['masks'][...,P.any(axis=0)].any()),
        erased_zero=bool(not w[:,:,4].any()))
    fields=fresh['end'].reshape(H,T,A,F,R,2,3,16,16)
    windows=fresh['late_ports'].reshape(cfg['observe_steps'],H,T,A,F,R,2,3,2)
    checks['erased_fields_common']=bool(np.array_equal(fields[:,:,4],np.broadcast_to(fields[0,0,4],fields[:,:,4].shape)))
    checks['erased_traces_common']=bool(np.array_equal(windows[:,:,:,4],np.broadcast_to(windows[:,0,0,4][:,None,None],windows[:,:,:,4].shape)))
    checks['pass']=all(checks.values())
    return cases,checks
