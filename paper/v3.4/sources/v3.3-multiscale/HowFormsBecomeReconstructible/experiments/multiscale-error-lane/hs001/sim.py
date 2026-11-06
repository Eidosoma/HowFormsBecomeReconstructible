"""HS001's lifecycle on E014's machinery, imported read-only and unchanged (E014_long_renewal.run, and through it
E006_compact_renewal.run and E001_unprescribed_capture's model and analyze; the E-series seeds of common.rng).

New here, and nothing else: `generation` (E006's generation line for line over a declared subset of arms: E001's read
and write noise has an arm axis of size 1 and every step acts on one 16 x 16 sheet, so the kept arms' arithmetic does
not depend on the others; checked bit for bit in Q3), the protected probes (the exact initial bytes of the own,
foreign, erased and background records, read once by the terminal-stream checkpoint reader, whose births and noise
are shared across horizons as in E014), the sixteen checkpoints to 256 rewrites, and the replicate concordance.
Nothing here writes a file; no E-series main(), worker or workflow is called.
"""
from __future__ import annotations

import sys

import numpy as np

from . import design as D

sys.dont_write_bytecode = True
if str(D.EXP) not in sys.path:
    sys.path.insert(0, str(D.EXP))
from E014_long_renewal import run as E14  # noqa: E402  (E006 and E001 through it, unchanged)

compact, tissue = E14.compact, E14.tissue
from common import rng  # noqa: E402  (the E-series seeds)

CFG = E14.CFG
ARMS = tissue.ARMS
score, own_scores = compact.score, compact.own_scores


def generation(packets, stream, number, factor, arms, cfg=CFG):
    """E006's generation over `arms` (names; copy and write_off keep their roles). Returns (outgoing packets, the
    lineage read's state (founders, recipients, arms, 3, 16, 16))."""
    state, _birth, _mask = tissue.read_packets(packets, stream, f"g{number}", factor=factor, arms=arms,
                                               disable_read=True, cfg=cfg)
    v, ema, ref = [state[:, :, :, i].copy() for i in range(3)]
    field = np.zeros_like(v)
    cp = arms.index("copy") if "copy" in arms else None
    if cp is not None:
        field[:, :, cp] = tissue.unpack(packets, factor)[:, :, cp]
    writing = np.array([a not in ("copy", "write_off") for a in arms])[None, None, :, None, None]
    random = rng(tissue.TAG, stream, f"g{number}", "write")
    for _ in range(cfg.write):
        noise = random.standard_normal((cfg.founders, cfg.recipients, 1, cfg.side, cfg.side))
        v, ema, ref, field = tissue.step(v, ema, ref, field, noise, gain=cfg.gain, writing=writing, cfg=cfg)
    out = tissue.pack(field, factor)
    if cp is not None:
        out[:, :, cp] = packets[:, :, cp]          # protected bytes, as E006
    return out, state


def source(block, cfg=CFG):
    """E014's worker's source: E001's heterogeneous formation and generic capture, unchanged."""
    src = tissue.formation(block, "heterogeneous", cfg)
    acquired, end, first = tissue.capture(src["founder_state"], block, cfg)
    src.update(acquired=acquired, capture_end=end, capture_first=first)
    return src


def initial(src, block, factor):
    """E006's initial packets for all ten arms (unchanged), then HS001's lineage panel and protected panel."""
    stream = block + 1000000
    full, perms = compact.initial(src, stream, factor)
    lin = full[:, :, [ARMS.index(a) for a in D.LINEAGE]].copy()
    prot = full[:, :, [ARMS.index(D.PROBE_SOURCE[p]) for p in D.PROBES]].copy()
    return full, lin, prot, stream


def read_state(packets, stream, factor, arms):
    """The fresh checkpoint reader (the 'terminal' stream; births and noise shared across horizons): the recipient's
    state (founders, recipients, arms, 3: v, ema, ref, 16, 16), native float64."""
    state, _b, _m = tissue.read_packets(packets, stream, "terminal", factor=factor, arms=arms, cfg=CFG)
    return state


def read(packets, stream, factor, arms):
    """The fresh checkpoint reader's v (the field E014's observer scores)."""
    return read_state(packets, stream, factor, arms)[:, :, :, 0]


def outcomes(v, proto):
    """E014's three observer outcomes on fields v (..., founders, recipients, arms, 16, 16), kept separate: qualified
    agreement Q and sign-only agreement S against every candidate prototype (target axis last), and the amplitude
    fraction (|v| > 0.2)."""
    return score(v, proto), score(v, proto, qualified=False), (np.abs(v) > 0.2).mean((-2, -1))


def concordance(fields):
    """fields (..., founders, recipients, arms, 16, 16) decoded records. Returns per founder (..., founders, arms):
    the sign agreement (b(x) = x > 0) between the founder's two recipient lineages, the mean sign agreement between
    the founder's lineages and every other founder's, and the same two as Pearson correlations over the 256 cells."""
    b = fields > 0
    f = fields.shape[-5]
    x = fields.reshape(*fields.shape[:-2], -1)
    x = x - x.mean(-1, keepdims=True)
    nx = np.sqrt((x ** 2).sum(-1))

    def agree(i, r, j, s):
        return (b[..., i, r, :, :, :] == b[..., j, s, :, :, :]).mean((-2, -1))

    def corr(i, r, j, s):
        den = nx[..., i, r, :] * nx[..., j, s, :]
        return np.where(den > 0, (x[..., i, r, :, :] * x[..., j, s, :, :]).sum(-1) / np.where(den > 0, den, 1.0), 0.0)

    same = np.stack([agree(i, 0, i, 1) for i in range(f)], -2)
    cross = np.stack([np.mean([agree(i, r, j, s) for j in range(f) if j != i for r in (0, 1) for s in (0, 1)], 0)
                      for i in range(f)], -2)
    csame = np.stack([corr(i, 0, i, 1) for i in range(f)], -2)
    ccross = np.stack([np.mean([corr(i, r, j, s) for j in range(f) if j != i for r in (0, 1) for s in (0, 1)], 0)
                       for i in range(f)], -2)
    return same, cross, csame, ccross


def lifecycle(src, block, factor, horizon=D.HORIZON, checkpoints=D.CHECKPOINTS, lineage=D.LINEAGE, export=False):
    """One block at one budget: the protected probes, then `horizon` renewals of the lineage arms with a fresh
    checkpoint read after each rewrite in `checkpoints`. Every score is E001's observer against all four founders'
    prototypes (target axis last); the sign-only and amplitude outcomes are kept beside it. With export, the
    recipients' full states (the checkpoint and protected reads) are returned too, for the identity export.
    Returns a dict of arrays."""
    full, lin, prot, stream = initial(src, block, factor)
    if tuple(lineage) != D.LINEAGE:
        lin = full[:, :, [ARMS.index(a) for a in lineage]].copy()
    proto = src["prototype"]
    probe_state = read_state(prot, stream, factor, D.PROBES)
    q, s, amp = outcomes(probe_state[None, :, :, :, 0], proto)
    out = {"probe_scores": q[0], "probe_sign_scores": s[0], "probe_amp": amp[0], "initial_lineage": lin.copy(),
           "initial_protected": prot, "checkpoints": np.array(checkpoints)}
    if export:
        out["probe_fields"] = probe_state
    g_scores, ck_packets, ck_scores, ck_sign, ck_amp, ck_fields = [], [], [], [], [], []
    packets = lin
    for g in range(1, horizon + 1):
        packets, state = generation(packets, stream, g, factor, tuple(lineage))
        g_scores.append(score(state[None, :, :, :, 0], proto)[0])
        if g in checkpoints:
            ck_packets.append(packets.copy())
            rs = read_state(packets, stream, factor, tuple(lineage))
            q, s, amp = outcomes(rs[None, :, :, :, 0], proto)
            ck_scores.append(q[0]); ck_sign.append(s[0]); ck_amp.append(amp[0])
            if export:
                ck_fields.append(rs)
    out["g_scores"] = np.stack(g_scores)
    out["ck_packets"] = np.stack(ck_packets)
    out["ck_scores"] = np.stack(ck_scores)
    out["ck_sign_scores"], out["ck_amp"] = np.stack(ck_sign), np.stack(ck_amp)
    if export:
        out["ck_fields"] = np.stack(ck_fields)
    out["final_packets"] = packets
    fields = tissue.unpack(out["ck_packets"], factor)
    out["field_sd"] = fields.std(axis=(-2, -1))
    out["conc_same"], out["conc_cross"], out["corr_same"], out["corr_cross"] = concordance(fields)
    return out


def bridge_e014(block, factor, horizon=16):
    """E014's own simulate (all ten arms, 16 generations, checkpoints 1, 3, 8, 16; pure, writes nothing) beside HS001's
    lifecycle on the same block: the largest differences of the kept arms' packets, lineage reads and checkpoint reads,
    and of the protected probes against E014's copy reads."""
    src = source(block)
    raw = E14.simulate(src, block, factor)
    mine = lifecycle(src, block, factor, horizon=horizon, checkpoints=tuple(c for c in D.CHECKPOINTS if c <= horizon))
    kept = [ARMS.index(a) for a in D.LINEAGE]
    proto = src["prototype"]
    e_g = score(raw["generation_read"][:, :, :, kept, 0], proto)
    e_ck = score(raw["checkpoint_read"][:, :, :, kept, 0], proto)
    my_ck = mine["ck_scores"][[list(mine["checkpoints"]).index(c) for c in E14.CHECKPOINTS]]
    pk = [list(mine["checkpoints"]).index(c) for c in E14.CHECKPOINTS]
    e_copy = score(raw["checkpoint_read"][:, :, :, [ARMS.index("copy")], 0], proto)[:, :, :, 0]
    return {"packets_equal": bool(np.array_equal(raw["checkpoint_packets"][:, :, :, kept], mine["ck_packets"][pk])),
            "outgoing_equal": bool(np.array_equal(raw["outgoing"][-1][:, :, kept], mine["final_packets"])),
            "g_scores_max_diff": float(np.abs(e_g - mine["g_scores"]).max()),
            "ck_scores_max_diff": float(np.abs(e_ck - my_ck).max()),
            "copy_probe_max_diff": float(np.abs(e_copy - mine["probe_scores"][None, :, :, 0]).max()),
            "src": src, "raw": raw, "mine": mine}
