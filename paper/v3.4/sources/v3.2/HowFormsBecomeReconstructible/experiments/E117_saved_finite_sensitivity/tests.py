"""Known-answer local examples plus independent full-field checks."""
import json
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import cap_cpus,dump,rng,sha,utc
from E117_saved_finite_sensitivity import measure,audit,data,analysis,inference
from E117_saved_finite_sensitivity.plan import HERE,ROOT,EDGE_METRICS,CELL_METRICS,settings
from E117_saved_finite_sensitivity.run import code_paths,inventory

def unit():
    checks=[];w=np.zeros((1,2,16,16));w[0,0,0,0]=1.;w[0,0,4,4]=2e-10
    current=w.copy();current[0,0,4,4]=0.;selected=np.zeros_like(w,bool);selected[0,0,4,4]=True
    mask=np.zeros((1,16,16),bool)
    e,c,_,_,_=analysis.checked_compare(w,current,mask,selected,0.,0.)
    ix=lambda x:EDGE_METRICS.index(x);ci=lambda x:CELL_METRICS.index(x)
    assert e[0,2,ix('lost_reference_mass')]==2e-10
    assert e[0,2,ix('lost_reference_coupling')]==2.
    assert e[0,2,ix('reference_coupling_mass')]==4.
    assert c[0,5,ci('newly_isolated')]==2
    num,den=measure.features(e,c,e)
    assert num[0,7]/den[0,7]==.5 and num[0,6]/den[0,6]<1e-9
    checks+=['tiny_raw_weight_can_carry_half_coupling','lost_edges_create_exact_isolated_cells','raw_and_normalized_ratios_separate']
    e,c,_,_,_=analysis.checked_compare(w,w,mask,selected,0.,1e-4)
    assert e[0,2,ix('lost_edges')]==0 and c[0,5,ci('newly_isolated')]==0
    assert c[0,5,ci('current_weak')]==2 and c[0,5,ci('floor_attenuation_sum')]>1.999
    checks.append('floor_attenuates_without_deleting_edges')
    # Injury severs a physical edge without attributing it to quantization.
    mask[0,4,4]=True;e,c,_,_,_=analysis.checked_compare(w,current,mask,selected,0.,0.)
    assert e[0,2,ix('lost_edges')]==0;checks.append('physical_absence_excluded_from_channel_loss')
    # Zero denominators produce undefined ratios rather than invented absence-of-effect values.
    z=np.zeros_like(w);e,c,_,_,_=analysis.checked_compare(z,z,mask,selected,0.,1e-4)
    n,d=measure.features(e,c,e);row={};analysis.ratio_fields(row,'E',n[0],d[0])
    assert row['E_lost_normalized_mass_fraction'] is None and row['E_floor_attenuation_mean']==0.
    checks.append('zero_reference_ratios_explicitly_undefined')
    r=rng('E117','tests');shape=(3,2,4,2)
    w=r.uniform(-1,1,(*shape,2,16,16));w[r.random(w.shape)<.3]=0.
    w*=r.choice([1.,1e-12],size=(*shape,1,1,1));v=w.copy();v[r.random(w.shape)<.2]=0.
    v[r.random(w.shape)<.1]*=-1
    mask=r.random((4,2,16,16))<.1;selected=r.random((2,4,2,2,16,16))<.15
    e,c,_,_,_=analysis.checked_compare(w,v,mask,selected,0.,np.full(shape,1e-4))
    np.testing.assert_allclose(e[...,0,:]+e[...,1,:],e[...,2,:],atol=2e-12,rtol=2e-13)
    np.testing.assert_allclose(c[...,:3,:].sum(axis=-2),c[...,5,:],atol=2e-12,rtol=2e-13)
    checks+=['all_vector_metrics_match_independent_formulas','selected_outside_partition','cell_regions_partition_free_cells']
    cfg=settings('benchmark');cfg['blocks']=[1,2];cfg['bootstrap_samples']=4
    weights=np.array([[2.,0.],[0.,2.],[1.,1.],[1.,1.]])
    rows=[dict(task=1,**{k:None for k in inference.COLUMNS}),dict(task=2,**{k:.5 for k in inference.COLUMNS})]
    out=inference.describe(rows,cfg,weights)['features'][inference.COLUMNS[0]]
    assert out['mean']==.5 and out['bootstrap_undefined_draws']==1 and out['valid_rows']==1
    out=inference.describe([],cfg,weights);assert out['rows']==0 and out['features'][inference.COLUMNS[0]]['mean'] is None
    checks+=['zero_denominator_bootstrap_draws_counted','empty_event_strata_retained']
    return checks

if __name__=='__main__':
    cap_cpus(1);(HERE/'analysis').mkdir(exist_ok=True);i=1
    while (HERE/f'analysis/tests_attempt_{i:03d}.json').exists():i+=1
    path=HERE/f'analysis/tests_attempt_{i:03d}.json';tick=time.monotonic()
    try:
        resources=inventory();data.registry('benchmark',full=True);checks=unit()
        dump(path,dict(status='PASS',utc=utc(),seconds=time.monotonic()-tick,checks=checks,resources=resources,
            inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in code_paths()},registry_sha256=sha(HERE/'SOURCE_DATA.json')))
        print(json.dumps(dict(status='PASS',checks=len(checks),seconds=time.monotonic()-tick)))
    except BaseException:
        dump(path,dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,traceback=traceback.format_exc()));raise
