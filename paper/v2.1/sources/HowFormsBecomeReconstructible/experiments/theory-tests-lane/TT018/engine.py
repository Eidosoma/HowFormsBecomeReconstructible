"""Acquisition, globally sealed forecasts, and fully replayed restored futures."""
import time
import numpy as np
import core
import current_repair
import lineage
import record_features
import serial
import serial_audit as audit
import support as s


def teaching(identity,cfg):
    raw=lineage.teaching(identity,cfg['native_config'])
    return raw,core.equal(raw,core.teaching(identity,cfg['native_config']),'teaching')


def preliminary(packets,identity,generation,history,cfg):
    code=int(generation in cfg['tolerance_generations'][history])
    args=(packets,identity,generation,[code],cfg['native_config'],cfg['native_cycle'],cfg['tolerance'])
    raw=lineage.rebuild(*args)
    receipt=core.equal(raw,core.rebuild(*args),'preliminary')
    return raw,dict(**receipt,generation=generation,writer_code=code,contexts=16)


def checked_read(packets,record,futures,generation,rule,cfg,terminal=False):
    arguments=(record,list(futures),generation,cfg['development_config'],terminal)
    raw=serial.read_packets(packets,serial.Draws(*arguments),cfg['development_config'],cfg['cycle'],write=not terminal)
    reference=audit.read_packets(packets,audit.Draws(*arguments),cfg['development_config'],cfg['cycle'],write=not terminal)
    receipt=audit.compare(raw,reference,'terminal' if terminal else 'continuation')
    rules=np.full(len(futures),rule)
    scored=serial.score(raw['mean_ports'],rules)
    receipt['scoring']=audit.score(raw,rules,scored)
    raw.update(scored)
    s.require(bool('outgoing' in raw)!=terminal,'Terminal assay does not write')
    s.require(np.all(raw['noise_moments'][:,5]==cfg['cycle']['read_steps']*256),'Per-future forcing count')
    return raw,receipt


def handoff(incoming,previous):
    s.equal(incoming,previous,'Each branch inherits its actual previous outgoing bytes')


def first_step(prepared,raw):
    s.equal(prepared[1],prepared[2],'Identical initial one-time and repeated repair')
    for name in ('end','outgoing','mean_ports','both_pass','opposite_pass'):
        s.equal(raw[name][1],raw[name][2],'First paired policy '+name)
    s.equal(raw['port_windows'][:,1],raw['port_windows'][:,2],'First paired policy windows')


def batch(folder,packet,record,futures,rule,cfg,progress):
    """No access to acquisition bodies, masks, model predictions or outcome gates."""
    folder.mkdir(exist_ok=False)
    futures=list(map(int,futures));n=len(futures)
    incoming=np.broadcast_to(packet,(3,n,4096)).copy();previous=incoming.copy()
    body=np.empty((n,3,18),bool);opposite=np.empty_like(body);margins=np.empty((n,3,18))
    calls=np.zeros((n,3),int);added=np.zeros((n,3),int);mass=np.zeros((n,3))
    repair_cpu=np.zeros((n,3));audit_cpu=np.zeros((n,3));receipts=[]
    for index,generation in enumerate(cfg['generations']):
        progress('serial_repair_and_full_replay',record=record,first_future=futures[0],generation=generation)
        handoff(incoming,previous)
        prepared,details=current_repair.prepare(incoming,generation,cfg['optimizer'])
        raw,receipt=checked_read(prepared,record,futures,generation,rule,cfg)
        if generation==15:first_step(prepared,raw)
        name=f'g{generation:02d}.npz'
        s.save(folder/name,dict(futures=np.array(futures),generation=np.array(generation),
            incoming=incoming,prepared=prepared,**details,**raw))
        receipt.update(file=name,file_sha256=s.sha(folder/name),optimizer_checks=int(details['independent_optimizer_checks']))
        receipts.append(receipt)
        body[:,:,index]=raw['both_pass'].T;opposite[:,:,index]=raw['opposite_pass'].T
        margins[:,:,index]=raw['min_margin'].T
        for target,key in ((calls,'applied'),(added,'added_edges'),(mass,'added_abs_weight'),
                           (repair_cpu,'repair_cpu_seconds'),(audit_cpu,'audit_cpu_seconds')):
            target+=details[key].T
        incoming=raw['outgoing'];previous=incoming.copy()
    progress('fresh_terminal_recipient_and_full_replay',record=record,first_future=futures[0])
    handoff(incoming,previous)
    raw,receipt=checked_read(incoming,record,futures,32,rule,cfg,terminal=True)
    s.save(folder/'terminal.npz',dict(futures=np.array(futures),incoming=incoming,**raw))
    receipt.update(file='terminal.npz',file_sha256=s.sha(folder/'terminal.npz'),optimizer_checks=0)
    receipts.append(receipt)
    summary=dict(futures=np.array(futures),body_success=body,body_opposite=opposite,body_margin=margins,
        terminal_success=raw['both_pass'].T,terminal_opposite=raw['opposite_pass'].T,
        terminal_margin=raw['min_margin'].T,repair_calls=calls,added_edges=added,added_abs_weight=mass,
        repair_cpu_seconds=repair_cpu,audit_cpu_seconds=audit_cpu)
    s.equal(calls,np.tile(np.array([0,1,18]),(n,1)),'Fixed calls through all failed bodies')
    s.save(folder/'panel.npz',summary)
    s.dump(folder/'REPLAY.json',dict(status='PASS',record_id=record,futures=futures,contexts=3*n*18,
        terminal_contexts=3*n,optimizer_checks=19*n,all_native_fields_byte_exact=True,receipts=receipts,
        panel_sha256=s.sha(folder/'panel.npz'),terminal_repairs=0,terminal_writes=0))
    return summary


def acquire(folder,index,block,cfg,progress):
    folder.mkdir(exist_ok=False)
    history=index%4;case=index//4
    identity=cfg['lineage_namespace']+':'+str(block)
    record=cfg['continuation_namespace']+':'+str(block)
    s.dump(folder/'ASSIGNMENT.json',dict(utc=s.utc(),block=block,index=index,history=history,case=case,
        record_id=record,selection='preassigned before teaching; no outcome filter'))
    progress('acquisition_teaching_and_full_replay',block=block)
    teach,teach_receipt=teaching(identity,cfg);s.save(folder/'teaching.npz',teach)
    packets=np.repeat(teach['acquired'][:,None],4,axis=1)[None];receipts=[]
    for generation in range(1,15):
        progress('acquisition_rebuild_and_full_replay',block=block,generation=generation)
        raw,receipt=preliminary(packets,identity,generation,history,cfg)
        name=f'g{generation:02d}.npz'
        s.save(folder/name,dict(incoming=packets,**raw))
        receipt.update(file=name,file_sha256=s.sha(folder/name));receipts.append(receipt)
        packets=raw['outgoing']
    packet=packets.reshape(16,4096)[case].copy();means=raw['mean_ports'].reshape(16,2,2)[case].copy()
    row,predictions,diagnostics=record_features.boundary(packet,means,history,case,cfg,record)
    row.update(block=block,index=index,history_index=history)
    s.save(folder/'selected.npz',dict(packet=packet,mean_ports=means,case=np.array(case),history=np.array(history)))
    s.dump(folder/'FORECASTS.json',dict(row=row,predictions=predictions,diagnostics=diagnostics,
        target='untreated_terminal_fresh_recipient',models_sha256=s.sha(s.HERE/'sources/tt008/FROZEN_MODELS.json')))
    s.dump(folder/'ACQUISITION_REPLAY.json',dict(status='PASS',teaching=teach_receipt,preliminary=receipts,
        teaching_sha256=s.sha(folder/'teaching.npz'),contexts=224))
    files=('ASSIGNMENT.json','selected.npz','FORECASTS.json','ACQUISITION_REPLAY.json','g14.npz')
    seal=dict(utc=s.utc(),block=block,index=index,history=history,case=case,record_id=record,
        files_sha256={name:s.sha(folder/name) for name in files})
    s.dump(folder/'SEAL.json',seal)
    return dict(folder=folder.name,seal_sha256=s.sha(folder/'SEAL.json'),record_id=record)


def verify_seal(folder,entry):
    s.require(s.sha(folder/'SEAL.json')==entry['seal_sha256'],'Original record seal')
    seal=s.read(folder/'SEAL.json')
    for name,digest in seal['files_sha256'].items():s.require(s.sha(folder/name)==digest,'Sealed acquisition '+name)
    return seal


def validate(output,cfg,progress):
    """Called only by the registered, qualified execution gate in run.py."""
    (output/'records').mkdir(exist_ok=False)
    entries=[]
    for index,block in enumerate(cfg['blocks']):
        entries.append(acquire(output/'records'/str(block),index,block,cfg,progress))
    s.require(len(entries)==64,'All selected records before any continuation')
    s.dump(output/'COHORT_SEAL.json',dict(utc=s.utc(),records=entries,
        registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),forecasts=192))
    cohort_hash=s.sha(output/'COHORT_SEAL.json')
    s.dump(output/'CONTINUATION_STARTED.json',dict(utc=s.utc(),cohort_seal_sha256=cohort_hash))
    for entry in entries:
        folder=output/'records'/entry['folder'];verify_seal(folder,entry)
        selected=s.arrays(folder/'selected.npz');forecast=s.read(folder/'FORECASTS.json')
        panels=[]
        for first in range(0,64,cfg['batch_size']):
            panels.append(batch(folder/f'futures_{first:02d}',selected['packet'],entry['record_id'],
                range(first,first+cfg['batch_size']),forecast['row']['task_rule'],cfg,progress))
        panel={key:np.concatenate([x[key] for x in panels]) for key in panels[0]}
        s.equal(panel['futures'],np.arange(64),'Every future retained exactly once')
        s.save(folder/'panel.npz',panel)
        s.dump(folder/'SERIAL_SEAL.json',dict(utc=s.utc(),cohort_seal_sha256=cohort_hash,
            panel_sha256=s.sha(folder/'panel.npz'),batches={f'futures_{first:02d}':s.sha(folder/f'futures_{first:02d}'/'REPLAY.json')
                for first in range(0,64,cfg['batch_size'])}))
    s.require(s.sha(output/'COHORT_SEAL.json')==cohort_hash,'Global seal unchanged through all futures')
    import analysis
    result=analysis.run(output,cfg,progress)
    import report
    report.run(output,result)
    return result
