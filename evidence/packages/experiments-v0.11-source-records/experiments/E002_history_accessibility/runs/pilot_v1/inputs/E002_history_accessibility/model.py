"""Exact finite-state maps with activity-written partial additive records."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import rng
import numpy as np

TAG = "forms-e002-accessibility-v1"


def states(genes=10):
    return (((np.arange(1 << genes)[:,None] >> np.arange(genes)) & 1)*2-1).astype(np.int8)


def encode(x):
    return ((x > 0)*(1 << np.arange(x.shape[-1]))).sum(axis=-1).astype(np.uint16)


def successors(weights, record=None, gain=0.):
    genes = len(weights)
    x = states(genes)
    record = np.zeros(genes) if record is None else np.asarray(record)
    if record.shape != (genes,) or not np.isfinite(record).all():
        raise ValueError("One finite fixed record value per gene required")
    for j in range(genes):
        field = x @ weights[j] + gain*record[j]
        x[field > 0,j] = 1
        x[field < 0,j] = -1
    return encode(x)


def graph(successor):
    """Resolve every functional-graph component without a trajectory cutoff."""
    successor = np.asarray(successor)
    n = len(successor)
    if successor.shape != (n,) or np.any(successor < 0) or np.any(successor >= n):
        raise ValueError("Invalid finite successor function")
    labels = np.full(n,-1,dtype=np.int32)
    distance = np.zeros(n,dtype=np.uint16)
    cycles = []
    for start in range(n):
        if labels[start] >= 0:
            continue
        path, seen, current = [], {}, start
        while labels[current] < 0 and current not in seen:
            seen[current] = len(path)
            path.append(current)
            current = int(successor[current])
        if current in seen:
            split = seen[current]
            orbit = path[split:]
            offset = orbit.index(min(orbit))
            orbit = tuple(orbit[offset:]+orbit[:offset])
            label = len(cycles)
            cycles.append(orbit)
            for x in path[split:]:
                labels[x] = label
            prefix = path[:split]
            d = 0
        else:
            label, d, prefix = int(labels[current]), int(distance[current]), path
        for x in reversed(prefix):
            d += 1
            labels[x], distance[x] = label, d
    order = sorted(range(len(cycles)), key=lambda i: cycles[i])
    inverse = np.empty(len(order),dtype=int)
    inverse[order] = np.arange(len(order))
    labels = inverse[labels].astype(np.uint16)
    cycles = [cycles[i] for i in order]
    counts = np.bincount(labels, minlength=len(cycles))
    return dict(successor=successor, labels=labels, distance=distance, cycles=cycles, counts=counts)


def access(mapped, target, horizon=16):
    try:
        label = mapped["cycles"].index(target)
    except ValueError:
        return 0., 0.
    same = mapped["labels"] == label
    return float((same & (mapped["distance"] <= horizon)).mean()), float(same.mean())


def compare(native, mapped):
    n = len(native["successor"])
    base = dict(zip(native["cycles"], native["counts"]/n))
    changed = dict(zip(mapped["cycles"], mapped["counts"]/n))
    union = set(base)|set(changed)
    tv = .5*sum(abs(base.get(key,0.)-changed.get(key,0.)) for key in union)
    edge_fraction = float((native["successor"] != mapped["successor"]).mean())
    if edge_fraction == 0:
        category = "unchanged_transition_map"
    elif set(base) != set(changed):
        category = "changed_destinations"
    elif tv > 0:
        category = "same_destinations_changed_basin_masses"
    else:
        category = "same_destinations_same_basin_masses"
    return dict(category=category, basin_total_variation=float(tv), changed_edge_fraction=edge_fraction,
                new_destinations=len(set(changed)-set(base)), lost_destinations=len(set(base)-set(changed)))


def simulate(rulebook):
    weights = rng(TAG,rulebook,"weights").normal(size=(10,10))
    weights /= np.linalg.norm(weights,axis=1,keepdims=True)
    native = graph(successors(weights))
    birth = rng(TAG,rulebook,"founder_birth").integers(0,1024,4,dtype=np.uint16)
    current = birth.copy()
    history = []
    for _ in range(64):
        current = native["successor"][current]
        history.append(current.copy())
    history = np.stack(history)
    records = states()[history[-16:]].mean(axis=0)
    order = rng(TAG,rulebook,"public_mask").permutation(10)
    maps = [native]
    entries = [dict(arm="neutral", founder=None, k=0, gain=0., record=[0.]*10)]
    raw = dict(weights=weights, founder_birth=birth, founder_history=history,
               activity_records=records, public_mask_order=order)
    for k in (2,5):
        addresses = order[:k]
        permutation = rng(TAG,rulebook,k,"shuffle").permutation(k)
        raw[f"shuffle_{k}"] = permutation
        raw[f"payload_{k}"] = np.ascontiguousarray(records[:,addresses],dtype="<f8").view(np.uint8).reshape(4,8*k)
        for gain in (.25,.5):
            for founder in range(4):
                target = native["cycles"][native["labels"][birth[founder]]]
                baseline16, baseline = access(native,target)
                for arm in ("own","foreign","shuffled"):
                    values = records[founder,addresses]
                    if arm == "foreign":
                        values = records[(founder+1)%4,addresses]
                    elif arm == "shuffled":
                        values = values[permutation]
                    record = np.zeros(10)
                    record[addresses] = values
                    mapped = graph(successors(weights,record,gain))
                    p16, eventual = access(mapped,target)
                    maps.append(mapped)
                    entries.append(dict(arm=arm,founder=founder,k=k,gain=gain,record=record.tolist(),
                        payload_bytes=8*k, founder_native_orbit=list(target), access16=p16, eventual_access=eventual,
                        native_access16=baseline16,native_eventual_access=baseline,
                        access16_change=p16-baseline16,eventual_access_change=eventual-baseline,
                        **compare(native,mapped)))
    raw.update(successors=np.stack([m["successor"] for m in maps]),
               attractor_assignment=np.stack([m["labels"] for m in maps]),
               distance_to_cycle=np.stack([m["distance"] for m in maps]))
    meta = dict(rulebook=rulebook,entries=entries,cycles=[[list(c) for c in m["cycles"]] for m in maps],
                basin_counts=[m["counts"].tolist() for m in maps],
                unique_founder_destinations=len(set(int(native["labels"][s]) for s in birth)),
                native_fixed_points=sum(len(c)==1 for c in native["cycles"]),
                native_periodic_orbits=sum(len(c)>1 for c in native["cycles"]))
    verify_graphs(raw,meta)
    return raw,meta


def verify_graphs(raw,meta):
    n = raw["successors"].shape[1]
    for i,(successor,labels,dist) in enumerate(zip(raw["successors"],raw["attractor_assignment"],raw["distance_to_cycle"])):
        assert sum(meta["basin_counts"][i]) == n
        np.testing.assert_array_equal(labels,labels[successor])
        np.testing.assert_array_equal(dist[dist>0],dist[successor[dist>0]]+1)
        cycle_nodes = []
        for cid,orbit in enumerate(meta["cycles"][i]):
            np.testing.assert_array_equal(successor[orbit], np.roll(orbit,-1))
            assert np.all(labels[orbit] == cid)
            cycle_nodes.extend(orbit)
        np.testing.assert_array_equal(np.sort(cycle_nodes),np.flatnonzero(dist==0))
        np.testing.assert_array_equal(np.bincount(labels,minlength=len(meta["cycles"][i])),meta["basin_counts"][i])
