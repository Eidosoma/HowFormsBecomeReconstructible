"""Fresh acquisition through fourteen native generations with complete replay."""
from study import *
import time
import lineage, lineage_audit as audit, reader

def initial_pass(means):
 x=means.reshape(16,2,2);founders=np.repeat(np.arange(4),4)
 return reader.scores(x[None,:,None,None],founders,.25)['both_pass'].reshape(16)

def teach(seed):
 a=lineage.teaching(seed,NCFG);proof=audit.equal(a,audit.teaching(seed,NCFG),'teaching')
 return a,proof

def rebuild(packets,seed,generation,h):
 code=[int(generation in SCHEDULES[h])]
 args=(packets,seed,generation,code,NCFG,CYCLE,TOLERANCE)
 a=lineage.rebuild(*args);proof=audit.equal(a,audit.rebuild(*args),f'g{generation}')
 proof.update(generation=generation,writer_code=code[0]);return a,proof

def retained_boundary(raw,generation,h):
 assert h in (0,2)
 known=arrays(ROOT/f'source/known/g{generation}.npz');slot=0 if h==0 else 1
 expected={k:known[k] if k in ('birth','masks') else known[k][slot:slot+1] for k in raw}
 audit.equal(raw,expected,'retained native boundary')

def known():
 raw=arrays(ROOT/'source/known/g14.npz');teaching=arrays(ROOT/'source/known/teaching.npz')
 return dict(outgoing=raw['outgoing'][0].reshape(16,4096),initial_pass=initial_pass(raw['mean_ports'][0]),history=0,teaching=teaching)

def generate(folder,index,role):
 folder=Path(folder);folder.mkdir(exist_ok=False);seed=source_identity(index,role);h=history(index);tick=time.monotonic()
 raw,proof=teach(seed);save(folder/'teaching.npz',raw)
 if role=='qualification':audit.equal(raw,arrays(ROOT/'source/known/teaching.npz'),'retained teaching')
 teaching=raw;packets=np.repeat(raw['acquired'][:,None],4,axis=1)[None];receipts=[]
 for generation in range(1,15):
  space();raw,check=rebuild(packets,seed,generation,h)
  if role=='qualification' and generation>=12:retained_boundary(raw,generation,h)
  path=folder/f'g{generation:02d}.npz';save(path,dict(incoming=packets,history=np.array(h),generation=np.array(generation),**raw))
  check.update(file=str(path),sha256=sha(path));receipts.append(check);packets=raw['outgoing']
 write(folder/'REPLAY.json',dict(status='PASS',source_identity=seed,history=h,teaching=proof,generations=receipts,
  full_native_replay=True,records=16,rebuild_contexts=224,seconds=time.monotonic()-tick,new_source_population=role=='production'))
 return dict(outgoing=packets.reshape(16,4096),initial_pass=initial_pass(raw['mean_ports']),history=h,teaching=teaching)

def benchmark(folder):
 folder=Path(folder);folder.mkdir(exist_ok=False);tick=time.monotonic();raw,proof=teach(34000)
 audit.equal(raw,arrays(ROOT/'source/known/teaching.npz'),'preflight teaching');save(folder/'teaching.npz',raw)
 times=[];proofs=[proof]
 for generation,h in ((13,0),(13,2),(14,2)):
  previous=arrays(ROOT/f'source/known/g{generation-1}.npz');slot=0 if h==0 else 1
  start=time.monotonic();raw,check=rebuild(previous['outgoing'][slot:slot+1],34000,generation,h)
  retained_boundary(raw,generation,h);times.append(time.monotonic()-start);proofs.append(check)
  save(folder/f'g{generation}_h{h}.npz',raw)
 receipt=dict(status='PASS',seconds=time.monotonic()-tick,rebuild_seconds=times,proofs=proofs,new_production_sources=False)
 write(folder/'COMPLETE.json',receipt);return receipt
