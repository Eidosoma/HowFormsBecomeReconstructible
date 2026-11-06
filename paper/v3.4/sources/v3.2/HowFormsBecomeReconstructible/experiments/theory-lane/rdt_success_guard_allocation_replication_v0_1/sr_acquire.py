"""Unchanged native acquisition with fresh acquisition/selection namespaces."""
from copy import deepcopy
import time

from sr_common import ROOT,P,np,bridge,ev,read,write,sha,stamp,binding,byte_equal
import acquisition
import ledger
import verify_science

ORIGINAL=deepcopy(read(ROOT/'native/protocol.json'))


def configure(stage):
    if stage not in P['stages']:raise ValueError('Undeclared acquisition stage')
    value=deepcopy(ORIGINAL)
    value['acquisition']['namespace']=P['namespace']+'/'+stage+'/acquisition'
    value['selection']['namespace']=P['namespace']+'/'+stage+'/selection'
    bridge.P.clear();bridge.P.update(value)
    return dict(acquisition=value['acquisition']['namespace'],selection=value['selection']['namespace'])


def check_rows(rows,block):
    expected={(block,h,f,r) for h in ORIGINAL['acquisition']['histories'] for f in range(4) for r in range(4)}
    keys=[tuple(r['key']) for r in rows]
    if len(keys)!=64 or set(keys)!=expected:raise ValueError('Full64-record native boundary required')
    for row in rows:
        if row['block']!=block or row['rule']!=(1 if row['founder']%2==0 else -1):raise ValueError('Native task identity changed')
        if row['current_pass'] not in (0,1):raise ValueError('Binary boundary label required')


def perform(folder,task,guard):
    start,cpu=time.monotonic(),time.process_time()
    block,stage=task['block'],task['stage'];legacy=bool(task.get('legacy',False))
    if legacy and (stage!='qualification' or block!=P['legacy_block']):raise ValueError('Legacy replay is qualification only')
    namespaces=configure(stage)
    raw,rows,receipt=acquisition.acquire(block,stage,folder,guard,legacy=legacy)
    check_rows(rows,block)
    if legacy:
        archive=ev.load(ROOT/'native/context/legacy_g14.npz',sha(ROOT/'native/context/legacy_g14.npz'))
        for name in ('end','outgoing','mean_ports'):byte_equal(raw[name],archive[name],'legacy g14 '+name)
    ev.save(folder/'boundary.npz',raw)
    write(folder/'ENROLLMENT.json',dict(rows=rows,receipt=receipt,namespaces=namespaces))
    audit=verify_science.boundary(ROOT/'native',folder,rows,False)
    audit.update(full_teaching_replay=receipt['teaching'],native_flat_audits=receipt['audits'],legacy_byte_exact=legacy)
    write(folder/'VERIFICATION.json',audit)
    guard.check()
    payload=dict(stage=stage,block=block,legacy=legacy,rows=rows,namespaces=namespaces,
        native_reads=receipt['native_reads'],flat_native_reads=receipt['flat_native_reads'],
        teaching_episodes=2,wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
    if payload['native_reads']!=896 or payload['flat_native_reads']!=12:raise ArithmeticError('Acquisition cost differs')
    ledger.commit(folder,dict(binding=binding(),kind='acquire',stage=stage,block=block,legacy=legacy),payload)
    return payload


def verify(folder,stage,block,legacy=False):
    value=ledger.verify(folder,dict(binding=binding(),kind='acquire',stage=stage,block=block,legacy=legacy))
    rows=read(folder/'ENROLLMENT.json')['rows'];payload=value['payload']
    check_rows(rows,block)
    if rows!=payload['rows'] or payload['stage']!=stage or payload['block']!=block or payload['legacy']!=legacy:
        raise ValueError('Acquisition commitment identity differs')
    if read(folder/'VERIFICATION.json')['status']!='PASS':raise ValueError('Acquisition audit missing')
    if payload['native_reads']!=896 or payload['flat_native_reads']!=12:raise ValueError('Acquisition accounting differs')
    expected=dict(acquisition=P['namespace']+'/'+stage+'/acquisition',selection=P['namespace']+'/'+stage+'/selection')
    if payload['namespaces']!=expected:raise ValueError('Acquisition namespace differs')
    return rows,payload
