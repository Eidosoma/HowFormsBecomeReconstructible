"""Recipient-only repair API, with no historical record or injury inputs."""
import numpy as np
from optimizer import complete


def edge_signs(nodes):
    return np.stack((nodes*np.roll(nodes,-1,-1),nodes*np.roll(nodes,-1,-2)))


def imputed_magnitude(outgoing):
    seen=np.abs(outgoing[outgoing!=0])
    return float(np.median(seen)) if seen.size else 0.


def recipient_repair(outgoing,options):
    assert outgoing.shape==(2,16,16) and np.isfinite(outgoing).all()
    solution=complete(outgoing,options)
    magnitude=imputed_magnitude(outgoing)
    result=outgoing.copy();missing=outgoing==0
    # Leave the canonical erased record untouched when no magnitude is observed.
    if magnitude>0:result[missing]=magnitude*edge_signs(solution['signs'])[missing]
    return result,solution,magnitude


def reference_records(outgoing,incoming,common,original_unavailable,solution,magnitude,recipient,random):
    signs=edge_signs(solution['signs'])
    full=original_unavailable&(incoming!=0)
    assert not outgoing[original_unavailable].any()
    assert np.all(~common|full)
    records=[incoming.copy(),outgoing.copy()]
    for support,weights in ((common,abs(incoming)*signs),(full,incoming),
                            (full,abs(incoming)*signs),(full,magnitude*signs)):
        result=outgoing.copy();result[support]=weights[support];records.append(result)
    records.append(recipient.copy())
    missing=outgoing==0;shuffled=outgoing.copy()
    permutation=random.permutation(int(missing.sum()))
    if magnitude>0:shuffled[missing]=magnitude*signs[missing][permutation]
    records.extend((shuffled,np.zeros_like(outgoing)))
    return np.stack(records),full,permutation
