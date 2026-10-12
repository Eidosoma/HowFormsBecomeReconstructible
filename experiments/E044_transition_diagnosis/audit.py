"""Independent scalar joins, outcome labels, history windows and conditional inference."""
import hashlib
import json
import numpy as np
from E032_renewal_failure_diagnosis import audit as prior

HORIZONS=(24,32)
TIMINGS=('original','extra_time','delayed_extra_time')
DAMAGE=('intact','scattered','square')
GROUPS=('persistent_failure','rescued','lost','stable_success')
CLASSES=('both_correct','both_reversed','locked_output_failure','other_failure')
PACKET_FIELDS=('nonzero', 'strong', 'weak_nonzero', 'absolute_mass', 'mean_absolute_change', 'changed_sign_nonzero', 'original_strong_same_strong', 'original_strong_opposite_strong', 'physical_strong_lost', 'available_strong_before', 'weak_promoted', 'strong_weakened', 'strong_sign_flips', 'new_strong_changed_sign', 'surviving_strong_changed_sign', 'available_weak_before', 'exact_strong_copies')
OUTPUT_FIELDS=('both_correct', 'both_reversed', 'locked_output_failure', 'other_failure', 'individual_cue_accuracy', 'worst_margin', 'cue_amplitude_A', 'cue_amplitude_B', 'absolute_bias_A', 'absolute_bias_B')
REPAIR_FIELDS=('available','returning','returning_nonzero','returning_strong','returning_abs_sum',
    'available_weak_nonzero','weak_promoted','weak_erased','available_zero','zero_restored','zero_promoted',
    'zero_abs_sum','young_weak','young_promoted','young_erased','young_abs_before','young_abs_after')
GRAPH_FIELDS=('nonzero_output_fraction','nonzero_all_outputs','strong_output_fraction','strong_all_outputs')
HISTORY_FIELDS=('prior_body_failure_fraction','previous_body_correct','current_body_correct','recent_body_failures',
    'recent_new_body_failures','recent_body_recoveries','recent_strong_delta','recent_weak_promotions',
    'recent_strong_weakenings','recent_physical_strong_losses','recent_strong_sign_flips','previous_strong')
WITNESS_FIELDS=('original_intact_correct','original_square_correct','delayed_intact_correct',
    'delayed_square_correct','next_body_success','next_body_observed')
CLASS_FIELDS=tuple(a+'_to_'+b for a in CLASSES for b in CLASSES)
FEATURES=('cohort_fraction',)+tuple(t+'.'+f for t in TIMINGS for f in OUTPUT_FIELDS)+tuple(
    p+'.'+f for p,fields in (('packet',PACKET_FIELDS),('repair',REPAIR_FIELDS),('graph',GRAPH_FIELDS),
        ('body',OUTPUT_FIELDS),('history',HISTORY_FIELDS),('witness',WITNESS_FIELDS),('class_change',CLASS_FIELDS)) for f in fields)
RATIOS={'returning_restored_fraction':('repair.returning_nonzero','repair.returning'),
    'weak_promoted_fraction':('repair.weak_promoted','repair.available_weak_nonzero'),
    'young_promoted_fraction':('repair.young_promoted','repair.young_weak')}



def load(path,digest):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}


def reconstruct(diagnosis,cases):
    R=cases['ports'].shape[2]
    out=np.empty((2,3,4,R,3,10))
    for hi in range(2):
        for t in range(3):
            for f,r,d in np.ndindex((4,R,3)):
                value=cases['ports'][6*hi+2*t+1,f,r,:,d,0,:]
                out[hi,t,f,r,d]=prior.output(value,1. if f in (0,2) else -1.)
    rows=np.empty((2,4,R,3,113));groups=np.empty((2,4,R,3),np.uint8)
    for hi,h in enumerate((24,32)):
        for f,r in np.ndindex((4,R)):
            body=diagnosis['body'][:,3,f,r];packet=diagnosis['packet'][:,3,f,r]
            good=[bool(x) for x in body[:,0]]
            hist=[sum(not x for x in good[:h-1])/(h-1),good[h-2],good[h-1],
                sum(not good[g-1] for g in range(h-7,h+1)),
                sum(good[g-2] and not good[g-1] for g in range(h-7,h+1)),
                sum(not good[g-2] and good[g-1] for g in range(h-7,h+1)),
                packet[h,1]-packet[h-8,1],sum(packet[g,10] for g in range(h-7,h+1)),
                sum(packet[g,11] for g in range(h-7,h+1)),sum(packet[g,8] for g in range(h-7,h+1)),
                sum(packet[g,12] for g in range(h-7,h+1)),packet[h-1,1]]
            witness=[out[hi,0,f,r,0,0],out[hi,0,f,r,2,0],out[hi,2,f,r,0,0],out[hi,2,f,r,2,0],
                int(good[h]) if h<32 else 0,int(h<32)]
            for d in range(3):
                old,new=out[hi,0,f,r,d],out[hi,2,f,r,d]
                groups[hi,f,r,d]=(3 if new[0] else 2) if old[0] else (1 if new[0] else 0)
                classification=[0]*16
                classification[4*list(old[:4]).index(1.)+list(new[:4]).index(1.)]=1
                rows[hi,f,r,d]=[1.,*out[hi,0,f,r,d],*out[hi,1,f,r,d],*out[hi,2,f,r,d],
                    *packet[h],*diagnosis['repair'][h-1,3,f,r],*diagnosis['graph'][5+hi,3,f,r,d],
                    *body[h-1],*hist,*witness,*classification]
                np.testing.assert_array_equal(old,diagnosis['terminal'][5+hi,3,f,r,d])
    return dict(features=rows,groups=groups)


def inspect(paths,block,complete,saved):
    raw={}
    for key,name in (('diagnosis',f'measurements_{block:06d}.npz'),('timing',f'cases_{block:06d}.npz')):
        raw[key]=load(paths[key]/name,complete[key]['outputs_sha256'][name])
    expected=reconstruct(raw['diagnosis'],raw['timing'])
    np.testing.assert_array_equal(saved['groups'],expected['groups'])
    np.testing.assert_allclose(saved['features'],expected['features'],rtol=1e-14,atol=1e-12)
    return True


def definitions():
    result={}
    for hi,h in enumerate(HORIZONS):
        for d,injury in enumerate(DAMAGE):
            for group_name in ('all',*GROUPS):
                group=None if group_name=='all' else GROUPS.index(group_name)
                prefix=f'h{h}.{injury}.{group_name}.'
                for k,field in enumerate(FEATURES):
                    denominator=FEATURES.index('witness.next_body_observed') if field=='witness.next_body_success' else None
                    result[prefix+field]=dict(horizon=hi,injury=d,group=group,feature=k,denominator=denominator,population_denominator=k==0)
                for label,(num,den) in RATIOS.items():
                    result[prefix+'repair.'+label]=dict(horizon=hi,injury=d,group=group,feature=FEATURES.index(num),
                        denominator=FEATURES.index(den),population_denominator=False)
    return result


def check_summaries(summary,data):
    assert summary['features']==list(FEATURES) and summary['groups']==list(GROUPS)
    assert summary['definitions']==definitions() and set(summary['series'])==set(summary['definitions'])
    key=json.dumps(['E044','bootstrap','transition_diagnosis'],separators=(',',':')).encode()
    seed=int.from_bytes(hashlib.sha256(key).digest()[:16],'little');count=len(summary['blocks'])
    draws=np.random.Generator(np.random.PCG64(seed)).integers(0,count,(10000,count)).T
    for name,sp in summary['definitions'].items():
        a=data['features'][:,sp['horizon'],:,:,sp['injury']]
        selected=np.ones(a.shape[:-1],bool) if sp['group'] is None else data['groups'][:,sp['horizon'],:,:,sp['injury']]==sp['group']
        num=(a[...,sp['feature']]*selected).sum(axis=(1,2))
        if sp['population_denominator']:den=np.full(count,a.shape[1]*a.shape[2])
        elif sp['denominator'] is None:den=selected.sum(axis=(1,2))
        else:den=(a[...,sp['denominator']]*selected).sum(axis=(1,2))
        st=summary['series'][name]
        np.testing.assert_array_equal(num,st['block_numerators']);np.testing.assert_array_equal(den,st['block_denominators'])
        assert st['mean']==(float(num.sum()/den.sum()) if den.sum() else None)
        n=num[draws].sum(axis=0);d=den[draws].sum(axis=0);valid=d>0
        ci=np.percentile(n[valid]/d[valid],[2.5,97.5]).tolist() if valid.any() else None
        if ci is None:assert st['ci95'] is None
        else:np.testing.assert_allclose(ci,st['ci95'],rtol=1e-14,atol=1e-12)
        assert st['valid_bootstrap_draws']==int(valid.sum())
