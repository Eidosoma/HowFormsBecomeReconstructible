"""New parents, selected repair controls and independent physical replay."""
from dataclasses import asdict
import hashlib
import math
from pathlib import Path
import time

import numpy as np
from common import *
import analysis
from design import plan, average_name


def aliases(raw, built, cfg):
    count=0; partner=built['partners']
    for packet in ('common','residual'):
        for prefix in ('','capture__'):
            live,fixed=[raw[f'{prefix}{packet}__own__{mode}'] for mode in ('live','fixed')]
            for key in KEYS:
                ref.exact(live['s1_'+key],fixed['s1_'+key],'first-step equality');count+=1
        fixed=raw[f'capture__{packet}__own__fixed']
        off=raw[f'capture__{packet}__own__writer_off']
        held=raw[f'capture__{packet}__own__reference_held']
        for step in cfg.times:
            for key in ('V','ema','R'):
                ref.exact(fixed[f's{step}_{key}'],off[f's{step}_{key}'],'fixed / disabled writer body');count+=1
            ref.exact(off[f's{step}_theta'],built[packet],'writer-off carrier');count+=1
            ref.exact(held[f's{step}_R'],built['body_own'],'protected snapshot');count+=1
    for step in cfg.times:
        for key in KEYS:
            for own,other in (('own','partner'),('own_scrambled','partner_scrambled')):
                ref.exact(raw[f'capture__common__{own}__live'][f's{step}_{key}'][partner],
                    raw[f'capture__common__{other}__live'][f's{step}_{key}'],'paired body reversal');count+=1
            value=raw['capture__common__history_erased__live'][f's{step}_{key}']
            ref.exact(value[partner],value,'history-erased equality');count+=1
    return count


def check_contrasts(records, observed):
    assert observed==analysis.contrasts(records)
    # Separate NumPy reductions check the scalar analysis implementation.
    for item in observed.values():
        a,b=records[item['left']],records[item['right']]
        for key in FIELDS:
            value=float(np.mean([x[key]-y[key] for x,y in zip(a,b)]))
            assert abs(value-item['mean'][key])<=2e-12


def run_block(directory,index,cfg,rcfg,role):
    assert index in (*BLOCKS,*DISPOSABLE) and cfg.replicates==rcfg.parents
    if index in BLOCKS:
        registration=read_json(ROOT/'REGISTRATION.json')
        assert registration['blocks']==list(BLOCKS)
        assert cfg==model.CONFIG and rcfg==model.READOUT and role=='prospective confirmation'
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    tick=time.monotonic();provenance=dict(source={},repairs={},reads={})
    write_json(directory/'CONFIG.json',dict(tissue=index,config=asdict(cfg),readout=asdict(rcfg),role=role,baseline=None))
    ctx=model.source.context(index,cfg);before,parent=model.source.prepare_parent(ctx)
    kept,scrambled,fresh,damaged=model.source.boundary(ctx,parent)
    original={**{'kept_'+k:v for k,v in kept.items()},'scrambled_V':scrambled,'fresh':fresh,
              'damaged_theta':damaged,'codes':ctx['codes'],'native_theta':ctx['native']}
    built=model.boundary.construct(parent['theta'],kept['V'],fresh,damaged,index,cfg.replicates)
    parent_proof=ref.parent(ctx,before,parent)
    source_proof=ref.source_boundary(ctx,parent,original)
    boundary=boundary_checker().check(parent['theta'],kept['V'],fresh,damaged,index,cfg.replicates,built)
    immutable={n:identities(v) for n,v in (('parent',parent),('original',original),('boundary',built))}
    for name,values in (('before',before),('parent',parent),('original',original),('boundary',built)):
        path=directory/(name+'.npz');write_arrays(path,values);provenance['source'][name]=pointer(path,values)
    write_json(directory/'CONTEXT.json',{k:asdict(ctx[k]) for k in ('tissue','ladder','bp')})
    raw_repairs={};packets={};repair_proofs={}
    for name,spec in plan().items():
        state=model.initial(built,original,spec);ref.initial(built,original,spec,state)
        result=model.repair(model.boundary.runtime_context(ctx),state,index,spec)
        path=directory/('repair_'+name+'.npz');raw=write_arrays(path,result['raw'])
        assert result['outgoing']==raw[f's{cfg.sweeps}_theta'].tobytes()
        avg=average_name(spec)
        assert (avg is not None)==(result['average'] is not None)
        if avg:assert result['average']==raw[f'a{cfg.sweeps}_theta'].tobytes()
        repair_proofs[name]=ref.repairs(physical_context(ctx),state,index,spec,raw,result['metadata'])
        write_json(directory/('repair_'+name+'.json'),result['metadata'])
        provenance['repairs'][name]=pointer(path,raw)
        raw_repairs[name]=raw;packets[name]=result['outgoing']
        if avg:packets[avg]=result['average']
    alias_count=aliases(raw_repairs,built,cfg)
    packets.update(input__common=built['common'].tobytes(),input__residual=built['residual'].tobytes(),
        intact_parent=parent['theta'].tobytes(),supplied_positive=(.3*np.repeat(ctx['codes'],cfg.replicates,axis=0)).tobytes())
    packets['reader_off']=packets['input__common'];assert len(packets)==29
    packet_arrays=write_arrays(directory/'packets.npz',{k:np.frombuffer(v,dtype=np.float64).reshape(4*cfg.replicates,16,16) for k,v in packets.items()})
    provenance['packets']=pointer(directory/'packets.npz',packet_arrays)
    reads={};read_proofs={};mapping={};records={}
    for name,packet in packets.items():
        off=name=='reader_off';key=hashlib.sha256(packet+bytes([off])).hexdigest()
        mapping[name]=dict(assay=key,packet_sha256=hashlib.sha256(packet).hexdigest(),reader_off=off)
        if key not in reads:
            result=model.boundary.fresh_read(ctx,packet,rcfg,off=off)
            path=directory/('read_'+key+'.npz');raw=write_arrays(path,result['raw'])
            metadata={k:v for k,v in result.items() if k!='raw'}
            write_json(directory/('read_'+key+'.json'),metadata)
            read_proofs[key]=ref.fresh_read(physical_context(ctx),packet,index,rcfg,off,raw,metadata)
            ref.scores(ctx['codes'],raw,rcfg)
            reads[key]=raw;provenance['reads'][key]=pointer(path,raw)
        records[name]=model.old.record_metrics(ctx,packet_arrays[name],parent,reads[key],rcfg)
        ref.record_scores(packet_arrays[name],parent,ctx['codes'],reads[key],rcfg,records[name])
    for step in rcfg.times:
        value=reads[mapping['input__common']['assay']][f's{step}_V'].reshape(4*cfg.replicates,rcfg.draws,16,16)
        ref.exact(value[built['partners']],value,'common-record reader pairing');alias_count+=1
        value=reads[mapping['reader_off']['assay']][f's{step}_V'].reshape(4,cfg.replicates*rcfg.draws,16,16)
        for message in (1,2,3):ref.exact(value[0],value[message],'disabled reading pairing');alias_count+=1
    assert math.fsum(r['accuracy'] for r in records['reader_off'])/(4*cfg.replicates)==.25
    contrasts=analysis.contrasts(records);check_contrasts(records,contrasts)
    for name,value in (('records',records),('contrasts',contrasts),('read_map',mapping),('PROVENANCE',provenance)):
        write_json(directory/(name+'.json'),value)
    for name,value in (('parent',parent),('original',original),('boundary',built)):
        assert identities(value)==immutable[name]
    proof=dict(status='PASS',tissue=index,role=role,parent=parent_proof,source_boundary=source_proof,
        boundary=boundary,repairs=repair_proofs,reads=read_proofs,records=4*cfg.replicates,
        repair_paths=20,logical_assays=29,unique_assays=len(reads),reused_scientific_trajectories=0,
        native_arrays=8+sum(v['native_arrays'] for v in repair_proofs.values())+sum(v['native_arrays'] for v in read_proofs.values()),
        max_native_error=0.,max_average_error=max(v['max_average_error'] for v in repair_proofs.values()),
        exact_alias_checks=alias_count,independent_physics=True,seconds=time.monotonic()-tick)
    write_json(directory/'CHECK.json',proof)
    write_json(directory/'SAVED_CHECK.json',saved_check(directory,cfg,rcfg))
    return proof


def saved_check(directory,cfg,rcfg):
    proof=read_json(directory/'CHECK.json');assert proof['status']=='PASS'
    provenance=read_json(directory/'PROVENANCE.json');loaded={};array_count=0
    for category in ('source','repairs','reads'):
        loaded[category]={}
        for name,item in provenance[category].items():
            assert Path(item['path']).parent.resolve()==Path(directory).resolve()
            values=open_pointer(item);loaded[category][name]=values;array_count+=len(values)
    packets=open_pointer(provenance['packets']);array_count+=len(packets)
    parent,original,built=[loaded['source'][name] for name in ('parent','original','boundary')]
    count=aliases(loaded['repairs'],built,cfg)
    rows=read_json(directory/'records.json');mapping=read_json(directory/'read_map.json')
    assert set(packets)==set(rows)==set(mapping) and len(rows)==29
    assert set(loaded['repairs'])==set(plan())
    for name,spec in plan().items():
        raw=loaded['repairs'][name];state=model.initial(built,original,spec);ref.initial(built,original,spec,state)
        for key in KEYS:ref.exact(raw['s0_'+key],state[key],'saved initial')
        ref.exact(packets[name],raw[f's{cfg.sweeps}_theta'],'saved outgoing')
        avg=average_name(spec)
        if avg:ref.exact(packets[avg],raw[f'a{cfg.sweeps}_theta'],'saved average')
    for name,expected in (('input__common',built['common']),('input__residual',built['residual']),
                          ('intact_parent',parent['theta']),('supplied_positive',.3*np.repeat(original['codes'],cfg.replicates,axis=0)),
                          ('reader_off',built['common'])):
        ref.exact(packets[name],expected,'saved control')
    seen=set()
    for name,packet in packets.items():
        off=name=='reader_off';key=hashlib.sha256(packet.tobytes()+bytes([off])).hexdigest();seen.add(key)
        assert mapping[name]==dict(assay=key,packet_sha256=hashlib.sha256(packet.tobytes()).hexdigest(),reader_off=off)
        raw=loaded['reads'][key]
        ref.record_scores(packet,parent,original['codes'],raw,rcfg,rows[name])
        for step in rcfg.times:ref.exact(raw[f's{step}_theta'],np.repeat(packet,rcfg.draws,axis=0),'unchanged reader carrier')
    assert seen==set(loaded['reads'])==set(proof['reads'])
    assert count+4*len(rcfg.times)==proof['exact_alias_checks']
    check_contrasts(rows,read_json(directory/'contrasts.json'))
    return dict(status='PASS',array_receipts=array_count,scalar_record_rows=sum(len(v) for v in rows.values()),
        packet_routes=len(mapping),unique_assays=len(seen),no_new_trajectories=True)
