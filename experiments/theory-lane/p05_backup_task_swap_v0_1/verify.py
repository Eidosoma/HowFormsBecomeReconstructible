"""Independent donor construction, dual scoring, tables and flat-reader audit."""
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import audit_reader
from common import arrays,equal,read,sha,stamp,write


def rng(parts):
    seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed))


def close(x,y):
    assert math.isfinite(x) and math.isfinite(y) and abs(x-y)<2e-12,(x,y)


def summary_check(result,values,cfg):
    close(result['mean'],sum(values)/len(values))
    for b,v in zip(cfg['blocks'],values):close(result['by_block'][str(b)],v)
    r=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    boot=np.array(values)[r.integers(len(values),size=(cfg['bootstrap_replicates'],len(values)))].mean(axis=1)
    for x,y in zip(result['descriptive_block_bootstrap_95'],np.quantile(boot,[.025,.975])):close(x,float(y))
    assert result['positive_blocks']==sum(v>0 for v in values)
    assert result['tied_blocks']==sum(v==0 for v in values)
    assert result['negative_blocks']==sum(v<0 for v in values)


def prepared_check(d,block,cfg):
    n=len(d['founders']);v=len(cfg['variants']);r=len(cfg['replicates'])
    w=np.frombuffer(d['packets'].tobytes(),dtype='<f8').reshape(n,v,2,16,16)
    donors=np.frombuffer(d['donor_packets'].tobytes(),dtype='<f8').reshape(n,2,2,16,16)
    ports={(y,x) for yy,xx in ((7,1),(3,10),(11,10)) for y in range(yy,yy+2) for x in range(xx,xx+2)}
    eligible=np.array([16*y+x for y in range(16) for x in range(16) if (y,x) not in ports])
    assert d['masks'].shape==(n,r,16,16)
    for case in range(n):
        f=int(d['founders'][case]);rec=int(d['recipients'][case]);h=int(d['histories'][case])
        expected_pair=2*(1-f//2)
        assert d['donor_founders'][case].tolist()==[expected_pair+f%2,expected_pair+1-f%2]
        mask=d['original_masks'][case];assert mask.sum()==24 and not any(mask[y,x] for y,x in ports)
        full=w[case,0].copy();own=w[case,1].copy();same=own.copy();opp=own.copy();scramble=own.copy()
        e=np.zeros((2,16,16),bool);k=e.copy();indices=[]
        for plane in range(2):
            for y in range(16):
                for x in range(16):
                    yy,xx=(y,(x+1)%16) if plane==0 else ((y+1)%16,x)
                    if mask[y,x] or mask[yy,xx]:
                        assert w[case,1,plane,y,x]==0.
                        if w[case,0,plane,y,x]!=0:
                            e[plane,y,x]=True
                            if donors[case,0,plane,y,x]!=0 and donors[case,1,plane,y,x]!=0:
                                k[plane,y,x]=True;indices.append(plane*256+y*16+x)
                                own[plane,y,x]=w[case,0,plane,y,x]
                                same[plane,y,x]=abs(w[case,0,plane,y,x])*(1. if donors[case,0,plane,y,x]>0 else -1.)
                                opp[plane,y,x]=abs(w[case,0,plane,y,x])*(1. if donors[case,1,plane,y,x]>0 else -1.)
                    else:full[plane,y,x]=w[case,1,plane,y,x]
        signs=np.array([1. if w[case,0].flat[j]>0 else -1. for j in indices])
        shuffled=rng([cfg['random_namespace'],block,'backup_signs',h,f,rec]).permutation(signs)
        for j,s in zip(indices,shuffled):scramble.flat[j]=abs(w[case,0].flat[j])*s
        for vi,expected in [(2,full),(3,own),(4,same),(5,opp),(6,scramble),(8,donors[case,0]),(9,donors[case,1])]:equal(expected,w[case,vi],'independent record construction')
        equal(e,d['backup_edges'][case]);equal(k,d['common_edges'][case]);assert not w[case,7].any()
        for vi in (4,5,6):equal(abs(w[case,3]),abs(w[case,vi]),'matched support and magnitudes')
        assert d['backup_nonzero_count'][case]==e.sum() and d['common_nonzero_count'][case]==len(indices)
        assert d['scramble_sign_changes'][case]==(signs!=shuffled).sum()
        for key,left,right in [('donor_sign_differences',donors[case,0],donors[case,1]),('same_sign_changes',w[case,0],donors[case,0]),('opposite_sign_changes',w[case,0],donors[case,1])]:
            assert d[key][case]==sum((left.flat[j]>0)!=(right.flat[j]>0) for j in indices)
        total=sum(abs(w[case,0].flat[j]) for j in np.flatnonzero(e))
        fraction=sum(abs(w[case,0].flat[j]) for j in indices)/total if total else 0.
        close(float(d['common_magnitude_fraction'][case]),fraction)
        for ri,rep in enumerate(cfg['replicates']):
            chosen=rng([cfg['random_namespace'],block,'injury',rep,f//2,rec]).choice(eligible,cfg['injury_cells'],replace=False)
            expected=np.zeros(256,bool);expected[chosen]=True
            equal(expected.reshape(16,16),d['masks'][case,ri],'independent fresh mask')
    for prefix in ('','control_'):
        for vi in (4,5,6):equal(d[prefix+'unsigned_access'][:,3],d[prefix+'unsigned_access'][:,vi],'unsigned identity')
    for key in ('signed_transfer','opposite_signed_transfer','unsigned_access'):
        for vi in (2,3,4,5,6):equal(d['control_'+key][:,1],d['control_'+key][:,vi],'original transport identity')


def sources_check(folder,cfg,data):
    p=read(folder/'inputs/prepared/COMPLETE.json')
    for path,digest in p['sources_sha256'].items():assert sha(path)==digest,path
    for b,d in data.items():
        raw={}
        for label,path in p['donor_source_runs'].items():
            with np.load(Path(path)/f'boundary_{b:06d}_g13.npz',allow_pickle=False) as z:raw[label]=z['outgoing']
        old=arrays(Path(p['recipient_source_run'])/'inputs/prepared'/f'cases_{b:06d}.npz')
        for key in ('founders','recipients','histories','original_masks','original_birth','original_end','original_mean_ports'):equal(d[key],old[key],key)
        equal(d['packets'][:,:2],old['packets'][:,:2],'source input records')
        equal(d['packets'][:,2],old['packets'][:,3],'source full hybrid')
        for i,(h,f,rec) in enumerate(zip(d['histories'],d['founders'],d['recipients'])):
            label,history={0:('spacing',0),1:('pulse',2),2:('spacing',1),3:('spacing',2)}[int(h)]
            first=2*(1-int(f)//2)+int(f)%2;second=2*(1-int(f)//2)+1-int(f)%2
            equal(d['packets'][i,0],raw[label][history,f,rec],'independent own selection')
            equal(d['donor_packets'][i,0],raw[label][history,first,rec],'independent same donor')
            equal(d['donor_packets'][i,1],raw[label][history,second,rec],'independent opposite donor')
    return len(p['sources_sha256'])


def pair_check(result,data,first,second,field,cfg):
    values=[];counts=dict(paired_reads=0,first_only=0,second_only=0,both_pass=0,both_fail=0)
    for b in cfg['blocks']:
        x=data[b][field][:,first].ravel();y=data[b][field][:,second].ravel()
        values.append(sum(int(i)-int(j) for i,j in zip(x,y))/len(x));counts['paired_reads']+=len(x)
        for key,z in [('first_only',x&~y),('second_only',y&~x),('both_pass',x&y),('both_fail',~x&~y)]:counts[key]+=int(z.sum())
    summary_check(result,values,cfg)
    for k,v in counts.items():assert result[k]==v,(k,result[k],v)


def verify(folder,cfg,check_sources=True):
    a=read(folder/'analysis.json');tables={}
    for name in ('reads','state_rates','block_summaries','rival_reads','rival_blocks'):
        with (folder/(name+'.csv')).open() as f:tables[name]=list(csv.DictReader(f))
    ix={(int(r['block']),int(r['local_case']),r['regime'],r['variant'],int(r['replicate'])):r for r in tables['reads']}
    sx={(int(r['block']),int(r['local_case']),r['regime'],r['variant']):r for r in tables['state_rates']}
    bx={(int(r['block']),r['regime'],r['variant']):r for r in tables['block_summaries']}
    rx={(int(r['block']),int(r['local_case']),int(r['replicate']),r['rule']):r for r in tables['rival_reads']}
    rb={(int(r['block']),r['rule']):r for r in tables['rival_blocks']}
    total=sum(cfg['cases_per_block']);nr=len(cfg['replicates']);nv=len(cfg['variants']);nb=len(cfg['blocks']);nc=len(cfg['original_replicates'])
    assert len(ix)==len(tables['reads'])==total*nv*(nr+nc)
    assert len(sx)==len(tables['state_rates'])==total*nv*2
    assert len(bx)==len(tables['block_summaries'])==nb*nv*2
    assert len(rx)==len(tables['rival_reads'])==total*nr*3
    assert len(rb)==len(tables['rival_blocks'])==nb*3
    all_data={};contexts=0;scored=0;rival_expected={}
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        receipt=read(folder/f'worker_{block:06d}.json');assert receipt['status']=='COMPLETE' and receipt['original_native_replay_byte_equal']
        d=arrays(folder/f'reads_{block:06d}.npz',receipt['output_sha256']);all_data[block]=d
        assert len(d['founders'])==n and int(d['block'])==block
        assert d['replicates'].tolist()==cfg['replicates'] and d['original_replicates'].tolist()==cfg['original_replicates'] and d['budgets'].tolist()==cfg['budgets']
        prepared_check(d,block,cfg);equal(d['control_birth'][:,0],d['birth'][:,0],'paired regime birth')
        for vi in (2,3,4,5,6):
            equal(d['control_end'][:,1],d['control_end'][:,vi],'masked hybrid identity')
            equal(d['control_port_windows'][:,:,1],d['control_port_windows'][:,:,vi],'masked hybrid window identity')
        for regime,prefix,reps,audit_rep in [('original','control_',cfg['original_replicates'],0),('fresh','',cfg['replicates'],4)]:
            equal(d[prefix+'port_windows'].mean(axis=0),d[prefix+'mean_ports'],'raw averaging')
            equal(d[prefix+'mean_ports'][:,7,:,0],d[prefix+'mean_ports'][:,7,:,1],'erased cue identity')
            assert not (d[prefix+'both_pass'][:,7]|d[prefix+'opposite_pass'][:,7]).any()
            ri=reps.index(audit_rep);mask=d['original_masks'][0] if prefix else d['masks'][0,ri]
            audit=audit_reader.replay(d['packets'][0],mask,int(d['founders'][0]),int(d['recipients'][0]),block,audit_rep,cfg)
            equal(audit['birth'],d[prefix+'birth'][0,ri],'independent birth')
            for field in ('end','mean_ports'):equal(audit[field][0],d[prefix+field][0,:,ri],'independent '+field)
            equal(audit['port_windows'][0],d[prefix+'port_windows'][:,0,:,ri],'independent windows')
            diag=audit_reader.transfer(d['packets'][0],mask,int(d['founders'][0]),cfg['transfer_steps'])
            oppdiag=audit_reader.transfer(d['packets'][0],mask,int(d['founders'][0])^1,cfg['transfer_steps'])
            for col,field in [(0,'signed_transfer'),(1,'unsigned_access')]:np.testing.assert_allclose(diag[:,col],d[prefix+field][0,:,ri],rtol=0,atol=1e-13)
            np.testing.assert_allclose(oppdiag[:,0],d[prefix+'opposite_signed_transfer'][0,:,ri],rtol=0,atol=1e-13);contexts+=1
            for case in range(n):
                rule=1. if d['founders'][case]%2==0 else -1.
                for vi,variant in enumerate(cfg['variants']):
                    hits=0;otherhits=0
                    for ri,rep in enumerate(reps):
                        ports=d[prefix+'mean_ports'][case,vi,ri];aligned=[rule*ports[0,0],-rule*ports[0,1],-rule*ports[1,0],rule*ports[1,1]]
                        margin=min(aligned);opposite=-max(aligned);good=margin>cfg['reader']['margin'];other=opposite>cfg['reader']['margin']
                        assert not (good and other);hits+=good;otherhits+=other;scored+=1
                        for field,val in [('min_margin',margin),('opposite_margin',opposite),('both_pass',good),('opposite_pass',other)]:assert d[prefix+field][case,vi,ri]==val
                        row=ix[block,case,regime,variant,rep]
                        for key,val in [('success',good),('opposite_success',other),('founder',d['founders'][case]),('recipient',d['recipients'][case])]:assert int(row[key])==val
                        assert row['history']==cfg['histories'][d['histories'][case]]
                        for key,val in [('margin',margin),('opposite_margin',opposite),*zip(('plus_a','plus_b','minus_a','minus_b'),ports.ravel())]:assert float(row[key])==val
                        for field in ('signed_transfer','unsigned_access'):assert float(row[field])==d[prefix+field][case,vi,ri]
                    row=sx[block,case,regime,variant];rr=len(reps)
                    assert int(row['successes'])==hits and int(row['opposite_successes'])==otherhits and int(row['reads'])==rr
                    assert int(row['founder'])==d['founders'][case] and int(row['recipient'])==d['recipients'][case] and row['history']==cfg['histories'][d['histories'][case]]
                    close(float(row['rate']),hits/rr);close(float(row['opposite_rate']),otherhits/rr)
                    for count,pre in [(hits,''),(otherhits,'opposite_')]:
                        z=1.959963984540054;p=count/rr;den=1+z*z/rr;center=(p+z*z/(2*rr))/den;half=z*math.sqrt(p*(1-p)/rr+z*z/(4*rr*rr))/den
                        close(float(row[pre+'conditional_MC_lower']),max(0.,center-half));close(float(row[pre+'conditional_MC_upper']),min(1.,center+half))
            for vi,variant in enumerate(cfg['variants']):
                row=bx[block,regime,variant];x=d[prefix+'both_pass'][:,vi];y=d[prefix+'opposite_pass'][:,vi]
                for key,val in [('cases',n),('reads',x.size),('successes',x.sum()),('opposite_successes',y.sum()),('neither',(~(x|y)).sum())]:assert int(row[key])==val
                close(float(row['rate']),float(x.mean()));close(float(row['opposite_rate']),float(y.mean()))
        for rule in ('signed_transport','task_label','unsigned_tie'):
            rewards=[];discordant=0;credit=0.;ties=0
            for case in range(n):
                for ri,rep in enumerate(cfg['replicates']):
                    q=float(d['signed_transfer'][case,4,ri]-d['signed_transfer'][case,5,ri])
                    pref=(1 if q>0 else -1 if q<0 else 0) if rule=='signed_transport' else 1 if rule=='task_label' else 0
                    delta=int(d['both_pass'][case,4,ri])-int(d['both_pass'][case,5,ri]);reward=pref*delta
                    cr=(.5 if pref==0 else float(pref==delta)) if delta!=0 else 0.
                    rewards.append(reward);discordant+=delta!=0;credit+=cr;ties+=pref==0
                    row=rx[block,case,rep,rule]
                    for key,val in [('preference',pref),('paired_success_difference',delta),('reward',reward),('discordant',delta!=0)]:assert int(row[key])==val
                    close(float(row['signed_transfer_difference']),q);close(float(row['discordant_credit']),cr)
            mean=sum(rewards)/len(rewards);accuracy=credit/discordant if discordant else None;rival_expected[block,rule]=(mean,discordant,credit,ties,accuracy)
            row=rb[block,rule]
            for key,val in [('paired_reads',n*nr),('discordant_reads',discordant),('predicted_ties',ties)]:assert int(row[key])==val
            close(float(row['reward']),mean);close(float(row['discordant_credit']),credit)
            if accuracy is None:assert row['discordant_accuracy']==''
            else:close(float(row['discordant_accuracy']),accuracy)
    bound_sources=sources_check(folder,cfg,all_data) if check_sources else 0
    for regime,prefix in [('original','control_'),('fresh','')]:
        for vi,variant in enumerate(cfg['variants']):
            for label,field in [('intended','both_pass'),('opposite','opposite_pass')]:
                result=a['rate_summaries'][regime][variant][label]
                summary_check(result,[float(all_data[b][prefix+field][:,vi].mean()) for b in cfg['blocks']],cfg)
                joined=np.concatenate([d[prefix+field][:,vi] for d in all_data.values()])
                assert result['reads']==joined.size and result['successes']==joined.sum()
                assert result['cases_with_any_success']==joined.any(axis=1).sum() and result['cases_with_all_success']==joined.all(axis=1).sum()
    for name,x,y in [('same_minus_opposite',4,5),('own_minus_same',3,4),('own_minus_opposite',3,5),('own_minus_scrambled',3,6),('same_minus_outgoing',4,1),('full_own_minus_common',2,3),('full_own_minus_incoming',2,0),('full_own_minus_outgoing',2,1)]:pair_check(a['fresh_intended_effects'][name],all_data,x,y,'both_pass',cfg)
    pair_check(a['opposite_task_replacement'],all_data,5,4,'opposite_pass',cfg)
    for rule,result in a['rivals'].items():
        entries=[rival_expected[b,rule] for b in cfg['blocks']];summary_check(result['reward'],[e[0] for e in entries],cfg)
        disc=sum(e[1] for e in entries);credit=sum(e[2] for e in entries)
        assert result['paired_reads']==total*nr and result['discordant_reads']==disc and result['predicted_ties']==sum(e[3] for e in entries)
        close(result['discordant_credit'],credit)
        if disc:close(result['pooled_discordant_accuracy'],credit/disc)
        else:assert result['pooled_discordant_accuracy'] is None
        for b,e in zip(cfg['blocks'],entries):
            assert result['by_block_discordant_reads'][str(b)]==e[1]
            if e[4] is None:assert result['by_block_discordant_accuracy'][str(b)] is None
            else:close(result['by_block_discordant_accuracy'][str(b)],e[4])
    summary_check(a['signed_reward_minus_task_label'],[rival_expected[b,'signed_transport'][0]-rival_expected[b,'task_label'][0] for b in cfg['blocks']],cfg)
    assert a['primary_direction_observed']==(a['fresh_intended_effects']['same_minus_opposite']['mean']>0)
    assert a['secondary_replacement_direction_observed']==(a['opposite_task_replacement']['mean']>0)
    for key,value in a['backup_totals'].items():assert value==sum(int(d[key].sum()) for d in all_data.values())
    assert a['identical_donor_cases']==sum(int((d['donor_sign_differences']==0).sum()) for d in all_data.values())
    assert a['zero_common_cases']==sum(int((d['common_nonzero_count']==0).sum()) for d in all_data.values())
    assert a['enrolled_cases']==total and a['blocks']==nb and a['read_trials']==scored and a['fitted_models']==0
    result=dict(status='PASS',at_utc=stamp(),native_read_rows=scored,conditional_rate_rows=len(sx),block_summary_rows=len(bx),rival_read_rows=len(rx),rival_block_rows=len(rb),
        independent_contexts=contexts,independent_variants_per_context=nv,source_bindings_checked=bound_sources,
        all_donor_selections_checked=check_sources,all_record_constructions_checked=True,all_masks_and_permutations_regenerated=True,
        all_raw_windows_and_dual_scores_checked=True,all_tables_and_bootstraps_checked=True,
        production_reader_imported_by_verifier=False,analysis_module_imported_by_verifier=False,
        files_sha256={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.suffix in ('.csv','.npz')})
    write(folder/'VERIFICATION.json',result);return result
