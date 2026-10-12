"""D181 fresh-only four-future summaries; signed estimates, no fitting or selection."""
import itertools
import numpy as np
from . import recipient_repeats as model

BLOCKS = model.BLOCKS
ASSAYS = ("common", "native")
KEYS = ("index", "life", "family", "coupling", "replica", "condition", "assay")
CONTINUOUS = ("preference", "body_rms", "clip_fraction", "f0_own_correlation",
              "f0_own_minus_alternative", "f3_own_correlation", "f3_own_minus_alternative")
CONTRASTS = (("protected_copy","write_off"), ("ordinary","ordinary_read_off"),
             ("ordinary","write_off"), ("aligned","aligned_read_off"), ("aligned","write_off"))


def extract_records(raw, meta):
    index, life = meta["index"], meta["life"]
    assert index in BLOCKS + (model.DISPOSABLE,) and type(life) is int and life in range(4)
    assert meta["cells"] == [list(c) for c in model.CELLS] and len(meta["paths"]) == 144
    rows = []
    for i, (family, g, rep, kind) in enumerate(model.CELLS):
        for a, assay in enumerate(ASSAYS):
            terminal = meta["paths"][i]["terminal"][a]
            v = raw["terminal_values"][i,a,-1]
            f0, f3 = raw["record_features"][i]
            rows.append(dict(index=index, life=life, family=family, coupling=g, replica=rep,
                condition=kind, assay=assay, preference=float(v[0]-v[1]), body_rms=float(v[6]),
                clip_fraction=float(v[7]), f0_own_correlation=float(f0[0]),
                f0_own_minus_alternative=float(f0[1]), f3_own_correlation=float(f3[0]),
                f3_own_minus_alternative=float(f3[1]),
                guide_family=terminal["selector"]["inferred_family"],
                guide_shift=terminal["selector"]["chosen_forward_shift"].copy()))
    return rows


def indexed(records):
    expected = set(itertools.product(BLOCKS, range(4), (0,1), model.COUPLINGS,
                                     model.REPLICAS, model.CONDITIONS, ASSAYS))
    result = {}
    for row in records:
        assert set(row) == set(KEYS + CONTINUOUS + ("guide_family","guide_shift"))
        key = tuple(row[k] for k in KEYS)
        assert key in expected and key not in result
        assert all(np.isfinite(row[k]) for k in CONTINUOUS)
        assert row["guide_family"] in (-1,0,1)
        assert len(row["guide_shift"]) == 2 and all(type(v) is int and 0 <= v < 16 for v in row["guide_shift"])
        assert -1 <= row["preference"] <= 1 and 0 <= row["clip_fraction"] <= 1
        result[key] = row
    assert set(result) == expected and len(result) == 4608
    return result


def describe(y, replicas=model.REPLICAS):
    y = np.asarray(y, dtype=np.float64)
    assert y.ndim == 3 and y.shape[1:] == (3,len(replicas))
    assert len(replicas) in (3,4) and len(set(replicas)) == len(replicas)
    assert set(replicas) <= set(model.REPLICAS) and np.isfinite(y).all()
    mean = y.mean(axis=(0,1),keepdims=True)
    record = y.mean(axis=1,keepdims=True)-mean
    recipient = y.mean(axis=0,keepdims=True)-mean
    fields = (record,recipient,y-mean-record-recipient,y-mean)
    names = ("record","recipient","interaction","total")
    pairs = [dict(first=replicas[i],second=replicas[j],components={
        key:float(np.mean(v[...,i]*v[...,j])) for key,v in zip(names,fields)})
        for i,j in itertools.combinations(range(len(replicas)),2)]
    cross = {key:float(np.mean([p["components"][key] for p in pairs])) for key in names}
    assert np.isclose(cross["total"],sum(cross[k] for k in names[:3]),rtol=0,atol=1e-12)
    powers = [{key:float(np.mean(v[...,i]**2)) for key,v in zip(names,fields)}
              for i in range(len(replicas))]
    return dict(records=len(y),replicas=list(replicas),mean=float(y.mean()),
        replica_means=y.mean(axis=(0,1)).tolist(),coupling_means=y.mean(axis=(0,2)).tolist(),
        cross_replica=cross,pair_components=pairs,replica_partitions=powers)


def ordering(y, a, b):
    mean = y.mean(axis=2)
    def ranks(v):
        _,inv,counts = np.unique(v,return_inverse=True,return_counts=True)
        return (np.cumsum(counts)-(counts+1)/2)[inv]
    ra,rb = ranks(mean[:,a]),ranks(mean[:,b])
    denom = float(np.sqrt(np.sum((ra-ra.mean())**2)*np.sum((rb-rb.mean())**2)))
    result = dict(spearman=None if denom==0 else float(np.sum((ra-ra.mean())*(rb-rb.mean()))/denom),
        reversed=0,unchanged=0,tied=0,replication_consistent_reversals=0)
    for i,j in itertools.combinations(range(len(y)),2):
        left,right = mean[i,a]-mean[j,a],mean[i,b]-mean[j,b]
        key = "tied" if not left or not right else "reversed" if left*right<0 else "unchanged"
        result[key] += 1
        ls,rs = np.sign(y[i,a]-y[j,a]),np.sign(y[i,b]-y[j,b])
        if np.all(ls==ls[0]) and np.all(rs==rs[0]) and ls[0]*rs[0]<0:
            result["replication_consistent_reversals"] += 1
    return result


def summarize(records):
    table = indexed(records)
    groups = []
    for assay, family, kind in itertools.product(ASSAYS, (0,1), ("ordinary","aligned")):
        y = np.asarray([[[table[index,life,family,g,rep,kind,assay]["preference"]
                          for rep in model.REPLICAS] for g in model.COUPLINGS]
                        for index in BLOCKS for life in range(4)], dtype=np.float64)
        groups.append(dict(assay=assay, family=family, condition=kind,
            focal=(assay,family,kind)==("common",1,"ordinary"), **describe(y),
            rankings=[dict(first=model.COUPLINGS[a], second=model.COUPLINGS[b], **ordering(y,a,b))
                      for a,b in ((0,1),(0,2),(1,2))],
            paired_rankings=[dict(replicas=list(pair),comparisons=[dict(first=model.COUPLINGS[a],
                second=model.COUPLINGS[b],**ordering(y[:,:,[model.REPLICAS.index(x) for x in pair]],a,b))
                for a,b in ((0,1),(0,2),(1,2))]) for pair in ((2,3),(4,5))],
            leave_one_future_out=[dict(omitted=rep,**describe(np.delete(y,i,axis=2),
                tuple(x for x in model.REPLICAS if x!=rep))) for i,rep in enumerate(model.REPLICAS)],
            donor_blocks=[dict(index=index, **describe(y[i*4:(i+1)*4])) for i,index in enumerate(BLOCKS)],
            leave_one_block_out=[dict(omitted=index, **describe(np.delete(y,slice(i*4,(i+1)*4),axis=0)))
                                 for i,index in enumerate(BLOCKS)]))
    controls = []
    means = {}
    for index,family,g,rep,assay,kind in itertools.product(BLOCKS,(0,1),model.COUPLINGS,model.REPLICAS,ASSAYS,model.CONDITIONS):
        sample = [table[index,life,family,g,rep,kind,assay] for life in range(4)]
        row = dict(index=index,family=family,coupling=g,replica=rep,assay=assay,condition=kind,lives=4,
                   **{k:float(np.mean([s[k] for s in sample])) for k in CONTINUOUS},
                   guide_family_retention=float(np.mean([s["guide_family"]==family for s in sample])))
        controls.append(row)
        means[index,family,g,rep,assay,kind] = row["preference"]
    contrasts = []
    for index,family,g,rep,assay in itertools.product(BLOCKS,(0,1),model.COUPLINGS,model.REPLICAS,ASSAYS):
        for a,b in CONTRASTS:
            contrasts.append(dict(index=index,family=family,coupling=g,replica=rep,assay=assay,
                first=a,second=b,first_minus_second=means[index,family,g,rep,assay,a]-means[index,family,g,rep,assay,b]))
    return dict(schema="d181_fresh_repeat_summary_v1", replicas=list(model.REPLICAS),
                fixed_pairs=[[2,3],[4,5]],old_futures_pooled=False, blocks=list(BLOCKS), lives_per_block=4,
                source_records=32, labelled_lineages=2304, primary_lineages=768, control_lineages=1536,
                assay_rows=4608, coupling=list(model.COUPLINGS), groups=groups, control_cells=controls,
                control_contrasts=contrasts, negative_components_clipped=False,
                uncertainty_intervals=False, percentage_decomposition=False, prospective_evidence=False,
                fitted_predictors=0, exclusions=0, population_generalization=False,
                automatic_successor=False)
