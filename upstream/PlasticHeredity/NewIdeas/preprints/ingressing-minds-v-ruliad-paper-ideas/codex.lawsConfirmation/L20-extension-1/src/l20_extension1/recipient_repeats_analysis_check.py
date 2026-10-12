"""Independent D181 row checks and matrix/closed-form four-future statistics."""
import itertools
import numpy as np
from . import recipient_repeats_check as replay

BLOCKS = (90000,90005,90010,90015)
ASSAYS = ("common","native")
FIELDS = ("preference","body_rms","clip_fraction","f0_own_correlation",
          "f0_own_minus_alternative","f3_own_correlation","f3_own_minus_alternative")
KEYS = ("index","life","family","coupling","replica","condition","assay")


def check_rows(rows, raw, meta):
    assert len(rows) == 288
    expected = []
    targets = replay.prior.prior.targets()
    for ci, (role,g,rep,kind) in enumerate(replay.CELLS):
        start = replay.features(raw["founder_packet"][ci].tobytes(),role,raw["guide"][ci])
        end = replay.features(raw["terminal_input"][ci].tobytes(),role,raw["guide"][ci])
        for ai,name in enumerate(ASSAYS):
            v = raw["terminal_states"][ci,ai,-1,0]
            active = abs(v) > .2
            score = (np.count_nonzero(((v>0)==(targets[role]>0)) & active)
                     - np.count_nonzero(((v>0)==(targets[1-role]>0)) & active))/256
            selector = meta["paths"][ci]["terminal"][ai]["selector"]
            expected.append(dict(index=meta["index"],life=meta["life"],family=role,
                coupling=g,replica=rep,condition=kind,assay=name,preference=float(score),
                body_rms=float(np.sqrt(np.sum(v*v)/256)),clip_fraction=float(np.count_nonzero(abs(v)==2)/256),
                f0_own_correlation=float(start[0]),f0_own_minus_alternative=float(start[1]),
                f3_own_correlation=float(end[0]),f3_own_minus_alternative=float(end[1]),
                guide_family=selector["inferred_family"],guide_shift=selector["chosen_forward_shift"]))
    replay.prior.nested(rows,expected)
    return dict(passes=True,rows=288)


def description(y, replicas=(2,3,4,5)):
    n,k,nrep=y.shape
    assert nrep in (3,4) and k==3 and len(replicas)==nrep
    ji=np.ones((n,n))/n
    jh=np.ones((k,k))/k
    pi,ph=np.eye(n)-ji,np.eye(k)-jh
    matrices=[]
    for r in range(nrep):
        v=y[:,:,r]
        matrices.append((pi@v@jh,ji@v@ph,pi@v@ph,v-ji@v@jh))
    names=("record","recipient","interaction","total")
    # Closed-form off-diagonal sum, independently of the production pair average.
    cross={}
    for i,key in enumerate(names):
        total=sum(m[i] for m in matrices)
        square=sum(float(np.sum(m[i]**2)) for m in matrices)
        cross[key]=(float(np.sum(total**2))-square)/(n*k*nrep*(nrep-1))
    pairs=[dict(first=replicas[a],second=replicas[b],components={
        key:float(np.sum(matrices[a][i]*matrices[b][i])/(n*k)) for i,key in enumerate(names)})
        for a,b in itertools.combinations(range(nrep),2)]
    parts=[{key:float(np.sum(matrices[r][i]**2)/(n*k)) for i,key in enumerate(names)}
           for r in range(nrep)]
    return dict(records=n,replicas=list(replicas),mean=float(np.sum(y)/(n*k*nrep)),
        replica_means=[float(np.sum(y[:,:,r])/(n*k)) for r in range(nrep)],
        coupling_means=[float(np.sum(y[:,h,:])/(n*nrep)) for h in range(3)],
        cross_replica=cross,pair_components=pairs,replica_partitions=parts)


def ranking(y,a,b):
    values=np.sum(y,axis=2)/y.shape[2]
    def ranks(v):
        return np.array([sum(x < item for x in v)+(sum(x==item for x in v)-1)/2 for item in v],float)
    ra,rb=ranks(values[:,a]),ranks(values[:,b])
    ra-=ra.mean()
    rb-=rb.mean()
    divisor=np.sqrt(float(ra@ra)*float(rb@rb))
    corr=None if divisor==0 else float(ra@rb/divisor)
    result=dict(reversed=0,unchanged=0,tied=0,replication_consistent_reversals=0,spearman=corr)
    for i,j in itertools.combinations(range(len(y)),2):
        left=float(values[i,a]-values[j,a])
        right=float(values[i,b]-values[j,b])
        result["tied" if not left or not right else "reversed" if left*right<0 else "unchanged"]+=1
        la=[float(y[i,a,r]-y[j,a,r]) for r in range(y.shape[2])]
        rb_=[float(y[i,b,r]-y[j,b,r]) for r in range(y.shape[2])]
        if all(x*la[0]>0 for x in la) and all(x*rb_[0]>0 for x in rb_) and la[0]*rb_[0]<0:
            result["replication_consistent_reversals"]+=1
    return result


def check_report(report,records):
    expected_keys=set(itertools.product(BLOCKS,range(4),(0,1),replay.COUPLINGS,(2,3,4,5),replay.KINDS,ASSAYS))
    table={}
    for row in records:
        key=tuple(row[k] for k in KEYS)
        assert key in expected_keys and key not in table
        assert set(row)==set(KEYS+FIELDS+("guide_family","guide_shift"))
        assert all(np.isfinite(row[k]) for k in FIELDS)
        table[key]=row
    assert set(table)==expected_keys and len(records)==4608
    groups=[]
    for assay in ASSAYS:
        for family in (0,1):
            for kind in ("ordinary","aligned"):
                y=np.empty((16,3,4))
                for bi,index in enumerate(BLOCKS):
                    for life in range(4):
                        for hi,g in enumerate(replay.COUPLINGS):
                            for ri,rep in enumerate((2,3,4,5)):
                                y[bi*4+life,hi,ri]=table[index,life,family,g,rep,kind,assay]["preference"]
                group=dict(assay=assay,family=family,condition=kind,
                    focal=(assay=="common" and family==1 and kind=="ordinary"),**description(y),
                    rankings=[dict(first=replay.COUPLINGS[a],second=replay.COUPLINGS[b],**ranking(y,a,b))
                              for a,b in ((0,1),(0,2),(1,2))],
                    paired_rankings=[dict(replicas=list(pair),comparisons=[dict(first=replay.COUPLINGS[a],
                        second=replay.COUPLINGS[b],**ranking(y[:,:,[x-2 for x in pair]],a,b))
                        for a,b in ((0,1),(0,2),(1,2))]) for pair in ((2,3),(4,5))],
                    leave_one_future_out=[dict(omitted=rep,**description(y[:,:,[j for j in range(4) if j!=i]],
                        tuple(x for x in (2,3,4,5) if x!=rep))) for i,rep in enumerate((2,3,4,5))],
                    donor_blocks=[],leave_one_block_out=[])
                for bi,index in enumerate(BLOCKS):
                    chosen=[i for i in range(16) if i//4==bi]
                    other=[i for i in range(16) if i//4!=bi]
                    group["donor_blocks"].append(dict(index=index,**description(y[chosen])))
                    group["leave_one_block_out"].append(dict(omitted=index,**description(y[other])))
                groups.append(group)
    controls=[]
    contrasts=[]
    for index in BLOCKS:
        for family in (0,1):
            for g in replay.COUPLINGS:
                for rep in (2,3,4,5):
                    for assay in ASSAYS:
                        means={}
                        for kind in replay.KINDS:
                            sample=[table[index,life,family,g,rep,kind,assay] for life in range(4)]
                            mean={k:float(sum(row[k] for row in sample)/4) for k in FIELDS}
                            means[kind]=mean["preference"]
                            controls.append(dict(index=index,family=family,coupling=g,replica=rep,
                                assay=assay,condition=kind,lives=4,**mean,
                                guide_family_retention=sum(row["guide_family"]==family for row in sample)/4))
                        for a,b in (("protected_copy","write_off"),("ordinary","ordinary_read_off"),
                                    ("ordinary","write_off"),("aligned","aligned_read_off"),("aligned","write_off")):
                            contrasts.append(dict(index=index,family=family,coupling=g,replica=rep,
                                assay=assay,first=a,second=b,first_minus_second=means[a]-means[b]))
    expected=dict(schema="d181_fresh_repeat_summary_v1",replicas=[2,3,4,5],
        fixed_pairs=[[2,3],[4,5]],old_futures_pooled=False,blocks=list(BLOCKS),lives_per_block=4,
        source_records=32,labelled_lineages=2304,primary_lineages=768,control_lineages=1536,assay_rows=4608,
        coupling=list(replay.COUPLINGS),groups=groups,control_cells=controls,control_contrasts=contrasts,
        negative_components_clipped=False,uncertainty_intervals=False,percentage_decomposition=False,
        prospective_evidence=False,fitted_predictors=0,exclusions=0,population_generalization=False,
        automatic_successor=False)
    replay.prior.nested(report,expected)
    return dict(passes=True,groups=8,donor_summaries=32,omission_summaries=32,
                ranking_comparisons=24,control_cells=1152,control_contrasts=960,
                rows=4608,independent_matrix_statistics=True,
                pair_components=48,pair_ranking_comparisons=48,future_omissions=32)
