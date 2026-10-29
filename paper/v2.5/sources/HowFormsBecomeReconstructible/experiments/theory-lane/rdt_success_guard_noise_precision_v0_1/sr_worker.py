"""One block/injury, both regimes and all four evolving policies."""
import argparse
import ctypes
import math
import os
from pathlib import Path
import signal
import time
import traceback

from sr_common import ROOT,P,POLICIES,np,fast_reader,flat,ev,read,write,sha,stamp,digest,byte_equal,Deadline,binding,verify_snapshot
import sr_forcing
import sr_policy
import sr_source


def scalar_flat_success(windows,rule):
    y=[]
    for arm in range(4):
        values=[math.fsum(float(windows[t,arm,c,p]) for t in range(len(windows)))/len(windows)*rule*(1 if c==p else -1)
                for c in range(2) for p in range(2)]
        y.append(int(min(values)>.25))
    return y


def scalar_flat_actions(h,passed):
    return [True,not(h==1 and passed[1]==0),bool(passed[2]),False]


def evolve(rows,initial,stage,injury,regime,output,guard,seal_path,seal_hash):
    started,cpu=time.monotonic(),time.process_time()
    if sha(seal_path)!=seal_hash:raise ValueError('Unchanged policy/panel seal required')
    histories=np.array([r['current_pass'] for r in rows],np.uint8)
    rules=np.array([r['rule'] for r in rows],np.int8)
    incoming=np.repeat(initial[:,None],4,axis=1)
    audit_index=min(range(4),key=lambda j:rows[j]['selection_hash'])
    flat_packet=np.repeat(initial[audit_index:audit_index+1],4,axis=0)
    saved={n:[] for n in ('incoming','mask','birth','end','windows','outgoing','passed','classes','aligned','actions')}
    fsaved={n:[] for n in ('flat_incoming','flat_end','flat_windows','flat_outgoing','flat_actions')}
    forcing=[];audits=[]
    for generation in P['generations']:
        guard.check()
        pairs=[sr_forcing.environment(stage,r['key'],generation,injury,regime) for r in rows]
        envs=[e for e,record in pairs]
        original=incoming.copy()
        result=fast_reader.read_batch(incoming,envs)
        byte_equal(incoming,original,'reader does not mutate incoming packet')
        passed,classes,aligned=sr_policy.classify(result['windows'],rules)
        after,actions=sr_policy.advance(incoming,result['outgoing'],histories,passed)
        if generation==33:actions=np.zeros_like(actions);after=incoming.copy()
        # Both identity controls concern actual native states, not merely outcome labels.
        for j,h in enumerate(histories):
            byte_equal(incoming[j,3],initial[j],'protected copy')
            if h==0:
                for name,value in [('incoming',incoming),*result.items()]:
                    # Native windows place frame before policy.
                    if name=='windows':byte_equal(value[j,:,0],value[j,:,1],'H0 window identity')
                    else:byte_equal(value[j,0],value[j,1],'H0 '+name+' identity')
            if generation==15:
                for arm in range(1,4):
                    byte_equal(result['windows'][j,:,0],result['windows'][j,:,arm],'pre-action read identity')
        independent=flat.read_write(flat_packet,*envs[audit_index],P['reader'],P['writer']['beta'])
        for name in ('end','windows','outgoing'):
            byte_equal(result[name][audit_index],independent[name],'independently propagated flat '+name)
        fy=scalar_flat_success(independent['windows'],rows[audit_index]['rule'])
        fa=scalar_flat_actions(int(histories[audit_index]),fy) if generation<33 else [False]*4
        if fy!=passed[audit_index].tolist() or fa!=actions[audit_index].tolist():
            raise ArithmeticError('Flat policy decision differs')
        fsaved['flat_incoming'].append(flat_packet.copy())
        for name in ('end','windows','outgoing'):fsaved['flat_'+name].append(independent[name].copy())
        fsaved['flat_actions'].append(np.array(fa,bool))
        next_flat=flat_packet.copy()
        for arm in range(4):
            if fa[arm]:next_flat[arm]=independent['outgoing'][arm]
        byte_equal(next_flat,after[audit_index],'independent flat inheritance')
        saved['incoming'].append(incoming.copy())
        saved['mask'].append(np.stack([x[0] for x in envs]));saved['birth'].append(np.stack([x[1] for x in envs]))
        for name in ('end','windows','outgoing'):saved[name].append(result[name])
        for name,value in [('passed',passed),('classes',classes),('aligned',aligned),('actions',actions)]:saved[name].append(value)
        for env,(_,record) in zip(envs,pairs):
            for name,array in zip(('mask','birth','noise'),env):
                if digest(array)!=record[name+'_sha256']:raise ArithmeticError('Forcing was mutated')
            forcing.append(record)
        audits.append(dict(generation=generation,key=rows[audit_index]['key'],policies=4,byte_exact=True))
        incoming=after;flat_packet=next_flat
    arrays={name:np.stack(values) for name,values in {**saved,**fsaved}.items()}
    arrays.update(initial_packets=initial,generations=np.array(P['generations'],np.int64),
                  histories=histories,rules=rules,final_packets=incoming,audit_index=np.array(audit_index,np.int64))
    raw_hash=ev.save(output.with_suffix('.npz'),arrays)
    outcomes=[]
    for j,row in enumerate(rows):
        for arm,name in enumerate(POLICIES):
            y=arrays['passed'][1:,j,arm]
            outcomes.append(dict(key=row['key'],block=row['block'],history_class=row['current_pass'],rule=row['rule'],
                injury=injury,regime=regime,policy=name,initial_pass=int(arrays['passed'][0,j,arm]),
                downstream_successes=int(y.sum()),downstream_reads=18,terminal=int(y[-1]),uninterrupted=int(y.all()),
                opposite_reads=int((arrays['classes'][1:,j,arm]==-1).sum()),
                promotions=int(arrays['actions'][:-1,j,arm].sum()),passed=arrays['passed'][:,j,arm].tolist()))
    receipt=dict(stage=stage,injury=injury,regime=regime,rows=rows,raw_sha256=raw_hash,
        policy_seal_sha256=seal_hash,forcing=forcing,audits=audits,native_reads=19*4*4,flat_native_reads=19*4,
        executed_native_writer_constructions=19*4*4,policy_decision_opportunities=18*4*4,
        wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu)
    write(output.with_suffix('.json'),receipt)
    return outcomes,receipt


def execute(task):
    folder=Path(task['output']);folder.mkdir(parents=True,exist_ok=False)
    started,cpu=time.monotonic(),time.process_time()
    def expired(*args):raise TimeoutError('Worker stage deadline or termination; no retry')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,max(.001,task['deadline']-time.time()))
    try:
        if os.getppid()!=task['parent_pid']:raise RuntimeError('Worker parent disappeared')
        if ctypes.CDLL(None).prctl(1,signal.SIGTERM,0,0,0)!=0:raise OSError('Cannot arm parent-death termination')
        if os.getppid()!=task['parent_pid']:raise RuntimeError('Worker parent disappeared during startup')
        verify_snapshot()
        if binding()!=task['binding']:raise ValueError('Task binding mismatch')
        guard=Deadline(task['deadline']);guard.check()
        run=Path(task['run'])
        if task['stage']=='scientific':
            qualification=read(run/'QUALIFICATION.json')
            release=read(run/'ACQUISITION_RELEASE.json')
            if qualification['status']!='PASS' or release['qualification_sha256']!=sha(run/'QUALIFICATION.json') or release['binding']!=binding():
                raise ValueError('Scientific work lacks successful qualification')
        write(folder/'START.json',dict(utc=stamp(),pid=os.getpid(),task=task))
        if task['kind']=='acquire':
            if (run/'scientific').exists():raise ValueError('Acquisition after scientific futures is forbidden')
            import sr_acquire
            sr_acquire.perform(folder,task,guard)
            return
        if task['kind']!='future':raise ValueError('Undeclared work kind')
        rows,packets=sr_source.load(task['stage'],task['block'],run)
        seal=read(task['seal_path'])
        if sha(task['seal_path'])!=task['seal_sha256'] or seal['binding']!=binding():raise ValueError('Seal identity mismatch')
        if [r for r in seal['rows'] if r['block']==task['block']]!=rows:raise ValueError('Panel changed after seal')
        if task['stage']=='scientific':
            release=read(run/'FUTURE_RELEASE.json')
            if (release['policy_seal_sha256']!=task['seal_sha256'] or seal['cohort_sha256']!=sha(run/'COHORT.json')
                    or release['qualification_sha256']!=sha(run/'QUALIFICATION.json')):
                raise ValueError('Scientific future lacks the complete-cohort release')
        outcomes=[];checks=[]
        import sr_unit_audit
        for regime in P['regimes']:
            y,receipt=evolve(rows,packets,task['stage'],task['injury'],regime,folder/regime,
                             guard,Path(task['seal_path']),task['seal_sha256'])
            check=sr_unit_audit.audit_case(folder/regime,rows,task['stage'],task['injury'],regime,task['seal_sha256'])
            write(folder/(regime+'_AUDIT.json'),check);checks.append(check);outcomes.extend(y)
            guard.check()
        write(folder/'OUTCOMES.json',outcomes)
        write(folder/'RESOURCES.json',dict(wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
                                         primary_native_reads=608,flat_native_reads=152))
        files={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file()}
        write(folder/'COMPLETE.json',dict(utc=stamp(),status='COMPLETE_AUDITED',stage=task['stage'],block=task['block'],injury=task['injury'],
              sha256=files,binding=binding(),policy_seal_sha256=task['seal_sha256'],outcomes=32,
              native_reads=608,flat_native_reads=152,wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu))
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL,0)
        write(folder/'FAILED.json',dict(utc=stamp(),traceback=traceback.format_exc(),automatic_retry=False))
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('task');args=parser.parse_args()
    execute(read(args.task))
