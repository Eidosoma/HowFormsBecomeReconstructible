"""Independent reconstruction, scoring, aggregation and flattened native audit."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import audit_reader
from common import arrays,equal,read,sha,stamp,write


def rng(parts):
    seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed))


def check_summary(result,values,cfg):
    values=np.array(values,float)
    assert abs(result['mean']-float(values.mean()))<2e-12
    for block,value in zip(cfg['blocks'],values):assert abs(result['by_block'][str(block)]-value)<2e-12
    random=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    means=values[random.integers(len(values),size=(cfg['bootstrap_replicates'],len(values)))].mean(axis=1)
    assert np.allclose(np.quantile(means,[.025,.975]),result['descriptive_block_bootstrap_95'],rtol=0,atol=2e-12)
    for label,test in (('positive_blocks',values>0),('tied_blocks',values==0),('negative_blocks',values<0)):
        assert result[label]==int(test.sum())


def prepared_check(data,block,cfg):
    n=len(data['founders']);w=np.frombuffer(data['packets'].tobytes(),dtype='<f8').reshape(n,9,2,16,16)
    donors=np.frombuffer(data['donor_packets'].tobytes(),dtype='<f8').reshape(n,2,2,16,16)
    ports=sorted(16*y+x for y0,x0 in ((7,1),(3,10),(11,10)) for y in range(y0,y0+2) for x in range(x0,x0+2))
    inputs=[16*y+x for y in (7,8) for x in (1,2)]
    eligible=np.array([i for i in range(256) if i not in ports])
    for case in range(n):
        mask=data['original_masks'][case];assert mask.sum()==24 and not mask.ravel()[ports].any()
        own=w[case,1].copy();same=own.copy();opposite=own.copy();aligned=[own.copy(),own.copy()];completed=own.copy()
        common=np.zeros((2,16,16),bool);signs=data['optimizer_signs'][case]
        assert np.all(abs(signs)==1) and np.all(signs[:2].reshape(2,256)[:,ports]==1)
        assert np.all(signs[2].ravel()[inputs]==1)
        for axis in (0,1):
            for y in range(16):
                for x in range(16):
                    yy,xx=(y,(x+1)%16) if axis==0 else ((y+1)%16,x)
                    if mask[y,x] or mask[yy,xx]:
                        assert w[case,1,axis,y,x]==0
                        if w[case,0,axis,y,x]!=0 and all(donors[case,d,axis,y,x]!=0 for d in (0,1)):
                            common[axis,y,x]=True;magnitude=abs(w[case,0,axis,y,x]);own[axis,y,x]=w[case,0,axis,y,x]
                            for d,target in enumerate((same,opposite)):
                                sign=1 if donors[case,d,axis,y,x]>0 else -1
                                target[axis,y,x]=magnitude*sign
                                aligned[d][axis,y,x]=magnitude*sign*signs[d,y,x]*signs[d,yy,xx]
                            completed[axis,y,x]=magnitude*signs[2,y,x]*signs[2,yy,xx]
        equal(common,data['common_edges'][case],'common support')
        for index,target in ((2,own),(3,same),(4,opposite),(5,aligned[0]),(6,aligned[1]),(7,completed)):
            equal(w[case,index],target,'independent graft construction')
            equal(abs(w[case,2]),abs(w[case,index]),'same unsigned record')
        for d in (0,1):
            changes=sum((w[case,3+d][common]>0)!=(w[case,5+d][common]>0))
            assert data['backup_sign_changes'][case,d]==changes
        assert not w[case,8].any()
        f,r=int(data['founders'][case]),int(data['recipients'][case])
        assert data['donor_founders'][case].tolist()==[f^2,f^3]
        for ri,rep in enumerate(cfg['replicates']):
            chosen=rng([cfg['random_namespace'],block,'injury',rep,f//2,r]).choice(eligible,24,replace=False)
            expected=np.zeros(256,bool);expected[chosen]=True
            equal(data['masks'][case,ri],expected.reshape(16,16),'independent mask')


def verify(folder,cfg,check_sources=True,check_dynamics=True):
    a=read(folder/'analysis.json')
    tables={}
    for name in ('reads','state_rates','block_summaries'):
        with (folder/(name+'.csv')).open() as f:tables[name]=list(csv.DictReader(f))
    rows={(int(r['block']),int(r['case']),r['regime'],r['variant'],int(r['replicate'])):r for r in tables['reads']}
    states={(int(r['block']),int(r['case']),r['regime'],r['variant']):r for r in tables['state_rates']}
    blocks={(int(r['block']),r['regime'],r['variant']):r for r in tables['block_summaries']}
    total=sum(cfg['cases_per_block']);assert len(rows)==len(tables['reads'])==total*9*(len(cfg['replicates'])+1)
    assert len(states)==len(tables['state_rates'])==total*9*2 and len(blocks)==len(tables['block_summaries'])==len(cfg['blocks'])*9*2
    prepared=None
    if check_sources:
        prepared=read(folder/'inputs/prepared/COMPLETE.json');assert prepared['independent_optimizer_checks']==192
        for path,digest in prepared['sources_sha256'].items():assert sha(path)==digest,path
    panel={};contexts=0
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        receipt=read(folder/f'worker_{block:06d}.json');assert receipt['original_native_replay_byte_equal']
        d=arrays(folder/f'reads_{block:06d}.npz',receipt['output_sha256']);panel[block]=d
        assert len(d['founders'])==n and int(d['block'])==block
        assert d['replicates'].tolist()==cfg['replicates'] and d['original_replicates'].tolist()==[0]
        if check_sources:
            name=f'cases_{block:06d}.npz';fixed=arrays(folder/'inputs/prepared'/name,prepared['outputs_sha256'][name])
            for key,value in fixed.items():equal(d[key],value,'frozen preparation '+key)
            source=arrays(Path(prepared['source_prepared'])/name)
            for key in ('founders','recipients','histories','original_masks','original_birth','original_end','original_mean_ports','donor_packets','donor_founders'):
                equal(d[key],source[key],'original source '+key)
            equal(d['packets'][:,[0,1,2,3,4,8]],source['packets'][:,[0,1,3,4,5,7]],'unaltered source controls')
        prepared_check(d,block,cfg)
        equal(d['control_birth'][:,0],d['birth'][:,0],'shared regime reset')
        for vi in range(2,8):
            equal(d['control_end'][:,1],d['control_end'][:,vi],'original mask endpoint identity')
            equal(d['control_port_windows'][:,:,1],d['control_port_windows'][:,:,vi],'original mask windows identity')
        for regime,prefix,reps,rep in (('fresh','',cfg['replicates'],4),('original','control_',[0],0)):
            equal(d[prefix+'port_windows'].mean(axis=0),d[prefix+'mean_ports'],'window averaging')
            equal(d[prefix+'mean_ports'][:,8,:,0],d[prefix+'mean_ports'][:,8,:,1],'erased cue identity')
            assert not (d[prefix+'both_pass'][:,8]|d[prefix+'opposite_pass'][:,8]).any()
            if check_dynamics:
                ri=reps.index(rep);mask=d['masks'][0,ri] if not prefix else d['original_masks'][0]
                independent=audit_reader.replay(d['packets'][0],mask,int(d['founders'][0]),int(d['recipients'][0]),block,rep,cfg)
                equal(independent['birth'],d[prefix+'birth'][0,ri],'flat birth')
                for field in ('end','mean_ports'):equal(independent[field][0],d[prefix+field][0,:,ri],'flat '+field)
                equal(independent['port_windows'][0],d[prefix+'port_windows'][:,0,:,ri],'flat windows');contexts+=1
            for case in range(n):
                rule=1 if int(d['founders'][case])%2==0 else -1
                for vi,variant in enumerate(cfg['variants']):
                    intended=0;opposite=0
                    for ri,rep in enumerate(reps):
                        p=d[prefix+'mean_ports'][case,vi,ri]
                        aligned=[rule*p[0,0],-rule*p[0,1],-rule*p[1,0],rule*p[1,1]]
                        margin=min(aligned);om=-max(aligned);good=margin>.25;other=om>.25
                        assert not (good and other);intended+=good;opposite+=other
                        for name,value in (('min_margin',margin),('opposite_margin',om),('both_pass',good),('opposite_pass',other)):
                            assert d[prefix+name][case,vi,ri]==value
                        row=rows[block,case,regime,variant,rep]
                        for key,value in (('intended',good),('opposite',other),('founder',d['founders'][case]),('recipient',d['recipients'][case]),('history',d['histories'][case])):assert int(row[key])==value
                        for key,value in [('margin',margin),('opposite_margin',om),*zip(('plus_a','plus_b','minus_a','minus_b'),p.ravel())]:assert float(row[key])==value
                    row=states[block,case,regime,variant]
                    for key,value in (('intended',intended),('opposite',opposite),('reads',len(reps)),('founder',d['founders'][case]),('recipient',d['recipients'][case]),('history',d['histories'][case])):assert int(row[key])==value
            for vi,variant in enumerate(cfg['variants']):
                row=blocks[block,regime,variant];x=d[prefix+'both_pass'][:,vi];y=d[prefix+'opposite_pass'][:,vi]
                for key,value in (('cases',n),('reads',x.size),('intended',x.sum()),('opposite',y.sum()),('neither',(~(x|y)).sum())):assert int(row[key])==value
    for regime,prefix in (('fresh',''),('original','control_')):
        for vi,variant in enumerate(cfg['variants']):
            for label,field in (('intended','both_pass'),('opposite','opposite_pass')):
                entry=a['rate_summaries'][regime][variant][label]
                values=[int(d[prefix+field][:,vi].sum())/d[prefix+field][:,vi].size for d in panel.values()]
                check_summary(entry,values,cfg)
                assert entry['successes']==sum(int(d[prefix+field][:,vi].sum()) for d in panel.values())
                assert entry['reads']==sum(d[prefix+field][:,vi].size for d in panel.values())
    weights={'mean_alignment_effect':{5:1,6:1,3:-1,4:-1},'same_alignment_effect':{5:2,3:-2},
             'opposite_alignment_effect':{6:2,4:-2},'aligned_minus_completion':{5:1,6:1,7:-2},
             'own_minus_aligned':{2:2,5:-1,6:-1},'completion_minus_outgoing':{7:2,1:-2},
             'aligned_minus_outgoing':{5:1,6:1,1:-2},'own_minus_completion':{2:2,7:-2}}
    for name,coefficients in weights.items():
        values=[sum(c*int(d['both_pass'][:,v].sum()) for v,c in coefficients.items())/(2*d['both_pass'][:,0].size) for d in panel.values()]
        check_summary(a['intended_effects'][name],values,cfg)
    values=[sum(c*int(d['opposite_pass'][:,v].sum()) for v,c in weights['mean_alignment_effect'].items())/(2*d['opposite_pass'][:,0].size) for d in panel.values()]
    check_summary(a['opposite_task_alignment_effect'],values,cfg)
    for label,left,right in (('same',5,3),('opposite',6,4)):
        x=np.concatenate([d['both_pass'][:,left] for d in panel.values()]);y=np.concatenate([d['both_pass'][:,right] for d in panel.values()])
        expected=dict(aligned_only=int((x&~y).sum()),unaligned_only=int((y&~x).sum()),both=int((x&y).sum()),neither=int((~x&~y).sum()),reads=int(x.size))
        assert a['paired_counts'][label]==expected
    assert a['primary_direction_observed']==(a['intended_effects']['mean_alignment_effect']['mean']>0)
    assert a['cases']==total and a['blocks']==len(cfg['blocks']) and a['read_contexts']==len(rows) and a['fitted_models']==0
    assert a['changed_backup_pairs']==sum(int((d['backup_sign_changes']>0).sum()) for d in panel.values())
    assert a['non_equivalent_pairs']==sum(int((~d['hybrid_gauge_equivalent']).sum()) for d in panel.values())
    result=dict(status='PASS',at_utc=stamp(),native_read_contexts=len(rows),native_audit_contexts=contexts,
        variants_per_native_audit=9,source_checks=check_sources,native_dynamics_checked=check_dynamics,
        independent_optimizer_checks_before_outcomes=192 if check_sources else 0,
        all_record_constructions_masks_windows_scores_tables_and_bootstraps_checked=True,
        same_lane_internal_verification=True,production_reader_imported=False,analysis_module_imported=False,
        files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.suffix in ('.npz','.csv')})
    write(folder/'VERIFICATION.json',result);return result
