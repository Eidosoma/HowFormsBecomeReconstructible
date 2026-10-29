"""D197 primary arithmetic wrapper and preregistered secondary reader margin."""

from copy import deepcopy
import numpy as np
from . import l22_pulse_founders_block as block
from . import l22_recipient_pulse_panel_analysis as old
from . import l22_yoked_separation_metrics as geometry

BLOCKS,FUTURES,ROLES=block.BLOCKS,block.FUTURES,block.ROLES


def relabel(value, reverse=False):
    out=deepcopy(value)
    out.update(schema='d195_recipient_pulse_panel_v1' if reverse else 'd197_recipient_pulse_primary_v1',
        blocks=list(old.BLOCKS if reverse else BLOCKS),new_founders=0 if reverse else 4,
        source_regenerated=not reverse)
    if reverse:assert out.pop('prospective') is True
    else:out['prospective']=True
    for row in [*out['by_future'].values(),out['new_only']]:
        row.update(schema='d195_four_block_stream_v1' if reverse else 'd197_four_block_stream_v1',
            blocks=list(old.BLOCKS if reverse else BLOCKS),new_founders=0 if reverse else 4)
    return out


def primary(data,parents=4,draws=4):
    if set(data)!=set(BLOCKS):raise ValueError('four new histories only; excluded cohorts cannot enter')
    slots={slot:data[index] for slot,index in zip(old.BLOCKS,BLOCKS)}
    value=relabel(old.aggregate(slots,parents,draws))
    block.checker().primary(data,value,parents,draws)
    return value


def extract_margins(directory,index,cfg=block.CONFIG,rcfg=block.READOUT):
    block.admit(index,cfg,rcfg)
    ctx=block.model.source.context(index,cfg);codes=ctx['codes'];scalar=geometry.checker();out={};score_rows=0
    packets=block.arrays(directory/'packets.npz')
    for future in FUTURES:
        mapping=block.read(directory/future/'read_map.json');saved=block.read(directory/future/'records.json')
        assert set(mapping)==set(saved)==set(packets)==set(block.packet_names())
        margins={}
        for name in block.packet_names():
            link=mapping[name]
            assert link['packet_sha256']==block.model.array_hash(packets[name]) and link['disabled'] is (name=='reader_off')
            assert __import__('pathlib').Path(link['assay']).name==link['assay']
            raw=block.arrays(directory/future/(link['assay']+'.npz'))
            np.testing.assert_array_equal(raw['s0_theta'],np.repeat(packets[name],rcfg.draws,axis=0))
            value=geometry.scores(raw[f's{rcfg.sweeps}_V'],codes,rcfg.parents,rcfg.draws)
            scalar.scores(raw[f's{rcfg.sweeps}_V'],codes,rcfg.parents,rcfg.draws,raw,value)
            for j,row in enumerate(saved[name]):
                assert (row['world'],row['message'],row['replicate'])==(j,j//rcfg.parents,j%rcfg.parents)
                for k,metric in enumerate(block.METRICS[:4]):scalar.close(row[metric],float(value[2][j,:,k].mean()))
            margins[name]=value[2][...,4].copy();score_rows+=4*rcfg.parents*rcfg.draws
        out[future]=margins
    return out,dict(passes=True,index=index,score_rows=score_rows,named_reads=74,
        margin='target_minus_strongest_other_template',independent_scalar_scores=True,new_dynamics=0)


def margin_stream(data,parents,draws):
    if set(data)!=set(BLOCKS):raise ValueError('all four new histories required')
    names=block.packet_names();matrices={}
    for name in names:
        for index in BLOCKS:
            assert set(data[index])==set(names)
            a=data[index][name]
            assert a.shape==(4*parents,draws) and a.dtype==np.float64 and np.isfinite(a).all()
        matrices[name]=np.stack([data[i][name] for i in BLOCKS])
    def count(a):
        return dict(n=int(a.size),improved=int((a>block.TOL).sum()),worsened=int((a < -block.TOL).sum()),
            tied=int((np.abs(a)<=block.TOL).sum()),net=float(a.mean()),
            positive=float(np.maximum(a,0).mean()),negative=float(np.minimum(a,0).mean()))
    def transitions(a):return dict(records=count(a.mean(axis=-1)),draws=count(a))
    def describe(a,contrast=False):
        value=geometry.describe(a.mean(axis=2)[...,None],('margin',),parents)
        value.update(per_record=a.mean(axis=2).tolist(),per_draw=a.tolist())
        if contrast:
            grouped=a.reshape(4,4,parents,draws)
            value['transitions']=dict(pooled=transitions(a),by_block=[transitions(x) for x in a],
                by_message=[transitions(grouped[:,m]) for m in range(4)],
                by_block_message=[[transitions(x) for x in b] for b in grouped])
        return value
    def view(values):
        return dict(arms={n:describe(a) for n,a in values.items()},
            contrasts={n:dict(coefficients=terms,**describe(sum(w*values[a] for a,w in terms.items()),True))
                       for n,terms in block.model.comparisons().items()})
    base=tuple(block.model.plan())+names[-5:];roles={}
    for role in ROLES:
        roles[role]={n:matrices[n.replace('__','__'+role+'__',1) if n in block.model.plan() else n] for n in base}
    mean={n:.5*(roles['A'][n]+roles['B'][n]) for n in base}
    return dict(blocks=list(BLOCKS),records=16*parents,parents_per_message=parents,reader_draws=draws,
        named_arms={n:describe(a) for n,a in matrices.items()},by_role={r:view(a) for r,a in roles.items()},
        role_mean=view(mean),endpoint='secondary_continuous_margin',fields=['margin'],
        prospective=True,fitted_models=0,uncertainty_interval=None)


def margins(data,parents=4,draws=4):
    if set(data)!=set(BLOCKS):raise ValueError('no missing, extra or excluded founders')
    assert all(set(x)==set(FUTURES) for x in data.values())
    both={i:{n:np.concatenate([data[i][f][n] for f in FUTURES],axis=1) for n in block.packet_names()} for i in BLOCKS}
    result=dict(schema='d197_secondary_margin_v1',blocks=list(BLOCKS),records=16*parents,
        definition='target_template_score_minus_strongest_other_template_score',
        by_future={f:margin_stream({i:data[i][f] for i in BLOCKS},parents,draws) for f in FUTURES},
        new_only=margin_stream(both,parents,2*draws),prospective=True,primary_unchanged=True)
    block.checker().margins(data,result,parents,draws)
    return result


def load_primary(directory):return {i:block.load_futures(directory/f'tissue_{i}') for i in BLOCKS}
def load_margins(directory):return {i:{f:block.arrays(directory/f'tissue_{i}'/(f+'.npz')) for f in FUTURES} for i in BLOCKS}
