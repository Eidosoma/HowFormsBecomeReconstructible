"""Four coupled policies on one fresh block; independent cue noise."""
import argparse
import ctypes
import os
from pathlib import Path
import signal
import time
import traceback
from sr_common import ROOT,P,POLICIES,np,fast_reader,flat,ev,read,write,sha,stamp,digest,byte_equal,Deadline,binding,verify_snapshot
import sr_forcing
import sr_policy
import sr_quota
import sr_source
import sr_unit_audit as independent


def evolve(rows,initial,stage,injury,regime,output,guard,seal_path,seal_hash):
    started,cpu=time.monotonic(),time.process_time()
    if sha(seal_path)!=seal_hash or len(rows)!=4 or len({r['block'] for r in rows})!=1:raise ValueError('One bound four-packet group required')
    histories=np.array([r['current_pass'] for r in rows],np.uint8);rules=np.array([r['rule'] for r in rows],np.int8)
    incoming=np.repeat(initial[:,None],4,axis=1);flat_packets=incoming.copy()
    saved={n:[] for n in ('incoming','mask','birth','end','windows','outgoing','passed','classes','aligned','actions','allocation_order','quota_count')}
    fsaved={n:[] for n in ('flat_incoming','flat_end','flat_windows','flat_outgoing','flat_actions')}
    forcing=[];audits=[];allocation=[]
    for generation in P['generations']:
        guard.check();pairs=[sr_forcing.environment(stage,r['key'],generation,injury,regime) for r in rows];envs=[e for e,record in pairs]
        before=incoming.copy();result=fast_reader.read_batch(incoming,envs)
        byte_equal(incoming,before,'reader leaves incoming unchanged')
        passed,classes,aligned=sr_policy.classify(result['windows'],rules)
        order=sr_quota.order(stage,rows[0]['block'],generation)
        after,actions=sr_policy.advance(incoming,result['outgoing'],passed,order)
        if generation==33:actions=np.zeros_like(actions);after=incoming.copy()
        # The audit independently propagates all donor and control packets.
        flat_results=[]
        for j in range(4):
            guard.check();flat_results.append(flat.read_write(flat_packets[j],*envs[j],P['reader'],P['writer']['beta']))
        fr={name:np.stack([x[name] for x in flat_results]) for name in ('end','windows','outgoing')}
        for name in fr:byte_equal(result[name],fr[name],'full independently propagated flat '+name)
        fclasses=[[independent.raw_class(fr['windows'][j,:,arm],rows[j]['rule'])[0] for arm in range(4)] for j in range(4)]
        forder=independent.independent_order(stage,rows[0]['block'],generation)
        fa=independent.scalar_actions(fclasses,forder,generation)
        byte_equal(actions,fa,'independent contemporaneous quota action')
        next_flat=flat_packets.copy()
        for j in range(4):
            byte_equal(incoming[j,3],initial[j],'protected original')
            for arm in range(4):
                if fa[j,arm]:next_flat[j,arm]=fr['outgoing'][j,arm]
            if generation==15:
                for arm in (1,2,3):byte_equal(result['windows'][j,:,0],result['windows'][j,:,arm],'shared first read')
        byte_equal(after,next_flat,'independent full-group inheritance')
        saved['incoming'].append(incoming.copy());saved['mask'].append(np.stack([e[0] for e in envs]));saved['birth'].append(np.stack([e[1] for e in envs]))
        for name in result:saved[name].append(result[name])
        for name,value in [('passed',passed),('classes',classes),('aligned',aligned),('actions',actions),('allocation_order',order),('quota_count',np.array(actions[:,2].sum(),np.int64))]:saved[name].append(value)
        fsaved['flat_incoming'].append(flat_packets.copy());fsaved['flat_actions'].append(fa)
        for name in fr:fsaved['flat_'+name].append(fr[name])
        for env,(_,record) in zip(envs,pairs):
            for name,array in zip(('mask','birth','noise'),env):
                if digest(array)!=record[name+'_sha256']:raise ArithmeticError('Forcing was mutated')
            forcing.append(record)
        allocation.append(dict(generation=generation,block=rows[0]['block'],order=order.tolist(),guard_promotions=int(actions[:,2].sum()),random_promotions=int(actions[:,1].sum())))
        audits.append(dict(generation=generation,packets=4,policies=4,byte_exact=True))
        incoming=after;flat_packets=next_flat
    arrays={name:np.stack(values) for name,values in {**saved,**fsaved}.items()}
    arrays.update(initial_packets=initial,generations=np.array(P['generations'],np.int64),histories=histories,rules=rules,final_packets=incoming)
    raw_hash=ev.save(output.with_suffix('.npz'),arrays);outcomes=[]
    for j,row in enumerate(rows):
        for arm,name in enumerate(POLICIES):
            y=arrays['passed'][1:,j,arm]
            outcomes.append(dict(key=row['key'],block=row['block'],history_class=row['current_pass'],rule=row['rule'],injury=injury,regime=regime,policy=name,
                initial_pass=int(arrays['passed'][0,j,arm]),downstream_successes=int(y.sum()),downstream_reads=18,terminal=int(y[-1]),uninterrupted=int(y.all()),
                opposite_reads=int((arrays['classes'][1:,j,arm]==-1).sum()),promotions=int(arrays['actions'][:-1,j,arm].sum()),passed=arrays['passed'][:,j,arm].tolist()))
    receipt=dict(stage=stage,injury=injury,regime=regime,rows=rows,raw_sha256=raw_hash,policy_seal_sha256=seal_hash,forcing=forcing,allocation=allocation,
                 audits=audits,native_reads=304,flat_native_reads=304,executed_native_writer_constructions=304,policy_decision_opportunities=288,
                 wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu)
    write(output.with_suffix('.json'),receipt);return outcomes,receipt


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
            if (run/'COHORT.json').exists() or (run/'FUTURE_RELEASE.json').exists() or (run/'scientific').exists():raise ValueError('Acquisition after cohort sealing is forbidden')
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
                                         primary_native_reads=304,flat_native_reads=304))
        files={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file()}
        write(folder/'COMPLETE.json',dict(utc=stamp(),status='COMPLETE_AUDITED',stage=task['stage'],block=task['block'],injury=task['injury'],
              sha256=files,binding=binding(),policy_seal_sha256=task['seal_sha256'],outcomes=16,
              native_reads=304,flat_native_reads=304,wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu))
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL,0)
        write(folder/'FAILED.json',dict(utc=stamp(),traceback=traceback.format_exc(),automatic_retry=False))
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('task');args=parser.parse_args()
    execute(read(args.task))
