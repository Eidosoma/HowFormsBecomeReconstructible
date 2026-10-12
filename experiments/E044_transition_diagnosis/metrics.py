"""Join previously audited E042 histories to E043 timing outcomes; no dynamics."""
import hashlib
import json
import numpy as np
from E032_renewal_failure_diagnosis import metrics as prior

HORIZONS=(24,32)
TIMINGS=('original','extra_time','delayed_extra_time')
DAMAGE=('intact','scattered','square')
GROUPS=('persistent_failure','rescued','lost','stable_success')
CLASSES=('both_correct','both_reversed','locked_output_failure','other_failure')
PACKET_FIELDS=prior.PACKET_FIELDS
OUTPUT_FIELDS=prior.OUTPUT_FIELDS
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


def load(run,name,complete):
    path=run/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==complete['outputs_sha256'][name],name
    with np.load(path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
    assert all(np.isfinite(v).all() for v in data.values())
    return data


def outputs(cases):
    R=cases['ports'].shape[2]
    assert cases['ports'].shape==(12,4,R,2,3,7,2)
    assert cases['correct'].shape==cases['margin'].shape==cases['ports'].shape[:-1]
    values=[]
    for hi in range(2):
        row=[]
        for ti in range(3):
            i=hi*6+ti*2+1
            ports=cases['ports'][i,:,:,:,:,0,:].transpose(0,1,3,2,4)
            out=prior.output_features(ports,prior.RULES[:,None,None])
            np.testing.assert_array_equal(out[...,0],cases['correct'][i,:,:,:,:,0].all(axis=2))
            np.testing.assert_array_equal(out[...,5],cases['margin'][i,:,:,:,:,0].min(axis=2))
            row.append(out)
        values.append(row)
    return np.asarray(values)


def classify(before,after):
    assert before.shape==after.shape
    return (2*before.astype(np.uint8)+after.astype(np.uint8))


def history(packet,body,h):
    correct=body[...,0].astype(bool)
    previous=correct[h-9:h-1];current=correct[h-8:h]
    p=lambda name:packet[h-7:h+1,...,PACKET_FIELDS.index(name)].sum(axis=0)
    rows=(1-correct[:h-1].mean(axis=0),correct[h-2],correct[h-1],(~current).sum(axis=0),
        (previous&~current).sum(axis=0),(~previous&current).sum(axis=0),
        packet[h,...,1]-packet[h-8,...,1],p('weak_promoted'),p('strong_weakened'),
        p('physical_strong_lost'),p('strong_sign_flips'),packet[h-1,...,1])
    return np.stack(rows,axis=-1).astype(float)


def join(diagnosis,cases):
    out=outputs(cases);packet=diagnosis['packet'][:,3];body=diagnosis['body'][:,3]
    R=out.shape[3]
    for key,shape in dict(packet=(33,11,4,R,17),body=(32,9,4,R,10),repair=(32,11,4,R,17),
                          graph=(7,4,4,R,3,4),terminal=(7,11,4,R,3,10)).items():
        assert diagnosis[key].shape==shape,(key,diagnosis[key].shape)
    features=[]
    for hi,h in enumerate(HORIZONS):
        ti=(0,1,3,8,16,24,32).index(h)
        np.testing.assert_array_equal(out[hi,0],diagnosis['terminal'][ti,3])
        hist=history(packet,body,h)
        np.testing.assert_array_equal(hist[...,6],hist[...,7]-hist[...,8]-hist[...,9])
        witness=np.stack((out[hi,0,:,:,0,0],out[hi,0,:,:,2,0],out[hi,2,:,:,0,0],out[hi,2,:,:,2,0],
            body[h,...,0] if h<32 else np.zeros_like(body[0,...,0]),np.full_like(body[0,...,0],h<32)),axis=-1)
        expand=lambda a:np.repeat(a[:,:,None,:],3,axis=2)
        codes=4*out[hi,0,...,:4].argmax(axis=-1)+out[hi,2,...,:4].argmax(axis=-1)
        pieces=[np.ones((*out[hi,0].shape[:-1],1)),*out[hi],expand(packet[h]),
            expand(diagnosis['repair'][h-1,3]),diagnosis['graph'][ti,3],expand(body[h-1]),
            expand(hist),expand(witness),np.eye(16)[codes]]
        features.append(np.concatenate(pieces,axis=-1))
    result=dict(features=np.stack(features),groups=classify(out[:,0,...,0],out[:,2,...,0]))
    assert result['features'].shape[-1]==len(FEATURES)==113
    return result


def extract(paths,block,complete):
    diagnosis=load(paths['diagnosis'],f'measurements_{block:06d}.npz',complete['diagnosis'])
    cases=load(paths['timing'],f'cases_{block:06d}.npz',complete['timing'])
    return join(diagnosis,cases)
