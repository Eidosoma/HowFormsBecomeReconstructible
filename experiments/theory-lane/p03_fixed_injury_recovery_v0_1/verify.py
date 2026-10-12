"""Independent raw-score, table, selection and flattened-reader verification."""
import csv
import math

import numpy as np

import audit_reader
from common import arrays,equal,read,sha,stamp,write


def csv_rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def close(a,b):
    assert math.isfinite(a) and math.isfinite(b) and abs(a-b)<2e-12,(a,b)


def summary_check(result,values,cfg):
    close(result['mean'],sum(values)/len(values))
    for b,v in zip(cfg['blocks'],values):
        close(result['by_block'][str(b)],v)
    random=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    bootstrap=np.asarray(values)[random.integers(len(values),size=(cfg['bootstrap_replicates'],len(values)))].mean(axis=1)
    for x,y in zip(result['descriptive_block_bootstrap_95'],np.quantile(bootstrap,[.025,.975])):
        close(x,float(y))


def verify(folder,cfg):
    analysis=read(folder/'analysis.json')
    rows=csv_rows(folder/'reads.csv')
    state_rows=csv_rows(folder/'state_rates.csv')
    block_rows=csv_rows(folder/'block_summaries.csv')
    choices=csv_rows(folder/'choice_cases.csv')
    index={tuple(int(r[k]) for k in ('block','local_case','budget','replicate'))+(r['variant'],):r for r in rows}
    state_index={tuple(int(r[k]) for k in ('block','local_case','budget'))+(r['variant'],):r for r in state_rows}
    block_index={(int(r['block']),int(r['budget']),r['variant']):r for r in block_rows}
    choice_index={(int(r['block']),int(r['local_case']),int(r['budget']),r['rule']):r for r in choices}
    assert len(index)==len(rows)==9216 and len(state_index)==len(state_rows)==576
    assert len(block_index)==len(block_rows)==72 and len(choice_index)==len(choices)==960
    all_data={}
    checked_raw=0
    independent_contexts=0
    for block,count in zip(cfg['blocks'],cfg['cases_per_block']):
        path=folder/f'reads_{block:06d}.npz'
        receipt=read(folder/f'worker_{block:06d}.json')
        assert receipt['status']=='COMPLETE' and receipt['original_native_replay_byte_equal']
        assert sha(path)==receipt['output_sha256']
        data=arrays(path)
        all_data[block]=data
        assert len(data['founders'])==count and int(data['block'])==block
        assert data['budgets'].tolist()==cfg['budgets'] and data['replicates'].tolist()==cfg['replicates']
        equal(data['port_windows'].mean(axis=1),data['mean_ports'],'raw output windows')
        equal(data['mean_ports'][:,:,2,:,0],data['mean_ports'][:,:,2,:,1],'erased matched cues')
        assert not data['both_pass'][:,:,2].any()
        # This fixed context was specified before scientific outputs; evaluate rep 4.
        audited=audit_reader.replay(data['packets'][0],data['masks'][0],int(data['founders'][0]),
            int(data['recipients'][0]),block,4,cfg)
        equal(data['birth'][0,4],audited['birth'],'independent birth')
        equal(data['end'][:,0,:,4],audited['end'],'independent nonlinear endpoint')
        equal(data['mean_ports'][:,0,:,4],audited['mean_ports'],'independent native means')
        equal(data['port_windows'][:,:,0,:,4],audited['port_windows'],'independent native windows')
        diagnostic=audit_reader.transfer(data['packets'][0],data['masks'][0],int(data['founders'][0]),64)
        np.testing.assert_allclose(data['signed_transfer'][0],diagnostic[:,0],rtol=0,atol=1e-13)
        np.testing.assert_allclose(data['unsigned_access'][0],diagnostic[:,1],rtol=0,atol=1e-13)
        independent_contexts+=1
        for bi,budget in enumerate(cfg['budgets']):
            for case in range(count):
                rule=1. if data['founders'][case]%2==0 else -1.
                for vi,variant in enumerate(cfg['variants']):
                    hits=0
                    for rep in cfg['replicates']:
                        ports=data['mean_ports'][bi,case,vi,rep]
                        margin=min(rule*ports[0,0],-rule*ports[0,1],-rule*ports[1,0],rule*ports[1,1])
                        correct=margin>.25
                        assert data['min_margin'][bi,case,vi,rep]==margin
                        assert data['both_pass'][bi,case,vi,rep]==correct
                        r=index[block,case,budget,rep,variant]
                        assert int(r['success'])==correct and float(r['margin'])==margin
                        assert int(r['founder'])==data['founders'][case] and int(r['recipient'])==data['recipients'][case]
                        assert r['history']==cfg['histories'][data['histories'][case]]
                        assert r['split']==('probe' if rep<4 else 'evaluation')
                        for name,value in zip(('plus_a','plus_b','minus_a','minus_b'),ports.ravel()):
                            assert float(r[name])==value
                        checked_raw+=1;hits+=correct
                    s=state_index[block,case,budget,variant]
                    assert int(s['reads'])==16 and int(s['successes'])==hits
                    close(float(s['rate']),hits/16)
                    z=1.959963984540054;p=hits/16;den=1+z*z/16
                    center=(p+z*z/32)/den
                    half=z*math.sqrt(p*(1-p)/16+z*z/(4*16*16))/den
                    close(float(s['conditional_MC_wilson_lower']),max(0.,center-half))
                    close(float(s['conditional_MC_wilson_upper']),min(1.,center+half))
                    close(float(s['signed_transfer']),float(data['signed_transfer'][case,vi]))
                    close(float(s['unsigned_access']),float(data['unsigned_access'][case,vi]))
                incoming=float(data['both_pass'][bi,case,0,4:].mean())
                outgoing=float(data['both_pass'][bi,case,1,4:].mean())
                for name in ('always_incoming','always_outgoing','signed_transfer','unsigned_access','direct_read_probe'):
                    if name=='always_incoming':w=0.
                    elif name=='always_outgoing':w=1.
                    else:
                        if name=='direct_read_probe':
                            a,b=[float(data['both_pass'][bi,case,v,:4].sum()) for v in (0,1)]
                        else:
                            a,b=map(float,data[name][case,:2])
                        w=1. if b>a else 0. if b<a else .5
                    r=choice_index[block,case,budget,name]
                    assert float(r['weight_outgoing'])==w
                    close(float(r['incoming_evaluation_rate']),incoming);close(float(r['outgoing_evaluation_rate']),outgoing)
                    close(float(r['attained_rate']),(1-w)*incoming+w*outgoing)
                    close(float(r['sample_oracle_rate']),max(incoming,outgoing))
                    close(float(r['regret']),max(incoming,outgoing)-((1-w)*incoming+w*outgoing))
                    assert int(r['evaluation_reads_per_record'])==12
            for vi,variant in enumerate(cfg['variants']):
                r=block_index[block,budget,variant]
                observed=data['both_pass'][bi,:,vi]
                assert int(r['cases'])==count and int(r['reads'])==observed.size
                assert int(r['successes'])==int(observed.sum())
                close(float(r['rate']),float(observed.mean()))
    for bi,budget in enumerate(cfg['budgets']):
        for vi,variant in enumerate(cfg['variants']):
            rates=[float(all_data[b]['both_pass'][bi,:,vi].mean()) for b in cfg['blocks']]
            result=analysis['rate_summaries'][str(budget)][variant]
            summary_check(result,rates,cfg)
            joined=np.concatenate([all_data[b]['both_pass'][bi,:,vi] for b in cfg['blocks']])
            assert result['successes']==int(joined.sum()) and result['reads']==1024
            assert result['states_with_any_success']==int(joined.any(axis=1).sum())
            assert result['states_with_all_success']==int(joined.all(axis=1).sum())
        result=analysis['rewrite_effects'][str(budget)]
        differences=[float((all_data[b]['both_pass'][bi,:,1].astype(int)-all_data[b]['both_pass'][bi,:,0].astype(int)).mean()) for b in cfg['blocks']]
        summary_check(result,differences,cfg)
        joined=np.concatenate([all_data[b]['both_pass'][bi,:,:2] for b in cfg['blocks']])
        incoming,outgoing=joined[:,0],joined[:,1]
        assert result['outgoing_only']==int((outgoing & ~incoming).sum())
        assert result['incoming_only']==int((incoming & ~outgoing).sum())
        assert result['both_pass']==int((incoming & outgoing).sum())
        assert result['both_fail']==int((~incoming & ~outgoing).sum())
        assert result['paired_reads']==1024
        assert result['positive_blocks']==sum(x>0 for x in differences)
        assert result['negative_blocks']==sum(x<0 for x in differences)
        assert result['tied_blocks']==sum(x==0 for x in differences)
        for name,result in analysis['choices'][str(budget)].items():
            group=[r for r in choices if int(r['budget'])==budget and r['rule']==name]
            yields=[np.mean([float(r['attained_rate']) for r in group if int(r['block'])==b]) for b in cfg['blocks']]
            regrets=[np.mean([float(r['regret']) for r in group if int(r['block'])==b]) for b in cfg['blocks']]
            summary_check(result['yield_summary'],yields,cfg);summary_check(result['regret_summary'],regrets,cfg)
            assert result['state_count']==64
            assert result['outgoing_choices']==sum(float(r['weight_outgoing'])==1 for r in group)
            assert result['incoming_choices']==sum(float(r['weight_outgoing'])==0 for r in group)
            assert result['ties']==sum(float(r['weight_outgoing'])==.5 for r in group)
        for rival,result in analysis['signed_choice_minus_rivals'][str(budget)].items():
            signed=analysis['choices'][str(budget)]['signed_transfer']['yield_summary']['by_block']
            base=analysis['choices'][str(budget)][rival]['yield_summary']['by_block']
            summary_check(result,[signed[str(b)]-base[str(b)] for b in cfg['blocks']],cfg)
        if budget!=2048:
            for vi,variant in enumerate(cfg['variants'][:2]):
                differences=[float((all_data[b]['both_pass'][bi,:,vi].astype(int)-all_data[b]['both_pass'][1,:,vi].astype(int)).mean()) for b in cfg['blocks']]
                summary_check(analysis['time_effects_relative_to_native'][str(budget)][variant],differences,cfg)
    assert checked_raw==9216 and independent_contexts==8
    result=dict(status='PASS',at_utc=stamp(),native_read_rows=checked_raw,conditional_rate_rows=576,
        block_summary_rows=72,choice_case_rows=960,independent_contexts=8,independent_variants_per_context=3,
        independent_budgets_per_context=3,independent_evaluation_replicate=4,
        all_choices_and_block_bootstrap_tables_verified=True,reader_module_imported=False,analysis_module_imported=False,
        files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.suffix in ('.csv','.npz')})
    write(folder/'VERIFICATION.json',result)
    return result
