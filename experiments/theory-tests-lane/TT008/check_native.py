"""Excluded short dynamics fixture and exact development-boundary diagnostics."""
import hashlib
import time
import numpy as np
import auditor as a
import native as n
import measure
import support as s


def run(output=None):
    began=time.monotonic();plan=s.read(s.HERE/'plan.json');cfg=dict(plan['native_config'],recipients=1,teach_steps=12,capture_steps=6,observe_steps=4)
    cycle=dict(plan['native_cycle'],read_steps=24,settling_steps=12);block=plan['excluded_technical_block'];receipts=[]
    source=n.teaching(block,cfg);receipts.append(a.equal(source,a.teaching(block,cfg),'teaching'))
    initial=np.repeat(source['acquired'][:,None],cfg['recipients'],axis=1);packets=np.repeat(initial[None],4,axis=0);boundary=None
    for generation in range(1,33):
        codes=[int(generation in times) for times in plan['tolerance_generations']]
        raw=n.rebuild(packets,block,generation,codes,cfg,cycle,1e-4)
        receipts.append(a.equal(raw,a.rebuild(packets,block,generation,codes,cfg,cycle,1e-4),f'g{generation}'))
        packets=raw['outgoing']
        if generation==14:boundary=raw
    terminal=n.assay(packets,block,32,cfg,cycle);receipts.append(a.equal(terminal,a.assay(packets,block,32,cfg,cycle),'terminal'))
    rows,packet=measure.records(block,boundary);s.require(len(rows)==16 and packet.shape==(16,512),'Measurement shape')
    s.require(all('terminal_success' not in row for row in rows),'Future target in measurement')
    final=measure.terminal(block,terminal);s.require(len(final)==60,'Terminal shape')
    corrupted={k:v.copy() for k,v in terminal.items()};corrupted['end'].flat[0]=np.nextafter(corrupted['end'].flat[0],np.inf)
    try:a.equal(corrupted,terminal,'intentional corruption')
    except ValueError:pass
    else:raise AssertionError('Dynamics corruption undetected')
    known=s.records();packets=s.packets(known);maximum=0.
    for i in range(0,512,16):
        row=known[i];signed,unsigned=measure.transfer(packets[i].astype('<f8').view(np.uint8),row['task_rule'])
        maximum=max(maximum,s.close([signed,unsigned],[row['signed_transfer'],row['unsigned_access']],1e-13,'TT007 diagnostics'))
    result=dict(status='PASS',seconds=time.monotonic()-began,excluded_block=block,teaching_replays=1,rebuild_replays=32,terminal_replays=1,
        arrays_compared=sum(r['arrays'] for r in receipts),replay_receipts=receipts,development_transfer_contexts=32,maximum_transfer_error=maximum,
        prospective_test_outcomes_generated=False)
    if output:s.dump(output/'native_checks.json',result)
    return result


if __name__=='__main__':
    result=run();print({k:v for k,v in result.items() if k!='replay_receipts'})
