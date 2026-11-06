"""Export every eligible retained boundary and cached prefix; no targets or fits."""
from pc_common import *
import time


def main():
    out = ROOT/'prepared'
    out.mkdir()
    (out/'cases').mkdir()
    require(sha(REPORT/'CLOSEOUT.json') == REPORT_SHA, 'E107 reporting closeout')
    reporting = read(REPORT/'CLOSEOUT.json')
    # Verify labels as an opaque file hash; only the later fitting stage reads them.
    for name in ('results_v1/weights.csv','results_v1/forecasts.csv','results_v1/outcomes.csv','results_v1/FIXED_BASELINE.json'):
        require(sha(REPORT/name) == reporting['files_sha256'][name], 'Qualified compact export changed')
    complete = read(RUN/'COMPLETE.json')
    require(sha(RUN/'OUTPUTS.json') == complete['output_manifest_sha256'], 'Original run output manifest')
    hashes = read(RUN/'OUTPUTS.json')['sha256']; consumed = {}
    def original(name):
        require(sha(RUN/name) == hashes[name], 'Original evidence changed: ' + name)
        consumed[name] = hashes[name]
        return RUN/name
    cohort = read(original('selection/COHORT.json'))
    require(cohort['blocks'] == list(range(80)) and len(cohort['rows']) == 319, 'All eligible retained sources')
    weight_map = {row_key(r):r for r in csv_rows(REPORT/'results_v1/weights.csv')}
    forecast_map = {(row_key(r),r['regime']):r for r in csv_rows(REPORT/'results_v1/forecasts.csv')}
    ff, _, _ = native()
    features, _ = cheap()
    fixed = read(ROOT/'comparator/MODELS.json')
    columns = fixed['models']['cheap_all']['columns']
    require(len(columns) == 70, 'Common cheap feature schema')
    families = {name:fixed['models'][name]['columns'] for name in ORDINARY}
    for family,q in [('direct8','q8'),('depth0','q0'),('depth1','q1'),('depth2','q2')]:
        families[family] = columns + [q]
    rows, xs, qs, ps, metadata = [], [], [], [], []
    feature_costs = []
    for block in range(80):
        block_rows = [r for r in cohort['rows'] if r['block'] == block]
        name = f'units/acquire/b{block}/boundary_{block:06d}_g14.npz'
        raw = ff.ev.load(original(name), hashes[name])
        for local,r in enumerate(block_rows):
            key = tuple(r['key']); h=features.HISTORIES.index(r['history']); f=r['founder']; v=r['recipient']
            packet = ff.e.native.decode(raw['outgoing'][h,f,v])
            require(hashlib.sha256(packet.tobytes()).hexdigest() == r['packet_sha256'], 'Source packet')
            tick=time.process_time(); wall=time.monotonic()
            values,groups = features.packet_body(packet,raw['end'][h,f,v],raw['masks'][f,v],
                                                 raw['mean_ports'][h,f,v],r['history'],r['rule'])
            feature_costs.append(dict(block=block,key=list(key),cpu_seconds=time.process_time()-tick,
                                      wall_seconds=time.monotonic()-wall))
            require(np.allclose([values[n] for n in features.B11],r['boundary'],rtol=0,atol=1e-12), 'All-cohort B11 interface')
            for regime in REGIMES:
                old={}; receipts={}
                for mode in ('direct64','successor32'):
                    base=f'units/measure/b{block}/case_{local:02d}_{regime}/{mode}'
                    receipt=read(original(base+'.json')); data=ff.ev.load(original(base+'.npz'),hashes[base+'.npz'])
                    require(receipt['raw_sha256']==hashes[base+'.npz'] and receipt['key']==r['key'] and
                            receipt['boundary']==r['boundary'] and receipt['regime']==regime and
                            receipt['stage']==OLD_STAGE and receipt['namespace']=='RDT_fresh_equal_read_v0_1/probe', 'Source measurement pairing')
                    require(data['packet'].tobytes()==packet.tobytes(), 'Source measurement packet')
                    old[mode],receipts[mode]=data,receipt
                s,d=old['successor32'],old['direct64']
                require(receipts['successor32']['audits']==[dict(probe=0,byte_exact=True,native_reads=2)], 'Cached first-writer audit')
                require(np.array_equal(s['successor_mask'][:20],d['direct_mask'][:20]) and
                        np.array_equal(s['successor_birth'][:20],d['direct_birth'][:20]), 'Paired terminal prefixes')
                case_id=f'b{block:03d}_i{local:02d}_{regime}'
                array_file='cases/'+case_id+'.npz'
                digest=save_arrays(out/array_file,dict(packet=packet,writer1_outgoing=s['writer_outgoing'][:20],
                    evaluation_mask=d['direct_mask'][:20],evaluation_birth=d['direct_birth'][:20]))
                q=[float(d['direct_passed'][:8].mean()),float(d['direct_passed'][:60].mean()),float(s['successor_passed'][:30].mean())]
                context,_=features.context(values,groups,24,regime)
                xs.append([context[n] for n in columns]);qs.append(q)
                fr=forecast_map[key,regime];ps.append([float(fr['p_'+n]) for n in LEGACY])
                w={name:float(weight_map[key][name]) for name in PROFILES}
                item=dict(case_id=case_id,key=list(key),block=block,fold=block%8,history=r['history'],
                    founder=f,recipient=v,rule=r['rule'],current_pass=r['current_pass'],regime=regime,
                    weights=w,array_file=array_file,array_sha256=digest,packet_sha256=r['packet_sha256'],
                    evaluation_forcing=receipts['direct64']['forcing'][:20],
                    writer1_source_sha256=receipts['successor32']['raw_sha256'])
                metadata.append(item)
                rows.append(dict(case_id=case_id,block=block,fold=block%8,history=r['history'],founder=f,recipient=v,
                    rule=r['rule'],current_pass=r['current_pass'],regime=regime,**w))
    require(len(rows)==638 and len(feature_costs)==319, 'Complete retained cohort')
    save_arrays(out/'FEATURES.npz',dict(cheap=np.array(xs),q=np.array(qs),legacy_probability=np.array(ps)))
    write(out/'CASES.json',metadata)
    write(out/'SCHEMA.json',dict(cheap_columns=columns,all_columns=columns+['q8','q0','q1','q2'],
        q_columns=['q8','q0','q1'],families=families,legacy_models=list(LEGACY),
        fit_weights='balanced packet weight divided by two regimes',outer_folds=8,
        fold_map={str(b):b%8 for b in range(80)},targets_excluded_from_features=True))
    write_csv(out/'cases.csv',rows)
    write(out/'FEATURE_COSTS.json',feature_costs)
    files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write(out/'SOURCES.json',dict(utc=utc(),scope='EXPOSED_RETAINED_DEVELOPMENT_INTERFACE',
        run_root=str(RUN.resolve()),old_output_manifest_sha256=complete['output_manifest_sha256'],
        e107_reporting_closeout_sha256=REPORT_SHA,original_files_sha256=consumed,
        output_files_sha256=files,records=319,cases=638,source_blocks=80,outer_folds=8,
        all_selected_sources_included=True,lossy_export=False,native_dtypes_preserved=True,
        target_outcomes_read=False,new_native_reads=0,new_fits=0,
        target_outcome_source=str(REPORT/'results_v1/outcomes.csv'),
        target_outcome_sha256=reporting['files_sha256']['results_v1/outcomes.csv']))
    print(json.dumps(dict(status='PREPARED',records=319,cases=638,blocks=80,original_files_verified=len(consumed),new_native_reads=0,new_fits=0)))


if __name__=='__main__':main()
