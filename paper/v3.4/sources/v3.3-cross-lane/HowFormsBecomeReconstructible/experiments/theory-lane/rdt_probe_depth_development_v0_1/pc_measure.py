"""Only the missing second writer and terminal read, from an audited cached prefix."""
from pc_common import *
import math
import resource
import shutil
import time


def tick():return time.process_time(),time.monotonic()
def elapsed(t):return dict(cpu=time.process_time()-t[0],wall=time.monotonic()-t[1])
def add(a,b):
    for k in a:a[k]+=b[k]


def decisions(windows,rule):
    means=np.array([math.fsum(v)/32 for v in windows.transpose(0,2,3,4,1).reshape(-1,32)]).reshape(-1,1,2,2)
    aligned=means*rule*np.array([[1.,-1.],[-1.,1.]])
    return (aligned.min(axis=(-2,-1))>.25).astype(np.uint8)


def current_memory_bytes():
    values={}
    for line in Path('/proc/self/status').read_text().splitlines():
        parts=line.split()
        if parts and parts[0] in ('VmRSS:','VmHWM:'):
            require(parts[2]=='kB','Linux memory accounting unit')
            values[parts[0][:-1]]=int(parts[1])*1024
    require(set(values)=={'VmRSS','VmHWM'} and min(values.values())>0,'Current-image memory metrics')
    return values


def check(folder,deadline):
    require(time.time()<deadline,'Fixed job deadline')
    # getrusage can retain a pre-exec high-water count on this launch path.
    # /proc VmHWM refers to the current process image; the ceiling is unchanged.
    require(max(current_memory_bytes().values())<1_500_000_000,'Worker RSS ceiling')
    require(shutil.disk_usage(folder).free>=2_000_000_000,'Free-space floor')


def measure(case,folder,deadline,scope='development',n=20):
    require(scope in STAGES and (n==20 if scope=='development' else 1<=n<=20),'Declared probe scope/count')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    begun=tick();ff,fast,probes=native()
    t=tick();raw=load_arrays(ROOT/'prepared'/case['array_file'],case['array_sha256']);retrieval=elapsed(t)
    packet=raw['packet'];protected=packet.tobytes()
    require(hashlib.sha256(protected).hexdigest()==case['packet_sha256'],'Protected g14 packet identity')
    require(raw['writer1_outgoing'].shape==(20,1,2,16,16),'Complete audited first-writer prefix')
    costs={k:dict(cpu=0.,wall=0.) for k in ('writer2','terminal','scoring','flat_audit','evidence','persistence')}
    fields=('mask','birth','end','windows','outgoing','passed')
    data={phase+'_'+name:[] for phase in ('writer2','terminal') for name in fields}
    forcing=[];flat_reads=0
    for begin in range(0,n,4):
        check(folder,deadline)
        indices=list(range(begin,min(n,begin+4)))
        t=tick()
        we=[probes.environment(STAGES[scope],case['key'],i,'writer',case['regime']) for i in indices]
        written=fast.read_batch(raw['writer1_outgoing'][indices],we)
        add(costs['writer2'],elapsed(t))
        t=tick()
        te=[probes.environment(OLD_STAGE,case['key'],i,'evaluation',case['regime']) for i in indices]
        tested=fast.read_batch(written['outgoing'],te)
        add(costs['terminal'],elapsed(t))
        t=tick();wp=probes.task(written['windows'],case['rule'])[2];tp=probes.task(tested['windows'],case['rule'])[2]
        add(costs['scoring'],elapsed(t))
        if begin==0:
            t=tick()
            # The cached source is a boundary already audited in E107. New flat descendants
            # inherit their own independently written state, never the new primary output.
            fw=probes.audit.read_write(raw['writer1_outgoing'][0],*we[0],ff.P['reader'],ff.P['writer']['beta'])
            probes.compare({k:v[0] for k,v in written.items()},fw)
            ft=probes.audit.read_write(fw['outgoing'],*te[0],ff.P['reader'],ff.P['writer']['beta'])
            probes.compare({k:v[0] for k,v in tested.items()},ft)
            flat_reads=2;add(costs['flat_audit'],elapsed(t))
        t=tick()
        for phase,envs,result,passed in (('writer2',we,written,wp),('terminal',te,tested,tp)):
            require(np.array_equal(passed,decisions(result['windows'],case['rule'])),'Independent endpoint arithmetic')
            for j,i in enumerate(indices):
                hashes={name:hashlib.sha256(v.tobytes()).hexdigest() for name,v in zip(('mask','birth','noise'),envs[j],strict=True)}
                if phase=='terminal':
                    require(hashes==case['evaluation_forcing'][i]['sha256'],'Original paired terminal forcing')
                    require(np.array_equal(envs[j][0],raw['evaluation_mask'][i]) and
                            np.array_equal(envs[j][1],raw['evaluation_birth'][i]),'Terminal mask/birth identity')
                forcing.append(dict(phase=phase,probe=i,stage=STAGES[scope] if phase=='writer2' else OLD_STAGE,
                                    purpose='writer' if phase=='writer2' else 'evaluation',sha256=hashes))
                data[phase+'_mask'].append(envs[j][0]);data[phase+'_birth'].append(envs[j][1])
                for name in ('end','windows','outgoing'):data[phase+'_'+name].append(result[name][j])
                data[phase+'_passed'].append(passed[j])
        require(packet.tobytes()==protected,'Incoming packet was altered')
        add(costs['evidence'],elapsed(t))
    require(len({f['sha256']['noise'] for f in forcing})==2*n,'Reused writer/terminal forcing')
    data={k:np.stack(v) for k,v in data.items()}
    data.update(packet=packet,writer1_outgoing=raw['writer1_outgoing'][:n],probes=np.arange(n,dtype=np.int64))
    passed=int(data['terminal_passed'].sum());q=passed/n
    t=tick();digest=save_arrays(folder/'arrays.npz',data);add(costs['persistence'],elapsed(t))
    receipt=dict(case_id=case['case_id'],key=case['key'],block=case['block'],regime=case['regime'],
        current_pass=case['current_pass'],rule=case['rule'],scope=scope,stage=STAGES[scope],branches=n,
        passed=passed,q2=q,new_primary_native_reads=2*n,new_flat_audit_reads=flat_reads,
        cached_first_writer_reads=n,charged_depth2_standalone_reads=3*n,
        charged_inherited_writes=2*n,charged_terminal_reads=n,charged_captures=3*n,
        raw_sha256=digest,input_file=case['array_file'],input_sha256=case['array_sha256'],
        writer1_original_source_sha256=case['writer1_source_sha256'],forcing=forcing,
        phase_seconds=costs,input_retrieval_seconds=retrieval,total_seconds=elapsed(begun),
        independent_flat_descendants=True,original_packet_protected=True,current_image_memory_bytes=current_memory_bytes(),
        new_target_futures=0,new_founders=0,new_fits=0)
    write(folder/'RECEIPT.json',receipt)
    return receipt


def worker(task):
    case,folder,deadline,scope,n=task
    return measure(case,folder,deadline,scope,n)
