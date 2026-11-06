"""HS002's continuation, on HS001's frozen machinery (hs001.sim, imported unchanged; through it E014's).

`continue_lineages` renews each lineage's saved outgoing record after rewrite 256 for rewrites 257..1,024 with
hs001.sim.generation (whose randomness is keyed only by the stream and the generation number, so a continuation from
the saved packets equals an uninterrupted run: checked bit for bit in Q3), reads every new checkpoint with HS001's
fresh terminal-stream reader, and keeps HS001's outcomes (Q, S, amplitude), the lineage reads, the field SDs, the
replicate concordance and, for the export, the recipients' full states. Nothing here writes a file.
"""
from __future__ import annotations

import numpy as np

from hs001 import sim as S1

from . import design as D


def continue_lineages(packets, block, factor, proto, start=D.START, horizon=D.HORIZON, checkpoints=D.NEW_CHECKPOINTS,
                      export=False):
    """packets: (4, 2, 4, bytes) uint8, the lineage arms' outgoing records after rewrite `start`. Returns a dict."""
    stream = block + 1000000
    g_scores, ck_packets, ck_scores, ck_sign, ck_amp, ck_fields = [], [], [], [], [], []
    p = packets.copy()
    for g in range(start + 1, horizon + 1):
        p, state = S1.generation(p, stream, g, factor, D.LINEAGE)
        g_scores.append(S1.score(state[None, :, :, :, 0], proto)[0])
        if g in checkpoints:
            ck_packets.append(p.copy())
            rs = S1.read_state(p, stream, factor, D.LINEAGE)
            q, s, a = S1.outcomes(rs[None, :, :, :, 0], proto)
            ck_scores.append(q[0]); ck_sign.append(s[0]); ck_amp.append(a[0])
            if export:
                ck_fields.append(rs)
    out = {"g_scores": np.stack(g_scores), "ck_packets": np.stack(ck_packets), "ck_scores": np.stack(ck_scores),
           "ck_sign_scores": np.stack(ck_sign), "ck_amp": np.stack(ck_amp), "final_packets": p,
           "checkpoints": np.array(checkpoints)}
    if export:
        out["ck_fields"] = np.stack(ck_fields)
    fields = S1.tissue.unpack(out["ck_packets"], factor)
    out["field_sd"] = fields.std(axis=(-2, -1))
    out["conc_same"], out["conc_cross"], out["corr_same"], out["corr_cross"] = S1.concordance(fields)
    return out


def bridge_exact(block, factor, end=320):
    """The continuation bridge: an uninterrupted HS001 lifecycle to `end` against HS001's lifecycle to 256 plus the
    continuation from its outgoing packets, bit for bit (packets, lineage reads, checkpoint reads and states)."""
    src = S1.source(block)
    cks = tuple(D.CHECKPOINTS[:16]) + (end,)
    whole = S1.lifecycle(src, block, factor, horizon=end, checkpoints=cks, export=True)
    first = S1.lifecycle(src, block, factor, horizon=D.START, checkpoints=tuple(D.CHECKPOINTS[:16]), export=True)
    cont = continue_lineages(first["final_packets"], block, factor, src["prototype"], horizon=end, checkpoints=(end,), export=True)
    return {"packets": bool(np.array_equal(whole["final_packets"], cont["final_packets"])
                            and np.array_equal(whole["ck_packets"][-1], cont["ck_packets"][-1])),
            "lineage_reads": bool(np.array_equal(whole["g_scores"][D.START:], cont["g_scores"])),
            "checkpoint_reads": bool(np.array_equal(whole["ck_scores"][-1], cont["ck_scores"][-1])
                                     and np.array_equal(whole["ck_sign_scores"][-1], cont["ck_sign_scores"][-1])
                                     and np.array_equal(whole["ck_amp"][-1], cont["ck_amp"][-1])),
            "recipient_states": bool(np.array_equal(whole["ck_fields"][-1], cont["ck_fields"][-1])),
            "first_256_equal_hs001_run": bool(np.array_equal(whole["g_scores"][:D.START], first["g_scores"])),
            "end": end}
