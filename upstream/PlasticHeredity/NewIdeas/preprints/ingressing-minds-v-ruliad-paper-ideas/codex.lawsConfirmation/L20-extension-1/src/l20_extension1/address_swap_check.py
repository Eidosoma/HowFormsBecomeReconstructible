"""Independent D169 replay/assignment and direct factorial accounting."""
from dataclasses import asdict
import hashlib
import numpy as np
from . import heldout_diagnostic_audit as audit, passive_feedback_check as geometry
from . import address_swap as spec

prior=audit.prior;physics=audit.physics


def same(got,want):
    """Preserve structural checks; batch rectangular numeric-list comparisons."""
    if isinstance(want,dict):
        assert isinstance(got,dict) and set(got)==set(want)
        for k in want:same(got[k],want[k])
    elif isinstance(want,(list,tuple)):
        assert isinstance(got,(list,tuple)) and len(got)==len(want)
        try:a=np.asarray(want)
        except ValueError:a=np.asarray([],dtype=object)
        if a.size and a.dtype.kind in 'fiu':
            b=np.asarray(got)
            assert b.shape==a.shape and b.dtype.kind in 'fiu' and np.isfinite(a).all() and np.isfinite(b).all()
            np.testing.assert_allclose(b,a,atol=2e-10,rtol=0)
        else:
            for x,y in zip(got,want):same(x,y)
    else:geometry.same(got,want)


def namespace(co,index):
    legal={'development':range(90000,90016),'pilot':range(100000,100064),'disposable':(514240,)}
    assert type(index) is int and index in legal[co]
    return {'development':'l20-extension1-heldout-v1:diagnostics:heldout',
        'pilot':'l20-extension1-pilot64-v1:diagnostics:heldout',
        'disposable':'l20-extension1-pilot64-v1:diagnostics:disposable'}[co]


def responses(raw):
    y=np.empty((4,2,2,7))
    for g in range(4):
        for c in range(2):
            for a in range(2):
                w=raw['write_states'][g,c,a];base=geometry.shape(w[0,2],g//2)
                r=audit.record_features(raw['outgoing'][g,c,a].tobytes(),g//2,raw['guide'])
                y[g,c,a]=[geometry.shape(w[t,2],g//2)-base for t in range(4)]+[r[0],r[2],
                    audit.terminal_features(raw['terminal_states'][g,c,a,-1,0],g//2)[0]]
    return y


def check_life(raw,meta,original,original_meta,replay=True):
    co,index,life=meta['cohort'],meta['index'],meta['life'];tag=namespace(co,index)
    assert type(life) is int and 0<=life<4 and meta['tag']==tag
    spec.validate(raw)
    same(meta['config'],asdict(audit.p.CONFIG));same(meta['host'],original_meta['host'])
    assert meta['initial_reader_replayed'] is False and meta['actual_lineage_outcomes_used'] is False
    assert meta['only_address_changed'] is True and meta['guide_sha256']==audit.GUIDE_SHA
    assert hashlib.sha256(raw['guide'].astype('<f8').tobytes()).hexdigest()==audit.GUIDE_SHA
    np.testing.assert_array_equal(raw['guide'],original['guide'])
    np.testing.assert_array_equal(raw['start'],original['read_states'][:,:,-1])
    np.testing.assert_array_equal(raw['donor_shift'],original['shift'])
    assert len(meta['cells'])==16
    tissue,ladder,bp=physics.parameters(meta['host']);cfg=audit.p.CONFIG
    wmax=tmax=0.;entries=[]
    for g in range(4):
        mode='translated' if g%2==0 else 'aligned'
        for c in range(2):
            draw=lambda phase:physics.generator(tag,index,life,f'trial{c}:{phase}')
            own=np.array(divmod(int(draw('shift').integers(1,256)),16),np.int64)
            np.testing.assert_array_equal(raw['donor_shift'][g,c],own)
            for a in range(2):
                donor=physics.generator(tag,index,life,f'trial{a}:shift')
                shift=np.array(divmod(int(donor.integers(1,256)),16),np.int64)
                assert raw['q'][g,a]==geometry.ideal(shift,g//2)
                writes,wm=prior.write_trace(raw['start'][g,c],tissue,ladder,draw('write'),mode,shift,cfg,replay=replay)
                np.testing.assert_array_equal(raw['write_states'][g,c,a,0],writes[0])
                if replay:wmax=max(wmax,physics.compare(raw['write_states'][g,c,a],writes))
                packet=prior.packet(prior.project(np.tanh(raw['write_states'][g,c,a,-1,2])))
                assert packet==raw['outgoing'][g,c,a].tobytes()
                routed,sc,sm=prior.prior.select(packet,raw['guide'])
                assert raw['terminal_packet'][g,c,a].tobytes()==routed
                same(raw['scores'][g,c,a],sc)
                terminal,rm=prior.read_trace(routed,tissue,ladder,bp,draw('final_birth'),draw('final_read'),
                    cfg,times=cfg.times,replay=replay)
                np.testing.assert_array_equal(raw['terminal_states'][g,c,a,0],terminal[0])
                if replay:tmax=max(tmax,physics.compare(raw['terminal_states'][g,c,a],terminal))
                entries.append(dict(body_copy=c,address_donor=a,mode=mode,writer=wm,selector=sm,reader=rm))
                if a==c:
                    for key in ('write_states','terminal_states','outgoing','terminal_packet'):
                        np.testing.assert_array_equal(raw[key][g,c,a],original[key][g,c])
                    np.testing.assert_array_equal(raw['scores'][g,c,a],original['scores'][g,c,1])
                    old=original_meta['cycles'][g][c]
                    for key,target in (('writer','writer'),('selector','terminal_selector'),('reader','terminal_reader')):
                        same(entries[-1][key],old[target])
                # Noise consumption must match the original regardless of address.
                old=original_meta['cycles'][g][c]
                assert wm['noise_rng']==old['writer']['noise_rng']
                for key in ('birth_rng','read_rng'):assert rm[key]==old['terminal_reader'][key]
            np.testing.assert_array_equal(raw['write_states'][g,c,0,:2],raw['write_states'][g,c,1,:2])
            np.testing.assert_array_equal(raw['terminal_states'][g,c,0,0],raw['terminal_states'][g,c,1,0])
            if g%2==1 or np.array_equal(raw['donor_shift'][g,0],raw['donor_shift'][g,1]):
                for key in ('write_states','terminal_states','outgoing','terminal_packet','scores','response'):
                    np.testing.assert_array_equal(raw[key][g,c,0],raw[key][g,c,1])
        assert not np.array_equal(raw['terminal_states'][g,0,0,0],raw['terminal_states'][g,1,0,0])
    for g in (0,2):
        np.testing.assert_array_equal(raw['start'][g],raw['start'][g+1])
        np.testing.assert_array_equal(raw['write_states'][g,:,:,:2],raw['write_states'][g+1,:,:,:2])
    same(meta['cells'],entries);expected=responses(raw);same(raw['response'],expected)
    for g in range(4):
        for c in range(2):
            same(raw['response'][g,c,c,4:],original['diagnostic_features'][g,c,[0,2,4]])
    return dict(passes=True,full_physics_replayed=bool(replay),writer_paths=16,reader_paths=16,
        original_paths_reproduced=8,aligned_swap_aliases=4,writer_max_abs=wmax,reader_max_abs=tmax,
        response_max_abs=float(abs(expected-raw['response']).max()),actual_lineage_outcomes_used=False)


def effects(y):
    z00,z01,z10,z11=[float(y[c,a]) for c,a in ((0,0),(0,1),(1,0),(1,1))]
    g=z11-z00;s=z10-z01
    return [g,s,(g-s)/2,(g+s)/2,z11+z00-z01-z10,z01-z00,z11-z10]


def describe(founder,weights):
    n=len(founder);v=np.array(founder);boot=weights@v/n
    omitted=[sum(founder[:j]+founder[j+1:])/(n-1) for j in range(n)]
    return dict(mean=sum(founder)/n,founder_values=founder,
        pointwise_founder_bootstrap_95=np.quantile(boot,[.025,.975]).tolist(),
        positive=sum(x>1e-12 for x in founder),negative=sum(x<-1e-12 for x in founder),
        numerical_zero=sum(abs(x)<=1e-12 for x in founder),omitted_means=omitted,
        omission_minimum=min(omitted),omission_maximum=max(omitted))


def check_summary(s,panels,ids):
    assert s['schema']=='d169_address_swap_v1' and s['ids']=={k:list(v) for k,v in ids.items()}
    assert s['groups']==list(spec.GROUPS) and s['responses']==list(spec.RESPONSES) and s['contrasts']==list(spec.CONTRASTS)
    assert len(s['rows'])==56 and len(s['q_pair_rows'])==424
    assert s['bootstrap_seeds']==[16920260922,16920260923] and s['bootstrap_resamples']==20000
    assert s['primary_focus']==['development','B_ordinary','outgoing_own','address']
    for k in ('all_cases_retained','post_test_intervention','conditional_on_saved_bodies_noise_and_guide','source_primary_unchanged'):assert s[k] is True
    for k in ('actual_lineage_outcomes_used','prospective_prediction_evidence','multiplicity_adjusted','equivalence_test','automatic_successor'):assert s[k] is False
    assert s['new_fits']==s['new_forecasts']==s['new_founders']==0
    row=pair=0
    for ci,co in enumerate(('development','pilot')):
        n=len(ids[co]);y=panels[co]['response'];q=panels[co]['q']
        assert n>1 and y.shape==(n,4,4,2,2,7) and q.shape==(n,4,4,2)
        assert np.isfinite(y).all() and np.isfinite(q).all()
        samples=np.random.default_rng(16920260922+ci).integers(0,n,(20000,n))
        weights=np.stack([np.bincount(v,minlength=n) for v in samples])
        for g,group in enumerate(spec.GROUPS):
            e=np.array([[[effects(y[b,l,g,:,:,k]) for k in range(7)] for l in range(4)] for b in range(n)])
            for k,name in enumerate(spec.RESPONSES):
                f=[[sum(float(y[b,l,g,c,a,k]) for l in range(4))/4 for c,a in ((0,0),(0,1),(1,0),(1,1))] for b in range(n)]
                fm=np.array(f).reshape(n,2,2)
                expected=dict(cohort=co,group=group,response=name,cell_mean=(fm.sum(0)/n).tolist(),
                    founder_cell_mean=fm.tolist(),contrasts={label:describe([sum(float(e[b,l,k,j]) for l in range(4))/4
                        for b in range(n)],weights) for j,label in enumerate(spec.CONTRASTS)})
                same(s['rows'][row],expected);row+=1
            levels=np.arange(-4,5)/4 if g<2 else np.arange(-2,3)/2
            for q0 in levels:
                for q1 in levels:
                    counts=[];sums=[]
                    for b in range(n):
                        ls=[l for l in range(4) if q[b,l,g,0]==q0 and q[b,l,g,1]==q1]
                        counts.append(len(ls));sums.append(sum((e[b,l] for l in ls),np.zeros((7,7))).tolist())
                    total=sum(counts)
                    expected=dict(cohort=co,group=group,q0=float(q0),q1=float(q1),cases=total,
                        founders=sum(v>0 for v in counts),founder_counts=counts,founder_contrast_sums=sums,
                        contrast_means=(np.array(sums).sum(0)/total).tolist() if total else [[None]*7 for _ in range(7)])
                    same(s['q_pair_rows'][pair],expected);pair+=1
    return dict(passes=True,rows=row,q_pair_rows=pair,all_founders_retained=True,
        independent_factorial_arithmetic=True,actual_lineage_outcomes_used=False)
