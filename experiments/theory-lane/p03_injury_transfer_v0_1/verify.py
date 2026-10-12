"""Separate scalar scoring, mask/erasure audit and independent native dynamics."""
import csv
import hashlib
import json
import math
import numpy as np

import audit_reader
from common import arrays,equal,read,sha,stamp,write


def csv_rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def close(a,b):
    assert math.isfinite(a) and math.isfinite(b) and abs(a-b)<2e-12,(a,b)


def summary_check(result,values,cfg):
    close(result['mean'],sum(values)/len(values))
    for block,value in zip(cfg['blocks'],values):close(result['by_block'][str(block)],value)
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    means=np.array(values)[rng.integers(len(values),size=(cfg['bootstrap_replicates'],len(values)))].mean(axis=1)
    for a,b in zip(result['descriptive_block_bootstrap_95'],np.quantile(means,[.025,.975])):close(a,float(b))
    assert result['positive_blocks']==sum(x>0 for x in values)
    assert result['tied_blocks']==sum(x==0 for x in values)
    assert result['negative_blocks']==sum(x<0 for x in values)


def prepared_check(data,block,cfg):
    # Deliberately do not import the preparation, dynamics or diagnostic modules.
    ports={(y,x) for yy,xx in ((7,1),(3,10),(11,10)) for y in range(yy,yy+2) for x in range(xx,xx+2)}
    eligible=np.array([16*y+x for y in range(16) for x in range(16) if (y,x) not in ports])
    n=len(data['founders']);reps=len(cfg['replicates'])
    assert data['masks'].shape==(2,n,reps,16,16)
    weights=np.frombuffer(data['packets'].tobytes(),dtype='<f8').reshape(n,4,2,16,16)
    for i in range(n):
        original=data['original_masks'][i]
        expected=weights[i,0].copy()
        for y in range(16):
            for x in range(16):
                for plane,(yy,xx) in enumerate(((y,(x+1)%16),((y+1)%16,x))):
                    if original[y,x] or original[yy,xx]:
                        expected[plane,y,x]*=False
                        assert weights[i,1,plane,y,x]==0.
        equal(expected,weights[i,2],'independent erasure construction')
        assert not weights[i,3].any()
        for ri,rep in enumerate(cfg['replicates']):
            key=[cfg['random_namespace'],block,'injury',rep,int(data['founders'][i])//2,int(data['recipients'][i])]
            seed=int.from_bytes(hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).digest()[:16],'little')
            chosen=np.random.Generator(np.random.PCG64(seed)).choice(eligible,cfg['injury_cells'],replace=False)
            expected_mask=np.zeros(256,bool);expected_mask[chosen]=True
            equal(data['masks'][1,i,ri],expected_mask.reshape(16,16),'independent fresh injury')
            equal(data['masks'][0,i,ri],original,'original injury identity')
            for regime in range(2):
                mask=data['masks'][regime,i,ri]
                assert mask.sum()==cfg['injury_cells'] and all(not mask[y,x] for y,x in ports)
            assert data['original_mask_overlap'][i,ri]==(original & expected_mask.reshape(16,16)).sum()


def verify(folder,cfg):
    a=read(folder/'analysis.json')
    tables={name:csv_rows(folder/(name+'.csv')) for name in ('reads','state_rates','block_summaries','choice_reads')}
    ix={ (int(r['block']),int(r['local_case']),r['regime'],r['variant'],int(r['replicate'])):r for r in tables['reads'] }
    sx={ (int(r['block']),int(r['local_case']),r['regime'],r['variant']):r for r in tables['state_rates'] }
    bx={ (int(r['block']),r['regime'],r['variant']):r for r in tables['block_summaries'] }
    cx={ (int(r['block']),int(r['local_case']),r['regime'],r['rule'],int(r['replicate'])):r for r in tables['choice_reads'] }
    total=sum(cfg['cases_per_block']);r=len(cfg['replicates'])
    assert len(ix)==len(tables['reads'])==total*2*4*r
    assert len(sx)==len(tables['state_rates'])==total*2*4
    assert len(bx)==len(tables['block_summaries'])==len(cfg['blocks'])*2*4
    assert len(cx)==len(tables['choice_reads'])==total*2*4*r
    all_data={};native_contexts=0;scored=0;decision_values={}
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        path=folder/f'reads_{block:06d}.npz';receipt=read(folder/f'worker_{block:06d}.json')
        assert receipt['status']=='COMPLETE' and receipt['original_native_replay_byte_equal']
        data=arrays(path,receipt['output_sha256']);all_data[block]=data
        assert len(data['founders'])==n and int(data['block'])==block
        assert data['replicates'].tolist()==cfg['replicates'] and data['budgets'].tolist()==cfg['budgets']
        prepared_check(data,block,cfg)
        equal(data['port_windows'].mean(axis=1),data['mean_ports'],'raw observation means')
        equal(data['birth'][0],data['birth'][1],'paired birth across injuries')
        equal(data['end'][0,:,0],data['end'][0,:,2],'original incoming/erasure trajectories')
        equal(data['port_windows'][0,:,:,0],data['port_windows'][0,:,:,2],'original incoming/erasure windows')
        equal(data['mean_ports'][:,:,3,:,0],data['mean_ports'][:,:,3,:,1],'erased cue equality')
        assert not data['both_pass'][:,:,3].any()
        for gi,regime in enumerate(cfg['regimes']):
            audited=audit_reader.replay(data['packets'][0],data['masks'][gi,0,4],int(data['founders'][0]),
                int(data['recipients'][0]),block,4,cfg)
            equal(audited['birth'],data['birth'][gi,0,4],'independent reset')
            equal(audited['end'][0],data['end'][gi,0,:,4],'independent body')
            equal(audited['mean_ports'][0],data['mean_ports'][gi,0,:,4],'independent mean ports')
            equal(audited['port_windows'][0],data['port_windows'][gi,:,0,:,4],'independent windows')
            d=audit_reader.transfer(data['packets'][0],data['masks'][gi,0,4],int(data['founders'][0]),cfg['transfer_steps'])
            np.testing.assert_allclose(d[:,0],data['signed_transfer'][gi,0,:,4],rtol=0,atol=1e-13)
            np.testing.assert_allclose(d[:,1],data['unsigned_access'][gi,0,:,4],rtol=0,atol=1e-13)
            native_contexts+=1
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
                        for k,value in zip(('plus_a','plus_b','minus_a','minus_b'),ports.ravel()):assert float(row[k])==value
                        for k in ('signed_transfer','unsigned_access'):assert float(row[k])==data[k][gi,case,vi,ri]
                        assert int(row['overlap_with_original'])==(data['masks'][gi,case,ri]&data['original_masks'][case]).sum()
                    row=sx[block,case,regime,variant]
                    assert int(row['successes'])==hits and int(row['reads'])==r
                    assert int(row['founder'])==data['founders'][case] and int(row['recipient'])==data['recipients'][case]
                    assert row['history']==cfg['histories'][data['histories'][case]]
                    close(float(row['rate']),hits/r)
                    z=1.959963984540054;p=hits/r;den=1+z*z/r
                    center=(p+z*z/(2*r))/den;half=z*math.sqrt(p*(1-p)/r+z*z/(4*r*r))/den
                    close(float(row['conditional_MC_wilson_lower']),max(0.,center-half))
                    close(float(row['conditional_MC_wilson_upper']),min(1.,center+half))
                for name in ('always_incoming','always_outgoing','signed_transfer','unsigned_access'):
                    dest=decision_values.setdefault((block,regime,name),[])
                    for ri,rep in enumerate(cfg['replicates']):
                        if name=='always_incoming':w=0.
                        elif name=='always_outgoing':w=1.
                        else:
                            x,y=data[name][gi,case,:2,ri];w=1. if y>x else 0. if y<x else .5
                        achieved=(1-w)*int(data['both_pass'][gi,case,0,ri])+w*int(data['both_pass'][gi,case,1,ri])
                        row=cx[block,case,regime,name,rep]
                        assert float(row['weight_outgoing'])==w and float(row['attained_success'])==achieved
                        dest.append((w,achieved))
            for vi,variant in enumerate(cfg['variants']):
                row=bx[block,regime,variant];outcome=data['both_pass'][gi,:,vi]
                assert int(row['cases'])==n and int(row['reads'])==n*r and int(row['successes'])==outcome.sum()
                close(float(row['rate']),float(outcome.mean()))
    for gi,regime in enumerate(cfg['regimes']):
        for vi,variant in enumerate(cfg['variants']):
            result=a['rate_summaries'][regime][variant]
            summary_check(result,[float(all_data[b]['both_pass'][gi,:,vi].mean()) for b in cfg['blocks']],cfg)
            joined=np.concatenate([all_data[b]['both_pass'][gi,:,vi] for b in cfg['blocks']])
            assert result['successes']==joined.sum() and result['reads']==joined.size
            assert result['cases_with_any_success']==joined.any(axis=1).sum() and result['cases_with_all_success']==joined.all(axis=1).sum()
        for name,first,second in [('rewrite',1,0),('beyond_erasure',1,2),('erasure_only',2,0)]:
            result=a['effects'][regime][name]
            delta=[float((all_data[b]['both_pass'][gi,:,first].astype(float)-all_data[b]['both_pass'][gi,:,second]).mean()) for b in cfg['blocks']]
            summary_check(result,delta,cfg)
            x=np.concatenate([d['both_pass'][gi,:,first] for d in all_data.values()])
            y=np.concatenate([d['both_pass'][gi,:,second] for d in all_data.values()])
            assert result['paired_reads']==x.size
            for key,values in [('first_only',x&~y),('second_only',y&~x),('both_pass',x&y),('both_fail',~x&~y)]:assert result[key]==values.sum()
        for name,result in a['choices'][regime].items():
            summary_check(result,[sum(v for _,v in decision_values[b,regime,name])/len(decision_values[b,regime,name]) for b in cfg['blocks']],cfg)
            weights=[w for b in cfg['blocks'] for w,_ in decision_values[b,regime,name]]
            for key,value in [('outgoing_choices',1.),('incoming_choices',0.),('ties',.5)]:assert result[key]==weights.count(value)
        for rival,result in a['signed_choice_minus_rivals'][regime].items():
            signed=a['choices'][regime]['signed_transfer']['by_block'];base=a['choices'][regime][rival]['by_block']
            summary_check(result,[signed[str(b)]-base[str(b)] for b in cfg['blocks']],cfg)
        for block in cfg['blocks']:
            effects=a['effects'][regime]
            close(effects['rewrite']['by_block'][str(block)],effects['beyond_erasure']['by_block'][str(block)]+effects['erasure_only']['by_block'][str(block)])
    summary_check(a['fresh_minus_original_rewrite_effect'],[
        a['effects']['fresh']['rewrite']['by_block'][str(b)]-a['effects']['original']['rewrite']['by_block'][str(b)] for b in cfg['blocks']],cfg)
    assert a['primary_estimate_positive']==(a['effects']['fresh']['rewrite']['mean']>0)
    assert scored==total*2*4*r and native_contexts==len(cfg['blocks'])*2
    result=dict(status='PASS',at_utc=stamp(),native_read_rows=scored,conditional_rate_rows=len(sx),
        block_summary_rows=len(bx),choice_read_rows=len(cx),independent_contexts=native_contexts,
        independent_variants_per_context=4,independent_replicate=4,
        all_masks_regenerated=True,erasure_construction_checked=True,all_tables_and_bootstraps_checked=True,
        production_reader_imported_by_verifier=False,analysis_module_imported_by_verifier=False,
        files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.suffix in ('.csv','.npz')})
    write(folder/'VERIFICATION.json',result)
    return result
