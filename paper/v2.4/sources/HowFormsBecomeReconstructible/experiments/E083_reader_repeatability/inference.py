"""Prespecified within-block/history alignment and complete secondary tables."""
import numpy as np
from common import rng
from E083_reader_repeatability.plan import cohort,settings,STARTS

GROUPS=('fail_fail','gain','harm','success_success')
METRICS=('both','minimum_margin','transfer','aligned_transfer','postinjury_selected_coupling_share')
CONTRASTS={'pruning_h0':('P0','I0'),'pruning_h1':('P1','I1'),
           'pattern':('FF','OF'),'ordinary_restore':('OF','P1'),'filtered_restore':('FF','P1')}


def alignment(old,new):
    # B, history, founder/recipient. Equal weight for all cases and histories.
    return ((old-old.mean(-1,keepdims=True))*(new-new.mean(-1,keepdims=True))).mean(axis=(-2,-1))


def interval(v,indices,confidence=.95):
    v=np.asarray(v,dtype=float);sample=v[indices].mean(axis=1)
    lo,hi=np.quantile(sample,[(1-confidence)/2,(1+confidence)/2])
    return dict(mean=float(v.mean()),interval=[float(lo),float(hi)],confidence=confidence,block_means=v.tolist())


def conditional(numerator,denominator,indices):
    num=np.asarray(numerator,dtype=float);den=np.asarray(denominator,dtype=int)
    sampled_den=den[indices].sum(1);missing=int((sampled_den==0).sum())
    mean=float(num.sum()/den.sum()) if den.sum() else None
    ci=None
    if not missing:
        ci=np.quantile(num[indices].sum(1)/sampled_den,[.025,.975]).tolist()
    return dict(mean=mean,interval=ci,confidence=.95,count=int(den.sum()),
                undefined_bootstrap_draws=missing,block_numerators=num.tolist(),block_denominators=den.tolist())


def label(ci):
    return 'POSITIVE_ALIGNMENT' if ci[0]>0 else 'NEGATIVE_ALIGNMENT' if ci[1]<0 else 'UNRESOLVED'


def stacks(tasks,sources,cases,tag):
    sel=[i for i,t in enumerate(tasks) if cohort(t)==tag]
    old={k[4:]:np.stack([sources[i][k] for i in sel]) for k in sources[sel[0]] if k.startswith('old_')}
    new={k:np.stack([np.stack([d[k] for d in cases[i]]) for i in sel]) for k in cases[sel[0]][0]}
    return [tasks[i] for i in sel],old,new


def transitions(old_of,old_ff,new_of,new_ff):
    group=(old_of.astype(int)*2+old_ff.astype(int))
    # binary codes 0 fail/fail, 1 gain, 2 harm, 3 success/success
    delta=new_ff.astype(int)-new_of.astype(int)
    tables={}
    for name,d in [('draw_0',delta[:,0]),('draw_1',delta[:,1]),('mean_sign',np.sign(delta.mean(axis=1)).astype(int))]:
        tables[name]=[[int(((group==g)&(d==v)).sum()) for v in (-1,0,1)] for g in range(4)]
    recurrence={}
    for g,sign in ((1,1),(2,-1)):
        n=(delta==sign).sum(axis=1)
        recurrence[GROUPS[g]]=[int(((group==g)&(n==v)).sum()) for v in range(3)]
    return dict(original_group_counts=[int((group==g).sum()) for g in range(4)],
                old_group_new_effect_tables=tables,recurrence_0_1_2_draws=recurrence,
                case_draw_pairs=int(delta.size),source_cases=int(group.size))


def pruning_table(c):
    a=c['both'];h0=a[...,4:8,:,:].astype(int)-a[...,:4,:,:].astype(int)
    h1=a[...,13:17,:,:].astype(int)-a[...,9:13,:,:].astype(int)
    return [[int(((h0==i)&(h1==j)).sum()) for j in (-1,0,1)] for i in (-1,0,1)]


def analyze(tasks,sources,cases,controls,mode):
    cfg=settings(mode);passed=all(c.get('pass',False) for c in controls)
    out=dict(experiment='E083',mode=mode,controls_pass=passed,fresh_reader_draws=2,
             old_observations_pooled=False,new_source_records=False,all_source_cases_retained=True,
             primary_effects={},cohorts={})
    for tag in cfg['cohorts']:
        blocks,old,new=stacks(tasks,sources,cases,tag);B=len(blocks)
        indices=rng('E083','reader_repeatability','bootstrap',tag).integers(0,B,(10000,B))
        od=old['both'][:,22:26].astype(int)-old['both'][:,18:22].astype(int)
        nd=new['both'][:,:,22:26].astype(int)-new['both'][:,:,18:22].astype(int)
        score=alignment(od[:,2:].reshape(B,2,-1),nd.mean(1)[:,2:].reshape(B,2,-1))
        primary=interval(score,indices,.975);name=tag+'_mixture_alignment'
        out['primary_effects'][name]=label(primary['interval']) if mode=='scientific' and passed else None
        row=dict(blocks=blocks,primary_alignment=primary,descriptions={},groups={},
                 original_pruning_table=pruning_table(old),new_pruning_tables={
                     'draw_'+str(d):pruning_table({k:v[:,d] for k,v in new.items()}) for d in range(2)})
        for kind,offset in (('native',0),('mixture',2)):
            for hist,arms in (('pooled',[offset,offset+1]),('sham',[offset]),('pulse',[offset+1])):
                prefix=kind+'_'+hist
                of=old['both'][:,18:22][:,arms];ff=old['both'][:,22:26][:,arms]
                nf=new['both'][:,:,18:22][:,:,arms];ng=new['both'][:,:,22:26][:,:,arms]
                group=of.astype(int)*2+ff.astype(int)
                gr=transitions(of,ff,nf,ng);gr['conditional_new_effects']={}
                for g,name_g in enumerate(GROUPS):
                    chosen=group==g;den=chosen.reshape(B,-1).sum(1)
                    gr['conditional_new_effects'][name_g]={}
                    for draw,d in [('draw_0',nd[:,0,arms]),('draw_1',nd[:,1,arms]),('mean',nd.mean(1)[:,arms])]:
                        gr['conditional_new_effects'][name_g][draw]=conditional((chosen*d).reshape(B,-1).sum(1),den,indices)
                row['groups'][prefix]=gr
                for draw,arr in [('draw_0',{k:v[:,0] for k,v in new.items()}),('draw_1',{k:v[:,1] for k,v in new.items()}),('mean',{k:v.mean(1) for k,v in new.items()})]:
                    desc={}
                    for metric in METRICS:
                        vals={c:arr[metric][:,start:start+4][:,arms].astype(float).reshape(B,-1).mean(1) for c,start in STARTS.items()}
                        entries={c:interval(v,indices) for c,v in vals.items()}
                        for effect,(a,b) in CONTRASTS.items():entries[effect]=interval(vals[a]-vals[b],indices)
                        entries['pruning_change']=interval((vals['P1']-vals['I1'])-(vals['P0']-vals['I0']),indices)
                        desc[metric]=entries
                    row['descriptions'][prefix+'_'+draw]=desc
        out['cohorts'][tag]=row
    out['alignment_at_both_cohorts']=all(v=='POSITIVE_ALIGNMENT' for v in out['primary_effects'].values()) if mode=='scientific' and passed else None
    return out


def audit(tasks,sources,cases,controls,summary,mode):
    """Independent scalar reductions/contingencies and separate RNG implementation."""
    from E015_functional_inheritance.audit import random
    checked=0
    assert summary['controls_pass']==all(c['pass'] for c in controls)
    for tag,row in summary['cohorts'].items():
        ids=[i for i,t in enumerate(tasks) if cohort(t)==tag];B=len(ids)
        boot=random('E083','reader_repeatability','bootstrap',tag).integers(0,B,(10000,B))
        independent=[]
        for i in ids:
            histories=[]
            for arm in (2,3):
                a=[];b=[]
                for f,r in np.ndindex(sources[i]['old_both'].shape[1:]):
                    a.append(int(sources[i]['old_both'][22+arm,f,r])-int(sources[i]['old_both'][18+arm,f,r]))
                    b.append(sum(int(cases[i][d]['both'][22+arm,f,r])-int(cases[i][d]['both'][18+arm,f,r]) for d in (0,1))/2)
                histories.append(sum(x*y for x,y in zip(a,b))/len(a)-(sum(a)/len(a))*(sum(b)/len(b)))
            independent.append(sum(histories)/2)
        p=row['primary_alignment'];np.testing.assert_array_equal(independent,p['block_means'])
        assert p['mean']==sum(independent)/len(independent)
        ci=np.percentile(np.asarray(independent)[boot].sum(1)/B,[1.25,98.75])
        np.testing.assert_allclose(ci,p['interval'],rtol=0,atol=1e-15);checked+=B+1
        expected=label(ci) if mode=='scientific' and summary['controls_pass'] else None
        assert summary['primary_effects'][tag+'_mixture_alignment']==expected
        for key,metrics in row['descriptions'].items():
            kind,hist,draw=key.split('_',2);off=0 if kind=='native' else 2
            arms=[off,off+1] if hist=='pooled' else [off+(hist=='pulse')]
            draws=(0,1) if draw=='mean' else (int(draw[-1]),)
            for metric,entries in metrics.items():
                raw={c:[] for c in STARTS}
                for i in ids:
                    for condition,start in STARTS.items():
                        values=[float(cases[i][d][metric][start+a,f,r]) for d in draws for a in arms for f,r in np.ndindex(cases[i][0][metric].shape[1:])]
                        raw[condition].append(sum(values)/len(values))
                for effect,(a,b) in CONTRASTS.items():raw[effect]=[x-y for x,y in zip(raw[a],raw[b])]
                raw['pruning_change']=[b-a for a,b in zip(raw['pruning_h0'],raw['pruning_h1'])]
                for name,entry in entries.items():
                    values=np.array(raw[name]);np.testing.assert_allclose(values,entry['block_means'],rtol=2e-14,atol=2e-15)
                    np.testing.assert_allclose(values.mean(),entry['mean'],rtol=2e-14,atol=2e-15)
                    np.testing.assert_allclose(np.percentile(values[boot].mean(1),[2.5,97.5]),entry['interval'],rtol=2e-13,atol=2e-15)
                    checked+=1
        for key,gr in row['groups'].items():
            kind,hist=key.split('_');off=0 if kind=='native' else 2
            arms=[off,off+1] if hist=='pooled' else [off+(hist=='pulse')]
            count=np.zeros(4,int);tables={k:np.zeros((4,3),int) for k in ('draw_0','draw_1','mean_sign')}
            recur=np.zeros((2,3),int);num=np.zeros((B,4,3));den=np.zeros((B,4),int)
            for pos,i in enumerate(ids):
                for a in arms:
                    for f,r in np.ndindex(sources[i]['old_both'].shape[1:]):
                        olda=bool(sources[i]['old_both'][18+a,f,r]);oldb=bool(sources[i]['old_both'][22+a,f,r])
                        g=2*int(olda)+int(oldb);count[g]+=1;den[pos,g]+=1
                        ds=[int(cases[i][d]['both'][22+a,f,r])-int(cases[i][d]['both'][18+a,f,r]) for d in (0,1)]
                        for d,v in enumerate(ds):tables['draw_'+str(d)][g,v+1]+=1;num[pos,g,d]+=v
                        tables['mean_sign'][g,int(np.sign(sum(ds)))+1]+=1;num[pos,g,2]+=sum(ds)/2
                        if g in (1,2):recur[g-1,sum(v==(1 if g==1 else -1) for v in ds)]+=1
            assert gr['original_group_counts']==count.tolist()
            assert gr['old_group_new_effect_tables']=={k:v.tolist() for k,v in tables.items()}
            assert gr['recurrence_0_1_2_draws']==dict(gain=recur[0].tolist(),harm=recur[1].tolist())
            assert sum(count)==gr['source_cases'] and 2*sum(count)==gr['case_draw_pairs']
            for g,name_g in enumerate(GROUPS):
                for d,name_d in enumerate(('draw_0','draw_1','mean')):
                    entry=gr['conditional_new_effects'][name_g][name_d]
                    np.testing.assert_array_equal(entry['block_numerators'],num[:,g,d]);np.testing.assert_array_equal(entry['block_denominators'],den[:,g])
                    sums=den[boot,g].sum(1);missing=int((sums==0).sum())
                    assert entry['undefined_bootstrap_draws']==missing
                    assert entry['mean']==(float(num[:,g,d].sum()/count[g]) if count[g] else None)
                    if missing:assert entry['interval'] is None
                    else:np.testing.assert_allclose(entry['interval'],np.percentile(num[boot,g,d].sum(1)/sums,[2.5,97.5]),rtol=0,atol=1e-15)
                    checked+=1
        for name in ('original','draw_0','draw_1'):
            table=np.zeros((3,3),int)
            for i in ids:
                v=sources[i]['old_both'] if name=='original' else cases[i][int(name[-1])]['both']
                for a,f,r in np.ndindex((4,)+v.shape[1:]):
                    x=int(v[4+a,f,r])-int(v[a,f,r]);y=int(v[13+a,f,r])-int(v[9+a,f,r]);table[x+1,y+1]+=1
            expected=row['original_pruning_table'] if name=='original' else row['new_pruning_tables'][name]
            assert table.tolist()==expected;checked+=1
    assert summary['alignment_at_both_cohorts']==(all(v=='POSITIVE_ALIGNMENT' for v in summary['primary_effects'].values()) if mode=='scientific' and summary['controls_pass'] else None)
    return checked


def report(s):
    lines=['# E083 reader repeatability','',f"Mode: {s['mode']}. Two fixed fresh draws; original observations supply labels only.",
           'Known source records; all individual harms and both endpoints retained.','']
    for tag,row in s['cohorts'].items():
        p=row['primary_alignment'];lines += [f"## {tag}",'',f"Mixture alignment: {p['mean']:.6f}, 97.5% interval {p['interval']}; {s['primary_effects'][tag+'_mixture_alignment']}.",'']
        for kind in ('native','mixture'):
            d=row['descriptions'][kind+'_pooled_mean']['both'];g=row['groups'][kind+'_pooled']
            lines += [f"{kind}: OF {100*d['OF']['mean']:.3f}%, FF {100*d['FF']['mean']:.3f}%; mean effect {100*d['pattern']['mean']:.3f} points (95% interval {[100*x for x in d['pattern']['interval']]}).",
                      f"Original groups (fail/fail, gain, harm, success/success): {g['original_group_counts']}. Gain/harm recurrence on 0/1/2 draws: {g['recurrence_0_1_2_draws']}.",'']
        lines += [f"Fresh pruning tables, rows immediate harm/unchanged/gain, columns later harm/unchanged/gain: {row['new_pruning_tables']}.",'']
    lines += ['Positive alignment describes relative ranking within blocks/history; it does not establish universal recurrence or that the old-harm group remains negative.',
              'All secondary intervals are pointwise. Empty conditional bootstrap samples produce null intervals, with counts retained in summary.json.',
              'This assay changes injury, birth and noise together; it cannot isolate their contributions or revise the original E081 primary verdict.','']
    return '\n'.join(lines)
