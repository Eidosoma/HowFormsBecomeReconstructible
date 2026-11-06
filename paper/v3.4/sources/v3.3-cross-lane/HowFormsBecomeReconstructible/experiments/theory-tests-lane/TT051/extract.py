"""Verify and compact the existing eight-block probe-development panel."""
from io_utils import *
import features, time

def main():
    start=time.monotonic();inputs={};copies=ROOT/'inputs';copies.mkdir()
    training=THEORY/'rdt_cheap_probe_transfer_v0_1/context'
    receipt=read(training/'TRAINING_AUDIT.json');assert receipt['status']=='PASS'
    p=training/'TRAINING_ROWS.json';assert sha(p)==receipt['training']['training_rows_sha256']
    rows=read(p)['rows'];assert len(rows)==768 and {r['block'] for r in rows}==set(BLOCKS)
    assert {r['injury'] for r in rows}=={12,24,36} and {r['regime'] for r in rows}=={'matched','independent'}
    inputs[str(p)]=sha(p);inputs[str(training/'TRAINING_AUDIT.json')]=sha(training/'TRAINING_AUDIT.json')
    source=THEORY/'rdt_fresh_equal_read_v0_1/runs/scientific_v1'
    expected=read(source/'OUTPUTS.json')['sha256'];done=read(source/'COMPLETE.json')
    assert sha(source/'OUTPUTS.json')==done['output_manifest_sha256']
    inputs.update({str(source/n):sha(source/n) for n in ('COMPLETE.json','OUTPUTS.json')})
    cache={};feature_seconds={};maximum_b11_error=0.;packet_keys=sorted({tuple(r['key']) for r in rows})
    assert len(packet_keys)==32
    for block in BLOCKS:
        folder=source/f'units/acquire/b{block}';commit=read(folder/'COMMIT.json')
        assert sha(folder/'COMMIT.json')==expected[f'units/acquire/b{block}/COMMIT.json']
        inputs[str(folder/'COMMIT.json')]=sha(folder/'COMMIT.json');raw={}
        for g in (12,13,14):
            name=f'boundary_{block:06d}_g{g:02d}.npz';assert sha(folder/name)==commit['sha256'][name]
            inputs[str(folder/name)]=sha(folder/name);raw[g]=arrays(folder/name)
        enrolled={tuple(r['key']):r for r in commit['payload']['rows']}
        for key in [k for k in packet_keys if k[0]==block]:
            _,history,f,r=key;h=HISTORIES.index(history);rule=1 if f%2==0 else -1
            values={};groups={};t=time.process_time()
            for g in (14,13,12):
                a=raw[g];v,gr=features.packet_body(a['outgoing'][h,f,r],a['end'][h,f,r],a['masks'][f,r],a['mean_ports'][h,f,r],history,rule)
                if g==14:
                    values=v;groups=gr
                    err=float(np.max(abs(np.array([v[k] for k in features.B11])-np.array(enrolled[key]['boundary']))))
                    assert err<1e-12;maximum_b11_error=max(maximum_b11_error,err)
                    assert hashlib.sha256(features.decode(a['outgoing'][h,f,r]).tobytes()).hexdigest()==enrolled[key]['packet_sha256']
                else:
                    prefix='parent' if g==13 else 'grandparent'
                    for name in features.ANCESTOR:values[prefix+'_'+name]=v[name];groups[prefix+'_'+name]=prefix
            feature_seconds[str(key)]=time.process_time()-t;cache[key]=(values,groups)
    matrix=[];targets=[];weights=[];ids=[];common_columns=None;common_groups=None
    for row in rows:
        key=tuple(row['key']);v,gr=cache[key];v,gr=features.context(v,gr,row['injury'],row['regime'])
        # Ancestors are stored in a separate column group; cheap families cannot select them.
        names=list(v)
        if common_columns is None:common_columns=names;common_groups=gr
        assert names==common_columns and gr==common_groups
        assert max(abs(v[k]-b) for k,b in zip(features.B11,row['boundary']))<1e-12
        assert int(v['current_pass'])==row['original_pass']
        assert row['outcome'] in (0,1) and row['target_replicate'] in range(4)
        matrix.append([v[k] for k in names]);targets.append(row['outcome']);weights.append(1/(2*row['class_packets']*4))
        ids.append({k:row[k] for k in ('block','key','injury','regime','original_pass','target_replicate','class_packets')})
    identities={(r['injury'],r['regime'],tuple(r['key']),r['target_replicate']) for r in rows}
    assert len(identities)==768
    schema=dict(version='TT051_boundary_v1',all_columns=common_columns,groups=common_groups,
        families={f:features.columns(common_groups,f) for f in features.FAMILIES},
        boundary_order=list(features.B11),target='g33 task expression after18 exact rewrites fromg14',
        native_probe_reads=0,signed_transfer_iterations=64,unsigned_transfer_iterations=64,
        additional_ancestor_iterations_per_boundary=128,ancestor_analysis_separate=True)
    data=dict(X=np.array(matrix),y=np.array(targets,float),weights=np.array(weights),
        blocks=np.array([r['block'] for r in rows]),injury=np.array([r['injury'] for r in rows]),
        noise=np.array([r['regime']=='independent' for r in rows]),current_pass=np.array([r['original_pass'] for r in rows]))
    for b in BLOCKS:
        for injury in (12,24,36):
            for noise in (False,True):
                m=(data['blocks']==b)&(data['injury']==injury)&(data['noise']==noise)
                assert abs(data['weights'][m].sum()-1)<1e-14
    save(ROOT/'DATA.npz',data);write(ROOT/'IDENTITIES.json',ids);write(ROOT/'FEATURE_SCHEMA.json',schema)
    old=LANE/'TT008/FROZEN_MODELS.json';registration=read(LANE/'TT008/REGISTRATION.json')
    assert sha(old)==registration['models_sha256'];write(ROOT/'TT008_FIXED_REFERENCE.json',read(old)['candidate'])
    inputs[str(old)]=sha(old);inputs[str(LANE/'TT008/REGISTRATION.json')]=sha(LANE/'TT008/REGISTRATION.json')
    write(ROOT/'SOURCE_MANIFEST.json',dict(utc=now(),inputs=inputs,development_blocks=BLOCKS,source_packets=32,rows=768,
        forbidden_outcomes_used=False,TT008_test_outcomes_used=False,E107_outcomes_used=False,
        maximum_B11_reproduction_error=maximum_b11_error,feature_cpu_seconds=sum(feature_seconds.values()),
        feature_cpu_seconds_by_packet=feature_seconds,feature_boundaries_per_packet=3,
        native_reads=0,seconds=time.monotonic()-start))
    print(json.dumps(dict(status='EXTRACTED',rows=768,packets=32,columns=len(common_columns),
        family_columns={k:len(v) for k,v in schema['families'].items()},B11_error=maximum_b11_error,
        seconds=time.monotonic()-start)))

if __name__=='__main__':main()
