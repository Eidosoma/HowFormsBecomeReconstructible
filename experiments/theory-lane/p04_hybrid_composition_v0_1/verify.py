"""Independent construction, scalar scoring, forecast and native-dynamics audit."""
import csv
import hashlib
import json
import math
import numpy as np

import audit_reader
from common import arrays,equal,read,sha,stamp,write


def csv_rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def close(x,y):
    assert math.isfinite(x) and math.isfinite(y) and abs(x-y)<2e-12,(x,y)


def rng(parts):
    seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed))


def summary_check(result,values,cfg):
    close(result['mean'],sum(values)/len(values))
    for b,v in zip(cfg['blocks'],values):close(result['by_block'][str(b)],v)
    random=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    boot=np.array(values)[random.integers(len(values),size=(cfg['bootstrap_replicates'],len(values)))].mean(axis=1)
    for x,y in zip(result['descriptive_block_bootstrap_95'],np.quantile(boot,[.025,.975])):close(x,float(y))
    assert result['positive_blocks']==sum(v>0 for v in values)
    assert result['tied_blocks']==sum(v==0 for v in values)
    assert result['negative_blocks']==sum(v<0 for v in values)


def prepared_check(data,block,cfg):
    ports={(y,x) for yy,xx in ((7,1),(3,10),(11,10)) for y in range(yy,yy+2) for x in range(xx,xx+2)}
    eligible=np.array([16*y+x for y in range(16) for x in range(16) if (y,x) not in ports])
    n=len(data['founders']);reps=len(cfg['replicates'])
    assert data['masks'].shape==(2,n,reps,16,16)
    weights=np.frombuffer(data['packets'].tobytes(),dtype='<f8').reshape(n,6,2,16,16)
    for case in range(n):
        mask=data['original_masks'][case];incoming=weights[case,0];outgoing=weights[case,1]
        erased=incoming.copy();hybrid=incoming.copy();indices=[]
        for plane in range(2):
            for y in range(16):
                for x in range(16):
                    yy,xx=(y,(x+1)%16) if plane==0 else ((y+1)%16,x)
                    if mask[y,x] or mask[yy,xx]:
                        erased[plane,y,x]*=False
                        assert outgoing[plane,y,x]==0.
                        if incoming[plane,y,x]!=0:indices.append(plane*256+y*16+x)
                    else:hybrid[plane,y,x]=outgoing[plane,y,x]
        equal(erased,weights[case,2],'independent erasure construction')
        equal(hybrid,weights[case,3],'independent hybrid construction')
        scrambled=hybrid.copy()
        signs=np.array([1. if incoming.flat[k]>0 else -1. for k in indices])
        key=[cfg['random_namespace'],block,'backup_signs',int(data['histories'][case]),int(data['founders'][case]),int(data['recipients'][case])]
        shuffled=rng(key).permutation(signs)
        for k,s in zip(indices,shuffled):scrambled.flat[k]=abs(incoming.flat[k])*s
        equal(scrambled,weights[case,4],'independent scrambled signs')
        equal(abs(hybrid),abs(scrambled),'support and magnitude identity')
        assert data['backup_nonzero_count'][case]==len(indices)
        assert data['backup_sign_changes'][case]==(signs!=shuffled).sum()
        assert not weights[case,5].any()
        for ri,rep in enumerate(cfg['replicates']):
            key=[cfg['random_namespace'],block,'injury',rep,int(data['founders'][case])//2,int(data['recipients'][case])]
            chosen=rng(key).choice(eligible,cfg['injury_cells'],replace=False)
            fresh=np.zeros(256,bool);fresh[chosen]=True;fresh=fresh.reshape(16,16)
            equal(fresh,data['masks'][1,case,ri],'independent injury')
            equal(mask,data['masks'][0,case,ri],'original mask')
            for gi in range(2):
                actual=data['masks'][gi,case,ri]
                assert actual.sum()==cfg['injury_cells'] and all(not actual[y,x] for y,x in ports)
            assert data['original_mask_overlap'][case,ri]==(fresh&mask).sum()
    equal(data['unsigned_access'][:,:,3],data['unsigned_access'][:,:,4],'identical unsigned diagnostics')


def forecast_check(folder,cfg):
    source=folder/'inputs/prepared/source_analysis.json'
    assert sha(source)==cfg['source_analysis_sha256']
    prior=read(source)['rate_summaries']['fresh'];f=read(folder/'inputs/prepared/forecasts.json')
    assert not f['clipped'] and f['fitted_parameters']==0 and f['source_analysis_sha256']==sha(source)
    assert f['forecast_rules']==['additive','incoming_reference','outgoing_reference']
    assert set(f['by_block'])=={str(b) for b in cfg['blocks']}
    predictions={}
    for b in cfg['blocks']:
        key=str(b);i=prior['incoming']['by_block'][key];o=prior['outgoing']['by_block'][key];d=prior['erasure_only']['by_block'][key]
        expected={'additive':o+i-d,'incoming_reference':i,'outgoing_reference':o,'erasure_reference':d}
        for name,value in expected.items():close(f['by_block'][key][name],value)
        assert 0<=expected['additive']<=1
        predictions[b]=expected
    close(f['additive_equal_block_mean'],sum(x['additive'] for x in predictions.values())/len(predictions))
    close(f['additive_equal_block_mean'],cfg['advertised_additive_forecast'])
    return predictions


def verify(folder,cfg):
    a=read(folder/'analysis.json');forecasts=forecast_check(folder,cfg)
    tables={name:csv_rows(folder/(name+'.csv')) for name in ('reads','state_rates','block_summaries','forecast_reads','forecast_blocks')}
    ix={(int(row['block']),int(row['local_case']),row['regime'],row['variant'],int(row['replicate'])):row for row in tables['reads']}
    sx={(int(row['block']),int(row['local_case']),row['regime'],row['variant']):row for row in tables['state_rates']}
    bx={(int(row['block']),row['regime'],row['variant']):row for row in tables['block_summaries']}
    fx={(int(row['block']),int(row['local_case']),int(row['replicate']),row['rule']):row for row in tables['forecast_reads']}
    fb={(int(row['block']),row['rule']):row for row in tables['forecast_blocks']}
    total=sum(cfg['cases_per_block']);reps=len(cfg['replicates']);count_blocks=len(cfg['blocks'])
    assert len(ix)==len(tables['reads'])==total*2*6*reps
    assert len(sx)==len(tables['state_rates'])==total*2*6
    assert len(bx)==len(tables['block_summaries'])==count_blocks*2*6
    assert len(fx)==len(tables['forecast_reads'])==total*reps*3
    assert len(fb)==len(tables['forecast_blocks'])==count_blocks*3
    all_data={};scored=0;contexts=0;independent_forecast={}
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        path=folder/f'reads_{block:06d}.npz';receipt=read(folder/f'worker_{block:06d}.json')
        assert receipt['status']=='COMPLETE' and receipt['original_native_replay_byte_equal']
        data=arrays(path,receipt['output_sha256']);all_data[block]=data
        assert len(data['founders'])==n and int(data['block'])==block
        assert data['replicates'].tolist()==cfg['replicates'] and data['budgets'].tolist()==cfg['budgets']
        prepared_check(data,block,cfg)
        equal(data['port_windows'].mean(axis=1),data['mean_ports'],'raw observation windows')
        equal(data['birth'][0],data['birth'][1],'paired injury births')
        for first,second in ((0,2),(1,3),(1,4)):
            equal(data['end'][0,:,first],data['end'][0,:,second],'original-mask control')
            equal(data['port_windows'][0,:,:,first],data['port_windows'][0,:,:,second],'original-mask windows')
        equal(data['mean_ports'][:,:,5,:,0],data['mean_ports'][:,:,5,:,1],'erased cue identity')
        assert not data['both_pass'][:,:,5].any()
        for gi,regime in enumerate(cfg['regimes']):
            independent=audit_reader.replay(data['packets'][0],data['masks'][gi,0,4],int(data['founders'][0]),int(data['recipients'][0]),block,4,cfg)
            equal(independent['birth'],data['birth'][gi,0,4],'independent birth')
            equal(independent['end'][0],data['end'][gi,0,:,4],'independent endpoint')
            equal(independent['mean_ports'][0],data['mean_ports'][gi,0,:,4],'independent mean ports')
            equal(independent['port_windows'][0],data['port_windows'][gi,:,0,:,4],'independent windows')
            diagnostic=audit_reader.transfer(data['packets'][0],data['masks'][gi,0,4],int(data['founders'][0]),cfg['transfer_steps'])
            np.testing.assert_allclose(diagnostic[:,0],data['signed_transfer'][gi,0,:,4],rtol=0,atol=1e-13)
            np.testing.assert_allclose(diagnostic[:,1],data['unsigned_access'][gi,0,:,4],rtol=0,atol=1e-13)
            contexts+=1
            for case in range(n):
                rule=1. if data['founders'][case]%2==0 else -1.
                for vi,variant in enumerate(cfg['variants']):
                    hits=0
                    for ri,rep in enumerate(cfg['replicates']):
                        ports=data['mean_ports'][gi,case,vi,ri]
                        margin=min(rule*ports[0,0],-rule*ports[0,1],-rule*ports[1,0],rule*ports[1,1])
                        good=margin>cfg['reader']['margin'];hits+=good;scored+=1
                        assert data['min_margin'][gi,case,vi,ri]==margin and data['both_pass'][gi,case,vi,ri]==good
                        row=ix[block,case,regime,variant,rep]
                        assert int(row['success'])==good and float(row['margin'])==margin
                        assert int(row['founder'])==data['founders'][case] and int(row['recipient'])==data['recipients'][case]
                        assert row['history']==cfg['histories'][data['histories'][case]]
                        for key,value in zip(('plus_a','plus_b','minus_a','minus_b'),ports.ravel()):assert float(row[key])==value
                        for key in ('signed_transfer','unsigned_access'):assert float(row[key])==data[key][gi,case,vi,ri]
                        for key in ('backup_nonzero_count','backup_sign_changes'):assert int(row[key])==data[key][case]
                        assert int(row['overlap_with_original'])==(data['masks'][gi,case,ri]&data['original_masks'][case]).sum()
                    row=sx[block,case,regime,variant]
                    assert int(row['successes'])==hits and int(row['reads'])==reps
                    assert int(row['founder'])==data['founders'][case] and int(row['recipient'])==data['recipients'][case]
                    assert row['history']==cfg['histories'][data['histories'][case]]
                    close(float(row['rate']),hits/reps)
                    z=1.959963984540054;p=hits/reps;den=1+z*z/reps
                    center=(p+z*z/(2*reps))/den;half=z*math.sqrt(p*(1-p)/reps+z*z/(4*reps*reps))/den
                    close(float(row['conditional_MC_wilson_lower']),max(0.,center-half))
                    close(float(row['conditional_MC_wilson_upper']),min(1.,center+half))
            for vi,variant in enumerate(cfg['variants']):
                row=bx[block,regime,variant];actual=data['both_pass'][gi,:,vi]
                assert int(row['cases'])==n and int(row['reads'])==n*reps and int(row['successes'])==actual.sum()
                close(float(row['rate']),float(actual.mean()))
        for name in ('additive','incoming_reference','outgoing_reference'):
            p=forecasts[block][name];ys=[];losses=[]
            for case in range(n):
                for ri,rep in enumerate(cfg['replicates']):
                    y=int(data['both_pass'][1,case,3,ri]);loss=(y-p)*(y-p);ys.append(y);losses.append(loss)
                    row=fx[block,case,rep,name]
                    assert int(row['hybrid_success'])==y
                    close(float(row['predicted_rate']),p);close(float(row['brier']),loss)
            observed=sum(ys)/len(ys);error=observed-p;brier=sum(losses)/len(losses)
            row=fb[block,name]
            assert int(row['cases'])==n and int(row['reads'])==n*reps
            for key,value in [('predicted_rate',p),('observed_hybrid_rate',observed),('error',error),('absolute_error',abs(error)),('squared_rate_error',error*error),('brier',brier)]:
                close(float(row[key]),value)
            independent_forecast[block,name]=(p,error,brier)
    interaction_values={}
    for gi,regime in enumerate(cfg['regimes']):
        for vi,variant in enumerate(cfg['variants']):
            result=a['rate_summaries'][regime][variant]
            summary_check(result,[float(all_data[b]['both_pass'][gi,:,vi].mean()) for b in cfg['blocks']],cfg)
            joined=np.concatenate([all_data[b]['both_pass'][gi,:,vi] for b in cfg['blocks']])
            assert result['reads']==joined.size and result['successes']==joined.sum()
            assert result['cases_with_any_success']==joined.any(axis=1).sum() and result['cases_with_all_success']==joined.all(axis=1).sum()
        for name,first,second in [('hybrid_minus_incoming',3,0),('hybrid_minus_outgoing',3,1),('hybrid_minus_scrambled',3,4),
                ('rewrite',1,0),('rewrite_beyond_erasure',1,2),('erasure_only',2,0),('scrambled_minus_outgoing',4,1)]:
            result=a['effects'][regime][name]
            values=[float((d['both_pass'][gi,:,first].astype(int)-d['both_pass'][gi,:,second].astype(int)).mean()) for d in all_data.values()]
            summary_check(result,values,cfg)
            x=np.concatenate([d['both_pass'][gi,:,first] for d in all_data.values()]);y=np.concatenate([d['both_pass'][gi,:,second] for d in all_data.values()])
            assert result['paired_reads']==x.size
            for key,actual in [('first_only',x&~y),('second_only',y&~x),('both_pass',x&y),('both_fail',~x&~y)]:assert result[key]==actual.sum()
        values=[]
        for b in cfg['blocks']:
            rows=all_data[b]['both_pass'][gi]
            value=sum(int(h)-int(o)-int(i)+int(d) for i,o,d,h in zip(rows[:,0].ravel(),rows[:,1].ravel(),rows[:,2].ravel(),rows[:,3].ravel()))/rows[:,0].size
            values.append(value)
        interaction_values[regime]=values
        summary_check(a['factorial_interaction'][regime],values,cfg)
    for name,result in a['frozen_forecast_evaluation'].items():
        probabilities,errors,losses=zip(*(independent_forecast[b,name] for b in cfg['blocks']))
        close(result['forecast_equal_block_mean'],sum(probabilities)/len(probabilities))
        summary_check(result['error'],errors,cfg);summary_check(result['brier'],losses,cfg)
        close(result['mean_absolute_block_error'],sum(abs(x) for x in errors)/len(errors))
        close(result['root_mean_square_block_error'],math.sqrt(sum(x*x for x in errors)/len(errors)))
    for rival,result in a['additive_brier_minus_rivals'].items():
        summary_check(result,[independent_forecast[b,'additive'][2]-independent_forecast[b,rival][2] for b in cfg['blocks']],cfg)
    shifts=[]
    for b,j in zip(cfg['blocks'],interaction_values['fresh']):
        r=all_data[b]['both_pass'][1]
        now=(int(r[:,1].sum())+int(r[:,0].sum())-int(r[:,2].sum()))/r[:,0].size
        shift=now-forecasts[b]['additive'];shifts.append(shift)
        close(independent_forecast[b,'additive'][1],j+shift)
    summary_check(a['contemporaneous_additive_control_shift'],shifts,cfg)
    assert a['hybrid_beats_both_reference_point_estimates']==all(a['effects']['fresh'][k]['mean']>0 for k in ('hybrid_minus_incoming','hybrid_minus_outgoing'))
    assert a['correct_backup_beats_scrambled_point_estimate']==(a['effects']['fresh']['hybrid_minus_scrambled']['mean']>0)
    close(a['frozen_forecast_value'],cfg['advertised_additive_forecast'])
    assert a['backup_nonzero_edges']==sum(int(d['backup_nonzero_count'].sum()) for d in all_data.values())
    assert a['backup_changed_signs']==sum(int(d['backup_sign_changes'].sum()) for d in all_data.values())
    assert a['cases_with_no_sign_change']==sum(int((d['backup_sign_changes']==0).sum()) for d in all_data.values())
    assert scored==total*2*6*reps and contexts==count_blocks*2
    result=dict(status='PASS',at_utc=stamp(),native_read_rows=scored,conditional_rate_rows=len(sx),block_summary_rows=len(bx),
        forecast_read_rows=len(fx),forecast_block_rows=len(fb),independent_contexts=contexts,independent_variants_per_context=6,
        independent_replicate=4,all_masks_and_sign_permutations_regenerated=True,all_record_constructions_checked=True,
        frozen_forecast_arithmetic_checked=True,all_tables_and_bootstraps_checked=True,
        production_reader_imported_by_verifier=False,analysis_module_imported_by_verifier=False,
        files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.suffix in ('.csv','.npz')})
    write(folder/'VERIFICATION.json',result)
    return result
