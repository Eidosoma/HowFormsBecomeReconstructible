"""Independent scores, aggregation, stratified uncertainty and native spot checks."""
import csv
import numpy as np
import audit_reader
from audit_cohort import check_records,check_lineage,decode
from common import arrays,equal,read,write,sha,stamp


def check_summary(result,values,cfg):
    values=np.array(values,float);assert len(values)==16
    assert abs(result['mean']-sum(values)/16)<2e-12
    for b,v in zip(cfg['blocks'],values):assert abs(result['by_block'][str(b)]-v)<2e-12
    random=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']));means=np.zeros(cfg['bootstrap_replicates'])
    for h in range(4):
        group=values[[i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h]]
        draw=random.integers(4,size=(cfg['bootstrap_replicates'],4));means+=group[draw].sum(axis=1)/16
    assert np.allclose(np.quantile(means,[.025,.975]),result['descriptive_stratified_block_bootstrap_95'],rtol=0,atol=2e-12)
    assert [result[k] for k in ('positive_blocks','tied_blocks','negative_blocks')]==[int((values>0).sum()),int((values==0).sum()),int((values<0).sum())]


def verify(folder,cfg,scientific=True):
    a=read(folder/'analysis.json');panel={};contexts=0
    tables={}
    for name in ('reads','block_summaries','resources'):
        with (folder/(name+'.csv')).open() as f:tables[name]=list(csv.DictReader(f))
    rows={(int(r['block']),int(r['case']),r['variant'],int(r['replicate'])):r for r in tables['reads']}
    blocks={(int(r['block']),r['variant']):r for r in tables['block_summaries']}
    resources={(int(r['block']),int(r['case'])):r for r in tables['resources']}
    assert len(rows)==len(tables['reads'])==8192 and len(blocks)==len(tables['block_summaries'])==64
    assert len(resources)==len(tables['resources'])==256
    for b in cfg['blocks']:
        receipt=read(folder/f'worker_{b:06d}.json');assert receipt['status']=='COMPLETE'
        d=arrays(folder/f'reads_{b:06d}.npz',receipt['reads_sha256']);panel[b]=d
        assert int(d['block'])==b and d['replicates'].tolist()==list(range(8))
        check_records(d,b,cfg)
        if scientific:
            acq=arrays(folder/f'acquisition_{b:06d}.npz',receipt['acquisition_sha256'])
            lineage=arrays(folder/f'lineage_{b:06d}.npz',receipt['lineage_sha256'])
            check_lineage(acq,lineage,b,cfg);contexts+=1
            equal(d['packets'][:,0],lineage['outgoing'][-1],'all unfiltered outgoing records')
            for case in range(16):
                rule=1 if case//4%2==0 else -1;p=lineage['mean_ports'][-1,case]
                passed=min(rule*p[0,0],-rule*p[0,1],-rule*p[1,0],rule*p[1,1])>.25
                assert d['pre_repair_pass'][case]==passed
            flat=audit_reader.replay(d['packets'][0],d['masks'][0,4],0,0,b,4,cfg)
            equal(flat['birth'],d['birth'][0,4],'flat assessment reset')
            for key in ('end','mean_ports'):equal(flat[key][0],d[key][0,:,4],'flat assessment '+key)
            equal(flat['port_windows'][0],d['port_windows'][:,0,:,4],'flat assessment windows');contexts+=1
        equal(d['port_windows'].mean(axis=0),d['mean_ports'],'endpoint window averaging')
        equal(d['mean_ports'][:,3,:,0],d['mean_ports'][:,3,:,1],'erased cue identity')
        assert not (d['both_pass'][:,3]|d['opposite_pass'][:,3]).any()
        for case in range(16):
            resource=resources[b,case]
            for key,field in [('history','histories'),('pre_repair_pass','pre_repair_pass'),('missing_edges','missing_edge_counts'),('shuffled_sign_changes','shuffled_sign_changes')]:assert int(resource[key])==d[field][case]
            for key,field in [('imputed_magnitude','imputed_magnitudes'),('added_abs_weight','added_abs_weight')]:assert float(resource[key])==d[field][case]
            rule=1 if int(d['founders'][case])%2==0 else -1
            for vi,name in enumerate(cfg['variants']):
                for ri,rep in enumerate(cfg['replicates']):
                    p=d['mean_ports'][case,vi,ri];aligned=[rule*p[0,0],-rule*p[0,1],-rule*p[1,0],rule*p[1,1]]
                    margin=min(aligned);om=-max(aligned);good=margin>.25;other=om>.25;assert not (good and other)
                    for key,v in [('both_pass',good),('opposite_pass',other),('min_margin',margin),('opposite_margin',om)]:assert d[key][case,vi,ri]==v
                    row=rows[b,case,name,rep]
                    for key,v in [('intended',good),('opposite',other),('pre_repair_pass',d['pre_repair_pass'][case]),('history',d['histories'][case]),('founder',case//4),('recipient',case%4)]:assert int(row[key])==v
                    for key,v in [('margin',margin),('opposite_margin',om),*zip(('plus_a','plus_b','minus_a','minus_b'),p.ravel())]:assert float(row[key])==v
        for vi,name in enumerate(cfg['variants']):
            row=blocks[b,name]
            assert int(row['history'])==cfg['history_by_block'][str(b)] and int(row['reads'])==128
            assert int(row['intended'])==d['both_pass'][:,vi].sum() and int(row['opposite'])==d['opposite_pass'][:,vi].sum()
    for vi,name in enumerate(cfg['variants']):
        for label,field in [('intended','both_pass'),('opposite','opposite_pass')]:
            summary=a['rates'][name][label];check_summary(summary,[int(d[field][:,vi].sum())/128 for d in panel.values()],cfg)
            assert summary['reads']==2048 and summary['successes']==sum(int(d[field][:,vi].sum()) for d in panel.values())
    for name,right in [('completion_minus_outgoing',0),('completion_minus_shuffled',2)]:
        values=[(int(d['both_pass'][:,1].sum())-int(d['both_pass'][:,right].sum()))/128 for d in panel.values()]
        check_summary(a['contrasts'][name],values,cfg)
    check_summary(a['opposite_task_primary_effect'],[(int(d['opposite_pass'][:,1].sum())-int(d['opposite_pass'][:,0].sum()))/128 for d in panel.values()],cfg)
    for name,right in [('completion_vs_outgoing',0),('completion_vs_shuffled',2)]:
        tally=[0,0,0,0]
        for d in panel.values():
            for x,y in zip(d['both_pass'][:,1].ravel(),d['both_pass'][:,right].ravel()):tally[0 if x and not y else 1 if y and not x else 2 if x else 3]+=1
        assert a['paired_counts'][name]==dict(zip(('left_only','right_only','both','neither','reads'),tally+[2048]))
    for name,flag in [('body_pass',True),('body_fail',False)]:
        count=0;successes=np.zeros(4,int)
        for d in panel.values():
            for case in range(16):
                if bool(d['pre_repair_pass'][case])==flag:count+=1;successes+=d['both_pass'][case].sum(axis=1)
        s=a['body_subgroups'][name];assert s['records']==count and s['reads_per_variant']==count*8
        for vi,v in enumerate(cfg['variants']):
            assert s['successes'][v]==int(successes[vi])
            assert s['rates'][v]==(float(successes[vi]/(count*8)) if count else None)
        assert s['completion_minus_outgoing']==(float((successes[1]-successes[0])/(count*8)) if count else None)
    for h,name in enumerate(cfg['histories']):
        successes=np.zeros(4,int)
        for b,d in panel.items():
            if cfg['history_by_block'][str(b)]==h:successes+=d['both_pass'].sum(axis=(0,2))
        s=a['history_summaries'][name];assert s['blocks']==4 and s['records']==64
        for vi,v in enumerate(cfg['variants']):assert s['rates'][v]==successes[vi]/512
        assert s['completion_minus_outgoing']==(successes[1]-successes[0])/512
    assert a['primary_direction_observed']==(a['contrasts']['completion_minus_outgoing']['mean']>0)
    assert a['blocks']==16 and a['records']==256 and a['read_contexts']==8192 and a['fitted_parameters']==0
    result=dict(status='PASS',at_utc=stamp(),scientific=scientific,records=256,read_contexts=8192,native_audit_contexts=contexts,
        independent_optimizer_checks_during_preparation=256 if scientific else 0,independent_captures=3584 if scientific else 0,
        same_lane_internal_verification=True,analysis_module_imported=False,primary_assessment_reader_imported=False,
        development_mask_generator_shared=True,
        files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.suffix in ('.npz','.csv')})
    write(folder/'VERIFICATION.json',result);return result
