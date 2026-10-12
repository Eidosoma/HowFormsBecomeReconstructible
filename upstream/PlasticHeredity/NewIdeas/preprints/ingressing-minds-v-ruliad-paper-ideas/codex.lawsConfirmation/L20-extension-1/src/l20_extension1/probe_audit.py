"""D151 independent edit algebra, source pairing and complete physics replay."""
from dataclasses import asdict
import numpy as np
from . import component_audit as algebra,audit as metrics

prior=algebra.prior;physics=prior.physics;CFG=algebra.CFG
CASES=((0,'translated'),(0,'aligned'),(1,'translated'),(1,'aligned'))
EDITS=('attenuate','sham_plus','sham_minus')


def namespace(spec,life):
    cohort,index=spec
    assert type(index) is int and type(life) is int and life in range(4)
    assert spec in tuple(('d135',i) for i in range(75000,75008))+tuple(('d140',i) for i in range(78000,78008))+tuple(('former_test',i) for i in range(90000,90016))+(('disposable_dev',514240),('disposable_test',514240))
    if cohort in ('d135','d140'):return 'l20-extension1-diagnostics-v1:'+cohort,index-2000 if cohort=='d135' else index
    if cohort=='disposable_dev':return 'l20-extension1-diagnostics-v1:disposable',index
    return 'l20-extension1-heldout-v1:diagnostics:'+('heldout' if cohort=='former_test' else 'disposable'),index


def check_edit(candidate,plan,founders,guide,ci,ei):
    role,mode=CASES[ci];name=EDITS[ei];founder=founders[role].tobytes()
    selected,scores,selection=prior.prior.select(founder,guide)
    expected,detail=algebra.expected_edit(selected,role,name)
    np.testing.assert_allclose(prior.unpack(candidate),expected,atol=1e-12,rtol=0)
    error=algebra.invariants(selected,candidate,role,name,detail)
    physics.nested(plan,dict(role=role,writer=mode,edit=name,founder_sha256=prior.sha(founder),
        selected_sha256=prior.sha(selected),edited_sha256=prior.sha(candidate),identity=candidate==selected,**detail))
    return selected,selection,error


def check_life(raw,meta,source,source_meta,replay=False):
    spec=tuple(meta['spec']);life=meta['life'];tag,host=namespace(spec,life)
    shapes=dict(input=(4,3,2048),outgoing=(4,3,2048),terminal_packet=(4,3,2048),
        read_states=(4,3,5,3,16,16),write_states=(4,3,4,4,16,16),terminal_states=(4,3,4,3,16,16),
        last_scores=(4,3,2,16,16),shift=(4,3,2),record_values=(4,3,10),diagnostic_features=(4,3,6),
        founder_packets=(2,2048),guide=(2,16,16),selected_packets=(4,2048))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('input','outgoing','terminal_packet','founder_packets','selected_packets') else np.int64 if k=='shift' else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all(),k
    assert source_meta['life']==life and source_meta['index']==spec[1] and source_meta['tag']==tag
    assert source_meta['host']['index']==host
    for k in ('founder_packets','guide'):np.testing.assert_array_equal(raw[k],source[k])
    assert prior.sha(raw['guide'].astype('<f8').tobytes())==metrics.GUIDE_SHA
    tissue,ladder,bp=physics.parameters(source_meta['host']);entries=[];maxima=dict(read=0.,write=0.,terminal=0.,invariants=0.)
    for ci,(role,mode) in enumerate(CASES):
        cases=[]
        for ei,name in enumerate(EDITS):
            packet=raw['input'][ci,ei].tobytes();cell=meta['cells'][ci][ei]
            selected,selection,error=check_edit(packet,cell['plan'],raw['founder_packets'],raw['guide'],ci,ei)
            assert raw['selected_packets'][ci].tobytes()==selected==source['routed'][ci,1].tobytes()
            maxima['invariants']=max(maxima['invariants'],*error.values())
            random=lambda phase:physics.generator(tag,spec[1],life,'trial1:'+phase)
            read,reader=prior.read_trace(packet,tissue,ladder,bp,random('birth'),random('read'),CFG,replay=replay)
            np.testing.assert_array_equal(raw['read_states'][ci,ei,0],read[0])
            np.testing.assert_array_equal(raw['read_states'][ci,ei,0],source['read_states'][ci,1,0])
            if replay:maxima['read']=max(maxima['read'],physics.compare(raw['read_states'][ci,ei],read))
            shift=np.array(divmod(int(random('shift').integers(1,256)),16),np.int64)
            np.testing.assert_array_equal(raw['shift'][ci,ei],shift);np.testing.assert_array_equal(shift,source['shift'][ci,1] if 'shift' in source else np.asarray(source_meta['cycles'][ci][1]['writer']['shift'],np.int64))
            start=raw['read_states'][ci,ei,-1]
            writes,writer=prior.write_trace(start,tissue,ladder,random('write'),mode,shift,CFG,replay=replay)
            np.testing.assert_array_equal(raw['write_states'][ci,ei,0],np.concatenate((start,np.zeros((1,16,16)))))
            if replay:maxima['write']=max(maxima['write'],physics.compare(raw['write_states'][ci,ei],writes))
            outgoing=prior.packet(prior.project(np.tanh(raw['write_states'][ci,ei,-1,2])))
            assert raw['outgoing'][ci,ei].tobytes()==outgoing
            terminal_packet,scores,final_selection=prior.prior.select(outgoing,raw['guide'])
            assert raw['terminal_packet'][ci,ei].tobytes()==terminal_packet
            np.testing.assert_allclose(raw['last_scores'][ci,ei],scores,atol=1e-12,rtol=0)
            terminal,final=prior.read_trace(terminal_packet,tissue,ladder,bp,random('final_birth'),random('final_read'),CFG,times=CFG.times,replay=replay)
            np.testing.assert_array_equal(raw['terminal_states'][ci,ei,0],terminal[0])
            np.testing.assert_array_equal(terminal[0],source['terminal_states'][ci,1,0])
            if replay:maxima['terminal']=max(maxima['terminal'],physics.compare(raw['terminal_states'][ci,ei],terminal))
            np.testing.assert_allclose(raw['record_values'][ci,ei],algebra.measures(packet,selected,role),atol=1e-12,rtol=0)
            endpoint=np.r_[metrics.record_features(outgoing,role,raw['guide']),metrics.terminal_features(raw['terminal_states'][ci,ei,-1,0],role)]
            np.testing.assert_allclose(raw['diagnostic_features'][ci,ei],endpoint,atol=1e-12,rtol=0)
            cases.append(dict(plan=cell['plan'],initial_selector=selection,reader=reader,writer=writer,
                terminal_selector=final_selection,terminal_reader=final,trial=1))
        entries.append(cases)
    expected=dict(spec=list(spec),life=life,host=source_meta['host'],tag='l20-extension1-targeted-prediction-v1',
        physics_namespace=tag,config=asdict(CFG),cases=[list(c) for c in CASES],edits=list(EDITS),cells=entries,
        guide_sha256=metrics.GUIDE_SHA,carrier_bytes=2048,new_cycles=12,new_readers=24,new_writers=12,
        new_founders=0,new_main_lineages=0,diagnostic_to_lineage=False,source_state_given_to_reader=False,
        rerouted_after_edit=False,independent_new_noise=False,analyst_supplied_edit=True,prospective_evidence=False)
    physics.nested({k:v for k,v in meta.items() if k!='replay'},expected)
    return dict(passes=True,cycles=12,readers=24,writers=12,replayed_cycles=12 if replay else 0,
        max_abs=max(maxima.values()),maxima=maxima,new_actual_lineages=0,prospective_evidence=False)
