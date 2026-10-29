"""Independent D197 fresh-source and primary/secondary statistics checker."""

from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import numpy as np

def module(name):
    spec=importlib.util.spec_from_file_location('d197_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

frozen=module('check_l22_recipient_pulse_panel')
scalar=module('check_l22_yoked_separation')
kernel,source,boundary,physical=frozen.kernel,frozen.source,frozen.boundary,frozen.physical
exact,close=frozen.exact,frozen.close
expected_scope,scope,initial=frozen.expected_scope,frozen.scope,frozen.initial
draws,saved_repair,routing=frozen.draws,frozen.saved_repair,frozen.routing
reader_context,saved_reader,statistics,costs=frozen.reader_context,frozen.saved_reader,frozen.statistics,frozen.costs
BLOCKS=(319700,319701,319702,319703)
FUTURES,ROLES=('future_1','future_2'),('A','B')


def source_saved(ctx,bundle):
    assert set(bundle)=={'before','parent','original','boundary','proof','provenance'}
    i=ctx['index'];p=bundle['provenance']
    assert type(i) is int and i in (*BLOCKS,603197,703193)
    role='fresh_main' if i in BLOCKS else ('fresh_excluded_disposable' if i==603197 else 'miniature_qualification')
    assert p==dict(index=i,role=role,source_regenerated=True,source_sha256={},old_source_directory=None,
        old_source_replay_retained=True,new_founders=int(i!=703193))
    source.saved_source(ctx,bundle['before'],bundle['parent'],bundle['original'],bundle['proof'])
    o=bundle['original']
    checked=boundary.check(bundle['parent']['theta'],o['kept_V'],o['fresh'],o['damaged_theta'],i,ctx['config'].replicates,bundle['boundary'])
    return dict(passes=True,source_replay_retained=True,boundary=checked,new_dynamics=0,new_founders=0)


def summary(futures,reported,index):
    assert index in (*BLOCKS,603197,703193)
    assert reported['schema']=='d197_two_future_block_v1' and reported['new_founders']==int(index!=703193)
    wire=deepcopy(reported);wire.update(schema='d193_two_future_block_v1',new_founders=0)
    return frozen.summary(futures,wire,index)


def primary(data,reported,parents,draws):
    assert set(data)==set(BLOCKS)
    assert reported['schema']=='d197_recipient_pulse_primary_v1' and reported['blocks']==list(BLOCKS)
    assert reported['new_founders']==4 and reported['source_regenerated'] and reported['prospective']
    wire=deepcopy(reported);wire.pop('prospective')
    wire.update(schema='d195_recipient_pulse_panel_v1',blocks=list(frozen.BLOCKS),new_founders=0,source_regenerated=False)
    for row in [*wire['by_future'].values(),wire['new_only']]:
        assert row['schema']=='d197_four_block_stream_v1' and row['blocks']==list(BLOCKS) and row['new_founders']==4
        row.update(schema='d195_four_block_stream_v1',blocks=list(frozen.BLOCKS),new_founders=0)
    slots={slot:data[index] for slot,index in zip(frozen.BLOCKS,BLOCKS)}
    frozen.panel_summary(slots,wire,parents,draws)
    return dict(passes=True,fresh_labels_restored=True,old_outcomes_pooled=False,independent_scalar_statistics=True)


def margins(data,result,parents,draws):
    assert set(data)==set(BLOCKS) and result['blocks']==list(BLOCKS) and result['records']==16*parents
    assert result['schema']=='d197_secondary_margin_v1' and result['prospective'] and result['primary_unchanged']
    assert result['definition']=='target_template_score_minus_strongest_other_template_score'
    assert set(result)=={'schema','blocks','records','definition','by_future','new_only','prospective','primary_unchanged'}
    assert set(result['by_future'])==set(FUTURES)
    names,terms=expected_scope();base=tuple(p+'__'+k for p in ('common','residual') for k in frozen.KINDS)+names[-5:]
    def count(xs):
        return dict(n=len(xs),improved=sum(x>2e-12 for x in xs),worsened=sum(x < -2e-12 for x in xs),
            tied=sum(abs(x)<=2e-12 for x in xs),net=math.fsum(xs)/len(xs),
            positive=math.fsum(max(x,0) for x in xs)/len(xs),negative=math.fsum(min(x,0) for x in xs)/len(xs))
    def trans(a):
        a=a.reshape(-1,a.shape[-1]);return dict(records=count([math.fsum(map(float,r))/len(r) for r in a]),draws=count(list(map(float,a.flat))))
    def means(a):return np.array([[math.fsum(map(float,r))/len(r) for r in b] for b in a])
    def check_row(a,row,contrast=False,weights=None):
        record=means(a)
        fields=('mean','minimum','median','maximum','by_block','by_message','by_block_message','leave_one_block_out')
        scalar.describe(record[...,None],('margin',),parents,{k:row[k] for k in fields})
        close(row['per_record'],record.tolist());close(row['per_draw'],a.tolist())
        extra={'transitions','coefficients'} if contrast else set()
        assert set(row)==set(fields)|{'per_record','per_draw'}|extra
        if contrast:
            assert row['coefficients']==weights;g=a.reshape(4,4,parents,a.shape[-1])
            expected=dict(pooled=trans(a),by_block=[trans(b) for b in a],
                by_message=[trans(g[:,m]) for m in range(4)],by_block_message=[[trans(x) for x in b] for b in g])
            close(row['transitions'],expected)
    for future,reported in [*result['by_future'].items(),('both',result['new_only'])]:
        fs=FUTURES if future=='both' else (future,);nd=draws*len(fs)
        assert reported['blocks']==list(BLOCKS) and reported['records']==16*parents and reported['reader_draws']==nd
        assert reported['parents_per_message']==parents and reported['endpoint']=='secondary_continuous_margin'
        assert reported['fields']==['margin'] and reported['prospective'] and reported['fitted_models']==0 and reported['uncertainty_interval'] is None
        assert set(reported['named_arms'])==set(names) and set(reported['by_role'])==set(ROLES)
        arrays={}
        for name in names:
            for i in BLOCKS:
                assert set(data[i])==set(FUTURES)
                for f in FUTURES:
                    assert set(data[i][f])==set(names)
                    x=data[i][f][name];assert x.shape==(4*parents,draws) and x.dtype==np.float64 and np.isfinite(x).all()
            arrays[name]=np.array([[[float(data[i][f][name][j,d]) for f in fs for d in range(draws)]
                                   for j in range(4*parents)] for i in BLOCKS])
            check_row(arrays[name],reported['named_arms'][name])
        by_role={r:{n:arrays[n.replace('__','__'+r+'__',1) if n in base[:-5] else n] for n in base} for r in ROLES}
        averaged={n:np.array([math.fsum((float(a),float(b)))/2 for a,b in zip(by_role['A'][n].flat,by_role['B'][n].flat)]).reshape(4,4*parents,nd) for n in base}
        for role,values in [*by_role.items(),('role_mean',averaged)]:
            view=reported['role_mean'] if role=='role_mean' else reported['by_role'][role]
            assert set(view['arms'])==set(base) and set(view['contrasts'])==set(terms)
            for n,a in values.items():check_row(a,view['arms'][n])
            for name,weights in terms.items():
                a=np.array([math.fsum(w*float(values[n].flat[j]) for n,w in weights.items()) for j in range(4*4*parents*nd)]).reshape(4,4*parents,nd)
                check_row(a,view['contrasts'][name],True,weights)
        for family in ('common','residual'):
            close(reported['role_mean']['arms'][family+'__trace_writer'],reported['role_mean']['arms'][family+'__LL'])
    return dict(passes=True,secondary_margin=True,all_controls=True,omission_divisor=3,independent_scalar_statistics=True)
