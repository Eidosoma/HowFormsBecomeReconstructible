"""D180 fixed descriptive summaries; no model fitting, tests of significance or selection."""
import itertools
import numpy as np
from . import recipient_coupling_pilot as model
from . import recipient_coupling_run as benchmark

BLOCKS = model.BLOCKS
ASSAYS = ("common", "native")
KEYS = ("index", "life", "family", "coupling", "replica", "condition", "assay")
CONTINUOUS = ("preference", "body_rms", "clip_fraction", "f0_own_correlation",
              "f0_own_minus_alternative", "f3_own_correlation", "f3_own_minus_alternative")
CONTRASTS = (("protected_copy","write_off"), ("ordinary","ordinary_read_off"),
             ("ordinary","write_off"), ("aligned","aligned_read_off"), ("aligned","write_off"))
design = benchmark.design_module()


def extract_records(raw, meta):
    index, life = meta["index"], meta["life"]
    assert index in BLOCKS + (model.DISPOSABLE,) and type(life) is int and life in range(4)
    assert meta["cells"] == [list(c) for c in model.CELLS] and len(meta["paths"]) == 72
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
                                     (0,1), model.CONDITIONS, ASSAYS))
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
    assert set(result) == expected and len(result) == 2304
    return result


def describe(y):
    components = design.cross_components(y)
    assert np.isclose(components["total"], sum(components[k] for k in ("record","recipient","interaction")),
                      rtol=0, atol=1e-12)
    fields = design.component_fields(y)
    powers = [dict(zip(("record","recipient","interaction","total"),
                       [float(np.mean(v[...,r]**2)) for v in fields])) for r in (0,1)]
    return dict(records=len(y), mean=float(y.mean()), replica_means=y.mean(axis=(0,1)).tolist(),
                coupling_means=y.mean(axis=(0,2)).tolist(), cross_replica=components,
                replica_partitions=powers)


def summarize(records):
    table = indexed(records)
    groups = []
    for assay, family, kind in itertools.product(ASSAYS, (0,1), ("ordinary","aligned")):
        y = np.asarray([[[table[index,life,family,g,rep,kind,assay]["preference"]
                          for rep in (0,1)] for g in model.COUPLINGS]
                        for index in BLOCKS for life in range(4)], dtype=np.float64)
        groups.append(dict(assay=assay, family=family, condition=kind,
            focal=(assay,family,kind)==("common",1,"ordinary"), **describe(y),
            rankings=[dict(first=model.COUPLINGS[a], second=model.COUPLINGS[b], **design.ordering(y,a,b))
                      for a,b in ((0,1),(0,2),(1,2))],
            donor_blocks=[dict(index=index, **describe(y[i*4:(i+1)*4])) for i,index in enumerate(BLOCKS)],
            leave_one_block_out=[dict(omitted=index, **describe(np.delete(y,slice(i*4,(i+1)*4),axis=0)))
                                 for i,index in enumerate(BLOCKS)]))
    controls = []
    means = {}
    for index,family,g,rep,assay,kind in itertools.product(BLOCKS,(0,1),model.COUPLINGS,(0,1),ASSAYS,model.CONDITIONS):
        sample = [table[index,life,family,g,rep,kind,assay] for life in range(4)]
        row = dict(index=index,family=family,coupling=g,replica=rep,assay=assay,condition=kind,lives=4,
                   **{k:float(np.mean([s[k] for s in sample])) for k in CONTINUOUS},
                   guide_family_retention=float(np.mean([s["guide_family"]==family for s in sample])))
        controls.append(row)
        means[index,family,g,rep,assay,kind] = row["preference"]
    contrasts = []
    for index,family,g,rep,assay in itertools.product(BLOCKS,(0,1),model.COUPLINGS,(0,1),ASSAYS):
        for a,b in CONTRASTS:
            contrasts.append(dict(index=index,family=family,coupling=g,replica=rep,assay=assay,
                first=a,second=b,first_minus_second=means[index,family,g,rep,assay,a]-means[index,family,g,rep,assay,b]))
    return dict(schema="d180_descriptive_summary_v1", blocks=list(BLOCKS), lives_per_block=4,
                source_records=32, labelled_lineages=1152, primary_lineages=384, control_lineages=768,
                assay_rows=2304, coupling=list(model.COUPLINGS), groups=groups, control_cells=controls,
                control_contrasts=contrasts, negative_components_clipped=False,
                uncertainty_intervals=False, percentage_decomposition=False, prospective_evidence=False,
                fitted_predictors=0, exclusions=0, population_generalization=False,
                automatic_successor=False)
